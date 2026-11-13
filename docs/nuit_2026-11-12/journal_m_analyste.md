# Journal de l'agent M-analyste (nuit du 12 au 13 novembre 2026)

Rôle (`docs/plan_nuit_10h.md`, section 2) : analyste d'erreurs des maladies. Quelles photos la chaîne installée et le meilleur candidat de M-banc ratent ou mettent en fausse alerte, et pourquoi. **Réglage seulement** : validation Tanzanie 2022-2023 (3 001), TDTU, PSFD, Éthiopie. Jamais BanSpot, la Cordana du Pérou ni AgroVisionBD (aucun fichier ouvert). Probabilités en cache seulement, aucun réseau lancé, 2 cœurs au plus. Étiquettes : [O] observé, [M] mesuré, [H] hypothèse.

Écrit dans : `out/maladies/analyse/`, `scripts/m12_analyse_*.py`, ce journal.

## 23 h 40 : lecture

- Lus : CLAUDE.md, plan 10 h, plan de nuit (sections 2 et 4), protocole v10b (section 7), journaux M-banc et M-entraînement, BILAN de D-maladies, récap du binôme (partie 1), `fieldscan/modules/maladies.py` (`decider_convnext`), `scripts/m12_banc_commun.py`, `scripts/m12_banc_finalistes.py`, `out/maladies/nuit_1112/banc/finalistes.md`.
- Références retenues : chaîne installée (coût moyen 49,23) et **F1** de M-banc (mélange géométrique v10b + soupe + v2, v10b lue entière + 2 × 2, seuil 0,70, loin « v2 ou proche » : 35,96), avec F3 (même mélange sans morceaux : 37,83). Je réutilise les fonctions de M-banc par import (lecture seule), pour avoir exactement leurs décisions.

## 23 h 55 : table par photo (A-1)

- `scripts/m12_analyse_table.py` → `out/maladies/analyse/table_reglage.csv` (6 664 photos de réglage) : probabilités en cache, réponses de la chaîne installée et de F1 / F2 / F3 / réserve (fonctions de M-banc importées), réponses de chaque modèle seul, mesures d'image (taille, octets par pixel, qualité JPEG estimée, netteté, luminosité, parts de vert / jaune / brun / sombre / gris). Contrôle : chiffres de la chaîne installée (9 ; 57 / 83 ; 177 / 149 / 179 ; 43) et de F1 (0 ; 62 / 19 ; 241 / 102 / 117 ; 28) retrouvés exactement [M].

## 23 h 58 : erreurs, accord, planches (A-2 à A-4)

- `scripts/m12_analyse_erreurs.py` → `resume_erreurs.txt` ; `scripts/m12_analyse_planches.py` → `planches/*.jpg` (16 planches).
- [M] F1 rate surtout la Sigatoka jaune de PSFD (65 / 264) et le Xanthomonas d'Éthiopie (114 / 814) ; aucune ratée de F1 n'est « franche » (marge de P(saine) au-dessus du seuil < 0,30 partout ; Éthiopie : 106 / 117 à moins de 0,15).
- [M] Ratées concentrées sur les photos à peu de jaune / brun : Éthiopie, quartile le moins taché 29,9 % de ratées (F1) contre 0 % pour le plus taché ; PSFD 30,3 % contre 3,8 %.
- [O] PSFD, planche `ratees_F1_psfd.jpg` : une grande part des ratées sont des **copies tournées à 45° sur fond noir** et des miroirs de la même feuille ; feuilles sans tache visible à 256 px.
- [M] `scripts/m12_analyse_psfd_copies.py` : 123 / 738 photos PSFD ont 4 coins noirs (tournées) ; elles font 53 des 102 ratées de F1 (taux 43 % contre 8 % pour les photos droites ; installée 56 % contre 13 %). Groupes de quasi-copies (DINOv3, cosinus ≥ 0,95) : PSFD 188 groupes pour 738 photos (jeu augmenté), contre 1 615 / 1 636 en TDTU et 1 255 / 1 289 en Éthiopie.
- [O] TDTU, saines en alerte (`fa_F1_tdtu_loin.jpg`, `fa_F1_tdtu_proche.jpg`) : images du web (filigranes alamy / shutterstock, plantes en pot, bananier ornemental rouge, diapositive « Banana Bunchy Top Disease Overview » rangée saine), plantes entières et plantations ; en proche, bords jaunis ou bruns, feuilles déchirées. Les saines sans alerte (`saines_sans_alerte_tdtu.jpg`) sont surtout des feuilles détourées sur fond blanc.
- [M] TDTU saines : fausses alertes de l'installée 45 à 55 % sur la moitié la moins « grise » (photos au champ) contre 10 à 12 % sur la moitié à fond blanc.
- [O] Éthiopie, ratées (`ratees_F1_ethiopie.jpg`) : feuilles entières au champ, 150 × 113 px, aucune lésion visible à cette taille (Xanthomonas : symptôme de plante, flétrissement, jaunissement).

## 0 h 05 : raccourci « pays = malade », séparabilité, lecture agrandie (A-5 à A-8)

- `scripts/m12_analyse_raccourci.py` → `raccourci_pmalade_par_source.csv`, `raccourci_sortie.txt`, `raccourci_bilan.json`. (Premier lancement arrêté : torch à 2 fils trop lent sur la machine saturée ; relancé sur 1 fil après réduction à 128 composantes principales.)
  - [M] La source se lit dans DINOv3 : classifieur logistique, 20 % tenus à part, exactitude 90 à 100 % par source ; sur les saines seules 89 à 99 %.
  - [M] Saines TDTU lues par le pli « sans TDTU » : P(malade) médiane a1 0,94, c1 0,997, c2 0,994 (v10b 0,18). Saines d'Éthiopie lues par le pli « sans Éthiopie » : c1 0,008, c2 0,003, a1 0,51 (v10b 0,30). Le pli sans TDTU n'a comme saines étrangères que 155 photos d'Éthiopie + 107 Mendeley (11 % des photos étrangères), le pli sans Éthiopie a les 577 saines de TDTU (24 %).
  - [M] v10b, saines TDTU : la moitié qui « ressemble » le moins à la Tanzanie (classifieur de source appris sans TDTU) est en alerte à 58 %, l'autre moitié à 10 % (Spearman +0,56). Pour a1 / c1 / c2 la corrélation est faible parce que presque tout est en alerte (79 à 92 % même dans la moitié « tanzanienne ») : le décalage est global, pas gradué par le style.
- `scripts/m12_analyse_pistes.py` → `pistes_bilan.json` (chiffrage, pas une sélection) :
  - [M] AUC saines / malades : v10b TDTU 0,897, Éthiopie 0,879 ; lecteur F1 0,938 et 0,939 ; F3 0,938 et 0,938 (F1 et F3 séparent pareil).
  - [M] PSFD sans copies tournées : coût moyen installée 49,23 → 43,84 ; F1 35,96 → 31,57. Par groupes de quasi-copies : 52,43 et 37,56. Classement des finalistes inchangé (F1 < F2 < F3 < réserve) dans les 3 comptes.
  - [M] Variantes de décision autour de F1 : « F1 ou v10b sûre » au mieux 35,89 (−0,07) ; « v2 seule si p_loin ≥ y » 37,29 à 40,92 (pire). Piste des décisions épuisée.
- [M] Morceaux et AUC (échantillon de 400 de M-banc) : v10b entière / 2 × 2 / 3 × 3 : TDTU 0,908 / 0,903 / 0,905 ; Éthiopie 0,862 / 0,845 / 0,853. Les morceaux ne séparent pas mieux : leur gain de coût vient d'un déplacement des probabilités, pas d'une meilleure lecture.
- [M] v10b lue en 384 contre 512 px : AUC validation 0,995 → 0,992, TDTU 0,897 → 0,863, **Éthiopie 0,879 → 0,799**. La perte croît avec l'agrandissement (Éthiopie : photos de 150 × 113, agrandies 2,6 fois à 384 px). La soupe et la v2 (lues à 224 px) font 0,944 et 0,936 en Éthiopie.
- `scripts/m12_analyse_v12.py` → `v12_diagnostic.csv` (a1, c1, c2, t1) : aucun candidat v12 n'améliore l'AUC du lecteur F1 en mélange (au mieux c1 en Éthiopie : 0,939 → 0,943 au poids 0,25 ; TDTU 0,938 → 0,916).

## 0 h 10 : rapport du cycle 2

- `out/maladies/analyse/rapport_cycle2.md` écrit : 6 essais recommandés (3 pour M-entraîneur, 3 pour M-banc dont un abandon et une mesure), 3 constats principaux, sections ratées / fausses alertes / raccourci / accord / v12.
- En attente du lot 2 de M-entraîneur (b1, a2, a3, a4) pour `scripts/m12_analyse_v12.py`.

## 0 h 20 : candidats v12 du lot 2 (A-9)

- `scripts/m12_analyse_v12.py` accepte maintenant `lot2/<candidat>` ; lancé sur a2, a3, a4, b1 et c3 (partiel : TDTU, PSFD et validation seulement).
- [M] Saines TDTU lues par le pli sans TDTU, P(malade) médiane : a1 0,94 ; a2 (poids 1) 0,81 ; a3 (moitié saines sur l'ensemble) 0,93 ; **a4 (a3 + PSFD retiré) 0,59** ; b1 0,85 ; c3 1,00.
- [M] Retirer PSFD est le levier le plus net. L'équilibre global des saines (a3) ne fait rien : il faut l'équilibre source par source (essai 1 du rapport).
- [M] b1 déplace tout vers « malade » : validation 255 / 1 000 saines en alerte, AUC Éthiopie 0,886. a4 est le meilleur réseau seul en Éthiopie (AUC 0,918).
- [M] Aucun ne monte l'AUC du lecteur F1 en mélange (au mieux +0,002).
- Rapport mis à jour (section 7 et essai 1).
