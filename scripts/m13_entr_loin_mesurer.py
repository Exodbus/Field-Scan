#!/usr/bin/env python3
"""ME3 (M-entraîneur, nuit du 13/11) : lecteur « loin » l1b à la place de la v2 dans la branche « loin ».

Seuil s (règle écrite à 23 h 55) : le plus haut s tel que l1b, lu sur toutes les feuilles de roamer_dev_loin_feuilles
(moyenne des 2 plis), ne rate pas plus de malades que la v2 (seuils de la chaîne) lue sur ces mêmes feuilles.
Chaîne : photo « loin » -> alerte si P_l1b(malade) >= s OU si le lecteur proche alerte (forme de F1) ; variante « l1b
seul ». Lecteur proche : F1 (famille C : F1 + réseau neuf) ou l'élève livrable (ensemble d2b) s'il est fourni.
Pour F1 sur AgroVisionBD, les morceaux 2 x 2 n'ont été lus que pour 113 photos : ailleurs, le lecteur proche de F1 est
pris sans morceaux (approximation, comptée et écrite).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_entr_loin_mesurer.py <lot> <recette> [eleve_lot:eleve_nom]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402
import m12_banc_finalistes as MF  # noqa: E402
import m13_entr_mesurer as M  # noqa: E402
from fieldscan.modules import maladies  # noqa: E402

F1 = MF.CANDIDATS["F1_trois_morceaux2x2"]
M_PROCHE = {**B.M_V10B, "seuil": F1["seuil"]}


def proche_f1():
    """Réponse du lecteur proche de F1 pour toutes les photos (y compris « loin »)."""
    J = B.charger_reglage()
    out, approx = {}, 0
    for j in B.REGLAGE:
        d = J[j]
        g2 = np.load(RACINE / f"out/maladies/nuit_1112/banc/kaggle_morceaux/morceaux_{j}.npz")["g2"].astype("float64")
        out[j] = maladies.decider_convnext(MF.geo(MF.lecture_v10b(d["P10"], F1, G2=g2), d["Pso"], d["Pv2"], (1, 1, 1)), M_PROCHE)[0]
    V = M.VIERGE
    P10, Pso, Pv2, G2 = (np.load(V / f"p_{k}.npy").astype("float64") for k in ("v10b", "soupe", "v2", "g2"))
    manque = np.isnan(G2).reshape(len(G2), -1).any(1)
    G2[manque] = np.repeat(P10[manque][:, None, :], 4, 1)   # sans morceaux : la photo entière tient lieu de morceaux
    out["agrovision"] = maladies.decider_convnext(MF.geo(MF.lecture_v10b(P10, F1, G2=G2), Pso, Pv2, (1, 1, 1)), M_PROCHE)[0]
    approx = int((manque & M.JEUX["agrovision"]["loin"]).sum())
    proche = ~M.JEUX["agrovision"]["loin"]   # photos « proche » : réponse exacte de F1 (cache du 13/11)
    out["agrovision"] = np.where(proche, M.JEUX["agrovision"]["f1"], out["agrovision"])
    z = np.load(M.KAG / "maitre" / "maitre_roamer_dev_loin.npz", allow_pickle=True)
    out["roamer_dev_loin"] = maladies.decider_convnext(MF.geo(MF.lecture_v10b(z["P10"].astype("float64"), F1, G2=z["G2"].astype("float64")),
                                                              z["Pso"].astype("float64"), z["Pv2"].astype("float64"), (1, 1, 1)), M_PROCHE)[0]
    return out, approx


def lire_loin(dos, rec):
    P = {}
    for j in M.TOUS:
        fs = [dos / f"loin_{rec}_{j}.csv"] if (dos / f"loin_{rec}_{j}.csv").exists() else sorted(dos.glob(f"loin_{rec}_{j}_pli_*.csv"))
        if fs:
            P[j] = np.mean([pd.read_csv(f).set_index("chemin").loc[M.JEUX[j]["chemin"]].p_malade.to_numpy() for f in fs], 0)
    return P


def chaine(rp, j, pl, s, seul=False):
    d = M.JEUX[j]
    rp = np.asarray(rp, dtype=object)
    if seul:
        loin_rep = np.where(pl >= s, "malade_non_identifiee", "saine")
    else:
        loin_rep = np.where(np.isin(rp, list(B.ALERTE)), rp, np.where(pl >= s, "malade_non_identifiee", rp))
    return np.where(d["loin"], loin_rep, rp)


if __name__ == "__main__":
    lot, rec = sys.argv[1], sys.argv[2]
    dos = M.KAG / lot
    PL = lire_loin(dos, rec)
    d = M.JEUX["roamer_dev_loin"]
    v2_rate = int((d["malade"] & ~np.isin(d["r_loin"], list(B.ALERTE))).sum())
    grille = np.round(np.arange(0.01, 1.0, 0.01), 2)
    ok = [s for s in grille if int((d["malade"] & (PL["roamer_dev_loin"] < s)).sum()) <= v2_rate]
    s = float(max(ok)) if ok else 0.01
    print(f"v2 seule sur les feuilles du roamer : {v2_rate} malades ratées ; seuil l1b retenu s = {s:.2f} "
          f"({int((d['malade'] & (PL['roamer_dev_loin'] < s)).sum())} ratées, {int((~d['malade'] & (PL['roamer_dev_loin'] >= s)).sum())} saines en alerte)")
    ref = M.reference_f1()
    proches, approx = proche_f1()
    lecteurs = {"F1": proches}
    if len(sys.argv) > 3:
        el, en = sys.argv[3].split(":")
        couple = tuple(json.loads((M.KAG / "lot1" / f"seuils2_{en[:2]}.json").read_text(encoding="utf-8"))["couple"])
        Pe = M.charger(M.KAG / el, en)
        lecteurs[en] = {j: maladies.decider_convnext(Ps[0] if j in ("tdtu", "ethiopie") and len(Ps) == 1 else np.mean(Ps, 0),
                                                     {**B.M_V10B, "seuil": couple[0]})[0] for j, Ps in Pe.items()}
    res = {"s": s, "v2_ratees_roamer": v2_rate, "agro_loin_sans_morceaux": approx}
    for nom, rps in lecteurs.items():
        for seul in (False, True):
            r = {}
            for j in M.TOUS:
                if j in PL and j in rps:
                    c = M.compter(j, chaine(rps[j], j, PL[j], s, seul))
                    c["cout"] = M.cout(c)
                    r[j] = c
            r["cout_reglage"] = float(np.mean([r[j]["cout"] for j in M.REGLAGE5]))
            v = r["validation"]
            conds = dict(cout=r["cout_reglage"] <= ref["cout_reglage"] - 1, tanzanie=v["msa"] <= 14 and v["sea"] <= 77,
                         pays=all(100 * (r[j]["msa"] / r[j]["nm"] - ref[j]["msa"] / ref[j]["nm"]) <= 2 for j in M.REGLAGE5),
                         roamer=r["roamer_dev_loin"]["msa"] <= ref["roamer_dev_loin"]["msa"] + 2)
            titre = f"{nom} + l1b{' seul' if seul else ' ou proche'}"
            print(M.ligne(titre, r)); print("   conditions :", conds)
            res[titre] = dict(bilan=r, conditions=conds)
    print("photos « loin » d'AgroVisionBD sans morceaux lus (approximation F1) :", approx)
    (dos / f"bilan_loin_{rec}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
