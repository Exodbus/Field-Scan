# Meilleur candidat de la famille C (mélange contenant un v12) : M-banc, 13 novembre 2026, 4 h 05 (lot 6 ajouté à 4 h 06)

Écrit **avant toute lecture des juges** (BanSpot, Cordana du Pérou, test vierge : jamais ouverts par M-banc). Familles : `docs/nuit_2026-11-12/regle_gel_finalistes.md`. Règle « finaliste » : `docs/plan_nuit_2026-11-12.md`, 4.4, inchangée. La grille et la règle de choix ont été écrites dans `docs/nuit_2026-11-12/journal_m_banc.md` (4 h 00) avant la mesure.

## Candidat : `C_quatre_v12a14`

- **Lecteur « proche »** : moyenne géométrique, poids égaux, de quatre modèles sur les 3 classes communes (saine, Sigatoka noire, fusariose) :
  - **v10b** (`modeles/maladies_binome/v10b`) ;
  - **soupe v2 + v8** (`modeles/maladies_soupe_v2_v8/poids`) ;
  - **v2** (`modeles/maladies_binome/maladies_v2/poids`) ;
  - **v12a14** (modèle final `modeles/maladies_v12_essais/v12a14/`).

  « Autre » = 1/4 × P(autre) de la v10b + 1/4 × P(autre) de la v12a14. Le tout est renormalisé, puis décidé par `decider_convnext` avec les seuils de la v10b, sauf **`seuil_confiance` (règle B) = 0,76**.
- **Aiguilleur** inchangé.
- **Branche « loin »** : réponse de la v2 (politique b) ; si elle n'alerte pas, réponse du lecteur proche.
- Lecture entière, 384 px, 4 vues, préparation de la chaîne.
- Finaliste pour t de 0,62 à 0,78 ; t = 0,76 a ses deux voisins finalistes.

## Lot 6 (a17 à a20), passé à 4 h 05 par la même grille, sans l'élargir (256 essais)

Meilleur point sûr du lot : **à quatre v10b + soupe + v2 + a19, t = 0,76, coût 34,73** (finaliste de 0,64 à 0,78). Validation 2 ; 71 (51 à vérifier) ; TDTU 18 ; 248 ; PSFD 78 ; Éthiopie 120 ; 31. Suivants du lot :
- a18 + soupe, t = 0,76 : 36,05 ;
- a19 + soupe, t = 0,74 : 36,14 ;
- a18 à quatre, t = 0,76 : 36,20.

**a19 n'a pas de modèle final.** M-entraînement a gelé ses recettes à 4 h 10 et n'entraîne plus rien. Le modèle installé serait le modèle final, et on ne peut ni l'installer ni le contrôler sur la validation. a19 ne remplit donc pas la condition « modèle final contrôlé » de la demande de 4 h. Il ne devient candidat que si un modèle final a19 (3 réseaux, recette `out/maladies/nuit_1112/kaggle/a19/recette_a19.json`, 5 époques) est entraîné et contrôlé avant 6 h 45. Écart avec a14 : 1,3 point, obtenu après 256 essais de plus. M-entraînement note par ailleurs que 5 époques n'ont pas aidé le v12 seul.

**Candidat retenu pour la famille C : `C_quatre_v12a14`** (ci-dessous), le meilleur dont le modèle final existe et a été contrôlé.

## Chiffres de réglage

Probabilités de la v12a14 : TDTU et Éthiopie lus par le pli qui n'a pas appris le pays ; PSFD (jamais appris) ; validation = moyenne des 2 plis présents.

| Chaîne | Validation (ratées / 2 001 ; saines en alerte / 1 000, dont à vérifier) | Sigatoka nommée | TDTU (/ 1 059 ; / 577) | PSFD (/ 738) | Éthiopie (/ 1 134 ; / 155) | Coût moyen |
| --- | --- | --- | --- | --- | --- | --- |
| Installée (v10b) | 9 ; 57 (25) | 872 | 83 ; 177 (38) | 149 | 179 ; 43 (18) | 49,23 |
| **C_quatre_v12a14, t = 0,76** | **2 ; 68 (48)** | 909 | **15 ; 260 (123)** | **86** | **122 ; 32 (31)** | **36,07** |
| Pour comparaison : F3 (famille A, à trois) | 2 ; 57 (48) | 916 | 28 ; 232 (136) | 109 | 134 ; 27 (27) | 37,83 |

- Coût par jeu : validation 7,1 ; TDTU 49,3 ; PSFD 35,0 ; Éthiopie 52,9.
- Pour information (la règle compte PSFD avec ses 738 photos) :
  - PSFD sans les 123 copies tournées : 45 / 615 ratées, coût moyen 32,82 ;
  - une photo par groupe de quasi-copies : 27 / 188, coût moyen 38,10.

**Contrôle du modèle final** (3 réseaux appris sur tout sauf PSFD et la validation ; `out/maladies/nuit_1112/kaggle/final_a13_a14/predictions_a14_final_validation.csv`). Validation Tanzanie, même mélange, t = 0,76 : **3 / 2 001 ratées, 69 / 1 000 saines en alerte** (dont 52 à vérifier), Sigatoka nommée 902 / 1 000. Les limites du plan (14 et 77) sont respectées. Avec les plis : 2 et 68.

Suivants de la famille C, pour mémoire (même règle de plateau) :
- a14 + soupe, t = 0,72 : 36,48 ; modèle final en validation 4 ; 63 ;
- a13 à quatre, t = 0,72 : 36,64 ; modèle final 3 ; 63 ;
- a14 + soupe + v2, t = 0,78 : 36,66.

## Nombre d'essais

- Famille C : **518** : 256 pour le lot 6, 70 avec `scripts/m12_banc_v12.py` sur a13 et a14 ; 192 avec la grille courte `scripts/m12_banc_v12_grille.py` sur a13, a14 et a4. S'y ajoutent les 245 essais de 0 h 23 et 23 h 36 sur les v12 précédentes.
- Total M-banc de la nuit : **1 733 essais de réglage**. Le coût de réglage est donc optimiste.

## Temps de calcul

Estimés sur le PC (processeur libre), par photo :
- v10b ≈ 1,8 s ; v12a14 ≈ 1,8 s (même architecture : 3 ConvNeXt-Tiny DINOv3, 384 px, 4 vues) ; soupe ≈ 0,7 s ; v2 ≈ 0,7 s ;
- **C_quatre_v12a14 ≈ 5 s par photo** (installée 1,8 s ; F3 ≈ 3,2 s) ;
- les photos « loin » sont lues par les quatre modèles, puisque la branche loin consulte le lecteur proche.

## Recalcul sur n'importe quel jeu

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_banc_finalistes.py \
    --v10b p_v10b.npy --soupe p_soupe.npy --v2 p_v2.npy --loin p_loin.npy --v12 p_v12a14.npy \
    [--verite verite.csv] --sortie reponses.csv
```
- Colonne `C_quatre_v12a14` ; vérifié : redonne 36,07 sur le réglage.
- Sur les juges, il faut d'abord les probabilités du **modèle final** v12a14 : `predire_convnext` avec `charger_convnext(modeles/maladies_v12_essais/v12a14)`.

## Correctif (non appliqué)

Mêmes changements que pour F3 (`out/maladies/nuit_1112/banc/finalistes.md`, section 5), avec un quatrième modèle :
```yaml
  melange_proche: [modeles/maladies_soupe_v2_v8/poids, modeles/maladies_binome/maladies_v2/poids, modeles/maladies_v12_essais/v12a14]
  seuil_confiance_melange: 0.76
  loin_ou_proche: true
```
Dans le code, utiliser la fonction `geo4` de `scripts/m12_banc_finalistes.py`.
