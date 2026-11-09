# Fiche `math-couleur` : indices explicites de couleur et de texture

Question : des indices explicites de couleur et de texture, sans apprentissage profond, reconnaissent-ils les maladies mieux ou plus robustement que l'IA, surtout hors du pays d'apprentissage, et que peuvent-ils apporter en complément de la v2 ?

Dossier de travail : `out/maladies/equipe/math-couleur/`. Lancement : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/maladies/equipe/math-couleur/<script>.py`.

## 0. Observations de départ

- [O] Mosaïque de 4 images par jeu et classe (dans le bloc-notes de session, non conservée) : Tanzanie 2021 = gros plans 768 px, Sigatoka avancée (nécroses brunes, halos jaunes) ; fusariose = feuilles jaunies, stries jaunes, tissu brun sec ; Pérou = gros plans 3072 px ; Tanzanie 2022 = photos 4624 × 3468, plus de fond ; BananaLSD = 224 px ; khadavy = photos de terrain 640 × 640 avec sol et herbe, Bercak-Hitam = petites taches sombres éparses, Bercak-Kuning = feuilles entières jaunies et bords secs ; **TDTU saine = feuilles détourées sur fond blanc** (artefact de jeu : un descripteur de fond trahirait la classe).
- [O] Prédictions de la v2 sur khadavy déjà disponibles : `out/maladies/test_khadavy/reponses_v2_convnext.csv` (test du 8 novembre, consulté, il ne départage plus rien).

## 1. Descripteurs (version figée D1)

Script : `descripteurs.py` (fonction `decrire(chemin)`), image réduite à 384 px de grand côté.
(détails remplis ci-dessous au fil du travail)

Contenu de D1 (environ 85 descripteurs, une ligne par image) :
- **masque de feuille** : cœur = pixels verts (teinte OpenCV 33-100, S > 0,10) ou jaunes (14-33, S > 0,30, V > 0,35), fermeture morphologique 11 px, trous bouchés, plus les pixels bruns, noirs ou pâles à moins de 4 px du cœur, moins fond blanc (S < 0,10, V > 0,85) et ciel ; composantes ≥ 1 % de l'image. [O] Contrôle visuel sur 32 images : correct sur gros plans verts ; **perd les grandes nécroses détachées du vert** (fusariose sèche) et **garde l'herbe** (khadavy) ; d'où un second jeu de fractions `fi_*` calculé sur toute l'image hors fond blanc et ciel ;
- **couleur** (`f_*` dans la feuille, `fi_*` dans l'image) : vert, jaune (chlorose), brun, noir (nécrose), pâle (paille) ; Lab (moyennes, centiles de a* et b*) ; ExG, VARI, GLI, NGRDI (moyenne, centiles bas, part NGRDI < 0) ; teinte moyenne circulaire et dispersion ;
- **taches sombres** : différence de gaussiennes (σ = 1,5 ; 3 ; 6 px, rapport 1,6) sur L*, maxima locaux de contraste > 3 (et > 6, « fortes ») dans la feuille érodée, densité pour 10 000 px de feuille ; « taches sur vert » = entourage à plus de 60 % vert ; résidu sombre contre la médiane locale 21 px (> 10 unités L*), composantes par taille (≤ 20 px, 20-200, > 200), halo jaune ou brun autour des taches ;
- **texture** : cooccurrence (16 niveaux, distance 2, horizontale et verticale : contraste, homogénéité, énergie, entropie, corrélation, anisotropie), LBP uniforme 8 voisins rayon 2 (10 cases + entropie), énergie de Gabor (λ = 6 et 12 px, 4 orientations, moyenne et anisotropie), écart-type local 7 × 7 de L* et de a*.
- Temps : environ 0,46 s par image sur un cœur (décodage JPEG réduit compris), 8 processus en parallèle.

## 2. Expériences sur le développement (réglages libres)

Jeux : **liste de développement de l'évaluateur** reproduite par `listes_evaluateur.py` → `liste_eval_dev.csv` = Tanzanie 2021 et Pérou 300 par classe (graine 2026, images `retenue`), TDTU entier (1 636, dont 655 « autre maladie »), khadavy entier (431) ; 3 567 images. Descripteurs : `cache_descripteurs.csv` (une ligne par chemin). Note : un premier calcul à 8 processus sur une liste à moi (`liste_dev.csv`) a été arrêté à la demande de l'orchestrateur (processeur saturé) ; désormais **un seul processus**, OpenCV à 2 fils, `extraire.py` écrit le cache au fil de l'eau.

**MC-1 (avant calcul)** — [H] certains descripteurs séparent malade et saine **dans le même sens sur les quatre jeux** (deux pays d'apprentissage de la v2, deux pays nouveaux). Mesure : AUC univariée malade contre saine par jeu. Réussite : au moins un descripteur avec AUC orientée ≥ 0,75 sur les quatre jeux ; et sur khadavy Bercak-Hitam contre Sehat, au moins un descripteur de taches ≥ 0,75.

**MC-2 (avant calcul)** — [H] un classifieur léger sur D1 appris sur Tanzanie 2021 + Pérou (les données de la v2) transfère mieux que la v2 à khadavy. Méthodes : régression logistique multinomiale (λ = 1 et 30) et arbre (profondeur 2 et 3), sur tous les descripteurs ou sur un jeu compact de 18 descripteurs couleur + taches fixé avant calcul. Référence v2 sur khadavy (test du 8 novembre, sans « je ne sais pas » pour nous) : Bercak-Hitam nommées Sigatoka 28,2 %, saines bien classées 94,3 %, F1 macro saine/BS 0,623. Réussite : Bercak-Hitam nommées Sigatoka ≥ 40 % **et** saines bien classées ≥ 85 %.

**MC-3 (avant calcul)** — même chose en laissant un jeu dehors (apprentissage sur les trois autres). Lecture seulement, pour choisir la recette à figer avant la validation.

**MC-4 (avant calcul)** — [H] les descripteurs ajoutent à la v2 une information utile hors domaine pour **détecter la maladie** (malade contre saine). Méthode : régression logistique (λ = 1) sur [logit p_saine et logit p_BS de la v2] seuls, ou + 18 descripteurs compacts, ou descripteurs seuls ; apprise sur TDTU, mesurée sur khadavy, et l'inverse (deux pays nouveaux pour la v2). Probabilités de la v2 : `out/maladies/equipe/evaluateur/predictions_v2_dev.csv`. Mesures : AUC malade/saine ; parts de saines bien classées et de malades ratées au seuil qui garde 94 % des saines du jeu d'apprentissage. Réussite : v2 + compact dépasse v2 seule d'au moins 0,03 d'AUC **dans les deux sens**. (Les « autres maladies » comptent comme malades. Limite : TDTU saine est sur fond blanc ; les descripteurs compacts n'incluent pas `f_fond_blanc`, mais le masque de feuille reste plus propre sur ces images.)

### Résultats sur le développement (9 novembre 2026)

Commandes : `extraire.py cache_descripteurs.csv liste_eval_dev.csv` (3 567 images, 0 erreur, 0,94 s/image sur processeur partagé) ; `analyse_dev.py cache_descripteurs.csv liste_eval_dev.csv` → `auc_par_jeu.csv`, `transfert_dev.csv`, `transfert_dev.txt`, `fusion_dev.csv` ; `fusion_regles.py` → `fusion_regles_dev.csv`, `predictions_mc_dev_hors_pli.csv`. Référence v2 = `evaluateur/predictions_v2_dev.csv`, mêmes images.

**MC-1 [M] : réussi, de justesse.** Meilleur descripteur sur les quatre jeux : fraction jaune de la feuille `f_jaune`, AUC malade/saine 0,967 (Tanzanie 2021), 0,974 (Pérou), 0,878 (TDTU), 0,761 (khadavy) ; puis `contr_local_a_moy` (variation locale de a*, 0,75 à 0,93) et `f_non_vert`. Sur khadavy Bercak-Hitam contre Sehat, le meilleur descripteur de taches est `comp_petites_dens` (densité de petites taches sombres ≤ 20 px) : **AUC 0,803** (≥ 0,75), mais seulement 0,62 sur TDTU. Les AUC tombent de 0,97 (pays d'apprentissage) à 0,74-0,88 (pays nouveaux) : **les couleurs se transportent mieux qu'un réseau ne le ferait seul, mais pas sans perte**.

**MC-2 [M] : réussi selon le critère écrit, mais pas meilleur que la v2 au total.** Logistique λ = 1 sur tous les descripteurs, apprise sur Tanzanie 2021 + Pérou : khadavy Bercak-Hitam nommées Sigatoka **49,4 %** (v2 : 38,4 % en argmax, 28,2 % avec ses seuils), saines bien classées 90,6 % (≥ 85 %). Mais 46,5 % des Bercak-Hitam sont dites saines (v2 : 36 %) et l'AUC malade/saine est 0,868 (v2 : 0,922). F1 macro saine/BS 0,664 contre 0,666 pour la v2 en argmax. Sur TDTU : Sigatoka nommée 64-67 % (v2 : 30 %), mais saines bien classées 64-68 % (v2 : 85 %). Les arbres (profondeur 2-3) transfèrent mal (AUC 0,66-0,80).

**MC-3 [M] (lecture)** : en laissant un jeu dehors, la logistique λ = 30 sur tous les descripteurs est la plus stable (khadavy : Sigatoka nommée 62 %, saines 87 %, AUC 0,88 ; TDTU : 72 %, 61 %, 0,85). Ajouter des pays différents à l'apprentissage aide (khadavy passe de 0,835 à 0,880 d'AUC quand TDTU est ajouté).

**MC-4 [M] : échec.** Fusion binaire malade/saine v2 + descripteurs : appris sur TDTU, testé sur khadavy, AUC 0,927 → 0,887 (pire) ; appris sur khadavy, testé sur TDTU, 0,856 → 0,877 (mieux), et la v2 brute fait 0,907. **Les descripteurs n'aident pas la v2 à décider « malade ou non »** hors domaine. Les descripteurs seuls font 0,61-0,71 d'AUC dans ce montage (appris sur un seul pays).

**MC-5 [M] (règles de fusion, maths hors pli)** — F1 « renommage » : une fusariose de la v2 devient Sigatoka si le modèle maths préfère BS à fusarium ; F2 « alerte » : une « saine » de la v2 devient malade si p_malade maths > 0,954 (seuil laissant passer 5 % des saines, hors pli).
- F1 : Sigatoka nommée khadavy **28,2 % → 39,2 %**, TDTU **21,0 % → 52,5 %** ; nom juste quand nommé 0,68 → 0,95 (khadavy), 0,37 → 0,93 (TDTU). Malades ratées et fausses alertes inchangées (la règle ne touche que le nom).
- **Risque non mesurable en développement** : la fusariose n'existe qu'en Tanzanie 2021 ; hors pli, le modèle maths ne l'a jamais vue et F1 détruit toute la fusariose (Tanzanie 2021 : fusariose nommée 100 % → 0 %). Ce risque sera mesuré sur la validation (1 001 fusarioses), où le modèle maths aura vu la fusariose de 2021.
- F2 : malades ratées 22,8 → 20,2 % (khadavy), 10,5 → 6,2 % (TDTU), mais fausses alertes 3,8 → 4,4 % et 10,2 → 19,4 %. **Abandonnée** (coût par image à peine meilleur, fausses alertes doublées sur TDTU).
- Le modèle maths seul : nom juste quand nommé 0,92-0,98 sur les pays nouveaux, mais trop de fausses alertes (13 % khadavy, 45 % TDTU) : **pas utilisable seul**.

## 3. Mesures sur la validation et BananaLSD (écrites avant tout calcul sur ces jeux)

Je n'ai lu ni les bilans de la v2 ou du B0 sur ces jeux, ni mes descripteurs sur ces jeux, avant d'écrire cette section.

**Méthode figée (M-D1)** : descripteurs D1 (`descripteurs.py` tel quel) ; régression logistique multinomiale λ = 30 (`outils.Logistique`), log1p + centrage-réduction (`outils.Prepa`), sur **tous les descripteurs sauf `f_fond_blanc` et `f_feuille`** ; apprise une fois sur tout le développement de l'évaluateur, classes connues (Tanzanie 2021 300 × 3, Pérou 300 × 2, TDTU BS + saine, khadavy BS + saine ; 2 885 images), classes équilibrées par poids. Réponse maths = argmax, sans abstention. Script : `appliquer.py` (apprend, enregistre `modele_maths_D1.npz`, écrit les fichiers). **Règle F1** (seule règle retenue) : réponse = celle de la v2, sauf si la v2 dit « fusariose » et que p_BS maths > p_fusarium maths, alors « cercosporiose noire ». Probabilités de F1 = celles de la v2. Mesures : `eval_commun.py` de l'évaluateur, bootstrap apparié contre `predictions_v2_*`.

**V-1 (validation, maths seules)** — [H] le modèle maths seul est moins bon que la v2 en Tanzanie 2022 (pays d'apprentissage de la v2). Mesure : F1 macro 3 classes, différence appariée maths − v2. « Réussite » des maths : différence ≥ − 0,02. Attendu : échec.

**V-2 (validation, v2 + F1 : innocuité)** — [H] le renommage ne détruit pas la fusariose quand le modèle maths l'a apprise. Mesures : fusariose nommée (1 001 images) et F1 macro 3 classes, v2 + F1 contre v2. Réussite : fusariose nommée en baisse de **3 points au plus**, et différence de F1 macro ≥ − 0,01. Sinon F1 est rejetée.

**V-3 (BananaLSD, v2 + F1 : effet hors domaine)** — [H] le renommage augmente la Sigatoka nommée au Bangladesh. Mesures : Sigatoka nommée (473), inconnues dites fusariose, coût par image. Réussite : Sigatoka nommée en hausse d'au moins 1 point, sans hausse des inconnues dites fusariose. (Jeu déjà consulté ; la v2 y est déjà forte, la marge peut être nulle : un résultat nul n'est pas un échec de V-2.)

**V-4 (BananaLSD, maths seules)** — lecture seulement (images 224 px, changement d'échelle des taches) : Sigatoka nommée, saines bien classées, AUC malade.

Recommandation écrite d'avance : F1 est proposée à l'orchestrateur **si V-2 réussit** et si V-3 ne recule pas (Sigatoka nommée ≥ v2 − 1 point) ; le bénéfice attendu est celui mesuré sur khadavy et TDTU (MC-5).

### Résultats (mesure unique, 9 novembre 2026)

Commandes : `extraire.py cache_descripteurs.csv liste_eval_validation.csv liste_eval_bananalsd.csv` (3 898 images, 0 erreur) puis `appliquer.py` (un seul passage) → `bilan_validation.json`, `predictions_mc_{validation,bananalsd}.csv`, `predictions_v2F1_{validation,bananalsd}.csv`, `modele_maths_D1.npz`. Comparaisons : `eval_commun.comparer`, bootstrap apparié 10 000 tirages, graine 2026. Rien n'a été changé après.

| Mesure | v2 | maths seules (M-D1) | v2 + F1 |
| --- | --- | --- | --- |
| Validation, F1 macro 3 classes | 0,960 | 0,759 (diff. − 0,201 [− 0,217 ; − 0,185]) | 0,832 (− 0,128 [− 0,140 ; − 0,116]) |
| Validation, Sigatoka nommée | 96,1 % | 84,0 % | 96,4 % |
| Validation, fusariose nommée | 88,6 % | 59,0 % | **53,5 %** (− 35,2 points [− 38,1 ; − 32,2]) |
| Validation, saines bien classées / malades dites saines | 97,5 % / 0,2 % | 84,8 % / 5,6 % | inchangé |
| Validation, AUC p_malade | 0,9998 | 0,968 | 0,9998 |
| BananaLSD, Sigatoka nommée (473) | 94,1 % | 34,3 % | 94,7 % (+ 0,6 point [0 ; + 1,5]) |
| BananaLSD, saines bien classées (90) | 95,6 % | 58,9 % | 95,6 % |
| BananaLSD, inconnues dites fusariose / Sigatoka | 10,5 % / 68,9 % | 12,0 % / 75,8 % | 1,5 % / **77,8 %** |
| BananaLSD, AUC p_malade | 1,000 | 0,817 | 1,000 |

- **V-1 [M] : échec (attendu).** Les maths seules perdent 0,20 de F1 macro contre la v2 en Tanzanie 2022.
- **V-2 [M] : échec, F1 rejetée.** Le renommage fait perdre 35 points de fusariose nommée (seuil : 3). Le modèle maths, appris sur la fusariose 2021 (gros plans 768 px), ne la reconnaît pas sur les photos 2022 (4 624 px, plus de fond) : il préfère BS pour 40 % des fusarioses que la v2 nommait bien.
- **V-3 [M] : échec.** Sigatoka nommée + 0,6 point au Bangladesh (seuil : + 1) ; les inconnues passent de « fusariose » à « Sigatoka » (+ 9 points), ce qui n'est pas mieux.
- **V-4 [M] (lecture)** : maths seules très faibles sur BananaLSD (images 224 px : les taches et textures changent d'échelle), 41 % de fausses alertes.

## 4. Conclusion

- Les indices explicites **ne reconnaissent pas mieux que la v2**, ni dans son pays (validation) ni au Bangladesh. Ils sont **plus robustes pour nommer la Sigatoka aux pays nouveaux en gros plan** (khadavy, TDTU : MC-2, MC-5), mais cette robustesse ne tient pas d'un appareil photo ou d'un cadrage à l'autre (Tanzanie 2022, BananaLSD 224 px) et ils confondent fusariose et Sigatoka dès que le cadrage change.
- Les descripteurs les plus stables entre pays sont simples : **fraction jaune (chlorose)**, fraction non verte, variation locale de a*, NGRDI ; et pour les taches précoces, **la densité de petites taches sombres** (AUC 0,80 sur khadavy Bercak-Hitam). Ils n'aident pas la v2 à décider « malade ou non » (MC-4).
- Recette proposée : **aucune règle maths ne doit modifier la réponse de la v2** dans la chaîne. Les descripteurs (`descripteurs_*.csv`) restent disponibles comme entrées de la fusion apprise d'`amelioration-modele`, avec la mise en garde que leur gain hors domaine n'a pas été démontré, et sous réserve d'une normalisation d'échelle (calcul sur la feuille recadrée à résolution physique comparable) avant tout nouvel essai.

## 5. Livrables pour la fusion

`out/maladies/equipe/math-couleur/descripteurs_{dev,validation,bananalsd}.csv` : une ligne par image, mêmes `chemin` que `evaluateur/predictions_v2_*.csv` (3 567, 3 001, 897 lignes). Colonnes : les descripteurs D1 (dont `f_fond_blanc` et `f_feuille`, artefacts à exclure : fond blanc des saines de TDTU), puis `mc_p_saine`, `mc_p_black_sigatoka`, `mc_p_fusarium`, `mc_reponse` du modèle maths. `mc_proba_hors_pli` = 1 sur le développement (probabilités laisser-un-pays-dehors ; la fusariose de Tanzanie 2021 n'y est jamais vue, donc ses p_fusarium sont sans valeur), 0 sur validation et BananaLSD (modèle appris sur tout le développement). Le fichier dev porte en plus `repli_masque`.
