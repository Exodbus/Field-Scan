#!/usr/bin/env python3
"""M2 (plan de la nuit du 12/11, section 4.3) : lecture en morceaux par la v10b, sur un échantillon tiré à l'avance.

Échantillon : 400 photos par jeu de réglage, graine 2026 (tirage sans remise parmi toutes les photos du jeu, jeux dans
l'ordre validation, tdtu, psfd, ethiopie). Seules les photos « proche » (p_loin < 0,5) sont lues : les autres vont à la
v2 quoi qu'il arrive. Grille g × g : morceaux rectangulaires de même forme que la photo, de côté 0,6 (2×2) ou 0,42 (3×3)
de chaque dimension, posés régulièrement d'un bord à l'autre (recouvrement de 20 % et 13 %). Chaque morceau passe par
la même préparation que la photo entière (maladies.predire_convnext : petit côté à 384 px, carré au centre, JPEG 95,
4 vues, 3 réseaux). Sortie : out/maladies/nuit_1112/banc/m2_<jeu>_g<g>.npz (indices, probabilités n × g² × 4).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/m12_banc_m2_morceaux.py [grille=2] [bloc=50]
"""
import io
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402
from fieldscan.modules import maladies  # noqa: E402

G = int(sys.argv[1]) if len(sys.argv) > 1 else 2
BLOC = int(sys.argv[2]) if len(sys.argv) > 2 else 50
PART = {2: 0.6, 3: 0.42}[G]


def echantillon(jeux, n=400, graine=2026):
    rng = np.random.default_rng(graine)
    return {j: np.sort(rng.choice(len(jeux[j]["chemin"]), size=n, replace=False)) for j in B.REGLAGE}


def morceaux(chemin):
    """Les g² morceaux d'une photo, en PNG en mémoire (sans perte), lisibles par maladies.preparer_convnext."""
    with Image.open(chemin) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
    w, h = im.size
    mw, mh = max(1, round(PART * w)), max(1, round(PART * h))
    sortie = []
    for iy in range(G):
        for ix in range(G):
            x0, y0 = round(ix * (w - mw) / (G - 1)), round(iy * (h - mh) / (G - 1))
            t = io.BytesIO()
            im.crop((x0, y0, x0 + mw, y0 + mh)).save(t, format="PNG")
            t.seek(0)
            sortie.append(t)
    return sortie


if __name__ == "__main__":
    jeux = B.charger_reglage()
    ech = echantillon(jeux)
    m = maladies.charger_convnext(RACINE / "modeles/maladies_binome/v10b")
    etat = {}
    for j in B.REGLAGE:
        idx = ech[j][~jeux[j]["loin"][ech[j]]]
        f = B.SORTIE / f"m2_{j}_g{G}.npz"
        if f.exists():
            z = np.load(f)
            assert np.array_equal(z["indices"], idx)
            etat[j] = dict(idx=idx, P=z["P"], fait=int(z["fait"]), f=f)
        else:
            etat[j] = dict(idx=idx, P=np.full((len(idx), G * G, 4), np.nan, "float32"), fait=0, f=f)
        print(j, len(idx), "photos proches dans l'échantillon, déjà faites :", etat[j]["fait"], flush=True)
    t0 = time.time()
    while any(e["fait"] < len(e["idx"]) for e in etat.values()):   # blocs à tour de rôle : résultats partiels utilisables
        for j, e in etat.items():
            a, b = e["fait"], min(e["fait"] + BLOC, len(e["idx"]))
            if a == b:
                continue
            tuiles = [t for i in e["idx"][a:b] for t in morceaux(B.fichier(jeux[j]["chemin"][i]))]
            e["P"][a:b] = maladies.predire_convnext(tuiles, m, lot=16).reshape(b - a, G * G, 4)
            e["fait"] = b
            np.savez(e["f"], indices=e["idx"], P=e["P"], fait=b)
            print(f"{j} {b}/{len(e['idx'])} ; {(time.time() - t0) / 60:.1f} min", flush=True)
    print("fini", flush=True)
