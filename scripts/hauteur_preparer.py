#!/usr/bin/env python3
"""Essai « hauteur » (docs/protocole_hauteur_banavista.md) : extraction de la ligne choisie.

Ligne : la plus longue suite de numéros DJI consécutifs de la session A de banavista, parmi les photos
d'ENTRAÎNEMENT du v5 (colonne `partie` de data/drone/decoupage_comptage_v5/decoupage.csv). Les dossiers
Roboflow (train/valid/test) ne servent qu'à retrouver le fichier, jamais au découpage.

Sorties (out/hauteur/) :
- odm/ligne_a/images/DJI_0xxx.JPG : photos extraites telles quelles ;
- boites_ligne_a.csv : boîtes COCO `Bananas` (et `Others`, marquées) de ces photos, en pixels de la photo ;
- ligne_a.json : liste, moitiés, MD5, nombre de champs EXIF.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/hauteur_preparer.py
"""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

DECOUPAGE = RACINE / "data/drone/decoupage_comptage_v5/decoupage.csv"
ZIP = RACINE / "data/roboflow/banavista.zip"
OUT = RACINE / "out/hauteur"


def plus_longue_suite(nums):
    suites, cur = [], [nums[0]]
    for n in nums[1:]:
        if n == cur[-1] + 1:
            cur.append(n)
        else:
            suites.append(cur)
            cur = [n]
    suites.append(cur)
    return max(suites, key=len)


def main():
    d = pd.read_csv(DECOUPAGE)
    a = d[(d.source == "banavista") & (d.groupe == "bv_session_a") & (d.partie == "train")].copy()
    a["num"] = a.photo.str.split("_").str[-1].astype(int)
    suite = plus_longue_suite(sorted(a.num))
    ligne = a[a.num.isin(suite)].sort_values("num")
    # garde-fou : aucune photo hors entraînement
    assert (ligne.partie == "train").all() and len(ligne) == len(suite)
    print(f"ligne : DJI_{suite[0]:04d} à DJI_{suite[-1]:04d}, {len(suite)} photos")

    dossier = OUT / "odm/ligne_a/images"
    dossier.mkdir(parents=True, exist_ok=True)
    z = zipfile.ZipFile(ZIP)
    cocos = {}
    lignes_boites, infos = [], []
    for _, r in ligne.iterrows():
        nom = f"DJI_{r.num:04d}.JPG"
        donnees = z.read(r.image)
        (dossier / nom).write_bytes(donnees)
        with Image.open(dossier / nom) as im:
            taille, nexif = im.size, len(im.getexif())
        part = r.image.split("/")[0]
        if part not in cocos:
            cocos[part] = json.loads(z.read(f"{part}/_annotations.coco.json"))
        c = cocos[part]
        cats = {k["id"]: k["name"] for k in c["categories"]}
        img = [i for i in c["images"] if i["file_name"] == r.image.split("/")[1]]
        assert len(img) == 1, r.image
        iid = img[0]["id"]
        for an in c["annotations"]:
            if an["image_id"] == iid:
                x, y, w, h = an["bbox"]
                lignes_boites.append(dict(photo=nom, num=r.num, classe=cats[an["category_id"]], x=x, y=y, w=w, h=h))
        infos.append(dict(photo=nom, num=int(r.num), source_zip=r.image, md5=hashlib.md5(donnees).hexdigest(),
                          largeur=taille[0], hauteur=taille[1], champs_exif=nexif))
    B = pd.DataFrame(lignes_boites)
    B.to_csv(OUT / "boites_ligne_a.csv", index=False)
    moitie = len(suite) // 2
    res = dict(regle="plus longue suite de numéros DJI consécutifs, session A, entraînement v5",
               premiere=suite[0], derniere=suite[-1], n=len(suite),
               reglage=[f"DJI_{n:04d}.JPG" for n in suite[:moitie]],
               mesure=[f"DJI_{n:04d}.JPG" for n in suite[moitie:]], photos=infos)
    (OUT / "ligne_a.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("boîtes :", B.classe.value_counts().to_dict())
    print("tailles :", {(i["largeur"], i["hauteur"]) for i in infos}, "; champs EXIF max :", max(i["champs_exif"] for i in infos))
    print("MD5 distincts :", len({i["md5"] for i in infos}), "/", len(infos))


if __name__ == "__main__":
    main()
