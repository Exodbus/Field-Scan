"""Explore un jeu d'images organise en sous-dossiers (un dossier = une classe).

Usage :
    python scripts/explore_dataset.py data/raw/bananalsd
    python scripts/explore_dataset.py data/raw/bananalsd --montage out/montage.jpg

Affiche, pour chaque dossier contenant des images : le nombre d'images,
les formats et les tailles trouvees. Sauve aussi une planche d'echantillons.
"""
import argparse
import random
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


def lister(racine: Path):
    """Regroupe les images par dossier parent."""
    groupes = defaultdict(list)
    for p in racine.rglob("*"):
        if p.is_file() and p.suffix.lower() in EXT:
            groupes[p.parent].append(p)
    return groupes


def resume(racine: Path, groupes):
    total = 0
    for dossier in sorted(groupes):
        fichiers = groupes[dossier]
        total += len(fichiers)
        tailles, formats = Counter(), Counter()
        for f in fichiers:
            try:
                with Image.open(f) as im:
                    tailles[im.size] += 1
                    formats[im.format] += 1
            except Exception as e:  # image illisible
                tailles[f"ILLISIBLE ({type(e).__name__})"] += 1
        print(f"\n{dossier.relative_to(racine)}  ->  {len(fichiers)} images")
        print("   formats :", dict(formats))
        print("   tailles :", dict(tailles.most_common(3)),
              "..." if len(tailles) > 3 else "")
    print(f"\nTOTAL : {total} images dans {len(groupes)} dossiers")


def montage(groupes, sortie: Path, par_classe=4, cote=160):
    """Une ligne par dossier, quelques images au hasard par ligne."""
    random.seed(0)
    dossiers = sorted(groupes)
    planche = Image.new("RGB", (par_classe * cote, len(dossiers) * cote), "white")
    for i, d in enumerate(dossiers):
        choix = random.sample(groupes[d], min(par_classe, len(groupes[d])))
        j = 0
        for f in choix:
            try:
                with Image.open(f) as im:
                    im = im.convert("RGB").resize((cote, cote))
                    planche.paste(im, (j * cote, i * cote))
                    j += 1
            except Exception:
                print("Image ignoree (illisible) :", f)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    planche.save(sortie)
    print("Planche d'echantillons :", sortie)
    print("Lignes, de haut en bas :", [d.name for d in dossiers])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier", type=Path)
    ap.add_argument("--montage", type=Path, default=Path("out/montage.jpg"))
    a = ap.parse_args()
    if not a.dossier.exists():
        raise SystemExit(f"Dossier introuvable : {a.dossier}")
    g = lister(a.dossier)
    if not g:
        raise SystemExit("Aucune image trouvee dans ce dossier.")
    resume(a.dossier, g)
    montage(g, a.montage)
