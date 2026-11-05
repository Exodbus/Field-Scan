# Protocole du détecteur de comptage v3 (réentraînement de zéro)

Écrit le 4 novembre 2026 et **validé par Corentin le même jour**, **avant** la préparation des tuiles et avant tout entraînement. Rien ici ne doit être modifié après avoir vu un résultat du v3 ; toute modification ultérieure est datée et justifiée.

## 1. Découpage

Construit et vérifié par `scripts/decouper_comptage.py` (sorties dans `data/drone/decoupage_comptage/` : `decoupage.csv`, `groupes.csv`, `rapport.txt`). Découpage par groupe (site, orthomosaïque, vol), aucune photo, image d'origine, groupe ou fichier identique dans deux parties.

| Partie | Bananiers | Sans bananier |
| --- | --- | --- |
| Entraînement | ReforesTree Flora Pluas, Nestor Macias, Leonor Aspiazu (boîtes ReforesTree, incomplètes) ; vols 100_0221-0224 et corte (boîtes de Count banana plants) ; segmento ouest (x < 22 400 px) ; jeunes bananiers dji_0546 et dji_0548 (points manuels) | palmiers zone 52000_20000 ; cocotiers n° 0-899 |
| Validation | segmento est (x ≥ 22 400 px) ; jeunes bananiers dji_0544 (points manuels) ; Manuel Macias, référence manuelle MM1-MM2 | palmiers zone 44000_16000 ; cocotiers n° 900-1299 |
| Test | Carlos Vera Guevara, référence manuelle CG1-CG9 | palmiers zone 44000_4000 ; cocotiers n° 1300 et plus |
| Exclu | Carlos Vera Arteaga (200 m de CG) ; vidéos obliques ; dji_0545, 0547, 0549 (recouvrent les photos annotées) ; cacaoyères DJI et cacaoyères cacau_1, cacau_2, cacao (bananiers visibles mais jamais annotés, constaté au contrôle des tuiles préparées) ; dji_fly (boîtes mal centrées) ; banana_drone | |

Parmi les copies d'une même image Plants-bana, une copie en couleur est préférée (Roboflow a passé quelques copies d'entraînement de segmento en niveaux de gris).

Limites à écrire : CG a déjà été consulté pour les anciens modèles (la recette en a hérité, pas les poids) ; dji_0544 vient de la même parcelle que dji_0546 et dji_0548 (sans recouvrement d'image) ; les cocotiers sont découpés par blocs de numéros (proximité supposée).

## 2. Échelle des photos DJI (jeunes bananiers)

Pas de métadonnées (Roboflow les retire). Deux mesures indépendantes sur les photos d'entraînement :

- traces de roues sur dji_0548 : environ 145 px entre les centres des deux ornières ; voie d'un pick-up ou d'un tracteur 1,5 à 1,8 m, soit 1,0 à 1,25 cm/pixel ;
- espacement des plants annotés (dji_0546, dji_0548) : distance médiane au plus proche voisin 195 à 205 px ; plantation courante de bananiers à 2 à 2,5 m, soit 1,0 à 1,25 cm/pixel.

**Valeur retenue : 1,1 cm/pixel** (photo réduite d'un facteur 1,1 / 5 = 0,22 pour passer à 5 cm/pixel). L'incertitude (environ ± 15 %) est couverte par l'augmentation d'échelle de l'entraînement (0,8 à 1,25). Appariement de l'évaluation à 1 m = 91 px sur la photo d'origine.

## 2 bis. Bords des photos DJI : seul le centre est gardé

Ce sont des photos brutes, pas des orthomosaïques : vers les bords, les plants sont vus de biais (pseudo-troncs visibles de côté, rosettes peu lisibles, constat de l'annotateur et contrôle visuel des coins, des bords et du centre de dji_0548). La déformation croît avec la distance au centre (angle de vue). Avec 1,1 cm/pixel, la hauteur de vol est d'environ 40 m (DJI 20 Mpx, focale 8,8 mm, capteur 13,2 mm) ; le haut d'un plant de 2,5 m est décalé de r × 2,5 / 40 par rapport à son pied, r étant la distance au centre au sol.

**Zone gardée : disque de 2 000 px de rayon autour du centre de chaque photo** (22 m au sol, angle de vue au plus 29°, décalage au plus 1,4 m ; 61 % de la surface). Hors du disque : ni cible ni fond à l'entraînement (zone ignorée), ni détection ni point compté à l'évaluation.

| Rayon | Angle max | Surface | dji_0546 | dji_0548 | dji_0544 (validation) |
| --- | --- | --- | --- | --- | --- |
| aucun | — | 100 % | 163 | 191 | 154 |
| **2 000 px (retenu)** | **29°** | **61 %** | **119** | **135** | **118** |

Choix fait sur la géométrie et l'aspect des images, avant tout entraînement, sans aucun résultat de modèle.

## 3. Taille de cible des points manuels

Les cibles de l'entraînement sont des gaussiennes d'écart-type proportionnel à la taille de la couronne (taille / 24), mesurée sur les boîtes. Pour les points des jeunes bananiers (pas de boîte), **taille fixe de 2,5 m (50 px à 5 cm/pixel)** : envergure typique mesurée à l'œil sur dji_0548 (feuilles d'environ 2 m, plants espacés de 2 à 2,5 m), un peu sous la médiane des couronnes adultes de l'entraînement (environ 3 m). Les rejets ne sont pas des cibles ; ils sont ignorés à l'évaluation (comme les points incertains).

## 3 bis. Préparation des tuiles (précisions ajoutées le 4 novembre 2026, avant tout entraînement)

`scripts/preparer_comptage_v3.py`, d'après `decoupage.csv`.

- **Échelle, un facteur par source d'images** (même orthomosaïque ou même jeu de vols) : la couronne médiane annotée de la source est ramenée à sa **taille réelle typique** à 5 cm/pixel : bananier 3 m, cacaoyer 3 m, palmier à huile 9 m, cocotier 7 m. Changement par rapport au v2, qui ramenait toutes les couronnes de Multiple tree (palmiers compris) à la taille d'un bananier : un palmier de 9 m apparaissait alors comme un bananier de 2,5 m, ce qui a pu apprendre au modèle à rejeter les petites rosettes en étoile (jeunes bananiers). Photos DJI : 1,1 cm/pixel mesuré (section 2). ReforesTree : déjà à 5 cm.
- **Entraînement** : facteur aléatoire supplémentaire de 0,75 à 1,4 sur les images Roboflow (graine fixe), comme pour le v2 ; tuiles de 512 px, recouvrement 20 %, boîte gardée si au moins 50 % est dans la tuile.
- **Jeunes bananiers DJI** : tuiles de 512 px (photo réduite à 1 204 × 803 px), points hors du disque retirés, zone hors disque ignorée par la perte ; **rejets ignorés** (ni cible ni fond, rayon 1 m) ; tuiles répétées pour former **10 % des échantillons d'entraînement** (sinon une douzaine de tuiles parmi plus d'un millier).
- **Parts des échantillons d'entraînement à chaque époque** (`notebooks/entrainer_centres_v3_kaggle.ipynb`) : segmento ouest et Count 40 % (chaque tuile une fois) ; ReforesTree 25 % (tuiles répétées, règle reprise du v2) ; jeunes bananiers DJI 10 % (répétés) ; sans bananier au plus 25 %.
- **Recette inchangée par rapport au v2** : ResNet-18 ImageNet + décodeur FPN, perte focale de CenterNet (pondérée par la zone ignorée), découpes de 448 px, augmentations (échelle 0,8 à 1,25, couleurs, miroir, quarts de tour), AdamW, OneCycle, lots de 16, 30 époques, graine 2026.
- **Exemples sans bananier (palmiers, cocotiers)** : à chaque époque, un tirage au hasard qui forme au plus **25 % des échantillons d'entraînement** (sinon ils en feraient environ les deux tiers, les tuiles de palmiers étant nombreuses après mise à l'échelle).
- **Validation** : dji_0544 en une seule image (disque appliqué aux points et aux détections) ; segmento est en tuiles ; images sans bananier comptées en fausses détections rapportées au nombre d'arbres annotés.

## 4. Règle de choix (époque et seuil)

Mesures sur la validation seulement, appariement des centres à 1 m, rejets et incertains ignorés :

- F1 segmento est (plantation dense, boîtes Roboflow) ;
- F1 jeunes bananiers dji_0544 (points manuels) ;
- F1 MM1-MM2, pieds mères seuls (agroforesterie, petite référence : 69 pieds) ;
- fausses détections sur les images de validation sans bananier (palmiers 44000_16000, cocotiers 900-1299), rapportées au nombre d'arbres annotés.

**Choix** : couple (époque, seuil), seuil de 0,10 à 0,60 par pas de 0,05, qui maximise la moyenne des trois F1, parmi les couples dont les fausses détections sur les images sans bananier restent sous 5 % des arbres. Si aucun couple ne respecte la contrainte, celui qui a le moins de fausses détections.

**Adoption** : le v3 remplace le v2 par principe de protocole (le v2 a été entraîné sur des images qui sont maintenant en validation : aucune comparaison loyale n'est possible sur la validation, et comparer sur le test serait un choix sur le test). Les deux sont mesurés une fois sur le test et rapportés tous les deux.

## 4 bis. Fourchette d'estimation du bulletin (règle écrite le 5 novembre 2026, avant de la mesurer)

Pieds estimés = détectés × [coefficient_bas, coefficient_haut]. Rapport réel / détecté du v3 au seuil retenu, mesuré avec le détecteur de la chaîne (`fieldscan.drone.DetecteurCentres`, ONNX sur processeur), sur les **trois validations seulement** : segmento est (plantation dense, boîtes Roboflow), dji_0544 dans le disque (jeunes plants, points manuels), MM1-MM2 (agroforesterie, mères seules). **coefficient_bas = le plus petit des trois rapports, coefficient_haut = le plus grand.** Jamais CG. Script : `scripts/mesurer_fourchette_v3.py`.

## 5. Test

Regardé une seule fois, après le choix : F1 et erreur de comptage sur CG1-CG9 (tous pieds et mères seules), fausses détections sur les images de test sans bananier. Aucun réglage après.
