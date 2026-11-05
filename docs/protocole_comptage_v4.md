# Protocole du détecteur de comptage v4 (plantations commerciales ajoutées)

Écrit le 5 novembre 2026 et validé par Corentin le même jour, **avant** l'annotation de la validation El Oro, la préparation des tuiles et tout entraînement. Reprend le protocole v3 (`docs/protocole_comptage_v3.md`) ; seuls les points ci-dessous changent. Toute modification ultérieure est datée et justifiée.

## 0. Pourquoi une v4

Le v3 a une bonne précision mais un rappel faible hors de ses données : CG1-CG9 (test) rappel 0,13 ; El Oro (bananeraie commerciale, contrôle visuel sans référence) 302 pieds détectés contre 388 pour le modèle hébergé Roboflow et 399 pour le v2, les points du v3 étant presque tous retrouvés par les deux autres. La validation du v3 ne contenait presque pas de plantation commerciale vue à 2-7 cm. La v4 ajoute des plantations annotées et une validation qui en contient.

## 1. Nouvelles sources (toutes CC BY 4.0, vérifiées le 5 novembre 2026)

| Source | Contenu | Version | Contrôles |
| --- | --- | --- | --- |
| `plantas_platano` (Roboflow, agromatica2025) | 304 tuiles de 3 orthomosaïques (`100_metros`, `lote_2`, `lote_2_parte_2`), jeunes plantains en rangs associés à une autre culture ; un point (boîte fixe de 13 px) au centre de chaque plant | export du 5 nov. 2026, sans augmentation ni redimensionnement (tuiles de 512 px agrandies en 640 par l'auteur, sans recouvrement) | annotations complètes et centrées (contrôle visuel), aucun doublon |
| `platano_lasuiza` (Roboflow, Daniel F Tovar R) | 433 tuiles de 640 px de plusieurs orthomosaïques non distinguables par le nom ; jeunes et moyens plantains ; boîtes | export du 5 nov. 2026, sans augmentation | 24 images avec les cadres d'annotation dessinés dans les pixels (retirées) ; boîtes souvent chevauchantes, quelques tuiles incomplètes |
| `banana_tree_detection` (Roboflow, Elliot Su) | 416 tuiles de 1 280 px d'une orthomosaïque (vol du 18/10/2022), jeunes bananiers en rangs sur paillage ; boîtes | v1 du 22 déc. 2022, sans augmentation | annotations complètes (contrôle visuel) ; une vingtaine de doublons (retirés) |
| El Oro (OpenAerialMap, UTMACH, 12/11/2018, 6,4 cm/px, géoréférencé) | bananeraie commerciale du campus agronomique de Machala : bande ouest (fermée) et bande est (ouverte) | — | référence manuelle à créer sur EO3 et EO4 (bande est), à l'aveugle |

Aucune image commune (nom d'origine, MD5) avec les jeux du v3. DS-v1/DS-v2 (Zenodo) écarté : photos à quelques mètres, lésions de cercosporiose annotées. Guangxi (Science Data Bank) : téléchargement non abouti, non utilisé.

## 2. Découpage (ajouts au découpage du v3)

| Partie | Ajouts |
| --- | --- |
| Entraînement | `plantas_platano` `lote_2` et `lote_2_parte_2` ; `platano_lasuiza` (sans les 24 images à cadres dessinés, une seule copie par image) |
| Validation | `plantas_platano` `100_metros` (orthomosaïque entière) ; El Oro EO3 et EO4 (référence manuelle à l'aveugle) |
| Test | `banana_tree_detection` (orthomosaïque entière, une copie par image) |
| Non utilisé | bande ouest d'El Oro (EO1, EO2) et reste du campus (bananiers isolés non annotés) |

Limites : `100_metros`, `lote_2` et `lote_2_parte_2` viennent probablement de la même ferme (même auteur) : la validation plantain est optimiste. EO3 et EO4 viennent d'un seul vol et d'une seule parcelle ; des détections ont déjà été regardées sur EO3 (planches de comparaison v2/v3) avant l'annotation.

## 3. Échelle (règle fixée avant la préparation)

- **Sources avec boîtes couvrant la plante** (`platano_lasuiza`) : comme au v3, couronne médiane ramenée à 3 m.
- **Sources annotées en points ou avec des plants trop jeunes pour la règle des 3 m** (`plantas_platano`, chaque orthomosaïque à part ; `banana_tree_detection`) : distance médiane au plus proche voisin entre plants annotés ramenée à **2,5 m** (espacement courant en plantation). Estimations : `plantas_platano` environ 2,5 à 2,9 cm/px, `banana_tree_detection` environ 3 cm/px.
- **El Oro** : géoréférencé (6,44 cm/px), lu à 5 cm/px.
- Taille de cible des points : 2,5 m (comme les jeunes bananiers DJI du v3).
- Incertitude d'environ 20 %, couverte par l'augmentation d'échelle de l'entraînement (0,8 à 1,25).

## 4. Parts des échantillons d'entraînement

Comme au v3, avec une part supplémentaire : plantations commerciales (`plantas_platano` entraînement + `platano_lasuiza`) **20 %** ; segmento ouest et Count 30 % ; ReforesTree 20 % ; jeunes bananiers DJI 10 % ; sans bananier au plus 20 %.

## 5. Règle de choix (époque et seuil)

Mêmes seuils (0,10 à 0,60 par pas de 0,05), même appariement (1 m), même contrainte (fausses détections sur les images de validation sans bananier sous 5 % des arbres). **Moyenne des cinq F1 de validation** : segmento est, jeunes bananiers dji_0544, MM1-MM2 (mères seules), `plantas_platano` `100_metros`, El Oro EO3-EO4.

## 6. Adoption (v4 contre v3)

Le v3 n'a vu aucune des cinq validations : la comparaison est loyale. Le v3 est mesuré sur les mêmes cinq validations, avec le **meilleur seuil pour lui** sur cette validation (même grille, même contrainte). **Le v4 remplace le v3 si sa moyenne est strictement meilleure.** Sinon le v3 reste en place (seuil 0,20 de son protocole). Le choix se fait avant de regarder le test.

## 7. Test (une seule fois, v3 et v4 rapportés tous les deux)

CG1-CG9 (mères seules et tous pieds), `banana_tree_detection` (F1 et erreur de comptage), images de test sans bananier (palmiers 44000_4000, cocotiers 1300 et plus). Aucun réglage après.
