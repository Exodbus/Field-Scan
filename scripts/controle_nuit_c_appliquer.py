#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : mesure des finalistes de comptage sur N'IMPORTE QUEL jeu au format de l'archive v5/v6
(deuxième avis pour l'agent Juge, code indépendant de celui de C-banc).

Deux formats :
  - tuiles : DOSSIER/tuiles.csv + DOSSIER/objets.csv + DOSSIER/images/, avec --ensemble (ex. test_dense, test_banano,
    test_negatifs, test_vierge) ; masque DJI lu dans tuiles.csv ; un jeu « sans bananier » se mesure avec --negatif ;
  - zones : DOSSIER/zones.csv + DOSSIER/points.csv + DOSSIER/images/ (ex. cg/ ou mm/).
Les cartes des modèles nécessaires (v3, v4, v5 : modeles/centres_5cm_*.onnx ; v6e, v6f : modeles/comptage_v6_essais/, SHA-256 vérifiés) sont
calculées ici (2 fils) et gardées dans --cache. Mesure : pics 7 x 7, appariement hongrois à 20 px, non-mères ignorées.
Finalistes : E10_moy_v6e+v5 (0,30), v6f (0,35), E5p90b_moy34_v5_d0.1 (0,30), E7_union_v5+v3_d0.05_r30 (0,30), v5 (0,30 et 0,20).
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_c_appliquer.py --dossier D --ensemble E --cache C
"""
import argparse
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

ONNX = {"v3": RACINE / "modeles/centres_5cm_v3.onnx", "v4": RACINE / "modeles/centres_5cm_v4.onnx",
        "v5": RACINE / "modeles/centres_5cm_v5.onnx", "v6b": RACINE / "modeles/comptage_v6_essais/centres_5cm_v6b.onnx",
        "v6e": RACINE / "modeles/comptage_v6_essais/centres_5cm_v6e.onnx", "v6f": RACINE / "modeles/comptage_v6_essais/centres_5cm_v6f.onnx"}
SHA = {"v6b": "f006a49b74671b1c8eb38472845142b6def2bdd8bd62e1336e69ffda9a35ae00",
       "v6e": "93fb659befd669e229a6af50eb08c83968468219b483e1b48ee9b8c993737f01",
       "v6f": "49602a142a8c7ebacddf761cddb337a9001d5a24e655df8e001716544f4a80af"}
V5, V3V4 = {"type": "seul", "modele": "v5"}, {"type": "melange", "membres": ["v3", "v4"], "mode": "moyenne"}
FINALISTES = {
    "E10_moy_v6e+v5": ({"type": "melange", "membres": ["v6e", "v5"], "mode": "moyenne"}, 0.30),
    "v6f": ({"type": "seul", "modele": "v6f"}, 0.35),
    "E5p90b_moy34_v5_d0.1": ({"type": "p90", "tau": 0.55, "decalage": 0.10, "petit": V3V4, "grand": V5}, 0.30),
    "E7_union_v5+v3_d0.05_r30": ({"type": "union", "membres": [["v5", 0.0], ["v3", 0.05]], "rayon": 30}, 0.30),
    "v5_030": (V5, 0.30), "v5_020": (V5, 0.20),
}
MOY, ECT = np.array([0.485, 0.456, 0.406], "f4"), np.array([0.229, 0.224, 0.225], "f4")


def items_generiques(dossier, ensemble):
    if (dossier / "zones.csv").exists():
        P, Z = pd.read_csv(dossier / "points.csv"), pd.read_csv(dossier / "zones.csv")
        return [dict(nom=z.image_path, pts=P[(P.zone_id == z.zone_id) & (P.type == "mere")][["x", "y"]].to_numpy("f8"),
                     ign=P[(P.zone_id == z.zone_id) & (P.type != "mere")][["x", "y"]].to_numpy("f8"),
                     zone=(z.x0, z.y0, z.x1, z.y1), masque=None, arbres=0) for z in Z.itertuples()]
    T, O = pd.read_csv(dossier / "tuiles.csv"), pd.read_csv(dossier / "objets.csv")
    T = T[T.ensemble == ensemble]
    assert len(T), f"ensemble {ensemble} vide"
    O = dict(tuple(O[O.image_path.isin(set(T.image_path))].groupby("image_path")))
    out = []
    for r in T.itertuples():
        o = O.get(r.image_path)
        m = o[o.type == "mere"][["cx", "cy"]].to_numpy("f8") if o is not None else np.zeros((0, 2))
        ig = o[o.type != "mere"][["cx", "cy"]].to_numpy("f8") if o is not None else np.zeros((0, 2))
        masque = None if pd.isna(r.masque_r) else (r.masque_cx, r.masque_cy, r.masque_r)
        if masque is not None:
            m = m[((m[:, 0] - masque[0]) ** 2 + (m[:, 1] - masque[1]) ** 2) <= masque[2] ** 2]
        out.append(dict(nom=r.image_path, pts=m, ign=ig, zone=None, masque=masque, arbres=int(r.n_autres_arbres)))
    return out


def cartes(dossier, items, cache, modeles, nom_jeu):
    import hashlib
    import onnxruntime as ort
    for k, h in SHA.items():
        if k in modeles:
            assert hashlib.sha256(ONNX[k].read_bytes()).hexdigest() == h, f"ONNX {k} différent du finaliste figé"
    cache.mkdir(parents=True, exist_ok=True)
    for m in modeles:
        if (cache / f"{m}_base_{nom_jeu}.json").exists():
            continue
        o = ort.SessionOptions(); o.intra_op_num_threads = 2
        s = ort.InferenceSession(str(ONNX[m]), o, providers=["CPUExecutionProvider"])
        blocs, idx, pos = [], {}, 0
        for nom in sorted({e["nom"] for e in items}):
            img = np.asarray(Image.open(dossier / "images" / nom).convert("RGB"))
            h, w = img.shape[:2]
            H, W = (h + 31) // 32 * 32, (w + 31) // 32 * 32
            x = np.zeros((H, W, 3), "f4"); x[:h, :w] = img / 255.0
            x = ((x - MOY) / ECT).transpose(2, 0, 1)[None].astype("f4")
            z = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
            if z.shape[0] >= 2 * ((H + 3) // 4) - 1:          # sortie à la demi-résolution (v6b) -> quart, maximum 2 x 2
                a, b = z.shape[0] // 2 * 2, z.shape[1] // 2 * 2
                z = z[:a, :b].reshape(a // 2, 2, b // 2, 2).max(axis=(1, 3))
            c = (1 / (1 + np.exp(-z.astype("f8"))))[:(h + 3) // 4, :(w + 3) // 4].astype("f4")
            blocs.append(c.ravel()); idx[nom] = [pos, c.shape[0], c.shape[1]]; pos += c.size
        np.concatenate(blocs).tofile(cache / f"{m}_base_{nom_jeu}.f32")
        (cache / f"{m}_base_{nom_jeu}.json").write_text(json.dumps(idx), encoding="utf-8")


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--dossier", required=True)
    a.add_argument("--ensemble", default="")
    a.add_argument("--cache", required=True)
    a.add_argument("--negatif", action="store_true")
    a.add_argument("--sortie")
    x = a.parse_args()
    dossier = Path(x.dossier)
    items = items_generiques(dossier, x.ensemble)
    nom_jeu = "neg" if x.negatif else "jeu"
    cartes(dossier, items, Path(x.cache), ["v3", "v4", "v5", "v6e", "v6f"], nom_jeu)
    R.CACHE, R.items = Path(x.cache), (lambda jeu: items)
    res = {}
    for nom, (spec, s) in FINALISTES.items():
        m = R.mesurer(spec, nom_jeu)[s]
        res[nom] = m
        if x.negatif:
            print(f"{nom:26s} seuil {s:.2f} : fausses détections {m['fp']} ({m['taux']:.2%} des arbres)")
        else:
            print(f"{nom:26s} seuil {s:.2f} : F1 {m['f1']:.4f} ; détectés / annotés {m['det']}/{m['reels']} ; erreur de compte {m['err']:.3f}")
    if x.sortie:
        Path(x.sortie).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
