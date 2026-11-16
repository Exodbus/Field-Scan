#!/usr/bin/env python3
"""Banc de comptage de la nuit du 13 au 14 novembre 2026 (agent C-banc) : partie commune.

Reprend sans le modifier le banc de la nuit précédente (scripts/v6_banc_commun.py : mesure du carnet v5, pics fenêtre 7,
rayon 20 px, appariement un-à-un, disque de 2 000 px, zones MM) et ses cartes en cache (out/comptage_v6/banc/cache,
lecture seule). Ce qui est neuf ici :
  - garde-fou des juges : seuls les jeux de réglage sont chargés, et chaque tuile est contrôlée par un assert sur son
    ensemble dans tuiles.csv avant toute lecture d'image ;
  - cache propre (out/comptage/nuit_1311/banc/cache) pour les cartes des images dégradées (CB2) ;
  - règle 5.3 du plan (docs/plan_nuit_2026-11-13.md) : référence v5 au seuil 0,30, contrainte val_negatifs < 1 %.
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import v6_banc_commun as bc  # noqa: E402

SORTIE = RACINE / "out/comptage/nuit_1311/banc"
CACHE = SORTIE / "cache"
KAGGLE_CACHE = RACINE / "out/comptage/nuit_1311/kaggle/cache"
SORTIE.mkdir(parents=True, exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)

REGLAGE = ["dense", "plantain", "jeunes", "mm", "btd_val"]
ANCIENS = ["dense", "plantain", "jeunes", "mm"]            # « 4 anciennes validations » (sans btd_val)
SEUILS = bc.SEUILS
FILS = 3                                                   # machine partagée : 3 fils au plus

# ---------------------------------------------------------------------------------------------- garde-fou des juges
ENSEMBLE_PERMIS = {"dense": ("v5", "val_dense_bv"), "plantain": ("v5", "val_plantain"), "jeunes": ("v5", "val_jeunes"),
                   "btd_val": ("v6", "val_espace"), "neg": ("v5", "val_negatifs")}
INTERDITS = {"test_dense", "test_banano", "test_negatifs", "test_espace"}
_TUILES = {}


def _ensembles(arch):
    if arch not in _TUILES:
        d = bc.D if arch == "v5" else bc.D6
        T = pd.read_csv(d / "tuiles.csv", usecols=["image_path", "ensemble"])
        _TUILES[arch] = dict(zip(T.image_path, T.ensemble))
    return _TUILES[arch]


def jeu(nom):
    """Images d'un jeu de réglage. Tout autre jeu est refusé ; chaque tuile est vérifiée dans tuiles.csv."""
    assert nom in REGLAGE + ["neg"], f"jeu refusé (réglage seulement) : {nom}"
    items = bc.jeu(nom)                    # _tuiles filtre tuiles.csv par ensemble avant toute lecture d'image
    if nom == "mm":
        for e in items:
            assert "/cg/" not in e["chemin"].replace("\\", "/") and "/mm/" in e["chemin"].replace("\\", "/"), e["chemin"]
    else:
        arch, ens = ENSEMBLE_PERMIS[nom]
        T = _ensembles(arch)
        for e in items:
            assert T[e["nom"]] == ens and T[e["nom"]] not in INTERDITS, (nom, e["nom"], T[e["nom"]])
            assert "/cg/" not in e["chemin"].replace("\\", "/") and "banana_trees_kp" not in e["chemin"], e["chemin"]
    return items


# ---------------------------------------------------------------------------------------------- cache propre (CB2)
def chemin_cache(modele, variante, nom_jeu):
    return CACHE / f"{modele}_{variante}_{nom_jeu}"


_MEM = {}
_carte_cache_v6 = bc.carte_cache


def carte_cache(modele, variante, nom_jeu, nom):
    """Cartes du banc v6 (lecture seule), ou du cache de cette nuit si la variante y est (images dégradées…)."""
    p = chemin_cache(modele, variante, nom_jeu)
    if not p.with_suffix(".json").exists():
        # cartes de C-entraîneur (spécialiste c13d), lecture seule
        pk = KAGGLE_CACHE / f"{modele}_{variante}_{nom_jeu}"
        if modele not in ("v3", "v4", "v5") and pk.with_suffix(".json").exists():
            p = pk
        else:
            return _carte_cache_v6(modele, variante, nom_jeu, nom)
    cle = (modele, variante, nom_jeu)
    if cle not in _MEM:
        _MEM[cle] = (np.memmap(p.with_suffix(".f32"), dtype="float32", mode="r"),
                     json.loads(p.with_suffix(".json").read_text(encoding="utf-8")))
    mm, idx = _MEM[cle]
    a, h, w = idx[nom]
    return np.asarray(mm[a:a + h * w]).reshape(h, w)


bc.carte_cache = carte_cache                # Contexte.carte lit désormais aussi le cache de cette nuit


# ---------------------------------------------------------------------------------------------- mesure et règle 5.3
def mesurer(candidat, jeux, items=None):
    items = items or {}
    return {j: bc.mesurer_jeu(candidat, j, items.get(j) or jeu(j)) for j in jeux}


def lignes(m, jeux=REGLAGE, neg="neg"):
    """Une ligne par seuil de la grille : F1 par jeu, moyenne des 5, moyenne des 4 anciennes, erreur de compte, fausses."""
    out = []
    for s in SEUILS:
        s = float(s)
        f = {j: m[j][s]["f1"] for j in jeux}
        l = dict(seuil=s, **{f"f1_{j}": f[j] for j in jeux}, moyenne=float(np.mean(list(f.values()))),
                 moy4=float(np.mean([f[j] for j in jeux if j in ANCIENS])),
                 err_compte=float(np.mean([m[j][s]["err_compte"] for j in jeux])),
                 **{f"ratio_{j}": m[j][s]["detectes"] / max(m[j][s]["reels"], 1) for j in jeux})
        if neg in m:
            l.update(fp_neg=m[neg][s]["fp"], taux_fp=m[neg][s]["taux"], eligible=m[neg][s]["taux"] < 0.01)
        out.append(l)
    return out


def choisir(ls):
    """Règle 5.3 : seuil qui maximise la moyenne des 5 F1 sous val_negatifs < 1 %."""
    el = [l for l in ls if l.get("eligible")]
    return max(el, key=lambda l: l["moyenne"]) if el else None


def reference_v5(E):
    """Référence : v5 au seuil 0,30 (plan, section 1 et consigne de la nuit)."""
    return [l for l in lignes(E["v5"]["res"]) if l["seuil"] == 0.30][0]


def statut(b, ref, jeux=REGLAGE):
    pertes = {j: b[f"f1_{j}"] - ref[f"f1_{j}"] for j in jeux}
    c = dict(gain=b["moyenne"] - ref["moyenne"], pire_perte=min(pertes.values()),
             pire_jeu=min(pertes, key=pertes.get))
    c["c1"] = b["moyenne"] > ref["moyenne"] + 0.010 and b["moy4"] >= ref["moy4"]
    c["c2"] = c["pire_perte"] >= -0.020
    c["c3"] = b["err_compte"] <= ref["err_compte"]
    c["c4"] = b["taux_fp"] < 0.01
    c["finaliste"] = bool(c["c1"] and c["c2"] and c["c3"] and c["c4"])
    return c


def res_float(res):
    return {j: {float(s): v for s, v in r.items()} for j, r in res.items()}
