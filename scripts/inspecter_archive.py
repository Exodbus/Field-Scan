#!/usr/bin/env python3
"""Décrit une ou plusieurs archives zip sans les décompresser.

Pour chaque archive : taille et empreinte SHA-256 (traçabilité dans le carnet), nombre de
fichiers par extension, nombre d'images par dossier (deux premiers niveaux), fichiers cachés
de macOS (__MACOSX) et zips imbriqués (fréquents sur Mendeley Data), décrits à leur tour.

Exemple :
    python scripts/inspecter_archive.py data/raw/zips/ethiopie_2021.zip data/raw/zips/perou_2026.zip
"""
import argparse
import hashlib
import io
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

EXT_IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def sha256(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def decrire(archive, nom, retrait=""):
    noms = [n for n in archive.namelist() if not n.endswith("/")]
    caches = [n for n in noms if "__MACOSX" in n or PurePosixPath(n).name.startswith("._")]
    utiles = [n for n in noms if n not in caches]
    ext = Counter(PurePosixPath(n).suffix.lower() or "(sans extension)" for n in utiles)
    images = [n for n in utiles if PurePosixPath(n).suffix.lower() in EXT_IMAGES]
    dossiers = Counter("/".join(PurePosixPath(n).parts[:-1][:2]) or "(racine)" for n in images)
    print(f"{retrait}{nom} : {len(noms)} fichiers, dont {len(caches)} cachés de macOS")
    print(f"{retrait}  extensions : " + ", ".join(f"{e} ({k})" for e, k in ext.most_common()))
    print(f"{retrait}  images par dossier :")
    for d, k in sorted(dossiers.items()):
        print(f"{retrait}    {k:6d}  {d}")
    autres = [n for n in utiles if PurePosixPath(n).suffix.lower() not in EXT_IMAGES | {".zip"}]
    if autres:
        print(f"{retrait}  autres fichiers : " + ", ".join(sorted(set(PurePosixPath(a).name for a in autres))[:8]))
    for z in [n for n in utiles if n.lower().endswith(".zip")]:
        print(f"{retrait}  zip imbriqué :")
        with zipfile.ZipFile(io.BytesIO(archive.read(z))) as interne:
            decrire(interne, z, retrait + "    ")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archives", nargs="+")
    args = ap.parse_args(argv)
    for a in args.archives:
        p = Path(a)
        if not p.exists():
            print(f"Introuvable : {p}\n")
            continue
        print(f"=== {p.name} | {p.stat().st_size / 1e6:,.1f} Mo | SHA-256 {sha256(p)}")
        with zipfile.ZipFile(p) as archive:
            decrire(archive, p.name)
        print()


if __name__ == "__main__":
    main()
