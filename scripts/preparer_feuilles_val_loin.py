#!/usr/bin/env python3
"""Recadrages des feuilles de val_loin pour la mesure « de loin » de la v7 (docs/protocole_maladies_v7.md, section 3),
sans modèle. Même règle que scripts/preparer_recadrages_v7.py (boîte du polygone élargie de 10 %, au moins 32 px),
sur les quatre jeux de feuilles ROAMER, images de val_loin seulement. Étiquette : « positive » -> malade,
« negative » -> saine (et le projet d'origine).

Sorties dans --out : images/, feuilles.csv (image, etat, projet, photo, groupe).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/preparer_feuilles_val_loin.py
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
sys.path.insert(0, str(RACINE / "scripts"))
from preparer_recadrages_v7 import COTE_MIN, MARGE, cle  # noqa: E402

ZIPS = ["roamer_feuilles_fusarium_leaf", "roamer_feuilles_moko_leaf", "roamer_feuilles_healthy_leaf",
        "roamer_feuilles_bunchytop_leaf"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/roamer_val_loin_feuilles")
    ap.add_argument("--partie", choices=["val_loin", "dev_loin"], default="val_loin")
    args = ap.parse_args(argv)
    out = RACINE / args.out
    if (out / "feuilles.csv").exists():
        sys.exit("déjà préparé : rien n'est réécrit")
    val = pd.read_csv(RACINE / f"out/maladies/equipe/evaluateur/decoupage_loin/{args.partie}.csv")
    (out / "images").mkdir(parents=True, exist_ok=True)
    lignes = []
    for nom_zip in ZIPS:
        sel = val[val.zip.eq(nom_zip)]
        groupe = dict(zip(sel.image, sel.groupe))
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
                    if chemin not in groupe:
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
                    lignes.append(dict(image=rel, etat="malade" if etat == "positive" else "saine",
                                       projet=nom_zip.replace("roamer_feuilles_", ""),
                                       photo=cle((info.get("extra") or {}).get("name") or info["file_name"]),
                                       groupe=groupe[chemin]))
    f = pd.DataFrame(lignes)
    f.to_csv(out / "feuilles.csv", index=False, encoding="utf-8", lineterminator="\n")
    print(pd.crosstab(f.projet, f.etat, margins=True).to_string())
    print("photos :", f.photo.nunique(), "; groupes :", f.groupe.nunique())
    print("SHA-256 feuilles.csv :", hashlib.sha256((out / "feuilles.csv").read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
