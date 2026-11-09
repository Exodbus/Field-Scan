# Protocole : recette d'entraînement renforcée (ConvNeXt-R)

Écrit le 9 novembre 2026, vers 16 h, par Claude, à la demande de Corentin (« faisons les 2 pistes en même temps »), **avant tout entraînement**. Les résultats de la v2, de la v8 et de la soupe v2 + v8 sont connus. Ceux de DINOv2-FT ne le sont pas : son entraînement tourne au moment où ce protocole est écrit. Le modèle s'appelle **« ConvNeXt-R »**, pour ne pas croiser les noms de version du binôme.

**Piste B abandonnée avant tout calcul** (lecture de la photo à plusieurs zooms, sans réentraîner) : les jeux qui peuvent juger n'ont pas la résolution qu'il faut. BananaLSD vaut 224 px à l'origine, TDTU 244 px. Zoomer n'y ajoute aucun détail. Les jeux à haute résolution sont soit exclus des décisions (khadavy, twakihasan), soit trop faciles (validation tanzanienne).

## 0. Pourquoi

Toutes nos versions ont repris la recette de la v2 sans la régler : 6 époques, dernière époque gardée, AdamW 1e-4, augmentations de la v2. La soupe v2 + v8, une moyenne de poids, a légèrement aidé hors domaine. [H] Trois leviers classiques peuvent rendre le réseau plus robuste au changement de pays :
- une moyenne glissante des poids pendant l'entraînement (EMA), soit une « soupe » au fil des pas ;
- CutMix : un morceau d'une photo collé sur une autre, avec étiquettes mélangées au prorata ;
- AugMix : mélanges de déformations de couleur et de contraste.

## 1. Données

- Apprentissage : celui de la v2, Tanzanie 2021 + Pérou (16 963 photos), 3 classes, Pérou tiré 3 fois plus souvent.
- Validation : Tanzanie 2022-2023 sur place (3 001), pour le garde-fou du choix, les seuils et la non-régression.
- **Choix de la variante : TDTU** (Vietnam, jamais vu par la v2 ni par la v8), les 1 636 photos (black_sigatoka 404, saine 577, autre_maladie 655). Malade = black_sigatoka ou autre_maladie.
- Mesure finale : BananaLSD (897) et feuilles de `val_loin` (3 014). Seules les probabilités sont écrites ; aucun score n'est affiché.
- Jamais lus : twakihasan, banana-buddy, la Cordana du Pérou, khadavy.

## 2. Variantes (un réseau chacune, graine 0)

Toutes ont la préparation de la v2 (224 px, JPEG 95), ConvNeXt-Tiny ImageNet, AdamW 1e-4, décroissance 1e-4, cosinus, lissage 0,1, lots de 32 et les augmentations de la v2. Chaque variante ajoute un levier à la précédente :

| Variante | Époques | EMA (0,999, poids moyens évalués) | CutMix (p = 0,5, α = 1) | AugMix (gravité 3) |
| --- | --- | --- | --- | --- |
| R0 (témoin : recette de la v2) | 6 | non | non | non |
| R1 | 10 | oui | non | non |
| R2 | 10 | oui | oui | non |
| R3 | 10 | oui | oui | oui |

## 3. Choix de la variante (écrit avant, appliqué automatiquement dans le carnet)

- Score de développement : AUC de P(malade) sur TDTU (vue d'origine).
- Garde-fou : coût minimal en validation (2 × ratées + fausses alertes, vue d'origine, grille de seuils de la v2) ≤ coût de R0 + 10.
- **Variante retenue** : parmi R1, R2 et R3 qui respectent le garde-fou, celle qui a la plus forte AUC sur TDTU, **à condition qu'elle dépasse R0 d'au moins 0,01**. Sinon, la piste s'arrête : pas de modèle final, résultat rapporté tel quel.

## 4. Modèle final et adoption

- La variante retenue est complétée par deux réseaux (graines 1 et 2), avec la même recette ; le réseau de la graine 0 est réutilisé. Seuils par les règles de la v2 sur la validation : moyenne ou un seul réseau, 1 ou 4 vues, alerte, nom, confiance.
- **Adoption** : exactement la règle de DINOv2-FT (`docs/protocole_maladies_dinov2_ft.md`, section 3), avec la v2 pour référence :
  - les 6 conditions de non-régression ;
  - AUC de loin ≥ v2 − 0,02 ;
  - inconnues de BananaLSD dites Sigatoka au plus 246 / 334 ;
  - rappel équilibré sur BananaLSD ≥ v2 + 1 point.
- **Départage, écrit avant tout résultat de DINOv2-FT et de ConvNeXt-R** : parmi les candidats adoptables (soupe v2 + v8, DINOv2-FT, ConvNeXt-R), on retient le meilleur rappel équilibré sur BananaLSD, avec deux exceptions :
  - DINOv2-FT, environ 4 fois plus coûteux, doit dépasser d'au moins 1 point le meilleur candidat ConvNeXt pour l'emporter ;
  - entre la soupe et ConvNeXt-R, qui coûtent autant, un écart de moins de 1 point garde la soupe, mesurée la première.
- L'intégration dans la chaîne reste soumise à l'accord de Corentin. La liste des finalistes de twakihasan est close.

## 5. Ordre

1. Ce protocole, commité avant l'entraînement. Essai du carnet en local, sur processeur, sans poids ImageNet.
2. Carnet Kaggle `notebooks/entrainer_maladies_recette_kaggle.py` (GPU, un seul lancement ; une relance seulement pour une panne technique, notée ici) : les 4 variantes, le choix, le modèle final, les seuils et les probabilités.
3. Mesure unique : `scripts/mesurer_recette.py`, dont les résultats et la décision sont écrits en section 6.

## 6. Résultats

(à remplir)
