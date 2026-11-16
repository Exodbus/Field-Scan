#!/usr/bin/env python3
"""Temps par photo de F1 (code installé) et de F1_bornes, à partir des temps mesurés par lecteur
(out/maladies/nuit_1311/banc/temps.json, m13_banc_temps.py) et des parts de photos qui lisent chaque lecteur sur les 5
jeux de réglage (m13_banc_mb2.masques).

  F1 installé (maladies._executer_melange) : aiguilleur + v2 + soupe + v10b sur toutes les photos ; morceaux 2 x 2 sur
    toutes celles dont la réponse vient du lecteur proche (toutes sauf « loin » + v2 en alerte).
  F1_bornes : aiguilleur + v2 sur toutes ; soupe + v10b sauf « loin » + v2 en alerte ; morceaux sur les photos « dep ».
Temps de chaque lecteur : moyenne sur les 6 photos du même jeu (même machine, mêmes photos, 2 fils, lot de 1).
"""
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m13_banc_commun as C  # noqa: E402
import m13_banc_mb2 as M2  # noqa: E402

LOG = C.SORTIE / "temps.log"


def temps_par_jeu():
    """Relit temps.log : {jeu: {lecteur: [secondes]}}."""
    T = {}
    for l in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        x = l.split()
        if len(x) == 13 and x[1].isdigit() and x[2] in C.JEUX5:
            T.setdefault(x[2], {})
            for k in range(3, 13, 2):
                T[x[2]].setdefault(x[k], []).append(float(x[k + 1]))
    return T


if __name__ == "__main__":
    jeux = C.charger(roamer=False)
    T = temps_par_jeu()
    res, tot = {}, dict(n=0, f1=0.0, var=0.0)
    for j in C.JEUX5:
        t = {k: float(np.mean(v)) for k, v in T[j].items()}
        lv, dep = M2.masques(jeux[j])
        n = len(lv)
        f1 = t["aiguilleur"] + t["v2"] + t["soupe"] + t["v10b"] + t["morceaux_2x2"] * (~lv).mean()
        var = t["aiguilleur"] + t["v2"] + (t["soupe"] + t["v10b"]) * (~lv).mean() + t["morceaux_2x2"] * dep.mean()
        res[j] = dict(lecteurs=t, part_lv=float(lv.mean()), part_morceaux_f1=float((~lv).mean()), part_morceaux_var=float(dep.mean()),
                      f1_s=f1, f1_bornes_s=var, gain=1 - var / f1)
        tot["n"] += n; tot["f1"] += f1 * n; tot["var"] += var * n
        print(f"{j:11s} F1 {f1:6.1f} s  F1_bornes {var:6.1f} s  gain {100 * (1 - var / f1):5.1f} %  "
              f"(lecteurs : " + ", ".join(f"{k} {v:.1f}" for k, v in t.items()) + ")")
    res["total"] = dict(f1_s=tot["f1"] / tot["n"], f1_bornes_s=tot["var"] / tot["n"], gain=1 - tot["var"] / tot["f1"])
    print(f"5 jeux (pondéré par photos) : F1 {res['total']['f1_s']:.1f} s, F1_bornes {res['total']['f1_bornes_s']:.1f} s, "
          f"gain {100 * res['total']['gain']:.1f} %")
    (C.SORTIE / "temps_bilan.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
