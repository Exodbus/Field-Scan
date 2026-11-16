# Avenant m16 : apprendre la robustesse à la basse résolution (16/11/2026, vers 2 h 15)

Cet avenant est écrit **avant tout envoi, tout entraînement et toute mesure** de l'essai m16. Son empreinte SHA-256 est dans `empreinte_avenant_m16.txt`. Aucun commit n'est fait : l'empreinte tient lieu de date.

Cadre :
- **Autorisation** : transmise par la session principale le 16/11 (mots de Corentin : « Envoie autant d'essais que tu veux sur Kaggle en mon absence […] Tu as le droit à tout tant que je ne paye pas. »). Compte `affilecorentin`, quota gratuit.
- **Pour cet essai** : **2 h de GPU au plus**, 2 fils au plus sur le processeur local. Aucun commit, aucun fichier existant modifié, aucun téléchargement hors des sorties de mon propre carnet.

## 0. Hypothèse et ce qui est déjà connu
- F1 laisse 117 malades sans alerte sur 1 134 en Éthiopie, et 0 sur 183 sur A1-test (PlantVillage pleine résolution) [O : `out/jeux_neufs_1611/a1_mesure_f1.md`]. Hypothèse [H] : la difficulté éthiopienne tient à la résolution.
- Constats faits avant cet avenant (fichiers existants, aucun calcul neuf sur le réglage) [O] :
  - les 1 289 photos éthiopiennes sont des miniatures de **150 × 113 px**, JPEG de qualité voisine de **75** (moyenne de la table de quantification de luminance ≈ 29, sur 65 photos tirées une sur vingt) ;
  - au banc, elles sont lues en 384 px (`fit_jpeg(…, 384)`) : le carré central de 113 px est agrandi 3,4 fois. L'apprentissage se fait en 224 px. À l'échelle de l'entrée d'apprentissage, l'Éthiopie équivaut donc à une image d'environ **66 px de côté** (113 × 224 / 384) remise en 224 ;
  - la recette d3b contient déjà `BasseRes` (p = 0,3 ; côté 100 à 160 px ; sans JPEG), qui ne descend pas jusque-là, surtout avant le recadrage aléatoire ;
  - valeurs connues de d3b, graines 0 à 3 (`out/maladies/nuit_1311/piste2/bilan_graines.json`) : coûts 32,77 ; 33,44 ; 34,49 ; 35,12 ; Éthiopie, malades sans alerte 120 ; 160 ; 157 ; 165.

## 1. Recette (une seule variante, 4 graines)
- **Base** : d3b à l'identique (`out/maladies/nuit_1311/kaggle/lot2p/recette_d3b.json` : alpha 0,75, morceaux 0,3, basse résolution 0,3, 3 époques de 16 000 tirages, lr 1e-5 / 1e-4, perte × 2, sans PSFD, jeux neufs du Bangladesh, `garder = true`, etc.).
- **Seul ajout : l'augmentation `ReduitJPEG`**, paramètres fixés ici, sans variante :
  - probabilité **p = 0,4** par image tirée ;
  - l'image d'apprentissage (224 × 224) est réduite à un carré de côté **c tiré uniformément entre 64 et 128 px** (entier), en `Image.BILINEAR` (Pillow lisse en réduction) ;
  - elle est recompressée en **JPEG de qualité tirée uniformément entre 50 et 90** (entier) ;
  - elle est remise à 224 × 224 en `Image.BILINEAR`.
  - Elle s'applique **en premier**, avant `BasseRes`, `Morceau`, `JPEGAleatoire` et le recadrage aléatoire, comme une dégradation à la source. Les autres augmentations sont inchangées et restent indépendantes.
  - Justification de la plage (écrite avant) : 64 à 128 px encadre l'équivalent éthiopien (≈ 66 px), le recadrage aléatoire qui suit (côté 0,63 à 1) l'abaisse encore ; la qualité 50 à 90 encadre ≈ 75.
- **Graines : 0, 1, 2, 3.** Noms `m16g0` à `m16g3`. Ce sont les graines de d3b g0 à g3 : la comparaison est appariée, pour information.
- Aucune autre variante n'est envoyée sous cet avenant.

## 2. Carnet et envoi
- **Carnet** : `notebooks/m16_entrainer_kaggle.py`, copie de `notebooks/m13_entrainer_kaggle.py`, avec ces seuls changements :
  - (a) `MODE` et `RECETTES` écrits en dur dans la copie envoyée (comme pour m13, m14 et a1) ;
  - (b) la classe `ReduitJPEG` et la clé `reduit_jpeg` (p ; 0 = absente, valeur par défaut) avec `reduit_cote` = (64, 128) et `reduit_qualite` = (50, 90) dans `DEFAUT`, et son insertion en tête dans `augmentations` ;
  - (c) le refus d'un maître neuf : le maître de `m13-lot1` est repris tel quel (même liste de chemins, aucun calcul de F1 sur Kaggle) ;
  - (d) un garde-fou de durée : avant chaque pli, si la session a passé **105 min**, la recette s'arrête en échec (l'essai est alors incomplet).
- **Pli** : comme d3b, `MODE = "plis"` : un réseau « sans TDTU » et un réseau « sans Éthiopie » (et sans PSFD) ; Éthiopie et TDTU sont lus par le réseau qui ne les a pas appris, les autres jeux par la moyenne des 2 plis (« ensemble livrable »).
- **Envoi** : un seul carnet, `affilecorentin/m16-lot1`, T4 × 2, 2 recettes par carte, jeux Kaggle déjà existants de m13 (aucune donnée neuve envoyée, aucun juge).
  - Contrôles avant l'envoi (`scripts/m16_pousser.py`) : le diff avec m13 ne contient que (a) à (d) ; les recettes égalent d3b sauf `nom`, `graine` et les 3 clés de `ReduitJPEG` ; le dossier d'envoi ne contient que le carnet et ses métadonnées ; le contrôle de fuite des outils de m13 est vide ; les refus de juges du carnet sont présents.
  - Si le carnet échoue avant la première époque par une erreur de code, **un seul renvoi corrigé** est permis, noté au journal, son GPU compté.
  - Kaggle n'accepte que 2 carnets GPU à la fois : l'envoi attend une place libre (vérification toutes les 10 min).
- **Plafond GPU : 2 h de session.** Au-delà, l'essai est arrêté et déclaré incomplet ; on ne mesure que si les 4 graines sont complètes.

## 3. Mesure sur le réglage (règle 4.3 de `docs/plan_nuit_2026-11-13.md`, sans changement)
- **Banc** : `scripts/m14_banc.py`, importé sans modification par `scripts/m16_banc.py` (comme `scripts/a1_kaggle_banc.py`).
  - Chaîne « élève » (`chaine_eleve`) au couple de d3b **(0,50 ; 0,70), sans nouveau réglage**.
  - Lecture « ensemble livrable » (`lire_kaggle`).
  - Contrôles avant tout essai : F1 doit redonner **33,94** et d3b **32,77** ; sinon arrêt.
- **Par graine** : coût de réglage (5 jeux), conditions 4.3, malades sans alerte et saines en alerte par jeu, roamer.
- **Décision sur la moyenne des 4 graines** : chaque compte (malades sans alerte, saines en alerte, par jeu, et roamer) est moyenné ; le coût de réglage et les conditions 4.3 sont calculés sur ces moyennes.
  - **Règle 4.3 inchangée** (4 conditions de réglage) :
    - coût de réglage ≤ F1 − 1, soit **≤ 32,94** ;
    - validation Tanzanie : malades sans alerte ≤ 14 et saines en alerte ≤ 77 ;
    - aucun des 5 jeux ne perd plus de 2 points de taux de malades sans alerte par rapport à F1 ;
    - roamer : malades sans alerte ≤ F1 + 2.
  - **Temps** : architecture de d3b (2 ConvNeXt-Tiny DINOv3, 384 px, 4 vues), déjà mesurée sous 1,2 × F1 le 13/11 ; l'augmentation n'agit qu'à l'apprentissage. Condition réputée remplie, sans nouvelle mesure.
- **Contrôle propre à l'essai** (en plus de 4.3, sur les mêmes moyennes) :
  - (E1) Éthiopie, malades sans alerte (lues par le pli « sans Éthiopie ») **strictement < 117** (valeur de F1) ;
  - (E2) Éthiopie, saines en alerte : pas de hausse au-delà de ce que tolère le taux d'échange de 4.3 (une malade ratée vaut 3 saines en alerte, en taux). Concrètement, **coût Éthiopie (3 × taux de malades sans alerte + taux de saines en alerte) ≤ celui de F1** (3 × 117 / 1 134 + 28 / 155 ≈ 49,01 points).
- **Finaliste** si la moyenne des 4 graines passe les 4 conditions de 4.3 **et** E1 **et** E2.
- **Réseau livrable** si finaliste : la graine de plus bas coût de réglage **parmi celles qui passent seules** 4.3, E1 et E2. Si aucune ne passe seule, pas de finaliste livrable, et on l'écrit.
- **Pour information seulement** (aucune décision) : écart apparié à d3b g0 à g3 (coût, Éthiopie), et effet sur les autres jeux.

## 4. Ordre des lectures
1. Réglage (5 jeux + roamer), pour les 4 graines, en une fois. Puis `out/maladies/jour_1611/m16_finalistes.md` (finaliste ou « aucun finaliste »).
2. **Seulement si finaliste** : les juges, une lecture chacun, par le réseau livrable : BanSpot (tachées sans alerte ≤ 6 / 646 et saines en alerte ≤ 56 / 646) et Cordana du Pérou (≥ 97 % en alerte). Ils ne partent jamais sur Kaggle : lus en local, à 2 fils.
3. **Seulement si les juges passent** (candidat proposé à l'adoption) : A1-test, une lecture, rapportée à côté du 0 / 183 de F1.
4. Aucune adoption sans Corentin.

## 5. Écriture
Fichiers neufs seulement : `notebooks/m16_*`, `scripts/m16_*`, `out/maladies/jour_1611/`, `docs/journee_2026-11-16/` (cet avenant, son empreinte, `journal_m16.md`). Les poids rapatriés vont dans `out/maladies/jour_1611/m16/lot1/` (jamais commités).
