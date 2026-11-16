# Avenant : pistes 2 et veille (14/11, 18 h 30)

À 18 h 30, Corentin a demandé de lancer d'autres pistes en parallèle, et d'envoyer des agents chercher les dernières publications sur ce qu'on cherche à faire.

Cet avenant est écrit avant tout calcul de ces pistes. Il ne change rien au plan (`docs/plan_nuit_2026-11-13.md`), ni au gel de 19 h, ni à la lecture des juges.

## 1. Place dans le protocole

- **Hors du gel de ce soir.** L'échéance d'admission (18 h 45) est passée. Les candidats des pistes 2 ne prennent aucune place dans la liste gelée à 19 h.
- **Aucun juge relu ni test vierge** n'est lu pour eux ce soir : BanSpot, Cordana du Pérou, segmento est, CG, `banano_dense`, `test_negatifs`, `banana_trees_kp`. Ils sont mesurés sur le réglage seulement.
- Un candidat qui passe la règle devient un **finaliste de réserve**. C'est Corentin qui décide s'il est jugé plus tard, et comment.
- **Règles inchangées**, celles du plan :
  - maladies : section 4.3, avec la référence F1 recalculée sur les mêmes photos ;
  - comptage : section 5.3, avec la référence v5.
- Familles A, B, C : celles du plan.
- **À titre d'information seulement** :
  - les chiffres sont aussi donnés à côté des finalistes de ce soir (F1_bornes, d3b, E5p90b_c13e_d-0.1, A1) ;
  - pour les maladies, chaque candidat donne aussi le total de malades sans alerte sur les 5 jeux, comparé à celui de F1 (consigne « rater un malade est plus grave »).

## 2. Équipe ajoutée

| Agent | Travail | Écrit dans |
| --- | --- | --- |
| Veille | publications récentes (2024-2026), maladies et comptage : lecture en ligne seulement, aucun téléchargement | `docs/veille_2026-11-14/` |
| M-piste2 | maladies : mélanges avec d3b (famille C), règles de désaccord, entraînement sensible au coût, stabilité de d3b | `out/maladies/nuit_1311/piste2/`, `scripts/m14_*.py`, `notebooks/m14_*.py`, `modeles/maladies_nuit_1411/`, `docs/nuit_2026-11-13/journal_m_piste2.md` |
| C-piste2 | comptage : stabilité de c13e, mélanges de cartes avec c13h (MM et 11 cm), aiguillage + trous | `out/comptage/nuit_1311/piste2/`, `scripts/c14_*.py`, `notebooks/c14_*.py`, `modeles/comptage_nuit_1411/`, `docs/nuit_2026-11-13/journal_c_piste2.md` |

Avec le Contrôleur et les deux Juges de 19 h, cela fait six agents actifs au plus.

## 3. Limites

- **GPU Kaggle** : 3 h au plus par agent de piste. Utiliser la forme P100, car les carnets T4 sont restés en file d'attente l'après-midi.
- **Processeur** : de 19 h à 20 h 30, au plus 3 fils par agent de piste, pour ne pas fausser les temps mesurés par les Juges.
- **Choix** : toute règle de choix propre à une piste (ordre des essais, choix entre variantes) est écrite dans son journal avant de calculer. Le nombre d'essais y est compté.
- Pas de commit, pas de téléchargement, pas de modification de `fieldscan/`, de `config.yaml`, des fichiers existants, ni des fichiers des autres agents.

## 4. Horaires

- Veille : rapport avant 20 h 30.
- Pistes 2 : `finalistes_piste2.md` avant 23 h 30.
- Vérification par le Contrôleur après la lecture des juges.
- Résultats ajoutés au récapitulatif dans une section « Pistes 2 ».
