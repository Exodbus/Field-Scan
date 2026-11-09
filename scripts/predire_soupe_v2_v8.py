#!/usr/bin/env python3
"""Probabilités de la soupe v2 + v8 (docs/protocole_maladies_melange_nouveaute.md, section 2, candidat A2).
N'affiche aucun score.

Réseau k de la soupe = moyenne, paramètre par paramètre, du réseau k de la v2 et du réseau k de la v8. 3 réseaux,
4 vues, préparation de la v2. Contrôle préalable : la v2 recalculée en local sur 8 photos de chaque jeu doit redonner
les probabilités GPU à 1e-3 près, sinon arrêt.
Sortie : out/maladies/melange/predictions_soupe_<jeu>.csv (mêmes lignes que les fichiers GPU, probabilités seulement).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/predire_soupe_v2_v8.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torchvision import models

RACINE = Path(__file__).resolve().parents[1]
V2 = RACINE / "modeles/maladies_binome/maladies_v2"
V8 = RACINE / "modeles/maladies_v8_kaggle/v8"
sys.path.insert(0, str(V2))
import classifieur  # noqa: E402

GPU = RACINE / "out/maladies/kaggle_adoption_finale"
SORTIE = RACINE / "out/maladies/melange"
JEUX = ["validation", "bananalsd", "val_loin_feuilles"]
P = ["p_saine", "p_black_sigatoka", "p_fusarium"]


def lire(chemin):
    w = torch.load(chemin, map_location="cpu", weights_only=True)
    return {k: v.float() if v.is_floating_point() else v for k, v in w.items()}


def soupes():
    a, b = sorted(V2.glob("poids/maladies_v2_convnext_tiny_*.pt")), sorted(V8.glob("maladies_v8_convnext_tiny_*.pt"))
    assert len(a) == len(b) == 3
    reseaux = []
    for fa, fb in zip(a, b):
        wa, wb = lire(fa), lire(fb)
        assert wa.keys() == wb.keys()
        m = models.convnext_tiny(weights=None)
        m.classifier[2] = torch.nn.Linear(m.classifier[2].in_features, 3)
        m.load_state_dict({k: (wa[k] + wb[k]) / 2 if wa[k].is_floating_point() else wa[k] for k in wa})
        reseaux.append(m.eval())
    return reseaux


def main():
    torch.set_num_threads(8)
    SORTIE.mkdir(parents=True, exist_ok=True)
    v2, _ = classifieur.charger(V2 / "poids")
    for j in JEUX:  # contrôle de la préparation
        g = pd.read_csv(GPU / f"predictions_v2_{j}.csv").sample(8, random_state=0)
        e = np.abs(classifieur.probabilites(v2, [str(RACINE / c) for c in g.chemin]) - g[P].to_numpy()).max()
        print(f"contrôle v2 {j} : écart max {e:.2e}", flush=True)
        if e > 1e-3:
            sys.exit("préparation différente du carnet GPU : arrêt (à noter dans le protocole)")
    del v2
    reseaux = soupes()
    for j in JEUX:
        f = SORTIE / f"predictions_soupe_{j}.csv"
        if f.exists():
            print(j, "déjà fait"); continue
        g = pd.read_csv(GPU / f"predictions_v2_{j}.csv").drop(columns=P + ["reponse"])
        out = []
        for i in range(0, len(g), 64):
            out.append(classifieur.probabilites(reseaux, [str(RACINE / c) for c in g.chemin[i:i + 64]], lot=32))
            print(f"  {j} {min(i + 64, len(g))}/{len(g)}", flush=True)
        g[P] = np.round(np.concatenate(out), 6)
        g.to_csv(f, index=False)
    print("fini")


if __name__ == "__main__":
    main()
