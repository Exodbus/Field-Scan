# Protocole : la v10b du binôme comme branche « gros plan » du module maladies

Écrit le 11 novembre 2026 par Claude, **avant d'avoir les poids de la v10b et avant toute prédiction de la v10b sur nos jeux**. Décision de Corentin (11 novembre) : intégrer la v10b du binôme dans la chaîne. Ce protocole ne décide donc pas de l'adoption : il fixe le contrôle d'intégration, deux garde-fous qui peuvent encore l'arrêter, et ce qui sera rapporté. Rien n'est commité sans l'accord de Corentin ; tant que ce fichier n'est pas commité, son empreinte SHA-256 et l'heure sont notées dans le journal avant la mesure.

## 0. Ce qu'on sait de la v10b (récap du binôme du 11/11, non vérifié par nous)

- 3 ConvNeXt-Tiny aux poids DINOv3 (`convnext_tiny.dinov3_lvd1689m` dans timm, à confirmer), photo lue en 384 px, 4 vues, 4 classes (saine, Sigatoka noire, fusariose, « autre » : insectes, Sigatoka jaune, Moko, flétrissement bactérien, Cordana d'Inde et du Bangladesh, Pestalotiopsis).
- Règle B : une feuille n'est dite saine que si P(saine) ≥ 0,519 ; sinon « à vérifier », qui déclenche une alerte. Règle de la v11 : un « je ne sais pas » avec 1 − P(saine) ≥ 0,675 devient « malade, non identifiée ».
- Sur BanSpot (Kerala, 1 292 photos, test du binôme) : malades ratées 0,93 % contre 3,56 % pour la v2 ; fausses alertes 10,2 % contre 5,1 %. Sa propre règle, écrite avant BanSpot, gardait la v2 ; il l'a installée quand même.
- Environ 3 s par photo sur 2 cœurs (1 s pour la v2).

## 1. Ce qu'on demande au binôme

1. Le dossier `modeles/maladies/` de la v10b : les 3 poids, `seuils.json` (avec les seuils de la règle B et de la v11).
2. Son `maladies/classifieur.py` du 11/11 (préparation exacte en 384 px, ordre des classes, décision).
3. **La liste de ses images d'apprentissage** (noms ou SHA-256, par jeu). Sans elle, on ne sait pas quels jeux de mesure sont propres pour la v10b.
4. Ses probabilités sur 80 photos (fichier CSV avec chemin et probabilités), pour le contrôle d'intégration.

## 2. Contrôle d'intégration (condition d'installation)

Sur les 80 photos du point 1.4 lues par notre module (`fieldscan/modules/maladies.py`) : probabilités égales à 10⁻³ près et réponses identiques à celles de son `classifieur.py`. Si ce n'est pas le cas, la v10b n'est pas installée tant que l'écart n'est pas expliqué.

## 3. Garde-fous (peuvent arrêter l'installation)

Mesurés une fois, sur nos jeux, **seulement les photos absentes de son apprentissage** (contrôle par la liste du point 1.3, puis dHash ≤ 10 bits sous les 8 symétries contre les jeux qu'il cite) :

- **G1, validation (3 001, Tanzanie 2022-2023)** : malades sans alerte du module avec la v10b ≤ celles du module actuel (9 / 2 001) + 10. Les fausses alertes sont rapportées sans seuil : les 1 000 saines contiennent des feuilles malades (relecture du binôme : 10 à 17 sur 60).
- **G2, temps** : la chaîne complète sur `data/demo_feuilles` tourne de bout en bout, et le temps par photo sur ce PC est rapporté (aucune borne : c'est un coût connu).

Si G1 échoue, Corentin est prévenu et la chaîne garde la soupe en attendant sa décision.

## 4. Rapporté, sans effet sur la décision

Module actuel (aiguilleur, soupe, politique b) contre module avec la v10b en branche « gros plan » (aiguilleur et branche « loin » inchangés), sur chaque jeu propre pour la v10b parmi : validation, BananaLSD, TDTU, PSFD, Éthiopie, Cordana du Pérou (505, jamais lue par un ConvNeXt), photos de loin du robot et du téléphone :
- malades sans alerte, saines en alerte, Sigatoka nommée, réponses « autre maladie » et « à vérifier » ;
- maladies inconnues (Cordana, Pestalotiopsis, Xanthomonas, Sigatoka jaune) : part en alerte, part dite Sigatoka.

Un jeu qui recouvre son apprentissage est rapporté à part, marqué « vu par la v10b ».

## 5. Branchement dans la chaîne

- `maladies.modele` pointe sur le dossier de la v10b ; `reseau: convnext_dinov3`, `taille: 384`, `classes` à 4 dont `autre` ; `seuil_saine` (règle B) et `seuil_jnsp_malade` (v11) lus dans `seuils.json`.
- Réponses : « autre maladie » → alerte, gravité forte ; « à vérifier » (règle B) → alerte, confiance faible (pénalité réduite de moitié, comme la branche « loin »), message « le modèle ne sait pas dire si la feuille est saine ».
- Température : réglée sur la validation (`scripts/regler_temperature.py`), décisions inchangées.
- Retour arrière : `maladies.modele: modeles/maladies_soupe_v2_v8/poids` dans `config.yaml`.

## 6. Amendement 1 (11 novembre 2026, vers 12 h 30, après réception des fichiers du binôme, avant toute prédiction de la v10b sur nos jeux)

**Ce qui a été fait avant cet amendement** :
- Fichiers reçus : archive `partage_corentin_2026-11-11.zip`, décompressée dans `data/raw/partage_binome_v10b/`, poids copiés dans `modeles/maladies_binome/v10b/` (SHA-256 : `cdb40911…`, `b09cd2a5…`, `cce62225…`).
- Son `seuils.json` diffère de ce que prévoyait la section 5 :
  - lecture du JPEG en 896 px ;
  - « autre » jamais nommée (une photo dont la maladie la plus probable est « autre » devient « malade, non identifiée ») ;
  - règle B appliquée avec le seuil de confiance (0,519) ;
  - seuil de la v11 sous le nom `seuil_inconnu_malade` (0,675).

  `fieldscan/modules/maladies.py` lit maintenant ce format tel quel. Dans notre chaîne, tout « je ne sais pas » restant après ces règles devient « à vérifier » : une alerte de confiance faible, comme « inconnu » dans la chaîne du binôme.
- **Contrôle d'intégration (section 2) : réussi.** Sur ses 40 photos de BanSpot, l'écart maximal des probabilités est de 7,2 × 10⁻⁷, et les 40 réponses sont identiques. Temps : 1,8 s par photo sur ce PC.
- Non-régression du code : avec la soupe, les sorties sont identiques à avant (écart 0, mêmes réponses sur `data/demo_feuilles`).
- Recouvrements, par les SHA-256 de sa liste (`liste_apprentissage_v10.csv`, photos d'origine et copies en 448 px) :
  - **BananaLSD : 670 des 897 photos dans son apprentissage** (et 223 dans sa validation) ;
  - nos 3 001 photos de validation : aucune dans son apprentissage. Elles sont toutes dans sa validation (Tanzanie 2025), qui a servi à régler ses seuils, comme pour nos modèles ;
  - Cordana du Pérou, TDTU, PSFD et Éthiopie (fichiers préparés et bruts) : aucune.

**Changements** :
1. Le contrôle par dHash contre cm8zf62kzh et BLADE (section 3) n'est pas fait : nous n'avons pas ces jeux. Le contrôle se limite aux SHA-256. Une copie recompressée y échapperait ; c'est une limite à rapporter. L'audit du binôme du 11/11 (SIFT sur 5 614 paires) n'a trouvé aucune copie entre jeux.
2. BananaLSD est rapporté à part, « vu par la v10b » (section 4).
3. Les photos de loin du robot et du téléphone ne sont pas recalculées : la branche « loin » ne change pas. Seules les photos aiguillées « proche » passent par la v10b.
4. Mesures, dans l'ordre :
   - G1 sur la validation ;
   - le rapport sur la Cordana du Pérou, TDTU, PSFD, Éthiopie et BananaLSD.

   Le module actuel est recalculé à partir des fichiers de prédictions existants (`scripts/evaluer_module_maladies.py`). La Cordana du Pérou n'a pas encore de prédictions de la soupe ni de la v2 : elles sont calculées avec les mêmes réglages.

## 7. Résultats (11 novembre 2026, vers 13 h 15, mesure unique)

**Calcul** :
- Carnet Kaggle `affilecorentin/predire-v10b` : T4, 32 bits, 22 min pour les 8 066 photos.
- Contrôle : 20 photos refaites en local, écart maximal 6,3 × 10⁻⁷.
- Soupe, v2 et aiguilleur sur la Cordana du Pérou : en local.
- Mesure : `scripts/mesurer_v10b.py` ; sortie dans `out/maladies/v10b/bilan_v10b.json`.

**Garde-fou G1 : rempli.** Validation, malades sans alerte du module avec la v10b : **9 / 2 001** (limite 19). **La v10b est installée** dans `config.yaml`. Température d'affichage : 0,79, réglée sur la validation.

Module actuel (soupe en gros plan) contre module avec la v10b. L'aiguilleur et la branche « loin » ne changent pas.

| Jeu | Malades sans alerte | Saines en alerte | Sigatoka nommée | Inconnues dites Sigatoka |
| --- | --- | --- | --- | --- |
| Validation (Tanzanie 2022-2023) | 9 → 9 / 2 001 | 15 → **57** / 1 000 | 965 → 872 / 1 000 | |
| Cordana du Pérou (jamais lue) | 7 → 5 / 505 | | | **453 → 262** / 505 |
| TDTU (Vietnam) | 153 → **83** / 1 059 | 119 → **177** / 577 | 112 → 59 / 404 | |
| PSFD (Inde) | 298 → **149** / 738 | | 108 → 97 / 474 | |
| Éthiopie | 338 → **179** / 1 134 | 2 → **43** / 155 | 48 → 47 / 320 | |
| BananaLSD (**vu par la v10b** : 670 photos apprises) | 0 → 0 / 807 | 3 → 5 / 90 | 452 → 451 / 473 | 273 → 2 / 334 |

**Lecture** :
- **Pays neufs** : la v10b divise par deux les malades sans alerte (TDTU − 46 %, PSFD − 50 %, Éthiopie − 47 %).
  - PSFD, Sigatoka jaune dite saine : 103 → 89 / 264.
  - Éthiopie, Xanthomonas dit saine : 223 → 164 / 814.
- **Maladie inconnue, Cordana du Pérou (jamais lue par aucun des deux modèles)** : la part dite Sigatoka passe de 90 % à 52 %. Le reste devient surtout « malade, non identifiée » (231). C'est le gain le plus net sur le rejet de l'inconnu.
- **Le prix : des fausses alertes.**
  - Validation : 57 / 1 000 au lieu de 15, dont 25 « à vérifier » (confiance faible) et 32 alertes franches. Le binôme estime qu'entre 10 et 28 % de ces feuilles saines (HEALTHY-1) sont en fait malades ; une partie de ces alertes serait donc juste.
  - Éthiopie : 43 / 155 (28 %) au lieu de 2, dont 18 « à vérifier ».
  - TDTU : 177 / 577 (31 %) au lieu de 119.
- **La Sigatoka est moins souvent nommée** (validation 872 au lieu de 965, TDTU 59 au lieu de 112). Les alertes restent, mais en « malade, non identifiée » (637 réponses de ce type en validation au lieu de 109).
- **Temps** : 1,8 s par photo sur ce PC, contre 0,7 s pour la soupe.
