#!/usr/bin/env python3
"""Téléchargement d'exports Roboflow Universe au format COCO, un zip par jeu, jamais décompressé ni exécuté.

Chaque argument : nom_local=espace/projet/version. Le zip va dans --racine/<nom_local>/<nom_local>.zip, avec une fiche
source.json (URL, version, date du téléchargement, MD5 du zip). La clé d'API est lue dans ~/.roboflow/cle_api et
n'est jamais affichée ni écrite.

Exemple :
    python scripts/v6_prosp_telecharger.py --racine data/roboflow_nuit_1112/comptage conteo_banano=oswaldos-workspace-emjqk/conteo-banano-h8avt/6
"""
import argparse
import datetime
import hashlib
import json
import time
from pathlib import Path

import requests


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jeux", nargs="+")
    ap.add_argument("--racine", required=True)
    ap.add_argument("--format", default="coco")
    args = ap.parse_args(argv)
    cle = (Path.home() / ".roboflow" / "cle_api").read_text().strip()
    for jeu in args.jeux:
        nom, chemin = jeu.split("=")
        d = Path(args.racine) / nom
        d.mkdir(parents=True, exist_ok=True)
        z = d / f"{nom}.zip"
        if z.exists():
            print(nom, "déjà là"); continue
        lien = None
        for essai in range(30):                      # l'export est préparé côté serveur : on attend qu'il soit prêt
            try:
                r = requests.get(f"https://api.roboflow.com/{chemin}/{args.format}", params={"api_key": cle}, timeout=120)
                j = r.json()
            except Exception as e:
                print(nom, "erreur", type(e).__name__); time.sleep(10); continue
            lien = (j.get("export") or {}).get("link")
            if lien:
                break
            if r.status_code >= 400 and "progress" not in str(j):
                print(nom, "refus", r.status_code, str(j)[:200].replace(cle, "***")); break
            time.sleep(10)
        if not lien:
            print(nom, "pas de lien d'export"); continue
        h = hashlib.md5()
        with requests.get(lien, stream=True, timeout=600) as r, open(z, "wb") as f:
            for bloc in r.iter_content(1 << 20):
                f.write(bloc); h.update(bloc)
        ws, proj, ver = chemin.split("/")
        (d / "source.json").write_text(json.dumps(dict(
            url=f"https://universe.roboflow.com/{ws}/{proj}", version=ver, format=args.format,
            telecharge=datetime.datetime.now().isoformat(timespec="seconds"), md5_zip=h.hexdigest(),
            octets=z.stat().st_size), ensure_ascii=False, indent=1), encoding="utf-8")
        print(nom, f"{z.stat().st_size / 1e6:.1f} Mo")


if __name__ == "__main__":
    main()
