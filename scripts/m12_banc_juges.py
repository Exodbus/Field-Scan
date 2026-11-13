#!/usr/bin/env python3
"""Lecture unique des juges (BanSpot, Cordana du Pérou) pour les finalistes de M-banc, puis règle d'adoption (plan 4.4).

Les finalistes sont lus dans out/maladies/nuit_1112/banc/finalistes.json, écrit AVANT ce script (et recopié au journal).
Adoption proposée si : BanSpot, tachées sans alerte <= 12 / 646 et saines en alerte <= 61 / 646 ; Cordana du Pérou en
alerte >= 97 %. Entre finalistes qui passent : le coût de réglage le plus bas. Le script refuse de tourner deux fois.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/m12_banc_juges.py
"""
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402
import m12_banc_combinaisons as C  # noqa: E402

SORTIE = B.SORTIE / "juges.json"
assert not SORTIE.exists(), "les juges ont déjà été lus : une seule lecture"
finalistes = json.loads((B.SORTIE / "finalistes.json").read_text(encoding="utf-8"))
assert 1 <= len(finalistes) <= 3
juges = B.charger_juges()
bilan = {}
for f in [dict(nom="chaîne installée", lecteur="v10b", seuil=B.M_V10B["seuil"], loin="v2", cout_reglage=None)] + finalistes:
    r = {j: B.mesure(d, C.reponses(d, f["lecteur"], f["seuil"], f["loin"])) for j, d in juges.items()}
    b, c = r["banspot"], r["cordana_perou"]
    part = 1 - c["msa"] / c["nm"]
    passe = bool(b["msa"] <= 12 and b["sea"] <= 61 and part >= 0.97)
    rep_c = C.reponses(juges["cordana_perou"], f["lecteur"], f["seuil"], f["loin"])
    bilan[f["nom"]] = dict(definition=f, banspot_tachees_sans_alerte=f"{b['msa']}/{b['nm']}",
                           banspot_saines_en_alerte=f"{b['sea']}/{b['ns']}", banspot_saines_a_verifier=b["sea_averif"],
                           cordana_en_alerte=f"{c['nm'] - c['msa']}/{c['nm']}", cordana_part=round(part, 4),
                           cordana_dite_sigatoka=int((rep_c == "cercosporiose_noire").sum()), adoption_possible=passe)
    print(f"{f['nom']}\n   BanSpot : tachées sans alerte {b['msa']}/{b['nm']} (limite 12), saines en alerte {b['sea']}/{b['ns']}"
          f" (limite 61, dont {b['sea_averif']} à vérifier) ; Cordana en alerte {c['nm'] - c['msa']}/{c['nm']} = {100 * part:.1f} %"
          f" (limite 97 %), dite Sigatoka {bilan[f['nom']]['cordana_dite_sigatoka']} -> {'PASSE' if passe else 'ne passe pas'}", flush=True)
ok = [f for f in finalistes if bilan[f["nom"]]["adoption_possible"]]
gagnant = min(ok, key=lambda f: f["cout_reglage"])["nom"] if ok else None
bilan["verdict"] = gagnant or "aucune adoption proposée"
print("verdict :", bilan["verdict"])
SORTIE.write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
