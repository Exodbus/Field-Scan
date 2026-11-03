"""Modules d'analyse. Chacun expose `executer(contexte) -> Resultat`.

Un module n'est lancé que si les données nécessaires sont présentes ; sinon il est marqué
« non évalué » dans le bulletin, avec la raison. Une erreur dans un module n'arrête pas les autres.
"""
import importlib
from dataclasses import dataclass, field

import pandas as pd

ORDRE = ["vigueur", "stress", "temporel", "comptage", "maladies"]
DESCRIPTIONS = {
    "vigueur": "vigueur (NDVI, NDRE sur Sentinel-2 ; ExG, VARI sur drone)",
    "stress": "stress hydrique (NDMI sur Sentinel-2)",
    "temporel": "suivi temporel (évolution entre deux dates Sentinel-2)",
    "comptage": "comptage des pieds (orthomosaïque de drone)",
    "maladies": "maladies des feuilles (photos)",
}


@dataclass
class Resultat:
    """Ce que rend un module : mesures par parcelle, alertes (avec leur preuve), couches écrites."""
    par_parcelle: pd.DataFrame = field(default_factory=pd.DataFrame)   # indexé par parcelle_id
    alertes: list = field(default_factory=list)                        # dicts : parcelle_id, type, gravite, message, preuve…
    couches: list = field(default_factory=list)                        # chemins des GeoTIFF / GeoJSON écrits
    resume: dict = field(default_factory=dict)


@dataclass
class Contexte:
    inventaire: object
    parcelles: object          # GeoDataFrame
    reglages: dict
    sortie: object             # Path du dossier de sortie
    journal: object
    resultats: dict = field(default_factory=dict)   # résultats des modules déjà exécutés
    cache: dict = field(default_factory=dict)       # données partagées entre modules (scènes Sentinel-2 chargées…)


def disponibilite(nom, inv):
    """(possible, raison) selon les données reconnues."""
    completes = [s for s in inv.scenes if s.complete]
    dates = sorted({s.date for s in completes})
    if nom == "vigueur":
        return (bool(completes or inv.orthos), "ni scène Sentinel-2 complète ni orthomosaïque de drone")
    if nom == "stress":
        return (bool(completes), "aucune scène Sentinel-2 complète (bandes B04, B05, B08, B8A, B11 et SCL)")
    if nom == "temporel":
        return (len(dates) >= 2, f"il faut au moins deux dates Sentinel-2 complètes ({len(dates)} trouvée(s))")
    if nom == "comptage":
        return (bool(inv.orthos), "aucune orthomosaïque de drone")
    if nom == "maladies":
        return (bool(inv.photos), "aucune photo de feuille")
    raise ValueError(nom)


def executer(nom, contexte):
    """Importe fieldscan.modules.<nom> et appelle sa fonction `executer`."""
    try:
        module = importlib.import_module(f"fieldscan.modules.{nom}")
    except ModuleNotFoundError:
        raise NotImplementedError(f"module « {nom} » pas encore écrit")
    return module.executer(contexte)
