# Protocole : mélange v2 + v8 et détecteur de nouveauté sur la v2

Écrit le 9 novembre 2026, en fin de matinée, par Claude, à la demande de Corentin. Il est écrit **avant tout calcul de ces essais** : aucune probabilité de la soupe, aucune caractéristique interne de la v2 et aucun score de mélange n'existent encore. Les résultats séparés de la v2 et de la v8 sont connus (`docs/protocole_maladies_v8.md`). Ces essais sont motivés par ces résultats, ce que la lecture finale devra rappeler. Aucun entraînement. Les noms v10 et suivants sont laissés au binôme : ses essais en cours s'appellent « mélange » et « nouveauté ».

## 0. Pourquoi

- La v8 a passé toute la non-régression et fait un peu mieux que la v2 sur les gros plans hors domaine (BananaLSD : Sigatoka nommée 95,1 % contre 94,1 %), mais moins bien de loin. Les deux modèles partent des mêmes poids ImageNet et suivent la même recette. **Partie A** : les combiner sans réentraîner, en moyennant soit leurs probabilités, soit leurs poids (« soupe »).
- La v2 donne un nom de maladie connue aux maladies qu'elle n'a jamais vues : 69 % des maladies inconnues de BananaLSD sont dites Sigatoka. La classe « autre maladie » apprise (v5, v7) a aggravé ce défaut. **Partie B** : détecter ces photos à partir des caractéristiques internes de la v2, sans classe apprise, et leur retirer le nom (« malade, non identifiée »).

## 1. Données (aucun nouveau jeu)

| Rôle | Jeu | Photos |
| --- | --- | --- |
| Réglage des seuils et non-régression | validation tanzanienne (`data/feuilles/images/validation`) | 3 001 |
| Non-régression hors domaine, maladies inconnues | BananaLSD (`data/feuilles/images/test`) | 897 |
| Vue de loin (partie A seulement) | feuilles de `val_loin` (`data/roamer_val_loin_feuilles`) | 3 014 |
| Ajustement du détecteur (partie B) | apprentissage de la v2 (`data/feuilles/images/entrainement`) : 500 photos tirées par source et classe (graine 2026), soit 2 500 | 2 500 |
| Choix de la variante du détecteur (partie B) | TDTU (`data/feuilles_v3_ajouts`) : `autre_maladie` (inconnues pour la v2) contre `black_sigatoka` (connue) | 655 + 404 |

Jamais lus : twakihasan, banana-buddy, la Cordana du Pérou. khadavy n'est pas utilisé (accord avec le binôme : test déjà mesuré, il ne sert pas à départager).

Probabilités de la v2 et de la v8 : celles déjà calculées sur GPU (`out/maladies/kaggle_adoption_finale/predictions_{v2,v8}_{validation,bananalsd,val_loin_feuilles}.csv`, 3 réseaux × 4 vues). La référence reste **la v2 avec son `seuils.json`**, c'est-à-dire ses réponses déjà écrites dans ces fichiers.

## 2. Partie A : mélange et soupe v2 + v8

**Candidats** (3 réseaux, 4 vues, sans autre choix) :

- **A1, mélange** : moyenne des probabilités de la v2 et de la v8 ;
- **A2, soupe** : pour k = 1, 2, 3, réseau k = moyenne, paramètre par paramètre, du réseau k de la v2 et du réseau k de la v8 (appariés par numéro de fichier). Prédictions en local sur processeur, avec la préparation de la v2 (`classifieur.preparer`). Contrôle avant tout calcul : la v2, recalculée en local sur 8 photos de chaque jeu, doit redonner les probabilités des fichiers GPU à 10⁻³ près ; sinon on arrête et on le note ici.

**Seuils** de chaque candidat, réglés sur la validation par les règles de la v2 (code du carnet v8, section 7) :
- seuil d'alerte : celui qui rend minimal 2 × ratées + fausses alertes, sur la grille 0,05 à 0,95 au pas de 0,05 ;
- seuil de nom : le plus petit, à partir de 0,50, qui donne au moins 95 % de noms justes ;
- seuil de confiance : celui qui garde 95 % des photos.

**Adoption** (règle écrite avant). Un candidat est adoptable s'il remplit :

1. les 6 conditions de non-régression face à la v2 (section 5 du protocole de la v5, `scripts/mesurer_adoption_v5.py`) ;
2. vue de loin : AUC de P(malade) sur les feuilles de `val_loin` ≥ AUC de la v2 − 0,02 ;
3. gain : BananaLSD, Sigatoka nommée ≥ v2 + 1 point (au moins 450 / 473).

Si A1 et A2 sont tous deux adoptables, on retient celui qui nomme le plus de Sigatoka sur BananaLSD. Si l'écart est inférieur à 1 point, on retient A2, deux fois moins coûteux à calculer. Rapporté sans effet sur la décision : maladies inconnues de BananaLSD dites Sigatoka, et matrices de confusion.

## 3. Partie B : détecteur de nouveauté sur la v2

**Caractéristiques** : pour chacun des 3 réseaux de la v2, l'entrée de la dernière couche (768 valeurs) et les sorties brutes (logits), vue d'origine seulement, préparation de la v2.

**Ajustement**, sur les 2 500 photos de la section 1 et pour chaque réseau : une moyenne par classe, et une covariance commune réduite vers l'identité. La réduction est fixée sans réglage : Σ' = 0,9 Σ + 0,1 (trace(Σ) / 768) I.

**Variantes de score** (plus haut veut dire plus nouveau ; moyenne des 3 réseaux) :

| | Score |
| --- | --- |
| a | 1 − plus forte probabilité (vue d'origine) : la référence, proche du « je ne sais pas » actuel |
| b | énergie : − log Σ exp(logits) |
| c | Mahalanobis : plus petite distance aux 3 classes |
| d | Mahalanobis relative : plus petite valeur, sur les 3 classes, de (distance à la classe − distance à la gaussienne globale de l'ajustement) |

**Choix de la variante, sur TDTU seulement** : la plus forte AUC entre `autre_maladie` (655) et `black_sigatoka` (404). Si deux variantes sont à moins de 0,01 l'une de l'autre, on retient la plus simple, dans l'ordre a, b, c, d.

**Seuil** : le quantile 98 % du score de la variante retenue sur la validation (3 001, maladies connues), fixé sans regarder BananaLSD.

**Décision** : quand la v2 nomme une maladie (cercosporiose noire ou fusariose) et que le score dépasse le seuil, la réponse devient « malade, non identifiée ». L'alerte est gardée, seul le nom est retiré. Les autres réponses de la v2 ne changent pas. Le détecteur ne peut donc ni ajouter, ni retirer une alerte.

**Adoption** du détecteur, ajouté à la v2 dans la chaîne (règle écrite avant) :

1. validation : part des malades qui reçoivent un nom ≥ v2 − 2 points, et maladie nommée juste ≥ 95 % ;
2. BananaLSD : Sigatoka nommée ≥ v2 − 2 points ;
3. gain : BananaLSD, maladies inconnues qui reçoivent un nom de maladie (Sigatoka ou fusariose) ≤ v2 − 10 points.

Les autres conditions de non-régression (malades dites saines, fausses alertes, saines bien classées, inconnues dites saines) ne peuvent pas bouger par construction : elles sont recalculées et rapportées. BananaLSD a déjà servi de juge de non-régression aux v5, v7 et v8. Il sert ici de juge une fois de plus, sans aucun réglage dessus.

## 4. Ordre

1. Ce protocole, commité avec l'accord de Corentin **avant toute lecture de score**.
2. Calculs sans lecture de score : `scripts/extraire_caracteristiques_v2.py` (caractéristiques et logits) et `scripts/predire_soupe_v2_v8.py` (probabilités de la soupe). Ces deux scripts n'affichent aucun score.
3. Mesure unique : `scripts/mesurer_melange_nouveaute.py`, dont les résultats et la décision sont écrits en section 5.

**Amendement 1 (9 novembre 2026, vers 12 h 55, avant tout résultat ; seul le lieu du calcul change, aucune règle ne change).** À la demande de Corentin, les calculs de l'étape 2 passent du processeur local à un GPU Kaggle. Le calcul local a été arrêté avant d'avoir écrit le moindre fichier. Le carnet `notebooks/predire_melange_nouveaute_kaggle.py` (Kaggle `affilecorentin/predire-melange-nouveaute`) fait les mêmes calculs que les deux scripts, avec les mêmes listes, le même ordre, la même préparation et le même tirage d'ajustement. Le contrôle de la préparation est conservé : le carnet calcule la v2 sur les 8 premières photos de chaque jeu, et la comparaison avec les fichiers GPU de la nuit (écart ≤ 10⁻³) se fait en local avant la mesure. Correction technique du script local : chemin des images TDTU (préfixe `ajouts_v3/` retiré).

Si un candidat est adopté avant la note commune sur twakihasan, il sera proposé au binôme comme cinquième finaliste. Sinon, les finalistes restent v2, v2_384, v6 et v8.

## 5. Résultats (9 novembre 2026, vers 13 h 10, mesure unique)

**Calculs** : carnet Kaggle `affilecorentin/predire-melange-nouveaute` (version 1, GPU). Contrôle de la préparation : la v2 recalculée sur les 8 premières photos de chaque jeu redonne exactement les probabilités de la nuit (écart 0). La soupe est calculée sur les mêmes photos, dans le même ordre. Mesure : `scripts/mesurer_melange_nouveaute.py`, sortie dans `out/maladies/melange/bilan_melange_nouveaute.json`.

### Partie A

Seuils réglés sur la validation : mélange (alerte 0,50, nom 0,50, confiance 0,655), soupe (alerte 0,55, nom 0,50, confiance 0,680).

| Condition | v2 | A1 mélange | A2 soupe |
| --- | --- | --- | --- |
| Validation : malades dites saines (≤ v2 + 0,5 point) | 4 / 2 001 (0,2 %) | 6 (0,3 %) | 4 (0,2 %) |
| Validation : fausses alertes (≤ v2 + 1 point) | 7 / 1 000 (0,7 %) | 1 (0,1 %) | 9 (0,9 %) |
| Validation : maladie nommée juste (≥ 95 %) | 97,6 % | 97,6 % | 97,3 % |
| BananaLSD : Sigatoka nommée (≥ v2 − 2 points) | 445 / 473 (94,1 %) | 444 (93,9 %) | 452 (95,6 %) |
| BananaLSD : saines bien classées (≥ v2 − 2 points) | 86 / 90 | 87 | 86 |
| BananaLSD : inconnues dites saines (≤ v2 + 1 point) | 0 / 334 | 0 | 0 |
| AUC de loin, `val_loin` (≥ v2 − 0,02) | 0,672 | 0,662 | 0,655 |
| **Gain : BananaLSD, Sigatoka nommée ≥ 450 / 473** | — | **échec** (444) | **OK** (452) |

**Selon la règle, le mélange n'est pas adoptable, la soupe l'est, et c'est elle qui est retenue.**

Rapporté sans effet sur la décision, et à écrire avec le résultat :
- Le gain est petit : 7 Sigatoka de plus sur 473. En paires, la soupe a raison et la v2 tort pour 9 photos, et l'inverse pour 2 (test de McNemar exact, calculé après la mesure, à titre indicatif : p ≈ 0,07).
- **La soupe aggrave le défaut des maladies inconnues** : sur BananaLSD, elle en dit 273 / 334 Sigatoka (81,7 %), contre 230 (68,9 %) pour la v2, et elle n'en signale que 33 comme non identifiées ou « je ne sais pas », contre 69 pour la v2. Le mélange fait de même, à un degré moindre (259 et 47). C'est le défaut déjà connu de la v8, transmis aux deux combinaisons.
- La règle a été écrite en connaissant les résultats séparés de la v2 et de la v8 : le gain n'est pas une découverte, il retrouve le petit avantage de la v8 en gros plan, sans perdre autant de loin.

### Partie B

AUC sur TDTU (`autre_maladie` contre `black_sigatoka`) : a 0,477 ; b 0,394 ; c 0,517 ; d 0,515. **Aucune variante ne sépare les maladies inconnues des Sigatoka mieux que le hasard.** La règle retient la variante c (Mahalanobis), avec un seuil de 17 326 (quantile 98 % de la validation).

| Condition | v2 | v2 + détecteur | Verdict |
| --- | --- | --- | --- |
| Validation : malades qui reçoivent un nom (≥ v2 − 2 points) | 1 894 / 2 001 (94,7 %) | 1 853 (92,6 %) | **échec** |
| Validation : maladie nommée juste (≥ 95 %) | 97,6 % | 97,6 % | OK |
| BananaLSD : Sigatoka nommée (≥ v2 − 2 points) | 94,1 % | 93,2 % | OK |
| **Gain : BananaLSD, inconnues nommées (≤ v2 − 10 points)** | 265 / 334 (79,3 %) | 263 (78,7 %) | **échec** |

**Le détecteur n'est pas adopté.** Dans l'espace des caractéristiques de la v2, les maladies inconnues ne sont pas plus loin des classes apprises que les maladies connues prises dans un autre pays. La v2 ne « voit » pas qu'une maladie est nouvelle : elle la projette sur la classe connue qui lui ressemble le plus. Avec la classe « autre » (v5, v7) qui a échoué, c'est la deuxième méthode qui ne règle pas ce défaut. Il est à écrire comme une limite.

### Conséquences

- Selon la règle, **la soupe v2 + v8 remplace la v2** comme modèle de gros plan. Elle a le même coût de calcul que la v2 : 3 réseaux, 4 vues. Son intégration dans la chaîne (`fieldscan/`) reste soumise à l'accord de Corentin, comme toute modification de l'existant. Elle est proposée au binôme comme **cinquième finaliste** de la note commune sur twakihasan, avec sa réserve sur les maladies inconnues.
- La recommandation de l'auteur est de **présenter la soupe et la v2 côte à côte sur twakihasan** avant de changer la chaîne. Le gain mesuré ici est petit et porte sur un seul jeu, BananaLSD, déjà consulté plusieurs fois. Le recul sur les maladies inconnues, lui, est net.
