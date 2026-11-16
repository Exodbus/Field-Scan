# Journal de l'agent C-banc, 15/11 (comptage sans entraînement, processeur)

Cadre : `docs/plan_journee_2026-11-15.md` ; règles du comptage : plan du 13/11, section 5.3, inchangées (référence v5 au seuil 0,30, `val_negatifs` < 1 %, seuil choisi sur la grille 0,10 à 0,60).

- Écrit seulement dans `out/comptage/jour_1511/banc/`, `scripts/c15_banc_*.py` et ce journal.
- Banc importé **sans modification** : `scripts/v6_banc_commun.py`, `c13_banc_commun.py` (garde-fou des juges par `assert`), `c13_banc_candidats.py`, et `c14_essais.py` (fabriques de C-piste2 : `f_melange`, `nms_grille`, `construire`), en lecture seule. Le fichier `essais.json` de C-piste2 n'est jamais réécrit : mes résultats vont dans `out/comptage/jour_1511/banc/essais.json`.
- Jeux lus : dense, plantain, jeunes, MM, btd_val, `val_negatifs` (réglage), à 5 cm et dégradés à 11 cm. Jamais segmento est, CG, `banano_dense`, `test_negatifs`, `banana_trees_kp`.
- Processeur : 2 fils au plus au total (un processus ONNX à 1 fil + un processus de mesure à 1 fil, ou un seul à 2 fils).

## 13 h 58. Règles écrites avant tout calcul

### Contrôles (ne comptent pas comme essais)

Recalcul par mon script, avec les fabriques de C-piste2 : `v5` (attendu : moyenne 5 = 0,7777, 4 anciennes = 0,8539, seuil 0,30), `CC1_v5h_50` (0,8886 / 0,8630, 11 cm 0,8569) et `CC3_a1_a35` (0,8671 / 0,8563). Si un chiffre diffère à la 4e décimale, j'arrête et je cherche pourquoi avant tout essai.

### Ce que je ne refais pas

- CC1 + suppression à l'écartement (CC3) : déjà mesuré par C-piste2 (essai 26), **aucun point retiré** sur CC1_v5h_50. Non refait (ce serait le même chiffre).
- Poids 0,3 / 0,5 / 0,7 du v5 et mélanges avec c13e : déjà mesurés (essais 1 à 5 de C-piste2).

### Famille G : c13h seulement sur les images où le v5 hésite (famille C), 2 essais

Critère d'hésitation, repris de l'aiguillage E5p90b déjà validé : pics du v5 (fenêtre 7, score ≥ 0,15) ; l'image « hésite » si elle a au moins un pic et si le 90e centile des scores des pics est < τ. Image qui hésite : mélange CC1 (0,5 v5 + 0,5 c13h, carte entière). Sinon : v5 seul (c13h n'est pas calculé).
- `G1_p90_55` : τ = 0,55 ;
- `G2_p90_70` : τ = 0,70.
Temps : part des images où c13h est calculé, par jeu (y compris `val_negatifs`), puis temps mesuré de bout en bout pour les finalistes.

### Famille S : c13h calculé sur l'image réduite (famille C), 2 essais

c13h a appris des images dégradées de 5 à 12 cm. On le calcule sur l'image réduite (PIL bilinéaire, comme la variante d'échelle du banc v6), puis sa carte est ramenée sur la grille du v5 (OpenCV bilinéaire) et mélangée 0,5 / 0,5. Coût attendu de c13h : environ la surface, soit 0,51 (7 cm) et 0,25 (10 cm).
- `S70_v5h_50` : image à 7 cm (facteur 5/7) ;
- `S50_v5h_50` : image à 10 cm (facteur 0,5).
À 11 cm : la même réduction est appliquée à l'image déjà dégradée (`degrader(img, 11)` de `c13_entr_mesure.py`).

### Famille W : autre fusion (famille C), 2 essais

- `W_v5h_60` : poids 0,6 v5 / 0,4 c13h (entre 0,5 et 0,7, non mesuré) ;
- `W_logit_50` : moyenne des logits (moyenne géométrique normalisée), poids 0,5 / 0,5.

### Famille T : seconde passe dans les trous de plantation sur CC1 (famille C), 1 essai

`T_cc1_trous20` : sur les points de CC1_v5h_50, ancres = score ≥ 0,30 ; pics bas = score dans [0,20 ; 0,30) ; promus à 0,30 par `promouvoir(..., "reseau", 0,30, 25)` de `c13_banc_candidats.py` (même règle que les trous d'A1).

### Combinaison (1 essai, conditionnel)

`GS_best` : seulement si un essai G **et** un essai S passent 5.3 : la meilleure porte G avec la meilleure réduction S (meilleure = moyenne des 5 de réglage). Sinon non fait.

### Décision

- Finaliste : règle 5.3 telle quelle (moyenne 5 > v5 + 0,010 et 4 anciennes ≥ 0,8539 ; aucune perte > 0,020 ; erreur de compte ≤ v5 ; `val_negatifs` < 1 %), ou « résolution » (11 cm ≥ 0,6306 et 5 cm ≥ 0,7727 + autres conditions).
- Pour le livrable, un finaliste n'est **proposé** que s'il apporte quelque chose face à CC1_v5h_50 : soit 4 anciennes ≥ 0,8630 (CC1) avec un temps plus court, soit une moyenne de réglage plus haute. Un finaliste qui ne fait ni l'un ni l'autre est listé « dominé ».
- Temps : mesuré de bout en bout (lecture, cartes ONNX, pics), 2 fils, 30 tuiles par jeu (dense, plantain, btd_val, `val_negatifs`), même échantillon que `c14_temps.py`, rapport au v5 mesuré dans la même passe.

Compte prévu : 7 essais (+1 conditionnel).

## Calculs

### 14 h 00. Contrôles (0 essai)

`scripts/c15_banc_essais.py v5 CC1_v5h_50 CC3_a1_a35 --cm11` (1 fil) :
- v5 au seuil 0,30 : dense 0,7795, plantain 0,8865, jeunes 0,8926, MM 0,8571, btd_val 0,4726 ; **moyenne 5 = 0,7777, 4 anciennes = 0,8539**, erreur 0,262, `val_negatifs` 16 (0,25 %) ; 11 cm 0,6005 (4 anciennes 0,7471). Retrouvé au chiffre près.
- CC1_v5h_50 : seuil 0,30, 0,8886 / 0,8630, erreur 0,117, neg 7, 11 cm 0,8569 (4 anciennes 0,8242). Retrouvé.
- CC3_a1_a35 : seuil 0,30, 0,8671 / 0,8563, erreur 0,128, neg 16, 11 cm 0,6058. Retrouvé.
- Cache de la famille S lancé à 13 h 59 (`scripts/c15_banc_cache.py`, 1 fil ONNX).

### 14 h 01. Essais 1 à 5 (familles G, W, T)

`scripts/c15_banc_essais.py G1_p90_55 G2_p90_70 W_v5h_60 W_logit_50 T_cc1_trous20 --cm11` :

| essai | candidat | seuil | moyenne 5 | 4 anciennes | erreur | neg | 11 cm | 5.3 | part d'images avec c13h (5 cm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | G1_p90_55 | 0,30 | 0,8810 | 0,8537 | 0,130 | 7 | 0,8061 | **non** (4 anciennes < 0,8539) | dense 0/84, plantain 15/165, btd_val 177/178, neg 116/1424 |
| 2 | G2_p90_70 | 0,30 | 0,8812 | 0,8537 | 0,136 | 5 | 0,8223 | **non** (4 anciennes) | dense 33/84, plantain 66/165, btd_val 178/178, neg 119/1424 |
| 3 | W_v5h_60 | 0,30 | 0,8860 | 0,8613 | 0,116 | 7 | 0,8417 | oui, mais dominé par CC1 | toutes |
| 4 | W_logit_50 | 0,30 | 0,8850 | 0,8640 | 0,110 | 4 | 0,7430 | oui ; 4 anciennes > CC1 mais même coût et moyenne plus basse : dominé | toutes |
| 5 | T_cc1_trous20 | 0,35 | 0,8848 | 0,8592 | 0,065 | 5 | 0,8364 | oui, mais dominé | toutes |

Lecture : la porte par image ne garde **pas** le gain de CC1 hors btd_val. Le v5 est sûr de lui sur presque toutes les images du dense, du jeunes et de MM, or c'est sur ces images que c13h corrige quelques pieds. Le gain de CC1 est local (quelques couronnes), pas lié à des images entières où le v5 se trompe.

### 14 h 03. Règle ajoutée avant calcul : famille B, c13h seulement dans les blocs où le v5 hésite (famille C), 2 essais

Écrite après avoir vu les essais 1 à 5, avant tout calcul de la famille B.
- Grille au quart du v5 découpée en blocs carrés. Un bloc « hésite » s'il contient un pic du v5 (fenêtre 7, score ≥ 0,10) de score < 0,60. Raison : avec 0,5 / 0,5, un pic du v5 ≥ 0,60 reste ≥ 0,30 quel que soit c13h, donc c13h ne peut changer la décision qu'autour des pics < 0,60 (ou là où le v5 n'a aucun pic, cas que la règle ne couvre pas).
- Dans les blocs qui hésitent : carte mélangée 0,5 / 0,5 ; ailleurs : carte du v5. Pics sur la carte composée.
- `B1_bloc64` : blocs de 64 cases (256 px, 12,8 m) ; `B2_bloc32` : blocs de 32 cases (128 px).
- Mesure : avec la carte entière de c13h en cache (approximation d'un calcul par morceaux à marge infinie). Le temps et l'écart au calcul réel par morceaux (marge de 64 px autour du bloc) seront mesurés de bout en bout pour un finaliste ; la part de surface calculée est relevée pour chaque jeu.

### 14 h 03. Essais 6 et 7 (famille B)

| essai | candidat | seuil | dense | plantain | jeunes | MM | btd_val | moyenne 5 | 4 anciennes | erreur | neg | 11 cm | 5.3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | B1_bloc64 | 0,30 | 0,7838 | 0,8867 | 0,9180 | 0,8633 | 0,9885 | 0,8881 | 0,8630 | 0,118 | 5 | 0,8476 | oui |
| 7 | B2_bloc32 | 0,30 | 0,7838 | 0,8867 | 0,9218 | 0,8633 | 0,9778 | 0,8867 | 0,8639 | 0,121 | 6 | 0,8179 | oui |

Part des blocs qui hésitent (5 cm) : B1 : dense 100 %, plantain 79 %, jeunes 90 %, MM 78 %, btd_val 73 %, `val_negatifs` 8,5 %. B2 : dense 94 %, plantain 72 %, MM 52 %, btd_val 66 %, `val_negatifs` 2,3 %.
Lecture : B1 garde **exactement** le gain de CC1 sur les 4 anciennes (mêmes F1 par jeu), btd_val −0,003. Mais dans une bananeraie le v5 hésite presque partout : l'économie ne vient que des zones sans bananier. Le temps réel (calcul par morceaux avec marge) reste à mesurer.

### 14 h 09. Essai 8 (famille S, 10 cm)

| essai | candidat | seuil | dense | plantain | jeunes | MM | btd_val | moyenne 5 | 4 anciennes | erreur | neg | 11 cm | 5.3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | S50_v5h_50 | 0,25 | 0,7621 | 0,8611 | 0,9143 | 0,8806 | 0,9878 | 0,8812 | 0,8545 | 0,174 | 12 | 0,8486 | **non** (plantain −0,025, erreur 0,174) |

Au seuil 0,30 (information, pas un choix) : voir `essais.json`. c13h à 10 cm perd trop de détail sur le plantain.

### 14 h 10. Règle ajoutée avant le calcul de S70 : combinaison B + S (1 essai, conditionnel)

L'essai conditionnel `GS_best` tombe (aucun G ne passe). À la place, écrit avant de voir S70 : **si `S70_v5h_50` passe 5.3**, `BS70_bloc64` = B1 (blocs de 64 cases) avec la carte de c13h à 7 cm au lieu de 5 cm. Sinon non fait. Total prévu : 9 essais au plus.

### 14 h 23. Essai 9 (famille S, 7 cm)

| essai | candidat | seuil | dense | plantain | jeunes | MM | btd_val | moyenne 5 | 4 anciennes | erreur | neg | 5.3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 9 | S70_v5h_50 | 0,30 | 0,7838 | 0,8851 | 0,9091 | 0,7970 | 0,9782 | 0,8706 | 0,8437 | 0,105 | 4 | **non** (MM −0,060, 4 anciennes < 0,8539) |

Non monotone (S50 garde MM à 0,881, S70 le perd) : MM, ce sont 2 zones d'environ 69 pieds, très sensibles à l'alignement de la grille réduite [H]. Sans importance pour la décision : ni S50 ni S70 ne passe. Par la règle de 14 h 10, `BS70_bloc64` **n'est pas fait**. Le cache des variantes d11s70 est arrêté (inutile). Total : **9 essais** (1 à 9).

### 14 h 24. Temps de bout en bout

`scripts/c15_banc_temps.py --fils 2 --n 30` : v5, CC1_v5h_50, B1_bloc64, B2_bloc32 (calcul réel de c13h par morceaux avec marge de 64 px ; carte entière si plus de la moitié des blocs hésitent). Contrôle préalable sur 12 tuiles : la carte par morceaux ne diffère de la carte entière que de 0,0096 au plus (moyenne 0,0006).

Résultat (14 h 26, 2 fils, 30 tuiles par jeu, temps par tuile, rapport au v5 mesuré dans la même passe) :

| jeu | v5 (s) | CC1_v5h_50 | B1_bloc64 | B2_bloc32 | surface de c13h calculée (B1 / B2) | points identiques au banc (CC1 / B1 / B2) |
| --- | --- | --- | --- | --- | --- | --- |
| dense | 0,323 | × 2,80 | × 2,78 | × 2,81 | 1,00 / 1,00 | 30 / 30 / 30 sur 30 |
| plantain | 0,060 | × 2,90 | × 2,95 | × 2,94 | 1,06 / 1,06 | 30 / 26 / 21 |
| btd_val | 0,399 | × 2,84 | × 2,86 | × 2,95 | 1,02 / 1,09 | 30 / 25 / 25 |
| `val_negatifs` | 0,162 | × 2,73 | × 1,18 | × 1,10 | 0,10 / 0,06 | 30 / 27 / 27 |

Lecture :
- CC1 coûte ici 2,7 à 2,9 fois le v5 (3,2 hier, à 3 fils sur une machine partagée).
- **Les blocs n'économisent rien dans une bananeraie** : le v5 y hésite partout, et les marges des morceaux coûtent plus que les blocs évités. Le gain de temps n'existe que sur les tuiles sans bananier (1,1 à 1,2 fois le v5 au lieu de 2,7).
- Le calcul réel par morceaux ne rend pas exactement les points du banc (carte entière en cache) sur 3 à 9 tuiles sur 30 : les F1 de B1 et B2 du tableau sont une approximation.

### 14 h 28. Règle écrite avant calcul : mesure réelle de B1 (0 essai neuf, remplace la mesure approchée)

B1 est le seul candidat qui garde exactement le gain de CC1 sur les 4 anciennes et qui gagne du temps quelque part. Je le mesure avec le calcul réel par morceaux (marge 64 px, carte entière si plus de la moitié des blocs hésitent), sur les 5 jeux et `val_negatifs` à 5 cm, et sur les 5 jeux à 11 cm (blocs décidés sur la carte du v5 de l'image dégradée). B2 n'est pas remesuré (il perd davantage sur btd_val à 11 cm : 0,7975 contre 0,9414). **Le chiffre réel remplace le chiffre approché** : si B1 réel ne passe pas 5.3, il n'est pas finaliste. Script : `scripts/c15_banc_reel.py` (cartes de c13h par morceaux en cache, variantes `blocs64` et `d11blocs64`), puis `c15_banc_essais.py B1r_bloc64 --cm11`.

### 14 h 40. Mesure réelle de B1 (`B1r_bloc64`)

Cartes réelles par morceaux : `scripts/c15_banc_reel.py --fils 2` (14 h 27 à 14 h 40). Surface de c13h calculée : dense 1,00, plantain 1,04, MM 1,00, btd_val 0,99, `val_negatifs` 0,13 (à 11 cm : dense 1,00, plantain 1,02, btd_val 1,02, MM 0,76).

| candidat | seuil | dense | plantain | jeunes | MM | btd_val | moyenne 5 | 4 anciennes | erreur | neg | 11 cm | 4 anciennes à 11 cm | 5.3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1r_bloc64 | 0,30 | 0,7838 | 0,8866 | 0,9180 | 0,8633 | 0,9885 | 0,8880 | 0,8629 | 0,118 | 6 (0,09 %) | 0,8476 | 0,8242 | oui |

Le calcul réel rend presque exactement l'approximation (plantain −0,0001 : une détection). Par ma règle de décision de 13 h 58, B1r **n'est pas proposé** : ses 4 anciennes (0,8629) sont sous CC1 (0,8630) d'une détection, sa moyenne est plus basse (0,8880 contre 0,8886), et il n'est plus rapide que hors bananeraie.

### 14 h 42. Bilan et décision

- 9 essais (1 à 9) + la remesure réelle de B1 (même candidat, pas un essai neuf). Contrôles : v5, CC1_v5h_50 et CC3_a1_a35 retrouvés au chiffre près.
- Passent 5.3 : W_v5h_60, W_logit_50, T_cc1_trous20, B1_bloc64 (B1r réel), B2_bloc32 (approché). **Aucun n'est proposé** : aucun ne dépasse la moyenne de CC1 (0,8886), et aucun n'est plus rapide que CC1 sur une bananeraie. W_logit_50 et B2_bloc32 dépassent CC1 sur les 4 anciennes d'une à deux détections (0,8640 et 0,8639) au même coût, en perdant btd_val et surtout le 11 cm.
- Réponse à la question : **le gain de CC1 hors btd_val ne se garde pas à moindre coût**, ni par une porte par image (G), ni par une carte de c13h réduite (S), ni par blocs (B : le v5 hésite partout dans une bananeraie). Le coût de CC1 ne baisse que sur les zones sans bananier.
- Livrable : `out/comptage/jour_1511/banc/finalistes.md`.
