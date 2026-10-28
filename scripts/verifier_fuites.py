#!/usr/bin/env python3
"""Vérification visuelle des « fuites visuelles » repérées par preparer_feuilles.py.

Pour chaque image exclue comme fuite visuelle, affiche côte à côte l'image exclue et l'image
d'un ensemble antérieur qui a confirmé l'alerte : parmi les candidats proposés par l'empreinte
(dHash à au plus --seuil-candidat bits), celle dont la vignette 16 x 16 en couleur est la plus
proche. Les deux mesures (bits d'empreinte, écart de vignette) sont indiquées. Permet de distinguer de vraies fuites (même photo) de fausses alertes
(images différentes mais d'empreintes voisines, typiquement des surfaces peu texturées).

Sorties dans --out : paires.csv et planches paires_<ensemble>_NN.jpg.

Exemple :
    python scripts/verifier_fuites.py
"""
import argparse
import io
import zipfile
from pathlib import Path

import sys

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preparer_feuilles import ouvrir_uniformisee, vignette  # noqa: E402  (mêmes calculs que la préparation)

ORDRE = ["entrainement", "validation", "test"]


def lire_octets_origine(ligne, args, archives):
    """Octets du fichier d'origine d'une ligne de l'index (les images exclues n'ont pas été écrites)."""
    conteneur, membre = ligne.cle.split("::", 1)
    z = Path(args.zips) / conteneur
    if z.exists():
        a = archives.setdefault(str(z), zipfile.ZipFile(z))
        return a.read(membre)
    if conteneur == "OriginalSet":
        trouves = [p for p in Path(args.bananalsd).rglob(Path(membre).name)
                   if "originalset" in [x.lower() for x in p.parts] and p.parent.name == Path(membre).parent.name]
        return trouves[0].read_bytes()
    base = Path(args.sain_2021 if ligne.source == "tanzanie_2021" else args.sain_2022)
    return (base / membre).read_bytes()


def vignette_affichage(im, cote):
    im = im.copy()
    im.thumbnail((cote, cote))
    fond = Image.new("RGB", (cote, cote), "white")
    fond.paste(im, ((cote - im.width) // 2, (cote - im.height) // 2))
    return fond


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--index", default="data/feuilles/index.csv")
    ap.add_argument("--images", default="data/feuilles")
    ap.add_argument("--zips", default="data/raw/zips")
    ap.add_argument("--sain-2021", default="data/raw/tanzania_2021/healthy_1")
    ap.add_argument("--sain-2022", default="data/raw/tanzania_2022/healthy_1")
    ap.add_argument("--bananalsd", default="data/raw/bananalsd")
    ap.add_argument("--out", default="out/feuilles/fuites")
    ap.add_argument("--par-planche", type=int, default=12)
    ap.add_argument("--seuil-candidat", type=int, default=6)
    ap.add_argument("--cote", type=int, default=256)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    idx = pd.read_csv(args.index)
    idx["h"] = idx.dhash.map(lambda x: int(str(x), 16)).astype(np.uint64)
    fuites = idx[idx.motif == "fuite_visuelle"]
    lignes, archives = [], {}
    for _, f in fuites.iterrows():
        anterieurs = idx[idx.ensemble.isin(ORDRE[:ORDRE.index(f.ensemble)]) & idx.retenue]
        d = np.bitwise_count(anterieurs.h.to_numpy() ^ np.uint64(f.h))
        candidats = anterieurs[d <= args.seuil_candidat].assign(bits=d[d <= args.seuil_candidat])
        im_ex, _ = ouvrir_uniformisee(lire_octets_origine(f, args, archives), args.cote)  # comme la préparation
        v_ex = vignette(im_ex)
        ecarts = [float(np.abs(v_ex - vignette(Image.open(Path(args.images) / c.chemin).convert("RGB"))).mean())
                  for c in candidats.itertuples()]
        k = int(np.argmin(ecarts))
        proche = candidats.iloc[k]
        lignes.append(dict(ensemble=f.ensemble, classe=f.classe, exclue=f.cle, proche=proche.cle,
                           classe_proche=proche.classe, ensemble_proche=proche.ensemble,
                           distance_bits=int(proche.bits), ecart_vignette=round(ecarts[k], 2),
                           candidats=len(candidats), taille_exclue=f"{f.largeur_origine}x{f.hauteur_origine}",
                           taille_proche=f"{proche.largeur_origine}x{proche.hauteur_origine}", _f=f, _p=proche))
    paires = pd.DataFrame(lignes)
    if paires.empty:
        print("Aucune fuite visuelle dans l'index.")
        return
    paires.drop(columns=["_f", "_p"]).to_csv(out / "paires.csv", index=False)
    print("Fuites visuelles : paire qui a confirmé chaque alerte")
    print(paires[["ensemble", "classe", "exclue", "proche", "distance_bits", "ecart_vignette", "candidats"]].to_string(index=False))

    cote = 200
    for ens, groupe in paires.groupby("ensemble"):
        for n, debut in enumerate(range(0, len(groupe), args.par_planche), start=1):
            bloc = groupe.iloc[debut:debut + args.par_planche]
            planche = Image.new("RGB", (2 * cote + 10, len(bloc) * (cote + 30)), "white")
            d = ImageDraw.Draw(planche)
            for k, (_, p) in enumerate(bloc.iterrows()):
                y = k * (cote + 30)
                exclue, _ = ouvrir_uniformisee(lire_octets_origine(p._f, args, archives), args.cote)
                proche = Image.open(Path(args.images) / p._p.chemin).convert("RGB")
                planche.paste(vignette_affichage(exclue, cote), (0, y + 28))
                planche.paste(vignette_affichage(proche, cote), (cote + 10, y + 28))
                d.text((2, y + 2), f"{p.distance_bits} bits, écart {p.ecart_vignette} | exclue ({p.classe}) : {p.exclue[-30:]}", fill="red")
                d.text((2, y + 14), f"la plus proche ({p.ensemble_proche}, {p.classe_proche}) : {p.proche[-34:]}", fill="black")
            planche.save(out / f"paires_{ens}_{n:02d}.jpg", quality=85)
    print(f"\nPlanches et liste des paires dans {out}/")


if __name__ == "__main__":
    main()
