# Journal de l'agent C-piste2 (comptage, pistes 2, 14 novembre 2026)

Cadre : `docs/nuit_2026-11-13/avenant_pistes_2.md` (SHA-256 vérifié à 18 h 31 : `baf20929…83b9`, identique à `empreinte_avenant_pistes_2.txt`), plan `docs/plan_nuit_2026-11-13.md` (sections 3, 5, 7). Règles 5.3 inchangées, référence **v5 au seuil 0,30** (dense 0,7795, plantain 0,8865, jeunes 0,8926, MM 0,8571, btd_val 0,4726 ; moyenne 0,7777 ; 4 anciennes 0,8539 ; erreur de compte 0,262 ; `val_negatifs` 16 / 6 459 ; réglage dégradé à 11 cm 0,6006).

Écrit seulement dans `out/comptage/nuit_1311/piste2/`, `scripts/c14_*.py`, `notebooks/c14_*.py`, `modeles/comptage_nuit_1411/` et ce journal. Aucun commit, aucun téléchargement de données. Juges jamais lus : segmento est, CG, `banano_dense`, `test_negatifs`, `banana_trees_kp` (lecture des jeux par `c13_banc_commun.jeu`, qui refuse par `assert` tout jeu hors réglage). De 19 h à 20 h 30 : 3 fils au plus en tout.

Compte d'essais : un essai = un candidat distinct mesuré sur le réglage (tous seuils de la grille confondus ; la mesure à 11 cm d'un candidat déjà compté n'est pas un essai de plus), ou une recette entraînée sur Kaggle.

- 18:31 Démarrage. Lu : CLAUDE.md, avenant pistes 2, plan (3, 5, 7), `out/comptage/nuit_1311/banc/finalistes.md`, `out/comptage/nuit_1311/kaggle/finalistes.md`, journaux C-banc et C-entraîneur, scripts `v6_banc_commun.py`, `v6_banc_candidats.py`, `c13_banc_commun.py`, `c13_banc_candidats.py`, `c13_entr_aiguillage.py`, `c13_entr_mesure.py`, `c13_entr_pousser.py`, `c13_entr_recuperer.py`, lanceur Kaggle `c13_lanceur_kaggle.py`.
- 18:32 [O] Les cartes de **c13h ne sont dans aucun cache** (seuls v3, v4, v5, c13d, c13e). Calcul lancé (`scripts/c14_cache.py`, ONNX `centres_5cm_c13h.onnx`, 3 fils) : 5 jeux + `val_negatifs` à 5 cm, puis 5 jeux dégradés à 11 cm (dégradation `degrader` de `c13_entr_mesure.py`, la même que C-banc et C-entraîneur), dans `out/comptage/nuit_1311/piste2/cache/`. Aucun essai (pas de choix).

## Règles de la piste, écrites à 18 h 40, avant tout calcul de candidat

Commun à toutes les pistes :
- seuil de chaque candidat : règle 5.3 (grille 0,10 à 0,60, meilleure moyenne des 5 F1 sous `val_negatifs` < 1 %) ;
- **finaliste** : les 4 conditions de 5.3 ; **finaliste « résolution »** : moyenne à 11 cm ≥ 0,6306 (v5 dégradé à 0,30 + 0,030) et moyenne à 5 cm ≥ 0,7727, avec les trois autres conditions (aucun jeu à moins de −0,020, erreur ≤ 0,262, `val_negatifs` < 1 %) ;
- réglage dégradé : chaque candidat est lu à 11 cm **au seuil choisi à 5 cm**, cartes de chaque membre calculées sur l'image dégradée ; `val_negatifs` n'est mesuré qu'à sa résolution d'origine ;
- pour information à côté de chaque candidat : moyenne des 4 anciennes (sans `btd_val`), écart à E5p90b_c13e_d-0.1 et à A1 ;
- familles : A (anciens réseaux seuls), C (contient un réseau neuf de la nuit).

### CC1 : mélange de cartes (famille C), 5 essais

Moyenne arithmétique pondérée des cartes de probabilité (même grille au quart), puis pics fenêtre 7 et grille de seuils. Poids fixés ici, aucun autre :

| essai | nom | v5 | c13h | c13e |
| --- | --- | --- | --- | --- |
| 1 | `CC1_v5h_50` | 0,50 | 0,50 | 0 |
| 2 | `CC1_v5h_70` | 0,70 | 0,30 | 0 |
| 3 | `CC1_v5h_30` | 0,30 | 0,70 | 0 |
| 4 | `CC1_v5he_333` | 1/3 | 1/3 | 1/3 |
| 5 | `CC1_v5he_50` | 0,50 | 0,25 | 0,25 |

Règle de choix CC1 : parmi les finalistes ordinaires, la meilleure moyenne des 5 ; parmi les finalistes « résolution » (qui ne sont pas finalistes ordinaires), la meilleure moyenne à 11 cm. Dans les deux cas, un candidat à moins de 0,003 du meilleur et de plus grand poids du v5 est préféré (plus proche de la référence). Au plus un retenu de chaque sorte.

### CC2 : aiguillage c13e + trous de plantation (famille C), 3 essais

Fabriques de C-banc et C-entraîneur importées sans modification (`v6_banc_candidats.f_aiguillage_p90`, `c13_banc_candidats.promouvoir` et `f_aiguillage_v2`).

| essai | nom | définition |
| --- | --- | --- |
| 6 | `CC2_e5c13e_trous20` | E5p90b_c13e_d-0.1 (tau 0,55, branche « petits » = c13e, score − 0,10) ; dans la branche « petits », ancres = score rendu ≥ 0,30, pics bas = score rendu dans [0,20 ; 0,30), promus à 0,30 s'ils bouchent une place vide du réseau (`promouvoir`, mode « reseau », tol_d 0,30), comme A1 |
| 7 | `CC2_e5c13e_trous25` | idem, pics bas dans [0,25 ; 0,30) |
| 8 | `CC2_a1c13e` | A1 (`aiguillage_v2` : tau 0,55, densité ≥ 200 /ha, accord du v5 ≥ 0,05, au moins 30 points « petits » à score rendu ≥ 0,30, trous bas 0,20 mode « reseau ») avec **c13e** à la place de v3 + v4, décalage −0,10 |

Règle de choix CC2 : meilleure moyenne des 5 parmi les finalistes ; `CC2_a1c13e` (garde-fous contre les tuiles sans bananier et le plantain) est préféré s'il est à moins de 0,003 du meilleur.

### CC3 : suppression des maxima à l'écartement de la plantation, 3 + 2 essais

Post-traitement des points d'un candidat, par image :
1. ancres = points de score ≥ 0,30 ; s'il y en a moins de 8, rien ne change ;
2. écartement d = **médiane des distances au 2e plus proche voisin** des ancres (dans un réseau carré ou rectangulaire, le 2e voisin est encore à un écartement ; un pic double sur une même couronne ne fausse que le 1er voisin) ;
3. rayon r = alpha x d, borné à 60 px ; suppression gloutonne par score décroissant : un point est retiré s'il est à moins de r d'un point gardé de score plus haut. Cette suppression donne le même résultat à tous les seuils de la grille (ordre par score).

| essai | nom | base | alpha |
| --- | --- | --- | --- |
| 9 | `CC3_v5_a35` | v5 | 0,35 |
| 10 | `CC3_v5_a45` | v5 | 0,45 |
| 11 | `CC3_v5_a55` | v5 | 0,55 |
| 12 | `CC3_e5c13e_aX` | E5p90b_c13e_d-0.1 | alpha choisi |
| 13 | `CC3_a1_aX` | A1 | alpha choisi |

Règle de choix CC3 : alpha = celui du meilleur finaliste parmi 9 à 11 (meilleure moyenne des 5) ; si aucun n'est finaliste, celui qui a la meilleure moyenne des 4 anciennes **à condition** qu'elle dépasse 0,8539 ; sinon CC3 s'arrête (essais 12 et 13 non faits). Les essais 12 (famille C) et 13 (famille A) appliquent cet alpha, sans autre variante.

### CC4 : Kaggle (P100, 3 h de GPU au plus), 3 recettes

Carnets de C-entraîneur copiés sans modification (`notebooks/c14_travail_centres.py`, `notebooks/c14_lanceur_kaggle.py`), envoi par `scripts/c14_pousser.py` (copie de `c13_entr_pousser.py`, slug `c14-…`, contrôle de fuite gardé : aucune recette ne cite un juge ; le travail retire les ensembles `test_*` et `cg/` par `assert`). Un seul carnet `c14-lot1`, machine **P100**, 3 recettes en parallèle, garde-fou de durée `duree_max_h` 2,3 h par recette :

| essai | nom | recette |
| --- | --- | --- |
| 14 | `c14e_g1` | recette exacte de c13e (tirage « petits », départ ONNX v5, BN figées, 3e-5 / 1e-4, 10 époques, échelle 0,6-1,6), **graine 1** |
| 15 | `c14e_g2` | idem, **graine 2** |
| 16 | `c14j` | c13h avec un réglage fin plus doux (essai c13j prévu par C-entraîneur) : départ `poids_v6f.pt`, parts v6a, dégradation p 0,5 (5-12 cm, JPEG), échelle 0,6-1,6, **1e-5 / 3e-5**, 10 époques |

Lecture (ONNX local, code du banc) :
- 14, 15 : mesurés seuls (information) et **dans E5p90b au décalage −0,10 fixé** (comme le finaliste) : 2 assemblages (essais 17, 18). Donnés tels quels, avec l'écart au finaliste (graine 0) ; **jamais choisis pour leur chance** : ils ne remplacent pas le finaliste, ils mesurent sa stabilité ;
- 16 : mesuré seul (règle 5.3 et « résolution »), puis, s'il en reste le temps, dans le mélange CC1 retenu à la place de c13h, mêmes poids (essai 19, un seul).

Total prévu : 19 essais au plus.

Ordre des calculs : cache c13h (en cours) → CC2 et CC3 (cartes déjà en cache) → CC1 dès que le cache c13h est prêt → CC4 à son retour.

## Calculs

- 18:37 **CC4 envoyé** : carnet privé `affilecorentin/c14-lot1` (`scripts/c14_pousser.py lot1`, recettes c14e_g1, c14j, c14e_g2 exactement comme écrit ci-dessus, jeux `comptage-v6-5cm`, `comptage-v6-maitres`, `comptage-c13-depart`). [O] Kaggle répond « 'NvidiaTeslaP100' is retired. Sessions run on the default GPU (NvidiaTeslaT4) instead » : le carnet tourne donc sur T4. Statut RUNNING à 18 h 39 (pas de file d'attente). Contrôle de fuite : le script refuse toute recette ou tout jeu qui cite un juge ; aucun fichier local n'est envoyé hors du code. 3 recettes = **essais 14 à 16** (comptés au retour).
- 18:39 **Contrôles** (aucun essai) [M] (`scripts/c14_essais.py controle --cm11`, `out/comptage/nuit_1311/piste2/essais.json`) : v5 au seuil 0,30 retrouvé (0,7777 ; 11 cm 0,6005) ; **E5p90b_c13e_d-0.1** : 0,8811, 4 anciennes 0,8544, erreur 0,128, `val_negatifs` 4, 11 cm 0,7850 (identique à C-entraîneur) ; ma fabrique `f_e5` sans trous rend exactement le même ; **A1** : 0,8650, 4 anciennes 0,8539, erreur 0,132, 16, 11 cm 0,6046 (identique à C-banc). Le code de mesure est donc le même.
- 18:40 **CC2, essais 6 à 8** [M] (seuil 5.3 = 0,30 pour les trois) :

| essai | candidat | dense | plantain | jeunes | MM | btd_val | moyenne 5 | 4 anciennes | erreur | val_neg | 11 cm | 5.3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| contrôle | E5p90b_c13e_d-0.1 | 0,7795 | 0,8883 | 0,8926 | 0,8571 | 0,9878 | 0,8811 | 0,8544 | 0,128 | 4 | 0,7850 | finaliste |
| 6 | CC2_e5c13e_trous20 | 0,7795 | 0,8886 | 0,8926 | 0,8571 | 0,9840 | 0,8804 | 0,8544 | 0,131 | 4 | 0,7909 | finaliste |
| 7 | CC2_e5c13e_trous25 | 0,7795 | 0,8888 | 0,8926 | 0,8571 | 0,9859 | 0,8808 | 0,8545 | 0,129 | 4 | 0,7878 | finaliste |
| 8 | CC2_a1c13e | 0,7795 | 0,8865 | 0,8926 | 0,8571 | 0,9693 | 0,8770 | 0,8539 | 0,133 | 16 | 0,6225 | finaliste |

  - Les trois sont finalistes 5.3, mais **les trous n'apportent rien** au-dessus de c13e : btd_val est déjà à 0,988 avec c13e seul, et les places promues y ajoutent plus de fausses que de vrais (0,9878 → 0,9840 / 0,9859). Les garde-fous de A1 (essai 8) coûtent 0,019 sur btd_val et presque tout le gain à 11 cm (0,6225 : à 11 cm les images btd ne franchissent plus 30 points).
  - **Choix CC2 (règle de 18 h 40)** : `CC2_e5c13e_trous25` (0,8808) ; `CC2_a1c13e` est à 0,0038, hors des 0,003. Il ne fait pas mieux que le finaliste E5p90b_c13e_d-0.1 dont il dérive (−0,0003) : **CC2 n'apporte rien** ; je le donne comme variante, pas comme finaliste de réserve distinct.
- 18:40 **CC3, essais 9 à 11** [M] (suppression à l'écartement sur le v5) : la règle 5.3 leur donne le seuil **0,20** (comme au v5 seul, dont la moyenne est maximale à 0,20) : moyenne 0,7926 / 0,7906 / 0,7863, 4 anciennes 0,8147 / 0,8157 / 0,8190, `val_negatifs` 61 : **aucun finaliste**, et aucun n'a une moyenne des 4 anciennes ≥ 0,8539 à son seuil : par la règle de 18 h 40, **CC3 s'arrête là (essais 12 et 13 non faits)**. 11 cm : 0,642 / 0,639 / 0,633 (au seuil 0,20).
  - [O] Pour information (aucun choix) : au seuil 0,30, la suppression touche peu le dense (rapport détectés / annotés 1,077 → 1,075) mais améliore jeunes et MM : alpha 0,45 : jeunes 0,9000 (+0,007), MM 0,8671 (+0,010 ; rapport MM 1,290 → 1,217), 4 anciennes 0,8582 (+0,0043), erreur 0,244 ; btd_val perd (0,473 → 0,464). Le surcompte du dense ne vient donc pas de pics doubles à moins d'un demi-écartement.
- 18:42 **Piste ajoutée CC3b, écrite avant sa mesure** (mais après avoir vu la ligne d'information à 0,30 des essais 9 à 11 : c'est dit ici, et c'est pourquoi les trois alpha sont mesurés sans préférence pour 0,45) : la suppression à l'écartement appliquée **sur les deux finalistes du jour**, dont le seuil 5.3 reste 0,30 :
  - essais 20 à 22 : `CC3_e5c13e_a35`, `_a45`, `_a55` (famille C) ;
  - essais 23 à 25 : `CC3_a1_a35`, `_a45`, `_a55` (famille A).
  - Règle de choix, par base : meilleure moyenne des 5 parmi les finalistes 5.3 ; à moins de 0,003, le plus petit alpha (le moins de changement). Un retenu par base au plus.
- 18:43 **CC3b, essais 20 à 25** [M] (seuil 5.3 = 0,30 pour les six, `val_negatifs` inchangé : 4 pour la base c13e, 16 pour A1) :

| essai | candidat | dense | plantain | jeunes | MM | btd_val | moyenne 5 | 4 anciennes | erreur | 11 cm | 5.3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | CC3_e5c13e_a35 | 0,7795 | 0,8883 | 0,8963 | 0,8630 | 0,9878 | 0,8830 | 0,8568 | 0,123 | 0,7863 | finaliste |
| 21 | CC3_e5c13e_a45 | 0,7792 | 0,8883 | 0,9000 | 0,8671 | 0,9878 | 0,8845 | 0,8587 | 0,108 | 0,7829 | finaliste |
| 22 | CC3_e5c13e_a55 | 0,7791 | 0,8882 | 0,8974 | 0,8633 | 0,9878 | 0,8832 | 0,8570 | 0,084 | 0,7783 | finaliste |
| 23 | CC3_a1_a35 | 0,7795 | 0,8865 | 0,8963 | 0,8630 | 0,9102 | 0,8671 | 0,8563 | 0,128 | 0,6058 | finaliste |
| 24 | CC3_a1_a45 | 0,7792 | 0,8865 | 0,9000 | 0,8671 | 0,9147 | 0,8695 | 0,8582 | 0,115 | 0,6025 | finaliste |
| 25 | CC3_a1_a55 | 0,7791 | 0,8867 | 0,8974 | 0,8633 | 0,9219 | 0,8697 | 0,8566 | 0,096 | 0,5986 | finaliste |

  - **Choix (règle de 18 h 42)** : base c13e : meilleur 0,8845 (alpha 0,45), alpha 0,35 à 0,0015 → **`CC3_e5c13e_a35`** (0,8830) ; base A1 : meilleur 0,8697 (alpha 0,55), alpha 0,35 à 0,0026 → **`CC3_a1_a35`** (0,8671).
  - [O] Le gain est **sur les 4 anciennes** (c'est la première piste du jour qui ne vient pas de btd_val), mais il est minuscule : jeunes = une seule image (+0,004), MM = 2 zones d'environ 69 pieds (+0,006, à peu près un pied) ; dense et plantain inchangés. Dans le bruit d'un pied ou deux.
- 18:44 Message du chef d'orchestre (veille) : vérification des pics par prototypes (DAVE, CountingDINO) et force de la grille avant le remplissage des trous. Pris en note ; facultatif, après CC1 et CC4. [H] La vérification par prototypes demande des descripteurs d'image ; l'ONNX du v5 ne rend que les logits, et un DINO serait un téléchargement : seule une version à descripteurs simples (couleur, texture autour du pic) est possible ici.
- 18:46 **Ajout écrit avant la mesure de CC1** : si CC1 retient un candidat (ordinaire ou « résolution »), la suppression à l'écartement alpha 0,35 (le choix CC3b) lui est appliquée, **un essai par candidat retenu** (essais 26, 27), lu par la même règle 5.3 et donné à côté, sans autre variante.
- 18:46 Cartes de c13h prêtes à 5 cm (dont `val_negatifs`, 570 s) ; à 11 cm à 18 h 52. Contrôle : c13h seul retrouve les chiffres de C-entraîneur (seuil 0,35, 0,8764 ; 11 cm 0,8521) [M].
- 18:47 **CC1, essais 1 à 5** [M] (5 cm ; 11 cm mesuré à 18 h 53 au seuil choisi à 5 cm) :

| essai | candidat | seuil | dense | plantain | jeunes | MM | btd_val | moyenne 5 | **4 anciennes** | erreur | val_neg | 11 cm (4 anciennes à 11 cm) | statut |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| réf. | v5 | 0,30 | 0,7795 | 0,8865 | 0,8926 | 0,8571 | 0,4726 | 0,7777 | 0,8539 | 0,262 | 16 | 0,6005 (0,7471) | référence |
| réf. | E5p90b_c13e_d-0.1 | 0,30 | 0,7795 | 0,8883 | 0,8926 | 0,8571 | 0,9878 | 0,8811 | 0,8544 | 0,128 | 4 | 0,7850 (0,7402) | finaliste du jour |
| info | c13h seul | 0,35 | 0,7781 | 0,8860 | 0,8988 | 0,8308 | 0,9886 | 0,8764 | 0,8484 | 0,067 | 6 | 0,8521 (0,8178) | échoue (MM) |
| 1 | **CC1_v5h_50** | 0,30 | **0,7838** | 0,8867 | **0,9180** | **0,8633** | 0,9912 | **0,8886** | **0,8630** | 0,117 | 7 | **0,8569 (0,8242)** | **finaliste et « résolution »** |
| 2 | CC1_v5h_70 | 0,25 | 0,7792 | 0,8709 | 0,9069 | 0,8435 | 0,9745 | 0,8750 | 0,8501 | 0,198 | 17 | 0,8267 (0,8225) | « résolution » seulement |
| 3 | CC1_v5h_30 | 0,30 | 0,7837 | 0,8837 | 0,9098 | 0,8507 | 0,9907 | 0,8837 | 0,8570 | 0,107 | 6 | 0,8601 (0,8273) | finaliste et « résolution » |
| 4 | CC1_v5he_333 | 0,35 | 0,7776 | 0,8896 | 0,9129 | 0,8429 | 0,9916 | 0,8829 | 0,8557 | 0,076 | 1 | 0,8148 (0,7748) | finaliste et « résolution » |
| 5 | CC1_v5he_50 | 0,35 | 0,7764 | 0,8903 | 0,9083 | 0,8429 | 0,9858 | 0,8807 | 0,8545 | 0,079 | 1 | 0,7811 (0,7573) | finaliste et « résolution » |

  - 11 cm par jeu, CC1_v5h_50 (seuil 0,30) : dense 0,748 (v5 0,622), plantain 0,889 (0,875), jeunes 0,901 (0,768), MM 0,759 (0,724), btd_val 0,988 (0,014).
  - **Choix CC1 (règle de 18 h 40)** : finaliste ordinaire = meilleure moyenne des 5 : **`CC1_v5h_50`** (0,8886 ; aucun candidat à plus grand poids du v5 à moins de 0,003 : CC1_v5h_70 n'est pas finaliste). Finaliste « résolution » qui n'est pas ordinaire : seul **`CC1_v5h_70`** (0,8267 à 11 cm), retenu par la règle, mais **dominé** par CC1_v5h_50 (meilleur à 5 cm et à 11 cm) : je le cite sans le proposer.
  - [O] **Première fois aujourd'hui que le gain ne vient pas que de btd_val** : à 5 cm, moyenne des 4 anciennes 0,8630 contre 0,8539 pour le v5 (+0,009) et 0,8544 pour E5p90b_c13e_d-0.1 ; dense +0,004, jeunes +0,025, MM +0,006, plantain +0,000. Mais les petits jeux pèsent lourd : jeunes = une seule image, MM = deux zones (environ 69 pieds ; +0,006 ≈ un pied). À 11 cm, la moyenne des 4 anciennes gagne +0,077 sur le v5 (dense +0,126, jeunes +0,133, MM +0,035).
  - [O] Rapport détectés / annotés à 5 cm (CC1_v5h_50) : dense 1,130 (v5 1,077), plantain 1,129 (1,112), jeunes 1,161, MM 1,159 (1,290), btd_val 0,994 : le mélange surcompte un peu plus le dense et le plantain, moins MM. Erreur de compte 0,117 contre 0,262.
- 18:53 **Essais 26 et 27** (règle de 18 h 46) [M] : suppression à l'écartement (alpha 0,35) sur CC1_v5h_50 : **aucun point retiré**, chiffres identiques (le mélange n'a plus de pics doubles à moins de 0,35 d) ; sur CC1_v5h_70 : seuil 0,25, 0,8770, 4 anciennes 0,8525, pas finaliste ; 11 cm 0,8172. Rien à retenir.
- 18:54 Consigne du chef d'orchestre : Juges commencés, **2 fils au plus** jusqu'à 20 h 30. Le calcul des cartes c13h est fini ; mes mesures tournent sur 1 fil (`OMP_NUM_THREADS=1`) ; les cartes des modèles c14 seront calculées avec 1 fil d'onnxruntime + 1 fil de mesure au plus.
- 18:55 **Ajout CC4c, écrit avant tout résultat de c14-lot1** : la stabilité qui compte le plus est désormais celle de CC1_v5h_50, qui dépend de c13h (graine 0). Recette `c14h_g1` = recette exacte de c13h (départ `poids_v6f.pt`, parts v6a, dégradation, 3e-5 / 1e-4, 10 époques), **graine 1**. Envoyée en `c14-lot2` seulement **après la fin de c14-lot1** (pour ne pas prendre une 2e place GPU au détriment de M-piste2) et si mon total GPU reste sous 3 h. Lecture : seule (information) et dans CC1_v5h_50 à la place de c13h, mêmes poids, seuil par 5.3 (essai 28) ; donnée telle quelle, jamais choisie pour sa chance. De même, l'essai 19 (c14j dans le mélange) reprend les poids de CC1_v5h_50.
- 18:55 **Comparaison appariée image par image, v5 (0,30) contre CC1_v5h_50 (0,30)** (information, aucun choix, pas un essai) [M] (`scripts/c14_apparie.py`, `out/comptage/nuit_1311/piste2/apparie_v5_CC1_v5h_50.json`), intervalle bootstrap à 95 % sur les images :
  - dense (84 tuiles) : +0,0044 [+0,0002 ; +0,0084] ; VP 6 636 → 6 841, FP 2 195 → 2 418, FN 1 560 → 1 355 ; 48 tuiles mieux, 30 moins bien ;
  - plantain (165) : +0,0002 [−0,0044 ; +0,0049] ; VP 2 465 → 2 485, FP 463 → 487 ;
  - jeunes (1 image) : +0,025 (VP 108 → 112, FP 16 → 14) ;
  - MM (2 zones) : +0,006 [−0,010 ; +0,009] ; VP 63 → 60, FP 15 → 10, FN 6 → 9 : **le mélange rate 3 pieds de plus** et retire 5 fausses ;
  - btd_val : +0,518.
  - [H] Les tuiles d'un même jeu viennent d'une seule orthomosaïque (dense : banavista session B) : elles ne sont pas indépendantes, et l'intervalle est trop étroit. Le gain hors btd_val est donc **petit et fragile** : seul le dense est à peine au-dessus de zéro.
- 18:56 Idées de la veille, décision (sans calcul) : **non prises**.
  - Vérification des pics par prototypes : elle vise les fausses détections sur les tuiles sans bananier ; or CC1_v5h_50 n'en fait que 7 sur `val_negatifs` (0,11 %) et n'aiguille rien. Sans descripteurs appris (l'ONNX ne rend que les logits, un DINO serait un téléchargement), la version « couleur + texture » serait un essai de plus sur un défaut que le réglage ne montre pas.
  - Force de la grille avant le remplissage des trous : CC2 a montré que les trous n'apportent rien au-dessus de c13e (btd_val déjà à 0,988) ; une porte en amont ne peut pas faire mieux.
- 18:56 Information (pas un essai) : cartes de c13h au réglage dégradé à **8 cm** en calcul (1 fil), pour lire CC1_v5h_50 à 8 cm comme C-banc l'a fait pour A1 et A2.
- 19:11 **Réglage dégradé à 8 cm** (information, pas un essai ; c13e n'a pas de cartes à 8 cm, E5p90b_c13e_d-0.1 n'y est donc pas lu) [M] : v5 (0,30) 0,6805 (4 anciennes 0,828) ; A1 0,7055 ; c13h seul (0,35) 0,8627 ; **CC1_v5h_50 (0,30) 0,8655** (dense 0,781, plantain 0,889, jeunes 0,920, MM **0,750** contre 0,770 pour le v5, btd_val 0,988 ; 4 anciennes 0,835) ; CC1_v5h_30 0,8644. [O] À 8 cm, MM perd 0,020 contre le v5 : la limite « aucun jeu à moins de −0,020 » n'est pas une règle du réglage dégradé, mais c'est à dire.
- 19:13 **c14-lot1 fini** (« TOUT EST FINI en 32 min », 2 x T4 ; aucune recette arrêtée par `duree_max_h` : c14e_g1 et c14e_g2 terminés à 29 min, c14j à 32 min). GPU : environ **0,55 h**. Sorties récupérées (`scripts/c14_recuperer.py lot1`) : ONNX, json et poids dans `modeles/comptage_nuit_1411/`, journaux dans `out/comptage/nuit_1311/piste2/kaggle/lot1/`. Écart ONNX / torch ≤ 6e-6. **Essais 14 à 16 faits.** Chiffres du carnet (torch, information ; l'ONNX local fera foi) : c14e_g1 seul seuil 0,45, moyenne 0,8169 ; c14e_g2 seuil 0,40, 0,8120 (c13e : 0,40, 0,8195 dans le carnet) ; **c14j** seuil 0,30, moyenne 0,8733, 4 anciennes 0,8455, 11 cm 0,8536.
- 19:15 **c14-lot2 envoyé** (règle de 18 h 55, après la fin de lot1) : `c14h_g1` (recette c13h, graine 1), 1 recette (**essai 29**), jeux `comptage-v6-5cm`, `comptage-c13-depart`. Kaggle a encore remplacé P100 par T4. Cumul GPU prévu : environ 0,55 + 0,5 h.
- 19:16 Cartes ONNX locales en calcul (`scripts/c14_cache.py`, 2 fils onnxruntime, aucun autre calcul en même temps) : c14e_g1, c14j (avec 11 cm), c14e_g2, puis 11 cm des deux graines c14e.
- [O] Numérotation : l'essai c14h_g1 seul est l'essai 29 ; son mélange dans CC1_v5h_50 est l'essai 28 (voir 18 h 55).
- 19:33 **CC4a, stabilité de c13e, graine 1** [M] (ONNX local, cartes `piste2/cache/c14e_g1_*`) :
  - c14e_g1 seul (information) : seuil 5.3 0,45 ; dense 0,7276, plantain 0,8811, jeunes 0,8992, MM 0,5938, btd_val 0,9902 ; moyenne 0,8184 (c13e seul : 0,40, 0,8216) ; `val_negatifs` 0 ;
  - **essai 17, E5p90b_c14e_g1_d-0.1** (décalage −0,10 fixé, rien d'autre ne change) : seuil 0,30 ; dense 0,7795, plantain **0,8877**, jeunes 0,8926, MM 0,8571, btd_val 0,9873 ; **moyenne 0,8808** (graine 0 : 0,8811), **4 anciennes 0,8542** (graine 0 : 0,8544 ; limite 0,8539), erreur 0,128, `val_negatifs` 3 : **finaliste lui aussi**. La recette est stable à 0,0003 près ; mais la marge sur « 4 anciennes ≥ v5 » reste de quelques fausses détections du plantain (+0,0003).
  - Les cartes de c14j et c14e_g2 ont été interrompues 1 min pour cette mesure (2 fils au plus) puis relancées.
- 20:10 `c14-lot2` toujours **en file d'attente** Kaggle (QUEUED depuis 19 h 15). Cartes locales de c14j lentes (2 fils, machine chargée par les Juges) : `val_negatifs` en cours depuis 19 h 46.
- 20:14 **CC4b, c14j** (c13h avec réglage fin doux 1e-5 / 3e-5) [M] (ONNX local) :
  - **essai 16, c14j seul** : seuil 5.3 0,35 ; dense 0,7769, plantain 0,8851, jeunes 0,8988, **MM 0,8254**, btd_val 0,9878 ; moyenne 0,8748, 4 anciennes 0,8466, erreur 0,077, `val_negatifs` 6 : **pas finaliste** (MM sous 0,837 ; 4 anciennes sous 0,8539). **Le réglage fin plus doux ne remonte pas MM** (c13h : 0,8308) : l'idée « garder plus de v6f » ne suffit pas.
  - **essai 19, CC1@c14j (poids de CC1_v5h_50, c14j à la place de c13h)** : seuil 0,30 ; dense 0,7846, plantain 0,8854, jeunes 0,9106, MM 0,8489, btd_val 0,9909 ; moyenne **0,8841**, 4 anciennes **0,8574**, erreur 0,121, `val_negatifs` 7 : **finaliste** lui aussi. Comparé à CC1_v5h_50 (0,8886 ; 0,8630), le gain hors btd_val est plus petit (+0,0035 au lieu de +0,0091 sur le v5) et MM passe sous le v5 (−0,008). [O] Le mélange « v5 + réseau robuste » reste finaliste avec un réseau frère, mais la part du gain hors btd_val dépend du réseau : c'est une mesure de stabilité, pas un choix (c14j n'est pas proposé).
  - Chaîne de cartes interrompue 30 s pour ces deux mesures puis relancée (c14j à 11 cm, c14e_g2, puis 11 cm des graines c14e).
- 20:31 À 11 cm (information) [M] : c14j seul (0,35) 0,8529 ; CC1@c14j (0,30) **0,8564** (CC1_v5h_50 : 0,8569). La robustesse à 11 cm du mélange ne dépend pas du réseau frère choisi.
- 20:34 `c14-lot2` encore en file (1 h 19) alors que `m14-lot2`, envoyé après, a tourné : **renvoyé à l'identique** (version 2 du même carnet, même recette c14h_g1). Statut : QUEUED. Règle écrite maintenant : s'il n'a pas démarré à 21 h 45, l'essai 28-29 est abandonné (trop tard pour entraîner, calculer les cartes et mesurer avant 23 h 30).
- 20:39 **CC4a, graine 2** [M] : c14e_g2 seul (information) seuil 0,40, moyenne 0,8128, MM 0,5405, `val_negatifs` 0 ; **essai 18, E5p90b_c14e_g2_d-0.1** : seuil 0,30 ; dense 0,7795, plantain 0,8879, jeunes 0,8926, MM 0,8571, btd_val 0,9876 ; **moyenne 0,8809**, **4 anciennes 0,8543**, erreur 0,128, `val_negatifs` 3 : **finaliste**.
  - **Stabilité du finaliste E5p90b_c13e_d-0.1 sur 3 graines** (0, 1, 2) : moyenne 0,8811 / 0,8808 / 0,8809 (étendue 0,0003) ; 4 anciennes 0,8544 / 0,8542 / 0,8543 (toujours ≥ 0,8539, de 0,0003 à 0,0005) ; plantain 0,8883 / 0,8877 / 0,8879 ; btd_val 0,9878 / 0,9873 / 0,9876 ; `val_negatifs` 4 / 3 / 3. Les 3 graines passent la règle 5.3. La recette est stable ; la marge sur la condition « 4 anciennes » est petite mais du même signe pour les trois.
- 20:44 **Temps** (information) [M] (`scripts/c14_temps.py --fils 3 --n 30`, `temps.json`) : CC1_v5h_50 recalculé de bout en bout = **3,2 fois le v5** (dense 2,74 contre 0,85 s/tuile ; plantain 3,6 ; btd_val 3,2 ; sans bananier 3,1) ; points identiques au cache sur 120 / 120 tuiles. Machine partagée (ma chaîne de cartes à 2 fils tournait aussi) : seuls les rapports comptent.
- 20:44 `finalistes_piste2.md` écrit (version provisoire, en attente de c14h_g1). `c14-lot2` toujours en file.
- 20:50 À 11 cm (information) [M] : E5p90b_c14e_g1_d-0.1 0,7862 ; E5p90b_c14e_g2_d-0.1 0,7855 (graine 0 : 0,7850). Stable aussi au réglage dégradé.
- 21:00 **Ajout CC1-frères, écrit avant calcul** (en attendant `c14-lot2`, toujours en file) : pour savoir si le gain de CC1_v5h_50 tient au mélange « v5 + réseau robuste à la résolution » ou à c13h lui-même, le même mélange (poids 0,5 / 0,5) est mesuré avec les deux autres CE1 de C-entraîneur qui ont appris la dégradation : **essai 30, CC1@c13f** (ResNet-18, c13a + btd_train) et **essai 31, CC1@c13g** (ResNet-34, recette v6f + dégradation, depuis zéro). Information sur la stabilité de l'idée ; **ils ne remplacent pas CC1_v5h_50**, quel que soit leur chiffre. Cartes calculées à 3 fils (après 20 h 30).
- 21:29 **CC1-frères, essais 30 et 31** [M] (poids 0,5 / 0,5, seuil 5.3 = 0,30 pour les deux) :
  - **CC1@c13f** : dense 0,7823, plantain 0,8887, jeunes 0,9061, MM 0,8507, btd_val 0,9906 ; moyenne 0,8837, 4 anciennes 0,8570, erreur 0,102, `val_negatifs` 9 ; 11 cm 0,8608 : finaliste ;
  - **CC1@c13g** : dense 0,7836, plantain 0,8850, jeunes 0,9032, MM 0,8593, btd_val 0,9911 ; moyenne 0,8844, 4 anciennes 0,8578, erreur 0,114, `val_negatifs` 12 ; 11 cm 0,8602 : finaliste.
  - **Bilan des 4 mélanges « v5 + réseau robuste »** (c13h, c14j, c13f, c13g) : **tous finalistes** ; moyenne 0,8837 à 0,8886 ; 4 anciennes 0,8570 à 0,8630 (+0,003 à +0,009 sur le v5) ; 11 cm 0,856 à 0,861. [O] L'idée tient avec chacun des quatre réseaux ; **c13h est le plus favorable des quatre** sur les 4 anciennes : le gain typique hors btd_val est plutôt **+0,004** que +0,009. Le gain à 11 cm, lui, ne dépend pas du réseau. MM sous le v5 avec c14j et c13f (−0,008, −0,006), au-dessus avec c13h et c13g.
- 21:46 `c14-lot2` toujours en file : **essais 28 et 29 abandonnés** (règle de 20 h 34). Le carnet n'est pas supprimé (décision laissée au chef d'orchestre ; s'il tourne plus tard : environ 0,5 h de GPU). GPU consommé par C-piste2 : environ **0,55 h** (c14-lot1).
- 21:47 **`out/comptage/nuit_1311/piste2/finalistes_piste2.md` définitif.** Finalistes de réserve proposés : 1. `CC1_v5h_50` (famille C) ; 2. `CC3_a1_a35` (famille A) ; variante `CC3_e5c13e_a35` (famille C, à la place d'E5p90b_c13e_d-0.1). **Essais mesurés : 27** (1 à 11, 14 à 27, 30, 31 ; non faits : 12, 13, 28, 29).
