#!/usr/bin/env python3
"""Allège un point de contrôle DeepForest : ne garde que les poids du réseau (state_dict).

Un point de contrôle d'entraînement contient aussi l'état de l'optimiseur (inutile en production, et
d'autant plus gros que le squelette a été dégelé). La chaîne (fieldscan.drone.Detecteur) ne lit que les poids.
Le script vérifie que le fichier allégé donne exactement les mêmes poids que l'original.

Exemple :
    python scripts/alleger_modele.py modeles/bananiers_deepforest_dense_v2.ckpt
    (écrit modeles/bananiers_deepforest_dense_v2_leger.ckpt)
"""
import argparse
from pathlib import Path

import torch


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entree")
    ap.add_argument("--sortie", default=None, help="par défaut : <nom>_leger.ckpt à côté de l'entrée")
    args = ap.parse_args(argv)
    entree = Path(args.entree)
    sortie = Path(args.sortie) if args.sortie else entree.with_name(entree.stem + "_leger.ckpt")
    point = torch.load(entree, map_location="cpu", weights_only=False)
    etat = point.get("state_dict", point)
    poids = {k: v for k, v in etat.items() if k.startswith("model.")}
    torch.save({"state_dict": poids, "origine": entree.name}, sortie)
    relu = torch.load(sortie, map_location="cpu", weights_only=False)["state_dict"]
    assert relu.keys() == poids.keys() and all(torch.equal(relu[k], poids[k]) for k in poids), "poids différents"
    print(f"{entree.name} : {entree.stat().st_size / 1e6:.0f} Mo -> {sortie.name} : {sortie.stat().st_size / 1e6:.0f} Mo "
          f"({len(poids)} tenseurs, identiques à l'original)")


if __name__ == "__main__":
    main()
