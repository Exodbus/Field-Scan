# Finalistes de M-banc (maladies, sans entraînement) : nuit du 12 au 13 novembre 2026

Écrit par l'agent M-banc **avant toute lecture des juges** (BanSpot et Cordana du Pérou n'ont pas été ouverts ; ils seront lus par l'agent « Juge »). Règles : `docs/plan_nuit_2026-11-12.md`, section 4.4. Journal complet : `docs/nuit_2026-11-12/journal_m_banc.md`.

**Nombre d'essais de réglage : 1 215** (947 au moment du premier choix, 23 h 48 ; finalistes inchangés depuis) (chaque seuil d'une grille compte pour un essai). Les coûts de réglage ci-dessous sont donc optimistes ; ils ont été choisis sur des plateaux (seuil voisin des deux côtés encore finaliste), pas sur des pics.

## 1. Règle de choix appliquée (écrite à 22 h 19, avant les essais)

Parmi les candidats qui remplissent la règle « finaliste » du plan (coût moyen ≤ référence − 1 ; Tanzanie ≤ 14 / 2 001 ratées et ≤ 77 / 1 000 fausses alertes ; aucun pays ne perd plus de 2 points de ratées) : le meilleur de chaque famille sur un seuil dont les deux voisins sont aussi finalistes, puis les 3 coûts moyens les plus bas.

## 2. Définition commune

Les trois finalistes sont des variantes du même module :
- **aiguilleur inchangé** (`p_loin ≥ 0,5` → photo « loin ») ;
- **lecteur « proche »** = moyenne géométrique, poids égaux, des probabilités de la **v10b**, de la **soupe v2 + v8** et de la **v2** sur les 3 classes communes (saine, Sigatoka noire, fusariose). La classe « autre » de la v10b est gardée, multipliée par 1/3. Le tout est renormalisé, puis décidé par `decider_convnext` avec les seuils de la v10b (`modeles/maladies_binome/v10b/seuils.json`), sauf `seuil_confiance` (règle B), remplacé par le seuil t du candidat. `seuil_alerte` 0,725, `seuil_nom` 0,79 et le seuil v11 0,675 sont inchangés ; ils ne touchent pas aux alertes ;
- **branche « loin »** = réponse de la v2 (politique b, `jnsp_alerte` vrai) ; si la v2 n'alerte pas, on prend la réponse du lecteur proche. Une photo loin est donc en alerte si la v2 **ou** le lecteur proche alerte.

Les finalistes ne diffèrent que par la façon de lire la v10b avant le mélange :

| Finaliste | Lecture de la v10b | Seuil t (règle B) | Plage où il reste finaliste |
| --- | --- | --- | --- |
| **F1** `F1_trois_morceaux2x2` | P(malade) = moyenne de (P(malade) de la photo entière en 384 px) et de (moyenne des 2 plus fortes P(malade) des 4 morceaux 2 × 2). Morceaux : rectangles de même forme que la photo, côté 0,6 de chaque dimension, aux 4 coins, chacun préparé comme une photo entière. P(saine) remplacée, maladies gardant leurs proportions | 0,70 | 0,60 à 0,72 |
| **F2** `F2_trois_384_512` | moyenne des probabilités de la v10b lue en 384 px (installé) et en 512 px | 0,72 | 0,62 à 0,74 |
| **F3** `F3_trois` | v10b lue comme aujourd'hui (384 px) | 0,74 | 0,64 à 0,76 |

Réserve (hors des 3, plus simple : deux modèles au lieu de trois) : `reserve_geo_v10b_soupe_loin`, géométrique v10b + soupe, t = 0,68, même branche loin : coût 39,24.

## 3. Chiffres de réglage

Chaque case : malades sans alerte ; saines en alerte (dont « à vérifier »). Coût = 3 × taux de ratées + taux de fausses alertes, en points ; PSFD n'a pas de saine.

| Chaîne | Validation Tanzanie (2 001 ; 1 000) | Sigatoka nommée | TDTU (1 059 ; 577) | PSFD (738) | Éthiopie (1 134 ; 155) | Coût moyen |
| --- | --- | --- | --- | --- | --- | --- |
| Installée (v10b) | 9 ; 57 (25) | 872 / 1 000 | 83 ; 177 (38) | 149 | 179 ; 43 (18) | **49,23** |
| **F1** | 0 ; 62 (53) | 919 | 19 ; 241 (143) | 102 | 117 ; 28 (28) | **35,96** |
| **F2** | 1 ; 58 (49) | 908 | 22 ; 234 (138) | 105 | 125 ; 27 (27) | **36,48** |
| **F3** | 2 ; 57 (48) | 916 | 28 ; 232 (136) | 109 | 134 ; 27 (27) | **37,83** |
| Réserve | 2 ; 64 (46) | 908 | 27 ; 222 (112) | 117 | 131 ; 34 (33) | 39,24 |

Coût par jeu (validation / TDTU / PSFD / Éthiopie) : installée 7,0 / 54,2 / 60,6 / 75,1 ; F1 6,2 / 47,2 / 41,5 / 49,0 ; F2 5,9 / 46,8 / 42,7 / 50,5 ; F3 6,0 / 48,1 / 44,3 / 52,9.

À noter :
- Les fausses alertes de TDTU montent (177 → 232 à 241 / 577). Le coût baisse quand même, parce que les ratées baissent fortement partout (TDTU 83 → 19 à 28, PSFD 149 → 102 à 109, Éthiopie 179 → 117 à 134). Une grande part des fausses alertes devient « à vérifier » (confiance faible).
- **Temps de calcul** par photo proche, sur le PC (processeur), estimé : installée 1,8 s ; F3 environ 3,2 s (v10b + soupe + v2) ; F2 environ 6 s (une lecture 512 px de plus) ; F1 environ 10 s (4 morceaux de plus).
- La Cordana dite Sigatoka n'a pas été regardée (juge). Sur le réglage, les autres maladies dites « Sigatoka » baissent beaucoup avec le mélange à trois (176 → 49 sur les 4 jeux, au seuil de nom 0,79), mais la vraie Sigatoka est aussi moins nommée dans les pays (PSFD 97 → 60 / 474).

### Pour information (la règle 4.4 compte PSFD avec ses 738 photos)

| Chaîne | Coût moyen, règle | PSFD sans les 123 copies tournées | PSFD, une photo par groupe de quasi-copies (188) |
| --- | --- | --- | --- |
| Installée | 49,23 | 43,84 | 53,23 |
| F1 | 35,96 | 31,57 | 38,76 |
| F2 | 36,48 | 32,03 | 39,37 |
| F3 | 37,83 | 33,46 | 40,32 |
| Réserve | 39,24 | 34,67 | 42,51 |

Mises en garde pour le Contrôleur :
- **F1 et F3 ont la même AUC** sur le réglage (TDTU 0,938, Éthiopie 0,939 / 0,938, mesure de M-analyste). Le gain des morceaux (1,9 point) vient d'un déplacement des probabilités, choisi après beaucoup d'essais ; F3 est le plus simple des trois.
- Écartés après le premier choix :
  - lecture 3 × 3 sur tous les jeux (arrêtée) ;
  - v10b en 224 px ou en taille adaptée (au mieux 38,31) ;
  - mélanges avec les v12 a1 à a4, b1, c1, c2 (au mieux 38,74).

## 4. Recalculer sur n'importe quel jeu de probabilités

Script : `scripts/m12_banc_finalistes.py` (définitions exactes dans `CANDIDATS` ; il importe `decider_convnext` de la chaîne). Il vérifie qu'il redonne les chiffres ci-dessus sur le réglage.

```
# probabilités déjà calculées (BanSpot : out/maladies/banspot/p_v10b.npy, p_soupe.npy, p_v2.npy, p_loin.npy)
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_banc_finalistes.py \
    --v10b p_v10b.npy --soupe p_soupe.npy --v2 p_v2.npy --loin p_loin.npy \
    [--v10b_512 p_v10b_512.npy] [--v10b_g2 p_v10b_g2.npy] [--verite verite.csv] --sortie reponses.csv
```
- Accepte des `.npy`, ou des `.csv` aux colonnes `p_saine, p_black_sigatoka, p_fusarium[, p_autre]` ou `p_loin`.
- `--verite` : CSV avec une colonne `malade` (0/1), dans le même ordre.
- F3 et la réserve n'ont besoin que des probabilités existantes de la v10b, de la soupe, de la v2 et de l'aiguilleur. Pour BanSpot, elles sont toutes en cache. Pour la Cordana du Pérou, voir `out/maladies/v10b/predictions_*_cordana_perou.csv` et `p_loin_cordana_perou.csv`.
- F2 et F1 demandent deux lectures de plus de la v10b (512 px ; 4 morceaux 2 × 2), **non calculées sur les juges**. Pour les calculer :
  - en local : `--photos liste.txt --calculer dossier/`, qui écrit `p_v10b_512.npy` et `p_v10b_g2.npy` (environ 10 s par photo sur un processeur libre, bien plus quand les autres agents tournent : 12 min pour 2 photos, chargement compris, le 12/11 à 23 h 45) ;
  - sur Kaggle : reprendre `scripts/m12_banc_kaggle_morceaux.py` (même préparation), en remplaçant la liste des photos.

## 5. Ce qu'il faudrait changer dans la chaîne en cas d'adoption (non appliqué)

`config.yaml`, bloc `maladies` : ajouter (clés nouvelles, lues par le code ci-dessous) :
```yaml
  # Mélange géométrique du lecteur proche (M-banc, nuit du 12/11) : v10b + soupe + v2, poids égaux
  melange_proche: [modeles/maladies_soupe_v2_v8/poids, modeles/maladies_binome/maladies_v2/poids]
  seuil_confiance_melange: 0.74     # F3 ; 0.72 pour F2 ; 0.70 pour F1
  loin_ou_proche: true              # photo « loin » en alerte si la v2 ou le lecteur proche alerte
  # F2 seulement : lecture_512: true ; F1 seulement : morceaux_2x2: true
```
`fieldscan/modules/maladies.py`, dans `executer` :
- charger les deux modèles de `melange_proche` avec `charger_convnext` ;
- pour les photos proches, calculer P10 (v10b), Pso, Pv2 avec `predire_convnext`, puis `P = geo(P10, Pso, Pv2, (1, 1, 1))` (fonction `geo` de `scripts/m12_banc_finalistes.py`) ;
- décider avec `decider_convnext(P, {**m_proche, "seuil": seuil_confiance_melange})` ;
- pour les photos loin, si la réponse de la v2 n'est pas une alerte, prendre la décision du lecteur proche sur la même photo. Il faut donc aussi lire les photos loin avec les trois modèles ;
- F2 : `P10 = (P10_384 + predire_convnext(chemins, {**m_proche, "taille": 512})) / 2` ;
- F1 : `P10 = lecture_v10b(P10, ..., G2=...)` avec les 4 morceaux (fonction `calculer` du script).
