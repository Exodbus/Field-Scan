#!/usr/bin/env python3
"""Travail d'entraînement d'un détecteur de centres v6 (nuit du 12/11, agent C-entraîneur).

Une recette (JSON dans la variable d'environnement V6_RECETTE) est entraînée puis mesurée sur le RÉGLAGE seulement :
les 4 validations du v5 (dense banavista session B, plantain 100_metros, jeunes dji_0544, MM1-MM2 mères seules)
+ banana_tree_detection moitié validation (val_espace), et les images sans bananier de validation (val_negatifs).
Règles : docs/plan_nuit_2026-11-12.md, section 3.4 (seuil : moyenne des 5 F1 maximale sur la grille 0,10-0,60,
sous 1 % de fausses détections sans bananier ; pas de choix d'époque : poids EMA de la dernière époque).

JAMAIS de juge : les ensembles test_* et le dossier cg/ sont retirés au chargement (contrôle bloquant).

Variables :
  V6_DONNEES   dossier de l'archive comptage_v6_5cm décompressée (tuiles.csv, objets.csv, images/, mm/)
  V6_SORTIE    dossier de sortie de la recette
  V6_RECETTE   JSON de la recette (voir RECETTE_DEFAUT)
  V6_ESSAI     1 = essai local sur processeur (quelques tuiles, 2 époques de 3 lots)
  V6_MESURER_ONNX  chemin d'un ONNX : pas d'entraînement, mesure de ce modèle sur le réglage (référence v5)
"""
import copy
import json
import math
import os
import platform
import random
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image, ImageEnhance
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
from torch.utils.data import DataLoader, Dataset

RECETTE_DEFAUT = dict(
    nom="v6a", graine=0, epoques=30, lot=16, reseau="resnet18",
    lr_squelette=3e-4, lr_decodeur=1e-3, decroissance_poids=1e-4, ecretage=5.0,
    ech_min=0.5, ech_max=2.0,              # augmentation d'échelle (v5 : 0,8-1,25)
    ema=0.999,                             # moyenne glissante des poids (None : sans)
    stride=4, decalage=False,              # v6b : stride 2 + tête de décalage
    k_pics=7,                              # fenêtre des maxima locaux (en pixels de sortie)
    sigma_min=0.8,                         # écart-type minimal de la gaussienne cible (pixels de sortie)
    tirage="parts_v6a",                    # ou « equilibre » (v6c)
    poids_pos=1.0,                         # v6c : poids du terme positif de la perte focale
    facteur_entree=1.0,                    # 5/3.5 : entrée à 3,5 cm
    init=None,                             # chemin d'un .pt de départ (réglage fin)
    seulement_espace=False,                # réglage fin sur la plantation espacée seule
    tete_densite=False,                    # deux têtes : centres + densité
    distillation=None,                     # liste d'ONNX maîtres (v3, v4, v5) : l'élève apprend aussi la moyenne de leurs cartes
    lambda_distil=10.0,                    # poids de la perte de distillation (entropie croisée, moyenne par pixel)
    bn_gele=False,                         # couches de normalisation figées (obligatoire en partant d'un ONNX : BN fusionnées)
    jeux_neufs=None,                       # dossiers « prepare » de jeux neufs ajoutés à l'ENTRAÎNEMENT (dmpcs2, geostar)
    jeu_finca=None,                        # dossier « prepare » de banano_finca : mesuré POUR INFORMATION, hors règle
    melange_poids=None,                    # [[chemin .pt ou .onnx, poids], ...] : moyenne pondérée des poids (soupe, interpolation)
    mesures_intermediaires=(10, 20),       # époques où l'EMA est mesuré pour information (aucun choix)
    duree_max_h=5.0, num_workers=2,
)

ESSAI = os.environ.get("V6_ESSAI") == "1"
D = os.environ["V6_DONNEES"]
SORTIE = os.environ.get("V6_SORTIE", "sortie_v6")
os.makedirs(SORTIE, exist_ok=True)
R = dict(RECETTE_DEFAUT)
R.update(json.loads(os.environ.get("V6_RECETTE", "{}")))
ONNX_A_MESURER = os.environ.get("V6_MESURER_ONNX")
DEV = "cuda" if torch.cuda.is_available() else "cpu"
JOURNAL = open(os.path.join(SORTIE, "journal.txt"), "a", encoding="utf-8")


def dire(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    JOURNAL.write(time.strftime("%H:%M:%S ") + s + "\n"); JOURNAL.flush()


VERSIONS = {"torch": torch.__version__, "python": platform.python_version(),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "aucun"}
dire("recette", json.dumps(R, ensure_ascii=False), "|", VERSIONS)

# ---------------------------------------------------------------- données (réglage seulement, jamais de juge)
TUILES = pd.read_csv(f"{D}/tuiles.csv")
OBJETS = pd.read_csv(f"{D}/objets.csv")
JUGES = TUILES.ensemble.str.startswith("test")
dire(f"{int(JUGES.sum())} tuiles de juges retirées au chargement (jamais lues)")
TUILES = TUILES[~JUGES].reset_index(drop=True)
OBJETS = OBJETS[OBJETS.image_path.isin(set(TUILES.image_path))]
ENS_PERMIS = {"train", "val_dense_bv", "val_plantain", "val_jeunes", "val_espace", "val_negatifs", "val_finca"}
assert set(TUILES.ensemble) <= ENS_PERMIS, f"ensemble inattendu : {set(TUILES.ensemble) - ENS_PERMIS}"
assert "val_espace" in set(TUILES.ensemble), "archive sans val_espace (btd_val) : ce n'est pas l'archive v6"
RACINE_IMAGE = {}
for dossier, ens_ok in [(x, {"train"}) for x in (R["jeux_neufs"] or [])] + ([(R["jeu_finca"], {"val_finca"})] if R["jeu_finca"] else []):
    t_, o_ = pd.read_csv(f"{dossier}/tuiles.csv"), pd.read_csv(f"{dossier}/objets.csv")
    assert set(t_.ensemble) <= ens_ok and not t_.ensemble.str.startswith("test").any(), f"ensemble interdit dans {dossier}"
    t_ = t_[[c for c in TUILES.columns if c in t_.columns]]
    RACINE_IMAGE.update({n: f"{dossier}/images" for n in t_.image_path})
    TUILES = pd.concat([TUILES, t_], ignore_index=True); OBJETS = pd.concat([OBJETS, o_[o_.image_path.isin(set(t_.image_path))]], ignore_index=True)
    dire(f"ajouté : {dossier} ({len(t_)} tuiles, ensembles {sorted(set(t_.ensemble))})")
if ESSAI:
    TUILES = TUILES.groupby(["ensemble", "groupe"]).head(3).reset_index(drop=True)
RAYON_IGNORE = 20.0


def chemin_image(nom):
    if nom in RACINE_IMAGE:
        return f"{RACINE_IMAGE[nom]}/{nom}"
    for sous in ("images", "mm/images"):           # cg/ n'est jamais lu (juge)
        p = f"{D}/{sous}/{nom}"
        if os.path.exists(p):
            return p
    raise FileNotFoundError(nom)


OBJ_PAR_IMAGE = {k: g for k, g in OBJETS.groupby("image_path")}
VIDE = OBJETS.iloc[:0]


def echantillon(r):
    o = OBJ_PAR_IMAGE.get(r.image_path, VIDE)
    meres = o[o.type == "mere"][["cx", "cy", "taille"]].to_numpy("float32").reshape(-1, 3)
    ign = o[o.type != "mere"][["cx", "cy"]].to_numpy("float32").reshape(-1, 2)
    ign = np.c_[ign, np.full(len(ign), RAYON_IGNORE, "float32")] if len(ign) else np.zeros((0, 3), "float32")
    masque = None if np.isnan(r.masque_r) else np.array([[r.masque_cx, r.masque_cy, r.masque_r]], "float32")
    return dict(nom=r.image_path, groupe=r.groupe, pts=meres, ign=ign, masque=masque, n_autres=int(r.n_autres_arbres))


ECH = {e: [echantillon(r) for r in g.itertuples()] for e, g in TUILES.groupby("ensemble")}
NEGATIF = lambda e: e["groupe"].startswith(("palmier", "cocotier"))
TRAIN = ECH["train"]
T_ESPACE = [e for e in TRAIN if e["groupe"].startswith("btd_")]
T_PLANT = [e for e in TRAIN if e["groupe"].startswith(("pp_", "lasuiza", "bv_"))]
T_RT = [e for e in TRAIN if e["groupe"].startswith("rt_")]
T_JEUNES = [e for e in TRAIN if e["groupe"].startswith("jeunes_dji")]
T_NEG = [e for e in TRAIN if NEGATIF(e)]
T_NEUFS = [e for e in TRAIN if e["groupe"].startswith(("dmpcs2", "geostar"))]
T_AUTRES = [e for e in TRAIN if not (e["groupe"].startswith(("pp_", "lasuiza", "bv_", "rt_", "jeunes_dji", "btd_", "dmpcs2", "geostar")) or NEGATIF(e))]
assert not any(g.startswith("btd") for g in TUILES[TUILES.ensemble == "train"].groupe) or T_ESPACE
N_EPOQUE = int(round(len(T_AUTRES) / 0.25))


def rep(liste, part):
    return max(1, int(round(part * N_EPOQUE / max(len(liste), 1))))


if R["seulement_espace"]:
    # Réglage fin sur la seule plantation espacée (essai 19) ; quelques négatifs pour garder la contrainte
    PLAN = [("espacée", T_ESPACE, 1)]
    N_NEG = min(len(T_NEG), len(T_ESPACE) // 5)
elif R["tirage"] == "equilibre":
    # v6c : sept types à parts égales, même nombre d'échantillons par époque que v6a
    TYPES = {"dense banavista": [e for e in T_PLANT if e["groupe"].startswith("bv_")],
             "plantain": [e for e in T_PLANT if not e["groupe"].startswith("bv_")],
             "autres": T_AUTRES, "espacée": T_ESPACE, "jeunes": T_JEUNES, "agroforesterie": T_RT}
    PLAN = [(k, v, None) for k, v in TYPES.items() if v]
    N_NEG = min(len(T_NEG), int(round(N_EPOQUE / 7)))
else:
    # v6a : parts v5 réparties pour faire place à la plantation espacée (écrites avant le premier lancement)
    PLAN = [("autres", T_AUTRES, 1), ("plantations", T_PLANT, rep(T_PLANT, 0.20)), ("espacée", T_ESPACE, rep(T_ESPACE, 0.15)),
            ("ReforesTree", T_RT, rep(T_RT, 0.15)), ("jeunes", T_JEUNES, rep(T_JEUNES, 0.10))] + ([("jeux neufs", T_NEUFS, 1)] if T_NEUFS else [])
    N_NEG = min(len(T_NEG), int(round(0.15 * N_EPOQUE)))


PETITS = []
if R["tirage"] == "taille":
    # v6d (recommandation de C-analyste, 23 h 45) : tirage v6a + une copie de plus de chaque tuile d'entraînement dont au moins
    # 30 % des plants (et au moins 2) ont une boîte < 40 px à 5 cm ; but : au moins 25 % des plants tirés sous 40 px
    for _, liste, k in PLAN:
        for e in liste:
            t_ = e["pts"][:, 2] if len(e["pts"]) else np.zeros(0)
            n_p = int((t_ < 40).sum())
            if n_p >= 2 and n_p >= 0.3 * len(t_):
                PETITS.append(e)


def echantillons_epoque(rng):
    out = list(PETITS)
    for _, liste, k in PLAN:
        if not liste:
            continue
        if k is None:                                   # tirage avec remise, part égale
            out += [rng.choice(liste) for _ in range(int(round(N_EPOQUE / 7)))]
        else:
            out += liste * k
    return out + rng.sample(T_NEG, N_NEG)


n0 = len(echantillons_epoque(random.Random(0)))
dire("tirage :", " ; ".join(f"{n} {len(l)} x {k if k is not None else 'égal'}" for n, l, k in PLAN),
     f"; sans bananier {N_NEG}/{len(T_NEG)} ; {n0} échantillons par époque")
for e, l in ECH.items():
    dire(f"  {e:14s} : {len(l):5d} images, {sum(len(x['pts']) for x in l):6d} bananiers, {sum(x['n_autres'] for x in l):5d} autres arbres")
PTS_MM, ZONES_MM = pd.read_csv(f"{D}/mm/points.csv"), pd.read_csv(f"{D}/mm/zones.csv")

# ---------------------------------------------------------------- jeu d'entraînement
CROP, STRIDE, FE = 448, int(R["stride"]), float(R["facteur_entree"])
MOY = np.array([0.485, 0.456, 0.406], "float32"); ECT = np.array([0.229, 0.224, 0.225], "float32")


def carte_cible(pts, h, w):
    H, W = (h + STRIDE - 1) // STRIDE, (w + STRIDE - 1) // STRIDE
    hm = np.zeros((H, W), "float32"); dec = np.zeros((2, H, W), "float32"); md = np.zeros((1, H, W), "float32")
    for cx, cy, t in pts:
        i, j = int(cx // STRIDE), int(cy // STRIDE)
        if not (0 <= i < W and 0 <= j < H):
            continue
        s = max(R["sigma_min"], t / STRIDE / 6)
        r = int(3 * s) + 1
        x0, x1, y0, y1 = max(0, i - r), min(W, i + r + 1), max(0, j - r), min(H, j + r + 1)
        xx, yy = np.arange(x0, x1)[None, :], np.arange(y0, y1)[:, None]
        hm[y0:y1, x0:x1] = np.maximum(hm[y0:y1, x0:x1], np.exp(-((xx - i) ** 2 + (yy - j) ** 2) / (2 * s * s)))
        dec[0, j, i], dec[1, j, i] = cx / STRIDE - (i + 0.5), cy / STRIDE - (j + 0.5); md[0, j, i] = 1
    return hm, dec, md


def carte_densite(pts, h, w):
    # densité : une gaussienne normalisée (somme 1) par plant, à la résolution de sortie
    H, W = (h + STRIDE - 1) // STRIDE, (w + STRIDE - 1) // STRIDE
    dm = np.zeros((H, W), "float32")
    yy, xx = np.mgrid[0:H, 0:W]
    for cx, cy, t in pts:
        s = max(1.0, t / STRIDE / 6); i, j = cx / STRIDE - 0.5, cy / STRIDE - 0.5
        g = np.exp(-((xx - i) ** 2 + (yy - j) ** 2) / (2 * s * s)); dm += g / max(g.sum(), 1e-6)
    return dm


def carte_poids(masque, ign, h, w):
    H, W = (h + STRIDE - 1) // STRIDE, (w + STRIDE - 1) // STRIDE
    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy = (xx + 0.5) * STRIDE, (yy + 0.5) * STRIDE
    p = np.ones((H, W), "float32")
    if masque is not None and len(masque):
        mx, my, mr = masque[0]
        p[(cx - mx) ** 2 + (cy - my) ** 2 > mr ** 2] = 0
    for x, y, r in ign:
        p[(cx - x) ** 2 + (cy - y) ** 2 <= r ** 2] = 0
    return p


def tourner(arr, pts, k):
    for _ in range(k):
        n = arr.shape[1]
        arr = np.rot90(arr)
        pts = [np.c_[p[:, 1], n - p[:, 0], p[:, 2]] if p is not None and len(p) else p for p in pts]
    return np.ascontiguousarray(arr), pts


class Tuiles(Dataset):
    def __init__(self, echantillons):
        self.e = echantillons

    def __len__(self):
        return len(self.e)

    def __getitem__(self, i):
        ech = self.e[i]
        im = Image.open(chemin_image(ech["nom"])).convert("RGB")
        pts, ign = ech["pts"].copy(), ech["ign"].copy()
        masque = None if ech["masque"] is None else ech["masque"].copy()
        # échelle tirée en log-uniforme (autant de réductions que d'agrandissements), puis entrée à FE
        e = math.exp(random.uniform(math.log(R["ech_min"]), math.log(R["ech_max"]))) * FE
        # découpe d'abord (fenêtre CROP / e dans l'image d'origine), puis mise à l'échelle de la seule fenêtre (plus rapide)
        fen = CROP / e
        W0, H0 = im.width, im.height
        x0 = random.uniform(0, max(0.0, W0 - fen)); y0 = random.uniform(0, max(0.0, H0 - fen))
        bw, bh = min(fen, W0 - x0), min(fen, H0 - y0)
        ow, oh = max(1, min(CROP, round(bw * e))), max(1, min(CROP, round(bh * e)))
        im = im.resize((ow, oh), Image.BILINEAR, box=(x0, y0, x0 + bw, y0 + bh))
        for f in (ImageEnhance.Brightness, ImageEnhance.Contrast, ImageEnhance.Color):
            im = f(im).enhance(random.uniform(0.8, 1.2))
        cadre = np.zeros((CROP, CROP, 3), "uint8")
        cadre[:oh, :ow] = np.asarray(im)
        # hors de l'image (complément noir) : zone ignorée, comme le reste hors masque
        hors = np.zeros((CROP, CROP), bool); hors[oh:, :] = True; hors[:, ow:] = True
        for p in [pts, ign] + ([masque] if masque is not None else []):
            p[:, 0] -= x0; p[:, 1] -= y0
        pts[:, :3] *= e; ign[:, :3] *= e
        if masque is not None:
            masque *= e
        pts = pts[(pts[:, 0] >= 0) & (pts[:, 0] < CROP) & (pts[:, 1] >= 0) & (pts[:, 1] < CROP)]
        if random.random() < 0.5:
            cadre = np.ascontiguousarray(cadre[:, ::-1]); hors = np.ascontiguousarray(hors[:, ::-1])
            for p in [pts, ign] + ([masque] if masque is not None else []):
                p[:, 0] = CROP - p[:, 0]
        k = random.randint(0, 3)
        cadre, (pts, ign, masque) = tourner(cadre, [pts, ign, masque], k)
        hors = np.ascontiguousarray(np.rot90(hors, k))
        x = ((cadre.astype("float32") / 255 - MOY) / ECT).transpose(2, 0, 1)
        hm, dec, md = carte_cible(pts, CROP, CROP)
        w = carte_poids(masque, ign, CROP, CROP)
        w[hors[STRIDE // 2::STRIDE, STRIDE // 2::STRIDE][:w.shape[0], :w.shape[1]]] = 0
        sortie = [torch.from_numpy(x), torch.from_numpy(hm[None]), torch.from_numpy(w[None]),
                  torch.from_numpy(dec), torch.from_numpy(md)]
        if R["tete_densite"]:
            sortie.append(torch.from_numpy(carte_densite(pts, CROP, CROP)[None]))
        return tuple(sortie)


# ---------------------------------------------------------------- réseau et pertes
from torchvision.models import (resnet18, ResNet18_Weights, resnet34, ResNet34_Weights,  # noqa: E402
                                resnet50, ResNet50_Weights)

CANAUX = {"resnet18": (64, 128, 256, 512), "resnet34": (64, 128, 256, 512), "resnet50": (256, 512, 1024, 2048)}


class DetecteurCentres(nn.Module):
    """Même réseau que le v5 (FPN sur ResNet, sortie au quart) ; options : stride 2 (latérale sur la souche),
    tête de décalage (2 canaux), tête de densité (1 canal). Canal 0 = logits des centres."""

    def __init__(self, reseau="resnet18", c=64, stride=4, decalage=False, densite=False, preentraine=True):
        super().__init__()
        f = {"resnet18": (resnet18, ResNet18_Weights), "resnet34": (resnet34, ResNet34_Weights),
             "resnet50": (resnet50, ResNet50_Weights)}[reseau]
        r = f[0](weights=f[1].DEFAULT if preentraine else None)
        self.stride = stride
        if stride == 4:
            self.souche = nn.Sequential(r.conv1, r.bn1, r.relu, r.maxpool)
        else:
            self.souche = nn.Sequential(r.conv1, r.bn1, r.relu)
            self.pool = r.maxpool
            self.lat0 = nn.Conv2d(64, c, 1)
        self.etages = nn.ModuleList([r.layer1, r.layer2, r.layer3, r.layer4])
        self.lat = nn.ModuleList([nn.Conv2d(k, c, 1) for k in CANAUX[reseau]])
        self.lisse = nn.Sequential(nn.Conv2d(c, c, 3, padding=1), nn.BatchNorm2d(c), nn.ReLU(inplace=True),
                                   nn.Conv2d(c, c, 3, padding=1), nn.BatchNorm2d(c), nn.ReLU(inplace=True))
        self.n_sorties = 1 + (2 if decalage else 0) + (1 if densite else 0)
        self.tete = nn.Conv2d(c, 1, 1)
        nn.init.constant_(self.tete.bias, -2.19)
        self.tete_dec = nn.Conv2d(c, 2, 1) if decalage else None
        self.tete_den = nn.Conv2d(c, 1, 1) if densite else None
        if densite:
            nn.init.constant_(self.tete_den.bias, -8.0)     # densité de départ presque nulle

    def forward(self, x):
        x = self.souche(x)
        if self.stride == 2:
            s2 = x; x = self.pool(x)
        feats = []
        for et in self.etages:
            x = et(x); feats.append(x)
        p = self.lat[3](feats[3])
        for k in (2, 1, 0):
            p = F.interpolate(p, size=feats[k].shape[-2:], mode="nearest") + self.lat[k](feats[k])
        if self.stride == 2:
            p = F.interpolate(p, size=s2.shape[-2:], mode="nearest") + self.lat0(s2)
        h = self.lisse(p)
        sorties = [self.tete(h)]
        if self.tete_dec is not None:
            sorties.append(self.tete_dec(h))
        if self.tete_den is not None:
            sorties.append(self.tete_den(h))
        return torch.cat(sorties, 1) if len(sorties) > 1 else sorties[0]


def perte_focale(logits, cible, poids, poids_pos=1.0):
    # perte focale pénalisée (CenterNet), comme le v5 ; poids_pos > 1 rend les oublis plus coûteux
    p = torch.sigmoid(logits.float()).clamp(1e-4, 1 - 1e-4)
    pos = cible.eq(1).float() * poids
    l_pos = torch.log(p) * (1 - p) ** 2 * pos * poids_pos
    l_neg = torch.log(1 - p) * p ** 2 * (1 - cible) ** 4 * (1 - cible.eq(1).float()) * poids
    return -(l_pos.sum() + l_neg.sum()) / pos.sum().clamp(min=1)


# ---------------------------------------------------------------- mesure (identique au carnet v5, + val_espace et compte)
K_PICS = int(R["k_pics"])
SEUILS = [round(0.10 + 0.05 * k, 2) for k in range(11)]
RAYON_PX = 20


def entree(img):
    if FE != 1.0:
        im = Image.fromarray(img)
        img = np.asarray(im.resize((max(1, round(im.width * FE)), max(1, round(im.height * FE))), Image.BILINEAR))
    h, w = img.shape[:2]
    H, W = (h + 31) // 32 * 32, (w + 31) // 32 * 32
    x = np.zeros((H, W, 3), "float32"); x[:h, :w] = img.astype("float32") / 255
    x[h:, :, :] = 0; x[:, w:, :] = 0
    return ((x - MOY) / ECT).transpose(2, 0, 1)[None].astype("float32"), h, w


def decoder(sortie, h, w, stride):
    """sortie : tenseur (C, H, W) de logits ; renvoie carte (sigmoïde) et décalages éventuels, coupés à l'image."""
    hh, ww = (h + stride - 1) // stride, (w + stride - 1) // stride
    carte = torch.sigmoid(sortie[0].float())[:hh, :ww]
    dec = sortie[1:3].float()[:, :hh, :ww] if sortie.shape[0] >= 3 and R["decalage"] else None
    return carte, dec


class PredicteurTorch:
    def __init__(self, modele):
        self.m = modele

    @torch.no_grad()
    def carte(self, img):
        x, h, w = entree(img)
        with torch.autocast(DEV, dtype=torch.float16, enabled=DEV == "cuda"):
            lg = self.m(torch.from_numpy(x).to(DEV))
        return decoder(lg[0], h, w, STRIDE)


class PredicteurOnnx:
    def __init__(self, chemin, stride=4):
        import onnxruntime as ort
        self.s = ort.InferenceSession(chemin, providers=["CPUExecutionProvider"])
        self.n = self.s.get_inputs()[0].name
        self.stride = stride

    def carte(self, img):
        x, h, w = entree(img)
        lg = torch.from_numpy(self.s.run(None, {self.n: x})[0])
        return decoder(lg[0], h, w, self.stride)


def pics(cd, seuil):
    carte, dec = cd
    m = F.max_pool2d(carte[None, None], K_PICS, 1, K_PICS // 2)[0, 0]
    ys, xs = torch.nonzero((carte == m) & (carte >= seuil), as_tuple=True)
    px, py = xs.float() + 0.5, ys.float() + 0.5
    if dec is not None:
        px, py = px + dec[0, ys, xs].clamp(-1, 1), py + dec[1, ys, xs].clamp(-1, 1)
    xy = np.c_[px.cpu().numpy() * STRIDE, py.cpu().numpy() * STRIDE] / FE   # coordonnées de l'image à 5 cm
    return xy, carte[ys, xs].float().cpu().numpy()


def compter(det, certains, ignores, rayon):
    n, pris = 0, set()
    if len(det) and len(certains):
        d = cdist(det, certains)
        li, co = linear_sum_assignment(np.where(d <= rayon, d, 1e6))
        ok = d[li, co] <= rayon
        n, pris = int(ok.sum()), set(li[ok].tolist())
    reste = [i for i in range(len(det)) if i not in pris]
    ign = int((cdist(det[reste], ignores).min(1) <= rayon).sum()) if len(ignores) and reste else 0
    return n, len(det) - n - ign, len(certains) - n


def f1(vp, fp, fn):
    p = vp / (vp + fp) if vp + fp else 0.0; r = vp / (vp + fn) if vp + fn else 0.0
    return round(2 * p * r / (p + r), 4) if p + r else 0.0


def dans_masque(xy, masque):
    if masque is None or not len(xy):
        return np.ones(len(xy), bool)
    mx, my, mr = masque[0]
    return (xy[:, 0] - mx) ** 2 + (xy[:, 1] - my) ** 2 <= mr ** 2


def lire(nom):
    return np.asarray(Image.open(chemin_image(nom)).convert("RGB"))


def mesurer_tuiles(pred, echantillons):
    acc = {s: [0, 0, 0] for s in SEUILS}; det_tot = {s: 0 for s in SEUILS}; vrais = 0
    for e in echantillons:
        det, sc = pics(pred.carte(lire(e["nom"])), min(SEUILS))
        garde = dans_masque(det, e["masque"]); det, sc = det[garde], sc[garde]
        certains = e["pts"][dans_masque(e["pts"], e["masque"])][:, :2]; vrais += len(certains)
        for s in SEUILS:
            det_tot[s] += int((sc >= s).sum())
            for k, v in enumerate(compter(det[sc >= s], certains, e["ign"][:, :2], RAYON_PX)):
                acc[s][k] += v
    return {s: dict(vp=a[0], fp=a[1], fn=a[2], f1=f1(*a), detectes=det_tot[s], reels=vrais) for s, a in acc.items()}


def mesurer_mm(pred):
    acc = {s: [0, 0, 0] for s in SEUILS}; det_tot = {s: 0 for s in SEUILS}; vrais = 0
    for _, z in ZONES_MM.iterrows():
        det, sc = pics(pred.carte(lire(z.image_path)), min(SEUILS))
        dedans = (det[:, 0] >= z.x0) & (det[:, 0] <= z.x1) & (det[:, 1] >= z.y0) & (det[:, 1] <= z.y1)
        det, sc = det[dedans], sc[dedans]
        p = PTS_MM[PTS_MM.zone_id == z.zone_id]
        certain = p.type == "mere"
        certains, ignores = p[certain][["x", "y"]].to_numpy(), p[~certain][["x", "y"]].to_numpy()
        vrais += len(certains)
        for s in SEUILS:
            det_tot[s] += int((sc >= s).sum())
            for k, v in enumerate(compter(det[sc >= s], certains, ignores, RAYON_PX)):
                acc[s][k] += v
    return {s: dict(vp=a[0], fp=a[1], fn=a[2], f1=f1(*a), detectes=det_tot[s], reels=vrais) for s, a in acc.items()}


def mesurer_negatifs(pred, echantillons):
    fp = {s: 0 for s in SEUILS}; arbres = sum(e["n_autres"] for e in echantillons)
    for e in echantillons:
        _, sc = pics(pred.carte(lire(e["nom"])), min(SEUILS))
        for s in SEUILS:
            fp[s] += int((sc >= s).sum())
    return {s: dict(fp=fp[s], arbres=arbres, taux=round(fp[s] / max(arbres, 1), 4)) for s in SEUILS}


JEUX = ("dense", "plantain", "jeunes", "mm", "espace")


def mesurer_reglage(pred):
    return dict(dense=mesurer_tuiles(pred, ECH["val_dense_bv"]), plantain=mesurer_tuiles(pred, ECH["val_plantain"]),
                jeunes=mesurer_tuiles(pred, ECH["val_jeunes"]), mm=mesurer_mm(pred),
                espace=mesurer_tuiles(pred, ECH["val_espace"]), neg=mesurer_negatifs(pred, ECH["val_negatifs"]),
                **({"finca": mesurer_tuiles(pred, ECH["val_finca"])} if "val_finca" in ECH else {}))


def lignes_reglage(m, etiquette):
    lignes = []
    for s in SEUILS:
        l = dict(etiquette=etiquette, seuil=s)
        for j in JEUX:
            t = m[j][s]
            l[f"f1_{j}"] = t["f1"]; l[f"det_{j}"] = t["detectes"]; l[f"reels_{j}"] = t["reels"]
            l[f"vp_{j}"], l[f"fp_{j}"], l[f"fn_{j}"] = t["vp"], t["fp"], t["fn"]
            l[f"err_{j}"] = round(abs(t["detectes"] / max(t["reels"], 1) - 1), 4)
        l["moyenne"] = round(sum(l[f"f1_{j}"] for j in JEUX) / len(JEUX), 4)
        l["moyenne_4_v5"] = round(sum(l[f"f1_{j}"] for j in JEUX[:4]) / 4, 4)
        l["erreur_compte"] = round(sum(l[f"err_{j}"] for j in JEUX) / len(JEUX), 4)
        if "finca" in m:                                   # pour information seulement : hors moyenne et hors règle
            t = m["finca"][s]
            l["info_f1_finca"], l["info_err_finca"] = t["f1"], round(abs(t["detectes"] / max(t["reels"], 1) - 1), 4)
        l["fp_neg"], l["arbres_neg"], l["taux_fp_neg"] = m["neg"][s]["fp"], m["neg"][s]["arbres"], m["neg"][s]["taux"]
        l["eligible"] = m["neg"][s]["taux"] < 0.01            # règle 3.4 : moins de 1 %
        lignes.append(l)
    return lignes


def choisir(lignes):
    el = [r for r in lignes if r["eligible"]]
    return max(el, key=lambda r: r["moyenne"]) if el else min(lignes, key=lambda r: (r["taux_fp_neg"], -r["moyenne"]))


def resume(l):
    return (f"seuil {l['seuil']} : " + ", ".join(f"{j} {l['f1_' + j]:.3f}" for j in JEUX) +
            f" | moyenne {l['moyenne']:.4f} | erreur de compte {l['erreur_compte']:.3f} | sans bananier {l['fp_neg']} ({l['taux_fp_neg']:.2%})"
            + (f" | info finca {l['info_f1_finca']:.3f}" if "info_f1_finca" in l else ""))


# ---------------------------------------------------------------- référence ONNX (sans entraînement)
if ONNX_A_MESURER:
    t0 = time.time()
    lignes = lignes_reglage(mesurer_reglage(PredicteurOnnx(ONNX_A_MESURER, STRIDE)), os.path.basename(ONNX_A_MESURER))
    pd.DataFrame(lignes).to_csv(f"{SORTIE}/reglage.csv", index=False)
    ch = choisir(lignes)
    dire(f"ONNX {ONNX_A_MESURER} ({(time.time() - t0) / 60:.1f} min) : retenu {resume(ch)}")
    for l in lignes:
        dire("   ", resume(l))
    json.dump(dict(retenu=ch, lignes=lignes), open(f"{SORTIE}/reglage.json", "w"), indent=1, ensure_ascii=False, default=float)
    raise SystemExit(0)

# ---------------------------------------------------------------- entraînement
g = int(R["graine"])
random.seed(g); np.random.seed(g); torch.manual_seed(g)
rng = random.Random(g)
modele = DetecteurCentres(R["reseau"], stride=STRIDE, decalage=R["decalage"], densite=R["tete_densite"]).to(DEV)


def suite_bn(chemin):
    for a, b in (("conv1", "bn1"), ("conv2", "bn2"), ("conv3", "bn3"), ("downsample.0", "downsample.1"), ("souche.0", "souche.1"),
                 ("lisse.0", "lisse.1"), ("lisse.3", "lisse.4")):
        if chemin.endswith(a):
            return chemin[: -len(a)] + b
    return None


def etat_depuis_onnx(chemin, modele_ref):
    """Poids d'un ONNX exporté depuis DetecteurCentres (BN fusionnées dans les convolutions) : chaque BN devient
    l'identité qui porte le biais fusionné. Vérifié contre onnxruntime (écart affiché)."""
    import onnx
    from onnx import numpy_helper
    m = onnx.load(chemin)
    init = {i.name: numpy_helper.to_array(i) for i in m.graph.initializer}
    mod = copy.deepcopy(modele_ref).cpu()
    modules = dict(mod.named_modules())
    n_conv = 0
    with torch.no_grad():
        for bn in [x for x in mod.modules() if isinstance(x, nn.BatchNorm2d)]:
            bn.weight.fill_(1); bn.bias.zero_(); bn.running_mean.zero_(); bn.running_var.fill_(1 - bn.eps)
        for nd in m.graph.node:
            if nd.op_type != "Conv":
                continue
            parties, chemin_l, prec = nd.name.strip("/").split("/")[:-1], [], None
            for q in parties:
                chemin_l.append(q[len(prec) + 1:] if prec and q.startswith(prec + ".") else q); prec = q
            nom = ".".join(chemin_l)
            conv = modules[nom]
            W = torch.from_numpy(init[nd.input[1]].copy()); b = torch.from_numpy(init[nd.input[2]].copy()) if len(nd.input) > 2 else None
            conv.weight.copy_(W)
            nbn = suite_bn(nom)
            if nbn is not None and nbn in modules:
                if conv.bias is not None:
                    conv.bias.zero_()
                if b is not None:
                    modules[nbn].bias.copy_(b)
            elif b is not None:
                conv.bias.copy_(b)
            n_conv += 1
    import onnxruntime as ort
    xin = np.random.RandomState(0).randn(1, 3, 256, 256).astype("float32")
    mod.eval()
    ecart = float(np.abs(mod(torch.from_numpy(xin)).detach().numpy()[:, :1] -
                         ort.InferenceSession(chemin, providers=["CPUExecutionProvider"]).run(None, {"image" if "image" in [i.name for i in m.graph.input] else m.graph.input[0].name: xin})[0][:, :1]).max())
    dire(f"ONNX converti : {chemin} ({n_conv} convolutions) ; écart avec onnxruntime {ecart:.2e}")
    assert ecart < 1e-3, "conversion ONNX -> torch fausse"
    return mod.state_dict()


def charger_etat(chemin, modele_ref):
    return etat_depuis_onnx(chemin, modele_ref) if chemin.endswith(".onnx") else torch.load(chemin, map_location="cpu")


if R["init"]:
    etat = charger_etat(R["init"], modele)
    manque = modele.load_state_dict(etat, strict=False)
    dire("départ :", R["init"], "|", manque)
if R["melange_poids"]:
    etats = [(charger_etat(c, modele), float(w_)) for c, w_ in R["melange_poids"]]
    tot = sum(w_ for _, w_ in etats)
    moy = {}
    for k, v in etats[0][0].items():
        moy[k] = sum(e_[k].float() * w_ for e_, w_ in etats) / tot if v.dtype.is_floating_point else v
    modele.load_state_dict(moy)
    dire("moyenne des poids :", R["melange_poids"])
MAITRES = []
if R["distillation"]:
    for c in R["distillation"]:
        mt = DetecteurCentres("resnet18", preentraine=False)
        mt.load_state_dict(etat_depuis_onnx(c, mt)); MAITRES.append(mt.to(DEV).eval())


def geler_bn(m):
    if R["bn_gele"]:
        for x in m.modules():
            if isinstance(x, nn.BatchNorm2d):
                x.eval(); x.weight.requires_grad_(False); x.bias.requires_grad_(False)
squelette = list(modele.souche.parameters()) + list(modele.etages.parameters())
ids = {id(p) for p in squelette}
decodeur = [p for p in modele.parameters() if id(p) not in ids]
opt = torch.optim.AdamW([{"params": squelette, "lr": R["lr_squelette"]}, {"params": decodeur, "lr": R["lr_decodeur"]}],
                        weight_decay=R["decroissance_poids"])
EPOQUES = min(2, int(R["epoques"])) if ESSAI else int(R["epoques"]); LOT = 2 if ESSAI else int(R["lot"])
n_lots = max(1, n0 // LOT)
if ESSAI:
    n_lots = min(n_lots, 3)
prog = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=[R["lr_squelette"], R["lr_decodeur"]],
                                           total_steps=max(1, EPOQUES * n_lots), pct_start=0.05)
echelle = torch.amp.GradScaler(enabled=DEV == "cuda")
ema = copy.deepcopy(modele).eval() if R["ema"] else None
for p_ in (ema.parameters() if ema is not None else []):
    p_.requires_grad_(False)
n_pas, debut, HISTO, ep = 0, time.time(), [], 0
dire(f"{n_lots} lots de {LOT} par époque, {EPOQUES} époques")


def maj_ema():
    d = min(R["ema"], (1 + n_pas) / (10 + n_pas))
    with torch.no_grad():
        for (k, e), p in zip(ema.state_dict().items(), modele.state_dict().values()):
            if e.dtype.is_floating_point:
                e.mul_(d).add_(p.detach(), alpha=1 - d)
            else:
                e.copy_(p)


for ep in range(1, EPOQUES + 1):
    modele.train(); geler_bn(modele); t0, somme, n = time.time(), 0.0, 0
    charge = DataLoader(Tuiles(echantillons_epoque(rng)), batch_size=LOT, shuffle=True,
                        num_workers=0 if ESSAI else int(R["num_workers"]), drop_last=True, pin_memory=DEV == "cuda",
                        persistent_workers=False)
    for k, lot in enumerate(charge):
        if k >= n_lots:
            break
        lot = [t.to(DEV, non_blocking=True) for t in lot]
        x, y, w, dec, md = lot[:5]
        with torch.autocast(DEV, dtype=torch.float16, enabled=DEV == "cuda"):
            sortie = modele(x)
        perte = perte_focale(sortie[:, :1], y, w, R["poids_pos"])
        if MAITRES:
            with torch.no_grad(), torch.autocast(DEV, dtype=torch.float16, enabled=DEV == "cuda"):
                cible_m = sum(torch.sigmoid(mt(x).float()[:, :1]) for mt in MAITRES) / len(MAITRES)
            perte = perte + R["lambda_distil"] * (F.binary_cross_entropy_with_logits(sortie[:, :1].float(), cible_m, reduction="none") * w).mean()
        c = 1
        if R["decalage"]:
            m_ = md * w
            perte = perte + (torch.abs(sortie[:, c:c + 2].float() - dec) * m_).sum() / m_.sum().clamp(min=1)
            c += 2
        if R["tete_densite"]:
            dens = F.softplus(sortie[:, c:c + 1].float())
            perte = perte + 1000 * (((dens - lot[5]) ** 2) * w).mean() + 0.02 * torch.abs((dens * w).sum((1, 2, 3)) - (lot[5] * w).sum((1, 2, 3))).mean()
        if not torch.isfinite(perte):
            raise RuntimeError(f"perte non finie à l'époque {ep}")
        opt.zero_grad(set_to_none=True)
        echelle.scale(perte).backward(); echelle.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(modele.parameters(), R["ecretage"])
        echelle.step(opt); echelle.update(); prog.step(); n_pas += 1
        if ema is not None:
            maj_ema()
        somme += float(perte.detach()); n += 1
    dire(f"époque {ep:2d} : perte {somme / max(n, 1):.3f} | {(time.time() - t0) / 60:.1f} min")
    if ep in tuple(R["mesures_intermediaires"]) and ep < EPOQUES:
        # pour information seulement : aucune époque n'est choisie
        m_ep = (ema if ema is not None else modele).eval()
        l = choisir(lignes_reglage(mesurer_reglage(PredicteurTorch(m_ep)), f"époque {ep}"))
        HISTO.append(l); dire(f"   (information, EMA époque {ep}) {resume(l)}")
    if (time.time() - debut) / 3600 > R["duree_max_h"]:
        dire("Durée maximale atteinte : arrêt propre"); break

final = ema if ema is not None else modele
final.eval()
torch.save(final.state_dict(), f"{SORTIE}/poids_{R['nom']}.pt")
t0 = time.time()
LIGNES = lignes_reglage(mesurer_reglage(PredicteurTorch(final)), "final")
RETENU = choisir(LIGNES)
pd.DataFrame(LIGNES + HISTO).to_csv(f"{SORTIE}/reglage.csv", index=False)
dire(f"RÉGLAGE ({(time.time() - t0) / 60:.1f} min), règle 3.4 : retenu {resume(RETENU)}")
for l in LIGNES:
    dire("   ", resume(l))

# ---------------------------------------------------------------- export ONNX (format de modeles/centres_5cm_v5.*)
nom_fichier = f"centres_5cm_{R['nom']}"
cpu = DetecteurCentres(R["reseau"], stride=STRIDE, decalage=R["decalage"], densite=R["tete_densite"], preentraine=False)
cpu.load_state_dict({k: v.float().cpu() for k, v in final.state_dict().items()}); cpu.eval()
chemin_onnx = f"{SORTIE}/{nom_fichier}.onnx"
ecart = None
try:
    torch.onnx.export(cpu, torch.randn(1, 3, 512, 512), chemin_onnx, input_names=["image"], output_names=["logits"],
                      opset_version=17, dynamic_axes={"image": {2: "h", 3: "l"}, "logits": {2: "hs", 3: "ls"}}, dynamo=False)
    import onnxruntime as ort
    xin, _, _ = entree(lire(ZONES_MM.image_path.iloc[0]))
    ref = cpu(torch.from_numpy(xin)).detach().numpy()
    out = ort.InferenceSession(chemin_onnx, providers=["CPUExecutionProvider"]).run(None, {"image": xin})[0]
    ecart = float(np.abs(out - ref).max())
    dire(f"ONNX : écart maximal {ecart:.2e} ; {os.path.getsize(chemin_onnx) / 1e6:.0f} Mo")
except Exception as e:  # l'export se refera en local à partir du .pt
    dire("Export ONNX impossible ici :", repr(e))
sortie_txt = (f"logits à 1/{STRIDE} de la résolution d'entrée ; canal 0 = centres (sigmoïde puis maxima locaux, fenêtre k_pics, "
              f"au-dessus du seuil)" + (" ; canaux 1-2 = décalage (x, y) en pixels de sortie, ajouté à la position du pic"
                                        if R["decalage"] else "")
              + (" ; dernier canal = densité (softplus, somme = compte)" if R["tete_densite"] else "")
              + (f" ; entrée agrandie d'un facteur {FE:.4f} (3,5 cm/px), coordonnées divisées par ce facteur" if FE != 1.0 else ""))
json.dump(dict(versions=VERSIONS, reglages=dict(R, stride=STRIDE, decoupe_px=CROP, epoques_faites=ep, lots_par_epoque=n_lots,
                                               tirage_detail=[(n_, len(l_), k_) for n_, l_, k_ in PLAN], n_negatifs_par_epoque=N_NEG,
                                               rayon_px=RAYON_PX, rayon_ignore_px=RAYON_IGNORE, duree_h=round((time.time() - debut) / 3600, 2)),
               retenu=RETENU, seuil=RETENU["seuil"], k_pics=K_PICS, stride=STRIDE, facteur_entree=FE, ecart_onnx=ecart,
               intermediaires=HISTO, normalisation=dict(moyenne=MOY.tolist(), ecart_type=ECT.tolist()),
               entree="RGB 0-255 / 255, normalisé, NCHW, complété en noir à un multiple de 32", sortie=sortie_txt,
               regle="docs/plan_nuit_2026-11-12.md 3.4 : poids EMA de la dernière époque (pas de choix d'époque) ; seuil = moyenne "
                     "des 5 F1 de réglage (dense banavista B, plantain 100_metros, jeunes dji_0544, MM1-MM2 mères, btd_val) maximale "
                     "sur 0,10-0,60, sous 1 % de fausses détections sur les images sans bananier de validation ; aucun juge calculé"),
          open(f"{SORTIE}/{nom_fichier}.json", "w"), indent=2, ensure_ascii=False, default=float)
dire("FIN", sorted(os.listdir(SORTIE)))
