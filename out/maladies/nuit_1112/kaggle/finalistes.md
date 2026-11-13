# Finalistes v12 (agent M-entraînement), écrits avant toute lecture des juges

Règle « finaliste » (plan du 12/11, 4.4) appliquée sur le réglage : validation Tanzanie (moyenne des 3 plis) + TDTU, PSFD, Éthiopie (chacun lu par le pli qui ne l'a pas appris). Chaîne complète (aiguilleur, v2 en « loin »), décision `decider_convnext`. Référence v10b : coût moyen 49,23 (seuil finaliste : ≤ 48,23). Mesure : `scripts/m12_entr_mesurer.py`. Aucun juge (BanSpot, Cordana du Pérou, AgroVisionBD) n'a été lu par l'agent M-entraînement.

| Finaliste | Recette | Seuils | Tanzanie (ratées ; fausses alertes) | TDTU | PSFD | Éthiopie | Coût moyen | Modèle final |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **v12a4** (00 h 25) | départ v10b, 3 époques, 224 px, EMA, perte « malade dite saine » × 3, tirage par pays et par classe puis moitié saines / moitié malades, **PSFD jamais appris** | v10b inchangés | 7,5 / 2 001 ; 46,5 / 1 000 (pire pli 11 ; 55) | 57 / 1 059 ; 258 / 577 | 147 / 738 | 178 / 1 134 ; 28 / 155 | **47,89** | carnet `m12-final-a4` (3 graines, départs v10b 0-1-2) → `modeles/maladies_v12_essais/v12a4/` |

Pour information (ne compte pas dans la règle) : PSFD sans les 123 copies tournées à coins noirs, v10b 80 / 615 ratées, v12a4 91 / 615 (`scripts/m12_entr_psfd_info.py`).

**v12a4, modèle final prêt (1 h 17)** : `modeles/maladies_v12_essais/v12a4/` (3 poids 16 bits `maladies_v12a4_{0,1,2}.pt` + `seuils.json` au format de la chaîne, seuils de la v10b). Contrôle : validation Tanzanie lue par le modèle final, chaîne complète : 10 / 2 001 malades sans alerte, 44 / 1 000 saines en alerte. Lecture des juges : à faire par l'agent Juge (préparation de la chaîne : `preparer_convnext`, 384 px, JPEG lu en 896 px, 4 vues).

| Finaliste | Recette | Seuils | Tanzanie | TDTU | PSFD | Éthiopie | Coût moyen | Modèle final |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **v12a7** (1 h 25) | comme a4 mais tirage 50/50 saines / malades dans chaque source, perte × 2, augmentation « basse résolution » (100-160 px, p = 0,3), PSFD jamais appris | **règle B (seuil de confiance) 0,69**, réglée sur le réglage (grille 0,02-0,70) ; autres seuils v10b | 7 / 2 001 ; 56,5 / 1 000 (2 plis) | 55 / 1 059 ; 248 / 577 | 129 / 738 | 184 / 1 134 ; 23 / 155 | **45,30** | à entraîner (une place GPU) |

Réserve (non retenue tant que les 3 places ne sont pas prises) : a5 (règle B 0,70 ; 47,27).

| Candidat (2 h 15) | Recette | Seuils | Tanzanie | TDTU | PSFD | Éthiopie | Coût moyen | État |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **v12a9** | a7 + jeux d'entraînement neufs `feuilles-nuit-1112` (Bangladesh, 1 405 photos ; jamais le test vierge) | règle B 0,65 | 5 ; 57 | 59 ; 217 | 113 | 173 ; 21 | **41,51** | finaliste ; modèle final à entraîner |
| v12a10 | a7 + morceaux p = 0,3 | règle B 0,61 | 6 ; 55,5 | 58 ; 230 | 126 | 172 ; 21 | 43,25 | finaliste possible |

Liste arrêtée à 5 h (au plus 3) ; les finalistes définitifs seront écrits ici avant 7 h, avant toute lecture des juges.

## Liste des finalistes v12 (arrêtée à 2 h 55, avant toute lecture des juges ; 3 au plus)

Tous gardent **les seuils de la v10b** (aucun seuil réglé) : ce sont les chiffres les moins optimistes. Rappel v10b (11/11) : coût moyen 49,23 ; Tanzanie 9 ; 57.

| Rang | Finaliste | Recette | Tanzanie (ratées / 2 001 ; fausses alertes / 1 000) | TDTU (/ 1 059 ; / 577) | PSFD (/ 738) | Éthiopie (/ 1 134 ; / 155) | Coût moyen | Modèle final |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **v12a13** | départ v10b ; 3 époques, 224 px, EMA ; PSFD jamais appris ; + `feuilles-nuit-1112` (Bangladesh) ; tirage par source puis 50/50 saines / malades dans chaque source ; perte « malade dite saine » × 2 ; augmentations de base + basse résolution (p = 0,3) + morceaux (p = 0,3) | 6 ; 65,5 | 64 ; 201 | 114 | 141 ; 34 | **41,50** | `m12-final-a13-a14` → `modeles/maladies_v12_essais/v12a13/` |
| 2 | v12a14 | comme a13 sans morceaux, perte × 3 | 5 ; 54 | 59 ; 209 | 119 | 194 ; 16 | 42,28 | `m12-final-a13-a14` → `modeles/maladies_v12_essais/v12a14/` |
| 3 | v12a4 | sans jeux neufs : tirage par pays et classe, puis moitié saines au total, perte × 3, PSFD jamais appris | 7,5 ; 46,5 | 57 ; 258 | 147 | 178 ; 28 | 47,89 | prêt : `modeles/maladies_v12_essais/v12a4/` |

Contrôles : aucun pays ne perd plus de 2 points de malades sans alerte ; Tanzanie ≤ 14 et ≤ 77. Entre finalistes qui passent les juges, la règle 4.4 prend le coût de réglage le plus bas (v12a13). Pour information : PSFD sans les 123 copies tournées, v10b 80 / 615, v12a13 68 / 615, v12a14 73 / 615, v12a4 91 / 615.
