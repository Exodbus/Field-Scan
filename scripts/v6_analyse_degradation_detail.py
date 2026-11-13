#!/usr/bin/env python3
"""Détail de la simulation de dégradation (agent C-analyste) : F1 sur les seules images aiguillées et non aiguillées,
quantiles du p90 du v5. Lit out/comptage/analyse/degradation_images.csv ; écrit degradation_detail.md.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/v6_analyse_degradation_detail.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import v6_banc_commun as bc  # noqa: E402

S = RACINE / "out/comptage/analyse"
D = pd.read_csv(S / "degradation_images.csv")
M = ["v5", "E10_p90_v6b_v5_d0.1", "E5p90b_moy34_v5_d0.1"]


def f1(g, m):
    vp, fp, fn, det = (g[f"{m}_{k}"].sum() for k in ("vp", "fp", "fn", "det"))
    return bc.prf(vp, fp, fn)[2], det / max(vp + fn, 1)


out = ["# Détail : images aiguillées ou non [M]\n", "`scripts/v6_analyse_degradation_detail.py`\n",
       "| cm/px | jeu | groupe | images | annotés | F1 v5 (dét./ann.) | F1 E10 | F1 E5p90b |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
for (cm, j), g in D.groupby(["cm", "jeu"]):
    for nom, h in (("aiguillées", g[g.aiguillee]), ("non aiguillées", g[~g.aiguillee])):
        if not len(h):
            continue
        c = [f1(h, m) for m in M]
        out.append(f"| {cm:g} | {j} | {nom} | {len(h)} | {h.annotes.sum()} | {c[0][0]:.3f} ({c[0][1]:.2f}) | "
                   f"{c[1][0]:.3f} ({c[1][1]:.2f}) | {c[2][0]:.3f} ({c[2][1]:.2f}) |")
out.append("\n## p90 du v5 par image (quantiles 10 / 50 / 90 %)\n\n| cm/px | jeu | à 5 cm (cache) | dégradé |\n| --- | --- | --- | --- |")
q = lambda s: " / ".join(f"{v:.2f}" for v in np.nanpercentile(s, [10, 50, 90]))
for (cm, j), g in D.groupby(["cm", "jeu"]):
    out.append(f"| {cm:g} | {j} | {q(g.p90_5cm)} | {q(g.p90)} |")
(S / "degradation_detail.md").write_text("\n".join(out) + "\n", encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8"); print("\n".join(out))
