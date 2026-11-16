#!/usr/bin/env python3
"""Contrôleur, nuit du 13/11 : cartes d'un modèle de comptage ONNX (réseau neuf de C-entraîneur, ou ancien pour
contrôle) sur les 5 jeux de RÉGLAGE et `val_negatifs`, calculées par moi (2 fils), à 5 cm ou sur le réglage dégradé
(d11 / d8 : image réduite à c cm/px en LANCZOS, remise à sa taille en LANCZOS, JPEG qualité 95, comme écrit dans les
journaux de C-banc et C-entraîneur). Cartes rangées dans out/controle_nuit_1311/cache_c/<modele>_<variante>_<jeu>,
lues ensuite par controle_1311_c_recalcul.py. Garde-fou : les images viennent de items() de mon script (réglage seul).
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_1311_c_cache_modele.py c13d [base|d11|d8] [jeux...]
"""
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import controle_1311_c_recalcul as R  # noqa: E402

DOSS = {"dense": R.D5 / "images", "plantain": R.D5 / "images", "jeunes": R.D5 / "images", "mm": R.D5 / "mm/images",
        "btd_val": R.D6 / "images", "neg": R.D5 / "images"}
MOY, ECT = np.array([0.485, 0.456, 0.406], "f4"), np.array([0.229, 0.224, 0.225], "f4")


def degrader(img, cm):
    h, w = img.shape[:2]
    petit = Image.fromarray(img).resize((max(1, round(w * 5 / cm)), max(1, round(h * 5 / cm))), Image.LANCZOS)
    tampon = io.BytesIO()
    petit.resize((w, h), Image.LANCZOS).save(tampon, format="JPEG", quality=95)
    return np.asarray(Image.open(io.BytesIO(tampon.getvalue())).convert("RGB"))


def onnx_de(m):
    for d in ("modeles/comptage_nuit_1311", "modeles/comptage_v6_essais", "modeles"):
        p = RACINE / d / f"centres_5cm_{m}.onnx"
        if p.exists():
            return p
    raise FileNotFoundError(m)


if __name__ == "__main__":
    import onnxruntime as ort
    m = sys.argv[1]
    var = sys.argv[2] if len(sys.argv) > 2 else "base"
    jeux = sys.argv[3:] or ["jeunes", "mm", "dense", "plantain", "btd_val", "neg"]
    onnx = onnx_de(m)
    print(m, onnx.relative_to(RACINE).as_posix(), "SHA-256", hashlib.sha256(onnx.read_bytes()).hexdigest(), flush=True)
    o = ort.SessionOptions(); o.intra_op_num_threads = 2; o.inter_op_num_threads = 1
    s = ort.InferenceSession(str(onnx), o, providers=["CPUExecutionProvider"])
    R.CACHE_MOI.mkdir(parents=True, exist_ok=True)
    for j in jeux:
        if (R.CACHE_MOI / f"{m}_{var}_{j}.json").exists():
            continue
        noms = sorted({e["nom"] for e in R.items(j)})
        blocs, idx, pos = [], {}, 0
        for nom in noms:
            R.garde(nom)
            img = np.asarray(Image.open(DOSS[j] / nom).convert("RGB"))
            if var != "base":
                img = degrader(img, float(var[1:]))
            h, w = img.shape[:2]
            H, W = (h + 31) // 32 * 32, (w + 31) // 32 * 32
            x = np.zeros((H, W, 3), "f4"); x[:h, :w] = img / 255.0
            x = ((x - MOY) / ECT).transpose(2, 0, 1)[None].astype("f4")
            z = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
            c = (1 / (1 + np.exp(-z.astype("f8"))))[:(h + 3) // 4, :(w + 3) // 4].astype("f4")
            blocs.append(c.ravel()); idx[nom] = [pos, c.shape[0], c.shape[1]]; pos += c.size
        np.concatenate(blocs).tofile(R.CACHE_MOI / f"{m}_{var}_{j}.f32")
        (R.CACHE_MOI / f"{m}_{var}_{j}.json").write_text(json.dumps(idx), encoding="utf-8")
        print(m, var, j, len(noms), "images", flush=True)
