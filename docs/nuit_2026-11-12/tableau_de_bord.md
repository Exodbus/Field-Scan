# Tableau de bord de la nuit du 12 au 13 novembre 2026

Tenu par le chef d'orchestre. Plan : `docs/plan_nuit_10h.md` ; règles : `docs/plan_nuit_2026-11-12.md` (SHA-256 7b19e221…).

## Cycle 1 (lancé vers 23 h)

| Agent | État | Journal |
| --- | --- | --- |
| D-comptage | relancé : découpage v6, jeu Kaggle comptage-v6-5cm | journal_c_decoupage.md |
| D-maladies | relancé : jeux de feuilles neufs, jeu Kaggle feuilles-nuit-1112 | journal_m_prospection.md |
| C-banc | relancé : essais comptage 1 à 10 sans entraînement | journal_c_banc.md |
| M-banc | relancé : essais maladies 5 à 9 (1 à 4 faits, 343 essais) | journal_m_banc.md |
| M-entraîneur | relancé : plis v12a, v12b, v12c sur Kaggle | journal_m_entrainement.md |
| C-analyste | lancé : analyse des erreurs du v5 sur le réglage | journal_c_analyste.md |

23 h 35 : D-comptage fini (btd_train 186 tuiles / 18 850 plants, btd_val 178 / 17 264, tampon 16, 16 tuiles aux annotations fausses exclues ; jeu Kaggle comptage-v6-5cm prêt ; aucune fuite confirmée). C-entraîneur lancé à 22 h 55 (v6a, v6b, v6c). C-prospection relancé à 23 h 35.

23 h 40 : D-maladies fini. Test vierge maladies = AgroVisionBD (Figshare 10.6084/m9.figshare.34005402, Bangladesh, Patuakhali ; 1 082 photos : 366 saines, 716 malades), choisi sur les effectifs, seul candidat valide ; source et région neuves, pas le pays (la v10b a appris BananaLSD). Jeu Kaggle feuilles-nuit-1112 (1 405 photos, Bangladesh, apport modeste). Écartés : ffbb33cj4y (compilation de nos jeux), ScholarSphere tzzb-zd65 (bunchy top, Xanthomonas : NC et anti-robot, à télécharger par Corentin s'il veut). M-analyste lancé.

00 h 10 : C-analyste, cycle 1 fini (`out/comptage/analyse/rapport_cycle1.md`). Le recul du v5 sur les plants espacés vient de l'a priori de taille appris (6,4 % de boîtes < 40 px dans son apprentissage, 87 % dans btd_val) ; agrandir l'image fait pire. Recommandations transmises : tirage équilibré par taille pour v6a, pas de GPU sur 3,5 cm ni sur la demi-résolution ; aiguillage par le 90e centile des scores pour C-banc. **Décision** : les 61 doublons d'annotation du plantain restent dans la référence (règle écrite avant) ; chiffres sans doublons pour information seulement.

00 h 15 : C-prospection fini. **Test vierge comptage = `banana_trees_kp`** (Roboflow test-purpose/banana-trees-cpzur, CC BY 4.0 ; 157 photos, 22 652 bananiers, dense, environ 11 cm/px, ramenées à 5 cm). Entraînement : dmpcs2_objets (1 415 bananiers), geostar_tree (2 025). banano_finca (juge du binôme, déjà lu) : information seulement. **Décision sur le critère d'échelle** : `plantain_m2` (24 885 plants, mais 20 à 35 cm/px, plants de 8 px) est écarté du test vierge. Le critère « 12 cm/px au plus » a été fixé après avoir vu les échelles mais avant toute prédiction ; je le valide : à ces échelles, le détecteur à 5 cm demanderait un agrandissement de 4 à 7 fois, hors du domaine que le bulletin annonce comme fiable. Limite à écrire : le test vierge ne couvre que le dense.

00 h 50 : M-analyste fini (`out/maladies/analyse/rapport_cycle2.md`). Constats : les malades encore ratées sont peu tachées (Sigatoka jaune de PSFD, Xanthomonas d'Éthiopie) et aucun seuil ne les rattrape ; PSFD est un jeu augmenté (738 photos, 188 groupes, 123 copies tournées à 45° sur fond noir, la moitié des ratées de F1) ; les v12 apprennent le raccourci « source = malade » (P(malade) médiane des saines TDTU 0,94 contre 0,18 pour la v10b) ; le gain des morceaux 2 × 2 vient d'un déplacement des probabilités, pas d'une meilleure séparation. Transmis : tirage 50/50 par source sans PSFD, augmentation basse résolution (M-entraîneur) ; v10b en 224 px, pas de 3 × 3 (M-banc). **Décision** : règle 4.4 inchangée, PSFD compté avec ses copies ; « PSFD sans copies » pour information.

00 h 55 : M-banc fini (1 215 essais). **Correction** : le coût de référence de la chaîne installée sur le réglage est **49,23** (45,4 était un candidat, écrit par erreur dans le plan de 10 h). Finalistes (`out/maladies/nuit_1112/banc/finalistes.md`) : F1 = à trois + morceaux 2 × 2 (35,96 ; validation 0 ratée, 62 fausses alertes ; environ 10 s par photo) ; F2 = à trois + 384/512 px (36,48 ; 6 s) ; F3 = à trois seul (37,83 ; 2 ratées, 57 fausses ; 3,2 s) ; réserve : v10b + soupe (39,24). Prix commun : fausses alertes TDTU 177 → 232 à 241. Pistes fermées : seuils seuls, températures, 3 × 3, 224 px, seuil de nom, mélanges avec les v12 actuelles.

01 h 00 : C-entraîneur, lot 1 fini. Moyenne des 5 F1 : v6a 0,873 (seuil 0,35), v6b 0,869, v6c 0,869, contre 0,792 pour le v5 (seuil 0,20 choisi par la règle 3.4). Les trois passent la règle « finaliste », mais tout le gain vient de btd_val (0,988 : même orthomosaïque que btd_train) ; sur les 4 anciennes validations, v6a fait 0,844 contre 0,853 pour le v5 à 0,30. Réserve forte à suivre par le Contrôleur et le Juge. **Arbitrage GPU** : une place Kaggle chacun pour M-entraîneur et C-entraîneur.

## Cycles 2 et 3 (1 h à 4 h)

01 h 35 : C-banc, essai 10 (mélanges avec les v6), 244 variantes. Finalistes : E10_p90_v6b_v5_d0.1 (0,8786), E5p90b_moy34_v5_d0.1 (0,8549), E7_union_v5+v3 (0,8352) ; E3 sort. Hors btd_val, personne ne bat le v5 en service (moyenne des 4 autres jeux : v5 à 0,30 0,854). Veille automatique des nouveaux ONNX jusqu'à 4 h 30.

02 h 55 à 03 h 20 : M-entraîneur (44 essais). Liste : v12a13 (coût 41,50, seuils de la v10b, aucun seuil réglé ; Éthiopie 179 → 141 ratées, PSFD 149 → 114), v12a14 (42,28), v12a4 (47,89). Modèles finaux de a13 et a14 rangés : validation 7 ; 60 et 9 ; 48. Bruit d'une graine à l'autre ≈ 1 point de coût. Lot 6 (a17 à a20) en cours.

03 h 22 : Contrôleur, version 7 de `out/controle_nuit_1112/verdicts.md`. Tous les finalistes sont ADMIS AVEC RÉSERVE ; chiffres recalculés à l'identique, aucune fuite. Réserves principales :
- maladies F1 à F3 : optimisme de la recherche ≈ 2,7 points sur 13,6, gain disparu Tanzanie laissée dehors, fausses alertes TDTU +64 ;
- a13 : choix parmi 44 recettes, Bangladesh appris (comme le test vierge) ;
- comptage : tout le gain vient de btd_val, nul sur banano_finca, aucun juge ne peut le confirmer.

03 h 55 : C-entraîneur, lot 2 fini. v6a graines 0 / 1 / 2 : 0,873 / 0,871 / 0,866 ; v6d 0,869 ; v6e 0,868. Tout est dans le bruit des graines ; aucun ne regagne MM ni le dense du v5. Soupe des poids des 3 graines : échec (F1 0). Lot 3 (ResNet-34, deux têtes, réglage fin du v5 et interpolations, distillation) vers 5 h 40.

03 h 56 : **règle de gel des finalistes** écrite avant toute lecture des juges : `regle_gel_finalistes.md` (SHA-256 73017722…). Trois places par module, par familles : la meilleure de toutes, puis la meilleure d'une autre famille, puis d'une troisième. Motif : les trois meilleurs des maladies sont la même famille, au même prix en fausses alertes.

04 h 00 :
- M-banc relancé sur l'essai 9 (mélanges contenant un v12, famille C), avant 5 h 45 ;
- C-analyste relancé sur la robustesse de l'aiguillage p90 à l'échelle (réglage dégradé à 8, 11 et 14 cm/px), avant 5 h 45 ;
- Contrôleur informé de la règle ; il gèle la liste à 7 h.

En attente : Juge (cycle 5, après 7 h).

## Meilleurs candidats (réglage seulement)

| Module | Candidat | Réglage | Référence |
| --- | --- | --- | --- |
| Maladies (0 h 10) | M-banc F1 : mélange à trois (v10b, soupe, v2) + lecture en morceaux 2 × 2, seuil 0,70 | coût 35,96 | v10b : coût 49,23 ; 9 et 57 |
| Maladies, entraîné (3 h 20) | v12a13 : v10b réentraînée, tirage par source sans PSFD, + Bangladesh neuf, seuils de la v10b | coût 41,50 ; validation (modèle final) 7 ; 60 | v10b : coût 49,23 ; 9 ; 57 |
| Comptage, mélange avec v6 (1 h 35) | E10 : aiguillage p90, petits = v6b, grands = v5 | 0,8786 (hors btd : identique au v5) | v5 à 0,30 : 0,778 |
| Comptage (23 h 53) | C-banc : aiguillage par taille des pics, petits = moyenne v3 + v4, grands = v5 | moyenne des 5 F1 0,855 (btd 0,868), après 177 variantes | v5 : 0,778 sur les 5 jeux (btd 0,473) |

04 h 10 : M-entraîneur fini (47 essais), rapport vérifié contre son journal et `out/maladies/nuit_1112/kaggle/finalistes.md`.
- Finalistes (famille B) : v12a13, v12a14, v12a4. Le lot 6 (a17 à a20, 41,25 à 43,11) ne bat pas a13 de plus d'un point : liste inchangée.
- Quota GPU Kaggle restant, tous agents : 4,68 h. Sa place est rendue à C-entraîneur.
- Incident relu : un premier envoi du carnet DINOv3 lisait la Cordana du Pérou. L'envoi a été refusé avant de tourner, et le carnet corrigé contient un `assert` qui l'interdit. Aucune lecture de juge, et v12c est fermé de toute façon.
- Correctif prêt, non appliqué : `maladies.modele: modeles/maladies_v12_essais/v12a13` dans `config.yaml`.

04 h 06 : M-banc, essai 9 fini : mélanges contenant un v12, 518 essais, soit 1 733 pour M-banc sur la nuit.
- Meilleur candidat de la famille C : **C_quatre_v12a14**, mélange géométrique v10b + soupe + v2 + v12a14, seuil 0,76.
- Coût de réglage **36,07**.
- Sur la validation : 2 malades ratées et 68 fausses alertes ; le modèle final relu donne 3 et 69.
- TDTU : 260 saines sur 577 en alerte, contre 177 pour la chaîne installée.
- Temps : environ 5 s par photo.
- Mélange avec a19 (34,73) non retenu : a19 n'a pas de modèle final. **Décision : on n'entraîne pas a19.** Son gain de 1,3 point arrive après 256 essais de plus, ce qui reste dans le bruit d'une graine (environ 1 point), et le quota GPU restant (4,7 h) va au comptage.
- Projection de la liste gelée maladies, selon la règle de 3 h 56, sous réserve du Contrôleur :
  - famille A : F1 (35,96) ;
  - famille C : C_quatre_v12a14 (36,07) ;
  - famille B : v12a13 (41,50).

04 h 22 : C-analyste, cycle 3 fini (`out/comptage/analyse/rapport_cycle3_echelle.md`). Simulation de résolution sur le réglage seulement : images dégradées comme celles du test vierge, puis remises à 5 cm.
- Règle écrite à 4 h 02, avant la mesure. Le risque est **confirmé sur l'aiguillage** : à 11 cm/px, 39 % des images denses partent vers la branche « petits » (85 % à 14 cm).
- **Pas de perte de F1** : pire écart −0,010. L'aiguillage prend le flou pour de petits plants, mais il compense un v5 qui sous-détecte. Sur le dense à 11 cm : E10 0,673, E5p90b 0,632, v5 0,622.
- **Risque principal : la chute du v5 lui-même** (dense 0,779 à 5 cm, 0,622 à 11 cm, 0,479 à 14 cm ; 55 % des pieds trouvés à 11 cm). Limite à écrire dans le bulletin : sous-comptage d'environ 45 % sur des images d'origine à 11 cm/px.
- Consigne pour le Juge : sur le test vierge, donner aussi la part d'images aiguillées.
- Piste pour plus tard, hors de cette nuit : un aiguillage insensible au flou (espacement des pics en mètres, résolution d'origine).

C-banc a fini sa file (324 variantes au total ; rapport vérifié contre `out/comptage_v6/banc/finalistes.md`).
- Le finaliste 1 devient **E10_moy_v6e+v5** : moyenne des cartes v6e et v5, seuil 0,30. Réglage 0,882, moyenne sans btd 0,855 (v5 à 0,30 : 0,854), erreur de compte 0,153. Il remplace E10_p90_v6b, qui sort de la liste. C'est un nouveau candidat, envoyé au Contrôleur.
- Finalistes 2 et 3 inchangés : E5p90b (0,855) et E7 (0,835).
- Essais fermés : compte par intégrale (erreur de compte 0,43 à 0,60), seuil relatif, échelles, symétries (+0,002 dans l'aiguillage pour 8 fois le calcul).
- Soupe des poids v6a cassée : aucune détection.

## Cycles 4 et 5 (4 h 30 à 9 h)

04 h 10 à 04 h 27 : le Contrôleur admet, avec réserve, C_quatre_v12a14 et E10_moy_v6e+v5.
- C_quatre_v12a14 : optimisme du choix d'environ 4 points ; contre F3, l'écart est de −1,78 (é.-t. 0,90).
- E10_moy_v6e+v5 : aucun finaliste sans btd ; banano_finca 0,751 contre 0,754.

05 h 34 à 06 h 50 : C-entraîneur a fini (17 essais, environ 6,8 h de GPU). Finalistes v6 seuls, tous dans le bruit des graines et sans gain hors btd :
- v6f (ResNet-34, graine 0), 0,877 ; la graine 1 échoue sur MM, et la moyenne des 3 graines (0,869) égale celle du v6a ;
- v6a ;
- v6d.

Pistes fermées : la soupe des poids, le réglage fin du v5 sur l'espacée (oubli de MM), la distillation, l'apprentissage à deux têtes. Le Contrôleur admet v6f avec réserve (« graine chanceuse ») ; v6a et v6d échouent en lecture stricte sur MM.

06 h 42 : admissions closes. Empreintes des fichiers utiles au Juge : `out/controle_nuit_1112/empreintes_liste_gelee.txt`. Liste attendue selon la règle de gel :
- maladies : F1 (A), C_quatre_v12a14 (C), v12a13 (B) ;
- comptage : E10_moy_v6e+v5 (C), v6f (B), E5p90b (A).

06 h 50 : **deux Juges lancés**, maladies et comptage, en parallèle et sur 4 fils chacun. Chacun attend la liste gelée du Contrôleur (7 h), lit les juges une fois par finaliste et applique 3.4 ou 4.4. Le test vierge n'est lu **que si un finaliste est adopté** ; sinon il reste vierge. Le partage en deux agents ne change pas le protocole et laisse tenir les calculs avant 8 h 30.

07 h 01 : **liste gelée** écrite par le Contrôleur en tête de `verdicts.md` (version 12) ; la règle et le plan sont revérifiés par leur SHA-256.
- Maladies : F1_trois_morceaux2x2 (35,96), C_quatre_v12a14 (36,07), v12a13 (41,50).
- Comptage : E10_moy_v6e+v5 (0,8822), v6f graine 0 (0,8780), E5p90b (0,8549).

Aucun refus et aucune fuite. Optimisme estimé :
- F1 : environ 2,7 points ;
- C_quatre_v12a14 : environ 4,1 points ; son avance sur F3 est à la limite du bruit ;
- v12a13 : environ 1 point ;
- comptage : gain nul hors btd_val.

Les chiffres ONNX font référence pour les v6.

09 h 05 : Juge maladies fini. **F1 passe la règle 4.4** : BanSpot 4 / 646 et 56 / 646, Cordana 99,4 %. Deuxième avis sans écart. Adoption proposée. C_quatre et v12a13 non mesurés (coupure). Test vierge non lu.

09 h 17 : Juge comptage fini. **Aucune adoption.**
- E5p90b : F1 des juges 0,672 contre 0,600 ; erreur de compte 0,215 contre 0,382 ; fausses sans bananier 1,12 %, au-dessus de la limite de 1 %.
- E10 et v6f échouent sur CG.
- Test vierge non lu.

09 h 25 : récapitulatif écrit (`recap.md`).

09 h 30 : accord de Corentin pour lire le test vierge AgroVisionBD une fois, en entier. Le Juge maladies lance le calcul à 9 h 23 (SHA-256 26 / 26).

09 h 46 : le Juge se fige. Son calcul s'arrête à 10 h 29 (v10b 1 024 / 1 082). À 10 h 46, le chef d'orchestre relance le même script, qui reprend sans rien relire.

11 h 44 : **test vierge AgroVisionBD lu** (1 082 photos ; 113 lues en 2 × 2). Deuxième avis : 0 écart.
- Chaîne installée : 12 / 716 malades ratées, 51 / 366 saines en alerte, coût 18,96.
- F1 : 5 / 716 ratées, 87 / 366 en alerte (dont 66 « à vérifier »), coût 25,87.
- F3 : 8 / 716 ratées, 79 / 366 en alerte, coût 24,94.
- F1 rate moins de malades, mais il donne plus de fausses alertes, surtout sur les saines vues de loin (50 sur 119, contre 20).
- Rien ne se décide sur ce test.

12 h 00 : Corentin adopte F1.

12 h 30 : F1 appliqué dans `fieldscan/modules/maladies.py` et `config.yaml` (sauvegarde dans `out/adoption_f1/sauvegarde_avant/`).
- Vérification : 0 réponse différente de la référence sur 2 879 jeux de probabilités en cache.
- Démo complète : sans erreur.
- Ancienne configuration : sorties identiques à avant.
- Temps de la démo : 175 s contre 42 s pour 12 photos.
- Non commité.
