#!/usr/bin/env python3
"""Détection des bananiers avec le modèle DeepForest affiné, sur processeur.

Pour chaque carré évalué :
  1. lecture de l'orthomosaïque autour du carré, rééchantillonnée à --resolution cm/pixel
     (la résolution d'entraînement : 10 cm) ;
  2. fenêtre glissante de --taille pixels (la taille des tuiles d'entraînement), avec
     --recouvrement ; prédiction du réseau sur chaque fenêtre ;
  3. fusion des boîtes en double entre fenêtres (suppression des non-maxima, --nms) ;
  4. seuil de score --seuil (choisi sur la validation pendant l'entraînement : 0,4) ;
  5. centre de chaque boîte -> point en EPSG:32717, puis évaluation contre la
     référence manuelle (evaluer_comptage.py, appariement à 1 m).
Le temps de calcul est mesuré et ramené à l'hectare (critère d'embarquabilité du sujet).

Comme pour les autres méthodes, plusieurs seuils ne sont permis que sur la validation.

Exemple :
    python scripts/detecter_deepforest.py --modele modeles/bananiers_deepforest.ckpt --out out/comptage/deepforest
"""
import argparse
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import torch
from rasterio.warp import transform as warp_transform
from torchvision.ops import nms

sys.path.insert(0, str(Path(__file__).resolve().parent))
from baseline_comptage import chemin_ortho, lire_fenetre  # noqa: E402
from evaluer_comptage import CRS_METRIQUE, evaluer_zone, scores  # noqa: E402
from preparer_deepforest import positions  # noqa: E402


def charger_modele(chemin):
    """Modèle vierge (configuration par défaut), puis chargement des seuls poids du fichier .ckpt.

    load_from_checkpoint reconstruirait le modèle avec la configuration enregistrée sur Colab,
    dont les chemins (/content/...) n'existent pas ici. On vérifie qu'aucun poids du réseau ne manque.
    """
    from deepforest import main as df_main
    m = df_main.deepforest()
    point = torch.load(chemin, map_location="cpu", weights_only=False)
    etat = point.get("state_dict", point)
    manquants, inattendus = m.load_state_dict(etat, strict=False)
    manquants_reseau = [k for k in manquants if k.startswith("model.")]
    inattendus_reseau = [k for k in inattendus if k.startswith("model.")]
    if manquants_reseau or inattendus_reseau:
        raise SystemExit(f"Poids incompatibles : {len(manquants_reseau)} manquants, {len(inattendus_reseau)} en trop "
                         f"(ex. {(manquants_reseau + inattendus_reseau)[:3]})")
    n = sum(1 for k in etat if k.startswith("model."))
    print(f"Modèle chargé : {n} tenseurs de poids du réseau, aucun manquant.")
    m.model.eval()
    return m


def predire_fenetre(m, rgb, valide, taille, recouvrement, iou_nms):
    """Boîtes (x0, y0, x1, y1) en pixels de la fenêtre, et leurs scores, sans seuil."""
    img = np.moveaxis(rgb, 0, -1) / 255.0
    img[~valide] = 0.0  # comme pour les tuiles d'entraînement
    h, l = valide.shape
    pas = max(1, int(taille * (1 - recouvrement)))
    boites, notes = [], []
    ancien = getattr(m.model, "score_thresh", None)
    m.model.score_thresh = 0.0
    with torch.no_grad():
        for y0 in positions(h, taille, pas):
            for x0 in positions(l, taille, pas):
                morceau = img[y0:y0 + taille, x0:x0 + taille]
                x = torch.tensor(np.ascontiguousarray(morceau), dtype=torch.float32).permute(2, 0, 1)
                o = m.model([x])[0]
                if len(o["boxes"]):
                    b = o["boxes"].numpy() + np.array([x0, y0, x0, y0])
                    boites.append(b)
                    notes.append(o["scores"].numpy())
    m.model.score_thresh = ancien
    if not boites:
        return np.empty((0, 4)), np.empty(0)
    b, s = np.concatenate(boites), np.concatenate(notes)
    garde = nms(torch.tensor(b, dtype=torch.float32), torch.tensor(s, dtype=torch.float32), iou_nms).numpy()
    return b[garde], s[garde]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modele", default="modeles/bananiers_deepforest.ckpt")
    ap.add_argument("--zip", default="data/drone/reforestree/reforesTree.zip")
    ap.add_argument("--orthos", default="data/drone/reforestree/wwf_ecuador/RGB Orthomosaics")
    ap.add_argument("--reference", default="data/drone/reforestree/prepare/annotations_manuelles.geojson")
    ap.add_argument("--zones", default="data/drone/reforestree/prepare/zones_annotation.geojson")
    ap.add_argument("--zones-evaluees", nargs="+", default=["MM1", "MM2"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--resolution", type=float, default=10.0, help="cm par pixel (défaut 10, celle de l'entraînement)")
    ap.add_argument("--taille", type=int, default=400, help="taille des fenêtres en pixels (défaut 400)")
    ap.add_argument("--recouvrement", type=float, default=0.25)
    ap.add_argument("--nms", type=float, default=0.3, help="seuil de recouvrement pour fusionner les doublons")
    ap.add_argument("--seuil", type=float, nargs="+", default=[0.4], help="seuil de score (défaut 0,4, choisi sur la validation)")
    ap.add_argument("--rayon", type=float, default=1.0)
    ap.add_argument("--marge", type=float, default=3.0)
    args = ap.parse_args(argv)

    zones = gpd.read_file(args.zones).to_crs(CRS_METRIQUE)
    zones = zones[zones.zone_id.isin(args.zones_evaluees)]
    if "split" in zones and (zones.split == "test").any() and len(args.seuil) > 1:
        raise SystemExit("Refus : un seul seuil, figé sur la validation, pour les carrés de test.")
    ref = gpd.read_file(args.reference).to_crs(CRS_METRIQUE)
    ref["type"] = ref["type"].astype(str).str.strip().str.lower()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    torch.set_grad_enabled(False)

    t_charge = time.time()
    m = charger_modele(args.modele)
    t_charge = time.time() - t_charge

    res_m = args.resolution / 100
    brutes, temps = {}, {}
    for _, z in zones.iterrows():
        rgb, valide, t, crs = lire_fenetre(chemin_ortho(z.site, args.orthos, args.zip), z.geometry, args.marge, res_m)
        debut = time.time()
        b, s = predire_fenetre(m, rgb, valide, args.taille, args.recouvrement, args.nms)
        temps[z.zone_id] = (time.time() - debut, valide.sum() * res_m ** 2 / 1e4)
        cx, cy = (b[:, 0] + b[:, 2]) / 2 + 0.5, (b[:, 1] + b[:, 3]) / 2 + 0.5
        xs, ys = t * (cx, cy)
        X, Y = warp_transform(crs, CRS_METRIQUE, np.atleast_1d(xs).tolist(), np.atleast_1d(ys).tolist()) if len(b) else ([], [])
        brutes[z.zone_id] = (np.c_[X, Y] if len(b) else np.empty((0, 2)), s, z)

    lignes, detections = [], []
    for seuil in args.seuil:
        tot = dict(vp=0, fp=0, fn=0, det=0, pieds=0, rejets=0, rejets_trouves=0)
        for k, (xy, s, z) in brutes.items():
            garde = s > seuil
            det = gpd.GeoDataFrame({"score": s[garde]}, geometry=gpd.points_from_xy(xy[garde, 0], xy[garde, 1]),
                                   crs=CRS_METRIQUE)
            det = det[det.within(z.geometry)].reset_index(drop=True)
            r = ref[(ref.zone_id == k) & ref.within(z.geometry)].reset_index(drop=True)
            res, statut, _ = evaluer_zone(det, r, args.rayon)
            for a, b_ in (("vp", "vrais_positifs"), ("fp", "faux_positifs"), ("fn", "oublies"), ("det", "detections"),
                          ("pieds", "pieds_reference"), ("rejets", "rejets_reference"), ("rejets_trouves", "rejets_trouves")):
                tot[a] += res[b_]
            p, rr, f1 = res["precision"], res["rappel"], res["f1"]
            lignes.append(dict(seuil=seuil, zone_id=k, pieds_reference=res["pieds_reference"], detections=res["detections"],
                               vrais_positifs=res["vrais_positifs"], faux_positifs=res["faux_positifs"],
                               oublies=res["oublies"], precision=p, rappel=rr, f1=f1,
                               erreur_comptage=res["erreur_comptage"], rejets_reference=res["rejets_reference"],
                               rejets_trouves=res["rejets_trouves"]))
            if seuil == args.seuil[0]:
                det["zone_id"], det["statut"] = k, statut
                detections.append(det)
        p, rr, f1 = scores(tot["vp"], tot["fp"], tot["fn"])
        lignes.append(dict(seuil=seuil, zone_id="TOTAL", pieds_reference=tot["pieds"], detections=tot["det"],
                           vrais_positifs=tot["vp"], faux_positifs=tot["fp"], oublies=tot["fn"], precision=p,
                           rappel=rr, f1=f1, erreur_comptage=tot["det"] - tot["pieds"],
                           rejets_reference=tot["rejets"], rejets_trouves=tot["rejets_trouves"]))

    tab = pd.DataFrame(lignes)
    tab.to_csv(out / "evaluation_zones.csv", index=False)
    if detections:
        pd.concat(detections, ignore_index=True).to_file(out / "detections.geojson", driver="GeoJSON")
    secondes = sum(v[0] for v in temps.values())
    hectares = sum(v[1] for v in temps.values())
    (out / "parametres.json").write_text(json.dumps(dict(
        modele=args.modele, resolution_cm=args.resolution, taille_px=args.taille, recouvrement=args.recouvrement,
        nms=args.nms, seuils=args.seuil, rayon_m=args.rayon, zones_evaluees=args.zones_evaluees,
        processeur=True, threads=torch.get_num_threads(), chargement_modele_s=round(t_charge, 1),
        inference_s=round(secondes, 1), surface_ha=round(hectares, 3),
        secondes_par_hectare=round(secondes / hectares, 1) if hectares else None), indent=2, ensure_ascii=False),
        encoding="utf-8")

    print(tab.round(3).to_string(index=False))
    print(f"\nProcesseur ({torch.get_num_threads()} fils) : chargement du modèle {t_charge:.1f} s, "
          f"inférence {secondes:.1f} s pour {hectares:.2f} ha lus, soit {secondes / hectares:.0f} s par hectare.")
    print(f"Résultats dans {out}/")


if __name__ == "__main__":
    main()
