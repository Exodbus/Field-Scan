"""Inspecte les tailles et les metadonnees d'un dossier d'images.

Usage :
    python scripts/inspect_sizes.py data/raw/tanzania_2022/healthy_1
    python scripts/inspect_sizes.py DOSSIER --sortie out/tailles_2022.jpg --max_groupes 8

Affiche :
  - le nombre de tailles distinctes et les N plus frequentes ;
  - un resume : orientation (paysage / portrait / carre), rapport
    largeur/hauteur et megapixels (min, mediane, max) ;
  - les metadonnees EXIF (marque, modele, date, GPS) ;
  - out/tailles.jpg : 4 images par groupe, SANS deformer leur proportion, pour
    les N tailles les plus frequentes, plus une ligne « autres tailles ».
"""
import argparse
import random
import statistics
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

EXT = {".jpg", ".jpeg", ".png"}


def lire(chemin: Path):
    with Image.open(chemin) as im:
        e = im.getexif()
        gps_coord = False
        try:
            g = e.get_ifd(0x8825)
            gps_coord = bool(g) and 2 in g and 4 in g
        except Exception:
            pass
        return im.size, {
            "marque": e.get(271) is not None,
            "modele": e.get(272) is not None,
            "date": e.get(306) is not None,
            "gps_balise": 34853 in e,
            "gps_coord": gps_coord,
        }


def quantile(valeurs, q):
    v = sorted(valeurs)
    return v[min(len(v) - 1, int(q * (len(v) - 1) + 0.5))]


def miniature(f: Path, cote: int):
    with Image.open(f) as im:
        try:
            im.draft("RGB", (cote * 2, cote * 2))  # decodage rapide des gros JPEG
        except Exception:
            pass
        im = im.convert("RGB")
        im.thumbnail((cote, cote))
        return im


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier", type=Path)
    ap.add_argument("--sortie", type=Path, default=Path("out/tailles.jpg"))
    ap.add_argument("--par_groupe", type=int, default=4)
    ap.add_argument("--max_groupes", type=int, default=8,
                    help="nombre de tailles affichees (listes et planche)")
    a = ap.parse_args()

    fichiers = sorted(p for p in a.dossier.rglob("*")
                      if p.is_file() and p.suffix.lower() in EXT)
    if not fichiers:
        raise SystemExit("Aucune image trouvee.")

    groupes = defaultdict(list)
    exif = {"marque": 0, "modele": 0, "date": 0, "gps_balise": 0, "gps_coord": 0}
    illisibles = 0
    for f in fichiers:
        try:
            taille, meta = lire(f)
        except Exception:
            illisibles += 1
            continue
        groupes[taille].append(f)
        for k, v in meta.items():
            exif[k] += int(v)

    total = sum(len(v) for v in groupes.values())
    print(f"{total} images lisibles ({illisibles} illisibles)")
    print(f"{len(groupes)} tailles distinctes\n")

    ordre = sorted(groupes, key=lambda t: -len(groupes[t]))
    print(f"Les {min(a.max_groupes, len(ordre))} tailles les plus frequentes :")
    for t in ordre[:a.max_groupes]:
        n = len(groupes[t])
        print(f"  {str(t):12s} {n:5d} images  {100 * n / total:5.1f} %   l/h = {t[0] / t[1]:.2f}")
    reste = sum(len(groupes[t]) for t in ordre[a.max_groupes:])
    if reste:
        print(f"  autres tailles ({len(ordre) - a.max_groupes} tailles) : {reste} images, {100 * reste / total:.1f} %")

    toutes = [t for t in groupes for _ in groupes[t]]
    rapports = [w / h for w, h in toutes]
    mp = [w * h / 1e6 for w, h in toutes]
    paysage = sum(1 for r in rapports if r > 1.05)
    portrait = sum(1 for r in rapports if r < 0.95)
    carre = len(rapports) - paysage - portrait
    print("\nResume :")
    print(f"  orientation : paysage {paysage}, portrait {portrait}, a peu pres carre (l/h entre 0,95 et 1,05) {carre}")
    print("  rapport largeur/hauteur : min {:.2f} | 10 % {:.2f} | mediane {:.2f} | 90 % {:.2f} | max {:.2f}".format(
        min(rapports), quantile(rapports, .1), statistics.median(rapports), quantile(rapports, .9), max(rapports)))
    print("  megapixels : min {:.2f} | mediane {:.2f} | max {:.2f}".format(
        min(mp), statistics.median(mp), max(mp)))
    cotes = [c for t in toutes for c in t]
    print(f"  plus grand cote : min {min(max(t) for t in toutes)} | mediane {statistics.median(max(t) for t in toutes):.0f} | max {max(cotes)}")

    print("\nMetadonnees EXIF presentes (nombre d'images) :")
    noms = {"marque": "marque", "modele": "modele", "date": "date",
            "gps_balise": "balise GPS (peut etre vide)", "gps_coord": "GPS avec coordonnees"}
    for k, v in exif.items():
        print(f"  {noms[k]:28s} : {v} sur {total}")

    random.seed(0)
    cote = 200
    lignes = [(f"{t[0]}x{t[1]}  ({len(groupes[t])} images)", groupes[t]) for t in ordre[:a.max_groupes]]
    if reste:
        autres = [f for t in ordre[a.max_groupes:] for f in groupes[t]]
        lignes.append((f"autres tailles ({len(autres)} images)", autres))
    planche = Image.new("RGB", (a.par_groupe * (cote + 4), len(lignes) * (cote + 16)), "white")
    dr = ImageDraw.Draw(planche)
    for i, (titre, liste) in enumerate(lignes):
        y0 = i * (cote + 16)
        dr.text((2, y0 + 2), titre, fill="black")
        for j, f in enumerate(random.sample(liste, min(a.par_groupe, len(liste)))):
            try:
                planche.paste(miniature(f, cote), (j * (cote + 4), y0 + 14))
            except Exception:
                pass
    a.sortie.parent.mkdir(parents=True, exist_ok=True)
    planche.save(a.sortie)
    print(f"\nPlanche : {a.sortie}  (une ligne par groupe, dans l'ordre ci-dessus)")
