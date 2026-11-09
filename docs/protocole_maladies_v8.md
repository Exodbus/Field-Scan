# Protocole du classifieur de maladies v8 (recette de la v2 + feuilles vues de loin)

Écrit le 9 novembre 2026 vers 1 h 40, par l'orchestrateur de l'équipe maladies, **avant tout entraînement de la v8**, après le rejet de la v5 (`docs/protocole_maladies_v3_convnext.md`, section 9) et pendant que la v7 s'entraîne (aucun résultat de la v7 connu). Carte blanche de Corentin pour la nuit, sans commit. Toute modification ultérieure est datée et justifiée ; aucune ne peut suivre un résultat de la v8.

## 0. Pourquoi

La v5 (v2 + khadavy + TDTU + classe « autre maladie ») est rejetée : plus de fausses alertes, et sa classe « autre » range encore plus de maladies inconnues dans la Sigatoka. La v7 garde ces ajouts : elle risque d'échouer de la même façon. La v8 **isole le levier « vue de loin »** : recette et classes de la v2, plus seulement les feuilles ROAMER vues de loin et les augmentations « de loin ».

## 1. Données et recette

- Tanzanie 2021 + Pérou (archive `feuilles_pret_perou`, 16 963 images) ; **ni khadavy, ni TDTU** ; **3 classes** (saine, black_sigatoka, fusarium).
- Recadrages ROAMER de `dev_loin` (jeu `roamer_recadrages_v7`, préparé sans modèle, section 1 du protocole v7) **réduits aux classes de la v8** : fusarium_leaf (324 fusarium, 361 saines) et feuilles saines de moko_leaf (161) ; les 244 feuilles Moko malades sont retirées. Liste d'exclusion `val_loin` inchangée.
- Recette de la v7 pour le reste : ConvNeXt-Tiny, 6 époques, 3 réseaux, ROAMER à 10 % des tirages, basse résolution (p = 0,3), flou jusqu'à σ = 3, mosaïque 2 × 2 (p = 0,15), précision mixte ; seuils réglés sur la validation tanzanienne (3 001) par les règles de la v2.
- Carnet : `notebooks/entrainer_maladies_v8_kaggle.py` (copie du carnet v7, changements ci-dessus seulement). Un seul entraînement.

## 2. Adoption (règle écrite avant)

Exactement la règle de la v7 (`docs/protocole_maladies_v7.md`, section 3), avec la v2 comme modèle de référence :

1. non-régression sur la validation tanzanienne et BananaLSD (conditions de la section 5 du protocole de la v5) ;
2. sur `val_loin` (mesure unique, niveau feuille) : feuilles malades dites malades au moins **+10 points** par rapport à la v2, fausses alertes au plus **+5 points**.

**Si la v7 et la v8 sont toutes deux adoptables**, celle qui entre dans la chaîne est celle qui a le plus fort gain de feuilles malades dites malades sur `val_loin` ; à égalité (écart inférieur à 2 points), la v8, plus simple. Règle écrite avant tout résultat de l'une ou de l'autre.

## 3. Résultats

**Entraînement** (Kaggle `affilecorentin/entrainer-maladies-v8`, un seul, terminé vers 2 h 30) : 846 recadrages ROAMER ; règles de la v2 : moyenne des 3 réseaux, 4 vues ; seuils alerte 0,60, nom 0,50, confiance 0,608. SHA-256 des poids cd55dffb…, 41e76e1c…, dfd5d60c… ; `seuils.json` e7c107c7….

**Adoption** (9 novembre vers 3 h, même carnet et même script que la v7, référence v2) :

| Condition | v2 | v8 | Verdict |
| --- | --- | --- | --- |
| Validation : malades dites saines | 0,2 % | 0,4 % | OK |
| Validation : fausses alertes | 0,7 % | 1,2 % | OK |
| Validation : maladie nommée juste | 97,6 % | 96,5 % | OK |
| BananaLSD : Sigatoka nommée | 94,1 % | 95,1 % | OK |
| BananaLSD : saines bien classées | 95,6 % | 95,6 % | OK |
| BananaLSD : inconnues dites saines | 0 % | 0 % | OK |
| `val_loin` : feuilles malades dites malades (≥ v2 + 10 points) | 46,3 % | 18,8 % (313 / 1 668) | **échec** |
| `val_loin` : feuilles saines dites malades (≤ v2 + 5 points) | 26,1 % | 6,0 % (81 / 1 346) | OK |

**La v8 n'est pas adoptée** (condition « de loin » non remplie). Ni la v7 ni la v8 n'étant adoptables, **la v2 reste dans la chaîne**.

Indicatif, sans effet sur la décision :
- AUC « de loin » : v8 0,600 [0,568 ; 0,632] contre 0,672 pour la v2. La v8 est beaucoup plus prudente de loin, et sépare moins bien malades et saines.
- La v8 passe toute la non-régression et fait un peu mieux que la v2 sur les gros plans hors domaine : BananaLSD Sigatoka nommée 95,1 % contre 94,1 % ; banana-buddy (jeu consulté) fausses alertes 1,3 % contre 3,9 %, fusariose nommée 76,6 % contre 72,9 %, maladie à taches dite malade 91,1 % contre 81,5 % (9 novembre : alerte de fuite du binôme vérifiée, les copies trouvées sont déjà exclues de la liste ; voir `docs/protocole_maladies_v3_convnext.md`, section 9). Mais elle range davantage les maladies inconnues de BananaLSD dans la Sigatoka (86,2 % contre 68,9 %) et les signale moins comme non identifiées (5,4 % contre 20,7 %).
- Une adoption de la v8 « pour les gros plans » serait une décision prise après avoir vu ces résultats, en partie sur un jeu consulté : elle n'est pas prise ici et revient à Corentin.
