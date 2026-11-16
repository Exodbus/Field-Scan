#!/usr/bin/env python3
"""M-banc : critère `roamer_dev_loin_feuilles` de la règle 4.3 (malades sans alerte ≤ celles de F1 + 2) pour F1 et les
candidats MB1, sur les feuilles déjà lues. Les règles qui gardent la branche « loin » de F1 (v2 en alerte -> alerte)
sont mesurées sur « fait_f1 » ; les règles « loin = lecteur proche seul » sur « fait_tout » (F1 remesuré sur le même
masque). Écrit aussi la liste des feuilles dont les morceaux 2 x 2 sont nécessaires (bornes) : roamer/liste_g2.json.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_banc_roamer_eval.py
"""
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m13_banc_commun as C  # noqa: E402
import m13_banc_regles as R  # noqa: E402

d = C.charger_roamer()
CAND = [("F1", R.f1, "fait_f1"), ("F1", R.f1, "fait_tout")]
CAND += [(f"MB1-B proche seul tL={t}", R.mb1_b_proche(t), "fait_tout") for t in (0.65, 0.675, 0.70, 0.725)]
CAND += [(f"MB1-A tL={t}", R.mb1_a(t), "fait_f1") for t in (0.55, 0.60, 0.65)]
besoin = np.zeros(len(d["chemin"]), bool)
res = []
for nom, regle, masque in CAND:
    a, rep, inc = C.bornes(d, regle)
    m = d[masque]
    r = C.mesure(d, a, inc, m)
    besoin |= inc & m
    r.update(nom=nom, masque=masque)
    res.append(r)
    print(f"{nom:28s} [{masque}] malades sans alerte {r['msa']}/{r['nm']} ; saines en alerte {r['sea']}/{r['ns']} ; inconnues {r['inconnues']}", flush=True)
(C.ROAMER / "liste_g2.json").write_text(json.dumps([int(i) for i in np.flatnonzero(besoin)]), encoding="utf-8")
(C.SORTIE / "roamer_eval.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("morceaux à lire :", int(besoin.sum()))
