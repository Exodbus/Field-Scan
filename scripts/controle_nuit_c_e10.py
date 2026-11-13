#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : finaliste E10 (aiguillage p90, petits = v6b) bloc par bloc de btd_val, et sur
banano_finca POUR INFORMATION (ni juge ni test vierge du projet). Réutilise controle_nuit_c_blocs / _finca.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_c_e10.py
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
import controle_nuit_c_blocs as CB  # noqa: E402
import controle_nuit_c_finca as CF  # noqa: E402

SPECS = json.loads((R.OUT / "specs_c_banc2.json").read_text(encoding="utf-8"))

if __name__ == "__main__":
    lignes = []
    B = CB.blocs_btd()
    items = R.items("btd_val")
    bl = np.array([B[e["nom"]] for e in items])
    for nom in ("v6b", "E10_p90_v6b_v5_d0.1"):
        pi = CB.par_image(SPECS[nom], items, [0.30])
        par = {b: CB.f1(sum(p[0.30] for p, x in zip(pi, bl) if x == b)) for b in (0, 1, 2)}
        lignes.append(f"btd_val {nom} au seuil 0,30 : blocs " + ", ".join(f"{b}: {v:.4f}" for b, v in par.items()))
    # banano_finca, information : cartes du v6b (demi-résolution ramenée au quart par maximum 2 x 2)
    import onnxruntime as ort
    import pandas as pd
    cf = CF.CF
    if not (cf / "v6b_base_finca.json").exists():
        o = ort.SessionOptions(); o.intra_op_num_threads = 2
        s = ort.InferenceSession(str(RACINE / "modeles/comptage_v6_essais/centres_5cm_v6b.onnx"), o, providers=["CPUExecutionProvider"])
        T = pd.read_csv(CF.DF / "tuiles.csv")
        blocs, idx, pos = [], {}, 0
        for nom in T.image_path:
            img = np.asarray(Image.open(CF.DF / "images" / nom).convert("RGB"))
            h, w = img.shape[:2]
            H, W = (h + 31) // 32 * 32, (w + 31) // 32 * 32
            x = np.zeros((H, W, 3), "f4"); x[:h, :w] = img / 255.0
            x = ((x - CF.MOY) / CF.ECT).transpose(2, 0, 1)[None].astype("f4")
            z = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
            a, b = z.shape[0] // 2 * 2, z.shape[1] // 2 * 2
            z = z[:a, :b].reshape(a // 2, 2, b // 2, 2).max(axis=(1, 3))
            c = (1 / (1 + np.exp(-z.astype("f8"))))[:(h + 3) // 4, :(w + 3) // 4].astype("f4")
            blocs.append(c.ravel()); idx[nom] = [pos, c.shape[0], c.shape[1]]; pos += c.size
        np.concatenate(blocs).tofile(cf / "v6b_base_finca.f32")
        (cf / "v6b_base_finca.json").write_text(json.dumps(idx), encoding="utf-8")
    R.CACHE = cf
    R.items = CF.items_finca
    for nom in ("v6b", "E10_p90_v6b_v5_d0.1"):
        m = R.mesurer(SPECS[nom], "finca")
        lignes.append(f"banano_finca (information) {nom} au seuil 0,30 : F1 {m[0.30]['f1']:.4f} ; détectés / annotés {m[0.30]['det']}/{m[0.30]['reels']}")
    (R.OUT / "c_e10.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))
