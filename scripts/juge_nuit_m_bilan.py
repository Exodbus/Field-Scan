#!/usr/bin/env python3
"""Juge maladies, nuit du 12/11 : bilan des juges pour la liste gelée, à partir des probabilités déjà calculées
(out/controle_nuit_1112/juge_m/), et deuxième avis par scripts/controle_nuit_m_appliquer.py (code du Contrôleur).

Pour chaque finaliste : BanSpot par ferme et au total, Cordana du Pérou, verdict de la règle 4.4. Les photos dont la
lecture a été évitée (borne exacte) ou n'a pas pu être faite (temps) sont remplies de deux façons (« moins d'alertes »,
« plus d'alertes ») : si les deux donnent la même décision, elle est certaine ; sinon la photo est « inconnue ».
Le deuxième avis est passé sur les deux remplissages : il doit redonner les mêmes alertes que ce script.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_nuit_m_bilan.py
"""
import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")   # -I ignore PYTHONIOENCODING

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import juge_nuit_m_juges as JJ  # noqa: E402
import m12_banc_commun as B  # noqa: E402

J = JJ.J
NOMS = ["F1_trois_morceaux2x2", "C_quatre_v12a14", "v12a13"]
COUT_REGLAGE = {"F1_trois_morceaux2x2": 35.958, "C_quatre_v12a14": 36.072, "v12a13": 41.498}
ARG = {"F1_trois_morceaux2x2": "v10b_g2", "C_quatre_v12a14": "v12a14", "v12a13": "v12a13"}


def compte(mal, al, ferme=None):
    s = np.ones(len(mal), bool) if ferme is None else ferme
    return dict(msa=int((mal & ~al & s).sum()), nm=int((mal & s).sum()), sea=int((~mal & al & s).sum()), ns=int((~mal & s).sum()))


def main():
    z = JJ.charger()
    bilan, ecarts = {}, {}
    temoin = json.loads((J / "temoin.json").read_text(encoding="utf-8"))
    for nom in NOMS:
        par, rep_tab = {}, {}
        for j in JJ.JEUX:
            d, lo, hi, inc = JJ.remplis(z, j, nom)
            r_lo, r_hi = JJ.repondre_nom(d, nom, lo), JJ.repondre_nom(d, nom, hi)
            a_lo, a_hi = JJ.alertes(r_lo), JJ.alertes(r_hi)
            mal = d["malade"].astype(bool)
            inconnue = a_lo != a_hi
            res = dict(lues=int((~inc).sum()), evitees_ou_non_lues=int(inc.sum()), inconnues=int(inconnue.sum()),
                       min=compte(mal, a_lo), max=compte(mal, a_hi))
            # min : le moins d'alertes (ratées max, fausses alertes min) ; max : l'inverse
            if j == "banspot":
                res["par_ferme"] = {f: dict(min=compte(mal, a_lo, d["ferme"] == f), max=compte(mal, a_hi, d["ferme"] == f))
                                    for f in sorted(set(d["ferme"]))}
                res["saines_a_verifier"] = int((~mal & (r_lo == "a_verifier")).sum())
            else:
                res["dite_sigatoka"] = int((r_lo == "cercosporiose_noire").sum())
            res["reponses_malades"] = pd.Series(r_lo[mal]).value_counts().to_dict()
            res["reponses_saines"] = pd.Series(r_lo[~mal]).value_counts().to_dict()
            par[j] = res
            rep_tab[j] = (r_lo, r_hi, a_lo, a_hi, lo, hi, d)
        b, c = par["banspot"], par["cordana_perou"]
        pire = b["min"]["msa"] <= 12 and b["max"]["sea"] <= 61 and 1 - c["min"]["msa"] / c["min"]["nm"] >= 0.97
        meilleur = b["max"]["msa"] <= 12 and b["min"]["sea"] <= 61 and 1 - c["max"]["msa"] / c["max"]["nm"] >= 0.97
        verdict = "PASSE" if pire else ("NE PASSE PAS" if not meilleur else "indéterminé (photos non lues)")
        bilan[nom] = dict(par=par, verdict=verdict, cout_reglage=COUT_REGLAGE[nom])
        # deuxième avis : code du Contrôleur sur les deux remplissages
        ecarts[nom] = {}
        for j in JJ.JEUX:
            r_lo, r_hi, a_lo, a_hi, lo, hi, d = rep_tab[j]
            dos = J / "second_avis" / j
            dos.mkdir(parents=True, exist_ok=True)
            np.save(dos / "v10b.npy", d["P10"]); np.save(dos / "soupe.npy", d["Pso"]); np.save(dos / "v2.npy", d["Pv2"])
            np.save(dos / "loin.npy", d["p_loin"])
            pd.DataFrame({"malade": d["malade"].astype(int)}).to_csv(dos / "verite.csv", index=False)
            for cote, P, a in (("lo", lo, a_lo), ("hi", hi, a_hi)):
                np.save(dos / f"{nom}_{cote}.npy", P)
                sortie = dos / f"alertes_{nom}_{cote}.csv"
                cmd = [sys.executable, "-I", "-u", str(RACINE / "scripts/controle_nuit_m_appliquer.py"),
                       "--v10b", str(dos / "v10b.npy"), "--soupe", str(dos / "soupe.npy"), "--v2", str(dos / "v2.npy"),
                       "--loin", str(dos / "loin.npy"), f"--{ARG[nom]}", str(dos / f"{nom}_{cote}.npy"), "--sortie", str(sortie)]
                subprocess.run(cmd, check=True, capture_output=True, env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
                ctrl = pd.read_csv(sortie)
                col = "F1_trois_morceaux2x2" if nom.startswith("F1") else nom
                ecarts[nom][f"{j}_{cote}"] = int((ctrl[col].astype(bool).to_numpy() != a).sum())
                if nom.startswith("F1"):
                    ecarts.setdefault("reference_v10b", {})[f"{j}_{cote}"] = int(
                        (ctrl["reference_v10b"].astype(bool).to_numpy() != JJ.alertes(
                            JJ.MF.repondre(d["P10"], d["Pso"], d["Pv2"], d["p_loin"], JJ.MF.CANDIDATS["installee"]))).sum())
        bilan[nom]["ecarts_second_avis"] = ecarts[nom]
    passent = [n for n in NOMS if bilan[n]["verdict"] == "PASSE"]
    bilan["second_avis_temoin"] = ecarts.get("reference_v10b")
    bilan["temoin"] = temoin
    bilan["passent"] = passent
    (J / "bilan.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1, default=int), encoding="utf-8")
    for n in NOMS:
        b, c = bilan[n]["par"]["banspot"], bilan[n]["par"]["cordana_perou"]
        print(f"{n} : BanSpot ratées {b['max']['msa']}..{b['min']['msa']}/{b['min']['nm']} ; fausses alertes "
              f"{b['min']['sea']}..{b['max']['sea']}/{b['min']['ns']} ; Cordana ratées {c['max']['msa']}..{c['min']['msa']}/{c['min']['nm']} ; "
              f"inconnues {b['inconnues']}+{c['inconnues']} ; lues {b['lues']}+{c['lues']} -> {bilan[n]['verdict']} ; second avis {ecarts[n]}")
    print("témoin, second avis :", bilan["second_avis_temoin"])
    print("passent :", passent)


if __name__ == "__main__":
    main()
