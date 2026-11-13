#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : recalcul indépendant d'un finaliste v12 (M-entraînement) et bruit de mesure.

Chaîne : aiguilleur (p_loin >= 0,5 -> v2, alerte si P_v2(saine) <= 0,70) ; sinon le candidat avec les seuils de la
v10b (alerte si P(saine) < 0,5186). Pays lus dans le pli qui ne les a pas appris (fichiers predictions_<c>_<pays>.csv),
validation = moyenne des plis disponibles (predictions_<c>_validation_pli_*.csv). Puis bootstrap apparié (photos
tirées avec remise dans chaque jeu, 2 000 tirages, graine 2026) de l'écart de coût moyen candidat − v10b, et le même
pour les finalistes de M-banc (pour comparer les gains au bruit). Réglage seulement.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_m_v12.py a4
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import controle_nuit_m_recalcul as R  # noqa: E402

T_V10B = 0.5186470150947571


def cout(m, a):
    """m : malade (bool), a : alerte (bool) -> coût en points."""
    nm, ns = m.sum(), (~m).sum()
    return 100 * (3 * (m & ~a).sum() / nm + ((~m & a).sum() / ns if ns else 0.0))


def main(c):
    K = RACINE / f"out/maladies/nuit_1112/kaggle/{c}"
    jeux = R.charger()
    al_c, lignes = {}, []
    for j in R.JEUX:
        d = jeux[j]
        v2a = d["Pv2"][:, 0] <= 0.70
        if j == "validation":
            fs = sorted(K.glob(f"predictions_{c}_validation_pli_*.csv"))
        else:
            fs = [K / f"predictions_{c}_{j}.csv"]
        al = []
        for f in fs:
            p = pd.read_csv(f).set_index("chemin").loc[list(d["chemin"])]
            al.append(np.where(d["loin"], v2a, p.p_saine.to_numpy() < T_V10B))
        al_c[j] = al
        cnt = [(int((d["malade"] & ~a).sum()), int((~d["malade"] & a).sum())) for a in al]
        lignes.append(f"{c} {j} : plis {[f.name for f in fs]} ; (ratées, fausses alertes) {cnt} ; moyenne "
                      f"{np.mean([x[0] for x in cnt]):.1f} ; {np.mean([x[1] for x in cnt]):.1f} ; coût "
                      f"{np.mean([cout(d['malade'], a) for a in al]):.3f}")
    cm = np.mean([np.mean([cout(jeux[j]["malade"], a) for a in al_c[j]]) for j in R.JEUX])
    lignes.append(f"{c} : coût moyen {cm:.3f}")
    # bootstrap apparié
    rng = np.random.default_rng(2026)
    refa = {j: R.alertes(jeux[j], R.ps_proche(jeux[j], "384", None), T_V10B, False) for j in R.JEUX}
    autres = {n: {j: R.alertes(jeux[j], R.ps_proche(jeux[j], f["mode"], f["w"]), f["t"], f["loin_ou"]) for j in R.JEUX}
              for n, f in R.FINALISTES.items() if n != "reserve_geo_v10b_soupe_loin"}
    cands = {c: al_c, **{n: {j: [a] for j, a in v.items()} for n, v in autres.items()}}
    diffs = {n: [] for n in cands}
    for _ in range(2000):
        tot = {n: 0.0 for n in cands}
        for j in R.JEUX:
            m = jeux[j]["malade"]
            i = rng.integers(0, len(m), len(m))
            cr = cout(m[i], refa[j][i])
            for n, al in cands.items():
                tot[n] += np.mean([cout(m[i], a[i]) for a in al[j]]) - cr
        for n in cands:
            diffs[n].append(tot[n] / len(R.JEUX))
    res = {}
    for n, v in diffs.items():
        v = np.array(v)
        res[n] = dict(moyenne=float(v.mean()), ecart_type=float(v.std()), ic95=[float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))],
                      p_gain_moins_1=float(np.mean(v > -1.0)))
        lignes.append(f"bootstrap {n} : écart de coût contre v10b {v.mean():+.2f} (é.-t. {v.std():.2f}, IC 95 % "
                      f"[{np.quantile(v, 0.025):+.2f} ; {np.quantile(v, 0.975):+.2f}]) ; part des tirages où le gain est < 1 point : {np.mean(v > -1.0):.2f}")
    (R.OUT / f"m_{c}.json").write_text(json.dumps(dict(cout_moyen=cm, bootstrap=res), ensure_ascii=False, indent=1), encoding="utf-8")
    (R.OUT / f"m_{c}.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "a4")
