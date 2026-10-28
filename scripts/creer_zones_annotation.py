#!/usr/bin/env python3
"""Tirage au hasard de zones carrées à annoter à la main (référence complète).

Les annotations de ReforesTree oublient des bananiers : pour mesurer un F1 qui ait
un sens, on annote soi-même TOUS les bananiers de quelques carrés tirés au hasard
dans les sites de validation et de test. Le tirage au hasard évite de choisir
inconsciemment les zones faciles ; la graine fixe le rend reproductible.

Chaque carré tombe entièrement dans la partie valide de l'orthomosaïque (masque
de transparence) et ne chevauche pas les autres carrés.

Sortie : zones_annotation.geojson (EPSG:32717), avec pour chaque carré le site,
le découpage et le nombre d'arbres et de bananiers que ReforesTree y annote.

Exemple :
    python scripts/creer_zones_annotation.py
    python scripts/creer_zones_annotation.py --cote 30
"""
import argparse
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio import features
from rasterio.enums import Resampling
from shapely.geometry import box, shape
from shapely.ops import unary_union

CRS_SORTIE = "EPSG:32717"
DOSSIER_ORTHOS = "wwf_ecuador/RGB Orthomosaics"
ZONES_PAR_DEFAUT = {"Manuel Macias": 2, "Carlos Vera Guevara": 3}


def zone_valide(chemin, pas_m=1.0):
    """Polygone (EPSG:32717) de la partie de l'orthomosaïque qui contient de l'image."""
    with rasterio.open(chemin) as src:
        # Lecture sous-échantillonnée (environ 1 m par pixel) : suffisant pour un masque
        res_m = abs(src.res[0]) * 111_320 if src.crs.is_geographic else abs(src.res[0])
        facteur = max(1, int(pas_m / res_m))
        h, w = src.height // facteur, src.width // facteur
        if src.count >= 4:
            masque = src.read(4, out_shape=(h, w), resampling=Resampling.nearest) > 0
        else:  # sans canal de transparence : on écarte le blanc pur et le noir pur
            rgb = src.read([1, 2, 3], out_shape=(3, h, w), resampling=Resampling.nearest)
            masque = ~((rgb == 255).all(0) | (rgb == 0).all(0))
        t = src.transform * src.transform.scale(src.width / w, src.height / h)
        crs = src.crs
    polys = [shape(g) for g, v in features.shapes(masque.astype("uint8"), mask=masque, transform=t) if v == 1]
    if not polys:
        raise SystemExit(f"Aucune zone valide trouvée dans {chemin}")
    return gpd.GeoSeries([unary_union(polys)], crs=crs).to_crs(CRS_SORTIE).iloc[0]


def tirer_carres(valide, n, cote, rng):
    """Tire n carrés de côté `cote` m entièrement dans `valide`, sans chevauchement.

    La zone est découpée en une grille de cases de `cote` m, décalée au hasard ;
    on tire ensuite n cases au hasard parmi celles entièrement dans l'image.
    Cela range mieux les carrés qu'un tirage libre, sur des sites de 150 m.
    """
    x0, y0, x1, y1 = valide.bounds
    dx, dy = rng.uniform(0, cote), rng.uniform(0, cote)
    cases = []
    for x in np.arange(x0 - dx, x1, cote):
        for y in np.arange(y0 - dy, y1, cote):
            c = box(x, y, x + cote, y + cote)
            if c.within(valide):
                cases.append(c)
    if len(cases) < n:
        raise SystemExit(f"Seulement {len(cases)} case(s) de {cote:.0f} m entièrement dans l'image : "
                         f"réduis --cote ou le nombre de zones")
    choix = rng.choice(len(cases), size=n, replace=False)
    return [cases[i] for i in sorted(choix)], len(cases)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", default="data/drone/reforestree/reforesTree.zip")
    ap.add_argument("--points", default="data/drone/reforestree/prepare/points_pieds.geojson",
                    help="points préparés par prepare_reforestree.py (pour compter ce que ReforesTree annote)")
    ap.add_argument("--out", default="data/drone/reforestree/prepare/zones_annotation.geojson")
    ap.add_argument("--cote", type=float, default=50.0, help="côté des carrés en mètres (défaut 50)")
    ap.add_argument("--graine", type=int, default=2026, help="graine du tirage, pour le rendre reproductible")
    ap.add_argument("--zones", default=json.dumps(ZONES_PAR_DEFAUT, ensure_ascii=False),
                    help='nombre de carrés par site, en JSON (défaut : {"Manuel Macias": 2, "Carlos Vera Guevara": 3})')
    args = ap.parse_args(argv)

    zones_par_site = json.loads(args.zones)
    rng = np.random.default_rng(args.graine)
    chemin_zip = Path(args.zip).resolve().as_posix()
    pts = gpd.read_file(args.points) if Path(args.points).exists() else None
    if pts is not None:
        pts = pts.to_crs(CRS_SORTIE)

    lignes = []
    for site, n in zones_par_site.items():
        print(f"{site} : masque de l'image valide...")
        valide = zone_valide(f"/vsizip/{chemin_zip}/{DOSSIER_ORTHOS}/{site} RGB.tif")
        carres, n_cases = tirer_carres(valide, n, args.cote, rng)
        print(f"  {n_cases} cases de {args.cote:.0f} m entièrement dans l'image, {n} tirées au hasard")
        for k, carre in enumerate(carres, start=1):
            ligne = dict(zone_id=f"{site.split()[0][0]}{site.split()[-1][0]}{k}", site=site, cote_m=args.cote,
                         geometry=carre)
            if pts is not None:
                dedans = pts[pts.within(carre)]
                ligne["split"] = dedans.split.iloc[0] if len(dedans) else pts[pts.site == site].split.iloc[0]
                ligne["arbres_reforestree"] = int(len(dedans))
                ligne["bananiers_reforestree"] = int(dedans.is_banana.astype(bool).sum())
            lignes.append(ligne)

    zones = gpd.GeoDataFrame(lignes, geometry="geometry", crs=CRS_SORTIE)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    zones.to_file(args.out, driver="GeoJSON")
    print("\n" + zones.drop(columns="geometry").to_string(index=False))
    print(f"\nGraine : {args.graine} | côté : {args.cote:.0f} m | zones écrites dans {args.out}")


if __name__ == "__main__":
    main()
