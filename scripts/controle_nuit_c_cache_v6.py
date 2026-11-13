#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : les cartes en cache d'un modèle v6 (out/comptage_v6/banc/cache) sont-elles bien celles
de son ONNX ? Recalcul indépendant (ONNX, 2 fils) sur quelques images de réglage par jeu, sortie à la demi-résolution
ramenée au quart par maximum 2 x 2 comme dans le banc. Réglage seulement.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_c_cache_v6.py v6b
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import controle_nuit_c_recalcul as R  # noqa: E402

MOY, ECT = np.array([0.485, 0.456, 0.406], "f4"), np.array([0.229, 0.224, 0.225], "f4")
CHEMINS = {"dense": R.D5 / "images", "plantain": R.D5 / "images", "jeunes": R.D5 / "images", "btd_val": R.D6 / "images",
           "neg": R.D5 / "images", "mm": R.D5 / "mm/images"}

if __name__ == "__main__":
    import onnxruntime as ort
    m = sys.argv[1]
    o = ort.SessionOptions(); o.intra_op_num_threads = 2
    s = ort.InferenceSession(str(RACINE / f"modeles/comptage_v6_essais/centres_5cm_{m}.onnx"), o, providers=["CPUExecutionProvider"])
    pire = 0.0
    for j in ("dense", "plantain", "btd_val", "neg", "mm"):
        its = R.items(j)
        for e in its[:: max(1, len(its) // 3)][:3]:
            img = np.asarray(Image.open(CHEMINS[j] / e["nom"]).convert("RGB"))
            h, w = img.shape[:2]
            H, W = (h + 31) // 32 * 32, (w + 31) // 32 * 32
            x = np.zeros((H, W, 3), "f4"); x[:h, :w] = img / 255.0
            x = ((x - MOY) / ECT).transpose(2, 0, 1)[None].astype("f4")
            z = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
            if z.shape[0] >= 2 * ((H + 3) // 4) - 1:
                a, b = z.shape[0] // 2 * 2, z.shape[1] // 2 * 2
                z = z[:a, :b].reshape(a // 2, 2, b // 2, 2).max(axis=(1, 3))
            c = (1 / (1 + np.exp(-z.astype("f8"))))[:(h + 3) // 4, :(w + 3) // 4]
            ref = R.carte(m, j, e["nom"])
            ecart = float(np.abs(c - ref).max()) if c.shape == ref.shape else float("inf")
            pire = max(pire, ecart)
            print(j, e["nom"], c.shape, ref.shape, f"écart max {ecart:.2e}", flush=True)
    print(f"{m} : écart maximal cache / ONNX {pire:.2e}")
