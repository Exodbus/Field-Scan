# Protocole du détecteur de comptage v5 (plantation dense industrielle)

Écrit le 5 novembre 2026 et validé par Corentin le même jour, **avant** toute préparation et tout entraînement du v5. Reprend le protocole v4 (`docs/protocole_comptage_v4.md`) ; seuls les points ci-dessous changent. Toute modification ultérieure est datée et justifiée.

## 0. Pourquoi une v5 (décision informée par le test du v4, à écrire tel quel)

Le test du v4 (regardé une fois) montre un rappel faible en plantation : dense 0,45 (segmento est), espacée 0,59 (`banana_tree_detection`) ; le contrôle visuel d'El Oro va dans le même sens (« la v4 en détecte moins en milieu dense »). La validation du v4 ne contenait pas de plantation dense indépendante : la validation plantain (100_metros) vient probablement de la même ferme que l'entraînement. La v5 ajoute une plantation dense industrielle en entraînement **et** en validation, et un **test dense neuf** que ni le v3 ni le v4 n'ont vu. Comme cette décision vient d'un résultat de test, la v5 est jugée surtout sur le test neuf (`banano`).

## 1. Nouvelles sources (vérifiées sans modèle le 5 novembre 2026, `scripts/analyser_jeu_roboflow.py`)

| Source | Contenu | Contrôles |
| --- | --- | --- |
| `banavista` (Roboflow, banana-detection-4hbck, CC BY 4.0, export du 5 nov. 2026 sans augmentation) | Tagum (Philippines) : 348 photos DJI brutes 4 000 × 3 000 (environ 1,2 cm/px) de bananeraies denses et d'une pépinière en pots ; 15 orthophotos ; boîtes `Bananas` (52 087) et `Others` (870) | 50 photos en double (une copie gardée) ; 8 noms communs avec Plants-bana (DJI_0542 à 0549) : photos différentes vérifiées à l'œil (simple coïncidence du compteur de l'appareil) ; recouvrement médian 81 % entre photos voisines |
| `banano_dense` (Roboflow, banano-qpl6j, CC BY 4.0, export du 5 nov. 2026 sans augmentation) | 71 tuiles de 1 024 px d'une orthomosaïque (10 colonnes × 15 rangées) de bananeraie à couronnes jointives ; 5 078 boîtes | aucun doublon, aucune fuite ; 49 boîtes aberrantes (plus de 3 fois la taille médiane, jusqu'à une tuile entière) |

Aucun modèle n'a été mesuré sur ces deux jeux avant ce protocole.

## 2. Découpage (ajouts au découpage v4, qui reste inchangé par ailleurs)

**banavista** : photos DJI seulement (orthophotos écartées : on ne sait pas de quelles photos elles sont tirées, risque de fuite) ; une copie par photo ; noms préfixés `bv_` (évite la collision avec dji_0544 des jeunes bananiers).
- Deux sessions séparées par une longue interruption de numérotation : **A** (DJI_0542 à 0682 : bandes de plantation dense et pépinière en pots) et **B** (DJI_0757 à 0945 : une mission de cartographie d'une plantation dense, en lignes de vol de 13 à 21 photos).
- **Entraînement** : session A entière ; session B, lignes DJI_0757 à 0841.
- **Exclu (bande tampon)** : session B, DJI_0842 à 0861 (lignes voisines des deux côtés ; le recouvrement latéral entre lignes n'a pas été détecté par appariement de points, mais une canopée répétitive peut le masquer).
- **Validation** : session B, DJI_0862 à 0945 (4 lignes, environ 8 800 plants).

**banano_dense** : **test** (orthomosaïque entière), jamais utilisé ailleurs.

Limites : sessions A et B sans doute de la même ferme (validation dense optimiste par rapport à une zone jamais vue) ; banano_dense est une seule orthomosaïque.

## 3. Préparation

- **banavista** : photos brutes, bords vus de biais : **disque de 2 000 px** autour du centre (même règle que les jeunes bananiers DJI ; angle de vue au plus 29° vers 40 m) ; hors du disque, zone ignorée à l'entraînement, rien de compté à la mesure. Échelle : couronne médiane `Bananas` ramenée à 3 m (règle des boîtes). `Others` n'est pas une cible (fond).
- **banano_dense** : boîtes de plus de 3 fois la taille médiane retirées ; échelle : couronne médiane ramenée à 3 m ; tuiles gardées entières pour la mesure.
- Le reste comme le v4.

## 4. Parts des échantillons d'entraînement

Autres (segmento ouest, Count) 25 % ; plantations (`plantas_platano`, `platano_lasuiza`, banavista entraînement) 25 % ; ReforesTree 20 % ; jeunes bananiers DJI 10 % ; sans bananier au plus 20 %. Recette inchangée (30 époques, graine 2026).

## 5. Règle de choix

Mêmes seuils, même appariement, même contrainte (fausses détections sans bananier sous 5 %). **Moyenne de quatre F1 de validation** : banavista session B (dense), `plantas_platano` 100_metros, jeunes bananiers dji_0544, MM1-MM2 (mères seules).

## 6. Adoption (v5 contre v4)

Le v4 n'a vu aucune image de banavista. Il est mesuré sur la même validation, avec son meilleur seuil (même grille, même contrainte). **Le v5 remplace le v4 si sa moyenne est strictement meilleure.** Décision avant tout test.

## 7. Test (une seule fois, v4 et v5 rapportés)

**banano_dense (test neuf, dense industriel)**, segmento est, `banana_tree_detection`, CG1-CG9, images sans bananier. Aucun réglage après.

## 8. Contrôle visuel en fin de test

Images tirées avant tout résultat (graine 2026) : 6 tuiles de banano_dense (parmi celles qui contiennent au moins 20 boîtes) ajoutées à la liste du v4 (`docs/controle_visuel_v5.json`). Planches v4 / v5.
