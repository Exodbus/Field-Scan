#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : finalistes du banc de comptage sur banano_finca, POUR INFORMATION.

banano_finca (Roboflow edison-zapata/banano-finca, 25 images entières à 5 cm, 409 plants, plantation jeune) n'est ni un
juge ni le test vierge du projet : décision du chef d'orchestre à 0 h 15, « information seulement » (ancien juge du
binôme). Il sert ici à voir si le gain de l'aiguillage, réglé sur btd_val, se retrouve sur une autre plantation jeune
jamais regardée par C-banc. Aucun choix n'en dépend (finalistes gelés à 0 h 39). Cartes calculées ici (ONNX v3, v4,
v5, processeur, 2 fils), écrites dans out/controle_nuit_1112/cache_finca/ ; mesure : controle_nuit_c_recalcul.py.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_c_finca.py
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

DF = RACINE / "data/roboflow_nuit_1112/comptage/banano_finca/prepare"
CF = R.OUT / "cache_finca"
MOY, ECT = np.array([0.485, 0.456, 0.406], "f4"), np.array([0.229, 0.224, 0.225], "f4")


def cartes():
    import onnxruntime as ort
    CF.mkdir(parents=True, exist_ok=True)
    T = pd.read_csv(DF / "tuiles.csv")
    for m in ("v3", "v4", "v5"):
        if (CF / f"{m}_base_finca.json").exists():
            continue
        o = ort.SessionOptions(); o.intra_op_num_threads = 2
        s = ort.InferenceSession(str(RACINE / f"modeles/centres_5cm_{m}.onnx"), o, providers=["CPUExecutionProvider"])
        blocs, idx, pos = [], {}, 0
        for nom in T.image_path:
            img = np.asarray(Image.open(DF / "images" / nom).convert("RGB"))
            h, w = img.shape[:2]
            H, W = (h + 31) // 32 * 32, (w + 31) // 32 * 32
            x = np.zeros((H, W, 3), "f4"); x[:h, :w] = img / 255.0
            x = ((x - MOY) / ECT).transpose(2, 0, 1)[None].astype("f4")
            z = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
            c = (1 / (1 + np.exp(-z.astype("f8"))))[:(h + 3) // 4, :(w + 3) // 4].astype("f4")
            blocs.append(c.ravel()); idx[nom] = [pos, c.shape[0], c.shape[1]]; pos += c.size
        np.concatenate(blocs).tofile(CF / f"{m}_base_finca.f32")
        (CF / f"{m}_base_finca.json").write_text(json.dumps(idx), encoding="utf-8")


def items_finca(jeu):
    T, O = pd.read_csv(DF / "tuiles.csv"), pd.read_csv(DF / "objets.csv")
    out = []
    for r in T.itertuples():
        o = O[O.image_path == r.image_path]
        out.append(dict(nom=r.image_path, pts=o[o.type == "mere"][["cx", "cy"]].to_numpy("f8"),
                        ign=o[o.type != "mere"][["cx", "cy"]].to_numpy("f8"), zone=None, masque=None, arbres=0))
    return out


if __name__ == "__main__":
    cartes()
    R.CACHE = CF
    R.items = items_finca
    specs = json.loads((R.OUT / "specs_c_banc.json").read_text(encoding="utf-8"))
    specs["v3"] = {"type": "seul", "modele": "v3"}
    seuils = {"v5": (0.20, 0.30), "E5p90b_moy34_v5_d0.1": (0.30,), "E7_union_v5+v3_d0.05_r30": (0.30,),
              "E3_log_v3+v4+v5": (0.25,), "v3": (0.20,)}
    lignes = []
    for nom, sp in specs.items():
        m = R.mesurer(sp, "finca")
        for s in seuils[nom]:
            lignes.append(f"{nom:28s} seuil {s:.2f} : F1 {m[s]['f1']:.4f} ; détectés / annotés {m[s]['det']}/{m[s]['reels']}")
    q = []
    for e in items_finca("finca"):
        _, sc = R.maxima(R.carte("v5", "finca", e["nom"]), 0.15)
        q.append(float(np.quantile(sc, 0.9)) if len(sc) else np.nan)
    lignes.append(f"part des images aiguillées (p90 du v5 < 0,55) : {np.nanmean(np.array(q) < 0.55):.2f} ; p90 médian {np.nanmedian(q):.3f}")
    (R.OUT / "c_finca_information.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))
