# Protocole du détecteur de comptage v5 (plantation dense industrielle)

Écrit le 5 novembre 2026 et validé par Corentin le même jour, **avant** toute préparation et tout entraînement du v5. Reprend le protocole v4 (`docs/protocole_comptage_v4.md`) ; seuls les points ci-dessous changent. Toute modification ultérieure est datée et justifiée.

**Préparation (5 novembre 2026, avant l'entraînement)** : découpage v5 sans fuite (photo, image, groupe, MD5) ; banavista : 123 photos de la session A et 71 photos des lignes DJI_0757 à 0841 en entraînement, 20 photos de bande tampon exclues, 84 photos en validation (8 838 plants avant disque), 14 orthophotos exclues ; échelles par la règle des couronnes : banavista 1,07 à 1,13 cm/px, banano_dense 2,74 cm/px (49 boîtes aberrantes de plus de 328 px retirées). Archive `comptage_v5_5cm.zip` (953 Mo). Carnet vérifié en local sur un petit échantillon ; le test y est calculé sans être affiché.

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

## 7 bis. Fourchette du bulletin (règle écrite le 5 novembre 2026, après l'adoption, avant de la mesurer)

Même règle que le v4 (protocole v4, section 7 bis), sur les **quatre validations du v5**. On calcule le rapport réel / détecté du v5 à son seuil (0,30), avec le détecteur de la chaîne, sur :
- banavista session B (disque de 2 000 px) ;
- `plantas_platano` 100_metros ;
- jeunes bananiers dji_0544 (disque) ;
- MM1-MM2 (mères seules).

coefficient_bas = plus petit rapport, coefficient_haut = plus grand. Jamais le test.

## 8. Contrôle visuel en fin de test

Images tirées avant tout résultat (graine 2026) : 6 tuiles de banano_dense (parmi celles qui contiennent au moins 20 boîtes) ajoutées à la liste du v4 (`docs/controle_visuel_v5.json`). Planches v4 / v5.

## 9. Résultats (5 novembre 2026, carnet Kaggle v5, 66 min sur T4)

**Choix (validation)** : époque 15, seuil 0,30. F1 : dense banavista 0,777, plantain 0,885, jeunes 0,893, MM 0,857 (moyenne 0,853). Fausses détections sans bananier : 0,26 % (17).

**Adoption** : le v4 (ONNX) est mesuré sur la même validation, avec son meilleur seuil 0,40. F1 : dense 0,718, plantain 0,893, jeunes 0,889, MM 0,789 (moyenne 0,822). **Le v5 remplace le v4** (écart de 0,031).

Le choix de l'époque tient en partie à un pic de MM : 0,857 à l'époque 15, alors que MM varie de 0,69 à 0,86 selon les époques (environ 70 arbres). L'adoption ne dépend pas de ce pic : de l'époque 13 à l'époque 30, la moyenne du v5 reste entre 0,829 et 0,853, au-dessus des 0,822 du v4.

**Test (une seule fois)** :

| Test | v4 (seuil 0,40) | v5 (seuil 0,30) |
| --- | --- | --- |
| dense industrielle, banano (test neuf) | P 0,851, R 0,747, F1 0,796 (4 412 détectés / 5 029 annotés) | P 0,841, R 0,776, F1 0,807 (4 641 / 5 029) |
| dense, segmento est | P 0,865, R 0,452, F1 0,594 (2 127 / 4 067) | P 0,807, R 0,577, F1 0,673 (2 908 / 4 067) |
| espacée, `banana_tree_detection` | P 0,974, R 0,586, F1 0,732 (23 336 / 38 790) | P 0,943, R 0,384, F1 0,546 (15 816 / 38 790) |
| agroforesterie, CG mères seules | P 0,777, R 0,252, F1 0,380 | P 0,848, R 0,193, F1 0,315 |
| CG tous pieds | F1 0,363 | F1 0,295 |
| images sans bananier | 5 fausses détections / 7 876 arbres (0,1 %) | 36 / 7 876 (0,5 %) |

Le v4 retrouve, à 0,002 près, les chiffres de son propre test (protocole v4, section 9) : la mesure est reproductible. ONNX v5 : 45 Mo, écart maximal avec PyTorch 6e-6, environ 2 s par hectare.

**Lecture** :
- **Dense, test neuf (banano)** : le gain est faible, +0,011 de F1 (rappel 0,776 contre 0,747). Sur la validation dense, il était de +0,059. Cette validation vient de la même ferme que l'entraînement (limite écrite à la section 2) et a surestimé le gain.
- **Segmento est** (dense, déjà vu au test du v3 et du v4) : le v5 regagne une partie du rappel perdu par le v4 (0,577 contre 0,452), sans revenir au niveau du v3 (F1 0,733).
- **Plantation espacée** : le v5 recule nettement, F1 0,546 contre 0,732 (rappel 0,384 contre 0,586) ; le v3 faisait 0,814. Aucune validation du v5 n'est une plantation espacée indépendante : la validation plantain (100_metros) n'a baissé que de 0,008 et n'a pas signalé ce recul.
- **Agroforesterie (CG)** : le v5 recule aussi, 0,315 contre 0,380, avec plus de précision et moins de rappel.
- **Images sans bananier** : 0,5 % de fausses détections, sous la limite de 5 %.
- **D'une version à l'autre**, chaque gain sur un type de plantation s'accompagne d'une perte sur un autre. Du v3 au v4, l'agroforesterie s'améliore et les plantations reculent ; du v4 au v5, le dense s'améliore, l'espacée et l'agroforesterie reculent. Un seul détecteur avec un seul seuil couvre mal les trois situations.
- **Conformément au protocole, le v5 reste adopté** et le compromis est rapporté tel quel. Revenir au v4 à cause de ce test serait une décision prise sur le test. Dans les plantations espacées, le bulletin sous-comptera ; la fourchette, mesurée sur la validation, ne couvre pas ce cas.
- **Limite** : segmento est, `banana_tree_detection` et CG ont servi au test du v3 et du v4, et le test du v4 a motivé la v5. Ce ne sont plus des tests vierges. Pour cette version, seul banano l'était.
