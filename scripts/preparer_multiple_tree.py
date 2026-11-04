#!/usr/bin/env python3
"""Prépare Multiple tree detection (Roboflow, CC BY 4.0) pour le détecteur de centres, à 5 cm par pixel.

Seules les boîtes de bananiers sont gardées. Les images sans bananier (palmiers à huile, cocotiers) sont
gardées aussi, avec zéro pied : ce sont des exemples NÉGATIFS (le modèle apprend qu'une couronne de palmier
n'est pas un bananier) et, en validation et en test, elles mesurent les fausses détections sur les palmiers.

Rôles (les parties du jeu ne partagent aucune image d'origine) : train -> entraînement (tirage de --n-train
images, graine fixe, variation d'échelle comme les autres jeux), valid -> val_mt (choix), test -> test_mt.
Mise à l'échelle : la couronne médiane de bananier ramenée à --boite-cible pixels (60 = 5 cm).

Sorties dans --out : images/, train_mt.csv, val_mt.csv, test_mt.csv (une ligne vide par tuile sans bananier),
parametres.json et <nom du dossier>.zip pour Kaggle.

Exemple :
    python scripts/preparer_multiple_tree.py data/roboflow/multiple_tree.zip
"""
import argparse
import json
import random
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preparer_roboflow_deepforest import convertir, lire_coco  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip")
    ap.add_argument("--out", default="data/drone/multiple_tree_5cm")
    ap.add_argument("--boite-cible", type=float, default=60.0)
    ap.add_argument("--taille", type=int, default=512)
    ap.add_argument("--n-train", type=int, default=4000, help="images d'entraînement tirées au hasard (0 = toutes)")
    ap.add_argument("--echelle-min", type=float, default=0.75)
    ap.add_argument("--echelle-max", type=float, default=1.4)
    ap.add_argument("--graine", type=int, default=2026)
    args = ap.parse_args(argv)
    dossier = Path(args.out)
    (dossier / "images").mkdir(parents=True, exist_ok=True)
    z, images = lire_coco(args.zip)
    tailles = np.concatenate([(i["boites"][:, 2] + i["boites"][:, 3]) / 2 for i in images if len(i["boites"])])
    facteur = args.boite_cible / float(np.median(tailles))
    par_partie = {p: [i for i in images if i["partie"] == p] for p in ("train", "valid", "test")}
    if 0 < args.n_train < len(par_partie["train"]):
        par_partie["train"] = random.Random(args.graine).sample(par_partie["train"], args.n_train)
    reglages = SimpleNamespace(taille=args.taille, echelle_min=args.echelle_min, echelle_max=args.echelle_max, format="jpg")
    rng = random.Random(args.graine)
    lignes = []
    # « train » garde la variation d'échelle de convertir() ; valid et test sont à l'échelle exacte
    for partie, role in (("train", "train"), ("valid", "val_mt"), ("test", "test_mt")):
        convertir(z, par_partie[partie], "mt", facteur, {partie: role}, reglages, rng, dossier, lignes)
    df = pd.DataFrame(lignes)
    df["split"] = df["split"].replace({"train": "train_mt"})
    print(f"Couronne médiane de bananier {np.median(tailles):.0f} px -> facteur {facteur:.3f}")
    fichiers = {"train_mt": "train_mt.csv", "val_mt": "val_mt.csv", "test_mt": "test_mt.csv"}
    for role, fichier in fichiers.items():
        s = df[df.split == role].drop(columns="split")
        s.to_csv(dossier / fichier, index=False)
        avec = s[s.xmax > 0].image_path.nunique()
        print(f"  {fichier} : {s.image_path.nunique()} tuiles ({avec} avec bananiers, {s.image_path.nunique() - avec} sans), "
              f"{int((s.xmax > 0).sum())} bananiers")
    (dossier / "parametres.json").write_text(json.dumps(dict(vars(args), facteur=round(facteur, 4)), indent=2, ensure_ascii=False),
                                             encoding="utf-8")
    nom_zip = f"{dossier.name}.zip"
    with zipfile.ZipFile(dossier / nom_zip, "w", zipfile.ZIP_STORED) as zz:
        for f in list(fichiers.values()) + ["parametres.json"]:
            zz.write(dossier / f, f)
        for f in sorted((dossier / "images").iterdir()):
            zz.write(f, f"images/{f.name}")
    print(f"Archive pour Kaggle : {dossier / nom_zip} ({(dossier / nom_zip).stat().st_size / 1e6:.0f} Mo)")


if __name__ == "__main__":
    main()
