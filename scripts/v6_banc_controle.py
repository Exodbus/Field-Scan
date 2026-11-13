#!/usr/bin/env python3
"""Étape 0 : le banc redonne-t-il les chiffres de validation du v5 (seuil 0,30) et du v4 (seuil 0,40) à 0,005 près ?"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v6_banc_commun as bc  # noqa: E402

ATTENDU = {"v5": (0.30, dict(dense=0.7767, plantain=0.8846, jeunes=0.8926, mm=0.8571), 17),
           "v4": (0.40, dict(dense=0.718, plantain=0.8929, jeunes=0.8889, mm=0.7891), 7)}
JEUX = ["dense", "plantain", "jeunes", "mm"]
bilan, ok = {}, True
for v in ("v5", "v4", "v3"):
    m = bc.mesurer(bc.cand_modele(v), JEUX)
    bilan[v] = {j: {str(s): r for s, r in m[j].items()} for j in m}
    if v in ATTENDU:
        s, att, fp = ATTENDU[v]
        for j in JEUX:
            r = m[j][s]
            e = r["f1"] - att[j]
            ok &= abs(e) <= 0.005
            print(f"{v} seuil {s} {j:9s} F1 {r['f1']:.4f} (attendu {att[j]:.4f}, écart {e:+.4f}) P {r['p']:.3f} R {r['r']:.3f} "
                  f"{r['detectes']} détectés / {r['reels']} annotés")
        print(f"{v} seuil {s} sans bananier : {m['neg'][s]['fp']} (attendu {fp}) / {m['neg'][s]['arbres']} arbres")
        ok &= m["neg"][s]["fp"] == fp
    else:
        for s in bc.SEUILS:
            print(f"v3 seuil {s} : " + ", ".join(f"{j} {m[j][s]['f1']:.3f}" for j in JEUX) + f" ; sans bananier {m['neg'][s]['fp']}")
(bc.SORTIE / "controle_banc.json").write_text(json.dumps(bilan, indent=1), encoding="utf-8")
print("CONTRÔLE DU BANC :", "CONFORME" if ok else "ÉCART")
