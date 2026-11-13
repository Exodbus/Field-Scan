# Notes de plant-geometry

## E-009 — A′ + répulsion géométrique entre mères (processus de Strauss), pré-enregistrement

Écrit le 7 novembre 2026, **avant tout calcul de F1** avec la sélection géométrique. Rien n'a été mesuré sur A′ + géométrie au moment d'écrire. Données ouvertes : aucune image ; seuls ont été lus les fichiers déjà publiés (E-006, E-007, `stats_geometrie_dev.csv` de scientific-challenger). `bv_b_train`, `bv_b_val` (`val_iter`, `val_scellee`), les groupes test ou exclus et `cg/` ne sont pas utilisés (assertions dans le script).

### 1. Question

Un a priori de plantation dense peut-il trancher entre « centre » et « milieu entre deux voisins » parmi les candidats de A′, et de combien améliore-t-il le F1 sur `bv_session_a` sans pépinière ?

### 2. Piste retenue : (b), processus ponctuel à répulsion, et pourquoi pas (a) ni (c)

- [M] E-006 : à rayon de suppression 1,2 m au lieu de 1,0 m, le F1 passe de 0,541 à 0,542. Une suppression gloutonne plus large ne gagne rien. Le défaut d'une suppression gloutonne est connu : si le milieu a un score plus haut que chacun des deux centres, elle garde le milieu et supprime les deux centres. Un critère **global** (somme des scores des points gardés) préfère deux centres moyens à un milieu un peu plus fort. C'est ce que fait (b) et que ni la suppression gloutonne ni (a) ne font.
- (a) maille locale adaptative : la maille de bv_session_a est déjà serrée et peu variable (ppv médian 2,44 m [M, scientific-challenger]) ; un rayon de 0,6 × maille ≈ 1,3–1,5 m retombe dans la grille de (b). Non retenue pour rester sous 3 paramètres.
- (c) rangées : non retenue. Domaine de validité trop étroit (inutilisable en agroforesterie, profil § Limites) et dérive des rangs non mesurée.

### 3. Formulation

Candidats : les détections d'A′ figées en E-006 (`out/comptage_math/leaf-mathematician/E-006/detections/A_luminance_s1.25_r1.0.csv` : maxima locaux de z ≥ 0,5, suppression 1,0 m, luminance, s = 1,25). La carte de score n'est pas modifiée.

Par tuile, on choisit le sous-ensemble S des candidats qui maximise l'énergie d'un processus de Strauss (mode a posteriori) :

E(S) = Σ_{i∈S} (z_i − t) − γ · #{ paires {i, j} ⊂ S : d_ij < r }.

- γ = ∞ : processus de Gibbs à cœur dur (aucune paire gardée à moins de r) ; c'est un ensemble indépendant de poids maximal.
- Optimisation **exacte** (`comptage_math/geometrie.py`, `selection_strauss`) : programme linéaire en nombres entiers résolu par HiGHS (`scipy.optimize.milp`), variables x_i ∈ {0, 1} et, pour γ fini, y_ij ≥ x_i + x_j − 1 par paire à moins de r ; pour γ = ∞, x_i + x_j ≤ 1.
- *Correction avant tout F1 (même jour)* : la première version utilisait une recherche locale (glouton puis mouvements « 1 → k » et « k → 1 »). La vérification synthétique l'a montrée bloquée sur une chaîne centre–milieu–centre… dont chaque milieu est plus fort qu'un centre mais dont l'ensemble des centres est meilleur (6 × 1,0 > 5 × 1,1). Elle est gardée (`selection_strauss_locale`) mais n'est pas utilisée. Sur 250 points aléatoires, l'optimum exact prend 0,03 à 0,17 s.
- La sélection voit tous les candidats de la tuile, y compris hors de la région comptée (contexte des voisins) ; l'évaluation ne garde ensuite que la région comptée, comme `me.lire_detections`.
- Les points gardés conservent leur z ; le seuil final est choisi par la règle de l'évaluateur (200 quantiles, meilleur F1 cumulé sur `bv_session_a`).

**Lecture en « centre contre milieu ».** L'intensité conditionnelle de Papangelou du processus en un point p, sachant les détections gardées, vaut

log λ(p | S) = z(p) − t − γ · n_r(p),

où n_r(p) est le nombre de détections gardées à moins de r de p, **sans compter** la détection gardée la plus proche de p si elle est à moins de 1,0 m (c'est « le point lui-même », rayon d'appariement de l'évaluateur). Un centre bien entouré (voisins à 2,2–2,9 m > r) n'est pas pénalisé ; un milieu dont les deux centres sont détectés l'est de 2γ (ou d'un γ si l'un des deux est à moins de 1 m). Pour γ = ∞, la pénalité est remplacée par 10⁶ dans ce contrôle seulement.

### 4. Paramètres (3) et leur origine

| Paramètre | Valeurs | Origine |
| --- | --- | --- |
| r, rayon d'interaction | 1,3 ; 1,5 ; 1,7 m | borne basse : demi-distance au ppv médian (2,44 / 2 = 1,22 m, bv_session_a) ; borne haute : r < 2 m, puisque 29 % des mères de banavista ont un voisin à moins de 2 m et 1 % à moins de 1 m [M, `stats_geometrie_dev.csv`] |
| γ, pénalité par paire (unités de z) | 0,5 ; 1,5 ; ∞ | réglé sur bv_session_a ; ∞ = cœur dur |
| t, décalage de poids | 0,5 ; 0,8 ; 1,1 | réglé sur bv_session_a ; 1,1 ≈ seuil retenu d'A′ en E-006 (1,0952), 0,5 = plancher des candidats |

Soit 27 configurations. Fixé, non réglé : tout A′ (E-006), le rayon « soi » de 1,0 m du contrôle, la sélection par tuile.

**Sensibilité à une erreur d'échelle de ±20 %.** r est en mètres : une erreur d'échelle de +20 % fait agir r = 1,5 m comme 1,25 m réel (sous la demi-maille, le milieu n'est plus en conflit avec les deux centres) ; −20 % le fait agir comme 1,8 m (plus de vraies paires < 2 m supprimées). La grille 1,3–1,7 couvre à peu près ±13 % autour de 1,5 m.

**Domaine de validité.** Plantation dense ou industrielle, mères seules (la répulsion supprimerait les rejets, à 0,5–1,5 m de la mère). En agroforesterie, la contrainte est inoffensive tant que r reste sous la distance minimale entre mères (pas de rangées supposées) ; elle n'y a pas été mesurée.

### 5. Règle de sélection

- Meilleur **F1 cumulé sur `bv_session_a` sans pépinière** (rôle `dev_reglage`, groupe `bv_session_a`, filtré par `data/comptage_math/references/dev_dense_images.csv`), mères seules, appariement à 1 m, seuil par la règle de l'évaluateur (200 quantiles, meilleur F1), calculé avec `comptes` et `prf` de `scripts/math_evaluer.py`.
- Égalités à 0,005 près : plus petit r, puis plus petit γ, puis t le plus proche de 1,1.
- Contrôle de non-régression, hors grille : γ = 0, t = 0,5 doit redonner le F1 d'A′ (0,541).
- `dev_transfert` : évalué au seuil figé par `scripts/math_evaluer.py --seuil-fixe`, rapporté sans choix.

### 6. Contrôles rapportés (même protocole qu'E-006 et E-007)

- F1 de A′ + géométrie et de A′ seul, sur `bv_session_a` et `dev_transfert`.
- Centres contre milieux (`test_final.md` § 3.3) sur `bv_session_a` et `vols_100_022x` : (i) z brut d'A′ (inchangé, rappel) ; (ii) log-intensité conditionnelle ci-dessus. Passe si la médiane aux centres dépasse le 75e centile aux milieux, sur les deux groupes.
- Double comptage (`double_comptage` de l'évaluateur, au seuil retenu).
- Rotation, règle de l'amendement 2 (`test_final.md` § 4.3), au budget N_réf : la sélection géométrique est appliquée aux détections d'A′ calculées sur image tournée (`E-006/rotation_A_luminance_s1.25_r1.0.csv`).
- Temps par hectare : A′ (13,5 s/ha sur un cœur, E-006) + sélection mesurée.

### 7. Prédictions chiffrées, écrites avant

- **P-G1** : le gain de F1 sur `bv_session_a` est positif mais faible : 0,541 < F1 < 0,571. Raison : la suppression à 1,2 m n'a rien gagné en E-006, et le double comptage d'A′ n'est que de 0,068, donc les milieux exacts ne pèsent qu'une petite part des faux positifs.
- **P-G2** : la configuration retenue a γ fini ou infini avec r ≤ 1,5 m (une répulsion plus large coûte plus de vraies paires < 2 m qu'elle ne retire de faux positifs).
- **P-G3** : la précision monte (> 0,445) et le rappel baisse d'au plus 0,03 (≥ 0,66).
- **P-G4** : le contrôle centres contre milieux sur l'intensité conditionnelle **passe** sur `bv_session_a` et sur `vols_100_022x` ; sur z brut, il échoue toujours sur vols (inchangé : 0,561 < 0,732).
- **P-G5** : double comptage < 0,068.
- **P-G6** : règle de rotation : passe (excès sous rotation ≤ 0,05).
- **P-G7** : `dev_transfert` au seuil figé : F1 dans [0,345 ; 0,385].
- **P-G8** : le coût de la sélection est < 1 s/ha sur un cœur, négligeable devant A′.
- **Réfutation de l'a priori** : si la configuration retenue fait moins de 0,546 (+0,005), la répulsion n'apporte pas d'information exploitable au-delà de la suppression des non-maxima d'A′, et le défaut « centre contre milieu » n'est pas dans le choix des candidats mais dans la carte elle-même.

### 8. Protocole

Script : `out/comptage_math/plant-geometry/e009_strauss.py` ; sorties dans `out/comptage_math/plant-geometry/E-009/`.

## E-009b — même sélection de Strauss appliquée aux candidats du vote B′ (E-008), pré-enregistrement

Écrit le 7 novembre 2026 à la demande du chef d'orchestre (D-006 : le vote devient la candidate principale), **après la fin du calcul d'E-009 mais avant d'en lire le moindre résultat**, et avant tout calcul sur le vote. Lu d'E-008 avant d'écrire : la configuration retenue (r_max 1,6 m, p 1, suppression 1,0 m, seuil z 2,238, F1 0,637, précision 0,630, rappel 0,643), les contrôles centres/milieux (passent), le temps (3,77 s/ha sur un cœur) et la distribution des scores de `vote.csv` (médiane 2,21, quartiles 1,69 et 2,91, plancher 0,5). Le pré-enregistrement d'E-009 (ci-dessus) n'est pas modifié.

- **Candidats** : `out/comptage_math/convergence-engineer/E-008/detections/vote.csv` (maxima locaux de la carte z du vote, suppression 1,0 m, z ≥ 0,5). Carte z, pour les contrôles : `comptage_math/votes.py`, `carte_votes_image(rgb, res, r_max=1.6, p=1.0)["z"]`, et `detecter` d'`out/comptage_math/convergence-engineer/e008_votes.py` (non modifiés, importés).
- **Formulation** : identique à E-009 (§ 3), mode exact.
- **Paramètres (3)** : r ∈ {1,3 ; 1,5 ; 1,7} m (même origine qu'E-009). γ et t sont en unités de z ; l'échelle du score du vote diffère de celle d'A′ (seuil de fonctionnement 2,24 contre 1,10, soit environ × 2). Grilles mises à cette échelle : **γ ∈ {1,0 ; 3,0 ; ∞}**, **t ∈ {0,5 ; 1,4 ; 2,2}** (plancher, intermédiaire, ≈ seuil du vote). 27 configurations.
- **Règle de sélection** : celle d'E-009 (§ 5) : F1 cumulé sur `bv_session_a` sans pépinière, seuil par la règle de l'évaluateur ; égalités à 0,005 : plus petit r, plus petit γ, t le plus proche de 2,2. Non-régression : γ = 0, t = 0,5 doit redonner 0,637.
- **Contrôles** : ceux d'E-009 (§ 6) : F1 vote + géométrie et vote seul sur `bv_session_a` et `dev_transfert` (seuil figé, sans choix) ; différence appariée (bootstrap par unité, 2 000, graine 2026) ; centres contre milieux sur z brut du vote et sur la log-intensité conditionnelle, sur `bv_session_a` et vols ; double comptage ; rotation (amendement 2), la carte du vote étant recalculée sur image tournée de 90° (tuiles carrées, coordonnées lues sans rotation inverse, comme E-007) ; temps (vote 3,77 s/ha + sélection).
- **Prédictions** :
  - **P-Gb1** : gain faible : 0,637 < F1 < 0,662 sur `bv_session_a`. Raison : le vote passe déjà le contrôle centres/milieux, il reste peu de milieux à retirer.
  - **P-Gb2** : r retenu ≤ 1,5 m.
  - **P-Gb3** : rappel ≥ 0,62 (baisse ≤ 0,02).
  - **P-Gb4** : centres contre milieux passe sur les deux groupes, sur z brut (déjà en E-008) et sur la log-intensité.
  - **P-Gb5** : double comptage du vote + géométrie ≤ celui du vote seul.
  - **P-Gb6** : règle de rotation passe.
  - **P-Gb7** : `dev_transfert` au seuil figé : F1 dans [0,536 ; 0,566] (vote seul 0,546).
  - **Réfutation** : F1 < 0,642 (+0,005) : l'a priori de répulsion n'apporte rien au vote.
- Script : `out/comptage_math/plant-geometry/e009b_strauss_vote.py` ; sorties `out/comptage_math/plant-geometry/E-009b/`.

## Résultats d'E-009 [M, développement seulement ; aucune image de `bv_b_train`, `bv_b_val`, test, exclus ni `cg/`]

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/plant-geometry/e009_strauss.py` (299 s, 8 cœurs). Bilan : `out/comptage_math/plant-geometry/E-009/bilan_E-009.json` ; grille : `E-009/grille_bv_session_a.csv` ; journal : `e009_journal.txt`. Empreintes SHA-256 : script `d4cd9fb5…`, `geometrie.py` `62e00ea8…`.

- 359 tuiles de `bv_session_a` sans pépinière, 985 de `dev_transfert`.
- **A′ seul, même protocole** : F1 0,5408 (P 0,445, R 0,690). Non-régression γ = 0 : identique.
- **Grille (27 configurations)** : F1 de 0,535 à **0,5432** (r 1,3, γ ∞, t 0,8). Toute la grille tient dans ±0,006 d'A′. La précision monte (jusqu'à 0,479) et le rappel baisse d'autant (jusqu'à 0,608) : la répulsion échange des vrais positifs contre des faux positifs à taux à peu près égal.
- **Configuration retenue** (règle § 5 : égalité à 0,005 → plus petit r, plus petit γ, t le plus proche de 1,1) : **r 1,3 m, γ 0,5, t 1,1** ; F1 **0,5412** (P 0,449, R 0,681), seuil z 1,153. Différence appariée avec A′ : +0,0004, IC 95 % [−0,0009 ; +0,0018].
- **dev_transfert** (seuil figé) : F1 0,356 [0,327 ; 0,383] ; corte 0,497 ; lasuiza 0,298 ; vols 0,424 ; double comptage 0,071.
- **Double comptage** (`bv_session_a`) : 0,066 (171 / 2 586) contre 0,068 pour A′.
- **Centres contre milieux** :

  | Groupe | z brut : médiane centres / p75 milieux | log-intensité : médiane centres / p75 milieux | milieux pénalisés | centres pénalisés |
  | --- | --- | --- | --- | --- |
  | `bv_session_a` | 0,742 > 0,723 (passe) | −0,464 > −0,588 (passe) | 44 % | 21 % |
  | `vols_100_022x` | 0,561 < 0,732 (échoue) | −0,648 < −0,569 (échoue) | 41 % | 34 % |

- **Rotation (amendement 2)** : F1_orig 0,497, F1_rot 0,291, F1_veg 0,331 ; excès −0,040 : passe (identique à A′ : avec γ = 0,5 et r = 1,3, les points retirés sont sous le budget N_réf).
- **Temps** : sélection 0,04 à 0,30 s/ha sur un cœur ; A′ 13,5 s/ha ; total ≈ 13,8 s/ha sur un cœur, 1,7 s/ha sur 8.

**Prédictions** : P-G1 (0,541 < F1 < 0,571) : réfutée de justesse par le bas (0,5412, +0,0004, dans le bruit). P-G2 (r ≤ 1,5) : confirmée (1,3). P-G3 (précision > 0,445 et rappel ≥ 0,66) : confirmée (0,449 ; 0,681). P-G4 : confirmée sur z brut (échec vols inchangé), **réfutée** sur la log-intensité (échoue sur vols). P-G5 (< 0,068) : confirmée (0,066). P-G6 : confirmée. P-G7 ([0,345 ; 0,385]) : confirmée (0,356). P-G8 (< 1 s/ha) : confirmée.

**Clause de réfutation déclenchée** (F1 < 0,546) : la répulsion entre mères n'apporte rien à A′. Lecture : sur vols, 34 % des centres de référence sont eux-mêmes pénalisés, c'est-à-dire qu'une détection gardée se trouve entre 1,0 et 1,3 m d'eux ; les détections d'A′ sont trop décalées des vrais centres pour qu'un a priori de distance tranche entre centre et milieu. Le défaut est dans la carte (localisation), pas dans le choix des candidats.

## Résultats d'E-009b [M, développement seulement ; aucune image de `bv_b_train`, `bv_b_val`, test, exclus ni `cg/`]

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/plant-geometry/e009b_strauss_vote.py` (418 s, 8 cœurs). Bilan : `out/comptage_math/plant-geometry/E-009b/bilan_E-009b.json` ; grille, détections, rotation et transfert dans `E-009b/` ; journal `e009b_journal.txt`. Empreinte du script `c3c92740…`.

- **Vote seul, même protocole** : F1 0,6368 (P 0,630, R 0,643), identique à E-008. Non-régression γ = 0 : identique.
- **Grille** : F1 de 0,6225 à **0,6368** (r 1,5, γ 1, t 0,5 : égal au vote seul). Aucune configuration ne dépasse le vote. Plus r et γ augmentent, plus le F1 baisse (r 1,7, cœur dur : 0,623, rappel 0,608).
- **Retenue** (r 1,3, γ 1,0, t 2,2) : F1 **0,6364** ; différence appariée avec le vote −0,0003, IC 95 % [−0,0013 ; +0,0007].
- **dev_transfert** (seuil figé) : 0,545 [0,519 ; 0,569] contre 0,546 pour le vote ; corte 0,666 / 0,667 ; lasuiza 0,529 / 0,530 ; vols 0,549 / 0,548.
- **Double comptage** : 0,050 contre 0,051 (`bv_session_a`) ; 0,041 contre 0,042 (transfert).
- **Centres contre milieux** : passe sur z brut (bv 1,207 > 0,717 ; vols 1,410 > 0,362) et sur la log-intensité (bv −1,03 > −1,67 ; vols −0,81 > −2,04). Centres pénalisés : 8 % (bv), 16 % (vols), contre 21 % et 34 % avec A′.
- **Rotation (amendement 2)**, carte du vote recalculée sur image tournée : F1_orig 0,636, F1_rot 0,293, F1_veg 0,331, excès −0,038 : passe (vote seul : −0,039, passe).
- **Temps** : sélection 0,01–0,02 s/ha sur un cœur, négligeable devant le vote (3,77 s/ha).

**Prédictions** : P-Gb1 (0,637 < F1 < 0,662) : réfutée (0,636). P-Gb2 (r ≤ 1,5) : confirmée. P-Gb3 (rappel ≥ 0,62) : confirmée (0,641). P-Gb4 : confirmée. P-Gb5 : confirmée (0,050 ≤ 0,051). P-Gb6 : confirmée. P-Gb7 ([0,536 ; 0,566]) : confirmée (0,545). **Clause de réfutation déclenchée** (F1 < 0,642) : l'a priori de répulsion n'améliore pas le vote.

**Lecture.** Le vote place déjà ses maxima aux centres (le contrôle centres/milieux passe avant toute géométrie) et sa suppression à 1,0 m laisse peu de paires de détections entre 1,0 et 1,7 m qui soient des milieux : ce qu'une répulsion retire au-delà, ce sont surtout de vraies paires de mères proches (29 % des mères à moins de 2 m). Pour un maximum local d'une carte déjà bien localisée, la contrainte de distance minimale est redondante avec la suppression des non-maxima. Contrainte de distance minimale entre mères : **valide** sur les références (1 % < 1 m), mais **sans valeur ajoutée mesurable** pour A′ comme pour le vote. Gain possible restant : les faux négatifs (rappel 0,64), qu'une répulsion ne peut pas créer.

## D-013 — Statistiques géométriques réelles pour le simulateur v2 (7 novembre 2026)

Mesures descriptives sur les **références** seules : aucune détection, aucun score.

- **Données** : `bv_session_a` sans pépinière (règle v2, `conventions_comptage.md` § 1.4), soit 64 photos et 359 tuiles. Références `dev_dense.csv` ; images `comptage_v5_5cm/images/` pour l'étendue ExG. Une assertion refuse tout autre groupe.
- **Partage** (scientific-challenger, D-013 § 1.1) : CAL = DJI_0543 à 0620 (32 photos), VAL-S = DJI_0628 à 0682 (32 photos). L'écart entre 0620 et 0628 vaut 8 numéros : aucune photo n'est écartée. Le partage coïncide avec `out/comptage_math/image-analyst/D-013/partage.csv` (assertion passée). **Seul CAL sert à calibrer.**
- **Commande** : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/plant-geometry/D-013/stats_geometriques.py` (142 s).
- **Sorties** dans `out/comptage_math/plant-geometry/D-013/` : `stats_geometriques.json` (blocs `CAL`, `VAL-S`, `distances_CAL_VAL-S`), `par_photo.csv`, `rangees_par_photo.csv`, `partage_plant_geometry.csv`, `journal.txt`.
- **Note technique** : `-I` fait ignorer `PYTHONIOENCODING`. Le script reconfigure donc lui-même sa sortie en UTF-8.

### Règles (écrites dans l'en-tête du script avant le premier lancement)

- **R0, reconstruction.** Dans chaque tuile, on ne garde que les points de sa zone propre. Les zones propres partitionnent la photo. Les points sont ramenés dans le repère du centre du disque.
  - Contrôle [O] : 8 649 points dans la région, autant que `dans_region` de `dev_dense.csv` ; 9 423 points dans les photos entières ; aucun doublon à moins de 5 cm.
- **R1, densité.** On la calcule par photo, par tuile (région de la tuile ≥ 50 m²) et par cellule de 10 m × 10 m entièrement dans le disque.
- **R2, voisins.** Les distances au 1er, 2e et 3e voisin sont cherchées parmi tous les points de la photo. Méthode du bord : un point compte pour le rang k s'il est à au moins d_k du bord de la photo.
- **R3, g(r) et K(r).** Estimateur à correction de translation sur le rectangle de la photo, mis en commun sur les photos, avec des anneaux de 0,25 m.
- **R4, rangées.** Facteur de structure fenêtré (Hann), périodes de 1,5 à 8 m. Une photo a des rangées si les deux conditions sont réunies :
  - S_max dépasse le maximum obtenu sur 10 tirages binomiaux ;
  - l'anisotropie dépasse 3.
- **R5, taille de couronne.** C'est le côté de boîte Roboflow, `(largeur + hauteur)/2` (`scripts/preparer_comptage_v3.py`, ligne 173). Les boîtes qui touchent le bord de la tuile ou de la photo sont écartées.
- **R6, étendue de végétation.** Pour chaque plant :
  - 16 secteurs, 3 rayons par secteur ;
  - fraction de pixels ExG > 0,05, lissée sur 0,3 m ;
  - étendue = premier rayon où cette fraction passe sous 0,5 ;
  - mesure censurée à la frontière de Voronoï et à 4 m.
- **R7, recouvrement.** Chaque couronne est un disque de rayon taille/2 (variantes ×1,25 et ×1,5). On mesure la part de ce disque couverte par l'union des disques voisins. Le taux de contact G5 est la part des mères ayant au moins une voisine avec d < r_i + r_j. On compte aussi la coupe des couronnes par le bord de la région.

### Résultats [O] (mesures sur références, sans E-NNN : ce ne sont pas des scores)

| Grandeur | CAL | VAL-S | Distance CAL↔VAL-S |
| --- | --- | --- | --- |
| Densité par photo, médiane [q05 ; q95] (/ha) | 950 [646 ; 1 206] | 1 064 [765 ; 1 257] | |
| Densité par tuile, moyenne ; CV | 952 /ha ; 0,35 | 1 029 /ha ; 0,21 | +8,0 % ; CV −39 % |
| Cellules de 10 m vides | 3,1 % | 0,8 % | |
| d1, médiane [q05 ; q95] (m) | 2,05 [1,33 ; 2,93] | 2,15 [1,42 ; 2,97] | KS 0,095 ; W1 0,098 m |
| d2 ; d3, médiane (m) | 2,51 ; 2,92 | 2,62 ; 3,04 | |
| d1 < 1 m ; < 1,5 m ; < 2 m | 0,8 % ; 11 % ; 46 % | 0,3 % ; 7 % ; 37 % | |
| Clark-Evans R | 1,28 | 1,39 | |
| g(r) : rayon où g < 0,1 ; pic | 1,0 m ; 1,46 à 2,4 m | 1,0 m ; 1,32 à 2,6 m | max ǀΔgǀ 0,27 (à 2,4 m) |
| Photos avec rangées (R4) | 6 / 32 | 2 / 32 | |
| Taille de boîte, médiane [q05 ; q95] (m) | 2,82 [1,81 ; 3,87] | 3,09 [2,07 ; 4,08] | KS 0,184 ; W1 0,242 m |
| Écart-type de log(taille) | 0,267 | 0,237 | |
| Taille < 2 m ; > 3,6 m | 8,4 % ; 11,4 % | 4,2 % ; 19,0 % | 0,042 ; 0,077 |
| Taille / d1, médiane | 1,38 | 1,43 | |
| Taux de contact G5 (d < r_i + r_j) | 94,4 % | 96,9 % | 0,025 |
| Part couverte par les voisins, rayon ×1 : médiane ; > 50 % | 0,23 ; 13 % | 0,28 ; 16 % | moyenne 0,038 |
| Idem, rayon ×1,25 : médiane | 0,58 | 0,64 | |
| Secteurs ExG censurés (végétation continue jusqu'à Voronoï) | 77 % | 80 % | |
| Couronnes coupées par le bord de la région | 11,8 % (disque 7,2 %, photo 7,0 %) | 14,5 % | |
| Plants hors région dont la couronne entre | 4,1 % des plants comptés | 4,7 % | |

### Lecture et consignes pour le simulateur (leaf-mathematician)

- **Disposition.** Le motif est régulier mais **sans rangées dans la plupart des photos** :
  - g ≈ 0 sous 1 m (cœur dur effectif), pic modéré de 1,3 à 1,5 vers 2,4 m, puis g ≈ 1 au-delà de 3,5 m ;
  - Clark-Evans de 1,3 à 1,4, loin du réseau parfait (2,15).

  Un processus à inhibition douce (Strauss ou Matérn, cœur dur de 1,0 m, inhibition jusqu'à 1,8 m environ) reproduit mieux ces données qu'une grille. R4 trouve des rangées sur 6 photos de CAL, de période 1,5 à 2,3 m, et leur orientation varie d'une photo à l'autre. La période du pic coïncide avec l'anneau du premier voisin. [H] : ce sont des alignements locaux, pas des rangs de plantation réguliers. Le simulateur peut ajouter une faible composante en rangées sur environ 20 % des scènes, sans en faire la règle.
- **Tailles.** Loi à peu près log-normale : σ_log ≈ 0,25, queue basse jusqu'à 0,45 × la médiane (q01).
  - La médiane en mètres (2,8 à 3,1) est **imposée par la convention d'échelle** « couronne médiane = 3 m » ([S] `parametres.json`). Elle n'est pas une mesure.
  - Seules les formes relatives sont mesurées : taille / médiane, taille / d1 ≈ 1,4, corrélation de Spearman taille–d1 ≈ +0,41 (les grandes couronnes ont des voisins plus éloignés).
  - La part de couronnes < 2 m est **très sensible à l'échelle** : 8 % à l'échelle nominale, 29 % à −20 %, 3 % à +20 %.
- **Recouvrement.** Les boîtes sont plus larges que l'espacement (taille/d1 ≈ 1,4) : 94 à 97 % des mères touchent au moins une voisine, et une couronne a en médiane le quart de sa surface sous les disques voisins. Côté image, 77 à 80 % des directions gardent de la végétation continue jusqu'à la frontière de Voronoï : la canopée est jointive.
  - Le rayon d'étendue ExG est une borne basse (1,4 m en médiane). L'herbe compte comme végétation et les feuilles sèches non.
  - On ne sait pas qui recouvre qui.
- **Bord.** 12 à 15 % des couronnes comptées sont coupées par le bord de la région. De plus, l'équivalent de 4 à 5 % de plants situés hors région entrent en partie dans la zone comptée : ce sont des distracteurs de bord.
- **Rejets.** [O] Les références ne contiennent que des mères. **Aucune statistique de rejet n'est produite** : nombre, distance mère-rejet et taille ne sont pas mesurables ici. Ils doivent venir d'une source [S] (banana-morphology) ou d'une hypothèse [H] déclarée. Les 0,3 à 0,8 % de paires à moins de 1 m sont des distances entre mères annotées, pas des rejets.
- **Feuilles.** Non mesurées : en canopée jointive à 3,6–6,7 cm/px, E-018 montre que la longueur et l'orientation d'une feuille ne s'estiment pas. Les valeurs sont reprises de `modele_feuille.md` § 2.2, tous en [H] avec des [O] ponctuels : K de 4 à 12, L de 0,8 à 2,5 m, W de 0,35 à 0,9 m, r0 de 0,1 à 0,6 m. `docs/recherche/morphologie.md` n'existe pas dans le dépôt.

### Incertitudes et points d'attention

- **Échelle.** L'erreur systématique de la convention des 3 m vaut plusieurs dizaines de pour cent [H]. Les longueurs varient comme s et la densité comme 1/s² (±20 % d'échelle donne ÷1,44 ou ×1,56). Sont insensibles à l'échelle : g en fonction de r/d1, taille/d1, recouvrement, parts coupées, Clark-Evans.
- **Variabilité naturelle CAL↔VAL-S, déjà supérieure à certains seuils absolus de scientific-challenger** :
  - G1, KS tailles : 0,18 pour un seuil de 0,10, et W1 0,24 m pour un seuil de 0,15 m ;
  - G4, max ǀΔgǀ : 0,27 pour un seuil de 0,25 ;
  - G3, CV de densité par tuile : −39 % pour un seuil de ±25 % ;
  - G6, part > 3,6 m : 0,077 pour un seuil de 0,05.

  Avec la règle max(seuil, 1,5 × d(CAL, VAL-S)), ces tests restent atteignables, mais les deux moitiés diffèrent réellement : en VAL-S, couronnes plus grandes et motif plus régulier. Un simulateur calé sur CAL partira avec cet écart. À signaler à scientific-challenger.
- **Boîtes.** Les boîtes Roboflow sont tracées par des annotateurs : la « taille » mesure la boîte, pas l'envergure foliaire réelle. annotation-manager (§ 1.3) note qu'en plantation jointive la boîte couvre surtout le centre de la couronne. Les variantes ×1,25 et ×1,5 encadrent ce biais : à ×1,25, la médiane couverte passe à 0,58.
- **CV par tuile.** Il est gonflé par les tuiles de bord à petite région (seuil de 50 m²). La densité par photo ou par cellule de 10 m est plus stable.
