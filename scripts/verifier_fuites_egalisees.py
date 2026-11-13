#!/usr/bin/env python3
"""Second contrôle des fuites, robuste aux retouches de contraste, sans modèle.

Complète scripts/verifier_jeux_maladies.py. Certains jeux Roboflow ont égalisé l'histogramme ou passé des
images en gris : la vignette en couleur ne reconnaît plus alors une copie. Ici, les deux côtés sont réduits,
passés en gris et égalisés avant l'empreinte dHash et la vignette 16 x 16 ; chaque image candidate est
comparée sous ses 8 symétries aux seuls jeux d'évaluation (validation Tanzanie 2022, BananaLSD, Pérou test,
Banana Disease Recognition), ceux qu'une copie dans l'entraînement fausserait.

Les recadrages et les retouches éloignent une copie au-delà du seuil de 5 : le script ne tranche pas, il
écrit l'écart de chaque image et des planches par bande d'écart pour un contrôle à l'œil.

Sorties dans --out/<jeu> : fuites_egalisees.csv, paires_egalisees.jpg (24 plus proches),
bande_<bas>_<haut>.jpg (16 paires tirées au hasard, graine 2026), et bilan_egalise.csv dans --out.

Exemple :
    python scripts/verifier_fuites_egalisees.py data/roboflow_maladies/*.zip
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageOps

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
from preparer_feuilles import dhash  # noqa: E402
from verifier_jeux_maladies import (comparer, lire_export, ouvrir, par_image, planche_paires,  # noqa: E402
                                    reduire, selection_references, variantes)

BANDES = [(5, 12), (12, 15), (15, 18), (18, 22), (22, 26)]


def preparer(im):
    return ImageOps.equalize(reduire(im).convert("L"))


def vignette_grise(im, cote=16):
    return np.asarray(im.resize((cote, cote), Image.BILINEAR), dtype=np.int16)[..., None]


def references_evaluation(index_csv, bdr, cache):
    chemins, src, _ = selection_references(index_csv, bdr)
    garde = [k for k, s in enumerate(src) if s.split("/")[1] != "entrainement"]
    chemins, src = [chemins[k] for k in garde], [src[k] for k in garde]
    if cache.exists():
        d = np.load(cache, allow_pickle=True)
        if list(d["src"]) == src:
            return list(d["h"]), np.asarray(d["v"], dtype=np.int16), src, chemins
    h, v = [], []
    for c in chemins:
        im = preparer(Image.open(c))
        h.append(dhash(im)); v.append(vignette_grise(im))
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, h=np.array(h, dtype=object), v=np.stack(v), src=np.array(src))
    return h, np.stack(v), src, chemins


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("exports", nargs="+")
    ap.add_argument("--index", default="data/feuilles/index.csv")
    ap.add_argument("--bdr", default="data/raw/banana_disease_recognition/extrait/Original Images")
    ap.add_argument("--out", default="out/maladies/roboflow")
    ap.add_argument("--seuil-candidat", type=int, default=10)
    ap.add_argument("--seuil-vignette", type=float, default=5.0)
    args = ap.parse_args(argv)
    out = Path(args.out)
    rh, rv, rsrc, rchemins = references_evaluation(args.index, args.bdr, out / "references_egalisees.npz")
    print(f"références d'évaluation : {len(rh)} ({pd.Series(rsrc).value_counts().to_dict()})")
    rng = np.random.default_rng(2026)
    bilan = []
    for chemin in args.exports:
        nom = Path(chemin).stem
        df, z = lire_export(chemin)
        hs, vs = [], []
        for r in df.itertuples():
            for t in variantes(preparer(ouvrir(z, r.image))):
                hs.append(dhash(t)); vs.append(vignette_grise(t))
        m, j = par_image(*comparer(hs, np.stack(vs), rh, rv, args.seuil_candidat, args.seuil_vignette)[:2])
        df["ecart_egalise"] = np.where(np.isfinite(m), np.round(m, 2), np.nan)
        df["source_egalise"] = [rsrc[k] if k >= 0 else "" for k in j]
        df["reference_egalise"] = [str(rchemins[k]) if k >= 0 else "" for k in j]
        d = out / nom
        d.mkdir(parents=True, exist_ok=True)
        df.to_csv(d / "fuites_egalisees.csv", index=False)

        def paires(ix):
            return [(ouvrir(z, df.image.iat[i]), Image.open(rchemins[j[i]]), f"{m[i]:.1f} {rsrc[j[i]]}")
                    for i in sorted(ix, key=lambda i: m[i])]
        planche_paires(paires(np.argsort(m)[:24][np.isfinite(np.sort(m)[:24])]), d / "paires_egalisees.jpg")
        ligne = dict(jeu=nom, images=len(df), fuites=int((m <= args.seuil_vignette).sum()),
                     ecart_min=round(float(np.nanmin(df.ecart_egalise)), 2) if df.ecart_egalise.notna().any() else None)
        for bas, haut in BANDES:
            ix = np.nonzero((m > bas) & (m <= haut))[0]
            ligne[f"bande_{bas}_{haut}"] = len(ix)
            if len(ix):
                planche_paires(paires(rng.choice(ix, min(16, len(ix)), replace=False)), d / f"bande_{bas}_{haut}.jpg")
        bilan.append(ligne)
        print(ligne)
    pd.DataFrame(bilan).to_csv(out / "bilan_egalise.csv", index=False)
    print("->", out)


if __name__ == "__main__":
    main()
