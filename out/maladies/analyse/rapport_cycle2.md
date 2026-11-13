# Analyse d'erreurs des maladies, cycle 2 (agent M-analyste, nuit du 12 au 13 novembre 2026)

Périmètre : **réglage seulement** (validation Tanzanie 2022-2023 : 2 001 malades et 1 000 saines ; TDTU : 1 059 et 577 ; PSFD : 738 malades ; Éthiopie : 1 134 et 155). Aucun fichier des juges (BanSpot, Cordana du Pérou) ni du test vierge (AgroVisionBD) n'a été ouvert. Aucun réseau lancé : tout vient des probabilités en cache. Chaînes analysées : **installée** (aiguilleur, v10b en proche, v2 en loin ; coût moyen 49,23) et **F1** de M-banc (mélange géométrique v10b + soupe + v2, v10b lue entière + 2 × 2, seuil 0,70, loin « v2 ou proche » ; coût 35,96), avec F3 (même mélange sans morceaux, 37,83). Décisions recalculées avec les fonctions de M-banc et `decider_convnext` de la chaîne : chiffres publiés retrouvés exactement.

Étiquettes : [O] observé sur une planche nommée, [M] mesuré (script et fichier cités), [H] hypothèse. Journal : `docs/nuit_2026-11-12/journal_m_analyste.md`.

## 1. Essais recommandés, classés par gain attendu

Les gains sont des estimations tirées du réglage ; ce ne sont pas des résultats. Chaque essai a son critère, écrit ici avant tout calcul.

| # | Pour | Essai | Pourquoi (chiffres) | Gain attendu | Critère (écrit avant) |
| --- | --- | --- | --- | --- | --- |
| 1 | M-entraîneur | **Tirage « source indépendante de l'étiquette »** (confirmé en partie par le lot 2 : a4, sans PSFD, ramène la P(malade) médiane des saines TDTU de 0,93 à 0,59 ; le tirage « moitié saines » sur l'ensemble de a3 ne fait rien ; voir section 7) : dans chaque source, poids saines = poids malades (50 / 50) ; **PSFD retiré de l'apprentissage** (aucune saine, 188 groupes réels pour 738 photos, 17 % de copies tournées sur fond noir) ; poids de la perte 3 gardé. À comparer à a3 / a4 du lot 2, qui n'équilibrent pas source par source. | [M] Saines TDTU lues par le pli sans TDTU : P(malade) médiane a1 0,94, c1 0,997, c2 0,994, contre 0,18 pour la v10b. Le même c1, sur l'Éthiopie (pli qui a appris les 577 saines de TDTU), ne met que 13 / 155 saines en alerte (v10b 43). Dans le pli sans TDTU, les saines ne font que 11 % des photos étrangères ; dans le pli sans Éthiopie, 24 %. | TDTU : saines en alerte (seuil B) de 486 / 577 (a1) vers le niveau de la v10b (199) ou mieux, en gardant les ratées de a1 (4 / 1 059 au seuil B). Si c'est atteint, coût TDTU 81 → 35 à 45, soit −10 points de coût moyen pour la v12 seule. | Pli sans TDTU : P(malade) médiane des saines TDTU ≤ 0,30 et AUC TDTU ≥ 0,90 (a1 : 0,882) ; sinon la piste est close. |
| 2 | M-banc (un passage Kaggle d'environ 10 min de T4) | **v10b lue en 224 px** (taille d'apprentissage), puis en « taille adaptée » `min(384, 2 × côté court)`, dans le mélange F3 / F1 ; seuil réglé comme d'habitude. | [M] Plus la photo est agrandie, plus la v10b perd : AUC 384 → 512 px, validation 0,995 → 0,992, TDTU 0,897 → 0,863, **Éthiopie 0,879 → 0,799** (photos de 150 × 113, agrandies 2,6 fois à 384). La soupe et la v2, lues à 224 px, font 0,944 et 0,936 en Éthiopie. [O] `ratees_F1_ethiopie.jpg` : ratées floues, sans lésion visible. | Éthiopie est le jeu le plus coûteux de F1 (49,0). [H] Si l'AUC de la v10b en Éthiopie remonte vers 0,93, de 1 à 3 points de coût moyen. Ne change presque rien en validation. | Finaliste si la règle du plan est remplie et AUC v10b Éthiopie (224) ≥ 0,90 ; sinon fermé. |
| 3 | M-entraîneur | **Augmentation « basse résolution »** dans v12b ou suivantes : réduire la photo à 100 à 160 px de côté court puis la ré-agrandir (p = 0,3), en plus des augmentations prévues. | [M] Éthiopie : 13,5 % de ratées en gros plan (F1). Elles se concentrent dans le quartile le moins net (F1 : 19,0 % de ratées contre 2,8 % dans le plus net) et le moins taché (29,9 % contre 0 %). Leur fichier pèse 0,275 octet par pixel, contre 0,325 pour les malades vues. | [H] Éthiopie : ratées du pli de 112 (a1) vers moins de 90, sans fausse alerte en plus. | AUC du pli sans Éthiopie ≥ 0,92 (a1 : 0,883) ; sinon fermé. |
| 4 | M-banc (aucun calcul de réseau) | **Ne pas lancer la lecture 3 × 3 sur tous les jeux** (`m12-banc-g3`) : la place GPU va à M-entraîneur (essais 1 et 3). | [M] Sur l'échantillon de 400, les morceaux ne séparent pas mieux saines et malades. AUC entière / 2 × 2 / 3 × 3 : TDTU 0,908 / 0,903 / 0,905 ; Éthiopie 0,862 / 0,845 / 0,853. F1 et F3 ont la même AUC (TDTU 0,938 et 0,938 ; Éthiopie 0,939 et 0,938). Le gain des morceaux (1,9 point) vient donc d'un déplacement des probabilités, réglé après 912 essais. | Environ 50 min de T4 libérées. Perte attendue : nulle ou faible. | Si le 3 × 3 est lancé quand même, il n'est retenu que si l'AUC monte d'au moins 0,01 sur TDTU ou sur l'Éthiopie. |
| 5 | M-banc et Contrôleur (mesure) | **Coût PSFD compté aussi sans les copies tournées et par groupe de quasi-copies**, à côté du compte officiel. Aucun candidat n'est préféré grâce aux seules copies tournées. Liste : `out/maladies/analyse/psfd_copies.csv`. | [M] 123 / 738 photos PSFD sont des copies tournées sur fond noir. Elles font 53 des 102 ratées de F1 (taux 43 %, contre 8 % sur les photos droites) et 69 des 149 de l'installée. Les groupes de quasi-copies (DINOv3, cosinus ≥ 0,95) sont 188 pour 738 photos ; [O] `psfd_groupes_quasi_copies.jpg` : copies retouchées de la même photo. | Aucun sur le module. Tous les coûts moyens baissent d'environ 4,4 points sans les copies tournées (installée 43,84 ; F1 31,57). Le classement F1 < F2 < F3 < réserve tient dans les 3 comptes. | Écart de classement entre les comptes signalé au Contrôleur. |
| 6 | M-entraîneur (après l'essai 1) | **Saines étrangères en plus** : les 848 + 34 saines de `feuilles-nuit-1112` (Bangladesh), seulement si PSFD est retiré. | Même mécanisme que l'essai 1. [H] Le fond noir de studio de `5nfjzntwd8` rappelle les copies tournées de PSFD (malades, coins noirs) : avec PSFD dans l'apprentissage, le réseau pourrait apprendre « fond noir ». | Complète l'essai 1 (pli sans TDTU). | Même critère que l'essai 1. |

Ce qu'il ne faut plus essayer (mesuré, `scripts/m12_analyse_pistes.py`, chiffrage seul) :
- **Autres décisions autour de F1.**
  - « F1 ou v10b sûre » (P(saine) v10b < 0,10 à 0,30) : au mieux 35,89, soit −0,07 point.
  - « v2 seule en loin si p_loin ≥ 0,7 à 0,99 » : de 37,29 à 40,92, pire que F1.
  - Les poids du mélange échangent TDTU contre l'Éthiopie. AUC du lecteur proche : (1, 1, 1) 0,957 / 0,931 ; (1, 2, 1) 0,954 / 0,936 ; (2, 1, 1) 0,959 / 0,921.
- **Mélanger les v12 actuelles à F1** : l'AUC ne monte nulle part, au mieux +0,004 (c1, Éthiopie, poids 0,25), et TDTU tombe de 0,938 à 0,916 (`v12_diagnostic.csv`).
- **Faire baisser les fausses alertes de la validation**. [O] `fa_F1_validation.jpg` : sur les 24 saines en alerte les plus basses en P(saine), environ 20 portent des stries brunes de Sigatoka débutante, ce qui rejoint l'audit du binôme sur HEALTHY-1. Les faire passer « saines » apprendrait à rater la Sigatoka légère.

## 2. Les trois constats les plus importants

1. **Les ratées qui restent ne sont pas un problème de seuil, mais de ce que montre la photo.**
   - [M] F1 rate 238 malades sur le réglage, toutes à moins de 0,30 au-dessus du seuil (Éthiopie : 106 / 117 à moins de 0,15). Les seuils ne les rattraperont pas sans fausses alertes : AUC 0,938 (TDTU) et 0,939 (Éthiopie).
   - [M] Elles sont concentrées sur deux classes : Sigatoka jaune de PSFD (65 / 264, 24,6 %) et Xanthomonas d'Éthiopie (114 / 814, 14,0 %). Elles portent peu de jaune ou de brun : dans le quartile le moins taché, 30,3 % de ratées en PSFD et 29,9 % en Éthiopie, contre 3,8 % et 0 % dans le plus taché.
   - [O] `ratees_F1_ethiopie.jpg`, `ratees_F1_tdtu.jpg` : feuilles entières au champ, sans lésion visible à 150 à 256 px. C'est ce que le binôme décrivait.
   - [O] Par contraste, `vues_F1_psfd_temoin.jpg` : les malades que F1 voit portent des nécroses jaunes ou brunes nettes, souvent en bord de feuille.
   - [H] Le Xanthomonas est une maladie de plante (flétrissement) : l'étiquette ne se voit pas toujours sur la feuille photographiée.
2. **PSFD est un jeu augmenté, et un quart du coût moyen repose dessus.**
   - [M] Ses 738 photos font 188 groupes de quasi-copies.
   - [M] 123 photos sont des copies tournées à 45° sur fond noir. Elles concentrent les ratées : 43 % pour F1, contre 8 % sur les photos droites ; 56 % contre 13 % pour l'installée.
   - [O] `ratees_F1_psfd.jpg` : les ratées sont surtout ces copies tournées et des miroirs de la même feuille, sans tache visible.
   - Une chaîne de terrain ne verra jamais ces coins noirs.
3. **Le raccourci « pays = malade » est réel pour les v12. La v10b a aussi un décalage de style.**
   - [M] La source se lit dans les caractéristiques DINOv3 : 90 à 100 % d'exactitude, 89 à 99 % sur les saines seules.
   - [M] Les v12 mettent en alerte 77 à 90 % des saines du pays tenu à l'écart quand leur apprentissage manque de saines étrangères (pli sans TDTU). Elles n'en mettent que 8 à 10 % quand il en a (pli sans Éthiopie : c1, c2).
   - [M] La v10b, elle, alerte sur les saines TDTU qui ne « ressemblent » pas à la Tanzanie : 58 % contre 10 % pour la moitié « tanzanienne » (Spearman +0,56).
   - [O] `fa_F1_tdtu_loin.jpg`, `fa_F1_tdtu_proche.jpg` : ces saines sont des images du web (filigranes alamy et shutterstock, plantes en pot, bananier ornemental rouge, une diapositive « Banana Bunchy Top Disease Overview » rangée saine), des plantes entières, des bords jaunis ou déchirés.
   - [O] `saines_sans_alerte_tdtu.jpg` : les saines sans alerte sont surtout des feuilles détourées sur fond blanc.
   - [M] Fausses alertes de l'installée : 45 à 55 % sur la moitié des saines TDTU la moins « grise » (photos au champ), 10 à 12 % sur l'autre moitié (fond blanc).

## 3. Malades ratées

Source : `scripts/m12_analyse_erreurs.py` → `resume_erreurs.txt` ; planches dans `planches/`.

### 3.1 Par pays et par classe [M]

| Jeu, classe | Installée | F3 | F1 |
| --- | --- | --- | --- |
| Validation, Sigatoka noire | 4 / 1 000 | 1 | 0 |
| Validation, fusariose | 5 / 1 001 | 1 | 0 |
| TDTU, autre maladie | 58 / 655 (8,9 %) | 18 | 12 |
| TDTU, Sigatoka noire | 25 / 404 (6,2 %) | 10 | 7 |
| PSFD, Sigatoka noire | 60 / 474 (12,7 %) | 40 | 37 (7,8 %) |
| PSFD, Sigatoka jaune | 89 / 264 (33,7 %) | 69 | **65 (24,6 %)** |
| Éthiopie, « sigatoka » | 15 / 320 | 3 | 3 |
| Éthiopie, Xanthomonas | 164 / 814 (20,1 %) | 131 | **114 (14,0 %)** |

### 3.2 Par cadrage (p_loin de l'aiguilleur) [M]

| Jeu | Gros plan (< 0,1) : installée → F1 | 0,1 à 0,5 | Loin (≥ 0,5) |
| --- | --- | --- | --- |
| TDTU | 35 / 628 → 14 | 5 / 125 → 2 | **43 / 306 → 3** |
| PSFD | 44 / 397 → 39 | 39 / 130 → 26 | 66 / 211 → 37 |
| Éthiopie | **132 / 802 → 108** | 9 / 143 → 6 | 38 / 189 → 3 |

- Ce que la branche loin « v2 ou proche » répare : 40 des 66 malades de TDTU rattrapées par F1 sont des photos loin. Avant F1, la v2 seule les disait saines, avec une P(saine) médiane de 0,82.
- Ce qui reste : surtout des **gros plans** en Éthiopie, et les cadrages intermédiaires de PSFD (32 % de ratées entre 0,3 et 0,5). Ce sont surtout des copies tournées : l'aiguilleur ne sait pas où les ranger.

### 3.3 Profil de probabilité : presque en alerte, ou franchement « saines » ? [M]

Marge = P(saine) du lecteur qui décide moins le seuil (en loin, pour F1 : la plus petite des deux marges).

| Jeu | Installée : < 0,05 / 0,05-0,15 / 0,15-0,30 / ≥ 0,30 | F1 : mêmes classes |
| --- | --- | --- |
| TDTU | 18 / 29 / 25 / 11 | 5 / 12 / 2 / 0 |
| PSFD | 17 / 37 / 58 / 37 | 16 / 46 / 40 / 0 |
| Éthiopie | 18 / 59 / 66 / 36 | 31 / 75 / 11 / 0 |

- Pour l'installée, 85 ratées sont franchement « saines » (marge ≥ 0,30). F1 n'en a plus aucune.
- Plafond théorique (`pistes_bilan.json`) :
  - si toutes les ratées de F1 à moins de 0,05 étaient rattrapées sans fausse alerte, le coût moyen tomberait à 31,93 ;
  - à moins de 0,10 : 25,85.

  Ce gain demande un lecteur qui sépare mieux (une AUC plus haute), pas un autre seuil.

### 3.4 Taille, qualité, gravité visible [M]

Médianes des malades ratées contre vues (installée) :
- **Éthiopie** :
  - netteté (variance du laplacien) 1 610 contre 2 450 ;
  - fichier 0,278 contre 0,325 octet par pixel ;
  - part jaune + brun 0,106 contre 0,295 ;
  - part de vert 0,74 contre 0,51.
- **PSFD** :
  - luminosité 51 contre 125, à cause des coins noirs des copies tournées ;
  - part jaune + brun 0,021 contre 0,042.
- **TDTU** :
  - p_loin médian 0,57 contre 0,02 : les ratées de l'installée sont surtout des photos loin ;
  - part jaune + brun 0,118 contre 0,258.

Qualité JPEG estimée : 75 dans tous les pays (photos recompressées), 92 en validation ; aucun écart entre ratées et vues.

Gravité visible, mesurée par la part de pixels jaunes ou bruns, en quartiles dans chaque jeu. Taux de ratées du quartile le moins taché au plus taché :

| Jeu | Installée | F1 |
| --- | --- | --- |
| TDTU | 15,5 / 9,8 / 4,5 / 1,5 % | 4,9 / 2,3 / 0 / 0 % |
| PSFD | 34,6 / 26,1 / 9,8 / 10,3 % | 30,3 / 17,4 / 3,8 / 3,8 % |
| Éthiopie | 38,7 / 15,5 / 7,1 / 1,8 % | 29,9 / 9,5 / 1,8 / 0 % |

Limite : cette mesure confond les taches avec la terre et les feuilles mortes du fond.

## 4. Fausses alertes sur saines

### 4.1 Réponses données [M]

| Jeu | Installée : à vérifier / Sigatoka / fusariose / non identifiée | F1 : mêmes réponses |
| --- | --- | --- |
| Validation (57 → 62) | 25 / 20 / 1 / 11 | 53 / 4 / 0 / 5 |
| TDTU (177 → 241) | 38 / 24 / 18 / 97 | 143 / 1 / 21 / 76 |
| Éthiopie (43 → 28) | 18 / 15 / 0 / 10 | 28 / 0 / 0 / 0 |

Avec F1, les fausses alertes deviennent surtout « à vérifier » (alerte de confiance faible) : 224 sur 331. Une maladie n'est presque plus nommée à tort.

### 4.2 Par pays et par cadrage [M]

- **TDTU** (F1) :
  - gros plan 107 / 338 (32 %) ;
  - loin **107 / 167 (64 %)**, contre 71 avec la v2 seule.
  - La branche loin « v2 ou proche » coûte donc 36 fausses alertes en TDTU loin, pour 40 malades rattrapées.
  - [O] `fa_F1_tdtu_loin.jpg` : plantes entières, plantations, plantes en pot. Sur ces photos, la v10b donne souvent P(saine) entre 0,03 et 0,06.
  - [H] La v10b n'a jamais vu de plante entière saine.
- **Éthiopie** (F1) : 28 / 155, toutes « à vérifier », avec une P(saine) du mélange entre 0,52 et 0,69.
  - [O] `fa_F1_ethiopie.jpg` contre `ratees_F1_ethiopie.jpg` : à 150 × 113 px, rien ne distingue à l'œil ces saines des Xanthomonas ratées.
- **Validation** (F1) : 62 / 1 000. [O] Une grande part porte des stries de Sigatoka (section 1) : ces alertes sont probablement justes.

### 4.3 Sénescence, déchirures, poussière [M] [O]

- **TDTU** :
  - [M] Taux de fausses alertes de l'installée du quartile le moins jaune ou brun au plus jaune ou brun : 5,5 / 13,2 / 43,1 / 61,1 % ; F1 : 9,0 / 27,8 / 53,5 / 77,1 %.
  - [M] Selon la part sombre : 4,8 → 52,8 %.
  - [O] `fa_F1_tdtu_proche.jpg` : bords jaunis ou brûlés, pointes sèches, feuilles déchirées, terre et feuilles mortes au fond.
- **Éthiopie** : quartiles jaune + brun, installée : 5,1 / 30,8 / 36,8 / 38,5 %.
- **Validation** : aucun effet net (6,8 / 6,4 / 2,8 / 6,8 %).
- Poussière : rien n'est visible sur les planches. Aucune mesure n'a été faite.

## 5. Le raccourci « pays = malade »

Source : `scripts/m12_analyse_raccourci.py` → `raccourci_pmalade_par_source.csv`, `raccourci_sortie.txt`. Les v12 sont lues dans le pli qui n'a pas appris le pays.

P(malade) médiane des saines (part ≥ 0,5) [M] :

| Modèle | Validation | TDTU | Éthiopie |
| --- | --- | --- | --- |
| v10b | 0,09 (5,5 %) | 0,18 (34 %) | 0,30 (32 %) |
| soupe | 0,08 (2,4 %) | 0,18 (19 %) | 0,09 (1,9 %) |
| v2 | 0,07 (0,9 %) | 0,14 (18 %) | 0,08 (1,3 %) |
| lecteur F1 | 0,12 (2,5 %) | 0,24 (23 %) | 0,21 (1,3 %) |
| a1 (v12a) | 0,06 (13 %) | **0,94 (83 %)** | 0,51 (51 %) |
| c1 (tête DINOv3) | 0,01 (5,5 %) | **0,997 (90 %)** | 0,008 (7,7 %) |
| c2 (tête DINOv3) | 0,001 (2,5 %) | **0,994 (77 %)** | 0,003 (10 %) |

**Lecture** :
- [M] Le style de la source est lisible : un classifieur logistique de la source, appris sur 128 composantes DINOv3, a une exactitude de 90 à 100 % sur 20 % tenus à part.
- [M] Le pli sans TDTU n'a comme saines étrangères que 155 photos d'Éthiopie et 107 de Mendeley : 11 % des photos étrangères. PSFD, qui n'a aucune saine, en fait 30 %.
- [M] Le tirage du carnet équilibre les classes **dans** chaque pays. PSFD (100 % malades) reste donc tout malade, et l'Éthiopie à 67 % malade.
- [M] Un pays inconnu y est presque toujours malade, d'où des fausses alertes en bloc sur TDTU. La corrélation de rang entre « ressemble à PSFD ou à l'Éthiopie » et P(malade) n'est que de +0,15 à +0,29 pour a1 et c2 (c1 : −0,25). Ce n'est donc pas un raccourci gradué sur le style : c'est un décalage global de ce qui est « hors Tanzanie ».
- [M] Le pli sans Éthiopie a appris les 577 saines de TDTU. Il ne fait pas cette erreur sur l'Éthiopie : c1 et c2 y sont meilleurs que la v10b.
- [H] Ces mesures pointent le **déséquilibre des saines entre sources** plutôt que PSFD seul. D'où l'essai 1 : 50 / 50 dans chaque source, PSFD retiré.

## 6. Accord et désaccord : v10b, soupe, v2 ; où le mélange gagne

Malades rattrapées par F1 / perdues par F1 par rapport à l'installée ; saines : fausses alertes ajoutées / retirées [M] :

| Jeu | Rattrapées (dont loin) | Perdues | Fausses alertes ajoutées (dont loin) | Fausses alertes retirées |
| --- | --- | --- | --- | --- |
| Validation | 9 (1) | 0 | 21 (0) | 16 |
| TDTU | 66 (40) | 2 | 81 (36) | 17 |
| PSFD | 53 (29) | 6 | | |
| Éthiopie | 89 (35) | **27** | 7 (3) | 22 |

- **Où le mélange gagne** :
  - [M] Il sépare mieux. AUC de la v10b, puis du lecteur F1 : TDTU 0,897 → 0,938, Éthiopie 0,879 → 0,939.
  - [M] Dans les malades rattrapées en Éthiopie, la v10b alerte seule dans 32 cas (photos loin, où l'installée ne lisait que la v2), la soupe et la v2 sans la v10b dans 17 cas, la v2 seule dans 13, et aucun modèle seul dans 21.
  - [M] La règle loin « v2 ou proche » rattrape aussi beaucoup de malades : 40 en TDTU, 29 en PSFD, 35 en Éthiopie.
- **Où il perd** :
  - [M] 27 Xanthomonas d'Éthiopie que seule la v10b voyait. [O] `perdues_F1_ethiopie.jpg` : P(saine) v10b entre 0,27 et 0,52, mélange entre 0,70 et 0,82.
  - Les rattraper par « F1 ou v10b sûre » coûte autant de fausses alertes (section 1).
- **Malades qu'aucun des trois modèles seuls ne voit** [M] :
  - validation 2 ;
  - TDTU 29 ;
  - **PSFD 113** ;
  - **Éthiopie 109**.

  F1 en rattrape 41 % en TDTU, 15 % en PSFD et 19 % en Éthiopie ; les autres restent ratées par F1 (17, 96 et 88). Aucun mélange de ces trois modèles ne peut les rattraper : il faut un nouveau modèle ou de nouvelles données.

## 7. Candidats v12

`scripts/m12_analyse_v12.py` → `v12_diagnostic.csv`. À relancer sur chaque nouveau candidat :

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_analyse_v12.py <candidat> ...
```

État à 0 h 08 (a1, c1, c2, t1 ; le lot 2 n'est pas encore arrivé) :

| Candidat | AUC TDTU | AUC Éthiopie | Saines TDTU en alerte (seuil B) | PSFD : ratées tournées / droites |
| --- | --- | --- | --- | --- |
| t1 (réseau 0 de la v10b) | 0,894 | 0,886 | 195 / 577 | 72 % / 10 % |
| a1 | 0,882 | 0,883 | 486 / 577 | 51 % / 9 % |
| c1 | 0,764 | 0,917 | 520 / 577 | 29 % / 15 % |
| c2 | 0,869 | 0,894 | 444 / 577 | 26 % / 20 % |

Pour mémoire, le lecteur F1 fait 0,938 en TDTU et 0,939 en Éthiopie. Aucune v12 ne sépare mieux, ni seule, ni en mélange avec F1 (au mieux +0,004).

**Mise à jour à 0 h 20 : lot 2 (`kaggle/lot2/`) et c3 partiel** [M]

Recettes (fichiers `recette_*.json`) :
- a2 = a1 avec un poids de perte de 1 ;
- a3 = a1 avec la moitié du tirage en saines, sur l'ensemble (option `sain50`) ;
- a4 = a3 avec PSFD jamais appris ;
- b1 = augmentations fortes, CutMix de fonds sains, lissage.

| Candidat | AUC TDTU / Éthiopie | Saines TDTU : P(malade) médiane (part ≥ 0,5) | Saines TDTU en alerte (seuil B) | Éthiopie : ratées ; saines en alerte | Validation : saines en alerte | PSFD : ratées tournées / droites |
| --- | --- | --- | --- | --- | --- | --- |
| a1 | 0,882 / 0,883 | 0,94 (83 %) | 486 | 75 ; 83 | 137 | 51 % / 9 % |
| a2 (poids 1) | 0,903 / 0,904 | 0,81 (68 %) | 399 | 174 ; 31 | 72 | 66 % / 11 % |
| a3 (moitié saines, ensemble) | 0,882 / 0,880 | 0,93 (75 %) | 437 | 272 ; 26 | 76 | 59 % / 11 % |
| **a4 (a3 + PSFD retiré)** | 0,896 / **0,918** | **0,59 (54 %)** | **315** | 142 ; 34 | 44 | 46 % / 13 % |
| b1 (augmentations fortes) | 0,904 / 0,886 | 0,85 (80 %) | 470 | **43** ; 101 | **255** | 45 % / 4 % |
| c3 (tête DINOv3, partiel) | 0,799 / – | 1,00 (79 %) | 455 | – | 30 | 46 % / 13 % |

**Lecture** :
- **Retirer PSFD est le levier le plus fort contre le raccourci.** De a3 à a4, la P(malade) médiane des saines TDTU passe de 0,93 à 0,59.
- **Imposer la moitié de saines sur l'ensemble ne sert à rien** : a3 est au niveau de a1, et non meilleur.
- **Le poids 1 aide un peu** (a2 : 0,81).
- Cela confirme l'essai 1 tel qu'il est écrit : **50 / 50 dans chaque source, PSFD retiré**, avec en plus un poids de perte de 1 à 2 (a2 + a4).
- b1 déplace tout vers « malade » sans mieux séparer :
  - AUC Éthiopie 0,886 ;
  - validation 255 / 1 000 saines en alerte ;
  - ses 43 ratées en Éthiopie et 81 en PSFD sont payées en fausses alertes.
- Aucun candidat du lot 2 n'apporte d'AUC au lecteur F1 en mélange : au mieux a2 en TDTU, 0,938 → 0,940.
- a4 est le meilleur réseau seul en Éthiopie (0,918 contre 0,879 pour la v10b) et le seul à baisser les fausses alertes de validation (44).

## 8. Fichiers

- Scripts (lecture seule de l'existant) :
  - `scripts/m12_analyse_table.py` ;
  - `scripts/m12_analyse_erreurs.py` ;
  - `scripts/m12_analyse_planches.py` ;
  - `scripts/m12_analyse_psfd_copies.py` ;
  - `scripts/m12_analyse_raccourci.py` ;
  - `scripts/m12_analyse_pistes.py` ;
  - `scripts/m12_analyse_v12.py`.
- Sorties dans `out/maladies/analyse/` :
  - `table_reglage.csv` (une ligne par photo de réglage) ;
  - `resume_erreurs.txt` ;
  - `psfd_copies.csv` et `copies_bilan.json` ;
  - `raccourci_*` ;
  - `pistes_bilan.json` ;
  - `v12_diagnostic.csv`.
- Planches (`planches/`) :
  - malades ratées : `ratees_F1_psfd`, `ratees_F1_ethiopie`, `ratees_F1_tdtu`, `ratees_installee_validation` ;
  - malades rattrapées ou perdues par F1 : `rattrapees_F1_tdtu`, `rattrapees_F1_ethiopie`, `perdues_F1_ethiopie` ;
  - fausses alertes : `fa_F1_tdtu_loin`, `fa_F1_tdtu_proche`, `fa_F1_nouvelles_tdtu`, `fa_F1_ethiopie`, `fa_F1_validation` ;
  - saines sans alerte : `saines_sans_alerte_tdtu`, `saines_sans_alerte_ethiopie` ;
  - témoins de malades vues : `vues_F1_psfd_temoin`, `vues_F1_ethiopie_xantho_temoin` ;
  - copies de PSFD : `psfd_groupes_quasi_copies`.

**Limites** :
- La « gravité visible » n'est qu'un substitut colorimétrique : la terre et les feuilles mortes du fond comptent comme taches.
- Les groupes de quasi-copies dépendent du seuil (0,90 : 48 groupes ; 0,95 : 188).
- Les observations [O] sont des lectures à l'œil de planches tirées au hasard (graine 0), sans compte exhaustif.
