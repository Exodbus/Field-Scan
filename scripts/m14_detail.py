#!/usr/bin/env python3
"""M-piste2 : description de MC1-OU-proche (pas un essai) : malades rattrapées par maladie, libellés des alertes ajoutées,
saines ajoutées en alerte, par jeu. Aucun juge.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m14_detail.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m13_banc_commun as C  # noqa: E402
import m14_banc as MB  # noqa: E402

jeux = MB.charger()
MB.jeux_global = jeux
MB.lire_eleve(jeux, MB.KAG / "pour_banc/d3b", "d3b")
out = {}
for j in MB.TOUS:
    d = jeux[j]
    a0, r0, _ = C.bornes(d, MB.f1)
    a1, r1, _ = C.bornes(d, MB.mc1_ou_proche)
    ratt = d["malade"] & a1 & ~a0
    sai = ~d["malade"] & a1 & ~a0
    out[j] = dict(malades_rattrapees=int(ratt.sum()), par_maladie=dict(Counter(map(str, d["vraie"][ratt]))),
                  ratees_F1_par_maladie=dict(Counter(map(str, d["vraie"][d["malade"] & ~a0]))),
                  libelles_ajoutes_malades=dict(Counter(map(str, r1[ratt]))),
                  saines_ajoutees=int(sai.sum()), libelles_ajoutes_saines=dict(Counter(map(str, r1[sai]))))
    print(j, json.dumps(out[j], ensure_ascii=False))
(MB.SORTIE / "detail_mc1_ou_proche.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
