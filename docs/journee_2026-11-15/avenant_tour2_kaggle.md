# Avenant : second tour Kaggle (15/11, vers 16 h 05)

Corentin a demandé à 16 h : « continuer de tenter d'améliorer les modèles avec kaggle ». Cet avenant est écrit **avant tout calcul du second tour**. Son empreinte SHA-256 est dans `empreinte_avenant_tour2.txt`.

## Ce qui reste valable
- `docs/plan_journee_2026-11-15.md` :
  - interdits ;
  - références (maladies : F1, installé en lecture F1_bornes depuis le commit 0f99dad, mêmes alertes ; comptage : v5 au seuil 0,30) ;
  - jeux de réglage ;
  - règles 4.3 et 5.3 du plan du 13/11 ;
  - familles et gel à 2 places par module.
- Kaggle : **3 h de GPU au plus par agent**, accord de Corentin du 15/11, T4 × 2.

## Ce qui change
- **Les juges relus perdent de leur valeur à chaque lecture.** BanSpot, Cordana du Pérou, segmento est, CG, `banano_dense` et `test_negatifs` ont déjà été lus pour les finalistes des 13, 14 et 15/11. Une lecture de plus reste permise, une par finaliste. Le récapitulatif donnera, à côté de chaque chiffre, le nombre de lectures déjà faites.
- **Leçon du premier tour pour le comptage.** Tout ce qui descend de v6f perd l'agroforesterie (CG), même mélangé à 50 % avec le v5, alors que MM (agroforesterie du réglage) ne le voyait pas. Le second tour doit partir du **v5** (ResNet-18), ou garder explicitement son comportement, par exemple en distillant le v5 sur les tuiles ReforesTree. Rien de ce qui part de v6f ou de c13h n'est proposé.
- **Contrôle propre au second tour.** Il est ajouté aux conditions 5.3, sans les remplacer. Le rappel des pieds du v5 sur les tuiles d'entraînement ReforesTree doit être conservé : le candidat retrouve au moins 95 % des pieds que le v5 trouve, à 1 m près, sur les tuiles ReforesTree des sites d'**entraînement**. C'est une mesure de non-régression sur des données vues : elle ne mesure pas une performance.
- **Maladies.** Le carnet `m15-traits` (traits ConvNeXt-Tiny DINOv3 pour le lecteur kNN) est toujours en file chez Kaggle. Il peut être repris tel quel. La règle de mesure écrite à 14 h 15 dans `journal_m_kaggle.md` s'applique, avec la règle 4.3.

## Horaires
- `finalistes.md` écrits avant **20 h 30**. La session principale admet les finalistes et gèle la liste à **20 h 35**.
- Juges relus de 20 h 35 à 21 h 30. Récapitulatif vers 21 h 45, puis notification à Corentin.

## Équipe
| Agent | Travail | Écrit dans |
| --- | --- | --- |
| M-kaggle2 | maladies, Kaggle 3 h au plus | `notebooks/m15b_*.py`, `out/maladies/jour_1511/kaggle2/`, `modeles/maladies_jour_1511/`, `docs/journee_2026-11-15/journal_m_kaggle2.md` |
| C-kaggle2 | comptage, Kaggle 3 h au plus | `notebooks/c15b_*.py`, `out/comptage/jour_1511/kaggle2/`, `modeles/comptage_jour_1511/`, `docs/journee_2026-11-15/journal_c_kaggle2.md` |

Les deux agents :
- utilisent 2 fils au plus sur le processeur local ;
- ne lisent ni n'envoient aucun juge ni test ;
- ne commitent rien ;
- ne téléchargent rien en local ;
- ne modifient pas les fichiers existants.
