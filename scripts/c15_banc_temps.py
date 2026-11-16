#!/usr/bin/env python3
"""Temps par tuile, de bout en bout (lecture faite hors chrono, cartes ONNX, mélange, pics), du v5 et des candidats
de l'agent C-banc (15/11), sur le même échantillon que scripts/c14_temps.py (30 tuiles par jeu : dense, plantain,
btd_val, val_negatifs). Réglage seulement (lecture gardée par c13_banc_commun.jeu).

Candidats chronométrés : v5, CC1_v5h_50 (deux cartes entières), S70_v5h_50 et S50_v5h_50 (c13h sur l'image réduite),
B1_bloc64 et B2_bloc32 (c13h calculé par morceaux, seulement sur les blocs où le v5 hésite, avec une marge de 64 px ;
si plus de la moitié des blocs hésitent, la carte entière est calculée).
Contrôle : points de chaque calcul réel comparés à ceux du banc (cartes en cache) ; pour B, l'écart vient de la marge.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c15_banc_temps.py --fils 2 --n 30
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import cv2  # noqa: E402
import numpy as np  # noqa: E402

import c15_banc_essais as ess  # noqa: E402
from c15_banc_cache import carte_reduite as reduite_img  # noqa: E402

ce, cc, bc = ess.ce, ess.cc, ess.bc
MARGE = 64


def carte_c13h_blocs(sh, img, c5, taille):
    """Carte de c13h calculée seulement sur les blocs hésitants (+ marge), à zéro ailleurs (non utilisée ailleurs)."""
    m, nh, n = ess.blocs_hesitants(c5, taille)
    if nh == 0:
        return None, m, 0.0
    if nh > n / 2:
        return bc.cartes_image(sh, img, "base")["base"], m, 1.0
    H, W = c5.shape
    ch = np.zeros((H, W), "float32")
    h, w = img.shape[:2]
    px = taille * bc.STRIDE
    calc = 0
    for bj in range((H + taille - 1) // taille):
        for bi in range((W + taille - 1) // taille):
            if not m[bj * taille, bi * taille]:
                continue
            y0, x0 = bj * px, bi * px
            ya, xa = max(0, y0 - MARGE), max(0, x0 - MARGE)
            yb, xb = min(h, y0 + px + MARGE), min(w, x0 + px + MARGE)
            c = bc.cartes_image(sh, np.ascontiguousarray(img[ya:yb, xa:xb]), "base")["base"]
            oj, oi = (y0 - ya) // bc.STRIDE, (x0 - xa) // bc.STRIDE
            hh, ww = min(taille, H - bj * taille), min(taille, W - bi * taille)
            ch[bj * taille:bj * taille + hh, bi * taille:bi * taille + ww] = c[oj:oj + hh, oi:oi + ww]
            calc += (yb - ya) * (xb - xa)
    return ch, m, calc / (h * w)


def egaux(a, b):
    (xy, sc), (xyc, scc) = a, b
    return int(len(xy) == len(xyc) and np.allclose(xy, xyc) and np.allclose(sc, scc, atol=1e-5))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--fils", type=int, default=2); ap.add_argument("--n", type=int, default=30)
    a = ap.parse_args()
    import onnxruntime as ort
    o = ort.SessionOptions(); o.intra_op_num_threads = a.fils; o.inter_op_num_threads = 1
    s5 = ort.InferenceSession(str(RACINE / "modeles/centres_5cm_v5.onnx"), o, providers=["CPUExecutionProvider"])
    sh = ort.InferenceSession(str(RACINE / "modeles/comptage_nuit_1311/centres_5cm_c13h.onnx"), o, providers=["CPUExecutionProvider"])
    noms = ["v5", "CC1_v5h_50", "B1_bloc64", "B2_bloc32"]   # S70 et S50 ont échoué à 5.3 : non chronométrés
    res = {}
    for j in ["dense", "plantain", "btd_val", "neg"]:
        items = cc.jeu(j)
        items = [items[i] for i in np.linspace(0, len(items) - 1, min(a.n, len(items))).astype(int)]
        T = {k: 0.0 for k in noms}
        eg = {k: 0 for k in noms}
        surf = {"B1_bloc64": 0.0, "B2_bloc32": 0.0}
        for e in items:
            img = bc.lire(e["chemin"])
            ctx = bc.Contexte(j, e)
            t0 = time.perf_counter()
            c5 = bc.cartes_image(s5, img, "base")["base"]
            t1 = time.perf_counter()
            p = bc.pics(c5)
            t2 = time.perf_counter()
            T["v5"] += t2 - t0; eg["v5"] += egaux(p, ess.construire("v5")(ctx))
            tv5 = t1 - t0
            t0 = time.perf_counter()
            ch = bc.cartes_image(sh, img, "base")["base"]
            p = bc.pics(ess.melange(c5, ch))
            T["CC1_v5h_50"] += tv5 + time.perf_counter() - t0
            eg["CC1_v5h_50"] += egaux(p, ess.construire("CC1_v5h_50")(ctx))
            for nom, f in ():
                t0 = time.perf_counter()
                cr = reduite_img(sh, img, f)
                cr = cv2.resize(cr, (c5.shape[1], c5.shape[0]), interpolation=cv2.INTER_LINEAR)
                p = bc.pics(ess.melange(c5, cr))
                T[nom] += tv5 + time.perf_counter() - t0
                eg[nom] += egaux(p, ess.construire(nom)(ctx))
            for nom, taille in (("B1_bloc64", 64), ("B2_bloc32", 32)):
                t0 = time.perf_counter()
                chb, m, fr = carte_c13h_blocs(sh, img, c5, taille)
                if chb is None:
                    p = bc.pics(c5)
                else:
                    c = c5.copy(); c[m] = ess.melange(c5, chb)[m]
                    p = bc.pics(c)
                T[nom] += tv5 + time.perf_counter() - t0
                surf[nom] += fr
                eg[nom] += egaux(p, ess.construire(nom)(ctx))
        n = len(items)
        res[j] = dict(n=n, s_par_tuile={k: v / n for k, v in T.items()},
                      rapport_v5={k: v / max(T["v5"], 1e-9) for k, v in T.items()},
                      points_identiques_au_banc={k: f"{v}/{n}" for k, v in eg.items()},
                      surface_c13h_calculee={k: v / n for k, v in surf.items()})
        print(j, json.dumps(res[j], ensure_ascii=False), flush=True)
    res["fils"] = a.fils
    res["heure"] = time.strftime("%H:%M")
    (ess.SORTIE / "temps.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
