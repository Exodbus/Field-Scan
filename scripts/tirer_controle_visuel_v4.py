#!/usr/bin/env python3
"""Tire, avant tout résultat, les images du contrôle visuel de fin de test du comptage v4 (protocole v4, section 8).

6 images de segmento est (Plants-bana), 6 de banana_tree_detection (une copie par image d'origine), carrés El Oro
EO1-EO4. Graine fixe ; la liste est écrite dans docs/controle_visuel_v4.json et ne doit plus changer.

Exemple :
    python scripts/tirer_controle_visuel_v4.py
"""
import json
import random
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verifier_sources_communes import origine  # noqa: E402

GRAINE = 2026


def main():
    dec = pd.read_csv("data/drone/decoupage_comptage/decoupage.csv")
    seg = sorted(dec[dec.groupe == "segmento_est"].image)
    z = zipfile.ZipFile("data/roboflow/banana_tree_detection.zip")
    btd = {}
    for n in sorted(z.namelist()):
        if n.lower().endswith((".jpg", ".jpeg", ".png")):
            btd.setdefault(origine(n), n)                       # une copie par image d'origine
    rng = random.Random(GRAINE)
    choix = dict(graine=GRAINE, date="2026-11-05",
                 segmento_est=rng.sample(seg, 6),
                 banana_tree_detection=[btd[o] for o in rng.sample(sorted(btd), 6)],
                 el_oro=["EO1", "EO2", "EO3", "EO4"],
                 regle="tirage avant tout résultat du v4 ; planches v3 / v4 / plants-bana/3 sur ces images seulement")
    Path("docs/controle_visuel_v4.json").write_text(json.dumps(choix, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(choix, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
