#!/usr/bin/env python3
"""Tire, avant tout résultat, les tuiles banano_dense du contrôle visuel du v5 (protocole v5, section 8).

6 tuiles parmi celles qui contiennent au moins 20 boîtes (graine 2026), ajoutées à la liste du v4.
Écrit docs/controle_visuel_v5.json, qui ne doit plus changer.
"""
import json
import random
import zipfile
from pathlib import Path


def main():
    z = zipfile.ZipFile("data/roboflow/banano_dense.zip")
    nb = {}
    for part in ["train", "valid", "test"]:
        d = json.loads(z.read(f"{part}/_annotations.coco.json"))
        noms = {im["id"]: f"{part}/{im['file_name']}" for im in d["images"]}
        for n in noms.values():
            nb[n] = 0
        for a in d["annotations"]:
            nb[noms[a["image_id"]]] += 1
    candidates = sorted(n for n, k in nb.items() if k >= 20)
    v4 = json.loads(Path("docs/controle_visuel_v4.json").read_text(encoding="utf-8"))
    choix = dict(v4, date_v5="2026-11-05", banano_dense=random.Random(2026).sample(candidates, 6),
                 regle_v5="tuiles banano_dense tirées avant tout résultat du v5 ; planches v4 / v5")
    Path("docs/controle_visuel_v5.json").write_text(json.dumps(choix, indent=2, ensure_ascii=False), encoding="utf-8")
    print(len(candidates), "tuiles candidates ;", choix["banano_dense"])


if __name__ == "__main__":
    main()
