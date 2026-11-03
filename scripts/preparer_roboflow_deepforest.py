#!/usr/bin/env python3
"""Convertit les jeux Roboflow (COCO) en tuiles DeepForest à l'échelle de ReforesTree (10 cm par pixel).

Mise à l'échelle : facteur = boite_cible / taille médiane des couronnes du jeu (30 px = la taille médiane des
bananiers d'entraînement de ReforesTree à 10 cm). Pour l'ENTRAÎNEMENT seulement, chaque image est en plus
multipliée par un facteur tiré au hasard entre --echelle-min et --echelle-max (le détecteur doit supporter des
couronnes plus ou moins grosses ; graine fixe). Une image plus petite que la tuile est placée dans un cadre noir
de 400 px (même échelle interne qu'en production) ; une image légèrement plus grande (jusqu'à 1,2 x) est ramenée
à 400 px ; au-delà, elle est découpée en tuiles qui se recouvrent (boîtes gardées si au moins 50 % à l'intérieur).

Rôles (fixés à l'avance) :
  - Plants-bana, toutes parties : entraînement (toutes les images, ou un tirage avec --n-plants-bana ; même région que Count banana
    plants, donc jamais utilisé pour évaluer) ; seules les boîtes « Banana » sont gardées (les cacaoyers non
    annotés deviennent des exemples négatifs) ;
  - Count banana plants : train -> entraînement, valid -> choix de l'époque (val_dense), test -> test (test_dense).

Sorties dans --out : images/*.png, train_roboflow.csv, val_dense.csv, test_dense.csv, parametres.json, et
<nom du dossier>.zip (chemins en « / », prêt pour Kaggle).

Exemple :
    python scripts/preparer_roboflow_deepforest.py
"""
import argparse
import io
import json
import random
import zipfile
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd
from PIL import Image

ETIQUETTE = "Banana"


def lire_coco(zip_):
    z = zipfile.ZipFile(zip_)
    images = []
    for a in [n for n in z.namelist() if n.endswith("_annotations.coco.json")]:
        partie = PurePosixPath(a).parent.name
        coco = json.loads(z.read(a))
        cats = {c["id"]: c["name"] for c in coco["categories"]}
        par_image = {}
        for an in coco["annotations"]:
            if "banana" in cats.get(an["category_id"], "").lower():
                par_image.setdefault(an["image_id"], []).append(an["bbox"])
        base = str(PurePosixPath(a).parent)
        for im in coco["images"]:
            images.append(dict(partie=partie, membre=f"{base}/{im['file_name']}",
                               boites=np.array(par_image.get(im["id"], []), float).reshape(-1, 4)))
    return z, images


def tuiles(img, boites, taille, recouvrement=0.2, part_min=0.5):
    """Découpe (ou encadre) une image déjà à l'échelle ; renvoie [(image_tuile, boites_xyxy)]."""
    l, h = img.size
    if l <= taille and h <= taille:
        cadre = Image.new("RGB", (taille, taille), (0, 0, 0))
        cadre.paste(img, (0, 0))
        return [(cadre, boites)]
    pas = int(taille * (1 - recouvrement))
    pos = lambda n: sorted(set(list(range(0, max(n - taille, 0) + 1, pas)) + [max(n - taille, 0)]))
    sorties = []
    for y0 in pos(h):
        for x0 in pos(l):
            t = Image.new("RGB", (taille, taille), (0, 0, 0))
            t.paste(img.crop((x0, y0, min(x0 + taille, l), min(y0 + taille, h))), (0, 0))
            b = boites.copy()
            if len(b):
                b[:, [0, 2]] -= x0; b[:, [1, 3]] -= y0
                aire = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
                c = np.c_[np.clip(b[:, 0], 0, taille), np.clip(b[:, 1], 0, taille), np.clip(b[:, 2], 0, taille), np.clip(b[:, 3], 0, taille)]
                garde = ((c[:, 2] - c[:, 0]) * (c[:, 3] - c[:, 1])) >= part_min * aire
                b = c[garde]
            sorties.append((t, b))
    return sorties


def convertir(z, images, prefixe, facteur, role_par_partie, args, rng, dossier, lignes):
    for k, im in enumerate(images):
        role = role_par_partie.get(im["partie"])
        if role is None:
            continue
        f = facteur * (rng.uniform(args.echelle_min, args.echelle_max) if role == "train" else 1.0)
        img = Image.open(io.BytesIO(z.read(im["membre"]))).convert("RGB")
        l, h = max(1, round(img.width * f)), max(1, round(img.height * f))
        if args.taille < max(l, h) <= args.taille * 1.2:          # légèrement trop grande : ramenée à la tuile
            f *= args.taille / max(l, h)
            l, h = max(1, round(img.width * f)), max(1, round(img.height * f))
        img = img.resize((l, h), Image.LANCZOS)
        b = im["boites"].copy()
        xyxy = np.c_[b[:, 0], b[:, 1], b[:, 0] + b[:, 2], b[:, 1] + b[:, 3]] * f if len(b) else np.empty((0, 4))
        for j, (t, bb) in enumerate(tuiles(img, xyxy, args.taille)):
            nom = f"{prefixe}_{role}_{k:05d}_{j}.{args.format}"
            if args.format == "jpg":
                t.save(dossier / "images" / nom, quality=95)
            else:
                t.save(dossier / "images" / nom)
            if len(bb) == 0:
                lignes.append(dict(image_path=nom, xmin=0, ymin=0, xmax=0, ymax=0, label=ETIQUETTE, split=role))
            for x0, y0, x1, y1 in bb:
                if x1 - x0 >= 2 and y1 - y0 >= 2:
                    lignes.append(dict(image_path=nom, xmin=int(round(x0)), ymin=int(round(y0)), xmax=int(round(x1)),
                                       ymax=int(round(y1)), label=ETIQUETTE, split=role))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plants-bana", default="data/roboflow/plants_bana_originaux.zip")
    ap.add_argument("--count", default="data/roboflow/count_banana_plants.zip")
    ap.add_argument("--out", default="data/drone/roboflow_deepforest_v2")
    ap.add_argument("--boite-cible", type=float, default=30.0)
    ap.add_argument("--taille", type=int, default=400)
    ap.add_argument("--echelle-min", type=float, default=0.75)
    ap.add_argument("--echelle-max", type=float, default=1.4)
    ap.add_argument("--n-plants-bana", type=int, default=0, help="tirage d'images de Plants-bana (0 = toutes)")
    ap.add_argument("--graine", type=int, default=2026)
    ap.add_argument("--format", choices=["png", "jpg"], default="png", help="format des tuiles (jpg : 4 fois plus léger)")
    args = ap.parse_args(argv)
    dossier = Path(args.out)
    (dossier / "images").mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.graine)
    lignes, parametres = [], dict(vars(args))

    for nom, chemin, prefixe, roles in (("plants_bana", args.plants_bana, "pb", {"train": "train", "valid": "train", "test": "train"}),
                                        ("count_banana_plants", args.count, "cb", {"train": "train", "valid": "val_dense", "test": "test_dense"})):
        z, images = lire_coco(chemin)
        tailles = np.concatenate([(i["boites"][:, 2] + i["boites"][:, 3]) / 2 for i in images if len(i["boites"])])
        facteur = args.boite_cible / float(np.median(tailles))
        if nom == "plants_bana" and 0 < args.n_plants_bana < len(images):
            images = random.Random(args.graine).sample(images, args.n_plants_bana)
        parametres[f"facteur_{nom}"] = round(facteur, 4)
        parametres[f"images_{nom}"] = len(images)
        print(f"{nom} : {len(images)} images, couronne médiane {np.median(tailles):.0f} px -> facteur {facteur:.3f}")
        convertir(z, images, prefixe, facteur, roles, args, rng, dossier, lignes)

    df = pd.DataFrame(lignes)
    fichiers = {"train": "train_roboflow.csv", "val_dense": "val_dense.csv", "test_dense": "test_dense.csv"}
    for role, fichier in fichiers.items():
        s = df[df.split == role].drop(columns="split")
        s.to_csv(dossier / fichier, index=False)
        boites = s[s.xmax > 0]
        print(f"  {fichier} : {s.image_path.nunique()} tuiles, {len(boites)} bananiers, "
              f"côté médian {((boites.xmax - boites.xmin)).median():.0f} px")
    (dossier / "parametres.json").write_text(json.dumps(parametres, indent=2, ensure_ascii=False), encoding="utf-8")
    nom_zip = f"{dossier.name}.zip"
    with zipfile.ZipFile(dossier / nom_zip, "w", zipfile.ZIP_STORED) as zz:
        for f in list(fichiers.values()) + ["parametres.json"]:
            zz.write(dossier / f, f)
        for f in sorted((dossier / "images").iterdir()):
            zz.write(f, f"images/{f.name}")
    print(f"\nArchive pour Kaggle : {dossier / nom_zip} ({(dossier / nom_zip).stat().st_size / 1e6:.0f} Mo)")


if __name__ == "__main__":
    main()
