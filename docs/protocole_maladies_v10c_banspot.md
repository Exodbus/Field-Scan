# Protocole : v10c, la v10b réentraînée avec les fermes libres de BanSpot

Écrit le 11 novembre 2026 par Claude, **avant le téléchargement de BanSpot et avant d'en avoir vu la moindre photo ou métadonnée**. Objectif fixé par Corentin : rater moins de feuilles malades. Une fausse alerte est moins grave, mais doit rester bornée. Rien n'est commité sans son accord ; l'empreinte SHA-256 de ce fichier et l'heure sont notées dans `docs/maladies_equipe/journal_v10b.md` avant chaque étape.

## 1. Données

**BanSpot** (Zenodo 20098282, CC BY 4.0) : feuilles de bananier photographiées au téléphone dans 10 fermes du district de Kasaragod (Kerala, Inde), classées « avec taches » ou « sans taches ». Ces étiquettes ne disent pas de quelle maladie il s'agit.

**Découpage par ferme, jamais par photo** :
- **Test** : les 2 fermes des 1 292 photos notées par le binôme (`banspot_liste_test.csv`), en entier. Elles ne servent qu'à la mesure finale, une seule fois.
- **Validation** : parmi les 8 autres fermes, celle qui a le plus de photos, puis la suivante si la première a moins de 300 photos ou moins de 50 photos d'une des deux classes. Règle mécanique, appliquée sur les seuls effectifs.
- **Apprentissage** : les fermes restantes.
- Si les métadonnées ne donnent pas la ferme de chaque photo, rien n'est entraîné, et Corentin est prévenu.

**Contrôle de fuite** avant tout entraînement : SHA-256, puis dHash ≤ 10 bits sous les 8 symétries, contre :
- les 1 292 photos de test ;
- nos jeux de feuilles (index, ajouts v3, jeux de la nuit) ;
- la liste de la v10 (SHA-256 seulement).

Une photo d'apprentissage ou de validation qui recopie une photo de test est retirée. Une ferme avec plus de 5 % de photos retirées passe entièrement en « exclue ».

**Feuilles abîmées par les insectes** : si les métadonnées signalent des dégâts d'insectes sur des photos « sans taches », ces photos sont retirées de l'apprentissage, sans quoi le modèle apprendrait qu'une feuille mangée est saine. Elles restent dans la validation et le test, et sont comptées à part. Si rien ne les signale, rien n'est retiré, et c'est écrit comme une limite.

**Autres données d'apprentissage** :
- celles de nos modèles : Tanzanie 2021 et Pérou (saines et Sigatoka), 16 963 photos, jeu Kaggle `feuilles-pret-perou` ;
- le jeu Mendeley `wfzpdmc5vx` déjà contrôlé (422 photos) : Cordana et Pestalotiopsis comptées en « autre », pour que la classe « autre » de la v10b ne s'efface pas ; ses Sigatoka et ses saines sont gardées telles quelles.

## 2. Entraînement (Kaggle, T4)

- **Départ** : chacun des 3 réseaux de la v10b (ConvNeXt-Tiny aux poids DINOv3, 4 classes), réentraîné séparément (graines 0, 1, 2).
- **Images** : apprentissage en 224 px comme la v10, lecture en 384 px comme la chaîne. BanSpot réduit au préalable en copies de 896 px de petit côté (préparation de la chaîne inchangée).
- **Recette** :
  - AdamW, taux 1e-5 pour le réseau et 1e-4 pour la tête, décroissance 0,05, cosinus, 3 époques, lots de 32, précision mixte ;
  - augmentations du carnet « cinq classes » (recadrage 0,4 à 1, miroirs, rotation 30°, couleurs, flou, JPEG, effacement) ;
  - tirage : BanSpot fait 30 % de chaque époque, `wfzpdmc5vx` 5 %, le reste nos données.
- **Pertes** :
  - photos étiquetées par maladie (Tanzanie, Pérou, `wfzpdmc5vx`) : entropie croisée à 4 classes, lissage 0,1 ;
  - BanSpot « sans taches » : entropie croisée sur « saine » ;
  - BanSpot « avec taches » : −log(1 − P(saine)). Le modèle apprend « malade » sans qu'on lui impose de nom.
- **Époque gardée** : la dernière (pas de choix d'époque).
- **Décision** : celle de la v10b, avec ses seuils inchangés (alerte 0,725, nom 0,79, confiance et règle B 0,519, v11 0,675). Aucun seuil n'est réglé à nouveau : on mesure l'effet des données seules.

## 3. Règle d'adoption (v10c contre la v10b installée), écrite avant

Même chaîne pour les deux (aiguilleur, branche « loin » inchangée). Une photo est en alerte si sa réponse est une maladie, « malade, non identifiée » ou « à vérifier ». **La v10c remplace la v10b si toutes ces conditions sont remplies :**

1. **Validation BanSpot** (fermes de validation), le gain visé :
   - coût 3 × malades sans alerte + saines en alerte **strictement plus bas** que la v10b. Le poids 3 traduit la préférence de Corentin ;
   - **et** saines en alerte ≤ v10b + 10 points.
2. **Validation Tanzanie 2022-2023 (3 001)**, la non-régression :
   - malades sans alerte ≤ 14 (v10b : 9) ;
   - saines en alerte ≤ 77 / 1 000 (v10b : 57).
3. **Pays neufs déjà mesurés le 11/11** (TDTU, PSFD, Éthiopie), la non-régression :
   - malades sans alerte ≤ v10b + 2 points sur chacun ;
   - saines en alerte ≤ v10b + 5 points (TDTU, Éthiopie).

Si l'une manque, la v10b reste installée.

## 4. Mesure finale (une fois, après la décision)

- **Test BanSpot** (2 fermes, 1 292 photos), pour la v10c et la v10b : malades sans alerte, saines en alerte, réponses « à vérifier ». Ce test ne change pas la décision.
- **Cordana du Pérou**, rapportée seulement : elle a déjà été lue une fois le 11/11.

Les chiffres de la v10b sur ce test, calculés par le binôme sur des copies réduites à 896 px, sont rapportés pour comparaison (0,93 % de malades ratées, 10,2 % de fausses alertes). Notre mesure est refaite sur les mêmes copies que celles de la v10c.

## 5. Constat à l'ouverture de l'archive (11 novembre 2026, vers 14 h 45, avant tout entraînement et toute prédiction)

`DATASET.zip` (5,3 Go, MD5 `bee4d641771fecefb819ffc33cc128f1`, identique à Zenodo) ne contient que **1 300 photos de 2 fermes** :

| Ferme | Sans taches | Avec taches |
| --- | --- | --- |
| PER_NKA | 102 | 139 |
| PER_RDMI | 548 | 511 |

Les 10 fermes annoncées par la page Zenodo ne sont pas dans l'archive. Le test du binôme (1 292 photos) couvre donc presque tout le jeu. **Il n'y a pas de ferme libre** : la section 1 ne peut pas s'appliquer, et **aucun entraînement n'est lancé**. Autre constat : sur ce jeu, la v10b ne rate déjà que 0,93 % des malades (chiffres du binôme). BanSpot aurait surtout réduit les fausses alertes au Kerala, pas les maladies ratées visées par Corentin.

## 6. Test « autre origine géographique » de la chaîne installée (écrit le 11 novembre 2026, vers 14 h 55, avant tout calcul sur BanSpot)

À la demande de Corentin, BanSpot devient **notre test**, regardé une seule fois. Il n'a jamais été lu par nos modèles. La v10b n'en a vu que 40 photos, celles du contrôle d'intégration.

- **Photos** : les 1 292 de la liste du binôme (`banspot_liste_test.csv`), lues dans l'archive d'origine (pas les copies réduites à 896 px du binôme).
- **Chaîne mesurée** : celle de `config.yaml` (aiguilleur ; « proche » → v10b ; « loin » → v2, politique b).
- **Mesures** :
  - « avec taches » sans alerte ;
  - « sans taches » en alerte, dont « à vérifier » ;
  - photos aiguillées « loin ».

  Une alerte est une maladie, « malade, non identifiée » ou « à vérifier ».
- **Rapporté pour comparaison** : l'ancienne chaîne (soupe en gros plan), calculée de la même façon, et les chiffres du binôme (0,93 % et 10,2 %).
- **Aucune décision n'est prise sur ce test** : ni seuil, ni modèle. Le résultat est écrit tel quel.

### Résultats (11 novembre 2026, vers 16 h 15, mesure unique)

Le protocole n'a pas changé depuis l'écriture de cette section (SHA-256 02fe2f73…, contrôlé avant lecture des chiffres). 1 292 photos : 646 « avec taches », 646 « sans taches ». Une seule photo est aiguillée « loin » : la chaîne installée et la v10b seule donnent donc les mêmes chiffres.

| Chaîne | « Avec taches » sans alerte | « Sans taches » en alerte | dont « à vérifier » |
| --- | --- | --- | --- |
| **Installée (v10b en gros plan)** | **6 / 646 (0,9 %)** | **61 / 646 (9,4 %)** | 26 |
| Ancienne (soupe en gros plan) | 30 / 646 (4,6 %) | 19 / 646 (2,9 %) | 0 (22 « je ne sais pas », sans alerte) |
| v10b, chiffres du binôme (copies 896 px) | 0,93 % | 10,2 % | — |

Par ferme, chaîne installée :

| Ferme | « Avec taches » sans alerte | « Sans taches » en alerte |
| --- | --- | --- |
| PER_NKA | 2 / 139 | 8 / 102 |
| PER_RDMI | 4 / 511 | 53 / 548 |

Réponses de la chaîne installée sur les 646 « avec taches » : 336 « malade, non identifiée », 280 Sigatoka noire, 19 fusariose, 5 « à vérifier », 6 saines. BanSpot ne dit pas de quelle maladie il s'agit : les noms donnés ne sont pas vérifiables ici.

Lecture : sur une origine géographique jamais vue (Kerala), la chaîne installée rate 5 fois moins de feuilles tachées que l'ancienne (6 contre 30), au prix de 42 fausses alertes de plus. Avec le coût de la section 3 (3 × ratées + fausses alertes), cela fait 79 contre 109. Les chiffres concordent avec ceux du binôme, calculés sur des copies réduites. **Aucune décision n'est prise sur ce test.**

Durée de calcul (processeur, 8 cœurs) : aiguilleur 8 min, v10b 54 min, v2 18 min, soupe 20 min. Fichiers : `out/maladies/banspot/bilan_banspot.json` et `reponses_banspot.csv`.
