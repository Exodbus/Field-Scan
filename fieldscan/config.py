"""Réglages de la chaîne : valeurs par défaut, éventuellement remplacées par un fichier YAML."""
import copy
from pathlib import Path

import yaml

DEFAUTS = {
    "entrees": {
        "drone_resolution_max_m": 0.5,      # au-delà, un GeoTIFF RGB n'est pas traité comme une image de drone
        "sentinel2_resolution_m": [8.0, 25.0],
    },
    "parcelles": {
        "champs_identifiant": ["parcelle_id", "id", "name", "nom", "ID", "Name", "zone_id", "site"],
    },
    "vigueur": {"seuil_z": -2.0, "ecart_min_ndvi": 0.05, "ecart_min_ndre": 0.05, "sigma_min": 0.01, "min_px_zone": 5,
                "ecart_min_exg": 0.03, "resolution_drone_m": 0.5, "lissage_drone_m": 3.0, "min_m2_zone_drone": 25},
    "stress": {"seuil_z": -2.0, "ecart_min_residu_ndmi": 0.03, "sigma_min": 0.01, "min_px_zone": 5},
    "nuages": {"seuil_masque_pct": 50.0, "marge_px": 2, "erosion_px": 1, "min_pixels": 20, "confiance_faible_pct": 30.0},
    "maladies": {"seuil_malade": 0.5, "seuil_rejet": 0.7076, "methode_rejet": "proba_max",
                 "modele": "modeles/maladies/maladies_v2.onnx"},
    "comptage": {"seuil_score": 0.5, "resolution_cm": 10, "modele": "modeles/bananiers_deepforest_dense_v2.ckpt",
                 "taille_fenetre": 400, "recouvrement": 0.25, "nms": 0.3,
                 "seuil_z": -2.0, "ecart_relatif_min": 0.2, "couverture_min": 0.5,
                 # pieds estimés = fourchette pieds détectés x [coefficient_bas, coefficient_haut] :
                 # bas = agroforesterie (référence manuelle MM1-MM2 : 83 réels / 58 détectés),
                 # haut = plantation dense (validation de Count banana plants : rapport réel / détecté 2,19)
                 "coefficient_bas": 1.43, "coefficient_haut": 2.19},
    "score": {"penalites": {"vigueur": 25, "stress": 20, "evolution": 15, "maladie": 30, "densite": 10},
              "facteur_moyenne": 0.6, "facteur_confiance_faible": 0.5, "seuil_vert": 80, "seuil_orange": 60},
}


def fusionner(base, ajout):
    """Fusion récursive : les valeurs de `ajout` remplacent celles de `base`."""
    out = copy.deepcopy(base)
    for k, v in (ajout or {}).items():
        out[k] = fusionner(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def charger(chemin=None):
    if chemin is None:
        return copy.deepcopy(DEFAUTS)
    p = Path(chemin)
    if not p.exists():
        raise SystemExit(f"Fichier de configuration introuvable : {p}")
    return fusionner(DEFAUTS, yaml.safe_load(p.read_text(encoding="utf-8")) or {})
