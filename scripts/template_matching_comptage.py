#!/usr/bin/env python3
"""Comptage des pieds par template matching (recherche de la forme d'un bananier).

1. Gabarits : on découpe l'image autour de bananiers annotés par ReforesTree sur
   les sites d'ENTRAÎNEMENT seulement, on normalise chaque découpe, puis on en fait
   la moyenne, par classe de taille de couronne (petit, moyen, grand). La moyenne
   inclut les 8 rotations et symétries, pour ne pas dépendre de l'orientation.
2. Recherche : dans chaque carré évalué, corrélation croisée normalisée (score de
   -1 à 1) entre l'image et chaque gabarit ; on garde le meilleur score par pixel.
3. Pics : maxima locaux du score, au-dessus de --seuil et espacés de --distance m.
4. Évaluation contre la référence manuelle (evaluer_comptage.py, appariement à 1 m).

Le canal comparé est l'indice de verdure ExG (--canal exg) ou la luminosité (--canal gris).
Comme pour la baseline, la recherche de réglages est refusée sur des carrés de test.

Exemples :
    python scripts/template_matching_comptage.py --out out/comptage/template
    python scripts/template_matching_comptage.py --canal gris --out out/comptage/template_gris
"""
import argparse
import itertools
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.warp import transform as warp_transform
from scipy import ndimage
from scipy.signal import fftconvolve

sys.path.insert(0, str(Path(__file__).resolve().parent))
from baseline_comptage import chemin_ortho, indice_exg, lire_fenetre, pics, resolution_native_m  # noqa: E402
from evaluer_comptage import CRS_METRIQUE, evaluer_zone, scores  # noqa: E402


def canal(rgb, nom):
    if nom == "exg":
        return indice_exg(rgb)
    return rgb.mean(0) / 255.0  # luminosité


def lire_image_entiere(chemin, res_m, nom_canal):
    """Image complète d'un site, rééchantillonnée à res_m (lecture unique, plus rapide qu'une lecture par arbre)."""
    with rasterio.open(chemin) as src:
        f = max(res_m / resolution_native_m(src), 1.0)
        h, l = round(src.height / f), round(src.width / f)
        data = src.read(out_shape=(src.count, h, l), resampling=Resampling.average).astype("float32")
        t = src.transform * rasterio.Affine.scale(src.width / l, src.height / h)
        crs = src.crs
    valide = data[3] > 127 if data.shape[0] >= 4 else ~(data[:3] >= 250).all(0)
    return canal(data[:3], nom_canal), valide, t, crs


def normaliser(p):
    s = p.std()
    return (p - p.mean()) / s if s > 1e-6 else None


def symetriser(p):
    """Moyenne des 8 rotations et symétries : le gabarit ne dépend plus de l'orientation."""
    vues = [np.rot90(p, k) for k in range(4)]
    vues += [np.fliplr(v) for v in vues]
    return np.mean(vues, axis=0)


def construire_gabarits(points, args, res_m):
    """Gabarits moyens par classe de taille, à partir des bananiers des sites d'entraînement."""
    b = points[(points.split == "train") & points.is_banana.astype(str).str.lower().isin(["true", "1"])].copy()
    if b.empty:
        raise SystemExit("Aucun bananier d'entraînement dans les points préparés.")
    b["cote_m"] = (b.largeur_m + b.hauteur_m) / 2
    b["classe"] = pd.qcut(b.cote_m, args.classes, labels=False, duplicates="drop")
    rng = np.random.default_rng(args.graine)
    sommes, effectifs, tailles = {}, {}, {}
    for site, sous in b.groupby("site"):
        img, valide, t, crs = lire_image_entiere(chemin_ortho(site, args.orthos, args.zip), res_m, args.canal)
        sous = sous.sample(min(len(sous), args.max_par_site), random_state=args.graine)
        xs, ys = warp_transform(CRS_METRIQUE, crs, sous.geometry.x.tolist(), sous.geometry.y.tolist())
        cols, rows = ~t * (np.array(xs), np.array(ys))
        for (_, arbre), r, c in zip(sous.iterrows(), rows, cols):
            k = int(arbre.classe)
            if k not in tailles:  # côté du gabarit : 1,3 fois la couronne médiane de la classe, impair
                cote_m = 1.3 * b[b.classe == k].cote_m.median()
                tailles[k] = int(round(cote_m / res_m)) // 2 * 2 + 1
            demi = tailles[k] // 2
            r, c = int(round(r)), int(round(c))
            if r - demi < 0 or c - demi < 0 or r + demi >= img.shape[0] or c + demi >= img.shape[1]:
                continue
            if valide[r - demi:r + demi + 1, c - demi:c + demi + 1].mean() < 0.95:
                continue
            p = normaliser(img[r - demi:r + demi + 1, c - demi:c + demi + 1])
            if p is None:
                continue
            sommes[k] = sommes.get(k, 0) + p
            effectifs[k] = effectifs.get(k, 0) + 1
    gabarits = {k: symetriser(sommes[k] / effectifs[k]) for k in sorted(sommes)}
    return gabarits, effectifs, {k: tailles[k] * res_m for k in tailles}


def correlation_normalisee(img, gab):
    """Corrélation croisée normalisée (score de -1 à 1) en chaque pixel, même taille que l'image."""
    g = gab - gab.mean()
    n = g.size
    num = fftconvolve(img, g[::-1, ::-1], mode="same")
    taille = g.shape
    somme = ndimage.uniform_filter(img, taille) * n
    somme2 = ndimage.uniform_filter(img * img, taille) * n
    var = np.maximum(somme2 - somme ** 2 / n, 1e-9)
    return num / (np.sqrt(var) * np.sqrt((g ** 2).sum()))


def enregistrer_gabarits_png(gabarits, chemin):
    vignettes = []
    for k, g in gabarits.items():
        v = (g - g.min()) / (g.max() - g.min() + 1e-9) * 255
        vignettes.append(Image.fromarray(v.astype("uint8")).resize((160, 160), Image.NEAREST))
    planche = Image.new("L", (170 * len(vignettes), 160), 255)
    for i, v in enumerate(vignettes):
        planche.paste(v, (170 * i, 0))
    planche.save(chemin)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", default="data/drone/reforestree/reforesTree.zip")
    ap.add_argument("--orthos", default="data/drone/reforestree/wwf_ecuador/RGB Orthomosaics")
    ap.add_argument("--points", default="data/drone/reforestree/prepare/points_pieds.geojson")
    ap.add_argument("--reference", default="data/drone/reforestree/prepare/annotations_manuelles.geojson")
    ap.add_argument("--zones", default="data/drone/reforestree/prepare/zones_annotation.geojson")
    ap.add_argument("--zones-evaluees", nargs="+", default=["MM1", "MM2"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--resolution", type=float, default=5.0, help="cm par pixel (défaut 5)")
    ap.add_argument("--canal", choices=["exg", "gris"], default="exg")
    ap.add_argument("--classes", type=int, default=3, help="nombre de classes de taille de gabarit (défaut 3)")
    ap.add_argument("--max-par-site", type=int, default=400, help="bananiers utilisés par site d'entraînement")
    ap.add_argument("--graine", type=int, default=2026)
    ap.add_argument("--lissage", type=float, nargs="+", default=[0.0, 0.1], help="lissage du canal avant recherche, en m")
    ap.add_argument("--distance", type=float, nargs="+", default=[1.0, 1.5, 2.0])
    ap.add_argument("--seuil", type=float, nargs="+", default=[0.2, 0.3, 0.4, 0.5, 0.6])
    ap.add_argument("--rayon", type=float, default=1.0)
    ap.add_argument("--marge", type=float, default=3.0)
    args = ap.parse_args(argv)

    debut = time.time()
    res_m = args.resolution / 100
    zones = gpd.read_file(args.zones).to_crs(CRS_METRIQUE)
    zones = zones[zones.zone_id.isin(args.zones_evaluees)]
    n_comb = len(args.lissage) * len(args.distance) * len(args.seuil)
    if "split" in zones and (zones.split == "test").any() and n_comb > 1:
        raise SystemExit("Refus : pas de recherche de réglages sur des carrés de test.")
    ref = gpd.read_file(args.reference).to_crs(CRS_METRIQUE)
    ref["type"] = ref["type"].astype(str).str.strip().str.lower()
    points = gpd.read_file(args.points).to_crs(CRS_METRIQUE)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print("Construction des gabarits sur les sites d'entraînement...")
    gabarits, effectifs, cotes = construire_gabarits(points, args, res_m)
    np.savez(out / "gabarits.npz", **{f"classe_{k}": g for k, g in gabarits.items()})
    enregistrer_gabarits_png(gabarits, out / "gabarits.png")
    for k in gabarits:
        print(f"  classe {k} : {effectifs[k]} bananiers moyennés, gabarit de {cotes[k]:.1f} m")

    images = {}
    for _, z in zones.iterrows():
        rgb, valide, t, crs = lire_fenetre(chemin_ortho(z.site, args.orthos, args.zip), z.geometry, args.marge, res_m)
        images[z.zone_id] = (canal(rgb, args.canal), valide, t, crs, z)

    lignes, meilleur = [], None
    for lissage in args.lissage:
        scores_carte = {}
        for k, (img, valide, t, crs, z) in images.items():
            im = ndimage.gaussian_filter(img, lissage / res_m) if lissage > 0 else img
            im = np.where(valide, im, np.nanmedian(im[valide]))
            carte = np.max([correlation_normalisee(im, g) for g in gabarits.values()], axis=0)
            scores_carte[k] = np.where(valide, carte, np.nan)
        for distance in args.distance:
            candidats = {k: pics(scores_carte[k], images[k][1], distance, res_m, images[k][2], images[k][3])
                         for k in images}
            for seuil in args.seuil:
                tot = dict(vp=0, fp=0, fn=0, det=0, pieds=0)
                detections = []
                for k, (*_r, z) in images.items():
                    xy, val = candidats[k]
                    garde = val > seuil
                    det = gpd.GeoDataFrame({"score": val[garde]},
                                           geometry=gpd.points_from_xy(xy[garde, 0], xy[garde, 1]), crs=CRS_METRIQUE)
                    det = det[det.within(z.geometry)].reset_index(drop=True)
                    r = ref[(ref.zone_id == k) & ref.within(z.geometry)].reset_index(drop=True)
                    res, statut, _ = evaluer_zone(det, r, args.rayon)
                    for a, b in (("vp", "vrais_positifs"), ("fp", "faux_positifs"), ("fn", "oublies"),
                                 ("det", "detections"), ("pieds", "pieds_reference")):
                        tot[a] += res[b]
                    det["zone_id"], det["statut"] = k, statut
                    detections.append(det)
                p, rr, f1 = scores(tot["vp"], tot["fp"], tot["fn"])
                ligne = dict(canal=args.canal, resolution_cm=args.resolution, lissage_m=lissage, distance_m=distance,
                             seuil=seuil, vrais_positifs=tot["vp"], faux_positifs=tot["fp"], oublies=tot["fn"],
                             precision=p, rappel=rr, f1=f1, erreur_comptage=tot["det"] - tot["pieds"])
                lignes.append(ligne)
                if meilleur is None or f1 > meilleur[0]["f1"]:
                    meilleur = (ligne, pd.concat(detections, ignore_index=True))

    grille = pd.DataFrame(lignes).sort_values("f1", ascending=False)
    grille.to_csv(out / "grille.csv", index=False)
    ligne, det = meilleur
    det.to_file(out / "detections.geojson", driver="GeoJSON")
    (out / "parametres.json").write_text(json.dumps(dict(
        zones_evaluees=args.zones_evaluees, canal=args.canal, resolution_cm=args.resolution, classes=args.classes,
        max_par_site=args.max_par_site, graine=args.graine, gabarits={str(k): dict(bananiers=effectifs[k],
        cote_m=round(cotes[k], 2)) for k in gabarits}, grille=dict(lissage_m=args.lissage, distance_m=args.distance,
        seuil=args.seuil), meilleur_resultat=ligne, duree_s=round(time.time() - debut, 1)),
        indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    cols = ["lissage_m", "distance_m", "seuil", "vrais_positifs", "faux_positifs", "oublies",
            "precision", "rappel", "f1", "erreur_comptage"]
    print(f"\n{len(grille)} combinaisons essayées sur {', '.join(args.zones_evaluees)} "
          f"en {time.time() - debut:.0f} s. Les 10 meilleures :")
    print(grille[cols].head(10).round(3).to_string(index=False))
    print(f"\nGabarits : {out / 'gabarits.png'} | détections : {out / 'detections.geojson'}")


if __name__ == "__main__":
    main()
