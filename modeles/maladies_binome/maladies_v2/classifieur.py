"""Classement des photos de feuilles (modèle retenu, voir docs/experiences.md, section 2).

Moyenne de 3 ConvNeXt-Tiny, chacun sur 4 vues de la photo. Décision en deux étapes,
avec les seuils réglés sur la validation (Tanzanie 2025) :
  1. malade ou saine ? P(Black Sigatoka) + P(Fusarium) comparé au seuil d'alerte ;
  2. quelle maladie ? nommée seulement si elle fait au moins SEUIL_NOM de cette probabilité,
     sinon « malade, non identifiée » ;
et « inconnu » quand le modèle n'est pas assez sûr de lui (confiance sous le seuil).
"""

import io
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from torchvision import models
from torchvision import transforms as T

CLASSES = ["saine", "black_sigatoka", "fusarium"]
REPONSES = ["saine", "black_sigatoka", "fusarium", "malade_non_identifiee", "inconnu"]
TAILLE = 224
PREPARATION = T.Compose([T.ToTensor(), T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
VUES = [lambda x: x, lambda x: x.flip(3), lambda x: x.flip(2), lambda x: x.rot90(1, (2, 3))]


def charger(dossier):
    """Charge les 3 réseaux (poids enregistrés en 16 bits, remis en 32 bits) et les seuils."""
    dossier = Path(dossier)
    reseaux = []
    for chemin in sorted(dossier.glob("maladies_v2_convnext_tiny_*.pt")):
        reseau = models.convnext_tiny(weights=None)
        reseau.classifier[2] = torch.nn.Linear(reseau.classifier[2].in_features, len(CLASSES))
        poids = torch.load(chemin, map_location="cpu", weights_only=True)
        reseau.load_state_dict({k: v.float() if v.is_floating_point() else v for k, v in poids.items()})
        reseaux.append(reseau.eval())
    if not reseaux:
        raise FileNotFoundError(f"Aucun modèle maladies dans {dossier}")
    seuils = json.loads((dossier / "seuils.json").read_text(encoding="utf-8"))
    return reseaux, seuils


def preparer(chemin):
    """Même préparation qu'à l'entraînement (outils/preparer_feuilles.py) : photo remise droite,
    côté le plus court à 224 px puis recadrage carré au centre, enregistrée en JPEG qualité 95."""
    with Image.open(chemin) as im:
        im.draft("RGB", (TAILLE * 2, TAILLE * 2))
        im = ImageOps.exif_transpose(im).convert("RGB")
        petite = ImageOps.fit(im, (TAILLE, TAILLE), method=Image.BILINEAR)
    tampon = io.BytesIO()
    petite.save(tampon, format="JPEG", quality=95)
    return Image.open(tampon).convert("RGB")


@torch.no_grad()
def probabilites(reseaux, photos, lot=16):
    """Probabilités (n, 3) : moyenne des 4 vues, puis des réseaux."""
    resultats = []
    for i in range(0, len(photos), lot):
        x = torch.stack([PREPARATION(preparer(p)) for p in photos[i:i + lot]])
        p = torch.stack([sum(torch.softmax(r(v(x)), 1) for v in VUES) / len(VUES) for r in reseaux]).mean(0)
        resultats.append(p)
    return torch.cat(resultats).numpy() if resultats else np.zeros((0, len(CLASSES)), np.float32)


def position_gps(chemin):
    """(longitude, latitude) lue dans les métadonnées de la photo, ou None si elle n'en a pas."""
    try:
        with Image.open(chemin) as im:
            gps = im.getexif().get_ifd(0x8825)
        if not gps or 2 not in gps or 4 not in gps:
            return None
        def degres(v):
            return float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
        lat, lon = degres(gps[2]), degres(gps[4])
        if gps.get(1) == "S":
            lat = -lat
        if gps.get(3) == "W":
            lon = -lon
        return lon, lat
    except Exception:
        return None


def decider(probas, seuils):
    """Une réponse par photo, parmi REPONSES."""
    p_malade = probas[:, 1:].sum(1)
    part = probas[:, 1:].max(1) / np.maximum(p_malade, 1e-9)
    nom = np.array(CLASSES)[1 + probas[:, 1:].argmax(1)]
    reponse = np.where(p_malade < seuils["seuil_alerte"], "saine",
                       np.where(part >= seuils["seuil_nom"], nom, "malade_non_identifiee")).astype(object)
    reponse[probas.max(1) < seuils["seuil_confiance"]] = "inconnu"
    return reponse
