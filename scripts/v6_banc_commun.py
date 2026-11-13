#!/usr/bin/env python3
"""Banc de mesure du comptage v6 (agent C-banc, nuit du 12 au 13 novembre 2026) : partie commune.

Un « candidat » est une fonction (Contexte d'image) -> (points xy en pixels à 5 cm, scores). Le banc donne par jeu,
pour chaque seuil de la grille 0,10 à 0,60 : précision, rappel, F1, détectés / annotés, et les fausses détections
sur les images sans bananier. La mesure est celle du carnet notebooks/entrainer_centres_v5_kaggle.ipynb, recopiée :
image entière complétée en noir à un multiple de 32, sigmoïde, maxima locaux (fenêtre K_PICS), appariement un-à-un
à distance minimale dans un rayon de 20 px, disque de 2 000 px (masque) pour les photos DJI, zones ignorées.

Les cartes de chaleur des v3, v4 et v5 sont mises en cache une fois (out/comptage_v6/banc/cache), par variante :
  base : image telle quelle ;  m8 / x8 / g8 : 8 symétries (moyenne des probabilités, maximum, moyenne des logits) ;
  s35 / s70 : image agrandie (5 -> 3,5 cm par pixel) ou réduite (5 -> 7 cm), carte à sa résolution propre.
Rien n'est modifié dans fieldscan/ ; la détection par pics est recopiée de fieldscan/drone.py (DetecteurCentres.predire).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from scipy.ndimage import maximum_filter
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
D = RACINE / "data/drone/comptage_v5_5cm"
SORTIE = RACINE / "out/comptage_v6/banc"
CACHE = SORTIE / "cache"
DECOUPAGE_V6 = RACINE / "data/drone/decoupage_comptage_v6/decoupage.csv"
MODELES = {v: RACINE / f"modeles/centres_5cm_{v}.onnx" for v in ("v3", "v4", "v5")}
# Essai 10 : modèles entraînés cette nuit (C-entraîneur), déclarés dans ce fichier {nom: chemin ONNX} par C-banc
_EXTRA = SORTIE / "modeles_nuit.json"
if _EXTRA.exists():
    MODELES.update({k: RACINE / v for k, v in json.loads(_EXTRA.read_text(encoding="utf-8")).items()})
SEUILS = [round(0.10 + 0.05 * k, 2) for k in range(11)]
K_PICS, STRIDE, RAYON_PX = 7, 4, 20
MOY = np.array([0.485, 0.456, 0.406], "float32")
ECT = np.array([0.229, 0.224, 0.225], "float32")
ECHELLES = {"s35": 5 / 3.5, "s70": 5 / 7}
VARIANTES = {"base": ["base"], "tta": ["m8", "x8", "g8"], "ech": ["s35", "s70"]}
REGLAGE = ["dense", "plantain", "jeunes", "mm", "btd_val"]          # les 5 F1 de réglage (btd_val : quand le découpage v6 existe)
JUGES = ["segmento", "cg", "banano"]


# ----------------------------------------------------------------------------------------------- jeux
def _tuiles(ensemble, noms=None, D=D):
    T, O = pd.read_csv(D / "tuiles.csv"), pd.read_csv(D / "objets.csv")
    T = T[T.ensemble == ensemble]
    if noms is not None:
        T = T[T.image_path.isin(noms)]
    O = {k: g for k, g in O[O.image_path.isin(set(T.image_path))].groupby("image_path")}
    items = []
    for r in T.itertuples():
        o = O.get(r.image_path)
        meres = o[o.type == "mere"][["cx", "cy"]].to_numpy("float64") if o is not None else np.zeros((0, 2))
        ign = o[o.type != "mere"][["cx", "cy"]].to_numpy("float64") if o is not None else np.zeros((0, 2))
        masque = None if np.isnan(r.masque_r) else (r.masque_cx, r.masque_cy, r.masque_r)
        if masque is not None:
            meres = meres[dans_masque(meres, masque)]
        items.append(dict(nom=r.image_path, chemin=str(D / "images" / r.image_path), pts=meres, ign=ign, masque=masque,
                          zone=None, n_autres=int(r.n_autres_arbres)))
    return items


def _zones(sous):
    P, Z = pd.read_csv(D / sous / "points.csv"), pd.read_csv(D / sous / "zones.csv")
    items = []
    for z in Z.itertuples():
        p = P[P.zone_id == z.zone_id]
        items.append(dict(nom=z.image_path, chemin=str(D / sous / "images" / z.image_path),
                          pts=p[p.type == "mere"][["x", "y"]].to_numpy("float64"),
                          ign=p[p.type != "mere"][["x", "y"]].to_numpy("float64"), masque=None,
                          zone=(z.x0, z.y0, z.x1, z.y1), n_autres=0))
    return items


D6 = RACINE / "data/drone/comptage_v6_5cm"
JOURNAL_DECOUPAGE = RACINE / "docs/nuit_2026-11-12/journal_c_decoupage.md"


def btd_val_pret():
    """banana_tree_detection, moitié validation : seulement si l'agent C-découpage (D-comptage) a écrit « DÉCOUPAGE PRÊT »
    et que l'archive v6 contient l'ensemble val_espace (images entières à 5 cm). Sinon aucune image de ce jeu n'est lue."""
    if not (DECOUPAGE_V6.exists() and JOURNAL_DECOUPAGE.exists() and (D6 / "tuiles.csv").exists() and (D6 / "objets.csv").exists()):
        return False
    if "DÉCOUPAGE PRÊT" not in JOURNAL_DECOUPAGE.read_text(encoding="utf-8"):
        return False
    return bool((pd.read_csv(D6 / "tuiles.csv").ensemble == "val_espace").any())


def noms_btd_validation():
    return True if btd_val_pret() else None


def jeu(nom):
    """Liste des images d'un jeu. Les juges ne sont chargés que par scripts/v6_banc_juges.py."""
    if nom == "dense":
        return _tuiles("val_dense_bv")
    if nom == "plantain":
        return _tuiles("val_plantain")
    if nom == "jeunes":
        return _tuiles("val_jeunes")
    if nom == "mm":
        return _zones("mm")
    if nom == "neg":
        return _tuiles("val_negatifs")
    if nom == "neg_q":
        # tri des variantes coûteuses (symétries, échelles) : une tuile sans bananier sur quatre, dans l'ordre du fichier.
        # Les finalistes sont ensuite contrôlés sur toutes les tuiles (neg).
        return _tuiles("val_negatifs")[::4]
    if nom == "btd_val":
        noms = noms_btd_validation()
        if noms is None:
            raise FileNotFoundError("decoupage_comptage_v6/decoupage.csv absent : aucune image de banana_tree_detection utilisable")
        return _tuiles("val_espace", D=D6)
    if nom == "segmento":
        return _tuiles("test_dense")
    if nom == "banano":
        return _tuiles("test_banano")
    if nom == "cg":
        return _zones("cg")
    if nom == "neg_test":
        return _tuiles("test_negatifs")
    raise KeyError(nom)


def dans_masque(xy, masque):
    if masque is None or not len(xy):
        return np.ones(len(xy), bool)
    mx, my, mr = masque
    return (xy[:, 0] - mx) ** 2 + (xy[:, 1] - my) ** 2 <= mr ** 2


# ----------------------------------------------------------------------------------------------- cartes
def lire(chemin):
    return np.asarray(Image.open(chemin).convert("RGB"))


def entree(img):
    """Image complétée en noir jusqu'à un multiple de 32 (comme le carnet v5)."""
    h, w = img.shape[:2]
    H, W = (h + 31) // 32 * 32, (w + 31) // 32 * 32
    x = np.zeros((H, W, 3), "float32")
    x[:h, :w] = img.astype("float32") / 255
    return ((x - MOY) / ECT).transpose(2, 0, 1)[None].astype("float32"), h, w


def _logits(sess, x):
    """Logits du centre au quart de la résolution. Un modèle à sortie à la demi-résolution (v6b) est ramené au quart
    par maximum 2 x 2 (pour se mélanger aux autres sur la même grille) ; la tête de décalage éventuelle est ignorée."""
    z = sess.run(None, {sess.get_inputs()[0].name: np.ascontiguousarray(x)})[0][0, 0]
    H4 = (x.shape[2] + 3) // 4
    if z.shape[0] >= 2 * H4 - 1:
        h2, w2 = z.shape[0] // 2 * 2, z.shape[1] // 2 * 2
        z = z[:h2, :w2].reshape(h2 // 2, 2, w2 // 2, 2).max(axis=(1, 3))
    return z


def sigmoide(z):
    return 1.0 / (1.0 + np.exp(-z.astype("float64")))


def cartes_image(sess, img, groupe):
    """Cartes (float32) d'une image pour un groupe de variantes."""
    x, h, w = entree(img)
    hh, ww = (h + 3) // 4, (w + 3) // 4
    if groupe == "base":
        return {"base": sigmoide(_logits(sess, x))[:hh, :ww].astype("float32")}
    if groupe == "tta":
        # 8 symétries appliquées à l'image déjà complétée : la grille au quart reste alignée après retour
        ps, zs = [], []
        for miroir in (False, True):
            for k in range(4):
                v = x[:, :, :, ::-1] if miroir else x
                v = np.rot90(v, k, axes=(2, 3))
                z = np.rot90(_logits(sess, v), -k, axes=(0, 1))
                z = z[:, ::-1] if miroir else z
                zs.append(z[:hh, :ww].astype("float64"))
                ps.append(sigmoide(zs[-1]))
        return {"m8": np.mean(ps, 0).astype("float32"), "x8": np.max(ps, 0).astype("float32"),
                "g8": sigmoide(np.mean(zs, 0)).astype("float32")}
    if groupe == "ech":
        res = {}
        for nom, f in ECHELLES.items():
            im = Image.fromarray(img).resize((max(32, round(w * f)), max(32, round(h * f))), Image.BILINEAR)
            x2, h2, w2 = entree(np.asarray(im))
            res[nom] = sigmoide(_logits(sess, x2))[:(h2 + 3) // 4, :(w2 + 3) // 4].astype("float32")
        return res
    raise KeyError(groupe)


def session(modele, fils=0):
    import onnxruntime as ort
    o = ort.SessionOptions()
    if fils:
        o.intra_op_num_threads = fils
    return ort.InferenceSession(str(MODELES[modele]), o, providers=["CPUExecutionProvider"])


def chemin_cache(modele, variante, nom_jeu):
    return CACHE / f"{modele}_{variante}_{nom_jeu}"


def ecrire_cache(modele, groupe, nom_jeu, fils=0, journal=print):
    """Calcule et enregistre les cartes d'un modèle pour un jeu (un fichier plat float32 + un index par variante)."""
    variantes = VARIANTES[groupe]
    if all(chemin_cache(modele, v, nom_jeu).with_suffix(".json").exists() for v in variantes):
        return
    CACHE.mkdir(parents=True, exist_ok=True)
    sess = session(modele, fils)
    items = jeu(nom_jeu)
    blocs = {v: [] for v in variantes}
    index = {v: {} for v in variantes}
    pos = {v: 0 for v in variantes}
    for n, e in enumerate(items):
        for v, c in cartes_image(sess, lire(e["chemin"]), groupe).items():
            blocs[v].append(c.ravel())
            index[v][e["nom"]] = [pos[v], c.shape[0], c.shape[1]]
            pos[v] += c.size
        if n % 200 == 0:
            journal(f"  cache {modele} {groupe} {nom_jeu} : {n}/{len(items)}")
    for v in variantes:
        np.concatenate(blocs[v]).astype("float32").tofile(chemin_cache(modele, v, nom_jeu).with_suffix(".f32"))
        chemin_cache(modele, v, nom_jeu).with_suffix(".json").write_text(json.dumps(index[v]), encoding="utf-8")


_MEM = {}


def carte_cache(modele, variante, nom_jeu, nom):
    if nom_jeu == "neg_q" and chemin_cache(modele, variante, "neg").with_suffix(".json").exists():
        nom_jeu = "neg"                      # le cache complet contient les tuiles du quart
    cle = (modele, variante, nom_jeu)
    if cle not in _MEM:
        p = chemin_cache(modele, variante, nom_jeu)
        _MEM[cle] = (np.memmap(p.with_suffix(".f32"), dtype="float32", mode="r"),
                     json.loads(p.with_suffix(".json").read_text(encoding="utf-8")))
    mm, idx = _MEM[cle]
    a, h, w = idx[nom]
    return np.asarray(mm[a:a + h * w]).reshape(h, w)


class Contexte:
    """Ce qu'un candidat peut lire pour une image : les cartes en cache (jamais les annotations)."""

    def __init__(self, nom_jeu, item):
        self.nom_jeu, self.nom = nom_jeu, item["nom"]

    def carte(self, modele, variante="base"):
        """Carte de probabilité sur la grille de base (H/4, L/4). Les variantes d'échelle y sont ramenées (bilinéaire)."""
        c = carte_cache(modele, variante, self.nom_jeu, self.nom)
        if variante in ECHELLES:
            import cv2
            b = carte_cache(modele, "base", self.nom_jeu, self.nom)
            c = cv2.resize(c, (b.shape[1], b.shape[0]), interpolation=cv2.INTER_LINEAR)
        return c

    def carte_propre(self, modele, variante):
        """Carte à sa résolution propre et facteur d'échelle de l'image (1 pour base et symétries)."""
        return carte_cache(modele, variante, self.nom_jeu, self.nom), ECHELLES.get(variante, 1.0)


# ----------------------------------------------------------------------------------------------- pics et mesure
def pics(carte, k=K_PICS, seuil_min=SEUILS[0], echelle=1.0):
    """Maxima locaux (fenêtre k) au-dessus de seuil_min : points (x, y) en pixels de l'image à 5 cm, et scores."""
    pic = (carte == maximum_filter(carte, size=k, mode="constant")) & (carte >= seuil_min)
    j, i = np.nonzero(pic)
    return np.c_[(i + 0.5) * STRIDE / echelle, (j + 0.5) * STRIDE / echelle], carte[j, i].astype("float64")


def compter(det, certains, ignores, rayon=RAYON_PX):
    n, pris = 0, set()
    if len(det) and len(certains):
        d = cdist(det, certains)
        li, co = linear_sum_assignment(np.where(d <= rayon, d, 1e6))
        ok = d[li, co] <= rayon
        n, pris = int(ok.sum()), set(li[ok].tolist())
    reste = [i for i in range(len(det)) if i not in pris]
    ign = int((cdist(det[reste], ignores).min(1) <= rayon).sum()) if len(ignores) and reste else 0
    return n, len(det) - n - ign, len(certains) - n


def prf(vp, fp, fn):
    p = vp / (vp + fp) if vp + fp else 0.0
    r = vp / (vp + fn) if vp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def mesurer_jeu(candidat, nom_jeu, items=None):
    """Mesure un candidat sur un jeu, à tous les seuils. Jeu sans bananier : fausses détections et taux par arbre."""
    items = jeu(nom_jeu) if items is None else items
    acc = {s: [0, 0, 0, 0] for s in SEUILS}
    reels = arbres = 0
    for e in items:
        xy, sc = candidat(Contexte(nom_jeu, e))
        xy, sc = np.asarray(xy, "float64").reshape(-1, 2), np.asarray(sc, "float64")
        if e["zone"] is not None:
            x0, y0, x1, y1 = e["zone"]
            g = (xy[:, 0] >= x0) & (xy[:, 0] <= x1) & (xy[:, 1] >= y0) & (xy[:, 1] <= y1)
        else:
            g = dans_masque(xy, e["masque"])
        xy, sc = xy[g], sc[g]
        reels += len(e["pts"]); arbres += e["n_autres"]
        for s in SEUILS:
            d = xy[sc >= s]
            acc[s][3] += len(d)
            if nom_jeu.startswith("neg"):
                acc[s][1] += len(d)
            else:
                for k, v in enumerate(compter(d, e["pts"], e["ign"])):
                    acc[s][k] += v
    res = {}
    for s, (vp, fp, fn, det) in acc.items():
        if nom_jeu.startswith("neg"):
            res[s] = dict(fp=fp, arbres=arbres, taux=fp / max(arbres, 1))
        else:
            p, r, f = prf(vp, fp, fn)
            res[s] = dict(vp=vp, fp=fp, fn=fn, p=p, r=r, f1=f, detectes=det, reels=reels,
                          err_compte=abs(det / reels - 1) if reels else float("nan"))
    return res


def neg_de(res):
    return "neg" if "neg" in res else "neg_q"


def mesurer(candidat, jeux, neg="neg", items=None):
    items = items or {}
    return {j: mesurer_jeu(candidat, j, items.get(j)) for j in list(jeux) + [neg]}


def resume(m, jeux, neg="neg", limite_fp=0.01):
    """Règle 3.4 : seuil qui maximise la moyenne des F1 des jeux, sous moins de `limite_fp` de fausses détections."""
    lignes = []
    for s in SEUILS:
        f = [m[j][s]["f1"] for j in jeux]
        lignes.append(dict(seuil=s, **{f"f1_{j}": round(m[j][s]["f1"], 4) for j in jeux}, moyenne=float(np.mean(f)),
                           err_compte=float(np.mean([m[j][s]["err_compte"] for j in jeux])),
                           **{f"ratio_{j}": round(m[j][s]["detectes"] / m[j][s]["reels"], 3) for j in jeux},
                           fp_neg=m[neg][s]["fp"], taux_fp=m[neg][s]["taux"], eligible=m[neg][s]["taux"] < limite_fp))
    el = [l for l in lignes if l["eligible"]]
    return (max(el, key=lambda l: l["moyenne"]) if el else None), lignes


# ----------------------------------------------------------------------------------------------- candidats de base
def cand_modele(modele, variante="base", k=K_PICS):
    def f(ctx):
        return pics(ctx.carte(modele, variante), k)
    return f
