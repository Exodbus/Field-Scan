#!/usr/bin/env python3
"""Prospection Roboflow Universe (nuit du 12 novembre 2026, agent C-prospection).

Interroge l'API de recherche de Roboflow Universe avec une liste de requêtes, garde les projets de détection
ou de segmentation, retire les doublons et écrit le tout dans --out (resultats.json, resultats.csv).
La clé d'API est lue dans ~/.roboflow/cle_api et n'est jamais affichée. Aucune image n'est téléchargée ici.

Exemple :
    python scripts/v6_prosp_recherche.py --out data/roboflow_nuit_1112/comptage/_recherche
"""
import argparse
import csv
import json
import time
from pathlib import Path

import requests

REQUETES = [
    "banano", "banana plant", "banana plants", "banana tree", "banana trees", "banana drone", "banana aerial",
    "banana uav", "banana plantation", "banana counting", "banana plant counting", "count banana", "banana crown",
    "banana canopy", "banana orthomosaic", "bananier", "bananiers", "bananeraie", "platano", "plátano", "platanos",
    "plantain", "plantain tree", "plantain drone", "plantas banano", "plantas platano", "conteo banano",
    "conteo platano", "conteo plantas", "conteo de plantas", "matas banano", "mata platano", "bananera", "platanera",
    "finca banano", "banano finca", "banano dron", "platano dron", "cultivo platano", "cultivo banano", "musa",
    "musaceas", "pisang", "pohon pisang", "kebun pisang", "saging", "kela", "banana farm", "banana field",
    "bananeira", "bananal", "bananeiras", "chuoi", "cay chuoi", "banana detection", "banana tree detection",
    "banana plant detection", "plants bana", "bana", "abaca", "enset", "manuel", "jeunes rangs", "plantain",
    "banana tree counting", "tree counting drone", "tree crown drone", "agroforestry drone", "cacao banano",
    "coconut banana", "palm banana", "papaya banana", "crop counting drone", "plant counting uav",
    "class:banana drone", "class:banano", "class:platano", "class:plantain", "class:banana-plant",
    "class:banana-tree", "class:bananier", "class:Banana-plant", "class:banana_tree", "class:banana_plant",
    "class:bananatree", "class:Bananas aerial", "class:pisang", "class:mata", "class:planta",
]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", type=int, default=4)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cle = (Path.home() / ".roboflow" / "cle_api").read_text().strip()
    vus = {}
    for q in REQUETES:
        n_req = 0
        for page in range(1, args.pages + 1):
            try:
                r = requests.get("https://api.roboflow.com/universe/search",
                                 params={"q": q, "page": page, "api_key": cle}, timeout=60)
                res = r.json().get("results", []) if r.status_code == 200 else []
            except Exception as e:                       # la clé ne doit jamais sortir dans un message d'erreur
                print(f"  erreur sur « {q} » page {page} : {type(e).__name__}")
                res = []
            for p in res:
                n_req += 1
                if p["url"] not in vus:
                    p["requetes"] = [q]
                    vus[p["url"]] = p
                elif q not in vus[p["url"]]["requetes"]:
                    vus[p["url"]]["requetes"].append(q)
            if len(res) < 12:
                break
            time.sleep(0.3)
        print(f"{q!r} : {n_req} résultats, {len(vus)} projets distincts au total", flush=True)
    (out / "resultats.json").write_text(json.dumps(list(vus.values()), ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "resultats.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url", "nom", "type", "images", "classes", "licence", "maj", "vignette", "requetes"])
        for p in vus.values():
            w.writerow([p["url"], p["name"], p["type"], p["images"], "|".join(map(str, p.get("classes", [])))[:200],
                        p.get("license"), (p.get("updated") or "")[:10], p.get("thumbnail"), "|".join(p["requetes"])])
    print(f"{len(vus)} projets -> {out / 'resultats.csv'}")


if __name__ == "__main__":
    main()
