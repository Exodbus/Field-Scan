# Veille du 14/11/2026 : comptage des bananiers sur orthomosaïques de drone

Agent Veille, 14 novembre 2026. Mêmes règles que `veille_maladies.md` :
- lecture en ligne seulement ;
- aucun téléchargement, aucun code exécuté, aucun fichier enregistré par les outils ;
- **[S]** suivi de **(page ouverte)** ou **(recherche seulement)** ; **[H]** pour mes hypothèses.

Rappel de nos faiblesses (plan du 13/11, section 2) :
- plantation dense ;
- agroforesterie (pieds mères sous couvert) ;
- très jeunes plants ;
- 11 cm/px (le v5 n'y trouve plus que 55 % des pieds) ;
- fausses détections sans bananier : E5p90b gagne sur les juges, mais monte à 1,12 % de fausses détections pour une limite de 1 %.

---

## 1. Comptage et détection de bananiers par drone (2024-2026)

1. [S] **Comparative Analysis of Deep Learning Models for Banana Plant Detection in UAV RGB and Grayscale Imagery.** C.-L. Fan, Y.-J. Chung, S.-M. Yen. *Computers, Materials & Continua* 84(3):4627-4653, 2025. https://www.techscience.com/cmc/v84n3/63198/html (page ouverte).
   - Données : Pingtung (Taïwan), vol à 132 m, orthomosaïque à **1,73 cm/px**, 470 images, 7 240 bananiers annotés en boîtes, toutes tailles confondues.
   - Modèles comparés : RetinaNet (le meilleur : précision 96,7 %, rappel 71,7 %, F1 81,3 %), Faster R-CNN, YOLOv3, SSD.
   - **Niveaux de gris répliqués sur 3 canaux : meilleurs que la couleur pour les 4 détecteurs**, surtout pour les jeunes plants, qui ressemblent à des adventices.
   - La zone en association avec des aréquiers (ombre, couverts qui se chevauchent) est la plus dure : RetinaNet y fait 426 bons pieds et 314 ratés.
   - Limites, selon les auteurs : un seul site, un seul vol. Les tableaux ne sont pas tous cohérents entre eux.
   - Données « sur demande aux auteurs » : pas ouvertes.
2. [S] Comptage de jeunes bananiers par un Faster R-CNN amélioré, avec la stratégie « découper, reconnaître, recoller » et une **déduplication aux bords des morceaux** : l'erreur de compte moyenne passe de 1,60 % à 0,60 %. *Chinese Journal of Biotechnology*, octobre 2025 (recherche seulement ; titre et auteurs non relevés, pas d'URL directe obtenue).
3. [S] **Agroforestry inventory, one detection model per species.** Fiche Hugging Face, https://huggingface.co/JefersonPMS/agroforestry-inventory (page ouverte).
   - Poids sous **CC BY 4.0**, code sous GPL-3.0 (https://github.com/COURAGEOUS-LAND/agroforestry-inventory). Architecture non indiquée.
   - Un modèle « banane » appris sur une ferme agroforestière de São Paulo (Brésil), à 1,66 cm/px, avec 133 étiquettes sur 14 fenêtres.
   - Banane : précision 0,59, rappel 0,93. La fiche explique la faible précision : **les rejets d'une même touffe sont comptés comme des pieds séparés**.
   - [H] C'est notre problème « pied mère contre rejets » en agroforesterie. L'échelle est trop fine (1,66 contre 5 à 11 cm/px) et l'apprentissage trop petit pour nous servir de modèle.
4. [S] Neupane, Horanont, Nguyen. **Deep learning based banana plant detection and counting using high-resolution RGB images collected from UAV.** *PLOS ONE*, 2019. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6797093/ (recherche seulement ; antérieur à 2024, cité pour une idée). Fusionner les détections de deux altitudes (40 et 50 m) **récupère les pieds ratés par l'une ou l'autre** : rappel jusqu'à 99 %.
5. [S] Mora et al., *Sci. Rep.* 15:3491, 2025 (voir `veille_maladies.md`, 1.1) : détection par drone de plants sains / fusariose / Xanthomonas, YOLOv9, de 55 à 86 %. Le jeu est celui de Selvaraj, déjà noté dans `candidats.md`.
6. [S] Banane en association (Taïwan, VARI + apprentissage profond), *CMC* v82n2, https://techscience.com/cmc/v82n2/59494/html (recherche seulement). Cartographie des bananeraies en U-Net, vallée du Ribeira (Brésil), *ISPRS Archives* XLIX-B3-2026, p. 907 (recherche seulement). Cartographie, pas de comptage.

**Constat** : aucun article 2024-2026 ne compte des bananiers à 5-11 cm/px. Ils travaillent tous entre 1,2 et 1,7 cm/px. Notre problème de résolution n'est traité nulle part pour la banane.

---

## 2. Comptage par points et cartes de densité

1. [S] **Improving Point-based Crowd Counting and Localization Based on Auxiliary Point Guidance (APGCC).** I-H. Chen, W.-T. Chen, Y.-W. Liu, M.-H. Yang, S.-Y. Kuo. ECCV 2024, arXiv 2405.10589. https://apgcc.github.io (recherche seulement). Stabilise l'appariement entre propositions et points annotés : points auxiliaires et interpolation implicite des traits.
2. [S] **Point-to-Region Loss for Semi-Supervised Point-Based Crowd Counting.** W. Lin, C. Zhao, A. B. Chan. CVPR 2025 (highlight), arXiv 2505.21943. https://arxiv.org/abs/2505.21943 (page ouverte).
   - Semi-supervisé : quelques images annotées et beaucoup d'images pseudo-étiquetées.
   - En supervision point à point, la confiance des pseudo-étiquettes ne se propage pas au fond, et le réseau prend les activations du fond pour des objets.
   - La perte « point vers région » supervise une **région** autour de chaque pseudo-point.
   - Testé aussi en adaptation de domaine non supervisée. Code : https://github.com/Elin24/P2RLoss.
3. [S] **ZIP: Scalable Crowd Counting via Zero-Inflated Poisson Modeling.** Y. Ma, V. Sanchez, T. Guha. arXiv 2506.19955, juin 2025. https://arxiv.org/abs/2506.19955 (page ouverte).
   - Plus de 95 % des blocs de 8 × 8 sont vides.
   - Le compte de chaque bloc suit une loi de Poisson **à zéros gonflés** : un terme apprend la probabilité qu'un bloc soit **structurellement vide**.
   - Meilleur que l'erreur quadratique et DM-Count sur 4 jeux de foule, pour des réseaux de toutes tailles.
4. [S] Erreurs sur le fond en comptage de foule (Amazon Science, recherche seulement) : une branche de segmentation qui éteint le fond réduit l'erreur sur le fond de 10 à 83 %. Les modèles se généralisent mal à des fonds d'un type nouveau. https://cdn.amazon.science/f7/91/06c0a5874dcfaa45383db440e0d1/understanding-the-impact-of-mistakes-on-background-regions-in-crowd-counting.pdf (lien PDF, **non ouvert**).
5. [S] **TasselNetV4: A vision foundation model for cross-scene, cross-scale, and cross-species plant counting.** X. Hu, X. Li, J. Xu, …, H. Lu. arXiv 2509.20857, septembre 2025. https://arxiv.org/abs/2509.20857 (page ouverte). Dépôt : https://github.com/tiny-smart/tasselnetv4 (page ouverte).
   - Comptage « toutes plantes » par **exemplaires** : ViT simple, attention découplée, **compteurs locaux à plusieurs branches selon la taille des boîtes**, pour la robustesse d'une échelle à l'autre.
   - MAE inférieure de 18,3 % aux meilleurs compteurs sans classe fixée (chiffre de la recherche, pas du résumé).
   - Poids : 1,05 Go (Baidu ou Google Drive). Code sous Apache 2.0 ; licence des poids non indiquée.
   - Jeux : PAC-105 (2,8 Go, licence non indiquée) et PAC-Somalia.
6. [S] **Plant Taxonomy Meets Plant Counting: A Fine-Grained, Taxonomic Dataset for Counting Hundreds of Plant Species (TPC-268).** J. Xu, T. Hu, X. Hu, L. Zhou, S. Cao, M. Zhang, H. Lu. CVPR 2026 (oral), arXiv 2603.21229. https://cvpr.thecvf.com/virtual/2026/oral/40331 (recherche) ; dépôt https://github.com/tiny-smart/TPC-268 (page ouverte).
   - Les modèles du type TasselNetV4 montrent **un fort écart de généralisation sur les scènes inédites** (recherche seulement).
   - Jeu : 10 000 images, environ 678 000 points, 268 catégories, de la télédétection au microscope. Licence CC BY-NC (le badge dit NC-SA), « recherche académique seulement ».

---

## 3. Comptage sans classe fixée (exemplaires, texte)

1. [S] **DAVE: A Detect-and-Verify Paradigm for Low-Shot Counting.** J. Pelhan, A. Lukežič, V. Zavrtanik, M. Kristan. CVPR 2024, p. 23293-23302. https://openaccess.thecvf.com/content/CVPR2024/html/Pelhan_DAVE_-_A_Detect-and-Verify_Paradigm_for_Low-Shot_Counting_CVPR_2024_paper.html (recherche seulement).
   - Deux temps : d'abord un ensemble de détections **à fort rappel**, puis une **vérification** qui retire les aberrantes (par leurs traits, comparés aux exemplaires).
   - Environ 20 % de MAE en moins que les meilleurs compteurs par densité.
2. [S] **A Novel Unified Architecture for Low-Shot Counting by Detection and Segmentation (GeCo).** J. Pelhan et al. NeurIPS 2024, arXiv 2409.18686 (recherche seulement).
3. [S] **Generalized-Scale Object Counting with Gradual Query Aggregation (GeCo2).** J. Pelhan, A. Lukežič, M. Kristan. AAAI 2026, arXiv 2511.08048. https://arxiv.org/abs/2511.08048 (page ouverte). Dépôt : https://github.com/jerpelhan/GECO2 (page ouverte).
   - Les compteurs à exemplaires peinent sur les objets de tailles variées et les **amas denses de petits objets**. GeCo2 construit des requêtes denses multi-échelles à haute résolution.
   - Environ 10 % de mieux en comptage et en détection, 3 fois plus rapide, moins de mémoire.
   - Poids : un point de contrôle sur Hugging Face et les poids FSCD sur Google Drive (taille non indiquée). Raffinement des masques par SAM2. Licence dans le fichier LICENSE, non lue.
4. [S] **CountingDINO: A Training-free Pipeline for Class-Agnostic Counting using Unsupervised Backbones.** G. Pacini, L. Bianchi, L. Ciampi, N. Messina, G. Amato, F. Falchi. WACV 2026, arXiv 2504.16570. https://arxiv.org/abs/2504.16570 (page ouverte).
   - **Sans aucun apprentissage.**
   - Des prototypes sont extraits des traits DINO par ROI-Align sur les exemplaires. Ils servent de **noyaux de convolution** pour produire des cartes de similarité, normalisées en densité.
   - Compétitif avec des méthodes supervisées sur FSC-147. Code : https://lorebianchi98.github.io/CountingDINO/.
5. [S] **CountGD: Multi-Modal Open-World Counting.** N. Amini-Naieni, T. Han, A. Zisserman. NeurIPS 2024, arXiv 2407.04619 (recherche seulement). Requête par texte, par exemplaires, ou les deux.
6. [S] **T-Rex2: Towards Generic Object Detection via Text-Visual Prompt Synergy.** ECCV 2024, arXiv 2403.14610 ; DINO-X, arXiv 2411.14347 (recherche seulement). [H] Ces modèles me semblent accessibles surtout par API (compte), donc hors de nos règles ; non vérifié.
7. [S] **SAM 3: Segment Anything with Concepts.** N. Carion, L. Gustafson, Y.-T. Hu et al. arXiv 2511.16719 (v2 du 28/03/2026), ICLR 2026. https://arxiv.org/abs/2511.16719 (page ouverte). Dépôt : https://github.com/facebookresearch/sam3 (page ouverte).
   - Segmente **toutes les instances** d'un concept donné par un groupe nominal ou des exemplaires.
   - Comptage évalué sur CountBench et PixMo-Count (chiffres non vérifiés).
   - 848 M paramètres ; licence « SAM License » ; GPU CUDA requis.
   - **Points de contrôle soumis à accès sur Hugging Face** (demande d'accès et jeton) : il faut un compte, donc ce n'est pas faisable sans Corentin. Hors de nos règles en l'état.
8. SAM sur les couronnes d'arbres (recherche seulement) :
   - [S] **Assessing SAM for Tree Crown Instance Segmentation from Drone Imagery**, arXiv 2503.20199 (2025). SAM sans réglage ne bat pas un Mask R-CNN appris ; ajouter l'altitude (MNS) aide tous les modèles.
   - [S] **Zero-Shot Tree Detection and Segmentation from Aerial Forest Imagery**, arXiv 2506.03114 (2025). SAM2 guidé par les boîtes de DeepForest se transfère « raisonnablement ».

---

## 4. Régularité de la grille de plantation

1. [S] L. P. Osco et al. Réseau à deux branches qui **compte les plants et détecte les rangs** ensemble ; l'information des rangs est réinjectée dans la détection des plants. arXiv 2012.15827, *ISPRS J. Photogramm. Remote Sens.* 2021. https://arxiv.org/abs/2012.15827 (recherche seulement ; antérieur à 2024, référence de base).
2. [S] **CRISCO**, extension ImageJ libre : identification des rangs et comptage, segmentation des amas de plants. *Smart Agricultural Technology*, août 2025. https://doaj.org/article/6c51a097a0a14a27b231bf3654cbfc14 (recherche seulement). Marche mieux quand les rangs sont droits.
3. [S] **MaizeStandCounting**, comptage par rang à partir d'orthomosaïques ou de vidéos de drone. arXiv 2510.07580, octobre 2025 (recherche seulement).
4. [S] **Combining Object Detection with Geometry-Aware Clustering to Distinguish Overlapping Plants in UAV Imagery.** I. J. Lee, H. D. Nguyen, M. Meenar, C. Morrison Martinez, C. Connelly. arXiv 2609.21304, 18 septembre 2026. https://arxiv.org/abs/2609.21304 (page ouverte).
   - **Après** un détecteur, une étape géométrique décide si une région contient un plant ou deux : centroïdes des composantes, points d'intersection radiaux, K-moyennes et mélange de gaussiennes, filtrage par densité.
   - Sans réentraînement : F1 0,89 sur l'aubergine, 0,75 sur la tomate.
   - [H] Transposable à nos « deux pics pour un pied » (rosette de feuilles) et « un pic pour deux pieds » (plantation dense).

---

## 5. Robustesse à la résolution, super-résolution

1. [S] S. Velumani et al. Densité de maïs estimée par Faster R-CNN, effet de la résolution. arXiv 2105.11857, *Plant Phenomics* 2021. https://arxiv.org/abs/2105.11857 (recherche seulement ; antérieur à 2024, seule étude directe trouvée).
   - Sur les images natives en basse résolution, rRMSE 0,48.
   - Une super-résolution par GAN la ramène à 0,22, mieux qu'un agrandissement bicubique, mais **loin des performances sur les images natives en haute résolution**.
2. [S] *Remote Sensing* 17(5):906, mars 2025 (recherche seulement ; titre non relevé). Contre la super-résolution pour les petites cibles agricoles : découpage SAHI et YOLOv10n directement sur les images brutes. https://mdpi.com/2072-4292/17/5/906.
3. [S] **SRGT: Spatial Resolution Guided Teacher for Robust Semi-Supervised Aerial Object Detection.** *IEEE Transactions on Image Processing*, 2026 (recherche seulement). La GSD sert à pondérer les pseudo-étiquettes quand les distributions de GSD diffèrent entre données étiquetées et non étiquetées.
4. [S] Normalisation de la GSD par redimensionnement vers une GSD cible avant détection (ACRS 2019, recherche seulement ; ancien, cité pour l'idée).
5. [S] TasselNetV4 (compteurs selon la taille des boîtes) et GeCo2 (requêtes multi-échelles) visent explicitement la robustesse entre échelles (section 2).

[H] Pour nous :
- la super-résolution apprise est un téléchargement de plus, et le gain publié reste partiel ;
- l'essai le moins cher : agrandir les images à 11 cm/px vers la GSD d'apprentissage, à plusieurs facteurs, puis fusionner les pics (idée de Neupane 2019 : deux altitudes se complètent).

---

## 6. Négatifs (images sans bananier)

- [S] ZIP (2.3) : modéliser explicitement les blocs vides.
- [S] Branche de segmentation du fond (2.4) : réduit les erreurs sur le fond, mais généralise mal à des fonds nouveaux.
- [S] DAVE (3.1) : vérifier les détections a posteriori, par leurs traits.
- [S] P2R (2.2) : la supervision par points seuls laisse le fond mal contraint.
- [S] **Towards Partial Supervision for Generic Object Counting in Natural Scenes**, arXiv 1912.06448 (recherche seulement ; ancien) : perte BCE sur une cible nulle là où l'objet est absent, pour réduire les fausses détections.

---

## 7. Couronnes d'arbres et palmiers (pour les négatifs et les idées)

- [S] **PalmDSNet**, arXiv 2410.11124 (recherche seulement) : 7 356 boîtes et 7 603 centres de palmiers sur 5 orthomosaïques, 449 ha.
- [S] **Detection and Geographic Localization of Natural Objects in the Wild: A Case Study on Palms (PRISM)**, arXiv 2502.13023 (recherche seulement) : 8 830 boîtes et 5 026 centres de palmiers, 21 sites de l'ouest de l'Équateur. Détection et segmentation en zéro-coup.
- [S] arXiv 2509.12400 (septembre 2025, recherche seulement) : détection sur orthomosaïque contre images brutes de drone en forêt tropicale. **Ajouter des annotations de centres de couronnes à l'entraînement améliore la localisation.**
- [S] DINOv3 (arXiv 2508.10104, page ouverte) :
  - traits denses de grande qualité ;
  - d'après des résumés secondaires (recherche seulement), une version apprise sur satellite (SAT-493M) mène en hauteur de canopée ;
  - CHMv2 (cartes de hauteur de canopée de Meta, arXiv 2603.06382) s'appuie sur DINOv3.
