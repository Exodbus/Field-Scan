#!/usr/bin/env python3
"""Bilan du Juge maladies (nuit du 13/11) : témoin F1, F1_bornes et d3b sur les juges relus, règle 4.3 telle qu'écrite.

Entrées : caches du 13/11 (out/controle_nuit_1112/juge_m) et lecture de d3b (out/controle_nuit_1311/juge_m/p_d3b_*.npy).
Décisions : m13_banc_finalistes (F1 = code installé, F1_bornes) et m13_entr_seuils2.reponse2 (d3b, couple 0,50 / 0,70),
importés sans modification. Sorties : bilan.json, reponses_<jeu>.csv (probabilités et décisions par photo).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_1311_m_bilan.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import juge_1311_m_juges as JG  # noqa: E402
import m12_banc_commun as B  # noqa: E402
from fieldscan.modules import maladies  # noqa: E402

AL = list(B.ALERTE)
LIMITES = dict(msa=6, sea=56, cordana=0.97)
COUT_REGLAGE = {"d3b": 32.77, "F1_bornes": 33.94}


def compte(mal, rep):
    rep = np.asarray(rep, dtype=object)
    al = np.isin(rep, AL)
    return dict(msa=int((mal & ~al).sum()), nm=int(mal.sum()), sea=int((~mal & al).sum()), ns=int((~mal).sum()),
                sea_averif=int((~mal & (rep == "a_verifier")).sum()), inconnues=int(np.isin(rep, ["inconnue", "inconnue_lire_morceaux"]).sum()),
                noms_tachees=dict(Counter(rep[mal].tolist())), noms_saines=dict(Counter(rep[~mal].tolist())))


def mesurer(C, reps):
    out = {}
    for j in JG.JEUX:
        d, rep = C[j], reps[j]
        out[j] = compte(d["malade"], rep)
        out[j]["par_ferme"] = {f: compte(d["malade"][d["ferme"] == f], rep[d["ferme"] == f]) for f in sorted(set(d["ferme"]))}
    b, c = out["banspot"], out["cordana_perou"]
    c["en_alerte"] = c["nm"] - c["msa"]
    c["taux_alerte"] = c["en_alerte"] / c["nm"]
    conds = dict(banspot_tachees=b["msa"] <= LIMITES["msa"], banspot_saines=b["sea"] <= LIMITES["sea"],
                 cordana=c["taux_alerte"] >= LIMITES["cordana"])
    out["conditions"] = conds
    out["passe"] = bool(all(conds.values()) and b["inconnues"] == 0 and c["inconnues"] == 0)
    # bornes si des décisions sont inconnues (« inconnue » est compté sans alerte dans msa / sea)
    it_b = b["noms_tachees"].get("inconnue", 0)
    is_b = b["noms_saines"].get("inconnue", 0)
    it_c = c["noms_tachees"].get("inconnue", 0)
    bo = dict(banspot_msa=(b["msa"] - it_b, b["msa"]), banspot_sea=(b["sea"], b["sea"] + is_b),
              cordana_alerte=(c["en_alerte"], c["en_alerte"] + it_c))
    pire = bo["banspot_msa"][1] <= 6 and bo["banspot_sea"][1] <= 56 and bo["cordana_alerte"][0] >= 0.97 * c["nm"]
    meilleur = bo["banspot_msa"][0] <= 6 and bo["banspot_sea"][0] <= 56 and bo["cordana_alerte"][1] >= 0.97 * c["nm"]
    out["bornes"] = bo
    out["verdict"] = "PASSE" if pire else ("NE PASSE PAS" if not meilleur else "indéterminé")
    return out


def main():
    C, R = JG.f1_et_bornes()
    M, S2 = JG._decision_d3b()
    reps = {"F1": {}, "F1_bornes": {}, "d3b": {}}
    lignes = {}
    for j in JG.JEUX:
        d = C[j]
        fp = JG.J / f"p_d3b_{j}.npy"
        P = np.load(fp).astype("float64") if fp.exists() else np.full((len(d["p_loin"]), 4), np.nan)
        manque = np.isnan(P).any(1)
        # entrée du jeu dans le dictionnaire de M-entraîneur, construite comme m13_entr_mesurer._jeux
        M.JEUX[j] = dict(chemin=list(d["photo"]), malade=d["malade"], loin=d["p_loin"] >= 0.5, Pv2=d["Pv2"],
                         r_loin=maladies.decider_convnext(d["Pv2"], B.M_V2)[0])
        # photos non encore lues : bornes « saine 100 % » / « malade 100 % » (alerte inconnue si elles diffèrent)
        rs = S2.reponse2(j, np.where(manque[:, None], [1.0, 0, 0, 0], P), *JG.COUPLE).astype(object)
        rm = S2.reponse2(j, np.where(manque[:, None], [0.0, 1.0, 0, 0], P), *JG.COUPLE).astype(object)
        rd = rs.copy()
        rd[np.isin(rs, AL) != np.isin(rm, AL)] = "inconnue"   # ailleurs, photo non lue : alerte fixée (ex. loin + v2)
        print(f"d3b {j} : {int((~manque).sum())} photos lues, {int(manque.sum())} non lues")
        reps["F1"][j], reps["F1_bornes"][j], reps["d3b"][j] = R[j]["f1"], R[j]["f1_bornes"], rd
        df = pd.DataFrame(dict(photo=d["photo"], ferme=d["ferme"], malade=d["malade"].astype(int), p_loin=d["p_loin"]))
        for k, nom in (("P10", "v10b"), ("Pso", "soupe"), ("Pv2", "v2")):
            for c in range(d[k].shape[1]):
                df[f"{nom}_{c}"] = d[k][:, c]
        df["morceaux_lus"] = (~np.isnan(d["G2"][:, :, 0]).any(1)).astype(int)
        df["f1_bornes_lit_morceaux"] = R[j]["dep"].astype(int)
        for c in range(4):
            df[f"d3b_{c}"] = P[:, c]
        df["rep_F1"], df["rep_F1_haut"], df["rep_F1_bornes"], df["rep_d3b"] = R[j]["f1"], R[j]["f1_haut"], R[j]["f1_bornes"], rd
        for nom in ("F1", "F1_bornes", "d3b"):
            df[f"alerte_{nom}"] = np.isin(df[f"rep_{nom}"].to_numpy(dtype=object), AL).astype(int)
        df.to_csv(JG.J / f"reponses_{j}.csv", index=False)
        lignes[j] = df
    bilan = {nom: mesurer(C, reps[nom]) for nom in reps}
    # F1_bornes contre F1 : alertes et libellés
    cmp = {}
    for j in JG.JEUX:
        a, b = reps["F1"][j], reps["F1_bornes"][j]
        cmp[j] = dict(alertes_differentes=int((np.isin(a, AL) != np.isin(b, AL)).sum()), libelles_differents=int((a != b).sum()),
                      changements=dict(Counter(f"{x} -> {y}" for x, y in zip(a, b) if x != y)),
                      photos_morceaux=int(R[j]["dep"].sum()))
        a, b = reps["F1"][j], reps["d3b"][j]
        cmp[j]["d3b_alertes_differentes_F1"] = int((np.isin(a, AL) != np.isin(b, AL)).sum())
        mal = C[j]["malade"]
        cmp[j]["d3b_malades_perdues_vs_F1"] = int((mal & np.isin(a, AL) & ~np.isin(b, AL)).sum())
        cmp[j]["d3b_malades_gagnees_vs_F1"] = int((mal & ~np.isin(a, AL) & np.isin(b, AL)).sum())
    bilan["comparaisons"] = cmp
    passent = [n for n in ("d3b", "F1_bornes") if bilan[n]["verdict"] == "PASSE"]
    bilan["finalistes_qui_passent"] = passent
    bilan["adoption_proposee"] = min(passent, key=lambda n: COUT_REGLAGE[n]) if passent else None
    (JG.J / "bilan.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
    for nom in ("F1", "F1_bornes", "d3b"):
        b, c = bilan[nom]["banspot"], bilan[nom]["cordana_perou"]
        fe = " | ".join(f"{f} {v['msa']}/{v['nm']} ; {v['sea']}/{v['ns']}" for f, v in b["par_ferme"].items())
        print(f"{nom:10s} BanSpot {b['msa']}/{b['nm']} ; {b['sea']}/{b['ns']} (à vérifier {b['sea_averif']}) [{fe}] ; "
              f"Cordana {c['en_alerte']}/{c['nm']} ({100 * c['taux_alerte']:.1f} %) ; inconnues {b['inconnues']}+{c['inconnues']} "
              f"-> {bilan[nom]['verdict']} {bilan[nom]['bornes']}")
    print("comparaisons :", json.dumps(cmp, ensure_ascii=False))
    print("adoption proposée :", bilan["adoption_proposee"])


if __name__ == "__main__":
    main()
