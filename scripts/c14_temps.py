#!/usr/bin/env python3
"""Temps par tuile du v5 seul et du mélange CC1_v5h_50 (v5 + c13h, moyenne des cartes), calculés de bout en bout
(lecture de l'image, cartes ONNX, pics), sur un échantillon fixe du réglage (agent C-piste2, 14/11). Information.
Contrôle : les points du mélange recalculé sont comparés à ceux lus dans le cache.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c14_temps.py --fils 3 --n 40
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import numpy as np  # noqa: E402

import c14_essais as ce  # noqa: E402

cc, bc = ce.cc, ce.bc


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--fils", type=int, default=3); ap.add_argument("--n", type=int, default=40)
    a = ap.parse_args()
    import onnxruntime as ort
    o = ort.SessionOptions(); o.intra_op_num_threads = a.fils; o.inter_op_num_threads = 1
    s5 = ort.InferenceSession(str(RACINE / "modeles/centres_5cm_v5.onnx"), o, providers=["CPUExecutionProvider"])
    sh = ort.InferenceSession(str(RACINE / "modeles/comptage_nuit_1311/centres_5cm_c13h.onnx"), o, providers=["CPUExecutionProvider"])
    res, egal, total = {}, 0, 0
    for j in ["dense", "plantain", "btd_val", "neg"]:
        items = cc.jeu(j)
        items = [items[i] for i in np.linspace(0, len(items) - 1, min(a.n, len(items))).astype(int)]
        t5 = tm = 0.0
        for e in items:
            img = bc.lire(e["chemin"])
            t0 = time.perf_counter()
            c5 = bc.cartes_image(s5, img, "base")["base"]
            bc.pics(c5)
            t1 = time.perf_counter()
            ch = bc.cartes_image(sh, img, "base")["base"]
            xy, sc = bc.pics((0.5 * c5.astype("float64") + 0.5 * ch.astype("float64")).astype("float32"))
            t2 = time.perf_counter()
            t5 += t1 - t0; tm += t2 - t0
            xyc, scc = ce.construire("CC1_v5h_50")(bc.Contexte(j, e))
            total += 1
            egal += int(len(xy) == len(xyc) and np.allclose(xy, xyc) and np.allclose(sc, scc, atol=1e-5))
        res[j] = dict(n=len(items), v5_s_par_tuile=t5 / len(items), cc1_s_par_tuile=tm / len(items), rapport=tm / max(t5, 1e-9))
        print(j, {k: round(v, 3) if isinstance(v, float) else v for k, v in res[j].items()}, flush=True)
    res["controle_points_identiques"] = f"{egal}/{total}"
    res["fils"] = a.fils
    res["heure"] = time.strftime("%H:%M")
    print("points identiques au cache :", egal, "/", total)
    (ce.SORTIE / "temps.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
