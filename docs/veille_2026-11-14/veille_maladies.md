# Veille du 14/11/2026 : maladies du bananier sur photos

Agent Veille, 14 novembre 2026, de 18 h 31 à 20 h environ. Lecture en ligne seulement : aucun fichier téléchargé, aucun code exécuté, aucun fichier enregistré par les outils (la lecture d'un PDF CEUR a été refusée par le garde-fou ; je ne l'ai pas contournée).

Étiquettes :
- **[S]** source : titre exact, premier auteur, année, lieu, URL. Je précise **(page ouverte)** quand j'ai lu la page de l'article (résumé arXiv, page de l'éditeur, fiche du dépôt), et **(recherche seulement)** quand je ne connais l'article que par les extraits du moteur de recherche ;
- **[H]** hypothèse de ma part, non vérifiée ;
- aucun chiffre de notre projet n'est donné ici : je renvoie au plan et aux journaux.

Rappel de nos faiblesses (plan du 13/11, section 2) : généralisation d'un pays à l'autre ; photos de loin (trop d'« à vérifier » sur les saines) ; malades peu tachées (Sigatoka jaune, Xanthomonas) ; temps de calcul ; coût asymétrique (3 × ratées + fausses alertes).

---

## 1. Travaux récents sur les maladies du bananier

1. [S] **Digital framework for georeferenced multiplatform surveillance of banana wilt using human in the loop AI and YOLO foundation models.** J. J. Mora, G. Blomme, N. Safari, S. Elayabalan, R. Selvarajan, M. G. Selvaraj. *Scientific Reports* 15:3491, 2025. doi 10.1038/s41598-025-87588-2. https://cgspace.cgiar.org/items/27c5e2de-e6d9-48b1-b934-d46338c88959 (recherche seulement).
   - Ce que dit la source : au sol, photos groupées par région (Afrique, Amérique latine, Inde, Asie, Australie), YOLOv8 en tête avec mAP@50, précision et rappel de 65 à 99 % selon l'organe et la région. Par drone, YOLOv9 en tête pour saines / fusariose / flétrissement bactérien (Xanthomonas), de 55 à 86 %. Un humain dans la boucle corrige les prédictions au sol.
   - Pour nous : c'est le jeu « Selvaraj » déjà noté dans `out/prospection_nuit_1311/candidats.md` (sur demande, non ouvert). Ce qui est neuf : l'écart de 65 à 99 % **selon la région** confirme que la généralisation par pays est le point dur, même chez eux.
2. [S] **Comparative Analysis of Deep Learning Models for Banana Plant Detection in UAV RGB and Grayscale Imagery.** C.-L. Fan, Y.-J. Chung, S.-M. Yen. *Computers, Materials & Continua* 84(3), 4627-4653, 2025. https://www.techscience.com/cmc/v84n3/63198/html (page ouverte). Voir surtout `veille_comptage.md` ; une leçon vaut aussi ici : passer en niveaux de gris a aidé les quatre détecteurs, surtout pour les petits plants. [H] Pour les maladies, c'est l'inverse qui est probable (les taches jaunes et brunes portent l'information) : ne pas transposer.
3. [S] Zanchetta, Watanabe, Araki. Classification CNN « sain / fusariose » de bananiers sur images multispectrales de drone, *ISPRS Annals* X-3-W4-2025, p. 371, publié en 2026 : 81,25 % d'exactitude au test, rappel à améliorer selon les auteurs. https://isprs-annals.copernicus.org/articles/X-3-W4-2025/371/2026/ (recherche seulement ; titre exact non relevé). Pas de RGB seul : peu utile pour nous.
4. [S] Actualité, non scientifique : le ministère de l'Agriculture philippin (région de Davao) teste depuis le 30/03/2026 des drones avec IA pour compter les bananiers et repérer les maladies (images multispectrales). https://www.sunstar.com.ph/davao/da-davao-tests-ai-drones-to-boost-banana-production (recherche seulement). Aucun résultat publié trouvé.
5. Le reste des articles « banane » de 2025-2026 trouvés (IntechOpen, JUTIF, revues de synthèse) évalue sur **un seul jeu** avec des exactitudes de 91 à 98 %. Rien d'utile pour la généralisation.

**Constat** : je n'ai trouvé aucun article 2024-2026 qui mesure la généralisation d'un pays à l'autre sur la banane. Nos validations croisées par pays sont déjà plus exigeantes que la littérature banane.

---

## 2. Modèles de fondation pour les plantes

1. [S] **DINOv3.** O. Siméoni et al. arXiv 2508.10104, août 2025. https://arxiv.org/abs/2508.10104 (page ouverte). Le résumé insiste sur des traits denses de grande qualité (« Gram anchoring ») et une suite de modèles pour diverses contraintes. C'est notre base actuelle.
2. [S] **BioCLIP 2: Emergent Properties from Scaling Hierarchical Contrastive Learning.** J. Gu et al. NeurIPS 2025 (spotlight), arXiv 2505.23883. https://arxiv.org/abs/2505.23883 (recherche seulement) ; fiche du modèle https://huggingface.co/imageomics/bioclip-2 (page ouverte).
   - Fiche : licence **MIT**, encodeur ViT-L/14 issu d'un CLIP LAION-2B. Sur PlantVillage, 25,1, sous SigLIP (28,5). Taille du fichier non indiquée ; [H] environ 1,7 Go pour un ViT-L/14 en float32. Une version 2.5 (ViT-H/14) existe.
   - Lecture : le gain de BioCLIP 2 porte sur l'identification des **espèces**, pas sur les maladies. Le score PlantVillage en zéro-coup est faible. [H] Il ne servirait qu'en sonde linéaire, comme lecteur de plus, ce qui demande un téléchargement.
3. [S] **SigLIP 2: Multilingual Vision-Language Encoders with Improved Semantic Understanding, Localization, and Dense Features.** M. Tschannen et al. arXiv 2502.14786, février 2025. https://arxiv.org/abs/2502.14786 (recherche seulement). Traits denses améliorés et variante NaFlex (résolution et rapport d'aspect d'origine). [H] La variante NaFlex lirait une photo de plante entière sans la déformer en carré ; à garder en réserve.
4. [S] **Rethinking Plant Disease Diagnosis: Bridging the Academic-Practical Gap with Vision Transformers and Zero-Shot Learning.** W. Benabbas, M. Brahimi, S. Akhrouf, B. Fortas. arXiv 2511.18989, novembre 2025. https://arxiv.org/abs/2511.18989 (page ouverte). Les CNN résistent mal au changement de domaine (labo vers champ), les ViT mieux, et CLIP en zéro-coup est présenté comme une adaptation peu coûteuse. Pas de chiffres dans le résumé.
5. [S] Modèles de fondation agricoles, **non vérifiés** (recherche seulement) :
   - Agri-FM+ (CVPR Workshops 2025, Al Nahian et al.), préentraînement continué sur Agri-147K : https://openaccess.thecvf.com/content/CVPR2025W/V4A/papers/Al_Nahian_Agri-FM_A_Self-Supervised_Foundation_Model_for_Agricultural_Vision_CVPRW_2025_paper.pdf ;
   - SPROUT (2026, Université de Tokyo), code et modèle annoncés sur https://github.com/UTokyo-FieldPhenomics-Lab/SPROUT ;
   - SCOLD (2025), vision-langage pour les feuilles : https://huggingface.co/enalis/scold.
   Aucun résultat de généralisation entre jeux n'a été vu. Pas prioritaire.
6. [S] **AgroBench: Vision-Language Model Benchmark in Agriculture.** Shinoda et al. ICCV 2025, arXiv 2507.20519. https://openaccess.thecvf.com/content/ICCV2025/html/Shinoda_AgroBench_Vision-Language_Model_Benchmark_in_Agriculture_ICCV_2025_paper.html (recherche seulement). 682 catégories de maladies, annotées par des agronomes. Les modèles vision-langage restent faibles en identification fine des maladies. Conclusion pour nous : un modèle vision-langage généraliste n'est pas une piste de remplacement.
7. **PlantCLEF 2025** (identification de plusieurs espèces sur des photos de quadrats, après un entraînement sur des photos d'une seule plante). C'est le cas le plus proche de nos photos de plante entière vues de loin, après un entraînement sur des gros plans.
   - [S] **Multi-Label Plant Species Prediction with Metadata-Enhanced Multi-Head Vision Transformers.** H. Herasimchyk, R. Labryga, T. Prusina. CLEF 2025 Working Notes, arXiv 2508.10457. https://arxiv.org/abs/2508.10457 (page ouverte).
     - DINOv2 ViT-B/14 ; morceaux à plusieurs échelles ; seuil dynamique réglé sur le nombre moyen de prédictions ; seuil sur les logits ; filtre top-n ; ensembles (bagging) ; recadrage des parties sans plante.
     - 3e au classement privé. Code : https://github.com/geranium12/plant-clef-2025/tree/v1.0.0.
   - [S] **Tile-Based ViT Inference with Visual-Cluster Priors for Zero-Shot Multi-Species Plant Identification.** Gustineli, Miyaguchi, Cheung, Khattak (DS@GT). arXiv 2507.06093, juillet 2025. https://arxiv.org/abs/2507.06093 (recherche seulement).
     - 2e place (macro-F1 0,348). Grille de 4 × 4 morceaux, à la taille de lecture du réseau (518 px).
     - Agrégation : on garde les **top-K espèces par fréquence** sur les morceaux, puis on applique des a priori par groupe visuel (PaCMAP + K-moyennes). Aucun réentraînement.
   - [S] Semenova, CLEF 2025 Working Notes (CEUR-WS Vol-4038, paper_252) : DINOv2 figé, morceaux multi-échelles et augmentation au test, sans réentraînement. https://ceur-ws.org/Vol-4038/paper_252.pdf (**non ouvert** : PDF, lecture refusée).

---

## 3. Généralisation entre pays et appareils, adaptation au test

1. [S] **Detection techniques for tomato diseases under non-stationary climatic conditions** (méthode CTTA-DisDet). Z. Wu, J. Han, S. Wang, X. Meng, R. Fu. *Frontiers in Plant Science* 16, 5 décembre 2025, doi 10.3389/fpls.2025.1704663. https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2025.1704663/full (page ouverte).
   - Adaptation **continue au test**, sans données sources. Un élève YOLOv9s fait un pas de gradient par image (taux 0,001) vers les sorties d'un maître.
   - Le maître est une moyenne mobile exponentielle de l'élève (0,95). Ses pseudo-étiquettes viennent de 8 versions augmentées de l'image, tirées parmi 32.
   - Pour limiter l'oubli : 10 % des paramètres de l'élève sont remis à leurs poids d'origine à chaque pas.
   - Résultats : mAP50 de 67,9 contre 63,1 (même augmentation, sans adaptation), 66,4 (LAME) et 64,8 (CoTTA). Sur PlantDoc, 49,8 contre 45,3.
   - Coût : 47 images/s contre 163, soit environ 11 fois plus de calcul.
   - Les auteurs comparent parfois à une base moins forte (60,6) : la marge annoncée n'est pas toujours à conditions égales.
2. [S] **Domain Adaptation for Big Data in Agricultural Image Analysis: A Comprehensive Review.** arXiv 2506.05972, 2025. https://arxiv.org/abs/2506.05972 (recherche seulement ; auteurs non relevés). L'auto-apprentissage par pseudo-étiquettes y est décrit comme la base de la plupart des adaptations semi-supervisées en agriculture.
3. [S] Isolated Test-Time Adaptation (ITTA) : seuls les paramètres « sensibles au domaine » de l'élève sont mis à jour. *Expert Systems with Applications*, 2025 (recherche seulement, sur un index chinois : référence à vérifier). https://search.napstic.cn/literature/periodical/0220250700359894.

[H] Ce qui s'applique chez nous sans réentraîner :
- l'EfficientNet a des couches de normalisation par lot : on peut recalculer leurs statistiques sur un lot de photos d'un même pays ou d'un même champ (forme la plus simple de l'adaptation au test) ;
- ConvNeXt n'a que des normalisations par couche : il faudrait mettre à jour leurs paramètres affines par minimisation d'entropie, avec un maître en moyenne mobile comme dans CTTA-DisDet.

---

## 4. Détection d'inconnus (open-set)

1. [S] **Enhancing anomaly detection in plant disease recognition with knowledge ensemble.** J. Dong, H. Zhou, A. Fuentes, S. Yoon, D. S. Park. *Frontiers in Plant Science* 16, 15 août 2025, doi 10.3389/fpls.2025.1623907. https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2025.1623907/full (page ouverte).
   - Score d'inconnu qui fusionne trois indices :
     1. la sortie du classifieur (max-logit ou énergie) ;
     2. l'opposé de la **similarité cosinus maximale** entre l'image et les images d'entraînement, dans l'espace de l'encodeur affiné ;
     3. la même similarité dans l'espace de l'encodeur **préentraîné figé**.
   - Aucun entraînement en plus.
   - Résultats : AUROC de 56,5 à 83,3 % (ConvNeXt affiné, 2 exemples par classe), et 99,7 % avec toutes les données. Sur PlantVillage, les 12 classes saines sont connues et les 26 maladies inconnues.
   - Code annoncé « bientôt » (https://github.com/JiuqingDong/Enhancing_Anomaly_Detection), non vérifié.
2. [S] Alfarisy et al., 2025 : ViT et score d'écart des top-K logits, meilleur AUROC connu / inconnu pour des espèces (recherche seulement, référence complète non relevée). https://journal.itk.ac.id/index.php/IIAIR/article/download/1227/741/7971.
3. [S] Jiang et al., 2022 (fraisier, OpenMatch) : la reconnaissance d'inconnus reste fragile sans **exposition à des exemples aberrants** pendant l'entraînement. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9520169/ (recherche seulement ; antérieur à 2024, cité pour la leçon).

[H] Pour nous, la similarité aux images d'entraînement peut servir à deux choses :
- **« autre »** : une photo loin de tout le connu (ni saine ni malade connue) ;
- **lecteur kNN** : P(malade) calculée à partir des k voisins les plus proches parmi les images d'entraînement (vote pondéré par la similarité). C'est un lecteur sans apprentissage, peu corrélé aux têtes softmax, donc utile dans le mélange.

---

## 5. Distillation, augmentation au test, calibration, coût asymétrique

1. [S] **Cross-Architecture Knowledge Distillation from a Vision Foundation Model to a Lightweight Visual State Space Model for Tea Leaf Disease Classification.** Z. Zhou et al. arXiv 2608.26771, 27 août 2026. https://arxiv.org/abs/2608.26771 (page ouverte).
   - Maître : DINOv2 affiné (22 M paramètres). Élève : 4,45 M paramètres.
   - **La distillation par les seuls logits (avec température) bat l'alignement des traits intermédiaires** ; l'alignement fait même baisser l'exactitude. Gain de 3,1 points ; l'élève garde 98,3 % de l'exactitude du maître.
   - La distillation n'aide que les élèves partis sous le niveau du maître.
2. [S] **Conformal Risk Control.** A. N. Angelopoulos, S. Bates, A. Fisch, L. Lei, T. Schuster. ICLR 2024, arXiv 2208.02814. https://arxiv.org/abs/2208.02814 (recherche seulement).
   - Choisit un seuil sur un jeu de calibration pour garantir que **l'espérance d'une perte monotone** (par exemple le taux de faux négatifs) reste sous α.
   - Garantie valable si calibration et test sont échangeables.
3. [S] **Conformal Prediction for Long-Tailed Classification.** T. Ding, J.-B. Fermanian, J. Salmon. ICLR 2026, arXiv 2507.06867. https://arxiv.org/abs/2507.06867 (recherche seulement). Couverture par classe (« Fuzzy CP »), appliquée aux plantes (Pl@ntNet).
4. [S] Fermanian et Hebiri, arXiv 2507.07150 (2025) : prédiction conforme qui **agrège plusieurs photos d'une même plante** et réduit l'ensemble prédit tout en gardant la garantie par classe (recherche seulement). [H] Cela correspond à nos photos multiples d'un même pied par le robot.
5. [S] **Risk-Calibrated Learning: Minimizing Fatal Errors in Medical AI.** A. Mohammadi-Seif, R. Baeza-Yates. IJCNN 2026, arXiv 2604.12693. https://arxiv.org/abs/2604.12693 (page ouverte).
   - Perte qui intègre une **matrice de gravité** des confusions : les erreurs « fatales » (malade vu comme sain) sont pénalisées, pas les confusions fines entre maladies voisines.
   - Erreurs critiques réduites de 20 à 92 % par rapport à la perte focale, sur 4 jeux médicaux. Formule non lue (dans le texte intégral).
6. [S] **Risk-Aware Robust Learning** (arXiv 2604.23875, avril 2026, recherche seulement) : perte pondérée par classe (20 contre 1) et étiquettes bruitées. Les poids forts ne marchent bien qu'avec un algorithme robuste qui garde la classe minoritaire représentée.

[H] Lecture pour nous :
- la matrice de gravité correspond exactement à notre coût : confusion Sigatoka noire / jaune = coût nul (alerte quand même) ; malade vers saine = 3 ; saine vers malade = 1 ;
- c'est le terrain de M-piste2 (« entraînement sensible au coût ») : je lui signale la référence, sans proposer de doublon.

---

## 6. Pseudo-étiquetage et auto-apprentissage

- [S] Revue arXiv 2506.05972 (voir 3.2) et CTTA-DisDet (3.1) : maître en moyenne mobile, pseudo-étiquettes moyennées sur plusieurs augmentations, remise à zéro partielle.
- [S] **Point-to-Region Loss for Semi-Supervised Point-Based Crowd Counting.** W. Lin, C. Zhao, A. B. Chan. CVPR 2025 (highlight), arXiv 2505.21943 (page ouverte). Leçon transposable : les pseudo-étiquettes doivent superviser **une région**, pas un seul point. [H] Pour les maladies, l'équivalent serait d'étiqueter un morceau par la décision de la photo entière seulement quand la confiance est haute (voir `veille_comptage.md`).
- Pas d'article 2024-2026 trouvé qui applique FixMatch ou un maître-élève à la banane entre pays.

---

## 7. Lecture multi-échelle et en morceaux, malades peu tachées

- PlantCLEF 2025 (section 2.7) :
  - grille de morceaux à la taille de lecture du réseau ;
  - agrégation **par fréquence des top-K** (DS@GT) ou seuil dynamique sur le nombre de prédictions (Herasimchyk et al.) ;
  - morceaux à plusieurs échelles (Herasimchyk, Semenova).
- [S] Soja, apprentissage à instances multiples (chaque photo est un « sac » de morceaux, cartes de chaleur du flétrissement). *Agriculture* 15(6):614, mars 2025. https://www.mdpi.com/2077-0472/15/6/614 (recherche seulement ; titre et auteurs non relevés).
- [S] Détection longue traîne avec branches multi-champ pour les lésions ponctuelles à étendues (CALM-Aug). *Plants*, MDPI, 2025. https://www.mdpi.com/2223-7747/15/8/1206 (recherche seulement ; titre et auteurs non relevés).

[H] Ce qui est neuf par rapport à nos essais :
- la lecture en 3 × 3 et le maximum des morceaux (MB4) sont déjà couverts ;
- non essayés : l'agrégation par **comptage des morceaux au-dessus d'un seuil** (fréquence top-K), le seuil qui dépend du nombre de morceaux, et le mélange « photo entière + morceaux » pondéré.

---

## 8. Ce que je ne recommande pas

- **Modèle vision-langage généraliste** comme lecteur (AgroBench : faible en identification fine des maladies).
- **BioCLIP 2 en zéro-coup** : 25,1 sur PlantVillage selon sa fiche. Seule une sonde linéaire aurait du sens, et elle demande un téléchargement d'environ 1,7 Go [H].
- **Adaptation continue lourde au test** (CTTA-DisDet complet : environ 11 fois plus de calcul) : contraire à notre faiblesse de temps.
