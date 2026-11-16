# Veille du 14/11/2026 : la hauteur (MNS, CHM) pour le comptage des bananiers

Agent Veille hauteur, 14 novembre 2026.

Règles suivies :
- lecture en ligne seulement ;
- aucun téléchargement, aucun code exécuté, aucun compte ;
- aucune image des juges ni des tests ouverte.

Étiquettes :
- **[S]** source, suivie de **(page ouverte)**, **(recherche seulement)** ou **(page refusée)** ;
- **[O]** observé dans un document texte du dépôt, avec son chemin ;
- **[H]** hypothèse.

Abréviations :
- **MNS** : modèle numérique de surface, le haut de la végétation ;
- **MNT** : modèle numérique de terrain, le sol ;
- **CHM** : hauteur de végétation, égale à MNS − MNT.

---

## 0. Réponse courte

1. **Aucun jeu public de bananiers par drone ne publie à la fois un MNS (ou un CHM) et des annotations de plants.** Toutes les recherches (Zenodo, figshare, Mendeley, Dryad, GitHub, Kaggle, articles 2019-2026) mènent soit à des orthomosaïques sans MNS, soit à des articles dont les données sont « sur demande » ou sous embargo.
2. **La meilleure piste est déjà sur le disque : banavista.** Il contient 348 photos DJI brutes qui se recouvrent (recouvrement médian de 81 % entre photos voisines) et 52 087 boîtes `Bananas` [O, `docs/protocole_comptage_v5.md`, section 1]. On peut en tirer un MNS par photogrammétrie sans rien télécharger côté données. Deux inconnues :
   - les métadonnées GPS ont-elles survécu à l'export Roboflow ? Pour Plants-bana, Roboflow les a retirées [O, `docs/protocole_comptage_v3.md`, section 2] ;
   - y a-t-il un recouvrement latéral entre lignes de vol ? Il n'a pas été détecté [O, protocole v5, section 2].
3. **Logiciel** : la situation a changé en 2026.
   - **WebODM s'est séparé d'OpenDroneMap en avril 2026, et ses installeurs Windows sont désormais gratuits** (AGPL-3.0).
   - Le binaire Windows natif d'**ODM 3.6.2** reste gratuit lui aussi (AGPL-3.0, 245 Mo).
   - Les deux tournent sur un processeur à 8 cœurs sans GPU. Comptez 15 à 25 min pour une centaine de photos et 1 h à 2 h pour 225 à 500 photos, d'après les bancs d'essai officiels.

---

## 1. Tableau classé des jeux utilisables

« Utilisable » veut dire : photos brutes qui se recouvrent, ou MNS, **et** annotations de plants existantes.

### 1.1 Bananier et plantain

| Rang | Jeu | Ce qui permet la hauteur | Annotations | cm/px | Pays | Licence | Taille | Recoupement avec nos jeux | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **banavista** (Roboflow `banavista/banana-detection-4hbck`), déjà dans `data/roboflow/banavista.zip` | 348 photos DJI brutes 4 000 × 3 000, recouvrement médian de 81 % ; la session B est une mission de cartographie en lignes de 13 à 21 photos [O, protocole v5] ; 15 orthophotos, preuve que quelqu'un en a déjà tiré une mosaïque [O] | 52 087 boîtes `Bananas`, 870 `Others` [O] | ≈ 1,1 [O, règle des couronnes] | Tagum, Philippines [O] | CC BY 4.0 [O, protocole v5] | 976 Mo, **déjà local** [O, `ls`] | **c'est notre jeu d'entraînement et de validation dense** : aucun risque de fuite nouveau, mais le MNS calculé sur la validation (DJI_0862 à 0945) ne doit servir qu'à mesurer, jamais à régler | **meilleur candidat**, sous deux réserves : GPS probablement absent [H], recouvrement latéral non détecté. Page Roboflow non ouverte (refusée, 403). |
| 2 | **Jeunes bananiers Plants-bana**, originaux pleine résolution (`data/roboflow/plants_bana_originaux.zip`, Roboflow `work-sd4ee/plants-bana`) | 6 photos DJI 5 472 × 3 648 : `dji_0545`, `0547` et `0549` recouvrent les photos annotées à 44-74 % [O, `docs/consigne_annotation_jeunes_bananiers.md`] | points manuels `mere` / `rejet` sur `dji_0544` (validation), `0546` et `0548` (entraînement) [O] | ≈ 1,0 à 1,25 [O, protocole v3] | inconnu | CC BY 4.0 [O, `CONTEXTE_FIELD_SCAN.md`] | 157 Mo, **déjà local** | `dji_0544` est une validation | **petit banc d'essai** du calcul mère/rejet : 2 ou 3 photos par couple. Pas de métadonnées [O, protocole v3]. Échelle seulement par la règle des couronnes. |
| 3 | Aeberli et al. (UNE, Australie), « Remote Sensing applications for Banana Crops – Dataset », doi 10.25952/jjjx-q835 | 22 campagnes Parrot Sequoia multispectral ; la hauteur de canopée est dérivée dans l'article de 2023 (R² 0,77 contre le terrain, recherche seulement) | l'article de 2021 détecte des plants un par un (CNN, F 0,85 à 0,93, recherche seulement) ; **annotations publiées : non indiquées** | non indiquée [H : 3 à 6 cm/px pour une Sequoia] | Australie [S] | **non indiquée** | non indiquée : la liste des fichiers est vide (.tiff, .txt, .zip annoncés) | aucun | **à vérifier à la main** : contenu, licence, accès. Fiche https://hdl.handle.net/1959.11/56246 (page ouverte). Articles MDPI *Remote Sens.* 13:2123 (2021) et 15:679 (2023) : pages refusées (403). La déclaration de disponibilité des données n'a pas pu être lue. |
| 4 | Fan, Chung, Yen, *CMC* 84(3), 2025 (Taïwan) | 470 photos, recouvrement 85 % / 80 %, orthomosaïque par SfM (recherche seulement) | 7 240 boîtes (voir `veille_comptage.md`) | 1,73 | Pingtung, Taïwan | données sur demande | — | aucun | **non ouvert** : une demande aux auteurs relève de Corentin |
| 5 | Selvaraj et al., *Sci. Rep.* 15:3491, 2025 | 6 854 images de drone RGB à 60 m [O, `out/prospection_nuit_1311/candidats.md`] ; recouvrement et photos brutes non vérifiés [H] | chaque plant annoté (≈ 23 550) [O, candidats.md] | 1,2 à 1,4 | RDC, Vietnam | sur demande | — | aucun | **non ouvert** (même démarche) |

### 1.2 Jeux de bananiers sans issue pour la hauteur

| Jeu | Pourquoi |
| --- | --- |
| **ReforesTree** (Zenodo 6813783, CC BY 4.0, 7,5 Go) | Vérifié en priorité. La page Zenodo (ouverte) ne liste qu'un fichier, `reforesTree.zip`, et ne mentionne ni MNS, ni MNT, ni nuage de points. Le README GitHub (ouvert) annonce des « Raw drone RGB images (see wwf_ecuador) », mais le dossier contient en réalité 6 orthomosaïques GeoTIFF et 100 tuiles PNG, sans photos brutes ni MNS [O, `docs/carnet_de_donnees.md`, section 6]. Les relevés de terrain contiennent espèce, diamètre, biomasse et position, **mais pas la hauteur** [S, README ; article arXiv 2201.11192, page ouverte]. Mavic 2 Pro, vols de 2020, WWF Équateur. Les photos brutes n'existent que chez WWF Équateur ou les auteurs [H]. |
| `banana_trees_kp` (Roboflow `test-purpose/banana-trees-cpzur`) | Photos DJI brutes, mais réduites et étirées en 640 × 640 [O, `data/roboflow_nuit_1112/comptage/BILAN.md`] : la photogrammétrie serait très dégradée. Surtout, c'est **le test vierge** : à ne pas toucher. |
| Count banana plants (`count-banana-plants`) | Découpes de 456 à 483 px dans des photos (`100_0221_0138_2880_960`) [O, `docs/recherche/notes/image-analyst.md`] : il manque les photos entières. |
| `plantas_platano`, `platano_lasuiza`, `banano_dense` (banano-qpl6j), `banana_tree_detection`, segmento (Plants-bana) | Ce sont des tuiles d'orthomosaïques [O, protocoles v4 et v5]. Aucun MNS n'est publié avec, d'après nos exports [O]. Les pages Roboflow n'ont pas pu être ouvertes (refusées, 403) : impossible de vérifier si l'auteur publie ailleurs les photos ou le MNS. [H] Peu probable sur Roboflow, qui ne gère que des images 2D. |
| El Oro (OpenAerialMap `5bf6a8940d1a8c00054a41cb`) | Pas d'annotations [O]. Métadonnées OAM non lues : l'API a répondu 500. |
| Neupane et al. 2019 (figshare 10.6084/m9.figshare.7981547) | Embargo permanent [S, recherche seulement ; O, `CONTEXTE_FIELD_SCAN.md`]. |
| Bananeraie du Yunnan, *Front. Plant Sci.* 2024, doi 10.3389/fpls.2024.1508549 (page ouverte) | 3 880 photos à 5, 8 et 12 m, recouvrement 80 % / 90 %, masques d'instances. Pas de MNS. Disponibilité des données non lue (page tronquée). Altitude sans rapport avec la nôtre. |
| ALSS-YOLO-Seg (arXiv 2410.07955, page ouverte) | Segmentation de bananeraie ; aucune publication de données ni de MNS. |
| Science Data Bank 10.57760/sciencedb.07000 (Guangxi) | Orthomosaïque multispectrale à 8 cm/px (recherche seulement). Pas d'annotation de plants vérifiée [O, candidats.md]. |

### 1.3 Repli : cultures et forêts proches avec MNS, CHM ou photos brutes (à part)

| Jeu | Hauteur | Annotations | cm/px | Lieu | Licence | Taille | Intérêt pour nous |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OliveTreeCrownsDb, Mendeley `xym8rd2srf` v3 (page ouverte) | nuage de points et MNE fournis ; 46 photos de Phantom 4 RTK à 74,7 m | couronnes d'oliviers, type non précisé, nombre non indiqué | non indiquée | Meknès, Maroc | CC BY 4.0 | non indiquée | petit jeu propre pour **tester la chaîne MNS → maxima locaux** sur des arbres isolés. Culture éloignée du bananier. |
| Palmiers de forêt amazonienne, Dalagnol et al., Zenodo 5670268 (recherche seulement) | CHM **LiDAR** | ≈ 7 000 palmiers en masques, 2 269 imagettes | non vérifiée | Amazonie brésilienne | CC BY 4.0 [S, recherche] | non vérifiée | palmiers sur CHM. Pas de photogrammétrie ni de RGB, d'après le résumé. |
| BCI 50 ha, Smithsonian figshare 10.25573/data.24784053 | **MNS fourni** comme 4e canal (recherche seulement) | 2 280 couronnes, 112 espèces | 4 | Panama, forêt tropicale | non vérifiée (page refusée, 403) | non vérifiée | forêt naturelle. Utile seulement pour l'idée « MNS + RGB ». |
| Plantations du Québec, FRDR doi 10.20383/103.0979 (recherche seulement) | MNS photogrammétrique, LiDAR, **hauteurs mesurées au sol** | polygones de couronnes, espèces | non vérifiée | Québec, tempéré | non vérifiée | non vérifiée | **exclu** : téléchargement par Globus, donc compte obligatoire. |
| BAMFORESTS (*Remote Sens.* 2024, recherche seulement) | MNS corrigé | 27 160 couronnes | non vérifiée | Bamberg, tempéré | CC BY 4.0 [S, recherche] | non vérifiée | forêt tempérée : faible intérêt. |
| Palmiers FCAT, Zenodo 17094346 (page ouverte) | aucune ; « raw patches » de 912 px, donc des découpes et non des photos entières [S, arXiv 2509.12400, page ouverte] | 5 850 boîtes, 5 430 centres de couronnes | non indiquée ; Phantom 4 RTK à 90 m | Esmeraldas, Équateur | CC BY 4.0 | 2,9 Go | pas de hauteur possible. Région côtière d'Équateur, comme ReforesTree, mais réserve forestière distincte [H]. |
| SelvaBox, Hugging Face `CanopyRS/SelvaBox` (page ouverte) | aucune | 83 000 boîtes de couronnes | 4,5 (sources de 1,2 à 5,1) | Brésil, Équateur, Panama | CC BY 4.0 | 31,3 Go | pas de MNS. |
| Palmiers à huile, Mendeley `nh7d23dgnw` et `xj4rs77c4j` (recherche seulement) | aucune mentionnée | palmiers sains / anormaux ; classes de terrain | — | Indonésie [H] | non vérifiée | — | pas de MNS. |

**Constat** : aucun jeu tropical de culture (bananier, plantain, palmier à huile, cocotier, papayer, cacao) ne publie ensemble MNS ou CHM et annotations de plants. Plusieurs articles calculent pourtant un CHM :
- bananier : Aeberli 2021 et 2023 ;
- palmier à huile : Fawcett 2019, Sarawak (recherche seulement).

Aucun ne publie ses données.

### 1.4 Ce que disent les sources sur l'apport de la hauteur

- [S] *Assessing SAM for Tree Crown Instance Segmentation from Drone Imagery*, arXiv 2503.20199 (déjà cité dans `veille_comptage.md`) : ajouter le MNS aide tous les modèles.
- [S] *Bringing SAM to new heights* (BalSAM), arXiv 2506.04970 (page ouverte, résumé) :
  - le MNS « s'obtient sans coût supplémentaire » à partir des photos RGB du drone ;
  - BalSAM montre du potentiel, « surtout dans les plantations ».
- [S] Aeberli et al. 2021 (recherche seulement) : des maxima locaux détectent des bananiers un par un, avec un F de 0,73 à 0,86 (contre 0,85 à 0,93 pour le CNN). Les recherches ne disent pas si ces maxima portent sur une hauteur ou sur un indice.
- [S] Fawcett et al. 2019, palmier à huile (recherche seulement) : les maxima locaux du CHM marchent le mieux **quand le palmier dépasse le sous-étage**.
  - [H] Pour nous, cela favorise l'usage « écarter les grands arbres d'ombrage », mais ne garantit pas la séparation des couronnes jointives de même hauteur, cas de la plantation dense.

---

## 2. Logiciel de photogrammétrie gratuit

### 2.1 Ce qui a changé en 2026 (vérifié)

- [S] README de `github.com/WebODM/WebODM` (page ouverte) :
  - « Official, up-to-date WebODM installers are free to download » ;
  - « If you paid for an installer after April 2026, you bought a different software » ;
  - « WebODM is not affiliated with OpenDroneMap » ;
  - « For processing, WebODM uses ODX, not ODM ».
- [S] webodm.org/download (page ouverte) : « 100% Free ». Le lien pointe directement vers une version GitHub. Aucune inscription n'est mentionnée. Configuration : Windows 10 ou plus récent, 8 Go de RAM au minimum, 16 Go conseillés ; 20 Go de disque au minimum, 100 Go conseillés.
- [S] opendronemap.org/download (page ouverte) : **vend toujours** un installeur WebODM, 64 $ (Standard) ou 149 $ (Business). « We currently do not offer free trials » ; installation manuelle gratuite possible. C'est l'installeur payant dont parlait la consigne. Il existe toujours, mais n'est plus le seul.
- [S] Séparation datée du 6 avril 2026 par des sources secondaires (recherche seulement) : community.opendronemap.org « Ecosystem Changes », un billet aerocartwright, un article SkyeBrowse. Les images Docker du fork sont dans l'espace `webodm/`.

### 2.2 Options gratuites sous Windows 11

| Option | Licence | Installation | Téléchargement | GPU | Remarques |
| --- | --- | --- | --- | --- | --- |
| **ODM 3.6.2, binaire Windows natif** (`ODM_Setup_3.6.2.exe`) | AGPL-3.0 [S, GitHub] | installeur, puis console « ODM Console » : `run C:\...\projet` (le dossier `images\` est dedans) [S, README ODM] | **244 864 104 octets ≈ 245 Mo** [S, API GitHub, publié le 12/08/2026] | facultatif (CUDA, extraction SIFT environ 2 fois plus rapide) | ligne de commande, **sans Docker**. Version stable et âgée de 3 mois. La 3.6.0 n'avait pas d'installeur ; la 3.6.1 est « the first installable release since 3.5.6 » [S, notes de version]. |
| **ODX** (fork d'ODM, `github.com/WebODM/ODX`) | AGPL-3.0 [S] | « download the latest Windows setup » depuis la page des versions, puis « ODX Console » [S, page ouverte] | taille non relevée | facultatif, activé par défaut sous Windows ; désactivable par `--no-gpu` [S] | moteur du WebODM actuel |
| **WebODM 4.0.0** (`WebODM_Setup.exe`, interface web locale + ODX) | AGPL-3.0 [S] | installeur gratuit | **479 324 480 octets ≈ 479 Mo** [S, API GitHub, publié le **04/11/2026**] ; la v3.3.2 du 29/10/2026 pèse 545 Mo | facultatif | interface confortable. La 4.0.0 n'a que 10 jours : [H] préférer la 3.3.2 ou ODM 3.6.2 pour la stabilité. |
| ODM par Docker (`opendronemap/odm:latest`) | AGPL-3.0 | Docker Desktop, puis `docker run ... --project-path` | image ≈ **627 Mo** compressée (amd64, 21/08/2026) [S, Docker Hub] ; la variante `gpu` fait 3,26 Go | facultatif | Docker Desktop est gratuit pour l'usage personnel et l'enseignement [H : non revérifié aujourd'hui]. Par défaut, il n'alloue que 2 processeurs et 20 Go de disque : à augmenter [S, docs.webodm.org]. Plus lourd que le binaire natif, sans avantage pour nous. |
| COLMAP | « new BSD » [S, colmap.github.io/license, page ouverte] | binaires Windows (GUI et ligne de commande, non signés) [S] | non relevée | **la reconstruction dense (`patch_match_stereo`) exige CUDA** [S, recherche seulement : message d'erreur du code source, rapports d'utilisateurs] | sans GPU local, seulement le nuage clairsemé : **pas de MNS dense sur notre machine**. Possible sur un GPU Kaggle [H, non vérifié]. |
| MicMac (IGN) | CeCILL-B [S, GitHub, page ouverte] | binaires précompilés annoncés sur la page des versions, non vérifiés | non relevée | pas de GPU mentionné | puissant mais austère. Production de MNS pour le drone non vérifiée sur la page. |

**Choix conseillé [H]** : le **binaire Windows natif d'ODM 3.6.2** (245 Mo). Il est gratuit, sans Docker et sans compte, stable depuis août 2026, et ne demande pas de GPU. Si Corentin préfère une interface, WebODM 3.3.2 (545 Mo, gratuit) fait le même travail avec ODX.

### 2.3 Durée sur 8 cœurs sans GPU

D'après les bancs d'essai officiels ODM, `github.com/OpenDroneMap/odm-benchmarks`, fichier `data-parsed/by-dataset.md` (page ouverte). Machine : Xeon E5-1620 à 8 cœurs, 56 à 64 Go de RAM, sans GPU indiqué.

| Jeu | Photos | Réglage « Default » | Réglage « DSM/DTM » | Autres |
| --- | --- | --- | --- | --- |
| Toledo | 87 | 15 à 19 min (photos réduites à 2 048 px), 24 à 25 min (pleine taille) | 26 min | « Forest » 51 min, « Field » 12 min |
| Wietrznia | 225 | 44 à 50 min (2 048 px), 1 h 44 à 1 h 46 (pleine taille) | 1 h 51 | « High Resolution » 1 h 50 |
| Shitan | 493 | 1 h 03 à 1 h 43 | 1 h 46 | « Forest » 2 h 51 |

- Machine plus récente (Ryzen 7 8845HS, 16 fils, 16 Go, ODM 3.5.4) : Toledo 27 min, Wietrznia 1 h 10 [S].
- [H] Pour banavista :
  - une ligne de 21 photos : quelques minutes ;
  - les 348 photos : de l'ordre de 1 h 30 à 3 h en pleine taille avec MNS ;
  - en pratique, lancer par ligne ou par session.
- **Mémoire** [S, docs.opendronemap.org/installation et docs.webodm.org, pages ouvertes] : 4 Go pour 40 photos, 16 Go pour 250, 32 Go pour 500 (RAM ou RAM + fichier d'échange). « No more than 100-200 images » avec 4 Go. La RAM de notre machine n'est pas notée dans `CLAUDE.md` : à vérifier avant tout lancement.
- **GPU** : la doc d'installation ODM dit qu'un GPU « currently has no impact on performance ». Le README ODM dit qu'il accélère environ 2 fois l'extraction SIFT seulement. Dans les deux cas, il est facultatif [S].

### 2.4 Sur Kaggle

- [H] Kaggle ne permet pas Docker dans les carnets. ODM ou ODX y demanderait une compilation native sous Ubuntu (dépendances lourdes, durée inconnue) : **aucune source ne confirme que cela fonctionne** [S, recherche seulement : aucun carnet Colab ou Kaggle trouvé].
- [H] COLMAP par conda-forge avec CUDA sur le GPU Kaggle est la seule voie dense plausible. Elle n'est pas vérifiée, et chaque installation y est un téléchargement soumis à accord.
- **Conclusion** : faire le calcul **en local** avec ODM. Le volume (quelques centaines de photos) le permet.

### 2.5 Ce qu'il faut en entrée

- **Recouvrement** [S, docs.opendronemap.org/flying, page ouverte] : 70 à 80 % pour les produits 2D et 2,5D (orthomosaïque, MNS) ; « for more complex buildings and vegetation, aim for closer to 80-83% overlap ». La page ne distingue pas recouvrement avant et latéral.
  - Banavista : 81 % vers l'avant [O].
  - [H] Le recouvrement latéral, non détecté, manque pour un bloc solide. Une seule ligne de vol se reconstruit, mais avec un risque de déformation en cuvette (*doming*), sans GPS ni points d'appui.
- **GPS** : ODM lit les géotags EXIF, ou un fichier de géolocalisation qui les remplace [S, recherche seulement]. Le comportement sans aucune coordonnée n'est pas confirmé par une source.
  - [H] La reconstruction se fait alors dans un repère local, sans échelle métrique.
  - [H] On peut retrouver l'échelle par la taille au sol connue : 1,07 à 1,13 cm/px pour banavista.
- **Nombre de photos** : pas de minimum documenté sur la page lue. Les bancs d'essai vont de 18 à 493 photos.
- **Limites propres au bananier [H]** :
  - le vent fait bouger les grandes feuilles d'une photo à l'autre, ce qui bruite l'appariement dense ;
  - en plantation dense à couronnes jointives, le sol est presque invisible : le MNT sera mal estimé, donc le CHM aussi ;
  - les maxima du MNS seul (hauteur relative) restent exploitables pour les sommets locaux ;
  - **nos orthomosaïques à 5-11 cm/px (segmento, `banana_trees_kp`) n'ont pas de photos brutes publiées** : la hauteur n'y sera jamais disponible.
- **Dans la chaîne réelle [H]** : les logiciels de photogrammétrie (ODM, Pix4D, Metashape, DJI Terra) produisent le MNS en même temps que l'orthomosaïque. Accepter un **MNS facultatif en entrée** de `run.py` coûterait peu à l'exploitant.

---

## 3. Ce qu'il faudrait télécharger si Corentin accepte

C'est Corentin qui décide de chaque point.

| Ordre | Quoi | Taille | Licence | But |
| --- | --- | --- | --- | --- |
| 0 | **Rien** : vérifier d'abord les EXIF (GPS, focale, modèle d'appareil) de quelques photos banavista de la **session A** (entraînement). Petit script local, à autoriser. | 0 | — | savoir si la photogrammétrie sera géoréférencée ou en repère local |
| 1 | **ODM 3.6.2, binaire Windows natif** : `https://github.com/OpenDroneMap/ODM/releases/download/v3.6.2/ODM_Setup_3.6.2.exe` (URL déduite du nom du fichier et de l'étiquette de version, à confirmer sur la page des versions) | ≈ 245 Mo (+ 20 à 100 Go de disque de travail) | AGPL-3.0 | calculer le MNS d'une ligne de banavista session A (21 photos), puis de toute la session A |
| 1 bis | à la place de 1, **WebODM 3.3.2** (`WebODM_Setup.exe`, github.com/WebODM/WebODM) | ≈ 545 Mo | AGPL-3.0 | même chose, avec une interface |
| 2 | facultatif : **OliveTreeCrownsDb** (Mendeley `xym8rd2srf` v3) | non indiquée sur la page | CC BY 4.0 | tester la chaîne MNS → maxima locaux sur des arbres isolés, avec un MNE de référence |
| — | démarches de Corentin, pas des téléchargements | — | — | demander les données à Aeberli (UNE ; contact sur la fiche), à Fan et al. (Taïwan) ou à Selvaraj et al. ; demander les photos brutes des vols ReforesTree à WWF Équateur ou aux auteurs |

**Expérience minimale proposée [H]**, à écrire en protocole avant tout lancement :
1. MNS d'une ligne de la session A de banavista (entraînement, jamais la validation pour régler).
2. Sommets locaux du MNS seul, puis fusionnés avec les détections du v5.
3. Critère écrit avant : le rappel en couronnes jointives progresse-t-il sur la session A ?
4. La validation (session B, DJI_0862 à 0945) ne sert qu'à la mesure finale, selon les règles du dépôt.

---

## 4. Sources ouvertes ou consultées

- https://zenodo.org/records/6813783 (ouverte) ; https://github.com/gyrrei/ReforesTree (ouverte) ; https://arxiv.org/html/2201.11192 (ouverte)
- https://rune.une.edu.au/web/handle/1959.11/56246?mode=full (ouverte) ; https://www.mdpi.com/2072-4292/13/11/2123 et https://www.mdpi.com/2072-4292/14/20/5206 (refusées, 403)
- https://universe.roboflow.com/banavista/banana-detection-4hbck (refusée, 403)
- https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2024.1508549/full (ouverte, lue en partie) ; https://arxiv.org/abs/2410.07955 (ouverte)
- https://huggingface.co/datasets/CanopyRS/SelvaBox/blob/main/README.md (ouverte) ; https://arxiv.org/abs/2506.04970 (ouverte) ; https://arxiv.org/html/2509.12400v2 (ouverte) ; https://zenodo.org/records/17094346 (ouverte) ; https://arxiv.org/abs/2410.11124 (ouverte) ; https://data.mendeley.com/datasets/xym8rd2srf/3 (ouverte)
- https://smithsonian.figshare.com/articles/dataset/Barro_Colorado_Island_50-ha_plot_crown_maps_manually_segmented_and_instance_segmented_/24784053 (refusée, 403) ; https://www.frdr-dfdr.ca/repo/dataset/9f10a155-c89f-43ee-9864-da28ca436af6 (recherche seulement) ; https://zenodo.org/records/5670268 (recherche seulement)
- https://github.com/OpenDroneMap/ODM (ouverte) ; https://api.github.com/repos/OpenDroneMap/ODM/releases (ouverte) ; https://docs.opendronemap.org/installation/ (ouverte) ; https://docs.opendronemap.org/flying/ (ouverte)
- https://github.com/WebODM/WebODM (ouverte) ; https://api.github.com/repos/OpenDroneMap/WebODM/releases (ouverte) ; https://webodm.org/download (ouverte) ; https://opendronemap.org/download/ (ouverte) ; https://docs.webodm.org/installation/ (ouverte) ; https://github.com/WebODM/ODX (ouverte)
- https://hub.docker.com/v2/repositories/opendronemap/odm/tags (ouverte) ; https://github.com/OpenDroneMap/odm-benchmarks/blob/master/data-parsed/by-dataset.md (ouverte)
- https://colmap.github.io/install.html et https://colmap.github.io/license.html (ouvertes) ; https://github.com/micmacIGN/micmac (ouverte)
- https://api.openaerialmap.org/meta/5bf6a8940d1a8c00054a41cb (erreur 500)

Aucun fichier n'a été enregistré par les outils. Les seules lectures locales portent sur des documents texte et sur la liste des archives de `data/roboflow/`.
