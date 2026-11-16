#!/usr/bin/env python3
"""Juge comptage, 15/11 : temps de bout en bout (lecture de l'image, cartes ONNX, pics) du v5, de CC1_v5h_50 (v5 + c13h)
et de c15d, ENTRELACÉS tuile par tuile (mêmes conditions de charge pour les trois), 2 fils, sur la même machine.
Échantillon fixe du RÉGLAGE (dense, neg : 25 tuiles chacun, régulièrement espacées), comme scripts/c14_temps.py ;
aucun juge n'est lu ici. Information, ne change pas la règle.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_1511_c_temps.py
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import numpy as np  # noqa: E402
import v6_banc_commun as bc  # noqa: E402

bc.MODELES["c13h"] = RACINE / "modeles/comptage_nuit_1311/centres_5cm_c13h.onnx"
bc.MODELES["c15d"] = RACINE / "modeles/comptage_jour_1511/centres_5cm_c15d.onnx"
N, FILS = 25, 2


def main():
    s = {m: bc.session(m, FILS) for m in ("v5", "c13h", "c15d")}
    res = {}
    for j in ["dense", "neg"]:
        items = bc.jeu(j)
        items = [items[i] for i in np.linspace(0, len(items) - 1, N).astype(int)]
        bc.cartes_image(s["c15d"], bc.lire(items[0]["chemin"]), "base")        # chauffe
        t = {"v5": 0.0, "CC1_v5h_50": 0.0, "c15d": 0.0}
        for e in items:
            t0 = time.perf_counter()
            img = bc.lire(e["chemin"])
            c5 = bc.cartes_image(s["v5"], img, "base")["base"]; bc.pics(c5)
            t1 = time.perf_counter()
            img = bc.lire(e["chemin"])
            a = bc.cartes_image(s["v5"], img, "base")["base"]; h = bc.cartes_image(s["c13h"], img, "base")["base"]
            bc.pics((0.5 * a.astype("float64") + 0.5 * h.astype("float64")).astype("float32"))
            t2 = time.perf_counter()
            img = bc.lire(e["chemin"])
            bc.pics(bc.cartes_image(s["c15d"], img, "base")["base"])
            t3 = time.perf_counter()
            t["v5"] += t1 - t0; t["CC1_v5h_50"] += t2 - t1; t["c15d"] += t3 - t2
        res[j] = {k: dict(s_par_tuile=v / N, rapport_v5=v / t["v5"]) for k, v in t.items()}
        res[j]["n"] = N
        print(j, json.dumps(res[j]), flush=True)
    res.update(fils=FILS, heure=time.strftime("%H:%M"), note="machine partagée avec le juge maladies")
    (RACINE / "out/controle_jour_1511/juge_c/temps.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
