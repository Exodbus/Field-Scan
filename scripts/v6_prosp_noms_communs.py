#!/usr/bin/env python3
"""Vérifie si les images d'un jeu neuf qui portent le même nom d'origine qu'une image de référence (ex. DJI_0779)
sont les mêmes photos : chaque image de référence est étirée à la taille de l'image neuve (comme le fait le
redimensionnement « Stretch » de Roboflow), puis on mesure l'écart moyen des pixels (niveaux de gris 64 x 64,
8 symétries) et on fait une planche côte à côte. Aucun modèle.

Exemple :
    python scripts/v6_prosp_noms_communs.py data/roboflow_nuit_1112/comptage/banana_trees_kp/banana_trees_kp.zip \
        data/roboflow/banavista.zip --out data/roboflow_nuit_1112/comptage/_fuites/noms_communs_banana_trees_kp
"""
import argparse
import io
import re
import zipfile
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageOps

MOTIF = re.compile(r"^(.*?)_(?:jpg|jpeg|png)\.rf\.", re.IGNORECASE)
Image.MAX_IMAGE_PIXELS = None


def origine(nom):
    b = PurePosixPath(nom).name
    m = MOTIF.match(b)
    return (m.group(1) if m else b.rsplit(".", 1)[0]).lower()


def petit(octets):
    im = Image.open(io.BytesIO(octets))
    if im.format == "JPEG":
        im.draft("RGB", (256, 256))
    return im.convert("RGB")


def vec(im):
    a = np.asarray(ImageOps.grayscale(im).resize((64, 64), Image.BILINEAR), dtype="float32")
    return (a - a.mean()) / (a.std() + 1e-6)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("neuf")
    ap.add_argument("reference")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    zr = zipfile.ZipFile(args.reference)
    ref = {}
    for n in zr.namelist():
        if n.lower().endswith((".jpg", ".jpeg", ".png")):
            ref.setdefault(origine(n), n)
    zn = zipfile.ZipFile(args.neuf)
    lignes, paires = [], []
    for n in sorted(zn.namelist()):
        if not n.lower().endswith((".jpg", ".jpeg", ".png")) or origine(n) not in ref:
            continue
        a = petit(zn.read(n)); b = petit(zr.read(ref[origine(n)]))
        va = vec(a)
        best = 9.0
        for k in range(4):
            r = b.rotate(90 * k, expand=True)
            for m in (r, ImageOps.mirror(r)):
                best = min(best, float(np.abs(va - vec(m.resize(a.size))).mean()))   # écart réduit, 0 = identique
        lignes.append(dict(image=n, origine=origine(n), reference=ref[origine(n)], ecart=round(best, 3)))
        if len(paires) < 12:
            paires.append((a, b, best, origine(n)))
    df = pd.DataFrame(lignes).sort_values("ecart")
    df.to_csv(out / "noms_communs.csv", index=False)
    print(f"{len(df)} noms communs ; écart réduit : min {df.ecart.min():.3f}, médiane {df.ecart.median():.3f}, "
          f"max {df.ecart.max():.3f} (0 = même photo ; deux photos sans rapport donnent environ 0,8 à 1,1)")
    print(df.head(8).to_string(index=False))
    c = 260
    pl = Image.new("RGB", (2 * c + 10, len(paires) * (c + 16)), "white"); d = ImageDraw.Draw(pl)
    for k, (a, b, e, o) in enumerate(paires):
        for j, im in enumerate((a, b)):
            im = im.copy(); im.thumbnail((c, c)); pl.paste(im, (j * (c + 10), k * (c + 16)))
        d.text((2, k * (c + 16) + c + 2), f"{o} : jeu neuf | référence (écart {e:.2f})", fill="black")
    pl.save(out / "planche.jpg", quality=85)


if __name__ == "__main__":
    main()
