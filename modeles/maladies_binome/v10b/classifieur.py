"""Classement des photos de feuilles (modèle retenu, voir docs/experiences.md, section 2).

Chaque modèle est une moyenne de réseaux, chacun sur 4 vues de la photo. Le dossier du modèle contient les poids
et un `seuils.json` qui dit quels réseaux charger (v2 : 3 ConvNeXt-Tiny, 3 classes ; v10 : jusqu'à deux familles de
réseaux, 4 classes avec « autre »). Décision en deux étapes, seuils réglés sur la validation :
  1. malade ou saine ? 1 − P(saine) comparé au seuil d'alerte ;
  2. quelle maladie ? nommée seulement si ce n'est pas « autre » et qu'elle fait au moins SEUIL_NOM de cette
     probabilité, sinon « malade, non identifiée » ;
et « inconnu » quand le modèle n'est pas assez sûr de lui (confiance sous le seuil). Le modèle installé (v10b) ajoute
la règle B (« saine » seulement si P(saine) atteint le seuil de confiance) et fait d'un « inconnu » probablement malade
une « maladie non identifiée » (voir decider).
"""

import io
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from torchvision import models
from torchvision import transforms as T

CLASSES = ["saine", "black_sigatoka", "fusarium"]          # classes de la v2 (valeur par défaut)
REPONSES = ["saine", "black_sigatoka", "fusarium", "malade_non_identifiee", "inconnu"]
TAILLE = 224
IMAGENET = ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
VUES = [lambda x: x, lambda x: x.flip(3), lambda x: x.flip(2), lambda x: x.rot90(1, (2, 3))]


def _reseau(nom, n_classes, taille_apprentissage):
    if nom == "convnext_tiny":
        reseau = models.convnext_tiny(weights=None)
        reseau.classifier[2] = torch.nn.Linear(reseau.classifier[2].in_features, n_classes)
        return reseau
    import timm  # réseaux DINOv3 / Pl@ntNet : seulement si le modèle installé en a besoin
    nom_timm = nom.split(":", 1)[1]
    try:
        return timm.create_model(nom_timm, pretrained=False, num_classes=n_classes, img_size=taille_apprentissage,
                                 dynamic_img_size=True)
    except TypeError:
        return timm.create_model(nom_timm, pretrained=False, num_classes=n_classes)


def charger(dossier):
    """Charge les réseaux (poids en 16 bits, remis en 32 bits) et les seuils.

    Renvoie (membres, seuils). Un membre = une famille de réseaux moyennés, avec sa taille d'image et sa
    normalisation. La v2 n'a qu'un membre ; une moyenne de deux candidats en a deux."""
    dossier = Path(dossier)
    seuils = json.loads((dossier / "seuils.json").read_text(encoding="utf-8"))
    classes = seuils.get("classes", CLASSES)
    descriptions = seuils.get("membres") or [{"motif": "maladies_v2_convnext_tiny_*.pt", "reseau": "convnext_tiny",
                                              "taille": TAILLE}]
    membres = []
    for d in descriptions:
        reseaux = []
        for chemin in sorted(dossier.glob(d["motif"])):
            reseau = _reseau(d.get("reseau", "convnext_tiny"), len(classes), d.get("taille_apprentissage", d.get("taille", TAILLE)))
            poids = torch.load(chemin, map_location="cpu", weights_only=True)
            reseau.load_state_dict({k: v.float() if v.is_floating_point() else v for k, v in poids.items()})
            reseaux.append(reseau.eval())
        if not reseaux:
            raise FileNotFoundError(f"Aucun modèle maladies {d['motif']} dans {dossier}")
        moyenne, ecart = d.get("moyenne", IMAGENET[0]), d.get("ecart", IMAGENET[1])
        membres.append({"reseaux": reseaux, "taille": d.get("taille", TAILLE), "lecture": d.get("lecture"),
                        "preparation": T.Compose([T.ToTensor(), T.Normalize(moyenne, ecart)])})
    seuils["classes"] = classes
    return membres, seuils


def preparer(chemin, taille=TAILLE, lecture=None):
    """Même préparation qu'à l'entraînement (outils/preparer_feuilles.py) : photo remise droite,
    côté le plus court à `taille` px puis recadrage carré au centre, enregistrée en JPEG qualité 95.
    `lecture` : taille de lecture du JPEG (2 × taille par défaut, comme la v2 ; 896 px pour la v10)."""
    with Image.open(chemin) as im:
        im.draft("RGB", (lecture or taille * 2, lecture or taille * 2))
        im = ImageOps.exif_transpose(im).convert("RGB")
        petite = ImageOps.fit(im, (taille, taille), method=Image.BILINEAR)
    tampon = io.BytesIO()
    petite.save(tampon, format="JPEG", quality=95)
    return Image.open(tampon).convert("RGB")


@torch.no_grad()
def probabilites(membres, photos, lot=16):
    """Probabilités (n, classes) : moyenne des 4 vues, puis des réseaux d'un membre, puis des membres."""
    if membres and isinstance(membres[0], torch.nn.Module):     # ancienne forme : une simple liste de réseaux
        membres = [{"reseaux": membres, "taille": TAILLE, "preparation": T.Compose([T.ToTensor(), T.Normalize(*IMAGENET)])}]
    resultats = []
    for i in range(0, len(photos), lot):
        p_membres = []
        for m in membres:
            x = torch.stack([m["preparation"](preparer(p, m["taille"], m.get("lecture"))) for p in photos[i:i + lot]])
            p_membres.append(torch.stack([sum(torch.softmax(r(v(x)), 1) for v in VUES) / len(VUES) for r in m["reseaux"]]).mean(0))
        resultats.append(torch.stack(p_membres).mean(0))
    n = membres[0]["reseaux"][0](torch.zeros(1, 3, 32, 32)).shape[1] if not resultats else None
    return torch.cat(resultats).numpy() if resultats else np.zeros((0, n), np.float32)


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
    """Une réponse par photo, parmi REPONSES. Avec la classe « autre », la réponse est « malade, non identifiée ».

    Deux règles en plus, seulement si seuils.json les donne (la v2 n'en a aucune) :
      - « regle_b » : une feuille n'est dite saine que si P(saine) atteint seuil_confiance ; sinon « inconnu »
        (« je ne sais pas », qui donne une alerte dans le bulletin) ;
      - « seuil_inconnu_malade » : un « inconnu » devient « malade, non identifiée » si 1 − P(saine) atteint ce seuil."""
    classes = seuils.get("classes", CLASSES)
    p_malade = 1 - probas[:, 0]
    part = probas[:, 1:].max(1) / np.maximum(p_malade, 1e-9)
    nom = np.array(classes)[1 + probas[:, 1:].argmax(1)]
    reponse = np.where(p_malade < seuils["seuil_alerte"], "saine",
                       np.where((nom != "autre") & (part >= seuils["seuil_nom"]), nom, "malade_non_identifiee")).astype(object)
    reponse[probas.max(1) < seuils["seuil_confiance"]] = "inconnu"
    if seuils.get("regle_b"):
        reponse[(reponse == "saine") & (probas[:, 0] < seuils["seuil_confiance"])] = "inconnu"
    if seuils.get("seuil_inconnu_malade") is not None:
        reponse[(reponse == "inconnu") & (p_malade >= seuils["seuil_inconnu_malade"])] = "malade_non_identifiee"
    return reponse
