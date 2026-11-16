#!/usr/bin/env python3
"""Juge comptage, 15/11 : contrôle préalable, SUR LE RÉGLAGE seulement (aucun juge). Les ONNX de c13h et de c15d lus
aujourd'hui donnent-ils les cartes qui ont servi au réglage des finalistes ? c13h n'a aucune empreinte écrite avant le gel :
ce contrôle tient lieu de vérification. Cartes recalculées sur 4 tuiles de `dense`, comparées aux caches des agents
(c13h : out/comptage/nuit_1311/piste2/cache ; c15d : out/comptage/jour_1511/kaggle/cache).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_1511_c_controle.py
"""
import json
import os
import sys
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import numpy as np  # noqa: E402
import v6_banc_commun as bc  # noqa: E402

bc.MODELES["c13h"] = RACINE / "modeles/comptage_nuit_1311/centres_5cm_c13h.onnx"
bc.MODELES["c15d"] = RACINE / "modeles/comptage_jour_1511/centres_5cm_c15d.onnx"
CACHES = {"c13h": RACINE / "out/comptage/nuit_1311/piste2/cache", "c15d": RACINE / "out/comptage/jour_1511/kaggle/cache"}


def main():
    items = bc.jeu("dense")
    items = [items[i] for i in (0, len(items) // 3, 2 * len(items) // 3, len(items) - 1)]
    res = {}
    for m, d in CACHES.items():
        p = d / f"{m}_base_dense"
        idx = json.loads(p.with_suffix(".json").read_text(encoding="utf-8"))
        mm = np.memmap(p.with_suffix(".f32"), dtype="float32", mode="r")
        s = bc.session(m, 2)
        ecarts = []
        for e in items:
            c = bc.cartes_image(s, bc.lire(e["chemin"]), "base")["base"]
            a, h, w = idx[e["nom"]]
            ref = np.asarray(mm[a:a + h * w]).reshape(h, w)
            ecarts.append(float(np.abs(c.astype("float64") - ref).max()) if c.shape == ref.shape else float("inf"))
        res[m] = dict(tuiles=[e["nom"] for e in items], ecart_max=max(ecarts))
        print(m, res[m], flush=True)
    out = RACINE / "out/controle_jour_1511/juge_c"
    out.mkdir(parents=True, exist_ok=True)
    (out / "controle_modeles_reglage.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
