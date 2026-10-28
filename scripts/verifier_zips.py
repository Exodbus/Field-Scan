#!/usr/bin/env python3
"""Vérifie l'intégrité des archives de feuilles téléchargées (sommes MD5 publiées par les dépôts).

Sources des sommes attendues :
  - Tanzanie 2021 : Harvard Dataverse, doi 10.7910/DVN/LQUWXW (API, liste des fichiers) ;
  - Tanzanie 2022-2023 : Zenodo, doi 10.5281/zenodo.7670326 (page du dépôt).

Exemple :
    python scripts/verifier_zips.py
"""
import argparse
import hashlib
from pathlib import Path

ATTENDU = {
    # Tanzanie 2021 (tiret bas dans les noms)
    "BLACK SIGATOKA_1.zip": "a801528927f604eb43ffdba4dbb38dfa",
    "BLACK SIGATOKA_2.zip": "b51c8e45255c440f3c4e3328d215cc25",
    "FUSARIUM WILT_1.zip": "d34af36da8efb6796f72e3d61b9111ea",
    "FUSARIUM WILT_2.zip": "050532bebf75ea3fce2388ca68ff2f85",
    "HEALTHY_1.zip": "1b1526a893ae29385bf14b312f8893bf",
    "HEALTHY_2.zip": "d7a130566e04511c94e1e7db0e02b2a2",
    # Tanzanie 2022-2023 (tiret dans les noms)
    "BLACK SIGATOKA-1.zip": "6b0fef13f54a8e375fc32318f3d5b4aa",
    "FUSARIUM WILT-1.zip": "3ef5c0ffd68c22514b904314bfb96924",
    "HEALTHY-1.zip": "d19fc229988d0e0e9eb26d0ae7c593f8",
}


def md5(chemin):
    h = hashlib.md5()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dossier", default="data/raw/zips")
    args = ap.parse_args(argv)
    dossier = Path(args.dossier)
    bilan = {"OK": 0, "ERREUR": 0, "ABSENT": 0}
    for nom, attendu in ATTENDU.items():
        p = dossier / nom
        if not p.exists():
            etat = "ABSENT"
        else:
            etat = "OK" if md5(p) == attendu else "ERREUR"
        bilan[etat] += 1
        taille = f"{p.stat().st_size / 1e6:,.0f} Mo" if p.exists() else ""
        print(f"{etat:7s} {nom:24s} {taille}")
    print(f"\n{bilan['OK']} OK, {bilan['ERREUR']} en erreur, {bilan['ABSENT']} absents.")
    if bilan["ERREUR"]:
        print("Un fichier en erreur est incomplet ou corrompu : supprime-le et relance son téléchargement.")


if __name__ == "__main__":
    main()
