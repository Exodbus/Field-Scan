#!/usr/bin/env python3
"""Part de végétation verte de chaque image de RÉGLAGE (agent C-banc, nuit du 13/11) : fraction des pixels dont l'indice
d'excès de vert ExG = 2g - r - b (couleurs chromatiques r, g, b = R, G, B / (R + G + B)) dépasse 0,10, dans le disque
(photos DJI) ou sur l'image entière. Enregistrée dans out/comptage/nuit_1311/banc/cache/vert.json {jeu: {image: part}}.
Signal « jeune plantation sur sol nu » de CB1 (aiguillage_v2, veg_max), indépendant de la taille de l'image.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c13_banc_vert.py
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c13_banc_commun as cc  # noqa: E402

bc = cc.bc
SEUIL_EXG = 0.10


def part_verte(img, masque=None):
    f = img.astype("float32")
    s = f.sum(2) + 1e-6
    exg = (2 * f[..., 1] - f[..., 0] - f[..., 2]) / s
    if masque is not None:
        yy, xx = np.mgrid[:exg.shape[0], :exg.shape[1]]
        exg = exg[(xx - masque[0]) ** 2 + (yy - masque[1]) ** 2 <= masque[2] ** 2]
    return float((exg > SEUIL_EXG).mean())


if __name__ == "__main__":
    p = cc.CACHE / "vert.json"
    V = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    for j in cc.REGLAGE + ["neg"]:
        if j in V:
            continue
        V[j] = {e["nom"]: part_verte(bc.lire(e["chemin"]), e["masque"]) for e in cc.jeu(j)}
        p.write_text(json.dumps(V), encoding="utf-8")
        print(j, len(V[j]), flush=True)
