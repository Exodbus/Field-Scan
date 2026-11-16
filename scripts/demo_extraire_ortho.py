#!/usr/bin/env python3
"""Démo finale : extraction et assemblage des deux orthophotos publiques (Martinique IGN, Silkwood Queensland).

Deux étapes, séparées pour que les tuiles téléchargées restent dans un dossier à elles (jamais exécutées) :

1. `telecharger` : requêtes une à une, avec pause, vers le service public du site :
   - martinique : WMS IGN `https://data.geopf.fr/wms-r/wms`, couche ORTHOIMAGERY.ORTHOPHOTOS, EPSG:5490, 0,20 m,
     `image/geotiff`, tuiles de 5 000 px au plus ;
   - silkwood : ImageServer Queensland `exportImage`, mosaïque LockRaster sur le projet Silkwood_2022_10cm_SISP
     (objectid 5610), grille native du raster (EPSG:3857, pas de 0,1 m Mercator, soit environ 9,5 cm au sol à
     17,7° S), tuiles de 4 096 x 2 048 px au plus, TIFF compressé JPEG q90 côté serveur (le TIFF brut ne se
     compresse pas sans perte : 369 Mo au lieu de 170 Mo).
2. `assembler` : les tuiles (même grille, même CRS) sont recopiées dans un seul GeoTIFF RGB tuilé (512 px),
   compressé JPEG q90 en YCbCr, avec aperçus internes (moyenne). Aucune valeur « nodata » n'est déclarée :
   le WMS IGN déclare 255, ce qui masquerait les pixels blancs (routes, toits) dans la chaîne.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/demo_extraire_ortho.py telecharger martinique DOSSIER_TUILES
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/demo_extraire_ortho.py assembler martinique DOSSIER_TUILES SORTIE.tif

Le téléchargement demande `REQUESTS_CA_BUNDLE` si un antivirus intercepte le HTTPS.
"""
import argparse
import json
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.windows import Window

SITES = {
    "martinique": dict(
        url="https://data.geopf.fr/wms-r/wms", crs="EPSG:5490", res=0.2,
        # emprise retenue (EPSG:5490) : 702 270 à 704 870 E, 1 642 370 à 1 643 870 N, soit 2,6 x 1,5 km
        x0=702270, x1=704870, y0=1642370, y1=1643870, tuile=(5000, 5000)),
    "silkwood": dict(
        url="https://spatial-img.information.qld.gov.au/arcgis/rest/services/TimeSeries/AerialOrtho_AllUsers/ImageServer/exportImage",
        crs="EPSG:3857", res=0.1, objectid=5610,
        ox=16251604.1366, oy=-2005336.1417,          # origine native du raster 5610 (coin nord-ouest)
        colonnes=(18200, 38250), lignes=(0, 6144), tuile=(4096, 2048)),
}


def telecharger(site, dossier):
    import requests
    p_site = SITES[site]
    dossier = Path(dossier); dossier.mkdir(parents=True, exist_ok=True)
    journal, tot = [], 0
    TW, TH = p_site["tuile"]
    if site == "martinique":
        R = p_site["res"]
        cases = []
        for r, ytop in enumerate(np.arange(p_site["y1"], p_site["y0"], -TH * R)):
            ybas = max(p_site["y0"], ytop - TH * R)
            for c, xg in enumerate(np.arange(p_site["x0"], p_site["x1"], TW * R)):
                xd = min(p_site["x1"], xg + TW * R)
                w, h = round((xd - xg) / R), round((ytop - ybas) / R)
                cases.append((f"mq_r{r}_c{c}.tif", dict(
                    SERVICE="WMS", VERSION="1.3.0", REQUEST="GetMap", LAYERS="ORTHOIMAGERY.ORTHOPHOTOS", STYLES="",
                    CRS="EPSG:5490", BBOX=f"{xg},{ybas},{xd},{ytop}", WIDTH=w, HEIGHT=h, FORMAT="image/geotiff")))
        pause = 1.5
    else:
        R, OX, OY = p_site["res"], p_site["ox"], p_site["oy"]
        mr = json.dumps({"mosaicMethod": "esriMosaicLockRaster", "lockRasterIds": [p_site["objectid"]]})
        cases = []
        for r, l in enumerate(range(*p_site["lignes"], TH)):
            h = min(TH, p_site["lignes"][1] - l)
            for c, k in enumerate(range(*p_site["colonnes"], TW)):
                w = min(TW, p_site["colonnes"][1] - k)
                bbox = f"{OX + k * R:.4f},{OY - (l + h) * R:.4f},{OX + (k + w) * R:.4f},{OY - l * R:.4f}"
                cases.append((f"qld_r{r}_c{c}.tif", dict(
                    bbox=bbox, bboxSR=3857, imageSR=3857, size=f"{w},{h}", format="tiff", compression="JPEG",
                    compressionQuality=90, bandIds="0,1,2", interpolation="RSP_NearestNeighbor", mosaicRule=mr, f="image")))
        pause = 2.0
    for nom, params in cases:
        f = dossier / nom
        if not f.exists():
            for essai in range(4):
                rep = requests.get(p_site["url"], params=params, timeout=300)
                if rep.status_code == 200 and rep.headers.get("content-type", "").startswith("image/"):
                    f.write_bytes(rep.content); break
                print("échec", rep.status_code, rep.text[:300]); time.sleep(10 * (essai + 1))
            else:
                sys.exit("abandon")
            time.sleep(pause)
        tot += f.stat().st_size
        journal.append(dict(fichier=nom, params=params, octets=f.stat().st_size))
        print(nom, f.stat().st_size, flush=True)
    (dossier / "requetes.json").write_text(json.dumps(dict(url=p_site["url"], tuiles=journal, octets=tot), indent=1))
    print("total octets", tot)


def assembler(site, dossier, sortie):
    p_site = SITES[site]
    tuiles = sorted(Path(dossier).glob("*.tif"))
    if not tuiles:
        sys.exit("aucune tuile")
    R = p_site["res"]
    bornes = []
    for t in tuiles:
        with rasterio.open(t) as s:
            assert s.count >= 3 and s.dtypes[0] == "uint8", (t, s.count, s.dtypes)
            assert abs(abs(s.transform.a) - R) < 1e-6 and abs(abs(s.transform.e) - R) < 1e-6, (t, s.transform)
            bornes.append((t, s.transform.c, s.transform.f, s.width, s.height))
    X0 = min(b[1] for b in bornes); Y1 = max(b[2] for b in bornes)
    W = round(max(b[1] + b[3] * R for b in bornes) - X0, 6) / R
    H = round(Y1 - min(b[2] - b[4] * R for b in bornes), 6) / R
    W, H = int(round(W)), int(round(H))
    transform = from_origin(X0, Y1, R, R)
    profil = dict(driver="GTiff", width=W, height=H, count=3, dtype="uint8", crs=CRS.from_string(p_site["crs"]),
                  transform=transform, tiled=True, blockxsize=512, blockysize=512, compress="JPEG",
                  photometric="YCBCR", jpeg_quality=90, interleave="pixel", BIGTIFF="IF_SAFER")
    sortie = Path(sortie); sortie.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(sortie, "w", **profil) as d:
        for t, x, y, w, h in bornes:
            col, lig = int(round((x - X0) / R)), int(round((Y1 - y) / R))
            with rasterio.open(t) as s:
                d.write(s.read([1, 2, 3]), window=Window(col, lig, w, h))
            print("tuile", t.name, "->", col, lig, w, h, flush=True)
    with rasterio.open(sortie, "r+") as d:
        d.build_overviews([2, 4, 8, 16, 32, 64], Resampling.average)
        d.update_tags(ns="rio_overview", resampling="average")
    print(json.dumps(dict(sortie=str(sortie), largeur=W, hauteur=H, crs=p_site["crs"], res=R,
                          bornes=[X0, Y1 - H * R, X0 + W * R, Y1], octets=sortie.stat().st_size)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["telecharger", "assembler"])
    ap.add_argument("site", choices=list(SITES))
    ap.add_argument("tuiles")
    ap.add_argument("sortie", nargs="?")
    a = ap.parse_args()
    if a.action == "telecharger":
        telecharger(a.site, a.tuiles)
    else:
        assembler(a.site, a.tuiles, a.sortie)


if __name__ == "__main__":
    main()
