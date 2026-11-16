# Avenant c16 : aiguillage du comptage par résolution d'origine (16/11, vers 0 h 40)

Accord de Corentin : « Oui, lance-le » (16/11), pour un essai de comptage sur Kaggle, **3 h de GPU au plus**, compte `affilecorentin`. Cet avenant est écrit **avant toute mesure et tout lancement** de l'essai c16. Son empreinte SHA-256 est dans `empreinte_avenant_c16.txt`. Aucun commit n'est fait : l'empreinte tient lieu de date.

## 0. Ce qui reste valable
- `docs/plan_nuit_2026-11-13.md`, section 5.3 : grille des seuils (0,10 à 0,60, pas 0,05), appariement, rayon et mesure du protocole v5 (pics fenêtre 7, appariement un à un dans 20 px, non-mères ignorées, disque DJI, zones MM). Code du banc importé sans modification : `scripts/v6_banc_commun.py`, `scripts/c13_banc_commun.py` (garde-fou des juges), `scripts/v6_banc_candidats.py`.
- Avenant du second tour (15/11) : rien ne part de v6f ni de c13h pour les réseaux neufs.
- Avenant des jeux neufs (15/11), section A2 : le Ghana est un jeu de **réglage**, jamais d'apprentissage.
- Aucun juge n'est lu, aucun test (section 6).

## 1. L'aiguillage
- La **résolution d'origine** d'une orthomosaïque est la taille du pixel au sol lue dans le GeoTIFF **avant** la remise à 5 cm/px (moyenne des deux axes, en cm/px).
- **Seuil d'aiguillage R = 7,5 cm/px**, fixé ici :
  - résolution d'origine ≤ 7,5 cm/px : **v5 tel quel**, au seuil 0,30 ;
  - résolution d'origine > 7,5 cm/px : **le spécialiste**, à son seuil (section 3).
- À 5 cm, l'aiguillage rend donc le v5 à l'identique : **aucune régression à 5 cm par construction**, rien n'est mesuré à 5 cm pour le spécialiste.
- Le spécialiste n'a pas à être bon à 5 cm. Il doit être bon de 8 à 14 cm/px **sans perdre l'agroforesterie** à ces résolutions.

## 2. Candidats « spécialiste » (liste fermée, 10 au plus)

### 2.1 Réseaux existants (mesurés en local, sans Kaggle)
`c13a`, `c15d`, `c15b_a`, `c15b_b`, `c15b_c`, `c15b_d`, avec leurs ONNX actuels (`modeles/comptage_nuit_1311/centres_5cm_c13a.onnx`, `modeles/comptage_jour_1511/centres_5cm_<nom>.onnx`). Leur seuil 5.3 d'hier ne sert pas : chacun reçoit un seuil par la règle de la section 3.

### 2.2 Réseaux neufs (Kaggle, un seul lot `c16-lot1`, 4 recettes)
Commun aux 4 :
- départ **v5** (`centres_5cm_v5.onnx` du jeu privé `comptage-v6-maitres`, converti, BN figées), ResNet-18 ;
- **distillation du v5 sur la vue nette** (`distil_net`) : sur chaque tuile, dégradée ou non, l'élève apprend la carte que le v5 donne sur la même fenêtre nette à 5 cm. C'est ce qui doit garder le comportement du v5 en agroforesterie ;
- tirage `parts_v5` avec btd_train 15 % (`avec_espace`), comme c15b_a, b, d : c'est ce qui a tenu btd_val et le seuil ;
- **dégradation systématique** : `degr_p` 1,0, `degr_cm` 7 à 15 cm/px (au lieu de 0,5 et 5-12), JPEG p 0,5 (qualité 60-95), échelle 0,6-1,6 ;
- 8 époques, lot 16, EMA 0,999, graine 0, **poids EMA de la dernière époque faite** (aucun choix d'époque) ; garde-fou `duree_max_h` 1,0 par recette ;
- nouvelle option `part_rt` (part des tuiles ReforesTree d'entraînement dans l'époque ; 0,20 = parts du v5), ajoutée dans une copie `notebooks/c16_travail_centres.py` de `notebooks/c15b_travail_centres.py`, sans effet si absente.

| essai | nom | `part_rt` | `lambda_distil` | `distil_rt` | taux squelette / décodeur |
| --- | --- | --- | --- | --- | --- |
| 7 | `c16_a` | 0,20 | 10 | 3 | 3e-5 / 1e-4 |
| 8 | `c16_b` | **0,40** (ReforesTree surpondéré) | 10 | 3 | 3e-5 / 1e-4 |
| 9 | `c16_c` | 0,40 | **30** | 3 | 3e-5 / 1e-4 |
| 10 | `c16_d` | 0,40 | 30 | 3 | **1e-5 / 3e-5** |

Kaggle :
- avant l'envoi, `kernels list --mine` et `kernels status` : aucun carnet en file ni en cours ;
- un seul carnet `c16-lot1`, T4 × 2 (2 GPU au plus), 2 recettes par GPU ; entrées : `comptage-v6-5cm`, `comptage-v6-maitres` (jeux privés déjà sur Kaggle) ; aucune image de juge (le travail retire `test_*` et `cg/` par `assert`) ;
- si l'envoi est refusé faute de place, nouvel essai toutes les 3 minutes pendant 45 minutes au plus ; s'il reste en file plus de 45 minutes après acceptation, il est abandonné et noté ;
- **pas de second lot.** GPU attendu : environ 1,3 h, sous la limite de 3 h ;
- les chiffres du carnet sont de l'information ; l'ONNX récupéré et mesuré en local fait foi.

## 3. Mesures (toutes sur le réglage, en local, onnxruntime, 3 fils au plus, un calcul à la fois)
**Dégradation** : la fonction `degrader` de `scripts/c13_entr_mesure.py` (identique à `scripts/v6_analyse_degradation.py`) : 5 cm → c cm (LANCZOS) → taille d'origine (LANCZOS) → JPEG qualité 95. Annotations inchangées.

- **M1. Réglage dégradé** à **8, 11 et 14 cm/px** : les 5 jeux (dense, plantain, jeunes, MM, btd_val), F1 par jeu sur toute la grille, moyenne des 5, erreur de compte.
- **M2. `val_negatifs` dégradé** à 8, 11 et 14 cm/px (toutes les tuiles) : fausses détections par arbre, sur toute la grille.
- **M3. Contrôle agroforesterie à basse résolution** : les tuiles `rt_*` de `data/drone/comptage_v5_5cm` dont `partie` = `ensemble` = « train » et `facteur` = 1 (`assert`, comme `notebooks/c15b_controle_rt.py`), dégradées à 8, 11 et 14 cm/px. Appariement un à un (hongrois), 20 px au plus.
  - (a) **rappel des mères annotées** du candidat (à son seuil), comparé au rappel du v5 (0,30) **à la même résolution** ;
  - (b) **part des pieds du v5 à 5 cm** (tuile nette, seuil 0,30) retrouvés par le candidat dégradé, comparée à la même part pour le v5 dégradé (0,30). C'est le contrôle qui a séparé c15d hier (86,6 %).
  - Non-régression sur des données vues (tuiles d'entraînement de tous les réseaux) : ce n'est pas une mesure de performance.
- **M4. Ghana (A2)** : les 199 photos réduites au facteur fixé **0,4** (Lanczos, `out/jeux_neufs_1511/a2_echelle.json`), puis dégradées à **11 cm/px** par la même fonction `degrader`. Mesure de `scripts/jeux_neufs_a2_mesure_v5.py` à l'identique (centre de boîte = pied, appariement 20 px, photo entière, F1 du total des 199 photos). Candidat à son seuil, v5 dégradé à 0,30. Pour économiser le processeur, M4 n'est fait que pour le v5 et pour les candidats qui ont rempli toutes les autres conditions (section 4) ; un candidat non mesuré sur M4 n'est pas finaliste.

**Référence** : le v5 au seuil 0,30, mesuré par le même code à chaque résolution (« v5 dégradé »). Contrôle du banc : à 11 cm, il doit redonner la moyenne 0,6005 (dense 0,622, MM 0,724, btd 0,014 ; journaux du 13/11 et du 15/11).

**Ordre de mesure**, fixe : v5, c13a, c15d, c15b_a, c15b_b, c15b_c, c15b_d, puis c16_a, c16_b, c16_c, c16_d. Il ne change pas selon les chiffres.

## 4. Règles

### 4.1 Seuil du spécialiste
Le seuil qui **maximise la moyenne des 5 F1 du réglage dégradé à 11 cm**, sur la grille 0,10-0,60, parmi les seuils où les fausses détections sur `val_negatifs` dégradé restent **sous 1 % à 8, à 11 et à 14 cm**. Égalité : le plus bas. Aucun seuil éligible : pas finaliste.

### 4.2 Finaliste (toutes les conditions, au seuil de 4.1)
1. **Gain** : moyenne des 5 F1 à 11 cm ≥ v5 dégradé à 11 cm + 0,030 (soit ≥ 0,6305 si le v5 redonne 0,6005).
2. **Aucune perte par jeu** : à 8, 11 et 14 cm, chaque jeu ≥ v5 à la même résolution − 0,020 ; et la moyenne des 5 à 8 cm et à 14 cm ≥ celle du v5 à la même résolution.
3. **`val_negatifs` dégradé** < 1 % à 8, 11 et 14 cm (garanti par 4.1).
4. **Agroforesterie à 11 cm (M3)** :
   - (a) rappel des mères annotées du candidat ≥ celui du v5 à 11 cm − 0,010 ;
   - (b) part des pieds du v5 à 5 cm retrouvés par le candidat à 11 cm ≥ celle du v5 à 11 cm − 0,010.
   À 8 et 14 cm, M3 est donné pour information.
5. **Ghana dégradé à 11 cm (M4)** : F1 du candidat ≥ F1 du v5 dégradé − 0,020, comme le prévoit l'avenant des jeux neufs. Le Ghana n'a été mesuré pour aucun de ces candidats avant cet avenant.

**Classement** des finalistes : moyenne des 5 F1 à 11 cm, la plus haute d'abord. Famille : B (réseau seul) dans l'aiguillage avec le v5.

### 4.3 Écriture
`out/comptage/jour_1611/finalistes.md` applique la règle telle quelle, sans rien changer après coup : tableau de tous les candidats (seuil, F1 à 8, 11 et 14 cm par jeu, `val_negatifs`, M3, Ghana), conditions remplies ou non. **Si aucun candidat ne passe, le rapport le dit : « aucun finaliste ».**

## 5. Ce qui n'est pas décidé ici
- Le finaliste classé premier est **proposé** à Corentin, pas adopté.
- L'intégration (`fieldscan/modules/comptage.py`, `config.yaml`) est seulement décrite dans une note ; elle demande l'accord de Corentin.

## 6. Juges et test
Aucun juge n'est lu : ni segmento est, ni CG, ni `banano_dense`, ni `test_negatifs`, ni `banana_trees_kp`. La lecture des juges ou du test pour le finaliste sera une décision à part, à demander à Corentin.

## 7. Cadre
- Écrit seulement dans `notebooks/c16_*.py`, `scripts/c16_*.py`, `out/comptage/jour_1611/`, `modeles/comptage_jour_1611/`, `docs/journee_2026-11-16/` et un dossier temporaire hors dépôt (`C:/Users/coren/kaggle_tmp/c16/`).
- Aucun fichier existant modifié (copies sous un nouveau nom), aucun commit, aucun téléchargement hors des sorties de mon propre carnet Kaggle. Jeton Kaggle jamais lu ni affiché.
- Machine partagée : 3 fils au plus, pas de lecture ni d'écriture dans `out/visite_basse_pointe_zone/` et `out/demo_martinique_rpg/`.
