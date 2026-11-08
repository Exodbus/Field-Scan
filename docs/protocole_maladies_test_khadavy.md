# Protocole de mesure : classifieurs de maladies sur khadavy (Indonésie)

Écrit le 8 novembre 2026, **avant toute mesure d'un modèle sur ces images**. À valider par Corentin et son binôme, puis à commiter (avec accord) avant la mesure. Toute modification ultérieure est datée et justifiée ; aucune ne peut suivre un résultat.

**Amendement 1 du 8 novembre 2026 (avant toute mesure ; aucun modèle n'a vu khadavy)**. Proposé par le binôme, accepté par Corentin.

- **Choix du modèle fait avant la mesure, sans khadavy** : la **v2 ConvNeXt** du binôme entre dans la chaîne. Motif, sur des mesures déjà connues : sur BananaLSD, elle nomme 95,1 % des Sigatoka contre 86,5 % pour le B0 ; elle n'y dit saine aucune feuille malade ; ses inconnues rejetées sont au même niveau (21 % contre 23 %).
- **khadavy devient le test final du module maladies**, noté une seule fois, sur la v2 ConvNeXt. Le B0 est noté à côté, sur les mêmes photos, pour le tableau comparatif, **sans effet sur aucune décision**.
- **La règle de choix de la section 5 (bootstrap apparié, B0 gardé en cas d'égalité) est annulée**. Elle est remplacée par la section 5 ci-dessous. Les sections 0 et 6 sont réécrites en conséquence.
- **Bercak-Kuning** : deux mesures rapportées au lieu d'une (section 6).
- **Contrôle de fuite ajouté avant la mesure** : khadavy contre la campagne tanzanienne 2022-2023 complète (11 766 images, validation du binôme), qui n'était présente qu'en partie (3 001 images) dans les références.

Motif de l'amendement : quand un jeu sert à choisir le modèle, son score est flatté et le module n'a plus de test. En choisissant avant, khadavy donne un score honnête dans un pays jamais vu.

## 0. Pourquoi

Le projet commun a deux classifieurs de maladies figés : le **B0** de Corentin et la **v2 ConvNeXt** de son binôme. Ils n'ont aucun jeu d'évaluation propre commun. BananaLSD et la Cordana du Pérou ont été consultés par les deux. Banana Disease Recognition a été évalué par les modèles du binôme. khadavy n'a été vu par aucun modèle des deux projets. Depuis l'amendement 1, il est le **test final** de la v2 ConvNeXt, choisie avant la mesure, et il est noté une seule fois.

**Statut à écrire tel quel** : le choix de la v2 ConvNeXt s'appuie sur BananaLSD, déjà consulté par les deux projets (validation hors domaine). Après cette mesure, le module maladies n'a plus de jeu vierge.

## 1. Source et contrôles (faits sans modèle le 8 novembre 2026)

- **Klasifikasi Daun Pisang**, Roboflow Universe, `khadavy/klasifikasi-daun-pisang`, v1 du 12 octobre 2024, CC BY 4.0, export « folder ». Fichier : `data/roboflow_maladies/nouveaux/khadavy.zip` (1 632 fichiers, 680 noms d'origine).
- **Contrôles** (`scripts/verifier_jeux_maladies.py`, sorties dans `out/maladies/roboflow_nouveaux/`) :
  - aucune fuite vers les 21 774 images de référence (Tanzanie 2021 et 2022, Pérou, BananaLSD, Banana Disease Recognition) sous les 8 symétries ;
  - les paires les plus proches (écart de vignette de 8,0 et plus) sont des photos différentes, vérifiées à l'œil ;
  - aucune copie avec les autres candidats Roboflow ni avec TDTU.
- **Doublons internes** : 680 noms d'origine regroupés en **431 photos distinctes**, aucune paire entre deux classes.
- **Images déformées** : Roboflow a ramené toutes les images à 640 × 640 (photos d'origine 3024 × 4032 ou 3024 × 3024). Pas d'original disponible ; les deux modèles reçoivent les mêmes fichiers.

## 2. Classes et réponses justes

Les noms de classes sont en indonésien, sans description de l'auteur. Le sens retenu a été fixé d'après les noms et les planches, avant toute mesure.

| Classe du jeu | Sens retenu | Photos distinctes | Rôle | Réponse juste |
| --- | --- | --- | --- | --- |
| Sehat (« saine ») | feuille saine | 159 | connue | « saine » |
| Bercak-Hitam (« taches noires ») | cercosporiose noire | 245 | connue | « cercosporiose noire » |
| Bercak-Kuning (« taches jaunes ») | cercosporiose jaune probable | 27 | **maladie inconnue** des deux modèles | « malade, non identifiée » ou « je ne sais pas » |

**Limite** : le sens des classes n'est pas confirmé par l'auteur. Bercak-Hitam peut contenir d'autres maladies à taches noires ; Bercak-Kuning n'a que 27 feuilles distinctes.

## 3. Sélection des images (sans modèle)

- **Une image par photo distincte** (431 au total). Dans chaque groupe de copies, on prend une image des parties `test` ou `valid` de Roboflow, non augmentées, la première par nom. À défaut, on prend la première image de `train` par nom.
- La liste (groupe, classe, fichier, SHA-256) est écrite par un script sans modèle, **avant la mesure**, et son empreinte est notée ici.
- Aucune image n'est retirée après la mesure.

**Liste figée le 8 novembre 2026, sans modèle** (`scripts/selectionner_test_khadavy.py`, sorties dans `data/test_khadavy/` : `liste.csv`, `empreinte.txt`, `images/`) :

- khadavy : 1 632 fichiers, 680 photos d'origine, **431 photos distinctes** (Sehat 159, Bercak-Hitam 245, Bercak-Kuning 27), aucun groupe mêlant deux classes. Images prises dans `test` (59), `valid` (100) et `train` (272).
- ROAMER Black-sigatoka : 143 photos (positive 104, negative + positive 37, negative 1, sans annotation 1).
- panama wilt in banana : 50 photos (healthy 25, diseased 25).
- **SHA-256 de `liste.csv` : `c8e6d50a2c5750605cb7de01c4ce2bc8351121f8b4904d497d78c0bc8681af73`.**

Limite : les 272 images prises dans `train` peuvent être des copies augmentées par Roboflow (retournement, luminosité) quand aucune copie `test` ou `valid` n'existe pour la photo.

## 4. Modèles mesurés (figés avant la mesure)

| Modèle | Fichiers | Décision |
| --- | --- | --- |
| B0 (Corentin) | `modeles/maladies/maladies_v2.onnx`, `entrainement_maladies.json` | 4 vues ; malade si P(cercosporiose) + P(fusariose) ≥ 0,5 ; rejet par probabilité maximale, seuil 0,7076 (`fieldscan/modules/maladies.py`) |
| v2 ConvNeXt (binôme) | 3 ConvNeXt-Tiny, `seuils.json`, `classifieur.py` (`modeles/maladies_binome/maladies_v2/`) | photo recadrée en carré 224 et réenregistrée en JPEG 95 ; 4 vues (identité, deux miroirs, quart de tour) × 3 réseaux ; malade si P(Black Sigatoka) + P(Fusarium) ≥ 0,30 ; maladie nommée si elle fait au moins 50 % de P(malade), sinon « malade, non identifiée » ; « je ne sais pas » (`inconnu`) si la plus forte probabilité est sous 0,6459, quelle que soit la réponse |

- Le SHA-256 des poids, des seuils et du code de prédiction de chaque modèle est noté ici avant la mesure.

**Empreintes (SHA-256), relevées le 8 novembre 2026 avant la mesure** :

| Fichier | SHA-256 |
| --- | --- |
| B0 : `modeles/maladies/maladies_v2.onnx` | `241841de12ce86fb0d4f411575f7300c7ec4785a23672824283ac3a5a00cf6a7` |
| B0 : `modeles/maladies/entrainement_maladies.json` | `3e766e578b207c8dd85259aea34487f57d2169a9a607cc32534dc092bba0ca98` |
| B0 : `fieldscan/modules/maladies.py` (commit `df4d28f`) | `fec6a9fe3a09105a91983bc1521f0d7c0f634017e9f22e965cadae08c29d01da` |
| v2 : `poids/maladies_v2_convnext_tiny_1.pt` | `276630d275c32c83a6f05942d6eb00036980c1a0a5fdb3c7130ab848265229b7` |
| v2 : `poids/maladies_v2_convnext_tiny_2.pt` | `1ad6e8981463a36eeefe5b130c709c8a3fb00de42779c0f6afd062da561db683` |
| v2 : `poids/maladies_v2_convnext_tiny_3.pt` | `711a202fc6f2d151c2ee75bf82d89f085ea02df35d0b6ad6d4bfdf2afff4e395` |
| v2 : `poids/seuils.json` | `a5a52d957b172a86e7737f8903a6f0bb3bf798af84321d0a56d374e80e4fd418` |
| v2 : `classifieur.py` | `7179ad81f55437a506eaa83a6e8a643363135fa39334096c7dff68865d8a7041` |

Les poids de la v2 (3 × 56 Mo) restent hors du dépôt ; seules leurs empreintes y sont.
- Chaque modèle passe **une seule fois** par sa propre chaîne de décision, sans aucun réglage.
- On écrit un fichier de réponses par modèle (fichier, réponse, probabilités).

## 5. Score de test (amendement 1 ; remplace la règle de choix, annulée)

Le modèle de la chaîne est déjà choisi (v2 ConvNeXt). Ce test ne décide rien : il donne le score du module, une seule fois, et aucun seuil ni réglage ne change après.

Unité : la photo distincte. Les réponses « saine », « cercosporiose noire », « fusariose », « malade, non identifiée » et « je ne sais pas » sont normalisées dans les deux chaînes.

**Score principal du module : F1 macro de la v2 ConvNeXt sur les deux classes connues** (saine, cercosporiose noire ; 404 photos), avec un intervalle à 95 % par bootstrap (10 000 tirages des photos distinctes avec remise, graine 2026). Toute autre réponse compte comme une erreur, y compris « fusariose », « malade, non identifiée » et « je ne sais pas ».

## 6. Mesures rapportées (v2 ConvNeXt, et B0 à côté, sur les mêmes photos)

- **Sigatoka nommée** : part des 245 Bercak-Hitam annoncées « cercosporiose noire » ;
- **saines bien classées** : part des 159 Sehat annoncées « saine » ;
- **fausses alertes** : part des 159 saines annoncées malades (n'importe quelle maladie, ou « malade, non identifiée ») ;
- **malades dites saines** : part des 272 feuilles malades (Bercak-Hitam et Bercak-Kuning) annoncées « saine », et part annoncée malade ;
- **« je ne sais pas »** : part par classe ;
- **Bercak-Kuning (27 photos), deux mesures, chacune avec un intervalle de Wilson à 95 %** :
    - **signalée malade** : réponse juste si la feuille est dite malade, quel que soit le nom (cercosporiose noire, fusariose, « malade, non identifiée ») ;
    - **reconnue inconnue** : réponse juste seulement si « malade, non identifiée » ou « je ne sais pas » ;
    - et la part annoncée « cercosporiose noire » (maladie voisine) ;
- F1 par classe, précision, rappel, matrice de confusion complète en photos distinctes ;
- temps par photo sur le même processeur.

Le B0 est rapporté avec les mêmes mesures, dans une colonne à part, pour le tableau comparatif du livrable.

## 7. Jeux indicatifs, mesurés dans le même passage

Rapportés à part, pour les deux modèles, **sans effet sur aucune décision**, une image par photo d'origine :

- **ROAMER Black-sigatoka** (Philippines, `roamer_black_sigatoka.zip`, 143 photos) : feuilles entières vues d'en dessous, contre le ciel. On mesure la part annoncée malade et la part annoncée « cercosporiose noire ». Pas de classe saine.
- **panama wilt in banana** (`research_panama.zip`, 50 photos : 25 saines, 25 malades) : plantes et feuilles mêlées. On mesure la part des malades annoncées malades, la part annoncée « fusariose » et les fausses alertes sur les saines. C'est la seule mesure de la fusariose hors de Tanzanie, très petite.

ROAMER Healthy, Bunchy-top, Fusarium wilt et kewalee sont écartés : plantes entières ou images de vidéo, hors du domaine du module.

## 8. Ordre

1. Validation de ce protocole par les deux étudiants.
2. Script de sélection (section 3) ; empreinte de la liste notée ici. **Fait le 8 novembre 2026.**
3. Contrôle de fuite de khadavy contre la campagne tanzanienne 2022-2023 complète (amendement 1), sans modèle ; résultat noté ici. **Fait le 8 novembre 2026** :
    - références : 14 232 images (BLACK SIGATOKA_1 et _2, FUSARIUM WILT_1 et _2, HEALTHY_2, dossier healthy_1), soit plus que les 11 766 de la validation du binôme. Les 3 071 autres entrées sont des fichiers de métadonnées macOS (`__MACOSX/._*`), pas des photos ;
    - méthode des contrôles précédents, sur les 624 images figées (khadavy, ROAMER Black-sigatoka, panama wilt), sous les 8 symétries ;
    - **aucune fuite**. Écarts minimaux : khadavy 7,97, ROAMER 24,61, panama 29,52. Les 4 paires les plus proches ont été vérifiées à l'œil : photos différentes (`out/maladies/roboflow_nouveaux/fuite_tanzanie_complete/paires.jpg`).
4. Empreintes des deux modèles notées ici (**fait le 8 novembre 2026**, section 4) ; commit du protocole (avec accord).
5. Mesure unique : un script, un passage par modèle, un fichier de résultats.
6. Résultats écrits ici tels quels, même s'ils sont mauvais. Aucun changement de modèle, de seuil ou de réglage après coup.

## 9. Résultats (mesure unique du 8 novembre 2026)

Script `scripts/mesurer_test_khadavy.py` (commit `5c0bf7d`, avant la mesure), lancé une seule fois ; empreintes des modèles, de la liste et des 624 images vérifiées par le script ; sorties dans `out/maladies/test_khadavy/` (`bilan.json`, `reponses_v2_convnext.csv`, `reponses_b0.csv`, `VERROU`). Rien n'a été changé après.

**Score du module (v2 ConvNeXt, modèle de la chaîne)** : **F1 macro 0,623** [0,577 ; 0,668] sur saine et cercosporiose noire (404 photos). Le B0, à côté : 0,505 [0,459 ; 0,551].

| Mesure (khadavy, photos distinctes) | v2 ConvNeXt | B0 |
| --- | --- | --- |
| F1 saine / F1 cercosporiose noire | 0,809 / 0,438 | 0,724 / 0,287 |
| Sigatoka nommée (245 Bercak-Hitam) | 69 (28,2 %) | 41 (16,7 %) |
| Saines bien classées (159) | 150 (94,3 %) | 148 (93,1 %) |
| Fausses alertes sur les saines | 6 (3,8 %) | 4 (2,5 %) |
| Malades dites saines (272) | 62 (22,8 %) | 111 (40,8 %) |
| « Je ne sais pas » (saines / Bercak-Hitam / Bercak-Kuning) | 3 / 82 / 0 | 7 / 24 / 2 |
| Bercak-Kuning signalée malade (27) | 27 (100 %) [87,5 ; 100] | 16 (59,3 %) [40,7 ; 75,5] |
| Bercak-Kuning reconnue inconnue | 0 (0 %) [0 ; 12,5] | 7 (25,9 %) [13,2 ; 44,7] |
| Bercak-Kuning dite cercosporiose noire | 0 | 0 |
| Temps par photo (même processeur) | 0,77 s | 0,06 s |

Réponses détaillées, v2 ConvNeXt : Bercak-Hitam → saine 62, cercosporiose noire 69, fusariose 32, je ne sais pas 82 ; Bercak-Kuning → fusariose 27 ; Sehat → saine 150, fusariose 5, cercosporiose noire 1, je ne sais pas 3. B0 : Bercak-Hitam → saine 102, cercosporiose noire 41, malade non identifiée 72, fusariose 6, je ne sais pas 24 ; Bercak-Kuning → fusariose 11, saine 9, malade non identifiée 5, je ne sais pas 2 ; Sehat → saine 148, malade non identifiée 4, je ne sais pas 7.

**Jeux indicatifs** :

| Mesure | v2 ConvNeXt | B0 |
| --- | --- | --- |
| ROAMER Black-sigatoka (143), dites malades | 15 (10,5 %) | 17 (11,9 %) |
| ROAMER, dites cercosporiose noire | 6 (4,2 %) | 9 (6,3 %) |
| panama wilt (25 malades), dites malades | 14 (56 %) | 18 (72 %) |
| panama wilt, dites fusariose | 12 (48 %) | 8 (32 %) |
| panama wilt (25 saines), fausses alertes | 4 (16 %) | 0 |

**Lecture** :
- **Le module généralise mal à khadavy** : F1 0,62, loin des 0,98 du Bangladesh. Les feuilles saines sont bien reconnues (94 %), mais seules 28 % des Bercak-Hitam sont nommées cercosporiose noire ; 23 % sont dites saines et un tiers reçoit « je ne sais pas ».
- **Cause probable, à écrire comme hypothèse** : les Bercak-Hitam montrent surtout de petites taches noires éparses sur une feuille verte (planches de la section 1), sans les stries et nécroses de la cercosporiose avancée des jeux d'entraînement. Il peut s'agir d'un stade précoce, ou d'une autre maladie à taches noires (le sens de la classe n'est pas confirmé, section 2). Les images sont aussi déformées en 640 × 640.
- **Bercak-Kuning** : toujours signalée malade par la v2, mais toujours nommée fusariose (feuilles jaunies) ; jamais reconnue comme inconnue.
- **v2 contre B0** : la v2 fait mieux sur le score principal et rate beaucoup moins de malades (23 % contre 41 % dites saines) ; le B0 fait un peu moins de fausses alertes et reconnaît plus souvent l'inconnu. Ces écarts confirment le choix de l'amendement 1, sans l'avoir décidé.
- **ROAMER** (feuilles entières vues d'en dessous) : presque tout est dit sain par les deux modèles. Le module ne lit pas ce type de photo.
- **Fusariose hors de Tanzanie** (panama wilt, 25 photos) : la v2 en nomme 12, le B0 8 ; effectif très petit, plantes et feuilles mêlées.
- Après cette mesure, le module maladies n'a plus de jeu vierge.
