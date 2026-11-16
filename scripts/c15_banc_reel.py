#!/usr/bin/env python3
"""Cartes réelles de c13h calculées par morceaux (blocs de 64 cases où le v5 hésite, marge 64 px), pour la mesure réelle
de B1 (agent C-banc, 15/11). Réglage seulement (lecture gardée par c13_banc_commun.jeu).

Les blocs sont décidés sur la carte du v5 (cache du banc ; à 11 cm, carte du v5 de l'image dégradée). La carte écrite
vaut 0 hors des blocs calculés (elle n'y est jamais lue). Écrit seulement dans out/comptage/jour_1511/banc/cache/
(c13h_blocs64_<jeu>, c13h_d11blocs64_<jeu>).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c15_banc_reel.py --fils 2 --taches base:dense ... d11:mm
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

import c15_banc_temps as tp  # noqa: E402
from c13_entr_mesure import degrader  # noqa: E402

ess, ce, cc, bc = tp.ess, tp.ce, tp.cc, tp.bc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--taches", nargs="+", required=True); ap.add_argument("--fils", type=int, default=2)
    a = ap.parse_args()
    import onnxruntime as ort
    o = ort.SessionOptions(); o.intra_op_num_threads = a.fils; o.inter_op_num_threads = 1
    sh = ort.InferenceSession(str(RACINE / "modeles/comptage_nuit_1311/centres_5cm_c13h.onnx"), o, providers=["CPUExecutionProvider"])
    for t in a.taches:
        variante, j = t.split(":")
        deg = variante == "d11"
        assert not (j == "neg" and deg)
        p = ess.CACHE / f"c13h_{'d11' if deg else ''}blocs64_{j}"
        if p.with_suffix(".json").exists():
            print(p.name, "déjà là", flush=True); continue
        items = cc.jeu(j)
        t0, blocs, index, pos, surf = time.time(), [], {}, 0, 0.0
        for e in items:
            img = bc.lire(e["chemin"])
            ce.FORCE["variante"] = "d11" if deg else None
            try:
                c5 = bc.Contexte(j, e).carte("v5")
            finally:
                ce.FORCE["variante"] = None
            if deg:
                img = degrader(img, 11)
            ch, m, fr = tp.carte_c13h_blocs(sh, img, c5, 64)
            if ch is None:
                ch = np.zeros_like(c5)
            assert ch.shape == c5.shape, (e["nom"], ch.shape, c5.shape)
            surf += fr
            blocs.append(ch.astype("float32").ravel()); index[e["nom"]] = [pos, ch.shape[0], ch.shape[1]]; pos += ch.size
        tmp = p.with_name(p.name + ".f32.tmp")
        np.concatenate(blocs).astype("float32").tofile(tmp)
        os.replace(tmp, p.with_suffix(".f32"))
        p.with_suffix(".json").write_text(json.dumps(index), encoding="utf-8")
        print(f"{time.strftime('%H:%M:%S')} c13h blocs64 {variante} {j} : {len(items)} images, surface calculée "
              f"{surf / len(items):.3f}, {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
