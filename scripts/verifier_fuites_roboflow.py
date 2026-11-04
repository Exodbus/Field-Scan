#!/usr/bin/env python3
"""Fuites entre un jeu Roboflow candidat (pour un test) et les jeux d'entraînement déjà utilisés.

Chaque image est réduite à une empreinte (dHash 8 x 8 en niveaux de gris, 64 bits) ; pour une image du
candidat, on calcule l'empreinte de ses 8 orientations (rotations et miroirs), et on cherche l'image
d'entraînement la plus proche (distance de Hamming). Sous --seuil bits, l'image est déclarée « doublon
probable » : elle ne doit pas servir de test. Une planche montre les paires pour vérification à l'œil.
Limite : un recadrage ou un changement d'échelle fort peut échapper à l'empreinte ; la planche aide à juger.

Sorties dans --out : fuites.csv (une ligne par image candidate), planche.jpg, et propres.txt (images à garder).

Exemple :
    python scripts/verifier_fuites_roboflow.py data/roboflow/banana_drone.zip \\
        --reference data/roboflow/plants_bana_originaux.zip data/roboflow/count_banana_plants.zip
"""
import argparse
import io
import zipfile
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageOps


def empreinte(im):
    g = np.asarray(ImageOps.grayscale(im).resize((9, 8), Image.BILINEAR), dtype="float32")
    return np.packbits((g[:, 1:] > g[:, :-1]).ravel())


def orientations(im):
    for k in range(4):
        r = im.rotate(90 * k, expand=True)
        yield r
        yield ImageOps.mirror(r)


def images_du_zip(chemin):
    z = zipfile.ZipFile(chemin)
    for n in z.namelist():
        if n.lower().endswith((".jpg", ".jpeg", ".png")):
            yield z, n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidat")
    ap.add_argument("--reference", nargs="+", required=True, help="zips des jeux déjà utilisés")
    ap.add_argument("--seuil", type=int, default=8, help="distance de Hamming maximale pour un doublon probable (sur 64)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    out = Path(args.out or f"out/fuites_roboflow/{Path(args.candidat).stem}")
    out.mkdir(parents=True, exist_ok=True)

    refs, noms_ref = [], []
    for zp in args.reference:
        for z, n in images_du_zip(zp):
            refs.append(empreinte(Image.open(io.BytesIO(z.read(n))).convert("RGB")))
            noms_ref.append((zp, n))
    R = np.unpackbits(np.stack(refs), axis=1).astype(bool)
    print(f"{len(refs)} images de référence")

    lignes, paires = [], []
    for z, n in images_du_zip(args.candidat):
        im = Image.open(io.BytesIO(z.read(n))).convert("RGB")
        best, idx = 65, -1
        for o in orientations(im):
            e = np.unpackbits(empreinte(o)).astype(bool)
            d = (R != e).sum(1)
            j = int(d.argmin())
            if d[j] < best:
                best, idx = int(d[j]), j
        doublon = best <= args.seuil
        lignes.append(dict(image=n, distance_min=best, doublon_probable=doublon,
                           plus_proche=f"{Path(noms_ref[idx][0]).name}:{noms_ref[idx][1]}"))
        if doublon and len(paires) < 16:
            zr = zipfile.ZipFile(noms_ref[idx][0])
            paires.append((im, Image.open(io.BytesIO(zr.read(noms_ref[idx][1]))).convert("RGB"), best))
    df = pd.DataFrame(lignes).sort_values("distance_min")
    df.to_csv(out / "fuites.csv", index=False)
    propres = df[~df.doublon_probable].image.tolist()
    (out / "propres.txt").write_text("\n".join(propres), encoding="utf-8")
    print(f"{len(df)} images candidates : {int(df.doublon_probable.sum())} doublons probables (≤ {args.seuil} bits), "
          f"{len(propres)} propres ; distance médiane {df.distance_min.median():.0f} bits")
    if paires:
        c = 220
        planche = Image.new("RGB", (2 * c + 10, len(paires) * (c + 16)), "white")
        d = ImageDraw.Draw(planche)
        for k, (a, b, dist) in enumerate(paires):
            for j, im in enumerate((a, b)):
                im = im.copy(); im.thumbnail((c, c))
                planche.paste(im, (j * (c + 10), k * (c + 16)))
            d.text((2, k * (c + 16) + c + 2), f"candidat | entraînement (distance {dist} bits)", fill="black")
        planche.save(out / "planche.jpg", quality=88)
        print(f"Planche des doublons probables : {out / 'planche.jpg'}")


if __name__ == "__main__":
    main()
