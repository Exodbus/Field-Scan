"""Regroupe les photos en sessions de prise de vue d'apres l'heure EXIF.

Usage :
    python scripts/inspect_sessions.py data/raw/tanzania_2021/healthy_1
    python scripts/inspect_sessions.py DOSSIER --ecart 30

Une nouvelle session commence quand deux photos successives (triees par heure)
sont separees de plus de --ecart minutes (30 par defaut). Des photos d'une meme
session viennent tres probablement du meme jardin : on les garde ensemble dans
un meme ensemble (entrainement, validation ou test).

Affiche : jours et sessions, tailles des sessions, lien entre le numero du
fichier (Image_N) et l'heure, et le nombre de carres GPS a trois precisions.
Les coordonnees exactes ne sont pas affichees.
"""
import argparse
import re
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path

from PIL import Image

EXT = {".jpg", ".jpeg", ".png"}
FMT = "%Y:%m:%d %H:%M:%S"


def en_degres(valeurs, ref):
    d, m, s = (float(v) for v in valeurs)
    deg = d + m / 60 + s / 3600
    return -deg if ref in ("S", "W") else deg


def lire(chemin: Path):
    with Image.open(chemin) as im:
        e = im.getexif()
        date = None
        try:
            date = e.get_ifd(0x8769).get(36867)
        except Exception:
            pass
        date = date or e.get(306)
        gps = None
        try:
            g = e.get_ifd(0x8825)
            if g and 2 in g and 4 in g:
                gps = (en_degres(g[2], g.get(1)), en_degres(g[4], g.get(3)))
        except Exception:
            pass
    t = None
    if date:
        try:
            t = datetime.strptime(str(date), FMT)
        except ValueError:
            t = None
    return t, gps


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier", type=Path)
    ap.add_argument("--ecart", type=int, default=30, help="minutes entre deux sessions")
    a = ap.parse_args()
    fichiers = sorted(p for p in a.dossier.rglob("*")
                      if p.is_file() and p.suffix.lower() in EXT)
    if not fichiers:
        raise SystemExit("Aucune image trouvee.")

    avec_heure, gps_pts, sans = [], [], 0
    for f in fichiers:
        try:
            t, gps = lire(f)
        except Exception:
            continue
        if t is None:
            sans += 1
            continue
        avec_heure.append((t, f))
        if gps:
            gps_pts.append(gps)
    print(f"{len(fichiers)} images : {len(avec_heure)} avec une heure, {sans} sans.\n")
    if not avec_heure:
        raise SystemExit("Aucune heure EXIF exploitable.")

    avec_heure.sort(key=lambda x: x[0])
    jours = Counter(t.date().isoformat() for t, _ in avec_heure)
    print(f"Du {avec_heure[0][0]:%Y-%m-%d} au {avec_heure[-1][0]:%Y-%m-%d} : {len(jours)} jours distincts.")
    for j, n in jours.most_common(5):
        print(f"   {j} : {n} images")

    sessions, cour = [], [avec_heure[0]]
    for prec, cur in zip(avec_heure, avec_heure[1:]):
        if (cur[0] - prec[0]).total_seconds() > a.ecart * 60:
            sessions.append(cour)
            cour = []
        cour.append(cur)
    sessions.append(cour)
    tailles = sorted((len(s) for s in sessions), reverse=True)
    print(f"\nSessions (ecart > {a.ecart} min) : {len(sessions)}")
    print(f"   taille mediane {statistics.median(tailles):.0f}, "
          f"plus petite {tailles[-1]}, plus grande {tailles[0]}")
    print("   les 5 plus grosses :", tailles[:5])
    print(f"   sessions d'une seule image : {sum(1 for n in tailles if n == 1)}")

    # le numero de fichier suit-il l'heure ?
    par_num = {}
    for t, f in avec_heure:
        m = re.search(r"(\d+)", f.stem)
        if m:
            par_num[int(m.group(1))] = t
    paires = [(n, n + 1) for n in par_num if n + 1 in par_num]
    if paires:
        proches = sum(1 for x, y in paires
                      if abs((par_num[x] - par_num[y]).total_seconds()) < 600)
        print(f"\nNumeros consecutifs (Image_N, Image_N+1) : {len(paires)} paires,")
        print(f"   {100 * proches / len(paires):.0f} % prises a moins de 10 min d'ecart")
        print("   (proche de 100 % : la numerotation suit l'ordre de prise de vue ;")
        print("    proche de 0 % : les numeros sont melanges)")

    if gps_pts:
        print(f"\nCarres GPS ({len(gps_pts)} images avec position) :")
        for pas, nom in ((0.1, "~11 km"), (0.01, "~1 km"), (0.001, "~100 m")):
            c = Counter((round(la / pas), round(lo / pas)) for la, lo in gps_pts)
            gros = c.most_common(1)[0][1]
            print(f"   carres de {nom:7s} : {len(c):4d} carres, le plus peuple : {gros} images")
