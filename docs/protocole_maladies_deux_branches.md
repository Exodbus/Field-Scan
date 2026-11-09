# Protocole : chaîne à deux branches (aiguilleur « loin / près ») et désaccord entre modèles

Écrit le 9 novembre 2026, vers 16 h, par Claude, à la demande de Corentin (« Oui, écris-le »). Choix d'architecture évoqué par Baptiste. Il est écrit **avant tout calcul** de ces essais : aucun aiguilleur n'est appris, et aucune prédiction de DINOv2-FT sur TDTU ni sur des photos de loin n'existe. Les résultats de la v2, de la soupe et de DINOv2-FT sur la validation, BananaLSD et `val_loin` sont connus. Cette architecture en est motivée, ce que la lecture finale devra rappeler. Les résultats de ConvNeXt-R ne sont pas connus.

## 0. Pourquoi

Avec la v8, la soupe et DINOv2-FT, on retrouve à chaque fois le même compromis : mieux reconnaître les maladies connues en gros plan hors domaine fait reculer la vue de loin et le traitement des maladies inconnues. DINOv2-FT est le meilleur en gros plan (rappel équilibré 0,972 sur BananaLSD), mais il échoue sur ces deux points.
- **Partie A, l'aiguilleur** : envoyer chaque photo à la branche qui lui convient. Une photo proche va au meilleur modèle de gros plan. Une photo de loin va à la v2, la meilleure de loin parmi nos modèles (AUC 0,672), avec un message « à confirmer par un gros plan ».
- **Partie B, le désaccord** : l'aiguilleur ne règle pas les maladies inconnues, qui sont photographiées de près. [H] Deux réseaux appris différemment (v2 ConvNeXt, DINOv2-FT) se contredisent plus souvent sur une maladie qu'aucun des deux n'a apprise. On n'avait pas encore testé ce signal : la classe « autre », puis les détecteurs sur la v2 et sur DINOv2, ont échoué.

## 1. Définitions et données (étiquettes par source, aucune annotation à la main)

- **Proche** : gros plan d'une partie de feuille, le limbe remplit le cadre. **Loin** : feuille entière ou plante entière, avec du décor autour.
- L'étiquette « loin / près » est celle de la source, vérifiée sur une planche avant tout calcul :

| Rôle | Proche | Loin |
| --- | --- | --- |
| Apprentissage de l'aiguilleur | apprentissage de la v2 : 500 photos par source et classe (graine 2026, mêmes photos que l'ajustement du détecteur) | photos entières du robot ROAMER de `dev_loin` (1 312) |
| Mesure de l'aiguilleur | validation tanzanienne (3 001) ; BananaLSD (897) | photos de **téléphone** ROAMER (bunchy top 139, saines 139, Sigatoka noire 143 : un autre appareil que le robot) ; Éthiopie 2021 (1 289 feuilles entières, déjà vues par l'ancien essai éthiopien) |
| Indicatif | — | photos entières du robot de `val_loin` (1 305 ; même robot que l'apprentissage, donc optimiste) |

- Choix du signal de désaccord (partie B) : TDTU, `autre_maladie` (655) contre `black_sigatoka` (404).
- Jamais lus : twakihasan, banana-buddy, la Cordana du Pérou, khadavy.

## 2. Partie A : l'aiguilleur

- Caractéristiques DINOv2 ViT-B/14 figées, comme dans le diagnostic DINOv2 : [jeton de classe, moyenne des jetons d'image], préparation de la v2, vue d'origine.
- Régression logistique à deux classes, avec la recette des sondes du diagnostic : centrage-réduction, L2 1e-4, L-BFGS. Les deux classes ont le même poids. Une photo est dite « loin » si P(loin) ≥ 0,5. Rien n'est réglé.
- **Réussite** si les quatre conditions sont remplies : au moins **95 %** de « proche » sur la validation et sur BananaLSD, chacune ; au moins **90 %** de « loin » sur le téléphone ROAMER et sur l'Éthiopie, chacun.
- Si l'aiguilleur réussit, la **branche « loin »** est proposée pour la chaîne : réponse de la v2, plus le message « photo prise de loin : à confirmer par un gros plan de la zone malade ». Ceci quelle que soit la branche « proche ». S'il échoue, il n'y a pas de deux branches. Le résultat est écrit comme une limite (une seule branche, avec le compromis connu).

## 3. Partie B : branche « proche » avec désaccord

- **Règle de désaccord (fixée, sans réglage)** : la réponse est celle de DINOv2-FT, avec ses seuils. Quand DINOv2-FT nomme une maladie (cercosporiose noire ou fusariose) et que la v2, avec ses propres seuils, ne donne pas ce même nom, la réponse devient « malade, non identifiée ». L'alerte est gardée.
- **Contrôle sur TDTU, avant toute mesure sur BananaLSD** : parmi les photos que DINOv2-FT nomme, la part qui perd son nom doit être plus grande d'au moins **20 points** pour `autre_maladie` que pour `black_sigatoka`. Sinon, la partie B s'arrête là, sans mesure.
- **Adoption de la branche « proche »** (DINOv2-FT + désaccord) si les conditions suivantes sont remplies :
  - les 6 conditions de non-régression face à la v2 ;
  - la garde : inconnues de BananaLSD dites Sigatoka au plus 246 / 334 ;
  - le gain : rappel équilibré sur BananaLSD ≥ v2 + 1 point.

  La vue de loin n'est pas une condition ici : c'est la branche « loin » qui la traite.
- **Départage** avec la soupe, retenue jusqu'ici en gros plan (rappel équilibré 0,956). La branche « proche » fait tourner deux modèles, la v2 et DINOv2-FT : elle ne remplace la soupe que si elle la dépasse d'au moins 1 point (≥ 0,966).

## 4. Calculs et ordre

1. Ce protocole, commité avant tout calcul ; planche de contrôle des sources « loin » et « proche ».
2. Jeu Kaggle privé avec les photos de loin (robot `dev_loin` et `val_loin`, téléphone ROAMER, Éthiopie), puis un carnet Kaggle (GPU, internet pour les poids DINOv2). Le carnet calcule :
   - les caractéristiques DINOv2 figées de ces photos ;
   - les probabilités de la v2 et de DINOv2-FT sur TDTU.

   Il n'affiche aucun score.
3. Mesure unique en local : `scripts/mesurer_deux_branches.py`. Résultats et décision écrits en section 5.

Toute intégration dans `fieldscan/` reste soumise à l'accord de Corentin.

**Amendement 1 (9 novembre 2026, vers 16 h 10, après la planche de contrôle des sources et avant tout calcul)** : la planche (`out/maladies/deux_branches/planche_sources.jpg`) montre deux sortes de photos de loin :
- des **plantes entières** : le robot, et les dossiers bunchy top et saines du téléphone ROAMER ;
- des **feuilles entières souvent cadrées serré**, à mi-chemin : l'Éthiopie et le dossier Sigatoka noire du téléphone ROAMER.

La condition « au moins 90 % de loin » s'applique donc au seul **téléphone ROAMER bunchy top + saines (278)**. L'Éthiopie et la Sigatoka noire du téléphone sont **rapportées à titre indicatif**, comme cas intermédiaires. Le reste du protocole est inchangé.

## 5. Résultats

(à remplir)
