#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : stabilité du gain de comptage sur btd_val, bloc de mosaïque par bloc.

btd_val (178 tuiles) vient de trois blocs de l'orthomosaïque banana_tree_detection (découpage v6 : bloc 0, 46 tuiles ;
bloc 1, 93 ; bloc 2, 39), sans position relative connue entre eux. Pour chaque bloc : F1 des finalistes du banc et du v5
(0,20 et 0,30), part des tuiles aiguillées ; puis, pour l'aiguillage p90, tau et décalage re-choisis sur les deux autres
blocs (seuil 0,30), lus sur le bloc dehors. Réglage seulement (code de controle_nuit_c_recalcul.py).
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_c_blocs.py
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import controle_nuit_c_recalcul as R  # noqa: E402


def blocs_btd():
    dec = pd.read_csv(RACINE / "data/drone/decoupage_comptage_v6/decoupage.csv")
    btd = dec[dec.groupe.isin(["btd_train", "btd_val"])].sort_values("image").reset_index(drop=True)
    return {f"btd_val_{k:04d}.jpg": int(r.bloc_mosaique) for k, r in btd.iterrows() if r.groupe == "btd_val"}


def par_image(spec, items, seuils):
    out = []
    for e in items:
        xy, sc = R.candidat(spec, "btd_val", e["nom"])
        out.append({s: np.array(R.apparier(xy[sc >= s], e["pts"], e["ign"])) for s in seuils})
    return out


def f1(c):
    vp, fp, fn = c
    return 2 * vp / (2 * vp + fp + fn) if vp else 0.0


def main():
    B = blocs_btd()
    items = R.items("btd_val")
    assert all(e["nom"] in B for e in items)
    bl = np.array([B[e["nom"]] for e in items])
    specs = json.loads((R.OUT / "specs_c_banc.json").read_text(encoding="utf-8"))
    seuils = {"v5": [0.20, 0.30], "E5p90b_moy34_v5_d0.1": [0.30], "E7_union_v5+v3_d0.05_r30": [0.30], "E3_log_v3+v4+v5": [0.25]}
    specs["v3"] = {"type": "seul", "modele": "v3"}; seuils["v3"] = [0.20]
    specs["moy34"] = {"type": "melange", "membres": ["v3", "v4"], "mode": "moyenne"}; seuils["moy34"] = [0.20]
    lignes, res = [f"tuiles par bloc : {dict(zip(*np.unique(bl, return_counts=True)))}"], {}
    for nom, spec in specs.items():
        pi = par_image(spec, items, seuils[nom])
        for s in seuils[nom]:
            par = {int(b): f1(sum(p[s] for p, x in zip(pi, bl) if x == b)) for b in (0, 1, 2)}
            tot = f1(sum(p[s] for p in pi))
            res[f"{nom}@{s}"] = dict(blocs=par, total=tot)
            lignes.append(f"{nom:28s} seuil {s:.2f} : total {tot:.4f} ; blocs " + ", ".join(f"{b}: {v:.4f}" for b, v in par.items()))
    # part aiguillée
    q = []
    for e in items:
        _, sc = R.maxima(R.carte("v5", "btd_val", e["nom"]), 0.15)
        q.append(float(np.quantile(sc, 0.9)) if len(sc) else np.nan)
    q = np.array(q)
    for b in (0, 1, 2):
        lignes.append(f"bloc {b} : p90 du v5 médian {np.nanmedian(q[bl == b]):.3f}, part sous 0,55 {np.mean(q[bl == b] < 0.55):.2f}")
    # tau / décalage re-choisis sur deux blocs, lus sur le troisième (seuil 0,30 ; petit = moyenne v3+v4)
    grille = list(itertools.product([0.40, 0.45, 0.50, 0.55, 0.60, 0.65], [0.05, 0.10, 0.15]))
    cache = {}
    for tau, d in grille:
        sp = {"type": "p90", "tau": tau, "decalage": d, "petit": specs["moy34"], "grand": {"type": "seul", "modele": "v5"}}
        cache[(tau, d)] = [p[0.30] for p in par_image(sp, items, [0.30])]
    for h in (0, 1, 2):
        ent = [b for b in (0, 1, 2) if b != h]
        def sc_(k, quels):
            return f1(sum(c for c, x in zip(cache[k], bl) if x in quels))
        k = max(grille, key=lambda k: sc_(k, ent))
        lignes.append(f"bloc {h} dehors : (tau, d) choisis {k} ; F1 bloc dehors {sc_(k, [h]):.4f} contre {sc_((0.55, 0.10), [h]):.4f} "
                      f"au choix officiel ; meilleur possible sur ce bloc {max(sc_(kk, [h]) for kk in grille):.4f}")
    res["grille_tau_d_total"] = {f"{k}": f1(sum(cache[k])) for k in grille}
    lignes.append("F1 btd_val total selon (tau, d) au seuil 0,30 : " + ", ".join(f"{k}: {v:.3f}" for k, v in res["grille_tau_d_total"].items()))
    (R.OUT / "c_blocs.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    (R.OUT / "c_blocs.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))


if __name__ == "__main__":
    main()
