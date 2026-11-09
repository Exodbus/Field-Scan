#!/usr/bin/env python3
"""Caractéristiques internes de la v2 pour le détecteur de nouveauté (docs/protocole_maladies_melange_nouveaute.md,
section 3). N'affiche aucun score.

Pour chacun des 3 réseaux de la v2, vue d'origine seulement, préparation de la v2 : entrée de la dernière couche
(768 valeurs) et logits. Jeux : ajustement (500 photos par source et classe de l'apprentissage, graine 2026),
tdtu (autre_maladie et black_sigatoka), validation (3 001), bananalsd (897).
Sortie : out/maladies/nouveaute/caracteristiques_<jeu>.npz (car : (3, n, 768), logits : (3, n, 3), chemin, classe).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/extraire_caracteristiques_v2.py
"""
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

RACINE = Path(__file__).resolve().parents[1]
V2 = RACINE / "modeles/maladies_binome/maladies_v2"
sys.path.insert(0, str(V2))
import classifieur  # noqa: E402

SORTIE = RACINE / "out/maladies/nouveaute"
PROTOCOLE = RACINE / "docs/protocole_maladies_melange_nouveaute.md"


def jeux():
    idx = pd.read_csv(RACINE / "data/feuilles/index.csv")
    idx = idx[idx.retenue & idx.chemin.notna()]
    idx["fichier"] = "data/feuilles/" + idx.chemin
    ent = idx[idx.ensemble.eq("entrainement")]
    ajust = ent.groupby(["source", "classe"], group_keys=False).apply(lambda g: g.sample(min(500, len(g)), random_state=2026))
    aj = pd.read_csv(RACINE / "data/feuilles_v3_ajouts/images.csv")
    tdtu = aj[aj.jeu.eq("tdtu") & aj.classe.isin(["autre_maladie", "black_sigatoka"])].copy()
    tdtu["fichier"] = "data/feuilles_v3_ajouts/" + tdtu.image
    val = idx[idx.ensemble.eq("validation")]
    bl = idx[idx.ensemble.eq("test") & idx.source.eq("bananalsd")]
    return {"ajustement": ajust, "tdtu": tdtu, "validation": val, "bananalsd": bl}


@torch.no_grad()
def extraire(reseaux, fichiers, lot=32):
    car, log = [[] for _ in reseaux], [[] for _ in reseaux]
    for i in range(0, len(fichiers), lot):
        x = torch.stack([classifieur.PREPARATION(classifieur.preparer(RACINE / f)) for f in fichiers[i:i + lot]])
        for k, r in enumerate(reseaux):
            z = r.classifier[1](r.classifier[0](r.avgpool(r.features(x))))  # LayerNorm2d puis Flatten : (n, 768)
            car[k].append(z.numpy().astype(np.float32)); log[k].append(r.classifier[2](z).numpy().astype(np.float32))
        if (i // lot) % 20 == 0:
            print(f"  {i + len(fichiers[i:i + lot])}/{len(fichiers)}", flush=True)
    return np.stack([np.concatenate(c) for c in car]), np.stack([np.concatenate(l) for l in log])


def main():
    torch.set_num_threads(8)
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / "protocole_sha256.txt").write_text(hashlib.sha256(PROTOCOLE.read_bytes()).hexdigest() + "\n", encoding="utf-8")
    reseaux, _ = classifieur.charger(V2 / "poids")
    for nom, df in jeux().items():
        f = SORTIE / f"caracteristiques_{nom}.npz"
        if f.exists():
            print(nom, "déjà fait"); continue
        print(nom, len(df), "photos", flush=True)
        car, log = extraire(reseaux, list(df.fichier))
        np.savez_compressed(f, car=car, logits=log, chemin=np.array(df.fichier), classe=np.array(df.classe),
                            source=np.array(df.get("source", df.get("jeu"))))
    print("fini")


if __name__ == "__main__":
    main()
