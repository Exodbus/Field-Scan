#!/usr/bin/env python3
"""Inventaire des jeux de feuilles, sans rien décompresser.

Pour chaque archive de data/raw/zips et chaque dossier déjà décompressé :
  - nombre d'images, extensions, autres fichiers, sous-dossiers ;
  - tailles d'image (lues dans l'en-tête, sans décoder toute l'image) ;
  - une planche de --n images tirées au hasard (graine fixe), pour voir le contenu.

Sorties dans --out : inventaire.csv (une ligne par source), tailles.csv (une ligne
par image), et planches/<source>.jpg.

Exemple :
    python scripts/inventaire_feuilles.py
"""
import argparse
import io
import random
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

import pandas as pd
from PIL import Image, ImageDraw

EXT_IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
DOSSIERS_DECOMPRESSES = {
    "2021_HEALTHY_1 (dossier)": "data/raw/tanzania_2021/healthy_1",
    "2022_HEALTHY-1 (dossier)": "data/raw/tanzania_2022/healthy_1",
    "BananaLSD (dossier)": "data/raw/bananalsd",
}


def campagne(nom):
    """Les noms 2021 ont un tiret bas (HEALTHY_1), ceux de 2022-2023 un tiret (HEALTHY-1)."""
    if "_" in Path(nom).stem and Path(nom).stem.split("_")[-1].isdigit():
        return "tanzanie_2021"
    if "-" in Path(nom).stem and Path(nom).stem.split("-")[-1].isdigit():
        return "tanzanie_2022"
    return "autre"


def sources(dossier_zips):
    """Liste de (nom, type, lecteur) ; le lecteur rend (liste des chemins, fonction d'ouverture)."""
    out = []
    for z in sorted(Path(dossier_zips).glob("*.zip")):
        def lecteur(z=z):
            arch = zipfile.ZipFile(z)
            noms = [n for n in arch.namelist() if not n.endswith("/")]
            return noms, lambda n: arch.open(n)
        out.append((z.name, campagne(z.name), lecteur))
    for nom, chemin in DOSSIERS_DECOMPRESSES.items():
        p = Path(chemin)
        if p.exists():
            def lecteur(p=p):
                noms = [str(f.relative_to(p)).replace("\\", "/") for f in p.rglob("*") if f.is_file()]
                return noms, lambda n: open(p / n, "rb")
            camp = "bananalsd" if "BananaLSD" in nom else ("tanzanie_2021" if "2021" in nom else "tanzanie_2022")
            out.append((nom, camp, lecteur))
    return out


def planche(images, titre, chemin, cote=180, colonnes=6):
    lignes = (len(images) + colonnes - 1) // colonnes
    feuille = Image.new("RGB", (colonnes * cote, lignes * (cote + 16) + 24), "white")
    d = ImageDraw.Draw(feuille)
    d.text((6, 4), titre, fill="black")
    for i, (legende, im) in enumerate(images):
        im = im.convert("RGB")
        im.thumbnail((cote - 6, cote - 6))
        x, y = (i % colonnes) * cote, 24 + (i // colonnes) * (cote + 16)
        feuille.paste(im, (x + (cote - im.width) // 2, y + (cote - im.height) // 2))
        d.text((x + 3, y + cote), legende[-28:], fill="black")
    feuille.save(chemin, quality=85)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zips", default="data/raw/zips")
    ap.add_argument("--out", default="out/feuilles/inventaire")
    ap.add_argument("--n", type=int, default=24, help="images par planche (défaut 24)")
    ap.add_argument("--graine", type=int, default=2026)
    args = ap.parse_args(argv)

    out = Path(args.out)
    (out / "planches").mkdir(parents=True, exist_ok=True)
    resume, tailles = [], []
    for nom, camp, lecteur in sources(args.zips):
        noms, ouvrir = lecteur()
        images = [n for n in noms if PurePosixPath(n).suffix.lower() in EXT_IMAGES]
        autres = [n for n in noms if n not in images]
        sous_dossiers = Counter(str(PurePosixPath(n).parent) for n in images)
        illisibles = 0
        for n in images:
            try:
                with ouvrir(n) as f:
                    im = Image.open(f)  # seul l'en-tête est lu pour la taille
                    l, h = im.size
                tailles.append(dict(source=nom, campagne=camp, fichier=n, largeur=l, hauteur=h))
            except Exception:
                illisibles += 1
        t = pd.DataFrame([x for x in tailles if x["source"] == nom])
        resume.append(dict(
            source=nom, campagne=camp, images=len(images), illisibles=illisibles,
            autres_fichiers=len(autres), exemples_autres="; ".join(sorted(set(PurePosixPath(a).name for a in autres))[:4]),
            sous_dossiers=len(sous_dossiers), principaux_dossiers="; ".join(f"{k} ({v})" for k, v in sous_dossiers.most_common(4)),
            extensions="; ".join(f"{k} ({v})" for k, v in Counter(PurePosixPath(n).suffix.lower() for n in images).items()),
            tailles_distinctes=int(t.groupby(["largeur", "hauteur"]).ngroups) if len(t) else 0,
            taille_la_plus_frequente=("{}x{}".format(*map(int, t.groupby(['largeur', 'hauteur']).size().idxmax())) if len(t) else ""),
            plus_grand_cote_median=int(t[["largeur", "hauteur"]].max(axis=1).median()) if len(t) else 0))
        tirage = random.Random(f"{args.graine}-{nom}").sample(images, min(args.n, len(images)))
        vignettes = []
        for n in tirage:
            try:
                with ouvrir(n) as f:
                    vignettes.append((PurePosixPath(n).name, Image.open(io.BytesIO(f.read()))))
            except Exception:
                pass
        if vignettes:
            nom_fichier = "".join(c if c.isalnum() or c in "-_" else "_" for c in nom) + ".jpg"
            planche(vignettes, f"{nom} : {len(tirage)} images tirées au hasard sur {len(images)}",
                    out / "planches" / nom_fichier)
        print(f"{nom:28s} {camp:14s} {len(images):6d} images, {illisibles} illisibles, {len(autres)} autres fichiers")

    pd.DataFrame(resume).to_csv(out / "inventaire.csv", index=False)
    pd.DataFrame(tailles).to_csv(out / "tailles.csv", index=False)
    print(f"\nInventaire : {out / 'inventaire.csv'} | planches : {out / 'planches'}")


if __name__ == "__main__":
    main()
