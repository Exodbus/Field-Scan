#!/usr/bin/env python3
"""Planches de contrôle des annotations Roboflow (boîtes dessinées sur les images), par groupe du découpage.

But : juger à l'œil si les annotations d'un groupe sont complètes (bananiers oubliés, boîtes en trop) avant de
figer le découpage. Contrôle des données, sans aucun modèle.

Couleurs : bananier en magenta, cacaoyer en cyan, autre classe en jaune. Une planche par groupe, images tirées
au hasard (graine fixe) ; avec --grand, une image par fichier, en grand.

Exemple :
    python scripts/planche_annotations_roboflow.py --groupes segmento_est dji --n 9
"""
import argparse
import io
import json
import random
import zipfile
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw

COULEURS = {"Banana": (255, 43, 214), "Banana-plant": (255, 43, 214), "Cacao": (0, 229, 255)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", default="data/roboflow/plants_bana_originaux.zip")
    ap.add_argument("--decoupage", default="data/drone/decoupage_comptage/decoupage.csv")
    ap.add_argument("--groupes", nargs="+", required=True)
    ap.add_argument("--n", type=int, default=9, help="images par planche")
    ap.add_argument("--cote", type=int, default=700, help="largeur de chaque image dans la planche (pixels)")
    ap.add_argument("--grand", action="store_true", help="une image par fichier, largeur 1 800 pixels")
    ap.add_argument("--graine", type=int, default=2026)
    ap.add_argument("--out", default="out/controle_annotations")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    z = zipfile.ZipFile(args.zip)
    boites, cats = {}, {}
    for part in ["train", "valid", "test"]:
        d = json.loads(z.read(f"{part}/_annotations.coco.json"))
        cat = {c["id"]: c["name"] for c in d["categories"]}
        ids = {im["id"]: f"{part}/{im['file_name']}" for im in d["images"]}
        for im in d["images"]:
            boites.setdefault(ids[im["id"]], [])
        for a in d["annotations"]:
            boites[ids[a["image_id"]]].append((cat[a["category_id"]], a["bbox"]))
    dec = pd.read_csv(args.decoupage)
    for g in args.groupes:
        lignes = dec[(dec.groupe == g) & (dec.source == "plants_bana")]
        if lignes.empty:
            print(f"{g} : aucune image")
            continue
        noms = sorted(lignes.image)
        random.Random(args.graine).shuffle(noms)
        noms = noms[:args.n]
        cote = 1800 if args.grand else args.cote
        vignettes = []
        for nom in noms:
            img = Image.open(io.BytesIO(z.read(nom))).convert("RGB")
            f = cote / img.width
            img = img.resize((cote, round(img.height * f)))
            dessin = ImageDraw.Draw(img)
            ep = 2 if cote < 1000 else 3
            for c, (x, y, w, h) in boites[nom]:
                dessin.rectangle([x * f, y * f, (x + w) * f, (y + h) * f], outline=COULEURS.get(c, (255, 230, 0)), width=ep)
            n_ban = sum(c in ("Banana", "Banana-plant") for c, _ in boites[nom])
            dessin.rectangle([0, 0, cote, 22], fill=(0, 0, 0))
            dessin.text((5, 5), f"{Path(nom).name[:70]}  |  {n_ban} bananiers, {len(boites[nom]) - n_ban} autres", fill=(255, 255, 255))
            vignettes.append(img)
        if args.grand:
            for k, v in enumerate(vignettes):
                v.save(out / f"{g}_{k:02d}.jpg", quality=88)
        else:
            col = 3
            lig = (len(vignettes) + col - 1) // col
            haut = max(v.height for v in vignettes)
            planche = Image.new("RGB", (col * cote + (col - 1) * 6, lig * haut + (lig - 1) * 6), "white")
            for k, v in enumerate(vignettes):
                planche.paste(v, ((k % col) * (cote + 6), (k // col) * (haut + 6)))
            planche.save(out / f"{g}.jpg", quality=88)
        print(f"{g} : {len(vignettes)} images sur {len(lignes)} -> {out}")


if __name__ == "__main__":
    main()
