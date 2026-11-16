import sys, json
from pathlib import Path
R = Path(r"C:/00_DATA/02 - Cours/ING4/06 - intelligence lab/projet_field_scan/Field-Scan")
sys.path.insert(0, str(R / "scripts"))
import numpy as np, m13_banc_commun as C, m14_banc as MB
jeux = MB.charger(); MB.jeux_global = jeux; MB.lire_eleve(jeux, MB.KAG / "pour_banc/d3b", "d3b")
tot, n, out = 0, 0, {}
for j in C.JEUX5:
    d = jeux[j]; a0, _, inc = C.bornes(d, MB.f1)
    lire = (~d["loin"]) & (~a0 | inc)
    out[j] = dict(photos=len(a0), proches=int((~d["loin"]).sum()), d3b_a_lire=int(lire.sum()))
    tot += lire.sum(); n += len(a0)
out["part_5jeux"] = float(tot / n)
print(out)
(MB.SORTIE / "part_d3b_a_lire.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
