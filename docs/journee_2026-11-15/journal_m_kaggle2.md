# Journal de M-kaggle2 (maladies, second tour Kaggle), 15/11/2026

Cadre : `docs/journee_2026-11-15/avenant_tour2_kaggle.md` (16 h 05) et `docs/plan_journee_2026-11-15.md`. Règle de finaliste : `docs/plan_nuit_2026-11-13.md`, section 4.3, sans changement ; référence F1 (coût de réglage 33,94), temps comparé à F1_bornes. Aucun juge relu (BanSpot, Cordana du Pérou) ni aucun test n'est lu ; aucune de leurs images n'est envoyée sur Kaggle. Processeur local : 2 fils au plus. Aucun commit, aucun téléchargement local (seules les sorties de mes propres carnets Kaggle sont rapatriées, comme au premier tour). Écriture seulement dans `notebooks/m15b_*.py`, `out/maladies/jour_1511/kaggle2/`, `modeles/maladies_jour_1511/` et ce journal.

Compte des essais : une règle (une configuration) mesurée sur le réglage = un essai. Les contrôles (F1 = 33,94) ne sont pas comptés.

## 16 h 05 : lecture et état des lieux (avant tout calcul)

- Lus : `CLAUDE.md`, l'avenant du second tour, le plan du 15/11, la section 4.3 du plan du 13/11, `journal_m_kaggle.md` (règles kNN de 14 h 15), `journal_m_banc.md`, `recap.md`, la fiche M1 de `docs/veille_2026-11-14/synthese.md`, `notebooks/m15_traits_kaggle.py`, `m15_knn.py`, `m15_mesurer.py`, `m15_pousser.py`, `m15_recuperer.py`.
- `affilecorentin/m15-traits` : **toujours QUEUED** à 16 h 04 (envoyé à 14 h 13, soit 1 h 51 en file). Aucun autre carnet du compte n'est en cours (c15-lot1, m15-soupe : COMPLETE). Je le considère bloqué ; je ne le supprime pas.
- GPU consommé par M-kaggle2 : 0 h. Essais : 0.

## 16 h 07 : décision (avant calcul) : renvoyer le même carnet sous `m15b-traits`

- Même code que `notebooks/m15_traits_kaggle.py` (contrôlé par SHA-256 dans `notebooks/m15b_pousser.py`), mêmes jeux, mêmes sorties, T4 × 2.
- **Repli sans GPU** : si `m15b-traits` est encore en file à **16 h 30**, j'envoie le même code sous `m15c-traits` sur processeur Kaggle (`enable_gpu: false` ; le carnet tourne aussi sans GPU : environ 32 000 photos à 224 px, estimé 30 à 60 min). Il ne consomme pas de GPU. Le premier des deux qui finit est utilisé ; l'autre est abandonné et noté.
- Règle d'arrêt (consigne) : un carnet en file plus de 45 min est abandonné et noté.

## 16 h 06 : `m15b-traits` envoyé ; RUNNING dès 16 h 08

- `notebooks/m15b_pousser.py gpu` : contrôles OK (code identique à l'envoi du premier tour, SHA-256 544b8831b0ed…), T4 × 2. Statut RUNNING à 16 h 08 : la file s'est libérée. Le repli processeur (`m15c-traits`) n'est pas envoyé.
- `m15-traits` (premier tour) reste en file, non supprimé ; s'il démarre, ses sorties ne seront pas utilisées.

## 16 h 09 : règles de mesure, écrites avant de voir les traits

### Piste 1 : lecteur kNN (règles de 14 h 15 de M-kaggle, avec une précision)

- Inchangé : traits des soupes s4, 224 px, 1 vue, normalisés L2 ; P_kNN = vote équilibré des k voisins (cosinus) ; k ∈ {5, 10, 20} choisi sur l'AUROC moyenne validation + TDTU (égalité à 0,002 : le plus grand k) ; KD1(s), s ∈ {0,50 ; 0,70 ; 0,90} ; KD2(q), q ∈ {0,05 ; 0,10 ; 0,20} ; KD3 = meilleur KD1 + meilleur KD2 ; lecture « ensemble livrable » (TDTU et Éthiopie par le pli qui ne les a pas vus, les autres jeux par la moyenne des 2 plis) ; famille C ; temps composé F1_bornes + 0,085 × d3b, estimé (10,55 s, 1,03 × F1_bornes).
- **Précision (consigne du second tour, fiche M1 de la veille) : les voisins sont cherchés seulement dans les autres pays.** La mémoire du pli sans x (sans x, sans PSFD) perd en plus le pays de la requête :
  - validation (Tanzanie 2022-2023) : sans `tanzanie_2021` ;
  - AgroVisionBD (Bangladesh) : sans `mendeley_bd`, `mendeley_5nfjzntwd8_bangladesh`, `mendeley_6yy9522rdy_bangladesh` ;
  - TDTU, Éthiopie, PSFD : déjà exclus par le pli ou par la règle de 14 h 15 ;
  - roamer : aucun pays commun en mémoire.
  Le code de 14 h 15 (`m15_knn.py`) gardait la Tanzanie 2021 pour la validation et le Bangladesh pour AgroVisionBD : il n'est pas lancé. Mon code : `notebooks/m15b_knn.py`. Une seule définition est mesurée (pas de variante « même pays »).
- Contrôle : F1 recalculé = 33,94 (sinon arrêt).
- Essais : 3 (k) + 7 (KD) = 10 au plus.

### Piste 2 : choix et règle (écrits avant tout calcul de la piste 2)

**Constat [O]** : le Xanthomonas n'existe que dans le jeu éthiopien (814 photos ; `nuit.csv`, `index.csv`, `liste_entrainement.csv` : aucune autre source n'en contient). En validation croisée par pays, aucun réseau ni aucune tête ne peut donc l'apprendre. Les morceaux en entraînement ont déjà été essayés (ME2 e1 : coût 36,81) et le tirage par source fait partie de la recette de d3b. **Je ne lance donc pas de nouvel entraînement Kaggle** : il ne viserait pas la cause connue et coûterait du GPU sans hypothèse nouvelle.

**Choix : tête apprise sur les traits de la piste 1 (KT), validation croisée par pays**, sur processeur local (2 fils), aucun GPU de plus.
- Tête : régression logistique binaire (malade / saine) sur les 768 traits, avec biais ; poids équilibrés (chaque classe pèse la moitié) ; pénalité L2 = 1e-4 × ‖w‖² ; L-BFGS de torch, 200 itérations, float32. **Aucun réglage** : ces valeurs sont fixées ici.
- Apprise sur **exactement la même mémoire que le kNN** de la requête (autres pays seulement, pli correspondant) ; P_tête = moyenne des 2 plis pour validation, PSFD, AgroVisionBD, roamer.
- Règles identiques à la piste 1, avec P_tête à la place de P_kNN : KT1(s), s ∈ {0,50 ; 0,70 ; 0,90} ; KT2(q), q ∈ {0,05 ; 0,10 ; 0,20} ; KT3 = meilleur KT1 + meilleur KT2. 7 essais. Famille C. Temps : celui de KD (même lecture de traits ; la tête est négligeable).
- Pour information seulement (pas un essai, aucun choix) : AUROC de P_tête par jeu.

### Choix entre finalistes et plafond

- Finaliste : règle 4.3 telle quelle (coût ≤ 32,94 ; Tanzanie ≤ 14 et ≤ 77 ; aucun jeu ne perd plus de 2 points de malades sans alerte ; roamer ≤ 229 ; temps ≤ 1,2 × F1_bornes = 12,24 s), ou « variante rapide ».
- Entre finalistes : coût de réglage le plus bas ; tous les finalistes sont écrits dans `finalistes.md` avec leur famille.
- Plafond : **17 essais** (10 + 7). Rien d'autre sans l'écrire ici avant.

## 16 h 18 : `m15b-traits` fini ; traits rapatriés

- COMPLETE à 16 h 17 (RUNNING dès 16 h 08) : 10,4 min de session T4 × 2 (log : 9,9 min de calcul) → **≈ 0,17 h de GPU**.
- `notebooks/m15b_recuperer.py` : sorties dans `out/maladies/jour_1511/kaggle2/lot_traits/` ; contrôles (`controle_traits.json`) : 21 715 images en mémoire, 7 746 + 2 985 requêtes, traits de norme 1 (± 2e-4), aucun nom de juge dans les chemins.
- Constat [O] : PSFD n'est dans la mémoire d'aucun pli (le carnet l'exclut de l'apprentissage). Mon assertion « psfd présent » était fausse : remplacée par « psfd absent ». Aucune règle changée.

## 16 h 19 : piste 1 (KD) et piste 2 (KT) : 17 essais, **aucun finaliste** [M]

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/m15b_knn.py` ; journal `out/maladies/jour_1511/kaggle2/knn.log`, bilan `bilan_knn.json`, tableau `tableau_essais.md`, P_kNN et P_tête `p_knn_tete.npz`.

- **Contrôle** : F1 = **33,94** retrouvé (validation 0 ; 62 | TDTU 19 ; 241 | PSFD 102 | Éthiopie 117 ; 28 | AgroVisionBD 5 ; 87 ; 243 ratées ; roamer 227).
- Mémoires « autres pays » : validation 4 384 et 4 731 images (sans Tanzanie 2021) ; TDTU 20 079 ; Éthiopie 20 426 ; AgroVisionBD 18 252 et 18 599 (sans Bangladesh).
- **Choix de k** (3 essais) : AUROC moyenne validation + TDTU : k = 5 : 0,923 ; k = 10 : 0,930 ; **k = 20 : 0,938 → k = 20**. Pour information : Éthiopie 0,920, AgroVisionBD 0,974, roamer 0,589. Tête (information) : validation 0,997, TDTU 0,928, Éthiopie 0,922, AgroVisionBD 0,978, roamer 0,599.

| Essai | Coût | Val. | TDTU | PSFD | Éth. | AgroVisionBD | Ratées 5 jeux | roamer | Perdues / rattrapées | Échoue sur |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | 33,94 | 0 ; 62 | 19 ; 241 | 102 | 117 ; 28 | 5 ; 87 | 243 | 227 | — | — |
| KD1 s = 0,50 | 34,87 | 0 ; 73 | 14 ; 263 | 99 | 116 ; 30 | 5 ; 92 | 234 | 225 | 0 / 9 | coût |
| KD1 s = 0,70 | 34,29 | 0 ; 67 | 16 ; 247 | 101 | 117 ; 29 | 5 ; 90 | 239 | 227 | 0 / 4 | coût |
| KD1 s = 0,90 | 34,07 | 0 ; 62 | 18 ; 241 | 102 | 117 ; 29 | 5 ; 88 | 242 | 227 | 0 / 1 | coût |
| KD2 q = 0,05 | 33,94 | = F1 | | | | | 243 | 243 | 0 / 0 | coût, roamer |
| KD2 q = 0,10 | 33,90 | 0 ; 62 | 19 ; 240 | 102 | 117 ; 28 | 5 ; 87 | 243 | 247 | 0 / 0 | coût, roamer |
| KD2 q = 0,20 | 33,91 | 0 ; 62 | 20 ; 240 | 103 | 119 ; 27 | 5 ; 85 | 247 | 259 | 4 / 0 | coût, roamer |
| KD3 (KD1 0,90 + KD2 0,10) | 34,03 | 0 ; 62 | 18 ; 240 | 102 | 117 ; 29 | 5 ; 88 | 242 | 247 | 0 / 1 | coût, roamer |
| KT1 s = 0,50 | 34,50 | 0 ; 72 | 18 ; 247 | 101 | 116 ; 29 | 5 ; 91 | 240 | 226 | 0 / 3 | coût |
| KT1 s = 0,70 | 34,32 | 0 ; 64 | 19 ; 244 | 102 | 117 ; 29 | 5 ; 89 | 243 | 227 | 0 / 0 | coût |
| KT1 s = 0,90 | 33,94 | = F1 | | | | | 243 | 227 | 0 / 0 | coût |
| KT2 q = 0,05 | 33,94 | = F1 | | | | | 243 | 238 | 0 / 0 | coût, roamer |
| KT2 q = 0,10 | 33,91 | 1 ; 62 | 19 ; 241 | 102 | 118 ; 28 | 5 ; 85 | 245 | 247 | 2 / 0 | coût, roamer |
| KT2 q = 0,20 | 34,60 | 1 ; 62 | 21 ; 239 | 113 | 123 ; 27 | 5 ; 78 | 263 | 268 | 20 / 0 | coût, roamer |
| KT3 (KT1 0,90 + KT2 0,10) | 33,91 | = KT2 q = 0,10 | | | | | 245 | 247 | 2 / 0 | coût, roamer |

Lecture :
- **Le lecteur kNN dans l'encodeur affiné n'apporte presque rien de neuf à F1.** Rattraper (KD1, KT1) : chaque malade rattrapée coûte 5 à 10 saines en alerte (TDTU surtout). Retirer des « à vérifier » loin (KD2, KT2) : quelques saines d'AgroVisionBD en moins, mais 11 à 41 malades de roamer ratées en plus (AUROC 0,59 sur roamer : les traits de feuille ne lisent pas les plantes vues de loin).
- Rien ne s'approche de F1 − 1 : le meilleur coût est 33,90 (KD2 q = 0,10), qui échoue sur roamer (247 > 229).
- Le Xanthomonas d'Éthiopie reste raté (116 à 123) : attendu, aucun voisin ni aucune tête n'en a vu (constat de 16 h 09).

Essais cumulés : **17** (plafond atteint pour les pistes 1 et 2).

## 16 h 22 : piste 3, écrite avant tout calcul : adaptation au pays pendant la lecture (idée M3 de la veille, jamais mesurée)

**Pourquoi.** Les pistes 1 et 2 confirment que le défaut est un **changement de domaine** (pays, appareil) : TDTU (241 saines en alerte sur 577), Éthiopie, roamer. La fiche M3 de la veille propose l'adaptation au test sans étiquette. Le ConvNeXt n'a pas de normalisation par lot : la forme prévue par M3 est **un pas de minimisation d'entropie sur les seuls paramètres affines des normalisations** (TENT, Wang et al., ICLR 2021). Aucune étiquette n'est lue. Budget : 1 carnet Kaggle (`m15b-tent`, T4 × 2), estimé à 0,3 h ; GPU cumulé prévu ≈ 0,5 h sur 3 h.

**Réseau** : les soupes s4 (une par pli, sorties de `m15-soupe` : aucune graine choisie), lues comme au premier tour (384 px, 4 vues, moyenne des softmax) ; lecture « ensemble livrable » : TDTU et Éthiopie par le pli qui ne les a pas appris, validation, PSFD, AgroVisionBD et roamer par chacun des 2 plis.

**Adaptation (fixée ici, aucun réglage)** :
- paramètres adaptés : poids et biais de toutes les couches de normalisation (LayerNorm) ; tout le reste figé ;
- perte : entropie moyenne du softmax à 4 classes, une vue (la photo telle quelle), 384 px ;
- SGD, pas 1e-3, moment 0,9 ; lots de 32 photos d'un **même jeu**, ordre tiré au hasard (graine 2026) ;
- **en ligne** : pour chaque lot, un pas d'adaptation, puis lecture de ce lot (4 vues) par le réseau adapté ; une photo n'est donc lue qu'avec ce qui a été vu avant elle et son propre lot ;
- **remise à zéro** aux poids d'origine toutes les 20 lots (640 photos, la taille d'un champ envoyé par le robot) ;
- si la mémoire du GPU ne suffit pas pour 32, lots de 16 (noté).

**Essais (2)**, seuils inchangés de d3b (0,50 proche, 0,70 loin) :
- **T1 `s4-tent`** : chaîne élève de d3b (`m14_banc.chaine_eleve`), réseaux = s4 adaptés. Famille B. Comparé à J3 `d3-soupe4` (34,31, sans adaptation).
- **T2 `MC1-OU-proche (s4-tent)`** : règle MC1-OU-proche, élève = s4 adaptés. Famille C. Comparé à J4 (33,41).

**Temps (estimation composée, dite comme telle)** : d3b = 2 réseaux × 4 vues = 4,1 s ; l'adaptation ajoute par réseau 1 lecture + 1 passe arrière ≈ 3 lectures d'une vue, soit + 6 / 8 × 4,1 = + 3,1 s par photo.
- T1 : 4,1 + 3,1 = 7,2 s (0,71 × F1_bornes).
- T2 : l'adaptation doit voir le flux entier (elle est mesurée ainsi) : 10,2 + 3,1 + 0,224 × 4,1 = 14,2 s = 1,39 × F1_bornes → **T2 échouera sur le temps** quoi qu'il arrive ; il est mesuré pour savoir si l'adaptation aide (information pour la suite), et dit comme tel.

**Garde-fou (information, pas un essai, aucun choix)** : la fiche M3 signale le risque d'un lot **déséquilibré**. Le carnet lit aussi, avec les s4 adaptés, un flux de validation à 90 % de saines (les 1 000 saines + 111 malades tirées avec la graine 2026, mélangées) ; je compare les malades ratées par la chaîne élève avec et sans adaptation sur ces 111.

**Règle** : 4.3 telle quelle, temps contre F1_bornes. Plafond porté à **19 essais** (17 + 2). Arrêt : si `m15b-tent` n'a pas rendu ses sorties à **19 h 30**, la piste est abandonnée ; s'il reste en file plus de 45 min, il est abandonné et noté.

## 16 h 23 : `m15b-tent` envoyé (RUNNING aussitôt)

- `notebooks/m15b_tent_kaggle.py` : données et contrôles anti-juges copiés de `m15_soupe_kaggle.py` (aucune image d'apprentissage chargée), puis l'adaptation de 16 h 22. Contrôle ajouté : s4 relu sans adaptation sur la validation (pli sans TDTU), à comparer aux probabilités de `m15-soupe`. Boucle testée sur processeur avec un réseau au hasard (forme et sommes des probabilités).
- Envoi : `notebooks/m15b_pousser.py tent` (dossier = carnet + métadonnées ; refus des juges présents ; contrôle de fuite OK), SHA-256 6cf3b7520c86…, T4 × 2, sources : jeux du premier tour + sorties de `m15-soupe`.
- Mesure prête : `notebooks/m15b_mesurer_tent.py` (contrôles F1 = 33,94, J3 = 34,31, J4 = 33,41 avant T1, T2).

## 16 h 32 : `m15b-tent` fini ; essais T1, T2 : **aucun finaliste** [M]

- Carnet : RUNNING dès 16 h 23, COMPLETE avant 16 h 32 ; 8,7 min de session (8,2 min de calcul), lots de 32 (la mémoire a suffi), 46 paramètres adaptés par réseau → **≈ 0,15 h de GPU**.
- Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/m15b_mesurer_tent.py` ; journal `out/maladies/jour_1511/kaggle2/tent.log`, bilan `bilan_tent.json`, sorties `lot_tent/`.
- Contrôles : s4 relu sans adaptation = probabilités de `m15-soupe` à 0,0005 près ; F1 = **33,94**, J3 = 34,31, J4 = 33,41 retrouvés.

| Essai | Famille | Coût | Val. | TDTU | PSFD | Éth. | AgroVisionBD | Ratées 5 jeux | roamer | Perdues / rattrapées | Temps / F1_bornes | Échoue sur |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | réf. | 33,94 | 0 ; 62 | 19 ; 241 | 102 | 117 ; 28 | 5 ; 87 | 243 | 227 | — | 1,00 | — |
| J3 `d3-soupe4` (rappel) | B | 34,31 | 6 ; 41 | 36 ; 206 | 102 | 158 ; 25 | 11 ; 61 | 313 | 214 | | 0,40 | |
| **T1 `s4-tent`** | B | **80,25** | 9 ; 26 | 357 ; 110 | 206 | 636 ; 6 | 24 ; 41 | 1 232 | 455 | 999 / 10 | 0,70 (est.) | coût, pays, roamer |
| J4 MC1-OU-proche (s4) (rappel) | C | 33,41 | 0 ; 66 | 19 ; 246 | 94 | 111 ; 29 | 5 ; 88 | 229 | 225 | | 1,09 | |
| **T2 MC1-OU-proche (s4-tent)** | C | **33,69** | 0 ; 63 | 19 ; 241 | 98 | 117 ; 28 | 5 ; 88 | 239 | 227 | 0 / 4 | 1,39 (est.) | coût, temps |

- **Garde-fou (information)**, flux de validation à 90 % de saines, chaîne élève : sans adaptation 0 / 111 malades sans alerte et 41 / 1 000 saines en alerte ; adapté : **13 / 111** et 9 / 1 000.
- Lecture : **l'adaptation par entropie s'effondre vers « saine »**. Elle rend le réseau plus sûr de ce qu'il croit déjà : là où il hésite entre « saine » et « malade » (Xanthomonas d'Éthiopie, TDTU, PSFD, roamer), elle tranche pour « saine ». Éthiopie : 158 → 636 malades ratées ; flux à 90 % de saines : 0 → 13 ratées. C'est exactement le risque annoncé par la fiche M3, et il va contre la priorité du projet (rater une malade est plus grave). Dans MC1-OU-proche, l'élève adapté n'alerte plus presque jamais : T2 retombe sur F1 (4 malades rattrapées seulement, contre 14 sans adaptation).
- **Piste fermée** sous cette forme (TENT sur les normalisations, sans garde-fou de classe). Une suite éventuelle devrait au minimum empêcher l'effondrement (terme de diversité des prédictions, ou adaptation seulement des statistiques sans pas de gradient) ; non tentée aujourd'hui : ce serait une recette réglée après lecture.

Essais cumulés : **19** (plafond atteint).

## 16 h 34 : arrêt et bilan

- Pas d'autre essai : les trois pistes ont une conclusion nette (kNN et tête redisent F1 à ± 0,05 ; l'adaptation par entropie dégrade). Une 4e piste choisie maintenant serait de la pêche après lecture.
- `m15-traits` (premier tour) : à 16 h 32, `kaggle kernels status` répond « accès refusé » : le carnet a été supprimé ou annulé hors de cette session (pas par moi). Il n'a rien consommé pour M-kaggle2.
- **GPU M-kaggle2 : ≈ 0,32 h** (m15b-traits 0,17 h, m15b-tent 0,15 h) sur 3 h. Aucun téléchargement local autre que les sorties de mes deux carnets. Aucun commit.
- **Aucun finaliste.** Meilleur essai au coût : T2 (33,69, F1 − 0,25 ; échoue sur le coût et le temps) ; meilleur essai dans le temps : KD2 q = 0,10 (33,90 ; échoue sur le coût et roamer).
- `out/maladies/jour_1511/kaggle2/finalistes.md` écrit à 16 h 35.
