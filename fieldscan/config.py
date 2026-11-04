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
    "comptage": {"seuil_score": 0.5, "resolution_cm": 8, "modele": "modeles/centres_5cm_v2.onnx",
                 "taille_fenetre": 400, "recouvrement": 0.25, "nms": 0.3,
                 "seuil_z": -2.0, "ecart_relatif_min": 0.2, "couverture_min": 0.5,
                 # modèle .onnx = détecteur de centres (seuil et résolution lus dans son .json ; seuil_score,
                 # resolution_cm, taille_fenetre, recouvrement et nms ignorés) ; .ckpt = DeepForest (seuil_score,
                 # resolution_cm). Réglages appliqués : « comptage_effectif » dans journal.json.
                 # Pieds estimés = détectés x [coefficient_bas, coefficient_haut] :
                 # rapports réel / détecté du détecteur de centres v2 en validation : plantation dense (Count banana
                 # plants : 1614 / 2010, indicatif car images liées à l'entraînement) et agroforesterie (MM1-MM2,
                 # mères seules : 69 / 52)
                 "coefficient_bas": 0.80, "coefficient_haut": 1.33},
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
