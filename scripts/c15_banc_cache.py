#!/usr/bin/env python3
"""Cartes de c13h calculées sur l'image réduite (famille S, agent C-banc, 15/11). Réglage seulement.

Reprend sans les modifier : la lecture des jeux gardée de scripts/c13_banc_commun.py (assert : réglage seulement),
`entree`, `_logits`, `sigmoide` de scripts/v6_banc_commun.py, `degrader` de scripts/c13_entr_mesure.py.
Variantes : s70 (image réduite d'un facteur 5/7, PIL bilinéaire, comme la variante d'échelle du banc v6),
s50 (facteur 0,5) ; d11s70 / d11s50 : même chose sur l'image dégradée à 11 cm. Carte à sa résolution propre.
Écrit seulement dans out/comptage/jour_1511/banc/cache/.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c15_banc_cache.py --taches s50:dense ... --fils 1
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import c13_banc_commun as cc  # noqa: E402  (garde-fou des juges)
import v6_banc_commun as bc  # noqa: E402
from c13_entr_mesure import degrader  # noqa: E402

CACHE = RACINE / "out/comptage/jour_1511/banc/cache"
ONNX = RACINE / "modeles/comptage_nuit_1311/centres_5cm_c13h.onnx"
FACTEURS = {"s70": 5 / 7, "s50": 0.5}


def carte_reduite(sess, img, f):
    """Carte de probabilité de l'image réduite d'un facteur f, à sa résolution propre (grille au quart)."""
    h, w = img.shape[:2]
    im = Image.fromarray(img).resize((max(32, round(w * f)), max(32, round(h * f))), Image.BILINEAR)
    x2, h2, w2 = bc.entree(np.asarray(im))
    return bc.sigmoide(bc._logits(sess, x2))[:(h2 + 3) // 4, :(w2 + 3) // 4].astype("float32")


def session(fils):
    import onnxruntime as ort
    o = ort.SessionOptions(); o.intra_op_num_threads = fils; o.inter_op_num_threads = 1
    return ort.InferenceSession(str(ONNX), o, providers=["CPUExecutionProvider"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--taches", nargs="+", required=True); ap.add_argument("--fils", type=int, default=1)
    a = ap.parse_args()
    sess = session(a.fils)
    CACHE.mkdir(parents=True, exist_ok=True)
    for t in a.taches:
        variante, j = t.split(":")
        p = CACHE / f"c13h_{variante}_{j}"
        if p.with_suffix(".json").exists():
            print(f"{p.name} déjà là", flush=True); continue
        deg = variante.startswith("d11")
        f = FACTEURS[variante[3:] if deg else variante]
        assert not (j == "neg" and deg), "val_negatifs : résolution d'origine seulement"
        items = cc.jeu(j)
        t0, blocs, index, pos = time.time(), [], {}, 0
        for e in items:
            img = bc.lire(e["chemin"])
            if deg:
                img = degrader(img, 11)
            c = carte_reduite(sess, img, f)
            blocs.append(c.ravel()); index[e["nom"]] = [pos, c.shape[0], c.shape[1]]; pos += c.size
        tmp = p.with_name(p.name + ".f32.tmp")
        np.concatenate(blocs).astype("float32").tofile(tmp)
        os.replace(tmp, p.with_suffix(".f32"))
        p.with_suffix(".json").write_text(json.dumps(index), encoding="utf-8")
        print(f"{time.strftime('%H:%M:%S')} c13h {variante} {j} : {len(items)} images, {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
