# Finalistes v6 entraînés (C-entraîneur, nuit du 12 au 13 novembre 2026)

Réglage seulement : aucun juge n'a été calculé ni lu par mes carnets (ensembles test_* retirés au chargement, `cg/` jamais ouvert).

**Règle « finaliste »** (docs/plan_nuit_2026-11-12.md, 3.4) avec la référence v5 mesurée par le même code (journal C-entraîneur, 23 h 37) : moyenne des 5 F1 de réglage > 0,8023 (v5 au seuil 3.4 = 0,20 : 0,7923) ; aucun jeu sous le v5 à 0,20 moins 0,020 ; erreur de compte ≤ 0,262 (v5 à 0,30) ; moins de 1 % de fausses détections sur les images sans bananier de validation. 11 candidats sur 17 passent (échouent : la soupe, le réglage fin du v5 et ses 3 interpolations, v6f graine 1) ; tableau complet : `tableau_essais.md`.

**Mise en garde (à lire par le Contrôleur et le Juge)** : tous passent grâce à btd_val (v5 0,716 à 0,20, 0,473 à 0,30 → v6 0,985 à 0,989), mesuré sur la même orthomosaïque que btd_train (même champ, même jour, même annotateur ; aucun pixel commun selon D-comptage). Sur les 4 anciennes validations du v5, **aucun v6 ne dépasse le v5 adopté** (0,8539 à 0,30). Sur banano_finca (jeunes plants d'un autre champ, ancien juge du binôme, information seulement), aucun v6 ne dépasse le v5 (0,754). Le gain sur les jeunes plants pourrait ne pas tenir hors de cette orthomosaïque : les juges trancheront.

## Finalistes proposés (3 au plus, classés par moyenne des 5 F1, règle 3.4)

| rang | candidat | ONNX + json | seuil | dense | plantain | jeunes | MM | espacée | moyenne 5 | moyenne 4 anciennes | écart au v5 (0,30) : dense / plantain / jeunes / MM | erreur de compte | sans bananier | finca (info) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| réf. | v5 adopté | `modeles/centres_5cm_v5.*` | 0,30 | 0,779 | 0,886 | 0,893 | 0,857 | 0,473 | 0,7777 | 0,854 | 0 | 0,262 | 16 (0,25 %) | 0,754 |
| 1 | **v6f** (v6a en ResNet-34), graine 0 | `out/comptage_v6/kaggle/v6f/centres_5cm_v6f.*` | 0,35 | 0,778 | 0,882 | 0,888 | 0,851 | 0,987 | **0,8771** | 0,850 | −0,002 / −0,004 / −0,005 / −0,006 | 0,109 | 2 (0,03 %) | 0,739 |
| 2 | **v6a** (recette v5 + btd_train + échelle 0,5-2 + EMA), graine 0 | `out/comptage_v6/kaggle/v6a/centres_5cm_v6a.*` | 0,35 | 0,775 | 0,885 | 0,895 | 0,822 | 0,988 | 0,8730 | 0,844 | −0,004 / −0,001 / +0,003 / −0,035 | 0,140 | 11 (0,17 %) | 0,754 |
| 3 | **v6d** (v6a + tirage par taille de plant), graine 0 | `out/comptage_v6/kaggle/v6d/centres_5cm_v6d.*` | 0,35 | 0,776 | 0,888 | 0,888 | 0,808 | 0,988 | 0,8694 | 0,840 | −0,004 / +0,001 / −0,005 / −0,049 | 0,157 | 4 (0,06 %) | 0,736 |

Graines (modèles finaux) :
- v6a : graine 1 (`v6a_g1`, 0,8709, seuil 0,40), graine 2 (`v6a_g2`, 0,8658, seuil 0,35). Écart entre graines 0,007, porté par MM (0,765 à 0,822). La soupe des poids des 3 graines échoue (F1 0) : utiliser au besoin la moyenne des cartes (banc de C-banc).
- v6f : graine 1 (`v6f_g1`, 0,8611, seuil 0,40 : MM 0,744, **ne passe pas** la règle par jeu), graine 2 (`v6f_g2`, 0,8685, seuil 0,40, passe). Écart entre graines 0,016, encore porté par MM (0,744 à 0,851) : **le MM de la graine 0 (0,851) est en partie de la chance**.

**Moyenne sur les 3 graines** (même recette, information pour le choix entre finalistes) : v6a 0,8699 (4 anciennes 0,840, erreur de compte 0,125) ; v6f 0,8689 (4 anciennes 0,839, erreur de compte 0,078). Les deux recettes sont équivalentes au bruit près ; v6f compte mieux (erreur 0,05 à 0,11 contre 0,10 à 0,14) et a moins de fausses détections sans bananier (2 à 5 contre 1 à 11), mais pèse 86 Mo contre 45 Mo et coûte environ 1,5 fois le calcul.
- v6d : une seule graine (gel des recettes à 5 h ; pas de place GPU pour ses graines).

Format de sortie de tous ces ONNX : celui du v5 (entrée RGB normalisée NCHW complétée à un multiple de 32 ; sortie logits au quart, canal 0 ; pics fenêtre 7). Le seuil de chacun est dans son json (`seuil`).
