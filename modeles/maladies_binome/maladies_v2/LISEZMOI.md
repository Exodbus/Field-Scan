# Modèle maladies v2 (Field Scan)

Classe une photo de feuille de bananier prise au sol en **saine**, **cercosporiose noire (Black Sigatoka)** ou **fusariose (Fusarium)**, ou répond **« je ne sais pas »**. C'est la moyenne de **3 ConvNeXt-Tiny**, chacun sur 4 vues de la photo.

## Contenu du dossier

| Fichier | Rôle |
|---|---|
| `classifieur.py` | le modèle : chargement, préparation des photos, probabilités, décision |
| `exemple.py` | classe toutes les photos d'un dossier et écrit un CSV |
| `poids/maladies_v2_convnext_tiny_1.pt` à `_3.pt` | les 3 réseaux (poids en 16 bits, 56 Mo chacun, remis en 32 bits au chargement) |
| `poids/seuils.json` | les seuils de décision, réglés sur la validation |
| `maladies_v2_kaggle.ipynb` | le notebook d'entraînement (Kaggle, GPU T4) |

## Installation et utilisation

Python 3.10 ou plus, sans GPU : `pip install torch torchvision pillow numpy`

```
python exemple.py DOSSIER_PHOTOS --sortie feuilles.csv
```

Depuis Python :

```python
import classifieur
reseaux, seuils = classifieur.charger("poids")
probas = classifieur.probabilites(reseaux, ["feuille1.jpg", "feuille2.jpg"])   # tableau (n, 3) : saine, Black Sigatoka, Fusarium
reponses = classifieur.decider(probas, seuils)                                  # "saine", "black_sigatoka", "fusarium", "malade_non_identifiee" ou "inconnu"
gps = classifieur.position_gps("feuille1.jpg")                                  # (longitude, latitude) ou None, pour rattacher la photo à sa parcelle
```

Environ 1 s par photo sur un processeur à 2 cœurs.

## Comment il décide

1. Chaque photo est remise droite (EXIF), son côté le plus court ramené à 224 px, puis recadrée au centre en carré et réenregistrée en JPEG qualité 95 (même préparation qu'à l'entraînement).
2. 4 vues (l'image, deux miroirs, un quart de tour) × 3 réseaux : toutes les probabilités sont moyennées.
3. **Malade** si P(Black Sigatoka) + P(Fusarium) ≥ **0,30**. Ce seuil rend le plus petit possible « 2 × malades ratées + fausses alertes » : rater une maladie compte comme deux fausses alertes.
4. **Quelle maladie** : nommée si elle fait au moins 50 % de la probabilité de maladie (donc toujours en pratique).
5. **« Je ne sais pas »** (`inconnu`) si la plus forte probabilité est sous **0,646** (seuil qui garde 95 % des photos de validation).

## Apprentissage

ConvNeXt-Tiny pré-entraîné sur ImageNet, dernière couche remplacée par 3 classes. 6 époques, dernière époque gardée, lissage des étiquettes 0,1. Modifications au hasard à chaque passage : cadrage, zoom, miroirs, rotation jusqu'à 30°, couleurs, flou, zone masquée, recompression JPEG. Les 3 réseaux ne diffèrent que par la graine du hasard.

## Données et découpage (par jeu, donc par pays ou par année)

| Rôle | Jeu | Photos |
|---|---|---|
| Apprentissage | Tanzanie 2023 (Harvard Dataverse) | 15 691 (5 627 saines, 5 766 Black Sigatoka, 4 298 Fusarium) |
| Apprentissage | Pérou (Mendeley), tiré 3 fois plus souvent | 1 268 (544 saines, 724 Sigatoka) |
| Validation | Tanzanie 2025 (Zenodo), complète | 11 766 (3 338 saines, 3 496 Black Sigatoka, 4 932 Fusarium) |
| Test (utilisé une fois, le 03/11/2026) | Bangladesh, BananaLSD (Mendeley) | 893 (90 saines, 472 Sigatoka, 159 Cordana et 172 Pestalotiopsis inconnues) |

- 398 photos de tiges retirées de Tanzanie 2023 (rangées avec les Fusarium : raccourci « tige = malade »), copies exactes retirées, aucune copie entre deux jeux.
- La Cordana du Pérou n'a jamais été lue (elle reste une maladie inconnue).

## Scores

**Validation (Tanzanie 2025)** : 30 feuilles malades sur 8 428 dites saines (0,4 %), 1,0 % de fausses alertes sur les saines, maladie nommée juste 96,9 % du temps. Le Fusarium est le plus difficile (3,5 % pris pour de la Black Sigatoka).

**Test Bangladesh** :

| Classe réelle | Saine | Black Sigatoka | Fusarium | Je ne sais pas |
|---|---|---|---|---|
| Saine (90) | **86 (95,6 %)** | 0 | 1 | 3 |
| Sigatoka (472) | 0 | **449 (95,1 %)** | 10 | 13 |
| Cordana, inconnue (159) | 0 | 93 | 13 | 53 (33 %) |
| Pestalotiopsis, inconnue (172) | 0 | 138 | 17 | 17 (10 %) |

Aucune feuille malade (connue ou inconnue) n'est dite saine.

**Jeux déjà regardés après le test (06/11/2026)** : Banana Disease Recognition (Bangladesh, 408 photos d'origine) : F1 moyenne 0,796 sur les classes connues, 18 fusarioses nommées sur 41 ; PSFD (Inde, Assam). Ces jeux ne sont donc plus vierges pour ce modèle.

## Limites

- Photos de feuilles prises au sol, de près : pas d'images drone.
- Le test ne contient pas de Fusarium : la fusariose dans un autre pays n'est pas mesurée. Sur PSFD, une fusariose sur trois est nommée (aucune dite saine), et la carence en potassium est prise pour de la fusariose dans 69 % des photos.
- Les maladies inconnues sont presque toujours signalées malades, mais rarement en « je ne sais pas » (21 % au Bangladesh), souvent nommées Black Sigatoka.
