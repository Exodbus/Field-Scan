#!/usr/bin/env python3
"""Image entière annotée (agent C-analyste) : mères (cercle vert, rayon 20 px), non-mères (jaune), détections v5 au seuil
(croix rouge), v3 au seuil (croix bleue), zone comptée (disque, blanc). Usage : --jeu dense --image bv_bv_b_val_0010.jpg"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import v6_analyse_erreurs as ae  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--jeu", required=True); ap.add_argument("--images", nargs="+", required=True)
ap.add_argument("--zoom", type=float, default=1.5)
a = ap.parse_args()
items = {e["nom"]: e for e in ae.items_complets(a.jeu)}
for nom in a.images:
    e = items[nom]
    img = Image.fromarray(ae.bc.lire(e["chemin"]))
    z = a.zoom
    img = img.resize((int(img.width * z), int(img.height * z)), Image.BILINEAR)
    d = ImageDraw.Draw(img)
    if e["masque"] is not None:
        mx, my, mr = e["masque"]; d.ellipse([(mx - mr) * z, (my - mr) * z, (mx + mr) * z, (my + mr) * z], outline=(255, 255, 255), width=2)
    for x, y in e["pts"]:
        d.ellipse([(x - 20) * z, (y - 20) * z, (x + 20) * z, (y + 20) * z], outline=(0, 255, 0), width=2)
    for x, y in e["ign"]:
        d.ellipse([(x - 6) * z, (y - 6) * z, (x + 6) * z, (y + 6) * z], outline=(255, 255, 0), width=2)
    for m, col, t in (("v3", (60, 140, 255), 6), ("v5", (255, 40, 40), 8)):
        xy, sc = ae.bc.pics(ae.carte(m, "base", a.jeu, nom), ae.bc.K_PICS, ae.SEUILS_ADOPTES[m])
        for x, y in xy:
            u, v = x * z, y * z
            d.line([u - t, v - t, u + t, v + t], fill=col, width=3); d.line([u - t, v + t, u + t, v - t], fill=col, width=3)
    out = ae.SORTIE / "planches" / f"image_{a.jeu}_{Path(nom).stem}.jpg"
    img.save(out, quality=88); print("écrit", out)
