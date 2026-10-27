"""Cherche les images identiques ou quasi identiques dans un dossier.

Usage :
    python scripts/find_duplicates.py data/raw/bananalsd/.../OriginalSet

Methode : empreinte perceptuelle (aHash 16x16, grossiere) pour reperer des
candidates, puis verification : fichiers strictement identiques (SHA-256) et
ecart moyen de pixels (0 = memes pixels, 255 = tout different).
Une planche des paires est sauvee dans out/doublons.jpg (gauche | droite).
"""
import argparse
import hashlib
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


def empreinte(chemin: Path, n: int = 16) -> int:
    with Image.open(chemin) as im:
        im = im.convert("L").resize((n, n))
        px = list(im.tobytes())
    moy = sum(px) / len(px)
    bits = 0
    for p in px:
        bits = (bits << 1) | (1 if p > moy else 0)
    return bits


def distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def sha(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def ecart_pixels(x: Path, y: Path) -> float:
    with Image.open(x) as a, Image.open(y) as b:
        a = a.convert("RGB").resize((224, 224))
        b = b.convert("RGB").resize((224, 224))
        d = ImageChops.difference(a, b)
        px = d.tobytes()
    return sum(px) / len(px)


def planche(paires, sortie: Path, maxi=8, cote=224):
    """Une ligne par paire : image de gauche | image de droite."""
    # les paires entre classes differentes d'abord
    ordre = sorted(paires, key=lambda t: (t[1].parent == t[2].parent, t[0]))[:maxi]
    img = Image.new("RGB", (2 * cote, len(ordre) * cote), "white")
    dr = ImageDraw.Draw(img)
    for i, (d, x, y, *_r) in enumerate(ordre):
        for j, f in enumerate((x, y)):
            try:
                with Image.open(f) as im:
                    img.paste(im.convert("RGB").resize((cote, cote)), (j * cote, i * cote))
            except Exception:
                pass
            dr.rectangle([j * cote, i * cote, j * cote + 150, i * cote + 12], fill="black")
            dr.text((j * cote + 2, i * cote), f"{f.parent.name}/{f.name}", fill="white")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    img.save(sortie)
    print(f"Planche des {len(ordre)} premieres paires (entre classes d'abord) : {sortie}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier", type=Path)
    ap.add_argument("--seuil", type=int, default=10,
                    help="distance max (sur 256 bits) pour parler de candidat")
    ap.add_argument("--planche", type=Path, default=Path("out/doublons.jpg"))
    a = ap.parse_args()
    fichiers = sorted(p for p in a.dossier.rglob("*")
                      if p.is_file() and p.suffix.lower() in EXT)
    if not fichiers:
        raise SystemExit("Aucune image trouvee.")
    emp = []
    for f in fichiers:
        try:
            emp.append((f, empreinte(f)))
        except Exception as e:
            print("Ignoree :", f.name, type(e).__name__)
    paires = []
    for i in range(len(emp)):
        for j in range(i + 1, len(emp)):
            d = distance(emp[i][1], emp[j][1])
            if d <= a.seuil:
                x, y = emp[i][0], emp[j][0]
                identiques = sha(x) == sha(y)
                ecart = ecart_pixels(x, y)
                paires.append((d, x, y, identiques, ecart))
    paires.sort(key=lambda t: (t[4], t[0]))
    ident = sum(1 for p in paires if p[3])
    quasi = sum(1 for p in paires if not p[3] and p[4] < 5)
    print(f"{len(emp)} images analysees, {len(paires)} paires candidates (seuil {a.seuil}).")
    print(f"  fichiers strictement identiques : {ident}")
    print(f"  quasi identiques (ecart de pixels < 5, fichiers differents) : {quasi}")
    memes = sum(1 for p in paires if p[1].parent == p[2].parent)
    print(f"  dans la meme classe : {memes} | entre classes differentes : {len(paires) - memes}")
    print("\nLes 15 paires les plus proches (ecart de pixels croissant) :")
    for d, x, y, identiques, ecart in paires[:15]:
        marque = "IDENTIQUES" if identiques else f"ecart={ecart:5.1f}"
        print(f"  {marque:>12}  {x.parent.name}/{x.name}  <->  {y.parent.name}/{y.name}")
    entre = [p for p in paires if p[1].parent != p[2].parent]
    if entre:
        print("\nPaires entre classes differentes :")
        for d, x, y, identiques, ecart in entre:
            marque = "IDENTIQUES" if identiques else f"ecart={ecart:5.1f}"
            print(f"  {marque:>12}  {x.parent.name}/{x.name}  <->  {y.parent.name}/{y.name}")
    if paires:
        planche(paires, a.planche)
