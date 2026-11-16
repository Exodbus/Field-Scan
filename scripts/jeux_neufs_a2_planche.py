#!/usr/bin/env python3
"""A2 « plantain du Ghana » : planche visuelle de 4 photos (boîtes annotées et détections du v5 au seuil 0,30).

Photos fixées d'avance, sans regarder les résultats du v5 : les 4 photos déjà examinées par la prospection
(out/prospection_jour_1511/universe/plantain_echelle.json : 00191, 00083, 00094, 00195 ; 197, 192, 41 et 13 boîtes).
Chaque ligne : la photo entière réduite au facteur d'échelle (puis à 1 400 px de large pour l'affichage), et un
recadrage de 700 × 700 px à 5 cm/px (35 m de côté) au centre de la photo, à pleine résolution.
Couleurs : boîte annotée en jaune ; détection v5 appariée en vert, non appariée (fausse) en rouge ; boîte annotée
sans détection (ratée) : croix magenta.
Sortie : out/jeux_neufs_1511/a2_planche.jpg
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.stdout.reconfigure(encoding="utf-8")  # en mode -I, PYTHONIOENCODING est ignoré
A2 = RACINE / "data/raw/plantain_ghana_m2"
OUT = RACINE / "out/jeux_neufs_1511"
PHOTOS = ["20230131_WN_ADABOKROM_1_Flight_04_00191", "20230131_WN_ADABOKROM_1_Flight_04_00083",
          "20230131_WN_ADABOKROM_1_Flight_04_00094", "20230131_WN_ADABOKROM_1_Flight_04_00195"]
SEUIL, RAYON, LARG, CROP = 0.30, 20, 1400, 700
Image.MAX_IMAGE_PIXELS = 60_000_000


def apparier(det, ref):
    ok_d, ok_r = np.zeros(len(det), bool), np.zeros(len(ref), bool)
    if len(det) and len(ref):
        d = cdist(det, ref)
        li, co = linear_sum_assignment(np.where(d <= RAYON, d, 1e6))
        m = d[li, co] <= RAYON
        ok_d[li[m]] = True; ok_r[co[m]] = True
    return ok_d, ok_r


def dessiner(img, boites, det, ok_d, ok_r, s, x0=0, y0=0, ep=2):
    dr = ImageDraw.Draw(img)
    for (cx, cy, w, h), ok in zip(boites, ok_r):
        x, y = (cx - x0) * s, (cy - y0) * s
        dr.rectangle([x - w * s / 2, y - h * s / 2, x + w * s / 2, y + h * s / 2], outline=(255, 230, 0), width=ep)
        if not ok:
            r = 6
            dr.line([x - r, y - r, x + r, y + r], fill=(255, 0, 255), width=ep + 1)
            dr.line([x - r, y + r, x + r, y - r], fill=(255, 0, 255), width=ep + 1)
    for (x, y), ok in zip(det, ok_d):
        x, y = (x - x0) * s, (y - y0) * s
        r = 5 if ok else 6
        dr.ellipse([x - r, y - r, x + r, y + r], outline=(0, 255, 0) if ok else (255, 40, 40), width=ep)


def main():
    f = float(json.loads((OUT / "a2_echelle.json").read_text(encoding="utf-8"))["facteur"])
    dets = np.load(OUT / "a2_v5/detections.npz")
    lignes = []
    for nom in PHOTOS:
        with Image.open(A2 / "images" / f"{nom}.JPG") as im:
            im = im.convert("RGB")
            red = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
        b = pd.read_csv(A2 / "annotations" / f"{nom}.csv").to_numpy(float) * f      # cx, cy, l, h à 5 cm/px
        d = dets[nom]
        det = d[d[:, 2] >= SEUIL, :2]
        ok_d, ok_r = apparier(det, b[:, :2])
        s = LARG / red.width
        vue = red.resize((LARG, round(red.height * s)), Image.LANCZOS)
        dessiner(vue, b, det, ok_d, ok_r, s, ep=2)
        cx, cy = red.width // 2, red.height // 2
        x0, y0 = cx - CROP // 2, cy - CROP // 2
        crop = red.crop((x0, y0, x0 + CROP, y0 + CROP))
        dessiner(crop, b, det, ok_d, ok_r, 1.0, x0, y0, ep=2)
        ligne = Image.new("RGB", (LARG + CROP + 30, max(vue.height, CROP) + 40), (25, 25, 25))
        ligne.paste(vue, (0, 40)); ligne.paste(crop, (LARG + 30, 40))
        dr = ImageDraw.Draw(ligne)
        dr.rectangle([x0 * s, 40 + y0 * s, (x0 + CROP) * s, 40 + (y0 + CROP) * s], outline=(255, 255, 255), width=2)
        vp = int(ok_d.sum())
        txt = (f"{nom}  facteur {f}  annotés {len(b)}  détectés {len(det)}  appariés {vp}  "
               f"faux {len(det) - vp}  ratés {len(b) - vp}   | droite : centre, 700 px = 35 m")
        try:
            police = ImageFont.truetype("arial.ttf", 22)
        except OSError:
            police = ImageFont.load_default()
        dr.text((8, 8), txt, fill=(255, 255, 255), font=police)
        lignes.append(ligne)
    H = sum(l.height for l in lignes)
    pl = Image.new("RGB", (lignes[0].width, H), (25, 25, 25))
    y = 0
    for l in lignes:
        pl.paste(l, (0, y)); y += l.height
    pl.save(OUT / "a2_planche.jpg", quality=88)
    print(OUT / "a2_planche.jpg", pl.size)


if __name__ == "__main__":
    main()
