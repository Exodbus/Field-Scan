#!/usr/bin/env python3
"""Préparation des données du rendu 3D (Blender) : une mosaïque de tuiles d'entraînement du comptage, ses pieds
détectés par le détecteur v5 et la vigueur (ExG) réellement calculée par la chaîne.

Étapes :
  1. tuiles rt_Flora_Pluas_5cm_<x0>_<y0> de data/drone/comptage_v5_5cm, toutes vérifiées « train » (partie et
     ensemble) et à l'échelle native (facteur 1). Les tuiles ont été découpées par scripts/preparer_deepforest.py
     dans l'orthomosaïque Flora Pluas rééchantillonnée à 5 cm, au pas de 409 px pour 512 px de côté : deux tuiles
     voisines se recouvrent sur 103 px. On les recolle à leur place (origine x0, y0 dans le nom) ; on contrôle que
     les recouvrements concordent et que la mosaïque ne contient aucun pixel hors orthomosaïque (noir) ;
  2. détecteur de centres v5 (fieldscan.drone.DetecteurCentres, importé tel quel), seuil 0,30, appliqué UNE fois
     à la mosaïque entière : le détecteur parcourt lui-même l'image par fenêtres (comme run.py sur une
     orthomosaïque), il n'y a donc ni doublon ni pied coupé aux jonctions des tuiles ;
  3. géoréférencement : même calcul de facteur que preparer_deepforest.py, contrôlé en relisant l'orthomosaïque ;
  4. vigueur : carte ExG drone écrite par la chaîne (run.py --modules vigueur, dossier --chaine), lue au centre de
     chaque pied ; écart à la médiane ExG de la parcelle donnée par le bulletin de la même exécution ;
     zones d'alerte du bulletin qui touchent la mosaïque.

Une seule tuile (prototype v1) : --x0 818 --y0 818 --out out/rendu_blender.

Sorties dans --out : plants.csv, tuile.png (texture du sol, la mosaïque), tuile_detections.png, donnees_rendu.json.

Exemple :
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/rendu_preparer.py
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import geopandas as gpd  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import rasterio  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from pyproj import Transformer  # noqa: E402
from rasterio.enums import Resampling  # noqa: E402
from rasterio.windows import Window  # noqa: E402
from shapely.geometry import Point, Polygon  # noqa: E402

from fieldscan import drone  # noqa: E402

PREFIXE = "rt_Flora_Pluas_5cm_"
SITE = "Flora Pluas"
RES_M = 0.05
UTM = "EPSG:32717"
COTE_TUILE = 512


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jeu", default="data/drone/comptage_v5_5cm")
    ap.add_argument("--x0", type=int, nargs="+", default=[818, 1227, 1636], help="colonnes des tuiles (px, ortho 5 cm)")
    ap.add_argument("--y0", type=int, nargs="+", default=[818, 1227, 1636], help="lignes des tuiles (px, ortho 5 cm)")
    ap.add_argument("--modele", default="modeles/centres_5cm_v5.onnx")
    ap.add_argument("--seuil", type=float, default=0.30)
    ap.add_argument("--ortho", default=f"data/drone/reforestree/wwf_ecuador/RGB Orthomosaics/{SITE} RGB.tif")
    ap.add_argument("--chaine", default="out/rendu_blender/chaine_vigueur",
                    help="sortie de run.py --modules vigueur sur les orthomosaïques ReforesTree")
    ap.add_argument("--out", default="out/rendu_blender/v2")
    a = ap.parse_args(argv)
    jeu, out, chaine = RACINE / a.jeu, RACINE / a.out, RACINE / a.chaine
    out.mkdir(parents=True, exist_ok=True)

    # 1. tuiles : split d'entraînement seulement, recollées à leur place
    t = pd.read_csv(jeu / "tuiles.csv")
    xs, ys = sorted(a.x0), sorted(a.y0)
    for v in (xs, ys):
        assert all(b - c <= COTE_TUILE for b, c in zip(v[1:], v[:-1])), f"tuiles non contiguës : {v}"
    X0, Y0 = xs[0], ys[0]
    l, h = xs[-1] + COTE_TUILE - X0, ys[-1] + COTE_TUILE - Y0
    rgb = np.zeros((h, l, 3), np.uint8)
    couvert = np.zeros((h, l), np.int16)
    noms, ecarts = [], []
    for y0 in ys:
        for x0 in xs:
            nom = f"{PREFIXE}{x0}_{y0}.jpg"
            ligne = t[t.image_path == nom]
            assert len(ligne) == 1, f"tuile absente de tuiles.csv : {nom}"
            ligne = ligne.iloc[0]
            assert ligne.partie == "train" and ligne.ensemble == "train", f"tuile hors entraînement : {nom} {ligne.partie}"
            assert float(ligne.facteur) == 1.0, f"tuile rééchantillonnée : {nom}"
            im = np.asarray(Image.open(jeu / "images" / nom).convert("RGB"))
            assert im.shape[:2] == (COTE_TUILE, COTE_TUILE), (nom, im.shape)
            zone = (slice(y0 - Y0, y0 - Y0 + COTE_TUILE), slice(x0 - X0, x0 - X0 + COTE_TUILE))
            deja = couvert[zone] > 0
            if deja.any():                                         # recouvrement : les deux tuiles doivent concorder
                ecarts.append(float(np.abs(rgb[zone][deja].astype("float32") - im[deja].astype("float32")).mean()))
            rgb[zone] = im
            couvert[zone] += 1
            noms.append(nom)
    assert (couvert > 0).all(), "mosaïque trouée"
    ecart_recouvrement = max(ecarts) if ecarts else 0.0
    print(f"{len(noms)} tuiles d'entraînement recollées : {l} x {h} px ; écart moyen max dans les recouvrements "
          f"{ecart_recouvrement:.2f} niveaux (compression JPEG)")
    assert ecart_recouvrement < 8, "les recouvrements ne concordent pas"
    noir = float((rgb.max(-1) < 8).mean())
    print(f"part de pixels noirs (hors orthomosaïque) : {noir:.4f}")
    assert noir < 0.002, "la mosaïque déborde de l'orthomosaïque"
    valide = np.ones((h, l), bool)
    Image.fromarray(rgb).save(out / "tuile.png")

    # 2. détecteur v5, code de fieldscan importé sans modification, appliqué à la mosaïque entière
    det = drone.DetecteurCentres(RACINE / a.modele)
    debut = time.time()
    xy, scores = det.predire(np.moveaxis(rgb, -1, 0), valide)    # le détecteur attend (3, h, l), ordre de rasterio
    duree = time.time() - debut
    garde = scores >= a.seuil
    xy, scores = xy[garde], scores[garde]
    print(f"{len(xy)} centres détectés au seuil {a.seuil} (seuil du .json : {det.seuil}) en {duree:.1f} s")
    # contrôle : plus proche voisin (un doublon donnerait deux centres à quelques décimètres)
    dmin = np.sqrt(((xy[:, None] - xy[None]) ** 2).sum(-1) + np.eye(len(xy)) * 1e12).min(1) * RES_M
    print(f"distance au plus proche voisin : min {dmin.min():.2f} m, médiane {np.median(dmin):.2f} m")

    # 3. géoréférencement (même calcul que scripts/preparer_deepforest.py : lire_site)
    with rasterio.open(RACINE / a.ortho) as src:
        lat = (src.bounds.bottom + src.bounds.top) / 2
        natif = abs(src.res[0]) * 111_320 * math.cos(math.radians(lat)) if src.crs.is_geographic else abs(src.res[0])
        f = max(RES_M / natif, 1.0)
        hh, ll = round(src.height / f), round(src.width / f)
        fx, fy = src.width / ll, src.height / hh
        T, crs = src.transform, src.crs
        # contrôle : relecture de la fenêtre de la mosaïque dans l'orthomosaïque, au même pas
        win = Window(X0 * fx, Y0 * fy, l * fx, h * fy)
        relu = src.read((1, 2, 3), window=win, out_shape=(3, h, l), resampling=Resampling.average)
    relu = np.moveaxis(relu, 0, -1).astype("float32")
    g1, g2 = relu.mean(-1).ravel(), rgb.astype("float32").mean(-1).ravel()
    correlation = float(np.corrcoef(g1, g2)[0, 1])
    print(f"contrôle du géoréférencement : corrélation mosaïque / orthomosaïque relue = {correlation:.3f}")
    assert correlation > 0.9, "la mosaïque ne correspond pas à la fenêtre calculée"
    vers_utm = Transformer.from_crs(crs, UTM, always_xy=True)

    def geo(px, py):
        lon, la = T * ((X0 + px) * fx, (Y0 + py) * fy)
        return vers_utm.transform(lon, la)

    coins = [geo(0, 0), geo(l, 0), geo(l, h), geo(0, h)]
    cote_m = (math.dist(coins[0], coins[1]), math.dist(coins[0], coins[3]))
    print(f"côtés de la mosaïque au sol : {cote_m[0]:.2f} x {cote_m[1]:.2f} m (attendu {l * RES_M:.2f} x {h * RES_M:.2f} m)")

    # 4. vigueur réelle de la chaîne
    carte = chaine / "cartes" / f"drone_exg_{SITE}.tif"
    bulletin = pd.read_csv(chaine / "bulletin.csv")
    bp = bulletin[bulletin.parcelle_id == SITE].iloc[0]
    med = float(bp.vigueur_drone_exg_med)
    alertes = gpd.read_file(chaine / "alertes.geojson").to_crs(UTM)
    poly = Polygon(coins)
    touchent = alertes[alertes.intersects(poly)]
    utm = np.array([geo(px, py) for px, py in xy])
    with rasterio.open(carte) as c:
        assert c.crs.to_string() == UTM or c.crs.to_epsg() == 32717, c.crs
        exg = np.array([v[0] for v in c.sample([tuple(p) for p in utm])], "float64")
        nodata = c.nodata
        b = poly.bounds
        w = rasterio.windows.from_bounds(*b, transform=c.transform)
        exg_tuile = c.read(1, window=w, boundless=True, fill_value=np.nan)
    if nodata is not None:
        exg[exg == nodata] = np.nan
    dans_alerte = [bool(any(g.contains(Point(p)) for g in touchent.geometry)) for p in utm]

    # repère du rendu : origine au centre de la mosaïque, x vers l'est (droite de l'image), y vers le nord (haut)
    df = pd.DataFrame(dict(
        id=np.arange(len(xy)),
        x_m=np.round((xy[:, 0] - l / 2) * RES_M, 3),
        y_m=np.round((h / 2 - xy[:, 1]) * RES_M, 3),
        x_px=np.round(xy[:, 0], 1), y_px=np.round(xy[:, 1], 1),
        score=np.round(scores, 3),
        est_utm=np.round(utm[:, 0], 2), nord_utm=np.round(utm[:, 1], 2),
        exg=np.round(exg, 4), exg_ecart_parcelle=np.round(exg - med, 4),
        dans_zone_alerte=dans_alerte,
    ))
    df.to_csv(out / "plants.csv", index=False, encoding="utf-8")

    # vignette : mosaïque réelle, centres détectés, jonctions des tuiles en pointillé
    im = Image.fromarray(rgb).convert("RGB")
    d = ImageDraw.Draw(im)
    for x0 in xs[1:]:
        for yy in range(0, h, 16):
            d.line([(x0 - X0, yy), (x0 - X0, yy + 7)], fill=(255, 255, 255), width=1)
    for y0 in ys[1:]:
        for xx in range(0, l, 16):
            d.line([(xx, y0 - Y0), (xx + 7, y0 - Y0)], fill=(255, 255, 255), width=1)
    for px, py in xy:
        d.ellipse((px - 7, py - 7, px + 7, py + 7), outline=(255, 40, 40), width=3)
    im.save(out / "tuile_detections.png")

    # annotations existantes (référence d'entraînement, pour mémoire : pas une mesure de performance). Dans les
    # recouvrements, un pied annoté figure dans deux tuiles : chaque tuile ne compte que sa « part » (coupure au
    # milieu du recouvrement).
    obj = pd.read_csv(jeu / "objets.csv")
    n_annot = 0
    for nom in noms:
        x0, y0 = map(int, Path(nom).stem.split("_")[-2:])
        o = obj[obj.image_path == nom]
        gx, gy = o.cx + x0, o.cy + y0

        def part(g, v, o0):
            i = v.index(o0)
            bas = v[0] if i == 0 else (v[i - 1] + COTE_TUILE + o0) / 2
            haut = v[-1] + COTE_TUILE if i == len(v) - 1 else (o0 + COTE_TUILE + v[i + 1]) / 2
            return (g >= bas) & (g < haut)
        n_annot += int((part(gx, xs, x0) & part(gy, ys, y0)).sum())

    info = dict(
        tuiles=noms, jeu=a.jeu, partie="train", groupe="rt_flora_pluas", site=SITE,
        resolution_m=RES_M, cote_px=[l, h], cote_sol_m=[round(cote_m[0], 3), round(cote_m[1], 3)],
        origine_dans_ortho_5cm_px=[X0, Y0], facteur_ortho=[fx, fy], correlation_controle=round(correlation, 4),
        ecart_recouvrements_niveaux=round(ecart_recouvrement, 2), part_pixels_noirs=round(noir, 5),
        coins_utm=[[round(x, 2), round(y, 2)] for x, y in coins],
        detecteur=dict(modele=a.modele, seuil=a.seuil, seuil_json=det.seuil, k_pics=det.k_pics,
                       n_detectes=int(len(xy)), duree_s=round(duree, 2), applique_a="mosaïque entière",
                       plus_proche_voisin_min_m=round(float(dmin.min()), 3)),
        annotations_existantes=n_annot,
        vigueur=dict(source=f"{a.chaine} (run.py --modules vigueur)", carte=carte.relative_to(RACINE).as_posix(),
                     parcelle=SITE, niveau_parcelle=str(bp.niveau), score_parcelle=float(bp.score),
                     exg_mediane_parcelle=med,
                     alertes_touchant_la_tuile=touchent.id.tolist() if "id" in touchent else [],
                     exg_pieds_min=float(np.nanmin(exg)), exg_pieds_max=float(np.nanmax(exg)),
                     exg_pieds_mediane=float(np.nanmedian(exg)),
                     ecart_pieds_min=float(np.nanmin(exg - med)), ecart_pieds_max=float(np.nanmax(exg - med)),
                     n_pieds_dans_alerte=int(sum(dans_alerte)),
                     exg_tuile_quantiles=[float(q) for q in np.nanquantile(exg_tuile, [0.05, 0.5, 0.95])]),
    )
    (out / "donnees_rendu.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"annotations existantes dans la mosaïque : {n_annot}")
    print(json.dumps(info["vigueur"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
