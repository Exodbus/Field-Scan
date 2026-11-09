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

Si un candidat est adopté avant la note commune sur twakihasan, il sera proposé au binôme comme cinquième finaliste. Sinon, les finalistes restent v2, v2_384, v6 et v8.

## 5. Résultats

(à remplir)
