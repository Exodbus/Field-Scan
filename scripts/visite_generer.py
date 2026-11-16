#!/usr/bin/env python3
"""Prépare les données de la visite 3D (out/visite_parcelle/) : pieds.json et la mini-carte.

Deux sources possibles :

  A. La scène du rendu Blender (défaut) : plants.csv, donnees_rendu.json, tuile.png et arbres_photo.csv d'un
     dossier écrit par scripts/rendu_preparer.py et scripts/rendu_arbres.py (défaut : out/rendu_blender/v4).

        PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/visite_generer.py

  B. Les sorties de run.py pour une autre exploitation :
       - pieds.geojson (module comptage) : un point par pied détecté, avec parcelle_id et score ;
       - bulletin.csv : médiane ExG de chaque parcelle (colonne vigueur_drone_exg_med) ;
       - facultatif, dans le même dossier que bulletin.csv : alertes.geojson (zones d'alerte) et
         cartes/drone_exg_<parcelle>.tif (carte ExG du module vigueur), lue au centre de chaque pied ;
       - facultatif : --ortho, l'orthomosaïque, pour la mini-carte (sinon une carte simple est dessinée).

        PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/visite_generer.py \
            --pieds resultats/pieds.geojson --bulletin resultats/bulletin.csv --parcelle "Nom de la parcelle" \
            --ortho "orthos/Nom de la parcelle RGB.tif" --out out/visite_autre

     Puis la scène : blender.exe -b --factory-startup -t 2 -P scripts/visite_exporter_blender.py -- --dossier out/visite_autre
     et copier index.html de out/visite_parcelle/ dans le nouveau dossier.

Ce qui est réel : la position de chaque pied (détecteur de comptage), son score, l'ExG lu sur la carte de la chaîne,
l'écart à la médiane de la parcelle et la zone d'alerte. Ce qui est illustratif et seulement tiré au hasard ici :
la forme (une des 48 formes de la v4), l'orientation et l'échelle de chaque bananier. Le tirage reprend exactement
celui de scripts/blender_scene.py (graine 1000 + identifiant), si bien qu'un pied a la même forme que dans les
rendus v4.

Repère : mètres, origine au centre de l'emprise, x vers l'est, y vers le nord (même repère que plants.csv).
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

N_FORMES = 48                          # formes de bananiers de la v4 (scripts/blender_scene.py, N_TYPES)
ECHELLE_SANTE = dict(bas=-0.05, haut=0.06, orange="#ef6c00", jaune="#e8c547", vert="#2e7d32")  # blender_scene.py
SEUILS_TEXTE = dict(plus_vert=0.02, moins_vert=-0.02)   # « plus vert / dans la moyenne / moins vert que la parcelle »
COTE_MINICARTE = 1024                  # pixels


def _flottant(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if x != x else x


def tirer_formes(pieds):
    """Forme, orientation et échelle de chaque pied, tirées comme dans scripts/blender_scene.py (construire) :
    graine 1000 + id ; échelle selon la distance au plus proche voisin, puis type, azimut, étirement vertical."""
    xy = np.array([[p["x"], p["y"]] for p in pieds], float)
    if len(xy) > 1:
        voisin = np.full(len(xy), 99.0)
        for i in range(0, len(xy), 2000):                          # par blocs (sans scipy)
            d = np.linalg.norm(xy[i:i + 2000, None] - xy[None], axis=2)
            d[np.arange(d.shape[0]), np.arange(i, i + d.shape[0])] = 99.0
            voisin[i:i + 2000] = d.min(1)
    else:
        voisin = np.full(len(xy), 3.0)
    for p, v in zip(pieds, voisin):
        rng = np.random.default_rng(1000 + int(p["id"]))
        s = float(np.clip(0.78 + 0.12 * (v - 1.5), 0.8, 1.05) * rng.uniform(0.95, 1.05))
        p["forme"] = int(rng.integers(N_FORMES))
        p["rotation"] = round(float(rng.uniform(0, 2 * math.pi)), 4)
        p["echelle"] = [round(s, 4), round(s, 4), round(s * float(rng.uniform(0.95, 1.05)), 4)]
        p["voisin_m"] = round(float(v), 2)


# --------------------------------------------------------------------------------------- source A : scène Blender
def depuis_scene(donnees, out):
    info = json.loads((donnees / "donnees_rendu.json").read_text(encoding="utf-8"))
    res = info["resolution_m"]
    demi = info["cote_px"][0] * res / 2
    pieds = []
    with open(donnees / "plants.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pieds.append(dict(id=int(r["id"]), x=float(r["x_m"]), y=float(r["y_m"]), score=_flottant(r["score"]),
                              exg=_flottant(r["exg"]), ecart=_flottant(r["exg_ecart_parcelle"]),
                              zone_alerte=r["dans_zone_alerte"].strip().lower() == "true"))
    arbres = []
    if (donnees / "arbres_photo.csv").exists():
        with open(donnees / "arbres_photo.csv", encoding="utf-8") as f:
            arbres = [dict(x=float(r["x_m"]), y=float(r["y_m"]), rayon=float(r["rayon_m"]),
                           hauteur=float(r["hauteur_m"])) for r in csv.DictReader(f)]
    # mini-carte : la mosaïque réelle (tuile.png couvre exactement [-demi, demi] en x et en y, nord en haut)
    img = Image.open(donnees / "tuile.png").convert("RGB")
    img.resize((COTE_MINICARTE, COTE_MINICARTE), Image.LANCZOS).save(out / "minicarte.jpg", quality=86)
    vig = info.get("vigueur", {})
    meta = dict(site=info.get("site", ""), parcelle=vig.get("parcelle", info.get("site", "")),
                source=dict(type="scene_rendu", dossier=str(donnees.relative_to(RACINE)).replace("\\", "/")
                            if donnees.is_relative_to(RACINE) else str(donnees),
                            detecteur=info.get("detecteur", {}).get("modele"),
                            seuil=info.get("detecteur", {}).get("seuil"),
                            vigueur=vig.get("source"), tuiles=info.get("tuiles"), partie=info.get("partie")),
                exg_mediane_parcelle=vig.get("exg_mediane_parcelle"), niveau_parcelle=vig.get("niveau_parcelle"),
                score_parcelle=vig.get("score_parcelle"),
                alertes_touchant_l_emprise=vig.get("alertes_touchant_la_tuile", []),
                minicarte=dict(image="minicarte.jpg", xmin=-demi, xmax=demi, ymin=-demi, ymax=demi,
                               legende="mosaïque de drone réelle (9 tuiles, 5 cm/px)"))
    return pieds, arbres, demi, meta


# --------------------------------------------------------------------------------------- source B : sorties de run.py
def depuis_run(a, out):
    import geopandas as gpd
    import pandas as pd
    import rasterio
    from shapely.geometry import Point

    g = gpd.read_file(a.pieds)
    if a.parcelle:
        g = g[g["parcelle_id"] == a.parcelle]
    elif "parcelle_id" in g and g["parcelle_id"].nunique() > 1:
        raise SystemExit(f"pieds.geojson contient plusieurs parcelles {sorted(g['parcelle_id'].unique())[:8]} : "
                         "choisir avec --parcelle")
    if len(g) == 0:
        raise SystemExit("aucun pied pour cette parcelle")
    parcelle = a.parcelle or (str(g["parcelle_id"].iloc[0]) if "parcelle_id" in g else "")
    utm = g.estimate_utm_crs()
    gu = g.to_crs(utm)
    E, N = gu.geometry.x.to_numpy(), gu.geometry.y.to_numpy()
    cx, cy = (E.min() + E.max()) / 2, (N.min() + N.max()) / 2
    demi = max(E.max() - E.min(), N.max() - N.min()) / 2 + 2.0    # 2 m de marge autour des pieds
    # vigueur : médiane ExG de la parcelle (bulletin), carte ExG de la chaîne lue au centre de chaque pied
    med, exg, zones = None, np.full(len(gu), np.nan), {}
    meta_b = {}
    if a.bulletin:
        bul = pd.read_csv(a.bulletin)
        ligne = bul[bul["parcelle_id"] == parcelle]
        if len(ligne) and "vigueur_drone_exg_med" in ligne:
            med = _flottant(ligne["vigueur_drone_exg_med"].iloc[0])
        if len(ligne):
            meta_b = dict(niveau_parcelle=str(ligne["niveau"].iloc[0]) if "niveau" in ligne else None,
                          score_parcelle=_flottant(ligne["score"].iloc[0]) if "score" in ligne else None)
        dossier = Path(a.bulletin).parent
        carte = Path(a.carte_exg) if a.carte_exg else dossier / "cartes" / f"drone_exg_{parcelle}.tif"
        if carte.exists():
            with rasterio.open(carte) as c:
                pts = gu.to_crs(c.crs)
                exg = np.array([v[0] for v in c.sample(list(zip(pts.geometry.x, pts.geometry.y)))], "float64")
                if c.nodata is not None:
                    exg[exg == c.nodata] = np.nan
        else:
            print(f"carte ExG absente ({carte}) : vigueur non renseignée")
        fa = dossier / "alertes.geojson"
        if fa.exists():
            al = gpd.read_file(fa)
            if len(al):
                al = al[(al["parcelle_id"] == parcelle) & al["type"].astype(str).str.startswith("zone")].to_crs(utm)
                zones = {str(r["id"]): r.geometry for _, r in al.iterrows()}
    pieds = []
    for k, (e, n) in enumerate(zip(E, N)):
        pt = Point(e, n)
        dans = [zid for zid, geom in zones.items() if geom is not None and geom.contains(pt)]
        x = _flottant(exg[k])
        pieds.append(dict(id=k, x=round(e - cx, 3), y=round(n - cy, 3),
                          score=_flottant(gu["score"].iloc[k]) if "score" in gu else None,
                          exg=round(x, 4) if x is not None else None,
                          ecart=round(x - med, 4) if (x is not None and med is not None) else None,
                          zone_alerte=dans[0] if dans else False))
    # mini-carte : l'orthomosaïque sur l'emprise, sinon une carte simple (fond clair et points)
    ok = False
    if a.ortho:
        from rasterio.enums import Resampling
        from rasterio.windows import from_bounds
        with rasterio.open(a.ortho) as src:
            from rasterio.warp import transform_bounds
            b = transform_bounds(utm, src.crs, cx - demi, cy - demi, cx + demi, cy + demi)
            w = from_bounds(*b, transform=src.transform)
            rgb = src.read([1, 2, 3], window=w, out_shape=(3, COTE_MINICARTE, COTE_MINICARTE), boundless=True,
                           fill_value=0, resampling=Resampling.bilinear)
            Image.fromarray(np.moveaxis(rgb, 0, -1).astype("uint8")).save(out / "minicarte.jpg", quality=86)
            ok = True
    if not ok:
        img = Image.new("RGB", (COTE_MINICARTE, COTE_MINICARTE), (214, 205, 180))
        d = ImageDraw.Draw(img)
        for p in pieds:
            u = (p["x"] + demi) / (2 * demi) * COTE_MINICARTE
            v = (demi - p["y"]) / (2 * demi) * COTE_MINICARTE
            d.ellipse([u - 5, v - 5, u + 5, v + 5], fill=(46, 125, 50))
        img.save(out / "minicarte.jpg", quality=86)
    meta = dict(site=parcelle, parcelle=parcelle,
                source=dict(type="run.py", pieds=str(a.pieds), bulletin=str(a.bulletin) if a.bulletin else None,
                            crs=str(utm), centre_utm=[round(cx, 2), round(cy, 2)]),
                exg_mediane_parcelle=med, alertes_touchant_l_emprise=sorted(zones), **meta_b,
                minicarte=dict(image="minicarte.jpg", xmin=-demi, xmax=demi, ymin=-demi, ymax=demi,
                               legende="orthomosaïque" if ok else "carte simple (pas d'orthomosaïque fournie)"))
    arbres = []
    if a.arbres:                                                    # arbres_photo.csv éventuel (même repère)
        with open(a.arbres, encoding="utf-8") as f:
            arbres = [dict(x=float(r["x_m"]), y=float(r["y_m"]), rayon=float(r["rayon_m"]),
                           hauteur=float(r["hauteur_m"])) for r in csv.DictReader(f)]
    return pieds, arbres, demi, meta


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--donnees", default=str(RACINE / "out/rendu_blender/v4"), help="source A : dossier de la scène")
    ap.add_argument("--pieds", help="source B : pieds.geojson de run.py")
    ap.add_argument("--bulletin", help="source B : bulletin.csv de run.py (même dossier : alertes.geojson, cartes/)")
    ap.add_argument("--parcelle", help="source B : parcelle_id à visiter")
    ap.add_argument("--carte-exg", help="source B : carte ExG (défaut : <dossier du bulletin>/cartes/drone_exg_<parcelle>.tif)")
    ap.add_argument("--ortho", help="source B : orthomosaïque pour la mini-carte")
    ap.add_argument("--arbres", help="source B : arbres_photo.csv (facultatif)")
    ap.add_argument("--out", default=str(RACINE / "out/visite_parcelle"))
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if a.pieds:
        pieds, arbres, demi, meta = depuis_run(a, out)
    else:
        pieds, arbres, demi, meta = depuis_scene(Path(a.donnees).resolve(), out)
    tirer_formes(pieds)
    # garder l'association pied -> instance du glb si elle existe déjà (écrite par visite_exporter_blender.py)
    ancien = out / "pieds.json"
    if ancien.exists():
        try:
            prec = {p["id"]: p.get("instance") for p in json.loads(ancien.read_text(encoding="utf-8"))["pieds"]}
            for p in pieds:
                if prec.get(p["id"]) and prec[p["id"]].get("forme") == p["forme"]:
                    p["instance"] = prec[p["id"]]
        except (KeyError, ValueError):
            pass
    doc = dict(
        version=1,
        description="Pieds de la visite 3D. Réel : x, y (m), score, exg, ecart, zone_alerte. Illustratif : forme, "
                    "rotation, echelle (tirées comme dans scripts/blender_scene.py). instance : nœud et indice de "
                    "l'instance dans scene.glb (écrit par scripts/visite_exporter_blender.py).",
        repere="mètres, origine au centre de l'emprise, x vers l'est, y vers le nord ; dans three.js : (x, 0, -y)",
        demi_cote_m=round(demi, 3),
        limites_marche_m=round(demi + 8.0, 3),
        echelle_sante=ECHELLE_SANTE, seuils_texte=SEUILS_TEXTE, n_formes=N_FORMES,
        **meta, arbres=arbres, pieds=pieds)
    (out / "pieds.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    ec = [p["ecart"] for p in pieds if p["ecart"] is not None]
    print(f"{len(pieds)} pieds, {len(arbres)} arbres, demi-côté {demi:.2f} m -> {out / 'pieds.json'}")
    if ec:
        print(f"écart ExG : {min(ec):+.3f} à {max(ec):+.3f} ; plus vert {sum(e > SEUILS_TEXTE['plus_vert'] for e in ec)}, "
              f"moins vert {sum(e < SEUILS_TEXTE['moins_vert'] for e in ec)}, "
              f"zone d'alerte {sum(bool(p['zone_alerte']) for p in pieds)}")


if __name__ == "__main__":
    main()
