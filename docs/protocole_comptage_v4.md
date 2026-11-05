# Protocole du détecteur de comptage v4 (plantations commerciales ajoutées)

Écrit le 5 novembre 2026 et validé par Corentin le même jour, **avant** la préparation des tuiles et tout entraînement. Reprend le protocole v3 (`docs/protocole_comptage_v3.md`) ; seuls les points ci-dessous changent. Toute modification ultérieure est datée et justifiée.

**Modification 1 du 5 novembre 2026 (avant toute préparation et tout entraînement)** : pas de nouvelle annotation manuelle (choix de Corentin, temps disponible). El Oro EO3-EO4 n'a donc pas de référence et **sort de la validation** ; il reste un contrôle visuel (comptes v3 / v4 / modèle hébergé Roboflow, sans référence).

**Modification 2 du 5 novembre 2026 (avant toute préparation et tout entraînement)** : le test doit couvrir trois situations : plantation dense, plantation espacée, plantation mêlée à d'autres arbres avec rejets. **segmento est passe de la validation au test** (plantation dense) ; la validation garde **trois** F1. Un **contrôle visuel** des détections est fait à la fin du test sur des tuiles tirées dès maintenant (section 8). Les sections ci-dessous intègrent ces deux modifications.

**Modification 3 du 5 novembre 2026 (pendant l'entraînement Kaggle, avant tout résultat de validation ou de test du v4)** : ajout d'un **test de plantation dense industrielle indépendant** : `banano-qpl6j` (Roboflow Universe, Jorge's Workspace, CC BY 4.0), 71 tuiles d'une orthomosaïque de bananeraie à couronnes jointives, une boîte par plant. Il ne sert ni au choix ni à l'adoption (déjà automatiques dans le carnet) ; il est mesuré une seule fois, en local, pour le v3 (seuil 0,20) et le v4 (seuil retenu), avec les fichiers `.onnx`. Contrôles avant mesure : doublons, fuites (nom d'origine, MD5) avec tous les jeux, complétude des annotations (planche). Échelle : règle des boîtes (couronne médiane ramenée à 3 m). Images gardées entières, appariement à 1 m. Si l'export n'est pas obtenu ou si les annotations sont jugées incomplètes au contrôle (avant toute mesure), ce test est abandonné et la raison est notée.

**Note du 5 novembre 2026 (vérification du code, avant l'entraînement)** : lors de l'essai local du carnet (3 images par groupe, 2 époques), le v3 a été mesuré sur 3 images de segmento est et 3 de `banana_tree_detection`, et ces chiffres se sont affichés une fois avant que l'affichage du test soit masqué en essai local. Aucune règle n'a été modifiée après (règles commitées avant, décisions automatiques dans le carnet).

**Préparation (5 novembre 2026)** : échelles obtenues par la règle de la section 3 : `plantas_platano` 100_metros 2,42 cm/px, lote_2 2,60, lote_2_parte_2 2,92 ; `banana_tree_detection` 3,14 ; `platano_lasuiza` couronne médiane 94 px (facteur 0,635). Images de validation et de test bananiers gardées entières (pas de tuiles qui se recouvrent). Contrôle visuel des tuiles préparées : cibles centrées sur les plants.

## 0. Pourquoi une v4

Le v3 a une bonne précision mais un rappel faible hors de ses données : CG1-CG9 (test) rappel 0,13 ; El Oro (bananeraie commerciale, contrôle visuel sans référence) 302 pieds détectés contre 388 pour le modèle hébergé Roboflow et 399 pour le v2, les points du v3 étant presque tous retrouvés par les deux autres. La validation du v3 ne contenait presque pas de plantation commerciale vue à 2-7 cm. La v4 ajoute des plantations annotées et une validation qui en contient.

## 1. Nouvelles sources (toutes CC BY 4.0, vérifiées le 5 novembre 2026)

| Source | Contenu | Version | Contrôles |
| --- | --- | --- | --- |
| `plantas_platano` (Roboflow, agromatica2025) | 304 tuiles de 3 orthomosaïques (`100_metros`, `lote_2`, `lote_2_parte_2`), jeunes plantains en rangs associés à une autre culture ; un point (boîte fixe de 13 px) au centre de chaque plant | export du 5 nov. 2026, sans augmentation ni redimensionnement (tuiles de 512 px agrandies en 640 par l'auteur, sans recouvrement) | annotations complètes et centrées (contrôle visuel), aucun doublon |
| `platano_lasuiza` (Roboflow, Daniel F Tovar R) | 433 tuiles de 640 px de plusieurs orthomosaïques non distinguables par le nom ; jeunes et moyens plantains ; boîtes | export du 5 nov. 2026, sans augmentation | 24 images avec les cadres d'annotation dessinés dans les pixels (retirées) ; boîtes souvent chevauchantes, quelques tuiles incomplètes |
| `banana_tree_detection` (Roboflow, Elliot Su) | 416 tuiles de 1 280 px d'une orthomosaïque (vol du 18/10/2022), jeunes bananiers en rangs sur paillage ; boîtes | v1 du 22 déc. 2022, sans augmentation | annotations complètes (contrôle visuel) ; une vingtaine de doublons (retirés) |
| El Oro (OpenAerialMap, UTMACH, 12/11/2018, 6,4 cm/px, géoréférencé) | bananeraie commerciale du campus agronomique de Machala : bande ouest (fermée) et bande est (ouverte) | — | pas de référence : contrôle visuel seulement |

Aucune image commune (nom d'origine, MD5) avec les jeux du v3. DS-v1/DS-v2 (Zenodo) écarté : photos à quelques mètres, lésions de cercosporiose annotées. Guangxi (Science Data Bank) : téléchargement non abouti, non utilisé.

## 2. Découpage (changements par rapport au v3)

| Partie | Contenu |
| --- | --- |
| Entraînement | celui du v3 + `plantas_platano` `lote_2` et `lote_2_parte_2` + `platano_lasuiza` (sans les 24 images à cadres dessinés, une seule copie par image) |
| Validation | `plantas_platano` `100_metros` (orthomosaïque entière) ; jeunes bananiers dji_0544 ; MM1-MM2 ; images sans bananier du v3 (palmiers 44000_16000, cocotiers 900-1299) |
| Test | **plantation dense** : segmento est (boîtes Roboflow) ; **plantation espacée** : `banana_tree_detection` (orthomosaïque entière, une copie par image) ; **agroforesterie avec rejets** : CG1-CG9 ; images sans bananier du v3 (palmiers 44000_4000, cocotiers 1300 et plus) |
| Contrôle visuel seulement | El Oro EO1-EO4 (pas de référence) |

Limites :
- `100_metros`, `lote_2` et `lote_2_parte_2` viennent probablement de la même ferme : la validation plantain est optimiste.
- segmento est partage l'orthomosaïque de segmento ouest (entraînement) : le test dense est optimiste ; ses boîtes Roboflow sont moins complètes en zone mélangée et contiennent quelques doublons. Le v3 a choisi son époque et son seuil sur segmento est : sur cette partie du test, la comparaison v3 / v4 avantage le v3.
- Aucun rejet n'est annoté dans `banana_tree_detection` ; les rejets ne sont mesurés que sur CG (test) et MM (validation).
- Aucune bananeraie commerciale indépendante à couronnes jointives n'a de référence (El Oro : contrôle visuel).

## 3. Échelle (règle fixée avant la préparation)

- **Sources avec boîtes couvrant la plante** (`platano_lasuiza`) : comme au v3, couronne médiane ramenée à 3 m.
- **Sources annotées en points ou avec des plants trop jeunes pour la règle des 3 m** (`plantas_platano`, chaque orthomosaïque à part ; `banana_tree_detection`) : distance médiane au plus proche voisin entre plants annotés ramenée à **2,5 m** (espacement courant en plantation). Estimations : `plantas_platano` environ 2,5 à 2,9 cm/px, `banana_tree_detection` environ 3 cm/px.
- Taille de cible des points : 2,5 m (comme les jeunes bananiers DJI du v3).
- Incertitude d'environ 20 %, couverte par l'augmentation d'échelle de l'entraînement (0,8 à 1,25).

## 4. Parts des échantillons d'entraînement

Plantations (`plantas_platano` entraînement + `platano_lasuiza`) **20 %** ; segmento ouest et Count 30 % ; ReforesTree 20 % ; jeunes bananiers DJI 10 % ; sans bananier au plus 20 % (tirage renouvelé à chaque époque). Recette du v3 inchangée par ailleurs (réseau, perte pondérée, augmentations, 30 époques, graine 2026).

## 5. Règle de choix (époque et seuil)

Mêmes seuils (0,10 à 0,60 par pas de 0,05), même appariement (1 m), même contrainte (fausses détections sur les images de validation sans bananier sous 5 % des arbres). **Moyenne des trois F1 de validation** : `plantas_platano` `100_metros`, jeunes bananiers dji_0544, MM1-MM2 (mères seules).

## 6. Adoption (v4 contre v3)

Le v3 n'a vu aucune des trois validations à l'entraînement ; il est mesuré sur les mêmes trois validations, avec le **meilleur seuil pour lui** sur cette validation (même grille, même contrainte). **Le v4 remplace le v3 si sa moyenne est strictement meilleure.** Sinon le v3 reste en place (seuil 0,20 de son protocole). Décision prise avant de regarder le test.

## 7. Test (une seule fois, v3 et v4 rapportés tous les deux)

segmento est (F1 contre les boîtes Roboflow), `banana_tree_detection` (F1 et erreur de comptage), CG1-CG9 (mères seules et tous pieds), images de test sans bananier (fausses détections rapportées au nombre d'arbres). Aucun réglage après.

## 8. Contrôle visuel en fin de test (tuiles tirées le 5 novembre 2026, avant tout résultat)

Liste dans `docs/controle_visuel_v4.json` (`scripts/tirer_controle_visuel_v4.py`, graine 2026) : 6 images de segmento est, 6 de `banana_tree_detection`, les carrés El Oro EO1-EO4. Planches côte à côte v3 / v4 / modèle hébergé Roboflow (`plants-bana/3`) sur ces tuiles seulement ; l'appréciation de Corentin (oublis, fausses détections) est rapportée telle quelle, à côté des chiffres, et ne change ni le choix ni l'adoption.
