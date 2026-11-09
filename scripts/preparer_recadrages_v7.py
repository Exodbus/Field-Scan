#!/usr/bin/env python3
"""Recadrages ROAMER de la v7 (docs/protocole_maladies_v7.md, section 1), sans modèle.

Seules les images listées dans dev_loin (out/maladies/equipe/evaluateur/decoupage_loin/dev_loin.csv) des zips
roamer_feuilles_fusarium_leaf et roamer_feuilles_moko_leaf sont lues ; toute image dont la clé color_frame_<hex>
apparaît dans val_loin est écartée (double sécurité). Chaque polygone « positive » ou « negative » donne un
recadrage : boîte élargie de 10 %, gardé s'il fait au moins 32 px de côté. Classes : fusarium_leaf positive ->
fusarium, moko_leaf positive -> autre_maladie, negative -> saine.

Sorties dans --out : images/, recadrages.csv (image, classe, jeu, photo), exclusions_roamer_val_loin.csv (photo).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/preparer_recadrages_v7.py
"""
import argparse
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
ZIPS = {"roamer_feuilles_fusarium_leaf": "fusarium", "roamer_feuilles_moko_leaf": "autre_maladie"}
MARGE, COTE_MIN = 0.10, 32


def cle(nom):
    n = Path(str(nom).replace("\\", "/")).name
    for coupe in ("_png.rf.", "_jpg.rf.", "_jpeg.rf.", ".rf."):
        if coupe in n:
            return n.split(coupe)[0]
    return n.rsplit(".", 1)[0]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/roamer_recadrages_v7")
    args = ap.parse_args(argv)
    out = RACINE / args.out
    if (out / "recadrages.csv").exists():
        sys.exit("recadrages déjà préparés : rien n'est réécrit")
    dec = RACINE / "out/maladies/equipe/evaluateur/decoupage_loin"
    dev, val = pd.read_csv(dec / "dev_loin.csv"), pd.read_csv(dec / "val_loin.csv")
    cles_val = {cle(x) for x in val.origine} | {cle(x) for x in val.image}
    (out / "images").mkdir(parents=True, exist_ok=True)
    lignes, ecartees = [], 0
    for nom_zip, classe_pos in ZIPS.items():
        autorisees = set(dev[dev.zip.eq(nom_zip)].image)
        with zipfile.ZipFile(RACINE / "data/roboflow_maladies/nouveaux" / f"{nom_zip}.zip") as z:
            for nj in sorted(n for n in z.namelist() if n.endswith("_annotations.coco.json")):
                partie = nj.split("/")[0]
                coco = json.loads(z.read(nj))
                cat = {c["id"]: c["name"] for c in coco["categories"]}
                ims = {i["id"]: i for i in coco["images"]}
                for a in coco["annotations"]:
                    etat = cat[a["category_id"]]
                    if etat not in ("positive", "negative"):
                        continue
                    info = ims[a["image_id"]]
                    chemin = f"{partie}/{info['file_name']}"
                    if chemin not in autorisees:
                        continue
                    photo = cle((info.get("extra") or {}).get("name") or info["file_name"])
                    if photo in cles_val or cle(info["file_name"]) in cles_val:
                        ecartees += 1
                        continue
                    with Image.open(io.BytesIO(z.read(chemin))) as im:
                        im = im.convert("RGB")
                        x, y, w, h = a["bbox"]
                        b = (max(0, x - MARGE * w), max(0, y - MARGE * h),
                             min(im.width, x + w + MARGE * w), min(im.height, y + h + MARGE * h))
                        if b[2] - b[0] < COTE_MIN or b[3] - b[1] < COTE_MIN:
                            continue
                        rel = f"images/{nom_zip}_{partie}_{a['id']:05d}.jpg"
                        im.crop(b).save(out / rel, quality=95)
                    lignes.append(dict(image=rel, classe=classe_pos if etat == "positive" else "saine",
                                       jeu=f"roamer_{nom_zip.split('_')[2]}", photo=photo))
    r = pd.DataFrame(lignes)
    r.to_csv(out / "recadrages.csv", index=False, encoding="utf-8", lineterminator="\n")
    pd.DataFrame(dict(photo=sorted(cles_val))).to_csv(out / "exclusions_roamer_val_loin.csv", index=False,
                                                       encoding="utf-8", lineterminator="\n")
    print(pd.crosstab(r.jeu, r.classe, margins=True).to_string())
    print("photos distinctes :", r.photo.nunique(), "; recadrages écartés (clé dans val_loin) :", ecartees)
    print("SHA-256 recadrages.csv :", hashlib.sha256((out / "recadrages.csv").read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
