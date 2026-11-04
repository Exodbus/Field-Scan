# Consigne d'annotation : jeunes bananiers (photos DJI)

Écrite le 4 novembre 2026, **avant** l'annotation et avant tout entraînement du nouveau détecteur. Même consigne que pour les références manuelles MM1-MM2 et CG1-CG9.

## Images

| Photo | Rôle prévu | Raison |
| --- | --- | --- |
| `dji_0546`, `dji_0548` | entraînement | jeunes bananiers, aucun recouvrement entre elles ni avec `dji_0544` |
| `dji_0544` | validation | même parcelle que les deux autres, mais sans recouvrement d'image (mesuré par appariement SIFT + RANSAC) |

Les photos `dji_0545`, `dji_0547` et `dji_0549` recouvrent les trois photos annotées (44 à 74 %) : elles ne sont utilisées nulle part.

Source : jeu Roboflow Plants-bana (`plants_bana_originaux.zip`), fichier pleine résolution 5472 × 3648 copié tel quel. Les boîtes Roboflow de ces photos (29 à 76 par photo, souvent sur une seule feuille) sont abandonnées.

## Dans QGIS

1. Ouvrir `data/drone/jeunes_bananiers/dji_0544.tif`, `dji_0546.tif`, `dji_0548.tif` et la couche `points_jeunes_bananiers.gpkg`.
2. Les trois images sont posées côte à côte dans un **repère local en pixels** (x = colonne + décalage, y = −ligne ; voir `cadres.json`). Le système EPSG:3857 n'a aucun sens géographique : il sert seulement à ce que tout s'ouvre ensemble.
3. Annoter dans la couche `points`, en remplissant `image` (`dji_0544`, `dji_0546` ou `dji_0548`) et `type`. Le champ `image` est revérifié d'après la position du point.

## Règles

- **Un point par plant**, au centre de la rosette de feuilles (là où sort le pseudo-tronc), pas sur une feuille.
- `type = mere` : tout plant qui a son propre pseudo-tronc, **y compris un jeune plant isolé**, même petit.
- `type = rejet` : pousse collée au pied d'un plant (dans la même touffe). Pas comptée (décision de périmètre avec le mentor), mais notée.
- `type = incertain` : on ne sait pas (bananier ou autre plante, un plant ou deux). Ignoré dans le calcul : ni bon ni faux.
- Un plant coupé par le bord de l'image : annoté si son centre est dans l'image.
- Pas d'annotation des cacaoyers, arbres ou herbes.
- **Photo de validation (`dji_0544`)** : annotée de zéro, sans regarder aucune sortie de modèle (sinon la référence hérite des oublis du modèle).
- **Photos d'entraînement (`dji_0546`, `dji_0548`)** : pré-annotation permise pour gagner du temps (`scripts/preannoter_jeunes_bananiers.py`, modèle hébergé Roboflow `plants-bana/3`, couches à part dans `pre_annotations.gpkg`). Chaque point proposé est relu : faux points supprimés, plants oubliés ajoutés, type corrigé. Attention : ce modèle a été entraîné sur ces mêmes photos avec leurs boîtes incomplètes, il risque de reproduire leurs oublis ; regarder d'abord les aperçus et ne s'en servir que si les propositions sont utiles.

## Après l'annotation

- Compter les points par image et par type (`mere`, `rejet`, `incertain`).
- Fixer, avant l'entraînement : l'échelle des photos (mesurée sur un objet de taille connue, par exemple l'écart des traces de roues sur `dji_0548`) et la taille de couronne utilisée pour la cible d'un jeune plant.
