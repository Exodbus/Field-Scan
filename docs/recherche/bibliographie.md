# Bibliographie : détection et comptage explicites de couronnes (arbres, palmiers, bananiers)

Rédacteur unique : scientific-researcher. Version du 7 novembre 2026 (mission 2).

**Règles de lecture.**
- Chaque chiffre est rapporté tel que publié (ou tel que le résumé le donne), sans extrapolation. Aucun chiffre ici n'est une mesure sur nos données.
- Colonne « vérifié » :
  - **oui** : j'ai lu la source primaire ou son résumé officiel en ligne (page de l'éditeur, de l'archive ouverte, de l'auteur ou de l'institution) ;
  - **partiel** : la notice bibliographique (auteurs, revue, volume, pages, DOI) est vérifiée (Crossref, éditeur ou catalogue), mais le contenu (méthode, chiffres) vient de seconde main (résumé relayé par un moteur de recherche, article citant) : **à vérifier** avant toute citation de chiffre ;
  - **non** : cité de seconde main seulement, à vérifier.
- Aucune de ces sources n'est « la méthode de Philemon ». Aucune trace publique de cette méthode n'a été trouvée (voir notes).
- Hypothèses H1 à H8 : `docs/research-brief.md`, section 3.
- « Dense » = couronnes jointives ou qui se chevauchent ; « espacé » = plants séparés par du sol ou de l'herbe.

## 1. Tableau des références

### 1.1 Bananier vu par drone (points de comparaison, y compris méthodes apprises)

| # | Référence | Méthode | Données | Résolution | Métrique et résultat annoncé | Densité | Lien H | Vérifié |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | Neupane B., Horanont T., Hung N. D. (2019). *Deep learning based banana plant detection and counting using high-resolution RGB images collected from UAV*. PLOS ONE 14(10): e0223906. https://doi.org/10.1371/journal.pone.0223906 | Appris : Faster R-CNN (Inception-v2, pré-entraîné COCO) sur 4 variantes d'image (RVB, étirement de contraste, transformée couleur, indice TGI), détections fusionnées par distance entre centroïdes (20 à 30 px) | Ferme commerciale, province d'Ayutthaya, Thaïlande ; DJI Phantom 3 ; 2 695 plants de référence dans la zone d'intérêt ; « plus de 10 000 jeunes bananiers » au total | 1,78 / 2,03 / 2,54 cm/px (40, 50, 60 m) | Rappel / précision : RVB seul 40 m 0,788 / 1,000 ; fusion 40 m 0,964 / 0,993 ; 60 m fusion 0,758 / 0,985 ; 40+50 m combinés 0,990 / 0,983. L'« Overall Accuracy » de l'article est la moyenne P et R, **pas un F1**. Appariement : IoU 0,5 sur boîtes | Plants jeunes, espacement de plantation ≈ 1,5 m, chevauchements fréquents avec les rejets | H5 (indice TGI), H7 (effet d'altitude) ; l'article note qu'un bananier peut avoir **plusieurs maxima** (contre H1) | oui (texte intégral PMC) |
| B2 | Aeberli A., Johansen K., Robson A., Lamb D. W., Phinn S. (2021). *Detection of Banana Plants Using Multi-Temporal Multispectral UAV Imagery*. Remote Sensing 13(11): 2123. https://doi.org/10.3390/rs13112123 | Comparaison dans un cadre GEOBIA : CNN, **corrélation de gabarits (TM)** et **filtre de maximum local (LMF)**, avec raffinement par classification simple | Drone multispectral, plusieurs dates ; lieu, capteur exact et nombre de plants **non lus** (texte intégral inaccessible, 403) | non lue (le résumé dit seulement « < 1 m ») | F-score : CNN 0,93 à 0,85 ; TM 0,86 à 0,74 ; LMF 0,86 à 0,73 selon les dates. Tolérance d'appariement non lue | Plantation (densité non lue) | H1 (LMF), gabarits ; seul résultat publié d'une méthode explicite sur bananier | oui (résumé Crossref et dépôt UNE) ; détails à lire dans le texte intégral |
| B3 | Reiersen G., Dao D., Lütjens B., Klemmer K., Amara K., Steinegger A., Zhang C., Zhu X. (2022). *ReforesTree: A Dataset for Estimating Tropical Forest Carbon Stock with Deep Learning and Aerial Imagery*. AAAI 36(11): 12119-12125. https://doi.org/10.1609/aaai.v36i11.21471 ; arXiv 2201.11192 | Appris : détection d'arbres individuels (DeepForest selon `docs/carnet_de_donnees.md`) puis estimation du carbone | 6 sites d'agroforesterie, Équateur ; drone RVB ; plus de 4 600 arbres appariés à des relevés de terrain | non donnée dans le résumé | Résumé : estimation du carbone « dans les standards de certification » ; pas de F1 de détection dans le résumé | Agroforesterie mêlée (bananiers, cacao, autres arbres) | Source de nos jeux MM, CG ; c'est l'« article sur l'inventaire en agroforesterie » de la consigne (`docs/carnet_de_donnees.md`, section 6) | oui (résumé arXiv) |
| B4 | Gomez Selvaraj M., Vergara A., Montenegro F., Ruiz H. A., Safari N., Raymaekers D., Ocimati W., Ntamwira J., Tits L., Omondi A. B., Blomme G. (2020). *Detection of banana plants and their major diseases through aerial images and machine learning methods: A case study in DR Congo and Republic of Benin*. ISPRS J. Photogramm. Remote Sens. 169: 110-124. https://doi.org/10.1016/j.isprsjprs.2020.08.025 | Appris : RetinaNet + classifieur pour localiser les bananiers sur images drone RVB ; forêt aléatoire sur indices pour les images satellite | Petites exploitations, RD Congo et Bénin | non lue | Seconde main : 99,4 %, 92,8 %, 93,3 % et 90,8 % de justesse sur quatre classes (sain, malades) ; 97 % de justesse globale pour l'approche par pixels (satellite). Pas de F1 de comptage lu | Paysages mêlés | H5 (indices) ; point de comparaison « zone mêlée » | partiel |
| B5 | Jiang Q., Huang Z., Xu G., Su Y. (2023). *MIoP-NMS: Perfecting crops target detection and counting in dense occlusion from high-resolution UAV imagery*. Smart Agricultural Technology 4: 100226 | Appris : YOLOv4 avec une suppression des non-maxima modifiée (intersection rapportée à la portion) pour les occultations | Bananiers, plusieurs niveaux de densité | non lue | Seconde main : mAP ≈ 85 %, erreur moyenne de comptage ≈ 1,3 % | **Dense, occulté** | Règle de fusion des candidats en canopée dense (comparable à notre étape de suppression des doublons) | non (page DOAJ en 403) |

### 1.2 Pics et taches : maxima locaux, laplacien, différence de gaussiennes

| # | Référence | Méthode | Données | Résolution | Métrique et résultat annoncé | Densité | Lien H | Vérifié |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | Lindeberg T. (1998). *Feature Detection with Automatic Scale Selection*. International Journal of Computer Vision 30(2): 77-116 (le catalogue de la revue indique 79-116). Résumé : https://www.csc.kth.se/cvap/abstracts/cvap198.html | Espace d'échelle ; dérivées normalisées en γ ; les extrema sur les échelles désignent les structures et leur taille (taches, jonctions, arêtes, crêtes, fréquence locale) | Images réelles et synthétiques | — | Théorie et démonstrations, pas de comptage d'arbres | — | **H1** (laplacien de gaussienne normalisé multi-échelle), **H7** (sélection d'échelle au lieu d'une résolution supposée connue) | oui (résumé de l'auteur) |
| P2 | Wulder M., Niemann K. O., Goodenough D. G. (2000). *Local Maximum Filtering for the Extraction of Tree Locations and Basal Area from High Spatial Resolution Imagery*. Remote Sensing of Environment 73(1): 103-114. https://doi.org/10.1016/S0034-4257(00)00101-2 | Filtre de maximum local, fenêtre fixe 3 × 3 contre fenêtre variable dérivée de la semi-variance | Forêt de conifères, Canada | 1 m | Seconde main : la fenêtre variable réduit omissions et commissions ; rayon de couronne d'environ 1,5 m minimum à 1 m/px | Forêt | H1 ; taille de fenêtre liée à l'échelle (H7) | partiel |
| P3 | Pouliot D. A., King D. J., Bell F. W., Pitt D. G. (2002). *Automated tree crown detection and delineation in high-resolution digital camera imagery of coniferous forest regeneration*. Remote Sensing of Environment 82(2-3): 322-334. https://doi.org/10.1016/S0034-4257(02)00050-0 | Maxima locaux puis transects radiaux depuis chaque sommet ; bord de couronne au maximum du taux de variation ; une seule cime gardée par contour | Régénération de conifères de 6 ans | 5 à 30 cm/px testés | Seconde main : détection 91 % au mieux, meilleure que les filtres de maximum à fenêtre fixe ; erreurs inacceptables à 30 cm | Plants jeunes, plutôt espacés | H1, profil radial (H5b), « un seul maximum par couronne » ; effet de résolution (H7) | partiel |
| P4 | Daliakopoulos I. N., Grillakis E. G., Koutroulis A. G., Tsanis I. K. (2009). *Tree Crown Detection on Multispectral VHR Satellite Imagery*. Photogrammetric Engineering & Remote Sensing 75(10): 1201-1211. https://doi.org/10.14358/PERS.75.10.1201 | « Arbor Crown Enumerator » : seuils sur la bande rouge et le NDVI, puis détection de taches par **laplacien de gaussienne** | QuickBird 4 bandes, bassin de Keritis, Crète ; vergers, oliviers, forêt ouverte | 0,7 m (pansharpening) | Seconde main : réduit l'effort de comptage ; pas de chiffre lu | Variée | **H1** (LoG sur masque de végétation), H5 | partiel |
| P5 | Srestasathiern P., Rakwatin P. (2014). *Oil Palm Tree Detection with High Resolution Multi-Spectral Satellite Imagery*. Remote Sensing 6(10): 9749-9774. https://doi.org/10.3390/rs6109749 | Choix de l'indice de végétation le plus discriminant, transformée de rang, maxima locaux par suppression des non-maxima ; **taille de fenêtre fixée par semi-variogramme** | Palmiers à huile, satellite multispectral | sous-métrique (non lue) | Seconde main : ≈ 90 % de détection contre un étiquetage manuel | Plantation régulière | H1, H5, estimation automatique de l'échelle (H7) | partiel |

### 1.3 Gabarits et corrélation

| # | Référence | Méthode | Données | Résolution | Métrique et résultat annoncé | Densité | Lien H | Vérifié |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G1 | Pollock R. J. (1996). *The Automatic Recognition of Individual Trees in Aerial Images of Forests Based on a Synthetic Tree Crown Image Model*. Thèse de doctorat, University of British Columbia. https://doi.org/10.14288/1.0051597 | Modèle de formation de l'image d'une couronne (géométrie + éclairage) servant de gabarit | Forêts boréales et tempérées, photographies aériennes | haute résolution (non lue) | Non lu | Forêt | H6 (forme explicite), gabarit paramétrique d'une plante | partiel |
| G2 | Larsen M., Rudemo M. (1998). *Optimizing templates for finding trees in aerial photographs*. Pattern Recognition Letters 19(12): 1153-1162 | Gabarit borné par une ellipse dont la taille, l'excentricité et le décalage sont optimisés ; cimes = maxima locaux de la corrélation | Épicéas, essai d'éclaircie en Norvège ; 3 images (éclairage latéral, contre-jour, de face) | non lue | Non lu ; comparaison avec des gabarits empiriques moyens | Forêt | Gabarits ; **effet de l'éclairage** (difficulté annoncée par la consigne) | partiel |

Rappel [M] (brief, section 2.3) : notre corrélation avec des gabarits moyens sur 8 rotations et symétries donne F1 0,36 sur MM1-MM2.

### 1.4 Votes : symétrie radiale et Hough

| # | Référence | Méthode | Données | Résolution | Métrique et résultat annoncé | Densité | Lien H | Vérifié |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V1 | Loy G., Zelinsky A. (2003). *Fast radial symmetry for detecting points of interest*. IEEE TPAMI 25(8): 959-973. https://doi.org/10.1109/TPAMI.2003.1217601 | Chaque pixel vote, le long de son gradient, à un ou plusieurs rayons ; accumulation d'orientation et de magnitude | Visages, images génériques | — | Plus de 60 images/s sur Pentium III ; aussi bon ou meilleur que les techniques de l'époque | — | **H4** (vote convergent), coût faible (processeur) | oui (notice ANU) |
| V2 | Ozdarici-Ok A. (2015). *Automatic detection and delineation of citrus trees from VHR satellite imagery*. International Journal of Remote Sensing 36(17): 4275-4296. https://doi.org/10.1080/01431161.2015.1079663 | Extraction de végétation, **symétrie radiale rapide (FRS)**, opérations orientées objet | GeoEye-1, deux sites d'agrumes | sous-métrique (non lue) | Jusqu'à 90 % de justesse en détection et délimitation ; meilleurs résultats en plantation régulière **avec peu de chevauchement** | Espacé (meilleur) ; dégradé si chevauchement | **H4** ; risque en canopée dense | oui (notice AGRIS) |
| V3 | Ok A. O., Ozdarici-Ok A. (2017). *Detection of Citrus Trees from UAV DSMs*. ISPRS Annals IV-1/W1: 27-34. https://doi.org/10.5194/isprs-annals-IV-1-W1-27-2017 ; suite : Ok & Ozdarici-Ok (2018), Int. J. Digital Earth 11(6): 583-608, https://doi.org/10.1080/17538947.2017.1337820 | **Symétrie radiale fondée sur l'orientation**, vérifiée par les maxima locaux ; (2018) régions d'influence et contours actifs | Modèles numériques de surface de drone, 5 (2017) puis 8 (2018) parcelles d'agrumes | non lue | Résumé : meilleur équilibre précision-rappel que l'état de l'art ; chiffres non lus | Densités variées | **H4** (vote orienté) + H1 (maxima) ; attention : entrée = hauteur, pas RVB | oui (2017, page de l'éditeur) ; partiel (2018) |
| V4 | Ballard D. H. (1981). *Generalizing the Hough transform to detect arbitrary shapes*. Pattern Recognition 13(2): 111-122. https://doi.org/10.1016/0031-3203(81)90009-1 | Table R : chaque point de contour orienté vote pour le point de référence d'une forme quelconque ; échelle et rotation en dimensions supplémentaires | — | — | — | — | **H4** (vote vers le centre selon l'orientation locale), H6 | partiel |
| V5 | Manandhar A., Hoegner L., Stilla U. (2016). *Palm tree detection using circular autocorrelation of polar shape matrix*. ISPRS Annals III-3: 465-472. https://doi.org/10.5194/isprs-annals-III-3-465-2016 | Descripteur de forme en coordonnées polaires (autocorrélation circulaire), réduit par SVM linéaire, puis maxima locaux de la carte obtenue | Images aériennes de palmiers, 8 images de test difficiles | non lue | 84 % et 76,1 % en moyenne (nature exacte de la mesure non précisée sur la page) | Plantations, cas difficiles | **H6** (forme étoilée des palmiers : utile pour les écarter), invariance par rotation | oui (page de l'éditeur) |

### 1.5 Orientation : tenseur de structure, filtres orientables

| # | Référence | Méthode | Données | Résolution | Métrique et résultat annoncé | Densité | Lien H | Vérifié |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| O1 | Bigün J., Granlund G. H. (1987). *Optimal orientation detection of linear symmetry*. Proc. 1st ICCV, Londres, p. 433-438 (rapport LiTH-ISY-I-0828, Linköping, 1986) | Tenseur de structure : orientation dominante = vecteur propre ; mesure de cohérence (symétrie linéaire) entre 0 et 1 | — | — | — | — | **H2, H3** (axe des feuilles, orientation des stries) ; cohérence = fiabilité | partiel |
| O2 | Freeman W. T., Adelson E. H. (1991). *The Design and Use of Steerable Filters*. IEEE TPAMI 13(9): 891-906. https://doi.org/10.1109/34.93808 | Filtres orientables : réponse à tout angle par combinaison de quelques filtres de base ; paires en quadrature (phase) ; pyramide orientable | — | — | — | — | **H2** (gaussiennes anisotropes orientées à faible coût), H3 | oui (page de l'auteur, MIT) |

### 1.6 Segmentation par partage des eaux

| # | Référence | Méthode | Données | Résolution | Métrique et résultat annoncé | Densité | Lien H | Vérifié |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| W1 | Wang L., Gong P., Biging G. S. (2004). *Individual Tree-Crown Delineation and Treetop Detection in High-Spatial-Resolution Aerial Imagery*. Photogrammetric Engineering & Remote Sensing 70(3): 351-357. https://doi.org/10.14358/PERS.70.3.351 | LoG pour masquer le fond, cimes = maxima de radiance près du centre, **partage des eaux contrôlé par marqueurs** pour séparer les couronnes jointives | Image aérienne CASI | non lue | Seconde main : accord « prometteur » avec la délimitation manuelle | Couronnes jointives | Séparation en canopée dense ; H1 | partiel |
| W2 | Yu K., Hao Z., Post C. J., Mikhailova E. A., Lin L., Zhao G., Tian S., Liu J. (2022). *Comparison of Classical Methods and Mask R-CNN for Automatic Tree Detection and Mapping Using UAV Imagery*. Remote Sensing 14(2): 295. https://doi.org/10.3390/rs14020295 | Maxima locaux et partage des eaux à marqueurs (sur modèle de hauteur) contre Mask R-CNN (RVB) | Jeune plantation, drone | non lue | F1 : Mask R-CNN RVB 94,68 % ; maxima locaux 87,86 % ; partage des eaux 85,92 % (méthodes classiques sur hauteur) | Jeune plantation | Ordre de grandeur de l'écart explicite / appris (H8) | oui (résumé Crossref) |

### 1.7 Modèles de scène : processus ponctuels marqués

| # | Référence | Méthode | Données | Résolution | Métrique et résultat annoncé | Densité | Lien H | Vérifié |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M1 | Perrin G., Descombes X., Zerubia J. (2004). *Tree crown extraction using marked point processes*. Proc. EUSIPCO 2004, Vienne, p. 2127-2130 ; et (2005) *Adaptive simulated annealing for energy minimization problem in a marked point process application*, EMMCVPR 2005 (volume LNCS non vérifié), HAL hal-00113382 | Couronnes = ellipses (centre, axes, orientation) ; densité = attache aux données + interaction (pénalise les recouvrements) ; RJMCMC et recuit simulé | Photographies aériennes infrarouges de peupleraies (IFN) | sous-métrique (non lue) | Pas de chiffre lu | Plantation régulière et forêt | Choix final des centres avec **a priori d'espacement** (≈ 2 m) ; H6 (ellipse) | partiel (pages HAL bloquées par un anti-robot) |
| M2 | Larsen M., Eriksson M., Descombes X., Perrin G., Brandtberg T., Gougeon F. A. (2011). *Comparison of six individual tree crown detection algorithms evaluated under varying forest conditions*. International Journal of Remote Sensing 32(20): 5827-5852. https://doi.org/10.1080/01431161.2010.507790 | Comparaison de 6 algorithmes : maxima locaux, suivi de vallées, croissance de régions, gabarits, espace d'échelle, processus ponctuels | 6 types de forêt, 3 pays européens | variable | Seconde main : **aucun algorithme ne réussit tous les cas** ; partitionner en peuplements homogènes avant la détection | Variée | H8 ; justifie un réglage par type de plantation (mesuré, jamais par jeu) | partiel |

### 1.8 Indices de végétation RVB et périodicité des rangées

| # | Référence | Méthode | Données | Résolution | Métrique et résultat annoncé | Densité | Lien H | Vérifié |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I1 | Woebbecke D. M., Meyer G. E., Von Bargen K., Mortensen D. A. (1995). *Color indices for weed identification under various soil, residue, and lighting conditions*. Transactions of the ASAE 38(1): 259-269. https://doi.org/10.13031/2013.27838 | Indices chromatiques ; **ExG = 2g − r − b** sur coordonnées normalisées | Diapositives de mauvaises herbes sur sols et résidus | — | Seconde main : teinte modifiée, 2g − r − b et g séparent le mieux plante et fond, à l'ombre comme au soleil | — | **H5** ; c'est l'indice de notre baseline (F1 0,37) | partiel |
| I2 | Gitelson A. A., Kaufman Y. J., Stark R., Rundquist D. (2002). *Novel algorithms for remote estimation of vegetation fraction*. Remote Sensing of Environment 80(1): 76-87 | **VARI = (G − R) / (G + R − B)**, peu sensible à l'atmosphère | Blé (fraction de 0 à 100 %), validation sur maïs, Nebraska | — | Seconde main : erreur sur la fraction de végétation < 10 % | — | **H5** ; robustesse à la lumière qui change d'un vol à l'autre | partiel |
| I3 | Aksoy S., Yalniz I. Z., Taşdemir K. (2012). *Automatic Detection and Segmentation of Orchards Using Very High Resolution Imagery*. IEEE TGRS 50(8): 3117-3131. https://doi.org/10.1109/TGRS.2011.2180912 | Filtres isotropes multi-granularité (rehaussent les arbres) ; régularité de plantation par profils de projection à plusieurs orientations | Ikonos, QuickBird, Google Earth | ≈ 0,6 à 1 m | Seconde main : bonne localisation des vergers ; chiffres non lus | Vergers réguliers | Rangées (contrainte activée par une mesure de régularité) ; H1 multi-échelle | partiel |

**Total : 25 références** (B1-B5, P1-P5, G1-G2, V1-V5, O1-O2, W1-W2, M1-M2, I1-I3). Vérifiées « oui » : B1, B2, B3, P1, V1, V2, V3 (2017), V5, O2, W2, soit **10**. Les autres ont une notice vérifiée mais un contenu de seconde main (« partiel »), sauf B5 (« non »).

## 2. Comparabilité avec notre métrique

- Notre métrique : F1 avec appariement de points à 1 m, sur plants principaux.
- Aucune source lue n'utilise exactement cette métrique. B1 apparie des boîtes (IoU 0,5) et ne publie pas de F1 ; B2 publie un F-score dont la tolérance n'a pas été lue ; W2 publie un F1 sur jeune plantation ; V2 publie une « justesse ».
- Aucune source ne distingue pieds mères et rejets. Les chiffres publiés portent sur « tous les plants visibles ».
- Conséquence : aucun chiffre publié n'est une référence à battre. Nos références restent F1 0,37 (ExG) et 0,36 (gabarits), et le v5 (brief, section 2.3). Demande à independent-evaluator (voir rapport).

## 3. Canopée dense et plants espacés

| Situation | Ce que disent les sources | Sources |
| --- | --- | --- |
| Plants espacés, plantation régulière | Les méthodes explicites atteignent des scores élevés : symétrie radiale jusqu'à 90 % (agrumes, peu de chevauchement), maxima locaux et partage des eaux F1 0,86 à 0,88 sur jeune plantation (hauteur), maxima locaux ≈ 90 % sur palmiers | V2, W2, P5 |
| Plants jeunes, petite taille | La résolution compte : la détection se dégrade à 30 cm/px (conifères) ; le rappel du détecteur appris chute de 0,79 à 0,46 entre 1,8 et 2,5 cm/px (bananiers) | P3, B1 |
| Canopée dense, couronnes jointives | Les sources signalent toutes la dégradation : FRS meilleure sans chevauchement ; maxima locaux de hauteur performants seulement si les palmes ne se chevauchent pas ; aucun algorithme universel ; séparation par partage des eaux à marqueurs ou par processus ponctuels avec terme d'interaction | V2, M2, W1, M1 |
| Bananier spécifiquement | Un bananier peut avoir plusieurs maxima (feuilles étalées autour du pseudo-tronc) ; forme irrégulière, couronne mobile | B1, B2 |

## 4. Synthèse : méthodes les plus prometteuses pour notre cas

Notre cas : canopée dense de bananiers, 1 à 5 cm/px, processeur seul, pieds mères seulement. Classement **proposé** [H], à départager par des expériences sur le développement (règle 3). Les critères chiffrés sont à fixer par independent-evaluator avant tout lancement.

### 4.1 Laplacien de gaussienne normalisé multi-échelle sur indice de couleur (P1, P4, P5, I1, I2) — témoin H1

- **Pourquoi** : coût minimal, une seule famille de paramètres (échelles σ), sélection d'échelle par extrema normalisés (Lindeberg), donc compatible avec H7. ExG et VARI sont calculables sans proche infrarouge.
- **Risques connus** : plusieurs maxima par bananier (B1) ; fusion de plants voisins en canopée jointive ; sensibilité à l'éclairage (G2). Notre baseline à une échelle plafonne à F1 0,37.
- **Expérience proposée** : rappel des candidats à 1 m, à budget de candidats égal à la baseline, ExG contre VARI, une échelle contre plusieurs (expérience minimale de H1 dans le brief).

### 4.2 Vote convergent orienté : symétrie radiale rapide et Hough généralisée (V1, V3, V4) — H4

- **Pourquoi** : c'est la seule famille publiée qui exploite explicitement « orientations qui convergent vers un centre ». FRS est rapide sur processeur (V1) et a été appliquée à des couronnes d'arbres (V2, V3). Le vote peut se faire le long de l'axe des feuilles (orientation du tenseur), et pas seulement le long du gradient.
- **Risques connus** : résultats publiés sur agrumes (couronnes compactes, quasi circulaires) et sur modèles de hauteur, pas sur RVB ; dégradation avec le chevauchement (V2) ; les palmiers sont aussi radiaux (brief, section 2.1).
- **Expérience proposée** : celle de H4 dans le brief (part des votes à moins de 1 m d'un centre annoté contre centres déplacés et orientations mélangées), en comparant le vote par gradient (FRS) et le vote par axe de feuille.

### 4.3 Tenseur de structure et filtres orientables pour l'axe des feuilles et les stries (O1, O2) — H2, H3

- **Pourquoi** : estimation d'orientation dense et bon marché ; la cohérence donne une fiabilité par pixel. Les filtres orientables (O2) réalisent des gaussiennes anisotropes à tout angle avec quelques convolutions, ce qui répond à l'indice « gaussiennes » et « orientations ».
- **Risques connus** : **aucun précédent publié trouvé sur bananier ou palmier** ; les stries dépendent de la résolution (H3a, inconnue 6 du brief) ; l'orientation est ambiguë à 180°, ce qui oblige à voter dans les deux sens.
- **Expérience proposée** : histogramme des écarts entre l'orientation du tenseur et la direction du centre annoté le plus proche, contre des centres tirés au hasard (H2, H3b), sur planches rééchantillonnées de 1 à 5 cm/px.

### 4.4 Séparation des couronnes jointives : partage des eaux à marqueurs ou processus ponctuel marqué (W1, M1, M2)

- **Pourquoi** : en canopée dense, le problème n'est plus de trouver de la végétation mais de décider combien de plants elle contient. Le partage des eaux à marqueurs (W1) est simple et rapide ; le processus ponctuel marqué (M1) ajoute un a priori d'espacement (≈ 2 m entre pieds, à sourcer par banana-morphology) et de forme.
- **Risques connus** : le processus ponctuel est coûteux (RJMCMC, recuit) et a de nombreux paramètres (poids d'interaction, schéma de refroidissement) ; aucun algorithme ne vaut pour tous les peuplements (M2) ; l'a priori d'espacement est faux en agroforesterie.
- **Expérience proposée** : à candidats fixés (issus de 4.1 ou 4.2), comparer suppression des non-maxima à rayon fixe, partage des eaux à marqueurs et sélection par énergie avec terme d'interaction ; mesurer le F1 à 1 m sur le développement dense, et le temps par hectare.

### 4.5 Gabarits paramétriques orientés (G1, G2, B2)

- **Pourquoi** : B2 est le seul résultat publié d'une méthode explicite sur bananier (F 0,74 à 0,86, multispectral, cadre GEOBIA). Un gabarit paramétrique (ellipse de G2, modèle de couronne de G1, ou étoile de feuilles de leaf-mathematician) peut porter H2 et H6.
- **Risques connus** : notre corrélation avec gabarits moyens fait déjà F1 0,36 [M] ; forme irrégulière et mobile du bananier (B2) ; effet de l'éclairage (G2).
- **Expérience proposée** : gabarit paramétrique (somme de gaussiennes anisotropes rayonnantes) contre gabarit moyen, même budget de candidats, même évaluation.

### Familles à rôle secondaire

- **Forme pour écarter les palmiers (V5, H6)** : le descripteur polaire de Manandhar et al. sert à reconnaître les palmiers ; un indicateur de ce type peut servir de **rejet** des candidats palmiers. Expérience : distributions de l'indicateur sur les négatifs palmiers du développement et autour des centres annotés.
- **Rangées par analyse de périodicité (I3)** : utile seulement là où une régularité est mesurée ; jamais imposée en agroforesterie. Expérience : régularité spectrale par tuile, comparée entre jeux denses et agroforesterie du développement.

## 5. Manques

- Texte intégral de B2 (Aeberli et al. 2021) non lu : résolution, paramètres du LMF et du TM, tolérance d'appariement inconnus. C'est la source la plus proche de notre problème.
- Aucune source sur la détection de bananiers par **stries** ou par orientation des feuilles.
- Aucune trace publique de la méthode de Philemon.
