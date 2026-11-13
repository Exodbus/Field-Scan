#!/usr/bin/env python3
"""Juge maladies, nuit du 12/11 : tableaux du rapport out/controle_nuit_1112/juge_maladies.md, à partir de
out/controle_nuit_1112/juge_m/bilan.json (écrit par juge_nuit_m_bilan.py). Écrit juge_m/tableaux.md, que le Juge
recopie dans le rapport.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_nuit_m_rapport.py
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")   # -I ignore PYTHONIOENCODING

RACINE = Path(__file__).resolve().parents[1]
J = RACINE / "out/controle_nuit_1112/juge_m"
b = json.loads((J / "bilan.json").read_text(encoding="utf-8"))


def intervalle(lo, hi):
    return f"{lo}" if lo == hi else f"{lo} à {hi}"


L = []
t = b["temoin"]
L.append("| Chaîne installée (témoin) | BanSpot PER_NKA | BanSpot PER_RDMI | BanSpot total | Cordana du Pérou en alerte |")
L.append("| --- | --- | --- | --- | --- |")
pf = t["banspot"]["par_ferme"]
L.append(f"| tachées sans alerte ; saines en alerte | {pf['PER_NKA']['msa']}/{pf['PER_NKA']['nm']} ; {pf['PER_NKA']['sea']}/{pf['PER_NKA']['ns']} | "
         f"{pf['PER_RDMI']['msa']}/{pf['PER_RDMI']['nm']} ; {pf['PER_RDMI']['sea']}/{pf['PER_RDMI']['ns']} | "
         f"**{t['banspot']['msa']}/{t['banspot']['nm']} ; {t['banspot']['sea']}/{t['banspot']['ns']}** ({t['banspot']['sea_averif']} à vérifier) | "
         f"{t['cordana_perou']['nm'] - t['cordana_perou']['msa']}/{t['cordana_perou']['nm']} "
         f"({100 * (1 - t['cordana_perou']['msa'] / t['cordana_perou']['nm']):.1f} %) |")
L.append("")
for nom in ["F1_trois_morceaux2x2", "C_quatre_v12a14", "v12a13"]:
    r = b[nom]
    bs, c = r["par"]["banspot"], r["par"]["cordana_perou"]
    L.append(f"### {nom} (coût de réglage {r['cout_reglage']:.2f})")
    L.append("")
    L.append(f"Photos lues pour ce finaliste : BanSpot {bs['lues']}, Cordana {c['lues']} ; décisions fixées par borne exacte ou "
             f"non lues : {bs['evitees_ou_non_lues']} + {c['evitees_ou_non_lues']} ; **décisions encore inconnues : "
             f"{bs['inconnues']} + {c['inconnues']}**.")
    L.append("")
    L.append("| Mesure | Limite (4.4) | PER_NKA | PER_RDMI | BanSpot total | Cordana du Pérou |")
    L.append("| --- | --- | --- | --- | --- | --- |")
    nk, rd = bs["par_ferme"]["PER_NKA"], bs["par_ferme"]["PER_RDMI"]
    L.append(f"| tachées sans alerte | ≤ 12 / 646 | {intervalle(nk['max']['msa'], nk['min']['msa'])}/{nk['min']['nm']} | "
             f"{intervalle(rd['max']['msa'], rd['min']['msa'])}/{rd['min']['nm']} | **{intervalle(bs['max']['msa'], bs['min']['msa'])}/{bs['min']['nm']}** | — |")
    L.append(f"| saines en alerte | ≤ 61 / 646 | {intervalle(nk['min']['sea'], nk['max']['sea'])}/{nk['min']['ns']} | "
             f"{intervalle(rd['min']['sea'], rd['max']['sea'])}/{rd['min']['ns']} | **{intervalle(bs['min']['sea'], bs['max']['sea'])}/{bs['min']['ns']}** | — |")
    n = c["min"]["nm"]
    lo, hi = n - c["min"]["msa"], n - c["max"]["msa"]
    L.append(f"| Cordana en alerte | ≥ 97 % (≥ 490 / 505) | — | — | — | **{intervalle(lo, hi)}/{n}** "
             f"({100 * lo / n:.1f} %{'' if lo == hi else f' à {100 * hi / n:.1f} %'}) |")
    L.append("")
    L.append(f"Saines BanSpot « à vérifier » (remplissage bas) : {bs['saines_a_verifier']} ; Cordana dite Sigatoka : {c['dite_sigatoka']}. "
             f"**Verdict de la règle : {r['verdict']}.** Deuxième avis (écarts de décision, remplissages bas / haut) : {r['ecarts_second_avis']}.")
    L.append("")
L.append(f"Passent la règle : {b['passent'] or 'aucun'}. Deuxième avis sur le témoin : {b['second_avis_temoin']}.")
(J / "tableaux.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
