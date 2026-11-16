# Synthèse de la veille du 14/11/2026 : idées testables et jeux nouveaux

Agent Veille, 14 novembre 2026, de 18 h 31 à 19 h environ. Détail et références complètes :
- `docs/veille_2026-11-14/veille_maladies.md` ;
- `docs/veille_2026-11-14/veille_comptage.md`.

Règles suivies :
- aucun téléchargement, aucun code exécuté, aucun fichier enregistré par les outils (la lecture d'un PDF CEUR a été refusée ; je ne l'ai pas contournée) ;
- aucun juge ni test lu ;
- **[S]** = source (page ouverte ou recherche seulement, précisé dans les fichiers détaillés) ; **[H]** = mon hypothèse ;
- les coûts en heures sont des **estimations [H]**.

Chaque essai se mesure **sur le réglage seulement**, avec les règles déjà écrites du plan du 13/11 :
- maladies : section 4.3, coût de réglage à comparer à F1 ;
- comptage : section 5.3, référence v5, contrainte `val_negatifs` < 1 %.

Toute règle propre à l'essai (ordre, variantes, k, seuils) est écrite dans le journal de la piste avant le calcul.

Ce qui est **déjà au plan** et que je ne recompte pas comme une idée neuve : MB4 (maximum des morceaux), CB2 (inférence multi-échelle à 8 et 11 cm/px), CB3 (petits plants dans les trous), CE1 (augmentation de résolution), l'entraînement sensible au coût de M-piste2. Quand une source les renforce, je le dis.

---

## 1. Maladies : les 5 idées les plus prometteuses

### M1. Lecteur kNN et score d'inconnu sur les traits existants

**Source.** [S] Dong, Zhou, Fuentes, Yoon, Park, « Enhancing anomaly detection in plant disease recognition with knowledge ensemble », *Frontiers in Plant Science* 16, 2025, doi 10.3389/fpls.2025.1623907.
- Le score d'inconnu fusionne trois indices :
  1. max-logit ou énergie ;
  2. la **similarité cosinus maximale aux images d'entraînement** dans l'encodeur affiné ;
  3. la même dans l'encodeur préentraîné figé.
- Aucun entraînement. AUROC de 56,5 à 83,3 % avec 2 exemples par classe, 99,7 % avec tout.

**Pourquoi chez nous.**
- [H] Un lecteur kNN (P(malade) = vote des k plus proches voisins, pondéré par la similarité) se trompe autrement que les têtes softmax. Il apporterait donc de la diversité au mélange F1, là où les têtes se trompent de pays à pays.
- [H] La similarité maximale sépare les vraies « autres » des saines inhabituelles. On peut aussi la tester sur les photos « loin » : une saine vue de loin, proche de saines connues, n'aurait plus besoin de « à vérifier ».

**Coût.**
- Processeur : extraction des traits de l'entraînement et du réglage avec le ConvNeXt-Tiny DINOv3 déjà présent, environ 2 à 4 h sur 8 cœurs (3 fils au plus d'après l'avenant), puis quelques minutes de calcul.
- Ou Kaggle P100 : environ 0,5 h.

**Téléchargement.** Aucun : poids et données déjà sur le PC.

**Test (réglage).**
- Validation croisée par pays : les voisins d'une photo sont cherchés **seulement dans les autres pays**.
- k parmi {5, 10, 20}, fixé sur Tanzanie et TDTU avant de regarder les 3 autres jeux.
- Mesures :
  - (a) P(malade kNN) seule ;
  - (b) ajoutée au mélange géométrique de F1 avec un poids réglé sur le réglage ;
  - (c) règle « à vérifier → saine » si la similarité aux saines dépasse un seuil (vise les « à vérifier » de AgroVisionBD et `roamer_dev_loin_feuilles`).
- Critère : la règle 4.3 telle quelle.

### M2. Agréger les morceaux par fréquence au-dessus d'un seuil (style PlantCLEF 2025)

**Source.**
- [S] Gustineli, Miyaguchi, Cheung, Khattak, « Tile-Based ViT Inference with Visual-Cluster Priors for Zero-Shot Multi-Species Plant Identification », arXiv 2507.06093, 2025 :
  - 2e de PlantCLEF 2025 ;
  - grille de morceaux à la taille de lecture du réseau ;
  - **top-K des classes par fréquence** sur les morceaux ;
  - aucun réentraînement.
- [S] Herasimchyk, Labryga, Prusina, arXiv 2508.10457 (CLEF 2025 Working Notes, 3e) : morceaux multi-échelles, **seuil dynamique** réglé sur le nombre moyen de prédictions, filtre top-n.

**Pourquoi chez nous.**
- [H] Malades peu tachées : une tache sur un seul morceau est noyée dans la moyenne. Le maximum (MB4) est trop sensible au bruit.
- [H] Compter les morceaux au-dessus d'un seuil, avec un seuil qui dépend du nombre de morceaux lus, se place entre les deux.
- [H] Photos de loin : PlantCLEF est exactement le passage « entraîné sur gros plans, testé sur scènes ».

**Coût.** Processeur, moins de 1 h : les probabilités des morceaux sont en cache pour une partie du réglage (dont AgroVisionBD). Les jeux sans cache demandent une relecture des morceaux, 1 à 3 h.

**Téléchargement.** Aucun.

**Test (réglage).**
- Règle « alerte si au moins m morceaux sur 4 ont P(malade) ≥ s », avec m ∈ {1, 2} et une grille de s ; combinée à la photo entière par la règle de F1.
- Variante : agrégation log-somme-exponentielle de température τ.
- Grille écrite avant ; critère 4.3.
- À coordonner avec M-banc (MB4) pour ne pas compter deux fois le même essai.

### M3. Adaptation des normalisations au test, par lot d'un même champ ou pays

**Source.**
- [S] Wu, Han, Wang, Meng, Fu, « Detection techniques for tomato diseases under non-stationary climatic conditions » (CTTA-DisDet), *Frontiers in Plant Science* 16, décembre 2025 :
  - adaptation continue au test ;
  - maître en moyenne mobile (0,95), pseudo-étiquettes moyennées sur des augmentations ;
  - 10 % des poids remis à l'origine à chaque pas ;
  - mAP50 de 67,9 contre 63,1 sans adaptation, mais environ 11 fois plus de calcul.
- [S] La revue arXiv 2506.05972 (2025) place l'auto-apprentissage au cœur de l'adaptation de domaine en agriculture.

**Pourquoi chez nous.** [H] La faiblesse n° 1 est le changement de pays et d'appareil. La forme la moins chère :
- recalculer les statistiques des couches de normalisation par lot de l'**EfficientNet** sur les photos d'un même jeu ou pays, sans gradient ;
- pour le ConvNeXt (normalisation par couche) : un pas de minimisation d'entropie sur les seuls paramètres affines des normalisations.

C'est réaliste en service : le robot envoie les photos d'un même champ par lots.

**Coût.** Processeur : 1 à 2 h pour l'EfficientNet (une passe de statistiques et une passe de lecture par jeu). Version entropie sur ConvNeXt : 2 à 4 h de processeur, ou 1 h de Kaggle.

**Téléchargement.** Aucun.

**Test (réglage).**
- Lots de 32 à 64 photos tirés **dans un seul jeu**.
- Comparer le coût de chaque jeu avant et après adaptation.
- Garde-fou : aucun jeu ne perd plus de 2 points de taux de malades sans alerte (règle 4.3).
- Mesurer aussi l'effet sur un lot **déséquilibré** (90 % de saines), qui ressemble au cas réel : c'est le risque connu de ces méthodes [H].

### M4. Auto-apprentissage maître-élève sur photos non étiquetées, distillé par les logits seuls

**Source.**
- [S] Zhou et al., arXiv 2608.26771, août 2026 (thé, maître DINOv2) : **la distillation par les seuls logits avec température bat l'alignement des traits intermédiaires**, qui fait même baisser l'exactitude. Gain de 3,1 points, l'élève garde 98,3 % du maître. La distillation n'aide que si l'élève part sous le maître.
- [S] Lin, Zhao, Chan, CVPR 2025 (P2R) et CTTA-DisDet 2025 : pseudo-étiquettes supervisant une **région** et non un point ; maître en moyenne mobile.

**Pourquoi chez nous.**
- [H] L'élève distillé (ME1) vient d'être appris. Deux suites :
  - vérifier qu'il n'utilise pas de perte d'alignement de traits ; sinon, la retirer ;
  - l'apprendre aussi sur des photos **non étiquetées** des domaines faibles (photos « loin », pays du réglage en validation croisée), avec les probabilités de F1 comme cible douce, seulement au-dessus d'une confiance.
- Effet visé : généralisation par pays et photos de loin, tout en gardant le gain de temps de l'élève.

**Coût.** Kaggle P100 : 2 à 3 h (dans le budget de 3 h de M-piste2 si Corentin le confie à cette piste).

**Téléchargement.** Aucun, si les photos non étiquetées sont déjà sur le PC. Sinon, accord.

**Test (réglage).**
- Validation croisée par pays, comme ME1 : les photos d'un pays ne servent jamais de pseudo-étiquettes pour l'élève évalué sur ce pays.
- Critère 4.3, ou « variante rapide » (au plus 0,5 % de décisions différentes de F1, au moins 30 % plus rapide).

### M5. Choix du seuil d'alerte par contrôle conformel du risque, pays par pays

**Source.**
- [S] Angelopoulos, Bates, Fisch, Lei, Schuster, « Conformal Risk Control », ICLR 2024, arXiv 2208.02814 : un seuil choisi sur une calibration **garantit que l'espérance d'une perte monotone** (ici le taux de malades sans alerte) reste sous α, si calibration et test sont échangeables.
- [S] Ding, Fermanian, Salmon, ICLR 2026, arXiv 2507.06867 : couverture par classe pour les plantes (Pl@ntNet).
- [S] Fermanian et Hebiri, arXiv 2507.07150 : agrégation de **plusieurs photos d'une même plante** sous garantie.
- [S] Mohammadi-Seif et Baeza-Yates, IJCNN 2026, arXiv 2604.12693 : perte à **matrice de gravité** des confusions ; erreurs « fatales » réduites de 20 à 92 % (médical).

**Pourquoi chez nous.**
- [H] « Rater un malade est plus grave » se traduit naturellement en garantie, par exemple : taux de malades sans alerte ≤ 1 % sur un pays jamais vu.
- [H] Les seuils seuls sont fermés pour baisser le **coût moyen** (nuit du 12/11). L'intérêt ici est autre : **mesurer, en sortant un pays à la fois, si un seuil choisi sur 4 pays tient sa promesse sur le 5e**. Cela dit honnêtement combien la garantie de ratées est fragile d'un pays à l'autre.
- La perte à matrice de gravité relève de M-piste2 : je lui signale la référence.

**Coût.** Processeur, quelques minutes, sur les probabilités en cache.

**Téléchargement.** Aucun.

**Test (réglage).**
- Calibration sur 4 jeux de réglage, mesure sur le 5e, en tournant sur les 5 ; α ∈ {1 %, 2 %}.
- Rapporter, pour chaque jeu, l'écart entre α et le taux observé, et le taux de saines en alerte qui en résulte.
- C'est un **diagnostic**, pas un candidat au gel. Il ne passe la règle 4.3 que s'il baisse aussi le coût.

**Écartés après lecture** :
- BioCLIP 2 (MIT, ViT-L/14, environ 1,7 Go [H], téléchargement) : faible en zéro-coup sur PlantVillage (25,1 sur sa fiche).
- Modèles vision-langage généralistes : AgroBench, ICCV 2025.
- Adaptation continue complète au test : trop lente.

---

## 2. Comptage : les 5 idées les plus prometteuses

### C1. Vérification de chaque pic par prototypes (« détecter puis vérifier »)

**Source.**
- [S] Pelhan, Lukežič, Zavrtanik, Kristan, « DAVE: A Detect-and-Verify Paradigm for Low-Shot Counting », CVPR 2024 : un ensemble de détections à **fort rappel**, puis une **vérification par les traits** qui retire les aberrantes ; environ 20 % de MAE en moins.
- [S] Pacini et al., « CountingDINO », WACV 2026, arXiv 2504.16570 : prototypes extraits des traits DINO par ROI-Align, utilisés comme noyaux de similarité, **sans aucun apprentissage**.

**Pourquoi chez nous.**
- [H] C'est la pièce qui manque à E5p90b. La branche permissive v3 + v4 donne le rappel ; elle dépasse la limite de fausses détections (1,12 % pour 1 %) parce que 20 % des tuiles sans bananier y sont envoyées.
- [H] Mécanisme : un pic de la branche permissive n'est gardé que si son trait est plus proche des **prototypes « bananier »** que des **prototypes « fond / autre végétation »**.
  - Prototypes bananier : les pics forts du v5 **de la même orthomosaïque**.
  - Prototypes fond : `train` des négatifs, jamais `val_negatifs`.
- Vise directement la contrainte de CB1.

**Coût.** Processeur, 2 à 4 h : traits ConvNeXt-Tiny DINOv3 ou ResNet du v5 aux pics, sur les 5 validations et `val_negatifs`.

**Téléchargement.** Aucun.

**Test (réglage).**
- Seuil de marge réglé par la règle 5.3 (meilleure moyenne des 5 F1 sous `val_negatifs` < 1 %).
- Critère : finaliste 5.3.
- Indicateur écrit d'avance : part des tuiles de `val_negatifs` avec au moins un pic, avant et après vérification.

### C2. Squelette DINOv3 ConvNeXt-Tiny pour le détecteur de centres, avec une tête « bloc vide »

**Source.**
- [S] Siméoni et al., « DINOv3 », arXiv 2508.10104, 2025 : traits **denses** de grande qualité. D'après des résumés secondaires, il est fort en hauteur de canopée et en segmentation aérienne.
- [S] Ma, Sanchez, Guha, « ZIP: Scalable Crowd Counting via Zero-Inflated Poisson Modeling », arXiv 2506.19955, 2025 : plus de 95 % des blocs sont vides, et un terme qui apprend la **probabilité qu'un bloc soit structurellement vide** bat l'erreur quadratique et DM-Count.
- [S] Comptage de foule, Amazon Science : une branche qui éteint le fond réduit l'erreur sur le fond de 10 à 83 %.

**Pourquoi chez nous.**
- [H] Le ResNet du v5 est le seul composant non « fondation » de la chaîne. Les poids ConvNeXt-Tiny DINOv3 sont **déjà sur le PC** (maladies).
- [H] Une tête « bloc vide » apprise sur les tuiles d'entraînement sans bananier vise les fausses détections. Des traits plus robustes visent les changements de site (CG, agroforesterie).

**Coût.** Kaggle P100 : 2 à 3 h (une recette, 2 graines).

**Téléchargement.** Aucun nouveau poids. Les poids DINOv3 sont déjà acceptés sous leur licence pour les maladies ; à confirmer par Corentin pour un second usage [H].

**Test (réglage).**
- Recette du v5 inchangée, sauf le squelette ; puis la même avec la tête « bloc vide » (perte BCE sur blocs vides, sans toucher au noyau gaussien).
- Critère 5.3, famille B.
- À ajouter à CE1 si C-entraîneur ou C-piste2 a du budget : ce n'est pas au plan.

### C3. Spécialiste à exemplaires de la même orthomosaïque (plantation dense, jeunes plants)

**Source.**
- [S] Pelhan, Lukežič, Kristan, « Generalized-Scale Object Counting with Gradual Query Aggregation (GeCo2) », AAAI 2026, arXiv 2511.08048 : vise les **amas denses de petits objets** et les tailles variées ; environ 10 % de mieux que l'état de l'art, 3 fois plus rapide.
- [S] Hu et al., « TasselNetV4 », arXiv 2509.20857, 2025 : comptage « toutes plantes » par exemplaires, compteurs locaux selon la taille des boîtes.
- [S] Xu et al., « TPC-268 », CVPR 2026 : ces modèles montrent un **fort écart de généralisation** sur des scènes inédites.
- [S] CountingDINO (C1) : la même idée sans apprentissage.

**Pourquoi chez nous.**
- [H] En plantation dense et chez les très jeunes plants, la taille des pieds varie d'une parcelle à l'autre. Un compteur qui prend 3 à 5 pieds sûrs **de la même orthomosaïque** comme exemplaires s'adapte à l'échelle et à l'âge sans réentraînement. Les exemplaires sont choisis par le v5 (pics forts), jamais à la main.
- [H] TPC-268 rappelle que ces modèles se généralisent mal hors de leurs scènes : il faut les essayer seulement comme branche d'aiguillage, pas comme remplaçant du v5.

**Coût.**
- Variante sans téléchargement : CountingDINO réimplémenté avec nos traits ConvNeXt-Tiny DINOv3, processeur, 3 à 5 h.
- Variante GeCo2 ou TasselNetV4 : Kaggle T4 ou P100, 1 à 2 h d'inférence sur le réglage.

**Téléchargement.**
- Variante sans téléchargement : aucun.
- GeCo2 : point de contrôle sur Hugging Face, taille non indiquée, licence dans un fichier LICENSE non lu, plus SAM2 pour le raffinement → **accord de Corentin**.
- TasselNetV4 : 1,05 Go (Baidu ou Google Drive), code Apache 2.0, licence des poids non indiquée → **accord de Corentin**.

**Test (réglage).** Branche « dense / petits » de l'aiguillage, à la place de v3 + v4 ; même règle d'aiguillage qu'E5p90b ; critère 5.3, famille C.

### C4. Géométrie de plantation : force de la périodicité, et séparation ou fusion des pics

**Source.**
- [S] Osco et al., arXiv 2012.15827, *ISPRS J. Photogramm. Remote Sens.* 2021 : compter les plants et détecter les rangs **ensemble**, le rang aidant la détection.
- [S] CRISCO, *Smart Agricultural Technology*, 2025 : rangs et comptage, meilleur quand les rangs sont droits.
- [S] Lee et al., arXiv 2609.21304, septembre 2026 : après un détecteur, une étape géométrique (centroïdes, points d'intersection radiaux, K-moyennes et mélange de gaussiennes, sans réentraînement) **sépare deux plants qui se chevauchent** ; F1 de 0,89 sur l'aubergine.
- [S] Fiche `agroforestry-inventory` (Hugging Face) : le modèle banane compte **les rejets d'une même touffe comme des pieds**.

**Pourquoi chez nous.**
- [H] CB3 (trous) est déjà au plan. Ce qui manque : **une mesure de la force de la périodicité** (pic de l'autocorrélation ou de la transformée de Fourier des positions des pics, par fenêtre de 30 m environ) pour **n'activer** la recherche dans les trous **que là où la grille existe**. En agroforesterie (CG), il n'y a pas de grille, et la règle de CB3 y ferait des fausses détections.
- [H] Ajout : fusionner deux pics plus proches que 0,4 fois le pas local (rejets, double pic d'une rosette), et en séparer un quand la grille en attend deux.

**Coût.** Processeur, 2 à 3 h (numpy et scipy seulement, sans scikit-learn : K-moyennes à 2 centres écrites à la main).

**Téléchargement.** Aucun.

**Test (réglage).** Seuil de périodicité et rayon de fusion réglés par la règle 5.3. Indicateur écrit d'avance : nombre de pics ajoutés ou retirés sur `val_negatifs` (doit rester proche de 0) et sur MM1-MM2. À proposer à C-banc comme variante de CB3.

### C5. Fusion d'échelles par union, et niveaux de gris en augmentation (renforce CB2 et CE1)

**Source.**
- [S] Neupane, Horanont, Nguyen, *PLOS ONE* 2019 : fusionner les détections de deux altitudes **récupère les pieds ratés par chacune** (rappel jusqu'à 99 %).
- [S] Velumani et al., arXiv 2105.11857, 2021 : la super-résolution apprise fait mieux que l'agrandissement bicubique (rRMSE 0,22 contre 0,48), mais reste loin de la haute résolution native.
- [S] Fan, Chung, Yen, *CMC* 84(3), 2025 : les **niveaux de gris** améliorent les 4 détecteurs, surtout sur les jeunes plants et en association de cultures.

**Pourquoi chez nous.**
- [H] CB2 prévoit l'inférence multi-échelle ; la source indique la fusion à choisir : **union** des pics des échelles, avec suppression des doublons au rayon d'appariement du v5, plutôt que moyenne des cartes.
- [H] Super-résolution apprise : gain partiel publié et téléchargement de plus, donc pas prioritaire.
- [H] Pour CE1 et CE2 : ajouter une augmentation « niveaux de gris aléatoires » (p = 0,2) ne coûte rien et vise les jeunes plants.

**Coût.** Processeur, 1 à 2 h pour la fusion (sur les sorties de CB2). Pas d'heure de plus pour l'augmentation, si elle entre dans un entraînement déjà prévu.

**Téléchargement.** Aucun.

**Test (réglage).** Critère « finaliste résolution » de 5.3 (réglage dégradé à 11 cm/px ≥ v5 dégradé + 0,030, et 5 cm ≥ v5 − 0,005).

**Écartés après lecture** :
- SAM 3 : 848 M paramètres, points de contrôle **à accès contrôlé sur Hugging Face**, donc compte et jeton, hors de nos règles en l'état.
- T-Rex2 et DINO-X : accès par API probable [H].
- CountGD : à garder si Corentin veut un compteur par texte, mais sans avantage connu sur les plantes.
- Super-résolution apprise.
- P2R (semi-supervisé avec pseudo-étiquettes sur orthomosaïques non annotées) : prometteur, mais lourd (entraînement complet). À garder pour après le rendu.

---

## 3. Jeux de données ouverts nouveaux (absents de `out/prospection_nuit_1311/candidats.md`)

Bilan honnête : **aucun nouveau jeu ouvert de bananiers**, ni pour les maladies ni pour le comptage. Ce que la veille ajoute :

| Jeu | Module | Contenu | Taille | Licence | URL | Avis |
| --- | --- | --- | --- | --- | --- | --- |
| TPC-268 (Xu et al., CVPR 2026) | comptage | 10 000 images, environ 678 000 points, 268 catégories (242 espèces), de la télédétection au microscope | non indiquée | **CC BY-NC** (badge NC-SA), recherche académique seulement | https://github.com/tiny-smart/TPC-268 ; https://huggingface.co/datasets/jinyu-xu/TPC-268 | Pas une licence ouverte au sens du plan. Présence de *Musa* inconnue. Utile surtout comme négatifs « autres plantes » vues du dessus, si Corentin accepte une licence NC. |
| PAC-105 (+ PAC-Somalia), TasselNetV4 | comptage | comptage de plantes multi-espèces par exemplaires | 2,8 Go (PAC-105) | **non indiquée** | https://github.com/tiny-smart/tasselnetv4 (liens Baidu et Google Drive) | Licence à éclaircir avant tout usage. |
| PalmDSNet (arXiv 2410.11124) | comptage (négatifs) | 7 356 boîtes et 7 603 centres de palmiers, 5 orthomosaïques, 449 ha | inconnue | non vérifiée | https://arxiv.org/abs/2410.11124 | Palmiers : déjà représentés chez nous (Multiple tree). Faible priorité. |
| PRISM / PALMS (arXiv 2502.13023) | comptage (négatifs) | 8 830 boîtes et 5 026 centres de palmiers, 21 sites, ouest de l'Équateur | inconnue | non vérifiée | https://arxiv.org/abs/2502.13023 | Forêt tropicale avec palmiers, piège réaliste. Licence à vérifier. |
| Amaranthus retroflexus, positions (Oregon, 2025) | comptage (format points) | 6 279 et 6 182 centroïdes de plantes sur 16 parcelles, tuiles d'orthomosaïques | inconnue | non vérifiée | https://data.mendeley.com/datasets/wbj8fm8p8n | Adventices en climat tempéré : peu pertinent. |
| Poids `agroforestry-inventory` (banane, 1,66 cm/px) | comptage | **un modèle**, pas un jeu : détecteur banane appris sur 133 étiquettes (Brésil) | non indiquée | poids **CC BY 4.0**, code GPL-3.0 | https://huggingface.co/JefersonPMS/agroforestry-inventory | Résolution trop fine pour nous ; précision 0,59 (rejets comptés). Pas recommandé. |
| BLADE (Mendeley `w7ytz3twjv`, mai 2026) | maladies | **tableau de caractéristiques** (texture, couleur) extraites d'images 512 × 512, frontière Uttar Pradesh-Bihar (Inde) : Sigatoka, Cordana, saines | non relevée | non relevée | https://data.mendeley.com/datasets/w7ytz3twjv/1 | Pas d'images : inutilisable pour nos réseaux. |
| AgroBench (ICCV 2025) | maladies (évaluation vision-langage) | questions-réponses expertes ; 682 catégories de maladies | non relevée | non vérifiée | https://dahlian00.github.io/AgroBenchPage/ | Banc de questions, pas un jeu de classification. Pas recommandé. |
| Fan et al. 2025 (Taïwan) | comptage | 470 images de drone, 7 240 bananiers en boîtes, 1,73 cm/px | — | **sur demande aux auteurs** | https://www.techscience.com/cmc/v84n3/63198/html | Non ouvert : démarche de Corentin s'il le souhaite. Seul jeu « bananiers par drone » neuf trouvé. |

Déjà dans `candidats.md` ou chez nous, donc non répétés : Selvaraj / Mora et al. 2025 (*Sci. Rep.* 15:3491), Banana Leaves Imagery Dataset (Tanzanie), PlantVillage / Penn State, OAM-TCD, Paracou, `conteo-lzfcf`, ananas ITCR, caféiers.

---

## 4. À transmettre aux pistes (proposition, décision de la session principale)

- **M-piste2** : M5, la perte à matrice de gravité (Mohammadi-Seif et Baeza-Yates 2026), pour son entraînement sensible au coût ; M4, la distillation par logits seuls.
- **M-banc** : M2, à confronter à MB4 avant tout calcul.
- **C-piste2 et C-banc** : C1 (vérification des pics pour faire passer E5p90b sous 1 %), C4 (périodicité comme garde de CB3), C5 (fusion par union dans CB2).
- **C-entraîneur** : C2 ; niveaux de gris en augmentation (C5).
- **Corentin** : décider des téléchargements éventuels (GeCo2, TasselNetV4, BioCLIP 2), de la licence NC de TPC-268, et d'une demande de données à Fan et al.
