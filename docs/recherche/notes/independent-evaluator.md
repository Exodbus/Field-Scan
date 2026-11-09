# Notes d'independent-evaluator

Rédacteur unique : independent-evaluator. Entrées datées, ajoutées à la suite.

## 7 novembre 2026 — Mise en place de l'évaluation dense (D-003)

### Interface de `scripts/math_evaluer.py` (fixée avant toute mesure)

- **Liste des images** : `out/comptage_math/evaluation/images_dense.csv`, produite par `math_evaluer.py --liste`. Une ligne par image préparée (`data/drone/comptage_v5_5cm/images/<image_path>`) : `image_path, groupe, role, cm_par_px, unite` (unité de bootstrap) et la région comptée (`disque_cx, disque_cy, disque_r`, `zx0, zx1, zy0, zy1`, en pixels de l'image préparée). Rôles écrits : `dev` (5 groupes denses), `annexe_segmento` (segmento_ouest, à part), `val_iter`, `controle_repro` (dji_0544, pp_100_metros). **`val_scellee` n'est jamais écrite dans ce fichier.**
- **Résolution** : les tuiles d'entraînement du v5 ont été préparées à une échelle tirée au hasard (0,75 à 1,4 fois l'échelle 5 cm) ; leur résolution réelle est `cm_par_px = 5 × facteur_nominal / facteur_tuile` (de 3,6 à 6,7 cm/px). `bv_b_val`, dji_0544 et pp_100_metros sont exactement à 5 cm/px. L'appariement se fait **en mètres** (pixels × cm_par_px / 100), rayon 1 m.
- **Détections** : CSV `image_path, x, y, score`, x et y en pixels de l'image préparée (origine en haut à gauche, x vers la droite). Une méthode qui travaille sur les photos natives convertit elle-même ; une image absente du CSV = zéro détection. Un score plus grand = plus sûr.
- **Région comptée** : intersection (a) du disque de 2 000 px natifs (banavista, dji_0544) et (b) de la **zone propre** de la tuile : les tuiles d'entraînement se recouvrent de 20 % ; chaque point de la photo n'est compté que dans la tuile dont il est le plus proche du centre (frontière au milieu du recouvrement). Références et détections hors région sont ignorées, puis l'appariement se fait dans la région (même règle que la validation v5 dans le disque).
- **Mères seules** : `definir_types_certains(True)` ; tout point non `mere` est traité comme incertain (une détection appariée à lui est ignorée).
- **Appariement** : `apparier()` importé de `scripts/evaluer_comptage.py`, non modifié ; la logique des incertains d'`evaluer_zone()` est reprise en tableaux numpy pour la vitesse ; l'égalité avec `evaluer_zone()` est vérifiée image par image (`--auto-test`).

### E-001 — Référence dense : v5 et baseline ExG mesurés avec le même code

Avant (7 novembre 2026, avant tout lancement) :
- Hypothèse : aucune (mesure de référence) ; responsable : independent-evaluator ; demandée par : chef d'orchestre (D-003).
- Données : développement dense (`bv_session_a`, `bv_b_train`, `lasuiza`, `vols_100_022x`, `corte`) ; annexe `segmento_ouest` ; validation `val_iter` (DJI_0904 à 0945) ; contrôle de reproductibilité dji_0544 et pp_100_metros. **Pas `val_scellee`.** Aucun groupe `test` ni `exclu`.
- Contrôle de reproductibilité (avant de croire le reste) : v5 au seuil 0,30, F1 attendus 0,893 (dji_0544) et 0,885 (pp_100_metros), protocole v5 section 9 ; **tolérance 0,002**. Si l'écart dépasse, aucun chiffre d'E-001 n'est publié avant explication.
- v5 : `modeles/centres_5cm_v5.onnx` via `fieldscan.drone.DetecteurCentres` (lecture seule), image ramenée à 5 cm/px (tuiles d'entraînement rééchantillonnées par `cm_par_px / 5`), maxima au-dessus de 0,05, puis coordonnées ramenées à l'image préparée. Seuil de référence : **0,30** (officiel). Le F1 du v5 sur le développement est mesuré sur **ses propres données d'entraînement** : il est rapporté pour information, il n'est pas comparable.
- Baseline ExG + maxima (`out/comptage_math/evaluation/baseline.py`, recodée d'après `scripts/baseline_comptage.py` sans le modifier) : ExG = 2g − r − b en couleurs normalisées, lissage gaussien normalisé (pixels noirs de remplissage exclus), maxima locaux dans une fenêtre carrée de côté `distance`, score = ExG lissé au pic. **Grille déclarée** : σ ∈ {0,35 ; 0,5 ; 0,75 ; 1,0 ; 1,25 ; 1,5} m × distance ∈ {1,0 ; 1,5 ; 2,0 ; 2,5} m (24 couples) ; seuil de score choisi par `math_evaluer.py` parmi les quantiles des scores du développement. Choix : couple et seuil qui maximisent le F1 cumulé du développement dense. Mesure ensuite sur `val_iter`, une fois, réglages figés. Si le meilleur σ ou la meilleure distance est au bord de la grille, c'est rapporté (pas d'extension après avoir vu `val_iter`).
- Niveaux nuls (HF-01), même code : (b) points uniformes dans la végétation (ExG > seuil d'Otsu de l'image) et (c) **demi-maille** : chaque mère de la région déplacée de a/2 dans une direction tirée au hasard, en restant dans la végétation et dans la région (a = distance médiane au plus proche voisin des mères du groupe, en mètres) ; autant de points que de mères ; graine 2026.
- Mesures rapportées : P, R, F1 (cumul), erreur de comptage relative, F1 au meilleur seuil du développement appliqué à `val_iter`, courbe rappel-budget k = N_réf × {0,5 ; 1 ; 1,5 ; 2 ; 3}, intervalles bootstrap à 95 % (par photo d'origine sur le développement — indicatif, photos recouvrantes ; par bloc de 7 photos sur `val_iter`), différence appariée baseline − v5 sur `val_iter`.
- Critère : aucun (référence). Le critère de victoire des variantes futures est écrit dans `docs/recherche/test_final.md`, section 2.
- Nombre de variantes déjà essayées sur `val_iter` : 0. Le v5 et la baseline ne comptent pas dans le plafond de 8 (ce sont les références).

**Amendement avant mesure (7 novembre 2026)** : pépinière retirée, lasuiza dédoublonné, bootstrap par photo d'origine, réglage sur `dev_reglage` (bv_session_a sans pépinière + bv_b_train), groupes de transfert rapportés sans servir au réglage. Détail dans `docs/recherche/test_final.md`, section 3. Une première passe de réglage de la baseline, sur l'ancien développement à 5 groupes, a été interrompue **sans être lue** et ses sorties ont été effacées. Les rôles d'`images_dense.csv` deviennent `dev_reglage`, `dev_transfert`, `dev_exclu` (pépinière, bordures, doublons), `annexe_segmento`, `val_iter` et `controle_repro`. Taux de double comptage ajouté au résumé (définition au § 3.3 b).

Après (7 novembre 2026) :
- Code : `scripts/math_evaluer.py` (SHA-256 `934585b1eae50751b6b961bc6cae46455a45d3dfe47547c69b490049b3a99260`), `out/comptage_math/evaluation/v5_detecter.py` (`ba76a523…`), `baseline.py` (`f58f03e2…`), `regler_baseline.py` (`3ebe0f6d…`). Aucun commit (D-003).
- **Vérifications.**
  - Égalité avec `evaluer_comptage.evaluer_zone` : 450 évaluations sur 450 (150 images, 3 seuils, 10 % de points rendus incertains). Commande : `math_evaluer.py --auto-test out/comptage_math/evaluation/v5/detections_val_iter_dev.csv`.
  - Reproductibilité du v5 à 0,30 : dji_0544, F1 **0,8926** (attendu 0,8926, écart 0) ; pp_100_metros, F1 **0,8830** (attendu 0,8846, écart 0,0016 < 0,002 ; 2 896 détectés et 2 633 réels, identiques à `out/fourchette_v5.json`). Sorties : `out/comptage_math/evaluation/E-001/controle_repro/`.
  - Zones propres des tuiles : grille reconstruite pour toutes les tuiles (0 anomalie) ; décalages cohérents avec les disques de banavista.
- **Résultats [M, E-001]** : mères seules, 1 m, F1 cumulé, IC à 95 % par bootstrap (photo d'origine sur le développement, bloc de 7 photos sur `val_iter`).

| Jeu | v5 (0,30) P / R / F1 [IC] | Baseline ExG (σ 0,35 m, distance 1,5 m, seuil 0,1317) P / R / F1 [IC] | Demi-maille F1 | Végétation uniforme F1 | Mères |
| --- | --- | --- | --- | --- | --- |
| `dev_reglage` | 0,866 / 0,787 / **0,824** [0,818 ; 0,830] | 0,478 / 0,659 / **0,554** [0,542 ; 0,565] | 0,103 | 0,335 | 18 120 |
| `dev_transfert` | 0,881 / 0,872 / **0,876** [0,870 ; 0,881] | 0,373 / 0,671 / **0,479** [0,445 ; 0,512] | 0,103 | 0,312 | 11 204 |
| `val_iter` (DJI_0904 à 0945) | 0,612 / 0,871 / **0,719** [0,703 ; 0,735] | 0,287 / 0,688 / **0,405** [0,368 ; 0,447] | 0,083 | 0,236 | 2 694 |

  - **Lecture du développement.** Le F1 du v5 y est mesuré sur ses propres données d'entraînement : il est optimiste et ne sert pas de comparaison. Sur les tuiles exclues (pépinière, doublons), le v5 obtient F1 0,882 (`dev_exclu`, pour information).
  - **Baseline contre v5 sur `val_iter`** : écart de −0,314, IC à 95 % de la différence appariée [−0,357 ; −0,266].
  - **Budget k = N_réf sur `val_iter`** : v5 F1 0,732 ; baseline 0,298. Sur `dev_reglage` : v5 0,836 ; baseline 0,478.
  - **Erreur de comptage relative** : v5 −9 % (`dev_reglage`) et **+42 %** (`val_iter`) ; baseline +38 % et +140 %.
  - **Double comptage** (§ 3.3 b) : v5 0,008 (`dev_reglage`) et 0,008 (`val_iter`) ; baseline 0,070 et 0,056 ; demi-maille 0,26 et 0,17.
  - **Choix de la baseline** (`out/comptage_math/evaluation/baseline/reglage_dev.csv`, `choix.json`). Le meilleur couple est σ = 0,35 m, distance 1,5 m, F1 0,554 sur `dev_reglage`. **σ est au bord bas de la grille** : c'est rapporté, et la grille n'est pas étendue (règle écrite avant).
  - **Niveau nul de demi-maille.** Il est bas (F1 0,08 à 0,10), car a/2 vaut 1,04 à 1,26 m, donc juste au-delà du rayon de 1 m (mailles : bv_b_train 2,24 m, bv_session_a 2,18, bv_b_val 2,52). Il mesure « dans le feuillage, mais pas au centre ». Le niveau « végétation uniforme » vaut 0,24 à 0,34.
- **Observation [O] à suivre.** Sur `val_iter`, la précision du v5 tombe à 0,61 et le comptage dépasse les références de 42 %, contre 0,85 à 0,88 et −9 % sur `bv_b_train` et `bv_session_a`. [H] Références incomplètes sur les lignes L3-L4, ou végétation non bananière (n_autres_arbres > 0 sur certaines photos). La comparaison reste appariée, mais la précision de toute méthode y est une borne basse. Je demande un contrôle de complétude de `val_iter` (références seules) à annotation-manager.
- **Commandes.**
  - `math_evaluer.py --liste`
  - `v5_detecter.py --roles controle_repro`, puis `--roles val_iter dev` (tuiles ramenées à 5 cm/px)
  - `math_evaluer.py --detections …/v5/detections_val_iter_dev.csv --nom v5 --seuil-fixe 0.30 --roles dev_reglage dev_transfert dev_exclu val_iter --out out/comptage_math/evaluation/E-001/v5`
  - `baseline.py --roles dev --grille` ; `regler_baseline.py` ; `baseline.py --roles val_iter --sigma 0.35 --distance 1.5`
  - `math_evaluer.py --detections …/baseline/detections_retenue_dev_val_iter.csv --nom baseline_exg --roles dev_reglage dev_transfert val_iter --comparer …/v5/detections_val_iter_dev.csv --nom-comparer v5 --seuil-comparer 0.30 --out …/E-001/baseline`
  - `math_evaluer.py --niveaux-nuls --roles dev_reglage dev_transfert val_iter`, puis évaluation de chaque fichier avec `--seuil-fixe 0`.
- **Non mesuré** : `val_scellee` (ni v5, ni baseline) ; `annexe_segmento` (détections v5 non lancées, faute de temps ; rôle prêt).
- **Conclusion** : la référence est posée. **Le chiffre à battre en dense sur `val_iter` est F1 0,719 (v5 à 0,30) ; au budget N_réf, il est de 0,732.** La baseline explicite (0,405) est loin derrière. Variantes consommées sur `val_iter` : 0 sur 8.

**Correctif (7 novembre 2026).** Les détections du v5 sur segmento_ouest ont été produites par la tâche lancée en arrière-plan : `out/comptage_math/evaluation/v5/detections_annexe_segmento.csv`. Elles ne sont pas encore évaluées. La mention « non lancées » ci-dessus est fausse.

**Réserve sur E-001 (7 novembre 2026).** Les références de `val_iter` sont incomplètes (conventions_comptage.md § 5 : environ 48 % des plants annotés). Le F1 du v5 sur `val_iter` (0,719) et celui de la baseline (0,405) ne valent pas comme critère. La baseline d'E-001 a été réglée sur un `dev_reglage` qui contenait `bv_b_train` : elle doit être réglée de nouveau sur `bv_session_a` seul si `bv_b_train` devient une validation.

## 7 novembre 2026 — C-002, question 3, et validation dense v2

- Règle de rotation amendée (test_final.md, section 4) : comparaison au nul végétation uniforme, au budget N_réf. Deux bornes : un écart absolu de 0,05 au plus, et au plus un quart de l'excès de la méthode sur ce nul. Pas d'effet rétroactif sur A′ (E-006).
- Projet « validation dense v2 » (test_final.md, section 5), avec trois options : 1a (`bv_b_train` coupé en T1 et T2, graine 2026 : `val_iter_v2` = 0800 à 0841, scellée = 0757 à 0799), 1b (recommandée : `bv_b_train` entier pour les cycles, `val_scellee` pour la confirmation, sous réserve de complétude) et 2 (6 photos conformes, déconseillée).
- Contrôle de complétude de `val_scellee` (test_final.md, section 6), règle écrite avant tout calcul. Aucune mesure faite.

### E-015 — Témoins T3, T5 et T6 (développement, bv_session_a sans pépinière)

Avant (7 novembre 2026) : critères dans `docs/recherche/test_final.md`, section 7, écrits avant toute mesure. Données : `dev_reglage`, groupe `bv_session_a` (359 tuiles, 64 photos), plus `dev_transfert` pour information. Aucune lecture de `bv_b_train` (assertion dans le script), de `bv_b_val` ni du test. Détections figées lues :
- vote : `out/comptage_math/convergence-engineer/E-008/detections/vote.csv` ;
- A′ : `out/comptage_math/leaf-mathematician/E-006/detections/A_luminance_s1.25_r1.0.csv` ;
- vote + d̃3 : `out/comptage_math/vegetation-color-engineer/E-013/detections_e013_choix.csv`.

Grille T3 : 90 couples. Bootstrap par blocs de 7 photos consécutives (décision) et par photo (information), 2 000 tirages, graine 2026. Script : `out/comptage_math/evaluation/e015_temoins.py`.

Après (7 novembre 2026) :
- Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/evaluation/e015_temoins.py` (SHA-256 `b7cb651b…`). Sorties dans `out/comptage_math/evaluation/E-015/` : `bilan_E-015.json`, `T3_grille_baseline.csv`, `T5_courbe_budget.csv`, détections de T3. Journal : `out/comptage_math/evaluation/E-015.log`.
- **Reproduction des chiffres connus** : vote 0,6368 (E-008 : 0,6368, IC par photo [0,6243 ; 0,649], identique au bilan d'E-008) ; A′ 0,5408 (E-006 : 0,541) ; vote + d̃3 0,6515 (E-013 : 0,652).
- **Unité du bootstrap** : l'IC du vote par photo est identique à celui d'E-008. Les intervalles publiés depuis E-006 sont donc bien **par photo d'origine** ; aucun recalcul n'est nécessaire à ce titre. Par blocs de 7 photos, ils s'élargissent d'environ 1,6 fois (vote [0,616 ; 0,656]).

[M, E-015], `bv_session_a` sans pépinière, 8 649 mères, chaque méthode à son seuil choisi sur ces mêmes données :

| Méthode | P | R | F1 [IC par blocs] | F1 à k = N_réf | Erreur de comptage | F1 hors pli (T6) | Optimisme |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Vote B′ (E-008) | 0,630 | 0,643 | **0,637** [0,616 ; 0,656] | 0,636 | +2,0 % | 0,632 | 0,005 |
| Baseline T3 (σ 0,35 m, distance 1,25 m) | 0,469 | 0,717 | 0,567 [0,537 ; 0,593] | 0,474 | +53 % | 0,567 | 0,000 |
| A′ (E-006) | 0,445 | 0,690 | 0,541 [0,526 ; 0,554] | 0,497 | +55 % | 0,538 | 0,003 |
| Vote + d̃3 (E-013) | 0,620 | 0,686 | 0,652 [0,622 ; 0,677] | 0,646 | +10,7 % | 0,647 | 0,004 |

- **T3 (bloquant) : PASSE.** Vote − baseline réglée = **+0,070**, IC par blocs [+0,037 ; +0,098] (par photo [+0,052 ; +0,087]). Le meilleur couple de la grille de 90 est σ 0,35 m et distance 1,25 m (pas au bord) ; le F1 de la baseline monte de 0,554 (E-001, réglée avec bv_b_train) à 0,567. Sur `dev_transfert`, au seuil figé, la baseline T3 fait 0,481, contre 0,546 pour le vote (E-008).
- **T5 (bloquant, vote contre T3) : PASSE.** À k = N_réf, vote − baseline = **+0,162**, IC par blocs [+0,146 ; +0,177]. La baseline a une erreur de comptage de +53 % à son seuil, contre +2 % pour le vote. Courbe rappel-budget : vote 0,39 / 0,64 / 0,77 / 0,81 aux multiples 0,5 / 1 / 1,5 / 2 ; baseline 0,23 / 0,47 / 0,71 / 0,72 ; le budget de 2 × N_réf n'est atteint par aucune méthode (toutes leurs détections sont en dessous).
- **E-013 à budget égal** : gain sur le vote à k = N_réf = **+0,0095**, IC par blocs [+0,0009 ; +0,0177]. Il exclut 0, de justesse.
- **T6 : (i) PASSE.** Hors pli, le vote fait 0,632 et la baseline 0,567. **(ii)** : l'optimisme du seuil sur le vote est de 0,005 < 0,02, donc pas de décote. Pour vote + d̃3 : 0,647 hors pli, soit un gain sur le vote de +0,016 qui survit au re-choix du seuil. Limite : seuls les seuils ont été re-choisis par pli, pas r_max, p, R_nms ni w.
- **Conséquences** :
  - le vote bat une baseline réglée honnêtement sur les mêmes images, à son seuil comme à budget égal, avec des blocs de photos ;
  - pour vote + d̃3, deux des trois conditions de D-007 lui sont favorables (T5, T6). T1, mesuré par vegetation-color-engineer, reste à faire ;
  - T9 reste bloquant pour l'envoi (non mesuré ici).

## 7 novembre 2026 — Préparation de la mesure unique sur `val_scellee` (D-012, E-020)

- Règles, liste des 40 photos conformes (6 blocs), méthodes figées, empreintes, critère et prédictions : `docs/recherche/test_final.md` § 8, écrit avant toute détection sur `val_scellee`.
- Script de mesure : `out/comptage_math/evaluation/e020_val_scellee.py` (SHA-256 `05536ad3…`). Mode `--mesure E-020` : verrou, contrôle des empreintes, détections des trois méthodes sur les 40 photos, `math_evaluer.evaluer` sur une liste restreinte.
- Essai à blanc sur 2 tuiles de `bv_session_a` (`E-020_essai/bilan_essai.json`) : détections du vote, du v5 et de la baseline identiques aux fichiers figés d'E-010, E-001 et E-015. Rien de `val_scellee` n'a été lu.
- Reste : commit des règles (accord de Corentin), puis la mesure, une seule fois.

## 7 novembre 2026 — D-013 : cibles scellées (cibles B) du test de prédiction du simulateur v2

Critères : note de scientific-challenger, section D-013, § 3. Partage : `out/comptage_math/image-analyst/D-013/partage.csv` (CAL = DJI_0543–0620, VAL-S = DJI_0628–0682, 32 photos, 176 tuiles, aucune photo écartée par le tampon). Aucune image hors bv_session_a lue (assertion). Aucune méthode relancée : détections figées lues (vote B′ `E-010/detections/vote_e010.csv`, baseline T3 `E-015/T3_detections_baseline_bv_session_a.csv`, vote ExG `E-016/T2_vote_exg.csv`, A′ et A-iso `E-006/detections/`) ; niveaux nuls figés d'E-001 (`evaluation/niveaux_nuls/`, graine 2026).

### Correspondance des cinq chiffres publics (§ 3.1)

[M, contrôle D-013] Les cinq cibles A (0,637 ; 0,567 ; 0,563 ; 0,541 ; 0,423) sont des **F1 au seuil figé** (seuil choisi sur bv_session_a entier par l'expérience d'origine), **pas au budget k = N_réf**. Reproduits à 0,0001 près sur bv_session_a entier (64 photos, 8 649 mères), même code. Au budget k = N_réf, sur les mêmes 64 photos : vote B′ 0,636 ; T3 0,474 ; vote ExG 0,549 ; A′ 0,497 ; A-iso 0,380 (nuls : demi-maille 0,109, végétation uniforme 0,331). Conséquence pour P1 à P6 : la métrique de décision étant le budget, les cibles A au seuil ne sont pas directement comparables au simulateur ; l'ordre P4 tient aux deux métriques, mais l'écart B′ − T3 (P6) passe de 0,070 au seuil à 0,162 au budget. À consigner dans `docs/experiment-log.md` par le chef d'orchestre (je n'y écris pas).
Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/evaluation/D-013/cibles_d013.py --controle` → `out/comptage_math/evaluation/D-013/controle_bv_session_a_entier.json`.

### Scellé (valeurs non écrites ici)

| Fichier | SHA-256 |
| --- | --- |
| `out/comptage_math/evaluation/D-013/cibles_VAL-S.json` | `6351313db6457a081727576d86b0e22778b8508fbc3599931d55135b826954fe` |
| `out/comptage_math/evaluation/D-013/cibles_cachees_VAL-S.json` | `e97be16015e12f2748e9adf31fdce468afb8235c230e53386c3bf17befbcbede` |
| script `cibles_d013.py` | `7a585beee3e300340e49ce2c367c9d17a26942bb2230f74faef29995ebb8f68f` |

Date : 7 novembre 2026. Commandes : `cibles_d013.py --cibles`, puis `--cachees`.

**Grandeurs de `cibles_VAL-S.json`** (VAL-S seul, mères seules, 1 m, `scripts/math_evaluer.py` importé sans modification) :
- pour chacune des 5 méthodes : F1, P, R, VP/FP/FN au **budget k = N_réf** (décision), avec IC à 95 % par bootstrap par photo ; F1, P, R, erreur de comptage au **seuil figé** (rapporté) ; empreinte du fichier de détections ;
- rappel de B′ par **tercile de taille de couronne** (T1 petites à T3 grandes), au budget et au seuil figé, avec les bornes des terciles. Règle : R5 de plant-geometry (`taille_m` de `dev_dense.csv`, boîtes rognées exclues), terciles sur les mères non rognées de VAL-S ;
- niveaux nuls au budget : **demi-maille** et **végétation uniforme** (E-001), plus, en complément non demandé par le § 3.2, l'image tournée d'E-010. Les deux nuls d'E-001 ont moins de points que N_réf dans la région : leur « budget » prend tous les points (`budget_atteint` = faux), comme dans E-010. Note : le § 3.2 cite « orientations mélangées, demi-maille » ; la demande du chef d'orchestre cite « demi-maille, végétation uniforme ». Les deux nuls d'E-001 sont scellés ; l'image tournée est le seul nul « d'orientation » disponible sans relancer B′.

**Grandeurs de `cibles_cachees_VAL-S.json`** (réservées, F6 à F8) :
- F6 : distribution de |∇Y| (dérivée de gaussienne 4 cm, Y/m) : histogramme fin, histogramme log, quantiles, moyenne, écart-type, échantillon trié ; énergie log10 du tenseur ;
- F7 : histogramme et quantiles de la cohérence du tenseur à l'échelle de B′ (σg 4 cm, σt 10 cm), toutes régions et végétation ;
- F8 : indice d'alignement radial d'E-003 (T_feuille, anneau 0,4–1,5 m, masque de végétation) autour des mères : moyenne par pixel, moyenne pondérée, distribution par tuile, histogramme angulaire ; contrôles demi-maille et orientations mélangées.
- Concordance avec `image-analyst/D-013/stats_validation_cachees.json` : histogrammes de cohérence et d'énergie identiques (écart max 5e-7), moyenne de |∇Y| identique.

**Garde.** Ces deux fichiers ne sont ouverts qu'au test de prédiction, par moi seul. Ils sont lisibles sur disque : le chef d'orchestre ne doit pas donner `out/comptage_math/evaluation/D-013/` à leaf-mathematician.
