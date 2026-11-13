#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : candidat maladies de la famille C (mélange contenant un v12), recalcul indépendant.

C_quatre_v12a14 : moyenne géométrique à poids égaux de v10b, soupe, v2, v12a14 sur saine / Sigatoka noire / fusariose ;
« autre » = (P_autre v10b + P_autre v12) / 4 ; proche en alerte si P(saine) < t (0,76) ; loin : v2 ou proche.
Probabilités v12 : pays lus par le pli qui ne les a pas appris ; validation : DEUX lectures, (a) probabilités des plis
moyennées (code de M-banc), (b) comptes des plis moyennés (définition de M-entraîneur) ; modèle final relu sur la
validation. Puis : plateau, « un jeu dehors » sur l'espace de la grille de 4 h (v12 x 4 mélanges x 16 seuils, règle de
plateau de M-banc), bootstrap apparié contre la v10b et contre F3. Réglage seulement.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_m_famille_c.py
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
import controle_nuit_m_recalcul as R  # noqa: E402

KAG = RACINE / "out/maladies/nuit_1112/kaggle"
C4 = ["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]
REF = {"validation": (9, 2001, 57, 1000), "tdtu": (83, 1059, 177, 577), "psfd": (149, 738, 0, 0), "ethiopie": (179, 1134, 43, 155)}
GRILLE = [round(x, 2) for x in np.arange(0.50, 0.801, 0.02)]
V12 = ["a13", "a14", "a4", "a17", "a18", "a19", "a20"]


def cout(msa, nm, sea, ns):
    return 100 * (3 * msa / nm + (sea / ns if ns else 0.0))


def ps_geo(membres):
    """membres : liste de matrices (n, 3) ou (n, 4) ; P(saine) du mélange géométrique à poids égaux."""
    w = 1.0 / len(membres)
    g = np.exp(sum(w * np.log(np.clip(P[:, :3], 1e-9, 1)) for P in membres))
    autre = sum(w * P[:, 3] for P in membres if P.shape[1] == 4)
    return g[:, 0] / (g.sum(1) + autre)


def main():
    jeux = R.charger()

    def lire_v12(c):
        out = {}
        for j in R.JEUX:
            ch = list(jeux[j]["chemin"])
            if j == "validation":
                fs = sorted((KAG / c).glob(f"predictions_{c}_validation_pli_*.csv"))
                out[j] = [pd.read_csv(f).set_index("chemin").loc[ch][C4].to_numpy("f8") for f in fs]
            else:
                out[j] = [pd.read_csv(KAG / c / f"predictions_{c}_{j}.csv").set_index("chemin").loc[ch][C4].to_numpy("f8")]
        return out

    V = {c: lire_v12(c) for c in V12 if (KAG / c).exists()}
    MEL = {"v12+v10b": lambda d, X: [X, d["P10"]], "v12+soupe": lambda d, X: [X, d["Pso"]],
           "quatre": lambda d, X: [d["P10"], d["Pso"], d["Pv2"], X], "v12+soupe+v2": lambda d, X: [X, d["Pso"], d["Pv2"]]}

    def alertes(d, ps, t):
        ap = ps < t
        return np.where(d["loin"], (d["Pv2"][:, 0] <= 0.70) | ap, ap)

    def comptes(c, mel, t, j, lecture="probas", idx=None):
        d = jeux[j]
        Xs = V[c][j]
        if j == "validation" and lecture == "probas":
            Xs = [np.mean(Xs, 0)]
        res = []
        for X in Xs:
            a = alertes(d, ps_geo(MEL[mel](d, X)), t)
            m = d["malade"]
            if idx is not None:
                a, m = a[idx], m[idx]
            res.append(((m & ~a).sum(), m.sum(), (~m & a).sum(), (~m).sum()))
        return np.mean(np.array(res, float), 0)

    ref_c = {j: cout(*REF[j]) for j in R.JEUX}

    def evalue(c, mel, t, quels, lecture="probas"):
        r = {j: comptes(c, mel, t, j, lecture) for j in quels}
        cm = float(np.mean([cout(*r[j]) for j in quels]))
        ok = cm <= np.mean([ref_c[j] for j in quels]) - 1.0
        if "validation" in quels:
            ok &= r["validation"][0] <= 14 and r["validation"][2] <= 77
        for j in quels:
            if j != "validation":
                ok &= 100 * (r[j][0] / r[j][1] - REF[j][0] / REF[j][1]) <= 2.0
        return cm, bool(ok), r

    L = []
    for lecture in ("probas", "comptes"):
        cm, ok, r = evalue("a14", "quatre", 0.76, R.JEUX, lecture)
        L.append(f"C_quatre_v12a14, t = 0,76, validation lue par « {lecture} » : coût {cm:.3f} ; finaliste {ok} ; "
                 + " ; ".join(f"{j} {r[j][0]:.1f}/{r[j][2]:.1f}" for j in R.JEUX))
    pl = [(t, *evalue("a14", "quatre", t, R.JEUX)[:2]) for t in GRILLE]
    L.append("plateau (probas) : " + " ".join(f"{t:.2f}:{c:.2f}{'F' if o else '-'}" for t, c, o in pl))
    # modèle final sur la validation
    d = jeux["validation"]
    pf = pd.read_csv(KAG / "final_a13_a14/predictions_a14_final_validation.csv").set_index("chemin").loc[list(d["chemin"])][C4].to_numpy("f8")
    a = alertes(d, ps_geo([d["P10"], d["Pso"], d["Pv2"], pf]), 0.76)
    L.append(f"modèle final v12a14 dans le mélange à quatre, t = 0,76, validation : {int((d['malade'] & ~a).sum())} ratées ; "
             f"{int((~d['malade'] & a).sum())} saines en alerte (limites 14 et 77)")
    # un jeu dehors sur l'espace de la grille (v12 disponibles x 4 mélanges x 16 seuils), règle de plateau de M-banc
    for nom_esp, v12s in (("grille de 4 h (a13, a14, a4)", ["a13", "a14", "a4"]), ("avec le lot 6", [c for c in V12 if c in V])):
        fam = list(itertools.product(v12s, MEL))
        cache = {(c, m, t): {j: comptes(c, m, t, j) for j in R.JEUX} for c, m in fam for t in GRILLE}

        def choisir(quels):
            best = None
            for c, m in fam:
                for i in range(1, len(GRILLE) - 1):
                    oks = []
                    for k in (i - 1, i, i + 1):
                        r = cache[(c, m, GRILLE[k])]
                        cmq = np.mean([cout(*r[j]) for j in quels])
                        ok = cmq <= np.mean([ref_c[j] for j in quels]) - 1.0
                        if "validation" in quels:
                            ok &= r["validation"][0] <= 14 and r["validation"][2] <= 77
                        for j in quels:
                            if j != "validation":
                                ok &= 100 * (r[j][0] / r[j][1] - REF[j][0] / REF[j][1]) <= 2.0
                        oks.append(ok)
                    if all(oks):
                        r = cache[(c, m, GRILLE[i])]
                        cmq = float(np.mean([cout(*r[j]) for j in quels]))
                        if best is None or cmq < best[0]:
                            best = (cmq, (c, m, GRILLE[i]))
            return best
        plein = choisir(R.JEUX)
        L.append(f"[{nom_esp}] choix sur les 4 jeux : {plein}")
        gd, gp = [], []
        for h in R.JEUX:
            ch = choisir([j for j in R.JEUX if j != h])
            if ch is None:
                L.append(f"  {h} dehors : aucun choix")
                continue
            cd = cout(*cache[ch[1]][h]); cp = cout(*cache[plein[1]][h])
            gd.append(ref_c[h] - cd); gp.append(ref_c[h] - cp)
            L.append(f"  {h} dehors : choix {ch[1]} ; coût dehors {cd:.2f} (choix plein {cp:.2f} ; v10b {ref_c[h]:.2f})")
        L.append(f"  gain moyen hors échantillon {np.mean(gd):.2f} contre {np.mean(gp):.2f} en plein (optimisme {np.mean(gp) - np.mean(gd):.2f})")
    # bootstrap apparié contre la v10b et contre F3
    rng = np.random.default_rng(2026)
    a_ref = {j: R.alertes(jeux[j], R.ps_proche(jeux[j], "384", None), 0.5186470150947571, False) for j in R.JEUX}
    a_f3 = {j: R.alertes(jeux[j], R.ps_proche(jeux[j], "384", (1, 1, 1)), 0.74, True) for j in R.JEUX}
    dv, df = [], []
    for _ in range(2000):
        tv = tf = 0.0
        for j in R.JEUX:
            m = jeux[j]["malade"]
            i = rng.integers(0, len(m), len(m))
            cc = cout(*comptes("a14", "quatre", 0.76, j, idx=i))
            mi = m[i]
            cr = cout((mi & ~a_ref[j][i]).sum(), mi.sum(), (~mi & a_ref[j][i]).sum(), (~mi).sum())
            c3 = cout((mi & ~a_f3[j][i]).sum(), mi.sum(), (~mi & a_f3[j][i]).sum(), (~mi).sum())
            tv += cc - cr; tf += cc - c3
        dv.append(tv / 4); df.append(tf / 4)
    for nom, v in (("v10b", np.array(dv)), ("F3", np.array(df))):
        L.append(f"bootstrap contre {nom} : {v.mean():+.2f} (é.-t. {v.std():.2f} ; IC 95 % [{np.quantile(v, 0.025):+.2f} ; {np.quantile(v, 0.975):+.2f}])")
    (R.OUT / "m_famille_c.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
