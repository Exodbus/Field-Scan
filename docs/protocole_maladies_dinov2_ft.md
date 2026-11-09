# Protocole : fine-tuning de DINOv2 (recette de la v2, seul le réseau change)

Écrit le 9 novembre 2026, vers 15 h, par Claude, à la demande de Corentin (« Oui, prépare-le »), **avant tout entraînement**. Il fait suite au diagnostic DINOv2 (`docs/protocole_maladies_dinov2.md`, section 6). Une sonde sur DINOv2 figé y bat la même sonde sur le ConvNeXt ImageNet de la v2 (+6,8 points sur BananaLSD, +8,5 en validation), mais reste sous la v2 fine-tunée. Les résultats de la v2, de la v8 et de la soupe v2 + v8 sont connus. Le nom « v10 » est laissé au binôme ; ce modèle s'appelle **« DINOv2-FT »**.

## 0. Pourquoi

Toutes nos versions partent du même ConvNeXt-Tiny ImageNet. Le diagnostic montre que DINOv2 donne, sans réglage, de bien meilleures caractéristiques. [H] Fine-tuné avec la recette de la v2, il pourrait mieux tenir hors domaine : BananaLSD, et plus tard d'autres pays. Le diagnostic n'a pas montré qu'il règle les maladies inconnues : la règle ci-dessous contient donc une garde sur ce point.

## 1. Données (celles de la v2)

- Apprentissage : Tanzanie 2021 + Pérou (16 963 photos), 3 classes (saine, black_sigatoka, fusarium), Pérou tiré 3 fois plus souvent. Ni khadavy, ni TDTU, ni ROAMER.
- Validation : Tanzanie 2022-2023 sur place (3 001), pour les seuils et la non-régression.
- Mesure : BananaLSD (897) et feuilles de `val_loin` (3 014). Seules les probabilités sont écrites par le carnet ; aucun score n'est affiché.
- Jamais lus : twakihasan, banana-buddy, la Cordana du Pérou, khadavy.

## 2. Recette

Celle de la v2 (`notebooks/entrainer_maladies_v5_kaggle.py` sans ajouts) pour les données, la préparation (224 px, JPEG 95), les augmentations (recadrage 0,4 à 1, miroirs, rotation 30°, couleurs, flou noyau 5 σ ≤ 2, JPEG aléatoire, zone masquée), le lissage des étiquettes (0,1), les 3 réseaux (graines 0, 1, 2), la dernière époque gardée et les règles de seuils. Seuls changent les points suivants, imposés par le réseau :

| Point | v2 | DINOv2-FT |
| --- | --- | --- |
| Réseau | ConvNeXt-Tiny ImageNet | **DINOv2 ViT-B/14** (`facebookresearch/dinov2`, `dinov2_vitb14`) ; tête linéaire à 3 classes sur [jeton de classe, moyenne des jetons d'image] (1 536) |
| Apprentissage | 6 époques, AdamW 1e-4, décroissance 1e-4 | **LP-FT** : 1 époque avec le réseau figé et la tête seule (AdamW 1e-3) ; puis 6 époques avec tout le réseau, AdamW (réseau 1e-5, tête 1e-4), décroissance 0,05, cosinus, gradients bornés à 1 |
| Calcul | 32 bits | précision mixte 16 bits sur GPU T4 |

Carnet : `notebooks/entrainer_maladies_dinov2_kaggle.py` (GPU, internet activé pour les poids DINOv2). Un seul entraînement. Une seule relance est permise, et seulement pour une panne technique (mémoire, perte non finie) ; elle sera notée ici.

## 3. Adoption (règle écrite avant)

Référence : **la v2** (modèle de la chaîne), ses réponses étant celles des fichiers GPU de la nuit. DINOv2-FT est adoptable s'il remplit toutes ces conditions :

1. les 6 conditions de non-régression face à la v2 (section 5 du protocole de la v5, `scripts/mesurer_adoption_v5.py`) ;
2. vue de loin : AUC de P(malade) sur les feuilles de `val_loin` ≥ AUC de la v2 − 0,02 ;
3. **garde sur les maladies inconnues** : sur BananaLSD, inconnues dites Sigatoka ≤ v2 + 5 points, soit au plus 246 / 334 ;
4. **gain** : rappel équilibré sur BananaLSD (moyenne de « Sigatoka nommée » et « saines bien classées ») ≥ v2 + 1 point, soit au moins 0,958.

**Départage avec la soupe v2 + v8**, adoptable selon son propre protocole (rappel équilibré BananaLSD 0,956) : si DINOv2-FT est adoptable, il est retenu à la place de la soupe seulement si son rappel équilibré sur BananaLSD dépasse celui de la soupe d'au moins 1 point (≥ 0,966). Sinon, la soupe reste, car elle coûte environ 4 fois moins de calcul. Dans tous les cas, l'intégration dans `fieldscan/` reste soumise à l'accord de Corentin.

Rapporté sans effet sur la décision : matrices de confusion, maladies inconnues dites malades non identifiées ou « je ne sais pas », courbe de coût en validation par époque.

**Note** : la liste des finalistes de twakihasan est close (v2, v2_384, v6, v8, soupe). DINOv2-FT n'y sera pas noté.

## 4. Ordre

1. Ce protocole, commité avant l'entraînement. Essai du carnet en local, avec un faux réseau et sans télécharger de poids, pour vérifier le code.
2. Entraînement Kaggle (un seul), puis récupération des sorties : poids, seuils, probabilités.
3. Mesure unique : `scripts/mesurer_dinov2_ft.py`, dont les résultats et la décision sont écrits en section 5.

## 5. Résultats (9 novembre 2026, vers 15 h 35, mesure unique)

**Entraînement** : Kaggle `affilecorentin/entrainer-maladies-dinov2-ft` (version 1, GPU T4, environ 1 h 30), un seul, sans relance. Pertes d'apprentissage de 0,39 (tête seule) à 0,30 (fin). Les règles de la v2 retiennent **un seul réseau et une seule vue** : coût en validation 55 pour un réseau, 56 pour la moyenne des trois. Seuils : alerte 0,35, nom 0,50, confiance 0,861. Le coût en validation par époque varie beaucoup (de 39 à 129). Sorties : `out/maladies/dinov2_ft/` ; mesure : `scripts/mesurer_dinov2_ft.py`, `out/maladies/dinov2_ft/bilan_dinov2_ft.json`.

| Condition | v2 | DINOv2-FT | Verdict |
| --- | --- | --- | --- |
| Validation : malades dites saines (≤ v2 + 0,5 point) | 4 / 2 001 | 9 | OK |
| Validation : fausses alertes (≤ v2 + 1 point) | 7 / 1 000 | 6 | OK |
| Validation : maladie nommée juste (≥ 95 %) | 97,6 % | 97,3 % | OK |
| BananaLSD : Sigatoka nommée (≥ v2 − 2 points) | 445 / 473 | **457** | OK |
| BananaLSD : saines bien classées (≥ v2 − 2 points) | 86 / 90 | **88** | OK |
| BananaLSD : inconnues dites saines (≤ v2 + 1 point) | 0 / 334 | 1 | OK |
| AUC de loin (≥ v2 − 0,02) | 0,672 | 0,626 | **échec** |
| Garde : inconnues dites Sigatoka (≤ 246 / 334) | 230 | 284 | **échec** |
| Gain : rappel équilibré BananaLSD (≥ v2 + 1 point) | 0,948 | **0,972** | OK |

**DINOv2-FT n'est pas adoptable** : il échoue sur la vue de loin et sur la garde des maladies inconnues. Selon le départage, la soupe reste le candidat retenu.

Lecture, sans effet sur la décision :
- C'est **le meilleur modèle mesuré en gros plan hors domaine**. Sur BananaLSD, il nomme 457 Sigatoka sur 473 (contre 445 pour la v2 et 452 pour la soupe) et classe bien 88 saines sur 90, avec un seul réseau et une seule vue.
- Mais il aggrave les deux faiblesses connues. Il dit Sigatoka pour 85 % des maladies inconnues (v2 : 69 %) et n'en signale que 22 comme non identifiées (v2 : 69). Et il sépare moins bien les feuilles malades et saines vues de loin.
- **Défaut à écrire, même si la règle l'accepte** : en validation, DINOv2-FT rate 9 malades sur 2 001, contre 4 pour la v2. C'est la mesure que le tuteur surveille le plus.
- **Ce que deviennent les maladies inconnues** (BananaLSD, 334, ajouté le 9 novembre après une remarque du binôme, sans effet sur les décisions). Une inconnue dite Sigatoka déclenche quand même une alerte dans la chaîne. Une inconnue dite saine ou « je ne sais pas » n'en déclenche pas :

  | Modèle | Saine | Sigatoka | Fusariose | Je ne sais pas | **Alerte** |
  | --- | --- | --- | --- | --- | --- |
  | v2 | 0 | 230 | 35 | 69 | **265 (79 %)** |
  | v8 | 0 | 288 | 28 | 18 | **316 (95 %)** |
  | soupe | 0 | 273 | 28 | 33 | **301 (90 %)** |
  | DINOv2-FT | 1 | 284 | 27 | 22 | **311 (93 %)** |

  Vue du côté des alertes, les modèles qui nomment le plus souvent Sigatoka sont aussi ceux qui laissent le moins de maladies inconnues sans alerte. La garde « inconnues dites Sigatoka » mesure le mauvais nom, pas l'absence d'alerte. Les deux comptent : un nom faux oriente vers un mauvais traitement, une absence d'alerte laisse la maladie sans visite. Ce point rejoint le choix, encore ouvert, de déclencher ou non une alerte quand la réponse est « je ne sais pas » mais que la probabilité de maladie est forte.
- Sur ces quatre modèles proches (même apprentissage, même validation), on observe une **tendance** : mieux reconnaître les maladies connues hors domaine va avec plus d'inconnues dites Sigatoka et une vue de loin moins bonne. C'est une observation sur 4 modèles, pas une loi.
