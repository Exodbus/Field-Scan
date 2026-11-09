# Protocole du classifieur de maladies v7 (feuilles vues de loin)

Écrit le 9 novembre 2026 vers 0 h 50, par l'orchestrateur de l'équipe maladies, **avant toute préparation des recadrages et tout entraînement de la v7**, pendant que la v5 s'entraîne encore (aucun résultat de la v5 connu). Corentin a donné carte blanche pour la nuit (versions, données, GPU), sans commit. Toute modification ultérieure est datée et justifiée ; aucune ne peut suivre un résultat de la v7.

## 0. Pourquoi

Objectif de Corentin : meilleur modèle, et meilleur sur les photos prises de loin. Constats de la nuit (`docs/maladies_equipe/journal.md`) :

- La v2 dit « saine » à la plupart des feuilles malades vues de loin (ROAMER Black-sigatoka : 113 sur 143 [M, `out/maladies/test_khadavy/bilan.json`]).
- Les méthodes mathématiques et leur fusion avec la v2 n'améliorent ni la validation ni BananaLSD (math-couleur, math-forme, amelioration-modele) : le levier restant est l'entraînement sur des données vues de loin.

La v7 reprend la recette de la v5 et ajoute des **feuilles vues de loin** et des **augmentations « de loin »**. Carnet : `notebooks/entrainer_maladies_v7_kaggle.py` (repris du brouillon de l'agent `amelioration-modele`, testé en local).

## 1. Données

- Comme la v5 : Tanzanie 2021 + Pérou (archive `feuilles_pret_perou`), khadavy + TDTU (`feuilles_v3_ajouts`).
- **Nouveau : recadrages ROAMER de Mindanao, partie `dev_loin` seulement** (découpage par scène figé par l'évaluateur : `out/maladies/equipe/evaluateur/decoupage_loin/dev_loin.csv`, SHA-256 46e4a558…). Jeux : `roamer_feuilles_fusarium_leaf.zip` (polygone « positive » → fusarium, « negative » → saine) et `roamer_feuilles_moko_leaf.zip` (« positive » → autre_maladie, « negative » → saine). Boîte du polygone élargie de 10 %, recadrage gardé s'il fait au moins 32 px de côté. Toute image de `val_loin` est exclue. Bunchy top écarté (tous ses polygones sont « positive » : l'étiquette désigne la plante).
- Jamais lus : banana-buddy, la Cordana du Pérou, Laguna, les jeux ROAMER téléphone, `val_loin`.

## 2. Recette

Celle de la v5 (ConvNeXt-Tiny ImageNet, 224 px, 6 époques, dernière gardée, lots de 32, taux 1e-4, lissage 0,1, 3 réseaux, 4 classes, Pérou ×3, autre_maladie 10 % hors ROAMER), plus :

- recadrages ROAMER tirés pour **10 %** des images de chaque époque ;
- **basse résolution** (p = 0,3, réduction d'un facteur 0,25 à 0,7 puis retour à 224 px) ; **flou** jusqu'à σ = 3 (noyau 7) ; **mosaïque 2 × 2** (p = 0,15 : l'image dans une case, trois feuilles saines autour, étiquette inchangée) ;
- précision mixte sur le GPU.

Seuils réglés sur la validation tanzanienne (3 001 images) par les règles de la v2, comme pour la v5. Un seul entraînement ; une relance seulement pour une panne technique, notée ici.

## 3. Adoption (règle écrite avant)

Modèle de référence : celui de la chaîne au moment de la décision (la v2, ou la v5 si elle a été adoptée selon son protocole). La v7 le remplace si **toutes** les conditions sont remplies :

1. **Non-régression** (mêmes mesures et mêmes seuils que la section 5 du protocole de la v5) sur la validation tanzanienne (3 001) et sur BananaLSD (897), mesurées en local par le même code, chaque modèle à ses propres seuils.
2. **Gain « de loin »** sur `val_loin`, mesuré **une seule fois** par l'évaluateur, au niveau de la feuille (recadrages des polygones des images de `val_loin`, même règle de recadrage qu'en section 1, sur les quatre jeux de feuilles : fusarium, moko, healthy, bunchytop) :
   - part des feuilles « positive » dites malades (n'importe quelle maladie ou « malade, non identifiée ») : au moins **+10 points** par rapport au modèle de référence ;
   - part des feuilles « negative » dites malades (fausses alertes) : au plus **+5 points**.

`val_loin` vient du même robot et des mêmes plantations que `dev_loin` : le gain mesuré est optimiste et sera écrit ainsi. Aucun test « de loin » vierge n'existe à ce jour.

## 4. Ordre

1. Recadrages `dev_loin` (sans modèle), effectifs notés ici ; carnet final ; jeu Kaggle.
2. Entraînement Kaggle (GPU), un seul.
3. Mesures de non-régression en local ; mesure `val_loin` par l'évaluateur ; décision écrite ici.

**Préparation (9 novembre 2026, vers 0 h 55, sans modèle)** : `scripts/preparer_recadrages_v7.py` → `data/roamer_recadrages_v7/` : 1 090 recadrages de 211 photos de `dev_loin` (fusarium_leaf : 324 fusarium, 361 saines ; moko_leaf : 244 autre_maladie, 161 saines) ; aucune clé de `val_loin` rencontrée ; liste d'exclusion `exclusions_roamer_val_loin.csv` (954 clés) jointe ; SHA-256 de `recadrages.csv` 3bf8d4b5…. Carnet final `notebooks/entrainer_maladies_v7_kaggle.py`, essai local réussi (`ESSAI_LOCAL=1`, 2 réseaux, 1 époque : ROAMER 10,0 % des tirages, autre_maladie 9,0 % hors ROAMER). Jeu Kaggle privé `affilecorentin/roamer-recadrages-v7` ; entraînement lancé vers 1 h 00 (`affilecorentin/entrainer-maladies-v7`, GPU, un seul).

## 5. Résultats

**Entraînement** (Kaggle `affilecorentin/entrainer-maladies-v7`, un seul, terminé vers 1 h 50) : 1 090 recadrages lus, 0 retiré par l'exclusion ; règles de la v2 : moyenne des 3 réseaux, 4 vues ; seuils alerte 0,80, nom 0,72. SHA-256 des poids 970c8c42…, bee98380…, 283ea11b… ; `seuils.json` 9add5477….

**Adoption** (9 novembre vers 3 h ; même carnet de prédiction GPU pour tous les modèles ; `scripts/mesurer_adoption_loin.py` → `out/maladies/kaggle_adoption_finale/bilan_adoption_loin.json`) : référence v2 (la v5 n'a pas été adoptée).

| Condition | v2 | v7 | Verdict |
| --- | --- | --- | --- |
| Validation : malades dites saines | 0,2 % | 0,5 % | OK |
| Validation : fausses alertes | 0,7 % | 2,9 % | **échec** |
| Validation : maladie nommée juste | 97,6 % | 95,8 % | OK |
| BananaLSD : Sigatoka nommée | 94,1 % | 90,7 % | **échec** |
| BananaLSD : saines bien classées | 95,6 % | 88,9 % | **échec** |
| BananaLSD : inconnues dites saines | 0 % | 0 % | OK |
| `val_loin` : feuilles malades dites malades (≥ v2 + 10 points) | 46,3 % (772 / 1 668) | 21,2 % (353 / 1 668) | **échec** |
| `val_loin` : feuilles saines dites malades (≤ v2 + 5 points) | 26,1 % (351 / 1 346) | 5,3 % (71 / 1 346) | OK |

**La v7 n'est pas adoptée.** Indicatif, sans effet : AUC « de loin » (P(malade), feuilles de `val_loin`, intervalle par bootstrap des groupes de scène) v2 0,672 [0,643 ; 0,698], v7 0,651 [0,624 ; 0,678] : l'apprentissage des feuilles ROAMER n'a pas amélioré la séparation malade / saine vue de loin. banana-buddy (jeu consulté) : fusariose nommée 5,3 % (v2 : 72,9 %) (9 novembre : alerte de fuite du binôme vérifiée, les copies trouvées sont déjà exclues de la liste ; voir `docs/protocole_maladies_v3_convnext.md`, section 9).
