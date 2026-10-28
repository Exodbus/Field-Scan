#!/usr/bin/env python3
"""Inspection du jeu ReforesTree (zip Zenodo), sans le décompresser.

Affiche : le contenu du zip, les orthomosaïques (taille, CRS, résolution),
les annotations (colonnes, classes, taille des boîtes, bananiers par site),
les tuiles et les arbres mesurés sur le terrain.

Exemple :
    python scripts/inspect_reforestree.py > out/inspection_reforestree.txt
"""
import argparse
import collections
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

import math

M_PAR_DEGRE = 111_320  # longueur d'un degré de longitude à l'équateur, en mètres


def titre(t):
    print("\n" + "=" * len(t) + "\n" + t + "\n" + "=" * len(t))


def lire_csv(z, nom):
    with z.open(nom) as f:
        return pd.read_csv(f)


def chercher(colonnes, mots):
    """Première colonne qui contient un des mots, en respectant l'ordre de priorité des mots."""
    for m in mots:
        for c in colonnes:
            if m in str(c).lower():
                return c
    return None


def site_de(valeur):
    """Nom du site d'après un nom de fichier ou d'image, par exemple 'Flora Pluas RGB_12_3.png' -> 'Flora Pluas'."""
    nom = Path(str(valeur)).name
    m = re.match(r"^(.*?)\s*RGB", nom)
    return m.group(1).strip() if m else nom.split("_")[0]


def resume_csv(z, nom, n=3):
    try:
        t = lire_csv(z, nom)
    except Exception as e:  # on continue même si un fichier pose problème
        print(f"{nom} : lecture impossible ({e})")
        return None
    print(f"{nom} : {len(t)} lignes")
    print("  colonnes :", list(t.columns))
    print(t.head(n).to_string(max_colwidth=40))
    return t


def est_banane(serie):
    """Vrai pour True, 1 ou un libellé contenant 'banan'."""
    t = serie.astype(str).str.strip().str.lower()
    return t.isin(["true", "1", "1.0"]) | t.str.contains("banan")


def resume_boites(a, label, gsd):
    """Taille des boîtes en pixels et en mètres, avec la résolution réelle de chaque site."""
    if not all(c in a.columns for c in ("xmin", "ymin", "xmax", "ymax")):
        print("Pas de colonnes xmin, ymin, xmax, ymax : format de boîtes à identifier.")
        return
    a = a.assign(cote_px=((a.xmax - a.xmin) + (a.ymax - a.ymin)) / 2)
    if "site" in a and gsd:
        a = a.assign(cote_m=a.cote_px * a.site.map(gsd))
    groupes = [("toutes", a)]
    if label:
        b = est_banane(a[label])
        groupes += [("bananiers", a[b]), ("autres", a[~b])]
    for nom, g in groupes:
        if len(g) == 0:
            continue
        txt = (f"  {nom} : {len(g)} boîtes, côté médian {g.cote_px.median():.0f} px, "
               f"10e-90e percentiles {g.cote_px.quantile(0.1):.0f}-{g.cote_px.quantile(0.9):.0f} px")
        if "cote_m" in g and g.cote_m.notna().any():
            txt += (f" ; en mètres : médiane {g.cote_m.median():.2f} m, "
                    f"10e-90e {g.cote_m.quantile(0.1):.2f}-{g.cote_m.quantile(0.9):.2f} m")
        print(txt)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", default="data/drone/reforestree/reforesTree.zip")
    ap.add_argument("--sortie", help="écrire le rapport dans ce fichier (UTF-8) au lieu de l'écran")
    args = ap.parse_args(argv)
    if args.sortie:
        Path(args.sortie).parent.mkdir(parents=True, exist_ok=True)
        sys.stdout = open(args.sortie, "w", encoding="utf-8")
    # Sous Windows, une sortie redirigée vers un fichier utilise un encodage limité (cp1252) :
    # on force l'UTF-8 pour que les accents et symboles ne fassent pas planter le script.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    z = zipfile.ZipFile(args.zip)
    noms = [n for n in z.namelist() if not n.endswith("/")]
    chemin_zip = Path(args.zip).resolve().as_posix()

    titre("1. Contenu du zip")
    print("Par extension :", dict(collections.Counter(Path(n).suffix.lower() for n in noms)))
    print("Par dossier :", dict(collections.Counter(n.split("/")[0] for n in noms)))
    pngs = [n for n in noms if n.lower().endswith(".png")]
    print(f"{len(pngs)} images PNG, par exemple : {pngs[:3]}")

    titre("2. Orthomosaïques GeoTIFF")
    gsd = {}  # site -> mètres par pixel
    try:
        import rasterio
        for n in [n for n in noms if n.lower().endswith((".tif", ".tiff"))]:
            try:
                with rasterio.open(f"/vsizip/{chemin_zip}/{n}") as s:
                    txt = (f"{n}\n  {s.width} x {s.height} px, {s.count} bandes ({s.dtypes[0]}), CRS = {s.crs}, "
                           f"résolution = {s.res[0]:.4g} x {s.res[1]:.4g}, emprise = {[round(v, 6) for v in s.bounds]}")
                    if s.crs is None:
                        txt += "\n  -> pas de géoréférencement : fichier ignoré pour la résolution"
                    elif s.crs.is_geographic:
                        lat = (s.bounds.bottom + s.bounds.top) / 2
                        mx = s.res[0] * M_PAR_DEGRE * math.cos(math.radians(lat))
                        my = s.res[1] * 110_574  # longueur d'un degré de latitude près de l'équateur
                        gsd[site_de(n)] = (mx + my) / 2
                        txt += (f"\n  -> résolution au sol environ {mx * 100:.2f} x {my * 100:.2f} cm/pixel, "
                                f"soit {s.width * mx:.0f} x {s.height * my:.0f} m")
                    else:
                        gsd[site_de(n)] = (s.res[0] + s.res[1]) / 2
                        txt += f"\n  -> résolution au sol {gsd[site_de(n)] * 100:.2f} cm/pixel"
                    print(txt)
            except Exception as e:
                print(f"{n} : lecture impossible ({e})")
    except ImportError:
        print("rasterio n'est pas installé.")

    titre("3. Annotations nettoyées")
    propres = [n for n in noms if n.endswith("clean_annotations.csv")]
    if propres:
        a = resume_csv(z, propres[0])
        if a is not None:
            label = chercher(a.columns, ["banan", "label", "class", "species", "group"])
            image = chercher(a.columns, ["img_name", "img", "image", "path", "tile", "name"])
            if image:
                a = a.assign(site=a[image].map(site_de))
            print(f"\nColonne de classe détectée : {label} | colonne d'image détectée : {image}")
            if label:
                print("\nClasses :")
                print(a[label].value_counts().head(15).to_string())
            print("\nTaille des boîtes :")
            resume_boites(a, label, gsd)
            if image:
                tuiles = "img_path" if "img_path" in a else image
                print(f"\nTuiles annotées : {a[tuiles].nunique()}")
                if label:
                    par_site = a.assign(banane=est_banane(a[label])).groupby("site").agg(
                        tuiles=(tuiles, "nunique"), boites=("banane", "size"), bananiers=("banane", "sum"))
                    par_site["part_bananiers"] = (par_site.bananiers / par_site.boites).round(2)
                    if "score" in a:
                        print(f"\nColonne 'score' présente (médiane {a.score.median():.2f}) : "
                              "les boîtes semblent venir d'un détecteur, puis nettoyées à la main.")
                    print("\nPar site :")
                    print(par_site.to_string())
    else:
        print("clean_annotations.csv introuvable.")

    titre("4. Autres tableaux")
    for nom in [n for n in noms if n.lower().endswith(".csv") and "clean_annotations" not in n]:
        print()
        resume_csv(z, nom, n=2)

    titre("5. Arbres mesurés sur le terrain (shapefile)")
    shp = [n for n in noms if n.lower().endswith(".shp")]
    if shp:
        try:
            import geopandas as gpd
            t = gpd.read_file(f"/vsizip/{chemin_zip}/{shp[0]}")
            print(f"{shp[0]} : {len(t)} entités, CRS = {t.crs}, géométrie = {t.geom_type.unique().tolist()}")
            print("  colonnes :", list(t.columns))
            esp = chercher([c for c in t.columns if c != "geometry"], ["spec", "espec", "group", "name", "nombre"])
            if esp:
                print(f"\nValeurs de '{esp}' :")
                print(t[esp].value_counts().head(15).to_string())
        except Exception as e:
            print(f"Lecture impossible ({e})")


if __name__ == "__main__":
    main()
