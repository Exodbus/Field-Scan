#!/usr/bin/env python3
"""Planche des vignettes des projets Universe trouvés par v6_prosp_recherche.py, pour repérer à l'œil les vues du ciel.

Seules les vignettes publiques (quelques ko) sont téléchargées, dans --dossier/vignettes ; elles ne sont jamais exécutées.
Les projets dont les classes parlent de fruits, de maladies ou d'objets sans rapport sont laissés de côté.

Exemple :
    python scripts/v6_prosp_vignettes.py --dossier data/roboflow_nuit_1112/comptage/_recherche
"""
import argparse
import io
import re
from pathlib import Path

import pandas as pd
import requests
from PIL import Image, ImageDraw

HORS_SUJET = re.compile(r"ripe|rotten|fresh|peel|apple|orange|sigatoka|leaf|disease|degree|level|busuk|matang|person|"
                        r"\bcar\b|helmet|mentah|masak|bunch|racimo|maduro|fruit|uav|drone|gun|plane|ship|horse|"
                        r"lesion|bruise|cavendish|pisang_|cell-phone", re.I)
SUJET = re.compile(r"banan|platan|plantain|pisang|chuoi|musa|tree|plant|aerial|conteo|count", re.I)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--par-planche", type=int, default=60)
    args = ap.parse_args(argv)
    d = Path(args.dossier)
    (d / "vignettes").mkdir(exist_ok=True)
    df = pd.read_csv(d / "resultats.csv")
    df = df[df.type.isin(["object-detection", "instance-segmentation", "keypoint-detection"])]
    df = df[~df.classes.astype(str).str.contains(HORS_SUJET) & (df.url + df.nom + df.classes.astype(str)).str.contains(SUJET)]
    df = df.sort_values("images", ascending=False).reset_index(drop=True)
    c, cols = 150, 10
    for debut in range(0, len(df), args.par_planche):
        bloc = df.iloc[debut:debut + args.par_planche]
        rangs = -(-len(bloc) // cols)
        planche = Image.new("RGB", (cols * c, rangs * (c + 14)), "white")
        dr = ImageDraw.Draw(planche)
        for k, (i, r) in enumerate(bloc.iterrows()):
            f = d / "vignettes" / f"{i:03d}.jpg"
            try:
                if not f.exists():
                    f.write_bytes(requests.get(r.vignette, timeout=30).content)
                im = Image.open(io.BytesIO(f.read_bytes())).convert("RGB").resize((c, c))
            except Exception:
                im = Image.new("RGB", (c, c), "gray")
            x, y = (k % cols) * c, (k // cols) * (c + 14)
            planche.paste(im, (x, y))
            dr.text((x + 2, y + c + 1), f"{i} ({r.images})", fill="black")
        planche.save(d / f"planche_vignettes_{debut:03d}.jpg", quality=85)
    df[["url", "nom", "images", "classes", "licence", "maj"]].to_csv(d / "candidats_vignettes.csv")
    print(len(df), "projets sur les planches")


if __name__ == "__main__":
    main()
