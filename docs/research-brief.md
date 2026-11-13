# Brief de recherche : comptage mathématique des plants principaux de bananiers

Écrit le 7 novembre 2026 par la session principale, avant toute expérience de l'équipe.

**Étiquettes** (règle 2 de `CLAUDE.md`) :
- **[O]** observé ;
- **[S]** source ;
- **[H]** hypothèse ;
- **[M]** mesuré, avec la référence de la mesure.

Les chiffres [M] ci-dessous viennent des protocoles du détecteur appris (v3 à v5), pas de la méthode mathématique, qui n'a encore rien mesuré.

## 1. Le problème

**Objectif.** Sur des images aériennes RVB (drone, orthomosaïque), localiser et compter les **plants principaux** de bananiers, c'est-à-dire les pieds mères, au centre de leur rosette, là où sort le pseudo-tronc. Les rejets ne sont pas comptés. Il s'agit d'une décision de périmètre prise avec le mentor [S : `CONTEXTE_FIELD_SCAN.md`, section 1].

**Exigences de la consigne** [S : `Field Scan analyse d'une bananeraie vue du ciel.pdf`, 4 nov. 2026] :
- **métrique** : F1 de détection avec appariement à 1 m, et erreur de comptage par parcelle ;
- **sobriété** : inférence sans GPU, et le temps par hectare sur processeur est noté ;
- **honnêteté** : signaler ce que le système ne sait pas ;
- **évaluation finale** : sur une zone jamais vue, « mélangée » (bananeraies et fermes) ;
- **difficultés annoncées** : canopée dense dès la troisième génération, rejets au pied des mères, lumière qui change d'un vol à l'autre.

**Nature de la méthode.** Une méthode **mathématique** : des modèles explicites (gaussiennes, formes, couleurs, stries, orientations), avec peu de paramètres, réglés sur le développement. Ce n'est pas un réseau appris. La frontière exacte reste à préciser (section 6).

**Sortie attendue.** Un point par plant principal, en coordonnées. Elle doit être lisible par l'évaluation et compatible avec `pieds.geojson` de la chaîne existante.

## 2. Connaissances établies

### 2.1 La plante vue du ciel

- [S, de mémoire, à vérifier : `docs/comprendre_bananier.md`]
  - herbe géante, sans tronc ligneux : son pseudo-tronc est fait de gaines de feuilles ;
  - vue du ciel, une étoile de grandes feuilles ;
  - feuilles de 2 à 3 m, pieds espacés d'environ 2 m ;
  - couronnes qui se chevauchent, rangs qui dérivent avec les générations ;
  - rejets cachés sous la mère, trois générations au même endroit.
- [O] Les annotations manuelles placent un point au centre de la rosette (`docs/consigne_annotation_jeunes_bananiers.md`). Elles distinguent `mere`, `rejet` et `incertain`.
- [O] Des palmiers à huile et des cocotiers, aux couronnes en étoile, étaient comptés comme bananiers par le premier détecteur appris : 6 876 fausses détections sur 873 images de palmiers [M : `CONTEXTE_FIELD_SCAN.md`, section 5.3].

### 2.2 Références annotées existantes

Aucune nouvelle annotation ne sera faite. La colonne de droite est une **proposition** : annotation-manager la vérifie, Corentin la valide.

| Jeu | Référence | Rôle dans le v5 | Résolution | Rôle proposé ici |
| --- | --- | --- | --- | --- |
| ReforesTree : Flora Pluas, Nestor Macias, Leonor Aspiazu (Équateur, agroforesterie) | boîtes ReforesTree, incomplètes | entraînement | native, à relever | développement |
| ReforesTree : Manuel Macias, MM1-MM2 | points manuels : 83 pieds (69 mères, 14 rejets, 1 incertain) | validation | idem | validation |
| ReforesTree : Carlos Vera Guevara, CG1-CG9 | points manuels : 313 pieds (290 mères) | test v3, v4 et v5 | idem | option de test (section 5) |
| ReforesTree : Carlos Vera Arteaga | boîtes ReforesTree, incomplètes | exclu partout (voisin de CG) | idem | option de test (section 5) |
| Plants-bana, segmento ouest | boîtes Roboflow | entraînement | environ 10 à 12 cm/px (corrigé, voir note) | développement |
| Plants-bana, segmento est | boîtes Roboflow, moins complètes en zone mêlée | test v4 et v5 (validation du v3) | environ 10 à 12 cm/px (même orthomosaïque, non ouverte) | option de test |
| Count banana plants (vols 100_0221 à 0224, corte) | boîtes ; validation et test contaminés par Plants-bana | entraînement | estimée | développement seulement |
| Jeunes bananiers DJI : dji_0546, dji_0548 | points manuels typés | entraînement | 1,1 cm/px, disque de 2 000 px | développement |
| Jeunes bananiers DJI : dji_0544 | points manuels typés | validation | idem | validation |
| plantas_platano : lote_2, lote_2_parte_2 | points | entraînement | 2,6 et 2,9 cm/px | développement |
| plantas_platano : 100_metros | points | validation | 2,4 cm/px | validation |
| platano_lasuiza | boîtes, quelques tuiles incomplètes | entraînement | estimée | développement |
| banana_tree_detection (jeunes plants espacés sur paillage) | boîtes | test v4 et v5 | 3,1 cm/px | option de test |
| banavista : session A, et lignes DJI_0757 à 0841 de la session B | boîtes `Bananas` | entraînement | 1,07 à 1,13 cm/px | développement |
| banavista : session B, DJI_0862 à 0945 | boîtes | validation | idem | validation |
| banavista : bande tampon DJI_0842 à 0861 | boîtes | exclue, aucun modèle mesuré dessus | idem | option de test (section 5) |
| banano_dense (orthomosaïque à couronnes jointives) | boîtes, doublons probables | test v5 | 2,7 cm/px | option de test |
| Multiple tree : palmiers et cocotiers, sans bananier | arbres annotés | négatifs : entraînement, validation et test selon la zone | 5 cm/px après préparation | même partage par zone |
| El Oro EO1-EO4 (OpenAerialMap) | **aucune** | contrôle visuel | 6,4 cm/px | contrôle visuel seulement, aucun score (règle 8) |

Sources de ce tableau : `docs/protocole_comptage_v3.md` à `v5.md` et `CONTEXTE_FIELD_SCAN.md`, section 5. Résolutions estimées par deux règles :
- couronne médiane ramenée à 3 m ;
- ou distance médiane au plus proche voisin ramenée à 2,5 m.

**Correction du 7 novembre 2026 (missions M1 et M4, vérifiée par le chef d'orchestre).** Segmento était noté à « environ 1,1 cm/px », valeur des photos DJI des jeunes bananiers. [O] `out/comptage_math/image-analyst/inventaire.csv` : segmento ouest, 12 643 boîtes, côté médian 25,5 px, plus proche voisin 24 px, tuiles de 640 px non réduites, soit environ 10 à 12 cm/px. [O] `data/drone/comptage_v5_5cm/parametres.json` : facteur d'agrandissement 2,22 vers 5 cm/px, cohérent. Conséquence : les indices « stries » et « nervure » ne sont pas testables sur segmento.

L'incertitude est de 15 à 20 % [S : protocoles v3 et v4].

Seuls MM, CG et les jeunes bananiers DJI distinguent mères et rejets. Les boîtes Roboflow donnent un point par plant visible, sans type.

### 2.3 Résultats déjà mesurés

**Méthodes classiques, sur MM1-MM2 (validation, tous pieds) :**
- [M] ExG, lissage gaussien et maxima locaux (`scripts/baseline_comptage.py`) : **F1 0,37** ;
- [M] corrélation avec des gabarits moyens sur les 8 rotations et symétries (`scripts/template_matching_comptage.py`) : **F1 0,36**.

Sources : `CONTEXTE_FIELD_SCAN.md`, sections 5.2 et 7. Ce sont les références à battre pour une méthode explicite.

**[M] Détecteur appris v5, adopté** (carte de chaleur des centres, ResNet-18, 5 cm/px) :
- validation : dense 0,777, plantain 0,885, jeunes plants 0,893, MM mères seules 0,857 ;
- test, regardé une fois, F1 : dense industriel (banano) 0,807, segmento est 0,673, plantation espacée (`banana_tree_detection`) 0,546, CG mères seules 0,315 ; 0,5 % de fausses détections sur les palmiers ;
- environ 2 s par hectare sur processeur, 45 Mo.

Source : `docs/protocole_comptage_v5.md`, section 9.

**[O] Compromis entre versions.** D'une version du détecteur appris à l'autre, chaque gain sur un type de plantation s'est payé par une perte sur un autre. Les petits plants espacés sont mal détectés par le v5. Ce constat vient d'un test : il oriente la recherche, mais aucune règle ne doit en découler sur ces mêmes images.

**[M] Effet de la résolution.** Une résolution plus fine améliore le rappel en canopée dense : ablation de résolution du détecteur DeepForest, `CONTEXTE_FIELD_SCAN.md`, section 5.2.

### 2.4 Pièges connus

- [O] L'empreinte d'image (dHash) est inutile pour détecter les fuites entre images de végétation. Seule la vérification par nom de photo d'origine est fiable.
- [O] Count banana plants est une autre découpe des photos de Plants-bana.
- [O] Les bananiers de Multiple tree viennent des mêmes photos.
- [O] Les photos DJI brutes sont vues de biais sur les bords : on ne garde qu'un disque de 2 000 px autour du centre.
- [O] Aucune annotation de masque (pixels de feuille, de bananier) n'existe. Les étapes intermédiaires se mesurent par des critères indirects, à partir des centres annotés.

## 3. Les indices de la présentation orale de Philemon

**Ce que l'on sait.** [O] Seulement des mots retenus d'une présentation orale : *gaussiennes, formes, couleurs, stries, orientations*.

**Ce que l'on ne sait pas.** La fonction originale, son ordre d'application, ses données, sa résolution et ses résultats sont **inconnus** (règle 1).

**Hypothèses de travail.** Les hypothèses ci-dessous sont des formulations compatibles avec ces indices, pas une reconstitution. Pour chacune, le critère chiffré de l'expérience est fixé par independent-evaluator avant le lancement. Toutes les expériences se font sur le développement, puis se mesurent sur la validation.

**H1 [H] — Gaussienne à l'échelle du plant.**
- Hypothèse : un plant est une tache, détectée par un laplacien ou une différence de gaussiennes, à plusieurs échelles.
- Prédiction : la baseline ExG est déjà un lissage gaussien à une seule échelle, donc l'échelle multiple n'apporte qu'un faible gain. H1 sert de **témoin**.
- Expérience minimale : rappel des candidats à 1 m, au même budget de candidats que la baseline.
- Ce qui la réfuterait : aucun gain mesurable sur le développement.

**H2 [H] — Gaussiennes anisotropes par feuille.**
- Hypothèse : un plant est une somme de feuilles allongées qui rayonnent depuis le centre.
- Prédiction : un filtre adapté orienté répond le plus fort selon la direction qui pointe vers le centre.
- Expérience minimale : écart entre l'orientation de réponse maximale et la direction du centre annoté le plus proche, comparé à des centres tirés au hasard.
- Ce qui la réfuterait : un écart identique à celui du contrôle.

**H3 [H] — Stries.**
- Hypothèse : le limbe se déchire le long des nervures secondaires, perpendiculaires à la nervure centrale. Vue du ciel, il en résulte une texture fine dont l'orientation donne l'axe de la feuille.
- Prédictions :
  - (a) les stries ne sont visibles que sous une certaine résolution, à mesurer par image-analyst ;
  - (b) leur orientation est perpendiculaire à la direction du centre.
- Expérience minimale : (a) planches rééchantillonnées ; (b) histogramme d'angles contre contrôles.
- Ce qui la réfuterait : pas de stries à 1 à 3 cm/px, ou des angles identiques au contrôle.
- Contre-exemple à tester : les folioles des palmiers produisent aussi des stries.

**H4 [H] — Orientations convergentes.**
- Hypothèse : les axes des feuilles convergent vers le pseudo-tronc, et un vote le long des axes concentre la preuve au centre.
- Expérience minimale : part des votes reçus à moins de 1 m d'un centre annoté, comparée à des centres déplacés, à des orientations mélangées et à des images de rangées sans centre.
- Ce qui la réfuterait : pas d'écart avec les contrôles.

**H5 [H] — Couleur.**
- Hypothèses :
  - (a) le bananier se distingue des palmiers et des autres arbres par la couleur ;
  - (b) le centre est plus clair (feuille cigare, jeunes feuilles) ;
  - (c) des feuilles sèches brunes sont en périphérie.
- Expérience minimale : séparation sur les images sans bananier du développement ; profil radial de couleur autour des centres annotés.
- Ce qui la réfuterait : aucune séparation au-delà du contrôle, ou un profil radial plat.

**H6 [H] — Forme.**
- Hypothèse : le limbe est large et continu (bananier), alors que les feuilles des palmiers sont pennées et découpées. Un indicateur de forme les sépare.
- Expérience minimale : indicateur mesuré sur les négatifs du développement et autour des centres annotés.
- Ce qui la réfuterait : des distributions confondues.

**H7 [H] — Échelle.**
- Hypothèse : la méthode dépend de la résolution connue, et une erreur de ±20 % dégrade le comptage de façon mesurable.
- Expérience minimale : perturbation d'échelle sur la validation, avec des règles écrites avant.
- Conséquence si elle est confirmée : prévoir une recherche multi-échelle ou une estimation de l'échelle.

**H8 [H, alternative portée par scientific-challenger] — Une méthode explicite peut rester sous le détecteur appris.**
- Hypothèse : les indices peuvent décrire une visualisation ou des étapes d'un autre système, et une méthode explicite peut rester sous le v5.
- Conséquence : l'objectif est de **mesurer**, pas de confirmer. Un résultat négatif, documenté, est un résultat.

## 4. Inconnues

1. **La présentation de Philemon** : support, date, données et résolution utilisées, résultats annoncés, sens précis de « gaussiennes » et de « stries ». Des notes ou des diapositives existent-elles ?
2. **La frontière de la « méthode mathématique »** : peut-on régler quelques paramètres sur le développement ? Utiliser un classifieur simple (par exemple une régression logistique) sur des attributs ? Utiliser le v5 comme composant ?
3. **Le test final** de la méthode : section 5, à trancher avant toute expérience.
4. **La place dans le livrable** : la méthode remplacera-t-elle le v5, le complétera-t-elle (par exemple pour les petits plants), ou servira-t-elle seulement de comparaison et d'ablation dans le rapport ? Faut-il l'intégrer à `run.py` ?
5. **L'échéance** : le rendu était estimé vers le 13 novembre 2026, date à confirmer avec Corentin.
6. **La visibilité des stries et des nervures** à chaque résolution des jeux (mesure d'image-analyst).
7. **La résolution native** des orthomosaïques ReforesTree, et l'échelle réelle des jeux Roboflow, qui n'ont pas de métadonnées.
8. **Les chiffres morphologiques** : nombre de feuilles, longueurs, angles. Ils sont écrits de mémoire et doivent être sourcés (banana-morphology).

## 5. Test final : options à trancher avant toute expérience

independent-evaluator rédige la proposition dans `docs/recherche/test_final.md`. Corentin décide. La décision est commitée avant la première expérience.

**A. Reprendre le test du v5** : banano_dense, segmento est, `banana_tree_detection`, CG1-CG9, images sans bananier du test.
- Pour : comparaison directe avec le v5 sur les mêmes images ; aucun de ces jeux n'a servi à régler quoi que ce soit.
- Contre : ces jeux ont déjà été regardés (résultats et contrôle visuel), et le test du v5 oriente cette recherche (section 2.3). Ce n'est plus un test vierge, et il faudra l'écrire.

**B. Données annotées jamais mesurées :**
- la bande tampon de banavista (DJI_0842 à 0861) : vierge, mais de la même ferme que des images de développement et de validation ;
- Carlos Vera Arteaga : boîtes ReforesTree incomplètes, voisin de CG.

Pour : vierges. Contre : petites, proches du développement, et références incomplètes pour Carlos Vera Arteaga.

**C. Les deux,** rapportés séparément : A pour la comparaison avec le v5, B comme seule partie vierge.

Quelle que soit l'option retenue :
- aucun agent, hormis independent-evaluator, n'ouvre ces images ;
- les jeux de validation de la section 2.2 restent la validation de la méthode.

## 6. Contraintes de travail

- Aucune annotation à la main, et aucune demande d'annotation.
- Aucun service payant. Aucun téléchargement sans l'accord de Corentin.
- Le calcul se fait sur le processeur de la machine de Corentin (8 cœurs, pas de GPU). La méthode doit tenir le temps par hectare sur processeur ; le v5 donne le point de comparaison.
- L'existant est préservé : le nouveau code va dans `comptage_math/` et dans de nouveaux scripts `scripts/math_*.py`.
