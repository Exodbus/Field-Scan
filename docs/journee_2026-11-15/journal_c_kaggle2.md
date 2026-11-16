# Journal de l'agent C-kaggle2 (15 novembre 2026, second tour Kaggle du comptage)

Cadre : `docs/journee_2026-11-15/avenant_tour2_kaggle.md` (repartir du **v5**, jamais de v6f ni de c13h ; contrôle de non-régression ReforesTree ajouté aux conditions 5.3), `docs/plan_journee_2026-11-15.md`, `docs/plan_nuit_2026-11-13.md` section 5.3. Kaggle : compte `affilecorentin`, **3 h de GPU au plus**, T4 × 2. Processeur local : 2 fils au plus. Écrit seulement dans `notebooks/c15b_*.py`, `out/comptage/jour_1511/kaggle2/`, `modeles/comptage_jour_1511/` et ce journal. Aucun commit ; aucun juge lu ni envoyé (segmento est, CG, `banano_dense`, `test_negatifs`, `banana_trees_kp`). `finalistes.md` avant 20 h 30.

Compteur d'essais : un essai = un réseau entraîné et mesuré sur le réglage par la règle 5.3.

- 16:04 Démarrage. Lu : CLAUDE.md, avenant du second tour, plan du jour, plan du 13/11 (5.3), journal C-kaggle (c15d), `out/controle_jour_1511/juge_comptage.md` (CG : CC1 22 et c15d 10 pieds détectés sur 290, contre 66 pour le v5), récapitulatif du jour, journaux C-entraîneur et C-piste2 du 13-14/11.
- 16:05 Copies sous mon nom, sans toucher aux originaux : `notebooks/c15b_mesure.py`, `c15b_cache.py`, `c15b_recuperer.py`, `c15b_pousser.py`, `c15b_lanceur_kaggle.py` (seuls les dossiers et le slug `c15b-…` changent), et `c15b_travail_centres.py` (copie de `c15_travail_centres.py` + deux options, voir plus bas).
- 16:06 **Contrôle du banc** [M] (`notebooks/c15b_mesure.py v5 --cm11`, `out/comptage/jour_1511/kaggle2/essais.json`, cartes du v5 lues dans les caches du banc) : v5 à 0,30 : dense 0,7795, plantain 0,8865, jeunes 0,8926, MM 0,8571, btd_val 0,4726, **moyenne 0,7777**, **4 anciennes 0,8539**, erreur 0,262, `val_negatifs` 16 ; **11 cm 0,6005**. Le v5 est retrouvé.
- 16:10 Options ajoutées dans `c15b_travail_centres.py` (sans effet si absentes) :
  - `distil_net` : le maître (v5) lit la **vue nette** de la même fenêtre (même découpe, même échelle, mêmes facteurs de couleur, mêmes symétries, sans dégradation ni JPEG). Sur une tuile dégradée, l'élève apprend donc à rendre la carte que le v5 donne à 5 cm, au lieu de la carte ratée du v5 sur l'image floue ;
  - `distil_rt` : multiplicateur du poids de distillation sur les tuiles ReforesTree (groupes `rt_*`).
  - Contrôle local [O] (scratchpad, `V6_ESSAI`, données `data/drone/comptage_v6_5cm`, 40 tirages) : sur les 23 tirages non dégradés, vue nette = entrée de l'élève à l'identique ; sur les 17 dégradés, les deux vues sont alignées (corrélation > 0,8) ; drapeau ReforesTree juste.

## Pourquoi ces recettes (écrit d'après les journaux, avant tout calcul du second tour)

- Les réglages fins du v5 avec dégradation de la nuit du 13/11 (c13b, c13c : `parts_v5` sans btd_train) gardaient la robustesse à 11 cm (0,68) mais perdaient **MM** (0,756 et 0,800) et laissaient btd_val bas, ce qui tirait le seuil à 0,25. Le réglage fin du v5 sur un tirage riche en btd (c13e) détruisait MM (0,587).
- c15d (départ v6f, distillation du v5 sur les seules tuiles nettes) passait le réglage mais **s'effondre sur CG** (10 pieds sur 290). L'avenant demande de partir du v5 et de garder son comportement en agroforesterie.
- D'où : départ **v5** (ResNet-18, ONNX converti, BN figées comme c13b/c13c), btd_train dans le tirage pour garder un seuil haut (comme c13f), dégradation 5-12 cm pour la robustesse, et **distillation du v5 sur toutes les tuiles**, dégradées et ReforesTree comprises, avec le v5 qui lit la vue nette.

## Recettes du lot `c15b-lot1` (écrites à 16 h 12, avant l'envoi)

Commun aux 4 : `reseau` resnet18, `init` = `centres_5cm_v5.onnx` (jeu `comptage-v6-maitres`), `bn_gele` vrai, `distillation` = [`centres_5cm_v5.onnx`], 10 époques, lot 16, AdamW 3e-5 / 1e-4 (OneCycle), échelle 0,6-1,6, dégradation p 0,5 de 5 à 12 cm, JPEG p 0,5 (qualité 60-95), EMA 0,999, graine 0, poids EMA de la dernière époque (aucun choix d'époque), `duree_max_h` 1,0 (garde-fou), mesure dans le carnet à 11 cm pour information.

| essai | nom | tirage | distillation | famille |
| --- | --- | --- | --- | --- |
| 1 | `c15b_a` | `parts_v5` + btd_train 15 % (`avec_espace`) | toutes tuiles, v5 sur vue nette (`distil_net`), lambda 10, ReforesTree × 1 | B |
| 2 | `c15b_b` | idem | idem, **ReforesTree × 3** (`distil_rt` 3) | B |
| 3 | `c15b_c` | `parts_v6a` (tirage de c15d) | **recette c15d avec le v5 comme départ et comme maître** : tuiles nettes seulement (`distil_propre`), lambda 10, maître sur l'entrée de l'élève | B |
| 4 | `c15b_d` | `parts_v5` + btd_train 15 % | toutes tuiles, vue nette, **lambda 30**, ReforesTree × 3 | B |

Kaggle : un seul carnet `c15b-lot1`, T4 × 2, 4 recettes en parallèle (2 par GPU). Entrées : `comptage-v6-5cm`, `comptage-v6-maitres`. Aucune image de juge (le travail retire `test_*` et `cg/` par `assert`, le script d'envoi refuse toute recette ou entrée qui cite un juge). **Règle d'arrêt** : s'il reste plus de 45 minutes en file d'attente, il est abandonné et noté ici. Pas de second lot, sauf si le premier finit avant 17 h 45 ; un second lot éventuel sera écrit ici avant son envoi.

## Règles de mesure et de finaliste (écrites à 16 h 12, avant tout entraînement)

**Mesure** : ONNX exporté par le carnet, récupéré (sorties de mon propre carnet, comme au premier tour) et mesuré en local (onnxruntime, 2 fils) par `notebooks/c15b_cache.py` puis `notebooks/c15b_mesure.py`, avec `scripts/v6_banc_commun.py`, `c13_banc_commun.py`, `c13_banc_candidats.py`, `v6_banc_candidats.py` importés sans modification. Les chiffres du carnet sont de l'information.

**Règle 5.3 telle quelle** (référence v5 au seuil 0,30) :
- seuil = meilleure moyenne des 5 F1 sur 0,10-0,60 (pas 0,05) sous `val_negatifs` < 1 % ;
- **finaliste ordinaire** : moyenne des 5 > 0,7877, 4 anciennes ≥ 0,8539, chaque jeu ≥ v5 (0,30) − 0,020, erreur de compte ≤ 0,262, `val_negatifs` < 1 % ;
- **finaliste « résolution »** : moyenne à 11 cm (lue au seuil choisi à 5 cm) ≥ 0,6305 (v5 dégradé 0,6005 + 0,030), moyenne des 5 à 5 cm ≥ 0,7727, et les trois autres conditions.

**Contrôle de non-régression ReforesTree** (avenant, ajouté aux conditions, sans les remplacer) : sur les tuiles `rt_*` de `data/drone/comptage_v5_5cm/` dont `partie` = `ensemble` = « train » et `facteur` = 1 (vérifié par `assert`, comme `scripts/rendu_preparer.py`), pics du v5 au seuil 0,30 contre pics du candidat à son seuil 5.3 (fenêtre 7, `bc.pics`) ; appariement un à un (hongrois) à 20 px au plus (1 m à 5 cm). **Le candidat doit retrouver au moins 95 % des pieds du v5.** Script `notebooks/c15b_controle_rt.py`, résultats `out/comptage/jour_1511/kaggle2/controle_rt.json`. Non-régression sur des données vues : ce n'est pas une mesure de performance.

**Ordre de mesure** : a, b, c, d (il ne change pas selon les chiffres des carnets). Un candidat dont la mesure n'est pas finie à 20 h 15 ne concourt pas.

**Finalistes** : tout candidat qui passe (ordinaire ou « résolution ») **et** le contrôle ReforesTree est écrit dans `out/comptage/jour_1511/kaggle2/finalistes.md`, classé par moyenne des 5 à 5 cm, avec sa famille (B), son tableau par jeu à 5 et 11 cm, son contrôle ReforesTree et son temps par rapport au v5. Aucun choix de seuil, d'époque ou de variante hors de cette règle. Si aucun ne passe : « aucun finaliste ».

**Temps** : comme `scripts/juge_1511_c_temps.py` (entrelacé tuile par tuile, 2 fils, 25 tuiles de `dense` et 25 de `val_negatifs`), information.

## Calculs
- 16:09 Envoi de `c15b-lot1` **refusé par Kaggle** : « Maximum batch GPU session count of 2 reached ». Les deux places sont prises par `m15-traits` (premier tour, en file depuis 14 h 13, abandonné par M-kaggle2 mais non supprimé : décision laissée à Corentin) et `m15b-traits` (M-kaggle2, RUNNING depuis 16 h 08). Je ne supprime aucun carnet qui n'est pas le mien. **Règle écrite maintenant** : nouvel essai d'envoi toutes les 3 minutes, à l'identique ; si l'envoi n'a pas réussi à **17 h 15**, le lot passe à 3 recettes (a, b, c ; d abandonnée) pour finir à temps ; s'il n'a pas réussi à **17 h 45**, plus d'entraînement : « aucun finaliste ». La règle des 45 minutes en file s'applique à partir de l'envoi accepté.
- 16:12 **Contrôle ReforesTree, témoins** (information, pas des essais) [M] (`notebooks/c15b_controle_rt.py`, `controle_rt.json`) : 121 tuiles `rt_*` (3 sites : Flora Pluas 40, Leonor Aspiazu 43, Nestor Macias 38), toutes « train », facteur 1, sans masque. v5 contre lui-même : 3 376 / 3 376 (100 %), le code apparie bien. **c15d (0,35) : 2 922 / 3 376 = 86,6 %** (86,9 / 88,3 / 85,6 % par site) : c15d **aurait échoué** à ce contrôle. Le contrôle sépare donc bien un réseau qui a perdu CG (10 pieds sur 290) d'un réseau qui garde le comportement du v5. [O] Rappel des mères annotées sur ces tuiles (information) : v5 0,908, c15d 0,897 : l'écart porte surtout sur des pieds que le v5 voit sans qu'ils soient annotés.
- 16:12 Message envoyé à la session principale (place GPU bloquée par `m15-traits`).
- 16:16 **`c15b-lot1` envoyé et accepté** (3e tentative ; `out/comptage/jour_1511/kaggle2/essayer_envoi.sh`, recettes exactes dans `out/comptage/jour_1511/kaggle2/recettes_lot1.json`, identiques au tableau de 16 h 12), 4 recettes, 4 places (2 par GPU), T4 × 2. Statut **RUNNING à 16 h 16** (pas de file). [O] `m15-traits` n'est plus accessible (supprimé par un autre que moi). GPU décompté à partir de 16 h 16.
- 16:20 Scripts prêts : `out/comptage/jour_1511/kaggle2/chaine_mesure.sh` (cartes 5 cm, `val_negatifs`, 11 cm, mesure 5.3, contrôle ReforesTree, dans l'ordre a, b, c, d) et `notebooks/c15b_temps.py` (essai à blanc sur le v5 seul : 0,26 s par tuile en dense, 0,12 s en `val_negatifs`, 2 fils).
- 16:25 **Rapport rendu à la session principale à sa demande, alors que `c15b-lot1` tourne encore** (RUNNING depuis 16 h 16). `finalistes.md` provisoire écrit : aucun finaliste à ce stade. GPU consommé jusqu'ici : environ 0,15 h (session en cours, environ 1 h attendue). Essais : 0 mesuré, 4 en entraînement. Rien n'est récupéré ni mesuré.
- 16:18 Reprise à la demande de la session principale : je fais moi-même les étapes 1 à 5 (attente de `c15b-lot1` par une boucle `until` en arrière-plan, récupération, mesure a, b, c, d, temps, `finalistes.md` définitif).
- 17:26 **`c15b-lot1` fini** (COMPLETE ; « TOUT EST FINI en 69 min », T4 × 2) : **environ 1,15 h de GPU** (durée de la session). Récupéré par `notebooks/c15b_recuperer.py c15b-lot1` (sorties de mon propre carnet) : ONNX, json et poids dans `modeles/comptage_jour_1511/` (`centres_5cm_c15b_{a,b,c,d}.*`, `poids_c15b_*.pt`), journaux dans `out/comptage/jour_1511/kaggle2/c15b-lot1/`. Écart ONNX / torch ≤ 5,5e-6. [O] Départ v5 « All keys matched », conversion ONNX → torch à 4,8e-6.
  - [O] **Garde-fou `duree_max_h` 1,0 atteint pour a, b et d** (vue nette = deux redimensionnements par tuile, 4 recettes sur 4 processeurs Kaggle : 7,8 min pour la 1re époque, environ 6,4 min ensuite) : ils se sont arrêtés proprement **après 9 époques sur 10** (taux du OneCycle presque à zéro, poids EMA de la 9e époque, aucun choix). c (sans vue nette) a fait ses 10 époques. Je le dis et je mesure tels quels, comme écrit.
  - Chiffres du carnet (torch sur GPU, **information** ; l'ONNX local fait foi), seuil 5.3 : a 0,30, moyenne 0,8705, MM 0,814, 11 cm 0,8464 ; b 0,30, 0,8718, MM 0,819, 11 cm 0,8497 ; c 0,35, 0,8721, MM 0,823, 11 cm 0,8497 ; d 0,35, 0,8753, MM 0,826, 11 cm 0,8507. MM sous la limite 0,837 dans les quatre carnets.
- 17:28 Chaîne de mesure locale lancée (`chaine_mesure.sh c15b_a c15b_b c15b_c c15b_d`, 2 fils, un calcul à la fois, ordre écrit avant ; journal `out/comptage/jour_1511/kaggle2/log_chaine.txt`).

## Lot 2 `c15b-lot2` (écrit à 17 h 31, avant son envoi ; le lot 1 a fini avant 17 h 45, comme le permet la règle de 16 h 12)

Choix de recettes d'après les chiffres **de carnet** du lot 1 (information, dit ici) : dans les quatre carnets, MM reste sous la limite (0,814 à 0,826 contre 0,837) et la plus forte distillation (d, lambda 30) est la plus proche du v5. Le lot 2 pousse donc la distillation plus loin, pour coller davantage au v5 hors dégradation. Ce sont des choix de recettes ; **les règles de mesure et de finaliste ne changent pas** (5.3 + contrôle ReforesTree ≥ 95 %, ordre de mesure après d : e, puis f).

Commun : comme `c15b_d` (départ et maître v5, BN figées, `parts_v5` + btd_train, vue nette, ReforesTree × 3, dégradation p 0,5 de 5 à 12 cm, JPEG p 0,5, échelle 0,6-1,6, EMA 0,999, graine 0), mais **8 époques** et `duree_max_h` 0,75, 2 recettes, une par GPU (pour finir avant 18 h 45).

| essai | nom | différence avec d | famille |
| --- | --- | --- | --- |
| 5 | `c15b_e` | lambda 100, taux 1e-5 / 3e-5 (réglage fin doux) | B |
| 6 | `c15b_f` | lambda 100, taux 3e-5 / 1e-4 | B |

Règle d'arrêt : en file plus de 45 min, abandonné et noté. Pas de troisième lot. GPU prévu : environ 0,7 h de plus (total attendu ≈ 1,9 h sur 3 h).
- 17:31 **`c15b-lot2` envoyé** (recettes exactes : `out/comptage/jour_1511/kaggle2/recettes_lot2.json`, 2 places, T4 × 2). Statut QUEUED à 17 h 31 : abandon s'il n'a pas démarré à 18 h 16.
- 17:58 **Essais 1 à 4 mesurés** [M] (ONNX local, 2 fils ; `essais.json`, `controle_rt.json`, `log_chaine.txt`). Limites : chaque jeu ≥ v5 − 0,020 (MM ≥ 0,8371), 4 anciennes ≥ 0,8539, contrôle ReforesTree ≥ 95 %.

| essai | nom | seuil | dense | plantain | jeunes | MM | btd_val | moyenne 5 | 4 anciennes | erreur | `val_neg` | 11 cm | ReforesTree (pieds du v5 retrouvés) | 5.3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| réf. | v5 | 0,30 | 0,7795 | 0,8865 | 0,8926 | 0,8571 | 0,4726 | 0,7777 | 0,8539 | 0,262 | 16 | 0,6005 | 100 % | — |
| 1 | `c15b_a` | 0,30 | 0,7771 | 0,8828 | 0,8971 | **0,8138** | 0,9871 | 0,8716 | 0,8427 | 0,148 | 19 | 0,8494 | **93,2 %** | non (MM −0,043) |
| 2 | `c15b_b` | 0,30 | 0,7777 | 0,8815 | 0,9008 | **0,8194** | 0,9870 | 0,8733 | 0,8449 | 0,144 | 20 | 0,8505 | **93,2 %** | non (MM −0,038) |
| 3 | `c15b_c` | 0,35 | 0,7732 | 0,8879 | 0,8917 | **0,8227** | 0,9891 | 0,8729 | 0,8439 | 0,075 | 11 | 0,8519 | **88,8 %** | non (MM −0,034) |
| 4 | `c15b_d` | 0,35 | 0,7769 | 0,8884 | 0,8992 | **0,8261** | 0,9892 | 0,8759 | 0,8476 | 0,065 | 11 | 0,8516 | **88,0 %** | non (MM −0,031) |

  - **Aucun des quatre n'est finaliste** : ni ordinaire (4 anciennes sous 0,8539), ni « résolution » (MM perd 0,031 à 0,043, plus que 0,020), et aucun ne passe le contrôle ReforesTree (88 à 93 %, limite 95 %). Tous gagnent nettement à 11 cm (0,849 à 0,852 contre 0,6005).
  - [O] La distillation remonte MM dans l'ordre attendu (a 0,814 → b, ReforesTree × 3, 0,819 → d, lambda 30, 0,826), mais pas assez. Sur ReforesTree, au seuil 0,30, a et b gardent 93 % des pieds du v5 ; au seuil 0,35 (c, d), seulement 88 % : la règle 5.3 monte le seuil, et le réseau perd les pics faibles du v5. Rappel des mères annotées sur ces tuiles (information) : a 0,913, b 0,909, contre 0,908 pour le v5 ; c 0,875, d 0,876.
  - [O] Chiffres des carnets retrouvés à 0,002 près.
- 17:59 **Temps** (information) [M] (`notebooks/c15b_temps.py`, `temps.json`, entrelacé, 2 fils, 25 tuiles de dense et 25 de `val_negatifs`) : les quatre coûtent **1,00 à 1,01 fois le v5** (dense 0,285-0,287 s par tuile contre 0,283 ; `val_negatifs` 0,138 contre 0,138), ce qu'on attend de la même architecture ResNet-18.
- 18:16 **`c15b-lot2` abandonné** (règle des 45 minutes) : toujours QUEUED de 17 h 31 à 18 h 16, jamais démarré, aucun GPU consommé. Essais 5 et 6 (`c15b_e`, `c15b_f`) **non faits**. Le carnet n'est pas supprimé (décision laissée à la session principale) ; s'il démarre plus tard, ses sorties ne seront pas utilisées (environ 0,7 h de GPU au plus).
- 18:18 **`finalistes.md` définitif : aucun finaliste.**
- **Bilan** : GPU environ **1,15 h** sur 3 h (`c15b-lot1` ; `c15b-lot2` jamais démarré). **4 essais** mesurés (1 à 4), 2 annoncés et non faits (5, 6) ; témoins du contrôle ReforesTree (v5, c15d), qui ne sont pas des essais. Aucun juge lu ni envoyé ; aucun commit ; aucun fichier existant modifié.
