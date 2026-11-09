# math-forme : forme, orientation et répartition spatiale des lésions

Agent `math-forme`, équipe maladies, nuit du 8 novembre 2026. Fichiers : `out/maladies/equipe/math-forme/`.

Question : **la forme et l'orientation des lésions distinguent-elles les maladies mieux que la couleur seule, de façon robuste d'un pays à l'autre ?**

## 0. Données et observations

- Développement : la liste `dev` de l'évaluateur (`predire_reference.py`, fonction `liste_jeu`, reprise telle quelle) : 300 images par (source, classe) de Tanzanie 2021 (saine, cercosporiose noire, fusariose) et du Pérou (saine, cercosporiose noire), plus toutes les images TDTU (577 saines, 404 Sigatoka, 655 autre maladie) et khadavy (159 saines, 245 Bercak-Hitam, 27 Bercak-Kuning).
- [O] Mosaïque `mosaique_dev.jpg` : en Tanzanie et au Pérou, les photos sont des **gros plans** d'un morceau de limbe ; le bord de feuille est rarement visible. TDTU et khadavy montrent plus souvent la feuille entière, voire la plante (TDTU : fonds blancs détourés, captures d'écran).
- [O] Tanzanie 2021, fusariose : larges bandes jaunes **parallèles aux nervures**, sans tache brune ; souvent un limbe jaune entier. Cercosporiose noire : plages brun-violet confluentes, halo jaune, stries brunes ; la nécrose est souvent **violacée** et non brun-noir.
- [O] khadavy Bercak-Hitam : petites ponctuations brunes rondes éparses, sur limbe vert clair (et non des stries).
- [O] Images de contrôle `apercus/<source>_<classe>.jpg` : la direction des nervures estimée par le tenseur de structure suit les nervures à l'œil sur les 44 images regardées, sauf sur les photos de plante entière (TDTU) où elle n'a pas de sens.

## 1. Méthode (fichier `forme.py`)

Image réduite à **224 px** de grand côté (d'abord 320 ; réduit avant tout calcul de descripteurs, sur consigne de l'orchestrateur : processeur partagé ; un seul processus, 2 fils OpenCV ; environ 0,5 s par image). Masques par seuils HSV fixes : feuille, nécrose N (brun-rouge sombre, violacé, très sombre), chlorose Y (jaune saturé plus orangé que le limbe de l'image : seuil relatif à la teinte médiane du limbe), tissu sec D (beige peu saturé). Puis :
- **nervures** : tenseur de structure (dérivée de gaussienne σ = 1,5, intégration σ = 6) sur la luminance L*, moyenne en angle double sur le vert ; cohérence globale, cohérence locale moyenne, dispersion ;
- **composantes connexes** de N, Y, D (8-connexité, aire ≥ 6 px) : moments d'ordre 2 → allongement √(λ1/λ2), angle de l'axe principal, alignement |cos(φ − θ_nervures)| (aléatoire : 0,64), compacité, densité, aire médiane, part de la plus grande (confluence), nombre de ponctuations rondes (aire < 80, allongement < 2) et de stries (allongement ≥ 3) ;
- **motif des lésions** : tenseur de structure du masque N ∪ Y (cohérence, alignement avec les nervures) ;
- **spectre orienté** : part de l'énergie de Fourier (bande 0,02-0,25 cycle/px) dans un secteur de ±15° autour de la normale aux nervures ;
- **répartition spatiale** : distance au bord de la feuille (transformée de distance, normalisée par la distance moyenne du limbe) des pixels Y, D, N, quand un bord est visible ; position radiale par rapport au centre de l'image.
- Référence « couleur simple » (colonnes `c_*`, plus les parts N, Y, D) : histogramme de teinte (12 cases), moyennes et écarts-types HSV et L*a*b*. Minimale, seulement pour la comparaison ; le vrai travail couleur est celui de `math-couleur`.

Groupes (`outils.py`) : **forme** = nervures, composantes, motif, spectre, répartition (sans aucune part de surface colorée) ; **couleur** = `c_*` + parts N, Y, D ; **scène** = part de feuille, part de fond.

## 2. Expériences sur le développement (critères écrits avant le calcul)

### E-F01 : quels descripteurs de forme séparent Sigatoka et saine dans les quatre pays ?
- Hypothèse [H] : les descripteurs de forme (alignement des lésions sur les nervures, allongement, ponctuations) séparent cercosporiose noire et saine dans le même sens dans les quatre sources.
- Jeu : dev, par source (Tanzanie 2021, Pérou, TDTU, khadavy).
- Mesure : AUC de chaque descripteur pour « cercosporiose noire contre saine », par source.
- Seuil : un descripteur est dit **robuste** s'il a |AUC − 0,5| ≥ 0,10 **dans le même sens** dans les quatre sources. Même mesure pour fusariose contre cercosporiose noire (Tanzanie seulement : un seul pays, donc aucune conclusion de robustesse).

### E-F02 : la forme ajoute-t-elle à la couleur d'un pays à l'autre ?
- Hypothèse [H] : un modèle linéaire forme + couleur généralise mieux d'un pays à l'autre qu'un modèle couleur seule.
- Jeu : dev, classes saine et cercosporiose noire, **un pays laissé de côté** à tour de rôle (apprentissage sur les trois autres).
- Méthode figée : régression logistique L2 (λ = 0,01), entrées standardisées, médiane pour les manques, classes équilibrées. Trois ensembles : forme, couleur, forme + couleur.
- Mesure : exactitude équilibrée sur le pays laissé de côté ; moyenne des quatre.
- Seuil : **H confirmée** si forme + couleur dépasse couleur seule d'au moins **+0,03** en moyenne et ne perd pas plus de 0,02 sur aucun pays. **Forme seule « meilleure que la couleur »** si elle la dépasse en moyenne.

### E-F03 : fusariose contre Sigatoka, Tanzanie 2021
- Hypothèse [H] : la forme (bandes jaunes alignées sans nécrose ronde, jaunissement près du bord) aide à séparer fusariose et Sigatoka.
- Jeu : dev Tanzanie 2021 (3 × 300), validation croisée en 5 plis (graine 0).
- Mesure : exactitude équilibrée à 3 classes ; forme, couleur, forme + couleur.
- Seuil : gain ≥ +0,03 de forme + couleur sur couleur seule. Limite écrite : un seul pays.

(Résultats : section 3.)

## 3. Résultats sur le développement

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/maladies/equipe/math-forme/analyse_dev.py` (descripteurs : `extraire.py dev`, 3 567 images, 717 s). Fichiers : `ef01_auc.csv`, `ef02_pays_laisse.csv`, `ef03_tanzanie.csv`.

### E-F01 [M] (Sigatoka contre saine, AUC par pays : Tanzanie, Pérou, TDTU, khadavy)
- **Robustes (même sens, |AUC − 0,5| ≥ 0,10 dans les 4 pays)**, groupe forme : `Y_stries` (0,90 / 0,90 / 0,78 / 0,72), `Y_densite` (0,94 / 0,95 / 0,79 / 0,71), `Y_points`, `D_stries`, `N_stries` (0,96 / 0,89 / 0,74 / 0,63), `D_dist_bord` (0,77 / 0,65 / 0,64 / 0,71) et surtout **`nerv_coherence_locale`** (0,23 / 0,13 / 0,32 / 0,34), **seul descripteur robuste qui ne dépend d'aucun seuil de couleur** : la maladie casse la texture régulière des nervures. Groupe couleur : `Y_part`, `c_a_moy`, `c_h1`, `c_G_part`… (les AUC couleur baissent nettement en TDTU et khadavy : `c_h1` 0,98 → 0,66).
- Limite : `Y_stries`, `Y_densite`, `N_stries` comptent des **objets** colorés (nombre par surface) : ils dépendent des masques de couleur, mais le nombre et la forme d'objets résistent mieux au changement de pays que leur surface.
- **Orientation par rapport aux nervures : réfutée comme critère de maladie.** `N_alignement` et `Y_alignement` ne sont robustes nulle part. Les lésions sont alignées sur les nervures en Tanzanie pour la Sigatoka **et** pour la fusariose (alignement moyen N 0,86 et 0,78, motif `lesion_alignement` 0,97 et 0,96) ; au Pérou et en khadavy l'alignement est au niveau du hasard (0,63-0,72) : petites taches rondes, ou stries trop fines pour 224 px.
- **Jaunissement depuis le bord (fusariose)** : non mesurable sur ces gros plans (bord visible pour 73 fusarioses sur 300) ; quand il l'est, `Y_dist_bord` ne sépare pas fusariose et Sigatoka (AUC 0,43). Hypothèse ni confirmée ni réfutée : les photos ne montrent pas la feuille entière.
- Fusariose contre Sigatoka (Tanzanie seulement) : `N_densite` 0,14, `N_points` 0,17 (la fusariose n'a presque pas de taches nécrotiques), **`spectre_secteur_nerv` 0,84** et `nerv_coherence_locale` 0,83 (la fusariose garde des bandes régulières parallèles aux nervures ; la Sigatoka casse ce motif).

### E-F02 [M] (pays laissé de côté, saine / Sigatoka, exactitude équilibrée)

| pays laissé | couleur | forme | forme + couleur |
| --- | --- | --- | --- |
| khadavy | 0,628 | **0,699** | 0,681 |
| Pérou | **0,937** | 0,927 | 0,910 |
| Tanzanie 2021 | **0,952** | 0,933 | 0,935 |
| TDTU | 0,688 | **0,755** | 0,735 |
| moyenne | 0,801 | **0,829** | 0,815 |

AUC sur khadavy : couleur 0,678, forme 0,836, forme + couleur 0,841.
- H « forme + couleur ≥ couleur + 0,03 » : **réfutée** (+0,014, et −0,027 au Pérou).
- « Forme seule meilleure que la couleur seule » : **confirmée sur le développement** (+0,028 en moyenne ; +0,07 sur les deux pays les plus éloignés, −0,01 et −0,02 sur les deux pays proches).

### E-F03 [M] (Tanzanie 2021, 3 classes, 5 plis)
Exactitude équilibrée : couleur 0,783, forme 0,842, **forme + couleur 0,900** (+0,117 ≥ +0,03 : **confirmée**, un seul pays). Fusarioses dites Sigatoka : 23 % → 12 %.

### E-F02b (critère écrit avant le calcul) : la géométrie pure, sans comptage d'objets colorés
- Hypothèse [H] : le sous-groupe « géométrie pure » (nervures, spectre, alignement, allongement, compacité, confluence, aire médiane, distance au bord, position radiale, motif ; **sans** densités, ponctuations ni stries comptées) porte à lui seul une information transférable.
- Même protocole qu'E-F02. Seuil : exactitude équilibrée moyenne ≥ 0,70 en pays laissé de côté ; et rapport du sous-groupe « comptages » (densités, ponctuations, stries) seul.

### E-F02b [M]
Exactitude équilibrée moyenne en pays laissé de côté : **géométrie pure 0,809** (khadavy 0,710, Pérou 0,887, Tanzanie 0,912, TDTU 0,727), comptages 0,787, couleur 0,801. Seuil 0,70 : **confirmée**. La géométrie pure, sans aucune surface ni aucun comptage coloré, égale la couleur simple en moyenne et la bat sur khadavy (AUC 0,810 contre 0,678). Fichier `ef02b_sous_groupes.csv`, commande `analyse_dev_b.py`.

## 4. Protocole de validation (écrit le 8 novembre 2026, avant toute mesure sur la validation et BananaLSD)

Aucun réglage après ce point. Méthode figée :
- descripteurs : `forme.py` tel qu'il est à cette heure (224 px), `extraire.py validation bananalsd` ;
- modèles : régression logistique `outils.Logistique(lam=0.01)` apprise **une fois** sur tout le développement des classes saine, cercosporiose noire, fusariose (2 885 images ; `autre_maladie` exclue), classes équilibrées ; quatre ensembles de descripteurs : `couleur`, `forme`, `geometrie` (E-F02b), `forme_couleur` ;
- réponse = classe de probabilité maximale (pas de rejet) ; fichiers de prédictions au format de l'évaluateur (`chemin, jeu, classe_vraie, p_saine, p_black_sigatoka, p_fusarium, reponse`) : `predictions_<ensemble>_{validation,bananalsd}.csv` ;
- mesures par `eval_commun.py` de l'évaluateur (sans modification), différences par bootstrap apparié `ec.comparer` (10 000 tirages, graine 2026).

### E-F10 : validation Tanzanie 2022-2023 (3 001 images)
- Mesure principale : F1 macro 3 classes (`mesures_validation`).
- **H-V1 (forme ≥ couleur)** : confirmée si F1(forme) − F1(couleur) > 0 avec borne basse de l'IC 95 % > 0 ; réfutée si borne haute < 0 ; sinon non tranchée. Même règle pour `geometrie` contre `couleur`.
- **H-V2 (la forme ajoute à la couleur)** : confirmée si F1(forme_couleur) − F1(couleur) ≥ +0,03 et borne basse > 0.
- Références (sans décision) : F1 du B0 et de la v2 (`predictions_{b0,v2}_validation.csv`), différence forme_couleur − référence.
- Limite écrite : même pays que la Tanzanie 2021 du développement ; la robustesse entre pays est surtout jugée sur BananaLSD.

### E-F11 : BananaLSD (Bangladesh, 897 images, dont 602 saines ou Sigatoka)
- Mesure principale : exactitude équilibrée saine / Sigatoka = moyenne de `sigatoka_nommee` et `saines_bien_classees` (fusariose répondue = erreur). Bootstrap apparié sur les 602 images connues.
- **H-B1 (forme ≥ couleur hors domaine)** : même règle que H-V1. Même règle pour `geometrie`.
- **H-B2** : même règle que H-V2 (+0,03).
- Les inconnues (Cordana, Pestalotiopsis) : parts dites saines / Sigatoka / fusariose, rapportées sans critère.

### E-F12 : fusion maths + IA (seulement si les prédictions de développement de la référence existent au moment de la mesure)
- Idée [H] : la v2 (ou le B0) se trompe sur les pays nouveaux en disant « saine » des feuilles à petites taches ; la géométrie pure, plus stable d'un pays à l'autre, corrige la décision saine / Sigatoka.
- Méthode figée : régression logistique binaire saine / Sigatoka (λ = 0,01) sur [log p_saine, log p_black_sigatoka, log p_fusarium de la référence] + `geometrie`, apprise **uniquement sur TDTU et khadavy** du développement (jamais vus par la référence). Décision : si la référence répond fusariose, on garde ; sinon la fusion tranche entre saine et Sigatoka.
- Seuil : F1 macro validation (fusion − référence) ≥ 0 (pas de perte, borne basse > −0,01) **et** exactitude équilibrée BananaLSD (fusion − référence) > 0 avec borne basse > 0.

Scripts figés avant la mesure : `mesure_validation.py` (E-F10, E-F11 ; une seule exécution, fichier `VERROU_validation`) et `mesure_fusion.py <ref>` (E-F12, une exécution par référence, dès que `predictions_<ref>_dev.csv` existe ; `VERROU_fusion_<ref>`). Les comparaisons aux références absentes au moment de la mesure seront faites ensuite avec `ec.comparer`, sur les fichiers de prédictions déjà écrits, sans rien réapprendre.

**Amendement à E-F12 (avant toute mesure sur la validation ou BananaLSD).** Diagnostic sur le développement (`diag_v2_dev.py`, `diag_v2_dev.csv`) [M] : sur TDTU et khadavy, la v2 brute n'atteint que 0,461 et 0,613 d'exactitude équilibrée saine / Sigatoka (25 % des Bercak-Hitam dites saines) ; une simple **recalibration** logistique de ses trois probabilités, apprise sur l'autre jeu, donne 0,813 et 0,859 ; ajouter la géométrie donne 0,742 et 0,857 (pas mieux). Le gain d'E-F12 contre la v2 brute mélangerait donc recalibration et géométrie. Ajout d'un **témoin** : « v2 recalibrée » (même méthode, sans descripteur de forme). Seuil supplémentaire pour attribuer un gain à la géométrie : fusion − v2 recalibrée > 0 avec borne basse > 0 sur BananaLSD.

## 5. Résultats de la validation (mesure unique, 9 novembre 2026)

Commandes : `PYTHONIOENCODING=utf-8 OMP_NUM_THREADS=2 .venv/Scripts/python.exe -I -u out/maladies/equipe/math-forme/mesure_validation.py` puis `mesure_fusion.py v2` et `mesure_fusion.py b0`. Fichiers : `mesure_validation.json`, `mesure_fusion_{v2,b0}.json`, `predictions_<ensemble>_{validation,bananalsd}.csv`, `fusion_*.csv`, `recalibree_*.csv`. Rien n'a été changé après. Note : la liste BananaLSD de l'évaluateur a 90 saines (et non 129), d'où 563 images connues.

### E-F10 [M] validation Tanzanie 2022-2023 (3 001), F1 macro 3 classes

| méthode | F1 macro |
| --- | --- |
| couleur simple | 0,663 |
| forme | 0,562 |
| géométrie pure | 0,553 |
| forme + couleur | 0,713 |
| B0 | 0,955 |
| v2 | 0,960 |

- **H-V1 (forme ≥ couleur) : réfutée** (−0,101, IC [−0,121 ; −0,081]) ; géométrie pure aussi (−0,110).
- **H-V2 (forme ajoute ≥ +0,03 à la couleur) : confirmée** (+0,050, IC [+0,033 ; +0,068]).
- Erreur principale : fusarioses dites Sigatoka (415 sur 1 001 pour forme + couleur). Les maths restent très loin des réseaux (−0,246 contre la v2).

### E-F11 [M] BananaLSD (563 saines ou Sigatoka), exactitude équilibrée saine / Sigatoka

couleur 0,403 ; **forme 0,564** ; géométrie 0,559 ; forme + couleur 0,550 ; B0 0,899 ; v2 0,948.
- **H-B1 (forme ≥ couleur hors domaine) : confirmée** (+0,161, IC [+0,097 ; +0,224]) ; géométrie pure aussi (+0,156, IC [+0,086 ; +0,228]).
- **H-B2 (forme + couleur ≥ couleur + 0,03) : confirmée** (+0,147, IC [+0,094 ; +0,200]).
- Mais le niveau absolu est faible : la moitié des Sigatoka du Bangladesh sont dites « fusariose » (242 sur 473 pour forme + couleur ; 321 pour la couleur). La seule fusariose apprise est tanzanienne : le modèle confond « jauni » et « fusariose ».

### E-F12 [M] fusion référence + géométrie pure (apprise sur TDTU + khadavy seulement)

| | validation F1 (fusion − réf.) | BananaLSD exactitude éq. (fusion − réf.) | fusion − recalibrée (BananaLSD) |
| --- | --- | --- | --- |
| v2 | 0,954 − 0,960 = −0,005 [−0,009 ; −0,002] | 0,979 − 0,948 = **+0,031** [+0,009 ; +0,056] | −0,006 [−0,019 ; 0,000] |
| B0 | 0,941 − 0,955 = −0,015 [−0,019 ; −0,010] | 0,920 − 0,899 = +0,021 [−0,017 ; +0,056] | −0,003 [−0,040 ; +0,033] |

- Seuil (validation ≥ 0 avec borne basse > −0,01, et BananaLSD > 0 avec borne basse > 0) : **non atteint** pour la v2 (perte de 0,005 sur la validation, estimation négative) ni pour le B0.
- Le gain sur BananaLSD vient de la **recalibration** (v2 recalibrée sans géométrie : 0,985, +0,037 [+0,018 ; +0,060] contre la v2 brute), **pas de la géométrie** (fusion − recalibrée ≤ 0). Le gain ne peut donc pas être attribué à la forme.

## 6. Conclusion

- [M] La forme et l'orientation **ne distinguent pas les maladies mieux que la couleur** sur la validation tanzanienne (H-V1 réfutée), mais elles **résistent mieux au changement de pays** : meilleures que la couleur en pays laissé de côté (E-F02, E-F02b) et sur BananaLSD (H-B1, +0,16). Elles **complètent** la couleur (H-V2, H-B2, E-F03).
- [M] Ce qui distingue vraiment : (1) la **rupture de la texture des nervures** (`nerv_coherence_locale`, AUC 0,13-0,34 dans les quatre pays, aucun seuil de couleur) pour malade contre saine ; (2) le **nombre d'objets** (ponctuations, stries) plutôt que leur surface ; (3) pour fusariose contre Sigatoka (Tanzanie seulement) : absence de petites nécroses (`N_densite`, AUC 0,14) et spectre concentré perpendiculairement aux nervures (`spectre_secteur_nerv`, 0,84).
- [M] **Réfuté** : l'orientation des lésions parallèle aux nervures comme critère de maladie (vraie pour la Sigatoka **et** la fusariose en Tanzanie ; au hasard ailleurs). Non testable : le jaunissement depuis le bord (gros plans sans bord).
- [M] Aucune méthode mathématique n'approche la v2 (0,71 contre 0,96 de F1 ; 0,55 contre 0,95 sur BananaLSD). La fusion géométrie + v2 n'apporte rien au-delà d'une recalibration de la v2.
- Proposition : (a) pour l'IA, **recalibrer la v2** sur des pays qu'elle n'a pas vus (TDTU, khadavy) est la seule amélioration mesurée ici sur BananaLSD (+0,037), au prix de −0,008 de F1 sur la validation : à soumettre à `amelioration-modele` comme piste, avec règle écrite avant ; (b) garder `nerv_coherence_locale` et les comptages d'objets comme **contrôle explicable** (« la texture des nervures est cassée ») et comme descripteurs de fusion pour l'agent de fusion, pas comme classifieur seul ; (c) la confusion fusariose / Sigatoka hors Tanzanie vient de la seule source de fusariose : aucun descripteur ne la corrigera sans une deuxième source de fusariose.
