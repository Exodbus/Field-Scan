# Avenant : essai Kaggle A1 (d3 + PlantVillage BXW), écrit avant tout envoi (16/11/2026, vers 1 h 50)

La proposition `out/jeux_neufs_1611/a1_proposition_kaggle.md` est figée : son SHA-256 est dans `empreinte_proposition_a1.txt`. Cet avenant précise les détails qu'elle laissait ouverts. Il est écrit **avant l'envoi et avant tout résultat d'entraînement**. Son empreinte est dans `empreinte_avenant_a1_kaggle.txt`.

Cadre :
- **Autorisation** : transmise par la session principale le 16/11 : essais Kaggle de nuit, 6 h de GPU au plus en tout.
- **Pour cet essai** : 1,5 h de GPU au plus, 2 fils au plus sur le processeur local. Aucun commit, aucun fichier existant modifié.

## 1. Données envoyées
- **Seules les 200 photos d'A1-appr** (`out/jeux_neufs_1611/a1_roles_finaux.csv`, rôle final `A1-appr`) partent sur Kaggle.
  - Elles ne sont ni A1-test (183) ni l'une des 24 photos retirées.
  - Un contrôle par SHA-256 des originaux, contre `a1_test_liste.csv` et les retirées, est fait avant l'envoi. Il est rejoué sur le dossier envoyé.
- **Forme envoyée** : chaque photo est déjà préparée comme le carnet prépare l'apprentissage (`preparer(chemin, 224, 448)` : lecture JPEG en 448 px, EXIF, `ImageOps.fit` 224 × 224 BILINEAR, JPEG qualité 95, relu). Elle est enregistrée en PNG sans perte, ce qui donne exactement le tableau `uint8` de l'apprentissage.
  - Jeu Kaggle privé : `affilecorentin/a1-appr-224` (200 PNG + `a1_appr.csv`).
  - Licence d'origine CC BY-NC-SA 4.0, notée dans la description.

## 2. Étiquette
- **Classe** : la liste d'entraînement de d3 étiquette le Xanthomonas éthiopien `classe_vraie = "xanthomonas"`. Le carnet m13 le range en **`autre` (indice 3)** par `VERS["xanthomonas"] = 3` [O : `notebooks/m13_entrainer_kaggle.py` ; `predictions_d3b_ethiopie.csv`]. Les 200 photos d'A1-appr reçoivent la même étiquette, `xanthomonas` → 3. Leur source est `plantvillage_psu`.
- **Cible de distillation** : d3 mélange 0,75 × distillation de F1 et 0,25 × étiquettes. Le maître (F1) n'est pas calculé sur A1-appr : sa ligne de maître est le **vecteur one-hot de la classe 3**. La perte de ces photos se réduit ainsi à la seule étiquette annotée, comme le prévoit la proposition. La fonction de perte n'est pas modifiée.

## 3. Recette et carnet
- **Carnet** : `notebooks/a1_entrainer_kaggle.py`, copie de `notebooks/m13_entrainer_kaggle.py`. Seuls trois changements :
  - (a) `MODE` et `RECETTES` sont écrits en dur ;
  - (b) un bloc ajoute A1-appr **après** la reprise du maître de `m13-lot1`, qui reste identique (même liste de chemins). Le carnet refuse de calculer un maître neuf ;
  - (c) dans le pli « sans TDTU », la source `plantvillage_psu` est retirée. Dans le pli « sans Éthiopie », elle est apprise.
- **Recette** : d3b à l'identique (`out/maladies/nuit_1311/kaggle/lot2p/recette_d3b.json` : alpha 0,75, morceaux 0,3, basse résolution 0,3, 3 époques de 16 000 tirages, etc.), `garder = true`.
  - **4 graines : 0, 1, 2, 3**. Les noms sont `a1g0` à `a1g3`.
  - Le tirage par source du carnet donne à `plantvillage_psu` la part d'une source « autre », comme toute source ajoutée. Ce n'est pas un nouveau réglage.
- **Envoi** : un seul (`affilecorentin/a1-lot1`, T4 × 2), 2 recettes par carte.
  - Si le carnet échoue avant la première époque à cause d'une erreur de code, un seul renvoi corrigé est permis. Il est noté et le GPU consommé est compté.
  - Au-delà de **1,5 h** de session, le carnet est arrêté. On mesure alors ce qui est sorti, et seulement si les 4 graines sont complètes. Sinon, l'essai est déclaré incomplet.

## 4. Mesure (règle 4.3 de `docs/plan_nuit_2026-11-13.md`, sans changement)
- **Banc** : `scripts/m14_banc.py`, importé sans modification par un nouveau script `scripts/a1_kaggle_banc.py`.
  - Chaîne « élève » (`chaine_eleve`) au **couple de d3b (0,50 ; 0,70), sans nouveau réglage**.
  - Lecture « ensemble livrable » : TDTU et Éthiopie par le réseau qui ne les a pas appris, les autres jeux par la moyenne des 2 plis.
  - Contrôles avant tout essai : F1 doit redonner 33,94, et d3b 32,77.
- **Par graine** : coût de réglage (5 jeux), conditions 4.3, malades sans alerte sur chaque jeu, roamer.
- **Décision sur la moyenne des 4 graines.** Chaque compte (malades sans alerte, saines en alerte, par jeu, et roamer) est moyenné sur les 4 graines. Le coût de réglage et les conditions 4.3 sont calculés sur ces moyennes.
  - **Finaliste** si ces moyennes passent les 4 conditions de réglage de 4.3 :
    - coût ≤ 32,94 ;
    - validation Tanzanie : malades sans alerte ≤ 14 et saines en alerte ≤ 77 ;
    - aucun jeu ne perd plus de 2 points ;
    - roamer ≤ F1 + 2 ;
  - **et** si le **contrôle propre** passe : malades sans alerte en Éthiopie (moyenne des 4 graines, lue par le pli « sans Éthiopie ») ≤ 117, la valeur de F1.
- **Temps** : chaque graine a l'architecture de d3b (2 ConvNeXt-Tiny DINOv3, 384 px, 4 vues), mesurée le 13/11 sous 1,2 × F1. La condition est réputée remplie, sans nouvelle mesure.
- **Réseau livrable** si finaliste : la graine de plus bas coût de réglage **parmi celles qui passent seules** toutes les conditions ci-dessus. Si aucune ne passe seule, il n'y a pas de finaliste livrable, et on l'écrit.
- **Pour information seulement** (aucune décision) : la même recette sans A1, graines 0 à 3. Valeurs : 32,77, 33,44, 34,49 et 35,12, soit une moyenne de 33,95 (`out/maladies/nuit_1311/piste2/bilan_graines.json`). L'écart à ces valeurs mesure l'effet d'A1-appr.

## 5. Ordre des lectures
1. Réglage (5 jeux + roamer), pour les 4 graines, en une fois. Puis `out/jeux_neufs_1611/a1_kaggle_finalistes.md` (finaliste ou « aucun finaliste »).
2. **Seulement si finaliste** : les juges, une lecture chacun, par le réseau livrable (BanSpot : tachées sans alerte ≤ 6 / 646 et saines en alerte ≤ 56 / 646 ; Cordana du Pérou ≥ 97 % en alerte). Les juges ne partent jamais sur Kaggle : ils sont lus en local, à 2 fils.
3. **Seulement si les juges passent** (candidat proposé à l'adoption) : A1-test, une lecture, rapportée à côté du 0 / 183 de F1, avec les deux réserves (pas de saines ; séries voisines d'A1-appr).
4. Aucune adoption sans Corentin.
