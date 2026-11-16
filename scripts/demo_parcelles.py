#!/usr/bin/env python3
"""Démo finale : délimitation automatique des parcelles sur une orthomosaïque (prototype, méthodes classiques).

Copie de `scripts/eloro_parcelles.py` (méthode d'El Oro, mêmes étapes et mêmes réglages par défaut), adaptée :
- site et orthomosaïque en paramètres (`--site martinique|silkwood` ou `--ortho` + `--out`) ;
- lecture réduite reprojetée dans un système métrique UTM (WarpedVRT, moyenne) : l'orthomosaïque de Silkwood est
  en EPSG:3857, dont le mètre vaut environ 0,95 m au sol à 17,7° S ;
- pixels valides : somme RGB > 0 (pas de valeur « nodata » déclarée dans les orthos de la démo) ;
- la vue de contrôle porte le nom du site.

Aucun modèle appris, aucune annotation à la main. L'orthomosaïque est lue réduite (0,5 m par pixel par défaut,
sous-échantillonnage rasterio en moyenne), jamais en pleine résolution.

Étapes :
1. excès de vert ExG = 2g - r - b (coordonnées chromatiques) et luminosité, lissés ;
2. « force de limite » de chaque pixel : structures étroites moins vertes que leur voisinage (black top-hat de l'ExG,
   chemins, drains, câbles) ou plus claires (white top-hat de la luminosité), plus le gradient de l'ExG et de la
   texture lissés (changement de couvert d'un champ à l'autre) ;
3. germes : maxima de la distance aux limites fortes ; ligne de partage des eaux (OpenCV) sur la force de limite ;
4. fusion des régions voisines séparées par une limite faible et de couvert semblable (union-find) ;
5. régions de moins de `--surface-min-ha` fusionnées à leur voisine la plus semblable, puis écartées si isolées ;
6. polygones (rasterio.features.shapes), simplifiés, en EPSG de l'orthomosaïque, puis GeoJSON (EPSG:4326 et UTM).

Sortie : GeoJSON avec parcelle_id (P01, P02…), surface_ha, part_vegetation, exg_median, type_couvert (indicatif),
et une vue de contrôle PNG.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/demo_parcelles.py --site martinique
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/demo_parcelles.py --site silkwood
"""
import argparse
import json
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import cv2
import geopandas as gpd
import numpy as np
import rasterio
from rasterio import features
from rasterio.enums import Resampling
from scipy import ndimage as ndi
from shapely.geometry import shape

SITES = {
    "martinique": dict(ortho=RACINE / "data/raw/ortho_martinique_basse_pointe/ortho_martinique_basse_pointe_2025_20cm.tif",
                       out=RACINE / "out/demo_martinique", nom="Martinique, Basse-Pointe (IGN BD ORTHO, 20 cm)"),
    "silkwood": dict(ortho=RACINE / "data/raw/ortho_qld_silkwood_2022/ortho_qld_silkwood_2022_10cm.tif",
                     out=RACINE / "out/demo_silkwood", nom="Silkwood, Queensland (SISP 2022, 10 cm)"),
}


def lire_reduite(chemin, res_m):
    """RGB float32 (3, H, W), masque valide, transform, crs métrique (UTM), à la résolution res_m (moyenne)."""
    import geopandas as _gpd
    from rasterio.transform import from_origin
    from rasterio.vrt import WarpedVRT
    from rasterio.warp import transform_bounds
    from shapely.geometry import box
    with rasterio.open(chemin) as s:
        b4326 = transform_bounds(s.crs, "EPSG:4326", *s.bounds)
        crs = _gpd.GeoSeries([box(*b4326)], crs="EPSG:4326").estimate_utm_crs()
        # même zone UTM que l'ortho si elle y est déjà (Martinique : EPSG:5490, RGAF09 / UTM 20N)
        if s.crs.is_projected and s.crs.to_epsg() != 3857:
            crs = s.crs
        x0, y0, x1, y1 = transform_bounds(s.crs, crs, *s.bounds)
        W, H = int(np.ceil((x1 - x0) / res_m)), int(np.ceil((y1 - y0) / res_m))
        t = from_origin(x0, y1, res_m, res_m)
        with WarpedVRT(s, crs=crs, transform=t, width=W, height=H, resampling=Resampling.average,
                       src_nodata=s.nodata, nodata=0) as v:
            a = v.read([1, 2, 3]).astype("float32")
    # hors couverture : noir, mais la compression JPEG y laisse quelques niveaux de bruit (Silkwood, bord nord)
    valide = a.sum(0) > 15
    return a, valide, t, crs


def exg_lum(a, valide):
    tot = a.sum(0)
    with np.errstate(divide="ignore", invalid="ignore"):
        e = np.where(valide, (2 * a[1] - a[0] - a[2]) / np.maximum(tot, 1), 0).astype("float32")
    lum = (tot / 3).astype("float32")
    return e, lum


def norm_pct(x, m, p=99):
    """Ramène x à [0, 1] par ses percentiles 1 et p dans le masque m."""
    lo, hi = np.percentile(x[m], [1, p])
    return np.clip((x - lo) / max(hi - lo, 1e-6), 0, 1).astype("float32")


def segment(longueur, angle_deg):
    """Élément structurant : segment de `longueur` pixels orienté à `angle_deg`."""
    k = longueur | 1
    se = np.zeros((k, k), np.uint8)
    c = k // 2
    dx, dy = np.cos(np.radians(angle_deg)) * c, np.sin(np.radians(angle_deg)) * c
    cv2.line(se, (int(round(c - dx)), int(round(c - dy))), (int(round(c + dx)), int(round(c + dy))), 1, 1)
    return se


def lineaire(x, longueur, n_angles=12):
    """Maximum des ouvertures morphologiques par des segments (approximation d'une ouverture par chemins)."""
    return np.max([cv2.morphologyEx(x, cv2.MORPH_OPEN, segment(longueur, a)) for a in np.arange(0, 180, 180 / n_angles)], axis=0)


def lisser_etiquettes(out, valide, px, sigma_m):
    """Lissage des contours : chaque pixel prend l'étiquette dont l'indicatrice lissée est la plus forte."""
    ids = np.unique(out[out > 0])
    meilleur = np.zeros(out.shape, "float32"); res = out.copy()
    for i in ids:
        s = cv2.GaussianBlur((out == i).astype("float32"), (0, 0), sigma_m / px)
        plus = s > meilleur
        res[plus] = i; meilleur[plus] = s[plus]
    res[~valide] = 0
    return res


def force_limite(e, lum, valide, px, largeur_chemin_m=8.0, poids_grad=0.6, poids_sombre=1.0):
    """Carte [0, 1] de la vraisemblance d'une limite de parcelle."""
    k = int(round(largeur_chemin_m / px)) | 1
    noyau = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    es = cv2.GaussianBlur(e, (0, 0), 0.75 / px)
    ls = cv2.GaussianBlur(lum, (0, 0), 0.75 / px)
    es_v = np.where(valide, es, np.median(es[valide])).astype("float32")
    ls_v = np.where(valide, ls, np.median(ls[valide])).astype("float32")
    sombre = cv2.morphologyEx(es_v, cv2.MORPH_BLACKHAT, noyau)        # étroit et moins vert que les côtés
    clair = cv2.morphologyEx(ls_v, cv2.MORPH_TOPHAT, noyau)            # étroit et plus clair que les côtés
    # changement de couvert : gradient de l'ExG moyen et de la texture (écart type local) à l'échelle de 5 m
    s5 = 5.0 / px
    m5 = cv2.GaussianBlur(es_v, (0, 0), s5)
    tex = np.sqrt(np.maximum(cv2.GaussianBlur(es_v * es_v, (0, 0), s5) - m5 * m5, 0))
    g = lambda x: np.hypot(cv2.Sobel(x, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(x, cv2.CV_32F, 0, 1, ksize=3))
    # texture fine (feuilles, ombres entre couronnes) : écart type relatif de la luminosité passe-haut (< 1,5 m),
    # moyenné sur 4 m ; sépare une bananeraie (grain fin et régulier) d'une prairie ou d'un bosquet
    hp = ls_v - cv2.GaussianBlur(ls_v, (0, 0), 1.5 / px)
    fin = np.sqrt(cv2.GaussianBlur(hp * hp, (0, 0), 4.0 / px)) / np.maximum(cv2.GaussianBlur(ls_v, (0, 0), 4.0 / px), 1)
    fin = fin.astype("float32")
    grad = (norm_pct(g(m5), valide) + norm_pct(g(tex), valide) + norm_pct(g(fin), valide)) / 3
    # poids_sombre < 1 : les lignes sombres (rangs d'ombre, drains entre doubles rangs) pèsent moins que les pistes claires
    ligne = np.maximum(poids_sombre * norm_pct(sombre, valide), 0.7 * norm_pct(clair, valide))
    # ne garder que les structures allongées : ouverture par des segments de 12 m dans 12 orientations (le maximum
    # des ouvertures efface les taches rondes, trous entre couronnes, troncs, et garde chemins, drains, câbles)
    lin = lineaire(ligne, int(round(12.0 / px)))
    f = np.maximum(norm_pct(lin, valide), poids_grad * grad)
    f[~valide] = 1.0
    return f.astype("float32"), m5, tex, fin, lin


def partage(f, valide, px, seuil_fort, dist_min_m, ecart_germes_m):
    """Ligne de partage des eaux sur f, germes aux maxima de la distance aux limites fortes."""
    fort = (f >= seuil_fort) | ~valide
    fort = cv2.morphologyEx(fort.astype("uint8"), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)).astype(bool)
    d = ndi.distance_transform_edt(~fort) * px
    pic = (d == ndi.maximum_filter(d, size=int(ecart_germes_m / px))) & (d >= dist_min_m)
    germes, n = ndi.label(cv2.dilate(pic.astype("uint8"), np.ones((3, 3), np.uint8)))
    germes = germes.astype("int32")
    germes[~valide] = n + 1                                     # fond : un germe à part
    relief = (np.clip(f, 0, 1) * 255).astype("uint8")
    lab = cv2.watershed(cv2.merge([relief, relief, relief]), germes)
    lab[lab == n + 1] = 0
    return lab, n


def fusionner(lab, f, m5, tex, fin, valide, seuil_limite, ecart_exg, ecart_tex, ecart_fin, seuil_limite_2=0.40):
    """Fusionne les voisines séparées par une limite faible (moyenne de f sur la frontière) et de couvert semblable.

    Deux paliers : frontière < seuil_limite et écarts de couvert sous leurs seuils ; ou frontière < seuil_limite_2
    et écarts sous la moitié des seuils (couvert très semblable : le grain d'une bananeraie crée des lignes
    internes de force moyenne)."""
    # frontières : pixels -1 de cv2.watershed ; voisins de part et d'autre (4 directions, à 1 et 2 pixels)
    H, W = lab.shape
    ys, xs = np.nonzero(lab == -1)
    paires = {}
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        y1, x1, y2, x2 = ys - dy, xs - dx, ys + dy, xs + dx
        ok = (y1 >= 0) & (x1 >= 0) & (x1 < W) & (y2 < H) & (x2 >= 0) & (x2 < W)
        a, b = lab[y1[ok], x1[ok]], lab[y2[ok], x2[ok]]
        v = f[ys[ok], xs[ok]]
        bon = (a > 0) & (b > 0) & (a != b)
        for i, j, val in zip(np.minimum(a, b)[bon], np.maximum(a, b)[bon], v[bon]):
            s = paires.setdefault((int(i), int(j)), [0.0, 0])
            s[0] += float(val); s[1] += 1
    ids = np.unique(lab[lab > 0])
    # statistiques de chaque groupe (moyennes pondérées par la surface), mises à jour à chaque fusion : on compare
    # les groupes déjà formés, pas les régions d'origine (évite les enchaînements prairie -> bosquet -> bananeraie)
    n_px = dict(zip(ids, ndi.sum(np.ones_like(m5), lab, ids)))
    stats = {int(i): np.array([n_px[i], *(n_px[i] * np.array([e, t_, fi]))])
             for i, e, t_, fi in zip(ids, ndi.median(m5, lab, ids), ndi.median(tex, lab, ids), ndi.median(fin, lab, ids))}
    parent = {int(i): int(i) for i in ids}

    def racine(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    seuils = np.array([ecart_exg, ecart_tex, ecart_fin])
    # des frontières les plus faibles aux plus fortes
    for (i, j), (s, n) in sorted(paires.items(), key=lambda kv: kv[1][0] / kv[1][1]):
        if n < 4 or s / n >= seuil_limite_2:
            continue
        ri, rj = racine(i), racine(j)
        if ri == rj:
            continue
        mi, mj = stats[ri][1:] / stats[ri][0], stats[rj][1:] / stats[rj][0]
        facteur = 1.0 if s / n < seuil_limite else 0.5
        if np.all(np.abs(mi - mj) < facteur * seuils):
            parent[rj] = ri
            stats[ri] = stats[ri] + stats[rj]
    table = np.zeros(lab.max() + 1, "int32")
    for i in ids:
        table[i] = racine(int(i))
    out = np.where(lab > 0, table[np.maximum(lab, 0)], 0)
    # pixels de frontière : rattachés à la région voisine majoritaire (évite des trous de 1 pixel dans les polygones)
    front = (lab == -1) & valide
    if front.any():
        _, (iy, ix) = ndi.distance_transform_edt(out == 0, return_indices=True)
        out[front] = out[iy[front], ix[front]]
    return out, paires


def petites(out, carac, seuils, px, surface_min_ha, valide):
    """Régions sous la surface minimale fusionnées à la voisine de couvert le plus proche (itératif).

    Couvert : médianes de l'ExG, de la texture et de la texture fine, chaque écart rapporté à son seuil de fusion."""
    pix_ha = px * px / 1e4
    for _ in range(50):
        ids, n = np.unique(out[out > 0], return_counts=True)
        surf = dict(zip(ids, n * pix_ha))
        trop = [i for i in ids if surf[i] < surface_min_ha]
        if not trop:
            break
        med = {i: np.array(v) for i, v in zip(ids, zip(*[ndi.median(c, out, ids) for c in carac]))}
        change = False
        for i in sorted(trop, key=lambda k: surf[k]):
            m = out == i
            anneau = cv2.dilate(m.astype("uint8"), np.ones((5, 5), np.uint8)).astype(bool) & ~m
            voisins = [v for v in np.unique(out[anneau]) if v > 0 and v != i]
            if not voisins:
                continue
            v = min(voisins, key=lambda k: float(np.max(np.abs(med[k] - med[i]) / seuils)))
            out[m] = v; change = True
        if not change:
            break
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", choices=list(SITES), help="site de la démo (fixe --ortho et --out par défaut)")
    ap.add_argument("--ortho", default=None)
    ap.add_argument("--res", type=float, default=0.5, help="résolution de travail (m par pixel)")
    ap.add_argument("--surface-min-ha", type=float, default=0.3)
    ap.add_argument("--seuil-fort", type=float, default=0.45, help="force de limite au-delà de laquelle un pixel est une limite")
    ap.add_argument("--seuil-fusion", type=float, default=0.26, help="force moyenne de frontière sous laquelle on fusionne")
    ap.add_argument("--seuil-fusion-2", type=float, default=0.40,
                    help="second palier : frontière plus forte tolérée si le couvert est très semblable (demi-écarts)")
    ap.add_argument("--ecart-exg", type=float, default=0.035)
    ap.add_argument("--ecart-tex", type=float, default=0.015)
    ap.add_argument("--ecart-fin", type=float, default=0.025, help="écart maximal de texture fine pour fusionner")
    ap.add_argument("--seuil-veg", type=float, default=0.06, help="ExG au-delà duquel un pixel est de la végétation")
    ap.add_argument("--lissage-m", type=float, default=2.5, help="lissage des contours des parcelles (m)")
    ap.add_argument("--largeur-chemin-m", type=float, default=8.0, help="taille du top-hat (structures plus étroites)")
    ap.add_argument("--ecart-germes-m", type=float, default=30.0, help="écart minimal entre germes du partage des eaux")
    ap.add_argument("--poids-sombre", type=float, default=1.0, help="poids des lignes sombres étroites (1 = El Oro)")
    ap.add_argument("--fils", type=int, default=6, help="fils OpenCV au plus")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.site:
        args.ortho = args.ortho or str(SITES[args.site]["ortho"]); args.out = args.out or str(SITES[args.site]["out"])
    if not args.ortho or not args.out:
        ap.error("--site, ou bien --ortho et --out")
    cv2.setNumThreads(args.fils)
    debut = time.time()
    sortie = Path(args.out); sortie.mkdir(parents=True, exist_ok=True)
    a, valide, t, crs = lire_reduite(args.ortho, args.res)
    px = abs(t.a)
    # bord de l'image : 2 m écartés (mosaïque floue, pixels mélangés au fond noir)
    valide = cv2.erode(valide.astype("uint8"), np.ones((5, 5), np.uint8)).astype(bool)
    e, lum = exg_lum(a, valide)
    f, m5, tex, fin, ligne = force_limite(e, lum, valide, px, largeur_chemin_m=args.largeur_chemin_m, poids_sombre=args.poids_sombre)
    lab, n_germes = partage(f, valide, px, args.seuil_fort, dist_min_m=6.0, ecart_germes_m=args.ecart_germes_m)
    out, _ = fusionner(lab, f, m5, tex, fin, valide, args.seuil_fusion, args.ecart_exg, args.ecart_tex, args.ecart_fin,
                       args.seuil_fusion_2)
    out = petites(out, (m5, tex, fin), np.array([args.ecart_exg, args.ecart_tex, args.ecart_fin]), px,
                  args.surface_min_ha, valide)
    out[~valide] = 0
    out = lisser_etiquettes(out, valide, px, args.lissage_m)

    # polygones
    veg = (cv2.GaussianBlur(e, (0, 0), 1.0) > args.seuil_veg) & valide
    lignes = []
    for geom, v in features.shapes(out.astype("int32"), mask=out > 0, transform=t):
        lignes.append(dict(lab=int(v), geometry=shape(geom)))
    g = gpd.GeoDataFrame(lignes, geometry="geometry", crs=crs).dissolve("lab").reset_index()
    g["geometry"] = g.geometry.buffer(0).simplify(1.0, preserve_topology=True)
    g["surface_ha"] = (g.area / 1e4).round(3)
    g = g[g.surface_ha >= args.surface_min_ha].copy()
    ids = g.lab.values
    part = ndi.mean(veg.astype("float32"), out, ids)
    exg_med = ndi.median(e, out, ids)
    tex_med = ndi.median(tex, out, ids)
    fin_med = ndi.median(fin, out, ids)
    g["part_vegetation"] = np.round(part, 3)
    g["exg_median"] = np.round(exg_med, 4)
    g["texture_exg"] = np.round(tex_med, 4)
    g["texture_fine"] = np.round(fin_med, 4)
    # ordre de lecture : du nord-ouest au sud-est (centroïde), identifiants P01, P02…
    c = g.geometry.centroid
    g = g.assign(_o=(-c.y.round(-1)) * 1e7 + c.x).sort_values("_o").drop(columns="_o")
    g["parcelle_id"] = [f"P{k:02d}" for k in range(1, len(g) + 1)]
    g["type_couvert"] = np.where(g.part_vegetation < 0.5, "bâti ou sol nu (indicatif)", "végétation")
    g["methode"] = "auto : ExG, top-hat, partage des eaux (scripts/demo_parcelles.py, méthode d'El Oro)"
    g = g[["parcelle_id", "surface_ha", "part_vegetation", "exg_median", "texture_exg", "texture_fine", "type_couvert", "methode", "lab", "geometry"]]
    g.drop(columns="lab").to_crs("EPSG:4326").to_file(sortie / "parcelles_auto.geojson", driver="GeoJSON")
    g.drop(columns="lab").to_file(sortie / "parcelles_auto_utm.geojson", driver="GeoJSON")

    # vue de contrôle
    img = np.moveaxis(a, 0, -1).clip(0, 255).astype("uint8").copy()
    img[~valide] = 255
    vue = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    inv = ~t
    for _, r in g.iterrows():
        polys = [r.geometry] if r.geometry.geom_type == "Polygon" else list(r.geometry.geoms)
        for p in polys:
            pts = np.array([inv * xy for xy in p.exterior.coords], np.int32)
            cv2.polylines(vue, [pts], True, (0, 255, 255), 2)
        cx, cy = inv * (r.geometry.representative_point().x, r.geometry.representative_point().y)
        txt = f"{r.parcelle_id} {r.surface_ha:.1f}ha"
        cv2.putText(vue, txt, (int(cx) - 40, int(cy)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(vue, txt, (int(cx) - 40, int(cy)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(str(sortie / "parcelles_auto.png"), vue)
    (sortie / "explo").mkdir(exist_ok=True)
    cv2.imwrite(str(sortie / "explo" / "force_limite.png"), (f * 255).astype("uint8"))

    resume = dict(ortho=Path(args.ortho).name, resolution_m=round(px, 3), surface_imagee_ha=round(valide.sum() * px * px / 1e4, 2),
                  germes=int(n_germes), parcelles=len(g), surface_parcelles_ha=round(float(g.surface_ha.sum()), 2),
                  reglages=vars(args), duree_s=round(time.time() - debut, 1))
    (sortie / "parcelles_auto_resume.json").write_text(json.dumps(resume, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resume, ensure_ascii=False))
    print(g.drop(columns=["geometry", "methode", "lab"]).to_string(index=False))


if __name__ == "__main__":
    main()
