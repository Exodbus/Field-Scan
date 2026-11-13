# Protocole du classifieur de maladies v3 (classe « autre maladie », test vierge)

Écrit le 6 novembre 2026, **à valider par Corentin avant toute préparation et tout entraînement du v3**. Reprend la procédure du v2 (`docs/carnet_de_donnees.md`, « Classifieur de maladies ») ; seuls les points ci-dessous changent. Toute modification ultérieure est datée et justifiée.

## 0. Pourquoi une v3

Le v2 nomme bien les maladies apprises, mais signale mal les maladies qu'il n'a jamais vues : il les range presque toujours dans la cercosporiose (rejet des inconnues de 11 à 31 %). De plus, le module n'a plus de test vierge : BananaLSD et la Cordana du Pérou ont été consultés (choix du réseau, B0 gardé contre B2), ce sont désormais des **validations hors domaine**.

La v3 change trois choses :
1. un **test vierge**, Banana Disease Recognition, jamais regardé avec un modèle ;
2. un jeu d'entraînement de plus, **TDTU** (Roboflow), seule source vérifiée qui apporte une maladie absente de nos données : le flétrissement bactérien (Xanthomonas) ;
3. une **quatrième classe, « autre maladie »**, apprise sur ce flétrissement bactérien, pour que le modèle ait une réponse « malade, autre chose » au lieu de forcer une maladie connue.

Les motivations viennent de validations (hors domaine) et de l'évaluation éthiopienne, pas du nouveau test.

## 1. Sources (vérifiées sans modèle le 6 novembre 2026)

Scripts : `scripts/verifier_jeux_maladies.py` (copies augmentées, doublons internes, fuites sous les 8 symétries, copies entre candidats) et `scripts/verifier_fuites_egalisees.py` (fuites après passage en gris et égalisation du contraste, contre les seuls jeux d'évaluation). Sorties dans `out/maladies/roboflow/`.

| Source | Contenu | Contrôles | Rôle |
| --- | --- | --- | --- |
| **Banana Disease Recognition** (Mendeley, doi 10.17632/79w2n6b4kf.1, v1 du 10 nov. 2023, Daffodil International University et Jahangirnagar University, CC BY 4.0) | dossier `Original Images` : 408 photos, 7 classes (saine 86, Black Sigatoka 67, Panama 41, Yellow Sigatoka 23, Moko 55, mosaïque des bractées 50, ravageurs 86) ; les 2 856 copies augmentées ne sont jamais utilisées | aucune copie dans nos ensembles ; une seule paire interne sous le seuil (écart 4,2), fausse (deux feuilles saines différentes, vérifiées à l'œil) | **test** |
| **TDTU** (Roboflow, nh-nguyn-trn-qunh/banana-diseases-admyw, v8, CC BY 4.0, export sans augmentation) | 2 648 images en 244 × 244 (étirées), 2 336 noms d'origine, **2 295 photos distinctes** ; boîtes de détection : Healthy, Black Segatoka, Xanthomonas wilt, Bacterial wilt, Other, Aphids | aucune copie des 21 774 images de référence (entraînement, validations, futur test), sous les 8 symétries ; après égalisation, plus proche image d'évaluation à un écart de 18,5 (photos différentes, vérifiées à l'œil) | **entraînement** |

**Jeux examinés et écartés** :

| Jeu (Roboflow) | Raison |
| --- | --- |
| BS - NO SIGATOKA (2 180 photos distinctes) | contient des photos de **BananaLSD** recadrées et au contraste renforcé (écarts de 8 à plus de 22 après égalisation, mêlées à des photos différentes : aucun seuil ne les sépare) ; l'entraîner fausserait la validation hors domaine |
| Banana Leaf Segmentation (936 photos distinctes sur 2 500) | taches de plusieurs maladies étiquetées sur la même feuille ; 335 groupes de copies aux étiquettes contradictoires ; une seule photo de freckle seul |
| Hoja de plátano (258 photos distinctes sur 673) | plantes entières, étiquette « malade / saine » sans nom de maladie, copies déposées déjà augmentées et parfois contradictoires |
| banana-vision-leaf (186 photos distinctes) | vues de plantation et collages d'images, pas des feuilles |
| Niams banana | pas encore exporté ; s'il est retenu, il entre par une modification datée de ce protocole, **avant** la préparation |

Règle permanente : un jeu qui contient une copie de Banana Disease Recognition n'entre jamais dans l'entraînement.

## 2. Rôles des données

| Ensemble | Contenu | Usage |
| --- | --- | --- |
| Entraînement | Tanzanie 2021 (sans les 397 tiges) + Pérou (saines, Sigatoka) + **TDTU** | apprentissage |
| Validation **VT** | Tanzanie 2022-2023 : saine 1 000, cercosporiose noire 1 000, fusariose 1 001 | choix de l'époque, seuil de rejet, adoption |
| Validation hors domaine **VH** | BananaLSD (saine 90, Sigatoka 473, Cordana 162, Pestalotiopsis 172) ; Cordana du Pérou 505 | adoption (aucun réglage d'époque ni de seuil) |
| **Test** | Banana Disease Recognition (section 7) | une seule fois, à la fin |

**Correspondance des étiquettes de TDTU** (étiquette d'image = ensemble des classes de ses boîtes ; une photo distincte = un groupe de copies, une seule image gardée, la première par nom) :

| Étiquettes de l'image | Classe v3 | Photos distinctes |
| --- | --- | --- |
| Healthy seul | saine | 577 |
| Black Segatoka (avec ou sans Healthy) | cercosporiose noire | 409 |
| Xanthomonas wilt et/ou Bacterial wilt (avec ou sans Healthy) | **autre maladie** | 677 |
| deux maladies différentes | exclue (étiquette ambiguë) | 305 |
| copies aux étiquettes contradictoires | exclue | 147 |
| Aphids (ravageur), seul ou avec Healthy | exclue | 116 |
| Other (contenu inconnu) | exclue | 62 |
| sans annotation | exclue | 2 |

TDTU apporte aussi des feuilles saines et des cercosporioses du même style de photo que le flétrissement bactérien : le modèle ne peut pas réussir en apprenant « style TDTU = autre maladie ».

## 3. Préparation

- `scripts/preparer_feuilles.py` étendu : TDTU (photo distincte, classe ci-dessus) en entraînement ; Banana Disease Recognition comme ensemble `test_bdr` ; BananaLSD et la Cordana du Pérou gardent leurs images, sous le nom de validation hors domaine.
- Même uniformisation (rotation EXIF, petit côté ramené à 256 pixels, jamais agrandi ; les images TDTU restent en 244).
- Même contrôle des fuites, avec Banana Disease Recognition parmi les ensembles d'évaluation : une image d'entraînement identique ou presque à une image de validation ou de test est retirée de l'**entraînement** (les ensembles d'évaluation ne bougent pas).
- Effectifs attendus avant ce contrôle : saine 6 749, cercosporiose noire 6 900, fusariose 4 300, autre maladie 677. Les effectifs réels sont notés ici après la préparation.
- Archive Kaggle `feuilles_pret_v3.zip`. Le carnet est vérifié en local sur un petit échantillon ; le test y est calculé sans être affiché.

## 4. Modèle et recette

- EfficientNet-B0 pré-entraîné sur ImageNet, **4 classes** (saine, cercosporiose noire, fusariose, autre maladie).
- Recette v2 inchangée : 12 époques, lots de 64, AdamW (0,0003 ; décroissance 0,0001), cosinus, lissage 0,1, recadrages de 15 à 100 %, masquage aléatoire, graine 2026. Un seul modèle (pas de v1), 4 vues (identité, deux miroirs, rotation de 180°).
- **Échantillonnage** : « autre maladie » ne fait que 3,6 % des images ; elle est tirée pour **10 % des images de chaque époque** (environ 2,7 passages par image), les trois autres classes gardant leurs proportions naturelles dans les 90 % restants. Ce chiffre est fixé ici et ne sera pas réglé.

## 5. Règle de choix (VT seulement)

- **Époque** : meilleure moyenne des F1 macro sur VT, images entières et recadrages centrés (même critère que le v2), calculés sur les 3 classes de VT ; une réponse « autre maladie » sur une feuille de VT compte comme une erreur.
- **Seuil de rejet** : probabilité maximale, réglée pour accepter 95 % des feuilles de VT (même règle que le v2).
- **Décision du bulletin** (même règle en deux étapes, seuil « malade » 0,5) : P(malade) = 1 − P(saine) ; si la feuille est malade, la maladie la plus probable est donnée si la confiance dépasse le seuil, sinon « malade, non identifiée » ; la classe « autre maladie » donne aussi « malade, non identifiée ». Pour le v2, P(malade) = 1 − P(saine) est exactement la règle actuelle. Le module `fieldscan/modules/maladies.py` est adapté pour lire une quatrième classe.

## 6. Adoption (v3 contre v2, sur la décision du bulletin)

Le v2 est mesuré par le même code, sur les mêmes images, avec son propre seuil. Mesures :
- **inconnues signalées** : part des 839 inconnues de VH (Cordana, Pestalotiopsis, Cordana du Pérou) annoncées « malade, non identifiée » ;
- **critère de VT** : moyenne des F1 macro, entières et recadrages (section 5) ;
- **fausses alertes** : part des feuilles saines de VT et de VH (1 090) annoncées malades ;
- **maladies manquées** : part des feuilles malades connues de VT et de VH (2 474) annoncées saines ;
- **rappel de la fusariose** sur VT (réponse « fusariose ») : le risque principal, le flétrissement bactérien imitant la fusariose.

**Le v3 remplace le v2 si ses inconnues signalées sont strictement plus nombreuses et si, en même temps** :
- son critère de VT ne perd pas plus de 0,01 ;
- ses fausses alertes et ses maladies manquées n'augmentent pas de plus de 0,5 point chacune ;
- son rappel de la fusariose ne perd pas plus de 2 points.

Décision écrite avant tout test. Cartes d'attention (Grad-CAM) sur des inconnues de VH et des feuilles de VT, pour la lecture seulement.

## 7. Test (une seule fois, v2 et v3 rapportés)

**Banana Disease Recognition**, dossier `Original Images`, chaque image comptée une fois (aucun regroupement : la seule paire trouvée est fausse). Réponse = décision du bulletin.

| Classe du jeu | Rôle | Réponse juste |
| --- | --- | --- |
| Healthy Leaf (86) | saine | « saine » |
| Black Sigatoka (67) | cercosporiose noire | « cercosporiose noire » |
| Panama (41) | fusariose (première mesure hors de Tanzanie) | « fusariose » |
| Yellow Sigatoka (23) | maladie inconnue | « malade, non identifiée » |
| Moko (55) | maladie inconnue (flétrissement bactérien) | « malade, non identifiée » ou « fusariose ou autre flétrissement vasculaire » (libellé du bulletin) |
| Bract Mosaic Virus (50) | hors du domaine du module (photos de pseudo-tronc, pas de feuilles) | rapporté à part, à titre indicatif |
| Insect Pest (86) | ravageurs, pas une maladie | rapporté à part, à titre indicatif |

Mesures sur les 272 images de la mesure principale :
- **F1 par classe et F1 macro** sur saine, cercosporiose noire et fusariose (194 images), une réponse « je ne sais pas » ou « malade, non identifiée » comptant comme une erreur ;
- **fausses alertes** : part des 86 feuilles saines annoncées malades ;
- **maladies signalées** : part des 186 feuilles malades annoncées malades (n'importe quelle maladie, ou « malade, non identifiée »), et part annoncée saine ;
- **inconnues bien signalées** : réponses justes du tableau, pour Yellow Sigatoka et Moko ; on note aussi la part de Yellow Sigatoka annoncée « cercosporiose noire » (maladie voisine).

Aucun réglage après le test. Le résultat est écrit ici tel quel, même s'il est moins bon que la validation.

**Limite connue** : Banana Disease Recognition vient sans doute du Bangladesh, comme BananaLSD (lieu de collecte non indiqué). C'est un jeu, des photographes et des plantations jamais vus, mais pas forcément un pays nouveau.

## 8. Ce qui ne change pas, ce qui est remis à plus tard

- Inchangés : préparation des images, 4 vues, méthode et règle du seuil de rejet, seuil « malade » 0,5, libellés du bulletin.
- Plus tard, chacun avec sa propre règle écrite avant : réglage du rejet et du seuil de fusariose sur la validation hors domaine ; domaine de validité des photos (refuser une photo de plante entière ou de tige).

## 9. Résultats

(à remplir après la préparation, puis après l'entraînement)
