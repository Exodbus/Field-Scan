#!/usr/bin/env python3
"""Essai 9, grille courte de 4 h (journal de M-banc, écrite avant la mesure) : famille C, mélanges contenant un v12.

Pour chaque v12 donné : (1) v12 + v10b ; (2) v12 + soupe ; (3) à quatre v10b + soupe + v2 + v12 ; (4) v12 + soupe + v2.
Géométrique à poids égaux ; seuil règle B 0,50 à 0,80 par 0,02 ; loin « v2 ou proche » ; lecture entière. Pays : pli qui
n'a pas appris le pays ; Tanzanie : moyenne des plis (scripts/m12_banc_v12.py, charger). Réglage seul.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/m12_banc_v12_grille.py a13 a14 a4
"""
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402
ARGS, sys.argv = sys.argv[1:], sys.argv[:1]   # m12_banc_v12 ne calcule rien sans argument
from m12_banc_v12 import charger, geo, jeux, ref  # noqa: E402
sys.argv += ARGS

GRILLE = [round(x, 2) for x in np.arange(0.50, 0.801, 0.02)]
MELANGES = {"v12 + v10b": lambda d, V: [V, d["P10"]], "v12 + soupe": lambda d, V: [V, d["Pso"]],
            "à quatre v10b + soupe + v2 + v12": lambda d, V: [d["P10"], d["Pso"], d["Pv2"], V],
            "v12 + soupe + v2": lambda d, V: [V, d["Pso"], d["Pv2"]]}


def reponses(d, P, t):
    rp = B.decider_v10b(P, seuil=t)
    rl = np.where(np.isin(d["r_loin"], list(B.ALERTE)), d["r_loin"], rp)
    return np.where(d["loin"], rl, rp)


if __name__ == "__main__":
    ESSAIS, meilleurs = [], []
    for nom in sys.argv[1:]:
        V = charger(nom)
        for nm, f in MELANGES.items():
            res = []
            for t in GRILLE:
                r = {}
                for j, d in jeux.items():
                    Ps = f(d, V[j])
                    r[j] = B.mesure(d, reponses(d, geo(Ps, [1] * len(Ps)), t))
                r["cout_moyen"] = float(np.mean([r[j]["cout"] for j in jeux]))
                ok, det = B.finaliste(r, ref)
                e = dict(famille="C", v12=nom, melange=nm, seuil=t, nom=f"{nom} / {nm} / t={t}", finaliste=ok, detail=det, **r)
                ESSAIS.append(e)
                res.append(e)
            fins = [x["seuil"] for x in res if x["finaliste"]]
            surs = [x for i, x in enumerate(res) if x["finaliste"] and 0 < i < len(res) - 1
                    and res[i - 1]["finaliste"] and res[i + 1]["finaliste"]]
            b = min(surs, key=lambda x: x["cout_moyen"]) if surs else None
            print(f"\n--- {nom} / {nm} : finaliste pour t = {fins}")
            if b:
                meilleurs.append(b)
                print("   meilleur sûr : " + B.ligne(f"t={b['seuil']}", b), flush=True)
            else:
                m = min(res, key=lambda x: x["cout_moyen"])
                print("   aucun point sûr ; plus bas : " + B.ligne(f"t={m['seuil']}", m), flush=True)
    print("\nClassement des meilleurs sûrs :")
    for b in sorted(meilleurs, key=lambda x: x["cout_moyen"]):
        print("  " + B.ligne(f"{b['v12']} / {b['melange']} t={b['seuil']}", b))
    print("essais :", len(ESSAIS))
    (B.SORTIE / f"essais_v12_grille_{'_'.join(sys.argv[1:])}.json").write_text(json.dumps(ESSAIS, ensure_ascii=False, indent=1), encoding="utf-8")
