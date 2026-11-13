#!/usr/bin/env python3
"""Pour information seulement (décision du chef d'orchestre : la référence garde les doublons) : F1 du plantain quand
l'un des deux points de chaque paire d'annotations à moins de 3 px est retiré."""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v6_banc_commun as bc  # noqa: E402
import v6_banc_candidats as ca  # noqa: E402
import v6_banc_essais as es  # noqa: E402

items, n_ret = [], 0
for e in bc.jeu("plantain"):
    p = e["pts"]
    garde = np.ones(len(p), bool)
    if len(p) > 1:
        for i, j in sorted(cKDTree(p).query_pairs(3.0)):
            if garde[i] and garde[j]:
                garde[j] = False
    n_ret += int((~garde).sum())
    items.append(dict(e, pts=p[garde]))
E = es.charger()
tab = {l["nom"]: l for l in json.loads((bc.SORTIE / "tableau_reglage.json").read_text(encoding="utf-8"))["lignes"]}
print(f"points retirés : {n_ret}")
for nom, s in [("v5", 0.30), ("v5", 0.20)] + [(n, tab[n]["seuil"]) for n in sys.argv[1:]]:
    e = E[nom]
    f = ca.construire(e["fabrique"], e["reglages"])
    a = bc.mesurer_jeu(f, "plantain")[s]
    b = bc.mesurer_jeu(f, "plantain", items)[s]
    print(f"{nom:28s} seuil {s:.2f} : F1 plantain {a['f1']:.3f} avec doublons, {b['f1']:.3f} sans (rappel {a['r']:.3f} -> {b['r']:.3f})")
