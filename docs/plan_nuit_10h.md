# Plan de nuit : 10 heures d'essais sur le comptage et les maladies

Écrit par Claude le 12 novembre 2026 vers 22 h 50, à la demande de Corentin (carte blanche, travail autonome). Ce plan organise l'équipe et le temps. **Les règles de choix et d'adoption restent celles de `docs/plan_nuit_2026-11-12.md`** (sections 2, 3.4, 3.5, 4.4, 4.5), écrites avant tout calcul : trois étages (réglage, juges, test vierge), aucun réglage sur les juges, test vierge lu une fois.

Les six agents lancés à 22 h 15 ont été arrêtés à 22 h 45. Ce qu'ils ont laissé est repris au point 6.

## 1. Objectif de la nuit

À 9 h, pour chaque module, l'un de ces deux résultats, écrit et vérifié :
- **une adoption proposée** : un candidat qui passe la règle sur le réglage puis sur les juges, mesuré une fois sur le test vierge, avec le correctif prêt (non appliqué, non commité) ;
- **ou un constat d'échec propre** : la liste des essais, pourquoi ils échouent, et ce qu'il faudrait pour aller plus loin.

Cible indicative, pas une règle : comptage, +0,03 de F1 moyen de réglage sans perdre sur les juges, et plus de 60 % des jeunes plants retrouvés ; maladies, coût moyen de réglage sous 40 (v10b : 45,4) avec au plus 9 malades ratées en validation.

## 2. Équipe : 11 rôles, 6 actifs au plus à la fois

La limite de 6 vient de la machine (8 cœurs, pas de GPU local) et du quota Kaggle (2 carnets GPU à la fois).

| Pôle | Agent | Rôle | Mission |
| --- | --- | --- | --- |
| Direction | **Chef d'orchestre** (session principale) | pilote, ne calcule pas | lance et relance les agents, tient le tableau de bord, vérifie les rapports, tranche selon les règles écrites, écrit le récapitulatif |
| Données | **D-comptage** | ingénieur données drone | découpage v6, archive 5 cm, jeu Kaggle ; puis prospection de jeux neufs et choix du test vierge |
| Données | **D-maladies** | ingénieur données feuilles | prospection de jeux neufs, contrôle de fuite, test vierge, archive d'entraînement sur Kaggle |
| Comptage | **C-banc** | ingénieur d'inférence | essais sans entraînement sur les cartes de chaleur en cache |
| Comptage | **C-entraîneur** | ingénieur d'apprentissage | carnets Kaggle v6 (recettes, architectures, graines) |
| Comptage | **C-analyste** | analyste d'erreurs | où et pourquoi le v5 et les candidats se trompent (taille des plants, densité, bords) ; propose les essais suivants |
| Maladies | **M-banc** | ingénieur d'inférence | mélanges, lecture en morceaux, seuils, sur les probabilités en cache |
| Maladies | **M-entraîneur** | ingénieur d'apprentissage | carnets Kaggle v12, validation croisée par pays |
| Maladies | **M-analyste** | analyste d'erreurs | quelles photos sont ratées ou en fausse alerte (pays, cadrage, gravité) ; propose les essais suivants |
| Contrôle | **Contrôleur** | contradicteur | relit règles, fuites, comptes d'essais et chiffres de chaque finaliste avant toute lecture des juges ; peut refuser un finaliste |
| Contrôle | **Juge** | évaluateur indépendant | seul à lire les juges et le test vierge, une fois, avec son propre code de mesure |

Règles de fonctionnement :
- chaque agent n'écrit que dans ses dossiers (tableau du premier plan, section 5 ; les analystes écrivent dans `out/<module>/analyse/`, le contrôleur et le juge dans `out/controle_nuit_1112/`) ;
- chaque agent tient `docs/nuit_2026-11-12/journal_<agent>.md` : heure, essai, résultat, **numéro d'essai** ;
- personne ne modifie `fieldscan/`, `run.py`, `config.yaml`, ni un script existant ; personne ne commite ;
- un agent qui a fini rend un rapport court ; le chef d'orchestre le relance sur la suite de sa file (même contexte) ;
- un analyste ne lit jamais les juges : il travaille sur le réglage.

## 3. Déroulé : 5 cycles de 2 heures

Chaque cycle suit la même boucle : **essayer, mesurer, analyser, choisir les essais suivants**. À la fin de chaque cycle, le chef d'orchestre lit les journaux, met à jour `docs/nuit_2026-11-12/tableau_de_bord.md` (essais faits, meilleur candidat par module, quota GPU restant) et relance.

| Cycle | Heure | Actifs (6 au plus) | But |
| --- | --- | --- | --- |
| 1 | 23 h à 1 h | D-comptage, D-maladies, C-banc, M-banc, M-entraîneur, C-analyste | données prêtes, bancs validés, premiers essais sans entraînement, plis v12 lancés |
| 2 | 1 h à 3 h | C-banc, C-entraîneur, M-banc, M-entraîneur, M-analyste, D (celui qui n'a pas fini) | v6a à v6c sur Kaggle ; lecture en morceaux ; recettes v12 comparées par pays |
| 3 | 3 h à 5 h | C-entraîneur, M-entraîneur, C-analyste, M-analyste, C-banc, M-banc | deuxième tour, guidé par les analyses : on creuse ce qui marche, on abandonne ce qui échoue deux fois |
| 4 | 5 h à 7 h | C-entraîneur, M-entraîneur, C-banc, M-banc, Contrôleur | modèles finaux (3 graines), mélanges candidats entraînés + anciens ; le contrôleur relit les finalistes |
| 5 | 7 h à 9 h | Juge, Contrôleur, C-banc ou M-banc (correctifs), chef d'orchestre | juges lus une fois, test vierge lu une fois, correctifs prêts, récapitulatif |

Garde-fous de temps :
- **3 h** : si le découpage v6 n'est pas prêt, le v6 s'entraîne sans `banana_tree_detection` en apprentissage (tout en validation) ;
- **5 h** : gel de la liste des recettes ; après, on ne lance que des modèles finaux ;
- **7 h** : gel des finalistes (3 au plus par module), écrits avant la lecture des juges ;
- **8 h 30** : plus aucun calcul ; écriture.

Budget GPU Kaggle : quota vérifié au début et écrit. Priorité si le quota manque : v12 par pays (maladies) > v6a 3 graines > v6b > v6c > le reste.

## 4. File d'essais du comptage (dans l'ordre)

Sans entraînement (C-banc) :
1. Banc validé contre les chiffres du v5 et du v4 (à 0,005 près).
2. Vues multiples : 8 symétries (moyenne, maximum, moyenne des logits).
3. Mélange v3 + v4 + v5 : moyenne, maximum, géométrique, poids par grille.
4. Plusieurs échelles (3,5 / 5 / 7 cm) : fusion par maximum, puis par vote.
5. Aiguillage v3 / v5 par espacement médian et par taille des pics.
6. Taille de la fenêtre des pics (k_pics 3, 5, 7, 9) et seuil relatif au maximum local.
7. Suppression des doublons par distance (0,8 à 1,5 m) après fusion.
8. Compte par intégrale de la carte contre compte par pics.
9. Marge au bord des tuiles (le binôme : +0,07 de F1 sur un jeu avec 1 m de marge) : mesurer l'effet, sans changer la référence.
10. Mélange des candidats entraînés de la nuit avec le v3 et le v5.

Avec entraînement (C-entraîneur, environ 1 h par carnet sur T4) :
11. **v6a** : recette v5 + plantation espacée + échelle 0,5 à 2 + EMA, graine 0.
12. **v6b** : v6a + sortie à la demi-résolution + tête de décalage + gaussienne suivant la taille du plant.
13. **v6c** : v6a + perte focale et tirage équilibré par type de plantation.
14. La meilleure des trois : graines 1 et 2, puis moyenne des poids des 3 graines.
15. Entrée à 3,5 cm au lieu de 5 cm (petits plants), même réseau.
16. Réseau de base ResNet-34, puis ResNet-50 (le ConvNeXt DINOv3 a échoué chez le binôme : pas refait).
17. Apprentissage à deux têtes : centres + densité (compte par intégrale appris).
18. Auto-apprentissage : pseudo-étiquettes du mélange v3 + v5 sur nos orthomosaïques sans annotation (El Oro), ajoutées à l'apprentissage seulement, jamais comme référence.
19. Réglage fin du v5 (5 époques, taux bas) sur la seule plantation espacée, puis moyenne des poids v5 / v5 réglé (interpolation 0,3 / 0,5 / 0,7).
20. Distillation : un seul réseau apprend la moyenne des cartes v3 + v4 + v5.

## 5. File d'essais des maladies (dans l'ordre)

Sans entraînement (M-banc) :
1. Banc validé contre les chiffres du 11/11.
2. Mélange v10b + soupe : moyenne, géométrique, poids ; alerte si l'un des deux alerte.
3. Branche « loin » : alerte si la v2 ou le modèle de près alerte.
4. Seuils de la règle B et de la v11 sur le réglage élargi ; seuil robuste (pire jeu).
5. Lecture en morceaux 2 × 2 puis 3 × 3 (maximum, deux plus fortes, « ou bruité »), d'abord sur un échantillon tiré à l'avance.
6. Lecture à plusieurs tailles (384 et 512 px).
7. Mélange à trois (v10b + soupe + v2) et températures par modèle.
8. Nom de la maladie : seuil de nom réglé pour moins de Cordana dite Sigatoka, sans toucher à l'alerte.
9. Mélange des candidats v12 avec la v10b.

Avec entraînement (M-entraîneur, validation croisée par pays, un réseau par pli) :
10. **v12a** : v10b réentraînée, tirage équilibré par pays et par classe, perte pondérée (malade dite saine × 3), EMA.
11. **v12b** : v12a + augmentations fortes + CutMix de fonds sains + lissage 0,1.
12. **v12c** : tête légère sur DINOv3 ViT-B figé, photo entière + 4 morceaux.
13. La meilleure : apprentissage à 384 px au lieu de 224.
14. Poids de la perte : 2, 3, 5 (sensibilité de la préférence « rater est plus grave »).
15. Perte par groupe (le pays le plus mal classé pèse le plus à chaque pas, façon Group-DRO).
16. Données neuves de D-maladies ajoutées à la meilleure recette.
17. Apprentissage multi-morceaux : la photo entière et ses morceaux partagent l'étiquette (vise la Sigatoka légère sur feuille entière).
18. Réglage fin des dernières couches seulement, puis du réseau entier (deux temps).
19. Modèle final : 3 graines sur tout, moyenne des poids, comparée à la moyenne des probabilités.
20. Distillation du meilleur mélange dans un seul réseau (temps de calcul de la chaîne divisé par 3).

Règle d'abandon, pour les deux files : une piste qui perd deux fois de suite sur le réglage est fermée et écrite comme échec ; une piste qui gagne est creusée avant de passer à la suivante.

## 6. Ce qui est déjà acquis (agents arrêtés à 22 h 45)

- **M-banc** : banc validé ; 343 essais sans entraînement. Meilleur candidat de réglage : mélange géométrique v10b + soupe, seuil 0,66, et branche « loin » qui alerte si la v2 ou le modèle de près alerte. Coût moyen **39,4 contre 45,4** ; validation : 4 malades ratées (9 avant) et 58 fausses alertes (57 avant). Chiffres de réglage, optimistes après 343 essais : **les juges ne sont pas lus**.
- **C-banc** : cartes de chaleur en cache commencées ; aucune fuite entre v3, v4 et v5 sur le réglage. Réserve : segmento est a servi de validation au v3, donc un mélange contenant le v3 y est avantagé (la moyenne des juges sera aussi donnée sans ce jeu).
- **D-comptage** : `banana_tree_detection` contient deux pavages (396 tuiles de 1 280 px, 20 de 1 024 px) ; 16 tuiles portent les annotations d'une autre image (fausses) et sont à exclure ; le test du v5 en contenait 4 (233 boîtes sur 38 790). Position des tuiles en cours de reconstruction.
- **M-entraîneur** : choix de recette écrits, aucun carnet lancé. **D-maladies** : un jeu Mendeley d'Indonésie en cours de téléchargement ; trois jeux appris par la v10b repérés comme non neufs.
- Aucun carnet Kaggle n'a été lancé et aucun calcul local ne tourne.
