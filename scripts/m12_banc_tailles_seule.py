#!/usr/bin/env python3
"""Suite de l'essai « tailles » : v10b SEULE lue en 224 px (AUC 0,926 en TDTU et en Éthiopie, contre 0,897 et 0,879 en
384), branche loin installée (v2) ou « v2 ou proche ». Réglage seul."""
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402
import m12_banc_tailles as T  # noqa: E402

ESSAIS = []
for loin_ou in (False, True):
    print(f"\n--- v10b seule en 224 px, loin {'« v2 ou proche »' if loin_ou else 'v2'} ---")
    for t in [round(x, 2) for x in np.arange(0.40, 0.801, 0.04)]:
        r = {}
        for j, d in T.jeux.items():
            rp = B.decider_v10b(d["p224"], seuil=t)
            rl = np.where(np.isin(d["r_loin"], list(B.ALERTE)), d["r_loin"], rp) if loin_ou else d["r_loin"]
            r[j] = B.mesure(d, np.where(d["loin"], rl, rp))
        r["cout_moyen"] = float(np.mean([r[j]["cout"] for j in T.jeux]))
        ok, det = B.finaliste(r, T.ref)
        ESSAIS.append(dict(famille="tailles seule", nom=f"v10b 224 loin_ou={loin_ou} t={t}", finaliste=ok, detail=det, **r))
        print(("F " if ok else "  ") + B.ligne(f"t={t}", r), flush=True)
print("essais :", len(ESSAIS))
(B.SORTIE / "essais_tailles_seule.json").write_text(json.dumps(ESSAIS, ensure_ascii=False, indent=1), encoding="utf-8")
