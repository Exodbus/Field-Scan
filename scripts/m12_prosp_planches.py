#!/usr/bin/env python3
"""Nuit du 12/11 (D-maladies) : planches de contrôle visuel, 24 photos tirées au hasard (graine 2026) par classe
d'origine, à partir de data/raw/nuit_1112/<jeu>/liste.csv (ou d'un dossier, groupé par sous-dossier ou par préfixe
de nom). Aucun modèle.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_prosp_planches.py <jeu> [<jeu> ...]
"""
import re
import sys
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFile, ImageOps

RACINE = Path(__file__).resolve().parents[1]
NUIT = RACINE / "data/raw/nuit_1112"
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


def planche(chemins, titre, sortie, n=24, c=6, t=200):
    s = pd.Series(chemins)
    s = s.sample(min(n, len(s)), random_state=2026)
    L = (len(s) + c - 1) // c
    pl = Image.new("RGB", (c * t, 24 + L * (t + 16)), "white")
    dr = ImageDraw.Draw(pl)
    dr.text((4, 4), titre, fill="black")
    for i, ch in enumerate(s):
        try:
            im = Image.open(ch)
            im.draft("RGB", (t * 2, t * 2))
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((t, t))
        except Exception:
            im = Image.new("RGB", (t, t), "red")
        x, y = (i % c) * t, 24 + (i // c) * (t + 16)
        pl.paste(im, (x, y))
        dr.text((x + 2, y + t), Path(ch).name[:32], fill="black")
    pl.save(sortie, quality=85)


def main():
    for nom in sys.argv[1:]:
        lst = NUIT / nom / "liste.csv"
        out = NUIT / nom / "planches"; out.mkdir(exist_ok=True)
        if lst.exists():
            d = pd.read_csv(lst)
            groupes = {f"{k}": g.chemin.tolist() for k, g in d.groupby("classe_origine")}
        else:
            fs = [f for f in (NUIT / nom).rglob("*") if f.suffix.lower() in (".jpg", ".jpeg", ".png")
                  and "planches" not in f.parts]
            groupes = {}
            for f in fs:
                k = f.parent.name if f.parent.name != "fichiers" else re.sub(r"[\s_]*\d+$", "", f.stem.lower())
                groupes.setdefault(k, []).append(str(f))
        for k, ch in groupes.items():
            planche(ch, f"{nom} / {k} ({len(ch)} photos)", out / f"planche_{re.sub(r'[^A-Za-z0-9_-]+', '_', k)}.jpg")
            print(nom, k, len(ch))


if __name__ == "__main__":
    main()
