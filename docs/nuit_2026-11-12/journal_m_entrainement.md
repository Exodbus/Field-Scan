# Journal de l'agent M-entraînement (nuit du 12 au 13 novembre 2026)

But : entraîner des candidats « v12 » (M4 à M7 du plan, section 4.3) qui ratent moins de malades hors Tanzanie sans alerter partout. Réglage : validation Tanzanie 2022-2023 + validation croisée par pays (TDTU, PSFD, Éthiopie). Juges (BanSpot, Cordana du Pérou) : jamais pendant le réglage.

## 22 h 20 : lecture et état de départ

- Lus : CLAUDE.md, plan (sections 1, 2, 4, 5), protocoles v10b et v10c, LISEZMOI et classifieur de la v10b, `fieldscan/modules/maladies.py` (preparer_convnext, decider_convnext), carnets « cinq classes » et « recette », carnet `predire-v10b`, `scripts/mesurer_v10b.py`.
- **Quota GPU Kaggle à 22 h 20 : 14,81 h utilisées, 15,19 h restantes sur 30** (remise à zéro le 14/11). Ce quota est partagé avec C-entraînement (comptage) : je me fixe un plafond d'environ 7 h.
- Données déjà sur Kaggle : `feuilles-pret-perou` (Tanzanie 2021 + Pérou, 16 963 ; validation 3 001), `feuilles-v3-ajouts` (TDTU 1 636), `maladies-nuit` (PSFD 738, Éthiopie 1 289, Mendeley `wfzpdmc5vx` 422), `maladies-v10b-poids` (3 poids + `listes_v10b.csv`, la liste exacte des photos mesurées le 11/11).
- Référence v10b (chaîne, 11/11), coût 4.4 = 3 × malades sans alerte + saines en alerte : Tanzanie 9 / 2 001 et 57 / 1 000 (7,05) ; TDTU 83 / 1 059 et 177 / 577 (54,19) ; PSFD 149 / 738 (60,57) ; Éthiopie 179 / 1 134 et 43 / 155 (75,10). **Coût moyen : 49,23.** Un finaliste doit être à 48,23 ou moins.

## 22 h 25 : choix écrits avant tout entraînement

1. **Classes** : celles de la v10b (saine, black_sigatoka, fusarium, autre). Étiquettes des pays reclassés :
   - TDTU : saine → saine ; black_sigatoka → black_sigatoka ; `autre_maladie` (maladies non nommées, peut-être hors classes) → **perte −log(1 − P(saine))**, sans nom imposé ;
   - PSFD : black_sigatoka → black_sigatoka ; Sigatoka jaune → **classe « autre »** (la v10b range la Sigatoka jaune dans « autre ») ;
   - Éthiopie : saine → saine ; Xanthomonas → **classe « autre »** (flétrissement bactérien, déjà dans « autre » pour la v10b) ; « sigatoka » (noire ou jaune, non précisé) → **perte −log(1 − P(saine))** ;
   - Mendeley `wfzpdmc5vx` : Cordana et Pestalotiopsis → « autre » (comme prévu pour la v10c).
2. **Perte pondérée** (une malade dite saine coûte 3) : pour une malade nommée, entropie croisée + 2 × (−log(1 − P(saine))) ; pour une malade sans nom, 3 × (−log(1 − P(saine))) ; pour une saine, entropie croisée. Autrement dit le terme « malade ou saine » pèse 3 pour les malades, le terme « quelle maladie » pèse 1.
3. **Tirage** équilibré par pays puis par classe dans le pays (tirage avec remise). Parts par défaut : Tanzanie 40 %, Pérou 10 %, Mendeley 5 %, le reste partagé à égalité entre les pays reclassés présents dans le pli. Variante « égal » : toutes les sources à parts égales. 16 000 photos tirées par époque.
4. **Recette de base (M4)** : départ = réseau 0 de la v10b ; AdamW 1e-5 (réseau) et 1e-4 (tête), décroissance 0,05, cosinus, 3 époques, lots de 32, précision mixte, EMA 0,998 (les poids EMA de la fin sont gardés, pas de choix d'époque), 224 px à l'apprentissage, 384 px + 4 vues à la lecture, augmentations du carnet « cinq classes », pas de lissage. M5 = M4 + augmentations fortes + CutMix de fonds + lissage 0,1.
5. **CutMix de fonds** (M5) : un rectangle (10 à 30 % de la surface) pris dans une photo **saine** du même lot est collé sur la photo ; l'étiquette ne change pas (une feuille malade en partie cachée par du vert sain reste malade, une saine reste saine). Pas de mélange d'étiquettes.
6. **Mesure d'un pli** : pays X lu par le réseau entraîné sans X. **Tanzanie** : la validation est lue par les 3 plis ; le chiffre retenu pour la règle « finaliste » est la **moyenne des 3 plis** (malades sans alerte et saines en alerte), et le pire pli est rapporté à côté. Décision : `decider_convnext` avec les seuils de la v10b inchangés ; chaîne complète = aiguilleur (`p_loin` ≥ 0,5 → réponse de la v2, politique b) + candidat pour les photos « proche », comme `scripts/mesurer_v10b.py`.
7. **Lecture en précision mixte** dans les plis (plus rapide) ; l'écart avec la lecture en 32 bits du 11/11 est mesuré par un témoin (v10b relue par le carnet). Les modèles finaux sont lus en 32 bits par la chaîne locale.
8. **Témoins** (ne comptent pas comme essais) : v10b à 3 réseaux relue par mon carnet (contrôle du carnet) et réseau 0 seul (pour savoir ce que coûte le passage de 3 réseaux à 1 dans les plis).
9. **Réglage des seuils d'un candidat** (si fait) : seulement sur le réglage ; grille seuil_alerte × seuil de la règle B ; le couple retenu minimise le coût moyen sous les contraintes « finaliste ». Compté comme essai.
10. **Compte des essais** : un essai = une recette passée en validation croisée (3 plis), ou un réglage de seuils / de tête appliqué à des probabilités déjà sorties.

## 22 h 35 : reprise sous le plan `docs/plan_nuit_10h.md` (rôle M-entraîneur, essais 10 à 20)

- Quota GPU noté à 22 h 20 : 15,19 h restantes (voir plus haut). Priorité du plan si le quota manque : v12 par pays d'abord.
- Le premier envoi du carnet d'extraction DINOv3 (M6) a été refusé : il lisait aussi la Cordana du Pérou (un juge) dans un fichier à part. **Corrigé** : le carnet `notebooks/m12_extraire_dinov3_kaggle.py` ne lit plus que l'apprentissage et le réglage, avec un contrôle qui l'interdit. Aucun de mes carnets ne lit BanSpot ni la Cordana du Pérou.
- Écart de référence : le plan 10 h donne un coût v10b de 45,4 (calcul de M-banc) ; mon script `scripts/m12_entr_mesurer.py`, qui reprend exactement `scripts/mesurer_v10b.py` (chaîne, aiguilleur, v2 en « loin »), redonne les chiffres du protocole v10b (9/2 001, 57/1 000 ; 83/1 059, 177/577 ; 149/738 ; 179/1 134, 43/155), soit **49,23**. Je compare tous mes candidats à 49,23 avec ce même script ; la différence avec 45,4 vient sans doute d'une autre façon de compter (à rapprocher avec M-banc).
- Les probabilités de chaque candidat seront déposées dans `out/maladies/nuit_1112/kaggle/<candidat>/predictions_<candidat>_<jeu>.csv` (colonnes chemin, jeu, classe_vraie, p_saine, p_black_sigatoka, p_fusarium, p_autre, comme `out/maladies/v10b/`).
- Essai local du carnet d'entraînement (processeur, quelques photos) en cours.
## 22 h 37 : lot 1 lancé (essais 10 et 11)

- Carnet Kaggle privé `affilecorentin/m12-lot1` (T4 × 2, copie dans `C:/Users/coren/kaggle_tmp/m12_lot1/`), plis par pays :
  - **a1 = v12a (essai 10)** : recette de base (choix 1 à 4) ;
  - **b1 = v12b (essai 11)** : a1 + augmentations fortes (éclairage, couleur, flou, JPEG 20-95, effacement jusqu'à 25 %, recadrage 0,25-1) + CutMix de fonds sains (p = 0,5) + lissage 0,1 ;
  - témoins t1 (réseau 0 de la v10b seul) et t3 (3 réseaux) relus par le carnet, pour contrôler la lecture et savoir ce que coûte un seul réseau par pli.
- Le carnet d'extraction DINOv3 (v12c, essai 12) est prêt mais refusé par Kaggle : « Maximum batch GPU session count of 2 reached » (un autre agent occupe l'autre place). Il partira dès qu'une place se libère.
- Scripts : `notebooks/m12_entrainer_v12_kaggle.py` (carnet), `scripts/m12_entr_pousser.py` (envoi), `scripts/m12_entr_mesurer.py` (chaîne + coût 4.4), `scripts/m12_entr_tete.py` (tête légère v12c, local).
## 22 h 52 : carnet complété pendant que le lot 1 tourne

- Options ajoutées au carnet (pour les essais suivants, le lot 1 tourne sur la version d'avant) : `taille` (apprentissage en 384 px, essai 13), `poids_ratee` (essai 14), `dro` (perte par groupe façon Group-DRO, les pays les plus mal servis pèsent plus, essai 15), `morceaux` (la photo est remplacée par un de ses morceaux, même étiquette, essai 17), `deux_temps` (1re époque : tête et dernier étage seuls, essai 18).
- Essai local (processeur, quelques photos) de ces options : passe sans erreur (`C:/Users/coren/kaggle_tmp/m12_essai_local.log`).
- `scripts/m12_entr_seuils.py` : réglage des seuils (alerte × règle B) sur le réglage seulement, sous les contraintes « finaliste ».
- L'API Kaggle renvoie des erreurs SSL sur les journaux des carnets (Norton ?) ; l'état et les sorties restent lisibles.
## 23 h 05 : résultats du lot 1 (essais 10 et 11)

- Carnet terminé en erreur **pour b1 seulement** : « os.fork is unsafe while filelock is changing descriptor ownership » (deux fils, un par GPU, qui créent leurs processus de chargement en même temps). a1, t1 et t3 sont complets. Corrigé : un verrou autour du chargement des poids et de la création des processus de chargement. b1 est à relancer (lot 2). GPU : environ 26 min de T4 × 2.
- Durée : un pli (3 époques de 16 000 photos) ≈ 5 min d'entraînement + lecture ; une recette (3 plis) ≈ 19 min sur un GPU.
- **Contrôle du carnet** : t3 (la v10b relue par le carnet, précision mixte) redonne exactement les chiffres du 11/11 sur les 4 jeux. La lecture du carnet est donc fiable.

| Recette (seuils v10b) | Tanzanie (moy. plis) | TDTU | PSFD | Éthiopie | Coût moyen | Finaliste |
| --- | --- | --- | --- | --- | --- | --- |
| v10b (3 réseaux, 11/11) | 9 ; 57 (7,05) | 83 ; 177 (54,19) | 149 (60,57) | 179 ; 43 (75,10) | **49,23** | — |
| t3 (témoin, v10b relue) | 9 ; 57 | 83 ; 177 | 149 | 179 ; 43 | 49,23 | — |
| t1 (témoin, réseau 0 seul) | 5 ; 51 (5,85) | 90 ; 174 (55,65) | 143 (58,13) | 209 ; 30 (74,65) | 48,57 | non |
| **a1 = v12a (essai 10)** | 5 ; **147** (15,45) | **47** ; **393** (81,43) | 134 (54,47) | **112** ; 74 (77,37) | 57,18 | non |

(chaque case : malades sans alerte ; saines en alerte (coût). Tanzanie : moyenne des 3 plis ; pire pli 8 ratées, 191 fausses alertes.)

- **Lecture de a1** : il rate beaucoup moins de malades hors Tanzanie (TDTU 83 → 47, Éthiopie 179 → 112), mais alerte presque partout : 393 / 577 saines de TDTU, 147 / 1 000 en Tanzanie. Hypothèse [H] : raccourci « pays inconnu = malade ». PSFD et Mendeley n'ont presque que des malades ; avec le tirage par pays, une photo « d'ailleurs » est surtout une malade ; le poids 3 accentue l'effet.
- **Essai 10b (réglage des seuils de a1 sur le réglage)** : avec la règle B, une photo n'est dite saine que si P(saine) ≥ max(seuil règle B, 1 − seuil d'alerte) : il n'y a qu'un bouton. Aucun réglage ne respecte Tanzanie ≤ 77 fausses alertes sans dépasser 14 ratées et sans faire remonter le coût (meilleur coût 55,8). **a1 : échec.**
- **Essai 10c (seuil de t1, réseau 0 de la v10b seul, sans entraînement)** : seuil règle B 0,63 → coût 47,04, Tanzanie 3 ; 67, et respecte les contraintes « finaliste » (coût 47,04 ≤ 48,23). C'est un réglage de seuil sans entraînement (domaine de M-banc, essai 4 de sa file) : noté, transmis, pas retenu comme candidat v12.
- Essais comptés à 23 h 05 : **3** (a1, réglage a1, réglage t1).
- Prochain lot (dès qu'une place GPU se libère ; l'extraction DINOv3 et un carnet de M-banc occupent les deux places) : b1 (v12b), et des variantes qui visent le raccourci « pays = malade » : poids de la perte 1 (essai 14), Tanzanie à 60 % du tirage, PSFD (sans saines) hors de l'apprentissage.
## 23 h 40 : diagnostic de a1, extraction DINOv3, premières têtes v12c

- **Diagnostic de a1 (sans effet sur les règles)** : aire sous la courbe saine / malade sur le pays jamais appris — TDTU 0,882 (v10b 0,897, réseau 0 seul 0,894), Éthiopie 0,884 (v10b 0,879). **Apprendre les autres pays ne rend pas le pays tenu à l'écart mieux séparable** : a1 a seulement déplacé toutes les probabilités vers « malade ». Ses malades « gagnées » sont payées en fausses alertes. Script : `C:/Users/coren/kaggle_tmp/m12_auc.py`.
- Carnet `m12-extraire-dinov3` terminé (≈ 13 min de T4) : caractéristiques (24 049 photos × 5 vues × 1 536) dans `out/maladies/nuit_1112/kaggle/caract_dinov3/`. Aucun juge dedans (contrôle dans le carnet).
- Machine locale saturée par les autres agents : torch à plusieurs fils devient 100 fois plus lent ; `scripts/m12_entr_tete.py` tourne sur un fil (variable FILS).
- **c1 = v12c, tête logistique sur la photo entière (essai 12)**, seuils v10b : Tanzanie 33,7 ; 67,7 (pire pli 46 ratées) ; TDTU 52 ; 433 ; PSFD 169 ; Éthiopie 257 ; 13. Coût moyen **61,67** ; aucun réglage de seuil ne respecte les contraintes (essai 12b). Aire sous la courbe : TDTU 0,764 (bien pire que la v10b), Éthiopie 0,918 (meilleure que la v10b, 0,879). **c1 : échec** comme modèle seul ; ses probabilités sont déposées pour M-banc (mélange avec la v10b, essai 9 de sa file), l'Éthiopie y gagne peut-être.
- Lot 2 envoyé à 23 h 25 (`m12-lot2`) : b1 (v12b), a2 (poids de la perte 1), a3 (moitié du tirage en saines), a4 (a3 + PSFD jamais appris, lu par le réseau du pli « sans TDTU »).
- Essais comptés : **5** (a1, réglage a1, réglage t1, c1, réglage c1).
## 0 h 25 : résultats du lot 2 (essais 11, 14 et variantes) et c2

| Recette (seuils v10b) | Tanzanie (moy. plis) | TDTU | PSFD | Éthiopie | Coût moyen | Finaliste |
| --- | --- | --- | --- | --- | --- | --- |
| v10b (11/11) | 9 ; 57 | 83 ; 177 | 149 | 179 ; 43 | **49,23** | — |
| b1 = v12b (essai 11) | 4 ; 251 | 47 ; 379 | 113 | 81 ; 91 | 57,69 | non |
| a2 = poids de perte 1 (essai 14a) | 12 ; 84 | 52 ; 320 | 148 | 205 ; 28 | 53,21 | non |
| a3 = moitié du tirage en saines | 10 ; 88 | 52 ; 347 | 144 | 282 ; 23 | 58,30 | non |
| **a4 = a3 + PSFD jamais appris** | 7,5 ; 46,5 (pire pli 11 ; 55) | 57 ; 258 | 147 | 178 ; 28 | **47,89** | **oui** |
| c2 = v12c, tête logistique, photo + 4 morceaux (essai 12) | 37,7 ; 40 | 47 ; 370 | 188 | 258 ; 15 | 60,36 | non |

- Réglage des seuils (essais 11b, 14b, a3b, a4b, c2b) : seul a4 a un réglage valide (règle B 0,65 → 46,85 ; Tanzanie 4,5 ; 60,5). b1, a2, a3, c2 : aucun.
- Aire sous la courbe (pays tenu à l'écart) : b1 TDTU 0,904 / Éthiopie 0,886 ; a2 0,903 / 0,904 ; a3 0,882 / 0,880 ; a4 0,896 / 0,918 ; c2 0,869 / 0,894 (v10b 0,897 / 0,879).
- **a4 est le premier finaliste v12** (47,89 ≤ 48,23 ; Tanzanie 7,5 et 46,5 ; aucun pays ne perd : TDTU −2,5 pts, PSFD −0,3, Éthiopie −0,1). Il garde les seuils de la v10b. PSFD est lu par le réseau du pli « sans TDTU », qui n'a jamais vu PSFD.
- b1 (v12b, augmentations fortes) : **échec, piste fermée** (même verdict que M-analyste : tout glisse vers « malade »).
- Recommandations de M-analyste reçues (`out/maladies/analyse/rapport_cycle2.md`) : tirage 50/50 saines/malades dans chaque source, PSFD retiré, poids 1 à 2, augmentation « basse résolution ». Ajoutées au carnet (`sain_source`, `basse_res`).
- Lot 3 prêt (`m12-lot3`, part dès qu'une place GPU se libère) : a5 (PSFD retiré, 50/50 par source, poids 2), a6 (idem, poids 1), a7 (a5 + basse résolution p = 0,3), a8 (a5 + perte par groupe, essai 15).
- Essais comptés : **16** (a1, b1, a2, a3, a4, c1, c2 et leurs 7 réglages de seuils, + réglage t1, + c3 en cours).
## 0 h 35 : v12c fermée (essai 12)

| Tête sur DINOv3 ViT-B figé (seuils v10b) | Tanzanie | TDTU | PSFD | Éthiopie | Coût moyen |
| --- | --- | --- | --- | --- | --- |
| c3 : petit MLP, photo + 4 morceaux | 21,7 ; 30,7 | 47 ; 375 | 173 | 266 ; 12 | 58,26 |
| c4 : logistique, photo + 4 morceaux, PSFD retiré, 50/50 par source, poids 2 | 42,5 ; 38 | 54 ; 317 | 223 | 268 ; 13 | 62,59 |

- Aucun réglage de seuil valide pour c3 ni c4 (essais c3b, c4b). Toutes les têtes v12c ratent 20 à 45 malades tanzaniennes (limite 14) et alertent sur 55 à 75 % des saines de TDTU. **Piste v12c fermée** (règle d'abandon : quatre pertes). [H] Le ViT figé encode surtout la source (M-analyste : 90-100 % d'exactitude sur la source) ; une tête linéaire ne s'en défait pas.
- Correctif : le tirage « 50/50 par source » modifiait un tableau en lecture seule (pandas récent) ; `.copy()` ajouté dans le carnet et dans `m12_entr_tete.py` avant l'envoi du lot 3.
- Lot 3 en attente d'une place GPU (M-banc et C-entraîneur occupent les deux).
- Essais comptés : **20**.
## 0 h 55 : lot 3 en cours, modèle final de a4 lancé

- 0 h 39 : `m12-lot3` parti (a5, a6, a7, a8). 0 h 54 : `m12-final-a4` parti (MODE final : 3 réseaux, départs 0, 1, 2 de la v10b, graines 0, 1, 2, recette a4 sur tout sauf PSFD et la validation). a4 est écrit comme finaliste dans `out/maladies/nuit_1112/kaggle/finalistes.md`.
- Quota GPU à 0 h 51 : 19,24 h utilisées, **10,76 h restantes** (tous agents confondus ; 15,19 h à 22 h 20).
- Pour information (hors règle) : PSFD sans les 123 copies tournées à coins noirs (liste de M-analyste) : v10b 80 / 615 ratées, a4 91 / 615, a1 75 / 615. Le gain de a4 sur PSFD vient des copies tournées ; sur les photos droites il rate 11 feuilles de plus (`scripts/m12_entr_psfd_info.py`).
- `scripts/m12_entr_installer.py` : range un modèle final dans `modeles/maladies_v12_essais/v12<candidat>/` (poids + seuils.json au format de la chaîne), sans rien installer.
- 1 h 05 : arbitrage du chef d'orchestre reçu : une seule place GPU pour moi désormais. m12-lot3 et m12-final-a4 finissent ; ensuite un carnet à la fois (le premier des deux qui finit libère la place de C-entraîneur).
## 1 h 17 : modèle final de v12a4 rangé

- `m12-final-a4` terminé (≈ 22 min de T4). Poids dans `modeles/maladies_v12_essais/v12a4/` (+ `seuils.json` de la v10b, motif changé). Contrôle sur la validation (modèle final, chaîne) : 10 / 2 001 ; 44 / 1 000.
- La place GPU libérée revient à C-entraîneur (arbitrage). Prochain carnet à moi : après m12-lot3.
## 1 h 25 : résultats du lot 3 (recommandations de M-analyste ; essais 14, 15, 3 de M-analyste)

Tous : PSFD jamais appris (lu par le réseau du pli « sans TDTU »), tirage 50/50 saines / malades **dans chaque source**. Tanzanie = moyenne des 2 plis (TDTU, Éthiopie).

| Recette | Seuils | Tanzanie | TDTU | PSFD | Éthiopie | Coût moyen | Finaliste |
| --- | --- | --- | --- | --- | --- | --- | --- |
| a5 : poids 2 | v10b | 10,5 ; 47 | 58 ; 230 | 140 | 250 ; 15 | 48,82 | non (Éthiopie +6,3 pts de ratées) |
| a5 | règle B 0,70 | 6,5 ; 66,5 | 52 ; 262 | 126 | 187 ; 32 | 47,27 | oui |
| a6 : poids 1 | v10b | 14,5 ; 35 | 60 ; 211 | 164 | 297 ; 7 | 52,25 | non ; aucun réglage valide |
| **a7 : poids 2 + basse résolution (p = 0,3)** | v10b | 7,5 ; 42 | 60 ; 215 | 146 | 249 ; 10 | 47,81 | non (Éthiopie +6,2 pts) |
| **a7** | **règle B 0,69** | 7 ; 56,5 | 55 ; 248 | 129 | 184 ; 23 | **45,30** | **oui** |
| a8 : poids 2 + Group-DRO (0,01) | v10b | 9 ; 54 | 60 ; 235 | 149 | 249 ; 16 | 50,31 | non |
| a8 | règle B 0,67 | 6 ; 75,5 | 55 ; 260 | 138 | 191 ; 25 | 47,96 | oui (de justesse) |

- AUC du pays tenu à l'écart : a5 TDTU 0,902 / Éthiopie 0,908 ; a6 0,896 / 0,910 ; **a7 0,901 / 0,917** ; a8 0,892 / 0,912 (v10b 0,897 / 0,879). Le tirage par source et la basse résolution améliorent un peu la séparation en Éthiopie (+0,04) ; TDTU ne bouge pas.
- Lecture : le tirage par source ramène les fausses alertes TDTU de 393 (a1) à 211-235 ; il rend le modèle plus « sain » partout, d'où un seuil règle B plus haut (0,67 à 0,70 au lieu de 0,519). Les seuils réglés sont choisis sur les mêmes plis que ceux qui les mesurent : chiffres optimistes.
- Group-DRO (a8) : pas de gain → fermé. Poids 1 (a6) : rate trop en Éthiopie → la préférence « rater coûte 3 » doit rester dans la perte (poids 2 à 3).
- **Finalistes à ce stade** : v12a4 (seuils v10b, 47,89 ; modèle final prêt) ; **v12a7, règle B 0,69 (45,30)** ; en réserve a5 (règle B 0,70, 47,27).
- 1 h 22 : `m12-lot4` parti (une seule place) : base a7 + (a9) jeux neufs `feuilles-nuit-1112` (essai 16), (a10) morceaux p = 0,3 (essai 17), (a11) deux temps (essai 18), (a12) apprentissage en 384 px (essai 13).
- Essais comptés : **28** (+ a5, a6, a7, a8 et leurs 4 réglages).
## 2 h 15 : résultats du lot 4 (essais 13, 16, 17, 18 ; base a7)

`m12-lot4` : ≈ 50 min de T4 × 2 (a12 en 384 px : 30 min à lui seul). Jeux neufs bien lus (1 405 photos de `feuilles-nuit-1112`, classes ramenées : Cordana / insectes / Moko → « autre », « Black and Yellow Sigatoka » → malade sans nom).

| Recette (base a7) | Seuils | Tanzanie | TDTU | PSFD | Éthiopie | Coût moyen | Finaliste |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **a9 : + jeux neufs du Bangladesh (essai 16)** | v10b | 6 ; 50 | 61 ; 197 | 122 | 208 ; 15 | 42,90 | non (Éthiopie +2,6 pts) |
| **a9** | **règle B 0,65** | 5 ; 57 | 59 ; 217 | 113 | 173 ; 21 | **41,51** | **oui** |
| a10 : + morceaux p = 0,3 (essai 17) | v10b | 8 ; 50 | 62 ; 212 | 138 | 213 ; 14 | 45,50 | non (Éthiopie +3,0) |
| a10 | règle B 0,61 | 6 ; 55,5 | 58 ; 230 | 126 | 172 ; 21 | 43,25 | oui |
| a11 : + deux temps (essai 18) | v10b | 9 ; 38 | 61 ; 213 | 161 | 215 ; 13 | 47,51 | non |
| a11 | règle B 0,60 | 6,5 ; 46 | 57 ; 222 | 146 | 171 ; 24 | 45,07 | oui |
| a12 : apprentissage en 384 px (essai 13) | v10b | 8 ; 47 | 68 ; 195 | 206 | 265 ; 6 | 54,17 | non ; aucun réglage valide → **fermé** |

- AUC du pays tenu à l'écart : **a9 TDTU 0,928 / Éthiopie 0,928** (a7 : 0,901 / 0,917 ; v10b : 0,897 / 0,879) ; a10 0,924 / 0,925 ; a11 0,922 / 0,920 ; a12 0,899 / 0,926. **Les jeux neufs (surtout 882 saines au champ et sur fond noir) sont le premier gain de séparation de la nuit** : la v12 apprend mieux ce qu'est une feuille saine « d'ailleurs ».
- Pour information (hors règle) : PSFD sans copies tournées, a9 et a10 en tête de ligne ci-dessous.
- 2 h 17 : `m12-lot5` parti (base a9) : a13 (+ morceaux), a14 (perte × 3), a15 (+ morceaux + deux temps), a16 (a9 refait avec la graine 1 : mesure du bruit d'une graine à l'autre).
- Essais comptés : **36**.
- PSFD sans copies tournées (information) : v10b 80 / 615, a9 75 / 615, a10 84 / 615.
## 2 h 30 : optimisme du réglage de la règle B (information, aucune règle changée)

`scripts/m12_entr_seuil_croise.py` : pour chaque jeu, seuil choisi sur les 3 autres (sans contraintes), appliqué au jeu laissé de côté. Coût moyen « croisé » : t1 49,75 ; a4 49,82 ; a7 45,70 ; **a9 43,94** ; a10 44,41 ; a11 49,63 (v10b, seuils d'origine : 49,23). Le seuil réglé coûte donc ≈ 2,4 points d'optimisme pour a9 (41,51 → 43,94), mais a9 et a10 restent ≈ 5 points sous la v10b. a4 et a11 ne gardent rien de leur gain après réglage croisé. Seuils choisis pour a9 : 0,50 à 0,75 selon le jeu laissé de côté (instables) ; pour a10 : 0,61 à 0,65 (stables).
## 2 h 52 : résultats du lot 5 (base a9 = a7 + jeux neufs)

| Recette | Seuils v10b : Tanzanie | TDTU | PSFD | Éthiopie | Coût moyen | Finaliste | Règle B réglée | Coût croisé |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| a9 (graine 0) | 6 ; 50 | 61 ; 197 | 122 | 208 ; 15 | 42,90 | non | 0,65 → 41,51 | 43,94 |
| a16 = a9, graine 1 | 9,5 ; 44 | 58 ; 212 | 128 | 183 ; 18 | 42,76 | oui | 0,65 → 41,55 | 43,03 |
| **a13 = a9 + morceaux p = 0,3** | 6 ; 65,5 | 64 ; 201 | 114 | **141** ; 34 | **41,50** | **oui** | 0,50 → 40,73 | **41,94** |
| a14 = a9, perte × 3 | 5 ; 54 | 59 ; 209 | 119 | 194 ; 16 | 42,28 | oui | 0,68 → 41,76 | 44,40 |
| a15 = a13 + deux temps | 5,5 ; 70 | 63 ; 207 | 121 | 149 ; 32 | 42,70 | oui | 0,53 → 42,16 | 45,24 |

- **Bruit d'une graine à l'autre** (a9 contre a16, même recette) : coût moyen 42,90 contre 42,76 ; par jeu jusqu'à 25 malades d'écart en Éthiopie (208 contre 183) et 3,5 en Tanzanie. Un écart de moins d'environ 1 point de coût moyen entre deux recettes n'est pas significatif.
- **a13 est le meilleur candidat** : finaliste **sans réglage de seuil** (seuils de la v10b), coût 41,50 (v10b 49,23), Éthiopie 179 → 141 ratées, PSFD 149 → 114, TDTU 83 → 64 ratées et 177 → 201 fausses alertes, Tanzanie 9 → 6 ratées et 57 → 65,5 fausses alertes. Son seuil réglé (0,50) est presque celui de la v10b (0,519) et stable d'un jeu à l'autre (coût croisé 41,94).
- AUC (pays tenu à l'écart) : a13 0,927 / 0,926 ; a14 0,930 / 0,928 ; a15 0,934 / 0,921 ; a16 0,922 / 0,930.
- 2 h 51 : `m12-final-a13-a14` parti (une place, deux GPU) : modèles finaux (3 réseaux, départs v10b 0-1-2) de a13 et a14, appris sur tout sauf PSFD et la validation.
- Essais comptés : **44**.
## 3 h 20 : modèles finaux de v12a13 et v12a14 rangés ; lot 6 lancé

- `m12-final-a13-a14` (≈ 29 min de T4 × 2). Rangés dans `modeles/maladies_v12_essais/v12a13/` et `v12a14/` (poids + seuils.json de la v10b). Contrôle, validation lue par le modèle final (chaîne) : **v12a13 7 / 2 001 ; 60 / 1 000** ; v12a14 9 / 2 001 ; 48 / 1 000. Les trois finalistes ont leur modèle final ; **les juges ne sont pas lus par moi** (agent Juge).
- 3 h 20 : `m12-lot6` (dernier lot de recettes, avant le gel de 5 h ; base a13) : a17 (perte × 3), a18 (a13, graine 1 : bruit), a19 (5 époques), a20 (lissage 0,1). Si l'un bat a13 de plus d'un point de façon nette, il remplacera v12a14 dans la liste des finalistes (modèle final à entraîner avant 7 h).
## 4 h 10 : lot 6 (dernier lot de recettes) et gel

| Recette (base a13), seuils v10b | Tanzanie | TDTU | PSFD | Éthiopie | Coût moyen | Finaliste | Coût croisé (règle B réglée ailleurs) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| a13 (rappel) | 6 ; 65,5 | 64 ; 201 | 114 | 141 ; 34 | 41,50 | oui | 41,94 |
| a17 : perte × 3 | 4,5 ; 76,5 | 63 ; 197 | 110 | 123 ; 45 | 41,65 | oui | 41,63 |
| a18 : a13, graine 1 | 6 ; 54,5 | 57 ; 211 | 117 | 173 ; 22 | 41,65 | oui | 42,09 |
| a19 : 5 époques | 7,5 ; 61 | 62 ; 203 | 117 | 182 ; 26 | 43,11 | oui | 45,43 |
| a20 : lissage 0,1 | 4 ; 80 | 62 ; 195 | 113 | 143 ; 33 | 41,25 | non (Tanzanie 80 > 77) | 41,47 |

- Aucune variante ne bat a13 de plus d'un point (le bruit d'une graine à l'autre est d'environ 1 point en Éthiopie). a18 confirme a13 (41,65 avec une autre graine). **Les finalistes ne changent pas** : v12a13, v12a14, v12a4 (tous avec modèle final rangé).
- **Gel des recettes** (avant 5 h). Plus aucun carnet de ma part : la place GPU est rendue à C-entraîneur.
- Quota GPU Kaggle à 4 h 10 : 25,32 h utilisées, 4,68 h restantes (tous agents). Mes carnets : extraction DINOv3, lots 1 à 6, deux carnets de modèles finaux, soit environ 5 h de session GPU (estimation par les durées des carnets).

## Bilan des essais (gel à 4 h 10)

**47 essais** : 21 recettes ConvNeXt en validation croisée par pays (a1 à a20, b1), 4 têtes DINOv3 figées (c1 à c4), 22 réglages de la règle B sur le réglage ; + 2 témoins (t1, t3), 4 contrôles « coût croisé » d'information et 3 modèles finaux (non comptés comme essais). Avec 47 essais sur les mêmes jeux de réglage, le meilleur chiffre est optimiste : c'est pourquoi les finalistes gardent les seuils de la v10b.

Ce qui a marché, dans l'ordre d'effet : (1) retirer PSFD (aucune feuille saine, copies tournées sur fond noir) de l'apprentissage et tirer 50/50 saines / malades **dans chaque source**, pour que la source ne dise plus l'étiquette ; (2) **les jeux neufs du Bangladesh** (882 saines étrangères) : AUC TDTU 0,90 → 0,93, Éthiopie 0,92 → 0,93 ; (3) augmentation basse résolution et morceaux (Éthiopie). Ce qui n'a pas marché : augmentations fortes + CutMix (b1), poids de perte 1, Group-DRO, deux temps, 384 px à l'apprentissage, 5 époques, têtes sur DINOv3 figé.

## Ce qu'il faudrait changer dans la chaîne si un finaliste passe les juges (proposé, rien n'est appliqué)

- `config.yaml` : `maladies.modele: modeles/maladies_v12_essais/v12a13` (ou le finaliste retenu). Même réseau (timm `convnext_tiny.dinov3_lvd1689m`), même préparation (384 px, JPEG lu en 896 px, 4 vues), mêmes seuils que la v10b : `fieldscan/modules/maladies.py` n'a pas à changer. Aiguilleur et branche « loin » (v2) inchangés.
- Retour arrière : `maladies.modele: modeles/maladies_binome/v10b`.
- Temps de calcul identique à la v10b (3 ConvNeXt-Tiny, ≈ 1,8 s par photo sur ce PC).
- Limites à écrire : PSFD n'a jamais été appris ; TDTU garde ≈ 35 % de saines en alerte (images du web, plantes entières) ; le Xanthomonas d'Éthiopie reste la première source de malades ratées ; les jeux neufs sont du Bangladesh, comme le test vierge AgroVisionBD (source, région et appareil différents, aucun recouvrement vérifié par D-maladies).
