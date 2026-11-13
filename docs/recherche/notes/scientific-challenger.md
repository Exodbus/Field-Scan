# Notes de scientific-challenger : hypothèses fragiles et expériences de contrôle

Mission 4 (vague 0), 7 novembre 2026. Rédacteur unique : scientific-challenger.

**Ce que ce document est.** Une liste d'hypothèses fragiles, explicites (H1 à H8 de `docs/research-brief.md`) et implicites, avec pour chacune l'expérience peu coûteuse, sur le développement, qui la confirmerait ou la réfuterait. Aucune expérience n'est lancée ici. **Tous les critères de réfutation sont des propositions** : independent-evaluator les fixe avant toute mesure (règle 3).

**Ce que ce document n'est pas.** Aucun score de comptage n'y figure. Les deux modèles de leaf-mathematician ne sont pas examinés ici (ils le seront à part).

**Lu** : `CLAUDE.md`, `docs/research-brief.md`, `docs/communication-protocol.md`, `docs/protocole_comptage_v3.md` (sections 2 et 2 bis), `v4.md` (extraits), `v5.md`, `CONTEXTE_FIELD_SCAN.md` sections 5 et 7, `docs/experiment-log.md`, `docs/consigne_annotation_jeunes_bananiers.md` (en-tête), `scripts/baseline_comptage.py` et `scripts/template_matching_comptage.py` (en-têtes et arguments), `out/comptage/baseline*/grille.csv`, `out/comptage/template*/grille.csv`, `data/drone/comptage_v5_5cm/parametres.json`, `data/drone/decoupage_comptage_v5/groupes.csv` et `rapport.txt`.

**Non ouvert** (scellé) : aucune image ni aucune ligne d'annotation des groupes `test` ou `exclu` ; ni `data/drone/comptage_v*_5cm/cg/`. Les deux calculs exploratoires ci-dessous filtrent `partie == "train"` avant toute lecture des objets.

---

## 0. Constats préliminaires (faits relevés pendant la mission)

Ces constats ont été relevés dans des fichiers existants ou par un petit calcul sans score. Ils fondent plusieurs objections de la section 2.

**C1 [O] — La résolution de Plants-bana (segmento) est probablement d'environ 11 cm/px, pas de 1,1 cm/px.**
- Le tableau 2.2 du brief indique « environ 1,1 cm/px » pour segmento ouest et est.
- Or `data/drone/comptage_v5_5cm/parametres.json`, entrée `segmento` : boîte médiane de 27 px ramenée à 3 m, facteur 2,2222. Les images ont donc été **agrandies** 2,2 fois pour atteindre 5 cm/px, ce qui donne une résolution d'origine d'environ 300 / 27 ≈ 11 cm/px.
- La valeur de 1,1 cm/px est celle des photos DJI des jeunes bananiers (`docs/protocole_comptage_v3.md`, section 2), qui viennent aussi de Plants-bana. La confusion est probable.
- Cohérent avec la planche `out/comptage_math/scientific-challenger/planche_dev_centres.jpg` (moitié droite, `segmento_ouest_0000_0.jpg`) : des taches floues, sans aucune structure de feuille.
- Conséquence : segmento ne peut servir ni pour les stries (H3) ni pour les orientations fines (H2). C'est un jeu de **taches**.

**C2 [O] — Les boîtes Roboflow de Plants-bana sont très incomplètes sur les photos DJI des jeunes bananiers.**
- Dans `data/roboflow/plants_bana_originaux.zip` (lecture du seul fichier COCO, aucune image) : DJI_0546 porte 55 boîtes `Banana`, DJI_0548 en porte 34.
- Les points manuels typés de ces deux mêmes photos en comptent 168 (163 mères, 5 rejets) et 196 (191 mères, 5 rejets) (`decoupage_comptage_v5/rapport.txt`).
- Les deux référentiels ne couvrent pas forcément la même zone (le disque de 2 000 px ne s'applique qu'aux points), mais un écart d'un facteur 3 à 6 montre que, **au moins sur des jeunes plants, une détection « sans boîte » n'est pas une fausse détection**.

**C3 [O] — Les baselines F1 0,37 et 0,36 sont des maxima de grille choisis sur MM1-MM2, sur ces mêmes carrés.**
- `out/comptage/baseline/grille.csv` : 100 combinaisons (σ, distance, seuil) à 5 cm/px. La meilleure fait 90 détections pour 83 pieds (32 vrais positifs).
- `out/comptage/template/grille.csv` : 30 combinaisons (60 avec le canal gris). La meilleure fait 116 détections (36 vrais positifs).
- Trois conséquences :
  - le réglage et la mesure sont faits sur les mêmes images, donc ces chiffres sont **optimistes** ;
  - les deux méthodes ne sont **pas au même budget** de candidats (90 contre 116) ;
  - le meilleur σ de la baseline (1,0 m) est **au bord de la grille**, ce qui la rend peut-être aussi **sous-optimale**.
- Ce sont des F1 « tous pieds » (rejets à trouver), à 5 cm/px. Une méthode mesurée « mères seules », ou à une autre résolution, ne leur est pas directement comparable.

**C4 [O + calcul] — À 1 m, le hasard réussit souvent en plantation dense.**
- Calcul sur les objets des groupes de développement (`out/comptage_math/scientific-challenger/stats_geometrie_dev.csv`, script dans le dossier temporaire de session, rien sur le test) :
  - distance médiane au plus proche voisin : 2,2 à 2,4 m pour banavista, Count (`corte`, `vols_100_022x`) et dji_0548 ; 2,5 à 2,9 m pour plantas_platano, ReforesTree, lasuiza et segmento ouest ;
  - 29 à 39 % des plants de banavista et de Count ont un voisin à moins de 2 m.
- [H, calcul approché] Pour un réseau carré de pas a, la part de la surface à moins de 1 m d'un centre vaut π / a² : environ 0,55 pour a = 2,4 m et 0,66 pour a = 2,2 m.
- Un point posé au hasard dans la canopée dense tombe donc **une fois sur deux environ** à moins de 1 m d'un centre annoté. Toute mesure « à moins de 1 m » (rappel des candidats, part des votes de H4) doit être lue par rapport à ce niveau, pas par rapport à zéro.
- Visible sur la planche (moitié gauche, `bv_bv_b_train_0000_1.jpg`) : les cercles de 1 m couvrent la majeure partie de la canopée.

**C5 [O] — Les règles d'échelle rendent les tailles vraies par construction sur le développement.**
- L'échelle de chaque jeu sans métadonnées est fixée de deux façons : soit la couronne médiane est ramenée à 3 m, soit la distance médiane au plus proche voisin est ramenée à 2,5 m (`parametres.json`).
- [O] Les médianes mesurées (taille 2,9 à 3,6 m ; plus proche voisin 2,5 à 2,6 m sur plantas_platano) le confirment : elles sont **imposées**.
- Une méthode dont l'échelle a priori vaut « couronne de 3 m » ou « pas de 2,5 m » paraîtra donc parfaitement calibrée sur le développement. Ce n'est pas une preuve qu'elle connaît l'échelle d'un jeu nouveau.

**C6 [O] — Les objets des jeux à boîtes sont tous typés `mere` par défaut** (`stats_geometrie_dev.csv`, colonne `types`). Seuls dji_0546 et dji_0548 portent des rejets (10 au total) dans le développement. La distinction mère / rejet n'est donc quasiment pas observable sur le développement.

**C7 [S, résumé de recherche web, articles non lus en entier]** — Le comptage des palmiers à huile par taches (indices de végétation, morphologie, analyse de taches) et par HOG + SVM sur images de drone est une pratique établie, avec des exactitudes annoncées de plus de 90 %. Exemples : Wang et al., « Automatic detection of individual oil palm trees from UAV images using HOG features and an SVM classifier » (PolyU, https://research.polyu.edu.hk/en/publications/automatic-detection-of-individual-oil-palm-trees-from-uav-images-/) ; https://arxiv.org/pdf/2201.02698. Une tache gaussienne (H1) ou une signature d'orientation (HOG, proche de H2 et H4) **ne sont donc pas propres au bananier**. Référence à faire vérifier par scientific-researcher.

---

## 1. Classement : risque pour le projet × coût du test

| N° | Hypothèse fragile (abrégée) | Hyp. du brief | Risque | Coût du test | Priorité |
| --- | --- | --- | --- | --- | --- |
| HF-01 | Un résultat « à moins de 1 m » est informatif | H1, H4, implicite | élevé | quelques minutes | **1** |
| HF-02 | Les baselines 0,37 / 0,36 sont la référence à battre | H1 (témoin), implicite | élevé | moins d'une heure | **1** |
| HF-04 | Les références de développement sont assez complètes pour juger une fausse détection | implicite | élevé | quelques minutes (annotations seules) | **2** |
| HF-05 | Centre de boîte, point manuel et pseudo-tronc coïncident | implicite | élevé | quelques minutes (annotations seules) | **2** |
| HF-06 | L'alignement radial vient des feuilles, pas de la tache | H2, H4 | élevé | quelques heures | **3** |
| HF-03 | La résolution de chaque jeu est connue | H7, implicite | élevé | moins d'une heure | 4 |
| HF-07 | La convergence désigne des centres, pas des rangées | H4 | moyen-élevé | quelques heures | 5 |
| HF-08 | Les stries sont visibles et propres au bananier | H3 | moyen (élevé si la méthode en dépend) | quelques heures ; volet palmiers non testable | 6 |
| HF-09 | La couleur sépare les espèces, pas les jeux | H5a, H6 | moyen | une heure | 7 |
| HF-10 | Le centre de la rosette est visible et plus clair | H5b | moyen | une à deux heures | 8 |
| HF-12 | La validation mesure la généralisation | implicite | moyen | une heure (inventaire) | 9 |
| HF-13 | Un écart de F1 sur la validation est un vrai écart | implicite | élevé | quelques minutes (calcul) | garde-fou |
| HF-11 | Ce qu'on compte sur des boîtes, ce sont des mères | implicite | moyen | non testable sur le dev | limite |
| HF-14 | Les indices décrivent une méthode de détection | H8 | moyen | non testable | décision |

Échelle du risque : **élevé** = l'hypothèse fausse invalide la mesure de plusieurs hypothèses ou la comparaison finale ; **moyen** = elle n'invalide qu'un module.

---

## 2. Fiches

Format de chaque fiche : énoncé ; pourquoi c'est fragile ; hypothèse alternative ; expérience de contrôle (données, mesure, contrôle négatif) ; critère de réfutation proposé ; coût.

### HF-01 — Un résultat « à moins de 1 m d'un centre » est informatif

- **Énoncé [H implicite].** Un rappel des candidats à 1 m (H1) ou une part de votes reçus à moins de 1 m d'un centre (H4) mesure la qualité de la méthode.
- **Fragilité.** [O + calcul, C4] En canopée dense de développement, 55 à 65 % de la surface est à moins de 1 m d'un centre annoté. Le contrôle « centres tirés au hasard dans l'image » est trop facile : il mélange sol et végétation. La différence mesurée serait alors celle entre végétation et sol, ce que l'ExG fait déjà.
- **Alternative.** La méthode concentre ses votes ou ses candidats sur la végétation, pas sur les centres.
- **Expérience E-proposée « niveaux nuls »** (aucune méthode, seulement des processus ponctuels) :
  - Données : groupes de développement à références jugées complètes. Pour commencer : bv_session_a et bv_b_train (dense), pp_lote_2 (rangs espacés), rt_flora_pluas (agroforesterie), dji_0546 dans le disque.
  - Mesures, pour chaque groupe :
    - part A₁ de la surface valide à moins de 1 m d'un centre ;
    - la même part restreinte au masque de végétation (ExG au-dessus d'un seuil d'Otsu, règle fixée avant) : A₁,veg ;
    - rappel et précision à 1 m de trois processus au **même nombre de points que la référence** : (a) points uniformes, (b) points uniformes dans le masque de végétation, (c) **points décalés d'une demi-maille** (chaque centre déplacé de a/2 dans une direction tirée au hasard, en restant dans la végétation).
  - Contrôle (c) : c'est le contrôle le plus strict. Ces points sont dans le feuillage, mais pas au centre.
- **Critère proposé.** Toute mesure de H1 ou H4 est rapportée en **excès sur (b) et (c)**, jamais en valeur brute. Pour qu'une hypothèse soit retenue, il faut un excès sur (c) supérieur à un seuil fixé par independent-evaluator (par exemple deux erreurs types de bootstrap par tuile). Si le niveau (b) dépasse déjà 0,5 sur un groupe, ce groupe ne sert pas à départager des variantes à 1 m. On ajoute alors une mesure à 0,5 m, ou une distance médiane au centre.
- **Coût.** Quelques minutes. Il faut seulement les objets et les masques ExG des tuiles de développement.

### HF-02 — Les baselines F1 0,37 / 0,36 sont la référence à battre

- **Énoncé [S : brief 2.3].** Ce sont les références pour une méthode explicite.
- **Fragilité [O, C3].**
  - Ce sont des maxima sur 100 et 30 réglages, choisis et mesurés sur MM1-MM2 (circularité).
  - Les budgets diffèrent (90 et 116 candidats pour 83 pieds).
  - Elles sont mesurées sur tous les pieds, à 5 cm/px seulement.
  - Le meilleur σ est en bord de grille.
  - Une méthode mathématique réglée honnêtement sur le développement puis mesurée sur MM part avec un handicap : elle peut « perdre » contre 0,37 tout en étant meilleure à réglage égal.
- **Alternative.** À réglage honnête et budget égal, la baseline ExG vaut moins (ou plus) que 0,37. Les deux baselines ne se distinguent pas l'une de l'autre.
- **Expérience E-proposée « baseline au même budget »** (code existant, à faire tourner par independent-evaluator ou experiment-engineer) :
  - Réglages de `baseline_comptage.py` choisis **sur le développement seulement** (ReforesTree Flora Pluas, Nestor Macias, Leonor Aspiazu, à partir des boîtes ; pour l'agroforesterie, comparer aussi le choix fait sur rt_* et celui fait sur banavista). La grille σ est étendue au-delà de 1 m, et la grille est déclarée avant.
  - Sortie : candidats classés par score, sans seuil. Rappel à 1 m en fonction du **budget k = N_réf × {0,5 ; 1 ; 1,5 ; 2 ; 3}**, et F1 à k = N_réf.
  - Même chose pour le template matching (gabarits déjà appris sur les sites d'entraînement) et pour les niveaux nuls (b) et (c) de HF-01.
  - Mesure sur la validation (MM mères seules **et** tous pieds, dji_0544, pp_100_metros, bv_b_val), une seule fois, réglages figés.
- **Critère proposé.** La référence à battre devient la courbe rappel-budget de la baseline réglée sur le développement. Une méthode explicite est « meilleure » si elle la domine à k = N_réf d'un écart supérieur à l'incertitude de HF-13, sur au moins deux validations sur quatre et sans recul notable sur les autres (règle à écrire par independent-evaluator). Les chiffres 0,37 / 0,36 restent cités, avec la mention « choisis sur MM ».
- **Coût.** Moins d'une heure de calcul sur processeur.

### HF-03 — La résolution de chaque jeu est connue (à 15-20 % près)

- **Énoncé [S : brief 2.2 et inconnue 7].** Les résolutions sont estimées par deux règles, avec une incertitude de 15 à 20 %.
- **Fragilité.**
  - [O, C1] Pour Plants-bana, le brief et `parametres.json` diffèrent d'un **facteur 10**.
  - [O, C5] Les deux règles imposent la taille de la couronne ou le pas, donc on ne peut pas vérifier l'échelle avec la même statistique.
  - [O, planche] Sur segmento ouest, les plants paraissent nettement plus petits que leurs boîtes, à vérifier : si les boîtes sont lâches, la règle des 3 m sous-estime la résolution.
  - [O, `parametres.json`] Les deux règles ne sont jamais appliquées au même jeu, donc leur accord n'a pas été mesuré.
- **Alternative.** L'erreur d'échelle réelle dépasse ±20 % sur certains jeux. H7, perturbation de ±20 %, est alors optimiste.
- **Expérience E-proposée « audit d'échelle »** :
  - Données : tous les groupes de développement à boîtes, plus dji_0546 et dji_0548, dont l'échelle est indépendante (ornières de roues, `protocole_comptage_v3.md`, section 2).
  - Mesure : appliquer **les deux** règles (couronne de 3 m **et** plus proche voisin de 2,5 m) à chaque groupe, puis rapporter le rapport des deux échelles. Sur dji_0546 et dji_0548, comparer aussi à l'échelle des ornières.
  - Contrôle : la dispersion du rapport entre groupes d'une même source (bv_session_a contre bv_b_train).
- **Critère proposé.** Si le rapport des deux règles sort de [0,8 ; 1,25] sur un groupe, l'échelle de ce groupe est déclarée « inconnue à plus de 20 % ». H7 doit alors être testée sur la plage réellement observée, et la méthode doit estimer l'échelle elle-même ou chercher sur plusieurs échelles. Sur dji_0546 et dji_0548, un écart de plus de 15 % avec les ornières invalide la règle concernée.
- **Coût.** Moins d'une heure (annotations seules).
- **Demande liée** : corriger le tableau 2.2 du brief (segmento environ 11 cm/px), après vérification par image-analyst.

### HF-04 — Les références de développement sont assez complètes pour qu'une fausse détection en soit vraiment une

- **Énoncé [H implicite].** Sur les jeux à boîtes, une détection sans boîte est une erreur.
- **Fragilité.**
  - [O, C2] 55 et 34 boîtes Roboflow contre 168 et 196 points manuels sur les mêmes photos DJI.
  - [S : brief 2.2] Les boîtes ReforesTree sont dites incomplètes, celles de lasuiza aussi par endroits, et segmento est « moins complet en zone mêlée ».
  - [S : protocole v5, section 9, remarques] banano_dense contient des doublons d'annotation. Il ne s'agit pas d'un jeu de développement, mais cela montre que les deux défauts existent sur Roboflow.
- **Alternative.** Les fausses détections mesurées sur le développement sont en partie de vrais plants non annotés. La précision y est alors sous-estimée de façon **différente selon les méthodes** : une méthode qui trouve les petits plants sera plus pénalisée.
- **Expérience E-proposée « complétude des références »** (annotations seules, aucune méthode) :
  - Données : DJI_0546 et DJI_0548, qui portent les deux référentiels (boîtes Plants-bana et points manuels).
  - Mesure : appariement à 1 m dans le disque de 2 000 px ; part des points manuels couverts par une boîte (complétude des boîtes) et part des boîtes sans point (excès).
  - Pour les autres jeux à boîtes, critère indirect déjà utilisable : la densité des boîtes par tuile comparée à la couverture végétale. Les tuiles à forte végétation et peu de boîtes sont suspectes. Le seuil est fixé avant.
- **Critère proposé.** Si la complétude des boîtes est inférieure à 0,8, la **précision** sur ce jeu n'est pas rapportée comme mesure de la méthode (rappel seul, ou tuiles certifiées complètes par un critère écrit avant). Les jeux à points (dji_*, plantas_platano, MM) deviennent les seuls juges de la précision.
- **Coût.** Quelques minutes.
- **Limite.** Pour ReforesTree, lasuiza et segmento, on ne peut pas mesurer la complétude sans annotation. Elle est consignée comme limite.

### HF-05 — Centre de boîte, point manuel et pseudo-tronc coïncident

- **Énoncé [H implicite].** Le centre d'une boîte Roboflow, le point manuel « centre de rosette » et le pseudo-tronc sont un même point à mieux que 1 m. Les annotations « point » et « boîte » mesurent la même chose.
- **Fragilité.**
  - Une boîte englobe la couronne visible, et une couronne asymétrique (feuilles cassées, voisins qui la recouvrent, vue oblique) déplace son centre.
  - Le point manuel suit une consigne (`docs/consigne_annotation_jeunes_bananiers.md`) que les annotateurs Roboflow n'ont pas.
  - H2 et H4 testent un **angle vers le centre** : un décalage systématique de 0,5 m sur un plant de 3 m de diamètre fausse l'angle de plusieurs dizaines de degrés près du centre.
- **Alternative.** Les deux conventions diffèrent de 0,3 à 1 m. Un test angulaire réussi sur des points peut échouer sur des boîtes, et inversement, sans rien dire de la méthode.
- **Expérience E-proposée** (même données que HF-04, annotations seules) :
  - Pour les paires boîte-point appariées, distribution du décalage (médiane et 90e centile, en m) ;
  - même mesure en fonction de la distance au centre de la photo (vue oblique) ;
  - contrôle : le même calcul après une permutation aléatoire des boîtes entre les deux photos, qui donne le niveau du hasard.
- **Critère proposé.** Si la médiane du décalage dépasse 0,3 m ou si le 90e centile dépasse 0,7 m, les tests angulaires de H2 et H4 se font seulement sur des références en points (dji_0546, dji_0548, plantas_platano) et les deux conventions sont rapportées séparément.
- **Coût.** Quelques minutes.

### HF-06 — L'orientation radiale vient des feuilles, pas de la forme de tache

- **Énoncé [H2, H4].** L'orientation locale (filtre orienté, tenseur de structure) pointe vers le centre parce que les feuilles rayonnent.
- **Fragilité.**
  - N'importe quelle **tache isotrope** (un disque plus vert ou plus clair que son entourage) produit un gradient radial, donc une orientation radiale ou tangentielle autour de son centre.
  - Si l'orientation est calculée à une échelle comparable à la couronne, H2 et H4 ne mesurent que H1 sous un autre nom.
  - [S, C7] Les palmiers donnent la même signature.
- **Alternative.** L'alignement radial est expliqué par la tache. Les feuilles n'apportent rien de plus.
- **Expérience E-proposée « tache synthétique et demi-maille »** :
  - Données : bv_session_a (1,1 cm/px, dense), dji_0546 dans le disque (jeunes plants espacés), pp_lote_2 (rangs).
  - Mesure : l'écart angulaire de H2 (|orientation − direction du centre|, pondéré par la cohérence), en anneaux de 0,3 à 1,5 m autour de chaque centre.
  - Contrôles, sur les mêmes images et avec le **même code** :
    1. image synthétique : somme de gaussiennes isotropes placées aux centres annotés, de taille égale aux boîtes, sur le fond moyen ;
    2. image réelle passée en **filtre passe-haut** (coupure sous la largeur d'une feuille, réglée avant), pour retirer la tache ;
    3. centres décalés d'une demi-maille (HF-01, c) ;
    4. orientations mélangées entre pixels de végétation ;
    5. image à phase aléatoire (même spectre, structure détruite).
- **Critère proposé.** H2 et H4 n'apportent quelque chose au-delà de H1 que si l'alignement mesuré sur l'image réelle passe-haut dépasse **à la fois** celui de la tache synthétique et celui de la demi-maille, avec une marge fixée par independent-evaluator. Si l'alignement passe-haut tombe au niveau des orientations mélangées, la piste « orientation » est réfutée pour ce type de plantation.
- **Coût.** Quelques heures. Les contrôles 3 à 5 deviennent des générateurs dans `scripts/math_controles.py`, à écrire plus tard.

### HF-07 — La convergence désigne des centres, pas des rangées

- **Énoncé [H4].** Un vote le long des axes des feuilles concentre la preuve au centre.
- **Fragilité.**
  - Les axes des feuilles orientées le long du rang passent par **tous** les centres du rang : un vote non signé (l'orientation est définie à π près) dépose de la preuve sur toute la ligne, y compris entre les plants.
  - Les rangées, les ornières et le sol travaillé produisent des orientations alignées sans centre.
  - En plantation dense, les feuilles de quatre voisins se rejoignent dans l'interstice.
- **Alternative.** La carte de votes dessine les rangs. Ses maxima tombent à mi-chemin des plants aussi souvent qu'aux centres.
- **Expérience E-proposée** :
  - Données : pp_lote_2 et lasuiza (rangs nets), bv_b_train (dense).
  - Mesure : profil de la carte de votes **le long du rang** (direction dominante de la référence, estimée avant), en fonction de la phase (0 = centre, 0,5 = mi-chemin), moyenné sur les plants.
  - Contrôles : orientations mélangées ; image tournée de 90° (la référence tourne avec elle, et le profil doit rester le même : test d'invariance) ; tuile de végétation sans plant identifiable, s'il y en a dans le développement.
- **Critère proposé.** H4 est réfutée pour les rangs si le rapport entre le vote moyen à la phase 0 et celui à la phase 0,5 est inférieur à un seuil fixé avant (par exemple 1,5), ou s'il n'est pas meilleur qu'avec les orientations mélangées.
- **Coût.** Quelques heures, une fois le vote écrit par convergence-engineer.

### HF-08 — Les stries sont visibles et propres au bananier

- **Énoncé [H3].** Une texture fine, perpendiculaire à l'axe de la feuille, est visible à 1 à 3 cm/px et absente des palmiers.
- **Fragilité.**
  - [O, `parametres.json`] En développement, seuls banavista (1,07 à 1,13 cm/px) et les photos DJI (1,1 cm/px) sont assez fins. plantas_platano (2,6 à 2,9 cm/px), Count (environ 2,75), lasuiza (environ 3,2) sont au bord du domaine, et segmento (environ 11 cm/px, C1) est hors de portée. La résolution native de ReforesTree reste à relever.
  - [O, `parametres.json`] Les palmiers et cocotiers de Multiple tree ont une échelle d'origine estimée à **10 à 12 cm/px** (couronnes de 9 m sur 75 à 88 px ; cocotiers de 7 m sur 59 px). À cette résolution, **aucune strie n'est visible, ni de bananier ni de palmier**. Le contre-exemple « les folioles produisent aussi des stries » **ne peut pas être testé** avec les données disponibles.
  - Les feuilles de bananier ne sont pas toutes déchirées. Les jeunes feuilles et les plants jeunes ne le sont pas, d'où un biais selon l'âge.
- **Alternative.** Les stries, visibles sur un sous-ensemble de jeux, sont un indice de résolution, pas d'espèce. Une méthode qui en dépend s'effondre dès 3 cm/px.
- **Expérience E-proposée** :
  - Données : bv_session_a et dji_0546 en résolution native (disque).
  - Mesure : énergie spectrale dans une bande de période fixée avant (correspondant à l'espacement des déchirures, à sourcer par banana-morphology), en anneaux autour des centres. Comparée à des points de végétation à demi-maille, puis après dégradation à 2, 3, 5 et 10 cm/px.
  - Pour (b), histogramme de l'angle entre l'orientation des stries et la direction du centre. Contrôles : orientations mélangées, phase aléatoire.
- **Critère proposé.** (a) La résolution limite est celle où l'excès d'énergie sur la demi-maille cesse de dépasser l'intervalle du contrôle. Si cette limite est plus fine que 2 cm/px, H3 n'est pas utilisable sur la plupart des jeux, et la méthode ne doit pas en dépendre. (b) L'histogramme des angles doit différer de celui du contrôle par un test fixé avant.
- **Coût.** Quelques heures.
- **Limite consignée.** La spécificité vis-à-vis des palmiers n'est pas testable sans images de palmiers à moins de 3 cm/px. Ne pas l'affirmer. Une recherche de jeu existant reviendrait à scientific-researcher, et un téléchargement demanderait l'accord de Corentin.

### HF-09 — La couleur (et la forme) séparent les espèces, pas les jeux

- **Énoncé [H5a, H6].** Une couleur ou un indicateur de forme sépare le bananier des palmiers.
- **Fragilité.**
  - Dans le développement, palmiers et cocotiers viennent **tous** de Multiple tree (une autre caméra, une autre lumière, une autre résolution d'origine), et les bananiers d'autres jeux.
  - Une séparation par la couleur peut donc séparer des **jeux**, pas des espèces. C'est le même raccourci que celui déjà observé dans le module maladies (style de photo appris à la place de la maladie, `docs/carnet_de_donnees.md`).
  - Pour H6, le rééchantillonnage des palmiers ×2 à ×2,4 (contre ×0,2 pour banavista) change la netteté des bords, donc tout indicateur de forme.
- **Alternative.** L'attribut sépare les jeux d'origine aussi bien que les espèces.
- **Expérience E-proposée « contrôle par l'identité du jeu »** :
  - Mesurer le pouvoir séparateur (aire sous la courbe ROC d'un attribut seul) pour (i) bananier contre palmier, et (ii) **bananier du jeu X contre bananier du jeu Y** (banavista contre lasuiza, Count contre ReforesTree), au même rééchantillonnage.
  - Contrôle supplémentaire : égaliser l'histogramme de couleur par jeu, ou normaliser par la médiane de la tuile, puis répéter.
- **Critère proposé.** Si la séparation entre deux jeux de bananiers atteint ou dépasse celle entre bananier et palmier, ou si la séparation bananier-palmier s'effondre après normalisation par tuile, l'attribut est déclaré **non spécifique** de l'espèce.
- **Coût.** Une heure environ.

### HF-10 — Le centre de la rosette est visible, et plus clair

- **Énoncé [H5b, implicite pour H1 et H2].** Vu du ciel, le centre est visible (feuille cigare, jeunes feuilles claires).
- **Fragilité.**
  - En canopée dense de troisième génération, le centre est souvent recouvert par les feuilles des voisins.
  - Sur les photos brutes, la vue oblique décale le haut de la plante : [S : protocole v3, section 2 bis] le décalage vaut r × h / 40 m, soit environ 1,4 à 1,6 m pour un plant de 2,5 à 3 m au bord du disque de 2 000 px (r ≈ 22 m à 1,1 cm/px), au-delà du rayon d'appariement. La symétrie radiale est perdue.
  - En agroforesterie (CG est connu pour cela, mais c'est un jeu de test, sans détail ici), le centre peut être caché sous d'autres arbres.
- **Alternative.** Le profil radial « centre plus clair » n'existe que pour les plants isolés vus de dessus. En dense, il est plat ou inversé (les ombres).
- **Expérience E-proposée** :
  - Données : bv_session_a et bv_b_train (photos brutes, centres connus en pixels d'origine), dji_0546 et dji_0548.
  - Mesure : profil radial de luminance et de teinte autour des centres, **stratifié** par distance au centre de la photo (trois classes fixées avant) et par densité locale (plus proche voisin à moins ou plus de 2 m).
  - Contrôles : le même profil autour des points à demi-maille ; le même profil après rotation de 180° de l'image (la vue oblique se retourne, et le profil doit suivre).
- **Critère proposé.** H5b est réfutée pour une strate si le contraste centre-anneau ne dépasse pas celui de la demi-maille. Si l'effet disparaît au-delà d'une distance au centre de la photo, le disque utile de la méthode doit être réduit en conséquence (décision écrite avant la validation).
- **Coût.** Une à deux heures.

### HF-11 — Sur des boîtes, on compte des mères

- **Énoncé [H implicite].** La cible est la mère (brief 1). Les jeux de développement à boîtes servent à régler une méthode qui comptera des mères.
- **Fragilité [O, C6].**
  - Les boîtes ne sont pas typées.
  - Le développement ne contient que 10 rejets typés (dji_0546 et dji_0548).
  - L'évaluation « mères seules » **ignore** les détections proches d'un rejet (`scripts/evaluer_comptage.py`, lignes 41 à 44, 76 à 84) : elle ne pénalise pas une méthode qui compte aussi les rejets, alors que le comptage par parcelle, lui, en est gonflé.
- **Alternative.** La méthode compte les plants visibles. Sa distinction mère / rejet est nulle et ne se voit pas dans le F1 « mères seules ».
- **Expérience.** Pas testable proprement sur le développement (10 rejets). Sur la validation (MM, 14 rejets ; dji_0544, 21 rejets), rapporter **en plus du F1** la part des détections appariées à un rejet, et l'erreur de comptage avec et sans elles.
- **Critère proposé.** Aucun avant d'avoir plus de données. **Consigné comme limite.**
- **Coût.** Nul (une colonne de plus dans l'évaluation).

### HF-12 — La validation mesure la généralisation

- **Énoncé [H implicite].** Une méthode réglée sur le développement et mesurée sur la validation est mesurée sur du « jamais vu ».
- **Fragilité [S : protocole v5, sections 2 et 9 ; carnet de données].**
  - bv_b_val vient de la même ferme que bv_session_a et bv_b_train, et le v5 y a surestimé son gain.
  - pp_100_metros vient probablement de la même ferme que pp_lote_2.
  - dji_0544 vient de la même parcelle que dji_0546 et dji_0548 (sans recouvrement d'image).
  - MM est à 2,9 km de Leonor Aspiazu.
  - Count banana plants est une autre découpe de Plants-bana, et ses parties `valid` et `test` sont contaminées.
- **Alternative.** Les écarts de validation surestiment la généralisation, surtout pour une méthode qui règle des attributs de couleur ou d'échelle propres à une ferme.
- **Expérience E-proposée.**
  - Sur le développement, **validation croisée par ferme ou jeu** (laisser un jeu de côté : banavista, plantas_platano, ReforesTree, Count, lasuiza, dji). Réglage sur les autres, mesure sur le jeu exclu, sans toucher à la validation.
  - Rapporter l'écart entre la mesure sur le jeu exclu et la mesure sur les jeux de réglage.
  - Interdiction d'utiliser `valid` et `test` de Count banana plants à quelque titre que ce soit.
- **Critère proposé.** Si l'écart entre réglage et jeu exclu dépasse l'écart attendu par HF-13, les paramètres concernés sont déclarés dépendants du jeu, et la méthode doit les estimer par image ou les rendre fixes.
- **Coût.** Une heure d'inventaire. Le calcul suit chaque méthode.

### HF-13 — Un écart de F1 sur la validation est un vrai écart

- **Énoncé [H implicite].** Comparer des variantes sur la validation départage des méthodes.
- **Fragilité [calcul approché].**
  - MM ne compte que 69 mères. Pour un rappel voisin de 0,4, l'erreur type binomiale vaut √(0,4 × 0,6 / 69) ≈ 0,06. Un écart de F1 inférieur à environ 0,1 sur MM seul n'est pas distinguable du bruit.
  - [S : protocole v5, section 9] Le F1 MM du v5 variait de 0,69 à 0,86 selon l'époque.
  - Avec 18 agents et 8 hypothèses à plusieurs paramètres, le nombre de variantes regardées sur la validation peut vite dépasser la dizaine, et la meilleure sera optimiste.
- **Expérience.** Pour chaque validation, intervalle de confiance par **bootstrap par tuile ou par carré** (et non par plant, à cause de l'autocorrélation), calculé par independent-evaluator, avec la baseline au même budget (HF-02) dans chaque tirage. Le compteur de variantes est obligatoire dans chaque E-NNN (champ déjà prévu dans le gabarit du journal).
- **Critère proposé.** Un écart n'est retenu que si l'intervalle bootstrap de la **différence appariée** (méthode − baseline, sur les mêmes tirages) exclut 0, avec une correction pour le nombre de variantes déclaré (Bonferroni ou Holm, au choix d'independent-evaluator).
- **Coût.** Quelques minutes de calcul.

### HF-14 — Les indices décrivent une méthode de détection

- **Énoncé [H8].** « Gaussiennes, formes, couleurs, stries, orientations » décrivent les étapes d'un détecteur.
- **Fragilité.** Ce sont des mots retenus d'un oral. Ils peuvent décrire une visualisation, une étape de prétraitement ou les attributs d'un classifieur appris.
- **Expérience.** Non testable avec des données. Seule source possible : Philemon lui-même ou ses diapositives (point ouvert 4 du journal).
- **Décision proposée.** Juger chaque indice **séparément**, par ablation (HF-06 à HF-10), sans chercher à reconstituer un ordre ou une fonction. Un indice qui ne passe pas ses contrôles est retiré, même s'il « vient de Philemon ».

---

## 3. Les trois expériences à faire en premier

Ordre choisi : risque élevé, coût faible, et capacité à invalider les mesures de **toutes** les autres hypothèses.

1. **Niveaux nuls et baseline au même budget (HF-01 et HF-02).**
   - Données : bv_session_a, bv_b_train, pp_lote_2, rt_flora_pluas et dji_0546 pour les niveaux nuls ; la validation figée pour la mesure finale de la baseline.
   - Ce qu'elle produit : le plancher du hasard à 1 m (uniforme, végétation, demi-maille) et la courbe rappel-budget d'une baseline réglée honnêtement.
   - Pourquoi en premier : sans elles, aucun chiffre de H1 ou H4 ne s'interprète, et la cible 0,37 est faussée par la circularité (C3).
   - Responsables suggérés : independent-evaluator (code d'évaluation), experiment-engineer (E-NNN).
2. **Conventions et complétude des références sur DJI_0546 et DJI_0548 (HF-04 et HF-05).**
   - Annotations seules, quelques minutes.
   - Ce qu'elle produit : la complétude des boîtes Plants-bana par rapport aux points, et le décalage entre centre de boîte et point manuel.
   - Pourquoi : elle décide quels jeux peuvent juger la précision et quels jeux peuvent juger un angle (H2, H4). Ces choix doivent être écrits avant tout réglage.
   - Responsable suggéré : annotation-manager (lecture des références), avec independent-evaluator pour le critère.
3. **Tache synthétique, passe-haut et demi-maille pour les orientations (HF-06).**
   - Données : bv_session_a, dji_0546 et pp_lote_2.
   - Ce qu'elle produit : la part de l'alignement radial qui ne s'explique pas par la tache.
   - Pourquoi : c'est la question qui décide si les orientations (H2, H4) et les stries (H3) méritent un module. Si l'alignement passe-haut est au niveau du contrôle, deux à trois agents peuvent être réorientés avant d'investir.
   - Responsables suggérés : orientation-engineer (mesure), scientific-challenger (générateurs de contrôle dans `scripts/math_controles.py`, sur feu vert).

En parallèle, presque sans coût : l'**audit d'échelle** (HF-03), qui ne lit que les annotations, et la correction de la résolution de segmento dans le brief.

---

## 4. Garde-fous de protocole

**Circularité**
- G1. Aucun paramètre n'est réglé sur MM, dji_0544, pp_100_metros ou bv_b_val, y compris le σ d'une baseline. Les chiffres 0,37 et 0,36 sont toujours cités avec la mention « choisis sur MM » (C3).
- G2. Une échelle a priori (couronne de 3 m, pas de 2,5 m) n'est jamais « validée » sur un jeu dont l'échelle a été fixée par cette même règle (C5). On la valide par l'autre règle, ou sur dji_0546 et dji_0548 (ornières).
- G3. Les critères angulaires et radiaux se mesurent sur des points manuels quand la convention de boîte n'est pas validée (HF-05).

**Fuites**
- G4. Count banana plants `valid` et `test` ne sont jamais utilisés, y compris comme « contrôle ». Seul `vols_100_022x` et `corte`, déjà en entraînement, restent utilisables.
- G5. Tout nouvel extrait (tuile, recadrage, patch de feuille) garde le **nom de photo d'origine** et passe `scripts/verifier_sources_communes.py` avant usage. L'empreinte dHash ne suffit pas (brief 2.4).
- G6. Les patchs de palmiers et de cocotiers viennent seulement des groupes de développement (`palmier_52000_20000`, `cocotier_0000_0899`). Les groupes de validation des palmiers (`palmier_44000_16000`, `cocotier_0900_1299`) ne servent qu'à la mesure.
- G7. banavista DJI_0542 à 0549 : même numéro que des photos de Plants-bana, mais des photos différentes (protocole v5). Le préfixe `bv_` doit être conservé partout pour éviter qu'un script mélange les deux.

**Multiplication des variantes**
- G8. Chaque E-NNN déclare le nombre de variantes déjà regardées sur la validation pour la même question. Au-delà de trois, la règle de décision passe à un critère corrigé (HF-13).
- G9. **Réserver une seconde validation** avant toute mesure. Par exemple, deux des quatre lignes de vol de bv_b_val, choisies au hasard avec la graine 2026 **avant** le premier résultat, sont mises sous scellé et ne sont mesurées qu'une fois, pour la méthode finale. Décision à prendre par Corentin, sur proposition d'independent-evaluator.
- G10. Toute comparaison se fait **au même budget de candidats** et à la même résolution d'entrée que la baseline (HF-02). Un gain obtenu avec plus de candidats n'est pas un gain.
- G11. Contrôles obligatoires pour chaque indice avant adoption : demi-maille, orientations mélangées, rotation ou miroir (le résultat ne doit pas changer), phase aléatoire, ablation de l'indice, perturbation d'échelle de ±20 % **et** sur la plage mesurée par HF-03.
- G12. Toute mesure « à 1 m » est rapportée avec son niveau nul (HF-01) dans la même ligne du tableau.

---

## 5. Registre des objections

| N° | Objection | Test de contrôle proposé | Résultat | Clôture |
| --- | --- | --- | --- | --- |
| HF-01 | Le hasard tombe à moins de 1 m d'un centre environ une fois sur deux en dense | Niveaux nuls uniforme, végétation, demi-maille | à mesurer | ouverte |
| HF-02 | Baselines choisies sur MM, budgets différents, σ en bord de grille | Baseline réglée sur le développement, courbe rappel-budget | à mesurer | ouverte |
| HF-03 | Segmento environ 11 cm/px et non 1,1 ; règles d'échelle circulaires | Audit des deux règles ; ornières de dji_0546 et dji_0548 | à mesurer | ouverte |
| HF-04 | Boîtes incomplètes (55 et 34 contre 168 et 196 points) | Complétude sur DJI_0546 et DJI_0548 | à mesurer | ouverte |
| HF-05 | Centre de boîte ≠ point manuel | Décalage boîte-point, permutation | à mesurer | ouverte |
| HF-06 | Alignement radial dû à la tache | Tache synthétique, passe-haut, demi-maille, phase aléatoire | à mesurer | ouverte |
| HF-07 | Votes sur les rangs | Profil de phase le long du rang, rotation de 90° | à mesurer | ouverte |
| HF-08 | Stries invisibles hors banavista et DJI ; palmiers non testables | Énergie de bande en fonction de la résolution | à mesurer ; volet palmiers non testable | partiellement close par une limite |
| HF-09 | Couleur et forme = identité du jeu | Séparation entre jeux de bananiers | à mesurer | ouverte |
| HF-10 | Centre caché en dense, décalé en vue oblique | Profil radial stratifié, rotation de 180° | à mesurer | ouverte |
| HF-11 | Mères et rejets non distingués en développement | Part des détections sur rejets (validation) | non testable sur le dev | close par une limite |
| HF-12 | Validation de la même ferme | Validation croisée par jeu sur le développement | à mesurer | ouverte |
| HF-13 | Petits effectifs, nombreuses variantes | Bootstrap par tuile ou par carré, correction | à mesurer | ouverte (garde-fou) |
| HF-14 | Indices = visualisation ou autre système | Ablation indice par indice | décision proposée | à décider |

---

## 6. Fichiers produits pendant cette mission

- `out/comptage_math/scientific-challenger/stats_geometrie_dev.csv` : taille des objets et plus proche voisin par groupe, uniquement pour `partie == train`. Aucune détection, aucun score.
- `out/comptage_math/scientific-challenger/planche_dev_centres.jpg` : deux tuiles de développement (`bv_bv_b_train_0000_1.jpg`, `segmento_ouest_0000_0.jpg`) avec les boîtes, leurs centres et un cercle de 1 m.
- Les scripts de calcul sont restés dans le dossier temporaire de la session (pas de `scripts/math_controles.py`, conformément au brief).

---

## C-001 — Examen des modèles A et B de leaf-mathematician (7 novembre 2026)

**Lu** : `docs/recherche/concertations/C-001.md`, `docs/recherche/modele_feuille.md`, `comptage_math/feuille.py` (classes de paramètres, rendus A et B, `fond`, `bruit`, `pics`, `apparier`, filtres A et B), `out/comptage_math/leaf-mathematician/resultats.md`, `diagnostic_signe_B.json`, la fin de `docs/recherche/notes/leaf-mathematician.md` et la décision D-003 dans `docs/experiment-log.md`.

**Rien n'a été recalculé.** Toutes les mesures citées viennent d'E-002 (synthétique). **Aucune image n'a été ouverte**, et `bv_b_val` n'a pas été touché (il est désormais scellé).

**Cadre (D-003).** L'objectif est de battre le v5 et la baseline en plantation dense ou industrielle, mères seules. Le développement dense utilisable :
- `bv_session_a`, à stratifier : la session contient une pépinière en pots [S : protocole v5, section 1], hors domaine ;
- `bv_b_train` ;
- en canopée jointive : ReforesTree `rt_flora_pluas` et `rt_nestor_macias` ;
- `vols_100_022x` et `corte` (environ 2,75 cm/px) ;
- `lasuiza` (environ 3,2 cm/px).

Les critères ci-dessous restent **proposés** : independent-evaluator les fixe (E-001).

### Faits relevés dans le code et les résultats

- **F1 [O, `feuille.py`].** Le détecteur A corrèle des gaussiennes anisotropes `gabarit_A` de même forme que celles du rendu `feuille_A`, soit σ_L = L/4 et σ_W = W/4. Ses paramètres (L = 1,25 ; W = 0,55 ; r0 = 0,25) tombent au milieu de la loi de tirage du rendu (L de 0,9 à 1,6 ; W/L de 0,33 à 0,45 ; r0 de 0,10 à 0,35).
- **F2 [O, `tirer_plant`].** Les deux rendus, A et B, partagent la même géométrie : de 5 à 9 feuilles régulièrement réparties (écart de 0,25 rad), ancrées à r0 du centre, dirigées vers l'extérieur. Le test croisé « A sur rendu B » n'est donc pas indépendant de la géométrie supposée par A.
- **F3 [O, `rendre_scene_B`, `Plant`].** Le centre synthétique est toujours **visible et marqué**, de quatre façons :
  - une feuille cigare claire de 8 cm ;
  - des pétioles qui convergent ;
  - un éclaircissement radial (`gain_coeur` de 0,10 à 0,35) ;
  - en A, un terme central `amplitude_centre` de 0 à 0,5.

  Or [O, image-analyst, C-001] le centre est caché en canopée jointive à toutes les résolutions, et [O, leaf-mathematician] le point annoté tombe souvent dans un petit vide **sombre**.
- **F4 [O, `controle_synthetique.py`].** Plants « jointifs » sur une grille de 2,3 m avec un décalage aléatoire de 0,25 m : presque un réseau parfait. Or [O, `stats_geometrie_dev.csv`] sur banavista, la distance médiane au plus proche voisin est de 2,35 à 2,44 m, mais 29 % des plants ont un voisin à moins de 2 m, ce qui est loin d'un réseau régulier.
- **F5 [O, `feuille.py`].** Le contrôle synthétique apparie à **0,5 m** (`apparier`). L'évaluation réelle se fait à **1 m**, où le niveau du hasard en dense vaut environ 0,55 (HF-01, C4).
- **F6 [M, E-002].** Le contrôle « centres au hasard » n'a été fait qu'en configuration **isolés**, sur des points de végétation à plus de 1 m de tout centre. En configuration jointifs, ces points seraient presque tous à **demi-maille** (1,15 m), et ce contrôle n'a pas été fait.
- **F7 [M, E-002].** Densité de prédictions et niveau du hasard :
  - en isolés, environ 150 prédictions pour 36 plants sur 576 m². Le hasard à 0,5 m donne une précision d'environ 36 × π × 0,25 / 576 ≈ 0,05 [calcul]. La précision de A (0,22 à 0,26) est donc au-dessus du hasard, mais 4 fois trop de pics ;
  - en jointifs, le hasard à 0,5 m donne une précision d'environ 0,14 et un rappel d'environ 0,19 pour 155 points [calcul]. A atteint 0,46 à 0,53 et 0,73 à 0,82.
- **F8 [M, `diagnostic_signe_B.json`].** Dans le rendu B, le tenseur est dominé par les bords et la nervure : Λ vaut −242 pour un plant complet et −274 sans stries. Les stries n'apportent qu'environ +30. La dérivation de B (vraisemblance von Mises « stries seules ») **ne décrit pas son propre monde synthétique**.

### Objections

**OBJ-C1 — Circularité : E-002 vérifie surtout que le filtre A retrouve les gaussiennes avec lesquelles on a peint la scène.**
- **Appui.** [O] F1, F2, F3.
- **Alternative.** Le rappel de 0,94 à 1,00 de A mesure l'accord entre le gabarit et le rendu, et non la capacité à trouver un bananier. Dès que les feuilles réelles s'écartent du profil gaussien (limbes oblongs à bords nets, lanières, pétioles visibles, feuilles pendantes), le rappel peut chuter sans que le synthétique l'ait annoncé.
- **Expérience.** Sur synthétique d'abord (gratuit, nouvelle graine), en trois variantes **déclarées d'avance**. Pour toutes, A n'est pas retouché :
  1. rendu B **sans cigare, sans pétioles, sans éclaircissement, avec a_c = 0** ;
  2. le même rendu, avec un **trou sombre** de 0,1 à 0,4 m au centre (conforme à l'[O] de leaf-mathematician) ;
  3. un rendu « hors famille » : limbes à bords nets non gaussiens, longueur tirée hors de l'intervalle de A (L de 1,6 à 2,5 m, ce qui correspond aux couronnes de 3,2 m de banavista), décalage de grille de 0,6 m.

  Ensuite, sur le **développement réel** : rappel et précision de A à 1 m au même budget que la baseline (HF-02) sur `bv_b_train`, avec les niveaux nuls de HF-01.
- **Critère proposé.** E-002 ne compte pas comme un appui à A pour le cycle 1 si le rappel de A tombe de plus de 0,2 entre le rendu d'origine et la variante 2 ou 3. Dans ce cas, seule la mesure sur le développement réel départage. Plus généralement, aucun contrôle synthétique **rendu par la famille du détecteur** ne compte comme validation : il ne vaut que comme test de non-régression du code.

**OBJ-C2 — HF-06 : A peut n'être qu'une tache à l'échelle du plant (H1).**
- **Appui.**
  - [O] Le score d'étoile S_A est la moyenne quadratique des m = 4 plus fortes réponses positives. Un disque vert isotrope de rayon de l'ordre de r0 + L donne une réponse dans **toutes** les directions, donc un S_A élevé.
  - [S, modele_feuille § 2.8] P-A3, qui compare A au laplacien isotrope, n'a pas encore été mesurée.
  - [M] En E-002, aucun témoin isotrope n'a été passé sur les mêmes scènes.
- **Alternative.** Le gain de A vient de la tache verte et non de l'anisotropie des feuilles. A-iso, qui utilise les mêmes candidats et la même suppression des non-maxima, ferait aussi bien.
- **Expérience.** Ablation **A-iso**. Le gabarit h_θ est remplacé par sa moyenne sur θ : un anneau radial de même profil u, à somme nulle. Une seconde variante est une différence de gaussiennes à l'échelle de la couronne. Le reste du pipeline est identique, et le budget de candidats aussi. Données :
  1. scènes synthétiques jointives, variantes 1 et 2 d'OBJ-C1 ;
  2. développement : `bv_b_train`, `rt_flora_pluas`, `vols_100_022x`.

  Contrôles : image à phase aléatoire, qui donne le niveau de A sur une texture sans plant ; orientations mélangées pour A, c'est-à-dire chaque gabarit tourné d'un angle aléatoire indépendant par direction (déjà prévu en P-A1).
- **Critère proposé.** L'indice « feuilles anisotropes » est retenu en dense seulement si A dépasse A-iso, au même budget, d'un écart supérieur à l'intervalle bootstrap par tuile (HF-13) sur au moins deux groupes denses sur trois. Sinon A est déclaré « tache » (H1), et la comparaison utile devient A-iso contre la baseline ExG.

**OBJ-C3 — Faux positif propre à A : la demi-maille, car le gabarit ne distingue pas la base d'une feuille de sa pointe.**
- **Appui.**
  - [O, `gabarit_A`] La gaussienne est symétrique le long de l'axe : centrée en μ = r0 + L/2, avec σ_L = L/4. Un limbe vu depuis sa **pointe** remplit le même gabarit qu'un limbe vu depuis sa base.
  - Entre deux plants espacés d'environ 2,3 m dont les feuilles se font face, le point milieu voit, dans la direction de chacun des deux plants, une bande verte allongée qui s'étend de r0 à r0 + L. Cela fait deux réponses fortes, plus celles des voisins en diagonale.
  - [S, modele_feuille § 2.7] L'auteur prévoit lui-même des pics à mi-chemin en canopée dense.
  - [O, F6] Le contrôle d'E-002 n'a pas regardé ces points.
- **Alternative.** Une part importante des fausses détections de A en jointif sont à demi-maille ou à la jonction de quatre plants. À 1 m, en dense réel, une partie d'entre elles **sera comptée comme vrai positif** (C4), ce qui gonfle la précision apparente et produit un double comptage.
- **Expérience.**
  1. Sur les sorties d'E-002 en jointif (vérité connue, sans nouveau calcul du détecteur) : histogramme de la distance de chaque fausse détection au centre le plus proche, et de sa phase dans la maille. Le mode est-il vers 1,0 à 1,3 m ?
  2. Contrôle « demi-maille » sur le synthétique jointif : S_A aux centres comparé à S_A aux milieux des paires de plus proches voisins, en remplacement des « points à plus de 1 m ».
  3. Sur le développement (`bv_b_train`, `rt_flora_pluas`) : le même rapport S_A(centre) / S_A(milieu des paires de voisins annotés), plus la **part des paires de voisins annotés qui reçoivent chacune deux détections**, ce qui signale un double comptage.
- **Critère proposé.**
  - A est déclaré **non discriminant en dense** si la médiane de S_A aux centres ne dépasse pas le 75e centile de S_A aux milieux (seuil à fixer par independent-evaluator).
  - Si plus de 30 % des fausses détections synthétiques sont entre 0,9 et 1,4 m d'un centre, la suppression des non-maxima de 0,8 m est déclarée inadaptée. Une règle « au plus une détection par cellule de Voronoï des pics forts », à pré-enregistrer, devient une variante déclarée.

**OBJ-C4 — Du synthétique isolé au jointif : ce qu'E-002 prédit pour banavista, et pourquoi c'est une borne haute.**
- **Appui.**
  - [M, E-002] En passant d'isolé à jointif, le rappel de A passe de 1,00 à 0,73-0,82, et la précision de 0,22-0,26 à 0,46-0,53. La précision monte parce qu'il y a plus de plants pour autant de fond ; ce n'est pas un gain du détecteur.
  - [O] La géométrie de banavista (couronne médiane de 3,2 m, plus proche voisin de 2,35 à 2,44 m, `stats_geometrie_dev.csv`) est **plus serrée et plus irrégulière** que le synthétique jointif (F4).
  - [O, image-analyst] Le centre est caché en canopée jointive.
  - [S, modele_feuille § 2.7] En canopée dense, l'indice v est presque uniforme (ExG saturé), et A ne répond plus que par les ombres.
- **Prédiction [H] à pré-enregistrer avant toute mesure de A sur `bv_b_train`.**
  - (a) Le rappel de A à 0,5 m est **inférieur** à 0,73. Le synthétique jointif est une borne haute : centre marqué, réseau régulier, v non saturé.
  - (b) À 1 m, la précision de A en excès sur la demi-maille (HF-01, c) est **inférieure** à son excès en jointif synthétique.
  - (c) Le rapport entre le nombre de détections et le nombre de références dépend du gain global et de l'exposition de chaque photo. Avec la règle τ × max, ce rapport varie d'une photo à l'autre plus que le nombre de références.
- **Alternative.** A en dense réel est un détecteur d'ombres entre limbes. Ses pics suivent l'éclairage, pas les plants.
- **Expérience.** Sur `bv_b_train` (photos brutes dans le disque de 2 000 px), et sur `bv_session_a` **sans** la pépinière, à exclure par une règle écrite avant (liste de photos) :
  - rappel et précision à 0,5 m et à 1 m au budget N_réf ;
  - excès sur la demi-maille ;
  - corrélation, par photo, entre le rapport détections / références et la luminance médiane ;
  - mêmes mesures sur `rt_flora_pluas` (orthomosaïque, sans vue oblique), pour séparer l'effet de l'oblique de celui de la densité.
- **Critère proposé.**
  - Si (a) ou (b) se vérifient, aucune extrapolation du synthétique vers le dense ne doit plus être faite dans les rapports.
  - Si la corrélation de (c) dépasse 0,5 en valeur absolue, A′ (seuil normalisé par le MAD) est obligatoire, et il faut y ajouter une normalisation photométrique par photo, déclarée.

**OBJ-C5 — B a échoué dans son propre monde : B′ et B″ ne sont pas encore des modèles, ce sont des corrections après coup.**
- **Appui.**
  - [M, F8] Le rappel de B est nul partout ; Λ est négatif aux centres.
  - P-B3 est réfutée en synthétique.
  - Le diagnostic du signe a été lancé **après** le contrôle.
  - B′ (signe −1) et B″ (Gabor, puis blanchiment des bords) sont conçus à partir de cet échec.
- **Alternative.** Le vote d'orientation en angle doublé, sous ses deux signes, est dominé par la géométrie des bords. Il ne porte pas l'indice « stries ». Sur image réelle, la direction des stries par rapport au centre est inconnue (P-B1 non mesurée).
- **Expérience, avant tout cycle de détection B.** Diagnostic P-B1 / P-B3 **sur le développement réel**, sans détection :
  - données : `rt_flora_pluas` (environ 1 cm/px, canopée jointive, stries nettes selon [O] leaf-mathematician) et `bv_b_train` en natif ;
  - mesure : moyenne de cos 2(φ − ψ) sur les pixels de végétation dans les anneaux de 0,4 à 1,5 m autour des centres annotés, à σ_g = λ/4 et à σ_g = W/4 ;
  - même mesure autour des **milieux des paires de voisins** (demi-maille), avec orientations permutées, et sur une image à phase aléatoire.
- **Critère proposé.**
  - B″ (stries) n'entre en cycle que si, à échelle fine, la moyenne aux centres est **positive** et dépasse celle de la demi-maille au-delà de l'intervalle bootstrap.
  - B′ (bords) n'entre en cycle que si, à échelle grossière, elle est **négative** et plus éloignée de 0 qu'à la demi-maille.
  - Si aucun des deux ne se distingue de la demi-maille, la piste « vote d'orientation » est close pour le dense (décision D-NNN).

**OBJ-C6 — Faux positifs propres à B′ : un détecteur de lignes droites.**
- **Appui [O, `noyau_B` + raisonnement].**
  - Avec sgn = −1, un point situé **sur** une ligne contrastée reçoit un vote positif de tous les pixels de la ligne, pondéré en 1/r. Le noyau n'est à moyenne nulle que pour un champ **uniforme**, pas pour une ligne isolée.
  - B′ répond donc à toute ligne droite : bords de feuilles longues, nervures, ombres portées nettes, bords de rangs, chemins, bâches.
  - En canopée dense, les bords de limbes voisins se croisent partout.
- **Alternative.** Les pics de B′ se placent aux croisements de bords, n'importe où dans la canopée, et non au centre des plants.
- **Expérience.** Sur `bv_b_train`, `lasuiza` (rangs) et `rt_flora_pluas` : part des pics de B′ situés à moins de 0,3 m d'un bord fort (gradient au-dessus du 90e centile, règle fixée avant), comparée à la même part pour des points de végétation tirés au hasard. Contrôles : image tournée de 90° (le résultat doit tourner avec elle) ; orientations mélangées.
- **Critère proposé.** B′ est rejeté si ses pics sont sur-représentés près des bords forts d'un facteur supérieur à 2 par rapport au hasard, **et** si son rappel au budget N_réf ne dépasse pas celui de A-iso.

**OBJ-C7 — Faux positifs propres à B″ : toute texture périodique de période λ, y compris la compression JPEG.**
- **Appui.**
  - [O] Les photos banavista et DJI sont des JPEG : blocs de 8 px, soit 8,8 cm à 1,1 cm/px, **en plein dans l'intervalle λ de 3 à 20 cm** du modèle.
  - [H] D'autres périodes de 3 à 20 cm peuvent exister : paillage, bâches, herbe semée en lignes, folioles de palmiers (non testable, HF-08), troncs feuillus.
  - [O, image-analyst] Les stries sont douteuses à 3 cm/px et invisibles dès 5. B″ n'est donc applicable qu'à banavista et DJI en natif, pas à `vols_100_022x` (environ 2,75 cm/px) ni à `lasuiza`.
- **Alternative.** L'énergie de Gabor de B″ mesure la grille JPEG ou une texture du fond, pas les déchirures.
- **Expérience.** Sur `bv_b_train` en natif :
  - énergie de Gabor à λ = 8 et 9 cm, sur l'image originale puis sur l'image décalée de 4 px (la phase de la grille JPEG change, celle des stries non) ;
  - spectre moyen des zones de sol nu : y a-t-il un pic à 8 px ?
  - énergie dans les anneaux autour des centres comparée à la demi-maille, en excluant les fréquences multiples de 1/8 px.
- **Critère proposé.** Si l'énergie de bande diffère de plus de 20 % entre l'image d'origine et l'image décalée, ou si le sol nu présente un pic à 8 px, la bande de Gabor de B″ doit exclure les harmoniques JPEG, par une règle écrite avant. Si, une fois ces fréquences exclues, le contraste centre / demi-maille disparaît, B″ est réfuté.

**OBJ-C8 — Règle de seuil et comparaison : les chiffres d'E-002 ne se comparent pas à ceux d'E-001.**
- **Appui.**
  - [O, `pics`] Le seuil τ = 0,25 × max de la scène rend le nombre de détections dépendant du plus fort pic de chaque image.
  - [O, F5] Appariement glouton à 0,5 m, contre 1 m dans l'évaluation commune.
  - [O, C3] La baseline 0,37 a été choisie sur MM.
  - A′ (seuil MAD) introduit un paramètre de plus, à régler.
- **Alternative.** Une différence entre A′ et le v5 au cycle 1 peut venir du point de fonctionnement (budget) et non du modèle.
- **Expérience et règle.**
  - Au cycle 1, A′, A-iso et la baseline ExG sont rapportés **(i)** en courbe rappel-budget à 1 m, avec le code d'independent-evaluator, et **(ii)** au seuil fixé **sur le développement seulement** (`bv_session_a` sans pépinière, `bv_b_train`), puis mesurés une fois sur `val_iter`.
  - Le seuil MAD de A′ est choisi par une règle écrite avant (par exemple : égaliser le nombre de détections et le nombre de références sur le développement dense).
- **Critère proposé.** « Battre le v5 » ne peut se dire qu'au point de fonctionnement pré-enregistré **et** à budget égal. Une victoire à un seul de ces deux points de lecture est rapportée comme non concluante.

**OBJ-C9 — Multiplication des variantes : A′, A-iso, B′, B″, A-Voronoï…**
- **Appui.**
  - [O] Leaf-mathematician propose déjà trois variantes, et ces objections en ajoutent deux (A-iso, règle de Voronoï).
  - [S, D-003] Il y a un plafond de variantes, fixé par independent-evaluator.
  - Le premier découpage en `val_iter` et `val_scellee` réduit la validation dense disponible.
- **Alternative.** Le meilleur des cinq sur `val_iter` est optimiste.
- **Règle proposée.**
  - Les ablations (A-iso) et les diagnostics sans détection (OBJ-C5, OBJ-C7) **ne consomment pas** de variante, car ils se mesurent sur le développement seul.
  - Seules les méthodes complètes envoyées sur `val_iter` comptent dans le plafond.
  - Au cycle 1, une seule méthode complète est envoyée sur `val_iter`, plus son ablation A-iso, qui sert de témoin et non de candidate.

### Quel modèle pour le cycle 1

**Recommandation : A′ seul comme candidat, avec son ablation A-iso comme témoin obligatoire.**

En parallèle, et sans détection : le diagnostic réel P-B1 / P-B3 (OBJ-C5) et le contrôle JPEG (OBJ-C7) sur le développement. Pas de B′ ni de B″ au cycle 1.

Raisons :
- A est le seul modèle avec un signal mesuré au-dessus du hasard, même s'il est synthétique et en partie circulaire (OBJ-C1). Son défaut principal en E-002 est la règle de seuil, et c'est précisément ce que A′ corrige.
- La question qui décide de la suite est celle d'OBJ-C2 : A vaut-il mieux qu'une tache ? A-iso y répond au même coût.
- B′ n'est pas l'indice « stries » : c'est un détecteur de lignes (OBJ-C6), et rien ne montre qu'il vaille mieux que A-iso.
- B″ n'a jamais été vu fonctionner, même en synthétique. Le diagnostic sur image réelle coûte moins qu'un cycle et dira s'il mérite le cycle 2.

**Conditions pour que A′ entre au cycle 1**, à écrire avant sa mesure :
- la règle du seuil MAD, fixée sur le développement dense ;
- les prédictions d'OBJ-C4, pré-enregistrées ;
- les contrôles de demi-maille et la vérification du double comptage (OBJ-C3), mesurés sur le développement avant tout envoi sur `val_iter` ;
- le compteur de variantes renseigné dans l'E-NNN.

### Registre (C-001)

| N° | Objection | Contrôle | Résultat | Clôture |
| --- | --- | --- | --- | --- |
| OBJ-C1 | E-002 est circulaire (rendu de la même famille que le détecteur) | Rendus sans centre marqué, centre sombre, hors famille ; mesure sur développement réel | à mesurer | ouverte |
| OBJ-C2 | A = tache (HF-06) | Ablation A-iso et différence de gaussiennes, phase aléatoire | à mesurer | ouverte |
| OBJ-C3 | Faux positifs à demi-maille et double comptage | Phase des fausses détections d'E-002 ; S_A aux centres contre milieux | à mesurer | ouverte |
| OBJ-C4 | Le synthétique jointif est une borne haute pour banavista | Prédictions (a), (b), (c) pré-enregistrées | à mesurer | ouverte |
| OBJ-C5 | B, B′ et B″ sont des corrections après coup | Signe de cos 2(φ − ψ) réel contre demi-maille | à mesurer | ouverte |
| OBJ-C6 | B′ = détecteur de lignes | Pics près des bords forts, rotation | à mesurer | ouverte |
| OBJ-C7 | B″ et la grille JPEG de 8 px | Décalage de 4 px, spectre du sol | à mesurer | ouverte |
| OBJ-C8 | Seuil τ × max, 0,5 m contre 1 m, budgets | Courbe rappel-budget, seuil fixé sur le développement | règle proposée | ouverte |
| OBJ-C9 | Plafond de variantes | Une seule candidate au cycle 1, ablations hors plafond | règle proposée | à décider (independent-evaluator) |

---

## Audit cycles 1-4 (7 novembre 2026, avant toute mesure sur une validation)

**Lu** :
- `docs/experiment-log.md`, de E-001 à E-013 ;
- `docs/recherche/test_final.md`, sections 2, 3, 5.4 et 5.6 ;
- `docs/recherche/notes/vegetation-color-engineer.md`, sections 1 et 2 ;
- `docs/recherche/notes/convergence-engineer.md`, par extraits ;
- les bilans JSON `E-006/bilan_E-006.json`, `E-008/bilan_E-008.json`, `E-010/bilan_E-010.json`, `E-012/bilan_E-012.json` et `E-013/bilan_E-013.json` ;
- les colonnes d'échelle de `data/drone/comptage_v5_5cm/tuiles.csv`, pour `bv_session_a` seulement.

**Rien n'a été recalculé.** Je n'ai ouvert ni image ni annotation de `bv_b_train`, `bv_b_val`, `val_scellee` ou du test.

### A. Faits relevés pendant l'audit

- **AF1 [O, journal, E-003, ligne « Données »] — `bv_b_train` a déjà été lu.** DJI_0800 et DJI_0804 ont servi à E-003, la mesure d'alignement réalisée par orientation-engineer avant la mesure conservatoire. C'est cette mesure qui a orienté l'équipe vers les « axes linéaires », donc vers B′.
  - [O, E-001] Le v5 et la baseline ont aussi été mesurés sur `dev_reglage`, qui contient `bv_b_train`, mais seulement en agrégat.
  - L'affirmation « personne n'a ouvert `bv_b_train` » est donc **inexacte pour deux photos**. La contamination est faible : aucun score de détection n'a été calculé, et seul le choix de la famille de modèles a été informé. Elle doit cependant être déclarée.
- **AF2 [O, `tuiles.csv` et notes de convergence-engineer, ligne 21] — Les tuiles de développement n'ont pas l'échelle de la validation.**
  - Les tuiles de `bv_session_a` sont des tuiles d'**entraînement du v5**, à facteur d'échelle aléatoire (facteurs de 0,267 à 0,314, soit 3,6 à 6,7 cm/px). Ce sont des découpes de 512 px **qui se recouvrent**.
  - La validation se lit sur des photos entières dans le disque de 2 000 px, à 5 cm/px fixes.
  - [M, E-011] 22,1 % des oubliés sont en **bord de tuile**, un régime propre aux tuiles de développement.
  - Résultat : le développement et la validation ne présentent ni la même échelle ni la même géométrie de bord.
- **AF3 [M, E-013, `bilan_E-013.json`] — Mécanisme réel du gain d'E-013.**
  - Le seuil passe de 2,24 à 1,86.
  - Les détections passent de 8 824 à 9 574 (+750, pour +373 vrais positifs et +377 faux).
  - La précision perd un point et le rappel en gagne 4,3.
  - L'erreur de comptage relative passe de **+2,0 % à +10,7 %**.
  - Sur `dev_transfert`, le mécanisme est **inverse** : 18 042 détections deviennent 17 492, et la précision monte, alors que le rappel bouge peu. Le gain de transfert ne « confirme » donc pas le même effet ; il en mesure un autre, sur des références incomplètes (lasuiza : ratio médian de 0,56, D-005).
- **AF4 [M, E-013] — d3 est d'abord un détecteur de sol, pas un attribut de bananier.** Avec une MAD de 0,020, le terme w·d̃3 agit comme un **rejet quasi dur** des candidats sur sol (constat de l'auteur). Contre l'« autre végétal », l'AUC de d3 n'est que de 0,584. Et l'AUC de 0,999 contre le sol est en partie circulaire, car la classe d'E-011 est définie par une quantité voisine.
- **AF5 [O, journal] — Les comparaisons ne portent pas sur les mêmes images.**
  - Le vote est mesuré sur `bv_session_a` seul (0,637 et 0,652).
  - La baseline ExG est mesurée sur `dev_reglage`, soit `bv_session_a` + `bv_b_train` (0,554), avec des réglages qui ne viennent pas de `bv_session_a`.
  - Le v5 est mesuré sur `bv_session_a` (0,821), où il a été entraîné.
  - Aucune baseline n'a été **réglée sur `bv_session_a` avec un budget de réglage comparable** à celui du vote. `test_final.md` § 5.6 le prévoit, mais ce n'est pas encore fait.

### B. Compte des variantes regardées sur `bv_session_a`

Toutes expériences comprises, chaque configuration ayant son seuil re-choisi sur ces mêmes données (de 15 à 200 seuils par configuration).

| Expérience | Famille | Configurations |
| --- | --- | --- |
| E-006 | A′ (canal × échelle × rayon) | 24 |
| E-007 | A″ (polarité) | 6 |
| E-008 | vote B′ (grille) + fusion A′ et vote | 18 + 5 |
| E-009 / E-009b | répulsion de Strauss, sur A′ et sur le vote | 27 + 27 |
| E-010 | extension r_max × multi-échelle | 6 |
| E-012 | recentrage et noyau | 15 |
| E-013 | descripteurs × poids | 16 (17 avec le témoin w = 0) |
| **Total** | | **environ 144 configurations** ; **87** dans la seule lignée du vote |

Deux circonstances aggravent ce compte :
- **analyse adaptative** : E-011 a classé les erreurs du vote **sur `bv_session_a`**, et E-012 et E-013 ont été conçus pour corriger ces classes, sur les mêmes images. Le choix du descripteur d3 n'est donc pas indépendant des données qui le mesurent ;
- **E-003** a utilisé 3 photos de `bv_session_a` et 2 de `bv_b_train` pour orienter le choix de la famille de modèles.

**Lecture [H, calcul approché].**
- Le paysage est plat près du sommet : 15 configurations d'E-012 à ±0,01, et une grille E-008 de 0,583 à 0,638. L'optimisme dû à la sélection, sur le sommet de 0,652, est donc plutôt de l'ordre de **0,005 à 0,02** que de 0,1.
- Le gain d'E-013 (+0,0147, avec un intervalle qui correspond à une erreur type d'environ 0,004) correspond à z ≈ 3,8. Il survit à Bonferroni sur les 16 configurations d'E-013 (seuil z ≈ 2,95) et de justesse à Bonferroni sur les 87 de la lignée (z ≈ 3,4).
- Mais ce calcul suppose des tirages bootstrap indépendants entre tuiles qui **se recouvrent** (AF2). Si l'unité réelle est la photo et non la tuile, l'erreur type est sous-estimée, et le gain n'est plus distinguable de la sélection.
- Le risque principal n'est pas l'optimisme de sélection : c'est le **déplacement de domaine** entre le développement et la validation (AF2, et session A contre session B).

### C. Failles par résultat positif

**E-008 et E-010 — vote des axes linéaires, F1 0,637.**

Les points solides [M] :
- l'écart avec le nul le plus fort (orientations mélangées, meilleur seuil, 0,369) vaut **+0,268** ;
- OBJ-C3 passe, y compris sur vols ;
- le double comptage est de 0,051 ;
- la règle de rotation passe ;
- `dev_transfert` atteint 0,546.

Les failles :
1. **Nul mal choisi pour la question qui compte.** Battre le hasard ne dit pas si le vote bat une **baseline réglée sur les mêmes images avec le même budget** (AF5). A-iso (0,423) n'est pas une baseline réglée, et ExG à 0,554 est mesuré sur d'autres images.
2. **Le canal du vote n'a pas été contrôlé.** Le champ T_feuille est calculé sur la luminance. Une partie du signal peut venir du contraste limbe éclairé contre ombre, c'est-à-dire de la direction du soleil, qui change d'une mission à l'autre : session A et session B ont été prises à des heures et des jours différents.
3. **Échelle (AF2).** r_max = 1,6 m et R_nms = 1,0 m ont été réglés sur des tuiles de 3,6 à 6,7 cm/px. Si le code utilise bien la résolution de chaque tuile, les paramètres sont cohérents en mètres. Mais l'optimum moyen sur une distribution d'échelles n'est pas forcément l'optimum à 5 cm/px fixes.
4. **Bord de tuile.** 22 % des oubliés (E-011) disparaissent sur les photos entières : on peut s'attendre à un gain de rappel en validation. Ce gain, hors méthode, bénéficie autant au v5.

**E-013 — vote + 0,25·d̃3, F1 0,652.**
1. **Effet de seuil.** Le gain vient de l'abaissement du seuil, rendu possible par le rejet du sol (AF3, AF4). Le même résultat peut s'obtenir avec une règle plus simple : rejet dur sur d3, puis seuil plus bas. Il faut en faire un témoin (T1).
2. **Surcomptage.** On passe de +2 % à +10,7 % sur `bv_session_a`. La consigne note aussi l'**erreur de comptage par parcelle**. Un gain de F1 de 0,015 contre une dégradation de 8,7 points sur le compte n'est pas un progrès net pour le bulletin.
3. **Transfert.** Le mécanisme est inverse sur `dev_transfert` (AF3), avec des références incomplètes. La « confirmation » est donc fragile : rejeter des candidats entourés de sol sur lasuiza (plantains jeunes, associés à une autre culture) peut retirer de vrais jeunes plants non annotés.
4. **Analyse adaptative** (section B) : d3 a été choisi après qu'E-011 a classé les erreurs sur les mêmes images.
5. **Validation probablement moins ouverte.** `val_scellee` vient d'une mission de cartographie de plantation dense (session B, protocole v5 § 2), a priori avec moins de sol visible que la session A, qui contient bandes et pépinière. Le levier d3 a donc moins de candidats sur sol à rejeter, alors que l'abaissement du seuil, lui, s'applique partout : risque de gagner seulement des faux positifs.

### D. Témoins à exiger avant tout envoi en validation

Tous se mesurent **sur le développement**, c'est-à-dire `bv_session_a` sans pépinière, plus `dev_transfert` en lecture seule. Aucun ne consomme de variante (`test_final.md` § 3.3 a). Aucun ne touche `bv_b_train` ni `val_scellee`.

| N° | Témoin | Question | Sur le dev ? | Critère proposé (à fixer par independent-evaluator) |
| --- | --- | --- | --- | --- |
| T1 | **Rejet dur d3 > 0,1, seul**, puis seuil du vote re-choisi | Le gain d'E-013 vient-il d'un simple rejet du sol suivi d'une baisse de seuil ? | oui | Si T1 ≥ E-013 − 0,005, la version « vote + d̃3 » n'a aucun avantage sur la règle simple ; on garde la plus simple, ou aucune (voir T5) |
| T2 | **Vote sur ExG** au lieu de la luminance (même grille réduite ; ce changement est une seule variante déclarée) | Le signal vient-il de la géométrie des feuilles ou du contraste d'éclairage ? | oui | Si F1(ExG) ≥ F1(lum) − 0,02, on retient l'ExG, plus robuste à l'éclairage ; si l'ExG s'effondre sous 0,55, le vote dépend de l'éclairage, et le risque de transfert est à déclarer |
| T3 | **Baseline ExG + maxima réglée sur `bv_session_a`** avec un budget de réglage comparable (σ, distance, seuil sur 200 quantiles, environ 90 configurations) | Le vote bat-il une baseline réglée honnêtement, sur les **mêmes** images ? | oui | L'avantage du vote doit dépasser l'IC apparié par **photo** ; sinon, le vote n'est pas meilleur qu'une tache verte réglée |
| T4 | **d3 appliqué à la baseline T3 et à A-iso** (même w, seuil re-choisi) | Le gain de d3 est-il propre au vote ? | oui | Si le gain sur T3 est ≥ celui sur le vote, d3 est un post-filtre générique et n'est pas porté au crédit du vote |
| T5 | **Lecture sans seuil** : courbe rappel-budget, F1 à k = N_réf, et erreur de comptage au seuil | Le gain d'E-013 tient-il à budget égal ? | oui | À k = N_réf, le gain doit exclure 0 ; sinon, le gain d'E-013 est un effet de point de fonctionnement |
| T6 | **Validation croisée interne** : seuil et (k, w) choisis sur une moitié des photos de `bv_session_a` (blocs de photos consécutives), mesure sur l'autre moitié, dans les deux sens | Optimisme de sélection et de seuil | oui | Si l'écart réglage − mesure dépasse 0,02, la valeur 0,652 est rapportée avec cette décote |
| T7 | **Stratification par échelle de tuile** (3,6–4,5 ; 4,5–5,5 ; 5,5–6,7 cm/px) | Le F1 dépend-il de l'échelle ? Que prédire à 5 cm/px fixes ? | oui | Rapporter le F1 de la tranche 4,5–5,5 comme prédiction pour la validation |
| T8 | **Bande de bord exclue** (régions à moins de r_max du bord de tuile non comptées, pour toutes les méthodes y compris le v5) | Écart dû aux tuiles | oui | Rapporté ; il sert à recaler la prédiction du § E |
| T9 | **Stabilité du seuil z entre photos** : corrélation, par photo, entre le rapport détections / références et la luminance médiane (OBJ-C4 c) | Le seuil absolu transfère-t-il d'une mission à l'autre ? | oui | Si \|r\| > 0,5, un seuil normalisé par photo est à pré-enregistrer avant l'envoi |
| T10 | **Déclaration E-003** : DJI_0800 et DJI_0804 retirées de `val_iter_v2` en option 1b, ou contamination déclarée | Fuite (AF1) | sans calcul | Décision à écrire avant tout cycle sur `bv_b_train` |

### E. Probabilité que la candidate batte le v5 sur `val_scellee`

**Estimation : environ 2 %, et au plus 5 %, pour « vote seul » comme pour « vote + d̃3 ».** Il s'agit du critère complet de `test_final.md` (point de fonctionnement **et** budget égal, borne unilatérale).

Arguments :
1. **Écart de niveau.** La candidate fait 0,652 sur le développement où elle a été choisie (environ 87 configurations), et 0,570 sur `dev_transfert`. Le v5 n'a pas été mesuré sur `val_scellee`, mais plusieurs repères le situent haut :
   - [S, protocole v5 § 9] 0,777 sur l'ensemble de `bv_b_val`, dont une moitié (`val_iter`) a des références incomplètes qui pénalisent sa précision (E-001 : P 0,612 sur `val_iter`) ;
   - [O, annotation-manager] les références de `val_scellee` sont complètes ;
   - [S, `test_final.md`, ligne 89] le seuil du v5 a été choisi en partie sur `bv_b_val`.

   Je m'attends donc à un v5 entre **0,78 et 0,86** sur `val_scellee` [H]. Il faudrait que la candidate gagne entre 0,13 et 0,20 de F1 en passant à une mission nouvelle. Or tout ce qu'on sait du transfert va dans l'autre sens (0,652 → 0,570).
2. **Leviers épuisés sur le développement.** La répulsion (E-009), le recentrage (E-012), la polarité (E-007) et la couleur contre l'autre végétal (E-013) sont réfutés ou marginaux. E-011 montre que le rappel est limité par les petites couronnes (oubli 0,647 contre 0,480 pour le v5) et par les grandes (0,289 contre 0,087). Aucune piste mesurée n'approche ces taux.
3. **Ce qui joue en faveur de la candidate**, et qui la maintient au-dessus de 0 : le passage aux photos entières supprime les oublis en bord de tuile (22 %), ce qui pourrait ajouter quelques points de rappel. Et le v5 est mesuré sans le bénéfice de son entraînement sur ces photos. Mais il a été entraîné sur la même ferme (session A et lignes voisines de la session B), ce qui lui profite aussi.

**Ce qui changerait l'estimation :**
- **à la hausse, nettement** :
  - le v5 mesuré sur `val_scellee` (ou sur un substitut honnête) sous 0,72, ce qui est peu plausible vu les références complètes ;
  - un nouveau levier qui ramène l'oubli des petites couronnes sous 0,5 sur le développement, avec T6 tenu ;
- **à la hausse, modérément** : T7 et T8 montrant que la candidate gagne plus de 0,05 à 5 cm/px fixes et hors bords, sans gain équivalent pour le v5 ;
- **à la baisse** : T2 (le vote dépend de la luminance), T3 (la baseline réglée est à moins de 0,03 du vote), ou T9 (seuil instable d'une photo à l'autre).

**Conséquence pratique.** Une mesure sur `val_scellee` sert surtout à **documenter H8** : quelle distance sépare une méthode explicite du détecteur appris, et pourquoi. C'est un résultat légitime (brief § 3, H8). Elle ne doit pas être présentée comme une tentative de victoire probable. `val_scellee` étant une mesure unique, il vaut mieux la dépenser sur la candidate la plus simple et la plus robuste que sur la mieux réglée.

### F. Candidate unique à envoyer, et conditions

**Candidate : le vote des axes linéaires B′ seul, dans sa configuration figée d'E-008 et E-010** (r_max 1,6 m, p = 1, R_nms 1,0 m, seuil z ≥ 2,238). Sur le canal, l'ExG remplace la luminance si T2 le justifie, et cela compte comme une variante déclarée.

**Pourquoi pas vote + d̃3 :**
- le gain (+0,015) est du même ordre que l'optimisme de sélection quand les tuiles se recouvrent ;
- son mécanisme diffère entre le développement et le transfert ;
- il dégrade l'erreur de comptage de 8,7 points ;
- son levier (le sol visible) sera probablement plus rare dans la mission de cartographie dense de `val_scellee`.

Je ne le réintroduirais que si les trois conditions suivantes sont réunies :
- T1 montre que le rejet dur ne fait pas aussi bien ;
- T5 montre un gain à budget égal ;
- T6 montre un gain qui survit à la validation croisée par blocs de photos.

**Conditions avant l'envoi**, toutes écrites et datées avant :
1. Corentin a choisi entre 1a et 1b. En 1b, la déclaration ou le retrait de DJI_0800 et DJI_0804 (T10) est écrit.
2. T3 est mesuré, et le vote bat la baseline réglée sur les mêmes images avec un IC apparié par photo qui exclut 0. Sinon, on n'envoie rien comme « méthode explicite meilleure qu'une tache ».
3. T2, T7, T8 et T9 sont mesurés. La **prédiction chiffrée** du F1 du vote sur `val_scellee` (à partir de T7 et T8) est écrite avant l'envoi, avec la prédiction du F1 du v5. Cela permet de lire l'issue comme une confirmation ou une réfutation de cette prédiction, et non comme un simple chiffre.
4. Le seuil est figé sur `bv_session_a`, ou normalisé par photo si T9 l'impose. Il n'est jamais re-choisi sur la validation.
5. L'erreur de comptage relative et l'écart au v5 sont rapportés à côté du F1, quelle que soit l'issue.

### Registre (audit cycles 1-4)

| N° | Objection | Contrôle | Résultat | Clôture |
| --- | --- | --- | --- | --- |
| AUD-1 | `bv_b_train` en partie lu (E-003, DJI_0800 et 0804) | T10 : retrait ou déclaration | sans calcul | à décider (chef d'orchestre, Corentin) |
| AUD-2 | Environ 144 configurations, dont 87 pour le vote, sur `bv_session_a`, avec analyse adaptative | T6 : validation croisée par blocs de photos | à mesurer | ouverte |
| AUD-3 | Baseline non réglée sur les mêmes images (nul mal choisi) | T3 | à mesurer | ouverte |
| AUD-4 | Gain d'E-013 = rejet du sol + baisse de seuil | T1, T4, T5 | à mesurer | ouverte |
| AUD-5 | Surcomptage de +10,7 % avec d̃3 | Rapporter l'erreur de comptage ; candidate sans d̃3 | constaté [M, E-013] | close par la décision du § F (proposée) |
| AUD-6 | Le vote dépend-il de l'éclairage (luminance) ? | T2, T9 | à mesurer | ouverte |
| AUD-7 | Échelle et bords : tuiles de 3,6 à 6,7 cm/px qui se recouvrent, contre photos entières à 5 cm/px | T7, T8 | à mesurer | ouverte |
| AUD-8 | Probabilité de battre le v5 environ 2 % | Prédiction écrite avant l'envoi | estimation [H] | à revoir après T2 à T9 |

---

## E-017 — Relecture contradictoire du pré-enregistrement (et de D-009) (7 novembre 2026, avant tout entraînement)

**Objet.** E-017 et D-009 (fin de `docs/experiment-log.md`) :
- professeur : vote B′ figé (E-008/E-010), F1 0,637 sur bv_session_a ;
- élève : resnet18 + FPN, carte de chaleur, l'architecture du v5 ;
- au plus 2 tours ;
- seuil : égaler le nombre de détections du professeur ;
- critère : +0,03 et borne basse > 0, par blocs de 7 photos ;
- témoin : la demi-maille.

**Faits relevés pour cette relecture [O].**
- **Groupes candidats** à une « réserve dense hors bv_session_a », d'après `data/drone/comptage_v5_5cm/tuiles.csv` :

  | Groupe | Tuiles |
  | --- | --- |
  | bv_b_train (DJI_0757 à 0841) | 352 |
  | segmento_ouest | 807 |
  | lasuiza | 688 |
  | vols_100_022x | 401 |
  | pp_lote_2 | 101 + 41 |
  | corte | 49 |
  | jeunes_dji_0546 et 0548 | 6 + 6 |

  - Tests : banano, segmento_est, btd.
  - Validations du v5 : bv_b_val (84), pp_100_metros (165), jeunes_dji_0544 (1).
- **Réserve non listée.** Le pré-enregistrement dit « plantations denses hors bv_session_a », sans liste : la réserve n'est donc pas encore définie.
- **Lignes de vol de la session B** (`test_final.md` § 1.2 et lignes 188 à 190 ; [O] `groupes_photos.json`) : lignes de 21 photos. La ligne 821-841 de bv_b_train est séparée de L1 (`val_scellee`) par la ligne tampon 842-861, absente des données. Pas de contact direct.
- **Option 1a ou 1b non tranchée** (`test_final.md` § 5.3 et 5.4) :
  - 1a : bv_b_train coupé en deux, une moitié devient validation ;
  - 1b : bv_b_train sert aux cycles.

  Le choix revient à Corentin, et le journal ne le consigne pas comme pris.
- **Disque de 2 000 px oublié.** Sur les photos brutes banavista (protocole v5 § 2), la zone hors du disque est ignorée à l'entraînement et rien n'y est compté. E-017 ne reprend pas cette règle pour les pseudo-étiquettes.
- **Aucune sortie encore produite.** `out/comptage_math/convergence-engineer/E-017/` et `comptage_math/eleve.py` sont absents : cette relecture précède toute mesure.

### Objections bloquantes (à amender avant l'entraînement)

**OBJ-E1 — Le témoin demi-maille ne teste rien pour un réseau convolutif.**
- Un réseau convolutif est presque équivariant par translation. Des étiquettes décalées d'un vecteur constant (la demi-maille) s'apprennent aussi facilement que les vraies : le réseau apprend « un point à environ 1,1 m de chaque rosette, toujours dans la même direction ».
- Ses détections seront alors décalées, donc mal appariées aux références **par construction**. Le témoin « échoue » dans tous les cas : il ne départage pas « le réseau apprend les cœurs » et « il apprend la densité de végétation ».
- Pour le vote, la demi-maille était un bon nul, parce que le vote ne s'entraîne pas.
- **Amendement.** Ajouter deux témoins entraînés exactement comme l'élève : même réserve, mêmes époques, même règle de seuil, même nombre de points par image.
  - **T-E1a, points au hasard dans la végétation.**
    - Positions tirées uniformément dans le masque ExG, avec la même distance minimale de 1,0 m entre points que les pics du professeur.
    - Ce témoin mesure ce que donnent à eux seuls l'a priori ImageNet, l'espacement et l'égalisation du compte.
    - Critère : l'élève dépasse T-E1a d'au moins +0,10, avec une borne basse par blocs > 0.
  - **T-E1b, professeur = baseline ExG réglée** (T3, F1 0,567).
    - Même distillation, avec un autre professeur. Ce témoin dit si le gain vient de la distillation en général ou de la géométrie du vote.
    - À rapporter : gain (élève du vote − vote) contre gain (élève de T3 − T3).
    - Si les deux gains sont du même ordre, le gain n'est pas porté au crédit du vote (H8), même si E-017 réussit.
  - Le témoin demi-maille reste comme simple contrôle du câblage, rapporté seulement. Il doit s'effondrer.

**OBJ-E2 — La réserve n'est pas listée, et plusieurs candidats posent problème.**
1. **Règle des ±3 numéros, trop courte.**
   - Avec 80 % de recouvrement longitudinal, chaque photo avance de 20 % de son emprise. Le recouvrement avec la photo i + k vaut environ 1 − 0,2·k : **40 % à k = 3**, 0 à k = 5. Il faut ±5.
   - Le recouvrement latéral se juge par lignes de vol (`groupes_photos.json`), pas par numéros.
   - En session B, la ligne tampon suffit déjà. La correction des ±3 vaut surtout pour les autres jeux.
2. **dev_transfert dans la réserve.** lasuiza, vols_100_022x et corte forment dev_transfert. Si l'élève s'entraîne sur leurs images, même sans références, la mesure de transfert devient transductive : elle ne mesure plus la généralisation.
3. **Voisins de validations et de tests.**
   - segmento_ouest est l'autre moitié de segmento_est, le test dense, qui n'est déjà plus vierge (protocole v5, ligne 97).
   - jeunes_dji_0546 et 0548 sont à 2 et 4 numéros de dji_0544, validation du v5.
   - pp_lote_2 a la même source que pp_100_metros. Les deux viennent probablement de la même ferme (protocole v5, ligne 9).
4. **bv_b_train et l'option 1a.** En 1a, une moitié de bv_b_train devient `val_iter_v2`. L'élève s'entraînerait alors, sans étiquettes, sur des images de validation, ce qui contamine cette moitié.
- **Amendement.**
  - Écrire avant l'entraînement la liste exacte des groupes et l'empreinte MD5.
  - Ma proposition de réserve :
    - **bv_b_train entier, si et seulement si Corentin retient 1b** ;
    - segmento_ouest et pp_lote_2, déclarés comme voisins de jeux déjà non vierges.
  - **Exclure** lasuiza, vols_100_022x et corte (dev_transfert reste un vrai transfert), jeunes_dji_0546 et 0548, et tout bv_b_val.
  - Exclure ±5 numéros autour des plages réservées, sur les jeux de photos en séquence.
  - Reprendre le disque de 2 000 px sur banavista : hors du disque, zone ignorée dans les pseudo-étiquettes, rien de compté.
  - Si 1a est retenu, la réserve se réduit à la moitié « cycles ». Tant que 1a ou 1b n'est pas tranché, E-017 attend.

**OBJ-E3 — Rien n'est écrit sur ce qui part sur `val_scellee` après E-017.**
- D-007 fixe une candidate unique : le vote B′. Or E-017 peut produire un élève meilleur sur bv_session_a.
- Choisir alors entre le vote et l'élève, ou envoyer les deux, après avoir vu E-017, revient à choisir sur résultat (CLAUDE.md, règle 3 ; D-008).
- **Amendement.** Écrire avant le tour 1 une règle de remplacement :
  - l'élève remplace le vote comme candidate unique si et seulement si les trois conditions suivantes sont réunies :
    - E-017 réussit selon son critère ;
    - les témoins T-E1a et T-E1b sont remplis ;
    - la seconde graine confirme (OBJ-E4) ;
  - sinon, le vote B′ figé reste la candidate.
  - `val_scellee` n'est mesurée qu'une fois, sans envoi double. L'envoi dépend toujours de la décision de Corentin entre 1a et 1b.

**OBJ-E4 — Une seule graine : la variance d'entraînement n'entre pas dans l'intervalle.**
- Le bootstrap par blocs mesure la variabilité due aux images, pas celle de l'entraînement : ordre des lots, augmentations, initialisation du décodeur.
- Pour un petit détecteur entraîné sur processeur avec quelques centaines de tuiles, un écart de 0,01 à 0,03 de F1 entre graines est plausible [H]. C'est l'ordre de la marge exigée (+0,03).
- **Amendement, séquentiel donc économe.**
  - Graine 2026 d'abord.
  - Si le critère passe, une seconde graine (2027) est entraînée avec les mêmes règles. **Le succès exige que les deux graines passent.** L'écart entre graines est rapporté.
  - Si la graine 2026 échoue, pas de seconde graine : on ne cherche pas la bonne graine.

### Objections non bloquantes (à intégrer au pré-enregistrement, ou à rapporter)

**OBJ-E5 — Le seuil « même nombre que le professeur » est sain, mais il mélange deux effets. Il faut aussi une lecture sans seuil.**
- **Biais [H].**
  - L'élève hérite de l'erreur de comptage du professeur, domaine par domaine. Le compte global, calculé sur une réserve qui mélange les domaines, compense les surcomptages des uns par les sous-comptages des autres.
  - Le compte est égalé sur les images d'entraînement, que l'élève a ajustées. Ses scores y sont plus confiants qu'ailleurs, ce qui place le seuil un peu trop haut hors de la réserve.
  - La règle empêche presque par construction tout gain de rappel global. Le gain mesurable viendra surtout du **classement** : moins de fausses détections pour le même compte. C'est sain pour attribuer le gain, à condition de le savoir.
- **Règle non supervisée préférable :** égaler le compte **sur un bloc mis de côté** (1 bloc de photos sur 5, non vu à l'entraînement), **pris dans le seul groupe dense de session B**, plus proche de `val_scellee` que la réserve mélangée.
- **Amendement.**
  - L'égalisation du compte reste la règle principale, avec ces deux corrections.
  - Deux lectures sans seuil sont rapportées pour toutes les méthodes (élève, vote, témoins) :
    - le **F1 à k = N_réf** par photo (comme T5) ;
    - la **courbe rappel-budget**.
  - Si l'élève ne gagne qu'au point de fonctionnement, et pas à k = N_réf, le gain est un effet de seuil, et c'est consigné.
  - Le seuil réglé sur bv_session_a reste rapporté, sans décider.

**OBJ-E6 — Copie et mémorisation : il faut un diagnostic, et la « dernière époque » est le point le plus exposé.**
- **Pourquoi l'élève peut copier.**
  - L'optimum exact de sa perte est de reproduire le vote, erreurs comprises.
  - Il ne le dépasse que grâce à la régularisation : un réseau apprend d'abord les motifs cohérents, et ne mémorise les étiquettes bruitées que tard [S : Arpit et al., 2017, ICML, « A closer look at memorization in deep networks »].
  - Le bruit injecté chez l'élève est ce qui lui permet de dépasser le maître [S : Xie et al., 2020, CVPR, « Self-training with Noisy Student »].
- **Le risque de la dernière époque.** Retenir la dernière époque d'un long entraînement sur peu de tuiles pousse vers la mémorisation des erreurs du vote.
- **Amendement.**
  - Fixer un nombre d'époques **modéré**, de l'ordre des 15 retenues par la validation du v5 (protocole v5, ligne 70), et non le maximum permis par les 3 h. Augmentations maintenues.
  - Rapporter le diagnostic de **désaccord** sur bv_session_a, avec les références et un appariement à 1 m :
    - fausses détections du vote supprimées par l'élève ;
    - mères oubliées par le vote et retrouvées par l'élève ;
    - nouvelles erreurs de l'élève.

    Un élève qui « gagne » sans corriger le vote dans les deux sens produit un effet de seuil (OBJ-E5).
  - Rapporter l'accord entre élève et professeur sur le bloc mis de côté. Au-delà de 0,95, c'est un signal de copie.

**OBJ-E7 — Le fond des pseudo-étiquettes contient les mères oubliées par le vote.**
- Le rappel du vote est d'environ 0,6 à 0,65 (E-011). Plus d'une mère sur trois est donc étiquetée « fond », sauf si son z tombe dans la bande ignorée [1,5 ; 2,238).
- Ce bruit asymétrique apprend à l'élève à étouffer précisément les cas difficiles, petites et grandes couronnes (E-011).
- **Amendement.**
  - Ne pas changer le tour 1, déjà figé : ce serait une variante de plus.
  - Rapporter le rappel de l'élève par classe de taille, comme dans E-011.
  - Pré-enregistrer, comme **variante déclarée** du tour 2 ou d'E-018, une zone ignorée étendue à la végétation où le vote est faible mais non nul, par exemple z ∈ [0,5 ; 1,5) dans le masque ExG.

**OBJ-E8 — Les étiquettes du tour 2 ne sont pas spécifiées.**
- « Mêmes règles » ne dit pas ce qui remplace les seuils z = 2,238 et z = 1,5 sur les scores de l'élève.
- **Amendement.** L'écrire avant le tour 1. Par exemple :
  - positifs : les détections de l'élève au seuil d'égalisation du compte ;
  - bande ignorée : les scores compris entre ce seuil et celui qui donne un compte k fois plus grand, où k est le rapport des comptes du professeur à z ≥ 1,5 et à z ≥ 2,238. Calculer k et le consigner avant le tour 1.

**OBJ-E9 — Le pipeline de mesure doit être le même, et la base de comparaison connue.**
- Mêmes tuiles, même NMS de 1,0 m, mêmes bords exclus que pour le vote. `scripts/math_evaluer.py` inchangé, avec son empreinte.
- 0,637 est le F1 du vote au seuil choisi sur bv_session_a. Hors pli, il vaut 0,632 (T6). Comparer l'élève à 0,637 le désavantage légèrement : c'est conservateur et acceptable. L'écart à 0,632 est rapporté aussi.
- La comparaison porte sur la **différence appariée** élève − vote par blocs de 7 photos, et non sur deux intervalles séparés.

**OBJ-E10 — Têtes de la diapositive (segmentation, vecteurs vers le cœur) : pas au tour 1.**
- **Pourquoi pas au tour 1.**
  - Changer à la fois les étiquettes et l'architecture rend le gain impossible à attribuer. L'identité d'architecture avec le v5 fait la force d'E-017.
  - Les étiquettes de ces têtes sont à construire :
    - la segmentation bananier/sol/autre demande un masque géométrique ;
    - les vecteurs demandent une partition, par exemple les cellules de Voronoï des pics du professeur, restreintes à la végétation.

    Ce sont des choix nouveaux, donc des variantes nouvelles.
  - SegFormer demande un téléchargement, soumis à accord.
- **Intérêt réel [H].** Les vecteurs vers le cœur visent le défaut mesuré le plus coûteux : maxima distincts à environ 1,3 m (E-012) et couronnes jointives.
- **Amendement : E-018**, pré-enregistré après le verdict d'E-017.
  - Même squelette resnet18.
  - Deux têtes ajoutées :
    - décalage : vecteur vers le pic du professeur de sa cellule de Voronoï, dans le masque de végétation ;
    - segmentation à 3 classes, à partir de l'ExG et des cellules.
  - Centres obtenus par vote des vecteurs.
  - Comparaison appariée à l'élève d'E-017, avec les mêmes témoins.

**OBJ-E11 — Le développement (bv_session_a) est déjà usé.**
- Environ 144 configurations y ont été évaluées (audit, § B). Y comparer l'élève au vote reste légitime, sans aucun réglage de l'élève dessus, mais chaque regard s'ajoute au compte.
- **Amendement.**
  - Déclarer le nombre de regards d'E-017 : élève (2 graines), tour 2, T-E1a, T-E1b, demi-maille, soit au plus 7.
  - Aucune nouvelle variante d'élève sur bv_session_a sans nouveau pré-enregistrement.
  - Si dev_transfert est exclu de la réserve (OBJ-E2), il devient la meilleure lecture de généralisation : la rapporter en priorité.

### Probabilité [H] que la chaîne atteigne ou dépasse le v5 sur `val_scellee`

**Estimation pour E-017 (carte de chaleur, 2 tours) : environ 4 %, entre 2 et 8 %.** Avec E-018 (vecteurs, segmentation) réussi sur le développement : 8 à 12 %.

**Raisons.**
- **Écart à combler : +0,15 à +0,22.**
  - Le v5 est attendu entre 0,78 et 0,86 (audit, § E).
  - Le professeur fait 0,637 sur le développement et devrait baisser en transfert : 0,546 à 0,570 sur dev_transfert, et 0,64 prédit pour un domaine semblable à bv_session_a (E-016).
- **Gain habituel de l'auto-entraînement** [H, ordre de grandeur de la littérature sur les pseudo-étiquettes en détection] : +0,02 à +0,08 au-dessus d'un professeur moyen. Le gain est plus grand quand le bruit du professeur est aléatoire et que les images non étiquetées abondent. Ici, aucune de ces deux conditions n'est remplie :
  - la réserve est petite : quelques centaines de tuiles denses ;
  - le bruit du vote est en partie **systématique** (tailles de couronne, E-011) : il sera appris, pas moyenné.
- **Le v5 n'est pas un étalon neutre.**
  - Il a été entraîné avec de vraies boîtes sur la même ferme, y compris bv_b_train.
  - Son seuil a été choisi en partie sur bv_b_val.
- **La diapositive ne fournit aucune mesure transposable** [O, transmise par Corentin] : ni F1, ni référence, ni taille de réserve.

**Ce qui la ferait monter :**
1. Tour 1 : au moins +0,06 sur le vote, à k = N_réf **et** au point de fonctionnement, avec les deux graines, T-E1a et T-E1b remplis : environ 8 %.
2. Le gain tient, ou grandit, sur dev_transfert exclu de la réserve. C'est le signal le plus proche de `val_scellee`, qui est un changement de session : environ 10 %.
3. Le tour 2 apporte un gain apparié qui exclut 0, ou E-018 réduit les maxima distincts à environ 1,3 m et l'oubli des grandes couronnes : 10 à 15 %.
4. Une réserve plus grande issue de la même mission : photos brutes de la session B hors validation et hors bandes tampon, si elles existent et si Corentin le décide.

**Ce qui la ferait baisser :**
- un gain obtenu seulement au point de fonctionnement ;
- T-E1b aussi bon que l'élève du vote ;
- un accord élève-professeur supérieur à 0,95 ;
- un écart entre graines supérieur à 0,03.

**Conséquence pratique.**
- `val_scellee` documente H8 : la distance entre une méthode sans annotation et le détecteur appris.
- E-017 vaut la peine d'être fait, car un gain apparié sur le développement est déjà un résultat. Il ne faut pas le présenter comme un chemin probable vers le v5.

### Registre (E-017)

| N° | Objection | Contrôle ou amendement | Bloquant | Résultat | Clôture |
| --- | --- | --- | --- | --- | --- |
| OBJ-E1 | Témoin demi-maille tautologique pour un réseau convolutif | T-E1a (points au hasard dans la végétation) ; T-E1b (professeur = baseline T3) ; demi-maille rapportée seulement | oui | à mesurer | ouverte |
| OBJ-E2 | Réserve non listée ; ±3 trop court (40 % de recouvrement à k = 3) ; dev_transfert, segmento_ouest, jeunes 0546 et 0548 ; dépend de 1a/1b ; disque de 2 000 px | Liste et MD5 avant l'entraînement ; ±5 ; dev_transfert et jeunes exclus ; bv_b_train seulement en 1b | oui | sans calcul | ouverte (convergence-engineer ; Corentin pour 1a/1b) |
| OBJ-E3 | Candidate pour `val_scellee` non fixée avant E-017 | Règle de remplacement écrite avant le tour 1 ; envoi unique | oui | sans calcul | ouverte (chef d'orchestre) |
| OBJ-E4 | Variance de graine absente de l'intervalle | Seconde graine si la première passe ; les deux doivent passer | oui | à mesurer | ouverte |
| OBJ-E5 | Égaliser le compte hérite du biais du professeur, sur des images ajustées | Égalisation sur un bloc mis de côté de bv_b_train ; F1 à k = N_réf et courbe rappel-budget | non | à mesurer | ouverte |
| OBJ-E6 | Copie et mémorisation (dernière époque) | Époques modérées ; diagnostic de désaccord ; accord élève-professeur | non | à mesurer | ouverte |
| OBJ-E7 | Mères oubliées étiquetées « fond » | Rappel par taille ; zone ignorée étendue en variante déclarée plus tard | non | à mesurer | ouverte |
| OBJ-E8 | Étiquettes du tour 2 non spécifiées | Règle écrite avant le tour 1 | non | sans calcul | ouverte |
| OBJ-E9 | Identité du pipeline ; base 0,637 contre 0,632 hors pli | Empreinte de l'évaluation ; différence appariée par blocs | non | sans calcul | ouverte |
| OBJ-E10 | Têtes de segmentation et de vecteurs | Pas au tour 1 ; E-018 après le verdict | non | décision proposée | proposée |
| OBJ-E11 | Développement usé (environ 144 configurations, plus E-017) | Au plus 7 regards déclarés ; dev_transfert hors réserve en priorité | non | sans calcul | ouverte |
| OBJ-E12 | Probabilité de battre le v5 | Environ 4 % (2 à 8 %) ; à revoir après le tour 1 | non | estimation [H] | à revoir |

## D-013 — Critères d'acceptation du simulateur v2 (7 novembre 2026, écrits avant toute construction)

Contexte : D-013, E-005 (circularité confirmée), E-018s et E-019s (B′ à 0,98 en synthétique contre 0,637 sur le réel). Ces critères sont écrits **avant** que `comptage_math/simulateur.py` existe et avant toute statistique d'image-analyst ou de plant-geometry. Ils ne seront pas assouplis après un résultat. Un amendement n'est valable que s'il est consigné dans `docs/experiment-log.md` avant la mesure qu'il touche.

Faits utiles [O] (`data/comptage_math/references/dev_dense.csv`, groupe `bv_session_a`, lu le 7 novembre 2026) : 64 photos d'origine, 19 217 références, toutes de type `mere` (aucun rejet annoté), `taille_m` renseignée partout, résolution de 3,6 à 6,7 cm/px (médiane 4,6).

### 1. Ce qui peut calibrer, ce qui est interdit

**1.1 Partage des photos (fixé maintenant, avant toute statistique).**
- Les 64 photos de `bv_session_a` sans pépinière sont triées par numéro DJI et coupées en deux moitiés contiguës :
  - **CAL** : la première moitié (32 photos), seule source de calibration ;
  - **VAL-S** : la seconde moitié, **moins les photos à moins de 3 numéros de la coupure** (règle de recouvrement de `CLAUDE.md`). Elle sert uniquement aux tests de fidélité (§ 2) et aux cibles réelles de prédiction (§ 3).
- image-analyst écrit la liste CAL / VAL-S, avec le MD5 des photos, dans `out/comptage_math/image-analyst/D-013/partage.csv`, avant le premier calcul. plant-geometry utilise la même liste.
- Aucun autre groupe (bv_b_train, bv_b_val, val_iter, val_scellee, dev_transfert, test) n'est lu, ni en image ni en référence.

**1.2 Autorisé pour calibrer (sur CAL seulement).**
- Photométrie :
  - histogrammes de luminance et d'ExG ;
  - fractions de pixels par classe (végétation verte, feuille sèche, ombre, sol nu, herbe), avec le classifieur figé d'image-analyst ;
  - couleur moyenne et dispersion de chaque classe ;
  - spectre de puissance radial de la luminance ;
  - direction et longueur des ombres ;
  - flou et bruit du capteur, compression JPEG.
- Géométrie, à partir des références de CAL :
  - distribution des tailles de couronne `taille_m` ;
  - densité par tuile ;
  - distances au plus proche voisin ;
  - fonction de corrélation de paires g(r) ;
  - taux de recouvrement des couronnes (d < r_i + r_j).
- Rejets : les références n'en contiennent pas [O]. Leur nombre et leur taille ne peuvent venir que d'une source [S] ou d'une hypothèse [H] déclarée, jamais d'un ajustement.
- Textures et fonds **prélevés sur CAL** :
  - fenêtres de sol, d'herbe et d'ombre situées à plus de 1,5 m de toute référence ;
  - échantillons de pixels de feuilles vertes et sèches.

**1.3 Interdit, sans exception.**
- Tout score de détection (F1, rappel, précision, compte) d'une méthode quelconque, sur le réel ou sur le simulateur, avant le test de prédiction officiel (§ 3).
- Toute information issue des **sorties** des méthodes testées : cartes de vote, réponses de gabarit, candidats, maxima, seuils, cartes d'erreur d'E-011.
- Les grandeurs internes de B′ ne servent qu'**à la validation**, jamais à la calibration : distribution de la cohérence du tenseur de structure à l'échelle de B′, alignement radial des orientations (E-003). Un simulateur calibré sur elles serait construit pour plaire à B′.
- Lancer B′, T3, le vote ExG, A′ ou A-iso sur des scènes v2 avant le test officiel. Seul independent-evaluator les lance (§ 4).

**1.4 Ne pas emprunter la forme supposée par les détecteurs.**
- `comptage_math/simulateur.py` n'importe **rien** des modules de détection : ni `feuille.py` (dont `masque_B`, `texture_B`, `rendre_scene_B`), ni le vote, ni le tenseur, ni les gabarits. Vérification par scientific-challenger, qui relève les imports avant le test.
- Aucune feuille à profil gaussien ni en bande de largeur constante. Le limbe appartient à une autre famille, justifiée par une source botanique [S] ou une image nommée [O] :
  - contour oblong à bords non parallèles ;
  - nervure courbée et retombante (raccourcissement en vue verticale) ;
  - **déchirures** du limbe en lanières perpendiculaires à la nervure ;
  - feuilles sèches pendantes, collées au pseudo-tronc ;
  - cigare.
- Chaque forme fonctionnelle utilisée figure dans un tableau « formes et origines » en tête du fichier.
- Rendu à une résolution fine (1 cm/px au plus), puis ramené entre 3,6 et 6,7 cm/px (valeur tirée dans la distribution [O] ci-dessus), par une PSF et une compression JPEG estimées sur CAL. Pas de rendu direct à l'échelle du détecteur.
- Fonds : collages de fenêtres réelles de CAL (sol, herbe, ombre). Pas de couleur uniforme ni de bruit blanc.
- Ombres portées : projetées par une géométrie 3D sommaire du plant, selon la direction mesurée sur CAL. Pas un simple assombrissement radial.

### 2. Tests de fidélité (sur VAL-S, jamais sur CAL)

**Principe.**
- Chaque distance simulé–réel, d(sim, VAL-S), est comparée à la variabilité naturelle d(CAL, VAL-S), calculée sur les mêmes quantités.
- Un test passe si **d(sim, VAL-S) ≤ max(seuil absolu, 1,5 × d(CAL, VAL-S))**.
- Les p-valeurs sont rapportées mais ne décident rien : avec des millions de pixels, tout écart devient « significatif ».
- Tuiles : même taille et même nombre que les tuiles réelles de VAL-S ; scènes générées avec les graines du § 4.

| N° | Quantité | Distance | Seuil absolu | Statut |
| --- | --- | --- | --- | --- |
| F1 | Luminance (par pixel, toutes tuiles) | KS D | ≤ 0,10 | calibrée |
| F2 | ExG (par pixel) | KS D | ≤ 0,10 | calibrée |
| F3 | Fractions de classes (vert, sec, ombre, sol, herbe), moyenne par tuile | écart absolu par classe | ≤ 0,05 | calibrée |
| F4 | Fractions de classes, dispersion entre tuiles | rapport des écarts-types | dans [0,67 ; 1,5] | calibrée |
| F5 | Spectre radial de la luminance, de 1/256 à 1/4 cycle/px | écart moyen absolu de log10 P ; pente | ≤ 0,15 dex ; pente à ±0,3 | calibrée |
| F6 | Norme du gradient de la luminance | Wasserstein-1 divisé par l'écart-type réel | ≤ 0,15 | **réservée** |
| F7 | Cohérence du tenseur de structure à l'échelle de B′ | KS D ; W1 | ≤ 0,10 ; ≤ 0,05 | **réservée** |
| F8 | Alignement radial des orientations autour des références (mesure d'E-003) | écart de l'indice moyen | ≤ 0,05 | **réservée** |
| G1 | Tailles de couronne des mères | KS D ; W1 | ≤ 0,10 ; ≤ 0,15 m | calibrée |
| G2 | Distance au plus proche voisin | KS D ; W1 | ≤ 0,10 ; ≤ 0,15 m | calibrée |
| G3 | Densité de mères par tuile | moyenne ; coefficient de variation | ±10 % ; ±25 % | calibrée |
| G4 | g(r), r de 0,5 à 6 m par pas de 0,25 m | max ǀΔgǀ | ≤ 0,25 | calibrée |
| G5 | Taux de recouvrement des couronnes | écart absolu | ≤ 0,05 | calibrée |
| G6 | Part des mères de moins de 2 m et de plus de 3,6 m (seuils d'E-016) | écart absolu de proportion | ≤ 0,05 | calibrée |

- **Quantité réservée** : jamais calculée par leaf-mathematician ni transmise à lui. Seuls image-analyst ou independent-evaluator la calculent, au moment du test. C'est la garde contre un simulateur qui ne ressemble au réel que sur ce qu'on lui a montré.
- **Verdict de fidélité** : tous les tests calibrés passent, et au moins 2 des 3 réservés. Sinon, le simulateur n'est pas soumis au § 3.
- **Contrôle de non-trivialité** : l'ancien rendu `rendre_scene_B` passe les mêmes tests et doit **échouer** au moins sur F3, F5 et G1. S'il passe, les seuils sont trop lâches : on le consigne et on les durcit avant de tester v2.

### 3. Test de prédiction

**3.1 Méthodes et métrique.**
- Méthodes figées, empreintes SHA-256 relevées par independent-evaluator avant le test : vote B′ (E-008/E-010), baseline T3 (E-015), vote ExG (T2, E-016), A′ et A-iso (E-006). Aucun paramètre ni seuil modifié.
- **Métrique principale** : celle qui a produit les chiffres de référence, avec le même code `scripts/math_evaluer.py`. C'est le F1 des mères, appariement à 1 m, **au budget k = N_réf** (classement global des scores, notation d'E-001). Avant le test, independent-evaluator vérifie que chacun des cinq chiffres est bien à k = N_réf. Sinon, il écrit la correspondance exacte dans le journal.
- Sur le simulateur, N_réf est le nombre de mères vraies. Les rejets éventuellement rendus ne comptent pas comme références, comme sur le réel.
- Le F1 au seuil figé de chaque méthode est **rapporté, mais ne décide rien** : l'échelle des scores dépend du contraste du rendu et ne se transfère pas.
- Sensibilité rapportée, sans valeur de décision : références simulées privées au hasard de 9 % des mères. Ce chiffre vient du rapport médian de 1,10 entre détections du v5 et références (E-001, `test_final.md`). Il mesure l'effet de l'incomplétude des références réelles.

**3.2 Cibles réelles.**
- **Cibles A, publiques** : 0,637 ; 0,567 ; 0,563 ; 0,541 ; 0,423, sur toutes les photos. leaf-mathematician les connaît : elles ne suffisent pas seules.
- **Cibles B, scellées.** independent-evaluator calcule, sur **VAL-S seul** :
  - les F1 des cinq méthodes ;
  - le rappel de B′ par tercile de taille de couronne ;
  - les deux niveaux nuls de B′ (orientations mélangées, demi-maille).

  Il les calcule et les hache avant la construction du simulateur, ne les transmet à personne et ne les ouvre qu'au test.
- Le simulateur produit autant de tuiles que VAL-S, regroupées en blocs de 7 pour les intervalles (bootstrap par blocs, comme E-015).

**3.3 Seuils (décision sur les cibles B ; cibles A rapportées).**

| Critère | Seuil |
| --- | --- |
| P1 Erreur absolue moyenne sur les 5 méthodes | ≤ 0,05 |
| P2 Erreur absolue maximale | ≤ 0,08 |
| P3 Biais signé moyen (simulé − réel) | dans [−0,04 ; +0,04] |
| P4 Ordres imposés (écarts réels ≥ 0,03) : B′ au-dessus des quatre autres ; T3, vote ExG et A′ au-dessus d'A-iso | tous reproduits |
| P5 Paires à écart réel < 0,03 (T3, vote ExG et A′ entre eux) | écart simulé < 0,06 en valeur absolue |
| P6 Écart B′ − T3 | à ±0,05 de l'écart réel |
| P7 Spearman des 5 méthodes | ≥ 0,8, rapporté seulement : avec 5 points, ρ est peu informatif ; P4 et P5 décident |
| P8 Rappel de B′ par tercile de taille | chaque tercile à ±0,10, avec la même pente (petites couronnes plus oubliées) |
| P9 Niveaux nuls de B′ | chacun à ±0,07 |

**3.4 Verdicts.**
- **Accepté** : fidélité (§ 2), P1 à P6, P8 et P9.
- **Accepté pour le classement seulement** : fidélité, P4, P5 et P8 passent, et P1 ≤ 0,10. Le simulateur sert alors de filtre relatif (§ 5), jamais pour une valeur absolue.
- **Rejeté** : dans tous les autres cas.
- **Trop optimiste** (P3 > +0,04) : un facteur de difficulté manque ou est trop faible.
  - Si la fidélité passait, les statistiques choisies ne capturent pas ce facteur. On le consigne comme résultat : « la difficulté réelle n'est pas dans ces statistiques ». Candidats : incomplétude des références, rejets, vue oblique, flou de bougé.
  - La version suivante ne peut ajouter qu'un facteur justifié par une **nouvelle statistique d'image mesurée sur CAL**, jamais par l'écart de score.
- **Trop pessimiste** (P3 < −0,04) : désordre rendu en excès (herbe, feuilles sèches, ombres) ou recouvrements trop forts. Même règle.
- **Ordre faux** (P4 échoue) : le simulateur est inutilisable, même comme filtre, car il favorise une famille de forme. On vérifie d'abord l'emprunt de forme (§ 1.4).

### 4. Protection contre le réglage caché

- **Au plus 3 versions** soumises au test de prédiction (v2.0, v2.1, v2.2). Après la troisième, les cibles A et B sont consommées. Un nouveau test exige alors de nouvelles cibles, par exemple dev_transfert avec une calibration propre, sur décision de Corentin.
- Les tests de fidélité calibrés sur CAL sont libres et sans limite. Sur VAL-S, une seule passe par version soumise.
- Pour chaque version, une entrée du journal, écrite **avant** le test, donne :
  - le SHA-256 de `simulateur.py` et du fichier de paramètres ;
  - la liste des graines ;
  - la liste des changements, chacun avec la statistique de fidélité qui le justifie.
- Graines des scènes, fixées dès maintenant : 20261113 + i, pour i de 0 à N_tuiles − 1, identiques pour toutes les versions. Aucune scène n'est retirée après coup.
- Seul independent-evaluator lance les cinq méthodes sur les scènes v2, une fois par version, et ouvre les cibles B. leaf-mathematician déclare dans sa note n'avoir lancé aucune des cinq méthodes sur ses rendus.
- Le simulateur ne modifie pas les méthodes, et les méthodes ne sont pas réglées sur le simulateur.

### 5. Usage ultérieur, et limites

**Usages permis**, seulement si le verdict est « accepté » ou « accepté pour le classement » :
- **Filtre d'élimination.** Une nouvelle formulation qui perd plus de 0,03 de F1 contre B′ sur v2 (IC par blocs entièrement sous 0) est écartée sans consommer le développement réel. Un gain sur v2 n'est **jamais** une preuve : il autorise seulement une mesure sur le réel, avec une règle écrite avant.
- **Diagnostic par facteur.** Ablation d'un facteur à la fois (tailles variées, feuilles sèches, ombres, herbe, recouvrements), à graines égales, avec le ΔF1 de chaque facteur pour B′ et T3.
  - Contrôle de cohérence : la part d'erreur attribuée aux petites couronnes et aux mères sans candidat doit être du même ordre que dans E-011 et E-016 (oubli de 0,65 sous 2 m ; 40 % des mères oubliées sans candidat à 1 m).
  - Sinon, le diagnostic est rapporté comme non fiable.
- **Prévision**, seulement si le verdict est « accepté » : une prévision chiffrée [H] avant une mesure réelle, à comparer ensuite.

**Ce qu'il ne pourra jamais prouver.**
- Qu'une méthode marche sur le réel, ni son score sur `val_scellee` ou sur le test. Aucune adoption ne se fonde sur lui.
- Un seuil de score : l'échelle des scores ne se transfère pas, donc aucun seuil n'est choisi sur v2.
- L'effet des facteurs non rendus : vue oblique des bords, erreur d'échelle, autres fermes ou sessions, palmiers et cocotiers, sol strié, rejets réels.
- La cause des erreurs réelles : il montre qu'un facteur **peut** produire une erreur, pas qu'il la produit sur le réel.
- Sa validité hors des conditions de bv_session_a. La prévision pour dev_transfert (0,546 pour B′) n'est pas testée par ce protocole.

### Registre (D-013)

| N° | Objection | Contrôle ou critère | Bloquant | Résultat | Clôture |
| --- | --- | --- | --- | --- | --- |
| OBJ-S1 | Calibration sur des scores ou sur les sorties des détecteurs (circularité d'E-005) | § 1.3 ; grandeurs internes de B′ en validation seulement | oui | sans calcul | ouverte |
| OBJ-S2 | Rendu dans la famille de forme des détecteurs (gaussiennes, bandes) | § 1.4 ; relevé des imports ; tableau des formes | oui | à vérifier | ouverte |
| OBJ-S3 | Calibration et validation sur les mêmes photos | Partage CAL / VAL-S avec tampon de 3 numéros | oui | sans calcul | ouverte (image-analyst) |
| OBJ-S4 | Fidélité limitée à ce qui a été montré au simulateur | Tests réservés F6 à F8 | oui | à mesurer | ouverte |
| OBJ-S5 | Cibles publiques connues de l'auteur | Cibles B scellées sur VAL-S, rappel par taille, niveaux nuls | oui | à mesurer | ouverte (independent-evaluator) |
| OBJ-S6 | Itérations cachées jusqu'à coller aux scores | 3 versions au plus ; journal ; graines fixes ; méthodes lancées par l'évaluateur seul | oui | sans calcul | ouverte |
| OBJ-S7 | Références réelles incomplètes, vérité simulée complète | Sensibilité à 9 % d'omission, rapportée | non | à mesurer | ouverte |
| OBJ-S8 | Rejets non annotés, impossibles à calibrer | Source ou hypothèse déclarée ; rapporté comme limite | non | sans calcul | limite |
