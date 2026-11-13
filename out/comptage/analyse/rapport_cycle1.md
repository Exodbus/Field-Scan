# Analyse d'erreurs du comptage, cycle 1 (agent C-analyste, nuit du 12 au 13 novembre 2026)

Jeux de **réglage seulement** : banavista session B (« dense », 84 photos, disque), `plantas_platano` 100_metros (« plantain », 165 tuiles), jeunes dji_0544, MM1-MM2, sans bananier de validation (1 424 tuiles), et la moitié validation de `banana_tree_detection` (« btd_val », 178 tuiles, 17 264 plants, découpage v6 de D-comptage). **Aucun juge n'a été lu** (ni segmento est, ni CG, ni banano, ni sans bananier du test). Modèles mesurés à leur seuil adopté : v3 0,20, v4 0,40, v5 0,30. Mesure : celle du banc de C-banc (pics fenêtre 7, rayon 20 px, appariement un-à-un, disque, points non-mères ignorés), importée telle quelle ; mes chiffres du v5 retombent sur ceux du banc (dense 0,7795, plantain 0,8865, jeunes 0,8926, MM 0,8571, 16 fausses sans bananier).

Étiquettes : [O] observé sur une image nommée ou un fichier, [M] mesuré (script et fichier de sortie donnés), [H] hypothèse. Aucun choix de modèle ni de seuil n'est fait ici ; l'esquisse d'aiguillage (section 3.5) a été regardée sur le réglage et ses chiffres sont optimistes.

## 1. Essais recommandés (classés par gain attendu)

1. **Apprendre les jeunes plants espacés pour de vrai : v6a avec btd_train (186 tuiles, 18 850 plants) et un tirage équilibré par taille de plant** (au moins 25 % des plants tirés sous 40 px de boîte à 5 cm). Gain attendu : F1 btd_val de 0,47 vers 0,80 (niveau du v3 : 0,81), soit environ +0,06 sur la moyenne des 5 F1, sans perte ailleurs si le dense reste dans le tirage.
   - Pourquoi : 87 % des plants de btd_val ont une boîte < 40 px ; le v5 en retrouve 0,11 (< 30 px) et 0,36 (30-40 px), le v3 0,52 et 0,81 avec **le même réseau, la même sortie au quart et la même résolution** [M]. Le défaut n'est donc pas l'architecture mais l'apprentissage : 1,1 % des boîtes d'entraînement du v5 font moins de 30 px, 6,4 % moins de 40 px ; banavista (43 639 boîtes, médiane 64 px) en fait près de la moitié [M].
   - Priorité dans les carnets : la donnée réelle (btd_train) avant l'augmentation d'échelle 0,5-2, car agrandir ou réduire l'image ne reproduit pas l'aspect d'un jeune plant (point 3).
2. **Sans entraînement, tout de suite (essai 5 de C-banc) : aiguillage par image sur le 90e centile des scores des pics du v5.** Si ce p90 (pics >= 0,15 dans la zone comptée) est sous 0,50, prendre le v3 au seuil 0,20 ; sinon le v5 à 0,30. Esquisse sur le réglage [M] : moyenne des 5 F1 0,778 -> 0,841 (+0,063) ; btd 0,473 -> 0,794 ; dense, jeunes et MM inchangés ; plantain -0,007 ; détectés / annotés sur btd 0,33 -> 0,73 ; 26 fausses sans bananier (0,40 %, sous 1 %). Le signal sépare bien les jeux : sous 0,50, 91 % des images btd, 8,5 % des tuiles plantain, aucune image dense, MM ou jeunes.
   - Variante sans le v3 (« v5 à 0,15 sous 0,50 ») : btd 0,777 mais 2,29 % de fausses sans bananier : refusée par la règle des 1 % ; à 0,20 : btd 0,700 et 0,94 % (limite).
   - Réserves pour la lecture des juges : le v3 a été choisi sur segmento est (biais déjà noté par C-banc) ; on ne sait pas de quel côté tomberont CG et banano.
3. **Ne pas dépenser de GPU sur « plus de pixels » pour les petits plants** (multi-échelle 3,5 cm, essai 4 ; sortie à la demi-résolution du v6b) avant les points 1 et 2.
   - Agrandir l'image (5 -> 3,5 cm) **fait baisser** le rappel des petits plants du v5 au seuil 0,30 : boîtes < 25 px 0,06 -> 0,02, 25-30 px 0,15 -> 0,08 ; F1 btd 0,473 -> 0,439. Seuls les plants de 40 px et plus gagnent un peu (0,69 -> 0,73) [M].
   - Deux plants sur un même pic (« fusion ») : 0 % des oubliés sur btd, 1 % sur le dense [M]. La sortie au quart ne fusionne donc pas les plants.
   - Le seul étage où la résolution peut limiter : les boîtes < 20 px (1 m), 2,8 % des plants de btd_val (488), retrouvées à 0,02 (v5), 0,09 (v4) et 0,24 (v3). Gain maximal de la demi-résolution : environ 2 % de rappel sur btd.
   - La « gaussienne qui suit la taille du plant » du v6b existe déjà dans le v5 (carnet, `carte_cible` : écart-type = taille / 24 cellules, au moins 0,8) [O].
4. **Mesure, à proposer au chef d'orchestre : retirer les doublons d'annotation du plantain** (deux points à moins de 3 px). 61 paires (122 points, distance médiane 1,9 px) [M] : une seule des deux peut être appariée, donc 61 des 168 oubliés du v5 (36 %) sont impossibles pour tous les modèles ; le rappel plafonne à 0,977. Correction automatique comparable à l'exclusion des 16 tuiles btd aux annotations fausses ; elle ne change pas le classement des modèles mais rend l'erreur de compte du plantain plus juste (environ +0,02 de rappel pour chacun : 0,936 -> 0,958 pour le v5). À décider avant toute mesure de candidat, ou à ne pas faire.
5. **Dense : pas de gain par le seuil ; tenter les vues multiples (essai 2) et le mélange (essai 3) en visant les pieds « presque » détectés.** 74 % des oubliés du v5 sur le dense ont un pic entre 0,15 et 0,30, mais baisser le seuil de 0,30 à 0,25 gagne 500 pieds pour 858 fausses (1,7 fausse par pied gagné ; F1 0,779 -> 0,776) [M]. Les oubliés sont des pieds serrés (51 % ont un voisin annoté à moins de 40 px, rappel 0,55 sous 30 px) ou petits sous la canopée (44 % ont une boîte < 50 px, rappel 0,40 à 0,58) [M]. Le v3 retrouve 38 % des oubliés du v5 (v3 ou v4 : 44 %) [M]. Gain attendu faible : de l'ordre de 0,01 sur le dense.
6. **Marge au bord (essai 9), plantain surtout.** Densité de fausses 1,3 à 1,6 fois plus forte à moins de 40 px du bord des tuiles plantain [M] ; [O] ce sont souvent des plants entiers ou coupés, non annotés, au bord (`planches/fausses_v5_plantain.jpg`). Gain attendu : quelques millièmes de F1 sur le plantain ; sans effet sur le dense (1,1 à 1,25).

## 2. Trois constats principaux

1. **Le recul du v5 sur la plantation espacée est un effet de taille du plant, appris à l'entraînement, et il est réversible sans entraînement.** Le score du v5 croît avec la taille de la boîte au même rythme sur le dense et sur btd (boîte 40-50 px : médiane du meilleur pic 0,34 et 0,36 ; 50-60 px : 0,44 et 0,50) [M]. Sur btd, 93 % des oubliés du v5 ont un pic (>= 0,05) et 61 % un pic entre 0,15 et 0,30 : le v5 voit les jeunes plants mais leur donne un score bas. Baisser le seuil y coûte 0,16 fausse par pied gagné, contre 2,1 sur le dense.
2. **Agrandir l'image n'aide pas ; ce n'est pas la résolution qui manque.** Le v5 à 3,5 cm fait moins bien sur les petits plants qu'à 5 cm ; le v3, au même pas de sortie, en retrouve 52 % sous 30 px. [O] Sur btd, les fausses détections du v5 tombent au milieu de la double rangée, sur la gaine d'irrigation, entre 2 à 4 petits plants (`planches/fausses_v5_btd_val.jpg`) : le réseau prend le groupe pour une seule grande couronne. [H] L'aspect d'un jeune plant (petite étoile sur paillage) manque à l'apprentissage ; seule une donnée réelle (btd_train) le corrige.
3. **Une bonne part des « erreurs » mesurées sur le réglage vient des annotations.** Plantain : 36 % des oubliés du v5 sont des doublons d'annotation à moins de 3 px [M]. Fausses « isolées » (rien d'annoté à 40 px) : 61 % des fausses du v5 sur le dense, 65 % sur le plantain ; le v3 détecte au même endroit dans 80 % et 96 % des cas, autant que pour les vraies détections (88 % et 96 %) [M] ; [O] beaucoup sont des plants visibles non annotés (`planches/fausses_v5_plantain.jpg`, `planches/image_plantain_pp_100_metros_0042.jpg`, `planches/image_dense_bv_bv_b_val_0010.jpg`). La précision mesurée est donc un plancher, et un candidat qui « supprime des fausses » sur ces jeux peut supprimer de vrais pieds.

## 3. Détail des mesures

Tables complètes : `tables_base.md` (4 validations du v5), `tables_btd.md` (btd_val), `compl_base.md`, `compl_btd.md`, `score_taille.md`, `echelle_btd_v5.md`, `signaux.md`, `aiguillage.md`. Données pied par pied : `pieds_base.csv`, `pieds_btd.csv` ; fausses : `fausses_base.csv`, `fausses_btd.csv`, `neg_v3.csv`, `neg_v4.csv`, `neg_v5.csv`.

### 3.1 Rappel par jeu et rapport détectés / annotés [M]

| modèle (seuil) | dense | plantain | jeunes | MM | btd_val |
| --- | --- | --- | --- | --- | --- |
| v5 (0,30) | 0,81 (1,08) | 0,94 (1,11) | 0,92 (1,16) | 0,91 (1,29) | 0,31 (0,33) |
| v3 (0,20) | 0,79 (1,21) | 0,93 (1,25) | 0,84 (1,05) | 0,84 (1,07) | 0,72 (0,76) |
| v4 (0,40) | 0,72 (1,00) | 0,89 (0,99) | 0,92 (1,14) | 0,84 (1,22) | 0,54 (0,55) |

F1 btd_val : v5 0,473, v3 0,811, v4 0,700 [M]. Sur btd_val, le v5 détecte 3 fois moins de pieds qu'il n'y en a ; partout ailleurs il en détecte 8 à 29 % de trop.

### 3.2 Taille du plant

Rappel selon la boîte (px à 5 cm ; 20 px = 1 m) [M] :

| modèle | jeu | < 30 | 30-40 | 40-50 | 50-60 | 60-70 | 70-80 | >= 80 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v5 | dense | 0,40 | 0,46 | 0,58 | 0,78 | 0,89 | 0,95 | 0,98 |
| v3 | dense | 0,40 | 0,55 | 0,64 | 0,77 | 0,84 | 0,89 | 0,92 |
| v5 | btd_val | 0,11 | 0,36 | 0,69 | 0,90 | - | - | - |
| v3 | btd_val | 0,52 | 0,81 | 0,91 | 0,98 | - | - | - |
| v4 | btd_val | 0,32 | 0,63 | 0,84 | 0,93 | - | - | - |

Effectifs btd_val : 6 413 plants < 30 px, 8 555 de 30 à 40 px, 2 212 de 40 à 50 px, 84 au-dessus. Dense : 423 sous 40 px, 1 078 de 40 à 50 px. Le v3 vaut mieux que le v5 sous 50 px, le v5 mieux au-dessus de 60 px (dense) : les deux se complètent par la taille.

Plantain, jeunes et MM n'ont pas de taille annotée. Le « rayon vert » estimé sur l'image (anneaux à plus de 50 % de pixels verts) [H] sature dans la canopée fermée et ne sépare rien sur ces jeux (rappel 0,8 à 1 dans toutes les classes) : je ne m'en sers pour aucune conclusion.

### 3.3 Voisinage et bord [M]

- Plus proche voisin annoté : dense, rappel du v5 0,55 sous 30 px, 0,71 de 30 à 40 px, 0,90 au-delà de 50 px. Plantain : 0,48 sous 30 px, dû aux doublons d'annotation (122 des 128 points sous 30 px sont à moins de 3 px d'un autre). btd : pas d'effet de voisinage (presque tous les plants à 40-60 px).
- Bord de la zone comptée (image, disque ou carré MM) : dense, rappel du v5 0,58 à moins de 20 px du bord contre 0,86 au-delà de 160 px (16 % des oubliés du dense sont à moins de 20 px du bord) ; btd 0,24 contre 0,29 ; plantain 0,90 contre 0,94. Plants coupés par le bord du disque ou de la photo.

### 3.4 Profil de score des oubliés [M]

| modèle | jeu | oubliés | fusion (pic pris par un voisin) | pic dans [seuil/2, seuil) | pic dans [0,05, seuil/2) | aucun pic >= 0,05 |
| --- | --- | --- | --- | --- | --- | --- |
| v5 | dense | 1 560 | 1 % | 74 % | 10 % | 14 % |
| v5 | plantain | 168 | 35 % (doublons d'annotation) | 55 % | 5 % | 5 % |
| v5 | btd_val | 11 833 | 0 % | 61 % | 32 % | 8 % |
| v3 | dense | 1 748 | 2 % | 54 % | 14 % | 30 % |
| v3 | btd_val | 4 917 | 0 % | 60 % | 16 % | 24 % |

Coût d'une baisse du seuil du v5 (fausses ajoutées par pied gagné, de 0,30 à 0,20) : dense 2,1, plantain 5,1, jeunes 8, MM 17, btd 0,16 [M] (`compl_base.md`, `compl_btd.md`).

### 3.5 Fausses détections du v5 : sur quoi [M]

| jeu | fausses | doublon d'un pied retrouvé | décalée (20-40 px d'une mère oubliée) | bord (<= 20 px) | isolée (rien à 40 px) | sur un rejet annoté (ignorée, non comptée) |
| --- | --- | --- | --- | --- | --- | --- |
| dense | 2 195 | 472 | 178 | 202 | 1 338 | 0 |
| plantain | 463 | 21 | 10 | 131 | 301 | 0 |
| jeunes | 16 | 10 | 0 | 4 | 1 | 13 |
| MM | 15 | 7 | 1 | 2 | 2 | 11 |
| btd_val | 291 | 87 | 193 | 5 | 6 | 0 |

- Doublons (deuxième pic sur un pied déjà retrouvé) : sur le dense, pas liés aux grands pieds (taille médiane du pied visé 59 px, comme l'ensemble) ; sur btd, ce sont les pics au milieu de la double rangée [O].
- Jeunes et MM : la moitié des détections non appariées tombent sur des rejets annotés (ignorés par la mesure) ; [O] `planches/fausses_v5_mm.jpg` : les autres sont surtout de petits bananiers non annotés comme mères. Le modèle ne distingue pas mère et rejet ; la mesure le pardonne seulement quand le rejet est annoté.
- Sans bananier (validation) : v5 16 fausses sur 6 459 arbres (0,25 %), toutes sur palmiers, dont 9 vignettes du même palmier gris vu dans plusieurs tuiles qui se recouvrent [O] ; v3 26 (dont 3 cocotiers), v4 7.

### 3.6 Écart v3 / v5 pied par pied [M]

| jeu | les deux | v3 seul | v5 seul | aucun |
| --- | --- | --- | --- | --- |
| dense | 5 863 | 585 | 773 | 975 |
| plantain | 2 362 | 74 | 103 | 94 |
| jeunes | 96 | 3 | 12 | 7 |
| MM | 56 | 2 | 7 | 4 |
| btd_val | 5 122 | 7 225 | 309 | 4 608 |

Le v5 gagne sur le dense, les jeunes et MM ; le v3 l'écrase sur btd. Les oubliés « v3 seul » du dense sont surtout petits (boîtes < 50 px, section 3.2).

### 3.7 Échelle [M] (`echelle_btd_v5.md`)

| v5, seuil 0,30 | F1 btd | < 25 px | 25-30 | 30-35 | 35-40 | 40-50 | >= 50 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 cm (base) | 0,473 | 0,06 | 0,15 | 0,29 | 0,46 | 0,69 | 0,90 |
| 3,5 cm (image agrandie) | 0,439 | 0,02 | 0,08 | 0,24 | 0,47 | 0,73 | 0,94 |
| 7 cm (image réduite) | 0,099 | 0,03 | 0,04 | 0,05 | 0,07 | 0,11 | 0,40 |

Même constat à tous les seuils de 0,15 à 0,40. Le calcul à 3,5 cm du v3 et du dense a été arrêté pour libérer la machine.

### 3.8 Signal d'aiguillage [M] (`signaux.md`, `aiguillage.md`)

90e centile des scores des pics du v5 (>= 0,15), quantiles 10 / 50 / 90 % des images : dense 0,68 / 0,72 / 0,76 ; plantain 0,56 / 0,73 / 0,81 ; btd_val 0,35 / 0,41 / 0,49 ; MM 0,78 à 0,80 ; jeunes 0,94. Le nombre de pics et l'espacement médian séparent moins bien (espacement btd 40 / 49 / 52 px contre 42 / 47 / 53 px sur le plantain).

| règle (regardée sur le réglage) | dense | plantain | jeunes | MM | btd_val | moyenne | sans bananier |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v5 seul à 0,30 | 0,779 | 0,887 | 0,893 | 0,857 | 0,473 | 0,778 | 16 (0,25 %) |
| v5 à 0,15 si p90 < 0,50 | 0,779 | 0,877 | 0,893 | 0,857 | 0,777 | 0,837 | 148 (2,29 %) |
| v5 à 0,20 si p90 < 0,50 | 0,779 | 0,880 | 0,893 | 0,857 | 0,700 | 0,822 | 61 (0,94 %) |
| v3 à 0,20 si p90 < 0,50 | 0,779 | 0,880 | 0,893 | 0,857 | 0,794 | 0,841 | 26 (0,40 %) |

## 4. Planches de contrôle à l'œil (`out/comptage/analyse/planches/`)

Vignettes de 6,4 m tirées au hasard (graine 0) par catégorie ; cercle vert : mère annotée (épais : le pied visé) ; jaune : rejet ; croix rouge : v5 ; croix bleue : v3.
- `oublies_v5_<jeu>.jpg` et `fausses_v5_<jeu>.jpg` pour dense, plantain, jeunes, mm, btd_val ;
- images entières : `image_dense_bv_bv_b_val_0010.jpg`, `image_dense_bv_bv_b_val_0050.jpg`, `image_plantain_pp_100_metros_0042.jpg`, `image_plantain_pp_100_metros_0060.jpg`, `image_btd_val_btd_0169.jpg` ;
- `fausses_v5_sans_bananier.jpg` (les 16 fausses du v5 sur les palmiers).

## 5. Scripts (tous `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u`)

`scripts/v6_analyse_erreurs.py` (pied par pied, fausses par catégorie), `v6_analyse_resume.py` (tables), `v6_analyse_compl.py` (co-détection, seuils, doublons, bord, mélange), `v6_analyse_score_taille.py`, `v6_analyse_echelle.py`, `v6_analyse_signal.py`, `v6_analyse_aiguillage.py`, `v6_analyse_neg.py`, `v6_analyse_cache.py` (cartes manquantes, 3 fils, dans `out/comptage/analyse/cache/`), `v6_analyse_planches.py`, `v6_analyse_image.py`. La correspondance des tuiles btd_val (noms v5 -> découpage v6) est dans `btd_val_tuiles.csv`.

## 6. Limites

- Les annotations du réglage sont incomplètes (section 2, constat 3) : précision sous-estimée, surtout sur le plantain et le dense.
- btd_val est une seule orthomosaïque, et la moitié entraînement (btd_train) en est voisine : un v6 qui l'apprend sera optimiste sur btd_val.
- L'esquisse d'aiguillage a été regardée sur le réglage avec 4 règles : à refaire par C-banc avec sa propre règle écrite avant, et à confirmer sur les juges.
- Les candidats de la nuit (C-banc, C-entraîneur) n'ont pas encore de résultats au moment de ce rapport : l'analyse des candidats viendra au cycle suivant.

## 7. Premier regard sur les candidats de C-banc (23:45, `out/comptage_v6/banc/essais.json`, lecture seule)

140 variantes mesurées sur les 5 jeux de réglage (essais 3, 5, 6, 7). Classement au meilleur seuil de chacun par la moyenne des 5 F1 (lecture d'analyste, pas la règle 3.4 de C-banc) [M] :
- v5 à 0,30 : 0,778 (btd 0,473) ; mes chiffres du v5 sur btd_val sont identiques (0,473), la correspondance des tuiles est donc la même.
- **E5 aiguillage v3 par taille des pics** (`taille8_d0.1`) : 0,842 ; btd 0,809 ; plantain 0,872 (-0,015, près de la limite de 0,020) ; sans bananier 0,25 %.
- E7 union v5 + v3 : 0,835 ; dense 0,765 (-0,014), plantain 0,863 (-0,024 : hors limite).
- E6 seuil relatif par image (v5) : 0,835 ; btd 0,779 ; plantain -0,016 ; sans bananier 0,57 %.

Ce que ça dit, au regard des sections 3.2 à 3.8 :
- Tous les gros gains viennent de btd, c'est-à-dire des petits plants : aucun candidat sans entraînement ne gagne plus de 0,01 sur le dense, ce qui confirme l'essai recommandé 5 (gain faible sur le dense).
- Le meilleur (E5) revient à « le v3 sur btd » : il récupère les plants de 30 à 50 px, mais garde les limites du v3 sous 30 px (rappel 0,52) et sous 20 px (0,24) [M, section 3.2]. Ce qui reste à gagner sur btd (le v3 y oublie 4 917 plants, dont 60 % avec un pic entre 0,10 et 0,20) demande l'entraînement (essai recommandé 1).
- Le coût sur le plantain (-0,015) vient des tuiles plantain envoyées vers le v3 ; le signal p90 de la section 3.8 n'en envoie que 8,5 % et ne perd que 0,007 sur le plantain dans mon esquisse. **Suggestion à C-banc : ajouter le critère p90 (90e centile des scores des pics du v5 >= 0,15, coupure 0,50) à l'essai 5**, en écrivant sa règle avant.
- L'analyse pied par pied des candidats (quels oubliés ils récupèrent, lesquels restent) demande leurs détections ; C-banc ne les écrit pas. Je la ferai au cycle suivant en recalculant le ou les finalistes à partir du cache.
