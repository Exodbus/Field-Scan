#!/usr/bin/env python3
"""Planches de contrôle à l'œil (agent C-analyste) : vignettes autour des oubliés ou des fausses détections.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/v6_analyse_planches.py --tag base --modele v5
Vignettes tirées au hasard (graine 0) dans chaque catégorie, 128 px à 5 cm (6,4 m) autour du point, agrandies x2.
Cercle vert : mère annotée (épais : le pied visé) ; jaune : point non-mère (rejet, ignoré) ; croix rouge : détection
du modèle au seuil ; croix bleue : détection du v3 à son seuil (si fournie). Texte : catégorie et score.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import v6_analyse_erreurs as ae  # noqa: E402

SORTIE = RACINE / "out/comptage/analyse/planches"
DEMI, ZOOM, COLS = 64, 2, 6


def vignette(img, x, y, meres, ign, dets, dets_b, texte, cible=None):
    h, w = img.shape[:2]
    x0, y0 = int(round(x)) - DEMI, int(round(y)) - DEMI
    tuile = np.zeros((2 * DEMI, 2 * DEMI, 3), "uint8")
    a0, b0 = max(0, x0), max(0, y0)
    a1, b1 = min(w, x0 + 2 * DEMI), min(h, y0 + 2 * DEMI)
    if a1 > a0 and b1 > b0:
        tuile[b0 - y0:b1 - y0, a0 - x0:a1 - x0] = img[b0:b1, a0:a1]
    im = Image.fromarray(tuile).resize((2 * DEMI * ZOOM,) * 2, Image.NEAREST)
    d = ImageDraw.Draw(im)
    f = lambda px, py: ((px - x0) * ZOOM, (py - y0) * ZOOM)
    for (px, py) in meres:
        u, v = f(px, py)
        e = 3 if cible is not None and abs(px - cible[0]) < 0.5 and abs(py - cible[1]) < 0.5 else 1
        d.ellipse([u - 20 * ZOOM, v - 20 * ZOOM, u + 20 * ZOOM, v + 20 * ZOOM], outline=(0, 255, 0), width=e)
    for (px, py) in ign:
        u, v = f(px, py)
        d.ellipse([u - 6, v - 6, u + 6, v + 6], outline=(255, 255, 0), width=2)
    for pts, col, t in ((dets_b, (60, 140, 255), 7), (dets, (255, 40, 40), 9)):
        for (px, py) in pts:
            u, v = f(px, py)
            d.line([u - t, v - t, u + t, v + t], fill=col, width=3)
            d.line([u - t, v + t, u + t, v - t], fill=col, width=3)
    d.rectangle([0, 0, im.width, 14], fill=(0, 0, 0))
    d.text((3, 1), texte, fill=(255, 255, 255))
    return im


def planche(lignes, nom, items, dets_m, dets_b, mode):
    n = len(lignes)
    if not n:
        return
    rows = (n + COLS - 1) // COLS
    T = 2 * DEMI * ZOOM
    P = Image.new("RGB", (COLS * T + (COLS - 1) * 4, rows * T + (rows - 1) * 4), (40, 40, 40))
    cache = {}
    for k, r in enumerate(lignes.itertuples()):
        e = items[r.image]
        if r.image not in cache:
            cache[r.image] = ae.bc.lire(e["chemin"])
        img = cache[r.image]
        if mode == "pieds":
            t = f"{r.cat} pic {r.pic:.2f} vmax {r.vmax:.2f}"
            if not np.isnan(r.taille):
                t += f" b{r.taille:.0f}"
        else:
            t = f"{r.cat} {r.score:.2f}"
        v = vignette(img, r.x, r.y, e["pts"], e["ign"], dets_m.get(r.image, np.zeros((0, 2))),
                     dets_b.get(r.image, np.zeros((0, 2))), t, cible=(r.x, r.y) if mode == "pieds" else None)
        P.paste(v, ((k % COLS) * (T + 4), (k // COLS) * (T + 4)))
    SORTIE.mkdir(parents=True, exist_ok=True)
    P.save(SORTIE / nom, quality=88)
    print("écrit", SORTIE / nom)


def detections(Pm, Dm):
    """Positions des détections (retrouvées = position de la mère, approximation ; fausses = position exacte)."""
    out = {}
    for img, g in Dm.groupby("image"):
        out[img] = g[["x", "y"]].to_numpy()
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="base")
    ap.add_argument("--modele", default="v5")
    ap.add_argument("--ref", default="v3")
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--variante", default="base")
    a = ap.parse_args()
    S = RACINE / "out/comptage/analyse"
    P = pd.read_csv(S / f"pieds_{a.tag}.csv")
    D = pd.read_csv(S / f"fausses_{a.tag}.csv")
    rng = np.random.default_rng(0)
    for j in P.jeu.unique():
        items = {e["nom"]: e for e in ae.items_complets(j)}
        # détections complètes au seuil, recalculées depuis la carte (pour dessiner aussi les retrouvées)
        dm, db = {}, {}
        for nom, e in items.items():
            for mod, dd in ((a.modele, dm), (a.ref, db)):
                if mod not in set(P.modele):
                    continue
                s = P[P.modele == mod].seuil.iloc[0]
                c = ae.carte(mod, a.variante if mod == a.modele else "base", j, nom) if mod in ("v3", "v4", "v5") else None
                if c is None:
                    continue
                xy, sc = ae.bc.pics(c, ae.bc.K_PICS, s)
                dd[nom] = xy[ae.dans_compte(xy, e)] if len(xy) else xy
        p = P[(P.modele == a.modele) & (P.jeu == j) & (~P.retrouve)].copy()
        s = P[P.modele == a.modele].seuil.iloc[0]
        p["cat"] = np.select([p.fusion, p.pic >= s, p.pic >= s / 2, p.pic >= 0.05],
                             ["fusion", "pic>=seuil", "presque", "faible"], "rien")
        lots = []
        for c, g in p.groupby("cat"):
            lots.append(g.iloc[rng.permutation(len(g))[:max(4, a.n * len(g) // max(len(p), 1))]])
        if lots:
            planche(pd.concat(lots).head(36), f"oublies_{a.modele}_{j}.jpg", items, dm, db, "pieds")
        d = D[(D.modele == a.modele) & (D.jeu == j)].copy()
        lots = []
        for c, g in d.groupby("cat"):
            lots.append(g.iloc[rng.permutation(len(g))[:max(3, a.n * len(g) // max(len(d), 1))]])
        if lots:
            planche(pd.concat(lots).head(36), f"fausses_{a.modele}_{j}.jpg", items, dm, db, "fausses")
