#!/usr/bin/env python3
"""Nombre d'images aiguillées vers la branche « petits » par jeu de RÉGLAGE (et val_negatifs), pour un candidat
aiguillage_v2 de la nuit du 13/11 (agent C-banc). Mesure seulement, aucun choix.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c13_banc_aiguillage.py --candidats CB13_trous_b0.20_reseau
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c13_banc_commun as cc  # noqa: E402
import c13_banc_candidats as cd  # noqa: E402

bc = cc.bc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidats", nargs="+", required=True)
    a = ap.parse_args()
    E = json.loads((cc.SORTIE / "essais.json").read_text(encoding="utf-8"))
    out = {}
    for nom in a.candidats:
        e = E[nom]
        assert e["fabrique"] in ("aiguillage_v2", "aiguillage_p90"), e["fabrique"]
        f = cd.construire(e["fabrique"], e["reglages"])
        f5 = cd.construire("seul", {"modele": "v5"})
        out[nom] = {}
        for j in cc.REGLAGE + ["neg"]:
            it = cc.jeu(j)
            n = 0
            for x in it:
                ctx = bc.Contexte(j, x)
                xy, sc = f(ctx)
                x5, s5 = f5(ctx)
                # aiguillée si le candidat ne rend pas exactement les pics du v5
                if len(xy) != len(x5) or not np.allclose(np.asarray(sc, float), np.asarray(s5, float)):
                    n += 1
            out[nom][j] = [n, len(it)]
        print(nom, out[nom], flush=True)
    p = cc.SORTIE / "aiguillage.json"
    old = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    old.update(out)
    p.write_text(json.dumps(old, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
