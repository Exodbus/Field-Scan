# Protocole du classifieur « de loin » v9 (étape 2 de la chaîne en deux étapes)

Écrit le 9 novembre 2026 vers 3 h 15, par l'orchestrateur de l'équipe maladies, **avant toute préparation et tout entraînement de la v9**. Les résultats de la v2, de la v5, de la v7 et de la v8 sur `val_loin` sont connus (AUC feuilles : v2 0,672, v7 0,651, v5 0,643, v8 0,600) : la v9 est motivée par eux, d'où une règle de réussite exigeante, écrite ici. Carte blanche de Corentin, sans commit.

## 0. Pourquoi

Hypothèse de Corentin : pour les photos de loin, d'abord trouver la feuille, puis classer sa maladie. vue-de-loin a montré que trouver la feuille n'est pas le goulot (même un recadrage parfait ne bat pas l'image entière avec le B0) : le goulot est le classeur. La v7 et la v8, qui mêlaient les feuilles ROAMER (10 % des tirages) aux gros plans, n'ont pas amélioré la séparation de loin. La v9 est un **classeur spécialisé**, appris seulement sur des feuilles vues de loin, pour l'étape 2 du mode « de loin ».

## 1. Données

- **Apprentissage** : recadrages des feuilles des images de `dev_loin` (découpage figé par l'évaluateur, SHA-256 46e4a558…) dans les quatre jeux de feuilles ROAMER (fusarium, moko, healthy, bunchytop), même règle que pour `val_loin` (`scripts/preparer_feuilles_val_loin.py` lancé sur `dev_loin`) : polygone « positive » → **malade**, « negative » → **saine**. Deux classes seulement (saine / malade) : les étiquettes ROAMER disent qu'une feuille est atteinte, pas toujours laquelle des maladies.
- **Mesure** : les 3 014 feuilles de `val_loin` déjà recadrées (`data/roamer_val_loin_feuilles/`), une seule fois.
- Aucun autre jeu.

## 2. Recette

ConvNeXt-Tiny ImageNet, 2 classes, 224 px (préparation de la v2), 8 époques, dernière gardée, lots de 32, AdamW 1e-4, cosinus, lissage 0,1, augmentations de la v7 (dont basse résolution et flou) sans mosaïque, tirage équilibré saine / malade, 3 réseaux (graines 0, 1, 2), 4 vues à la mesure. Un seul entraînement.

## 3. Règle de réussite (écrite avant)

Score : P(malade) moyen des 3 réseaux et 4 vues. Sur les feuilles de `val_loin` :

- **AUC v9 − AUC v2 ≥ +0,05**, et borne basse de l'intervalle à 95 % (bootstrap apparié par groupes de scène, 1 000 tirages, graine 2026) **> 0**.

Si c'est réussi, la v9 devient le classeur de l'étape 2 du **mode « de loin »** proposé pour la chaîne (photo de loin → feuilles → v9 → « malade, à vérifier de près »), sans remplacer la v2 pour les gros plans. Seuil de décision de la v9 : celui qui donne 10 % de fausses alertes sur les feuilles saines de `dev_loin`, fixé avant la mesure. `val_loin` vient du même robot que `dev_loin` : le gain mesuré est optimiste et sera écrit ainsi.

## 4. Résultats

**Entraînement** (Kaggle `affilecorentin/entrainer-maladies-v9-loin`, un seul, vers 3 h 25) : 2 985 feuilles de `dev_loin` (1 715 malades, 1 270 saines), aucune photo commune avec `val_loin` (vérifié dans le carnet) ; perte finale 0,43 ; seuil (10 % de fausses alertes sur les saines de `dev_loin`) 0,585. Sorties `modeles/maladies_v9_loin_kaggle/v9/`.

**Mesure unique sur les 3 014 feuilles de `val_loin`** (`modeles/maladies_v9_loin_kaggle/bilan_v9.json`) :

- AUC v9 **0,870** ; AUC v2 0,672 ; écart **+0,198**, IC 95 % [+0,171 ; +0,226] (bootstrap apparié par groupes de scène, 1 000 tirages, graine 2026). **Règle remplie.**
- Au seuil fixé sur `dev_loin` : feuilles malades dites malades 82,5 % (v2 : 46,3 %), feuilles saines dites malades 27,4 % (v2 : 26,1 %). Le seuil réglé sur `dev_loin` donne donc plus de fausses alertes en validation (27 % contre 10 % visés).

**Réserve, à écrire telle quelle** : à l'intérieur d'un même projet, le gain est faible ou nul (fusarium_leaf : AUC 0,744 contre 0,720 ; moko_leaf : 0,624 contre 0,630). Le gain global vient surtout de la séparation entre les feuilles de bunchytop_leaf (toutes « positive ») et celles de healthy_leaf (toutes « negative »). Ce peut être le vrai symptôme du bunchy top, visible de loin (feuilles étroites et dressées en bouquet), ou un raccourci (reconnaître une plantation ou une prise de vue) : `val_loin` vient du même robot et des mêmes plantations que `dev_loin`, ce découpage ne permet pas de trancher.

**Contrôle indicatif ajouté après le résultat (9 novembre vers 3 h 30, sans effet sur la règle, mais qui change la recommandation)** : photos de téléphone ROAMER (autre appareil que le robot ; 139 bunchy top, 139 plantes saines ; jeux déjà ouverts par vue-de-loin, sans score) ; AUC de P(malade) sur l'image entière : **v9 0,639, v2 0,629** (`out/maladies/controle_v9_telephone.json`, script `out/maladies/controle_v9_telephone.py`). Hors du robot, la v9 ne sépare pas mieux le bunchy top des plantes saines que la v2 : son gain sur `val_loin` vient très probablement d'un raccourci propre au robot (plantations, prises de vue), pas du symptôme. Limite du contrôle : images de plantes entières, pas des recadrages de feuilles.

**Recommandation finale de l'orchestrateur : ne pas intégrer la v9.** La règle écrite est remplie, mais le contrôle hors du robot montre qu'elle ne généralise pas. Le mode « de loin » reste non résolu.

**Conséquence de la règle seule (gardée pour mémoire)** : selon la règle, la v9 est proposée comme classeur de l'étape 2 d'un **mode « de loin »** de la chaîne (photo de loin → feuilles → v9 → « malade, à vérifier de près »), sans remplacer la v2. Vu la réserve, ce mode doit être présenté comme **expérimental**, avec un message « à confirmer de près », et sa validation sur une autre source reste à faire. Décision d'intégration laissée à Corentin.
