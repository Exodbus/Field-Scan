# Journal A1 : PlantVillage / Penn State, flétrissement bactérien (`bxw-leaf`), 16/11/2026

Rédacteur : l'agent A1, lancé par la session principale. Règles : `CLAUDE.md` section 1, et `docs/journee_2026-11-15/avenant_jeux_neufs.md` section A1.

- **0 h 30.** Lecture de `CLAUDE.md` et de l'avenant.
  - SHA-256 de l'avenant : `077ce1a17186360ab4d36822a0016a2fdd5f11d9dc911cd62a0b46de05b6f12b`, **identique** à `empreinte_avenant_jeux_neufs.txt` [M].
  - SHA-256 des deux archives identiques à `data/raw/plantvillage_psu/sha256.txt` [M].
- **0 h 37.** Extraction (`scripts/a1_extraire.py`, Python `-I`) dans `data/raw/plantvillage_psu/extrait/` :
  - 407 photos dans `bxw-leaf/`, sans `__MACOSX` ;
  - les 407 XML correspondants dans `annotations_bxw_leaf/` ;
  - `manifeste.csv` avec la taille et le SHA-256 de chaque photo.

  Rien n'est exécuté. Les noms sont vérifiés (aucun chemin absolu ni `..`) et écrits à plat.
- **0 h 38.** Inventaire des XML (`scripts/a1_decoupage.py`).
  - Fichiers Pascal VOC (`folder`, `filename`, `path`, `size`, `object`). **Aucun champ ferme, lieu ou date.**
  - Le pays n'est que dans le nom publié, le district ougandais et la date malawite que dans le nom d'origine.
  - Application de la seconde branche de la règle : blocs de 50 noms, en commençant par A1-test.
  - Résultat : A1-test 207 photos (DRC 150, Malawi 9, Uganda 48), A1-appr 200 (DRC 150, Uganda 50).
  - Écrit dans `out/jeux_neufs_1611/a1_decoupage.md` **avant tout contrôle et toute lecture par un modèle**.
- **0 h 41.** Écart de chemin noté : l'avenant prévoit le rapport de fuite dans `out/jeux_neufs_1511/controle_fuite.md`. La consigne de la session du 16/11 le place dans `out/jeux_neufs_1611/controle_fuite_a1.md`. On suit la consigne ; `out/jeux_neufs_1511/` n'est pas modifié (hors de la zone d'écriture).
- **0 h 41. Règle de retrait fixée avant le contrôle.** On applique l'avenant à la lettre : une photo d'A1-test sort du test si l'une de ces conditions est vraie :
  - (a) son SHA-256 est égal à celui d'une référence ;
  - (b) son nom d'origine, publié ou du XML, normalisé, est celui d'une référence ou d'une entrée de l'index ;
  - (c) son dHash est à 6 bits ou moins d'une référence, sous ses 8 symétries.

  L'écart de vignette est rapporté pour information (copie confirmée ou coïncidence probable), mais il **ne sauve pas** une photo. Une photo d'A1-test à dHash ≤ 6 d'une photo d'A1-appr sort aussi du test (fuite entre moitiés).
- **0 h 42 à 0 h 52.** Références complémentaires R3 (`scripts/a1_fuites.py references`, 2 processus, 589 s) : 73 761 images (`data/feuilles*`, `data/roamer_*`, `data/demo_feuilles`, dossiers de `data/raw` ajoutés après le cache du 15/11).
- **0 h 47 (complétée à 0 h 59).** Proposition d'essai Kaggle écrite **avant la mesure de F1** et avant tout entraînement : `out/jeux_neufs_1611/a1_proposition_kaggle.md`.
- **0 h 52 à 0 h 55.** Comparaison (`scripts/a1_fuites.py comparer`).
  - SHA-256 : 0 égalité. Noms : 0. Doublons internes : 0.
  - dHash ≤ 6 : 45 photos ont une paire, mais **aucune n'est confirmée** (vignette ≥ 28 sur 255). Ce sont des coïncidences.
  - Par la règle de 0 h 41, appliquée sans la changer, 24 photos sortent d'A1-test.
- **0 h 57.** Vérification `godliver` par les EXIF : les 98 photos ougandaises datent d'avril à juin 2022 (Samsung SM-A125F), alors que le dépôt `godliver` date de 2014. Pas de fuite par la v10b.

  Les EXIF montrent aussi que 116 des 183 photos d'A1-test partagent un jour de prise avec A1-appr. C'est une limite pour les futurs candidats, pas pour F1.
- **0 h 59.** Rapport `out/jeux_neufs_1611/controle_fuite_a1.md`. Rôles finaux : **A1-test 183** (DRC 129, Uganda 45, Malawi 9), **A1-appr 200** (DRC 150, Uganda 50), 24 retirées.
- **1 h 00.** Copie des 183 photos d'A1-test (`scripts/a1_mesure.py preparer`, SHA-256 vérifiés, liste gelée `a1_test_liste.csv`).
  - Lancement **unique** de `run.py --modules maladies`, configuration installée (F1_bornes), sans `-I`.
  - Limites : masque d'affinité `0xE0` (3 processeurs logiques), `OMP_NUM_THREADS=3`.
  - SHA-256 de `config.yaml`, `maladies.py` et `run.py` notés dans le rapport.
- **1 h 43.** Fin de la chaîne : code 0, module en 2 573 s. Bilan lu une seule fois (`scripts/a1_mesure.py bilan`).
  - **Malades sans alerte : 0 / 183 (0,0 %)**, avec une borne haute à 95 % de 2,0 %.
  - Réponses : fusariose 134, malade non identifiée 41, cercosporiose noire 4, à vérifier 4, saine 0.
  - 121 photos vues « de loin ».
  - Rapport : `out/jeux_neufs_1611/a1_mesure_f1.md`. Aucun réglage, aucune deuxième lecture.
- Rien n'est commité ni téléchargé, aucun entraînement n'est lancé. `fieldscan/`, `run.py`, `config.yaml` et les scripts existants n'ont pas été modifiés. Scripts nouveaux : `scripts/a1_extraire.py`, `a1_decoupage.py`, `a1_fuites.py`, `a1_mesure.py`.

## Essai Kaggle A1 (autorisation transmise par la session principale vers 1 h 45)

- **1 h 48.** Empreinte de la proposition figée : `bcdf8a55…63e7b5`, dans `empreinte_proposition_a1.txt`. La proposition date de 0 h 47, avec une dernière retouche à 0 h 59, donc d'avant la fin de la mesure de F1 (1 h 43).
- **1 h 50.** Avenant `avenant_a1_kaggle.md` écrit avant l'envoi. Empreinte dans `empreinte_avenant_a1_kaggle.txt`. Il fixe :
  - l'étiquette `xanthomonas` → 3, une cible one-hot pour le maître ;
  - A1-appr dans le pli « sans Éthiopie » seulement ;
  - 4 graines, la décision sur leur moyenne et le contrôle Éthiopie ≤ 117 ;
  - l'ordre des lectures ;
  - une limite de 1,5 h de GPU.
- **1 h 45.** `kernels list --mine` : `c16-lot1` en cours (RUNNING). Une seule place GPU est libre pour cet essai.
- **1 h 50.** Jeu préparé (`scripts/a1_kaggle_preparer.py`) : 200 PNG d'A1-appr en 224 px, 20,2 Mo. Contrôle SHA-256 : 0 photo d'A1-test ni des 24 retirées.
- **1 h 51.** Carnet `notebooks/a1_entrainer_kaggle.py`, copie de m13 avec les seuls changements de l'avenant. Contrôles d'envoi passés en mode `--essai` (`scripts/a1_kaggle_pousser.py`).
- **1 h 51.** **Création du jeu Kaggle refusée par le système de permissions** de Claude Code (« communication non autorisée »).
  - L'autorisation de la nuit est venue de la session principale, pas de Corentin dans cette session.
  - Pas de contournement : rien n'est parti, rien n'a été envoyé, 0 h de GPU.
- **1 h 52.** Banc `scripts/a1_kaggle_banc.py controle` (2 fils) : F1 33,94 et d3b 32,77 retrouvés. Le banc est prêt.
- **1 h 53.** `out/jeux_neufs_1611/a1_kaggle_finalistes.md` : aucun finaliste, essai non lancé. Les commandes pour lancer sur accord direct de Corentin y sont notées.
- **Vers 2 h 10.** Corentin a donné son accord direct (« Envoie l'essai »), transmis par la session principale. Celle-ci a créé le jeu et envoyé `a1-lot1`.
- **3 h 01.** Avenant et proposition vérifiés identiques à leurs empreintes. `a1-lot1` est COMPLETE : 2 891 s, soit **0,80 h de GPU** (T4 × 2), 4 graines sans échec, `plantvillage_psu` (200, classe 3) bien appris.
- **3 h 03.** `a1_kaggle_banc.py recuperer` : 40 fichiers de prédictions et 8 réseaux, dans `modeles/maladies_a1_1611/lot1/`.
- **3 h 05.** `a1_kaggle_banc.py mesurer`, lu une seule fois, à 2 fils. Contrôles F1 33,94 et d3b 32,77 retrouvés.
  - Coûts de réglage : a1g0 34,28, a1g1 35,84, a1g2 34,92, a1g3 35,45, **moyenne 35,12**.
  - Éthiopie, malades sans alerte : 155, 162, 161, 171, moyenne 162,3 (limite 117).
  - **Aucun finaliste** : échec sur le coût, sur l'Éthiopie (+ 4,0 points) et sur le contrôle propre. Juges et A1-test non lus.
  - Pour information, la même recette sans A1 donnait 33,95 en moyenne (Éthiopie 150,5).
- **3 h 07.** `out/jeux_neufs_1611/a1_kaggle_finalistes.md` écrit. Aucun commit. `fieldscan/` et `config.yaml` n'ont pas été modifiés.
