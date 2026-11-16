#!/usr/bin/env python3
"""Essai « hauteur » : contrôle visuel, pour information, des reconstructions OpenSfM (nuage clairsemé).

La phase 1 s'arrête au premier critère (photos placées) : ni MNS ni orthophoto ne sont calculés. Cette planche
montre, vu de dessus, le nuage clairsemé de chaque reconstruction coloré par la hauteur (mètres, échelle propre
à chaque reconstruction par la règle des 1,1 cm/px), avec les positions des caméras.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/hauteur_controle_nuage.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
from hauteur_commun import OUT, echelle, lire_reconstructions, poses  # noqa: E402


def main():
    recs = lire_reconstructions()
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    for ax, i, titre in zip(axes, (0, 1), ("reconstruction 0 : pépinière en pots", "reconstruction 1 : plantation dense")):
        rec = recs[i]
        k, _, _ = echelle(rec)
        pts = np.array([p["coordinates"] for p in rec["points"].values()]) * k
        z = pts[:, 2] - np.median(pts[:, 2])
        lo, hi = np.percentile(z, [2, 98])
        sc = ax.scatter(pts[:, 0], pts[:, 1], c=np.clip(z, lo, hi), s=0.3, cmap="viridis")
        C = np.array([p[2] for p in poses(rec).values()]) * k
        ax.plot(C[:, 0], C[:, 1], "r.", ms=5)
        ax.set_aspect("equal")
        ax.set_title(f"{titre}\n{len(rec['shots'])} photos, {len(pts)} points ; hauteur relative (m)")
        ax.set_xlabel("x (m, repère local)"); ax.set_ylabel("y (m)")
        fig.colorbar(sc, ax=ax, shrink=0.7)
    fig.tight_layout()
    fig.savefig(OUT / "controle_nuage_clairseme.png", dpi=110)
    print(OUT / "controle_nuage_clairseme.png")


if __name__ == "__main__":
    main()
