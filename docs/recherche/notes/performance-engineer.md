# Notes de performance-engineer

## E-017 — Élève sur les pseudo-étiquettes du vote B′ : coût et nombre d'époques (7 novembre 2026)

Écrit **avant tout entraînement réel**, sur des étiquettes factices (points tirés au hasard). Aucune mesure de qualité ici.

### Code

- `comptage_math/eleve.py` : jeu de données (pseudo-étiquettes `image_path,x,y,z`, positifs z ≥ 2,238, disque ignoré de 0,5 m autour des 1,5 ≤ z < 2,238, fond ailleurs, poids nul hors du disque `masque_*` de `tuiles.csv` comme dans le v5), cible gaussienne σ = 0,3 m convertie en pixels par la résolution de chaque image (`cm_par_px` de `dev_dense_images.csv`, puis `out/comptage_math/evaluation/images_dense.csv`, sinon 5 cm/px avec avertissement), perte focale CenterNet (copie du v5), réseau resnet18 + FPN sortie au quart (copie du v5, poids ImageNet du cache local), AdamW, OneCycle 5 %, écrêtage 5, graine 2026, dernière époque retenue ; inférence : maxima locaux 3×3, plancher 0,05, NMS gloutonne 1,0 m ; seuil non supervisé.
- `scripts/math_eleve.py` : `entrainer`, `predire`, `seuil`, `essai-temps`.
- [O] Contrôle d'alignement : après miroir et quarts de tour, chaque pic de cible tombe sur le pixel marqué de l'image (8 tirages sur 8).
- [O] Test : `predire --modele imagenet` (réseau non entraîné) sur 5 images bv_b_train → CSV `image_path,x,y,score` valide (2 148 lignes, coordonnées dans [0 ; 512], scores dans [0 ; 1], aucune valeur manquante) : `out/comptage_math/performance-engineer/E-017/test_inference/`.
- [O] `seuil` sur l'essai factice : 1 152 détections retenues pour 1 152 points z ≥ 2,238 du « professeur » factice.

### Machine

Intel Core i7-1185G7 (4 cœurs physiques, 8 logiques), 31,4 Go de mémoire, Windows 11, Python 3.14.5, torch 2.14.1+cpu. Pendant les mesures, d'autres processus Python de l'équipe tournaient (production des pseudo-étiquettes) : les temps sont ceux d'une machine partagée.

### Mesures [M] E-017 (essai de temps)

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/math_eleve.py essai-temps --n 32 --epoques 3 --threads T --configs 512x8 384x8 --sortie out/comptage_math/performance-engineer/E-017/essai_temps_tT` (et un premier passage `essai_temps/` avec 384x16 et 320x16). 32 images bv_b_train de 512 px, 60 points factices par image, images gardées en mémoire.

| Découpe | Lot | Threads | s par image (entraînement) | Remarque |
| --- | --- | --- | --- | --- |
| 512 | 8 | 8 | 0,39 et 0,45 | deux passages |
| 512 | 8 | 4 | 0,42 | |
| 384 | 8 | 8 | 0,24 et 0,25 | |
| 384 | 8 | 4 | 0,24 | |
| 384 | 16 | 8 | 0,21 puis 0,76 | perturbé par un autre processus |
| 320 | 16 | 8 | 0,65 à 1,25 | perturbé par un autre processus |

- Lecture et augmentation des données : environ 6 % du temps d'une époque (num_workers = 0 suffit).
- Coût proportionnel au nombre de pixels : 384² / 512² = 0,56, et 0,245 / 0,42 ≈ 0,58.
- 8 threads n'apportent rien sur 4 (4 cœurs physiques) ; on garde `torch.set_num_threads(8)` comme demandé.
- Inférence : 0,12 à 0,13 s par image de 512 px (lot 8), 0,29 s avec 2 threads.
- Mémoire de pointe du processus : 1,79 à 1,87 Go. Avec 2 000 tuiles en mémoire (0,79 Mo chacune), prévoir environ 3,4 Go : sans risque sur 31 Go.

### Choix figés pour E-017 (tours 1 et 2, et le contrôle « demi-maille »)

- Découpe aléatoire de **384 px** dans chaque tuile de 512 px, **lot 8**, **8 threads**, une époque = un passage sur toutes les images de la réserve (dernier lot incomplet abandonné).
  Raison : même coût par pixel que 512 px, deux fois plus d'époques dans le budget et une translation aléatoire en plus ; le v5 utilisait 448 px.
- Coût retenu pour le budget : **0,30 s par image** (0,25 mesuré + 20 % de marge pour une machine partagée).
- Budget : 3 h = 10 800 s, moins 1 200 s réservés au chargement, à l'inférence sur la réserve (≈ 0,13 s par image) et à la marge, soit 9 600 s d'entraînement.
- **Règle du nombre d'époques**, appliquée au nombre d'images de la réserve `n` (fixé par la liste MD5 de convergence-engineer, avant tout résultat) :
  **N = min(30, ⌊9 600 / (0,30 × n)⌋)**.

| n (tuiles de la réserve) | N |
| --- | --- |
| 1 000 | 30 |
| 1 250 | 25 |
| 1 500 | 21 |
| 1 750 | 18 |
| 2 000 | 16 |

  Le plafond 30 est celui du v5. Le même N sert au tour 2 et au contrôle « demi-maille » (même réserve).
- Aucune époque n'est choisie sur des références : la dernière est retenue, quel que soit son résultat.

### Risques

- Machine partagée : un autre calcul lourd en parallèle peut doubler ou tripler le temps (mesuré ci-dessus jusqu'à 0,76 s par image). L'entraînement réel doit tourner seul ; sinon il dépasse 3 h (aucun arrêt automatique : `dernier.pt` et `historique.csv` sont écrits à chaque époque, la durée réelle est consignée).
- La découpe de 384 px ne voit que 56 % de chaque tuile par époque ; sur N époques chaque zone est vue en moyenne 0,56 N fois.
- Images sans `cm_par_px` dans les deux listes : résolution supposée de 5 cm/px, signalée dans le journal ; à vérifier sur la réserve réelle.
- Les points z < 1,5 éventuellement présents dans le CSV du professeur sont ignorés (ni positifs ni zone ignorée).
