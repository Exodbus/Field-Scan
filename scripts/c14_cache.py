#!/usr/bin/env python3
"""Cartes de chaleur d'un ONNX de centres sur le réglage, à 5 cm et dégradé (agent C-piste2, 14/11).

Reprend sans les modifier : la lecture des jeux gardée de scripts/c13_banc_commun.py (assert : réglage seulement), la
carte `bc.cartes_image(..., "base")` de scripts/v6_banc_commun.py et `degrader` de scripts/c13_entr_mesure.py
(LANCZOS aller-retour, JPEG 95). Écrit seulement dans out/comptage/nuit_1311/piste2/cache/, au format du banc
(<nom>_<variante>_<jeu>.f32 + .json ; variante base à 5 cm, d<cm> dégradé). Aucun juge.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c14_cache.py --nom c13h \
        --onnx modeles/comptage_nuit_1311/centres_5cm_c13h.onnx --taches base:dense base:plantain ... d11:mm --fils 3
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "3")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import numpy as np  # noqa: E402

import c13_banc_commun as cc  # noqa: E402  (garde-fou des juges)
import v6_banc_commun as bc  # noqa: E402
from c13_entr_mesure import degrader  # noqa: E402

CACHE = RACINE / "out/comptage/nuit_1311/piste2/cache"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nom", required=True); ap.add_argument("--onnx", required=True)
    ap.add_argument("--taches", nargs="+", required=True); ap.add_argument("--fils", type=int, default=3)
    a = ap.parse_args()
    import onnxruntime as ort
    o = ort.SessionOptions(); o.intra_op_num_threads = a.fils; o.inter_op_num_threads = 1
    sess = ort.InferenceSession(str(RACINE / a.onnx), o, providers=["CPUExecutionProvider"])
    CACHE.mkdir(parents=True, exist_ok=True)
    for t in a.taches:
        variante, j = t.split(":")
        p = CACHE / f"{a.nom}_{variante}_{j}"
        if p.with_suffix(".json").exists():
            print(f"{p.name} déjà là", flush=True); continue
        cm = 5 if variante == "base" else int(variante[1:])
        assert not (j == "neg" and cm != 5), "val_negatifs : résolution d'origine seulement"
        items = cc.jeu(j)
        t0, blocs, index, pos = time.time(), [], {}, 0
        for e in items:
            img = bc.lire(e["chemin"])
            if cm != 5:
                img = degrader(img, cm)
            c = bc.cartes_image(sess, img, "base")["base"]
            blocs.append(c.ravel()); index[e["nom"]] = [pos, c.shape[0], c.shape[1]]; pos += c.size
        tmp = p.with_name(p.name + ".f32.tmp")
        np.concatenate(blocs).astype("float32").tofile(tmp)
        os.replace(tmp, p.with_suffix(".f32"))
        p.with_suffix(".json").write_text(json.dumps(index), encoding="utf-8")
        print(f"{time.strftime('%H:%M:%S')} {a.nom} {variante} {j} : {len(items)} images, {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
