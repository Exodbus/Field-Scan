# v10b avec la règle B (11/11/2026)

## Contenu

- `modeles_maladies/` : les 3 poids de v10b (16 bits) et `seuils.json`. Seuils : alerte 0,725, nom 0,79, confiance 0,519. `"regle_b": true` (une feuille n'est dite saine que si P(saine) atteint 0,519, sinon « inconnu », qui donne une alerte). `"seuil_inconnu_malade": 0.675` (un « inconnu » avec 1 − P(saine) ≥ 0,675 devient « malade_non_identifiee »).
- `classifieur.py` : le classifieur du dépôt. `charger(dossier)` renvoie (membres, seuils), `probabilites(membres, photos)` un tableau (n, 4), `decider(probas, seuils)` une réponse par photo.
- `controle_v10b/` : 40 photos d'origine de BanSpot, 8 par réponse (saine, inconnu, malade_non_identifiee, black_sigatoka, fusarium), et `probas_v10b.csv` (chemin, 4 probabilités, réponse). Les probabilités sont calculées avec ce classifieur et ces poids, sur ces fichiers mêmes.
- `liste_apprentissage_v10.csv` : les 36 455 images de la v10, apprentissage et validation. Colonnes : jeu, classe, partie, chemin et nom dans le jeu d'origine, SHA-256 de la photo d'origine, SHA-256 de la copie en 448 px qui a servi à l'apprentissage.
- `banspot_liste_test.csv` : les 1 292 photos de BanSpot notées le 11/11 (2 fermes), avec leur chemin dans l'archive Zenodo.

## Le modèle

- Ordre des classes : saine, black_sigatoka, fusarium, autre.
- Réseau : timm `convnext_tiny.dinov3_lvd1689m` (timm 1.0.20 ou plus), 4 classes, créé avec `img_size=224` et `dynamic_img_size=True`, lu en 384 px.
- Préparation d'une photo : remise droite (EXIF), JPEG lu en au moins 896 px (`draft`), petit côté à 384 px puis recadrage carré au centre (`ImageOps.fit`, BILINEAR), réenregistrée en JPEG qualité 95, normalisation ImageNet.
- Probabilités : softmax, moyenne des 4 vues (identité, miroir gauche-droite, miroir haut-bas, rotation de 90°), puis moyenne des 3 réseaux.
- Décision : alerte si 1 − P(saine) ≥ 0,725 ; maladie nommée si la plus probable n'est pas « autre » et fait au moins 0,79 de 1 − P(saine), sinon malade_non_identifiee ; inconnu si la plus forte probabilité est sous 0,519 ; puis la règle B et le seuil 0,675 ci-dessus.

## Ce que la v10 a vu

| Jeu | Apprentissage | Validation |
| --- | --- | --- |
| tanzanie_2023 | 15 691 | 0 |
| perou (saines et Sigatoka seulement) | 1 268 | 0 |
| bananalsd | 670 | 223 |
| cm8zf62kzh | 3 750 | 1 251 |
| blade | 911 | 304 |
| godliver | 465 | 156 |
| tanzanie_2025 | 0 | 11 766 |

La validation sert à régler les seuils. La Cordana du Pérou n'a jamais été lue. PSFD, TDTU et l'Éthiopie n'ont jamais servi. cm8zf62kzh et BLADE rassemblent des photos dont je ne connais pas toutes les sources : les SHA-256 permettent de vérifier.

## À savoir

Mes évaluations (juges, test neuf du 10/11, BanSpot) lisaient des copies déjà réduites à 896 px de petit côté. Sur 300 photos de BanSpot tirées au hasard, les photos d'origine donnent des probabilités un peu différentes (écart moyen 0,010, jusqu'à 0,25), mais la même alerte pour 299 photos sur 300. Pour comparer à 10⁻³ près, il faut donc faire tourner la chaîne sur les photos fournies dans `controle_v10b/photos/`.

BanSpot : Zenodo, enregistrement 20098282 (https://zenodo.org/records/20098282), CC BY 4.0, environ 5,3 Go. Le téléchargement automatique est refusé, il faut passer par le navigateur.
