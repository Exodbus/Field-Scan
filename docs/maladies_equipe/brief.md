# Équipe maladies : brief commun (8 novembre 2026, nuit)

Objectif fixé par Corentin : **le meilleur classifieur de maladies des feuilles possible**, et **meilleur sur les photos prises de loin** (feuille entière, plante, vue d'en dessous). Les pistes mathématiques (sans apprentissage) sont à explorer sérieusement, seules ou combinées à l'IA. Toute hypothèse est testée, avec un critère écrit avant le calcul.

Orchestrateur : la session principale. Elle seule écrit les protocoles (`docs/protocole_*.md`), lance les GPU Kaggle et tranche les désaccords. **Aucun commit, aucun push, par personne.**

## 1. Règles (CLAUDE.md du dépôt, en plus court)

- Français partout. Python : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u script.py` ; chaque script ajoute la racine du dépôt à `sys.path`. Bibliothèques présentes : numpy, scipy, OpenCV (headless), kornia, torch et torchvision (processeur), pandas, matplotlib, Pillow, onnxruntime. **Absentes : scikit-image, scikit-learn** (ne pas les installer ; tout réimplémenter avec numpy, scipy ou torch).
- **Critère écrit avant de calculer** : chaque expérience note dans ta fiche, avant toute mesure, l'hypothèse, le jeu utilisé, la mesure et le seuil de réussite. Puis le résultat, tel quel.
- Étiquettes : [O] observé, [S] source, [H] hypothèse, [M] mesuré (commande + fichier de sortie).
- **Aucun réglage sur un test. Aucun score annoncé sans fichier de sortie.** Un rapport n'est pas une preuve : l'orchestrateur relit les fichiers.
- Processeur à 8 cœurs, pas de GPU local : garder les calculs raisonnables (sous-échantillonner si besoin, en le disant).

## 2. Données et rôles

| Données | Chemin | Rôle |
| --- | --- | --- |
| Tanzanie 2021 + Pérou (entraînement de la v2 et de la v5) | `data/feuilles/index.csv` (`ensemble == entrainement`, `retenue`), images `data/feuilles/<chemin>` | **développement** (réglages libres) |
| TDTU (Vietnam) et khadavy (Indonésie), ajouts de la v5 | `data/feuilles_v3_ajouts/images.csv` et `images/` | **développement** (réglages libres ; khadavy a déjà servi de test le 8 novembre, il ne départage plus rien) |
| Tanzanie 2022-2023, 3 001 images | `data/feuilles/index.csv` (`ensemble == validation`) | **validation** : choix entre méthodes, une règle écrite avant |
| BananaLSD (Bangladesh, 897) | `data/feuilles/index.csv` (`ensemble == test`, source bananalsd) | **validation hors domaine** (déjà consultée) |
| ROAMER Mindanao, feuilles segmentées vues de loin | `data/roboflow_maladies/nouveaux/roamer_feuilles_*.zip` **sauf laguna** (COCO, polygones « positive » = feuille malade, « negative » = feuille saine) | **développement « de loin »** |
| ROAMER Laguna | `roamer_feuilles_laguna_leaf_segmentation.zip` | **test « de loin », figé par l'évaluateur. Personne d'autre ne l'ouvre.** |
| banana-buddy (test de la v5) | `data/test_banana_buddy/` | **interdit** |
| Cordana du Pérou (`test_perou`) | — | **interdit** |

## 3. Modèles de référence

- **v2 ConvNeXt** (binôme, modèle de la chaîne) : `modeles/maladies_binome/maladies_v2/` (`classifieur.py`, `poids/`, `seuils.json` ; classes saine, black_sigatoka, fusarium ; environ 0,8 s par photo sur processeur).
- **B0** : `modeles/maladies/maladies_v2.onnx` et `fieldscan/modules/maladies.py` (35 ms par photo).
- **v5** (en entraînement sur Kaggle, 4 classes avec autre_maladie) : `modeles/maladies_v5_kaggle/` quand elle arrive.
- Faiblesses mesurées de la v2 (test khadavy, Indonésie) : 28 % des taches noires précoces nommées ; Sigatoka jaune nommée fusariose ; feuilles vues d'en dessous (ROAMER) presque toutes dites saines.

## 4. Équipe et propriété des fichiers

Chacun écrit **seulement** dans `out/maladies/equipe/<nom>/` et dans sa fiche `docs/maladies_equipe/<nom>.md`. Scripts dans `out/maladies/equipe/<nom>/` (pas dans `scripts/`).

| Agent | Mission |
| --- | --- |
| `evaluateur` | fige le test « de loin » (Laguna), écrit le code d'évaluation commun, contrôle les fuites, fait seul les mesures sur le test |
| `math-couleur` | indices de couleur et de texture explicites (chlorose, nécrose, taches), classifieur sans apprentissage profond |
| `math-forme` | forme et orientation des lésions (stries parallèles aux nervures, taches rondes, jaunissement des bords), géométrie de la feuille |
| `vue-de-loin` | adapter la lecture aux photos de loin : découpe en tuiles, agrégation, zoom sur les feuilles, données ROAMER |
| `amelioration-modele` | recette d'entraînement, fusion maths + IA, calibration, préparation d'une version suivante |

Les demandes entre agents passent par l'orchestrateur.
