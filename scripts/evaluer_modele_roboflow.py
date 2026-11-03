#!/usr/bin/env python3
"""Étalon externe : le modèle hébergé de Roboflow (Plants-bana) mesuré sur nos carrés de référence.

Ce modèle ne sert qu'à comparer (il tourne sur les serveurs de Roboflow : il n'entre pas dans la chaîne).
Comparaison loyale :
  - même mesure que nos modèles : centres des boîtes appariés aux points de référence à moins de 1 m
    (fonction evaluer_zone de scripts/evaluer_comptage.py) ;
  - échelle du modèle : les carrés sont lus à --gsd-cm (6,7 cm : une couronne adulte de 3 m ≈ 45 pixels, la taille
    médiane des boîtes de Plants-bana), en tuiles de 640 pixels qui se recouvrent ; doublons fusionnés (NMS) ;
  - seuil de confiance choisi sur la validation (--zones-validation, MM1 et MM2), puis appliqué tel quel au test.
Seules les boîtes de la classe banane sont gardées. Chaque réponse est mise en cache (une tuile n'est envoyée qu'une
fois). La clé est lue dans la variable d'environnement ROBOFLOW_API_KEY, jamais écrite dans un fichier.

Exemple :
    $env:ROBOFLOW_API_KEY = "..."
    python scripts/evaluer_modele_roboflow.py --zones-validation MM1 MM2 --zones-test CG1 CG2 CG3 CG4 CG5 CG6 CG7 CG8 CG9
"""
import argparse
import base64
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
from fieldscan import drone  # noqa: E402
from evaluer_comptage import CRS_METRIQUE, evaluer_zone, scores  # noqa: E402
from evaluer_comptage import definir_types_certains  # noqa: E402


def positions(n, taille, pas):
    if n <= taille:
        return [0]
    p = list(range(0, n - taille + 1, pas))
    return p if p[-1] == n - taille else p + [n - taille]


def nms(boites, notes, iou_max=0.3):
    """Suppression des doublons : on garde la boîte la plus sûre, on retire celles qui la recouvrent trop."""
    b, ordre, garde = np.asarray(boites, float), np.argsort(notes)[::-1], []
    aires = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    while len(ordre):
        i, ordre = ordre[0], ordre[1:]
        garde.append(i)
        xx0, yy0 = np.maximum(b[i, 0], b[ordre, 0]), np.maximum(b[i, 1], b[ordre, 1])
        xx1, yy1 = np.minimum(b[i, 2], b[ordre, 2]), np.minimum(b[i, 3], b[ordre, 3])
        inter = np.clip(xx1 - xx0, 0, None) * np.clip(yy1 - yy0, 0, None)
        ordre = ordre[inter / (aires[i] + aires[ordre] - inter) <= iou_max]
    return np.array(garde, int)


def interroger(image, modele, cle, cache, point_acces, confiance_pct):
    """Prédictions du modèle hébergé pour une tuile (réponse mise en cache sur disque)."""
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    tampon = io.BytesIO(); image.save(tampon, "JPEG", quality=95)
    corps = base64.b64encode(tampon.getvalue())
    url = f"{point_acces}/{modele}?" + urllib.parse.urlencode(dict(api_key=cle, confidence=confiance_pct, overlap=30, format="json"))
    for essai in range(3):
        try:
            req = urllib.request.Request(url, data=corps, headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=120) as r:
                reponse = json.loads(r.read().decode("utf-8"))
            cache.write_text(json.dumps(reponse), encoding="utf-8")
            return reponse
        except urllib.error.HTTPError as e:
            message = e.read().decode("utf-8", "ignore")[:300]
            if e.code in (401, 403):
                raise SystemExit(f"Accès refusé par Roboflow ({e.code}) : vérifie ROBOFLOW_API_KEY. {message}")
            if e.code == 404:
                raise SystemExit(f"Modèle introuvable ({modele}) à {point_acces} : {message}")
            print(f"  erreur {e.code}, nouvel essai : {message}")
        except Exception as e:  # réseau
            print(f"  erreur réseau ({e}), nouvel essai")
        time.sleep(3 * (essai + 1))
    raise SystemExit("Roboflow ne répond pas")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modele", default="plants-bana/3")
    ap.add_argument("--point-acces", default="https://detect.roboflow.com")
    ap.add_argument("--zones", default="data/drone/reforestree/prepare/zones_annotation.geojson")
    ap.add_argument("--reference", default="data/drone/reforestree/prepare/annotations_manuelles.geojson")
    ap.add_argument("--orthos", default="data/drone/reforestree/wwf_ecuador/RGB Orthomosaics")
    ap.add_argument("--zones-validation", nargs="+", default=["MM1", "MM2"])
    ap.add_argument("--zones-test", nargs="+", default=[f"CG{k}" for k in range(1, 10)])
    ap.add_argument("--gsd-cm", type=float, default=6.7)
    ap.add_argument("--tuile", type=int, default=640)
    ap.add_argument("--recouvrement", type=float, default=0.2)
    ap.add_argument("--marge", type=float, default=3.0)
    ap.add_argument("--confiance-min-pct", type=int, default=5, help="confiance minimale demandée à l'API, en %% (défaut 5)")
    ap.add_argument("--seuils", type=float, nargs="+", default=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7])
    ap.add_argument("--meres-seules", action="store_true", help="pieds mères seuls : rejets traités comme incertains")
    ap.add_argument("--rayon", type=float, default=1.0)
    ap.add_argument("--out", default="out/comptage/roboflow_plants_bana")
    args = ap.parse_args(argv)
    definir_types_certains(args.meres_seules)
    cle = os.environ.get("ROBOFLOW_API_KEY")
    if not cle:
        raise SystemExit("Définis d'abord la clé : $env:ROBOFLOW_API_KEY = \"...\"")
    out = Path(args.out); (out / "cache").mkdir(parents=True, exist_ok=True)
    zones = gpd.read_file(args.zones).to_crs(CRS_METRIQUE)
    ref = gpd.read_file(args.reference).to_crs(CRS_METRIQUE)
    brut = ref["type"].astype(str).str.strip().str.lower().str.replace("è", "e", regex=False)
    vides = ref["type"].isna() | brut.isin(["", "none", "nan", "null"])
    ref["type"] = brut.where(~vides, "mere")
    manquantes = sorted(set(args.zones_validation + args.zones_test) - set(zones.zone_id))
    if manquantes:
        raise SystemExit(f"Zone(s) absente(s) de {args.zones} : {manquantes}. Ajoute-les d'abord au fichier des zones.")
    res = args.gsd_cm / 100
    pas = int(args.tuile * (1 - args.recouvrement))
    detections, appels = [], 0
    for zid in args.zones_validation + args.zones_test:
        z = zones[zones.zone_id == zid]
        if z.empty:
            print(f"{zid} : zone introuvable"); continue
        site = z.iloc[0]["site"]
        x0, y0, x1, y1 = z.geometry.iloc[0].buffer(args.marge).bounds
        rgb, valide, t = drone.lire_fenetre(str(Path(args.orthos) / f"{site} RGB.tif"), CRS_METRIQUE, (x0, y0, x1, y1), res)
        img = np.moveaxis(np.clip(rgb, 0, 255).astype("uint8"), 0, -1)
        img[~valide] = 0
        h, l = valide.shape
        boites, notes = [], []
        for yt in positions(h, args.tuile, pas):
            for xt in positions(l, args.tuile, pas):
                tuile = Image.fromarray(img[yt:yt + args.tuile, xt:xt + args.tuile])
                cache = out / "cache" / f"{zid}_{args.gsd_cm}_{yt}_{xt}.json"
                appels += 0 if cache.exists() else 1
                rep = interroger(tuile, args.modele, cle, cache, args.point_acces, args.confiance_min_pct)
                for p in rep.get("predictions", []):
                    if "banana" not in str(p.get("class", "")).lower():
                        continue
                    cx, cy, w_, h_ = p["x"] + xt, p["y"] + yt, p["width"], p["height"]
                    boites.append([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2]); notes.append(float(p["confidence"]))
        if boites:
            garde = nms(boites, notes, 0.3)
            b, s = np.asarray(boites, float)[garde], np.asarray(notes, float)[garde]
            cx, cy = (b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2
            d = gpd.GeoDataFrame({"zone_id": zid, "score": s}, geometry=gpd.points_from_xy(t.c + cx * res, t.f - cy * res), crs=CRS_METRIQUE)
            detections.append(d[d.within(z.geometry.iloc[0])])
        print(f"{zid} ({site}) : {len(boites)} boîtes « banana » avant fusion, "
              f"{len(detections[-1]) if boites else 0} dans le carré après fusion")
    det = pd.concat(detections, ignore_index=True) if detections else gpd.GeoDataFrame(columns=["zone_id", "score", "geometry"])
    gpd.GeoDataFrame(det, geometry="geometry", crs=CRS_METRIQUE).to_file(out / "detections.geojson", driver="GeoJSON")
    if len(det):
        print(f"Confiances renvoyées : de {det.score.min():.2f} à {det.score.max():.2f} ({appels} appel(s) à l'API cette fois)")

    lignes = []
    for seuil in args.seuils:
        for zid in args.zones_validation + args.zones_test:
            z = zones[zones.zone_id == zid]
            if z.empty:
                continue
            dz = det[(det.zone_id == zid) & (det.score >= seuil)].reset_index(drop=True)
            rz = ref[(ref.zone_id == zid) & ref.within(z.geometry.iloc[0])].reset_index(drop=True)
            r_, _, _ = evaluer_zone(dz, rz, args.rayon)
            lignes.append(dict(seuil=seuil, zone_id=zid, **{k: r_[k] for k in ("pieds_reference", "detections", "vrais_positifs",
                                                                                 "faux_positifs", "oublies")}))
    tab = pd.DataFrame(lignes); tab.to_csv(out / "evaluation_zones.csv", index=False)

    def bilan(zs):
        t_ = tab[tab.zone_id.isin(zs)].groupby("seuil")[["pieds_reference", "detections", "vrais_positifs", "faux_positifs", "oublies"]].sum()
        sc = t_.apply(lambda r: pd.Series(scores(r.vrais_positifs, r.faux_positifs, r.oublies), index=["precision", "rappel", "f1"]), axis=1)
        t_ = t_.join(sc.round(3)); t_["erreur_comptage"] = t_.detections - t_.pieds_reference
        return t_
    val = bilan(args.zones_validation)
    print("\nValidation (" + ", ".join(args.zones_validation) + ") :\n" + val.to_string())
    seuil = float(val.f1.idxmax())
    print(f"\nSeuil retenu sur la validation : {seuil}")
    groupes = {"Test (" + ", ".join(args.zones_test) + ")": args.zones_test}
    if all(z in args.zones_test for z in ("CG1", "CG2", "CG3")):
        groupes = {"CG1-CG3": ["CG1", "CG2", "CG3"], "CG4-CG9": [z for z in args.zones_test if z not in ("CG1", "CG2", "CG3")],
                   "Total test": args.zones_test}
    for nom, zs in groupes.items():
        b_ = bilan(zs)
        print(f"\n{nom}, au seuil retenu ({seuil}) :\n" + b_.loc[[seuil]].to_string())
    print(f"\nCourbe complète (information) :\n" + bilan(args.zones_test).to_string())
    json.dump(dict(modele=args.modele, gsd_cm=args.gsd_cm, seuil_retenu=seuil, rayon_m=args.rayon,
                   remarque="étalon externe hébergé par Roboflow, hors chaîne"), open(out / "parametres.json", "w"), indent=2)


if __name__ == "__main__":
    main()
