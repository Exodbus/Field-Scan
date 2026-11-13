#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : cartes d'un modèle de comptage (ONNX) sur les 5 jeux de RÉGLAGE et les tuiles sans
bananier de VALIDATION, calculées par moi (2 fils), dans out/controle_nuit_1112/cache_reglage/, puis mesure par
controle_nuit_c_recalcul.py (seuil par la règle 3.4). Aucun juge, aucun test vierge.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_c_cache_modele.py v6f
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import controle_nuit_c_recalcul as R  # noqa: E402

CR = R.OUT / "cache_reglage"
DOSS = {"dense": R.D5 / "images", "plantain": R.D5 / "images", "jeunes": R.D5 / "images", "mm": R.D5 / "mm/images",
        "btd_val": R.D6 / "images", "neg": R.D5 / "images"}
MOY, ECT = np.array([0.485, 0.456, 0.406], "f4"), np.array([0.229, 0.224, 0.225], "f4")

if __name__ == "__main__":
    import hashlib
    import onnxruntime as ort
    m = sys.argv[1]
    onnx = RACINE / f"modeles/comptage_v6_essais/centres_5cm_{m}.onnx"
    print(m, "SHA-256", hashlib.sha256(onnx.read_bytes()).hexdigest(), flush=True)
    o = ort.SessionOptions(); o.intra_op_num_threads = 2
    s = ort.InferenceSession(str(onnx), o, providers=["CPUExecutionProvider"])
    CR.mkdir(parents=True, exist_ok=True)
    for j in ("jeunes", "mm", "dense", "plantain", "btd_val", "neg"):
        if (CR / f"{m}_base_{j}.json").exists():
            continue
        noms = sorted({e["nom"] for e in R.items(j)})
        blocs, idx, pos = [], {}, 0
        for nom in noms:
            img = np.asarray(Image.open(DOSS[j] / nom).convert("RGB"))
            h, w = img.shape[:2]
            H, W = (h + 31) // 32 * 32, (w + 31) // 32 * 32
            x = np.zeros((H, W, 3), "f4"); x[:h, :w] = img / 255.0
            x = ((x - MOY) / ECT).transpose(2, 0, 1)[None].astype("f4")
            z = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
            if z.shape[0] >= 2 * ((H + 3) // 4) - 1:
                a, b = z.shape[0] // 2 * 2, z.shape[1] // 2 * 2
                z = z[:a, :b].reshape(a // 2, 2, b // 2, 2).max(axis=(1, 3))
            c = (1 / (1 + np.exp(-z.astype("f8"))))[:(h + 3) // 4, :(w + 3) // 4].astype("f4")
            blocs.append(c.ravel()); idx[nom] = [pos, c.shape[0], c.shape[1]]; pos += c.size
        np.concatenate(blocs).tofile(CR / f"{m}_base_{j}.f32")
        (CR / f"{m}_base_{j}.json").write_text(json.dumps(idx), encoding="utf-8")
        print(m, j, len(noms), "images", flush=True)
    R.CACHE = CR
    res = {j: R.mesurer({"type": "seul", "modele": m}, j) for j in R.JEUX + ["neg"]}
    s3, moy = R.regle_34(res)
    r = R.resumer(m, res, s3)
    l = f"{m} : seuil {s3:.2f} moyenne {r['moyenne']:.4f} {r['f1']} err {r['err']:.3f} fausses {r['fp_neg']} ({r['taux']:.2%})"
    (R.OUT / f"c_modele_{m}.txt").write_text(l + "\n", encoding="utf-8")
    (R.OUT / f"c_modele_{m}.json").write_text(json.dumps({str(k): v for k, v in res.items()}, default=str), encoding="utf-8")
    print(l)
