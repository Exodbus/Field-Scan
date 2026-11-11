# Protocole : apprendre Cordana et Pestalotiopsis (5 classes), et module maladies à deux branches

Écrit le 10 novembre 2026, vers 1 h 20, par Claude, pendant la nuit de travail autonome demandée par Corentin (« fais-moi un module meilleur que celui qu'on a », « ne me demande rien »). **Écrit avant tout entraînement et avant toute prédiction sur les jeux neufs.** Ont déjà tourné : le téléchargement du jeu Mendeley `wfzpdmc5vx` et son contrôle de fuites. Pas de commit cette nuit, selon la consigne de la nuit précédente. Avant chaque mesure, l'empreinte SHA-256 de ce fichier et l'heure sont notées dans `docs/maladies_equipe/journal_nuit_9_10.md`.

Résultats déjà connus : v2, v8, soupe v2 + v8, DINOv2-FT, ConvNeXt-R, aiguilleur « loin / près », et les chiffres twakihasan du binôme (récap du 9 novembre). Le nouveau récap du binôme (artefact claude.ai) n'a pas pu être lu.

## 0. Pourquoi

- Le défaut principal de tous nos modèles : les maladies jamais apprises du Bangladesh (Cordana, Pestalotiopsis) sont dites « Sigatoka ». Quatre méthodes ont échoué : la classe « autre », le détecteur sur la v2, le détecteur sur DINOv2 et le désaccord entre deux modèles.
- [S] Fort et al. 2021 (NeurIPS, arXiv 2106.03004) : quelques exemples des classes proches suffisent à séparer des classes très voisines. Une seule image par classe fait passer l'AUROC de 85 % à 98,7 %.
- [O] Un jeu public, **Mendeley `wfzpdmc5vx`** (Shahrin, Daffodil International University, déc. 2024, CC BY 4.0), apporte ces deux maladies d'une autre source que BananaLSD. Il compte 424 photos (Cordana 100, Pestalotiopsis 117, Sigatoka 100, saines 107), prises dans d'autres districts (Noakhali, Rangamati, Bandarban, Chittagong), avec un téléphone Xiaomi, redimensionnées en 320 × 427.
- [H] Apprises comme classes, ces deux maladies seraient nommées, et ne seraient plus dites Sigatoka. Le jeu est pris **en entier, avec ses Sigatoka et ses saines**. Sinon, le style « photo du Bangladesh » serait lié à Cordana et à Pestalotiopsis, et ce raccourci enverrait les Sigatoka de BananaLSD vers ces deux classes.
- **Conséquence pour la lecture** : pour les nouveaux modèles, Cordana et Pestalotiopsis de BananaLSD ne sont plus des maladies inconnues. Elles deviennent un test, d'une autre source mais du même pays, de ces deux nouvelles classes. Le comportement face aux maladies vraiment inconnues se mesure sur d'autres jeux (section 3).

## 1. Données

- **Apprentissage** : celui de la v2, Tanzanie 2021 + Pérou (16 963 photos), plus `wfzpdmc5vx` sans les photos retirées par le contrôle de fuites. Une photo est retirée si elle est copie d'une référence (dHash ≤ 10 bits puis vignette ≤ 5, sous les 8 symétries). Références : index des feuilles avec tout BananaLSD et le Pérou, BDR, ajouts v3 (TDTU, khadavy), test khadavy, zips Roboflow, banana_buddy. Une photo est aussi retirée si elle a un double interne de classe différente. Tirage : Pérou × 3 (comme la v2), `wfzpdmc5vx` × 5.
- **5 classes** : saine, black_sigatoka, fusarium, cordana, pestalotiopsis.
- **Validation** (seuils, non-régression) : Tanzanie 2022-2023 (3 001), comme toujours.
- **Mesure**, avec probabilités seules, aucun score affiché par les carnets :
  - BananaLSD (897) ;
  - TDTU (Vietnam ; 1 636 photos, dont autre_maladie 655) ;
  - PSFD-Musa (Inde) : Sigatoka noire 474, Sigatoka jaune 264 ;
  - Éthiopie 2021 : Sigatoka 320, Xanthomonas 814, saines 155 (miniatures 150 × 113).
- **Jamais lus** : twakihasan, banana-buddy, la Cordana du Pérou, khadavy, BDR (test du binôme).

## 2. Candidats pour la branche « proche »

Existants (prédictions recalculées sur les jeux neufs, mêmes réglages) : **v2** (référence), **soupe v2 + v8**, **DINOv2-FT**.

Nouveaux, entraînés sur Kaggle avec les données de la section 1 et 5 classes, 3 réseaux chacun (graines 0, 1, 2), dernière époque gardée :

| Nom | Réseau | Recette |
| --- | --- | --- |
| **C5** | ConvNeXt-Tiny ImageNet | celle de la v2 : 6 époques, AdamW 1e-4, décroissance 1e-4, cosinus, lissage 0,1, augmentations de la v2 |
| **D5** | DINOv2 ViT-B/14 | celle de DINOv2-FT : LP-FT, 1 + 6 époques, précision mixte |
| **E5** | DINOv3 ViT-B/16 (`timm`, `vit_base_patch16_dinov3.lvd1689m`, poids non restreints, licence DINOv3 de Meta) | celle de DINOv2-FT, tête sur [jeton de classe, moyenne des jetons d'image]. Lancé seulement si un GPU Kaggle est libre avant 5 h. |

**Ensemble C5 + D5** : moyenne de leurs probabilités, avec leurs réglages respectifs (réseaux, vues), et seuils recalculés par les règles de la v2.

**Seuils, par les règles de la v2 sur la validation** :
- P(malade) = 1 − P(saine) ;
- alerte au coût minimal (2 × ratées + fausses alertes) ;
- nom = la maladie la plus probable (parmi les 4), donné si sa part dans P(malade) atteint le seuil de nom (95 % de noms justes en validation) ;
- confiance qui garde 95 % des photos ;
- un ou trois réseaux, une ou quatre vues.

La validation ne contient ni Cordana ni Pestalotiopsis : leurs noms suivent le même seuil commun.

## 3. Règle de choix (écrite avant)

Un candidat est **adoptable** pour la branche « proche » s'il remplit toutes les conditions suivantes. Les références sont celles de la v2, calculées avec les mêmes fichiers.

1. **Les 6 conditions de non-régression** face à la v2 (protocole v5, section 5) :
   - validation : malades dites saines ≤ v2 + 0,5 point ; fausses alertes ≤ v2 + 1 point ; nom juste ≥ 95 % ;
   - BananaLSD : Sigatoka nommée ≥ v2 − 2 points ; saines bien classées ≥ v2 − 2 points ; Cordana et Pestalotiopsis dites saines ≤ v2 + 1 point.
2. **Garde** : Cordana et Pestalotiopsis de BananaLSD dites Sigatoka ≤ 246 / 334, la même borne qu'avant.
3. **Gain** : rappel équilibré sur BananaLSD (moyenne de « Sigatoka nommée » et de « saines bien classées ») ≥ v2 + 1 point.
4. **Noms nouveaux fiables** : sur BananaLSD, parmi les photos nommées Cordana ou Pestalotiopsis, au moins 80 % sont bien de cette maladie. Cette condition vaut pour les modèles à 5 classes seulement.
5. **Maladies vraiment inconnues, pas de visite manquée** : la part dite saine ne dépasse pas celle de la v2 de plus de 2 points, sur chacun de ces trois jeux :
   - TDTU autre_maladie (655) ;
   - PSFD Sigatoka jaune (264) ;
   - Éthiopie Xanthomonas (814).
6. **Maladie connue dans un nouveau pays** :
   - part en alerte ≥ v2 − 2 points sur la Sigatoka noire de PSFD (474) et sur la Sigatoka d'Éthiopie (320) ;
   - fausses alertes sur les saines d'Éthiopie ≤ v2 + 5 points.

Les conditions 5 et 6 sont nouvelles. Elles portent sur des jeux où aucun de nos modèles n'a jamais été mesuré. Elles empêchent d'adopter un modèle qui ne gagnerait que sur BananaLSD, jeu déjà consulté de nombreuses fois.

**Choix** : parmi les candidats adoptables, celui qui a le meilleur rappel équilibré sur BananaLSD. Un écart de moins de 1 point départage par le coût de calcul : C5 avant D5 et E5, eux-mêmes avant l'ensemble. La soupe et DINOv2-FT sont jugés par la même règle, mais leurs résultats sur BananaLSD sont connus : ils échouent déjà à la garde (273 et 284 sur 334).

**Si aucun candidat n'est adoptable**, la branche « proche » est la **soupe**. Elle avait été adoptée par son propre protocole (`docs/protocole_maladies_melange_nouveaute.md`), qui ne comportait pas la garde. Sur twakihasan, la note unique du binôme, elle rate le moins de malades (2,7 % contre 4,4 % pour la v2). La garde sera écrite comme une limite.

Rapporté sans effet sur la décision :
- Cordana et Pestalotiopsis bien nommées sur BananaLSD ;
- matrices de confusion par jeu ;
- part de « je ne sais pas » ;
- coût en validation par époque.

## 4. Module (architecture de la chaîne)

Le **module maladies** est construit ainsi :
1. **Aiguilleur** « loin / près » : caractéristiques DINOv2 ViT-B/14 figées, puis régression logistique. Il est réussi selon `docs/protocole_maladies_deux_branches.md` et réajusté à l'identique (mêmes photos, même recette), avec ses coefficients enregistrés.
2. **Branche « loin »** : la v2, plus le message « photo prise de loin : à confirmer par un gros plan de la zone malade ».
3. **Branche « proche »** : le candidat retenu en section 3.
4. **Probabilités affichées** : mise à l'échelle de température, T réglé sur la validation (log-vraisemblance) pour le modèle de la branche « proche ». Les décisions ne changent pas.

Contrôle d'intégration : sur 20 photos de validation, les réponses de la chaîne doivent être identiques à celles des fichiers de prédiction du modèle retenu, avec des probabilités égales à 10⁻³ près.

## 5. Calculs et ordre

1. Contrôle des fuites de `wfzpdmc5vx` (`scripts/controle_fuites_mendeley_bd.py`), déjà lancé avant l'écriture de ce protocole.
2. Jeu Kaggle privé `maladies-nuit` : `wfzpdmc5vx` filtré, PSFD (Sigatoka noire et jaune), Éthiopie.
3. Carnet `notebooks/entrainer_maladies_cinq_classes_kaggle.py`, un par réseau de départ (C5, D5, puis E5). Il fait l'entraînement, les seuils, puis écrit les probabilités sur la validation, BananaLSD, TDTU, PSFD et l'Éthiopie. Une relance est permise pour une panne technique seulement, et notée ici.
4. Prédictions des modèles existants (v2, soupe, DINOv2-FT) sur TDTU, PSFD et l'Éthiopie, sur le processeur local, mêmes réglages.
5. Mesure unique : `scripts/mesurer_cinq_classes.py`. Résultats et décision en section 6.
6. Intégration du module dans `fieldscan/` (section 4), contrôle d'intégration, puis récapitulatif du matin.

**Amendement 1 (10 novembre 2026, vers 1 h 45, avant tout résultat de C5, D5 et E5 ; C5 et D5 tournent).** Kaggle refuse plus de 2 sessions GPU à la fois : E5 est lancé automatiquement dès que C5 ou D5 finit. Un quatrième candidat est ajouté pour le créneau GPU suivant :
- **L5** : DINOv2 **ViT-L/14** (`dinov2_vitl14`). Même recette et mêmes données que D5 ; tête sur [jeton de classe, moyenne des jetons d'image] (2 048). Seulement **2 réseaux** (graines 0 et 1), pour tenir dans la nuit : environ 3,3 fois le calcul d'un ViT-B. La règle de la v2 choisit entre un réseau et la moyenne des deux.
- Même règle de choix (section 3). Ordre de coût pour le départage à moins de 1 point : C5, puis D5 et E5, puis l'ensemble C5 + D5, puis L5.
- Si L5 finit après la mesure des autres candidats, il est mesuré à part, par le même script et la même règle. Le choix est alors refait avec tous les candidats.

## 6. Résultats (10 novembre 2026, vers 3 h 50, mesure unique ; L5 encore en cours)

**Calculs** :
- C5, D5 et E5 ont tourné sur Kaggle, sans relance d'entraînement. Le premier lancement de C5 et D5 s'est arrêté au démarrage, avant tout calcul, sur un nom de fichier (`images_ajouts.csv`).
- Réglages retenus par les règles de la v2 :

  | Modèle | Réseaux | Vues | Alerte | Nom |
  | --- | --- | --- | --- | --- |
  | C5 | 3 | 4 | 0,50 | 0,69 |
  | D5 | 3 | 1 | 0,60 | 0,70 |
  | E5 | 3 | 4 | 0,65 | 0,58 |

- Prédictions de la v2, de la soupe et de DINOv2-FT sur les jeux neufs : processeur local.
- Mesure : `scripts/mesurer_cinq_classes.py`. Sorties : `out/maladies/cinq_classes/bilan_cinq_classes.json` et `tableau_cinq_classes.csv`.

| Mesure | v2 | soupe | DINOv2-FT | C5 | D5 | E5 | C5 + D5 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Validation : malades dites saines | 4 / 2 001 | 4 | 9 | 9 | 10 | 7 | 8 |
| Validation : fausses alertes | 7 / 1 000 | 9 | 6 | 5 | 15 | 8 | 6 |
| BananaLSD : Sigatoka nommée | 445 / 473 | 452 | 457 | 402 | 423 | 445 | 429 |
| BananaLSD : saines bien classées | 86 / 90 | 86 | 88 | 87 | 87 | 86 | 87 |
| **Garde** : Cordana et Pestalotiopsis dites Sigatoka (≤ 246) | 230 / 334 | 273 | 284 | **109** | **124** | **119** | **132** |
| Cordana bien nommée | — | — | — | 39 / 162 | 36 | 33 | 46 |
| Pestalotiopsis bien nommée | — | — | — | 6 / 172 | 2 | 1 | 3 |
| Noms nouveaux justes (≥ 80 %) | — | — | — | 45 / 57 | 38 / 52 | 34 / 43 | 49 / 62 |
| Cordana et Pestalotiopsis en alerte | 265 / 334 | 301 | 311 | 216 | 228 | 193 | 214 |
| TDTU autre_maladie dite saine | 69 / 655 | **47** | 93 | 80 | 95 | 76 | 79 |
| PSFD Sigatoka jaune dite saine | 110 / 264 | **101** | 118 | 121 | 128 | 112 | 125 |
| Éthiopie Xanthomonas dite saine | 245 / 814 | **212** | 253 | 247 | 289 | 268 | 267 |
| PSFD Sigatoka noire en alerte | 138 / 474 | 161 | 197 | 176 | 206 | 156 | 167 |
| Éthiopie Sigatoka en alerte | 141 / 320 | 169 | 174 | 151 | 192 | 197 | 165 |
| Éthiopie saines en alerte | 1 / 155 | 1 | 0 | 1 | 0 | 0 | 0 |
| *Rapporté* : Sigatoka nommée TDTU / PSFD / Éthiopie | 85 / 63 / 38 | 114 / 132 / 50 | 136 / 176 / 92 | 101 / 63 / 60 | 133 / 138 / 112 | 134 / 61 / 112 | 119 / 112 / 94 |
| *Rapporté* : TDTU saines en alerte (sur 577) | 59 | 30 | 18 | 32 | 18 | 23 | 15 |
| Rappel équilibré BananaLSD (≥ 0,958) | 0,948 | 0,956 | 0,972 | 0,908 | 0,931 | 0,948 | 0,937 |

**Aucun candidat n'est adoptable.** Conditions en échec :

| Candidat | Conditions en échec |
| --- | --- |
| soupe | garde ; gain |
| DINOv2-FT | garde ; maladies inconnues dites saines (TDTU, Sigatoka jaune) |
| C5 | Sigatoka nommée ; gain ; Sigatoka jaune dite saine ; noms nouveaux 79 % |
| D5 | Sigatoka nommée ; gain ; inconnues dites saines sur les 3 jeux ; noms nouveaux 73 % |
| E5 | gain (0,948 contre 0,958 au moins) ; Xanthomonas dite saine (+ 2,8 points) ; noms nouveaux 79 % |
| C5 + D5 | Sigatoka nommée ; gain ; Sigatoka jaune et Xanthomonas dites saines ; noms nouveaux 79 % |

**Selon la section 3, la branche « proche » est la soupe.**

Lecture, sans effet sur la décision :
- **Apprendre Cordana et Pestalotiopsis divise par deux les maladies inconnues dites Sigatoka** : 109 à 132, contre 230 pour la v2. C'est la première méthode qui passe nettement la garde.
- Mais ces deux maladies ne sont pas vraiment apprises :
  - Cordana est bien nommée dans 20 à 28 % des cas seulement ;
  - Pestalotiopsis est presque jamais nommée (1 à 6 sur 172), et reste surtout dite Sigatoka (83 à 98) ;
  - le reste part en « je ne sais pas » (Cordana : 67 à 87), ce qui ne déclenche pas d'alerte. D'où moins d'inconnues en alerte (193 à 228, contre 265).

  Avec 99 Cordana et 117 Pestalotiopsis d'un seul jeu, le modèle apprend surtout que ce n'est pas de la Sigatoka, sans savoir dire ce que c'est. La Pestalotiopsis du jeu Mendeley ne ressemble pas assez à celle de BananaLSD.
- **La soupe est meilleure que la v2 sur tous les jeux neufs**, sans aucune exception :
  - moins de maladies inconnues dites saines (TDTU 47 contre 69, Sigatoka jaune 101 contre 110, Xanthomonas 212 contre 245) ;
  - plus de Sigatoka en alerte (PSFD 161 contre 138, Éthiopie 169 contre 141) et mieux nommée ;
  - deux fois moins de fausses alertes sur les saines de TDTU (30 contre 59).

  Elle n'échoue qu'à la garde et au gain, mesurés sur BananaLSD. Cela confirme, sur des jeux qu'aucun modèle n'avait vus, ce que montrait twakihasan.
- Les réseaux DINOv2 et DINOv3 nomment beaucoup mieux la Sigatoka dans les pays neufs (Éthiopie 92 à 112 contre 38 pour la v2). Mais ils laissent passer plus de maladies inconnues comme saines. C'est le même compromis que la nuit précédente.

**Amendement 2 (10 novembre 2026, vers 4 h, après la décision de la section 6 et avant tout calcul sur ce point) : « je ne sais pas » avec forte probabilité de maladie.** Corentin a laissé ce choix ouvert le 9 novembre, puis a donné carte blanche pour la nuit.

Avec la règle de la v2, une photo dont la plus forte probabilité est sous le seuil de confiance devient « je ne sais pas », et ne déclenche pas d'alerte, **même quand P(malade) dépasse le seuil d'alerte**. Exemple : une photo de démonstration avec P(malade) = 0,96 répond « je ne sais pas ». L'ancien classifieur B0 répondait dans ce cas « malade, non identifiée », avec une alerte.

- **Politique (b)** : dans la branche « proche », une photo « je ne sais pas » avec P(malade) ≥ seuil d'alerte devient « malade, non identifiée », donc déclenche une alerte. Les autres réponses ne changent pas.
- **Règle** : (b) est adoptée si, **sur la validation** (3 001), elle a un coût strictement plus bas que la règle actuelle (a). Le coût est celui qui fixe le seuil d'alerte : 2 × malades sans alerte + saines en alerte. Une photo « je ne sais pas » compte comme sans alerte.
- Rapporté sans effet sur la décision : fausses alertes et malades sans alerte en validation ; maladies inconnues en alerte sur BananaLSD, TDTU, PSFD et l'Éthiopie ; saines en alerte sur TDTU et l'Éthiopie.
- Déjà connu, pour la v2 et non pour la soupe, dans un calcul du 9 novembre : en validation, les fausses alertes passeraient de 0,7 % à 2,5 %.

**Résultat de l'amendement 2** (soupe, ses seuils : alerte 0,55 ; `scripts/mesurer_jnsp_alerte.py`, `out/maladies/cinq_classes/bilan_jnsp_alerte.json`) :

| Jeu | Malades sans alerte, (a) → (b) | Saines en alerte, (a) → (b) | Coût, (a) → (b) |
| --- | --- | --- | --- |
| **Validation** (décision) | 112 → **9** / 2 001 | 9 → 15 / 1 000 | 233 → **33** |
| BananaLSD | 50 → 0 / 807 | 0 → 3 / 90 | |
| TDTU | 435 → 187 / 1 059 | 30 → 90 / 577 | |
| PSFD | 490 → 332 / 738 | — | |
| Éthiopie | 592 → 346 / 1 134 | 1 → 2 / 155 | |

**La politique (b) est adoptée** : elle est intégrée à la branche « proche » de la chaîne (`maladies.jnsp_alerte: true`). Lecture :
- La mesure « malades dites saines » (4 sur 2 001) ne comptait pas les « je ne sais pas ». Or, avec la règle de la v2, **112 photos malades de la validation n'avaient pas d'alerte**. La politique (b) en rattrape 103, pour 6 fausses alertes de plus.
- Hors domaine, le gain en alertes est très fort : toutes les maladies inconnues de BananaLSD sont désormais en alerte, et TDTU passe de 435 à 187 malades sans alerte. Le prix est réel sur TDTU : les saines en alerte passent de 5 % à 16 %.

**Amendement 3 (10 novembre 2026, vers 4 h 20, avant tout calcul sur ce point) : la même politique (b) pour la branche « loin » ?**
- Les photos de loin ne sont pas dans la validation. La décision se prend donc sur les **photos du robot ROAMER de `dev_loin`** (1 312 : saines 438, fusariose 344, moko 270, bunchy top 260). Ces photos ont servi à ajuster l'aiguilleur, jamais la v2 ni ses seuils.
- Réponses de la v2 (3 réseaux, 4 vues, ses seuils, alerte 0,30), politique (a) contre (b), même coût que l'amendement 2. (b) est adoptée pour la branche « loin » si son coût est strictement plus bas.
- Rapporté sans effet : photos du robot de `val_loin` (1 305) et photos de téléphone (bunchy top 139, saines 139).

### Module complet contre l'ancienne chaîne (rapport, sans effet sur les décisions)

Le module comprend l'aiguilleur, la soupe avec la politique (b) pour les gros plans, et la v2 avec la politique (b) pour les plantes entières (amendements 2 et 3). L'ancienne chaîne est la v2 seule, avec la règle de la v2. Une photo est « sans alerte » si sa réponse est « saine » ou « je ne sais pas ». Mesure : `scripts/evaluer_module_maladies.py`, sortie `out/maladies/cinq_classes/tableau_module_complet.csv`.

| Jeu | Malades sans alerte (ancienne → module) | Saines en alerte (ancienne → module) | Sigatoka nommée (ancienne → module) | Photos aiguillées « loin » |
| --- | --- | --- | --- | --- |
| Validation (Tanzanie) | 107 → **9** / 2 001 | 7 → 15 / 1 000 | 961 → 965 / 1 000 | 15 / 3 001 |
| BananaLSD (Bangladesh) | 88 → **0** / 807 | 0 → 3 / 90 | 445 → 452 / 473 | 3 / 897 |
| TDTU (Vietnam) | 424 → **153** / 1 059 | 59 → 119 / 577 | 85 → 112 / 404 | 473 / 1 636 |
| PSFD (Inde) | 490 → **298** / 738 | — | 63 → 108 / 474 | 211 / 738 |
| Éthiopie | 592 → **338** / 1 134 | 1 → 2 / 155 | 38 → 48 / 320 | 199 / 1 289 |

Sur BananaLSD, Cordana et Pestalotiopsis dites Sigatoka passent de 230 à 273 sur 334 (défaut connu de la soupe) ; toutes déclenchent désormais une alerte. Le module rate **de 39 à 64 % de malades en moins** dans les pays neufs, et 12 fois moins en validation. En contrepartie, les fausses alertes passent de 0,7 % à 1,5 % en validation et de 10 % à 21 % sur TDTU, dont 29 % des photos sont aiguillées « loin ».

**Relance technique de L5 (10 novembre 2026, vers 4 h 35)** : la version 1 du carnet a entraîné le réseau 1 en entier (tête seule, puis 6 époques). Elle s'est ensuite arrêtée par manque de mémoire GPU au début du réseau 2, parce que le réseau 1 restait sur le GPU. Dans la version 2, les réseaux finis restent sur le processeur et sont évalués un par un. Le réseau 1 est repris tel quel de la version 1, via le jeu Kaggle privé `maladies-l5-reseau1` : même recette, même graine. Seul le réseau 2 est entraîné. Aucune autre modification.

**Résultat de l'amendement 3** (v2, seuil d'alerte 0,30 ; `scripts/mesurer_jnsp_loin.py`, `out/maladies/cinq_classes/bilan_jnsp_loin.json`) :

| Photos de loin | Malades sans alerte, (a) → (b) | Saines en alerte, (a) → (b) | Coût, (a) → (b) |
| --- | --- | --- | --- |
| **Robot, `dev_loin`** (décision) | 418 → 39 / 874 | 98 → 345 / 438 | 934 → **423** |
| Robot, `val_loin` | 366 → 21 / 860 | 107 → 369 / 445 | 839 → 411 |
| Téléphone | 97 → 32 / 139 | 25 → 89 / 139 | 219 → 153 |

**La politique (b) est adoptée pour la branche « loin »** (`maladies.jnsp_alerte_loin: true`). Lecture : de loin, la v2 distingue mal les plantes malades des saines (AUC 0,67). Avec la règle de coût, presque toute photo de loin douteuse devient une alerte « à confirmer par un gros plan » ; 79 % des plantes saines du robot en reçoivent une. C'est cohérent avec le rôle de la branche « loin » : orienter vers un gros plan, sans conclure. Ces alertes ont une confiance « faible » dans le bulletin, donc une pénalité réduite de moitié, et ne font pas passer à elles seules une parcelle en orange. Corentin peut revenir à la règle de la v2 par la config.

### Résultat de L5 (10 novembre 2026, vers 6 h 15, mesure à part, amendement 1)

Calcul : version 2 du carnet (relance technique ci-dessus). Les règles de la v2 retiennent la moyenne des 2 réseaux, avec 4 vues (coût de validation 21 contre 36 pour un réseau), un seuil d'alerte de 0,45 et un seuil de nom de 0,83. L'empreinte du protocole a été notée dans le journal avant la mesure. Même script (`scripts/mesurer_cinq_classes.py`, L5 ajouté en dernier dans l'ordre de coût) ; les mesures des autres candidats sont identiques à celles de la section 6. La première sortie est gardée dans `bilan_cinq_classes_sans_l5.json`.

| Mesure | v2 | soupe | L5 |
| --- | --- | --- | --- |
| Validation : malades dites saines | 4 / 2 001 | 4 | 6 |
| Validation : fausses alertes | 7 / 1 000 | 9 | **1** |
| Validation : nom juste | 1 848 / 1 894 | 1 838 / 1 889 | 1 631 / 1 715 (95,1 %) |
| BananaLSD : Sigatoka nommée | 445 / 473 | 452 | 388 |
| BananaLSD : saines bien classées | 86 / 90 | 86 | 88 |
| **Garde** : Cordana et Pestalotiopsis dites Sigatoka (≤ 246) | 230 / 334 | 273 | **82** |
| Cordana bien nommée | — | — | 50 / 162 |
| Pestalotiopsis bien nommée | — | — | 1 / 172 |
| Noms nouveaux justes (≥ 80 %) | — | — | 51 / 61 (84 %) |
| Cordana et Pestalotiopsis en alerte | 265 / 334 | 301 | 241 |
| TDTU autre_maladie dite saine | 69 / 655 | 47 | 116 |
| PSFD Sigatoka jaune dite saine | 110 / 264 | 101 | 116 |
| Éthiopie Xanthomonas dite saine | 245 / 814 | 212 | 309 |
| PSFD Sigatoka noire en alerte | 138 / 474 | 161 | 185 |
| Éthiopie Sigatoka en alerte | 141 / 320 | 169 | 201 |
| Éthiopie saines en alerte | 1 / 155 | 1 | 0 |
| *Rapporté* : TDTU saines en alerte (sur 577) | 59 | 30 | 12 |
| Rappel équilibré BananaLSD (≥ 0,958) | 0,948 | 0,956 | 0,899 |

**L5 n'est pas adoptable.** Conditions en échec : Sigatoka nommée sur BananaLSD (388 contre 445, − 12 points) ; gain ; maladies inconnues dites saines sur les trois jeux (TDTU + 7,2 points, Sigatoka jaune + 2,3, Xanthomonas + 7,9). **Le choix refait avec tous les candidats ne change pas : la branche « proche » reste la soupe.**

Lecture, sans effet sur la décision :
- L5 est le seul candidat qui passe à la fois la garde (82, le plus bas de tous) et la condition des noms nouveaux (84 % de justes). Il est aussi le plus sobre en fausses alertes (1 sur 1 000 en validation, 12 sur 577 sur TDTU).
- Le prix : il dit « saine » plus souvent devant une maladie qu'il ne connaît pas, et il hésite sur la Sigatoka. En validation, 52 Sigatoka sont nommées « Pestalotiopsis » et 196 restent sans nom (« je ne sais pas » ou « malade, non identifiée »). Sur BananaLSD, Pestalotiopsis reste surtout dite Sigatoka (75 sur 172) ou sans nom (83).
- Un réseau plus grand ne compense pas des données trop pauvres pour ces deux maladies (une centaine de photos d'un seul jeu chacune).
