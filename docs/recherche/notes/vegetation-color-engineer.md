# Notes de vegetation-color-engineer (équipe VISION)

## 1. E-013 — Filtre couleur et texture sur les candidats du vote B′ : pré-enregistrement

Écrit le 7 novembre 2026, **avant tout calcul de F1, d'AUC ou de descripteur** sur les candidats. Je n'ai lu ni les
colonnes `lum`, `exg`, `coh` des fichiers d'error-analyst (E-011) pour choisir, ni aucune planche chiffrée : seulement
les pourcentages de classes cités dans la demande.

### 1.1 Question

Un descripteur explicite de couleur ou de texture, calculé autour de chaque candidat du vote B′ (configuration figée
d'E-008/E-010), sépare-t-il les vraies détections des fausses (autre végétal, sol) ? Combiné au z du vote, améliore-t-il
le F1 sur bv_session_a sans pépinière ?

### 1.2 Données

- Candidats : `out/comptage_math/convergence-engineer/E-010/detections/vote_e010_attributs.csv` (z ≥ 0,5), restreints à
  la région d'évaluation (`math_evaluer.dans_region`).
- Images : bv_session_a (rôle dev_reglage, sans pépinière, liste `math_evaluer.charger_liste`) pour **tout choix** ;
  dev_transfert (corte, lasuiza, vols_100_022x) **rapporté seulement**.
- Assertions dans le script : aucune image de bv_b_train, bv_b_val (val_iter, val_scellee), des groupes interdits
  (`math_evaluer.INTERDITS`), de `cg/`. Aucun négatif palmier ou cocotier n'est lu.

### 1.3 Masque propre (`comptage_math/couleur.py`)

Tout en Lab (OpenCV, flottants 0–1 : L* 0–100) et ExG normalisé, lissés par une gaussienne de 4 cm.
- **Ombre** : L* < 0,55 × médiane de L* de la tuile (pixels valides). Relatif à la tuile, donc stable entre vols.
- **Végétation** : (ExG normalisé > 0,05 **ou** a* < −4) **et** non ombre. Le terme a* < −4 récupère les limbes pâles,
  presque blancs [O image-analyst, Flora Pluas, Nestor Macias], dont l'ExG est faible mais qui restent du côté vert de
  l'axe a*. Le sol nu est du côté a* ≥ 0.
- Mesure indirecte (fixée ici, sans seuil de réussite) : part des mères annotées de bv_session_a dont le disque de 0,3 m
  contient au moins 50 % de masque, pour le masque provisoire (ExG > 0,05, Y > 0,18) et le masque propre ; part de mères
  « perdues à l'ombre » (disque de 0,3 m à plus de 50 % d'ombre).

### 1.4 Descripteurs (3 au plus), tous normalisés par tuile

Résolution de travail : celle de la tuile (`cm_par_px`). Moyennes sur un disque (filtre de convolution normalisé).
- **d1 — fraction de limbe large**, disque de rayon 1,5 m. Variance locale de luminance s(x) = écart-type de Y dans une
  gaussienne de 6 cm après retrait d'un fond gaussien de 6 cm. Pixel « limbe large » = végétation propre et
  s(x) < médiane de s sur la végétation de la tuile. d1 = part des pixels du disque qui sont limbe large.
  Sens attendu : vrai > faux (le limbe du bananier est large et lisse, l'herbe et les buissons sont granuleux).
- **d2 — teinte relative**, disque de rayon 1,0 m. Teinte de Lab : h = atan2(b*, a*) en degrés, moyennée sur les
  pixels de végétation propre du disque, moins la médiane de h sur la végétation de la tuile. Sens attendu : vrai < faux
  [H : le limbe du bananier est plus jaune-vert et plus pâle, h plus proche de 90°, que l'herbe et les buissons plus
  bleu-vert, h plus grand].
- **d3 — fraction non végétale**, disque de rayon 1,0 m : part des pixels ni végétation propre ni ombre (sol, débris).
  Sens attendu : vrai < faux (vise la classe « sol »).

Avant la combinaison, chaque descripteur est orienté selon le sens attendu ci-dessus (signe fixé ici, pas mesuré) et
réduit : d̃ = (d − médiane) / (1,4826 × MAD), médiane et MAD calculées sur **tous les candidats de bv_session_a**
(sans étiquette).

### 1.5 Combinaison avec le z du vote (2 paramètres) et sélection

- Score combiné : **s = z + w · d̃_k**, k ∈ {1, 2, 3}, w ∈ {0 ; 0,25 ; 0,5 ; 1 ; 1,5 ; 2}. Paramètres : k et w.
  w = 0 est le vote seul (témoin de la même procédure).
- Pour chaque (k, w) : seuil sur s choisi comme dans `math_evaluer.evaluer` (grille de 200 quantiles des scores des
  candidats de bv_session_a, meilleur F1 cumulé), puis NMS inchangée (les candidats sont déjà les maxima du vote).
- **Sélection** : meilleur F1 cumulé sur bv_session_a. En cas d'égalité à 0,001 près, le plus petit w.
- dev_transfert : évalué au seuil et à la configuration figés, rapporté sans servir au choix.

### 1.6 Critère

- **Gain retenu** si la différence appariée F1(retenu) − F1(vote seul, w = 0) sur bv_session_a a un IC à 95 % qui exclut
  0 : bootstrap de 2 000 tirages par unité (photo ou tuile d'origine), graine 2026, mêmes tirages pour les deux.
  Le choix (k, w) étant fait sur ces mêmes données, le gain est optimiste ; dev_transfert sert de contrôle de transfert,
  sans décider.
- **AUC** (Mann-Whitney) de chaque descripteur orienté : vrais positifs contre faux positifs du vote seul au seuil
  E-010 (z ≥ 2,238), et contre les seules classes « autre végétal » et « sol » d'E-011 (jointure par image, x, y).
  Un descripteur est dit **séparateur** si AUC ≥ 0,65 contre « autre végétal » ou contre « sol ».

### 1.7 Prédictions chiffrées (avant calcul)

| Mesure | Prédiction |
| --- | --- |
| AUC d1, VP contre FP (tous) | 0,58 – 0,68 |
| AUC d1, VP contre autre végétal | 0,62 – 0,72 |
| AUC d2, VP contre autre végétal | 0,55 – 0,65 |
| AUC d3, VP contre sol | 0,70 – 0,85 |
| Configuration retenue | k = 1, w ∈ [0,5 ; 1,5] |
| Gain F1 bv_session_a | +0,010 à +0,030, IC excluant 0 |
| Gain F1 dev_transfert (rapporté) | +0,010 à +0,050 (plus d'autre végétal et de sol) |
| Masque : mères couvertes, propre contre provisoire | propre ≥ provisoire + 2 points |
| Temps des descripteurs | < 1 s par hectare sur 8 cœurs |

Réfutation : si aucun descripteur n'atteint AUC 0,65 contre l'autre végétal **et** si l'IC du gain contient 0, la
couleur et la texture locales ne séparent pas les faux du vote ; je ne cherche pas d'autres seuils sur ces images.

## 2. E-013 — Résultats (7 novembre 2026)

Commandes :
- `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/vegetation-color-engineer/e013_couleur.py`
  (356 s, 8 cœurs) → `out/comptage_math/vegetation-color-engineer/E-013/bilan_E-013.json`, `grille_bv_session_a.csv`,
  `candidats_au_seuil_e010.csv`, `detections_e013_choix.csv`, `transfert/` (évaluateur officiel, seuil figé).
- `.../e013_complement.py` → `E-013/complement_auc.json`, `E-013/planche_masques.png`.

Contrôle de reproduction : vote seul au seuil re-choisi = 2,2382 (E-010 : 2,2382), F1 0,6368, 5 563 VP et 3 261 FP,
identiques à E-010 et E-011.

**Écart au pré-enregistrement (libellé, pas un choix).** La classe d'E-011 s'appelle « sol ou débris », pas « sol » : le
script principal a rendu des AUC vides pour cette classe. Elles sont calculées dans `e013_complement.py`, sans rien
changer à la sélection.

### 2.1 AUC [M] (descripteur orienté selon le sens pré-enregistré ; VP contre FP du vote au seuil E-010)

| | d1 limbe large | d2 teinte rel. | d3 non végétal | z du vote |
| --- | --- | --- | --- | --- |
| bv_session_a, tous FP | 0,595 | 0,441 | 0,597 | 0,713 |
| bv_session_a, autre végétal | 0,568 | 0,460 | 0,584 | 0,728 |
| bv_session_a, sol ou débris | 0,931 | 0,090 | 0,999 | 0,799 |
| dev_transfert, tous FP | 0,587 | 0,374 | 0,687 | 0,754 |
| dev_transfert, autre végétal | 0,539 | 0,383 | 0,659 | 0,784 |
| dev_transfert, sol ou débris | 0,883 | 0,248 | 0,970 | 0,682 |

- d2 : **sens réfuté**. Les vrais ont une teinte plus grande (plus bleu-vert) que les faux, pas plus petite. Au signe
  inverse (exploratoire, sans décision) : 0,559 sur bv_session_a, 0,626 sur dev_transfert.
- d3 contre « sol ou débris » : AUC presque 1, mais en partie **circulaire** : la classe d'E-011 est définie par une
  fraction de végétation proche du point, quantité voisine de d3. À ne pas citer comme preuve indépendante.
- Contre l'autre végétal, aucun descripteur n'atteint 0,65 sur bv_session_a (meilleur : d3, 0,584). Sur dev_transfert,
  d3 atteint 0,659 (rapporté seulement).
- [O] `planche_masques.png` : sur lasuiza_0185_0, l'herbe pâle du sol est classée « limbe large » : à 5 cm/px, l'herbe
  rase est aussi lisse qu'un limbe. C'est l'explication la plus simple de l'échec de d1.

### 2.2 Combinaison [M]

Grille (F1 sur bv_session_a) : w = 0 : 0,6368 ; d1 : 0,6357 → 0,594 (décroît avec w) ; d2 : 0,586 → 0,560 ;
d3 : **0,6515** (w = 0,25), 0,629, 0,616, 0,614, 0,613. Aucun seuil au bord de la grille.

**Retenu : k = 3 (fraction non végétale), w = 0,25, seuil s ≥ 1,8626.**

| | Vote seul | Vote + 0,25·d̃3 | Gain apparié [IC 95 %] |
| --- | --- | --- | --- |
| bv_session_a F1 (P / R) | 0,6368 (0,630 / 0,643) | **0,6515** (0,620 / 0,686), IC [0,635 ; 0,667] | **+0,0147 [+0,0072 ; +0,0225]** |
| dev_transfert F1 (P / R), rapporté | 0,5455 (0,442 / 0,712) | **0,5703** (0,468 / 0,730), IC [0,541 ; 0,596] | +0,0247 [+0,0156 ; +0,0336] |
| Double comptage bv_session_a | 0,051 | 0,064 | |
| Double comptage dev_transfert | 0,042 | 0,045 | |
| Erreur de comptage relative bv_session_a | +2,0 % | +10,7 % | |

- **Critère rempli** : l'IC du gain apparié exclut 0 sur bv_session_a. Réserve : (k, w) choisis sur ces mêmes données
  (17 configurations), gain optimiste. dev_transfert, non utilisé pour choisir, confirme le sens (+0,025, IC > 0) ; par
  groupe : corte 0,667 → 0,679, lasuiza 0,530 → 0,548, vols_100_022x 0,548 → 0,580.
- Mécanisme : d̃3 a une MAD très faible (0,020) ; avec w = 0,25 le terme agit comme un **rejet quasi dur** des candidats
  sur sol, ce qui permet de baisser le seuil de z (2,24 → 1,86) et de gagner du rappel (+4,3 points) pour une perte de
  précision d'un point. Le gain vient donc surtout du rappel ; le double comptage et la surestimation du nombre de
  plants augmentent.
- Évaluateur officiel (`scripts/math_evaluer.py --seuil-fixe 1.8626 --roles dev_transfert`) : F1 0,570 [0,541 ; 0,596],
  identique au calcul interne.

### 2.3 Masque propre [M]

| | bv_session_a | dev_transfert |
| --- | --- | --- |
| Mères couvertes (disque 0,3 m ≥ 50 %), provisoire | 0,9992 | 0,9929 |
| Mères couvertes, propre | 0,9954 | 0,9960 |
| Mères perdues à l'ombre | 0,34 % | 0,22 % |
| Fraction de végétation de la tuile, provisoire / propre | 0,851 / 0,780 | 0,772 / 0,759 |
| Fraction d'ombre | 9,7 % | 4,3 % (corte 5,0 ; lasuiza 2,7 ; vols 6,4) |

Le masque propre retire 7 points de surface sur bv_session_a (surtout ombres entre couronnes) en gardant 99,5 % des
mères ; il gagne 0,3 point de mères sur dev_transfert. Prédiction « +2 points » réfutée (effet plafond : le provisoire
couvre déjà 99 %). Son effet sur le vote lui-même n'est pas mesuré (`votes.py` non modifié).

### 2.4 Temps [M]

Cartes d1–d3 : 9,9 s par hectare sur un cœur, **1,24 s/ha sur 8 cœurs** (44,6 ha). Prédiction < 1 s/ha réfutée ; le
disque de 1,5 m de d1, inutile, en est la plus grosse part. d3 seul (disque de 1 m) coûterait moins.

### 2.5 Bilan des prédictions

| Prédiction | Résultat |
| --- | --- |
| AUC d1 tous FP 0,58–0,68 | 0,595 : oui |
| AUC d1 autre végétal 0,62–0,72 | 0,568 : non |
| AUC d2 autre végétal 0,55–0,65 | 0,460 (sens inverse) : non |
| AUC d3 sol 0,70–0,85 | 0,999 (circulaire en partie) : au-dessus |
| Retenu k = 1, w 0,5–1,5 | k = 3, w = 0,25 : non |
| Gain bv_session_a +0,010 à +0,030, IC > 0 | +0,0147 [+0,007 ; +0,023] : oui |
| Gain dev_transfert +0,010 à +0,050 | +0,0247 : oui |
| Masque propre ≥ provisoire + 2 points | non (plafond) |
| Temps < 1 s/ha | 1,24 s/ha : non |

**Conclusion.** La couleur et la texture locales **ne séparent pas l'autre végétal** des bananiers à cette résolution
(AUC ≤ 0,58 sur bv_session_a, hypothèse réfutée pour d1 et d2 ; je ne cherche pas d'autres seuils sur ces images). La
**fraction de sol** autour du candidat (d3) apporte un gain de F1 petit mais net : +0,015 sur bv_session_a, +0,025 sur
dev_transfert, au prix de +1,3 point de double comptage.
