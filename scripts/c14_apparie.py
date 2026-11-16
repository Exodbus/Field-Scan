#!/usr/bin/env python3
"""Comparaison appariée image par image de deux candidats au même seuil (agent C-piste2, 14/11) : information
seulement, aucun choix. Pour chaque jeu de réglage : VP, FP, FN par image, puis écart de F1 (B − A) et intervalle
bootstrap à 95 % en tirant les images avec remise (2 000 tirages, graine 0). Code de mesure du banc (mesurer_jeu).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c14_apparie.py v5:0.30 CC1_v5h_50:0.30
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import numpy as np  # noqa: E402

import c14_essais as ce  # noqa: E402

cc, bc = ce.cc, ce.bc


def par_image(nom, seuil, j):
    f = ce.construire(nom)
    out = []
    for e in cc.jeu(j):
        r = bc.mesurer_jeu(f, j, [e])[seuil]
        out.append((r["vp"], r["fp"], r["fn"]))
    return np.array(out, "float64")


def f1(t):
    vp, fp, fn = t.sum(0)
    return 2 * vp / max(2 * vp + fp + fn, 1)


def main():
    (a, sa), (b, sb) = [(x.split(":")[0], float(x.split(":")[1])) for x in sys.argv[1:3]]
    rng = np.random.default_rng(0)
    res = {}
    for j in cc.REGLAGE:
        A, B = par_image(a, sa, j), par_image(b, sb, j)
        d = f1(B) - f1(A)
        n = len(A)
        boot = []
        if n > 1:
            for _ in range(2000):
                i = rng.integers(0, n, n)
                boot.append(f1(B[i]) - f1(A[i]))
        lo, hi = (np.percentile(boot, [2.5, 97.5]) if boot else (np.nan, np.nan))
        gagne = int(((B[:, 0] - B[:, 1] - B[:, 2]) > (A[:, 0] - A[:, 1] - A[:, 2])).sum())
        perd = int(((B[:, 0] - B[:, 1] - B[:, 2]) < (A[:, 0] - A[:, 1] - A[:, 2])).sum())
        res[j] = dict(n_images=n, f1_a=f1(A), f1_b=f1(B), ecart=d, ic95=[float(lo), float(hi)],
                      vp_fp_fn_a=A.sum(0).astype(int).tolist(), vp_fp_fn_b=B.sum(0).astype(int).tolist(),
                      images_mieux=gagne, images_moins_bien=perd)
        print(f"{j}: {n} images, F1 {f1(A):.4f} -> {f1(B):.4f} (écart {d:+.4f}, IC95 [{lo:+.4f} ; {hi:+.4f}]) "
              f"VP/FP/FN {A.sum(0).astype(int).tolist()} -> {B.sum(0).astype(int).tolist()} ; images mieux {gagne}, moins bien {perd}", flush=True)
    p = ce.SORTIE / f"apparie_{a}_{b}.json".replace(":", "")
    p.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
