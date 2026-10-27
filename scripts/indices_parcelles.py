#!/usr/bin/env python3
"""Indices de végétation par parcelle, à partir de scènes Sentinel-2 L2A.

Entrée : un dossier de scènes exportées depuis le Copernicus Browser (dossiers
décompressés ou archives .zip, une scène par date) et un GeoJSON de parcelles.
Sortie : un tableau CSV (une ligne par parcelle et par date), un GeoJSON
enrichi, des cartes GeoTIFF des indices et un fichier de paramètres.

Exemple :
    python indices_parcelles.py --images data/equateur \
        --parcelles parcelles_equateur.geojson --out resultats/equateur

Choix de calcul (à justifier dans le rapport) :
    NDVI = (B08 - B04) / (B08 + B04)
    NDRE = (B8A - B05) / (B8A + B05)   (B05 est à 20 m, rééchantillonnée à ~10 m)
    NDMI = (B08 - B11) / (B08 + B11)   (B11 est à 20 m, rééchantillonnée à ~10 m)

Chaque parcelle est conservée dans les résultats, avec son pourcentage de pixels
masqués. Une parcelle n'est jamais supprimée : elle reçoit un statut.
"""
import argparse
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio import features

# Palette standard de la carte de classification de scène (SCL) de Sentinel-2.
# La carte téléchargée est une image colorée : on retrouve la classe par la couleur.
PALETTE = {
    (0, 0, 0): "nodata",
    (255, 0, 0): "sature",
    (47, 47, 47): "sombre",
    (100, 50, 0): "ombre_nuage",
    (0, 160, 0): "vegetation",
    (255, 230, 90): "sol_nu",
    (0, 0, 255): "eau",
    (128, 128, 128): "non_classe",
    (192, 192, 192): "nuage_moyen",
    (255, 255, 255): "nuage_fort",
    (100, 200, 255): "cirrus",
    (255, 150, 255): "neige",
}
# Classes comptées dans le pourcentage de pixels masqués (nuages, cirrus, ombres...).
MASQUE = {"nodata", "sature", "sombre", "ombre_nuage", "nuage_moyen", "nuage_fort", "cirrus"}
# Pixels exclus des statistiques : le masque, plus l'eau (pixels mélangés berge/rivière).
EXCLUS_STATS = MASQUE | {"eau"}

BANDES_NECESSAIRES = ("B04", "B05", "B08", "B8A", "B11")
INDICES = {
    "ndvi": ("B08", "B04"),
    "ndre": ("B8A", "B05"),
    "ndmi": ("B08", "B11"),
}
RE_FICHIER = re.compile(
    r"^(\d{4}-\d{2}-\d{2}).*_L2A_(B\d{1,2}A?|True_color|Scene_classification_map_?)"
    r"(?:_\(Raw\))?\.tiff?$",
    re.IGNORECASE,
)


def lister_scenes(dossier, tmp):
    """Retourne {date: {"bandes": {nom: chemin}, "source": nom}} pour chaque scène."""
    scenes = {}

    def ajouter(chemin, source):
        m = RE_FICHIER.match(chemin.name)
        if not m:
            return
        date, bande = m.group(1), m.group(2)
        bande = "SCL" if bande.lower().startswith("scene") else bande.upper()
        s = scenes.setdefault(date, {"bandes": {}, "source": source})
        if bande in s["bandes"]:
            raise SystemExit(f"Deux fichiers pour la bande {bande} à la date {date} : "
                             f"{s['bandes'][bande]} et {chemin}. Un seul jeu par date est attendu.")
        s["bandes"][bande] = str(chemin)

    for p in sorted(Path(dossier).rglob("*")):
        if p.suffix.lower() == ".zip":
            dest = Path(tmp) / p.stem
            dest.mkdir(exist_ok=True)
            with zipfile.ZipFile(p) as z:
                for nom in z.namelist():
                    base = Path(nom).name  # on ignore les sous-dossiers : pas de traversée de chemin
                    if base and RE_FICHIER.match(base):
                        (dest / base).write_bytes(z.read(nom))
            for f in sorted(dest.iterdir()):
                ajouter(f, p.name)
        elif p.is_file() and p.suffix.lower() in (".tif", ".tiff"):
            ajouter(p, p.parent.name)
    return scenes


def classer_scl(rgb):
    """Convertit la SCL colorée (3, H, W) en indices de classes, par couleur la plus proche."""
    arr = np.rint(rgb * 255).astype(np.int32)
    meilleur = np.full(arr.shape[1:], 10**9, dtype=np.int32)
    lab = np.zeros(arr.shape[1:], dtype=np.int8)
    for k, couleur in enumerate(PALETTE):
        d = sum((arr[c] - couleur[c]) ** 2 for c in range(3))
        mieux = d < meilleur
        meilleur[mieux] = d[mieux]
        lab[mieux] = k
    return lab, float((meilleur > 64).mean())  # part des pixels qui ne ressemblent à aucune classe


def indice_normalise(a, b):
    num, den = a - b, a + b
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(den > 1e-6, num / den, np.nan).astype("float32")


def stats(valeurs):
    if valeurs.size == 0:
        return dict(moy=np.nan, med=np.nan, std=np.nan, p10=np.nan, p90=np.nan)
    return dict(moy=float(valeurs.mean()), med=float(np.median(valeurs)), std=float(valeurs.std()),
                p10=float(np.percentile(valeurs, 10)), p90=float(np.percentile(valeurs, 90)))


def ecrire_carte(chemin, tableau, profil):
    p = profil.copy()
    p.update(count=1, dtype=tableau.dtype.name, compress="deflate",
             nodata=np.nan if tableau.dtype.kind == "f" else None)
    with rasterio.open(chemin, "w", **p) as dst:
        dst.write(tableau, 1)


def traiter_scene(date, scene, parcelles, args, dossier_cartes):
    manque = [b for b in BANDES_NECESSAIRES + ("SCL",) if b not in scene["bandes"]]
    if manque:
        raise SystemExit(f"Scène {date} ({scene['source']}) : bandes manquantes {manque}")

    with rasterio.open(scene["bandes"]["B04"]) as ref:
        profil, transform, crs, forme, res = ref.profile, ref.transform, ref.crs, ref.shape, ref.res[0]
    bandes = {}
    for nom in BANDES_NECESSAIRES:
        with rasterio.open(scene["bandes"][nom]) as src:
            if src.shape != forme or src.transform != transform:
                raise SystemExit(f"Scène {date} : la bande {nom} n'a pas la même grille que B04")
            bandes[nom] = src.read(1).astype("float32")
    with rasterio.open(scene["bandes"]["SCL"]) as src:
        lab, inconnu = classer_scl(src.read())
    if inconnu > 0.01:
        print(f"  Attention : {inconnu:.1%} des pixels SCL ne correspondent à aucune classe connue", file=sys.stderr)

    noms = list(PALETTE.values())
    masque = np.isin(lab, [k for k, n in enumerate(noms) if n in MASQUE])
    eau = np.isin(lab, [k for k, n in enumerate(noms) if n == "eau"])
    exclus = masque | eau

    cartes = {nom: indice_normalise(bandes[a], bandes[b]) for nom, (a, b) in INDICES.items()
              if nom in args.indices}
    for nom, c in cartes.items():
        ecrire_carte(dossier_cartes / f"{date}_{nom}.tif", np.where(exclus, np.nan, c).astype("float32"), profil)
    ecrire_carte(dossier_cartes / f"{date}_masque_nuages.tif", masque.astype("uint8"), profil)

    parcelles_r = parcelles.to_crs(crs)
    # contrôle d'emprise : les parcelles doivent chevaucher l'image
    gauche, bas, droite, haut = rasterio.transform.array_bounds(forme[0], forme[1], transform)
    x0, y0, x1, y1 = parcelles_r.total_bounds
    if x1 < gauche or x0 > droite or y1 < bas or y0 > haut:
        raise SystemExit(f"Les parcelles ne chevauchent pas la scène {date} : vérifie le CRS et le site.")

    lignes = []
    for (_, p), geom in zip(parcelles.iterrows(), parcelles_r.geometry):
        reduite = geom.buffer(-args.erosion_px * res) if args.erosion_px > 0 else geom
        if reduite.is_empty:
            m = np.zeros(forme, dtype=bool)
        else:
            m = features.geometry_mask([reduite], out_shape=forme, transform=transform, invert=True)
        n_px = int(m.sum())
        ligne = dict(parcelle_id=p["parcelle_id"], site=p.get("site"), date=date, scene_source=scene["source"],
                     aire_ha=round(geom.area / 1e4, 3), n_px_parcelle=n_px)
        pct_masque = float(masque[m].mean() * 100) if n_px else np.nan
        pct_eau = float(eau[m].mean() * 100) if n_px else np.nan
        utiles = m & ~exclus
        ligne.update(n_px_valides=int(utiles.sum()), pct_masque=round(pct_masque, 1), pct_eau=round(pct_eau, 1))
        if n_px < args.min_pixels:
            statut = "trop_petite"
        elif pct_masque > args.seuil_nuage:
            statut = "non_fiable"
        elif ligne["n_px_valides"] < args.min_pixels:
            statut = "insuffisant"
        else:
            statut = "ok"
        ligne["statut"] = statut
        for nom, c in cartes.items():
            v = c[utiles]
            s = stats(v[~np.isnan(v)]) if statut != "trop_petite" else stats(np.array([]))
            ligne.update({f"{nom}_{k}": (round(x, 4) if not np.isnan(x) else np.nan) for k, x in s.items()})
        lignes.append(ligne)
    return lignes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", required=True, help="dossier de scènes Sentinel-2 (dossiers ou .zip)")
    ap.add_argument("--parcelles", required=True, help="GeoJSON des parcelles (champs parcelle_id, site)")
    ap.add_argument("--out", required=True, help="dossier de résultats")
    ap.add_argument("--seuil-nuage", type=float, default=50.0,
                    help="au-dessus de ce %% de pixels masqués, la parcelle est 'non_fiable' (défaut 50)")
    ap.add_argument("--erosion-px", type=float, default=1.0, help="rétrécissement des parcelles, en pixels (défaut 1)")
    ap.add_argument("--min-pixels", type=int, default=20, help="pixels minimum pour calculer des statistiques (défaut 20)")
    ap.add_argument("--indices", nargs="+", default=list(INDICES), choices=list(INDICES))
    args = ap.parse_args(argv)

    parcelles = gpd.read_file(args.parcelles)
    if "parcelle_id" not in parcelles.columns:
        raise SystemExit("Le GeoJSON doit contenir un champ 'parcelle_id'.")
    if not parcelles.parcelle_id.is_unique:
        raise SystemExit("Les parcelle_id ne sont pas uniques : " +
                         str(parcelles.parcelle_id[parcelles.parcelle_id.duplicated()].tolist()))
    if parcelles.crs is None:
        raise SystemExit("Le GeoJSON n'a pas de système de coordonnées.")

    out = Path(args.out)
    cartes = out / "cartes"
    cartes.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        scenes = lister_scenes(args.images, tmp)
        if not scenes:
            raise SystemExit(f"Aucune scène Sentinel-2 trouvée dans {args.images}")
        toutes = []
        for date in sorted(scenes):
            print(f"Scène {date} ({scenes[date]['source']})")
            toutes += traiter_scene(date, scenes[date], parcelles, args, cartes)

    df = pd.DataFrame(toutes)
    df.to_csv(out / "parcelles_indices.csv", index=False)

    large = parcelles[["parcelle_id", "site", "geometry"]].copy()
    for date in sorted(scenes):
        sous = df[df.date == date].set_index("parcelle_id")
        for col in ["statut", "pct_masque"] + [f"{i}_moy" for i in args.indices]:
            large[f"{col}_{date}"] = large.parcelle_id.map(sous[col])
    large.to_file(out / "parcelles_indices.geojson", driver="GeoJSON")

    (out / "parametres.json").write_text(json.dumps({
        "seuil_nuage_pct": args.seuil_nuage, "erosion_px": args.erosion_px, "min_pixels": args.min_pixels,
        "indices": {k: v for k, v in INDICES.items() if k in args.indices},
        "scenes": {d: s["source"] for d, s in scenes.items()},
        "parcelles": str(args.parcelles), "n_parcelles": len(parcelles)}, indent=2, ensure_ascii=False),
        encoding="utf8")

    print("\nStatuts par date :")
    print(df.groupby(["date", "statut"]).size().unstack(fill_value=0).to_string())
    print(f"\nRésultats dans {out}/")


if __name__ == "__main__":
    main()
