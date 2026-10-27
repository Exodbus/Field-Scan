"""Croise tailles d'image et metadonnees EXIF dans un dossier.

Usage :
    python scripts/inspect_exif.py data/raw/tanzania_2021/healthy_1

Affiche :
  1. pour chaque taille : combien d'images ont des metadonnees EXIF / un GPS ;
  2. les marques et modeles de telephone ;
  3. les dates de prise de vue, comptees par mois ;
  4. les positions GPS regroupees par carres de 0,1 degre (environ 11 km),
     pour voir si plusieurs zones (donc plusieurs sites) sont presentes.
Les coordonnees exactes ne sont pas affichees.
"""
import argparse
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

EXT = {".jpg", ".jpeg", ".png"}


def en_degres(valeurs, ref):
    d, m, s = (float(v) for v in valeurs)
    deg = d + m / 60 + s / 3600
    return -deg if ref in ("S", "W") else deg


def lire(chemin: Path):
    with Image.open(chemin) as im:
        e = im.getexif()
        taille = im.size
        marque, modele, date = e.get(271), e.get(272), e.get(306)
        gps = None
        try:
            g = e.get_ifd(0x8825)
            if g and 2 in g and 4 in g:
                gps = (en_degres(g[2], g.get(1)), en_degres(g[4], g.get(3)))
        except Exception:
            gps = None
    return taille, marque, modele, date, gps


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier", type=Path)
    a = ap.parse_args()
    fichiers = sorted(p for p in a.dossier.rglob("*")
                      if p.is_file() and p.suffix.lower() in EXT)
    if not fichiers:
        raise SystemExit("Aucune image trouvee.")

    par_taille = defaultdict(lambda: {"n": 0, "exif": 0, "gps": 0})
    modeles, mois, zones = Counter(), Counter(), Counter()
    lisibles = 0
    for f in fichiers:
        try:
            taille, marque, modele, date, gps = lire(f)
        except Exception:
            continue
        lisibles += 1
        t = par_taille[taille]
        t["n"] += 1
        if marque or modele or date:
            t["exif"] += 1
            modeles[f"{marque} {modele}".strip()] += 1
        if date:
            mois[str(date)[:7].replace(":", "-")] += 1
        if gps:
            t["gps"] += 1
            zones[(round(gps[0], 1), round(gps[1], 1))] += 1

    print(f"{lisibles} images lisibles\n")
    print("1. Metadonnees par taille (images | avec EXIF | avec GPS) :")
    for taille in sorted(par_taille, key=lambda t: -par_taille[t]["n"]):
        t = par_taille[taille]
        print(f"   {str(taille):12s} {t['n']:5d} | {t['exif']:5d} | {t['gps']:5d}")
    print("\n2. Marques et modeles (images avec EXIF) :")
    for m, n in modeles.most_common(10):
        print(f"   {n:5d}  {m}")
    print("\n3. Dates de prise de vue par mois :")
    for m in sorted(mois):
        print(f"   {m} : {mois[m]}")
    print(f"\n4. Zones GPS (carres de 0,1 degre) : {len(zones)} zones, "
          f"{sum(zones.values())} images avec GPS")
    for i, (z, n) in enumerate(zones.most_common(10), 1):
        print(f"   zone {i:2d} : {n} images")
