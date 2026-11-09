# Fiche `vue-de-loin` : détecter les maladies sur les photos prises de loin

Agent : `vue-de-loin` (équipe maladies, 8-9 novembre 2026). Écrit seulement ici et dans `out/maladies/equipe/vue-de-loin/`.
Étiquettes : [O] observé, [S] source, [H] hypothèse, [M] mesuré (commande + fichier).

## 0. Données « de loin » disponibles (constat avant tout calcul)

[O] Présents dans `data/roboflow_maladies/nouveaux/` à 23 h 20 : `roamer_feuilles_fusarium_leaf.zip`, `roamer_feuilles_moko_leaf.zip`,
`roamer_black_sigatoka.zip`, `roamer_bunchy_top.zip`, `roamer_healthy.zip`, `roamer2_fusarium.zip`, `roamer2_healthy_plantes.zip`,
`roamer2_moko_plantes.zip`. **Absents** : `roamer_feuilles_bunchytop_leaf`, `roamer_feuilles_healthy_leaf`, `roamer_feuilles_leaf_segmentation`.
Laguna n'est pas ouvert (et pas présent dans le dossier à cette heure).

[O] Structure (script `out/maladies/equipe/vue-de-loin/inspecter.py`, sortie console) :

| Projet | Images | Format | Annotations |
| --- | --- | --- | --- |
| fusarium-leaf (feuilles) | 229 | images de vidéo du robot, 720 x 1280 (portrait) | 618 « positive », 698 « negative » |
| moko-leaf (feuilles) | 182 | idem | 521 « positive », 310 « negative » |
| Black-sigatoka | 143 | photos de téléphone, 640 x 640 | 193 « positive », 57 « negative » |
| Bunchy-top | 139 | téléphone, 640 x 640 | 834 « Positive » (aucune négative) |
| Healthy (2023) | 139 | téléphone, 640 x 640 | 859 « Negative » |
| roamer2 Fusarium wilt (plantes) | 450 | vidéo du robot, 640 x 640 (étirée) | « banana-tree » |
| roamer2 Moko (plantes) | 351 | idem | « banana-tree » |
| roamer2 Healthy (plantes) | 588 | idem | « banana-tree » |

[O] **Les 229 images de fusarium-leaf sont toutes dans roamer2 Fusarium (même nom d'origine), les 182 de moko-leaf toutes dans roamer2 Moko.**
Les projets « feuilles » sont donc une réannotation par feuille d'images déjà présentes dans les projets « plantes ». Le découpage doit être
commun aux deux. [H] Les projets à venir (healthy-leaf, bunchytop-leaf, leaf-segmentation) recoupent probablement roamer2 Healthy ;
l'évaluateur devrait vérifier qu'aucune image de Laguna ne figure dans les projets de Mindanao (je ne peux pas le faire sans ouvrir Laguna).

[O] Les noms Roboflow (`color_frame_<8 hex>`, `<uuid>`) ne portent ni ordre ni numéro de séquence : les images voisines d'une même vidéo
ne se reconnaissent qu'à leur ressemblance.

## 1. Règle de découpage développement / validation (écrite avant tout calcul de score)

1. **Unité** : l'image d'origine (nom avant `.rf.`). Une image présente dans deux projets (feuilles et plantes) est la même image.
2. **Groupes (séquences)** : descripteur = image ramenée à 32 x 32 en Lab (après remise au format 360 x 640 pour les images étirées du robot,
   640 x 640 sinon), centrée-réduite ; deux images sont liées si leur corrélation est ≥ seuil `s` ; groupe = composante connexe des liens,
   calculée séparément pour les images du robot (vidéo) et pour chaque projet de téléphone. Le seuil `s` est fixé en regardant **seulement**
   l'histogramme des corrélations au plus proche voisin (aucun score de maladie n'est calculé à ce moment) : on prend le creux entre le mode
   « quasi-doublon » et le mode « images différentes » ; à défaut, `s = 0,85`.
3. **Affectation** : chaque groupe va entier en validation si `md5(nom du plus petit membre)` modulo 100 < 30, sinon en développement
   (environ 30 % en validation, tirage reproductible, sans regarder les étiquettes). Un groupe qui pèse plus de 20 % de son projet va en développement.
4. **Contrôle de fuite** : on publie, pour chaque image de validation, sa corrélation maximale avec une image de développement ;
   au-delà de `s`, c'est une erreur du découpage.
5. **Usage** : tous les choix (taille de tuile, agrégation, seuils, masque de couleur) se font sur le **développement** ;
   la validation mesure une fois chaque méthode retenue, avec une règle écrite avant.

Résultat du découpage : section 2.

### 1 bis. Révision de la règle de groupes (avant tout score de maladie)

[M] `decoupage_etape1.py` → `out/maladies/equipe/vue-de-loin/decoupage_plus_proche_voisin.json` : pour les 1 389 images du robot,
la corrélation au plus proche voisin (32 x 32 Lab) est étalée de 0,4 à 0,92 sans creux ; aucune paire ≥ 0,925.
[O] Planche de paires (non conservée, scratchpad) : même à 0,92, les deux images montrent **des scènes différentes** de mise en page voisine.
Le descripteur global ne reconnaît donc pas les images d'une même scène : il est abandonné **avant tout calcul de score**.

**Règle révisée** : deux images d'un même projet sont de la même scène si l'appariement de points ORB (800 points, test du rapport 0,75,
homographie RANSAC à 8 px) donne au moins **`s` inliers** ; `s` est fixé sur la distribution des inliers (creux entre le bruit et les vraies
correspondances), à défaut `s = 25`. Les projets « feuilles » sont rattachés à leur projet « plantes » (mêmes images). Groupes = composantes
connexes ; l'affectation (point 3) et le contrôle (point 4, en inliers) sont inchangés.

## 3. Expériences : critères écrits avant les mesures

Notations : P(malade) = 1 − P(saine) (B0 : `modeles/maladies/maladies_v2.onnx` ; v2 : P(black_sigatoka) + P(fusarium)).
AUC = aire sous la courbe ROC (Mann-Whitney). Intervalles : bootstrap **par groupe** (1 000 tirages), 95 %.
Moko et bunchy top ne sont pas des classes du modèle : on mesure seulement « malade contre saine ».

**Jeux de mesure** (tous de Mindanao, hors Laguna) :
- *Images du robot* (niveau image) : positives = images des projets roamer2 Fusarium et Moko (plante malade dans le champ),
  négatives = images de roamer2 Healthy ; toutes au même format 360 x 640 (étirement 640 x 640 défait). [H] Une image d'un projet malade
  contient au moins une feuille malade (vrai pour 100 % des images de fusarium-leaf et moko-leaf qui ont une feuille « positive », à vérifier).
- *Feuilles du robot* (niveau feuille, oracle = polygones) : feuilles « positive » contre « negative » de fusarium-leaf et moko-leaf,
  en 720 x 1280. La comparaison se fait **dans les mêmes images**, ce qui neutralise l'écart de prise de vue entre projets.
- *Téléphone* (niveau image) : Black-sigatoka et Bunchy-top (positives) contre Healthy 2023 (négatives) ; niveau feuille sur Black-sigatoka.

**E-VDL-1 (référence, aucune décision)** : score « centre » (préparation actuelle du module : petit côté à 224, carré central, 4 vues)
et « écrasée » (image entière ramenée à 224 x 224). AUC et rappel au seuil natif (B0 : P(malade) ≥ 0,5 ; v2 : ≥ 0,3).

**E-VDL-2 (tuiles, sans réentraîner)** — hypothèse : lire l'image en tuiles puis agréger détecte mieux les images malades que le centre.
Tuiles carrées de côté f x petit côté, f ∈ {1/2, 1/3, 1/4}, pas = demi-côté, vue identité. Agrégations : maximum, moyenne des k plus
malades (k = 3, 5, 10), quantile 90 %, part des tuiles ≥ 0,5. **Choix sur le développement** : la combinaison (échelles, agrégation)
d'AUC maximale sur les images du robot ; seuil de décision = celui qui donne 10 % de fausses alertes sur les négatives du développement.
**Critère de succès (validation, mesuré une fois)** : AUC(tuiles) − AUC(centre) ≥ 0,05 sur les images du robot, avec l'intervalle à 95 %
de la différence au-dessus de 0 ; et rappel au seuil choisi supérieur à celui du centre au même taux de fausses alertes du développement.

**E-VDL-3 (zoom sur la feuille, oracle)** — hypothèse : classer chaque feuille recadrée sépare feuilles malades et saines mieux que l'image
entière. Scores par feuille : (a) carré englobant le polygone (côté = max(l, h) x 1,1), ramené à 224, 4 vues ; (b) tuiles dont ≥ 50 % de la
surface est dans le polygone, agrégées par la règle retenue en E-VDL-2 ; (c) score de l'image entière (référence, constante par image).
Succès : AUC feuille (a) ou (b) ≥ 0,65 en validation **et** ≥ AUC (c) + 0,05.

**E-VDL-4 (trouver les feuilles par les maths)** — hypothèse : un masque de feuillage (teinte verte à jaune, saturation, hors ciel et sol)
puis composantes connexes donne des recadrages qui font aussi bien que les tuiles. Mesures : (i) rappel des polygones (part des polygones
annotés couverts à ≥ 50 % par une composante retenue, développement) ; (ii) AUC image sur les images du robot, agrégation max des recadrages
ou de tuiles filtrées par le masque (tuile gardée si ≥ 50 % de feuillage). Réglages (seuils de couleur, aire minimale) sur le développement.
Succès en validation : AUC ≥ AUC(tuiles retenues en E-VDL-2) − 0,02 avec moins de tuiles lues, ou AUC supérieure de 0,03.

**E-VDL-5 (confirmation v2)** : sur un sous-échantillon de la validation (au plus 120 images, tirées par groupe), centre contre la recette
retenue avec la v2. Succès : même sens que le B0 (AUC tuiles > AUC centre).

### Consigne de l'orchestrateur (8 novembre, vers 23 h 45)

- `roamer_feuilles_leaf_segmentation.zip` devient le test « de loin » figé par l'évaluateur (Laguna inutilisable) : **jamais ouvert**
  (il n'est d'ailleurs pas encore dans le dossier) ; retiré de `commun.py`, garde-fou `assert` à l'extraction. Le développement « de loin »
  se limite à fusarium-leaf, moko-leaf, puis bunchytop-leaf et healthy-leaf à leur arrivée (et aux projets plantes et téléphone de Mindanao).
- J'avais déjà ouvert fusarium-leaf et moko-leaf (extraction, inventaire, planche de contrôle), comme prévu par ma mission.
- Processeur partagé : un seul processus de calcul à la fois, 2 fils (`cv2.setNumThreads(2)`, onnxruntime 2 fils). Le premier appariement
  ORB (8 processus) a été arrêté avant la fin et relancé en un seul processus avec 400 points par image (au lieu de 800) ;
  seuil par défaut ramené à **`s = 15` inliers** (moitié moins de points), toujours fixé d'abord sur l'histogramme des inliers.

### Arrivée de bunchytop-leaf et healthy-leaf ; réduction des calculs (avant tout score)

[O] `roamer_feuilles_bunchytop_leaf.zip` : 521 images de vidéo du robot (720 x 1280), 2 247 polygones tous « positive » (bunchy top),
aucun projet plantes correspondant (famille à part). `roamer_feuilles_healthy_leaf.zip` : 296 images, 1 611 polygones tous « negative » ;
**ses 296 images sont toutes dans roamer2 Healthy** (même nom d'origine), rattachées à cette famille.
`roamer_feuilles_leaf_segmentation.zip` et `roamer_feuilles_laguna_leaf_segmentation.zip` sont dans le dossier : **non ouverts**.

[M] Débit du B0 à 2 fils sur le processeur partagé : **175 ms par tuile** (contre 9 ms attendus), mesuré à 23 h 50. Les expériences sont
donc réduites, sans rien changer aux critères :
- **échantillon** : 100 images par projet du robot (roamer2 Fusarium, roamer2 Moko, roamer2 Healthy, bunchytop-leaf), tirées avec la graine 0
  parmi les images qui portent des polygones de feuilles ; elles servent au niveau image **et** au niveau feuille. Format commun 360 x 640 ;
- **tuiles** : f = 1/2 (pas = demi-côté, 21 tuiles) et f = 1/3 (jointives, 18 tuiles) ; f = 1/4 abandonné ; agrégations : max, top3, top5,
  top10, q90, part ≥ 0,5, moyenne ; échelles 1/2, 1/3, les deux ;
- **centre** : 4 vues (comme le module) ; **écrasée** et recadrages : vue identité seule ;
- **téléphone** (Black-sigatoka, Bunchy-top, Healthy 2023) : non lu.
Avec environ 30 % de validation, la validation compte environ 90 images malades et 30 saines : les intervalles seront larges.

### E-VDL-6 (demande de Corentin, via l'orchestrateur, 9 novembre vers 0 h 40) : architecture en deux étapes, critère écrit avant

Hypothèse : « 1) trouver les feuilles, 2) classer chaque feuille recadrée, 3) agréger » détecte mieux de loin que l'image entière ; on sépare
l'erreur de **détection de feuille** de l'erreur de **classement** grâce à l'oracle (polygones annotés).

Trois détecteurs de feuilles, même classeur (B0, carré englobant x 1,1, vue identité) et même agrégation (maximum, puis top3 en variante) :
- **oracle** : polygones annotés (borne haute de l'étape 1) ;
- **a) maths** : E-VDL-4 (masque de feuillage HSV, érosion, composantes) ;
- **b) IA** : segmenteur d'instances Mask R-CNN (torchvision), une seule classe « feuille », appris sur les polygones du **développement**
  (fusarium-leaf, moko-leaf, bunchytop-leaf, healthy-leaf ; toutes étiquettes confondues), entraîné sur Kaggle par Corentin
  (carnet préparé ici : `out/maladies/equipe/vue-de-loin/kaggle_segmenteur/`), prédictions rendues sur les images de validation.

Mesures sur la validation (images de l'échantillon, format commun) :
1. *Détection* : rappel des polygones (part des polygones annotés couverts à ≥ 50 % par une boîte détectée) et nombre de boîtes par image ;
2. *Classement* : AUC feuille avec les recadrages oracle (déjà E-VDL-3) ;
3. *Chaîne* : AUC image (malade / saine) de chaque détecteur + B0 + agrégation, comparée au centre et aux tuiles.

Critères de succès (validation) : (i) la chaîne « oracle » bat le centre d'au moins 0,05 d'AUC image — sinon l'architecture n'a pas
d'intérêt avec le classeur actuel, quel que soit le détecteur ; (ii) un détecteur réel est « candidat pour la chaîne finale » si son AUC image
est à moins de 0,03 de l'oracle **et** au moins égale à celle des tuiles retenues en E-VDL-2.

### Informations de l'orchestrateur (9 novembre, vers 0 h 45)

- [S, évaluateur] `roamer_feuilles_leaf_segmentation.zip` = réunion exacte de bunchytop-leaf, healthy-leaf, fusarium-leaf et moko-leaf : rien de neuf, non utilisé.
- [S, évaluateur] Laguna contient `roamer_black_sigatoka` et `roamer_bunchy_top` (pcmqg). Je les avais ouverts (inventaire, planche,
  descripteurs, ORB ; **aucun score de maladie**). Les trois projets téléphone pcmqg sont retirés de mes jeux (`commun.py`).
- roamer2 (plantes) : candidats au test « de loin » au niveau du pied ; je les avais déjà ouverts et lus avec le B0 (300 images),
  ce que j'ai signalé à l'orchestrateur. Rappel : les images des projets feuilles **sont** des images de roamer2.

### Décision de l'orchestrateur (9 novembre, vers 0 h 50) : découpage commun de l'évaluateur

Pas de test « de loin » vierge (tout ROAMER a été vu). **Mon découpage (sections 1 et 1 bis) est abandonné** (appariement ORB arrêté avant
la fin, aucun groupe produit) au profit de celui de l'évaluateur : `out/maladies/equipe/evaluateur/decoupage_loin/{dev_loin,val_loin}.csv`
(groupes de scènes, moitié-moitié par projet). `decoupage_evaluateur.py` le recopie dans mon `decoupage.csv` (dev_loin → développement,
val_loin → validation). Toutes les sections 3 à 6 s'entendent avec ce découpage : réglages sur **dev_loin seulement**, val_loin mesuré une
fois par méthode retenue. Les scores B0 déjà calculés (`tuiles_b0_images.npz`, calculés avant ce découpage, sans aucune AUC) ne servent
que pour leurs images de dev_loin ; pour val_loin ils sont relus tels quels (mêmes calculs, aucun réglage), une fois. Les recadrages pour
la v7 viennent de dev_loin uniquement.
[O] Aucune AUC ni aucun score de choix n'a été calculé avant cette décision (fichiers : seulement `tuiles_b0_images.npz`).

## 4. Résultats (découpage de l'évaluateur ; échantillon de 400 images du robot : 200 dev_loin, 200 val_loin ; B0)

Note de procédure : la consigne « prévenir l'orchestrateur avant de mesurer val_loin » est arrivée juste **après** les trois mesures
ci-dessous (E-VDL-1/2, E-VDL-3, E-VDL-6 oracle) ; elles ont été faites une fois, choix sur dev_loin, critères écrits avant ; je l'ai signalé.

### E-VDL-1 et E-VDL-2 : image entière contre tuiles (niveau image)

[M] `analyse_images.py` → `out/maladies/equipe/vue-de-loin/resultats_images.json` (scores : `scores_images_b0.csv`).
dev_loin : 157 images malades, 43 saines ; val_loin : 143 malades, 57 saines.

| Méthode | AUC dev | AUC val | Rappel val au seuil dev (10 % FA dev) | FA val | Rappel / FA val au seuil natif 0,5 |
| --- | --- | --- | --- | --- | --- |
| centre (module actuel, 4 vues) | 0,625 | **0,712** | 0,18 | 0,04 | 0,87 / **0,65** |
| écrasée (image entière en 224) | 0,687 | 0,711 | 0,28 | 0,02 | 0,87 / 0,67 |
| tuiles 1/2, max (choisie sur dev parmi 21 combinaisons) | 0,716 | 0,683 | 0,38 | 0,14 | 0,99 / 1,00 |

Différence d'AUC val tuiles − centre : IC95 [−0,10 ; +0,04]. **Critère E-VDL-2 non atteint : la lecture en tuiles n'améliore pas la
détection de loin avec le B0.** Le gain de dev (+0,09) ne se retrouve pas en val (choix parmi 21 combinaisons sur 43 saines : sur-ajustement).
[O] Constat important : au seuil natif, le B0 dit « malade » à **65 % des plantes saines** du robot (contre-jour, feuilles déchirées,
bords secs) : de loin, le B0 n'est pas « aveugle » comme la v2 sur Black-sigatoka, il est **non discriminant** (AUC ≈ 0,7).

### E-VDL-3 : zoom sur la feuille, oracle (niveau feuille)

[M] `feuilles_oracle.py` → `scores_feuilles_b0.csv` (1 964 feuilles d'au moins 24 px) ; `analyse_feuilles.py` → `resultats_feuilles.json`.
val_loin : 465 feuilles « positive », 512 « negative ».

| Score de la feuille | AUC dev | AUC val |
| --- | --- | --- |
| image entière (centre), la même pour toutes les feuilles de l'image | 0,532 | 0,615 |
| carré englobant la feuille (oracle), B0 | 0,568 | **0,637** |
| tuiles couvertes à ≥ 50 % par la feuille, top3 (choisi sur dev) | 0,647 | 0,548 (281 feuilles seulement : les tuiles sont plus grandes que la plupart des feuilles) |

Dans les mêmes images (val) : fusarium-leaf 0,677 (carré) contre 0,610 (image) ; moko-leaf 0,545 contre 0,525.
Différence carré − image : IC95 [−0,02 ; +0,07]. **Critère E-VDL-3 non atteint** (seuil 0,65 et + 0,05).
[H] Les étiquettes « positive » de ROAMER désignent souvent des feuilles encore vertes d'une plante atteinte (fusariose, Moko) : le symptôme
visible par feuille est faible, et le B0 n'a jamais appris le Moko ni le bunchy top.

### E-VDL-6 (partie oracle) : chaîne « trouver la feuille puis la classer » avec les polygones annotés

[M] `resultats_feuilles.json`, section `chaine_oracle_image` (4,9 feuilles par image en moyenne).

| Méthode | AUC dev | AUC val | Rappel val (seuil dev 10 % FA) | FA val |
| --- | --- | --- | --- | --- |
| centre | 0,625 | 0,710 | 0,18 | 0,04 |
| oracle, top3 des feuilles (choisi sur dev) | 0,676 | 0,714 | 0,32 | 0,07 |

Différence : IC95 [−0,06 ; +0,06]. **Critère (i) d'E-VDL-6 non atteint** : avec le classeur actuel, même une détection parfaite des
feuilles n'améliore pas l'AUC de loin. Conséquence : le goulot est le **classeur** (domaine « de loin », maladies non apprises), pas la
localisation. Le segmenteur Mask R-CNN (carnet prêt) n'a d'intérêt qu'avec un classeur réentraîné sur des recadrages « de loin ».

### E-VDL-4 : trouver les feuilles par les maths — réglage sur dev_loin

[M] `feuilles_maths.py dev` → `feuilles_maths_choix.json`, `feuilles_maths_dev.csv` (200 images dev_loin : 157 malades, 43 saines).
Masque de feuillage : teinte OpenCV 15 à 95, saturation ≥ 40, valeur ≥ 30 (vert à jaune, ni ciel ni ombre noire).

| Configuration | Couverture des polygones (dev) | AUC image dev |
| --- | --- | --- |
| composantes sans érosion, aire ≥ 1 % | 0,786 (mais les feuilles se touchent : peu de composantes, très grandes) | 0,572 (top3) |
| **composantes, érosion 9 px, aire ≥ 1 %** | 0,567 | **0,652** (top3) |
| composantes, érosion 15 px, aire ≥ 2 % | 0,384 | 0,604 (max) |
| **tuiles gardées si ≥ 50 % de feuillage, top3 (1/2 et 1/3)** | — | **0,727** |
| (rappel) tuiles brutes 1/2 max ; centre | — | 0,716 ; 0,625 |

[O] Les composantes connexes ne séparent pas les feuilles qui se recouvrent (vue de dessous, plante entière) : sans érosion, une
composante couvre souvent la plante entière ; avec érosion, les feuilles fines (bunchy top, feuilles déchirées) disparaissent.
Retenus sur dev (figés dans `feuilles_maths_choix.json`) : `comp[e9_a0.01|top3]` et `tfeuil[toutes|top3]`.
Mesure val_loin : **en attente de l'accord de l'orchestrateur** (demandé le 9 novembre vers 1 h).

### Carte de chaleur des tuiles (dev_loin seulement, aucun calcul nouveau)

[O] `carte_chaleur.py` → `out/maladies/equipe/vue-de-loin/carte_chaleur_dev.jpg` (5 plantes saines, 5 malades ; tuiles 1/3, B0).
Sur les plantes **saines**, les tuiles les plus « malades » sont le **sol** nu, les **pseudo-troncs** bruns, les **feuilles mortes
sèches** au pied et parfois le ciel blanc ; les feuilles vertes restent froides. Le B0 a appris « brun / nécrosé = malade » sur des gros
plans où toute l'image est une feuille ; de loin, le décor en est plein. C'est la cause principale des 65 % de fausses alertes, et
la raison pour laquelle le filtrage des tuiles par le masque de feuillage gagne sur dev (0,727 contre 0,716 ; à confirmer sur val).
[H] Un classeur « de loin » doit apprendre explicitement une classe « hors feuille / décor » (sol, tronc, ciel, feuilles sèches au sol),
ou ne lire que des recadrages filtrés par un masque de feuille.

### E-VDL-4 : mesure val_loin (une fois, avec l'accord de l'orchestrateur)

[M] `feuilles_maths.py val` → `out/maladies/equipe/vue-de-loin/resultats_feuilles_maths.json` (`feuilles_maths_val.csv`) ; 143 malades, 57 saines.

| Méthode figée sur dev | AUC val | Rappel val (seuil dev 10 % FA) | FA val | Lectures B0 par image |
| --- | --- | --- | --- | --- |
| composantes, érosion 9, aire ≥ 1 %, top3 | 0,676 | 0,30 | 0,09 | 2,3 |
| tuiles filtrées par le feuillage, top3 | 0,676 | 0,48 | 0,19 | 10,4 |
| (rappel E-VDL-2) tuiles brutes 1/2 max ; centre | 0,683 ; **0,712** | 0,38 ; 0,18 | 0,14 ; 0,04 | 21 ; 4 |

Couverture des polygones val (composantes) : 0,581. **Critère E-VDL-4 atteint au sens écrit** (AUC ≥ tuiles − 0,02 avec 4 à 17 fois
moins de lectures), **mais aucune variante ne dépasse le centre** (0,712). Le gain de dev du filtrage par feuillage (0,727) ne se
retrouve pas en val.

## 5. Bilan

- **Rien de ce qui a été testé sans réentraîner n'améliore la détection de loin avec le B0** sur ROAMER Mindanao : tuiles (0,683),
  zoom oracle sur les feuilles (chaîne 0,714 ; feuille 0,637), feuilles par les maths (0,676) contre centre 0,712 (val_loin, AUC image).
  Les tuiles augmentent le rappel au prix des fausses alertes, sans améliorer le classement.
- Le goulot est le **classeur**, pas la localisation : même avec les polygones annotés (détection parfaite), l'AUC ne bouge pas. Le B0
  prend le décor brun (sol, troncs, feuilles mortes) pour de la maladie et ne connaît ni le Moko ni le bunchy top.
- Recommandation pour la chaîne : garder la lecture actuelle (centre) pour les photos de loin ; ne pas adopter les tuiles ni les feuilles
  par les maths. L'architecture deux étapes reste candidate **seulement** avec un classeur qui a appris les vues de loin (v7, recadrages
  dev_loin préparés par l'orchestrateur) et une classe « décor » ; à tester alors sur dev_loin avec la chaîne oracle d'abord
  (`feuilles_oracle.py` + `analyse_feuilles.py` réutilisables), puis le segmenteur (carnet `kaggle_segmenteur/segmenteur_feuilles.ipynb`
  prêt, non lancé).
- Limites : échantillon de 400 images (100 par projet), 57 saines en validation (IC larges) ; B0 seul (v2 non confirmée, processeur saturé) ;
  étiquettes « positive » ROAMER = feuille d'une plante atteinte, symptôme souvent faible.
