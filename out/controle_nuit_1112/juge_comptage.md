# Juge comptage : finalistes gelés sur les juges (nuit du 12 au 13 novembre 2026)

Agent Juge comptage. Règles appliquées sans changement : `docs/plan_nuit_2026-11-12.md` (3.4 adoption, 3.5 test vierge) et `docs/nuit_2026-11-12/regle_gel_finalistes.md`. Chaque juge a été lu **une fois**. Rien n'a été réglé sur eux. Journal : `docs/nuit_2026-11-12/journal_juge_comptage.md`.

**Verdict : aucune adoption.** Aucun des trois finalistes ne remplit les trois conditions. Le v5 au seuil 0,30 reste en service. Le test vierge n'a pas été lu.

## 1. Liste gelée

Liste lue en tête de `out/controle_nuit_1112/verdicts.md` (version 12, écrite à 7 h 00, lue à 7 h 02). Elle est conforme à la liste attendue.

| Place | Finaliste | Famille | Seuil | Moyenne de réglage (5 F1, ONNX) | Modèles |
| --- | --- | --- | --- | --- | --- |
| 1 | `E10_moy_v6e+v5` | C | 0,30 | 0,8822 | v6e + v5 (moyenne des cartes) |
| 2 | `v6f`, graine 0 | B | 0,35 | 0,8780 | v6f (ResNet-34) |
| 3 | `E5p90b_moy34_v5_d0.1` | A | 0,30 | 0,8549 | v5 ; v3 + v4 si l'image est aiguillée |

- **Empreintes** : les SHA-256 des cinq ONNX (v3, v4, v5, v6e, v6f) sont identiques à `out/controle_nuit_1112/empreintes_liste_gelee.txt`. Vérifiés à 6 h 48, à 7 h 02, puis à chaque calcul de cartes par `cartes()` pour v6e et v6f. Les scripts `controle_nuit_c_appliquer.py`, `controle_nuit_c_recalcul.py`, `v6_banc_commun.py` et `v6_banc_candidats.py` sont aussi identiques.
- **Non lus** : v6a, v6d et E7, absents de la liste.

## 2. Juges et mesure

- **Juges** (`data/drone/comptage_v5_5cm`, identiques à ceux de `comptage_v6_5cm` : mêmes noms d'images, `cg/` identique au MD5) :
  - segmento est (`test_dense`) : 39 images, 4 067 plants ;
  - CG1 à CG9, mères seules (`cg/`) : 9 zones, 290 mères ;
  - `banano_dense` (`test_banano`) : 71 tuiles, 5 029 plants ;
  - images sans bananier (`test_negatifs`) : 1 667 tuiles, 7 876 arbres.
- **Mesure principale** : `scripts/juge_nuit_c_mesure.py`.
  - Il reprend tels quels les éléments du Contrôleur : `items_generiques` et `cartes` de `controle_nuit_c_appliquer.py`, `candidat` et `apparier` de `controle_nuit_c_recalcul.py`.
  - Méthode : pics 7 × 7, appariement hongrois à 20 px, non-mères ignorées, disque DJI, zones CG.
  - Il n'ajoute que la précision, le rappel et la part d'images aiguillées.
  - Contrôle : pour chaque candidat, `R.mesurer` du Contrôleur, appelé sans modification, devait redonner le même F1 et la même erreur de compte. C'est le cas sur tous les jeux.
- **Deuxième avis** : `scripts/juge_nuit_c_second_avis.py`.
  - Il reprend le banc de C-banc (`v6_banc_commun.py`, `v6_banc_candidats.py`, réglages lus dans `essais.json`), avec des cartes recalculées à part (`juge_c/cache2_banano`).
  - Sur banano, il est **identique** à la mesure principale pour les cinq candidats : P, R, F1 et nombre de détectés au chiffre près. Aucun écart à signaler.
- **Essai préalable** sur MM (un jeu de réglage, pas un juge) : les deux codes retrouvent exactement les chiffres de réglage publiés.

## 3. Témoin : v5 à 0,30 contre son protocole (`docs/protocole_comptage_v5.md`, section 9)

| Juge | Publié (carnet v5, GPU) | Mesuré cette nuit (ONNX, processeur) | Écart |
| --- | --- | --- | --- |
| banano | P 0,841, R 0,776, F1 0,807 (4 641 / 5 029) | P 0,8436, R 0,7755, F1 0,8081 (4 623 / 5 029) | F1 +0,001 ; 18 détections de moins |
| segmento est | P 0,807, R 0,577, F1 0,673 (2 908 / 4 067) | P 0,8180, R 0,5781, F1 0,6774 (2 874 / 4 067) | F1 +0,004 ; 34 détections de moins |
| CG, mères seules | P 0,848, R 0,193, F1 0,315 | P 0,8485, R 0,1931, F1 0,3146 (66 / 290) | identique |
| sans bananier | 36 / 7 876 arbres (0,5 %) | 36 / 7 876 (0,46 %) | identique |

Le témoin est retrouvé. Les petits écarts sur banano et segmento restent sous 0,004 de F1 et sous 1 % des détections. C'est l'ordre de grandeur de l'écart ONNX contre carnet GPU déjà relevé au réglage (jusqu'à 0,007 sur MM). Ils ne changent pas la règle : tous les candidats, v5 compris, passent par le même code.

## 4. Tableaux

### 4.1 Par juge

Chaque case donne P / R / F1, puis détectés / annotés, puis l'erreur de compte (|détectés / annotés − 1|).

| Candidat | Seuil | segmento est | CG mères seules | banano |
| --- | --- | --- | --- | --- |
| `E10_moy_v6e+v5` | 0,30 | 0,814 / 0,639 / **0,716** ; 3 195 / 4 067 ; 0,214 | 0,885 / 0,079 / **0,146** ; 27 / 290 ; 0,907 | 0,830 / 0,787 / **0,808** ; 4 766 / 5 029 ; 0,052 |
| `v6f` | 0,35 | 0,838 / 0,614 / **0,709** ; 2 981 / 4 067 ; 0,267 | 0,471 / 0,083 / **0,141** ; 51 / 290 ; 0,824 | 0,856 / 0,756 / **0,803** ; 4 443 / 5 029 ; 0,117 |
| `E5p90b_moy34_v5_d0.1` | 0,30 | 0,737 / 0,676 / **0,705** ; 3 728 / 4 067 ; 0,083 | 0,748 / 0,379 / **0,503** ; 150 / 290 ; 0,483 | 0,843 / 0,776 / **0,808** ; 4 627 / 5 029 ; 0,080 |
| v5 (référence) | 0,30 | 0,818 / 0,578 / **0,677** ; 2 874 / 4 067 ; 0,293 | 0,848 / 0,193 / **0,315** ; 66 / 290 ; 0,772 | 0,844 / 0,776 / **0,808** ; 4 623 / 5 029 ; 0,081 |
| v5 (information) | 0,20 | 0,711 / 0,763 / **0,736** ; 4 363 / 4 067 ; 0,073 | 0,714 / 0,310 / **0,433** ; 128 / 290 ; 0,559 | 0,783 / 0,840 / **0,811** ; 5 395 / 5 029 ; 0,073 |

### 4.2 Moyennes et fausses détections

| Candidat | F1 moyen (3 juges) | Erreur de compte moyenne (3 juges) | F1 moyen sans segmento est | Erreur moyenne sans segmento est | Fausses détections sans bananier |
| --- | --- | --- | --- | --- | --- |
| `E10_moy_v6e+v5` | 0,5564 | 0,391 | 0,4767 | 0,480 | 18 / 7 876 (0,23 %) |
| `v6f` | 0,5508 | 0,403 | 0,4719 | 0,470 | 10 / 7 876 (0,13 %) |
| `E5p90b_moy34_v5_d0.1` | **0,6722** | **0,215** | **0,6556** | **0,281** | **88 / 7 876 (1,12 %)** |
| v5 à 0,30 (référence) | 0,6001 | 0,382 | 0,5614 | 0,427 | 36 / 7 876 (0,46 %) |
| v5 à 0,20 (information) | 0,6597 | 0,235 | 0,6218 | 0,316 | 192 / 7 876 (2,44 %) |

### 4.3 E5p90b : images aiguillées vers la branche « petits » (v3 + v4)

| Jeu | Images aiguillées |
| --- | --- |
| segmento est | 15 / 39 (38 %) |
| CG | 9 / 9 (100 %) |
| banano | 3 / 71 (4 %) |
| sans bananier | 328 / 1 667 (20 %) |

## 5. Verdict (règle 3.4, une lecture)

Seuils de la règle, calculés sur le v5 à 0,30 :
- F1 moyen ≥ 0,6001 − 0,010 = **0,5901** ;
- erreur de compte moyenne ≤ **0,382** ;
- fausses détections sans bananier **< 1 %**.

| Finaliste | F1 moyen ≥ 0,5901 | Erreur ≤ 0,382 | Fausses < 1 % | Résultat |
| --- | --- | --- | --- | --- |
| `E10_moy_v6e+v5` | non (0,5564) | non (0,391) | oui (0,23 %) | **échoue** |
| `v6f` | non (0,5508) | non (0,403) | oui (0,13 %) | **échoue** |
| `E5p90b_moy34_v5_d0.1` | oui (0,6722) | oui (0,215) | **non (1,12 %)** | **échoue** |

Lecture :
- **E10 et v6f** :
  - ils égalent le v5 sur banano et le dépassent sur segmento est (+0,03 à +0,04) ;
  - en revanche, ils **s'effondrent sur l'agroforesterie (CG)** : F1 de 0,15 et 0,14 contre 0,31, avec un rappel de 8 % ;
  - les deux réseaux de la nuit ne voient presque plus les pieds mères sous couvert.
- **E5p90b** :
  - il est le meilleur sur le F1 et sur l'erreur de compte, même sans segmento est (0,656 contre 0,561) ;
  - son gain vient surtout de CG, dont toutes les images partent vers v3 + v4 ;
  - mais l'aiguillage envoie aussi 20 % des tuiles sans bananier vers v3 + v4, dont le seuil effectif est de 0,20. Résultat : 88 fausses détections, soit 1,12 %, au-dessus de la limite de 1 % ;
  - c'est rapporté tel quel : la limite n'est pas rediscutée après lecture.

## 6. Adoption

**Aucune.** Le v5 au seuil 0,30 reste le modèle de comptage en service.

## 7. Test vierge (`banana_trees_kp`)

- **Non lu.** La règle ne le fait lire que pour un modèle adopté, et il n'y en a pas. À la reprise de 8 h 52, le chef d'orchestre a aussi demandé de ne pas le lire : Corentin décidera ce matin s'il le fait lire en entier.
- **Prévision de C-analyste** (environ 40 % d'images aiguillées, v5 vers 0,62) : non vérifiée, faute de lecture.
- **Temps estimé d'une lecture complète** [H] :
  - données : 157 photos agrandies 2,22 fois (pour passer à 5 cm/px), 122 Mo d'images ; la taille des photos n'a pas été lue ;
  - débit mesuré cette nuit : environ 0,4 à 0,6 million de pixels par seconde et par modèle, avec 2 fils ;
  - avec des photos d'origine de 640 px (environ 320 millions de pixels après agrandissement) : environ 10 min par modèle avec 2 fils, et environ 1 min de comptage ;
  - v5 seul : environ 10 min ;
  - E5p90b et v5 ensemble (cartes v3, v4 et v5 en 3 processus de 2 fils) : 10 à 15 min ;
  - avec des photos d'origine de 1 024 px, compter environ 2,5 fois plus, soit 25 à 40 min ;
  - ces durées valent pour une machine libre.

## 8. Réserves du Contrôleur à rappeler

- **Le gain de réglage vient entièrement de btd_val**, une plantation tout juste plantée tirée d'une seule orthomosaïque.
  - Hors btd, aucun finaliste ne bat le v5 en service.
  - Le gain est **nul sur banano_finca**.
  - Les juges ne contiennent aucune plantation jeune espacée : ils ne pouvaient montrer que la non-régression. Même celle-ci n'est pas obtenue.
- **E10 et v6f ont appris btd_train**, l'autre moitié de l'orthomosaïque de btd_val.
- **La graine 0 du v6f est peut-être chanceuse** : sa graine 1 échoue à la règle de réglage, et la moyenne des 3 graines (0,8689) est sous celle de v6a.
- **E5p90b contient le v3**, qui a choisi son époque et son seuil sur segmento est. D'où la moyenne sans segmento est en 4.2 : E5p90b y reste devant.
- **Une tuile d'apprentissage dmpcs2 du v6e** est à 5 bits de dHash d'une tuile « sans bananier » de juge (faux positif selon C-prospection). Effet possible seulement sur les fausses détections d'E10, qui en fait peu (0,23 %).

## 9. Fichiers

- Mesures : `out/controle_nuit_1112/juge_c/mesure_{banano,segmento,cg,neg_test}.json` et `log_mesure_*.txt`.
- Règle : `juge_c/regle_adoption.json` et `log_regle.txt`.
- Deuxième avis : `juge_c/second_avis_banano.json` et `log_second_avis_banano.txt`.
- Cartes en cache : `juge_c/cache_*` et `cache2_banano`.
- Scripts : `scripts/juge_nuit_c_mesure.py`, `scripts/juge_nuit_c_second_avis.py`, `scripts/juge_nuit_c_regle.py`.
