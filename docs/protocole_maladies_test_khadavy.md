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
| v2 ConvNeXt (binôme) | 3 ConvNeXt-Tiny, `seuils.json` | 4 vues, 3 graines ; malade si P(Black Sigatoka) + P(Fusarium) ≥ 0,30 ; nom de maladie si confiance ≥ 0,50 ; « je ne sais pas » sous 0,646 (sa propre chaîne) |

- Le SHA-256 des poids, des seuils et du code de prédiction de chaque modèle est noté ici avant la mesure.
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
3. Contrôle de fuite de khadavy contre la campagne tanzanienne 2022-2023 complète (amendement 1), sans modèle ; résultat noté ici.
4. Empreintes des deux modèles notées ici ; commit du protocole (avec accord).
5. Mesure unique : un script, un passage par modèle, un fichier de résultats.
6. Résultats écrits ici tels quels, même s'ils sont mauvais. Aucun changement de modèle, de seuil ou de réglage après coup.

## 9. Résultats

À remplir après la mesure.
