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

## 5. Résultats

(à remplir)
