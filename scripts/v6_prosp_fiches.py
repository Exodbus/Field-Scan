#!/usr/bin/env python3
"""Fiche Roboflow (API) de chaque projet candidat : auteur, licence, versions, nombre d'images et d'annotations,
classes, prétraitements et augmentations de chaque version. Aucune image n'est téléchargée.

Exemple :
    python scripts/v6_prosp_fiches.py --out data/roboflow_nuit_1112/comptage/_recherche/fiches.json ws/projet ...
"""
import argparse
import json
from pathlib import Path

import requests


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("projets", nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    cle = (Path.home() / ".roboflow" / "cle_api").read_text().strip()
    sortie = Path(args.out)
    fiches = json.loads(sortie.read_text(encoding="utf-8")) if sortie.exists() else {}
    for p in args.projets:
        try:
            r = requests.get(f"https://api.roboflow.com/{p}", params={"api_key": cle}, timeout=60)
            j = r.json()
        except Exception as e:
            print(p, "erreur", type(e).__name__); continue
        if "project" not in j:
            print(p, "pas de fiche", str(j)[:150].replace(cle, "***")); continue
        pr = j["project"]
        vers = []
        for v in j.get("versions", []):
            vers.append(dict(id=v["id"].split("/")[-1], images=v.get("images"), splits=v.get("splits"),
                             pretraitement=v.get("preprocessing"), augmentation=v.get("augmentation"),
                             cree=v.get("created")))
        fiches[p] = dict(nom=pr.get("name"), images=pr.get("images"), annotation=pr.get("annotation"),
                         classes=pr.get("classes"), licence=pr.get("license"), cree=pr.get("created"),
                         maj=pr.get("updated"), espace=j.get("workspace", {}).get("name"), versions=vers)
        cl = pr.get("classes") or {}
        print(f"{p} | {pr.get('images')} im | {pr.get('license')} | classes {dict(list(cl.items())[:6])} | "
              f"versions {[(v['id'], v['images'], bool(v['augmentation'])) for v in vers][:6]}")
    sortie.write_text(json.dumps(fiches, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
