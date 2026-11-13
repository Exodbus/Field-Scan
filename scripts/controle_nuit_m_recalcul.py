#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : recalcul INDÉPENDANT des finalistes maladies de M-banc sur le réglage.

Ne lit que les probabilités en cache des 4 jeux de réglage (validation Tanzanie, TDTU, PSFD, Éthiopie) ; aucun juge
(BanSpot, Cordana du Pérou) ni test vierge (AgroVisionBD) n'est ouvert. N'importe pas les fonctions de M-banc ni
decider_convnext : la règle d'alerte est réécrite à partir de son texte.

Règle d'alerte réécrite (démontrée sur le code de decider_convnext, seuils v10b : seuil_alerte 0,725, règle B, v11) :
une photo « proche » lue par la décision v10b au seuil t (t > 0,275) est en alerte si et seulement si P(saine) < t.
Branche loin (v2, politique b, seuil_alerte 0,30, seuil de confiance 0,646) : alerte si et seulement si
P_v2(saine) <= 0,70 (p_malade >= 0,30) ; « je ne sais pas » impossible car P(saine) > 0,70 donne une confiance > 0,646.
Contrôle : on compare aussi au module de M-banc (scripts/m12_banc_finalistes.py) sur chaque photo.

Sorties : out/controle_nuit_1112/m_recalcul.json et m_recalcul.txt
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_m_recalcul.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
OUT = RACINE / "out/controle_nuit_1112"
OUT.mkdir(parents=True, exist_ok=True)
JEUX = ["validation", "tdtu", "psfd", "ethiopie"]
K = RACINE / "out/maladies/nuit_1112/banc/kaggle_morceaux"
C4 = ["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]
INTERDITS = ("banspot", "cordana", "perou", "agrovision", "test_")


def lire_csv(p):
    assert not any(m in str(p).lower() for m in INTERDITS), p
    return pd.read_csv(p)


def charger():
    jeux = {}
    for j in JEUX:
        v10 = lire_csv(RACINE / f"out/maladies/v10b/predictions_v10b_{j}.csv")
        dos = RACINE / ("out/maladies/dinov2_ft" if j == "validation" else "out/maladies/cinq_classes")
        so = lire_csv(dos / f"predictions_soupe_{j}.csv")
        v2 = lire_csv(dos / f"predictions_v2_{j}.csv")
        pl = lire_csv(RACINE / f"out/maladies/cinq_classes/p_loin_{j}.csv")
        p512 = lire_csv(K / f"p512_{j}.csv")
        z = np.load(K / f"morceaux_{j}.npz")
        for d in (so, v2, pl, p512):
            assert list(d.chemin) == list(v10.chemin), j
        assert z["g2"].shape[0] == len(v10)
        jeux[j] = dict(malade=(v10.classe_vraie != "saine").to_numpy(), P10=v10[C4].to_numpy("f8"),
                       Pso=so[C4[:3]].to_numpy("f8"), Pv2=v2[C4[:3]].to_numpy("f8"),
                       loin=pl.p_loin.to_numpy("f8") >= 0.5, P512=p512[C4].to_numpy("f8"),
                       G2=z["g2"].astype("f8"), chemin=v10.chemin.to_numpy(object))
    return jeux


def melange(P10, Pso, Pv2, w=(1, 1, 1)):
    """P(saine) du mélange : moyenne géométrique pondérée des 3 classes communes ; « autre » v10b × w0/somme."""
    w = np.asarray(w, "f8") / sum(w)
    g = np.exp(w[0] * np.log(np.clip(P10[:, :3], 1e-9, 1)) + w[1] * np.log(np.clip(Pso, 1e-9, 1))
               + w[2] * np.log(np.clip(Pv2, 1e-9, 1)))
    tot = g.sum(1) + w[0] * P10[:, 3]
    return g[:, 0] / tot


def lecture(d, mode):
    P10 = d["P10"]
    if mode == "384":
        return P10
    if mode == "384+512":
        return (P10 + d["P512"]) / 2
    pm_morc = 1 - d["G2"][:, :, 0]
    if mode == "g2_2fortes":
        agr = np.sort(pm_morc, 1)[:, -2:].mean(1)
    elif mode == "g2_max":
        agr = pm_morc.max(1)
    elif mode == "g2_ou":
        agr = 1 - np.prod(1 - pm_morc, 1)
    else:
        raise ValueError(mode)
    pm = ((1 - P10[:, 0]) + agr) / 2
    Q = P10 * (pm / np.clip(1 - P10[:, 0], 1e-9, None))[:, None]
    Q[:, 0] = 1 - pm
    return Q


def ps_proche(d, mode, w):
    P10 = lecture(d, mode)
    if w is None:
        return P10[:, 0]
    return melange(P10, d["Pso"], d["Pv2"], w)


def alertes(d, ps, t, loin_ou):
    a_proche = ps < t
    a_v2 = d["Pv2"][:, 0] <= 0.70
    a_loin = (a_v2 | a_proche) if loin_ou else a_v2
    return np.where(d["loin"], a_loin, a_proche)


def mesure(d, al):
    m = d["malade"]
    msa, sea, nm, ns = int((m & ~al).sum()), int((~m & al).sum()), int(m.sum()), int((~m).sum())
    return dict(msa=msa, nm=nm, sea=sea, ns=ns, cout=100 * (3 * msa / nm + (sea / ns if ns else 0.0)))


def evaluer(jeux, mode, w, t, loin_ou, quels=JEUX):
    r = {j: mesure(jeux[j], alertes(jeux[j], ps_proche(jeux[j], mode, w), t, loin_ou)) for j in quels}
    r["cout_moyen"] = float(np.mean([r[j]["cout"] for j in quels]))
    return r


REF = dict(mode="384", w=None, t=0.5186470150947571, loin_ou=False)
FINALISTES = {
    "F1_trois_morceaux2x2": dict(mode="g2_2fortes", w=(1, 1, 1), t=0.70, loin_ou=True),
    "F2_trois_384_512": dict(mode="384+512", w=(1, 1, 1), t=0.72, loin_ou=True),
    "F3_trois": dict(mode="384", w=(1, 1, 1), t=0.74, loin_ou=True),
    "reserve_geo_v10b_soupe_loin": dict(mode="384", w=(1, 1, 0), t=0.68, loin_ou=True),
}
ANNONCE = {  # finalistes.md de M-banc : (msa, sea) par jeu, coût moyen
    "F1_trois_morceaux2x2": ([(0, 62), (19, 241), (102, 0), (117, 28)], 35.96),
    "F2_trois_384_512": ([(1, 58), (22, 234), (105, 0), (125, 27)], 36.48),
    "F3_trois": ([(2, 57), (28, 232), (109, 0), (134, 27)], 37.83),
    "reserve_geo_v10b_soupe_loin": ([(2, 64), (27, 222), (117, 0), (131, 34)], 39.24),
}


def finaliste(r, ref):
    c1 = r["cout_moyen"] <= ref["cout_moyen"] - 1.0
    c2 = r["validation"]["msa"] <= 14 and r["validation"]["sea"] <= 77
    c3 = all(100 * (r[j]["msa"] / r[j]["nm"] - ref[j]["msa"] / ref[j]["nm"]) <= 2.0 for j in ("tdtu", "psfd", "ethiopie"))
    return bool(c1 and c2 and c3), dict(cout=c1, tanzanie=c2, pays=c3)


def auc(score_malade, malade):
    """AUC (Mann-Whitney) : probabilité qu'une malade ait un score plus haut qu'une saine."""
    s1, s0 = score_malade[malade], score_malade[~malade]
    if len(s1) == 0 or len(s0) == 0:
        return None
    r = pd.Series(np.concatenate([s1, s0])).rank().to_numpy()
    return float((r[:len(s1)].sum() - len(s1) * (len(s1) + 1) / 2) / (len(s1) * len(s0)))


if __name__ == "__main__":
    jeux = charger()
    lignes, res = [], {}
    ref = evaluer(jeux, **REF)
    lignes.append(f"référence (v10b installée) : coût moyen {ref['cout_moyen']:.3f} ; "
                  + " ; ".join(f"{j} {ref[j]['msa']}/{ref[j]['nm']} {ref[j]['sea']}/{ref[j]['ns']}" for j in JEUX))
    res["reference"] = ref
    # 1. recalcul indépendant et règle « finaliste »
    for nom, c in FINALISTES.items():
        r = evaluer(jeux, **c)
        ok, det = finaliste(r, ref)
        ann, cm = ANNONCE[nom]
        ecarts = [(r[j]["msa"] - a, r[j]["sea"] - b) for j, (a, b) in zip(JEUX, ann)]
        res[nom] = dict(r=r, finaliste=ok, detail=det, ecart_annonce=ecarts, ecart_cout=r["cout_moyen"] - cm)
        lignes.append(f"{nom:30s} coût {r['cout_moyen']:.3f} (annoncé {cm}, écart {r['cout_moyen'] - cm:+.3f}) ; "
                      + " ; ".join(f"{j} {r[j]['msa']}/{r[j]['sea']}" for j in JEUX)
                      + f" ; écarts comptes {ecarts} ; finaliste {ok} {det}")
        # plateau : seuil de 0,50 à 0,84 par 0,02
        pl = []
        for t in np.round(np.arange(0.50, 0.845, 0.02), 2):
            rt = evaluer(jeux, **{**c, "t": float(t)})
            pl.append((float(t), round(rt["cout_moyen"], 2), finaliste(rt, ref)[0], rt["validation"]["sea"]))
        res[nom]["plateau"] = pl
        lignes.append("   plateau (t, coût, finaliste, saines en alerte Tanzanie) : "
                      + " ".join(f"{t:.2f}:{cc}{'F' if f else '-'}({s})" for t, cc, f, s in pl))
    # 2. contrôle croisé avec le code de M-banc (décisions photo par photo)
    try:
        sys.path.insert(0, str(RACINE / "scripts"))
        import m12_banc_finalistes as MF  # noqa: E402
        diff = {}
        for nom, c in FINALISTES.items():
            n = 0
            for j in JEUX:
                d = jeux[j]
                rep = MF.repondre(d["P10"], d["Pso"], d["Pv2"], np.where(d["loin"], 1.0, 0.0), MF.CANDIDATS[nom],
                                  d["P512"], d["G2"])
                al_mb = np.isin(rep, list(MF.B.ALERTE))
                al_moi = alertes(d, ps_proche(d, c["mode"], c["w"]), c["t"], c["loin_ou"])
                n += int((al_mb != al_moi).sum())
            diff[nom] = n
        res["desaccords_photo_avec_mbanc"] = diff
        lignes.append(f"désaccords d'alerte photo par photo avec scripts/m12_banc_finalistes.py : {diff}")
    except Exception as e:  # noqa: BLE001
        lignes.append(f"contrôle croisé impossible : {e!r}")
    # 3. séparabilité : AUC de 1 - P(saine) du lecteur proche, par jeu (photos proches seules et toutes)
    lecteurs = {"v10b_384": ("384", None), "F3_trois": ("384", (1, 1, 1)), "F2_384_512": ("384+512", (1, 1, 1)),
                "F1_g2_2fortes": ("g2_2fortes", (1, 1, 1)), "v10b_g2_2fortes": ("g2_2fortes", None)}
    aucs = {}
    for nom, (mode, w) in lecteurs.items():
        aucs[nom] = {}
        for j in ("validation", "tdtu", "ethiopie"):
            d = jeux[j]
            s = 1 - ps_proche(d, mode, w)
            aucs[nom][j] = dict(toutes=auc(s, d["malade"]), proches=auc(s[~d["loin"]], d["malade"][~d["loin"]]))
    res["auc"] = aucs
    lignes.append("AUC (1 - P(saine) du lecteur proche) toutes / proches : " + json.dumps(aucs, ensure_ascii=False))
    # 4. F1 contre F3 à fausses alertes égales : pour chaque jeu avec saines, on règle F3 (seuil continu, par jeu, oracle)
    #    pour avoir exactement autant de saines en alerte que F1, et on compare les malades ratées.
    cmp = {}
    for j in ("validation", "tdtu", "ethiopie"):
        d = jeux[j]
        a1 = alertes(d, ps_proche(d, "g2_2fortes", (1, 1, 1)), 0.70, True)
        cible = int((~d["malade"] & a1).sum())
        ps3 = ps_proche(d, "384", (1, 1, 1))
        best = None
        for t in np.unique(np.concatenate([ps3, [0.0, 1.0]])):
            for eps in (1e-12,):
                a3 = alertes(d, ps3, t + eps, True)
                if int((~d["malade"] & a3).sum()) <= cible:
                    m3 = int((d["malade"] & ~a3).sum())
                    if best is None or m3 < best[1]:
                        best = (float(t), m3, int((~d["malade"] & a3).sum()))
        cmp[j] = dict(F1_ratees=int((d["malade"] & ~a1).sum()), F1_fa=cible, F3_meme_fa_ratees=best[1],
                      F3_fa=best[2], t3=best[0])
    res["F1_contre_F3_meme_fa"] = cmp
    lignes.append("F1 contre F3 à fausses alertes égales (seuil F3 choisi par jeu) : " + json.dumps(cmp))
    (OUT / "m_recalcul.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (OUT / "m_recalcul.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))
