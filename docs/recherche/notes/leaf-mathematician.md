# Notes de travail — leaf-mathematician

Rédacteur unique : leaf-mathematician. Étiquettes [O] [S] [H] [M] selon `CLAUDE.md`, règle 2.

## 2026-11-07 — Mission 3 : deux modèles de feuille et de plant

### Observations préalables sur le développement [O]

Images ouvertes (toutes du développement, `docs/research-brief.md` § 2.2) : `data/drone/jeunes_bananiers/dji_0546.jpg`, `dji_0548.jpg` (découpes autour de mères annotées), centre de `data/drone/reforestree/wwf_ecuador/RGB Orthomosaics/Flora Pluas RGB.tif`. Aucune image de test ou d'exclusion ouverte. Les découpes de travail sont restées dans le scratchpad de la session, hors dépôt.

- [O] dji_0546 : 168 points (163 `mere`, 5 `rejet`) ; dji_0548 : 196 points (191 `mere`, 5 `rejet`). Distance médiane au plus proche voisin entre mères : 205 px et 195 px, soit 2,1 à 2,3 m à 1,1 cm/px.
- [O] dji_0546, dji_0548 (jeunes plants) : 4 à 8 limbes visibles par plant, de forme oblongue, environ 1 à 2 m de long et 0,4 à 0,7 m de large (lecture à l'œil sur les découpes, ±30 %). Nervure centrale visible comme une ligne claire. Les limbes ne touchent pas le centre : la zone du point annoté est souvent un petit vide (sol, ombre, pétioles) de 0,1 à 0,4 m. Une jeune feuille vert clair, enroulée ou à demi ouverte, est souvent à moins de 0,3 m du centre, mais pas centrée exactement sur le point.
- [O] dji_0546, dji_0548 : des feuilles sèches brunes pendent au pied ou gisent au sol, entre les plants plutôt qu'en couronne régulière.
- [O] dji_0546, dji_0548 : l'axe d'un limbe prolongé passe près du centre, mais pas exactement : écart latéral de quelques dizaines de centimètres (pétiole courbe, limbe tombant).
- [O] Flora Pluas (centre de l'orthomosaïque, résolution du fichier 8,7e-8 degré, soit environ 1 cm/px à cette latitude) : canopée jointive, limbes déchirés en lanières le long des nervures secondaires, déchirures presque perpendiculaires à la nervure centrale, espacées de quelques centimètres à une vingtaine de centimètres. C'est la texture de l'indice « stries » sous sa forme la plus nette.

### Choix des deux modèles

- **Modèle A, « étoile de gaussiennes anisotropes »** : information basse fréquence (amplitude de l'indice de végétation), estimateur par filtres adaptés ancrés au centre. Formulation compatible avec les indices « gaussiennes », « formes », « orientations » (H1, H2, H4 implicite).
- **Modèle B, « bandes nervurées striées et profil radial de couleur »** : information haute fréquence (phase de la texture des stries, nervure) et couleur, estimateur par vraisemblance d'un champ d'orientation (von Mises) qui se réduit à une convolution complexe. Formulation compatible avec les indices « stries », « orientations », « couleurs » (H3, H4, H5).

Raison du découpage : A et B n'utilisent pas la même information (amplitude grossière contre orientation fine) et ne partagent pas l'estimateur (corrélation de gabarits contre vote d'orientation). Leurs échecs attendus diffèrent, donc des expériences peuvent les départager.

### Critère du contrôle synthétique, fixé avant le lancement

Rédigé avant la première exécution de `out/comptage_math/leaf-mathematician/controle_synthetique.py`.

Scènes : 24 m × 24 m, plants sur une grille jittée. Deux configurations :
- « isolés » : espacement 4 m, limbes de 0,9 à 1,6 m, aucun recouvrement entre plants ;
- « jointifs » : espacement 2,3 m, limbes de 1,0 à 2,0 m, recouvrements.

Rendus : par le modèle A et par le modèle B, à 1, 2, 3 et 5 cm/px, bruit gaussien σ = 0,04 par canal, sol texturé et touffes d'herbe sans stries, gain global tiré dans [0,8 ; 1,2]. Graine fixe.

Règle de détection, identique pour tous les cas : maxima locaux avec suppression des non-maxima de rayon 0,8 m, score ≥ 0,25 × score maximal de la scène. Appariement glouton à 0,5 m.

Critère de réussite, configuration « isolés » seulement, chaque détecteur sur les scènes rendues par son propre modèle :
- A sur scènes A, à 1, 2, 3 et 5 cm/px : rappel ≥ 0,90 et précision ≥ 0,90 ;
- B sur scènes B, à 1, 2 et 3 cm/px : rappel ≥ 0,90 et précision ≥ 0,90. À 5 cm/px, B est déclaré non identifiable d'avance (stries sous-échantillonnées) : le résultat est rapporté sans critère.

Contrôles, mêmes scènes « isolés » à 2 cm/px :
- centres au hasard : le score médian aux vrais centres dépasse le 95e centile des scores en des points de végétation tirés à plus de 1 m de tout centre ;
- orientations mélangées (B) : on permute les orientations entre pixels de végétation ; le rappel tombe sous 0,30 ;
- erreur d'échelle (A et B) : paramètres du détecteur multipliés par 0,8 et 1,2 ; prédiction : rappel ≥ 0,85 dans les deux cas.

Rapportés sans critère : résultats croisés (A sur scènes B, B sur scènes A), configuration « jointifs », signe de la vraisemblance de B à échelle fine et grossière (prédiction P-B3 de `docs/recherche/modele_feuille.md`), temps de calcul extrapolé à l'hectare à 2 cm/px.

Un échec se rapporte tel quel, sans retoucher le modèle sur ces mêmes scènes.

### Correction de rendu avant le lancement (aucune métrique regardée)

Un essai de fumée (2 plants, graine 1, scratchpad, sans calcul de rappel ni de précision) a montré un défaut de **rendu** : le sol texturé n'était appliqué que là où v valait exactement 0, d'où des halos autour des plants A. Corrigé en composant les plants sur un fond (`fond`, `bruit` dans `comptage_math/feuille.py`). Les détecteurs n'ont pas été touchés.

### Résultats du contrôle (E-synth-LM-01, identifiant à attribuer)

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/leaf-mathematician/controle_synthetique.py` ; sorties `out/comptage_math/leaf-mathematician/resultats.{md,json}` et vignettes.

- [M synthétique] A sur rendus A, « isolés » : rappel 1,00 / 1,00 / 1,00 / 0,94 et précision 0,26 / 0,22 / 0,24 / 0,23 à 1, 2, 3 et 5 cm/px ; erreur médiane 0,16 à 0,21 m. **Critère manqué (précision).**
- [M synthétique] B sur rendus B : rappel 0 à toutes les résolutions. **Critère manqué.** Λ négatif aux centres.
- [M synthétique] Contrôles : hasard A réussi (2,35 > 1,75) ; hasard B échoué ; échelle 0,8 et 1,2 : A rappel 1,00 et 0,97, B 0 ; orientations mélangées B : rappel 0,25 (sans portée).
- [M synthétique] Temps : A 2,4 s/ha, B 4,9 s/ha à 2 cm/px.
- [M synthétique] Diagnostic après coup (`diagnostic_signe_B.py`, graine 777) : signe correct sur des stries pures (+466) et des rayons pleins (−309) ; plant complet −242, sans stries −274, sans nervure −123. Dans le rendu B, bords et nervure dominent le tenseur de structure ; P-B3 réfutée en synthétique.

Décision personnelle : aucun réglage sur ces scènes. Les formulations B′ (signe −1), B″ (Gabor sélectif) et A′ (seuil absolu normalisé) sont proposées pour un nouvel essai pré-enregistré sur une nouvelle graine.

## 2026-11-07 — Concertation C-001

Renumérotation communiquée par le chef d'orchestre : mon contrôle synthétique devient **E-002** ; la mesure d'orientation-engineer, E-003 ; sa décomposition synthétique de B, E-004. `bv_b_val` m'est interdit.

Code ajouté à `comptage_math/feuille.py`. Les valeurs par défaut reproduisent le comportement d'E-002 :
- options de rendu `petioles` et `trou_centre` ;
- canal du modèle A (`canal` : `exg` ou `luminance`) ;
- témoin `filtre_A_iso` ;
- règle de seuil `pics_mad` (A′) ;
- lecture au budget `pics_budget`.

### Essai synthétique hors famille (OBJ-C1, OBJ-C2, OBJ-C3), critère écrit avant le lancement

Script `out/comptage_math/leaf-mathematician/controle_hors_famille.py`. Nouvelle graine 20261108, distincte de celle d'E-002. Scènes de 24 m × 24 m à 2 cm/px. Les détecteurs A et A-iso gardent exactement les paramètres d'E-002 (`ParamsA()` par défaut, canal ExG) ; aucun réglage.

Variantes de rendu, toutes faites avec le modèle B (limbes à bords nets, non gaussiens) :
- **v0, origine** : rendu B d'E-002 (cigare, pétioles, centre éclairci), configuration jointive (grille de 2,3 m, décalage 0,25 m, L de 1,0 à 2,0 m).
- **v1** : comme v0, sans cigare, sans pétioles, sans éclaircissement, a_c = 0.
- **v2** : comme v1, avec un vide sombre de 0,1 à 0,4 m au centre.
- **v3** : comme v2, avec L de 1,6 à 2,5 m (hors de la plage du détecteur), grille de 2,4 m et décalage de 0,6 m.

Lectures :
- (i) rappel et précision au budget N_vrais, à 0,5 m et à 1 m ;
- (ii) rappel et précision avec la règle d'E-002 (τ = 0,25 × max) ;
- (iii) contrôle demi-maille : médiane de S aux centres contre 75e centile de S aux milieux des paires de plus proches voisins ;
- (iv) part des fausses détections (règle τ) situées entre 0,9 et 1,4 m du centre le plus proche.

Critères repris des examinateurs :
- **OBJ-C1** : si le rappel au budget à 0,5 m de A chute de plus de 0,2 entre v0 et v2 ou v3, E-002 ne compte pas comme appui à A.
- **OBJ-C2, synthétique seulement et indicatif** : A doit dépasser A-iso au budget en v1, v2 et v3. Sinon, l'anisotropie n'apporte rien même en synthétique.
- **OBJ-C3** : si plus de 30 % des fausses détections sont entre 0,9 et 1,4 m, la suppression des non-maxima de 0,8 m est déclarée inadaptée. A est déclaré non discriminant si la médiane aux centres ne dépasse pas le 75e centile aux milieux.
- Ajouté avant le lancement, rapporté sans critère : la variante A-L (canal luminance, mêmes paramètres).

### Résultats d'E-synth-HF (identifiant à attribuer)

[M synthétique] Au budget N_vrais, rappel à 0,5 m de A : 0,48 (v0), 0,47 (v1), 0,46 (v2), 0,18 (v3). A-iso : 0,05 à 0,11. A-L : 0,18 à 0,33. Verdicts :
- OBJ-C1 : chute de 0,30 > 0,2, donc E-002 ne compte pas comme appui ;
- OBJ-C2 (indicatif) : A > A-iso ;
- OBJ-C3 : 37 à 54 % des fausses détections à demi-maille en v1–v3, et A non discriminant en v3.

Détail : `out/comptage_math/leaf-mathematician/resultats_hors_famille.json` ; tableau dans `docs/recherche/modele_feuille.md` § 7.2.

Réponses aux objections et pré-enregistrement du cycle 1 : `docs/recherche/modele_feuille.md`, sections 7 et 8. Candidate : A′ seul (canal, échelle et rayon réglés sur le développement dense), témoin A-iso.

## 2026-11-07 — Cycle 1, E-006 (grille A′ et témoin A-iso sur le développement dense)

- Amendements 1 et 2 au § 8.3 de `docs/recherche/modele_feuille.md`, écrits avant tout calcul.
  - Le critère de sélection devient le F1 cumulé (D-005).
  - Ce F1 se calcule sur `bv_session_a` sans pépinière seulement : `bv_b_train` est réservé, et aucune détection n'y est calculée.
- Avant l'amendement 2, j'ai vu de `bv_b_train` les quatre premières lignes d'`images_dense.csv` et sa maille médiane (2,24 m). Aucun score, aucune détection.
- Essai de fumée du pipeline : 12 tuiles par groupe, sorties dans le scratchpad. Il a révélé deux défauts techniques, corrigés sans toucher au modèle ni à la grille :
  - encodage de la console (`-I` ignore `PYTHONIOENCODING`) ;
  - lenteur de `maximum_filter` à empreinte circulaire, remplacé par `cv2.dilate` (même opération).
- Le F1 du sous-ensemble de fumée a été vu (environ 0,53 sur 12 tuiles de `bv_session_a`). Il n'a servi à aucun choix : la grille et les règles étaient déjà écrites.
- Lancement : `.venv/Scripts/python.exe -I -u out/comptage_math/leaf-mathematician/cycle1_grille.py` ; journal dans `cycle1_grille.log`.
- Résultat d'E-006 : voir `docs/recherche/modele_feuille.md` § 8.9.
  - Configuration choisie : luminance, s = 1,25, rayon 1,0 m, z0 = 1,095 ; F1 0,541 sur `bv_session_a`.
  - Conditions d'envoi : deux échouent, centres contre milieux sur vols et rotation. A′ n'est donc **pas** envoyé sur `val_iter`.
  - Après coup, j'ai calculé pour l'interprétation les nuls « végétation uniforme » (0,331) et « demi-maille » (0,109) sur `bv_session_a`, à partir des fichiers d'independent-evaluator. Ce calcul n'a servi à aucun choix.

## 2026-11-07 — Cycle 2, E-007 (A″ : polarité)

- Pré-enregistrement : `docs/recherche/modele_feuille.md` § 9, écrit avant le calcul. Il comprend deux termes, l'anisotropie angulaire a₂ (β) et le vide central sombre H (w_trou), ainsi que le point d'entrée w_vote · z_vote, avec w_vote = 0.
- Règle de rotation d'independent-evaluator (`test_final.md` § 4.3) : appliquée par `regle_rotation_e007.py`. Je l'ai consignée au § 9 avant de lire les résultats.
- Essai de fumée sur 6 tuiles par groupe, dans le scratchpad : il n'a servi à aucun choix.
- Résultat : la grille retient β = 0 et w_trou = 0, c'est-à-dire A′ lui-même. Les deux termes relèvent davantage les milieux que les centres. La condition sur vols échoue toujours, et rien n'est envoyé. Détail au § 9.6.
- Nettoyage : sur les 48 CSV d'E-006, 46 sont supprimés (seuls A′ et A-iso sont gardés) ; sur les 6 d'E-007, 5 sont supprimés (seule la configuration retenue est gardée). Tous sont reproductibles par les scripts.

## 2026-11-07 — C-003, modèle F (feuille entière, un vecteur par feuille)

### Contrôle synthétique E-018s, critère écrit avant le lancement

Script `out/comptage_math/leaf-mathematician/e018_synthetique.py`, graine 20261109 (nouvelle). Rendu du modèle B (feuilles à bords nets, non gaussiennes, donc hors de la famille du gabarit F), rendu directement à 5 cm/px, 24 m × 24 m, 4 scènes par configuration :
- « isolés » : grille 4 m, décalage 0,25 m, L 0,9–1,6 m ;
- « jointifs » : grille 2,3 m, décalage 0,25 m, L 1,0–2,0 m, sans cigare, pétioles ni éclaircissement (v1 d'E-synth-HF).

Détecteur : `ParamsF()` par défaut (deux côtés, une voix par feuille, d = r0 + L*/2). Aucun réglage sur ces scènes. Comparé, sans critère, au vote B′ (configuration E-010) sur les mêmes scènes.

Critères :
- **identifiabilité de la feuille (isolés)** : ≥ 50 % des feuilles vraies ont une feuille détectée à moins de 0,3 m du milieu du limbe et à moins de 20° d'axe ;
- **centres (isolés)** : rappel au budget N_vrais à 1 m ≥ 0,80 ;
- si l'un des deux échoue, la formulation F est déclarée en échec synthétique et E-018 n'est pas lancé.
Rapportés sans critère : jointifs (rappel au budget, F contre B′), corrélation de rang L* contre L vrai. La polarité n'est pas testable sur le rendu B (limbe symétrique, sin^0,4) : elle n'est jugée que sur le réel.

### E-018s, 1er essai (graine 20261109) : échec [M synthétique]

- Isolés : feuilles identifiées 1,6 % (critère ≥ 50 %), rappel des centres au budget 0,25 (critère ≥ 0,80). B′ sur les mêmes scènes : 0,99. Jointifs : F 0,57, B′ 0,98. Sortie : `E-018/synthetique_essai1.json`.
- Diagnostic (même scène, sans réglage de paramètre) : dans le rendu B, le limbe est **plus sombre** que le sol en luminance (0,32 contre 0,35) ; Ŷ médian au milieu des limbes = −0,52. Le gabarit « limbe clair entre deux creux sombres » cherche le contraire.
- Correction de la formulation, pas d'un paramètre : `contraste = "abs"`, R* = max_{L,θ} |h_{L,θ} ⋆ Ŷ| (objet allongé clair OU sombre ; en canopée réelle, les creux d'ombre entre limbes sont eux aussi radiaux). La réponse impaire est multipliée par le signe de la réponse paire.
- 2e essai sur **nouvelle graine 20261110**, mêmes critères. S'il échoue aussi, F est déclaré en échec synthétique.

### E-018s, 2e essai (graine 20261110) : échec [M synthétique]

- Isolés : 8,6 % des feuilles retrouvées, rappel au budget 0,38 ; jointifs 0,71 ; B′ 0,98–0,99. Les deux critères échouent : **F déclaré en échec synthétique, E-018 non lancé** (aucune image réelle traitée par F).
- Diagnostic après coup : position sur l'axe souvent juste (53 % à 0,15 m), orientation fausse (médiane 37°), L* × 1,35, détections sur l'herbe. Détail et suite proposée (F′ : feuille = segment cohérent du champ d'orientation) : `modele_feuille.md` § 10.4–10.5.

## 2026-11-07 — D-013, simulateur v2.1

Mission : construire le simulateur v2 (`comptage_math/simulateur.py`, version v2.1), générer 60 scènes, puis passer les tests de fidélité non réservés. Détail, paramètres et SHA-256 : `modele_feuille.md` § 11.

**Déclarations**
- **Données lues** : blocs CAL et VAL_S publics de `stats_photometriques.json`, et `stats_geometriques.json` (CAL pour calibrer, VAL-S pour la fidélité seulement) ; tuiles et références CAL ; références VAL-S, pour les seuls tests G de fidélité.
- **Non ouverts** : `stats_validation_cachees.json`, `out/comptage_math/evaluation/D-013/`, tout score de détection.
- **Aucun détecteur lancé** : je n'ai lancé ni B′, ni T3, ni le vote ExG, ni A′, ni A-iso, ni aucun autre détecteur sur les rendus v2.1 ou sur les scènes de calibration.
- **Calcul de fidélité** : le classifieur figé d'image-analyst est chargé par chemin (`outils_d013.classifieur`). Sa fonction `mesurer`, qui contient le calcul réservé F6–F7, n'est jamais appelée.

**Historique de calibration** (scènes de calibration à graines 5000 + i, comparées à CAL seulement) :
1. Premier rendu : plants trop petits et clairsemés, halos noirs d'occultation, fond en damier.
   - Envergure portée à f_env 1,3–1,7, puis 1,6–2,1 ;
   - occultation adoucie (h0 0,5 → 1,5 m, plancher 0,25) ;
   - collage à recouvrement ½, avec des fenêtres prises dans 3 tuiles sources par scène.
2. Comparaison sur 24 scènes : herbe 0,27 contre 0,17, spectre trop pauvre en hautes fréquences, dispersion entre tuiles trop faible.
   - Texture des limbes ajoutée, isotrope d'abord, puis en côtes perpendiculaires à la nervure ;
   - décalage Lab de la classe feuillage ;
   - allées sans plants ;
   - envergure variable par scène ;
   - feuilles sèches plus nombreuses, avec une dispersion par scène.
3. Géométrie, 3e grille de `calibrer_geometrie.py`, avec le taux de contact ajouté au critère : h = 0,9 m, R = 2,2 m, γ = 0. Les deux premières grilles butaient à max ǀΔgǀ ≈ 0,27–0,30.
4. Gel après la comparaison sur 32 scènes (`derniere_comparaison_cal.json`). Les écarts CAL restants étaient connus avant le gel : contact 0,875 contre 0,925, herbe +0,044, variance du laplacien 22 000 contre 35 200.

**Résultat de fidélité contre VAL-S** (une passe, `fidelite_v2.1.json`) [M] :
- **passent** : F1, F2, F5, G1, G3, G6 ;
- **échouent** : F3 (herbe +0,094), F4 (dispersion du sec et de l'herbe), G2 (KS d1 0,18), G4 (0,46), G5 (0,058).
- **Verdict** : fidélité en échec, v2.1 non soumise au test de prédiction.
- **Ancien rendu B** : échoue sur tous les tests, dont F3, F5 et G1 ; le contrôle de non-trivialité est passé.

**Écart au contrat** : 60 tuiles (mission) au lieu de 176 (« autant que VAL-S », contrat § 2 et § 3.2). À trancher par le chef d'orchestre et scientific-challenger.

**Versions consommées** : 1 sur 3 (v2.1). Aucune retouche après la passe VAL-S.

## 2026-11-07 — D-013, simulateur v2.2 (2e version sur 3)

Demande du chef d'orchestre après la consignation de v2.1 : corriger à partir de CAL seulement et produire 176 tuiles. Détail : `modele_feuille.md` § 11.3, consigné avant la passe VAL-S, et § 11.4.

**Déclarations**
- **Code v2.1 conservé** : `out/comptage_math/leaf-mathematician/D-013/v2.1/simulateur_v2.1.py`, avec un SHA-256 identique à celui du § 11.1.
- **Aucun détecteur lancé**, aucun fichier scellé ouvert.
- **Pendant la calibration**, une seule comparaison VAL-S, faite après le gel (`fidelite_v2.2.json`).

**Calibration** (scènes CAL, graines 5000 + i) :
1. Géométrie, en trois passages de la grille du réseau perturbé et aminci :
   - 1er passage, région = tuile entière : taux de contact biaisé ;
   - 2e passage, sur les gabarits CAL : CV et densité hors cible ;
   - 3e passage, cœur dur avant l'amincissement et terme de CV dans le critère : retenu.
2. Photométrie, en trois comparaisons à CAL :
   - herbe 0,34 avec une densité trop basse ;
   - herbe +0,04 ;
   - texture 16, σ du sec au sol 0,9, allées à p = 0,3 : gel.

**Résultat VAL-S (une passe)** [M]
- **Passent** : F1–F5, G1, G4, G5, G6.
- **Échouent** : G2 (KS d1 0,18) et G3 (densité −15 %, CV +111 %).
- **Verdict** : échec de fidélité ; v2.2 n'est pas soumise à la prédiction.

**Écart de méthode reconnu** : p_allee a été ramené de 0,5 à 0,3 après la grille géométrique, sans réajuster la géométrie.

## 2026-11-07 — D-013, v2.3 : règle du contrôle photométrique final sur CAL (écrite avant son résultat)

- **Échantillon** : 64 scènes de calibration (graines 5000 à 5063), `comparer_cal.py 64`, comparées à CAL seulement.
- **Seuils** (seuils absolus du contrat, appliqués contre CAL) :
  - F1 et F2 : KS ≤ 0,10 ;
  - F3 : chaque classe à ǀΔǀ ≤ 0,05 ;
  - F4 : chaque rapport des écarts-types dans [0,67 ; 1,5] ;
  - F5 : écart ≤ 0,15 dex et ǀΔ penteǀ ≤ 0,3.
- **Contrôles géométriques** : faits sur 549 tuiles (183 gabarits × 3) par `calibrer_geometrie.py` ; ils sont tous passés.
- **Si un seul de ces seuils échoue**, pas de passe VAL-S : je m'arrête et je rends compte au chef d'orchestre.

## 2026-11-07 — D-013, simulateur v2.3 (3e et dernière version) : résultat

- **Calibration sur CAL** :
  - grille géométrique recalée avec p = 0,3, σ_f plafonné par les cellules de 10 m vides, densité et CV dans le critère ; retenu : b1 = 2,2 m, k = 1,2, σ_j = 0,45 m, h = 0,9 m, σ_f = 0 ;
  - texture des limbes en plis 1D ;
  - 5 comparaisons photométriques à CAL.
- **Contrôles CAL** (règle écrite avant leur résultat) : tous passés, géométrie sur 549 tuiles et photométrie sur 64 scènes (`modele_feuille.md` § 11.5).
- **Passe VAL-S unique** (`fidelite_v2.3.json`) [M] :
  - passent : F2, F3, F5 et G1–G6 ;
  - échouent : F1 (KS luminance 0,112 pour 0,10) et F4 (rapport du sol 1,69).
  - Fidélité en échec : v2.3 nest