# Field Scan

Chaîne d'analyse d'une bananeraie à partir d'images aériennes et de photos de feuilles : une commande produit, **parcelle par parcelle**, un bulletin de santé (score, alertes, priorités) où **chaque constat renvoie à l'image qui le justifie**, avec les cartes et couches géospatiales correspondantes.

| Module | Données | Méthode | Résultat mesuré (voir `docs/carnet_de_donnees.md`) |
| --- | --- | --- | --- |
| Vigueur | Sentinel-2 ; drone RGB | NDVI, NDRE (satellite) ; ExG lissé (drone) ; zones et parcelles faibles par z-score robuste | alertes identiques aux scripts d'analyse validés |
| Stress hydrique | Sentinel-2 | résidu du NDMI par rapport à la droite NDMI ~ NDVI du site | idem |
| Suivi temporel | Sentinel-2, deux dates ou plus | évolution corrigée de la variation commune au site | idem |
| Maladies | photos de feuilles | module à deux branches : un aiguilleur (DINOv2 figé) sépare gros plans et plantes entières ; gros plans : v10b du binôme (3 ConvNeXt-Tiny aux poids DINOv3, photo lue en 384 px, 4 vues, 4 classes dont « autre maladie ») ; plantes entières : v2, avec « à confirmer par un gros plan » ; décision en deux étapes (alerte, nom) ; une feuille n'est dite saine que si le modèle en est assez sûr, sinon « à vérifier » (alerte de confiance faible) (`docs/protocole_maladies_v10b.md`) | validation : 9 malades sans alerte sur 2 001, 5,7 % de fausses alertes (dont une partie sur des feuilles en fait malades) ; jeux de pays neufs (Vietnam, Inde, Éthiopie) : 46 à 50 % de malades sans alerte en moins qu'avec l'ancienne branche, mais 28 à 31 % de fausses alertes sur les feuilles saines ; Cordana du Pérou (maladie jamais apprise) : 99 % en alerte, dite Sigatoka dans 52 % des cas (90 % avant) |
| Comptage des pieds | orthomosaïque de drone | détecteur de centres de couronnes (carte de chaleur, ResNet-18, 5 cm, ONNX), palmiers et cocotiers appris comme exemples négatifs | F1 0,79 en validation (MM1-MM2, pieds mères) ; 14 fausses détections sur 873 images de palmiers ; **faible sur jeunes plants et bananiers cachés** (F1 0,19 sur le site de test) |

Temps sur processeur : environ **1,8 s par photo de feuille** (3 réseaux × 4 vues en 384 px, processeur à 4 cœurs ; 35 ms avec l'ancien B0) et **2 à 4 s par hectare** de drone pour le comptage.

## Installation

Python 3.11 ou plus récent requis. Testé avec Python 3.14 sous Windows 11 (inférence) ; entraînement sous Python 3.13 (Kaggle, GPU T4).

```bash
git clone <adresse du dépôt> Field-Scan
cd Field-Scan
python -m venv .venv
# Windows : .venv\Scripts\Activate.ps1   |   Linux, macOS : source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` donne les versions exactes de l'environnement de développement (régénéré par `python scripts/ecrire_requirements.py`).

## Modèles

| Fichier | Module | Où le trouver |
| --- | --- | --- |
| `modeles/maladies_binome/v10b/` (3 fichiers `maladies_v10b_*.pt` et `seuils.json`) | maladies, gros plans (retenu) | hors du dépôt (166 Mo) : archive du binôme du 11/11 ; demande `timm` ≥ 1.0.20 |
| `modeles/maladies_soupe_v2_v8/poids/` (3 fichiers `maladies_soupe_convnext_tiny_*.pt` et `seuils.json`) | maladies, gros plans (ancien, comparaison) | hors du dépôt (150 Mo) : moyenne des poids de la v2 et de la v8 (`scripts/predire_soupe_v2_v8.py`) |
| `modeles/maladies_binome/maladies_v2/poids/` (3 fichiers `*_convnext_tiny_*.pt` et `seuils.json`) | maladies, plantes entières (retenu) | hors du dépôt (170 Mo) : archive `maladies_v2.zip` du binôme, dossier `poids/` à copier ici |
| `modeles/maladies_aiguilleur/aiguilleur.npz` | maladies, aiguilleur loin / près | hors du dépôt (25 Ko) : `scripts/ajuster_aiguilleur.py` ; demande les poids DINOv2 ViT-B/14 (torch.hub, téléchargés une fois) |
| `modeles/maladies/maladies_v2.onnx` | maladies (ancien B0, comparaison) | dans le dépôt (16 Mo) |
| `modeles/maladies/entrainement_maladies.json` | maladies | dans le dépôt : classes, vues, normalisation, seuil de rejet |
| `modeles/maladies/rejet.npz` | maladies (analyses) | dans le dépôt |
| `modeles/centres_5cm_v2.onnx` et `modeles/centres_5cm_v2.json` | comptage (retenu) | dans le dépôt (45 Mo) : détecteur de centres v2, seuil, résolution, normalisation et règle de choix ; les deux fichiers doivent porter le même nom |
| `modeles/centres_5cm.onnx` et `modeles/centres_5cm.json` | comptage (détecteur v1, comparaison) | dans le dépôt (45 Mo) |
| `modeles/bananiers_deepforest_dense_v2.ckpt` | comptage (ancien détecteur, comparaison) | trop gros pour le dépôt : page **Releases** du dépôt |

Sans le modèle de comptage, la chaîne fonctionne : le module comptage est simplement marqué « non évalué ».

## Utilisation

```bash
python run.py --images DOSSIER --parcelles parcelles.geojson --out resultats/
```

Options : `--modules vigueur stress temporel comptage maladies` pour n'en lancer que certains (par défaut, tous ceux que les données permettent) ; `--config autre.yaml` pour d'autres réglages (par défaut, `config.yaml` à côté de `run.py`).

Exemples avec les données du projet :

```bash
# Sentinel-2 (deux dates) : vigueur, stress hydrique, suivi temporel
python run.py --images data/sentinel2 --parcelles data/parcelles/parcelles_cotedivoire.geojson --out resultats/cotedivoire
# Drone : comptage et vigueur RGB
python run.py --images "data/drone/reforestree/wwf_ecuador/RGB Orthomosaics" --parcelles data/drone/reforestree/prepare/sites.geojson --out resultats/drone
# Photos de feuilles seules
python run.py --images data/demo_feuilles --parcelles data/parcelles/parcelles_cotedivoire.geojson --out resultats/feuilles --modules maladies
```

### Données reconnues dans `--images`

Le dossier est parcouru en entier ; chaque fichier est classé, et tout fichier écarté est listé avec sa raison dans `inventaire.json`.

| Données | Forme attendue |
| --- | --- |
| Sentinel-2 L2A | export du Copernicus Browser (bandes `…_L2A_B04_(Raw).tiff`, dossiers ou `.zip`) **ou** produit officiel `.SAFE` (dossier ou `.zip`) ; bandes B04, B05, B08, B8A, B11 et SCL nécessaires ; plusieurs dates possibles ; scènes hors des parcelles écartées |
| Orthomosaïque de drone | GeoTIFF RGB (3 bandes, ou 4 avec transparence), résolution meilleure que 50 cm, en mètres ou en degrés ; jamais chargée en entier |
| Photos de feuilles | JPG ou PNG ; rattachées à leur parcelle si elles contiennent des coordonnées GPS (EXIF), sinon listées à part |

### Parcelles

GeoJSON de polygones, dans n'importe quel système de coordonnées. Identifiant lu dans le premier champ trouvé parmi `parcelle_id`, `id`, `name`, `nom`, `zone_id`, `site` ; sinon, parcelles numérotées. Géométries invalides réparées, doublons d'identifiant suffixés (signalés dans le journal).

## Sorties

```
resultats/
├── bulletin.html          bulletin lisible : carte (parcelles par niveau, zones et photos en alerte), tableau par priorité,
│                          preuve de chaque alerte au clic (la carte demande Internet ; le reste fonctionne hors ligne)
├── bulletin.csv           une ligne par parcelle : score, niveau, priorité, alertes, mesures de chaque module
├── alertes.geojson        chaque alerte : géométrie (EPSG:4326), message, gravité, confiance, source, chemin de la preuve
├── pieds.geojson          pieds détectés (drone)
├── carte_bulletin.png     carte fixe des scores
├── cartes/                GeoTIFF : NDVI, NDRE, NDMI, résidu NDMI, masque de nuages, évolutions, ExG drone
├── preuves/               vignette de chaque alerte (extrait de la carte ou de l'orthomosaïque, photo de feuille)
├── *_par_date.csv, evolution_par_paire.csv, comptage_parcelles.csv, maladies_photos.csv   détails par module
├── inventaire.json        données reconnues et fichiers écartés
└── journal.json           versions, réglages, durées (dont secondes par hectare), événements et erreurs
```

## Lire le bulletin

- **Date des données** : chaque parcelle est décrite par la **dernière date où elle est exploitable** (pas trop nuageuse) ; le bulletin signale quand cette date est antérieure à la dernière image.
- **Score de santé** (0 à 100) : 100 moins une pénalité par module en alerte (vigueur 25, stress 20, évolution 15, maladie 30, densité 10 ; un module compte une fois par parcelle), réduite à 60 % pour une gravité moyenne et divisée par deux si la confiance est faible. Vert ≥ 80, orange ≥ 60, rouge en dessous ; une alerte forte et fiable place la parcelle au moins en orange. Une parcelle qu'aucun module n'a pu évaluer est « non évaluée ».
- **Priorité** : parcelles en alerte, par score croissant puis surface décroissante.
- **Alerte** : toujours deux conditions, un écart inhabituel (z-score robuste) **et** un écart suffisant en valeur absolue.
- **Comptage** : détecteur de **centres de couronnes** (carte de chaleur, ResNet-18, 5 cm par pixel, ONNX, 2 à 4 s par hectare sur processeur). Le bulletin donne les pieds **détectés** et une **fourchette** estimée (détectés x 0,80 à x 1,33, rapports réel / détecté mesurés en validation en plantation dense et en agroforesterie ; la borne basse est indicative, voir les limites). F1 (appariement à 1 m, pieds mères) : 0,79 sur la référence manuelle MM1-MM2 (validation), 0,20 sur le site de test Carlos Vera Guevara (jeunes plants et bananiers cachés sous d'autres arbres : rappel 0,11). Les jeunes plantations sortent de la fourchette.
- **Maladies** : « saine », « cercosporiose noire », « fusariose ou autre flétrissement vasculaire (à confirmer par un examen du pseudo-tronc) », « malade, maladie non identifiée » ou « je ne sais pas ». Une feuille malade est signalée même quand la maladie n'est pas identifiée, y compris quand le modèle hésite sur le nom mais pas sur la maladie. Une photo prise de loin (plante entière) porte la mention « à confirmer par un gros plan de la zone malade ».

Tous les seuils sont dans `config.yaml` (valeurs par défaut dans `fieldscan/config.py`).

## Limites connues

- **Comptage indicatif** : fiable sur des bananiers adultes bien visibles (plantation, agroforesterie) ; il oublie la plupart des jeunes plants et des bananiers cachés sous d'autres arbres (rappel 0,11 sur le site de test). C'est le prix de l'apprentissage des palmiers comme exemples négatifs (fausses détections sur palmiers : 6 876 → 14 sur 873 images). Ses alertes de densité sont en confiance faible.
- **Rejets** : le comptage ne distingue pas pieds mères et rejets ; les rejets au pied des bananiers ne sont pas comptés (choix de périmètre).
- **Borne basse de la fourchette** : mesurée sur Count banana plants, dont les images sont d'autres découpes des photos d'entraînement (Plants-bana) ; elle est optimiste et seulement indicative.
- **Maladies inconnues** : détectées comme malades (toutes celles de BananaLSD sont en alerte), mais souvent nommées d'après une maladie connue (Cordana et Pestalotiopsis dites Sigatoka dans 82 % des cas au Bangladesh). Quatre méthodes ont échoué à corriger ce défaut (classe « autre maladie », détecteurs de nouveauté sur la v2 et sur DINOv2, désaccord entre deux modèles). Apprendre Cordana et Pestalotiopsis sur un autre jeu du Bangladesh divise ces erreurs par deux, mais nomme mal ces maladies et fait reculer d'autres mesures (`docs/protocole_maladies_cinq_classes.md`).
- **Prise de vue** : le classifieur est fiable sur des gros plans de la zone malade ; il sépare mal les feuilles malades et saines vues de loin (AUC 0,67 sur les feuilles du robot ROAMER), et aucune version apprise sur des vues de loin n'a mieux fait hors de ce robot.
- **Stress hydrique** : la bande B11 (20 m) est plus floue que le NDVI (10 m) ; aux bords nets d'une zone peu vigoureuse, de petites zones de stress peuvent apparaître.
- **Nuages** : une parcelle couverte à plus de 50 % est non exploitable à cette date.

## Reproduire l'entraînement

- Données de feuilles : `scripts/verifier_zips.py`, `scripts/reperer_tiges.py`, `scripts/preparer_feuilles.py` (exclusion des tiges, doublons, fuites).
- Classifieurs retenus : v2 du binôme, carnet `maladies_v2_kaggle.ipynb` (archive `maladies_v2.zip`) ; soupe v2 + v8, `scripts/predire_soupe_v2_v8.py` ; aiguilleur, `scripts/ajuster_aiguilleur.py`. Essais suivants, chacun avec son protocole : `notebooks/entrainer_maladies_v*_kaggle.py`, `notebooks/entrainer_maladies_dinov2_kaggle.py`, `notebooks/entrainer_maladies_cinq_classes_kaggle.py`.
- Ancien classifieur B0 : `notebooks/entrainer_maladies_kaggle.ipynb` (ou la version Colab) ; deux exécutions complètes ont donné des résultats identiques.
- Comptage : `scripts/prepare_reforestree.py`, `scripts/preparer_roboflow_deepforest.py` (`--boite-cible 60 --format jpg`), `scripts/preparer_multiple_tree.py`, `scripts/preparer_validation_points.py`, puis `notebooks/entrainer_centres_v2_kaggle.ipynb` (règle de choix de l'époque et du seuil écrite dans `modeles/centres_5cm_v2.json`). Vérification des fuites : `scripts/verifier_sources_communes.py`.

## Structure

```
run.py, config.yaml        commande et réglages
fieldscan/                 paquet : entrees, parcelles, sentinel2, drone, anomalies, bulletin, journal, modules/
scripts/                   préparation des données, évaluations, analyses
notebooks/                 entraînements (Colab, Kaggle)
docs/                      carnet de données (sources, licences, découpages, résultats, limites) et images
modeles/                   poids des modèles
```

## Données et licences

Toutes les sources sont publiques et documentées dans `docs/carnet_de_donnees.md` (provenance, licence, résolution, dates, découpage entraînement / validation / test, risques de fuite, biais et limites).
