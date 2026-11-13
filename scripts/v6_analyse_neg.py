#!/usr/bin/env python3
"""Fausses détections sur les images sans bananier de validation (agent C-analyste) : par groupe (cocotiers, palmiers),
par modèle à son seuil, scores ; écrit neg_<modèle>.csv et une planche des 24 plus fortes.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/v6_analyse_neg.py --modeles v5 v3 v4
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import v6_analyse_erreurs as ae  # noqa: E402
import v6_analyse_planches as pl  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("--modeles", nargs="+", default=["v5", "v3", "v4"])
a = ap.parse_args()
sys.stdout.reconfigure(encoding="utf-8")
items = {e["nom"]: e for e in ae.bc.jeu("neg")}
arbres = {}
for e in items.values():
    g = e["nom"].split("_")[0]; arbres[g] = arbres.get(g, 0) + e["n_autres"]
print("arbres par groupe :", arbres, "tuiles :", len(items))
for m in a.modeles:
    s = ae.SEUILS_ADOPTES[m]
    N = ae.analyser_neg(m, s)
    N.to_csv(ae.SORTIE / f"neg_{m}.csv", index=False)
    par = N.groupby("groupe").size().to_dict() if len(N) else {}
    print(f"{m} seuil {s} : {len(N)} fausses sur {len(N.image.unique()) if len(N) else 0} tuiles ; par groupe {par} ; "
          f"scores médiane {N.score.median():.2f} max {N.score.max():.2f}" if len(N) else f"{m} : 0")
    if m == "v5" and len(N):
        top = N.sort_values("score", ascending=False).head(24)
        T = 2 * pl.DEMI * pl.ZOOM
        P = Image.new("RGB", (6 * T + 20, 4 * T + 12), (40, 40, 40))
        for k, r in enumerate(top.itertuples()):
            img = ae.bc.lire(items[r.image]["chemin"])
            v = pl.vignette(img, r.x, r.y, np.zeros((0, 2)), np.zeros((0, 2)), np.array([[r.x, r.y]]), np.zeros((0, 2)), f"{r.groupe} {r.score:.2f}")
            P.paste(v, ((k % 6) * (T + 4), (k // 6) * (T + 4)))
        P.save(ae.SORTIE / "planches" / "fausses_v5_sans_bananier.jpg", quality=88)
