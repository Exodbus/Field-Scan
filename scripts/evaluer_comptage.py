#!/usr/bin/env python3
"""Évaluation d'un comptage de pieds contre une référence complète, zone par zone.

Les détections (d'un modèle, ou les annotations de ReforesTree) sont appariées
aux pieds de la référence manuelle : un appariement un-à-un, qui minimise la
distance totale, et n'accepte que les paires à moins de --rayon mètres (1 m dans
la consigne). On en tire, pour chaque zone :
  - VP : détections appariées à un vrai pied ;
  - FN : pieds de la référence sans détection (oubliés) ;
  - FP : détections sans pied de la référence (fausses détections) ;
  - précision, rappel, F1, et erreur de comptage (détections - pieds).

Les points de référence de type 'incertain' ne comptent ni comme pieds à trouver,
ni comme fausses détections : une détection appariée à un point incertain est
simplement ignorée.

Seules les détections dont le centre est dans une zone sont évaluées.

Exemples :
    # Complétude de ReforesTree par rapport à la référence manuelle
    python scripts/evaluer_comptage.py --detections data/drone/reforestree/prepare/points_pieds.geojson \
        --filtre-banane --out out/comptage/reforestree_vs_manuel
    # Évaluation d'un détecteur
    python scripts/evaluer_comptage.py --detections out/comptage/baseline/detections.geojson \
        --out out/comptage/baseline/evaluation
"""
import argparse
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

CRS_METRIQUE = "EPSG:32717"
TYPES_CERTAINS = {"mere", "rejet"}


def apparier(det_xy, ref_xy, rayon):
    """Appariement un-à-un à distance totale minimale, limité à `rayon`. Retourne [(i_det, j_ref, distance)]."""
    if len(det_xy) == 0 or len(ref_xy) == 0:
        return []
    d = cdist(det_xy, ref_xy)
    cout = np.where(d <= rayon, d, 1e6)  # une paire trop éloignée est rendue impossible
    lignes, colonnes = linear_sum_assignment(cout)
    return [(i, j, float(d[i, j])) for i, j in zip(lignes, colonnes) if d[i, j] <= rayon]


def scores(vp, fp, fn):
    p = vp / (vp + fp) if vp + fp else np.nan
    r = vp / (vp + fn) if vp + fn else np.nan
    f1 = 2 * p * r / (p + r) if p and r and not np.isnan(p) and not np.isnan(r) else (0.0 if vp == 0 and (fp or fn) else np.nan)
    return p, r, f1


def evaluer_zone(det, ref, rayon):
    """Évalue une zone. `det` et `ref` sont des GeoDataFrame déjà restreints à la zone."""
    certains = ref[ref["type"].isin(TYPES_CERTAINS)]
    incertains = ref[~ref["type"].isin(TYPES_CERTAINS)]
    det_xy = np.c_[det.geometry.x, det.geometry.y] if len(det) else np.empty((0, 2))
    ref_xy = np.c_[certains.geometry.x, certains.geometry.y] if len(certains) else np.empty((0, 2))

    paires = apparier(det_xy, ref_xy, rayon)
    det_vp = {i for i, _, _ in paires}
    ref_vp = {j for _, j, _ in paires}

    # Détections restantes proches d'un point incertain : ignorées
    restantes = [i for i in range(len(det)) if i not in det_vp]
    ignorees = set()
    if len(incertains) and restantes:
        inc_xy = np.c_[incertains.geometry.x, incertains.geometry.y]
        for i, _, _ in apparier(det_xy[restantes], inc_xy, rayon):
            ignorees.add(restantes[i])

    statut_det = ["vrai_positif" if i in det_vp else "ignore_incertain" if i in ignorees else "faux_positif"
                  for i in range(len(det))]
    statut_ref = ["trouve" if j in ref_vp else "oublie" for j in range(len(certains))]
    vp, fp, fn = len(paires), statut_det.count("faux_positif"), statut_ref.count("oublie")
    p, r, f1 = scores(vp, fp, fn)
    rejets = certains["type"].to_numpy() == "rejet"
    res = dict(pieds_reference=len(certains), incertains=len(incertains),
               detections=len(det) - len(ignorees), vrais_positifs=vp, faux_positifs=fp, oublies=fn,
               precision=p, rappel=r, f1=f1,
               erreur_comptage=(len(det) - len(ignorees)) - len(certains),
               distance_mediane_m=float(np.median([d for _, _, d in paires])) if paires else np.nan,
               rejets_reference=int(rejets.sum()),
               rejets_trouves=int(sum(1 for j in ref_vp if rejets[j])))
    return res, statut_det, statut_ref


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--detections", required=True, help="points détectés (GeoJSON)")
    ap.add_argument("--reference", default="data/drone/reforestree/prepare/annotations_manuelles.geojson")
    ap.add_argument("--zones", default="data/drone/reforestree/prepare/zones_annotation.geojson")
    ap.add_argument("--out", required=True, help="dossier de sortie")
    ap.add_argument("--rayon", type=float, default=1.0, help="distance maximale d'appariement en mètres (défaut 1)")
    ap.add_argument("--filtre-banane", action="store_true",
                    help="ne garder que les détections dont is_banana est vrai (annotations ReforesTree)")
    ap.add_argument("--zones-evaluees", nargs="*",
                    help="ne garder que ces zones (défaut : les zones qui contiennent au moins un point de référence)")
    args = ap.parse_args(argv)

    det = gpd.read_file(args.detections).to_crs(CRS_METRIQUE)
    ref = gpd.read_file(args.reference).to_crs(CRS_METRIQUE)
    zones = gpd.read_file(args.zones).to_crs(CRS_METRIQUE)
    if "type" not in ref.columns:
        raise SystemExit("La référence doit avoir un champ 'type' (mere, rejet, incertain).")
    ref["type"] = ref["type"].astype(str).str.strip().str.lower()
    if args.filtre_banane:
        det = det[det["is_banana"].astype(str).str.strip().str.lower().isin(["true", "1", "1.0"])]

    a_evaluer = args.zones_evaluees or sorted(ref["zone_id"].dropna().unique())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    lignes, det_sorties, ref_sorties = [], [], []
    for _, z in zones[zones.zone_id.isin(a_evaluer)].iterrows():
        d = det[det.within(z.geometry)].copy()
        r = ref[(ref.zone_id == z.zone_id) & ref.within(z.geometry)].copy()
        hors = int(((ref.zone_id == z.zone_id) & ~ref.within(z.geometry)).sum())
        res, statut_det, statut_ref = evaluer_zone(d.reset_index(drop=True), r.reset_index(drop=True), args.rayon)
        lignes.append(dict(zone_id=z.zone_id, site=z.get("site"), split=z.get("split"),
                           points_reference_hors_zone=hors, **res))
        d["statut"], d["zone_id"] = statut_det, z.zone_id
        rc = r[r["type"].isin(TYPES_CERTAINS)].copy()
        rc["statut"] = statut_ref
        det_sorties.append(d[["zone_id", "statut", "geometry"]])
        ref_sorties.append(rc[["zone_id", "type", "statut", "geometry"]])

    tab = pd.DataFrame(lignes)
    tot = tab[["pieds_reference", "incertains", "detections", "vrais_positifs", "faux_positifs", "oublies",
               "rejets_reference", "rejets_trouves", "points_reference_hors_zone"]].sum()
    p, r, f1 = scores(tot.vrais_positifs, tot.faux_positifs, tot.oublies)
    total = dict(zone_id="TOTAL", **tot.to_dict(), precision=p, rappel=r, f1=f1,
                 erreur_comptage=int(tot.detections - tot.pieds_reference))
    tab = pd.concat([tab, pd.DataFrame([total])], ignore_index=True)
    tab.to_csv(out / "evaluation_zones.csv", index=False)
    if det_sorties:
        pd.concat(det_sorties).to_file(out / "detections_statut.geojson", driver="GeoJSON")
        pd.concat(ref_sorties).to_file(out / "reference_statut.geojson", driver="GeoJSON")
    (out / "parametres.json").write_text(json.dumps(dict(
        detections=args.detections, reference=args.reference, zones=args.zones, rayon_m=args.rayon,
        filtre_banane=args.filtre_banane, zones_evaluees=a_evaluer), indent=2, ensure_ascii=False), encoding="utf-8")

    affiche = tab[["zone_id", "pieds_reference", "detections", "vrais_positifs", "faux_positifs", "oublies",
                   "precision", "rappel", "f1", "erreur_comptage", "rejets_reference", "rejets_trouves"]]
    print(affiche.round(3).to_string(index=False))
    if tot.points_reference_hors_zone:
        print(f"\nAttention : {int(tot.points_reference_hors_zone)} point(s) de référence hors de leur carré (non comptés).")
    print(f"\nRésultats dans {out}/")


if __name__ == "__main__":
    main()
