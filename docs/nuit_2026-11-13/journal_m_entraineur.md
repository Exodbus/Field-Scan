# Journal de l'agent M-entraîneur (nuit du 13 au 14 novembre 2026)

Cahier des charges : `docs/plan_nuit_2026-11-13.md`, sections 4.2 (ME1 à ME3), 4.3 (règles gelées), 6 et 7. GPU Kaggle : 7 h au plus pour moi. Aucun juge (BanSpot, Cordana du Pérou) n'est lu ; aucune de leurs images n'est envoyée. Aucun commit.

## 23 h 40 : lecture et choix écrits avant tout calcul

Lus : CLAUDE.md, plan du 13/11, journal M-entraînement du 12/11, récapitulatif (section 2), `scripts/m12_banc_commun.py`, `scripts/m12_banc_finalistes.py`, `fieldscan/modules/maladies.py` (F1), carnet `notebooks/m12_entrainer_v12_kaggle.py`.

**Référence F1** (définition exacte : `fieldscan/modules/maladies.py`, `decider_melange`) : lecteur proche = moyenne géométrique (v10b lue entière et en 4 morceaux 2 × 2, soupe, v2), seuils v10b sauf confiance 0,70, `jnsp_alerte` ; photo « loin » (p_loin ≥ 0,5) : réponse de la v2 si elle alerte, sinon celle du lecteur proche. Recalculée par mon script de mesure sur les mêmes photos que les candidats (5 jeux de réglage + `roamer_dev_loin_feuilles`).

**ME1. Distillation de F1 (famille B).**
1. Maître : probabilités du lecteur proche de F1 (`melange_geometrique(lecture_morceaux(P10, G2), Pso, Pv2)`, 4 classes), calculées sur Kaggle sur les images d'apprentissage seulement : Tanzanie 2021 et Pérou (`ensemble == entrainement`), Mendeley `wfzpdmc5vx` (422), TDTU (1 636) et Éthiopie (1 289) (appris seulement dans les plis qui ne les mesurent pas), jeux neufs `feuilles-nuit-1112` (1 405). Jamais la validation Tanzanie, PSFD, AgroVisionBD, `roamer_dev_loin_feuilles` ni aucun juge.
2. Élève : un ConvNeXt-Tiny (timm `convnext_tiny.dinov3_lvd1689m`, départ réseau 0 de la v10b), appris en 224 px, 3 époques de 16 000 tirages, EMA 0,998, AdamW 1e-5 / 1e-4, lu en 384 px avec 4 vues (préparation de la chaîne). Tirage : par source puis 50/50 saines / malades dans chaque source (leçon du 12/11). PSFD jamais appris.
3. Recettes :
   - **d1, distillation pure** : perte = entropie croisée douce contre les probabilités de F1 (température 1). Augmentations de base + basse résolution p = 0,3.
   - **d2, distillation + étiquettes** : perte = 0,5 × entropie croisée douce (F1) + 0,5 × perte pondérée du 12/11 (malade dite saine × 2, étiquettes sans nom → −log(1 − P(saine))). Augmentations de a13 (base + basse résolution 0,3 + morceaux 0,3), jeux neufs.
4. Mesure : validation croisée par pays, plis « sans TDTU » et « sans Éthiopie » (chaque pays lu par le réseau qui ne l'a pas appris) ; PSFD, validation Tanzanie, AgroVisionBD et `roamer_dev_loin_feuilles` (jamais appris) lus par les 2 plis, **moyenne des plis** retenue (pire pli rapporté). Chaîne : aiguilleur (caches existants), branche « loin » = v2 si elle alerte, sinon l'élève ; décision `decider_convnext` aux seuils de la v10b sauf la confiance, **0,70 (celle de F1), sans réglage**. Un réglage de la confiance sur le réglage (grille 0,50 à 0,80) compte comme un essai et sera signalé optimiste.
5. Modèle final (si un pli passe la règle 4.3) : un seul réseau appris sur tout (sans PSFD, sans validation, sans AgroVisionBD), même recette.

**ME2. v12 avec les leçons (famille B).** Base = recette v12a13 du 12/11 (sans PSFD, tirage 50/50 par source, jeux neufs, basse résolution 0,3, morceaux 0,3, perte × 2, seuils v10b). **e1** : morceaux de feuilles plus fréquents et plus petits (p = 0,5, côté 30 à 60 %), pour la Sigatoka légère. Mesure comme ME1 (2 plis), seuils de la v10b puis confiance 0,70.

**ME3. Lecteur « loin » neuf.** Décidé après le lancement de ME1 (données « plantes entières » à inventorier) ; écrit ici avant tout calcul de ME3.

**AgroVisionBD** : jeu de réglage, jamais appris. Pour le lire sur Kaggle sans envoyer 4,9 Go, chaque photo est envoyée **déjà préparée** : image décodée comme la chaîne (JPEG lu en 896 px, EXIF), recadrée en 384 × 384 (`ImageOps.fit`, BILINEAR), enregistrée en PNG sans perte ; le carnet refait ensuite JPEG 95 et normalisation, ce qui donne exactement le tenseur de `preparer_convnext` (vérifié en local sur quelques photos avant l'envoi).

**Coût de réglage** (règle 4.3) : moyenne à poids égaux des coûts de validation Tanzanie, TDTU, PSFD, Éthiopie et AgroVisionBD ; finaliste selon les 5 conditions de 4.3 contre F1, ou « variante rapide ». Temps par photo mesuré sur ce PC, mêmes photos, mêmes fils, pour F1 et pour le candidat.

**Compte des essais** : un essai = une recette passée en validation croisée, ou un réglage de seuil appliqué à des probabilités déjà sorties.

## 23 h 52 : référence F1 recalculée par mon script (`scripts/m13_entr_mesurer.py`)

[M] F1, même code que `scripts/m12_banc_finalistes.py` : validation 0 / 2 001 ; 62 / 1 000 (c = 6,20) | TDTU 19 / 1 059 ; 241 / 577 (47,15) | PSFD 102 / 738 (41,46) | Éthiopie 117 / 1 134 ; 28 / 155 (49,02) | AgroVisionBD 5 / 716 ; 87 / 366 (25,87). Coût sur 4 jeux 35,96 (chiffre du récapitulatif retrouvé) ; **coût de réglage (5 jeux) 33,94** : un finaliste doit être à **32,94 ou moins**. `roamer_dev_loin_feuilles` : F1 à calculer (maître sur Kaggle + aiguilleur local, `scripts/m13_entr_loin_roamer.py`, en cours).

Photos « loin » (p_loin ≥ 0,5) et alertes de F1 sur les saines vues de loin : TDTU 107 / 167 (dont 71 par la v2), AgroVisionBD 50 / 119 (20 par la v2) ; PSFD : 37 malades « loin » ratées sur 211.

Préparation : jeu Kaggle privé `affilecorentin/m13-entr-outils` (soupe, aiguilleur, v9 « loin », AgroVisionBD préparé en 384 px PNG), `scripts/m13_entr_preparer.py` ; contrôle de fuite par MD5 et par nom contre BanSpot (`data/raw/banspot`) et la Cordana du Pérou (`data/feuilles/images/test_perou`) avant l'envoi. Le carnet `notebooks/m13_entrainer_kaggle.py` refuse aussi tout chemin de juge et toute photo dont le SHA-256 est celui d'une photo `test_perou`.

## 23 h 55 : ME3 écrit avant tout calcul (carnet `notebooks/m13_loin_kaggle.py`)

- **l1** : ConvNeXt-Tiny torchvision, 2 classes (saine, malade), départ réseau 1 de la v9 « loin », préparation de la v2 (224 px), 4 vues. Apprentissage : photos entières du robot de `dev_loin` (1 312, rôle `apprentissage_loin` de `photos-loin` ; plantes saines → saine, fusarium / moko / bunchy top → malade), jeux neufs du Bangladesh (1 405), et photos « loin » (p_loin ≥ 0,5 dans les caches) de TDTU et d'Éthiopie dans le pli qui ne les mesure pas. Jamais la validation, PSFD, AgroVisionBD ni `roamer_dev_loin_feuilles`. Sources à parts égales, 50/50 saines / malades par source ; 4 époques de 4 000 tirages, AdamW 3e-5 / 3e-4, lissage 0,1, EMA.
- **Règle de chaîne** : photo « loin » → alerte si P_l1(malade) ≥ s **ou** si le lecteur proche alerte (même forme que F1, la v2 remplacée par l1). Variante « l1 seul » pour les photos « loin » mesurée aussi (essai à part).
- **Seuil s réglé sur `roamer_dev_loin_feuilles`** (règle du plan) : le plus haut s tel que l1 lu sur toutes les feuilles de `roamer_dev_loin_feuilles` ne rate pas plus de malades que la branche « loin » de F1 (v2, seuils de la chaîne) lue sur ces mêmes feuilles. Moyenne des 2 plis.
- AgroVisionBD n'est disponible sur Kaggle qu'en 384 px (préparation v10b) : l1 le lit après réduction à 224 px depuis ce 384 px (petit écart de préparation, noté).
- Mesure : coût de réglage des 5 jeux avec F1 en lecteur proche (famille C : F1 + réseau neuf), et avec l'élève de ME1 s'il existe.

## 0 h 06 : lot 1 lancé (`affilecorentin/m13-lot1`, T4 × 2)

- Jeu `m13-entr-outils` créé (privé). Contrôle de fuite : 1 801 MD5 de juges (BanSpot 1 300 fichiers + Cordana du Pérou), 1 092 fichiers envoyés et 1 082 photos d'origine d'AgroVisionBD : **aucun MD5 commun, aucun nom de juge** (`out/maladies/nuit_1311/kaggle/controle_fuite_outils.json`). Le premier passage avait refusé l'envoi parce que le filtre de noms « cordana » attrapait la classe `banana_cordana_spot_leaf` d'AgroVisionBD ; filtre ramené aux noms de juges (`cordana_perou`, `test_perou`). Préparation 384 px : écart 0,0 sur 20 photos.
- Carnet : phase maître (F1 sur l'apprentissage et sur `roamer_dev_loin_feuilles`, plus 300 photos de validation pour contrôler la lecture contre les caches), puis 4 recettes en plis (sans TDTU, sans Éthiopie) : **d1** (essai 1), **d2** (essai 2), **e1** (ME2, essai 3), **d3** = d2 avec alpha 0,75 (essai 4, ajouté avant tout résultat : encadre alpha).
- C-entraîneur occupe l'autre place GPU (`c13-lot1`, lancé à 23 h 42).

## 0 h 43 : temps par photo et aiguillage de `roamer_dev_loin_feuilles`

- [M] `scripts/m13_entr_temps.py`, 12 photos de validation, 2 fils, F1 et élève alternés photo par photo (élève = un ConvNeXt-Tiny DINOv3 en 384 px ; sans poids d'élève, le réseau 0 de la v10b a la même architecture donc le même coût) : F1 160 s, **élève 4 vues 18,6 s (rapport 0,116)**, élève 1 vue 6,0 s (0,037). La machine est très chargée par les autres agents (F1 met ici 75 à 600 s par photo au lieu de 6,8 s mesurées le 13/11 sur 8 fils machine seule) : seuls les **rapports** comptent. Ramené aux 6,8 s de F1 : élève 4 vues ≈ 0,8 s par photo ; d'après les composantes mesurées le 13/11 (aiguilleur 0,58 s, un ConvNeXt DINOv3 4 vues ≈ 1,1 s, v2 0,88 s sur les seules photos « loin ») : ≈ 1,7 à 1,8 s. Sous 2 s dans les deux estimations ; à remesurer machine seule. Sortie `out/maladies/nuit_1311/kaggle/temps.json`.
- [M] Aiguilleur sur `roamer_dev_loin_feuilles` (local, `scripts/m13_entr_loin_roamer.py`) : 2 789 / 2 985 feuilles vues « loin » (bunchy top 1 043 / 1 147 ; saines 1 209 / 1 270). Ce jeu teste donc surtout la branche « loin ».
- Quota Kaggle à 0 h 35 : 29,15 h utilisées sur 30 (remise à zéro à 1 h, heure de Paris) ; deux carnets tournent (le mien et `c13-lot1`).

## Arrêt vers 1 h 05, reprise le 14/11 à 13 h 10

La session s'est arrêtée vers 1 h 05 (tous les agents). Le carnet `m13-lot1` a continué sur Kaggle et s'est terminé (COMPLETE). Reprise à 13 h 10 sur demande de Corentin (`docs/nuit_2026-11-13/avenant_horaires.md`) : `finalistes.md` avant 18 h 40, gel à 19 h, règles inchangées. Aucune sortie n'avait été regardée avant l'arrêt.

## 13 h 15 : résultats du lot 1 (essais 1 à 4)

- **GPU** : `m13-lot1` a tourné 6 796 s, soit **1,89 h** de T4 × 2 (maître 73 min, 4 recettes 40 min). Total consommé par M-entraîneur : 1,89 h sur 7 h.
- **Contrôle du maître** : 300 photos de validation relues sur Kaggle contre les caches locaux : écart maximal 0,0008 sur les probabilités, **0 / 300 réponse de F1 différente**. Les cibles de distillation sont donc bien celles de F1.
- [M] `scripts/m13_entr_mesurer.py`, confiance 0,70 (celle de F1), moyenne des 2 plis (validation, PSFD, AgroVisionBD, roamer lus par les 2 plis ; TDTU et Éthiopie par le pli qui ne les a pas appris). Chaque case : malades sans alerte ; saines en alerte (coût).

| Candidat | Validation | TDTU | PSFD | Éthiopie | AgroVisionBD | Coût de réglage | roamer_dev_loin (malades sans alerte) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F1 (référence) | 0 ; 62 (6,20) | 19 ; 241 (47,15) | 102 (41,46) | 117 ; 28 (49,02) | 5 ; 87 (25,87) | **33,94** | 227 / 1 715 (saines en alerte 938 / 1 270) |
| d1, distillation pure | 3,5 ; 77 (8,22) | 11 ; 277 (51,12) | 59 (23,98) | 44 ; 91 (70,35) | 9 ; 107,5 (33,14) | 37,36 | 182,5 |
| d2, distillation + étiquettes (0,5) | 2,5 ; 108,5 (11,22) | 11 ; 289 (53,20) | 55,5 (22,56) | 45 ; 87 (68,03) | 5 ; 97 (28,60) | 36,72 | 190 |
| d3, distillation 0,75 | 2 ; 105 (10,80) | 11 ; 291 (53,55) | 56,5 (22,97) | 29 ; 102 (73,48) | 6,5 ; 97,5 (29,36) | 38,03 | 170 |
| e1 (ME2, morceaux 0,5) | 3 ; 104 (10,85) | 15 ; 263 (49,83) | 70 (28,46) | 53 ; 84 (68,21) | 5 ; 90 (26,69) | 36,81 | 234,5 |

- Lecture : à confiance 0,70 les élèves **ratent beaucoup moins de malades** que F1 (PSFD 102 → 55 à 70, Éthiopie 117 → 29 à 53, TDTU 19 → 11) mais alertent beaucoup plus sur les saines, surtout par « à vérifier » (Éthiopie 28 → 84 à 102 / 155). Un seul réseau est moins sûr de lui que le mélange : la confiance 0,70, réglée pour F1, ne lui convient pas. **Aucun n'est finaliste à 0,70** (coût de réglage 36,7 à 38,0 contre 33,94).
- **Essais 5 à 8 (réglage de la confiance, un par candidat, `scripts/m13_entr_seuils.py`)** : grille 0,40 à 0,80 (élargie sous 0,50, la borne écrite à 23 h 40, avant de lancer la grille). Meilleur coût : d2 à 0,50 → 32,44 (coût croisé 34,38), e1 à 0,46 → 33,10, d1 à 0,57 → 33,15, d3 à 0,50 → 32,98. **Aucun seuil ne remplit les conditions** : à chaque fois `roamer_dev_loin_feuilles` passe à 293 à 307 malades sans alerte (limite F1 + 2 = 229), et pour d1, d3 un pays perd plus de 2 points (TDTU). Chiffres optimistes (seuil choisi sur les jeux qui le mesurent).
- Pourquoi le roamer bloque : 2 789 / 2 985 de ses feuilles sont vues « loin » ; la branche « loin » alerte si la v2 **ou** le lecteur proche alerte ; avec une confiance basse, l'élève dit « saine » sur des feuilles du robot que F1 envoyait en « à vérifier ».
- Essais comptés : **8**.

## 13 h 17 : essais 9 à 12 écrits avant calcul (deux confiances)

Pour chaque élève (d1, d2, d3, e1) : une confiance pour les photos « proche » (s_p, grille 0,40 à 0,80, pas 0,02) et une autre pour l'élève quand il intervient dans la branche « loin » (s_l, grille 0,50 à 0,90, pas 0,02 ; la v2 reste inchangée). Couple retenu : coût de réglage le plus bas parmi ceux qui remplissent les conditions « finaliste » sans le temps. Un essai par candidat ; coût croisé (couple choisi sur 4 jeux, appliqué au 5e) rapporté à côté. Ce réglage est du type MB1 (seuil propre aux photos « loin ») appliqué à un réseau neuf : il est signalé à M-banc pour éviter un doublon.

## 13 h 20 : essais 9 à 12 (deux confiances) : d2 et d3 passent sur le réglage

[M] `scripts/m13_entr_seuils2.py` (sorties `out/maladies/nuit_1311/kaggle/lot1/seuils2_*.json`) :

| Candidat | s_p ; s_l | Validation | TDTU | PSFD | Éthiopie | AgroVisionBD | Coût de réglage | Coût croisé | roamer (ratées / 1 715) | Conditions sans le temps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | 0,70 | 0 ; 62 | 19 ; 241 | 102 | 117 ; 28 | 5 ; 87 | 33,94 | — | 227 | — |
| **d2** | 0,50 ; 0,66 | 6,5 ; 55 | 25 ; 224 | 84 | 124 ; 33 | 8 ; 64 | **32,29** | 34,09 | 226,5 | **oui** (19 couples valides) |
| **d3** | 0,50 ; 0,70 | 6 ; 45 | 31 ; 219 | 87 | 120 ; 35 | 10,5 ; 64 | **32,74** | 33,73 | 192 | **oui** (4 couples valides) |
| d1 | 0,58 ; 0,68 | 6,5 ; 40,5 | 30 ; 211 | 88,5 | 112 ; 40 | 12 ; 68 | 33,02 | 38,53 | 216 | non (coût) |
| e1 | 0,46 ; 0,50 | 6,5 ; 59 | 34 ; 203 | 101,5 | 129 ; 29 | 8 ; 59 | 33,05 | 35,54 | 298,5 | non (coût, roamer) |

- d2 et d3 remplissent les 4 conditions de réglage contre F1 (coût ≤ 32,94 ; Tanzanie ≤ 14 et ≤ 77 ; aucun jeu ne perd plus de 2 points de malades sans alerte : au pire TDTU + 0,6 point, Éthiopie + 0,6 ; roamer ≤ 229). Le temps (rapport 0,12 de F1) passe largement.
- **Réserves, à écrire avec le chiffre** : (1) marge faible (d2 : 1,65 point sous F1 ; d3 : 1,20) et seuils choisis sur les jeux qui les mesurent après 12 essais ; le coût croisé (34,09 et 33,73) est **au niveau de F1 ou au-dessus** : le gain n'est pas sûr. (2) Les élèves ratent un peu plus de malades que F1 partout sauf PSFD (validation 0 → 6,5 ; AgroVisionBD 5 → 8 à 10,5) et donnent moins de fausses alertes : c'est un autre compromis, pas un F1 plus rapide. (3) La moyenne des 2 plis est un ensemble de deux réseaux appris sans un pays ; le modèle livré est un réseau unique appris sur tout (carnet `m13-final1`).
- **Fuite de référence trouvée en passant** : la soupe (v2 + v8), un des trois lecteurs de F1, contient la v8, apprise sur 1 090 recadrages des scènes de `dev_loin` (`docs/protocole_maladies_v8.md`). Le chiffre de F1 sur `roamer_dev_loin_feuilles` est donc optimiste ; la condition « roamer ≤ F1 + 2 » est plus dure pour un réseau neuf qui n'a jamais vu ce robot.
- 13 h 18 : `m13-final1` lancé (modèles finaux de d2 et d3, un réseau chacun, sur tout sauf PSFD, validation et AgroVisionBD ; maître repris des sorties de `m13-lot1`).
- Essais comptés : **12**.

## 13 h 22 : ME3, réponse au point du Contrôleur (fuite `dev_loin`)

Le Contrôleur a raison, et la fuite est double : l1 (écrit à 23 h 55) apprenait les photos entières du robot `dev_loin`, **et** partait de la v9, elle-même apprise sur les 2 985 feuilles de `roamer_dev_loin_feuilles`. l1 n'a jamais été lancé. Il est remplacé par **l1b**, écrit ici avant tout calcul :
- **aucune photo du robot** (`dev_loin` ni `val_loin`) et **pas de départ v9** : départ = réseau 1 de la v2 (qui n'a appris aucune image ROAMER), tête neuve à 2 classes initialisée depuis celle de la v2 ;
- apprentissage : jeux neufs du Bangladesh (1 405) + photos « loin » de TDTU et d'Éthiopie (pli qui ne les mesure pas) ; reste de la recette inchangé (4 époques de 4 000, sources à parts égales, 50/50) ;
- `roamer_dev_loin_feuilles` ne sert alors qu'à régler s (règle de 23 h 55) et au contrôle « ratées ≤ F1 + 2 », sans qu'aucune de ses scènes ait été apprise par l1b. Un découpage par scène n'est pas nécessaire puisque rien du robot n'est appris.

## 13 h 30 : essais 13 et 14 écrits avant calcul (bruit d'une graine)

La marge de d2 et d3 (1,2 à 1,7 point) est de l'ordre du bruit d'une graine mesuré le 12/11 (≈ 1 point). Lot 2 : d2 et d3 refaits avec la graine 1 (`d2g1`, `d3g1`), même recette, mesurés **aux couples déjà choisis** (d2 : 0,50 ; 0,66 ; d3 : 0,50 ; 0,70), sans nouveau réglage. Règle écrite avant : si la version graine 1 n'est pas elle aussi sous 32,94, le candidat reste écrit dans `finalistes.md` mais avec la mention « instable d'une graine à l'autre » ; si l'un des deux reste sous 32,94 avec les deux graines et l'autre non, c'est lui qui passe en premier. Aucun autre réglage n'en découle.

Probabilités moyennes des plis déposées pour M-banc (famille C) : `out/maladies/nuit_1311/kaggle/pour_banc/{d1,d2,d3,e1}/predictions_<candidat>_<jeu>.csv` (6 jeux, colonnes du cache : chemin, jeu, classe_vraie [malade / saine], p_saine, p_black_sigatoka, p_fusarium, p_autre). Entrées de F1 sur `roamer_dev_loin_feuilles` : `out/maladies/nuit_1311/kaggle/maitre/maitre_roamer_dev_loin.npz` (P10, G2, Pso, Pv2) et `p_loin_roamer_dev_loin.csv`.

## 13 h 45 : modèles finaux d2 et d3 (`m13-final1`) : contrôle défavorable sur le roamer

- GPU : `m13-final1` 1 302 s = **0,36 h**. Poids : `modeles/maladies_nuit_1311/final1/maladies_m13d2_0.pt`, `maladies_m13d3_0.pt` (un réseau chacun, appris sur tout sauf PSFD, validation et AgroVisionBD).
- [M] Contrôle sur les jeux qu'ils n'ont pas appris, aux couples déjà choisis (`scripts/m13_entr_controle_final.py`, `out/maladies/nuit_1311/kaggle/controle_final.json`) :

| Modèle | Validation | PSFD | AgroVisionBD | roamer (ratées / 1 715) |
| --- | --- | --- | --- | --- |
| F1 | 0 ; 62 | 102 | 5 ; 87 | 227 |
| d2, moyenne des 2 plis | 6,5 ; 55 | 84 | 8 ; 64 | 226,5 (plis : 248 et 205) |
| d2, modèle final | 7 ; 53 | 112 | 9 ; 47 | **276** |
| d3, moyenne des 2 plis | 6 ; 45 | 87 | 10,5 ; 64 | 192 (plis : 196 et 188) |
| d3, modèle final | 7 ; 47 | 103 | 13 ; 61 | **239** |

- Lecture : le nombre de feuilles du robot ratées varie beaucoup d'un réseau à l'autre (205 à 276 pour la même recette d2). Les modèles finaux, qui ont appris TDTU **et** l'Éthiopie (plus de saines « d'ailleurs »), sont plus indulgents sur le robot et **dépassent la limite roamer (229)**. Le modèle final unique n'est donc pas le candidat mesuré.
- Décision (écrite avant les lots suivants) : le candidat livrable devient **l'ensemble des 2 réseaux des plis** (moyenne des probabilités du réseau « sans TDTU » et du réseau « sans Éthiopie »), c'est-à-dire exactement ce qui a été mesuré. Ses chiffres : TDTU et Éthiopie lus par le réseau qui ne les a pas appris, validation / PSFD / AgroVisionBD / roamer lus par l'ensemble (moyenne des probabilités). Coût en temps : 2 réseaux (rapport ≈ 0,23 de F1). Les poids des plis du lot 1 n'ont pas été gardés : un lot 3 refait d2 et d3 (graine 0) **en gardant les poids** ; les couples (s_p, s_l) restent ceux des essais 10 et 11, sans nouveau réglage.
- Le lot 2 (`m13-lot2`, graine 1, poids non gardés) part comme prévu ; une tentative de le remplacer par une version qui garde les poids a été refusée par Kaggle (2 sessions GPU déjà prises).

## 14 h 08 : lot 2 remplacé par le lot 2b (même expérience, poids gardés)

- `m13-lot2` est resté en file d'attente Kaggle (QUEUED) de 13 h 42 à 14 h 08 sans démarrer ; je l'ai supprimé (aucune sortie, aucun GPU consommé) et remplacé par `m13-lot2b`, qui fait en un seul carnet ce que devaient faire les lots 2 et 3 : **d2b, d3b** (graine 0, refaits en gardant les poids des 2 plis : candidats livrables) et **d2g1, d3g1** (graine 1, poids gardés : bruit d'une graine, essais 13 et 14). Couples de confiances inchangés (d2 : 0,50 ; 0,66 ; d3 : 0,50 ; 0,70). Règles de 13 h 30 et 13 h 45 inchangées.
- [M] Lecture locale contrôlée : le modèle final d2 lu par `fieldscan.modules.maladies.predire_convnext` (32 bits, processeur) redonne les probabilités du carnet (16 bits) à 6e-5 près sur 6 photos de validation. `charger_convnext` charge plusieurs réseaux d'un même dossier (motif) : l'ensemble des 2 plis s'installe comme la v10b, dans un dossier à 2 poids et un `seuils.json`.

## 15 h 20 : file d'attente Kaggle

- `m13-lot2b` est en file d'attente (QUEUED) depuis 14 h 08, sans consommer de GPU ; `c13-lot3` (C-entraîneur) aussi depuis 14 h 57 : manque de T4 chez Kaggle, pas une limite du compte (quota : 1,78 h utilisées sur 30 à 14 h 39, toutes de C-entraîneur). Les deux places de session sont prises par ces deux carnets en attente : rien d'autre ne peut partir (ni l1b).
- `out/maladies/nuit_1311/kaggle/finalistes.md` écrit dans un état provisoire (14 h 50) : d2 et d3 passent la règle sur le réglage, mais aucun poids livrable ne correspond encore à ces chiffres ; ils ne doivent pas être admis tant que le lot 2b n'a pas rendu ses poids.
- GPU consommé par M-entraîneur : 1,89 h (lot 1) + 0,36 h (final1) = **2,25 h**.

## 16 h 55 : lot 2p sur P100

`m13-lot2b` (T4 × 2) est toujours en file d'attente (2 h 47). Une place s'étant libérée, j'ai envoyé `m13-lot2p` sur **P100** (une seule carte, file libre : démarrage immédiat) avec seulement **d2b et d3b** (graine 0, poids des plis gardés), même carnet, même recette, mêmes couples. Si le P100 n'est pas pris en charge par le torch de Kaggle, le carnet échoue tout de suite. Le lot 2b reste en file (bruit d'une graine).

## 17 h 27 : lot 2p terminé (d2b, d3b, poids gardés) ; d3b seul finaliste

- Le carnet `m13-lot2p`, envoyé avec la forme « P100 », a en fait tourné sur T4 × 2 (Kaggle) : 1 895 s = **0,53 h**. `m13-lot2b` (encore en file à 17 h 27) est supprimé : ses résultats seraient arrivés après le gel. Le bruit d'une graine (essais 13 et 14) n'est donc pas mesuré ; à la place, d2b et d3b sont des **reprises de la même recette et de la même graine** (le GPU n'est pas déterministe), ce qui mesure déjà une part du bruit.
- [M] `scripts/m13_entr_ensemble.py lot2p d2b:d2 d3b:d3`, couples des essais 10 et 11 sans nouveau réglage :

| Candidat livrable (ensemble des 2 plis) | Validation | TDTU | PSFD | Éthiopie | AgroVisionBD | Coût de réglage | roamer | Finaliste |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | 0 ; 62 | 19 ; 241 | 102 | 117 ; 28 | 5 ; 87 | 33,94 | 227 | — |
| d2 (lot 1, poids perdus) | 6 ; 56 | 25 ; 224 | 81 | 124 ; 33 | 7 ; 67 | 32,13 | 215 | (oui) |
| **d2b** (reprise) | 4 ; 55 | 21 ; 232 | 93 | 124 ; 33 | 8 ; 67 | **33,16** | 209 | **non** (coût > 32,94) |
| d3 (lot 1, poids perdus) | 7 ; 43 | 31 ; 219 | 88 | 120 ; 35 | 10 ; 63 | 32,72 | 183 | (oui) |
| **d3b** (reprise) | 5 ; 42 | 30 ; 218 | 86 | 120 ; 35 | 10 ; 70 | **32,77** | 182 | **oui** |

- Lecture : d2 n'est pas stable d'une reprise à l'autre (32,13 → 33,16, surtout PSFD 81 → 93) : il sort. d3 l'est (32,72 → 32,77). **d3b est le seul finaliste de M-entraîneur** (famille B), poids rangés dans `modeles/maladies_nuit_1311/d3b/` (2 réseaux + `seuils.json`). Lecture locale contrôlée : `charger_convnext` + `predire_convnext` redonnent les probabilités du carnet à 6e-5 près.
- Essais comptés : **14** (12 + les deux reprises d2b, d3b mesurées aux couples déjà choisis). ME3 : rien n'a tourné (l1b sans place GPU).
- **GPU consommé au total : 1,89 + 0,36 + 0,53 = 2,78 h** sur 7 h.

## 17 h 45 : ME3 l1b lancé (`m13-loin2`)

`m13-loin1` (forme « T4 ») est resté en file 16 min ; supprimé et renvoyé avec la forme « P100 » (`m13-loin2`), qui démarre tout de suite (le lot 2p avait fait de même et tourné sur T4 × 2 : la file semblait propre à la forme demandée). Recette l1b telle qu'écrite à 13 h 22, aucun changement. `finalistes.md` écrit à 17 h 30 avec d3b ; l1b y sera ajouté seulement s'il rend ses résultats et passe la règle avant 18 h 40.

## 17 h 55 : résultat de ME3 (l1b) : pas de finaliste

- GPU : `m13-loin2` 508 s = **0,14 h**. Le journal du carnet affiche les photos du robot dans la table d'entrée (elles sont chargées), mais la recette l1b les retire de chaque pli (`robot=False`) : aucune n'est apprise.
- [M] `scripts/m13_entr_loin_mesurer.py loin2 l1b lot2p:d3b` (`out/maladies/nuit_1311/kaggle/loin2/bilan_loin_l1b.json`). Seuil réglé sur `roamer_dev_loin_feuilles` (règle de 23 h 55) : la v2 seule rate 393 feuilles malades du robot ; l1b à s = 0,58 en rate 386 (806 saines en alerte sur 1 270).

| Chaîne (photo « loin ») | Coût de réglage | Validation | TDTU | PSFD | Éthiopie | AgroVisionBD | roamer | Finaliste |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 (v2 ou proche) | 33,94 | 0 ; 62 | 19 ; 241 | 102 | 117 ; 28 | 5 ; 87 | 227 | — |
| F1 + l1b ou proche (famille C) | 34,16 | 0 ; 62 | 16 ; 249 | 100 | 117 ; 28 | 5 ; 92 | 219 | non (coût) |
| F1 + l1b seul | 35,61 | 1 ; 62 | 22 ; 248 | 108 | 158 ; 25 | 5 ; 68 | 370 | non |
| d3b + l1b ou proche | 32,28 | 5 ; 42 | 33 ; 215 | 96 | 123 ; 30 | 10 ; 54 | **308** | non (roamer) |
| d3b + l1b seul | 34,10 | 5 ; 42 | 36 ; 214 | 104 | 164 ; 25 | 10 ; 45 | 391 | non |

- Lecture : appris sans le robot, l1b ne vaut guère mieux que la v2 sur les feuilles du robot (386 contre 393 ratées) ; il retire des « à vérifier » sur les saines vues de loin d'AgroVisionBD (F1 + l1b seul : 87 → 68 saines en alerte) mais rate plus de malades en Éthiopie (117 → 158). Aucune forme ne passe : **ME3 sans finaliste**. Pour F1 sur AgroVisionBD, 94 photos « loin » sans morceaux lus ont été décidées sans morceaux (approximation, sans effet sur la conclusion : le coût de F1 + l1b est au-dessus de F1 de toute façon).
- Essais comptés : **18** (14 + 4 formes de chaîne de ME3). **GPU total : 2,78 + 0,14 = 2,92 h** sur 7 h.
