# Journal de l'orchestrateur : nuit du 8 au 9 novembre 2026 (équipe maladies)

Rien n'est commité (autorisation de Corentin : pas de commit cette nuit). Les chiffres viennent des fichiers cités, relus par l'orchestrateur.

## Décisions

| Heure | Décision | Raison |
| --- | --- | --- |
| 23 h 10 | Copie (fork) dans l'espace Roboflow de Corentin de 6 projets ROAMER au niveau feuille, versions brutes générées, exportés (`data/roboflow_maladies/nouveaux/roamer_feuilles_*.zip`) | projets sans version publiée ; seule voie d'export ; données « de loin » annotées feuille par feuille |
| 23 h 30 | Équipe de 5 agents lancée (`docs/maladies_equipe/brief.md`) | demande de Corentin |
| 23 h 45 | Test « de loin » = `roamer_feuilles_leaf_segmentation.zip`, figé par l'évaluateur ; Laguna écarté | Laguna sans étiquette saine / malade fiable (évaluateur) ; moko et fusarium déjà donnés au développement ; leaf_segmentation pas encore téléchargé, donc vu par personne |
| 23 h 50 | Prédictions de la v2 calculées sur GPU Kaggle (`affilecorentin/predictions-v2-reference`, jeu privé `affilecorentin/maladies-v2-binome` avec les poids du binôme) | processeur saturé (v2 à plus de 10 s par photo) ; contrôle : BananaLSD saines 86/90, Sigatoka 445/473, conforme à la notice du binôme ; réponses recalculées en local par l'évaluateur, 0 écart |

| vers 0 h 35 | `leaf_segmentation` abandonné comme test « de loin » | l'évaluateur montre que ses 1 228 images sont des copies exactes des quatre zips de développement (bunchytop 521 + healthy 296 + fusarium 229 + moko 182) ; Laguna contient aussi les jeux ROAMER de téléphone (black_sigatoka 142/143, bunchy_top 139/139). Le robot ROAMER a été publié plusieurs fois sous des noms différents |
| vers 0 h 35 | Contrôle des recoupements des jeux de pieds entiers `roamer2_*` (sans figer) | dernière piste de test « de loin » ; même robot et mêmes plantations que le développement : un tel test serait optimiste |

| vers 0 h 45 | **Pas de test « de loin » vierge cette nuit.** Découpage par scène de ROAMER Mindanao en `dev_loin` / `val_loin`, figé par l'évaluateur avant tout score de choix | vue-de-loin avait ouvert les jeux de pieds entiers `roamer2_*` (dont les zips de feuilles sont des sous-ensembles exacts) et les trois jeux téléphone (contenus dans Laguna). `val_loin` est une validation « même robot, mêmes plantations », donc optimiste |

| vers 1 h 00 | Découpage figé par l'évaluateur : `out/maladies/equipe/evaluateur/decoupage_loin/dev_loin.csv` (1 312) et `val_loin.csv` (1 305), SHA-256 46e4a558… et ebafc6a2… | 1 881 groupes de scène (707 copies, 36 « même scène » par ORB), aucun groupe dans les deux moitiés |

| vers 1 h 00 | **v7 lancée sur Kaggle** (protocole `docs/protocole_maladies_v7.md` écrit avant) : recette v5 + 1 090 feuilles ROAMER vues de loin (`dev_loin` seulement) + augmentations « de loin » | constat commun des agents : aucun post-traitement ne bat la v2 ; le classifieur n'a jamais appris de feuilles vues de loin (vue-de-loin : même un recadrage parfait de la feuille ne bat pas l'image entière) |
| vers 1 h 00 | Feuilles de `val_loin` recadrées sans modèle (`data/roamer_val_loin_feuilles/`, 3 014 feuilles, 1 668 malades et 1 346 saines, 604 photos) et carnet de prédiction commun v2 / v5 / v7 prêt (`affilecorentin/predictions-adoption-v5-v7`) | mesures d'adoption dès la fin des entraînements |

| vers 1 h 30 | **v5 non adoptée** (règle de la section 5 de son protocole) : fausses alertes en validation 3,0 % contre 0,7 % ; BananaLSD Sigatoka nommée 91,5 % contre 94,1 %, saines 91,1 % contre 95,6 %. La v2 reste dans la chaîne ; la v7 sera comparée à la v2 | la classe « autre maladie » ne généralise pas : inconnues de BananaLSD dites Sigatoka 88,6 % contre 68,9 % pour la v2 |

| vers 1 h 40 | **v8 lancée sur Kaggle** (protocole `docs/protocole_maladies_v8.md` écrit avant) : recette et 3 classes de la v2 + 846 feuilles ROAMER saines ou fusariose de `dev_loin` + augmentations « de loin » ; ni khadavy, ni TDTU, ni classe « autre » | isoler le levier « vue de loin », la v7 gardant les ajouts qui ont fait échouer la v5 ; règle de départage v7 / v8 écrite avant |

| vers 3 h 00 | **v7 et v8 non adoptées** (règles écrites avant) ; **la v2 reste dans la chaîne**. La v8 passe toute la non-régression (BananaLSD Sigatoka 95,1 % contre 94,1 %) mais échoue sur le gain « de loin » (feuilles malades dites malades 18,8 % contre 46,3 % ; fausses alertes 6,0 % contre 26,1 %). AUC « de loin » (indicatif) : v2 0,672, v7 0,651, v5 0,643, v8 0,600 | apprendre les feuilles ROAMER mêlées aux gros plans n'améliore pas la séparation de loin |
| vers 3 h 00 | Test banana-buddy mesuré une fois (v2, v5 ; v7, v8 en indicatif) : **première mesure de la fusariose hors de Tanzanie** (alerte de fuite du binôme vérifiée le 9 novembre : copies déjà exclues de la liste) : v2 72,9 % nommée, v8 76,6 %, v5 7,9 %, v7 5,3 % | la classe « autre maladie » absorbe la fusariose vue sous un autre style de photo |
| vers 3 h 10 | **v9 « de loin » lancée** (protocole `docs/protocole_maladies_v9_loin.md` écrit avant) : classeur saine / malade appris seulement sur les 2 985 feuilles de `dev_loin` ; réussite si AUC `val_loin` ≥ v2 + 0,05 avec borne basse > 0 | hypothèse de Corentin (deux étapes) : l'étape 2 doit être un classeur spécialisé des vues de loin |

| vers 3 h 30 | **v9 « de loin » : règle remplie** (AUC `val_loin` 0,870 contre 0,672 pour la v2, écart +0,198 [+0,171 ; +0,226]) **avec une réserve forte** : à l'intérieur d'un projet, presque pas de gain (fusarium 0,744 contre 0,720 ; Moko 0,624 contre 0,630) ; le gain vient surtout de bunchy top contre plantes saines, peut-être un raccourci de plantation | proposée comme étape 2 expérimentale d'un mode « de loin », décision à Corentin |

| vers 3 h 30 | **v9 à ne pas intégrer** : contrôle indicatif sur les photos de téléphone ROAMER (autre appareil), AUC v9 0,639 contre v2 0,629 | le gain de la v9 sur `val_loin` vient très probablement d'un raccourci propre au robot ; la vue de loin reste non résolue |

## Incidents

- La clé API Roboflow est apparue dans un message d'erreur de la bibliothèque `requests` (URL complète). Les scripts ont été corrigés. **À faire par Corentin : régénérer la clé Roboflow.**
- Norton intercepte le HTTPS : coupures fréquentes des téléchargements, gérées par reprises automatiques.

## Résultats des agents

### evaluateur (rapport vers 0 h 40 ; fichiers `out/maladies/equipe/evaluateur/bilan_{v2,b0}_{validation,bananalsd}.json`)

| Mesure | v2 | B0 |
| --- | --- | --- |
| Validation : F1 macro 3 classes | 0,960 [0,953 ; 0,966] | 0,955 [0,949 ; 0,961] |
| Validation : coût (2 × ratées + fausses alertes) | 15 | 28 |
| BananaLSD : Sigatoka nommée | 445 / 473 (0,941) | 409 / 473 (0,865) |
| BananaLSD : inconnues dites Sigatoka | 230 / 334 | 237 / 334 |

v2 − B0 (bootstrap apparié) : validation F1 +0,005 [−0,001 ; +0,010], pas de différence nette ; BananaLSD Sigatoka nommée +0,076 [+0,048 ; +0,105], net en faveur de la v2.

### vue-de-loin (message vers 1 h 15 ; fichiers `out/maladies/equipe/vue-de-loin/resultats_images.json`, `resultats_feuilles.json`)

Mesures faites sur `val_loin` une fois par méthode (échantillon de 200 images de validation, B0), critères écrits avant, tous les choix faits sur `dev_loin` :

- image entière (centre) : AUC 0,712 ; lecture en tuiles (choisie sur `dev_loin`) : 0,683 (écart IC 95 % [−0,10 ; +0,04]) → **échec** ;
- feuille recadrée selon le polygone annoté (oracle) : 0,637 contre 0,615 pour l'image entière (écart [−0,02 ; +0,07]) → **échec** du seuil +0,05 ;
- chaîne « trouver la feuille (oracle) puis la classer, 3 feuilles les plus malades » : 0,714 contre 0,710 → **échec**.
- **Lecture** : même avec des feuilles parfaitement trouvées, le classifieur actuel ne reconnaît pas les maladies vues de loin. Le problème n'est pas de trouver la feuille mais d'avoir appris des feuilles vues de loin : c'est l'objet de la v7. L'hypothèse de Corentin (deux étapes) reste candidate pour la chaîne finale, une fois le classifieur entraîné sur ces vues.
- Écart de procédure mineur : ma consigne « prévenir avant de mesurer `val_loin` » est arrivée après ces mesures ; règles respectées par ailleurs. `val_loin` sert encore pour la v7 (autre modèle, mesuré une fois, aucun réglage de la v7 dessus).

### amelioration-modele (rapport vers 0 h 50 ; fichiers `out/maladies/equipe/amelioration-modele/fusion_resultats.json`, `fusion_tableau.csv`)

Fusion apprise sur TDTU + khadavy seulement (pays non vus par la v2), critères écrits avant :

| Méthode | Validation : AUC, coût 2R+F | BananaLSD : AUC, coût |
| --- | --- | --- |
| v2 + `seuils.json` (actuelle) | 0,9998, 33 | 1,0000, 4 |
| v2 recalibrée | 0,9998, 66 | 1,0000, 8 |
| v2 + descripteurs maths | 0,9983, 560 | 0,9858, 24 |
| v2 + B0 | 0,9998, 99 | 0,9999, 13 |

- Empilement v2 + descripteurs : **échec** (AUC −0,0015 en validation, −0,014 sur BananaLSD), alors qu'il gagne sur le développement où il apprend (0,909 → 0,937). Les descripteurs gagnants (part de jaune) captent une particularité de TDTU et khadavy, pas une règle générale.
- Règle « la v2 dit saine mais un descripteur dit malade » : **échec** (fausses alertes 25 → 315 en validation).
- **Température T = 0,60 : réussite** (BananaLSD : log-perte 0,150 → 0,092, erreur de calibration 0,079 → 0,016). Ne change pas la décision ; utile pour afficher des probabilités fiables.
- La v2 nomme mal les maladies inconnues : Sigatoka jaune 27/27 en fusariose, flétrissement bactérien de TDTU 394/655 en fusariose, Cordana et Pestalotiopsis surtout en cercosporiose. C'est la justification de la classe « autre maladie » (v5, v7).
- **Conclusion de l'équipe** : garder la v2 et `seuils.json`, ne pas fusionner, réserver les descripteurs à l'explication d'une réponse.
- Brouillon de carnet v7 testé en local (recadrages ROAMER fusarium et moko, augmentations « de loin »).

### math-couleur (rapport vers 0 h 45 ; fichiers `out/maladies/equipe/math-couleur/bilan_validation.json`, `transfert_dev.csv`)

- Maths seules, validation : F1 macro 0,759 contre 0,960 pour la v2 (−0,20 [−0,22 ; −0,18]).
- En gros plan dans des pays nouveaux pour la v2, les indices nomment mieux la Sigatoka : khadavy Bercak-Hitam 49 % contre 28 % pour la v2 avec ses seuils ; TDTU 67 % contre 30 %. Mais ils classent moins bien les saines (TDTU 68 % contre 85 %).
- Règle de renommage F1 (« fusariose » de la v2 → Sigatoka si les maths préfèrent la Sigatoka), figée avant : **échec sur la validation**, fusariose nommée 88,6 % → 53,5 %. Rejetée.
- Cause principale des échecs : la sensibilité à l'échelle et au cadrage (gros plans de 768 px, photos de 4 624 px avec fond, images de 224 px).
- Recommandation : aucune règle mathématique ne modifie la réponse de la v2 ; descripteurs gardés comme entrées de la fusion apprise.

### math-forme (rapport vers 0 h 25 ; fichiers relus : `out/maladies/equipe/math-forme/mesure_*.json`, verrous de mesure unique présents)

- Sur la validation tanzanienne, les descripteurs explicites restent loin des réseaux : F1 macro forme + couleur 0,713, contre 0,960 pour la v2.
- Hors domaine (BananaLSD), la forme tient mieux que la couleur : exactitude équilibrée 0,564 contre 0,403. Les réseaux restent bien au-dessus (v2 0,948).
- Descripteur robuste et explicable : cohérence locale des nervures (la maladie casse la texture régulière), stable dans les quatre pays.
- Orientation « stries parallèles aux nervures » réfutée comme critère de maladie.
- Fusion v2 + géométrie : pas de gain propre ; le gain sur BananaLSD (+0,031) vient de la **recalibration** de la v2 sur des pays non vus (+0,037), pas de la forme.
