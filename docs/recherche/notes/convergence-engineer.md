# Notes de convergence-engineer (équipe COMPTAGE)

Rédacteur unique : convergence-engineer. Ouvert le 7 novembre 2026 pour la concertation C-002, question 2 :
un vote des axes linéaires (B′ : signe −1, noyau tronqué, pondéré par la cohérence) donne-t-il une carte de preuve
des centres meilleure que le hasard, et complémentaire de A′ ?

Code : `comptage_math/votes.py`. Sorties : `out/comptage_math/convergence-engineer/`.

---

## 1. Pré-enregistrement d'E-008 (écrit le 7 novembre 2026, avant tout calcul, y compris le contrôle de résolution)

### 1.0 Données

- Réglage et sélection : tuiles de `out/comptage_math/evaluation/images_dense.csv` de rôle `dev_reglage` **et** de groupe
  `bv_session_a` (359 tuiles, 64 unités ; la liste est déjà filtrée par `data/comptage_math/references/dev_dense_images.csv`,
  sans pépinière).
- Rapport sans choix : rôle `dev_transfert` (lasuiza dédoublonné, vols_100_022x, corte), au seuil figé sur bv_session_a.
- Interdits, vérifiés par assertion dans les scripts : bv_b_train (réservé), bv_b_val (val_iter, val_scellee), groupes
  test ou exclus (`math_evaluer.INTERDITS`), `cg/`. Aucune donnée de ces groupes n'est lue.
- Images préparées `data/drone/comptage_v5_5cm/images/`, 3,6 à 6,7 cm/px ; appariement des mères à 1 m
  (`scripts/math_evaluer.py`, fonctions `comptes`, `prf`, `evaluer_points`, `double_comptage`).

### 1.1 Contrôle préalable : le signe de l'alignement survit-il à la résolution préparée ?

E-003 a mesuré s = cos 2(φ − ψ) ≈ −0,245 (T_feuille) à 1,1 et 2 cm/px sur photos natives. orientation-engineer prédit
que le signe survit à 3 cm/px et disparaît à 5 cm/px.

- **Tuiles** : 10 tuiles de bv_session_a (rôle dev_reglage), 10 unités distinctes, au moins 10 mères dans la région
  comptée, tirées avec la graine 20261108 (`out/comptage_math/convergence-engineer/verif_resolution.py`).
- **Canal** : T_feuille de `comptage_math/orientation.py` (`tenseur`), luminance, σ_g = 4 cm et σ_t = 10 cm convertis en
  pixels à la résolution de la tuile (planchers du module : 0,7 px et 1 px). Masque : `masque_vegetation`.
- **Statistique** : moyenne de s sur les pixels du masque situés dans l'anneau 0,4–1,5 m autour de la mère la plus
  proche (comme E-003). Contrôles : demi-maille (chaque mère décalée de 0,5 × 2,18 m, maille de bv_session_a de
  `niveaux_nuls/maille_par_groupe.json`, direction aléatoire), orientations mélangées entre pixels.
- **Règle de lecture (écrite avant)** :
  - « survit » si s̄_réel < 0, si l'écart apparié réel − demi-maille est négatif sur au moins 8 tuiles sur 10 et si
    l'écart moyen est ≤ −0,05 ;
  - « disparaît » si l'écart moyen est > −0,02 ou négatif sur moins de 6 tuiles sur 10 ;
  - entre les deux : « affaibli » ; E-008 est lancée, avec cette réserve écrite dans la conclusion.
  - Si « disparaît » : E-008 n'est pas lancée sur les images préparées ; rapport « bloqué » et description du travail
    sur photos natives.
- Rapporté en plus, sans effet sur la règle : s̄ par tercile de cohérence, et s̄ séparé pour les tuiles < 5 cm/px et
  ≥ 5 cm/px (pour la prédiction d'orientation-engineer).

### 1.2 Formulation du vote (B′)

Notations : z(x) = c(x) e^{2iφ(x)} sortie de `orientation.tenseur` (φ = direction du gradient, c = cohérence),
d = x − c_0 pour un centre candidat c_0, ψ = arg d.

- **Poids par pixel** : a(x) = m(x) · c(x)^{p−1} · z(x), soit un module c^p et la phase 2φ ; m = masque de végétation.
  p = 1 : pondération par la cohérence (fiabilité validée par E-003 : s̄ −0,115, −0,224, −0,395 par tercile).
- **Noyau** (leaf-mathematician, `modele_feuille.md` § 3) : k(d) = ρ(|d|) e^{−2i arg d}, ρ(r) = r_min / r sur
  [r_min, r_max], 0 ailleurs ; r_min = 0,2 m fixé (anneau interne d'E-003 encore négatif). k(−d) = k(d) : corrélation
  = convolution, calculée par FFT.
- **Signe −1** (axes linéaires radiaux, gradient tangentiel) : V(c_0) = −Re[(a ∗ k)(c_0)] = Σ_x ρ · c^p · (−cos 2(φ − ψ)).
- **Troncature** (OBJ-V4 : le vote en angle doublé n'a pas de polarité) : r_max ≈ 0,6 × maille, réglé dans la grille.
- **Normalisation par la densité de végétation** : sous l'hypothèse nulle d'orientations uniformes et indépendantes,
  E[V] = 0 et Var[V] = ½ Σ_x |a(x)|² ρ(|d|)², d'où le score analytique
  z_an(c_0) = V / √(½ (|a|² ∗ ρ²)(c_0) + ε). Il ne dépend plus de la quantité de végétation, seulement de la cohérence
  de l'alignement. Les pixels voisins étant corrélés (lissage σ_t), z_an est gonflé d'un facteur à peu près constant :
  la carte exposée pour la détection et la fusion est le **z robuste par image**, z_vote = (z_an − médiane) / (1,4826 ×
  MAD) sur les pixels valides, comme `zrob` d'E-006 pour A′.
- **Échelles du tenseur** : σ_g = 4 cm et σ_t = 10 cm (E-003), non réglées.
- **Extraction** : maxima locaux de z_vote sur un disque de rayon R_nms, z_vote ≥ 0,5, pixels valides (somme RGB > 15),
  comme E-006.

### 1.3 Grille réduite (3 paramètres, 18 configurations)

| Paramètre | Valeurs | Origine |
| --- | --- | --- |
| r_max | 1,0 ; 1,3 ; 1,6 m (≈ 0,45 ; 0,6 ; 0,75 × maille 2,18 m) | OBJ-V4 |
| p (exposant de la cohérence) | 1 ; 2 | fiabilité E-003 |
| R_nms | 0,8 ; 1,0 ; 1,2 m | comme A′ (E-006) |

### 1.4 Règle de sélection

- Pour chaque configuration : seuil de score choisi au maximum du **F1 cumulé sur bv_session_a** (200 quantiles, comme
  `cycle1_grille.py`) ; la configuration retenue a le meilleur F1 cumulé. Égalité à 0,005 près : préférer r_max = 1,3,
  puis p = 1, puis R_nms = 1,0.
- dev_transfert est évalué par `scripts/math_evaluer.py` au seuil figé, sans choix.

### 1.5 Contrôles (configuration retenue, seuil figé, bv_session_a)

- **Orientations mélangées** : permutation de z entre pixels du masque (graine 20261108), même vote, même seuil ; on
  rapporte aussi son F1 au seuil qui lui est le plus favorable.
- **Végétation uniforme** et **demi-maille** : F1 des fichiers `out/comptage_math/evaluation/niveaux_nuls/*.csv` sur
  bv_session_a ; au niveau des scores, AUC de z_vote aux mères contre z_vote aux points de ces deux nuls, et règle
  OBJ-C3 (médiane de z aux mères > 75e centile de z aux milieux des paires de plus proches voisins mutuels < 3,5 m).
- **Critère « meilleur que le hasard »** : F1_vote − max(F1 végétation uniforme, F1 mélangé au meilleur seuil) > 0, borne
  basse de l'IC95 par bootstrap des unités (2 000 tirages, graine 2026) > 0.

### 1.6 Complémentarité avec A′

- z_A : carte `zrob(score_etoile)` de `comptage_math/feuille.py`, configuration figée d'E-006 (luminance, échelle 1,25).
- Corrélations de Pearson et de Spearman entre z_A et z_vote aux mères de bv_session_a (et, pour référence, aux points
  de végétation uniforme).
- **Fusion** : z_F = z_A + w · z_vote, w ∈ {0 ; 0,25 ; 0,5 ; 1 ; 2}, R_nms = 1,0 m (celui de A′), z_F ≥ 0,5 ; w et le
  seuil choisis au meilleur F1 cumulé sur bv_session_a (égalité à 0,005 près : le plus petit w). w = 0 doit redonner A′
  (≈ 0,541 ; contrôle de non-régression).
- **Critère « complémentaire »** : Spearman aux mères < 0,5 **et** F1(w*) − F1(w = 0) > 0 sur bv_session_a avec borne
  basse de l'IC95 bootstrap des unités > 0. Cette différence est mesurée sur l'ensemble qui a servi à choisir w : elle est
  optimiste, et dev_transfert (seuil et w figés) est le chiffre honnête.

### 1.7 Prédictions chiffrées (avant calcul)

| # | Grandeur | Prédiction |
| --- | --- | --- |
| P-V0 | Contrôle de résolution | « affaibli » ou « survit » : écart moyen réel − demi-maille ≈ −0,07 [−0,15 ; −0,02] ; plus faible au-delà de 5 cm/px |
| P-V1 | F1 du vote seul, bv_session_a | 0,38 [0,30 ; 0,45] : au-dessus de la végétation uniforme (0,331), sous A-iso (0,423) |
| P-V2 | F1 orientations mélangées (meilleur seuil) | ≤ 0,34 |
| P-V3 | Critère « meilleur que le hasard » | passe, de peu (probabilité 0,55) |
| P-V4 | OBJ-C3 pour le vote | échoue (probabilité 0,6) : sans polarité, le milieu de deux voisins reçoit les axes des deux plants |
| P-V5 | Spearman z_A – z_vote aux mères | 0,2 [0,05 ; 0,4] |
| P-V6 | w* et gain de fusion sur bv_session_a | w* ∈ {0,25 ; 0,5} ; gain +0,02 [0 ; +0,05] ; sur dev_transfert +0,01 [−0,02 ; +0,04] |
| P-V7 | Temps du vote | < 1 s par hectare sur 8 cœurs |

---

## 2. Résultats d'E-008 (7 novembre 2026, après calcul ; le § 1 n'a pas été modifié)

Commandes :
```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/convergence-engineer/verif_resolution.py
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/convergence-engineer/e008_votes.py
```
Sorties : `out/comptage_math/convergence-engineer/E-008_verif_resolution.{csv,json}`, `E-008/bilan_E-008.json`,
`E-008/grille_bv_session_a.csv`, `E-008/fusion_bv_session_a.csv`, `E-008/detections/`, `E-008/transfert/`,
`E-008_journal.txt`. Empreintes SHA-256 du script, de `votes.py` et d'`orientation.py` dans le bilan. Durée 1 104 s sur 8 cœurs.

### 2.1 Contrôle de résolution [M, E-008 étape 0]

- 10 tuiles (3,6 à 5,7 cm/px ; 9 sous 5 cm/px) : s̄ réel −0,168 ; demi-maille +0,034 ; mélange 0,000.
- Écart réel − demi-maille −0,201 (écart-type 0,036), négatif sur **10/10** tuiles. **Verdict selon la règle : « survit ».**
- La seule tuile ≥ 5 cm/px (5,7 cm/px) donne −0,253 : la prédiction « disparaît à 5 cm/px » n'est pas appuyée
  (une tuile seulement : non concluant sur ce point).
- Terciles de cohérence : −0,063, −0,146, −0,293 (même tendance qu'E-003).

### 2.2 Vote seul (bv_session_a, sélection) [M, E-008]

- Grille : F1 de 0,583 à 0,638 ; croissant avec r_max (1,0 → 1,3 → 1,6). Retenu par la règle :
  r_max = 1,6 m, p = 1, R_nms = 1,0 m, seuil z ≥ 2,24. **r_max est au bord de la grille.**
- F1 0,637 [IC95 0,624 ; 0,649], précision 0,630, rappel 0,643 ; double comptage 0,051.
- Nuls : orientations mélangées 0,335 (seuil figé) et 0,369 (meilleur seuil) ; végétation uniforme 0,331 ;
  demi-maille 0,109. Écart au nul le plus fort +0,268 [0,253 ; 0,283] : **meilleur que le hasard**.
- Scores : AUC mères contre végétation uniforme 0,742, contre demi-maille 0,809, contre milieux de voisins 0,777
  (mélangé : 0,505). OBJ-C3 **passe** : médiane aux mères 1,21 contre 75e centile aux milieux 0,72 ; sur
  vols_100_022x (rapport) 1,41 contre 0,36, là où A′ échouait (0,561 contre 0,732).

### 2.3 Complémentarité avec A′ [M, E-008]

- z_A (configuration d'E-006) reproduit A′ : F1 0,541 à w = 0 (E-006 : 0,541).
- Corrélation aux mères : Pearson 0,232, Spearman 0,232 (aux points de végétation : 0,34).
- Fusion z_A + w z_vote sur bv_session_a : 0,541 (w 0), 0,580 (0,25), 0,598 (0,5), 0,624 (1), **0,638 (2, au bord)**.
  Gain sur A′ +0,098 [0,086 ; 0,109] : critère « complémentaire » passé **à la lettre**, mais la fusion n'apporte rien
  au vote seul (0,638 contre 0,637) : c'est le vote qui porte la preuve, et A′ n'ajoute rien de mesurable.

### 2.4 dev_transfert, sans choix, par `scripts/math_evaluer.py` au seuil figé [M, E-008]

| Méthode | F1 [IC95] | P | R | corte | lasuiza | vols_100_022x | double comptage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Vote B′ seul | **0,546** [0,519 ; 0,569] | 0,442 | 0,712 | 0,667 | 0,530 | 0,548 | 0,042 |
| A′ (w = 0) | 0,355 [0,325 ; 0,383] | 0,252 | 0,601 | 0,496 | 0,298 | 0,422 | 0,075 |
| Fusion w = 2 | 0,533 [0,507 ; 0,555] | 0,427 | 0,708 | 0,651 | 0,512 | 0,542 | 0,045 |

Pour information : v5 0,821 (bv_session_a) et 0,876 (dev_transfert), E-001/E-006, entraîné sur ces photos.
Références de lasuiza et vols incomplètes (D-005) : la précision y est sous-estimée.

### 2.5 Prédictions

| # | Prédit | Mesuré | Verdict |
| --- | --- | --- | --- |
| P-V0 | écart ≈ −0,07 [−0,15 ; −0,02] | −0,201 | signe confirmé, ampleur sous-estimée |
| P-V1 | F1 0,38 [0,30 ; 0,45] | 0,637 | **réfutée** (bien meilleur) |
| P-V2 | mélangé ≤ 0,34 | 0,369 (meilleur seuil) ; 0,335 (seuil figé) | réfutée de peu |
| P-V3 | meilleur que le hasard, de peu | oui, +0,268 | confirmée (pas « de peu ») |
| P-V4 | OBJ-C3 échoue | passe (bv_session_a et vols) | **réfutée** |
| P-V5 | Spearman 0,2 [0,05 ; 0,4] | 0,232 | confirmée |
| P-V6 | w* ∈ {0,25 ; 0,5}, gain +0,02 | w* = 2 (bord), +0,098 ; transfert −0,013 contre le vote seul | réfutée |
| P-V7 | < 1 s/ha sur 8 cœurs | 0,47 s/ha (3,8 s/ha sur un cœur, médiane) | confirmée |

### 2.6 Réserves

- r_max et w au bord de leur grille : l'optimum est peut-être au-delà (r_max > 0,73 × maille ; w → ∞, soit le vote seul).
  Toute extension est une nouvelle grille, à pré-enregistrer.
- Seuil et configuration choisis sur bv_session_a : son F1 est optimiste ; dev_transfert est le chiffre honnête.
- La condition « rotation » (image tournée, centres non tournés) n'a pas été mesurée pour le vote.
- Le masque de végétation est le masque provisoire d'`orientation.py`.

---

## 3. Pré-enregistrement d'E-010 (cycle 3, D-006 ; écrit le 7 novembre 2026, avant tout calcul)

Le vote B′ est la candidate principale ; A′ n'est plus qu'un témoin (D-006). Données et interdits identiques au § 1.0 :
sélection sur bv_session_a sans pépinière (rôle dev_reglage), dev_transfert rapporté sans choix ; bv_b_train, bv_b_val,
groupes test ou exclus et `cg/` exclus par assertion.

### 3.1 Grille d'extension (2 paramètres, 6 configurations)

Fixés d'après E-008 (sans nouveau réglage) : p = 1, R_nms = 1,0 m, r_min = 0,2 m, σ_g = 4 cm, z ≥ 0,5 pour les candidats.

| Paramètre | Valeurs |
| --- | --- |
| r_max | 1,6 ; 2,0 ; 2,4 m (0,73 ; 0,92 ; 1,10 × maille) |
| échelles σ_t du champ | « simple » : 10 cm (E-008) ; « multi » : 6, 10 et 15 cm |

**Combinaison des échelles : fusion des votes.** Pour chaque σ_t, on calcule le z analytique z_an,s (§ 1.2). La carte est
z = zrob(Σ_s z_an,s). Le maximum de cohérence a été écarté pour deux raisons :
- il choisit par pixel un tenseur dont le bruit diffère selon l'échelle, ce qui biaise la cohérence vers la petite échelle (moins lissée) ;
- il casse la linéarité du vote.

La somme des z garde, elle, une convolution par échelle. Elle reste un z sous le nul (à un facteur près, corrigé par
zrob). Une échelle qui ne vote pas ne pèse que par son bruit.

### 3.2 Règle de sélection

- Seuil au maximum du **F1 cumulé sur bv_session_a** (200 quantiles), comme au § 1.4.
- Configuration retenue : meilleur F1. En cas d'égalité à 0,005 près, on préfère « simple », puis le r_max le plus proche de 1,6 m.

### 3.3 Mesures sur la configuration retenue (aucune ne sert au choix)

- **Règle de rotation** (`docs/recherche/test_final.md` § 4.3, amendement 2) :
  - l'image est tournée de 90° (`np.rot90`) et les détections sont lues dans le repère des pixels de la tuile, sans rotation
    inverse ni rotation des centres, comme dans E-007 ;
  - F1 au budget k = N_réf (classement global), comparé à F1_orig au budget et au nul de végétation uniforme ;
  - la condition est remplie si F1_rot − F1_veg ≤ 0,05 **et** si F1_rot − F1_veg ≤ 0,25 × (F1_orig − F1_veg) ;
  - rapportés en plus : l'IC95 bootstrap par unité de F1_rot − F1_veg, et F1_rot au seuil de fonctionnement.
- **Double comptage** (`math_evaluer.double_comptage`, au seuil de fonctionnement) et **OBJ-C3** (médiane de z aux mères
  supérieure au 75e centile aux milieux), sur bv_session_a ; OBJ-C3 aussi sur vols_100_022x, pour le rapport.
- **dev_transfert** : F1 donné par `math_evaluer.py` au seuil figé.

### 3.4 Attributs des candidats (rapportés, jamais utilisés pour choisir)

Ils sont calculés pour chaque candidat c, avec ψ = arg(x − c), sur les pixels du masque de végétation à une distance
comprise entre r_min et r_max. On note t(x) = −cos 2(φ(x) − ψ), qui vaut 1 pour un axe radial. Le champ utilisé est celui
du canal σ_t = 10 cm.
- **n_soutien** : nombre de pixels dont t > 0,5 (axe à moins de 30° du radial) et dont la cohérence dépasse la médiane de la tuile.
  On rapporte aussi la fraction par rapport aux pixels du disque ; le hasard donne 1/3.
- **couverture** : nombre de secteurs, sur 8 secteurs de 45°, où la moyenne de c·t est supérieure à 0,1. On le divise par 8.
- **rayon** : le profil est la moyenne de c·t par anneaux de 0,2 m. Le rayon est le rayon extérieur du dernier anneau dont
  le profil dépasse la moitié du maximum.

Ces attributs sont rapportés pour les vrais positifs et les faux positifs, appariés à 1 m au seuil de fonctionnement sur bv_session_a.

### 3.5 Prédictions chiffrées

| # | Grandeur | Prédiction |
| --- | --- | --- |
| P-X1 | r_max retenu | 2,0 m ; F1 bv_session_a 0,645 [0,635 ; 0,66] |
| P-X2 | gain « multi » − « simple » au même r_max | +0,005 [−0,01 ; +0,02] ; donc « simple » retenu (probabilité 0,6) |
| P-X3 | règle de rotation | remplie (probabilité 0,7) : F1_rot ≈ 0,36, F1_rot − F1_veg ≈ 0,03 |
| P-X4 | double comptage | ≤ 0,06 |
| P-X5 | OBJ-C3 | passe sur bv_session_a et sur vols |
| P-X6 | attributs | médianes couverture 5/8 (vrais positifs) contre 3/8 (faux positifs) ; fraction de soutien 0,45 contre 0,38 ; rayon médian des vrais positifs 1,0 m [0,6 ; 1,4] |
| P-X7 | dev_transfert | F1 0,55 [0,52 ; 0,58] |

## 4. Résultats d'E-010 (7 novembre 2026, après calcul ; le § 3 n'a pas été modifié)

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/convergence-engineer/e010_extension.py`.
Durée : 458 s sur 8 cœurs.

Sorties, dans `out/comptage_math/convergence-engineer/` :
- `E-010/bilan_E-010.json` et `E-010/grille_bv_session_a.csv` ;
- `E-010/detections/vote_e010.csv` (identique à E-008 : 16 650 candidats sur bv_session_a dans les deux passes) ;
- `E-010/detections/vote_e010_attributs.csv`, avec les attributs de tous les candidats (z ≥ 0,5) de bv_session_a et de dev_transfert ;
- `E-010/rotation_vote_e010.csv`, `E-010/transfert/` et `E-010_journal.txt`.

### 4.1 Grille [M, E-010]

| r_max | simple (σ_t 10 cm) | multi (6, 10, 15 cm) |
| --- | --- | --- |
| 1,6 m | **0,6368** | 0,6371 |
| 2,0 m | 0,6304 | 0,6291 |
| 2,4 m | 0,6180 | 0,6173 |

- L'optimum est à r_max = 1,6 m. Le bord de grille signalé en E-008 était donc un vrai maximum : le F1 baisse au-delà.
- Le gain du multi-échelle est nul (+0,0003 ; −0,0013 ; −0,0007).
- **Configuration retenue** : r_max = 1,6 m, σ_t = 10 cm seul, p = 1, R_nms = 1,0 m, seuil z 2,24. C'est la configuration d'E-008.
- Temps : 0,52 s/ha sur 8 cœurs en simple, 1,56 s/ha en multi.

### 4.2 Règle de rotation (test_final.md § 4.3) [M, E-010]

- Au budget N_réf = 8 649 : F1_orig 0,636, F1_rot 0,292, F1_veg 0,331.
- Excès après rotation : −0,039. IC95 bootstrap par unité [−0,050 ; −0,027]. Excès d'origine : +0,305.
- Condition 1 (≤ 0,05) : vraie. Condition 2 (≤ 0,25 × 0,305) : vraie. **La règle de rotation est remplie.**
- F1_rot au seuil de fonctionnement : 0,297.

### 4.3 Double comptage, OBJ-C3, dev_transfert [M, E-010]

- bv_session_a : F1 0,637 [0,624 ; 0,649] ; double comptage 0,051.
- OBJ-C3 passe sur les deux groupes :
  - bv_session_a : 1,21 contre 0,72 (AUC 0,777) ;
  - vols_100_022x : 1,41 contre 0,36 (AUC 0,836).
- dev_transfert, au seuil figé : F1 0,546 [0,519 ; 0,569] ; double comptage 0,042.

### 4.4 Attributs des candidats, bv_session_a, au seuil (rapportés, non utilisés) [M, E-010]

| Attribut | Vrais positifs (n 5 563), médiane [q25 ; q75] | Faux positifs (n 3 261) | AUC VP contre FP |
| --- | --- | --- | --- |
| n_soutien (px) | 1 187 | 999 | 0,618 |
| fraction de soutien (hasard 1/3) | 0,543 [0,504 ; 0,588] | 0,507 [0,478 ; 0,545] | 0,665 |
| couverture (sur 8 secteurs) | 0,75 [0,625 ; 0,75] | 0,625 [0,5 ; 0,75] | 0,661 |
| rayon (m) | 1,4 [1,2 ; 1,6] | 1,2 [1,0 ; 1,4] | 0,550 |

Le rayon est en partie borné par r_max (1,6 m) ; il mesure l'étendue du soutien, pas la taille du plant.

### 4.5 Prédictions

| # | Prédit | Mesuré | Verdict |
| --- | --- | --- | --- |
| P-X1 | r_max 2,0 ; F1 0,645 | 1,6 ; 0,637 | réfutée |
| P-X2 | gain multi ≈ +0,005, « simple » retenu | gain ≈ 0, « simple » retenu | confirmée |
| P-X3 | rotation remplie, excès ≈ +0,03 | remplie, excès −0,039 | confirmée (excès plus bas que prévu) |
| P-X4 | double comptage ≤ 0,06 | 0,051 | confirmée |
| P-X5 | OBJ-C3 passe sur les deux groupes | passe | confirmée |
| P-X6 | couverture 5/8 contre 3/8 ; fraction 0,45 contre 0,38 ; rayon 1,0 m | 6/8 contre 5/8 ; 0,54 contre 0,51 ; 1,4 m | sens confirmé, niveaux réfutés (sélection des candidats sur l'alignement) |
| P-X7 | dev_transfert 0,55 [0,52 ; 0,58] | 0,546 | confirmée |

---

## 5. Pré-enregistrement d'E-012 (écrit le 7 novembre 2026, avant tout calcul)

Point de départ : les constats d'error-analyst (E-011).
- Le pic du vote tombe sur le flanc de la couronne : le candidat le plus proche des mères oubliées est à 1,29 m en médiane, avec z 2,47.
- Les grandes couronnes sont souvent oubliées : 0,289 au-delà de 3,6 m, contre 0,087 pour le v5.
- 19 % des fausses détections sont des doublons.

Données et interdits : comme au § 1.0. Sélection sur bv_session_a sans pépinière, dev_transfert rapporté sans choix, assertions contre bv_b_train et bv_b_val.

**Base** (configuration E-008/E-010) : champ σ_t = 10 cm ; vote r_max 1,6 m, p = 1 ; maxima avec R_nms 1,0 m ; z ≥ 0,5.

### 5.1 Variantes (3 facteurs, 15 configurations)

**(b) Noyau.** Trois valeurs :
- **K16** : la base ;
- **Kmax** : max(zrob(z_an,1.6), zrob(z_an,2.4)) pixel par pixel. C'est le r_max par pixel au maximum du z normalisé ;
- **Kfus** : zrob(z_an,1.6 + z_an,2.4), la fusion des deux cartes.

Les candidats sont les maxima de cette carte, avec R_nms 1,0 m et z ≥ 0,5. Leur score est la valeur de la carte au pic.

**(a) Recentrage.** Il s'applique à chaque candidat. Le score n'est pas modifié. Un déplacement de plus de 1,5 m est refusé, et le candidat garde alors sa position.
- **R0** : aucun recentrage.
- **Rb, barycentre.** Dans le disque de 1,5 m autour du pic, on prend la composante connexe du pic dans {Z ≥ ½ Z(pic)}. Le point retenu est son barycentre pondéré par Z − ½ Z(pic).
- **Rmc, convergence par moindres carrés des droites support.** Chaque pixel x_i du masque, à une distance de r_min à r_max (celui du noyau ; 2,4 m pour Kmax et Kfus) de l'estimation courante p, porte une droite. Cette droite passe par x_i et suit la direction de l'axe linéaire (φ_i + 90°). Le poids vaut w_i = c_i · max(t_i, 0) · r_min/|x_i − p|, avec t_i = −cos 2(φ_i − ψ_i(p)). On calcule p ← argmin Σ w_i dist(p, droite_i)², soit (Σ w_i P_i)⁻¹ Σ w_i P_i x_i avec P_i = I − u_i u_iᵀ. On fait 3 itérations, en partant du pic.

**(c) Suppression des non-maxima après recentrage** (seulement avec Rb ou Rmc).
- **N0** : non.
- **N1** : suppression gloutonne par score décroissant ; tout candidat recentré à moins de 1,0 m d'un candidat déjà gardé est supprimé.

Configurations : 3 noyaux × (R0 + 2 recentrages × 2 suppressions) = 15.

### 5.2 Règle de sélection et critère

- Seuil au maximum du **F1 cumulé sur bv_session_a** (200 quantiles), pour chaque configuration.
- Configuration retenue : meilleur F1. En cas d'égalité à 0,005 près, la plus simple : d'abord K16, puis Kfus, puis Kmax ; d'abord R0, puis Rb, puis Rmc ; d'abord N0, puis N1.
- **Critère d'adoption** : gain de F1 apparié (retenue − base, chacune à son seuil), bootstrap des unités (2 000 tirages, graine 2026). L'IC95 doit exclure 0. Si ce n'est pas le cas, la base reste la configuration de référence ; les mesures du § 5.3 sont tout de même faites sur la retenue et rapportées.

### 5.3 Mesures sur la retenue (sans choix)

- F1 et IC95.
- Double comptage.
- OBJ-C3, sur la carte du noyau retenu : bv_session_a et vols_100_022x.
- Règle de rotation de `test_final.md` § 4.3, avec la chaîne complète (noyau, recentrage, suppression) appliquée à l'image tournée, comme dans E-010.
- dev_transfert, au seuil figé.
- **Taux d'oubli par classe de taille** de la boîte de référence (`taille` × cm/px), avec les classes d'E-011 : ≤ 2,0 ; 2,0–2,4 ; 2,4–2,8 ; 2,8–3,2 ; 3,2–3,6 ; > 3,6 m. Il est mesuré pour la base, pour la retenue et pour la meilleure configuration de chaque noyau, au seuil de chacune.
- Distance médiane entre les vrais positifs et leur mère : base contre retenue.

### 5.4 Prédictions chiffrées

| # | Grandeur | Prédiction |
| --- | --- | --- |
| P-R1 | Rb (K16, N0) − base | +0,01 [0 ; +0,03] |
| P-R2 | Rmc (K16, N0) − base | +0,02 [−0,01 ; +0,05] |
| P-R3 | N1 − N0 (même noyau et recentrage) | +0,005 [0 ; +0,015] |
| P-R4 | Kmax et Kfus (R0) − K16 (R0) | entre −0,01 et +0,01 ; oubli au-delà de 3,6 m de 0,29 à 0,22 avec Kmax, avec une hausse de l'oubli sous 2,4 m |
| P-R5 | F1 de la retenue | 0,655 [0,64 ; 0,68], loin de la borne de 0,716 |
| P-R6 | Critère d'adoption | passe (probabilité 0,55) |
| P-R7 | Rotation, double comptage, OBJ-C3 | rotation remplie ; double comptage ≤ 0,05 ; OBJ-C3 passe |
| P-R8 | dev_transfert | 0,56 [0,53 ; 0,59] |
| P-R9 | Distance médiane vrai positif – mère | de 0,45 m (base) à 0,38 m (retenue) |

## 6. Résultats d'E-012 (7 novembre 2026, après calcul ; le § 5 n'a pas été modifié)

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/convergence-engineer/e012_recentrage.py`.
Durée : 791 s sur 8 cœurs, soit 7,0 s/ha sur 8 cœurs pour les 15 configurations ensemble.

Sorties, dans `out/comptage_math/convergence-engineer/` :
- dans `E-012/` : `bilan_E-012.json`, `grille_bv_session_a.csv`, `detections/<config>.csv` (15 fichiers), `rotation_K16_R0_N0.csv` et `transfert/` ;
- `E-012_journal.txt`.

### 6.1 Grille et critère [M, E-012]

F1 cumulé sur bv_session_a, avec entre crochets le gain apparié sur la base et son IC95 bootstrap par unité :

| Noyau | R0 | Rb N0 | Rb N1 | Rmc N0 | Rmc N1 |
| --- | --- | --- | --- | --- | --- |
| K16 | 0,6368 (base) | 0,6378 [−0,003 ; +0,005] | 0,6393 [−0,003 ; +0,008] | 0,6362 [−0,005 ; +0,003] | 0,6367 [−0,004 ; +0,004] |
| Kfus | 0,6368 [−0,006 ; +0,006] | 0,6329 [−0,010 ; +0,003] | 0,6386 [−0,004 ; +0,008] | 0,6391 [−0,004 ; +0,009] | **0,6402** [−0,003 ; +0,010] |
| Kmax | 0,6336 [−0,007 ; 0,000] | 0,6272 [−0,014 ; −0,004] | 0,6322 [−0,010 ; +0,001] | 0,6351 [−0,007 ; +0,003] | 0,6357 [−0,006 ; +0,004] |

- Les 15 configurations sont à moins de 0,01 de la base. Le meilleur F1 (Kfus Rmc N1, 0,6402) est à moins de 0,005 de la base.
- La règle d'égalité retient donc la base, **K16 R0 N0**. Le critère d'adoption n'est pas rempli : aucun IC95 de gain n'exclut 0, y compris pour la meilleure configuration ([−0,003 ; +0,010]).
- **Résultat négatif : ni le recentrage, ni le noyau adaptatif, ni la suppression après recentrage n'apportent de gain mesurable.**
- Sur une tuile témoin, le recentrage ne déplace les pics que de 0,10 m (Rb) à 0,15 m (Rmc) en médiane. Les candidats à 1,29 m des mères oubliées (E-011) ne sont donc pas des pics « sur le flanc » d'un même mode : ce sont des maxima distincts, et le recentrage local ne les ramène pas [H, voir la suite].

### 6.2 Oubli par classe de taille (au seuil de chaque configuration) [M, E-012]

| Taille de la boîte (m) | ≤ 2,0 | 2,0–2,4 | 2,4–2,8 | 2,8–3,2 | 3,2–3,6 | > 3,6 | global | distance VP–mère |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| n | 583 | 1 036 | 1 951 | 2 138 | 1 670 | 1 271 | 8 649 | |
| base K16 R0 N0 | 0,647 | 0,475 | 0,369 | 0,300 | 0,293 | 0,289 | 0,357 | 0,441 m |
| K16 Rb N1 | 0,626 | 0,448 | 0,353 | 0,282 | 0,276 | 0,263 | 0,337 | 0,434 m |
| Kfus Rmc N1 | 0,623 | 0,479 | 0,364 | 0,285 | 0,256 | **0,234** | 0,336 | 0,463 m |
| Kmax Rmc N1 | 0,648 | 0,489 | 0,381 | 0,298 | 0,290 | 0,264 | 0,357 | 0,450 m |

- Kfus fait passer l'oubli au-delà de 3,6 m de 0,289 à 0,234. Mais son seuil est plus bas (1,96 contre 2,24) : il gagne en rappel et perd en précision, et le F1 ne bouge pas. On reste loin du v5 (0,087).

### 6.3 Mesures sur la retenue (la base) [M, E-012]

Elles sont identiques à E-010 :
- F1 0,637 [0,624 ; 0,649] ;
- double comptage 0,051 ;
- OBJ-C3 passe : 1,21 contre 0,72 sur bv_session_a, 1,41 contre 0,36 sur vols ;
- règle de rotation remplie : F1_rot 0,292, F1_veg 0,331, excès −0,039 ;
- dev_transfert 0,546 [0,519 ; 0,569].

### 6.4 Prédictions

| # | Prédit | Mesuré | Verdict |
| --- | --- | --- | --- |
| P-R1 | Rb − base +0,01 | +0,001 | réfutée (gain nul) |
| P-R2 | Rmc − base +0,02 | −0,0005 | réfutée |
| P-R3 | N1 − N0 +0,005 | de +0,0005 à +0,0057 selon le noyau et le recentrage | confirmée en ordre de grandeur, non significative |
| P-R4 | Kmax/Kfus ±0,01 ; oubli > 3,6 m de 0,29 à 0,22 avec Kmax | ±0,003 ; Kmax R0 non mesuré par classe ; meilleur Kmax 0,264, Kfus 0,234 | partiellement confirmée |
| P-R5 | F1 retenue 0,655 | 0,637 (base) | réfutée |
| P-R6 | critère passe (probabilité 0,55) | ne passe pas | réfutée |
| P-R7 | rotation, double comptage, OBJ-C3 | conformes | confirmée |
| P-R8 | dev_transfert 0,56 | 0,546 | confirmée |
| P-R9 | distance VP de 0,45 à 0,38 m | 0,441 m (base), 0,434 m (Rb) | réfutée |

---

## 7. Pré-enregistrement d'E-014 (écrit le 7 novembre 2026, avant tout calcul)

Objet : la normalisation du vote et le masque, pour les grandes couronnes (taux d'oubli de 0,29 au-delà de 3,6 m, contre
0,09 pour le v5 ; E-011, E-012).

Données et interdits : comme au § 1.0. Sélection sur bv_session_a sans pépinière, dev_transfert rapporté sans choix,
assertions contre bv_b_train et bv_b_val. `comptage_math/couleur.py` est importé, jamais modifié.

**Référence** : la méthode E-013, s = z + 0,25 · d̃3.
- z est le vote d'E-008 : ρ = r_min/r, normalisation par l'écart-type nul, masque provisoire, r_max 1,6 m, p = 1.
  Les candidats sont les maxima de z (R_nms 1,0 m, z ≥ 0,5).
- d̃3 = −(d3 − 0,01352) / 0,02005, avec d3 = `couleur.carte_descripteurs(...)["d3"]` au candidat.
- La médiane et la MAD sont **figées** à leurs valeurs d'E-013 (`bilan_E-013.json`) et ne sont pas recalculées sur les
  nouveaux candidats. w est figé à 0,25 pour toutes les variantes.
- Cette référence doit redonner le F1 d'E-013, 0,6515 à 0,002 près. C'est un contrôle de non-régression.

### 7.1 Variantes (2 facteurs, 6 configurations)

**(a) Normalisation du vote.**
- **Nsd** : la référence. ρ = r_min/r, z_an = V / √(½ Σ|a|²ρ²).
- **Ncst** : ρ constant (= 1) sur [r_min, r_max], même normalisation par l'écart-type nul. Les pixels lointains
  d'une grande couronne pèsent autant que les proches.
- **Nsom** : ρ = r_min/r, normalisation par la somme des poids, z_an = V / Σ|a|ρ. C'est l'alignement moyen pondéré :
  il ne grandit plus avec la quantité de végétation.

Dans les trois cas, z = zrob(z_an) par image.

**(b) Masque de vote.**
- **Mprov** : `orientation.masque_vegetation`, le masque provisoire.
- **Mcoul** : `couleur.masque_vegetation(rgb, valide, res)`, le masque propre d'E-013.

### 7.2 Règle de sélection et critère

- Pour chaque configuration, le seuil sur s est choisi au maximum du **F1 cumulé sur bv_session_a** (200 quantiles).
- Configuration retenue : meilleur F1. En cas d'égalité à 0,005 près, on préfère Nsd, puis Ncst, puis Nsom ; puis Mprov, puis Mcoul.
- **Critère d'adoption** : gain apparié de F1 (retenue − référence, chacune à son seuil), bootstrap des unités
  (2 000 tirages, graine 2026). L'IC95 doit exclure 0.

### 7.3 Mesures sans choix

- **Taux d'oubli par classe de taille** (≤ 2,0 ; 2,0–2,4 ; 2,4–2,8 ; 2,8–3,2 ; 3,2–3,6 ; > 3,6 m), au seuil de chaque
  configuration, pour les six.
- Surcomptage : détections au seuil ÷ mères − 1.
- Sur la retenue :
  - F1 et IC95 ;
  - double comptage ;
  - OBJ-C3, sur la carte z du vote et sur la carte s = z + 0,25 · d̃3(carte), pour bv_session_a et vols_100_022x ;
  - règle de rotation de `test_final.md` § 4.3, avec la chaîne complète sur l'image tournée ;
  - dev_transfert par `math_evaluer.py`, au seuil figé.

### 7.4 Prédictions chiffrées

| # | Grandeur | Prédiction |
| --- | --- | --- |
| P-N0 | Référence reconstruite | F1 0,6515 ± 0,002 |
| P-N1 | Ncst − Nsd (Mprov) | −0,005 [−0,02 ; +0,01] ; oubli > 3,6 m en baisse de 0,03 |
| P-N2 | Nsom − Nsd (Mprov) | −0,03 [−0,06 ; 0] (bruit dans la végétation clairsemée) |
| P-N3 | Mcoul − Mprov (Nsd) | +0,003 [−0,005 ; +0,01] |
| P-N4 | Critère d'adoption | échoue (probabilité 0,65) ; la référence est maintenue |
| P-N5 | Retenue : double comptage, OBJ-C3, rotation | double comptage ≈ 0,064 ; OBJ-C3 passe ; rotation remplie |
| P-N6 | dev_transfert | 0,57 [0,54 ; 0,60] |

## 8. Résultats d'E-014 (7 novembre 2026, après calcul ; le § 7 n'a pas été modifié)

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/convergence-engineer/e014_normalisation.py`.
Durée : 408 s sur 8 cœurs, soit 2,9 s/ha sur 8 cœurs pour les 6 configurations et la carte d3 ensemble.

Sorties, dans `out/comptage_math/convergence-engineer/` :
- dans `E-014/` : `bilan_E-014.json`, `grille_bv_session_a.csv`, `detections/<config>.csv`, `rotation_Nsd_Mcoul.csv` et `transfert/` ;
- `E-014_journal.txt`.

`votes.py` gagne trois options, `rho_forme`, `normalisation` et `masque`. Leurs valeurs par défaut reproduisent E-008.

### 8.1 Grille et critère [M, E-014]

Toutes les configurations portent le terme + 0,25 · d̃3, avec médiane et MAD figées à leurs valeurs d'E-013. Gain apparié sur la référence, IC95 bootstrap des unités.

| Configuration | F1 bv_session_a | seuil s | gain [IC95] | surcomptage | oubli > 3,6 m | oubli global |
| --- | --- | --- | --- | --- | --- | --- |
| Nsd Mprov (référence) | 0,6515 | 1,86 | — | +0,107 | 0,231 | 0,314 |
| Nsd Mcoul | 0,6544 | 1,91 | +0,0029 [0,000 ; +0,006] | +0,090 | 0,231 | 0,316 |
| Ncst Mprov | 0,6538 | 1,33 | +0,0023 [−0,003 ; +0,008] | +0,103 | 0,208 | 0,313 |
| **Ncst Mcoul** | **0,6589** | 1,32 | **+0,0074 [+0,002 ; +0,013]** | +0,112 | **0,200** | 0,304 |
| Nsom Mprov | 0,6483 | 1,74 | −0,0032 [−0,007 ; +0,001] | +0,099 | 0,235 | 0,320 |
| Nsom Mcoul | 0,6496 | 1,66 | −0,0019 [−0,006 ; +0,003] | +0,156 | 0,227 | 0,300 |

- **Contrôle P-N0** : la référence redonne exactement le F1 d'E-013 (0,6515).
- **Application de la règle du § 7.2.**
  - Le maximum est 0,6589 (Ncst Mcoul). La fenêtre d'égalité de 0,005 contient Nsd Mcoul (0,6544). La règle d'égalité, qui préfère Nsd, retient donc **Nsd Mcoul**.
  - Son gain, +0,0029, a un IC95 de [−0,0001 ; +0,006] (arrondi [0,000 ; +0,006]) : il n'exclut pas 0. **Critère d'adoption non rempli. La référence (E-013) reste la méthode du développement.**
- **Constat hors règle**, signalé et non adopté : Ncst Mcoul est la seule configuration dont le gain exclut 0 (+0,0074 [+0,002 ; +0,013]). La règle d'égalité l'a écartée.
  - C'est un défaut de conception de ma règle : une fenêtre d'égalité de 0,005, plus large que les gains attendus, a empêché de retenir le seul effet significatif.
  - Ce constat ne vaut pas adoption. Il appelle une décision du chef d'orchestre et, le cas échéant, une confirmation pré-enregistrée.
- Taux d'oubli par classe, de la plus petite à la plus grande (≤ 2,0 ; … ; > 3,6 m) :
  - référence : 0,666 ; 0,452 ; 0,329 ; 0,245 ; 0,239 ; 0,231 ;
  - Ncst Mcoul : 0,693 ; 0,479 ; 0,318 ; 0,231 ; 0,217 ; 0,200.

  ρ constant fait baisser l'oubli des grandes couronnes (−0,031 au-delà de 3,6 m) et monter celui des petites (+0,027 sous 2,0 m), comme prévu. L'écart avec le v5 (0,087) reste grand.

### 8.2 Mesures sur la retenue (Nsd Mcoul) [M, E-014]

- F1 sur bv_session_a : 0,654 [0,639 ; 0,670].
- Double comptage : 0,062, contre 0,064 pour la référence.
- OBJ-C3 passe :
  - bv_session_a : sur z, 1,21 contre 0,72 ; sur s, 1,16 contre 0,73 ;
  - vols : sur z, 1,41 contre 0,36 ; sur s, 1,41 contre 0,43.
- Règle de rotation remplie : F1_rot 0,290, F1_veg 0,331, excès −0,041 [−0,053 ; −0,029].
- dev_transfert, au seuil figé :
  - retenue : 0,582 [0,554 ; 0,606] (corte 0,689, lasuiza 0,553, vols 0,599), double comptage 0,045 ;
  - référence : 0,570 [0,541 ; 0,596] (corte 0,679, lasuiza 0,548, vols 0,580).
- Ncst Mcoul n'a pas été mesuré sur la rotation ni sur dev_transfert, car il n'est pas la configuration retenue.

### 8.3 Prédictions

| # | Prédit | Mesuré | Verdict |
| --- | --- | --- | --- |
| P-N0 | référence 0,6515 ± 0,002 | 0,6515 | confirmée |
| P-N1 | Ncst − Nsd (Mprov) −0,005 ; oubli > 3,6 m −0,03 | +0,0023 ; −0,023 | sens de l'oubli confirmé, F1 meilleur que prévu |
| P-N2 | Nsom − Nsd −0,03 | −0,0032 | sens confirmé, ampleur réfutée |
| P-N3 | Mcoul − Mprov (Nsd) +0,003 | +0,0029 | confirmée |
| P-N4 | critère échoue, référence maintenue | échoue (par la règle d'égalité) | confirmée |
| P-N5 | double comptage ≈ 0,064 ; OBJ-C3 et rotation conformes | 0,062 ; conformes | confirmée |
| P-N6 | dev_transfert 0,57 [0,54 ; 0,60] | 0,582 | confirmée |

---

## 9. E-016 : témoins T9, T2, T7 et T8 (7 novembre 2026)

Les critères ont été écrits avant la mesure par independent-evaluator, dans `docs/recherche/test_final.md` § 7. Aucune nouvelle configuration du vote n'a été essayée. Le vote reste figé dans sa configuration d'E-008/E-010 (seuil z 2,238).

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/convergence-engineer/e016_temoins.py`. Durée : 59 s.

Sorties : `out/comptage_math/convergence-engineer/E-016/`, qui contient `bilan_E-016.json`, `T9_par_photo.csv` et `T2_vote_exg.csv`.

Seul ajout dans `votes.py` : l'option `champ(canal="exg")`, qui sert uniquement au témoin T2.

Contrôles de reproduction : le vote donne F1 0,6368, T3 0,567 et le v5 0,821, comme dans E-008, E-015 et E-001. Les intervalles sont des IC95 bootstrap par blocs de 7 photos (§ 7.0).

### T9, bloquant : passe

- Corrélation de Pearson, sur 64 photos, entre le rapport détections/références et la luminance médiane de la photo : r = −0,229 (Spearman −0,252). |r| ≤ 0,5, donc le témoin passe : aucune normalisation du seuil par photo n'est requise.
- Rapport médian : 1,03.
- Réserve : la luminance médiane varie peu, de 0,435 à 0,557. La puissance du test contre l'éclairage reste donc limitée.

### T2, témoin non bloquant

| | Luminance | ExG |
| --- | --- | --- |
| F1 bv_session_a (seuil re-choisi : z 1,98 pour l'ExG) | 0,637 | 0,563 |
| F1 dev_transfert | 0,546 | 0,431 |

- Écart ExG − luminance : −0,074, IC95 [−0,084 ; −0,065].
- F1(ExG) < F1(lum) − 0,02 : **l'ExG ne remplace pas la luminance**.
- F1(ExG) ≥ 0,55 : aucune dépendance à l'éclairage n'est à déclarer à ce titre.

### T7, rapporté : F1 par tranche d'échelle, au seuil figé

| Tranche (cm/px) | Vote, bv_session_a [IC95] | v5, bv_session_a | Vote, dev_transfert | v5, dev_transfert |
| --- | --- | --- | --- | --- |
| 3,6–4,5 (201 tuiles) | 0,625 [0,602 ; 0,654] | 0,819 | 0,550 | 0,877 |
| **4,5–5,5** (112 tuiles) | **0,640** [0,616 ; 0,658] | 0,827 | 0,543 | 0,879 |
| 5,5–6,7 (46 tuiles) | 0,662 [0,643 ; 0,690] | 0,817 | 0,541 | 0,871 |

Le vote ne se dégrade pas quand la résolution baisse. **Prédiction pour une validation à 5 cm/px : F1 ≈ 0,64 sur bv_session_a, et ≈ 0,54 sur des données de type dev_transfert.**

### T8, rapporté : bande de 1,6 m au bord réel de la tuile exclue

La bande exclue retire 896 des 8 649 mères de bv_session_a.

| Méthode | bv_session_a complet | sans bande [IC95] | dev_transfert complet | sans bande |
| --- | --- | --- | --- | --- |
| Vote | 0,637 | 0,632 [0,610 ; 0,652] | 0,546 | 0,550 |
| Baseline T3 | 0,567 | 0,577 [0,546 ; 0,604] | 0,481 | 0,506 |
| v5 | 0,821 | 0,830 [0,820 ; 0,840] | 0,876 | 0,872 |

Le vote n'est pas plus pénalisé par le bord que les autres méthodes : sa variation est de −0,005, contre +0,010 pour T3 et +0,009 pour le v5. L'écart du vote à T3 passe de +0,070 à +0,055 une fois la bande exclue. Ce sont des chiffres ponctuels ; aucun IC apparié n'a été calculé.

---

## 10. E-017 : réserve d'entraînement et pseudo-étiquettes du professeur (7 novembre 2026, avant tout entraînement)

Cadre : D-009, E-017 et **E-017, amendement 1** (OBJ-E2), dans `docs/experiment-log.md`. Le vote B′ est le professeur, figé tel qu'en E-008/E-010 : luminance, σ_g 4 cm, σ_t 10 cm, r_min 0,2 m, r_max 1,6 m, p = 1, signe −1, z robuste par image, maxima sur un disque de 1,0 m, seuil z 2,238. **Aucun réglage.** Aucune annotation n'est lue : ni pour la réserve (métadonnées seules), ni pour les témoins. Aucune évaluation sur les références.

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/convergence-engineer/e017_professeur.py`. Durée : 22 s au total, dont 13 s de vote sur 8 cœurs (330 tuiles). Journal : `E-017_journal.txt`. Bilan : `E-017/bilan_E-017.json`.

### 10.1 Réserve (amendement 1)

- **Entrent** : les tuiles banavista préparées hors références et hors exclusions, soit `bv_b_train` seul, en images seulement. [O] Les autres groupes banavista préparés sont exclus : `bv_session_a` (évaluation d'E-017, pépinière comprise) et `bv_b_val` (val_iter, val_scellee). `bv_b_tampon` et `bv_ortho` sont scellés et ne sont pas préparés.
- **Sortent** (amendement 1) : dev_transfert (lasuiza, vols_100_022x, corte), segmento_ouest, jeunes 0546 et 0548, pp_lote_2. J'exclus aussi pp_lote_2_parte_2 (même lot que pp_lote_2), ainsi que tous les groupes non banavista.
- **Marge de ±5 numéros DJI** autour de toutes les photos banavista exclues (DJI_0542 à 0682, 0842 à 0945) : DJI_0837 à 0841 sont retirées (22 tuiles).
- **Disque de 2 000 px** : colonnes `disque_cx`, `disque_cy`, `disque_r` (= `masque_*` de `tuiles.csv`). Le vote est calculé sur la tuile entière, comme dans l'évaluation d'E-008/E-010. Seuls les pics situés dans le disque sont gardés. L'élève doit traiter l'extérieur du disque comme une zone ignorée.
- **Bloc de seuil** (`seuil_bloc.csv`, sorti de la réserve, pas d'entraînement) : le plus petit préfixe de photos consécutives, dans l'ordre DJI, qui atteint 15 % des tuiles. Ce sont les 9 photos DJI_0757 et 0767 à 0774, soit 50 tuiles. [O] `groupes_photos.json` (test_final.md § 5.2) : ce sont les groupes de recouvrement 757 et 767-774. Les numéros 775 à 777 manquent, et 778 forme un groupe à part : le bloc ne recouvre donc aucune photo de la réserve.
- **Contrôles de fuite** :
  - cm/px identiques à `images_dense.csv` ;
  - aucune photo d'origine partagée avec un autre groupe ;
  - aucune image de `decoupage_bv_b_val.csv` ;
  - MD5 : 0 fichier identique parmi les 9 353 images hors réserve.

| Fichier | Tuiles | Photos | MD5 |
| --- | --- | --- | --- |
| `E-017/reserve.csv` (bv_b_train) | **280** | 57 (DJI_0778 à 0836) | `825175c587aa17b8de7f60e89d9201f5` |
| `E-017/seuil_bloc.csv` | 50 | 9 | `7c5dbba7faa5155b94a285f470460d48` |

**La réserve compte 280 tuiles, sous les ~600 visées.** Elle ne peut pas grossir sans réintroduire un groupe exclu par l'amendement 1.

### 10.2 Pseudo-étiquettes et témoins (coordonnées en pixels de l'image préparée)

| Fichier | Points | Positifs (z ≥ 2,238) | Ignorés (1,5 ≤ z < 2,238) | MD5 |
| --- | --- | --- | --- | --- |
| `pseudo.csv` (réserve) | 24 385 | 15 215 (médiane : 52 par tuile ; aucune tuile sans positif) | 9 170 | `a8351ba7b069e16577ac075fab781d00` |
| `pseudo_seuil_bloc.csv` (bloc de seuil, pour l'égalisation) | 4 140 | 2 611 | 1 529 | `021c9d4c209dbc14b40b555996110e56` |
| `pseudo_demimaille.csv` (indicatif, OBJ-E1) | 24 385 | 15 215 | 9 170 | `a8057940d29a9e70a079873e3e0ad0fd` |
| `pseudo_hasard_veg.csv` (T-E1a, z = 3) | 15 215 | 15 215 | 0 | `3f8a84c0bdf8455980c954fdcb25f76f` |

- **Demi-maille** : c'est la définition de `math_evaluer.py --niveaux-nuls` (c), et non le milieu entre plus proches voisins.
  - Chaque point (positif ou ignoré, z conservé) est déplacé de a/2 dans une direction tirée au hasard. On fait jusqu'à 50 essais pour tomber dans la végétation (ExG > Otsu dans le disque).
  - Écart avec l'évaluateur : a est la maille des positifs du professeur, 2,186 m (médiane des distances au plus proche voisin), et non la maille des références (2,239 m pour bv_b_train). La raison : aucune annotation n'entre dans l'entraînement.
  - Le point est ramené dans l'image. Le déplacement vaut 1,093 m.
  - Le nombre de positifs par image est identique (assertion).
- **Hasard dans la végétation** : même nombre de positifs par image que `pseudo.csv`, tirés uniformément dans le même masque ExG > Otsu (niveaux nuls (b)), restreint au disque. Graine [2026, indice de la tuile].

### 10.3 Contrôle visuel [O]

Vignettes `E-017/vignette_1_bv_bv_b_train_0002_3.png` (DJI_0780), `vignette_2_bv_bv_b_train_0060_4.png` (DJI_0783) et `vignette_3_bv_bv_b_train_0018_3.png` (DJI_0784), tirées avec la graine 2026. Positifs en rouge, zones ignorées en jaune, disque en cyan.

- La plupart des positifs tombent au cœur d'une rosette.
- Il manque des rosettes visibles.
- Quelques positifs tombent sur de l'herbe sans bananier : centre de la plage d'herbe de la vignette 3, et haut à droite de la vignette 2.
- Les zones ignorées tombent souvent entre deux plants.

Ce bruit est celui du professeur (F1 0,637 sur bv_session_a, E-010), et non un défaut de l'export.

### 10.4 Réserves

- **bv_b_train** entre en images : il ne pourra plus servir de développement vierge pour les élèves (amendement 1).
- Les tuiles d'une même photo se recouvrent de 20 % (découpage de préparation) : un même plant peut porter une étiquette dans deux tuiles.
- **Passe abandonnée** : une première passe, faite avant l'amendement 1, comptait 2 087 tuiles (MD5 `11733be35762c9c55d3706281a05d22e`). Elle est remplacée et ses fichiers sont supprimés. Il n'en reste que le journal `E-017_journal_v0_avant_amendement.txt`.

---

## 11. E-019 : F′, feuille = segment cohérent du champ d'orientation de B′ (C-003, D-011, suite d'E-018s)

### 11.0 Formulation et critère synthétique (écrits le 7 novembre 2026, avant tout calcul)

Formulation compatible avec les indices « vecteurs sur les feuilles » et « orientation » [S, D-011] ; ce n'est pas une reconstitution. Code : `comptage_math/votes.py`, section E-019 (`segments_feuilles`, `carte_votes_segments`), ajoutée sans modifier B′.

- **Champ** : celui de B′ figé (luminance, σ_g 4 cm, σ_t 10 cm, masque provisoire), z = c e^{2iφ}. Axe de la structure linéaire α = φ + 90°, soit e^{2iα} = −z/c (c'est l'axe le long duquel B′ vote avec le signe −1).
- **Feuille** : pixels du masque de cohérence c ≥ médiane de c sur le masque (par image) ; α quantifié en 6 classes de 30° (la courbure a priori, |κ|L ≤ 0,5 rad, interdit des classes plus fines), deux quantifications décalées de 15° ; composantes 4-connexes par classe. Doublons entre quantifications : glouton par taille, gardé si ≥ 50 % de pixels libres.
- **Segment** : moments pondérés par c. Centre p ; direction u = orientation moyenne du tenseur (angle doublé), pas l'ACP ; ℓ = √12 · écart type des projections sur u (longueur d'un segment uniforme), w idem sur la normale. Gardé si ℓ ≥ 0,3 m et ℓ ≥ 1,5 w.
- **Vote** : deux points p ± d u, **d(ℓ) = min(ℓ, 2,6 m)/2 + δ, δ = 0,2 m** (δ = r_min de B′ ; distance base du limbe → centre, a priori [H] 0,1–0,35 m ; 2,6 m = longueur de limbe maximale a priori). Noyau gaussien de crête 1, σ = max(0,15 m ; 0,25 d) (comme le modèle F, § 10.2 de `modele_feuille.md`). Poids « un » : V(c) = nombre de feuilles qui désignent c. Variante « lc » : poids ℓ × cohérence moyenne. Témoin d'échelle fixe : mêmes segments, d = 0,85 m et σ = 0,21 m pour tous.
- **Aucun paramètre réglé** : tous viennent de B′, du modèle F ou des a priori de plant-geometry.

**Critère synthétique** (même rendu et mêmes scènes qu'E-018s essai 2, graine 20261110, `e018_synthetique.py` importé sans modification) :
- feuilles retrouvées ≥ 50 % sur « isolés » : un segment dont le centre est à moins de 0,15 m de la nervure vraie (portion limbe, courbure comprise) et dont l'axe fait moins de 15° avec la tangente au point le plus proche ;
- rappel des centres au budget (N = nombre de plants, maxima NMS 1 m, appariement 1 m) ≥ 0,80 sur « isolés », pour F′ poids « un ».
- Les deux doivent passer. Sinon F′ est déclaré en échec synthétique et E-019 n'est pas lancé sur le réel. Un seul essai est prévu ; tout essai supplémentaire serait rapporté avec le premier.
- Rapportés : jointifs, variante « lc », témoin d'échelle fixe, B′ sur les mêmes scènes, ℓ/L.

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/convergence-engineer/e019_synthetique.py`.

### 11.1 Résultat d'E-019s [M synthétique] (après calcul ; le § 11.0 n'a pas été modifié)

Sorties : `out/comptage_math/convergence-engineer/E-019/synthetique.json`, journal `E-019s_journal.txt`. Scènes identiques à E-018s essai 2 (B′ y refait 0,98 / 0,99, comme en E-018s).

| | Isolés | Jointifs |
| --- | --- | --- |
| Feuilles retrouvées (< 0,15 m, < 15°) | **0,531** (1 025 feuilles) | 0,491 |
| Part des segments posés sur une feuille | 0,52 | 0,65 |
| ℓ/L médian [q25 ; q75] | 0,78 [0,68 ; 0,88] | 0,69 [0,46 ; 0,82] |
| Rappel au budget, F′ poids « un » (C1) | **0,757** | 0,800 |
| F′ poids « lc » | 0,743 | 0,798 |
| Témoin d'échelle fixe (d 0,85 m, σ 0,21 m) | 0,854 | 0,838 |
| B′ | 0,979 | 0,985 |

- Identifiabilité : passe (0,531 ≥ 0,50). Centres : **échec** (0,757 < 0,80).
- **Verdict : F′ échoue au contrôle synthétique. E-019 n'est pas pré-enregistré ni lancé sur le réel** (aucune image réelle ouverte).
- Diagnostic après coup (`e019_diagnostic.py`, 2 scènes isolées, sans effet sur le verdict ; `E-019/diagnostic_synthetique.json`) : 65 % des segments ont un axe à moins de 15° de la direction du centre le plus proche (écart médian 9°) ; pour ceux-là, la distance prédite d(ℓ) est de 0,65 m en médiane contre 0,91 m vraie. ℓ sous-estime L (les bouts du limbe, effilés, ne sont pas cohérents ; les feuilles recouvertes sont coupées) et l'écart base–centre dépasse δ. **L'échelle mesurée par feuille est donc biaisée vers le bas ; le témoin à distance fixe fait mieux (0,854) que la distance adaptative.** L'orientation par segment est bonne : ce qui manque, c'est la longueur.
- Pistes, non pré-enregistrées : d = a·ℓ + b étalonné en synthétique (mais ℓ dépend du recouvrement, donc de la densité, et ne transfère pas tel quel) ; ou ne garder du segment que sa droite d'appui et voter sur un intervalle [ℓ/2, ℓ/2 + L_max] (ce qui revient à B′ par segment).

---

## 12. E-022 : échelle de dérivation σ_g du vote B′ (7 novembre 2026)

Pré-enregistrement : `docs/experiment-log.md`, entrée E-022 (écrite avant tout calcul), et `docs/recherche/notes/error-analyst.md`, E-021 § 3. Rien n'a été modifié après le début des calculs.

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/convergence-engineer/e022_sigma_g.py` (350 s, 4 processus).
Sorties : `out/comptage_math/convergence-engineer/E-022/` (`bilan_E-022_A.json`, `etapeA_*.csv`, `E-022_A.log`).

Données : bv_session_a sans pépinière (critère) et dev_transfert (contrôle), assertions contre bv_b_*, val_*, `cg/`, D-013. Groupes et milieux repris des CSV d'E-021 (lecture seule) ; définition de l'alignement recopiée d'`e021_ecart_v5.py`.

`votes.py` : `champ(..., sigma_g_m=0.04)` et `carte_votes_multi(..., sigmas_g=None)` ajoutés ; valeurs par défaut = B′ figé. Cartes z (simple et multi) identiques au bit près avant et après l'ajout sur 3 tuiles de bv_session_a.

### 12.1 Étape A [M, E-022]

Contrôle de départ : à 4 cm, 340/857 = 39,7 % et 85,6 %, A_in identique à E-021 (écart max 1e-16), T_in = 0,1182 comme E-021. **Conforme.**

| σ_g (σ_t) | T_in | G_oub hors bord ≥ T_in (n = 857) | G_deux (n = 2 742) | AUC oub./deux | dev_transfert G_oub / G_deux |
| --- | --- | --- | --- | --- | --- |
| 4 (10) cm | 0,118 | 39,7 % (340) | 85,6 % | 0,151 | 41,8 % / 91,5 % |
| 6 (15) cm | 0,134 | 50,4 % (432) | 89,8 % | 0,163 | 39,1 % / 89,4 % |
| 8 (20) cm | 0,147 | **54,96 % (471)** | 89,8 % | 0,181 | 33,3 % / 86,3 % |
| 12 (30) cm | 0,175 | 53,8 % (461) | 86,0 % | 0,218 | 24,8 % / 75,2 % |

**Critère A : échoue.** Aucune échelle n'atteint 55 % ; le maximum, 8 cm, est à une mère du seuil (472/857 requis). La condition G_deux est remplie partout. Selon la règle écrite : arrêt, l'étape B n'est pas lancée, et l'hypothèse « nervures » est déclarée réfutée au sens du critère.

Lecture :
- [M] Sur bv_session_a, l'alignement des oubliées monte avec σ_g (médiane 0,077 → 0,165 à 8 cm), mais celui des trouvées aussi (0,29 → 0,41) : l'écart entre groupes ne se referme pas, l'AUC s'approche seulement de 0,5 (0,15 → 0,22).
- [M] Sur dev_transfert, l'effet est inverse : la part des oubliées avec signal baisse dès 6 cm (41,8 → 39,1 → 33,3 → 24,8 %). Même si le seuil de 55 % avait été franchi d'une mère sur bv_session_a, l'effet ne se transfère pas.
- [H] Le gain sur bv_session_a ressemble à un effet de lissage commun aux deux groupes plutôt qu'à une correction spécifique des grands limbes.

---

## 13. E-023 : symétrie radiale de la couronne (FRST) (7 novembre 2026)

Pré-enregistrement : `docs/experiment-log.md`, entrée E-023 (écrite avant tout calcul). Ce qui suit précise la mise en œuvre là où l'entrée est muette ; **écrit avant tout calcul, y compris le contrôle synthétique**. Les grilles et les seuils des critères A et B ne sont pas modifiés.

Code : `comptage_math/symetrie.py` (FRST) ; script `out/comptage_math/convergence-engineer/e023_frst.py` ; sorties `out/comptage_math/convergence-engineer/E-023/`.

### 13.0 Précisions de mise en œuvre (avant calcul)

- **FRST** [S] Loy et Zelinsky 2003 :
  - luminance `orientation.luminance` (même canal que `votes.champ`), lissée par une gaussienne σ_s / res px ;
  - gradient de Sobel 3 × 3 (÷ 8) ; votent les pixels valides (somme RGB > 15) après érosion du masque valide de ⌈3 σ_s/res⌉ + 1 px (les bords noirs du disque ne votent pas) ; pas de seuil β sur |g| (l'entrée n'en prévoit pas) ;
  - p± = p ± round(n ĝ), n en px = n_m / res ; O_n(p±) ± 1, M_n(p±) ± |g| (accumulation par `np.bincount`) ; Õ_n écrêté à ± k_n, k_n = 8 (valeur de l'article pour n > 1 px) ;
  - F_n = (M_n / k_n) · (|Õ_n| / k_n)^α ; A_n gaussienne d'écart-type 0,25 n (px) ; S = moyenne des F_n ∗ A_n sur les 4 rayons ;
  - polarité « positive » : votes en p+ seulement (centre plus clair), S ≥ 0 ; « négative » : votes en p− seulement, signe retourné pour que S ≥ 0 au centre sombre ; « les deux » : accumulation signée de l'article (p+ : +, p− : −), score |S| ;
  - z robuste par tuile : médiane et MAD de S sur le masque végétation de `votes.champ` (défauts de B′) ∩ valide, appliquées à toute la tuile.
- **Échantillonnage** : valeur de z_FRST au pixel entier du point (comme `e008_votes.echantillon` et z0 d'E-021).
- **Groupes** (CSV d'E-021, lecture seule) : « signal absent » = `groupe_cmp == G_oub`, `d_bord_m ≥ 1`, `cas == "signal radial absent"` (477 sur bv_session_a, 598 sur dev_transfert) ; trouvées = `G_deux`, `d_bord_m ≥ 1` (2 742 ; 4 725) ; milieux = toutes les lignes de `nul_milieux_*.csv`. T = P90 de z_FRST sur les milieux du même jeu.
- **Égalité au critère A** (parts égales à l'unité près) : σ_s 8 avant 16, puis α = 2 avant 1, puis polarité « les deux », positive, négative.
- **Étape B** (si A passe) :
  - B′ figé = `votes.carte_votes_image(r_max 1,6, p 1)`, z robuste, NMS 1,0 m (`e008_votes.detecter`) ; contrôle : mêmes détections que `E-010/detections/vote_e010.csv` sur bv_session_a ;
  - fusion z = zrob(z_vote + w z_FRST) sur les pixels valides, mêmes maxima et NMS ; seuil de chaque carte = max du F1 cumulé sur bv_session_a (200 quantiles, règle d'E-008) ;
  - choix de w ∈ {0,5 ; 1,0} : meilleur F1 cumulé ; à 0,001 près (D-008), w = 0,5 ;
  - gain apparié contre B′ (chacun à son seuil) ; IC 95 % par **blocs de 7 photos** : colonne `unite` (photo d'origine) triée par ordre alphabétique, blocs consécutifs de 7 (dernier bloc incomplet), 2 000 tirages, graine 2026. L'IC par photo (unité d'E-012) est rapporté à côté, sans effet sur la décision ;
  - oubli des mères de plus de 2,8 m (taille × cm/px), appariement à 1 m, fonction `oubli_taille` d'E-012 ; « baisse d'au moins 5 points » = oubli(B′) − oubli(fusion) ≥ 0,05 ;
  - dev_transfert : `scripts/math_evaluer.py --roles dev_transfert --seuil-fixe` (lecture seule), pour B′ et pour la fusion ; perte = F1(B′) − F1(fusion) ≤ 0,005 ;
  - fenêtre d'égalité 0,001 (D-008) : le gain est déclaré atteint s'il est ≥ 0,010 − 0,001 ; idem pour les autres seuils (5 points − 0,001 ; perte ≤ 0,005 + 0,001) ;
  - un gain < 0,02 est déclaré ambigu.

### 13.1 Contrôle synthétique [M, E-023s] (écrit après le contrôle, avant l'étape A)

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/convergence-engineer/e023_synthetique.py` ; sortie `E-023/controle_synthetique.json`. Critère écrit dans l'en-tête du script avant de le lancer : maximum global de S (polarité attendue et « deux ») à moins de 0,15 m du centre, pour les 12 configurations ; 5 cm/px, bruit σ 5, graine 2026.

- Disque clair de 1 m (polarités pos et deux) et disque sombre (neg et deux) : maximum à 0,011 m du centre dans les 8 cas attendus sur chaque scène. Les polarités contraires ne répondent pas au centre (maximum à 1,6–1,8 m). **Passe.**
- Étoile de 8 bandes claires radiales (r 1,5 m) : maximum global à 1,16–1,24 m du centre dans toutes les configurations. **Échoue.** Au centre, S vaut 0,50 à 1,0 fois le maximum (pos : 91e–96e centile de la carte ; deux, α 2 : égal au maximum, ex æquo avec des pics excentrés). [H] Les bords des bandes radiales ont un gradient tangentiel : leurs votes p ± n ĝ tombent à √(r² + n²) du centre et ne convergent pas ; seule l'enveloppe extérieure vote au centre, et seulement au rayon n ≈ 1,5 m. Ce n'est pas un défaut du code (les disques passent) mais une propriété de la FRST : elle capte le **contour** d'un objet compact, pas la structure en rayons d'une étoile.
- Conséquence : l'étape A est lancée comme pré-enregistré (la mission demandait un disque *ou* une étoile) ; l'échec sur l'étoile est un écart signalé et une prédiction [H] : la FRST ne répondra aux couronnes que si leur enveloppe se détache du fond.

### 13.2 Étape A [M, E-023] (après calcul ; § 13.0 non modifié)

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/convergence-engineer/e023_frst.py` (396 s, 4 processus). Sorties : `E-023/bilan_E-023.json`, `etapeA_*.csv`, `critere_A.csv`, `planche_signal_absent.png`, `E-023.log`. Vérification ponctuelle : valeurs échantillonnées de la 1re tuile identiques à un recalcul isolé.

Part au-dessus de T = P90 des milieux (« absent » : n = 477 bv_session_a, 598 dev_transfert ; trouvées : 2 742 et 4 725) :

| Config. | absent bv_a | trouvées bv_a | absent dev | trouvées dev |
| --- | --- | --- | --- | --- |
| s8 deux α2 | 4,0 % | 1,4 % | 7,5 % | 1,8 % |
| s8 pos α2 | 3,1 % | 0,8 % | 7,5 % | 1,4 % |
| s8 neg α2 | 2,1 % | 0,3 % | 4,9 % | 0,6 % |
| s8 deux α1 | 4,6 % | 1,5 % | 6,7 % | 1,8 % |
| s8 pos α1 | 4,0 % | 0,6 % | 7,0 % | 1,3 % |
| s8 neg α1 | 1,7 % | 0,2 % | 4,9 % | 0,4 % |
| s16 deux α2 | 5,2 % | 1,2 % | 6,7 % | 2,8 % |
| s16 pos α2 | 7,5 % | 1,5 % | 7,9 % | 3,4 % |
| s16 neg α2 | 2,1 % | 0,5 % | 4,4 % | 1,6 % |
| s16 deux α1 | 5,0 % | 1,2 % | 6,4 % | 2,8 % |
| s16 pos α1 | 8,6 % | 1,4 % | 10,0 % | 3,5 % |
| s16 neg α1 | 1,5 % | 0,3 % | 3,9 % | 1,3 % |

**Critère A : échoue.** Aucune configuration n'approche les 40 % (max 8,6 %) ni les 60 % pour les trouvées (max 1,5 %). Selon la règle : arrêt, étape B non lancée, FRST réfutée comme complément du vote au sens du critère.

Lecture :
- [M] Les parts sont **sous** le taux de base de 10 % des milieux, partout : la FRST à 0,6–1,5 m répond moins aux centres de mères qu'aux milieux de paires. Médianes de z_FRST : trouvées −0,08 à −0,68, milieux +0,29 à +0,71 (les deux jeux). Le signe est inversé, pas seulement faible.
- [O] Planche (`planche_signal_absent.png`, s16 pos α1, à titre d'illustration) : les pics de la FRST tombent sur des limbes clairs isolés et sur des trouées, pas au centre des couronnes.
- [H] Cohérent avec le contrôle synthétique (§ 13.1) : une couronne vue du dessus est une étoile de limbes à bords tangentiels ; sans enveloppe détachée du fond, la FRST ne converge pas au centre et répond aux objets compacts plus petits (limbes, trous de canopée).
