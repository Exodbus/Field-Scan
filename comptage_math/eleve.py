"""Élève de E-017 : réseau de cartes de chaleur entraîné sur les pseudo-étiquettes du vote B′ (performance-engineer).

Version du 7 novembre 2026. Décision D-009, pré-enregistrement E-017 (`docs/experiment-log.md`).

Architecture reprise du v5 (`modeles/centres_5cm_v5.json`, code de `notebooks/entrainer_centres_v5_kaggle.ipynb`,
lu sans modification) : resnet18 ImageNet + décodeur FPN (latérales 1×1, 64 canaux, lissage 2 × conv 3×3),
sortie au quart, une carte de logits ; perte focale de CenterNet ; AdamW, OneCycle 5 % de montée, écrêtage 5.
Seule différence voulue avec le v5 : l'origine des étiquettes (professeur figé E-010) et la géométrie des cibles,
exprimée en mètres (σ = 0,3 m, zone ignorée 0,5 m) grâce à la résolution réelle de chaque image.

Pseudo-étiquettes (CSV `image_path,x,y,z`, x et y en pixels de l'image préparée) :
  - positif : z ≥ 2,238 ;
  - ignoré  : disque de 0,5 m autour des points 1,5 ≤ z < 2,238 ;
  - fond    : tout le reste ; les points z < 1,5 sont écartés.
Le disque `masque_cx/cy/r` de `tuiles.csv` (zone couverte par la photo d'origine), s'il existe, borne la perte comme
dans le v5 : hors du disque, poids nul. Le disque compté de la réserve (`disque_cx/cy/r`, D-010 : le professeur n'a
gardé que les pics de ce disque) s'y ajoute : hors de ce disque aussi, poids nul.

Détections (format de `scripts/math_evaluer.py`) : CSV `image_path,x,y,score`, maxima locaux de la sigmoïde
au-dessus d'un plancher, puis NMS gloutonne de 1,0 m.

Seuil non supervisé : le score s tel que le nombre de détections de l'élève (score ≥ s) sur la réserve égale le
nombre de points z ≥ 2,238 du professeur sur la même réserve.
"""
from __future__ import annotations

import math
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
DOSSIER_IMAGES = RACINE / "data/drone/comptage_v5_5cm/images"
TUILES_CSV = RACINE / "data/drone/comptage_v5_5cm/tuiles.csv"
RESOLUTIONS_CSV = [RACINE / "data/comptage_math/references/dev_dense_images.csv",
                   RACINE / "out/comptage_math/evaluation/images_dense.csv"]
POIDS_IMAGENET = Path("C:/Users/coren/.cache/torch/hub/checkpoints/resnet18-f37072fd.pth")

Z_POSITIF = 2.238          # seuil figé du professeur (E-010)
Z_IGNORE = 1.5             # bas de la zone ignorée
SIGMA_M = 0.30             # écart-type de la gaussienne cible
RAYON_IGNORE_M = 0.50      # disque ignoré autour des pics incertains
NMS_M = 1.0                # NMS des détections
CM_DEFAUT = 5.0            # résolution nominale des images préparées, si l'image n'est dans aucune liste
STRIDE = 4
GRAINE = 2026
MOY = np.array([0.485, 0.456, 0.406], "float32")
ECT = np.array([0.229, 0.224, 0.225], "float32")


# --------------------------------------------------------------------------------------------- métadonnées
def table_resolutions() -> dict[str, float]:
    """cm_par_px par image : dev_dense_images.csv d'abord, puis images_dense.csv de l'évaluation."""
    res: dict[str, float] = {}
    for p in reversed(RESOLUTIONS_CSV):
        if p.exists():
            d = pd.read_csv(p, usecols=["image_path", "cm_par_px"])
            res.update(dict(zip(d.image_path, d.cm_par_px.astype(float))))
    return res


def table_masques() -> dict[str, tuple[float, float, float]]:
    """Disque couvert par la photo d'origine (tuiles.csv, colonnes masque_*), en pixels."""
    if not TUILES_CSV.exists():
        return {}
    d = pd.read_csv(TUILES_CSV, usecols=["image_path", "masque_cx", "masque_cy", "masque_r"]).dropna()
    return {r.image_path: (float(r.masque_cx), float(r.masque_cy), float(r.masque_r)) for r in d.itertuples()}


def lire_liste(chemin) -> list[str]:
    """Liste d'images : CSV avec une colonne image_path (ou première colonne)."""
    d = pd.read_csv(chemin)
    col = "image_path" if "image_path" in d.columns else d.columns[0]
    return list(dict.fromkeys(d[col].astype(str)))


def lire_disques(chemin) -> tuple[dict, dict]:
    """Disque compté {image: (cx, cy, r)} et résolution {image: cm_par_px} d'une liste (reserve.csv, seuil_bloc.csv).

    Colonnes absentes : dictionnaires vides."""
    d = pd.read_csv(chemin)
    disques, res = {}, {}
    if {"disque_cx", "disque_cy", "disque_r"} <= set(d.columns):
        for r in d.dropna(subset=["disque_cx", "disque_cy", "disque_r"]).itertuples():
            disques[str(r.image_path)] = (float(r.disque_cx), float(r.disque_cy), float(r.disque_r))
    if "cm_par_px" in d.columns:
        res = dict(zip(d.image_path.astype(str), d.cm_par_px.astype(float)))
    return disques, res


def dans_disques(det: pd.DataFrame, disques: dict) -> pd.DataFrame:
    """Garde les lignes (image_path, x, y) situées dans le disque de leur image ; image sans disque : gardée."""
    if det.empty or not disques:
        return det
    c = np.array([disques.get(n, (np.nan, np.nan, np.nan)) for n in det.image_path], float)
    dedans = ((det.x.to_numpy() - c[:, 0]) ** 2 + (det.y.to_numpy() - c[:, 1]) ** 2 <= c[:, 2] ** 2) | np.isnan(c[:, 2])
    return det[dedans]


def lire_pseudo(chemin) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """{image: (positifs (n,2), ignorés (m,2))} en pixels."""
    d = pd.read_csv(chemin)
    out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for nom, g in d.groupby("image_path"):
        z = g.z.to_numpy(float)
        xy = g[["x", "y"]].to_numpy("float32")
        out[str(nom)] = (xy[z >= Z_POSITIF], xy[(z >= Z_IGNORE) & (z < Z_POSITIF)])
    return out


def chemin_image(nom: str) -> Path:
    return DOSSIER_IMAGES / nom


def lire_image(nom: str) -> np.ndarray:
    return np.asarray(Image.open(chemin_image(nom)).convert("RGB"))


# --------------------------------------------------------------------------------------------- cibles
def carte_cible(pts: np.ndarray, h: int, w: int, sigma_px: float) -> np.ndarray:
    """Gaussiennes centrées sur la cellule de chaque positif, valeur exactement 1 au centre (CenterNet)."""
    H, W = (h + STRIDE - 1) // STRIDE, (w + STRIDE - 1) // STRIDE
    hm = np.zeros((H, W), "float32")
    s = max(0.8, sigma_px / STRIDE)
    r = int(3 * s) + 1
    for cx, cy in pts:
        i, j = int(cx // STRIDE), int(cy // STRIDE)
        if not (0 <= i < W and 0 <= j < H):
            continue
        x0, x1, y0, y1 = max(0, i - r), min(W, i + r + 1), max(0, j - r), min(H, j + r + 1)
        xx, yy = np.arange(x0, x1)[None, :], np.arange(y0, y1)[:, None]
        hm[y0:y1, x0:x1] = np.maximum(hm[y0:y1, x0:x1], np.exp(-((xx - i) ** 2 + (yy - j) ** 2) / (2 * s * s)))
    return hm


def carte_poids(ign: np.ndarray, rayon_px: float, masques, h: int, w: int) -> np.ndarray:
    """1 partout, 0 dans les disques ignorés et hors de chacun des disques `masques` [(cx, cy, r), …]."""
    H, W = (h + STRIDE - 1) // STRIDE, (w + STRIDE - 1) // STRIDE
    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy = (xx + 0.5) * STRIDE, (yy + 0.5) * STRIDE
    p = np.ones((H, W), "float32")
    for mx, my, mr in masques:
        p[(cx - mx) ** 2 + (cy - my) ** 2 > mr ** 2] = 0
    for x, y in ign:
        p[(cx - x) ** 2 + (cy - y) ** 2 <= rayon_px ** 2] = 0
    return p


def _tourner(a: np.ndarray, pts: list[np.ndarray], k: int):
    """k quarts de tour (sens de np.rot90) de l'image et des points (x, y) continus."""
    for _ in range(k):
        n = a.shape[1]
        a = np.rot90(a)
        pts = [np.c_[p[:, 1], n - p[:, 0]].astype("float32") if len(p) else p for p in pts]
    return np.ascontiguousarray(a), pts


class JeuPseudo(torch.utils.data.Dataset):
    """Découpes aléatoires des images de la réserve, avec cibles et poids issus des pseudo-étiquettes.

    Les images sans pseudo-étiquette sont gardées : ce sont des fonds (aucun pic du professeur).
    """

    def __init__(self, images: list[str], pseudo: dict, decoupe: int = 512, augmenter: bool = True,
                 en_memoire: bool = True, disques: dict | None = None, resolutions: dict | None = None):
        """disques : {image: (cx, cy, r)} disque compté (poids nul hors du disque, D-010), en plus du masque de
        tuiles.csv ; resolutions : {image: cm_par_px}, prioritaire sur les listes de référence."""
        self.images = images
        self.pseudo = pseudo
        self.decoupe = decoupe
        self.augmenter = augmenter
        res, masques = table_resolutions(), table_masques()
        res.update(resolutions or {})
        disques = disques or {}
        self.cm = [res.get(n, CM_DEFAUT) for n in images]
        self.masques = [[d for d in (masques.get(n), disques.get(n)) if d is not None] for n in images]
        self.n_sans_resolution = sum(n not in res for n in images)
        self.cache = [lire_image(n) for n in images] if en_memoire else None
        vide = np.zeros((0, 2), "float32")
        self.etiq = [pseudo.get(n, (vide, vide)) for n in images]

    def __len__(self):
        return len(self.images)

    def __getitem__(self, i):
        a = self.cache[i] if self.cache is not None else lire_image(self.images[i])
        pos, ign = self.etiq[i][0].copy(), self.etiq[i][1].copy()
        m = self.masques[i]
        cen = np.array([[d[0], d[1]] for d in m], "float32").reshape(-1, 2)
        C = self.decoupe
        h, w = a.shape[:2]
        x0 = random.randint(0, max(0, w - C)) if self.augmenter else 0
        y0 = random.randint(0, max(0, h - C)) if self.augmenter else 0
        cadre = np.zeros((C, C, 3), "float32")
        morceau = a[y0:y0 + C, x0:x0 + C].astype("float32")
        if self.augmenter:                                   # luminosité puis contraste (autour de la moyenne)
            morceau = morceau * random.uniform(0.8, 1.2)
            moy = morceau.mean()
            morceau = np.clip((morceau - moy) * random.uniform(0.8, 1.2) + moy, 0, 255)
        cadre[:morceau.shape[0], :morceau.shape[1]] = morceau
        for p in (pos, ign, cen):
            if len(p):
                p[:, 0] -= x0
                p[:, 1] -= y0
        if self.augmenter:
            if random.random() < 0.5:
                cadre = np.ascontiguousarray(cadre[:, ::-1])
                for p in (pos, ign, cen):
                    if len(p):
                        p[:, 0] = C - p[:, 0]
            cadre, (pos, ign, cen) = _tourner(cadre, [pos, ign, cen], random.randint(0, 3))
        masques = [(float(c[0]), float(c[1]), d[2]) for c, d in zip(cen, m)]
        cm = self.cm[i]
        x = ((cadre / 255 - MOY) / ECT).transpose(2, 0, 1).astype("float32")
        y = carte_cible(pos, C, C, SIGMA_M * 100 / cm)
        p = carte_poids(ign, RAYON_IGNORE_M * 100 / cm, masques, C, C)
        # les images préparées font 512 px : avec decoupe ≤ 512, aucune découpe ne déborde de l'image
        return torch.from_numpy(x), torch.from_numpy(y[None]), torch.from_numpy(p[None])


# --------------------------------------------------------------------------------------------- réseau
class DetecteurCentres(nn.Module):
    """resnet18 + FPN, sortie au quart (copie de l'architecture du v5)."""

    def __init__(self, c: int = 64, imagenet: bool = True):
        super().__init__()
        from torchvision.models import resnet18
        r = resnet18(weights=None)
        if imagenet:
            r.load_state_dict(torch.load(POIDS_IMAGENET, map_location="cpu", weights_only=True))
        self.souche = nn.Sequential(r.conv1, r.bn1, r.relu, r.maxpool)
        self.etages = nn.ModuleList([r.layer1, r.layer2, r.layer3, r.layer4])
        self.lat = nn.ModuleList([nn.Conv2d(k, c, 1) for k in (64, 128, 256, 512)])
        self.lisse = nn.Sequential(nn.Conv2d(c, c, 3, padding=1), nn.BatchNorm2d(c), nn.ReLU(inplace=True),
                                   nn.Conv2d(c, c, 3, padding=1), nn.BatchNorm2d(c), nn.ReLU(inplace=True))
        self.tete = nn.Conv2d(c, 1, 1)
        nn.init.constant_(self.tete.bias, -2.19)

    def forward(self, x):
        x = self.souche(x)
        feats = []
        for et in self.etages:
            x = et(x)
            feats.append(x)
        p = self.lat[3](feats[3])
        for k in (2, 1, 0):
            p = F.interpolate(p, size=feats[k].shape[-2:], mode="nearest") + self.lat[k](feats[k])
        return self.tete(self.lisse(p))


def perte_focale(logits, cible, poids):
    """Perte focale de CenterNet (α = 2, β = 4), normalisée par le nombre de positifs pondérés (comme le v5)."""
    p = torch.sigmoid(logits.float()).clamp(1e-4, 1 - 1e-4)
    est_pos = cible.eq(1).float()
    pos = est_pos * poids
    l_pos = torch.log(p) * (1 - p) ** 2 * pos
    l_neg = torch.log(1 - p) * p ** 2 * (1 - cible) ** 4 * (1 - est_pos) * poids
    return -(l_pos.sum() + l_neg.sum()) / pos.sum().clamp(min=1)


def fixer_graine(g: int = GRAINE):
    random.seed(g)
    np.random.seed(g)
    torch.manual_seed(g)


# --------------------------------------------------------------------------------------------- entraînement
def entrainer(images: list[str], pseudo: dict, epoques: int, sortie: Path, decoupe: int = 512, lot: int = 8,
              threads: int = 8, lr_squelette: float = 3e-4, lr_decodeur: float = 1e-3, wd: float = 1e-4,
              ecretage: float = 5.0, max_lots: int | None = None, journal=print, disques: dict | None = None,
              resolutions: dict | None = None) -> dict:
    """Entraîne l'élève ; la dernière époque est retenue (E-017), sans arrêt précoce.

    Écrit `sortie/dernier.pt` à chaque époque et `sortie/historique.csv`. Retourne un résumé des temps.
    """
    torch.set_num_threads(threads)
    fixer_graine()
    sortie = Path(sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    t_charge = time.perf_counter()
    jeu = JeuPseudo(images, pseudo, decoupe=decoupe, augmenter=True, disques=disques, resolutions=resolutions)
    t_charge = time.perf_counter() - t_charge
    if jeu.n_sans_resolution:
        journal(f"attention : {jeu.n_sans_resolution} images sans cm_par_px, résolution {CM_DEFAUT} cm/px supposée")
    g = torch.Generator()
    g.manual_seed(GRAINE)
    charge = torch.utils.data.DataLoader(jeu, batch_size=lot, shuffle=True, drop_last=len(jeu) >= 2 * lot,
                                         num_workers=0, generator=g)
    n_lots = len(charge) if max_lots is None else min(len(charge), max_lots)
    modele = DetecteurCentres()
    squelette = list(modele.souche.parameters()) + list(modele.etages.parameters())
    ids = {id(p) for p in squelette}
    decodeur = [p for p in modele.parameters() if id(p) not in ids]
    opt = torch.optim.AdamW([{"params": squelette, "lr": lr_squelette}, {"params": decodeur, "lr": lr_decodeur}],
                            weight_decay=wd)
    prog = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=[lr_squelette, lr_decodeur],
                                               total_steps=epoques * n_lots, pct_start=0.05)
    histo = []
    debut = time.perf_counter()
    for ep in range(1, epoques + 1):
        modele.train()
        t0, somme, n, t_donnees = time.perf_counter(), 0.0, 0, 0.0
        tl = time.perf_counter()
        for k, (x, y, w) in enumerate(charge):
            t_donnees += time.perf_counter() - tl
            if k >= n_lots:
                break
            perte = perte_focale(modele(x), y, w)
            if not torch.isfinite(perte):
                raise RuntimeError(f"perte non finie à l'époque {ep}")
            opt.zero_grad(set_to_none=True)
            perte.backward()
            torch.nn.utils.clip_grad_norm_(modele.parameters(), ecretage)
            opt.step()
            prog.step()
            somme += float(perte.detach())
            n += 1
            tl = time.perf_counter()
        duree = time.perf_counter() - t0
        histo.append(dict(epoque=ep, perte=somme / max(n, 1), duree_s=round(duree, 2),
                          donnees_s=round(t_donnees, 2), images=n * lot))
        torch.save(modele.state_dict(), sortie / "dernier.pt")
        pd.DataFrame(histo).to_csv(sortie / "historique.csv", index=False)
        journal(f"époque {ep}/{epoques} : perte {somme / max(n, 1):.4f}, {duree:.1f} s "
                f"(données {t_donnees:.1f} s), {duree / max(n * lot, 1):.3f} s par image")
    return dict(chargement_s=t_charge, total_s=time.perf_counter() - debut, historique=histo, n_lots=n_lots)


# --------------------------------------------------------------------------------------------- inférence
def charger(chemin_pt) -> DetecteurCentres:
    m = DetecteurCentres(imagenet=False)
    m.load_state_dict(torch.load(chemin_pt, map_location="cpu", weights_only=True))
    return m.eval()


def _entree(a: np.ndarray):
    h, w = a.shape[:2]
    H, W = (h + 31) // 32 * 32, (w + 31) // 32 * 32
    x = np.zeros((H, W, 3), "float32")
    x[:h, :w] = a.astype("float32") / 255
    x[h:, :, :] = 0
    x[:, w:, :] = 0
    return ((x - MOY) / ECT).transpose(2, 0, 1), h, w


def nms_metrique(xy: np.ndarray, sc: np.ndarray, rayon_px: float) -> np.ndarray:
    """NMS gloutonne : garde le plus fort, supprime les voisins à moins de rayon_px. Retourne les indices gardés."""
    ordre = np.argsort(-sc, kind="stable")
    garde, suppr = [], np.zeros(len(sc), bool)
    r2 = rayon_px * rayon_px
    for i in ordre:
        if suppr[i]:
            continue
        garde.append(i)
        d2 = ((xy - xy[i]) ** 2).sum(1)
        suppr |= d2 < r2
    return np.array(garde, int)


@torch.no_grad()
def predire(modele: DetecteurCentres, images: list[str], plancher: float = 0.05, lot: int = 8,
            threads: int = 8) -> pd.DataFrame:
    """Détections `image_path,x,y,score` : maxima locaux 3×3 de la sigmoïde ≥ plancher, puis NMS de 1,0 m."""
    torch.set_num_threads(threads)
    modele.eval()
    res = table_resolutions()
    lignes = []
    for k in range(0, len(images), lot):
        noms = images[k:k + lot]
        entrees = [_entree(lire_image(n)) for n in noms]
        formes = {e[0].shape for e in entrees}
        if len(formes) == 1:
            sorties = torch.sigmoid(modele(torch.from_numpy(np.stack([e[0] for e in entrees]))))
            cartes = [sorties[i, 0] for i in range(len(noms))]
        else:
            cartes = [torch.sigmoid(modele(torch.from_numpy(e[0][None])))[0, 0] for e in entrees]
        for nom, (_, h, w), c in zip(noms, entrees, cartes):
            c = c[:(h + STRIDE - 1) // STRIDE, :(w + STRIDE - 1) // STRIDE]
            mx = F.max_pool2d(c[None, None], 3, 1, 1)[0, 0]
            ys, xs = torch.nonzero((c == mx) & (c >= plancher), as_tuple=True)
            if len(ys) == 0:
                continue
            xy = np.c_[(xs.numpy() + 0.5) * STRIDE, (ys.numpy() + 0.5) * STRIDE]
            sc = c[ys, xs].numpy().astype(float)
            cm = res.get(nom, CM_DEFAUT)
            g = nms_metrique(xy, sc, NMS_M * 100 / cm)
            for i in g:
                lignes.append((nom, round(float(xy[i, 0]), 2), round(float(xy[i, 1]), 2), round(float(sc[i]), 5)))
    return pd.DataFrame(lignes, columns=["image_path", "x", "y", "score"])


# --------------------------------------------------------------------------------------------- seuil
def seuil_non_supervise(detections: pd.DataFrame, pseudo_csv, images: list[str]) -> dict:
    """Seuil s de l'élève tel que #{détections ≥ s} sur la réserve = #{points z ≥ 2,238 du professeur} sur la réserve.

    En cas d'ex æquo, s est le score de la N-ième détection (ordre décroissant) : le compte peut alors dépasser N.
    """
    ens = set(images)
    p = pd.read_csv(pseudo_csv)
    n_prof = int(((p.z >= Z_POSITIF) & p.image_path.isin(ens)).sum())
    sc = np.sort(detections.loc[detections.image_path.isin(ens), "score"].to_numpy(float))[::-1]
    if n_prof == 0:
        s = float("inf")
    elif n_prof > len(sc):
        s = float(sc[-1]) if len(sc) else float("nan")   # plancher atteint : l'élève ne peut pas égaler le professeur
    else:
        s = float(sc[n_prof - 1])
    n_eleve = int((sc >= s).sum()) if np.isfinite(s) else 0
    return dict(seuil=s, n_professeur=n_prof, n_eleve=n_eleve, n_images=len(ens),
                plancher_atteint=bool(n_prof > len(sc)))
