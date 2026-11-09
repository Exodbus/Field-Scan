# Protocole : diagnostic DINOv2 (réseau pré-appris plus général)

Écrit le 9 novembre 2026, vers 13 h 40, par Claude, avec l'accord de Corentin (« go sur la piste 1 » : GPU Kaggle et téléchargement des poids par Kaggle). Il est écrit **avant tout calcul** : aucune caractéristique DINOv2 n'existe encore. Aucun réseau n'est entraîné ici : on n'apprend que des couches de classement simples (sondes linéaires) sur des caractéristiques figées. Il s'agit d'un **diagnostic** : il décide si un fine-tuning complet de DINOv2 vaut la peine (protocole séparé, à écrire avant). Il ne décide pas du modèle de la chaîne, sauf dans le cas décrit en D1.

## 0. Pourquoi

- Le détecteur de nouveauté sur la v2 a échoué : dans l'espace de la v2, les maladies inconnues de TDTU ne se distinguent pas des Sigatoka (AUC de 0,39 à 0,52, `docs/protocole_maladies_melange_nouveaute.md`, section 5). [H] Les caractéristiques de la v2 sont trop spécialisées sur ses 3 classes.
- DINOv2 est pré-appris sans étiquettes sur 142 millions d'images. [H] Ses caractéristiques sont plus générales et tiennent mieux les changements de domaine. Il n'a encore jamais été testé dans ce projet. Toutes nos versions partaient du même ConvNeXt-Tiny ImageNet.

## 1. Réseaux et caractéristiques (figés, sans choix)

| Réseau | Poids | Caractéristique |
| --- | --- | --- |
| **DINOv2** ViT-B/14 | `facebookresearch/dinov2`, `dinov2_vitb14` (torch.hub) | jeton de classe et moyenne des jetons d'image (normalisés), mis bout à bout : 1 536 valeurs |
| **Référence** : ConvNeXt-Tiny ImageNet | torchvision `IMAGENET1K_V1`, point de départ de la v2 | sortie de la mise en commun et de la normalisation : 768 valeurs |

- Préparation de la v2 (`classifieur.preparer` : 224 px, recadrage carré, JPEG 95 ; normalisation ImageNet).
- Une vue pour l'apprentissage, l'ajustement et TDTU ; les 4 vues de la v2 pour la validation et BananaLSD.
- Carnet Kaggle `notebooks/extraire_dinov2_kaggle.py` (GPU, internet activé pour télécharger les poids). Il n'écrit que des caractéristiques, aucun score.

## 2. Données (aucun nouveau jeu)

| Rôle | Jeu |
| --- | --- |
| Apprentissage des sondes | apprentissage de la v2, Tanzanie 2021 et Pérou (16 963 photos) ; Pérou pesé ×3, comme la v2 |
| Ajustement du détecteur | les mêmes 2 500 photos que le protocole « mélange + nouveauté » (500 par source et classe, graine 2026) |
| Choix du détecteur | TDTU : `autre_maladie` (655) contre `black_sigatoka` (404) |
| Seuils et mesure | validation (3 001) ; BananaLSD (897) |

Jamais lus : twakihasan, banana-buddy, la Cordana du Pérou, khadavy.

## 3. D1 : détecteur de nouveauté dans l'espace DINOv2

- Variantes c (Mahalanobis, plus petite distance aux 3 classes) et d (Mahalanobis relative), exactement comme dans le protocole « mélange + nouveauté » : covariance commune réduite, Σ' = 0,9 Σ + 0,1 (trace(Σ) / d) I. Elles sont calculées sur les caractéristiques DINOv2, vue d'origine. Les mêmes variantes sont calculées sur la référence ConvNeXt ImageNet, et rapportées.
- **Seuil de réussite du diagnostic** : la meilleure AUC DINOv2 sur TDTU atteint **au moins 0,65**. À titre de repère, l'espace de la v2 donnait au mieux 0,517.
- **Si c'est réussi**, le détecteur DINOv2 est ajouté à la v2 avec les règles de la partie B du protocole « mélange + nouveauté » :
  - variante retenue : la plus forte AUC sur TDTU, c si l'écart est inférieur à 0,01 ;
  - seuil : quantile 98 % de la validation ;
  - décision : le nom est retiré quand la v2 nomme une maladie et que le score dépasse le seuil ;
  - adoption, si les quatre conditions suivantes sont remplies : malades nommées en validation ≥ v2 − 2 points ; nommée juste ≥ 95 % ; BananaLSD Sigatoka nommée ≥ v2 − 2 points ; **inconnues nommées sur BananaLSD ≤ v2 − 10 points**.
  
  Il est mesuré une fois. Les réponses de la v2 sont celles des fichiers GPU de la nuit.
- **Si c'est un échec**, rien n'est mesuré sur BananaLSD pour D1.

## 4. D2 : sondes linéaires, DINOv2 contre ConvNeXt ImageNet

- **Sonde** : régression logistique à 3 classes sur les caractéristiques centrées-réduites (moyenne et écart-type de l'apprentissage). Pénalité L2 fixée sans réglage, λ = 1e-4 × ‖W‖², optimisée par L-BFGS (500 itérations au plus), poids des photos : Pérou ×3. Même recette pour les deux réseaux.
- **Probabilités** : la moyenne des 4 vues. **Seuils** : les règles de la v2 sur la validation (alerte au coût minimal 2 × ratées + fausses alertes, nom à 95 % de noms justes, confiance qui garde 95 % des photos).
- **Mesures**, pour chaque sonde et pour la v2 (repère) :
  - rappel équilibré en validation : moyenne, sur les 3 classes, de la part de réponses exactes ;
  - rappel équilibré sur BananaLSD : moyenne de « Sigatoka nommée » et « saines bien classées » ;
  - les 6 conditions de non-régression, rapportées ;
  - maladies inconnues dites Sigatoka, rapportées.
- **Règle du diagnostic** (écrite avant) : un fine-tuning complet de DINOv2 est proposé si la sonde DINOv2 a :
  - un rappel équilibré sur BananaLSD **≥ celui de la sonde ConvNeXt + 3 points** ;
  - et un rappel équilibré en validation ≥ celui de la sonde ConvNeXt − 1 point.
- Les sondes ne remplacent pas la v2 : aucune adoption n'est décidée en D2.

## 5. Ordre

1. Ce protocole, commité avant tout calcul.
2. Carnet Kaggle d'extraction, puis contrôle : la sonde ConvNeXt doit lire les mêmes photos, dans le même ordre, que les fichiers GPU de la nuit.
3. Mesure unique : `scripts/mesurer_dinov2.py`, dont les résultats sont écrits en section 6.

## 6. Résultats (9 novembre 2026, vers 14 h 45, mesure unique)

**Calculs** : carnet Kaggle `affilecorentin/extraire-dinov2` (version 1, GPU, 11 minutes). Aucune valeur non finie dans les caractéristiques. Contrôles passés : les photos de validation et de BananaLSD sont dans le même ordre que les fichiers GPU de la nuit, et le tirage d'ajustement est identique à celui du protocole « mélange + nouveauté ». Mesure : `scripts/mesurer_dinov2.py`, sortie dans `out/maladies/dinov2/bilan_dinov2.json`.

### D1 : détecteur de nouveauté

| Espace | AUC TDTU, variante c | variante d |
| --- | --- | --- |
| v2 (protocole précédent) | 0,517 | 0,515 |
| ConvNeXt ImageNet (figé) | 0,505 | 0,494 |
| **DINOv2 (figé)** | **0,576** | 0,570 |

**Échec du diagnostic** : l'AUC exigée était d'au moins 0,65. DINOv2 sépare un peu mieux que le hasard les maladies inconnues de TDTU des Sigatoka, mais pas assez pour un détecteur. Comme prévu, rien n'a été mesuré sur BananaLSD pour D1.

### D2 : sondes linéaires

| Mesure | v2 (fine-tunée, repère) | Sonde DINOv2 | Sonde ConvNeXt ImageNet |
| --- | --- | --- | --- |
| Validation : malades dites saines | 4 / 2 001 | 8 | 35 |
| Validation : fausses alertes | 7 / 1 000 | 3 | 27 |
| Validation : rappel équilibré | 0,941 | **0,894** | 0,809 |
| BananaLSD : Sigatoka nommée | 445 / 473 | 399 | 303 |
| BananaLSD : saines bien classées | 86 / 90 | 76 | 82 |
| BananaLSD : rappel équilibré | 0,948 | **0,844** | 0,776 |
| BananaLSD : inconnues dites Sigatoka | 230 / 334 | 262 | 188 |

Règle : BananaLSD, DINOv2 0,844 contre ConvNeXt 0,776, soit +6,8 points pour +3 exigés : **OK**. Validation : 0,894 contre 0,809, soit +8,5 points : **OK**. **Un fine-tuning complet de DINOv2 est proposé.** Il fera l'objet d'un protocole séparé, écrit et commité avant l'entraînement.

Lecture :
- Figé, DINOv2 donne de bien meilleures caractéristiques que le point de départ de la v2. Une simple couche dessus atteint 0,894 de rappel équilibré en validation, contre 0,809 pour ConvNeXt.
- Une sonde figée reste loin de la v2 fine-tunée (0,894 contre 0,941 ; 0,844 contre 0,948 sur BananaLSD). Le diagnostic dit que DINOv2 est un meilleur point de départ ; il ne dit pas qu'un DINOv2 fine-tuné battra la v2.
- Les deux sondes collent presque parfaitement à leur apprentissage (perte finale 0,0025 et 0,0046). La pénalité, fixée sans réglage, est faible.
- La sonde DINOv2 range aussi beaucoup de maladies inconnues dans la Sigatoka (262 / 334). Les caractéristiques générales ne règlent pas, à elles seules, le défaut des maladies inconnues.
