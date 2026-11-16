# Avenant c16 (2) : une lecture des juges dégradés pour le finaliste c16_a (16/11, vers 9 h)

Corentin a répondu « Lance le » ce matin (message transmis par la session principale) : écrire une règle, puis lire **une fois** les juges dégradés pour le finaliste `c16_a`, en vue d'une éventuelle adoption de l'aiguillage v5 / c16_a. Cet avenant est écrit **avant toute lecture d'un juge**. Son empreinte SHA-256 est dans `empreinte_avenant_c16_juges.txt`. Aucun commit.

## 1. Ce qui est lu
- **Juges** (`data/drone/comptage_v5_5cm`, chargés par `bc.jeu` de `scripts/v6_banc_commun.py`, comme les juges des 14 et 15/11) :
  - segmento est (`test_dense`, 39 images) ;
  - CG1-CG9, mères seules (zones de `cg/`) ;
  - `banano_dense` (`test_banano`, 71 tuiles) ;
  - `test_negatifs` (1 667 tuiles).
- Ces juges ont déjà été lus à 5 cm/px les 12, 13, 14 et 15/11 (juges **relus**). Ils n'ont **jamais** été lus dégradés. Le rapport le dira.
- **`banana_trees_kp` n'est pas lu** : c'est une décision à part. Aucun autre finaliste n'est lu. Il n'y a pas de seconde lecture.

## 2. Dégradation
- La fonction `degrader` de `scripts/c13_entr_mesure.py` (5 cm → c cm LANCZOS → taille d'origine LANCZOS → JPEG 95), appliquée à chaque image entière. Annotations, zones CG et disques DJI inchangés.
- **11 cm/px** : c'est la lecture qui décide.
- 8 et 14 cm/px : **information seulement**, calculés après la lecture à 11 cm. Ils ne décident de rien et ne peuvent rien rattraper.

## 3. Candidat et référence
- **Candidat** : `c16_a` (`modeles/comptage_jour_1611/centres_5cm_c16_a.onnx`, SHA-256 `544dd09b…64522`, vérifié avant la lecture) au **seuil 0,35** (règle 4.1 de l'avenant c16), sans rien changer.
- **Référence** : le v5 (`modeles/centres_5cm_v5.onnx`, SHA-256 `12f9b4ca…2f1ea`) **dégradé, au seuil 0,30**, lu sur les mêmes images dégradées.
- Mesure du protocole v5, inchangée : pics fenêtre 7 (`bc.pics`), appariement un à un dans 20 px, non-mères ignorées, disque DJI, zones CG (`bc.mesurer_jeu`). Erreur de compte d'un juge : |détectés / annotés − 1|.

## 4. Conditions d'adoption proposée (toutes, à 11 cm)
- (a) moyenne des F1 de segmento est, CG et `banano_dense` ≥ v5 dégradé + 0,030 ;
- (b) F1 de CG ≥ v5 dégradé − 0,020 (ne pas perdre l'agroforesterie) ;
- (c) erreur de compte moyenne (moyenne simple des trois erreurs de compte de segmento est, CG et `banano_dense`) ≤ celle du v5 dégradé ;
- (d) `test_negatifs` dégradé : fausses détections / arbres < 1 %.

Si les quatre conditions sont remplies : **« adoption proposée à Corentin »**. Sinon : **« non adopté »**. Les conditions sont celles transmises, sans les durcir ni les assouplir ; elles ne changent pas après la lecture.

## 5. Garde-fous de la lecture
- Juste avant de lire : vérifier que l'empreinte de cet avenant correspond, que le garde-fou de `scripts/c13_banc_commun.py` refuse bien les juges (`cc.jeu("segmento")` lève une erreur, ce qui prouve que la mesure c16 n'a jamais pu les lire), et les SHA-256 des deux ONNX.
- Script neuf `scripts/c16_juges.py` : il refuse d'écrire une sortie qui existe déjà (une seule lecture par juge et par résolution) et vérifie que la somme des comptes par image égale la mesure.
- 6 fils au plus (les autres agents ont fini). Images dégradées des juges : cache hors dépôt `C:/Users/coren/kaggle_tmp/c16/juges/`, supprimable.
- Sortie : `out/comptage/jour_1611/juges_c16_a.md` (un tableau par juge et par résolution : v5 contre c16_a, F1, rappel, précision, erreur de compte ; puis la décision).
