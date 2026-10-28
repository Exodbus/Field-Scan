#!/usr/bin/env python3
"""Baseline classique de comptage des pieds : indice de verdure, lissage, maxima locaux.

Pour chaque carré évalué :
  1. lecture de l'orthomosaïque autour du carré, rééchantillonnée à --resolution cm/pixel
     (moyenne des pixels : simule une prise de vue plus haute) ;
  2. indice de verdure ExG = 2g - r - b, en couleurs normalisées (r = R / (R + G + B)...) ;
  3. lissage gaussien de rayon --sigma mètres (une plante = un seul pic) ;
  4. maxima locaux : un pic est gardé s'il est le plus haut dans un voisinage de
     --distance mètres et si sa valeur dépasse --seuil ;
  5. comparaison à la référence manuelle (appariement à 1 m, evaluer_comptage.py).

Si plusieurs valeurs sont données pour un réglage, toutes les combinaisons sont
essayées et classées par F1 : c'est la recherche de réglages. Elle n'est permise
que sur des carrés de validation ; sur le test, une seule combinaison est
acceptée (les réglages doivent être figés avant).

Limite connue : l'ExG ne distingue pas les espèces. Les arbustes donnent aussi
des pics, d'où des fausses détections attendues.

Exemples :
    # Recherche de réglages sur la validation (MM1, MM2), à 5 cm/pixel
    python scripts/baseline_comptage.py --out out/comptage/baseline
    # Ablation de la résolution, autres réglages figés
    python scripts/baseline_comptage.py --resolution 2 5 10 20 --sigma 0.5 --distance 1.5 --seuil 0.05 \
        --out out/comptage/baseline_resolution
"""
import argparse
import itertools
import json
import math
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import transform as warp_transform
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluer_comptage import CRS_METRIQUE, TYPES_CERTAINS, evaluer_zone, scores  # noqa: E402

DOSSIER_ORTHOS = "wwf_ecuador/RGB Orthomosaics"


def chemin_ortho(site, dossier_extrait, chemin_zip):
    """L'image extraite si elle existe, sinon lecture directe dans le zip."""
    p = Path(dossier_extrait) / f"{site} RGB.tif"
    if p.exists():
        return str(p)
    return f"/vsizip/{Path(chemin_zip).resolve().as_posix()}/{DOSSIER_ORTHOS}/{site} RGB.tif"


def resolution_native_m(src):
    if src.crs.is_geographic:
        lat = (src.bounds.bottom + src.bounds.top) / 2
        return abs(src.res[0]) * 111_320 * math.cos(math.radians(lat))
    return abs(src.res[0])


def lire_fenetre(chemin, zone, marge_m, res_m):
    """Image autour d'une zone (géométrie en EPSG:32717), rééchantillonnée à res_m mètres par pixel."""
    with rasterio.open(chemin) as src:
        b = transform_bounds(CRS_METRIQUE, src.crs, *zone.buffer(marge_m).bounds)
        w = from_bounds(*b, transform=src.transform)
        c0, r0 = max(0, int(math.floor(w.col_off))), max(0, int(math.floor(w.row_off)))
        c1 = min(src.width, int(math.ceil(w.col_off + w.width)))
        r1 = min(src.height, int(math.ceil(w.row_off + w.height)))
        w = Window(c0, r0, c1 - c0, r1 - r0)
        facteur = max(res_m / resolution_native_m(src), 1.0)
        h, l = max(1, round(w.height / facteur)), max(1, round(w.width / facteur))
        data = src.read(window=w, out_shape=(src.count, h, l), resampling=Resampling.average).astype("float32")
        t = src.window_transform(w) * rasterio.Affine.scale(w.width / l, w.height / h)
        crs = src.crs
    rgb = data[:3]
    valide = data[3] > 127 if data.shape[0] >= 4 else ~(rgb >= 250).all(0)
    return rgb, valide, t, crs


def indice_exg(rgb):
    somme = rgb.sum(0)
    somme[somme == 0] = 1
    r, g, b = rgb / somme
    return 2 * g - r - b


def lisser(exg, valide, sigma_m, res_m):
    """Lissage gaussien qui ignore les pixels hors image (convolution normalisée)."""
    s = sigma_m / res_m
    num = ndimage.gaussian_filter(np.where(valide, exg, 0).astype("float32"), s)
    den = ndimage.gaussian_filter(valide.astype("float32"), s)
    return np.where(den > 0.2, num / np.maximum(den, 1e-6), np.nan)


def pics(lisse, valide, distance_m, res_m, t, crs):
    """Maxima locaux (sans seuil) : retourne leurs coordonnées EPSG:32717 et leur valeur."""
    m = np.nan_to_num(lisse, nan=-9.0)
    taille = max(3, int(round(distance_m / res_m)) | 1)  # fenêtre impaire
    est_pic = (m == ndimage.maximum_filter(m, size=taille)) & valide & (m > -9)
    lab, n = ndimage.label(est_pic)  # un plateau de pixels égaux ne compte qu'une fois
    if n == 0:
        return np.empty((0, 2)), np.empty(0)
    centres = np.array(ndimage.center_of_mass(est_pic, lab, range(1, n + 1)))
    valeurs = np.array(ndimage.maximum(m, lab, range(1, n + 1)))
    xs, ys = t * (centres[:, 1] + 0.5, centres[:, 0] + 0.5)
    X, Y = warp_transform(crs, CRS_METRIQUE, np.atleast_1d(xs), np.atleast_1d(ys))
    return np.c_[X, Y], valeurs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", default="data/drone/reforestree/reforesTree.zip")
    ap.add_argument("--orthos", default="data/drone/reforestree/wwf_ecuador/RGB Orthomosaics",
                    help="dossier des orthomosaïques extraites (sinon lecture dans le zip)")
    ap.add_argument("--reference", default="data/drone/reforestree/prepare/annotations_manuelles.geojson")
    ap.add_argument("--zones", default="data/drone/reforestree/prepare/zones_annotation.geojson")
    ap.add_argument("--zones-evaluees", nargs="+", default=["MM1", "MM2"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--resolution", type=float, nargs="+", default=[5.0], help="cm par pixel (défaut 5)")
    ap.add_argument("--sigma", type=float, nargs="+", default=[0.2, 0.35, 0.5, 0.75, 1.0], help="lissage en m")
    ap.add_argument("--distance", type=float, nargs="+", default=[1.0, 1.5, 2.0, 2.5],
                    help="distance minimale entre deux pieds détectés, en m")
    ap.add_argument("--seuil", type=float, nargs="+", default=[0.0, 0.02, 0.05, 0.08, 0.12],
                    help="valeur minimale d'ExG lissé pour garder un pic")
    ap.add_argument("--rayon", type=float, default=1.0, help="rayon d'appariement pour l'évaluation (défaut 1 m)")
    ap.add_argument("--marge", type=float, default=3.0, help="marge lue autour des carrés, en m (évite les effets de bord)")
    args = ap.parse_args(argv)

    zones = gpd.read_file(args.zones).to_crs(CRS_METRIQUE)
    zones = zones[zones.zone_id.isin(args.zones_evaluees)]
    if zones.empty:
        raise SystemExit(f"Aucune des zones {args.zones_evaluees} dans {args.zones}")
    n_combinaisons = len(args.resolution) * len(args.sigma) * len(args.distance) * len(args.seuil)
    if "split" in zones and (zones.split == "test").any() and n_combinaisons > 1:
        raise SystemExit("Refus : pas de recherche de réglages sur des carrés de test. "
                         "Donne une seule valeur par réglage, choisie sur la validation.")
    ref = gpd.read_file(args.reference).to_crs(CRS_METRIQUE)
    ref["type"] = ref["type"].astype(str).str.strip().str.lower()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lignes, meilleur = [], None
    debut = time.time()

    for res_cm in args.resolution:
        res_m = res_cm / 100
        images = {}
        for _, z in zones.iterrows():
            chemin = chemin_ortho(z.site, args.orthos, args.zip)
            rgb, valide, t, crs = lire_fenetre(chemin, z.geometry, args.marge, res_m)
            images[z.zone_id] = (indice_exg(rgb), valide, t, crs, z)
        for sigma in args.sigma:
            lisses = {k: lisser(e, v, sigma, res_m) for k, (e, v, *_rest) in images.items()}
            for distance in args.distance:
                candidats = {k: pics(lisses[k], v, distance, res_m, t, crs) for k, (_, v, t, crs, _z) in images.items()}
                for seuil in args.seuil:
                    tot = dict(vp=0, fp=0, fn=0, detections=0, pieds=0)
                    detections = []
                    for k, (*_rest, z) in images.items():
                        xy, val = candidats[k]
                        garde = val > seuil
                        det = gpd.GeoDataFrame({"exg_lisse": val[garde]},
                                               geometry=gpd.points_from_xy(xy[garde, 0], xy[garde, 1]),
                                               crs=CRS_METRIQUE)
                        det = det[det.within(z.geometry)].reset_index(drop=True)
                        r = ref[(ref.zone_id == k) & ref.within(z.geometry)].reset_index(drop=True)
                        res, statut, _ = evaluer_zone(det, r, args.rayon)
                        tot["vp"] += res["vrais_positifs"]
                        tot["fp"] += res["faux_positifs"]
                        tot["fn"] += res["oublies"]
                        tot["detections"] += res["detections"]
                        tot["pieds"] += res["pieds_reference"]
                        det["zone_id"], det["statut"] = k, statut
                        detections.append(det)
                    p, rr, f1 = scores(tot["vp"], tot["fp"], tot["fn"])
                    ligne = dict(resolution_cm=res_cm, sigma_m=sigma, distance_m=distance, seuil=seuil,
                                 vrais_positifs=tot["vp"], faux_positifs=tot["fp"], oublies=tot["fn"],
                                 precision=p, rappel=rr, f1=f1, erreur_comptage=tot["detections"] - tot["pieds"])
                    lignes.append(ligne)
                    if meilleur is None or (f1 > meilleur[0]["f1"]):
                        meilleur = (ligne, pd.concat(detections, ignore_index=True))

    grille = pd.DataFrame(lignes).sort_values("f1", ascending=False)
    grille.to_csv(out / "grille.csv", index=False)
    ligne, det = meilleur
    det.to_file(out / "detections.geojson", driver="GeoJSON")
    (out / "parametres.json").write_text(json.dumps(dict(
        zones_evaluees=args.zones_evaluees, reference=args.reference, rayon_m=args.rayon, marge_m=args.marge,
        grille=dict(resolution_cm=args.resolution, sigma_m=args.sigma, distance_m=args.distance, seuil=args.seuil),
        meilleurs_reglages={k: ligne[k] for k in ("resolution_cm", "sigma_m", "distance_m", "seuil")},
        meilleur_resultat={k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in ligne.items()},
        duree_s=round(time.time() - debut, 1)), indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    cols = ["resolution_cm", "sigma_m", "distance_m", "seuil", "vrais_positifs", "faux_positifs", "oublies",
            "precision", "rappel", "f1", "erreur_comptage"]
    print(f"{len(grille)} combinaisons essayées sur {', '.join(args.zones_evaluees)} "
          f"en {time.time() - debut:.0f} s. Les 10 meilleures :")
    print(grille[cols].head(10).round(3).to_string(index=False))
    if len(args.resolution) > 1:
        print("\nMeilleur F1 par résolution :")
        print(grille.loc[grille.groupby("resolution_cm").f1.idxmax(), cols].round(3).to_string(index=False))
    print(f"\nDétections des meilleurs réglages : {out / 'detections.geojson'}")


if __name__ == "__main__":
    main()
