# Fiche `amelioration-modele` (nuit du 8 au 9 novembre 2026)

Rôle : fusion maths + IA, calibration et décision, recette de la v7 (brouillon de carnet Kaggle). Aucun GPU lancé, aucun téléchargement, aucun commit. Sorties dans `out/maladies/equipe/amelioration-modele/`.

Étiquettes : [O] observé, [S] source, [H] hypothèse, [M] mesuré (commande + fichier).

## 0. Constats préalables (avant toute mesure)

- [O] Les seuils de la v2 (`seuils.json` : alerte 0,30, nom 0,50, confiance 0,646) ont été réglés par le binôme sur la **Tanzanie 2022-2023 complète (11 766 images)** (`LISEZMOI.md`), dont nos 3 001 images de validation sont tirées. La v2 a donc déjà « vu » la validation pour ses seuils : une méthode dont les seuils sont réglés sur le développement part avec un handicap si on la compare à la v2 avec ses seuils.
- [O] Le développement Tanzanie 2021 + Pérou est **l'entraînement même de la v2** : ses probabilités y sont sur-confiantes. [H] Une régression apprise dessus donnerait tout le poids à la v2 et presque rien aux descripteurs. Le développement utile pour apprendre une fusion est la partie **que la v2 n'a jamais vue : TDTU et khadavy** (2 067 images).
- [O] La v2 n'a que 3 classes ; TDTU et khadavy ont des « autre_maladie » (Sigatoka jaune, flétrissements bactériens). En binaire (malade / saine), elles comptent comme malades.

## 1. Critères écrits avant les mesures

### E-AM-01 : empilement [P(malade) v2 + descripteurs] par régression logistique

- **Hypothèse** : des descripteurs explicites (couleur, forme) apportent à la v2 une information qu'elle n'a pas, surtout hors de son domaine (taches précoces).
- **Apprentissage** : sur le développement **non vu par la v2** (TDTU + khadavy), étiquette binaire malade / saine. Variables : logit de P(malade) de la v2, plus descripteurs standardisés (moyenne et écart-type du développement ; valeurs manquantes remplacées par la moyenne). Régression logistique pénalisée L2, **λ fixé à 1e-2** (perte moyenne + λ‖w‖²), sans réglage. Si les descripteurs dépassent 30 colonnes, on garde les 30 de plus forte AUC univariée sur le développement (choix fait sur le développement).
- **Référence de même nature** : régression logistique sur le seul logit de la v2, apprise sur le même développement (v2 recalibrée). La v2 avec `seuils.json` est rapportée à côté.
- **Seuil de décision** : pour chaque méthode, celui qui rend minimal « 2 × malades ratées + fausses alertes » sur le développement (règle de la v2).
- **Mesures** sur la validation (3 001) et BananaLSD (malade = cercosporiose, Cordana, Pestalotiopsis ; saine = saine) : AUC de P(malade), coût 2 × ratées + fausses alertes au seuil du développement, taux de ratées et de fausses alertes. Intervalle bootstrap (1 000 tirages) sur la différence d'AUC.
- **Réussite** si, sur la validation **et** sur BananaLSD : AUC(empilement) − AUC(référence) ≥ +0,005, et coût au seuil du développement plus bas que la référence. Sinon échec, écrit tel quel.

### E-AM-02 : règle simple « la v2 dit saine mais les taches disent malade »

- **Règle** : si la v2 répond « saine » (P(malade) < 0,30) et qu'un descripteur D dépasse un seuil t, la réponse devient « malade ».
- **Choix de D et de t, sur le développement (TDTU + khadavy) seulement** : D = le descripteur de plus forte AUC (malade contre saine) parmi les images que la v2 dit saines, signe compris ; t = le seuil qui rend minimal 2 × ratées + fausses alertes de la règle complète sur le développement.
- **Mesures** sur la validation et BananaLSD : coût, malades dites saines, fausses alertes, contre la v2 seule (`seuils.json`).
- **Réussite** si le coût baisse sur la validation **et** sur BananaLSD, et si les fausses alertes de la validation augmentent d'au plus 1 point (garde de non-régression du protocole v5). Sinon échec.

### E-AM-03 : calibration par la température

- **Méthode** : p_T ∝ p^(1/T) appliqué aux probabilités moyennes de la v2 (3 classes). T est réglé par la vraisemblance sur la **validation** (3 001, 3 classes), grille 0,25 à 4.
- **Mesures** : sur BananaLSD (saines et cercosporioses seulement, seules classes communes), log-perte et erreur de calibration (ECE, 10 classes de confiance) avant et après.
- **Réussite** si la log-perte et l'ECE de BananaLSD baissent toutes deux. Lecture seulement : la température ne change ni l'ordre des classes, ni la décision si les seuils sont réglés de nouveau ; elle sert à rendre lisibles les probabilités affichées et à combiner des modèles.

### E-AM-04 : effet de la classe « autre » (lecture, sans choix)

- Sur le développement (TDTU + khadavy autre_maladie) et les inconnues de BananaLSD : part dite malade, part nommée fusariose ou cercosporiose, part « malade, non identifiée » et « je ne sais pas », avec la v2 (et la v5 si elle arrive). Aucun seuil réglé ici.

### E-AM-05 : fusion v2 + B0 (écrit avant la mesure, mêmes règles que E-AM-01)

- Régression logistique sur [logit P(malade) v2, logit P(malade) B0], apprise sur TDTU + khadavy, λ = 1e-2, seuil réglé sur le développement ; référence : la v2 recalibrée seule (E-AM-01). Même critère de réussite que E-AM-01 (AUC +0,005 et coût plus bas, sur la validation et sur BananaLSD).
- Variante « tout » : la même régression avec v2, B0 et les descripteurs retenus.

### Variante d'apprentissage (rapportée, ne décide rien)

- Chaque régression est aussi apprise sur **tout** le développement prédit (TDTU, khadavy, 300 images par source et classe de la Tanzanie 2021 et du Pérou), pour montrer l'effet des probabilités sur-confiantes de la v2 sur son propre entraînement.

### E-AM-06 : gain hors domaine, croisé entre sources du développement (écrit le 9 novembre, après l'incident décrit en section 2, dont les chiffres sont sans valeur, et avant l'arrivée de tout descripteur complet)

- **Pourquoi** : [M] la v2 est déjà au plafond en binaire sur la validation (AUC 0,9998) et sur BananaLSD (AUC 1,0000) (`fusion_tableau.csv`). Le critère d'E-AM-01 (+0,005 d'AUC) ne peut donc presque pas être atteint là, quelle que soit la méthode. Il reste écrit tel quel et sera rapporté tel quel. Le seul endroit où la v2 se trompe est hors domaine : TDTU + khadavy (AUC 0,909 ; 13 % de malades ratées, 24 % de fausses alertes au seuil 0,30).
- **Mesure** : régressions d'E-AM-01 (mêmes variables, même λ, seuil réglé sur la source d'apprentissage), apprises sur TDTU et mesurées sur khadavy, puis l'inverse. Référence : la v2 recalibrée, apprise de la même façon.
- **Réussite** si l'AUC de l'empilement dépasse celle de la référence d'au moins **0,01 dans les deux sens**, et si le coût baisse dans les deux sens. Ces deux jeux sont du développement : le résultat sert à décider s'il vaut la peine de proposer la fusion à l'orchestrateur, pas à l'adopter.

## 2. Résultats

### Incident du 9 novembre (lancement sur fichiers incomplets, non compté)

Un premier lancement de `fusion.py` a eu lieu alors que seul `math-forme/descripteurs_dev.csv` existait : les descripteurs de la validation et de BananaLSD manquaient tous et ont été remplacés par la moyenne. Les chiffres d'E-AM-01 et d'E-AM-02 de ce lancement n'ont **aucune valeur**. Ils sont gardés à part, sous le nom `*_partiel_invalide.*`, et ne départagent rien. Correctif : un agent n'entre dans la fusion que si ses descripteurs couvrent au moins 95 % des lignes de chacun des trois jeux (une ligne est couverte si au moins un descripteur y est renseigné). C'est une condition de validité, pas un réglage. Les critères de la section 1 sont inchangés.

### Étape 1 (v2 seule ; sans descripteurs complets ni B0 sur le développement)

Commande : `OMP_NUM_THREADS=2 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/maladies/equipe/amelioration-modele/fusion.py`. Sorties : `out/maladies/equipe/amelioration-modele/fusion_resultats.json`, `fusion_tableau.csv`, journal `fusion_etape1.log`.

**Référence, v2 avec `seuils.json`** [M], en binaire malade / saine :

| Jeu | AUC | malades ratées | fausses alertes | coût 2R + F |
| --- | --- | --- | --- | --- |
| Développement non vu (TDTU + khadavy, 2 067) | 0,909 | 173 / 1 331 (13,0 %) | 175 / 736 (23,8 %) | 521 |
| Validation (3 001) | 0,9998 | 4 (0,2 %) | 25 (2,5 %) | 33 |
| BananaLSD (897) | 1,0000 | 0 | 4 (4,4 %) | 4 |

- [M] **v2 recalibrée** (régression sur son logit, apprise sur TDTU + khadavy, seuil réglé sur ce développement) : 1 ratée et 64 fausses alertes (coût 66) en validation, 0 et 8 (coût 8) sur BananaLSD. C'est **plus mauvais que `seuils.json`** : le seuil appris hors domaine (où beaucoup de malades ont l'air saines) pousse à alerter trop tôt dans le domaine. [H] Un seuil réglé sur un domaine ne se transporte pas à un autre ; la décision doit garder un seuil réglé sur la validation.

**E-AM-03, température : réussite** [M]. T = 0,60, réglée sur la validation : la v2 est **trop peu confiante** (moyenne de 4 vues × 3 réseaux et lissage des étiquettes 0,1).

| | log-perte avant → après | ECE avant → après |
| --- | --- | --- |
| Validation (où T est réglée) | 0,157 → 0,106 | 0,070 → 0,005 |
| **BananaLSD (saines + cercosporioses)** | **0,150 → 0,092** | **0,079 → 0,016** |

Conséquence pratique [H] : afficher `p^(1/0,6)` renormalisé donne des probabilités lisibles. L'ordre des classes ne change pas. Le seuil d'alerte doit être transposé : 0,30 sur l'échelle brute correspond à un autre nombre après la température. À utiliser pour combiner des modèles (v2 + v5, v2 + descripteurs), pas pour changer la décision de la chaîne.

**E-AM-04, effet de la classe « autre »** [M] (réponses de la v2) :

| Jeu | n | dite malade | fusariose | cercosporiose | je ne sais pas | saine |
| --- | --- | --- | --- | --- | --- | --- |
| khadavy Bercak-Kuning (Sigatoka jaune) | 27 | 100 % | 27 | 0 | 0 | 0 |
| TDTU autre_maladie (flétrissements bactériens) | 655 | 89 % | 394 | 14 | 178 | 69 |
| BananaLSD Cordana | 162 | 100 % | 15 | 93 | 54 | 0 |
| BananaLSD Pestalotiopsis | 172 | 100 % | 20 | 137 | 15 | 0 |

Lecture : la v2 **détecte** presque toujours ces maladies inconnues, mais leur donne un nom faux. Elle range les maladies jaunissantes ou flétrissantes en fusariose, les maladies à taches en cercosporiose. « Je ne sais pas » n'en rattrape qu'une partie (0 % à 33 %). La classe autre_maladie de la v5 et de la v7 vise exactement ce défaut. La mesure de la v5 sur ces mêmes jeux dira si elle le corrige (TDTU et khadavy sont appris par la v5 : seul BananaLSD vaudra).

**E-AM-05, fusion v2 + B0 : échec** [M] (9 novembre ; journal `fusion_etape2.log`, chiffres dans `fusion_tableau.csv` et `fusion_resultats.json` ; descripteurs encore incomplets, donc écartés par la condition de couverture).

| Jeu | v2 recalibrée : AUC, coût (R / F) | v2 + B0 : AUC, coût (R / F) | Δ AUC [IC 95 %] |
| --- | --- | --- | --- |
| Validation | 0,9998, 66 (1 / 64) | 0,9998, 99 (0 / 99) | 0,0000 [0,0000 ; 0,0001] |
| BananaLSD | 1,0000, 8 (0 / 8) | 0,9999, 13 (0 / 13) | −0,0001 [−0,0002 ; 0,0001] |
| Développement non vu (apprentissage) | 0,909, 440 | 0,908, 452 | — |

Lecture : le B0 n'ajoute rien à la v2, même hors domaine, sur le développement où la régression est apprise. Le plafond de la validation et de BananaLSD rendait de toute façon le critère presque inatteignable (voir E-AM-06). La variante apprise sur tout le développement ne change rien (coûts 78 et 11). Le B0 n'a pas sa place dans une fusion avec la v2.

### Étape 2 : fusion complète (9 novembre ; descripteurs des deux mathématiciens)

Commande : `OMP_NUM_THREADS=2 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/maladies/equipe/amelioration-modele/fusion.py`. Journal `fusion_complete.log` ; sorties `fusion_resultats.json`, `fusion_tableau.csv`, `fusion_coefficients.csv`. Couverture : 100 % des lignes des trois jeux pour les deux agents ; 77 descripteurs de math-couleur et 66 de math-forme.

Colonnes écartées **avant la mesure** : d'après la consigne de l'orchestrateur, `f_fond_blanc` et `f_feuille` (artefact : les saines de TDTU sont détourées sur fond blanc), `mc_*` (sorties de leur propre modèle) et `repli_masque` (présente sur le seul développement). Par le même principe, j'ai aussi écarté `part_feuille` et `fond_part` de math-forme.

| Méthode (apprise sur TDTU + khadavy) | Validation : AUC, coût (R / F) | BananaLSD : AUC, coût (R / F) | Dév. non vu : AUC, coût |
| --- | --- | --- | --- |
| v2 avec `seuils.json` (rappel) | 0,9998, 33 (4 / 25) | 1,0000, 4 (0 / 4) | 0,909, 521 |
| **v2 recalibrée (référence)** | 0,9998, 66 (1 / 64) | 1,0000, 8 (0 / 8) | 0,909, 440 |
| v2 + 30 descripteurs | 0,9983, 560 (0 / 560) | 0,9858, 24 (0 / 24) | 0,937, 364 |
| v2 + B0 + 30 descripteurs | 0,9990, 527 (0 / 527) | 0,9934, 23 (0 / 23) | 0,937, 361 |
| Règle E-AM-02 (`nerv_coherence_locale` basse) | —, 321 (3 / 315) | —, 26 (0 / 26) | —, 423 |

- **E-AM-01 : échec** [M]. Δ AUC −0,0015 [−0,0023 ; −0,0008] sur la validation et −0,014 [−0,029 ; −0,003] sur BananaLSD ; le coût est multiplié par 8 en validation (560 contre 66). Les descripteurs améliorent le développement où ils sont appris (AUC 0,909 → 0,937), mais **dégradent les deux jeux de mesure**.
- **E-AM-05 « tout » (v2 + B0 + descripteurs) : échec**, même tableau.
- **E-AM-02 : échec** [M]. La règle choisie sur le développement (le descripteur le plus discriminant parmi les images que la v2 dit saines : `math-forme:nerv_coherence_locale`, sens bas) ne change rien aux malades ratées. Elle fait passer les fausses alertes de 25 à 315 en validation et de 4 à 26 sur BananaLSD.
- **E-AM-06 (croisé entre sources) : échec** [M]. Appris sur TDTU et mesuré sur khadavy : AUC 0,922 → 0,869, coût 105 → 155. Appris sur khadavy et mesuré sur TDTU : AUC 0,907 → 0,899, coût 378 → 411. Même d'une source hors domaine à une autre, les descripteurs ne se transportent pas.
- Variante apprise sur tout le développement : même conclusion (validation : coût 129 contre 66 ; BananaLSD : 24 contre 8).
- **Exploratoire, écrit après ces résultats et sans valeur de décision** (`regle_necrose_exploratoire.py`, sortie `regle_necrose_exploratoire.csv`) : l'exemple de la mission, « la v2 dit saine mais la nécrose dépasse t », avec t réglé sur TDTU + khadavy, pour trois descripteurs fixés dans le script.
  - `f_necrose` : coût 521 → 495 sur le développement, mais 33 → 55 en validation (fausses alertes 25 → 51) ; BananaLSD inchangé (4).
  - `tache_dens_s3` et `tache_fort_dens_s3` : un petit gain sur le développement (521 → 501 et 513), aucun changement sur la validation ni sur BananaLSD (le seuil appris ne s'y déclenche jamais).

**Lecture** [M] puis [H] :
- [M] Les descripteurs les plus discriminants sur le développement sont des parts de jaune et de non-vert (`f_jaune`, AUC univariée 0,855 ; `Y_part`, 0,846 ; `f_ngrdi_neg`, 0,842).
- [H] Sur TDTU et khadavy, les malades sont jaunies (flétrissements, Sigatoka jaune). En Tanzanie et au Bangladesh, des feuilles saines ont aussi du jaune ou du sec, et la v2 les classe déjà presque parfaitement. Ce que la régression apprend hors domaine est une particularité de ces sources, pas une règle des maladies.
- [M] Ce constat rejoint ceux des mathématiciens : le gain apparent sur BananaLSD vient de la recalibration de la v2 (constat de math-forme). Le renommage F1 de math-couleur fait chuter la fusariose nommée en validation (88,6 % → 53,5 %, leur fiche).
- **Conclusion pour la chaîne** : ne pas fusionner les descripteurs avec la v2. Garder la v2 et ses seuils réglés sur la validation (`seuils.json` bat toutes les variantes réglées sur le développement). Les descripteurs restent utiles pour **expliquer** une réponse (part jaune, nécrose), pas pour la décider.

## 4. Recette proposée pour la v7 (brouillon, à figer par l'orchestrateur dans un protocole)

Brouillon de carnet : `out/maladies/equipe/amelioration-modele/entrainer_maladies_v7_kaggle.py` (structure du carnet de la v5, mêmes sections, mêmes règles de seuils).

| Point | v5 | v7 proposée | Justification |
| --- | --- | --- | --- |
| Réseau, départ | ConvNeXt-Tiny ImageNet | inchangé | une seule chose à la fois ; la v6 du binôme teste le départ depuis la v2 |
| Résolution | 224 px | **224 px, inchangée** | [O] l'archive `feuilles_pret_perou.zip` est déjà ramenée à 256 px de petit côté (vérifié sur 5 images de l'archive et 40 par source dans `data/feuilles/`), BananaLSD à 224, TDTU à 244 : monter à 320 ou 384 ne ferait qu'agrandir les mêmes pixels. [O] `out/maladies/resolution/resolution_validation.csv` : exactitude stable de 256 à 113 px sur la validation. Une vraie hausse de résolution demande une nouvelle préparation depuis `data/raw/` (la v6 du binôme, en 384, le dira) |
| Classes | 4 (avec autre_maladie) | inchangé | réponse « malade, autre chose » pour la Sigatoka jaune, nommée fusariose par la v2 |
| Données ajoutées | khadavy, TDTU | **+ recadrages ROAMER de Mindanao** (liste blanche dans le carnet : fusarium_leaf et moko_leaf ; **jamais** le test « de loin » `roamer_feuilles_leaf_segmentation.zip` ni Laguna, le carnet s'arrête si l'un d'eux est en entrée ; **images communes ou quasi identiques au test retirées** par la liste d'exclusion de l'évaluateur, obligatoire sur Kaggle) | [M] khadavy : feuilles vues d'en dessous presque toutes dites saines (ROAMER Black-sigatoka : 10,5 % dites malades). Aucune photo de ce style dans l'entraînement. [M] 2 137 feuilles recadrées (fusarium : 617 malades, 694 saines ; moko : 516 malades, 310 saines), boîte élargie de 10 % ; « positive » d'un champ fusariose → fusarium, d'un champ Moko → autre_maladie [H], « negative » → saine |
| Échantillonnage | Pérou ×3 ; autre_maladie 10 % | + **ROAMER 10 % des tirages** ; hors ROAMER, autre_maladie 10 % (soit 9 % du total) | assez pour apprendre le style sans le laisser dominer : les ROAMER sont des images de vidéo, très redondantes (une même feuille sur plusieurs images) |
| Augmentations | celles de la v2 | + **basse résolution** (p = 0,3, réduction ×0,25 à ×0,7 puis retour à 224) ; **flou** plus fort (noyau 7, σ ≤ 3) ; **mosaïque 2 × 2** (p = 0,15 : l'image dans une case, trois feuilles saines autour, étiquette inchangée) | vue de loin = moins de pixels par lésion, mise au point imparfaite, et feuille malade entourée de feuillage sain. La mosaïque apprend à signaler une maladie qui n'occupe qu'un quart de l'image |
| Taches précoces | — | rien de spécifique au-delà de khadavy (déjà dans la v5) | [H] les petites taches éparses demanderaient plus de pixels (voir résolution) ; la fusion avec un descripteur de taches est testée à part (E-AM-01, E-AM-02) |
| Calcul | 32 bits | **précision mixte 16 bits** + `channels_last` | 2 à 3 fois plus rapide sur T4 [H], ce qui laisse la place à la v6 dans le quota Kaggle |
| Sorties | poids, seuils, journal | + `probas_validation.csv` | pour la calibration et la fusion sans relancer le modèle |

Règle d'adoption suggérée : celle de la v5 (non-régression sur la validation et BananaLSD), **plus** une condition « de loin » mesurée une fois par l'évaluateur sur le test « de loin » (`roamer_feuilles_leaf_segmentation.zip`, Laguna étant écarté) (par exemple : feuilles malades dites malades, au moins +20 points par rapport à la v2), à écrire par l'orchestrateur avant l'entraînement.

Risques connus : étiquette « positive » de ROAMER = feuille malade sans nom vérifié de la maladie ; images de vidéo voisines (ROAMER) presque identiques ; la mosaïque peut cacher une petite lésion en la réduisant de moitié (étiquette alors bruitée).

### État du brouillon de carnet v7

- [M] **Essai local réussi** (8 novembre, 23 h 45 ; relancé le 9 novembre après les changements ci-dessous, réussi aussi, `fin code 0`) : `ESSAI_LOCAL=1 OMP_NUM_THREADS=2 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/maladies/equipe/amelioration-modele/entrainer_maladies_v7_kaggle.py`, journal `out/maladies/equipe/amelioration-modele/essai_local_v7.log`, sorties `v7_essai_local/` (poids de l'essai effacés). Processeur, sans poids ImageNet (rien téléchargé), 2 images par jeu et classe (32 en entraînement dont 54 recadrages ROAMER faits par le carnet sur 6 annotations par fichier COCO), 12 en validation, 1 époque, 2 réseaux : toutes les sections passent (recadrage ROAMER, tirage pondéré ROAMER 10,0 % / autre 9,0 %, mosaïque, basse résolution, règles de seuils, sauvegarde, `probas_validation.csv`). Les chiffres de l'essai n'ont aucun sens (réseau non pré-entraîné).
- Non vérifié en local : la précision mixte (GPU seulement) et la lecture d'un `recadrages.csv` de `vue-de-loin` (pas encore produit).
- Test « de loin » : le carnet n'ouvre qu'une liste blanche de deux zips (`ZIPS_AUTORISES`) ; liste interdite `ZIPS_INTERDITS` (`roamer_feuilles_leaf_segmentation.zip`, Laguna) : sur Kaggle, il s'arrête si l'un d'eux est en entrée.
- **Exclusion des images communes avec le test** (même robot de Mindanao) : le carnet lit tout `exclusions_roamer*.csv` (colonne `photo`, `fichier`, `file_name`, `image` ou `nom`), compare par clé d'image (`color_frame_<hex>`, qu'on donne le nom Roboflow ou le nom d'origine) et retire toutes les feuilles d'une image listée. Obligatoire sur Kaggle (arrêt sinon). Si `vue-de-loin` fournit les recadrages, son `recadrages.csv` doit porter une colonne `photo`. [M] Vérifié en local avec une liste d'essai de 2 images (une au format Roboflow, une au format d'origine) : 9 recadrages retirés sur 4 391 (sortie de la commande, scratchpad).
- **Bunchy top écarté** [O] : `roamer_feuilles_bunchytop_leaf.zip` n'a que des polygones « positive » (2 247, aucun « negative ») ; l'étiquette désigne sans doute la plante, pas la feuille, et ces recadrages auraient fait 51 % de la part ROAMER.
