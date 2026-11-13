# Journal de l'agent M-banc (nuit du 12 au 13 novembre 2026)

Essais sans entraînement M1 à M3 sur la chaîne maladies installée (aiguilleur ; proche → v10b ; loin → v2). Règles : `docs/plan_nuit_2026-11-12.md`, section 4.4, appliquées telles quelles. Corentin dort : les choix sont pris ici et notés.

## 22 h 18 : banc et référence

- Banc : `scripts/m12_banc_commun.py`. Il ne lit que les probabilités en cache (`out/maladies/v10b`, `cinq_classes`, `dinov2_ft`) et importe `decider_convnext` de la chaîne.
- Référence recalculée, identique aux chiffres du 11/11 (vérifié par `assert`) :

| Jeu | Malades sans alerte | Saines en alerte (dont « à vérifier ») | Coût (points) |
| --- | --- | --- | --- |
| Validation Tanzanie | 9 / 2 001 | 57 / 1 000 (25) | 7,0 |
| TDTU | 83 / 1 059 | 177 / 577 (38) | 54,2 |
| PSFD | 149 / 738 | pas de saine | 60,6 |
| Éthiopie | 179 / 1 134 | 43 / 155 (18) | 75,1 |
| **Coût moyen** | | | **49,23** |

- Sigatoka nommée en validation : 872 / 1 000.
- Photos envoyées vers la branche « loin » (v2) : validation 15, TDTU 473 / 1 636, PSFD 211 / 738, Éthiopie 199 / 1 289. Dans les pays, un quart des photos ne passe donc pas par la v10b.
- Constat sur le code : avec la règle B, une photo proche est sans alerte si et seulement si P(saine) ≥ `seuil_confiance` (tant que `seuil_alerte` ≥ 1 − `seuil_confiance`). L'alerte de la v10b est donc déjà « 1 − P(saine) seule » ; `seuil_alerte`, `seuil_nom` et le seuil v11 ne changent que le libellé (maladie nommée, « malade, non identifiée », « à vérifier »).
- Taille des photos : validation environ 256 × 341 px, TDTU 244 × 244, PSFD 256 × 256, Éthiopie 150 × 113. Un morceau de photo (M2) sera donc très agrandi avant lecture.

## 22 h 19 : choix écrits avant les essais

- Juges (BanSpot, Cordana du Pérou) : aucun fichier lu avant la liste des finalistes. Le seul code qui les charge est `charger_juges()`, appelé par `scripts/m12_banc_juges.py`.
- Comptage des essais : une configuration évaluée sur le réglage = un essai (chaque point de grille compte).
- Choix des finalistes (3 au plus) : parmi les candidats qui remplissent la règle « finaliste » du plan, le coût moyen le plus bas dans chaque famille (M1, M2, M3, idées libres), puis les 3 coûts les plus bas. Un optimum pointu est écarté : le candidat doit rester finaliste quand son seuil bouge d'un pas de grille dans les deux sens ; sinon je prends le point voisin le plus proche qui a cette propriété.
- M2 : échantillon de 400 photos par jeu, graine 2026, tiré par `scripts/m12_banc_m2_morceaux.py` avant toute lecture ; grille 2 × 2 lancée en tâche de fond à 22 h 19 (processeur). Extension seulement si le gain d'échantillon dépasse 1 point de coût.

## 22 h 22 : M3, M1 et idées libres sur le réglage (343 essais)

Scripts : `scripts/m12_banc_m1_m3.py` (252 essais), `scripts/m12_banc_combinaisons.py` (66), `scripts/m12_banc_m3_libelles.py` (25). Sorties et journaux complets dans `out/maladies/nuit_1112/banc/` (`m1_m3.log`, `combinaisons.log`, `m3_libelles.log`, `essais_*.json`). Coût en points ; « F » = remplit la règle « finaliste ».

**M3 (seuils de la v10b seule) : aucun finaliste.**
- Seuil de confiance (règle B), 31 valeurs de 0,30 à 0,90 : le coût moyen reste entre 48,1 et 49,3 de 0,52 à 0,76. La courbe est plate : le seuil installé (0,5186) est déjà au bord du plateau. Le minimum (48,12 à 0,68) gagne 1,1 point mais met 116 saines en alerte en Tanzanie (limite 77).
- Réglage « robuste » (pire coût des 4 jeux le plus bas) : seuil 0,54, pire coût 73,9 (Éthiopie) au lieu de 75,1, coût moyen 48,36. Gain de 0,9 point : sous la barre de 1 point.
- `seuil_alerte` (0,40 à 0,85) et seuil v11 (0,50 à 0,85), 25 couples : aucun effet sur le nombre d'alertes tant que `seuil_alerte` ≥ 1 − seuil de confiance. Ils déplacent seulement des réponses entre « à vérifier » et « malade, non identifiée » (saines « à vérifier » en validation : 2 à 38 sur 57). Sigatoka nommée : 872 partout.

**M1 (mélange v10b + soupe en gros plan, branche loin inchangée).** La soupe est ramenée aux 4 classes de la v10b avec P(autre) = 0 ; la décision est celle de la v10b sur le mélange.

| Candidat | Coût moyen | Validation | TDTU | PSFD | Éthiopie | F |
| --- | --- | --- | --- | --- | --- | --- |
| Chaîne installée | 49,23 | 9 ; 57 (25) ; sig 872 | 83 ; 177 | 149 | 179 ; 43 | |
| Moyenne, poids soupe 0,25, seuils v10b | 47,57 | 7 ; 47 (25) ; sig 885 | 79 ; 166 | 154 | 192 ; 31 | oui |
| Moyenne 0,5, seuils v10b | 47,35 | 6 ; 39 (26) ; sig 899 | 83 ; 150 | 166 | 219 ; 15 | non (PSFD et Éthiopie perdent plus de 2 points) |
| Moyenne 0,75, seuils v10b | 59,60 | 8 ; 29 ; sig 929 | 112 ; 133 | 257 | 274 ; 4 | non |
| Moyenne géométrique 0,5, seuils v10b | 48,78 | 6 ; 39 ; sig 908 | 95 ; 136 | 168 | 246 ; 10 | non |
| Moyenne 0,5 avec températures 0,79 / 0,61 | 50,09 | 7 ; 34 ; sig 925 | 95 ; 139 | 183 | 247 ; 8 | non |
| Alerte si l'un des deux alerte | 46,75 | 6 ; 61 (25) ; sig 874 | 71 ; 190 | 139 | 159 ; 44 | oui |
| Alerte si les deux alertent | 72,14 | 12 ; 11 | 165 ; 106 | 308 | 358 ; 1 | non |
| Moyenne 0,25, seuil 0,62 | 45,97 | 6 ; 72 (50) ; sig 885 | 65 ; 191 | 136 | 151 ; 45 | oui (plateau 0,52 à 0,62) |
| Moyenne 0,5, seuil 0,66 | 44,62 | 4 ; 64 (51) ; sig 899 | 63 ; 200 | 137 | 149 ; 37 | oui (plateau 0,56 à 0,68) |
| Moyenne 0,75, seuil 0,70 | 44,61 | 2 ; 66 ; sig 929 | 65 ; 198 | 149 | 169 ; 21 | oui, mais pointu (0,68 et 0,70 seulement) |
| Moyenne géométrique 0,5, seuil 0,68 | 43,94 | 2 ; 64 (46) ; sig 908 | 65 ; 185 | 137 | 167 ; 29 | oui (plateau 0,64 à 0,70) |
| Moyenne 0,5 + températures, seuil 0,74 | 45,24 | 4 ; 65 ; sig 925 | 63 ; 205 | 135 | 148 ; 41 | oui (plateau 0,62 à 0,76) |
| « L’un des deux », seuils réglés (v10b 0,46 ; soupe 0,70) | 45,48 | 2 ; 77 (13) ; sig 874 | 60 ; 222 | 131 | 144 ; 42 | oui (au bord de la limite 77) |

Lecture des cases : malades sans alerte ; saines en alerte (dont « à vérifier ») ; Sigatoka nommée en validation. Dénominateurs : validation 2 001 et 1 000, TDTU 1 059 et 577, PSFD 738, Éthiopie 1 134 et 155.

**Idées libres : la branche « loin ».** Détail des erreurs de la chaîne installée par branche : dans les pays, les photos envoyées vers la v2 ratent plus (TDTU 43 / 306 contre 40 / 753 en proche ; PSFD 66 / 211 contre 83 / 527).

| Candidat | Coût moyen | Validation | TDTU | PSFD | Éthiopie | F |
| --- | --- | --- | --- | --- | --- | --- |
| Seuil de l’aiguilleur 0,1 / 0,3 / 0,7 / 0,9 / 0,97 | 50,39 / 49,77 / 49,30 / 48,42 / 48,54 | | | | | non |
| Sans aiguilleur (tout par la v10b) | 46,36 | 10 ; 57 | 47 ; 199 | 144 | 145 ; 52 | oui |
| Tout par la v2 | 60,56 | 4 ; 25 | 111 ; 166 | 260 | 267 ; 4 | non |
| Loin : alerte si la v2 ou la v10b alerte | 45,36 | 9 ; 57 (25) ; sig 872 | 47 ; 215 | 129 | 143 ; 52 | oui |
| Loin : alerte si la v2 et la v10b alertent | 50,23 | 10 ; 57 | 83 ; 161 | 164 | 181 ; 43 | non |

**Combinaisons (mélange en gros plan + branche loin), seuil de 0,50 à 0,78 par pas de 0,04.**

| Candidat | Coût moyen | Validation | TDTU | PSFD | Éthiopie | F |
| --- | --- | --- | --- | --- | --- | --- |
| Loin « v2 ou proche » ; proche = moyenne 0,25, seuil 0,62 | 41,86 | 6 ; 72 (50) ; sig 885 | 27 ; 229 | 115 | 115 ; 54 | oui (voisin 0,66 non) |
| Loin « v2 ou proche » ; proche = moyenne 0,5, seuil 0,62 | 40,75 | 4 ; 52 (39) ; sig 899 | 28 ; 223 | 125 | 131 ; 39 | oui (0,54 à 0,66) |
| Loin « v2 ou proche » ; proche = moyenne 0,5, seuil 0,66 | 40,21 | 4 ; 64 (51) ; sig 899 | 25 ; 236 | 117 | 113 ; 44 | oui (voisin 0,70 non) |
| Loin « v2 ou proche » ; proche = géométrique 0,5, seuil 0,66 | **39,44** | 4 ; 58 (40) ; sig 908 | 30 ; 215 | 122 | 141 ; 29 | oui (0,58 à 0,70) |
| Sans aiguilleur ; proche = géométrique 0,5, seuil 0,66 | 39,76 | 4 ; 58 ; sig 908 | 30 ; 202 | 130 | 142 ; 29 | oui (0,58 à 0,70) |
| Sans aiguilleur ; proche = moyenne 0,5, seuil 0,66 | 40,37 | 4 ; 64 ; sig 899 | 25 ; 228 | 122 | 113 ; 44 | oui (voisin 0,70 non) |

Des points à coût encore plus bas existent (géométrique, seuil 0,74 : 38,90) mais ils dépassent 77 saines en alerte en Tanzanie : non finalistes.

Mise en garde : ces coûts de réglage viennent de 343 essais sur les mêmes photos, ils sont optimistes. Le gain vient de deux sources assez indépendantes (mélange : environ 5 points ; branche loin : environ 4 points), chacune avec un plateau, ce qui rassure un peu.

## 22 h 30 : reprise sur le plan `docs/plan_nuit_10h.md`

- Message du chef d'orchestre : file des essais 1 à 9 de la section 5 ; **je ne lis pas les juges** (ce sera l'agent « Juge »). Le script `scripts/m12_banc_juges.py`, écrit à 22 h 23, n'a **jamais été lancé** et ne le sera pas par moi ; aucun fichier BanSpot ni Cordana n'a été ouvert.
- Correction d'un chiffre du plan de 10 h : la référence de la chaîne installée sur le réglage est **49,23** (pas 45,4 : 45,36 est le candidat « branche loin = v2 ou v10b » seul).
- La lecture en morceaux locale lancée à 22 h 19 a été tuée avec l'arrêt des agents (aucun morceau lu). Elle part sur Kaggle.

## 22 h 33 : essais 5 et 6 envoyés sur Kaggle

- Carnet `affilecorentin/m12-banc-morceaux` (T4, demi-précision), source : `scripts/m12_banc_kaggle_morceaux.py`. Jeux de réglage seulement (filtre sur la colonne `jeu` de `listes_v10b.csv`, ordre vérifié identique aux fichiers de prédiction).
- Échantillon tiré à l'avance (graine 2026, 400 photos par jeu) : `out/maladies/nuit_1112/banc/echantillon_m2.json`. Malades / saines dans l'échantillon : validation 269 / 131, TDTU 249 / 151, PSFD 400 / 0, Éthiopie 353 / 47.
- Calculé : 3 × 3 et lecture entière 384 px (contrôle de la demi-précision) sur l'échantillon ; 2 × 2 sur tous les jeux de réglage ; lecture entière 512 px sur tous les jeux de réglage.
- Règle (écrite avant de lire) : décision sur l'échantillon d'abord ; les résultats 2 × 2 sur les jeux entiers ne sont regardés que si le gain d'échantillon dépasse 1 point de coût.

## 22 h 34 : essai 7, mélange à trois et températures (129 essais : 90 + 39)

Scripts : `scripts/m12_banc_trois.py`, `scripts/m12_banc_trois_fin.py` ; journaux `trois.log`, `trois_fin.log`. Lecteur proche = moyenne géométrique pondérée (v10b, soupe, v2) sur les 3 classes communes, « autre » de la v10b gardée avec le poids de la v10b ; branche loin « v2 ou proche ».

| Candidat (meilleur seuil finaliste) | Coût moyen | Validation | TDTU | PSFD | Éthiopie | Plage finaliste |
| --- | --- | --- | --- | --- | --- | --- |
| Géo v10b + soupe (1, 1, 0), t = 0,68 | 39,24 | 2 ; 64 (46) ; sig 908 | 27 ; 222 | 117 | 131 ; 34 | 0,60 à 0,70 |
| **Géo à trois (1, 1, 1), t = 0,74** | **37,83** | 2 ; 57 (48) ; sig 916 | 28 ; 232 | 109 | 134 ; 27 | 0,64 à 0,76 |
| Géo à trois (1, 1, 1), t = 0,76 | 36,84 | 1 ; 67 (58) ; sig 916 | 23 ; 242 | 103 | 119 ; 29 | bord : 0,78 dépasse 77 saines |
| Géo à trois (2, 2, 1), t = 0,74 | 37,55 | 2 ; 69 (58) ; sig 914 | 23 ; 240 | 104 | 116 ; 34 | 0,62 à 0,74 (bord) |
| Géo (2, 1, 1), t = 0,74 | 38,56 | 1 ; 77 | 24 ; 246 | 103 | 101 ; 44 | |
| Géo (1, 0, 1) v10b + v2, t = 0,74 | 39,32 | 2 ; 64 | 24 ; 245 | 106 | 108 ; 46 | |
| Températures v10b / soupe (7 couples) | 38,69 à 41,07 | | | | | |
| À trois avec températures | 40,71 et 42,91 | | | | | |

- Les températures ne gagnent rien de net (au mieux 0,6 point, avec un plateau étroit) : piste fermée.
- Le mélange à trois gagne environ 1,4 point sur le mélange à deux, avec un large plateau (0,64 à 0,76). Prix : trois modèles par photo proche (environ 1,8 + 0,7 + 0,7 s sur ce PC au lieu de 1,8 s).
- Choix de seuil selon ma règle de 22 h 19 (les deux voisins doivent être finalistes) : (1, 1, 1) à 0,74 ; (2, 2, 1) à 0,72 (38,61), car 0,74 est au bord.
- Cumul : 343 + 129 = **472 essais**.

## 22 h 34 : règle de l'essai 8 (seuil de nom), écrite avant le calcul

Le seuil de nom ne change pas les alertes. Sans regarder la Cordana (juge), le substitut sur le réglage est : **autres maladies dites Sigatoka** = photos malades qui ne sont pas de la Sigatoka (validation : fusariose ; TDTU : autre maladie ; PSFD : Sigatoka jaune ; Éthiopie : Xanthomonas) et dont la réponse est « cercosporiose noire ». Choix : le `seuil_nom` (grille 0,50 à 0,95) qui minimise ce total sur les 4 jeux, sous la contrainte Sigatoka nommée en validation ≥ 95 % de la valeur de la même chaîne au seuil installé 0,79.

## 22 h 35 : essai 8, seuil de nom (18 essais ; cumul 490)

Script `scripts/m12_banc_nom.py`, journal `nom.log`. Les alertes ne bougent pas (vérifié : même nombre d'alertes à chaque seuil).

| Chaîne | seuil_nom | Autres maladies dites Sigatoka (4 jeux) | Sigatoka nommée validation | Sigatoka nommée TDTU / PSFD / Éthiopie |
| --- | --- | --- | --- | --- |
| Installée | 0,79 (actuel) | 176 (val 41, TDTU 39, PSFD 9, Éth 87) | 872 | 59 / 97 / 47 |
| Installée | **0,83 (choix de la règle)** | 142 | 853 | 52 / 84 / 36 |
| Installée | 0,87 | 106 | 810 (sous la limite de 95 %) | 47 / 59 / 26 |
| À trois (1, 1, 1), t = 0,74 | 0,79 | 49 (val 30, TDTU 9, PSFD 5, Éth 5) | 916 | 59 / 60 / 26 |
| À trois (1, 1, 1), t = 0,74 | **0,87 (choix de la règle)** | 32 | 879 | 44 / 35 / 15 |

Lecture : le mélange à trois nomme déjà beaucoup moins d'autres maladies « Sigatoka » (49 contre 176) sans changer de seuil de nom, mais il nomme aussi moins la vraie Sigatoka dans les pays (PSFD 60 au lieu de 97). Le seuil de nom est un réglage d'affichage : je le laisse à 0,79 dans les finalistes (il ne change pas le coût) et je le signale comme option.

## 23 h 25 à 23 h 35 : essais 5 et 6, lecture en morceaux et à 512 px (422 essais ; cumul 912)

Carnet `m12-banc-morceaux` terminé à 23 h 25 (50 min de T4). Sorties : `out/maladies/nuit_1112/banc/kaggle_morceaux/`. Contrôle : la lecture entière 384 px du carnet (demi-précision) s'écarte du cache 32 bits d'au plus 0,004 (PSFD), 0,001 ailleurs.

Méthode : P(malade) des morceaux réunie (maximum, moyenne des 2 plus fortes, « ou bruité »), puis combinée à la lecture entière (morceaux seuls, maximum, moyenne) ; la P(saine) de la v10b est remplacée, les maladies gardent leurs proportions ; décision par le code de la chaîne. Deux bases : chaîne installée (v10b seule) et mélange « à trois ». Script `scripts/m12_banc_m2_analyse.py` (échantillon puis complet), `scripts/m12_banc_m2_fin.py` (grille fine).

**Échantillon (240 essais, `m2_echantillon.log`)** :
- Base installée (v10b seule) : meilleur morceaux 51,07 contre 51,98 pour la référence sur l'échantillon : gain 0,9, sous 1 point. Les morceaux font surtout monter les saines en alerte (validation 5 → 15 / 131). **Piste fermée pour la v10b seule.**
- Base « à trois » : 3 × 3 maximum / moyenne avec l'entière, t = 0,70 : 33,92 contre 37,77 (meilleure lecture entière sur la même grille) : **gain 3,85 > 1 point, donc extension** (règle de 22 h 33). Les 2 × 2 gagnent 1,7 à 2,3 points.
- 512 px : seul, il ne gagne rien (v10b seule : − 4 à − 5 points ; à trois : + 0,95 au mieux). En moyenne avec 384 px, à trois : + 1,7.

**Jeux entiers, 2 × 2 (déjà calculé ; 132 essais grossiers + 50 fins, `m2_complet_g2.log`, `m2_fin.log`)**, base « à trois », loin « v2 ou proche » :

| Lecture de la v10b dans le mélange à trois | Meilleur seuil sûr (voisins finalistes) | Coût moyen | Validation | TDTU | PSFD | Éthiopie | Plage finaliste |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Entière 384 (= F1) | 0,74 | 37,83 | 2 ; 57 (48) ; sig 916 | 28 ; 232 | 109 | 134 ; 27 | 0,64 à 0,76 |
| Moyenne 384 + 512 | 0,72 | 36,48 | 1 ; 58 (49) ; sig 908 | 22 ; 234 | 105 | 125 ; 27 | 0,62 à 0,74 |
| 2 × 2, maximum, moyenne avec l'entière | 0,68 | 36,64 | 1 ; 62 (52) ; sig 919 | 20 ; 238 | 105 | 123 ; 28 | 0,60 à 0,70 |
| **2 × 2, 2 plus fortes, moyenne avec l'entière** | **0,70** | **35,96** | 0 ; 62 (53) ; sig 919 | 19 ; 241 | 102 | 117 ; 28 | 0,60 à 0,72 |
| 2 × 2, « ou bruité », moyenne avec l'entière | 0,66 | 37,21 | 0 ; 64 (48) ; sig 918 | 22 ; 246 | 104 | 128 ; 27 | 0,60 à 0,68 |

- Gain des morceaux 2 × 2 sur les jeux entiers : environ 1,9 point (35,96 contre 37,83), moins que sur l'échantillon (3,85) : effet du petit échantillon (131 saines en validation, 47 en Éthiopie) et de la sélection.
- Coût de calcul : 4 lectures de plus de la v10b par photo proche (environ 5 fois le temps de la v10b seule ; sur ce PC, environ 9 s de plus par photo).
- 3 × 3 sur tous les jeux : carnet `m12-banc-g3` (`scripts/m12_banc_kaggle_g3.py`) en attente d'une place GPU (2 carnets de M-entraînement occupent les deux places).

## 23 h 36 : essai 9, mélange avec la v12a (a1) de M-entraînement (35 essais ; cumul 947)

Script `scripts/m12_banc_v12.py a1`, journal `v12_a1.log`. Pays lus dans le pli qui ne les a pas appris ; validation = moyenne des 3 plis.
- a1 seul, v10b + a1 (moyenne ou géométrique) : aucun finaliste.
- À quatre (v10b, soupe, v2, a1), loin « v2 ou proche » : au mieux 45,89 (TDTU 367 / 577 saines en alerte).
- À trois + a1 poids 0,5 : au mieux 42,50.
- Tout est moins bon que le mélange à trois sans a1 (37,83) : a1 apporte des fausses alertes (raccourci « pays inconnu = malade » noté par M-entraînement). **Piste fermée pour a1** ; à refaire si une meilleure v12 arrive.

## 23 h 48 : finalistes écrits ; contrôle de la lecture locale

- `out/maladies/nuit_1112/banc/finalistes.md` écrit (avant toute lecture des juges) : F1 = à trois + morceaux 2 × 2 (t = 0,70 ; 35,96), F2 = à trois + moyenne 384/512 px (t = 0,72 ; 36,48), F3 = à trois (t = 0,74 ; 37,83) ; réserve : géo v10b + soupe, loin « ou » (t = 0,68 ; 39,24). Choix par la règle de 22 h 19 (meilleur plateau par famille, puis 3 coûts les plus bas).
- `scripts/m12_banc_finalistes.py` redonne exactement ces chiffres sur le réglage. Son mode `--calculer` (lectures 512 px et 2 × 2 en local) a été contrôlé sur 2 photos de TDTU contre le carnet Kaggle : écart maximal 1 × 10⁻⁴ (512 px) et 2 × 10⁻⁴ (2 × 2). Temps : 12 min pour 2 photos, chargement compris, sur un processeur partagé avec les autres agents : sur les juges, passer par Kaggle.
- En attente : carnet 3 × 3 (places GPU prises), nouvelles v12 de M-entraînement (essai 9).
- 00 h 18 : carnet `m12-banc-g3` (3 × 3 sur tous les jeux de réglage) parti sur Kaggle.

## 00 h 23 : essai 9 sur les v12 du lot 2 (210 essais ; cumul 1 157)

`scripts/m12_banc_v12.py <nom>` pour b1, a2, a3, a4, c1, c2 (c3 incomplet), journaux `v12_<nom>.log`. Meilleur finaliste par famille de mélange :

| v12 | À quatre (v10b, soupe, v2, v12), loin « ou » | À trois + v12 poids 0,5, loin « ou » |
| --- | --- | --- |
| b1 | 42,27 | 39,36 |
| a2 | 44,15 | 41,65 |
| a3 | 47,05 | 43,57 |
| a4 | 39,14 | 38,74 |
| c1 | 46,25 | 43,95 |
| c2 | 43,83 | 41,01 |

Toutes moins bonnes que F3 (37,83, sans v12) : elles ajoutent des fausses alertes en TDTU (287 à 511 / 577). Seules ou avec la v10b seule : aucun finaliste sous 46. **Piste 9 fermée pour ces v12** (deux échecs de suite, règle d'abandon). M-analyste arrive au même constat (AUC qui ne monte pas).

## 00 h 23 : recommandations de M-analyste appliquées

- **3 × 3 arrêté** : carnet `m12-banc-g3` supprimé de Kaggle pendant qu'il tournait (place GPU rendue à M-entraînement). Raison : sur l'échantillon, les morceaux ne séparent pas mieux (AUC entière / 2 × 2 / 3 × 3 : TDTU 0,908 / 0,903 / 0,905 ; Éthiopie 0,862 / 0,845 / 0,853). Le gain de F1 sur F3 (1,9 point) vient d'un déplacement des probabilités, choisi après beaucoup d'essais : le Contrôleur le regardera.
- **Essai « tailles » lancé** : carnet `m12-banc-tailles` (`scripts/m12_banc_kaggle_tailles.py`), v10b lue en 224 px et en taille adaptée min(384, 2 × côté court), sur les 4 jeux de réglage. La taille adaptée ne change que les petites photos : Éthiopie (150 × 113 → 226 px) ; validation, TDTU et PSFD restent à 384.
  - Critère, écrit avant de lire (repris de M-analyste) : finaliste si la règle du plan est remplie **et** si l'AUC de la v10b sur l'Éthiopie dépasse 0,90 en 224 px.
  - Si un candidat « 224 » ou « taille adaptée » entre dans les 3, `finalistes.md` est mis à jour avant 7 h. **Ordre actuel, gardé ici : F1 (35,96), F2 (36,48), F3 (37,83) ; réserve 39,24.**
- **PSFD sans copies, pour information** (règle 4.4 inchangée ; `scripts/m12_banc_psfd_sans_copies.py`, `psfd_sans_copies.log`) :

| Chaîne | Coût moyen, règle (PSFD 738) | PSFD sans les 123 copies tournées (615) | PSFD, une photo par groupe de quasi-copies (188) |
| --- | --- | --- | --- |
| Installée | 49,23 | 43,84 | 53,23 |
| F1 | 35,96 | 31,57 | 38,76 |
| F2 | 36,48 | 32,03 | 39,37 |
| F3 | 37,83 | 33,46 | 40,32 |
| Réserve | 39,24 | 34,67 | 42,51 |

  Le classement est le même dans les trois comptes.

## 00 h 50 : essai « tailles » (58 essais ; cumul 1 215)

Carnet `m12-banc-tailles` terminé (sorties `out/maladies/nuit_1112/banc/kaggle_tailles/`). Scripts `scripts/m12_banc_tailles.py`, `scripts/m12_banc_tailles_seule.py` ; journaux `tailles.log`, `tailles_seule.log`.

AUC (1 − P(saine), toutes photos) :

| Lecture de la v10b | v10b seule : validation / TDTU / Éthiopie | Mélange à trois : validation / TDTU / Éthiopie |
| --- | --- | --- |
| 384 (installée) | 0,995 / 0,897 / 0,879 | 1,000 / 0,938 / 0,938 |
| 224 | 0,997 / **0,926 / 0,926** | 1,000 / 0,937 / 0,944 |
| Adaptée min(384, 2 × côté court) | 0,995 / 0,897 / 0,926 | 1,000 / 0,937 / 0,944 |
| Moyenne 384 + 224 | 0,996 / 0,923 / 0,913 | 1,000 / 0,938 / 0,943 |

Coût (mélange à trois, loin « ou », meilleur seuil dont les deux voisins sont finalistes) :
- 224 : seul t = 0,82 est finaliste (43,26), au bord de la grille ;
- adaptée : t = 0,74, 38,31 (plage 0,72 à 0,76) ;
- moyenne 384 + 224 : t = 0,78, 39,21 (plage 0,74 à 0,80).

v10b seule en 224 px : au mieux 52,03 (loin v2) et 47,86 (loin « ou »), aucun finaliste. PSFD s'effondre : 187 à 271 ratées sur 738.

Lecture :
- La v10b lue en 224 px sépare nettement mieux TDTU et l'Éthiopie (AUC + 0,03 et + 0,05). Le critère de M-analyste (AUC Éthiopie ≥ 0,90) est rempli.
- Mais dans le mélange à trois, l'AUC ne bouge presque pas (Éthiopie 0,938 → 0,944) : la soupe et la v2, lues en 224, apportaient déjà cette séparation.
- En coût, le 224 px fait rater beaucoup plus de PSFD (Sigatoka à 256 px, photos qui ne sont pas agrandies).

Aucun candidat « taille » n'entre dans les 3 : **finalistes inchangés** (F1 35,96 ; F2 36,48 ; F3 37,83 ; réserve 39,24). Piste fermée.

## 00 h 52 : état de la file

Essais 1 à 9 et « tailles » faits ; 3 × 3 arrêté (sur recommandation). Il ne reste que l'essai 9 sur de futures v12 (lot 3 de M-entraînement) : `scripts/m12_banc_v12.py <nom>` le refait en une minute sur `out/maladies/nuit_1112/kaggle/<nom>/`. **Total : 1 215 essais de réglage.** Juges jamais lus.

## 04 h 00 : relance, essai 9 sur les v12 finalistes (famille C) ; grille écrite AVANT la mesure

Demande du chef d'orchestre (4 h) et règle de gel `docs/nuit_2026-11-12/regle_gel_finalistes.md` : les mélanges contenant un v12 forment la famille C. Juges toujours non lus.

- Étape 1 : `scripts/m12_banc_v12.py` sur a13 et a14 (même script qu'à 0 h 23 : 5 mélanges × 7 seuils = 35 essais par v12).
- Étape 2, grille courte, fixée ici avant tout calcul, pour **a13, a14 et a4** (les trois finalistes v12 de M-entraînement) :
  - mélanges, tous en moyenne géométrique à poids égaux sur les 3 classes communes ; « autre » = moyenne pondérée des « autre » des membres à 4 classes ; renormalisée :
    1. v12 + v10b ;
    2. v12 + soupe ;
    3. v10b + soupe + v2 + v12 (à quatre) ;
    4. v12 + soupe + v2 (v12 à la place de la v10b dans le mélange à trois) ;
  - seuil de confiance (règle B) de 0,50 à 0,80 par pas de 0,02 (16 valeurs), autres seuils de la v10b ;
  - branche loin « v2 ou proche » ; lecture entière seulement ;
  - chiffres : TDTU et Éthiopie lus par le pli qui n'a pas appris le pays ; PSFD par son fichier (jamais appris) ; Tanzanie = moyenne des plis présents ;
  - essais : 3 × 4 × 16 = 192.
- Choix du meilleur de la famille C, écrit avant : parmi les points qui remplissent la règle « finaliste » 4.4 **et** dont les deux seuils voisins (± 0,02) la remplissent aussi, le coût moyen le plus bas. Égalité à 0,001 près : le mélange le moins coûteux en calcul.
- Contrôle du modèle final (3 réseaux appris sur tout sauf PSFD et la validation) : validation Tanzanie, au seuil choisi, avec `out/maladies/nuit_1112/kaggle/final_*/predictions_<nom>_final_validation.csv`. Limites du plan : ≤ 14 ratées et ≤ 77 fausses alertes.
- Lot 6 (a17 à a20) : s'il arrive avant 5 h, même grille, sans l'élargir.

## 04 h 05 : famille C mesurée (262 essais ; cumul 1 477)

- `m12_banc_v12.py` sur a13 et a14 (70 essais, `v12_a13.log`, `v12_a14.log`) : à quatre 36,12 (a13) et 36,67 (a14) ; à trois + v12 poids 0,5 : 36,52 et 35,87. Ces points touchent le bord de leur grille (pas 0,04) ; la grille courte décide.
- Grille courte (192 essais, `scripts/m12_banc_v12_grille.py`, `v12_grille.log`). Meilleur seuil sûr de chaque mélange :

| v12 | v12 + v10b | v12 + soupe | À quatre | v12 + soupe + v2 |
| --- | --- | --- | --- | --- |
| a13 | 39,14 (0,58) | 37,75 (0,68) | 36,64 (0,72) | 37,36 (0,76) |
| a14 | 38,51 (0,66) | 36,48 (0,72) | **36,07 (0,76)** | 36,66 (0,78) |
| a4 | 43,39 (0,60) | 42,46 (0,76) | 40,00 (0,76) | 42,85 (0,78) |

- **Meilleur de la famille C, selon la règle écrite à 4 h : à quatre v10b + soupe + v2 + v12a14, t = 0,76, coût 36,07.** Validation 2 ; 68 (48 à vérifier) ; TDTU 15 ; 260 ; PSFD 86 ; Éthiopie 122 ; 32.
- Contrôle du modèle final sur la validation, même seuil (`scripts/m12_banc_v12_controle_final.py`, `v12_controle_final.log`) : 3 / 2 001 ; 69 / 1 000. Limites respectées.
- Écrit dans `out/maladies/nuit_1112/banc/finalistes_famille_c.md`. Candidat ajouté à `scripts/m12_banc_finalistes.py` (`C_quatre_v12a14`, option `--v12`) ; il redonne 36,07.
- Lecture : par rapport à F3 (37,83), le v12a14 fait baisser les ratées dans les pays (TDTU 28 → 15, PSFD 109 → 86, Éthiopie 134 → 122). En contrepartie, les fausses alertes montent en TDTU (232 → 260) et en validation (57 → 68). Temps ≈ 5 s par photo.
- En attente du lot 6 (a17 à a20) jusqu'à 5 h : même grille, sans l'élargir.

## 04 h 06 : lot 6 (256 essais ; cumul 1 733)

- a17 à a20 arrivés avant 5 h : même grille, sans l'élargir (`v12_grille_lot6.log`). Meilleur point sûr : à quatre + a19, t = 0,76, **34,73** (plage 0,64 à 0,78). Suivants : a18 + soupe 36,05 ; a19 + soupe 36,14 ; a18 à quatre 36,20 ; a20 à quatre 36,53 ; a17 à quatre 36,71.
- a19 n'a pas de modèle final, et M-entraînement gèle ses recettes à 4 h 10 : le contrôle du modèle final demandé à 4 h est impossible. Décision : **le candidat de la famille C reste à quatre + v12a14, t = 0,76 (36,07, modèle final contrôlé : 3 ; 69)**. a19 est signalé dans `finalistes_famille_c.md` comme meilleur sur le réglage, à condition qu'un modèle final soit entraîné et contrôlé avant 6 h 45.
- Fin de la file. Juges jamais lus.
