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

**Amendement 1 (9 novembre 2026, vers 15 h 05, avant tout résultat ; seuls le lieu et le découpage du calcul changent, aucune règle ne change).** Kaggle n'accepte qu'un carnet GPU à la fois : le carnet complet attendait que DINOv2-FT ait fini. À la demande de Corentin (« chaque gain de temps est important »), le calcul est réparti entre Kaggle et Colab (GPU T4 gratuit, Colab CLI, solde de 0 unité de calcul), avec les mêmes données, variantes, graines et règle. Le carnet accepte des étapes (`ETAPE`), essayées en local de bout en bout :
1. variantes R0 et R3 sur Kaggle, R1 et R2 sur Colab ;
2. choix en local, par la règle de la section 3 appliquée aux 4 scores (`ETAPE=choix`) ;
3. graine 1 sur une plateforme, graine 2 sur l'autre ;
4. étape finale (seuils et probabilités) sur une seule machine, à partir des 3 réseaux.

Le lancement complet en file d'attente sur Kaggle est retiré avant d'avoir démarré (carnet supprimé avec l'accord de Corentin).

**Précision (vers 15 h 45, avant tout résultat)** : l'envoi des données vers Colab a échoué (morceaux de 100 Mo refusés sans message d'erreur). La session Colab est arrêtée sans avoir rien calculé. Kaggle accepte en fait deux carnets GPU à la fois. R0 et R3 tournent donc dans `affilecorentin/entrainer-maladies-recette-a`, R1 et R2 dans `affilecorentin/entrainer-maladies-recette-b`. La suite (graines 1 et 2, étape finale) se fera de même sur Kaggle.

**Précision 2 (vers 17 h 20, avant tout résultat de R1 et R2)** : R0 et R3 ont tourné sur Kaggle. Le carnet R1 + R2 est ensuite resté plus d'une heure en file d'attente, à cause d'un incident Kaggle (bandeau : « an issue preventing notebooks from starting »). Il est supprimé avec l'accord de Corentin. R1 et R2 tournent sur Colab (GPU T4 gratuit, Colab CLI), avec le même carnet et les mêmes données, envoyées par morceaux de 40 Mo.

## 6. Résultats (9 novembre 2026, vers 18 h 50)

**Calculs** : R0 et R3 sur Kaggle (`entrainer-maladies-recette-a`), R1 et R2 sur Colab (T4 gratuit, environ 3 min 20 par époque). Choix appliqué en local (`ETAPE=choix`), sortie dans `out/maladies/recette/recette/bilan_choix.json`.

| Variante | AUC sur TDTU (choix) | Coût en validation (garde-fou : ≤ R0 + 10 = 62) |
| --- | --- | --- |
| R0 (témoin : recette de la v2) | 0,8972 | 52 |
| R1 (+ EMA, 10 époques) | 0,8743 | 45 |
| R2 (+ CutMix) | 0,8938 | 55 |
| R3 (+ AugMix) | **0,8987** | **32** |

**Aucune variante n'est retenue.** La meilleure, R3, ne dépasse le témoin que de 0,0015 sur TDTU, alors qu'il fallait au moins 0,01. Selon la section 3, la piste s'arrête : pas de graines 1 et 2, pas de modèle final, pas de mesure sur BananaLSD.

Lecture, sans effet sur la décision :
- Avec un seul réseau par variante, des écarts de 0,02 sur TDTU peuvent venir de la seule graine. Ni la moyenne glissante des poids, ni CutMix, ni AugMix ne montrent de gain hors domaine qui dépasse ce bruit.
- R3 a le coût le plus bas en validation (32 contre 52). C'est un meilleur réglage dans le domaine tanzanien, pas un gain hors domaine.
- **La recette n'est pas le frein** pour passer à un autre pays, du moins selon TDTU. Ce qui a vraiment changé quelque chose hors domaine, c'est le réseau de départ (DINOv2-FT). Ses défauts sont ailleurs : maladies inconnues et vue de loin.
