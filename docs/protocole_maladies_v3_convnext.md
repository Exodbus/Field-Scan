# Protocole du classifieur de maladies v3 (ConvNeXt, nouvelles sources, classe « autre maladie »)

Écrit le 8 novembre 2026, **avant toute préparation et tout entraînement de la v3**. À valider par les deux étudiants, puis à commiter (avec accord) avant la préparation. Toute modification ultérieure est datée et justifiée ; aucune ne peut suivre un résultat de la v3.

Ce protocole remplace `docs/protocole_maladies_v3.md` (v3 sur EfficientNet-B0, écrit le 6 novembre, jamais validé ni lancé) : le modèle de la chaîne est désormais la v2 ConvNeXt (`docs/protocole_maladies_test_khadavy.md`, amendement 1).

**Amendement 1 du 8 novembre 2026 (avant tout entraînement ; aucun modèle n'a vu les ajouts ni le test)** :

- **Nom** : le modèle de ce protocole s'appelle **v5**. « v3 » et « v4 » désignent déjà deux modèles du binôme : sa v3 (v2 + Tanzanie 2022-2023 apprise, non retenue) et sa v4 (non retenue). Dans la suite du texte, « v3 » se lit « v5 ».
- **Exécutant** : Corentin entraîne la v5 sur Kaggle, avec le carnet `notebooks/entrainer_maladies_v5_kaggle.ipynb`, écrit avant l'entraînement et testé en local sur un petit échantillon.
- **Données d'entraînement** : l'archive `data/feuilles_pret_perou.zip` (Tanzanie 2021 et Pérou, 16 963 images retenues, tiges exclues), mêmes sources que la v2 du binôme mais préparée par Corentin (397 tiges exclues contre 398 ; doublons repérés par une autre méthode), plus `data/feuilles_v3_ajouts.zip`. La Cordana du Pérou (`test_perou`) n'est jamais lue.
- **Validation** : la campagne tanzanienne 2022-2023 disponible en local, **3 001 images** tirées (1 000 saines, 1 000 cercosporioses, 1 001 fusarioses), au lieu des 11 766 de la validation du binôme, qui ne sont pas en local. Les seuils de la v5 y sont réglés par les règles de la v2 (section 4) ; le choix entre un réseau et la moyenne des trois, et entre 1 et 4 vues, suit aussi les règles du carnet de la v2 (coût le plus bas en validation).
- **Adoption (section 5)** : la v2 et la v5 sont mesurées par Corentin, en local, par le même code, sur ces 3 001 images et sur BananaLSD (897 images de l'archive), chacune avec ses propres seuils (`seuils.json` de la v2, seuils de la v5 réglés en validation).
- **Préparation des images** : chaque image passe par la préparation de la v2 (`classifieur.preparer` : recadrage carré au centre en 224 px, réenregistrement en JPEG qualité 95), à l'entraînement comme à l'évaluation.
- **Test banana-buddy : jeu déjà consulté, à écrire tel quel.** Réponse du binôme (8 novembre 2026) :
    - le **6 novembre**, sa v2 et sa v4 ont été notées sur banana-buddy (dossiers Healthy, Healthy Leaf, Leafspot, Leafspot Leaf), résultats vus. Ce jeu n'est donc pas vierge pour l'équipe, ni pour la v2 ;
    - dans son « étape 1 » en cours, seule la v2 a été lancée sur 450 photos des dossiers « … Leaf » ; **aucun résultat affiché** ; banana-buddy a été retiré de ses juges et ces réponses sont supprimées sans être lues ;
    - son audit trouve 705 copies tanzaniennes dans Healthy Leaf, 817 dans Leafspot Leaf, 624 dans Panama Leaf, ce qui concorde avec les photos `Image_N` exclues ici (707, 817, 625). Ces copies sont souvent tournées : la sélection de la section 7 compare toujours sous les 8 symétries.

  Conséquences : la v5 n'a jamais vu banana-buddy, et aucune décision du protocole ne dépend du test (l'adoption se fait sur les validations, section 5). Le test reste donc mesuré une fois et rapporté, mais comme un **jeu consulté** par l'équipe, pas comme un test vierge. La comparaison v2 / v5 sur ce jeu est indicative.
- **Versions du binôme** : sa version en 384 px, partie de la v2, s'appellera **v6**. Elle ne se compare à la v5 que sur des jeux qu'aucune des deux n'a appris (validation tanzanienne 2022-2023, BananaLSD) ; khadavy, appris par la v5, ne peut pas les départager.

**Date limite** : si la v3 n'est pas entraînée et mesurée sur la validation le **11 novembre 2026 à 23 h 59**, elle est abandonnée et la v2 reste dans la chaîne. Le test (section 7) n'est alors pas lancé.

## 0. Pourquoi une v3

Le test khadavy (Indonésie, mesure unique du 8 novembre) montre trois faiblesses de la v2 :

1. **taches précoces** : 28 % seulement des Bercak-Hitam nommées cercosporiose noire, 23 % dites saines ;
2. **maladie inconnue nommée à tort** : la Sigatoka jaune (Bercak-Kuning) est toujours appelée fusariose ;
3. **autres styles de photo** : les feuilles entières vues d'en dessous (ROAMER) sont presque toutes dites saines.

La v3 garde la recette de la v2 et change deux choses :

- **nouvelles sources d'entraînement** : khadavy (consommé comme test, il peut désormais servir à apprendre) et TDTU (Vietnam) ;
- **une quatrième classe « autre maladie »**, pour que le modèle ait une réponse « malade, autre chose » au lieu de forcer une maladie connue.

Ces choix viennent d'un résultat de test (khadavy). La v3 est donc jugée sur un **nouveau test vierge**, fixé ici avant tout entraînement (section 7).

## 1. Sources

| Source | Contrôles déjà faits (sans modèle) | Rôle |
| --- | --- | --- |
| Tanzanie 2021 (Harvard Dataverse) et Pérou (Mendeley) | ceux de la v2 | entraînement, comme la v2 |
| **khadavy** (Roboflow `khadavy/klasifikasi-daun-pisang`, Indonésie, CC BY 4.0) | 431 photos distinctes ; aucune fuite vers Tanzanie 2021, Tanzanie 2022-2023 locale (3 001), Pérou, BananaLSD, Banana Disease Recognition, TDTU | **entraînement** (nouveau) |
| **TDTU** (Roboflow `nh-nguyn-trn-qunh/banana-diseases-admyw`, Vietnam, CC BY 4.0) | 2 295 photos distinctes ; aucune fuite (contrôles du 6 et du 8 novembre) | **entraînement** (nouveau) |
| Tanzanie 2022-2023 (Zenodo), validation de la v2 | — | **validation** (seuils), comme la v2 |
| BananaLSD (Bangladesh) | consulté par les deux projets | **validation hors domaine** (adoption seulement) |
| **banana-buddy, partie originale** (Roboflow `banana-buddy-research-sgury/banana-disease-identification`, CC BY 4.0) | voir section 7 | **test** (nouveau, une seule fois) |

**Jamais utilisés pour la v3** : khadavy comme mesure (consommé), Banana Disease Recognition et PSFD (vus par le binôme), ROAMER, panama wilt, kewalee, BANANADETECT et sab a (copies ou plantes entières).

## 2. Classes et correspondances

Quatre classes : **saine**, **black_sigatoka**, **fusarium**, **autre_maladie**.

| Source | Étiquette d'origine | Classe v3 |
| --- | --- | --- |
| khadavy | Sehat | saine |
| khadavy | Bercak-Hitam | black_sigatoka |
| khadavy | Bercak-Kuning (Sigatoka jaune probable) | autre_maladie |
| TDTU | Healthy seul | saine |
| TDTU | Black Segatoka (avec ou sans Healthy) | black_sigatoka |
| TDTU | Xanthomonas wilt et/ou Bacterial wilt (avec ou sans Healthy) | autre_maladie |
| TDTU | deux maladies différentes, étiquettes contradictoires, Aphids, Other, sans annotation | exclue |
| Tanzanie, Pérou | comme la v2 | comme la v2 |

khadavy : une image par photo distincte (431, liste `data/test_khadavy/liste.csv`). TDTU : une image par photo distincte, la première par nom (correspondance et effectifs du protocole du 6 novembre : 577 saines, 409 black_sigatoka, 677 autre_maladie).

**Limite connue** : le sens des classes de khadavy n'est pas confirmé par l'auteur. Si Bercak-Hitam contient d'autres maladies à taches noires, la v3 apprendra à les appeler black_sigatoka.

## 3. Préparation (par Corentin)

- Archive Kaggle `feuilles_v3_ajouts.zip` : images de khadavy et de TDTU retenues, avec un `images.csv` au format du carnet de la v2 (colonnes `image`, `jeu`, `classe`, `source`).
- Mêmes règles que la v2 : rotation EXIF, aucune image agrandie.
- **Contrôle de fuite avant l'archive** : khadavy et TDTU contre la validation tanzanienne 2022-2023 et contre le test banana-buddy (section 7). Toute image d'entraînement identique ou presque à une image de validation ou de test est retirée de l'**entraînement**.
- Effectifs réels notés ici après la préparation.

**Préparation faite le 8 novembre 2026, sans modèle** (`scripts/preparer_ajouts_v3.py`, sorties dans `data/feuilles_v3_ajouts/` : `images/`, `images.csv`, `exclusions.csv` ; archive `data/feuilles_v3_ajouts.zip`, 42,5 Mo, avec `ajouts_v3/images_ajouts.csv`, nom distinct pour ne pas masquer l'`images.csv` du carnet) :

| Jeu | saine | black_sigatoka | autre_maladie | Total |
| --- | --- | --- | --- | --- |
| khadavy | 159 | 245 | 27 | 431 |
| TDTU | 577 | 404 | 655 | 1 636 |
| **Total** | **736** | **649** | **682** | **2 067** |

- TDTU : 2 295 photos distinctes ; **172 groupes aux étiquettes contradictoires exclus** et 487 photos exclues par la correspondance de la section 2 (deux maladies différentes, Aphids, Other, sans annotation). Écart avec les effectifs prévus (409 black_sigatoka, 677 autre_maladie) : les photos distinctes sont ici des groupes de quasi-doublons, plus larges que les groupes de noms du 6 novembre, d'où un peu plus de groupes contradictoires exclus.
- **Contrôle de fuite** contre 5 768 images (validation tanzanienne 2022-2023 locale, BananaLSD, test banana-buddy figé), sous les 8 symétries : **aucun ajout retiré**.
- **SHA-256 de `images.csv` : `a673630c9b30c90064a996943bba64eb7f828661d58dea87ef8bd92d6417c83a`.**
- Pour le binôme : ajouter le dossier `ajouts_v3/` à côté de ses données (les chemins de la colonne `image` commencent par `ajouts_v3/`) et concaténer `images_ajouts.csv` à son `images.csv`, jeux `khadavy` et `tdtu` en entraînement.

## 4. Recette (par le binôme, carnet `maladies_v2_kaggle.ipynb` adapté)

Recette de la v2 inchangée : ConvNeXt-Tiny ImageNet, 224 px, 6 époques, dernière époque gardée, lots de 32, taux 1e-4, recompression JPEG au hasard, lissage 0,1, mêmes augmentations, **3 réseaux** (3 graines), Pérou tiré 3 fois plus souvent.

Changements, et seulement ceux-ci :

- **4 classes** (section 2) ;
- **échantillonnage** : autre_maladie est tirée pour **10 % des images de chaque époque** ; khadavy et TDTU sont tirés à leur proportion naturelle parmi les autres. Ces chiffres sont fixés ici et ne seront pas réglés ;
- **décision** : P(malade) = P(black_sigatoka) + P(fusarium) + P(autre_maladie). Si la maladie la plus probable est autre_maladie, ou si sa part de P(malade) est sous le seuil de nom, la réponse est « malade, non identifiée ». Le « je ne sais pas » est inchangé.

**Seuils** (alerte, nom, confiance) réglés sur la validation tanzanienne **par les mêmes règles que la v2** : coût 2 × malades ratées + fausses alertes ; maladie nommée juste au moins 95 % du temps ; 95 % des photos de validation acceptées. Rien d'autre n'est réglé.

## 5. Adoption (v3 contre v2, sur les validations seulement, règle écrite avant)

Les gains attendus portent sur des pays et des styles de photo absents des validations. La règle d'adoption est donc une règle de **non-régression** : la v3 remplace la v2 si **toutes** les conditions suivantes sont remplies.

Sur la validation tanzanienne 2022-2023 (la même que la v2, même code, chaque modèle à ses propres seuils) :

- malades dites saines : au plus **+0,5 point** par rapport à la v2 ;
- fausses alertes sur les saines : au plus **+1 point** ;
- maladie nommée juste (quand elle est nommée) : au moins **95 %**.

Sur BananaLSD (validation hors domaine) :

- Sigatoka nommée : au plus **−2 points** par rapport à la v2 ;
- saines bien classées : au plus **−2 points** ;
- inconnues (Cordana, Pestalotiopsis) dites saines : au plus **+1 point**.

Si une condition échoue, la v2 reste dans la chaîne. Décision prise et écrite avant le test.

## 6. Garde-fous

- Cartes d'attention (Grad-CAM) sur quelques images de la validation, pour la lecture seulement.
- Aucun essai multiple : **un seul entraînement de la v3** (3 réseaux). S'il échoue pour une raison technique (plantage, erreur de données), une seule relance, notée ici avec sa cause.

## 7. Test (une seule fois, v2 et v3 rapportés, quel que soit le modèle adopté)

**banana-buddy, partie originale**. Contrôles déjà faits le 8 novembre 2026 (`out/maladies/roboflow_nouveaux/banana_buddy/`, `fuite_tanzanie_complete/banana_buddy.csv`) : 12 860 fichiers, 5 359 photos d'origine, 4 027 distinctes ; **2 150 photos nommées `Image_N` sont des copies de la Tanzanie 2021** (écart jusqu'à 0,12).

**Sélection (sans modèle, avant tout entraînement de la v3)** :

- toute photo nommée `Image_N` (format tanzanien) est **exclue**, qu'une copie ait été trouvée ou non ;
- tout groupe de photos contenant une image proche (écart ≤ 5) d'un jeu de référence (Tanzanie 2021 et 2022-2023 locale, Pérou, BananaLSD, Banana Disease Recognition, khadavy, TDTU) est exclu ;
- une image par photo distincte, prise d'abord dans `test` ou `valid` (non augmentées) ;
- la liste (photo, classe, SHA-256) est figée par un script sans modèle, et son empreinte est notée ici avant l'entraînement.

| Classe du jeu | Classe de référence | Réponse juste |
| --- | --- | --- |
| Healthy, Healthy Leaf | saine | « saine » |
| Panama, Panama Leaf | fusariose | « fusariose » (et, à part, « malade » quel que soit le nom) |
| Leafspot, Leafspot Leaf | maladie à taches, nom non vérifié | « malade », quel que soit le nom ; on rapporte à part la part « cercosporiose noire » |

**Liste figée le 8 novembre 2026, avant toute préparation et tout entraînement de la v3** (`scripts/selectionner_test_banana_buddy.py`, sorties dans `data/test_banana_buddy/` : `liste.csv`, `empreinte.txt`, `exclusions.csv`, `planche.jpg`) :

- 5 359 photos d'origine ; **2 145 exclues** au format tanzanien (`Image_N`) ; reste 3 214 photos (7 712 fichiers), regroupées en 1 889 photos distinctes ;
- références : 39 085 images (Tanzanie 2021 index et zips complets, Tanzanie 2022-2023 locale, Pérou, BananaLSD, Banana Disease Recognition, khadavy, TDTU) ;
- **19 groupes exclus** : 18 proches d'une référence (dont des copies de **TDTU**, 28 photos d'origine, et 6 de la Tanzanie 2021), 1 mêlant deux classes ;
- **1 870 photos retenues** : saine 712 (Healthy 419, Healthy Leaf 293), fusariose 608 (Panama 546, Panama Leaf 62), maladie à taches 550 (Leafspot 371, Leafspot Leaf 179) ; gros plans 534, vues larges 1 336 ; parties `test` 300, `valid` 537, `train` 1 033 ;
- **SHA-256 de `liste.csv` : `9eb9adcc5e3242c15020eae7f4ade6e971f7f91b494b4d1ffc8e5a9bfa5a8000`.**

Constats sur la planche (48 photos tirées au hasard) : Leafspot ressemble à de la cercosporiose (stries jaunes et brunes) ; Panama mêle plantes flétries typiques, vues de plantation larges et quelques images probablement tirées d'Internet (`panama-N-Copy`, `download-N`, feuille sur fond blanc) ; des images de la partie `train` sont tournées par Roboflow, avec des coins noirs. Rien n'est retiré à la main : ces limites sont rapportées avec le résultat.

**Mesures (v2 et v3, mêmes photos)** :

- **malades dites saines** (Panama et Leafspot) et **fausses alertes** (Healthy), avec intervalles de Wilson ;
- **fusariose nommée** (Panama) : première mesure de la fusariose hors de Tanzanie ;
- F1 macro saine / fusariose ;
- part des Leafspot dites cercosporiose noire, « malade, non identifiée » ou « je ne sais pas » ;
- résultats séparés pour les gros plans (classes « … Leaf ») et les vues larges (autres classes).

**Limites connues** : photos de 2023 d'origine inconnue (Sri Lanka probable) ; images de l'export redimensionnées en 640 × 640 et, pour la partie `train`, parfois tournées par Roboflow ; le binôme a entraîné sa v4 (non retenue) sur 562 feuilles saines de ce jeu, sans doute des copies tanzaniennes exclues ici.

Aucun réglage après le test. Le résultat est écrit ici tel quel.

## 8. Ordre

1. Validation de ce protocole par les deux étudiants ; commit (avec accord).
2. Sélection et liste figée du test banana-buddy (section 7) ; empreinte notée ici. **Fait le 8 novembre 2026.**
3. Préparation de `feuilles_v3_ajouts.zip` et contrôle de fuite (section 3). **Fait le 8 novembre 2026.**
4. Entraînement de la v3 sur Kaggle (binôme) ; seuils réglés sur la validation.
5. Adoption (section 5), écrite ici.
6. Test unique (section 7), v2 et v3.

## 9. Résultats

À remplir.
