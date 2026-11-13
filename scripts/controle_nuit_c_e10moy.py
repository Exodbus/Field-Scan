#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : E10_moy_v6e+v5 (moyenne des cartes v6e et v5, seuil 0,30) bloc par bloc de btd_val et
sur banano_finca POUR INFORMATION (ni juge ni test vierge du projet).
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_c_e10moy.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import controle_nuit_c_recalcul as R  # noqa: E402
import controle_nuit_c_blocs as CB  # noqa: E402
import controle_nuit_c_finca as CF  # noqa: E402

SPECS = {"v6e": {"type": "seul", "modele": "v6e"}, "E10_moy_v6e+v5": {"type": "melange", "membres": ["v6e", "v5"], "mode": "moyenne"},
         "v5": {"type": "seul", "modele": "v5"}}
SEUILS = {"v6e": 0.35, "E10_moy_v6e+v5": 0.30, "v5": 0.30}

if __name__ == "__main__":
    L = []
    B = CB.blocs_btd()
    items = R.items("btd_val")
    bl = np.array([B[e["nom"]] for e in items])
    for nom, sp in SPECS.items():
        s = SEUILS[nom]
        pi = CB.par_image(sp, items, [s])
        par = {b: CB.f1(sum(p[s] for p, x in zip(pi, bl) if x == b)) for b in (0, 1, 2)}
        L.append(f"btd_val {nom} ({s}) : blocs " + ", ".join(f"{b}: {v:.4f}" for b, v in par.items()))
    import onnxruntime as ort
    if not (CF.CF / "v6e_base_finca.json").exists():
        o = ort.SessionOptions(); o.intra_op_num_threads = 2
        se = ort.InferenceSession(str(RACINE / "modeles/comptage_v6_essais/centres_5cm_v6e.onnx"), o, providers=["CPUExecutionProvider"])
        T = pd.read_csv(CF.DF / "tuiles.csv")
        blocs, idx, pos = [], {}, 0
        for nom in T.image_path:
            img = np.asarray(Image.open(CF.DF / "images" / nom).convert("RGB"))
            h, w = img.shape[:2]
            H, W = (h + 31) // 32 * 32, (w + 31) // 32 * 32
            x = np.zeros((H, W, 3), "f4"); x[:h, :w] = img / 255.0
            x = ((x - CF.MOY) / CF.ECT).transpose(2, 0, 1)[None].astype("f4")
            z = se.run(None, {se.get_inputs()[0].name: x})[0][0, 0]
            c = (1 / (1 + np.exp(-z.astype("f8"))))[:(h + 3) // 4, :(w + 3) // 4].astype("f4")
            blocs.append(c.ravel()); idx[nom] = [pos, c.shape[0], c.shape[1]]; pos += c.size
        np.concatenate(blocs).tofile(CF.CF / "v6e_base_finca.f32")
        (CF.CF / "v6e_base_finca.json").write_text(json.dumps(idx), encoding="utf-8")
    R.CACHE, R.items = CF.CF, CF.items_finca
    for nom, sp in SPECS.items():
        m = R.mesurer(sp, "finca")[SEUILS[nom]]
        L.append(f"banano_finca (information) {nom} ({SEUILS[nom]}) : F1 {m['f1']:.4f} ; détectés / annotés {m['det']}/{m['reels']}")
    (R.OUT / "c_e10moy.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
