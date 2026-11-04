#!/usr/bin/env python3
"""Images d'origine communes entre un jeu Roboflow évalué et des jeux d'entraînement, d'après les noms de fichiers.

Roboflow garde le nom d'origine avant « _jpg.rf. » (ou _png.rf., _jpeg.rf.) : « 100_0222_jpg.rf.abc.jpg »
vient de « 100_0222 ». Une image d'origine présente à la fois dans la partie évaluée (valid, test) et dans
un jeu d'entraînement est une fuite certaine (plus sûre que l'empreinte d'image).

Sorties dans --out : communes.csv (une ligne par image évaluée : origine, fuite oui/non), propres.txt
(chemins des images sans fuite, utilisable avec evaluer_comptage_roboflow.py --garder).

Exemple :
    python scripts/verifier_sources_communes.py data/roboflow/count_banana_plants.zip --parties valid test \\
        --entrainement data/roboflow/plants_bana_originaux.zip data/roboflow/plants_bana.zip
"""
import argparse
import re
import zipfile
from pathlib import Path, PurePosixPath

import pandas as pd

MOTIF = re.compile(r"^(.*?)_(?:jpg|jpeg|png)\.rf\.", re.IGNORECASE)


def origine(nom):
    base = PurePosixPath(nom).name
    m = MOTIF.match(base)
    return (m.group(1) if m else base.rsplit(".", 1)[0]).lower()


def photo(nom):
    """Photo d'origine : le nom d'origine sans le suffixe d'extension ni les décalages de découpe (« _1440_1920 »).
    Deux morceaux d'une même photo de drone, découpés à des endroits différents, ont la même photo d'origine."""
    o = re.sub(r"_(?:jpg|jpeg|png)$", "", origine(nom))
    return re.sub(r"(?:_\d+){2}$", "", o)


def images(chemin_zip, parties=None):
    for n in zipfile.ZipFile(chemin_zip).namelist():
        if not n.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        partie = PurePosixPath(n).parent.name
        if parties and partie not in parties:
            continue
        yield n, partie


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("evalue")
    ap.add_argument("--parties", nargs="+", default=["valid", "test"])
    ap.add_argument("--entrainement", nargs="+", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    out = Path(args.out or f"out/sources_communes/{Path(args.evalue).stem}")
    out.mkdir(parents=True, exist_ok=True)
    vus, photos = {}, {}
    for z in args.entrainement:
        for n, _ in images(z):
            vus.setdefault(origine(n), Path(z).name)
            photos.setdefault(photo(n), Path(z).name)
    lignes = [dict(image=n, partie=p, origine=origine(n), photo=photo(n), dans=vus.get(origine(n), ""),
                   photo_dans=photos.get(photo(n), "")) for n, p in images(args.evalue, args.parties)]
    df = pd.DataFrame(lignes)
    df["meme_image"] = df.dans != ""
    df["meme_photo"] = df.photo_dans != ""
    df["fuite"] = df.meme_image | df.meme_photo                      # le plus strict des deux
    df.to_csv(out / "communes.csv", index=False)
    (out / "propres.txt").write_text("\n".join(df[~df.fuite].image), encoding="utf-8")
    print(f"{len(vus)} images d'origine dans l'entraînement ({', '.join(Path(z).name for z in args.entrainement)})")
    for p, g in df.groupby("partie"):
        print(f"  {p} : {len(g)} images ({g.photo.nunique()} photos d'origine) ; même image dans l'entraînement : "
              f"{int(g.meme_image.sum())} ; même photo d'origine (autre découpe comprise) : {int(g.meme_photo.sum())}")
    if df.fuite.any():
        print("  exemples de photos communes :", ", ".join(sorted(df[df.fuite].photo.unique())[:8]))
    print(f"Images propres : {int((~df.fuite).sum())} -> {out / 'propres.txt'}")


if __name__ == "__main__":
    main()
