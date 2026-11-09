# Fiche de l'évaluateur (équipe maladies)

Rédacteur unique : `evaluateur`. Sorties : `out/maladies/equipe/evaluateur/`.

## 1. Prédictions de référence (v2 ConvNeXt, B0)

Script : `out/maladies/equipe/evaluateur/predire_reference.py` (vérifie d'abord les empreintes des modèles, les mêmes que `scripts/mesurer_test_khadavy.py`).
Appels : v2 = `classifieur.charger` / `probabilites` / `decider` avec `poids/seuils.json` ; B0 = `charger_modele` / `predire` / `decider(L, m, 0.5)` avec les réglages de `predire_b0`.

Format : `predictions_{v2,b0}_{validation,bananalsd,dev}.csv`, colonnes `chemin, jeu, classe_vraie, p_saine, p_black_sigatoka, p_fusarium, reponse`.
- `chemin` relatif à la racine du dépôt ; `jeu` = source (tanzanie_2022, bananalsd, tanzanie_2021, perou_2026, khadavy, tdtu) ;
- `classe_vraie` : saine, cercosporiose_noire, fusariose, inconnue_cordana, inconnue_pestalotiopsis, autre_maladie ;
- `reponse` déjà en vocabulaire commun : saine, cercosporiose_noire, fusariose, malade_non_identifiee, je_ne_sais_pas (le « inconnu » de la v2 devient je_ne_sais_pas).

Sous-échantillon de développement (`dev`) : pour chaque (source, classe) de tanzanie_2021 et perou_2026 (`ensemble == entrainement`, `retenue`), lignes triées par (source, classe, id) puis `sample(n=300, random_state=2026)` ; soit 3 × 300 Tanzanie 2021 + 2 × 300 Pérou = 1 500, plus les 2 067 images de `data/feuilles_v3_ajouts/images.csv` (khadavy 431, tdtu 1 636) ; total 3 567.

État des fichiers : voir section 5 (journal).

## 2. Code d'évaluation commun

`out/maladies/equipe/evaluateur/eval_commun.py` (définitions en tête du fichier, écrites avant toute mesure). Résumé :
- malade ratée = vraie malade dite « saine » ; fausse alerte = vraie saine dite malade (cercosporiose, fusariose ou non identifiée) ; « je ne sais pas » à part (variante `cout_jnsp_compte_ratee`) ;
- coût = 2 × ratées + fausses alertes ; F1 macro sur saine / cercosporiose / fusariose (non identifiée et je ne sais pas = erreurs) ;
- Wilson 95 % pour les proportions, bootstrap apparié 10 000 tirages graine 2026 (`comparer(a, b, METRIQUES[...])`).

## 3. Test « de loin »

### 3.1 ROAMER Laguna : inspection sans modèle (8 novembre, 23 h 40)

Critère écrit avant l'inspection : Laguna sert de test « de loin » seulement si chaque image (ou chaque feuille annotée) porte une étiquette saine / malade fiable, c'est-à-dire une classe dont le sens sanitaire est constant sur les planches.

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/maladies/equipe/evaluateur/test_de_loin/inspecter_laguna.py` ; sorties `test_de_loin/inventaire_laguna.csv`, `test_de_loin/planche_*.jpg` (annotations tracées : rouge « Positive », bleu « object », vert « 1 »).

- [O] Zip de 424 fichiers : 420 images 640 × 640 (train 293, valid 84, test 43), 3 fichiers COCO, un README. « No image augmentation » ; 420 noms d'origine distincts (`extra.name`), donc une image par photo.
- [O] Catégories : `banana-leaves` (racine), `1` (72 polygones), `Positive` (1 224 polygones), `object` (218 boîtes sans polygone, aire médiane 1 036 px²).
- [O] Combinaisons par image : Positive seul 187, object seul 85, 1 seul 24, 1 + Positive 16, sans annotation 108.
- [O] `planche_Positive.jpg` : « Positive » entoure **toutes** les feuilles d'un pied, vertes et saines comme tachées ou jaunies (ex. train e4faaaed : feuille tachée et feuilles vertes, même classe). C'est une classe « feuille », pas « feuille malade ».
- [O] `planche_1.jpg` et `planche_1_Positive.jpg` : « 1 » entoure une grande feuille au premier plan, tantôt très atteinte (train 97e03b30, test 34ba1ac5, valid 2b821dca), tantôt entièrement verte (train 41c43741, dc4fe847, 7777467e). Aucun sens sanitaire constant.
- [O] `planche_object.jpg` : « object » = traits horizontaux de quelques pixels de haut, artefacts d'annotation sans objet visible.
- [O] `planche_sans_annotation.jpg` : 108 photos de feuilles vues d'en dessous, sans aucune étiquette.

**Décision : Laguna est inutilisable comme test « de loin » étiqueté** (critère non rempli : aucune étiquette saine / malade, ni par image ni par feuille). [H] Ce projet est un jeu de segmentation de feuilles ; « Positive » et « 1 » semblent être deux passes d'annotation de « feuille ». Rien n'est figé. Ne pas étiqueter ces photos à la main (règle du projet).

### 3.2 Alternative proposée (non figée, en attente de l'accord de l'orchestrateur)

[O] Les zips Mindanao ont des polygones `positive` / `negative` dont le sens est constant sur les planches `test_de_loin/apercu_mindanao_*.jpg` (rouge positive = feuilles jaunies ou nécrosées d'un pied atteint ; vert negative = feuilles vertes) :
- `roamer_feuilles_fusarium_leaf.zip` : 229 images (positive 618, negative 698 polygones ; 191 images ont les deux classes) ;
- `roamer_feuilles_moko_leaf.zip` : 182 images (positive 521, negative 310).
[O] Les noms d'origine sont des `color_frame_…` : ce sont des **images extraites de vidéos**, d'où un fort risque de quasi-doublons entre images voisines.

Proposition : figer **`roamer_feuilles_moko_leaf.zip`** comme test « de loin » et réserver `roamer_feuilles_fusarium_leaf.zip` au développement « de loin » (découpage par jeu, donc par tournage). Règle :
- unité : la feuille (polygone), découpée sur son rectangle englobant (avec le masque disponible pour qui veut l'utiliser) ; étiquette positive = malade, negative = saine ; secondairement, l'image (pied) : malade si au moins une feuille positive ;
- sélection : toutes les feuilles de polygone d'au moins 32 × 32 px ; une image par groupe de quasi-doublons (dHash ≤ 10 bits et vignette ≤ 5 sur 255, 8 symétries), en gardant la première par ordre de nom ; contrôle de fuites contre toutes les données (y compris le zip fusarium) ;
- réserve : la maladie (moko, bactérienne ; flétrissement) n'est aucune des classes de la v2 : seule la mesure saine / malade a un sens. [H] Si un agent a déjà ouvert le zip moko (le brief le classait en développement), ce test n'est plus aveugle : à confirmer par l'orchestrateur.

### 3.3 Décision de l'orchestrateur (8 novembre, vers 23 h 45)

[S] Message de l'orchestrateur : Laguna écarté ; moko et fusarium restent du développement (déjà donnés à vue-de-loin), l'alternative 3.2 est abandonnée. Le test « de loin » sera `roamer_feuilles_leaf_segmentation.zip` (ROAMER Mindanao, environ 1 228 images, polygones positive / negative), pas encore téléchargé, vu par personne. À son arrivée, sans modèle : planche, règle (unité feuille et unité image ou pied, dédoublonnage des images de vidéo voisines), fuites sous 8 symétries contre tous les autres zips `roamer_*` et toutes les données de développement, retrait de tout recoupement, gel de la liste et de son SHA-256.

### 3.4 Règle du test « de loin » (écrite avant l'arrivée du zip)

Script : `out/maladies/equipe/evaluateur/test_de_loin/figer_test.py` (aucun modèle).
1. Étiquettes : polygones `positive` = feuille malade, `negative` = feuille saine ; catégorie racine ignorée ; toute autre catégorie signalée et ignorée. Si la planche montre que positive / negative n'ont pas ce sens, rien n'est figé et je préviens l'orchestrateur.
2. Fuites : chaque image, sous ses 8 symétries, contre les références de `controle_fuites.py` : index des feuilles (retenue, plus tout BananaLSD), originaux de Banana Disease Recognition, `data/feuilles_v3_ajouts`, `data/test_khadavy`, **tous** les zips `data/roboflow_maladies/*.zip` et `nouveaux/*.zip` (donc tous les autres `roamer_*`, Laguna compris), sauf `banana_buddy` (test de la v5, interdit). dHash ≤ 10 bits puis vignette 16 × 16 ≤ 5 sur 255 : image retirée. Paires à moins de 25 montrées sur `paires_references.jpg` ; une paire entre 5 et 25 visiblement de la même scène (même pied, même instant) est retirée aussi, et notée.
3. Dédoublonnage des images de vidéo : mêmes seuils entre images du zip (8 symétries) ; de plus, si les noms d'origine portent un numéro d'image de vidéo, les images d'une même séquence à au plus N numéros d'écart sont regroupées. N est fixé d'après les noms seuls (pas les étiquettes), avant le gel, et noté ici. Composantes connexes ; une image par groupe : celle qui a le plus de feuilles retenues, puis la première par nom d'origine.
4. Unités : **feuille** = polygone dont le rectangle englobant fait au moins 32 × 32 px (classe = positive / negative) ; **image (pied)** = malade si au moins une feuille positive retenue, saine si seulement des negative ; images sans feuille retenue exclues.
5. Gel : `test_de_loin/liste.csv` (une ligne par unité : unite, image, origine, sha256, id_annotation, classe_vraie, rectangle) et `test_de_loin/empreintes.json` (SHA-256 du zip, de liste.csv). Après le gel, plus aucune modification ; les mesures ne se font qu'à la demande de l'orchestrateur.

### 3.5 Précision de la règle 3.4 (même scène), fixée avant le gel, sans lire les étiquettes

[O] Noms d'origine `color_frame_<8 hex>` : pas de numéro d'image, donc N sans objet (pas de regroupement par séquence).
[M] `test_de_loin/diagnostic_doublons.py` : aucune paire interne à écart de vignette ≤ 20 (8 symétries, dHash ≤ 16) ; 3 paires ≤ 25, 22 ≤ 30. Planches `diagnostic_paires_*.jpg` : parmi les paires à 20 à 30, deux sont visiblement la même scène (écarts 20,7 et 28,7), les autres non. L'écart de vignette ne suffit donc pas pour les images de vidéo voisines.
[M] `test_de_loin/scenes.py` (points ORB, homographie RANSAC, sans modèle appris) sur 10 532 paires présélectionnées (10 plus proches voisines par vignette, plus les paires ≤ 25) : 9 paires à ≥ 15 points cohérents, 3 à ≥ 30. Les deux paires « même scène » ci-dessus ont 596 et 40 points ; les paires de vignette proche mais de scène différente en ont 0 à 6. Planches `scenes_inliers_*.jpg` : entre 15 et 25 points, mélange de même scène et de scènes différentes ; sous 15, scènes différentes en grande majorité.
Règle retenue (prudente : mieux vaut retirer quelques images distinctes que garder des quasi-doublons) :
- même scène en interne = vignette ≤ 5 (copie, 8 symétries) **ou** au moins **15** points ORB cohérents (paires présélectionnées comme ci-dessus) ; composantes connexes ; une image par groupe (règle 3.4) ;
- fuite = vignette ≤ 5 contre toutes les références (8 symétries) **ou** au moins 15 points ORB cohérents avec une image d'un autre zip `roamer_*` (présélection : 10 plus proches voisines par vignette parmi les images roamer, plus toutes celles à écart ≤ 25) -> image retirée du test.

### 3.6 Inspection du zip de test (sans modèle)

[O] 1 228 images 720 × 1280 (train 726, valid 171, test 331 dans le découpage Roboflow, sans importance ici) ; catégories `leaf` (racine), `negative`, `positive` ; 6 005 polygones (positive 3 386, negative 2 619 ; l'orchestrateur annonçait environ 4 260 / 4 348 : écart à signaler, [H] annonce faite d'après la page du projet, peut-être une autre version).
[O] Planches `test_de_loin/planche_test_de_loin_2026.jpg` et `_2027.jpg` (rouge positive, vert negative) : pieds entiers vus d'en dessous ou de côté ; les feuilles positive sont en majorité jaunies, à bords bruns ou nécrosés, les negative vertes. Le sens « positive = feuille malade » tient, avec du bruit : quelques feuilles positive paraissent vertes, et l'étiquette semble souvent donnée au pied entier (toutes ses feuilles de la même classe). La maladie n'est pas nommée : seule la mesure saine / malade a un sens. Critère 3.4.1 jugé rempli, avec cette réserve.

### 3.7 Résultat du gel : le zip leaf_segmentation est entièrement du développement, rien n'est figé

[M] `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/maladies/equipe/evaluateur/test_de_loin/figer_test.py` (journal `test_de_loin/journal_gel.txt`, bilan `test_de_loin/bilan_gel_echoue.json`, détail par image `test_de_loin/images_test_controle.csv`) :
- références : 40 986 images, plus les zips arrivés depuis (dont 3 458 images `roamer_*` pour le contrôle ORB) ;
- **les 1 228 images sont des copies exactes** (écart de vignette 0,0 pour toutes) d'images de quatre zips de développement : `roamer_feuilles_bunchytop_leaf` 521, `roamer_feuilles_healthy_leaf` 296, `roamer_feuilles_fusarium_leaf` 229, `roamer_feuilles_moko_leaf` 182 (total 1 228). Le contrôle ORB donne le même résultat (au moins 28 points cohérents pour chaque image).
- [O] Confirmé par les noms d'origine (`extra.name`) : les 1 228 noms du zip se retrouvent tous dans ces quatre zips (521 + 296 + 229 + 182). `roamer_feuilles_leaf_segmentation` est le projet réunissant les quatre projets par maladie.
- Conséquence : après retrait des fuites, il reste **0 image**. **Aucun test « de loin » n'est figé.** Les sorties ont été renommées `liste_vide_NON_FIGEE.csv` et `bilan_gel_echoue.json` pour éviter toute confusion.
- [O] Au passage : Laguna contient 142 des 143 noms de `roamer_black_sigatoka.zip` et les 139 de `roamer_bunchy_top.zip` (Laguna écarté de toute façon, 3.1).
- Zips roamer encore non recoupés par nom : `roamer2_fusarium` (450 images), `roamer2_healthy_plantes` (588), `roamer2_moko_plantes` (351), catégories `banana-tree` (détection de pieds), sans étiquette saine / malade par objet ; seul le nom du zip indiquerait l'état du pied. [H] Candidat possible pour un test « de loin » au niveau du pied (healthy = sain ; fusarium, moko = malade), si aucun agent ne les a ouverts et après le même contrôle de fuites (8 symétries et ORB) ; à décider par l'orchestrateur.

## 4. Contrôle des fuites

Outils : `test_de_loin/controle_fuites.py` (références : index des feuilles, BDR, ajouts v3, test_khadavy, tous les zips Roboflow sauf banana_buddy ; dHash + vignette, 8 symétries ; cache incrémental `references_fuites.npz`) et `test_de_loin/scenes.py` (même scène par ORB). Résultat sur leaf_segmentation : section 3.7 (100 % de recoupement avec le développement).

## 5. Journal
- 23 h 21 : lancement local des prédictions B0 (`journal_b0.txt`) et v2 (`journal_v2.txt`).
- vers 23 h 50 : v2 locale à plus de 10 s par photo (machine à 100 %, 96 photos faites) ; sur décision de l'orchestrateur, **v2 locale arrêtée** ; ses prédictions seront calculées sur GPU Kaggle avec `predire_reference.py` (mêmes logique et échantillonnage). Aucun fichier `predictions_v2_*.csv` local pour l'instant. Le B0 continue en local.
- 23 h 44 : `roamer_feuilles_leaf_segmentation.zip` reçu (167 015 706 octets ; 1 228 images 720 × 1280, catégories leaf (racine), negative, positive ; noms d'origine `color_frame_<8 hex>` uniques, sans numéro d'image ; « No image augmentation »).
- 23 h 45 : **prêt** `out/maladies/equipe/evaluateur/predictions_b0_validation.csv` (3 001 lignes).
- 23 h 48 : **prêt** `out/maladies/equipe/evaluateur/predictions_b0_bananalsd.csv` (897 lignes). `predictions_b0_dev.csv` en cours.
- Test de `eval_commun.py` sur le B0 (la v2 viendra de Kaggle) [M] :
  `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/maladies/equipe/evaluateur/eval_commun.py out/maladies/equipe/evaluateur/predictions_b0_validation.csv --json out/maladies/equipe/evaluateur/bilan_b0_validation.json` (et `--bananalsd` -> `bilan_b0_bananalsd.json`).
  - Validation (3 001) : F1 macro 3 classes 0,9551 [0,9487 ; 0,9613] ; coût 2 × 9 ratées + 10 fausses alertes = 28 (0,0093 par image) ; malades dites saines 9 / 2 001 ; fausses alertes 10 / 1 000 ; je ne sais pas 25 / 3 001 ; maladie nommée juste 1 822 / 1 861 (0,979) ; AUC de P(malade) 0,9989.
  - BananaLSD (897) : Sigatoka nommée 409 / 473 (0,865 [0,831 ; 0,893]) ; saines bien classées 84 / 90 ; fausses alertes 1 / 90 ; inconnues (Cordana, Pestalotiopsis) dites saines 2 / 334, dites Sigatoka 237 / 334 (0,710), dites non identifiée ou je ne sais pas 76 / 334 (0,228).
  - Bootstrap apparié vérifié : B0 contre lui-même, différence 0 [0 ; 0] ; B0 contre B0 où « je ne sais pas » devient « saine », coût par image −0,0053 [−0,0093 ; −0,0020] (10 000 tirages, 20 s).
- 23 h 58 : **prêts** `predictions_v2_validation.csv` (3 001), `predictions_v2_bananalsd.csv` (897), `predictions_v2_dev.csv` (3 567). [S] Origine : GPU Kaggle, carnet `affilecorentin/predictions-v2-reference`, lancé par l'orchestrateur avec `predire_reference.py` (mêmes listes et même tirage, empreintes des poids vérifiées sur Kaggle, index.csv identique, SHA-256 2d96e5e0…) ; originaux et journal dans `out/maladies/kaggle_predictions_v2/`.
  Contrôles locaux [M] : colonnes conformes ; chemins et classes vraies identiques ligne à ligne à ceux du B0 (validation, BananaLSD) ; probabilités sommant à 1 (écart ≤ 1e-6) ; `classifieur.decider` réappliqué localement aux probabilités avec `poids/seuils.json` : 0 réponse différente sur les trois fichiers ; SHA-256 local de `data/feuilles/index.csv` = 2d96e5e03e71c549…
- Mesures de référence v2 [M] (`eval_commun.py ... --contre predictions_b0_*.csv`, sorties `bilan_v2_validation.json`, `bilan_v2_bananalsd.json`) :
  - Validation : F1 macro 0,9597 [0,9533 ; 0,9658] ; coût 2 × 4 + 7 = 15 (0,0050 par image) ; malades dites saines 4 / 2 001 ; fausses alertes 7 / 1 000 ; je ne sais pas 121 / 3 001 (0,040) ; nommée juste 1 848 / 1 894 (0,976) ; cercosporiose nommée 961 / 1 000 ; fusariose nommée 887 / 1 001 ; AUC 0,9998.
  - BananaLSD : Sigatoka nommée 445 / 473 (0,941 [0,916 ; 0,959]) ; saines bien classées 86 / 90 ; fausses alertes 0 / 90 ; inconnues dites saines 0 / 334, dites Sigatoka 230 / 334 (0,689), dites fusariose 35 / 334, dites non identifiée ou je ne sais pas 69 / 334 (0,207).
  - v2 − B0, bootstrap apparié (10 000, graine 2026) : validation F1 +0,0046 [−0,0010 ; +0,0100] ; coût par image −0,0043 [−0,0090 ; 0,0000] ; BananaLSD Sigatoka nommée +0,076 [+0,048 ; +0,105] ; saines bien classées +0,022 [−0,021 ; +0,069] ; coût par image −0,0123 [−0,0234 ; −0,0033].
- 00 h 05 : précalcul des empreintes de référence terminé (40 986 images, `test_de_loin/references_fuites.npz`, sans les zips arrivés après son lancement : ils seront ajoutés par le cache incrémental au gel).
- 00 h 15 : **prêt** `predictions_b0_dev.csv` (3 567 lignes : tanzanie_2021 900, perou_2026 600, khadavy 431, tdtu 1 636) ; chemins et classes identiques ligne à ligne à `predictions_v2_dev.csv` (le tirage Kaggle est bien le même). **Les six fichiers de prédictions de référence sont prêts.**

## 6. Découpage de ROAMER Mindanao en dev_loin / val_loin (règle écrite avant le calcul)

[S] Décision de l'orchestrateur (9 novembre, nuit) : pas de test « de loin » vierge cette nuit (vue-de-loin a déjà ouvert les roamer2_*). À la place, découpage en deux moitiés. **val_loin est une validation « même robot, mêmes plantations » (optimiste), pas un test.** Les trois zips pcmqg (`roamer_black_sigatoka`, `roamer_bunchy_top`, `roamer_healthy`) ne sont pas utilisés.

Règle (script `out/maladies/equipe/evaluateur/decoupage_loin/decouper.py`, sans modèle, sans étiquette de maladie) :
1. Images : toutes les entrées d'image des fichiers COCO de sept zips : les quatre **projets** `roamer2_fusarium`, `roamer2_healthy_plantes`, `roamer2_moko_plantes`, `roamer_feuilles_bunchytop_leaf`, et les trois sous-ensembles `roamer_feuilles_fusarium_leaf`, `roamer_feuilles_moko_leaf`, `roamer_feuilles_healthy_leaf`. Identifiant : (zip, chemin dans le zip) ; nom d'origine = `extra.name`.
2. Liens (graphe non orienté) entre deux images, tous zips confondus :
   - même nom d'origine dans un même zip ;
   - copie : dHash ≤ 10 bits puis vignette 16 × 16 ≤ 5 sur 255, sous 8 symétries ;
   - même scène : au moins 15 points ORB cohérents (`test_de_loin/scenes.py`), sur les paires présélectionnées (10 plus proches voisines par vignette dans l'union, plus toutes les paires à écart ≤ 25).
3. Groupes = composantes connexes. Projet d'un groupe = projet le plus représenté parmi ses images des quatre projets (égalité : ordre alphabétique) ; un groupe sans image des quatre projets prend le projet du sous-ensemble (fusarium_leaf -> roamer2_fusarium, moko_leaf -> roamer2_moko_plantes, healthy_leaf -> roamer2_healthy_plantes) et c'est signalé.
4. Tirage, par projet : groupes triés par leur plus petit identifiant, permutés par `numpy.random.default_rng(2026)` (un générateur par projet, dans l'ordre alphabétique des projets, même graine) ; on parcourt la permutation et on met le groupe en dev_loin tant que le nombre cumulé d'images du projet en dev_loin (comptées dans les quatre projets seulement) est sous 50 % ; ensuite val_loin.
5. Sorties : `decoupage_loin/dev_loin.csv` et `val_loin.csv` (colonnes zip, image, origine, groupe, projet) pour les sept zips (une image va dans la moitié de son groupe, dans chaque zip), `decoupage_loin/bilan.json` (effectifs par zip et par moitié, nombre de groupes, liens par type, SHA-256 des deux CSV).
- Le contrôle `test_de_loin/controle_roamer2.py` (recoupements roamer2_* contre feuilles et pcmqg), lancé sur ton accord précédent, a été **arrêté avant la fin** : ta décision suivante (roamer2_* déjà ouverts, pas de test vierge) le rend sans objet. Aucun résultat n'en est tiré. Les recoupements entre roamer2 et les zips de feuilles sont mesurés par le découpage ci-dessous (liens « copie »).

### 6.1 Résultat du découpage (figé)

[M] `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/maladies/equipe/evaluateur/decoupage_loin/decouper.py` (journal `decoupage_loin/journal.txt`, bilan `decoupage_loin/bilan.json`, paires ORB `decoupage_loin/paires_orb.csv`) :
- 2 617 entrées d'image dans les 7 zips ; 1 881 groupes (705 de plus d'une image, au plus 4 images) ; liens : 707 copies, 36 « même scène » (ORB ≥ 15 sur 21 892 paires vérifiées), 0 doublon de nom.
- **Les 707 images des trois zips de feuilles (fusarium 229, moko 182, healthy 296) ont toutes une copie dans le roamer2 correspondant** (sous-ensembles confirmés) ; elles suivent donc la moitié de leur copie.
- 2 groupes mêlent deux projets (projet majoritaire appliqué) ; 0 groupe sans projet.
- Effectifs dev_loin / val_loin : roamer2_fusarium 226 / 224 ; roamer2_healthy_plantes 294 / 294 ; roamer2_moko_plantes 175 / 176 ; roamer_feuilles_bunchytop_leaf 261 / 260 ; roamer_feuilles_fusarium_leaf 118 / 111 ; roamer_feuilles_healthy_leaf 144 / 152 ; roamer_feuilles_moko_leaf 94 / 88. Groupes : 942 / 939.
- Contrôles : aucun groupe et aucune image dans les deux moitiés.
- **SHA-256** : `decoupage_loin/dev_loin.csv` = `46e4a558f06a78f6c02f964dc7161e596e4eb226b3b70d0c81273d326df4f011` ; `decoupage_loin/val_loin.csv` = `ebafc6a29d518ca0829078c42c53b705f0022f29977223203d264ff68db4bcb8`.
- **val_loin est une validation « même robot, mêmes plantations » (optimiste), pas un test.** [H] Des plantes voisines ou la même plante filmée sous un angle très différent peuvent rester de part et d'autre (ORB ne relie que les vues assez semblables). Les zips pcmqg et Laguna ne sont pas utilisés.
