#!/usr/bin/env python3
"""Repérage semi-automatique des photos de tiges (coupes de pseudo-tronc) parmi la fusariose 2021.

Le test (BananaLSD) ne contient que des feuilles : les photos de tiges sont exclues de
l'entraînement. Il y en a des centaines, trop pour un tri entièrement manuel, mais elles
sont visuellement très typiques. Deux étapes :

1. classer (par défaut) : un réseau pré-entraîné sur ImageNet (EfficientNet-B0, torchvision)
   résume chaque image en un vecteur. Score d'une image = ressemblance (cosinus) maximale avec
   les tiges repérées sur les planches d'inventaire, moins ressemblance maximale avec les
   feuilles de ces mêmes planches. Les images sont rangées par score décroissant et affichées
   sur des pages numérotées (out/feuilles/tiges/pages/).

2. valider : après avoir regardé les pages, on indique jusqu'à quel rang ce sont des tiges,
   et les exceptions éventuelles ; le script écrit la liste d'exclusion (versionnée).

Exemples :
    python scripts/reperer_tiges.py
    python scripts/reperer_tiges.py --valider --jusqu-au-rang 520 --garder-rangs 87 312 --exclure-rangs 534 601
"""
import argparse
import io
import zipfile
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

ZIPS_PAR_DEFAUT = ["FUSARIUM WILT_1.zip", "FUSARIUM WILT_2.zip"]
EXT_IMAGES = {".jpg", ".jpeg", ".png"}

# Exemples repérés sur les planches d'inventaire (graine 2026)
TIGES = {
    "FUSARIUM WILT_1.zip": ["Image_1100", "Image_3069", "Image_1653", "Image_1815"],
    "FUSARIUM WILT_2.zip": ["Image_3531", "Image_4103"],
}
FEUILLES = {
    "FUSARIUM WILT_1.zip": ["Image_496", "Image_1705", "Image_1376", "Image_1645", "Image_83", "Image_3450",
                            "Image_74", "Image_1284", "Image_1424", "Image_1753", "Image_303", "Image_1902",
                            "Image_1197", "Image_1078", "Image_1235", "Image_1422", "Image_425", "Image_2058",
                            "Image_491", "Image_1763"],
    "FUSARIUM WILT_2.zip": ["Image_4395", "Image_4154", "Image_4451", "Image_5904", "Image_4423", "Image_5467",
                            "Image_5024", "Image_4506", "Image_5628", "Image_4104", "Image_4963", "Image_3667",
                            "Image_4599", "Image_4865", "Image_4408", "Image_5897", "Image_5405", "Image_4083",
                            "Image_5645", "Image_3868", "Image_4798", "Image_5074"],
}


def lister_images(zips):
    """(zip, membre) de chaque vraie image, sans le dossier __MACOSX créé par macOS."""
    out = []
    for z in zips:
        with zipfile.ZipFile(z) as a:
            for n in a.namelist():
                if n.endswith("/") or "__MACOSX" in n or PurePosixPath(n).name.startswith("._"):
                    continue
                if PurePosixPath(n).suffix.lower() in EXT_IMAGES:
                    out.append((Path(z).name, n))
    return out


def charger(chemin_zip, membre):
    with zipfile.ZipFile(chemin_zip) as a, a.open(membre) as f:
        return Image.open(io.BytesIO(f.read())).convert("RGB")


def calculer_vecteurs(images, dossier_zips, lot=32):
    """Vecteurs EfficientNet-B0 (ImageNet), normalisés, une ligne par image."""
    import torch
    from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0

    poids = EfficientNet_B0_Weights.DEFAULT
    modele = efficientnet_b0(weights=poids)
    modele.classifier = torch.nn.Identity()
    modele.eval()
    preparer = poids.transforms()
    vecteurs = []
    with torch.no_grad():
        for i in range(0, len(images), lot):
            x = torch.stack([preparer(charger(Path(dossier_zips) / z, m)) for z, m in images[i:i + lot]])
            vecteurs.append(modele(x).numpy())
            print(f"\r  {min(i + lot, len(images))}/{len(images)} images", end="", flush=True)
    print()
    v = np.concatenate(vecteurs)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def indices_exemples(images, exemples):
    cles = {(z, n) for z, noms in exemples.items() for n in noms}
    idx = [i for i, (z, m) in enumerate(images) if (z, PurePosixPath(m).stem) in cles]
    trouves = {(images[i][0], PurePosixPath(images[i][1]).stem) for i in idx}
    return idx, len(cles - trouves)


def pages(classement, dossier_zips, dossier, par_page=96, colonnes=12, cote=120, max_rang=None):
    dossier.mkdir(parents=True, exist_ok=True)
    lignes_tab = classement if max_rang is None else classement[classement.rang <= max_rang]
    for p, debut in enumerate(range(0, len(lignes_tab), par_page), start=1):
        bloc = lignes_tab.iloc[debut:debut + par_page]
        lignes = (len(bloc) + colonnes - 1) // colonnes
        feuille = Image.new("RGB", (colonnes * cote, lignes * (cote + 14) + 20), "white")
        d = ImageDraw.Draw(feuille)
        d.text((4, 3), f"Rangs {bloc.rang.min()} à {bloc.rang.max()} (du plus « tige » au plus « feuille »)", fill="black")
        for k, (_, r) in enumerate(bloc.iterrows()):
            im = charger(Path(dossier_zips) / r.zip, r.membre)
            im.thumbnail((cote - 4, cote - 4))
            x, y = (k % colonnes) * cote, 20 + (k // colonnes) * (cote + 14)
            feuille.paste(im, (x + (cote - im.width) // 2, y + (cote - im.height) // 2))
            d.text((x + 2, y + cote), f"{r.rang}", fill="red")
        feuille.save(dossier / f"page_{p:02d}.jpg", quality=80)
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zips", default="data/raw/zips")
    ap.add_argument("--fichiers", nargs="+", default=ZIPS_PAR_DEFAUT)
    ap.add_argument("--out", default="out/feuilles/tiges")
    ap.add_argument("--pages-jusqu-au-rang", type=int, default=960, help="rangs affichés sur les pages (défaut 960)")
    ap.add_argument("--valider", action="store_true", help="écrire la liste d'exclusion à partir du classement")
    ap.add_argument("--jusqu-au-rang", type=int, help="rangs 1 à N : des tiges (avec --valider)")
    ap.add_argument("--garder-rangs", type=int, nargs="*", default=[], help="rangs <= N qui sont en fait des feuilles")
    ap.add_argument("--exclure-rangs", type=int, nargs="*", default=[], help="rangs > N qui sont en fait des tiges")
    ap.add_argument("--liste", default="docs/exclusions/tiges_fusariose_2021.csv")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.valider:
        if args.jusqu_au_rang is None:
            raise SystemExit("Avec --valider, indique --jusqu-au-rang N.")
        c = pd.read_csv(out / "classement.csv")
        tige = (c.rang <= args.jusqu_au_rang) & ~c.rang.isin(args.garder_rangs) | c.rang.isin(args.exclure_rangs)
        ex = c[tige].assign(motif="photo de tige (coupe de pseudo-tronc), absente du test qui ne contient que des feuilles")
        Path(args.liste).parent.mkdir(parents=True, exist_ok=True)
        ex[["zip", "membre", "rang", "score", "motif"]].to_csv(args.liste, index=False)
        print(f"{len(ex)} images exclues sur {len(c)} ({len(ex) / len(c):.1%}) : rangs 1 à {args.jusqu_au_rang}, "
              f"moins {len(args.garder_rangs)} gardées, plus {len(args.exclure_rangs)} ajoutées.")
        print(ex.zip.value_counts().to_string())
        print(f"Liste écrite : {args.liste}")
        return

    fichiers = [Path(args.zips) / f for f in args.fichiers]
    for f in fichiers:
        if not f.exists():
            raise SystemExit(f"Introuvable : {f}")
    images = lister_images(fichiers)
    print(f"{len(images)} images à classer")
    cache = out / "vecteurs.npz"
    cles = np.array([f"{z}::{m}" for z, m in images])
    if cache.exists() and np.array_equal(np.load(cache, allow_pickle=True)["cles"], cles):
        v = np.load(cache, allow_pickle=True)["vecteurs"]
        print("Vecteurs repris du cache")
    else:
        print("Calcul des vecteurs (EfficientNet-B0, processeur) :")
        v = calculer_vecteurs(images, args.zips)
        np.savez(cache, cles=cles, vecteurs=v)

    i_tiges, m_t = indices_exemples(images, TIGES)
    i_feuilles, m_f = indices_exemples(images, FEUILLES)
    if m_t or m_f:
        print(f"Attention : {m_t} tiges et {m_f} feuilles d'exemple introuvables dans les zips")
    sim = v @ v.T[:, i_tiges + i_feuilles]
    s_tige, s_feuille = sim[:, :len(i_tiges)].max(1), sim[:, len(i_tiges):].max(1)
    c = pd.DataFrame(dict(zip=[z for z, _ in images], membre=[m for _, m in images],
                          score=np.round(s_tige - s_feuille, 4), ressemblance_tige=np.round(s_tige, 4),
                          ressemblance_feuille=np.round(s_feuille, 4)))
    c["exemple"] = ""
    c.loc[i_tiges, "exemple"] = "tige"
    c.loc[i_feuilles, "exemple"] = "feuille"
    c = c.sort_values("score", ascending=False).reset_index(drop=True)
    c.insert(0, "rang", np.arange(1, len(c) + 1))
    c.to_csv(out / "classement.csv", index=False)
    n_pages = pages(c, args.zips, out / "pages", max_rang=args.pages_jusqu_au_rang)
    ex = c[c.exemple != ""]
    print(f"Rangs des exemples de tiges : {sorted(ex[ex.exemple == 'tige'].rang.tolist())}")
    print(f"Rang de la feuille d'exemple la mieux classée : {ex[ex.exemple == 'feuille'].rang.min()}")
    print(f"Images avec un score positif (plus proches d'une tige que d'une feuille) : {(c.score > 0).sum()}")
    print(f"{n_pages} pages de 96 images dans {out / 'pages'} | classement : {out / 'classement.csv'}")


if __name__ == "__main__":
    main()
