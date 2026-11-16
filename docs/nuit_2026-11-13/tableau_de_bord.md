# Tableau de bord, nuit du 13 au 14 novembre 2026

23 h 45 : plan écrit avant tout calcul (`docs/plan_nuit_2026-11-13.md`, empreinte dans `empreinte_plan.txt`). Corentin : les deux modules, local + Kaggle, aucun téléchargement.

23 h 50 : six agents lancés : M-banc, M-entraîneur, C-banc, C-entraîneur, Prospection (sans téléchargement), Contrôleur. Gel des finalistes à 6 h, juges relus de 6 h à 7 h 30, récapitulatif à 8 h.

1 h 00 : Prospection finie, rien téléchargé. Maladies : candidat test vierge BBTV-3 (Universe, 1 338 images, CC BY 4.0, ~70 Mo) ; BTDDD le dépasserait par la règle des effectifs : à trancher par Corentin avant téléchargement. Comptage : aucun jeu bananier ouvert ; négatifs possibles (ananas, caféiers, conteo-lzfcf). ~450 Mo à télécharger si accord. `out/prospection_nuit_1311/candidats.md`.

13 h 10 : session arrêtée vers 1 h 05, agents arrêtés, rien gelé, aucun juge lu. Corentin relance. Avenant : gel à 19 h, juges de 19 h à 20 h 30, récapitulatif à 21 h (`avenant_horaires.md`). Agents repris avec leur contexte.

13 h 20 : C-entraîneur, point d'étape. Lot 1 : aucun finaliste. c13a passe la condition « résolution » à 11 cm (0,713 contre 0,601), mais perd sur MM, plantain, dense et l'erreur de compte. c13d (« petits ») : 0,860 à 5 cm, mais les 4 anciennes validations sont sous le v5. Lot 2 lancé sur Kaggle à 13 h 14. GPU : 1,4 h. Relancé jusqu'à 18 h 40 ; cartes et c13d transmis à C-banc.

13 h 30 : Contrôleur, point d'étape, aucune alerte. Les lectures des juges sont expliquées : calcul des MD5 par M-entraîneur pour bloquer les envois, liste des noms du zip par Prospection. ADMIS AVEC RÉSERVE : F1_bornes, variante rapide de M-banc (0 alerte différente sur 7 746 photos, 54 à 58 % de temps en moins). C-banc : deux choix recalculés à l'identique, pas encore écrits. Contrôleur relancé jusqu'au gel.

13 h 50 : C-banc fini. finalistes.md : A1 CB13_trous_b0.20_reseau (0,8650 ; famille A), A2 CB2_cb13_moy345sh_b0.20 (résolution, 11 cm 0,7027 contre 0,6005), C1 CB1C_c13d_dec-0.05 (0,8773, btd optimiste car c13d a appris btd_train). Tout le gain vient de btd_val ; les 4 anciennes sont identiques au v5. 166 essais.

14 h 55 : M-banc fini. finalistes.md : un seul candidat, F1_bornes (famille A, « variante rapide ») : 0 alerte différente de F1 sur 7 746 photos, coût 33,94 (= F1, recoupé par M-entraîneur), 54 % de temps en moins par lecteur et 67 % de bout en bout (12 photos). Réserve écrite par M-banc : le « 6,8 s » du plan est déjà F1 lu avec les bornes ; le gain est mesuré sur le code en service (morceaux lus sur 91 % des photos). Ne passent pas : MB1 (33,23 > 32,94), MB3 (4 jeux seulement), MB4. 96 essais. Aucun calcul de M-banc ne tourne.

16 h 50 : C-entraîneur fini. finalistes.md définitif : 3 candidats famille C (E5p90b_c13e_d-0.1 0,8811, 4 anciennes 0,8544, val_negatifs 4 ; E5p90b_c13d_d-0.1 0,8808 ; E5p90b_c13e_d-0.05 0,8804), tous admis avec réserve par le Contrôleur (recalculs identiques). Aucun CE1 (MM < 0,837 ; c13h à 0,831). Lot 3 jamais démarré (file Kaggle 14 h 54-16 h 49), supprimé : pas de mesure entre graines. GPU 3,05 h sur 7. Jeu Kaggle privé créé : comptage-c13-depart (ses poids v6f). Liste provisoire du Contrôleur : comptage E5p90b_c13e_d-0.1 (C) et A1 CB13_trous_b0.20_reseau (A) ; maladies F1_bornes (A), 2e place vide tant que le lot 2b de M-entraîneur (file Kaggle depuis 14 h 08) n'a pas rendu de poids.

17 h 56 : M-entraîneur fini. finalistes.md : un finaliste, d3b (famille B, élève distillé de F1, ensemble de 2 ConvNeXt-Tiny appris sans TDTU / sans Éthiopie) : coût de réglage 32,77 (F1 33,94), roamer 182 (limite 229), environ 0,2 × F1 en temps (estimé). Admis avec réserve par le Contrôleur à 17 h 32 (recalcul 32,766). Réserves : confiances réglées sur les jeux qui les mesurent (coût croisé 33,73) ; plus de malades ratées que F1 en validation (0 → 5), TDTU (19 → 30), AgroVisionBD (5 → 10). d2b instable (33,16), ME2 et ME3 sans finaliste. lot2b supprimé (file T4), relancé en P100 (lot2p). GPU 2,92 h sur 7. Poids : modeles/maladies_nuit_1311/d3b/ (jamais commités).

18 h 30 : à la demande de Corentin, pistes 2 et veille lancées, hors du gel de 19 h (avenant_pistes_2.md, SHA-256 baf20929f04b17c1…). Veille (publications 2024-2026, lecture seulement, rapport avant 20 h 30), M-piste2 (mélanges F1 + d3b, désaccord, élève sensible au coût, stabilité de d3b) et C-piste2 (mélanges de cartes v5 + c13h, A1 + c13e, grille de plantation, stabilité de c13e). Réglage seulement, aucun juge ; finalistes de réserve avant 23 h 30. Contrôleur prévenu des nouvelles zones.

18 h 45 : Veille finie (docs/veille_2026-11-14/ : synthese.md, veille_maladies.md, veille_comptage.md ; 66 adresses citées). Deux références vérifiées en ligne par la session principale : Zhou et al., arXiv 2608.26771 (distillation DINOv2 → modèle léger, thé) et Pacini et al., CountingDINO, arXiv 2504.16570, WACV 2026 : conformes. Aucun téléchargement ; un PDF CEUR refusé par le garde-fou, non contourné. Aucun nouveau jeu ouvert de bananiers. Idées sans téléchargement transmises à M-piste2 (lecteur kNN, agrégation des morceaux, contrôle conformel) et à C-piste2 (vérification des pics par prototypes, force de la grille). Idées qui demanderaient un téléchargement (GeCo2, TasselNetV4) : à soumettre à Corentin.

18 h 53 : à la demande de Corentin (« n'attends pas si tu as déjà tout »), gel avancé : l'échéance d'admission (18 h 45) est passée et les empreintes sont écrites depuis 18 h 47. Contrôleur prié d'écrire la LISTE GELÉE maintenant. Juge maladies et Juge comptage lancés ; ils attendent la liste écrite et vérifient les empreintes avant toute lecture. Fils : Juge maladies 4, Juge comptage 2, pistes 2 chacune jusqu'à 20 h 30.

18 h 53 : LISTE GELÉE écrite par le Contrôleur (verdicts.md version 12), gel avancé à la demande de Corentin, aucun candidat admis après 18 h 45. Maladies : 1. d3b (B, 32,77), 2. F1_bornes (A, 33,94). Comptage : 1. E5p90b_c13e_d-0.1 (C, 0,8811), 2. CB13_trous_b0.20_reseau (A, 0,86495 ; égalité exacte avec CB2, le moins coûteux gardé). Empreintes : 88 fichiers à 18 h 47. Aucune alerte sur 13 passages des interdits. Le Contrôleur demande, pour CB13, la moyenne sans segmento est (le v3 l'a appris) : transmis au Juge comptage.

19 h 50 : Veille hauteur finie (docs/veille_2026-11-14/hauteur.md), à la demande de Corentin (MNS/CHM pour le comptage). Aucun jeu public de bananiers avec MNS et annotations. Meilleure piste : banavista, déjà local (348 photos DJI brutes 4 000 × 3 000, recouvrement médian 81 %). Vérifié par la session principale : 0 champ EXIF (donc pas de GPS) sur 6 photos du zip, Roboflow les a retirés ; mémoire de la machine 31,4 Go. ReforesTree : ni MNS ni photos brutes. Logiciel : ODM natif Windows (AGPL) ; dépôts GitHub ODM et WebODM vérifiés (ODM 3.6.2, WebODM 4.0.0 ; noms et tailles des fichiers non visibles). Téléchargement d'ODM soumis à Corentin.

19 h 35 : avec l'accord de Corentin (« Oui, télécharge »), ODM_Setup_3.6.2.exe téléchargé depuis la page GitHub officielle dans C:\Users\coren\outils\odm_3.6.2\ (hors du dépôt) : 244 864 104 octets, SHA-256 c9dbfabf0d066529… identique à celui publié par GitHub, signature Authenticode valide (CN=OpenDroneMap). Pas encore installé. Brouillon de protocole écrit avant tout calcul : docs/protocole_hauteur_banavista.md (photos d'entraînement de banavista seulement). Kaggle : m14-lot1 et c14-lot1 finis et récupérés par les agents ; m14-lot2 en cours, c14-lot2 en file.

19 h 45 : Corentin valide le protocole hauteur (« Oui, lance ») : docs/protocole_hauteur_banavista.md, SHA-256 6ad53cb4138944ec… (protocole_hauteur_banavista.sha256). ODM 3.6.2 installé en silencieux (code 0) dans C:\ODM (985 Mo), hors du dépôt ; journal d'installation dans C:\Users\coren\outils\odm_3.6.2\. Agent Hauteur lancé (photos d'entraînement de banavista seulement, 2 fils jusqu'à la fin des Juges). Écrit dans out/hauteur/, scripts/hauteur_*.py, journal_hauteur.md.

19 h 50 : Juge comptage fini (juge_comptage.md, juge_c/regle_adoption.json relus). Empreintes 30/30 avant et après. Témoin v5 = chiffres du 12/11. Les deux finalistes passent les 3 conditions ; la règle désigne E5p90b_c13e_d-0.1 (meilleur réglage) : F1 moyen 0,5998 (seuil 0,5901 ; v5 0,6001), erreur 0,170 (v5 0,382), 0 fausse détection sans bananier (v5 36). CB13 : 0,6304, erreur 0,238, 36 fausses. Deuxième avis : identique sauf CB13 segmento (2 détections, tri non stable), verdict inchangé. Adoption proposée et lecture de banana_trees_kp : à décider par Corentin.

19 h 55 : Corentin confirme la lecture du test vierge (« Oui, lis-le ») : banana_trees_kp, une seule fois, pour E5p90b_c13e_d-0.1 et le v5 à 0,30. Juge comptage repris ; méthode de mesure écrite au journal avant la lecture.

20 h 05 : M-piste2 fini (finalistes_piste2.md, bilan_graines.json relus). Finaliste de réserve MC1-OU-proche (C) : 32,83, 208 malades sans alerte sur 5 jeux contre 243 pour F1, mais instable (graines 1-3 : 33,11 ; 33,29 ; 33,71) et sans doute hors limite sur BanSpot (ses alertes contiennent celles de F1, déjà à 56/56). Constat majeur : d3b n'est pas stable d'une graine à l'autre (graines 1-3 : 33,44 ; 34,49 ; 35,12 ; moyenne des 4 = 33,95 = F1). 23 essais, GPU 1,14 h.

20 h 15 : test vierge banana_trees_kp lu une fois (19 h 49-20 h 13), méthode écrite à 19 h 48 avant lecture, empreintes 10/10. v5 : F1 0,126, erreur 0,485 ; E5p90b_c13e_d-0.1 : F1 0,110, erreur 0,511, 148/157 photos aiguillées. Le candidat fait moins bien que le v5 ; deuxième avis identique. Scores très bas pour les deux (photos ≈ 11 cm/px réduites à 640 px ; détections à 45 px médians des points annotés). Adoption déconseillée ; décision à Corentin.

20 h 41 : décision de Corentin (« Oui, garde le v5 ») : E5p90b_c13e_d-0.1 n'est pas adopté ; le v5 au seuil 0,30 reste en service. config.yaml inchangé.

20 h 57 : Corentin veut un rendu Blender de la parcelle (« on peut essayer de faire ça non »). Blender 5.2.4 LTS portable (GPL) téléchargé depuis download.blender.org dans C:\Users\coren\outils\blender_5.2.4\ (hors du dépôt) : 405 779 142 octets (annoncé « environ 350 Mo »), SHA-256 bbd78f89… identique au fichier publié, signature valide. Agent Rendu lancé : bananier procédural, plants placés sur les détections du v5 d'une tuile d'entraînement, rendus Cycles à 2 fils jusqu'à 21 h 45. Écrit dans out/rendu_blender/, scripts/blender_*.py, scripts/rendu_*.py, journal_rendu.md.

21 h 10 : Juge maladies fini (juge_maladies.md, juge_m/bilan.json relus). Empreintes 88/88. F1_bornes passe (4/646 ; 56/646 ; Cordana 99,4 %, = F1) ; d3b ne passe pas (BanSpot 12/646 tachées sans alerte, limite 6 ; saines et 137 Cordana non lues, lecture arrêtée après le verdict). Adoption proposée : F1_bornes (modification de fieldscan/ à soumettre à Corentin). Agent Hauteur autorisé à 4 fils.

21 h 15 : récapitulatif écrit (docs/nuit_2026-11-13/recap.md). Pistes 2 comptage, hauteur et rendu encore en cours.

21 h 25 : essai hauteur arrêté en phase 1 (out/hauteur/resultat.md, phase1_sfm.json relus) : 58/98 photos placées (59 %, seuil 80 %). La ligne DJI_0564-0661 (session A, entraînement) mélange une pépinière en pots (58 photos) et une plantation dense (40) ; OpenSfM les sépare en 3 reconstructions ; la plantation seule : 31/40. Phase 2 non lancée. Protocole inchangé (SHA-256 6ad53cb4… au début et à la fin). Piste proposée : avenant pour les lignes DJI_0757-0841 (session B, entraînement, plantation dense en lignes de vol), à décider par Corentin.

21 h 50 : C-piste2 fini (finalistes_piste2.md, tableau_essais.md relus). Finalistes de réserve : CC1_v5h_50 (C ; 0,8886 ; sans btd_val 0,8630 ; 11 cm 0,8569 ; val_negatifs 7 ; 3,2 × le temps du v5 ; gain hors btd_val fragile : +0,004 avec les 3 autres réseaux robustes) et CC3_a1_a35 (A ; 0,8671 ; 0,8563). Stabilité de c13e sur 3 graines confirmée. 27 essais, GPU ≈ 0,55 h. Carnet Kaggle c14-lot2 toujours en file, abandonné mais non supprimé.

22 h 05 : Rendu Blender fini (out/rendu_blender/, README, parcelle_bananiers.blend ; vues relues). Tuile d'entraînement rt_Flora_Pluas_5cm_818_818 (ReforesTree), 60 centres du v5 à 0,30, teinte par l'ExG réel de la chaîne (run.py --modules vigueur relancé dans out/rendu_blender/chaine_vigueur/). Prototype convaincant en vue de dessus ; en vue proche, faux-troncs trop fins et hauts (aspect palmier), sol flou, plan qui flotte sur un fond uni.

### 15/11, 00 h 15 : rendu Blender v2, mission de la nuit

**Rendu v2** (`out/rendu_blender/v2/`) :
- 9 tuiles d'entraînement de Flora Pluas, sur 66,5 m de côté ;
- 334 bananiers placés sur les centres du v5 ;
- bananiers refaits : tronc épais, feuilles sèches, régimes illustratifs ;
- sol procédural, lisière d'arbres et horizon.

**Avis de Corentin** : « C'est super, avance a fond dessus! C'est ta mission de la nuit. »

**À vérifier** : la planche vue de dessus semble mal alignée avec les centres de la photo, alors que `plants.csv` est cohérent.

**Suite confiée à l'agent Rendu** (sortie dans `v3/`) :
- contrôle de l'alignement par projection ;
- couronnes calibrées sur la couverture réelle ;
- lisière plus réaliste ;
- éclairage rasant ;
- vidéo de survol et image « héros » en 1920 × 1080.

### 15/11, 03 h 30 : rendu Blender v3 terminé et vérifié

**Alignement** : pas de défaut.
- Les centres projetés par la caméra Blender sont à 0,00 px de la formule de `plants.csv`, et 100 % tombent sur une feuille.
- Ma fausse alerte venait des arbres d'agroforesterie (zones vertes sans centre), qui étaient en sol nu dans la v2.

**v3** (`out/rendu_blender/v3/`) :
- 12 arbres illustratifs placés sur les zones d'arbres de la photo ;
- couronnes calibrées : 85,7 % de vert sur la photo, 84,9 % sur le rendu à l'échelle 1,0 ;
- corrélation du vert photo/rendu par blocs de 5 m : 0,04 → 0,28 ;
- lumière de fin d'après-midi ;
- image héros 1920 × 1080 ;
- `survol_parcelle.mp4` : 12,5 s, 300 images, photo réelle puis 3D, contrôlé sur 4 images extraites.

**Incident** : `v2/parcelle_bananiers.blend` a été écrasé par un essai (images v2 intactes, signalé dans le README).

**Limites restantes** :
- la vue de dessus est moins couverte que la photo ;
- les feuilles des arbres sont en losange quand on les voit de près ;
- il n'y a que 24 formes de bananier ;
- l'aspect EEVEE du survol diffère des images fixes.

Images et vidéo envoyées à Corentin.

### 15/11, 07 h 00 : rendu Blender v4 terminé et vérifié, fin de la mission de nuit

`out/rendu_blender/v4/`. La v2 et la v3 n'ont pas été modifiées : dernière écriture dans v3 à 03 h 26.

**Changements :**
- survol EEVEE rapproché de Cycles, fondu photo → 3D de 1,5 s avec étalonnage (300 images, contrôlé sur 4 images extraites) ;
- arbres : feuilles elliptiques, plus aucune feuille flottante, écorce procédurale ;
- 48 formes de bananier, rejets et régimes retouchés ;
- pistes de terre, haies, brume plus légère ;
- teinte des arbres en vue de dessus : rapport R/V/B 0,56/0,48/0,62 en v3, 0,79/0,70/0,87 en v4, 0,97/0,92/1,00 sur la photo.

**Contrôles v4 :**
- alignement : 100 % des centres tombent sur une feuille ;
- corrélation du vert photo/rendu par blocs de 5 m : 0,31 (0,28 en v3).

**Limites :**
- le survol EEVEE reste distinct des images Cycles ;
- l'horizon est voilé ;
- la bande clairsemée en vue de dessus est gardée volontairement (pieds non détectés par le v5).

Images et vidéo envoyées à Corentin.

### 15/11, vers 16 h : F1_bornes appliqué (accord de Corentin, « Oui, applique »)

**Fichiers modifiés**
- `fieldscan/modules/maladies.py` : la lecture F1_bornes passe par `_melange_bornes`. Les morceaux sont lus par `_lire_morceaux`, et la mise en forme est commune aux deux lectures (`_sorties_melange`).
- `config.yaml` : `morceaux_bornes: true`.

**Contrôles**
- Caches de réglage, 7 746 photos (`scripts/verifier_f1_bornes.py`) :
  - aucune alerte ne diffère de F1 ;
  - 60 noms de maladie changent ;
  - les morceaux ne sont lus que sur 12 % des photos.
- Photos de démo (12) :
  - réponses identiques ;
  - module maladies en 128 s au lieu de 279 s ;
  - avec `morceaux_bornes: false`, on retrouve la lecture complète de F1.

Rien n'est commité.

### 15/11, vers 16 h 45 : visite web 3D de la parcelle (accord de Corentin pour three.js chargé depuis un CDN)

**Livraison**
- Dossier : `out/visite_parcelle/` (`index.html`, `scene.glb` de 39,2 Mo, `pieds.json`, `LISEZMOI.md`, captures).
- Scripts : `scripts/visite_generer.py`, `scripts/visite_exporter_blender.py`.

**Ce que fait la visite**
- Promenade à 1,7 m de hauteur.
- Vue drone et mini-carte sur la photo réelle.
- Fiche de chaque pied, mode Santé, interface pour téléphone.

**Vérifié par la session principale dans le navigateur intégré**
- La page se charge ; la vue drone et le mode Santé fonctionnent.
- La console ne montre aucune erreur.

**Limites**
- Le serveur local tronque parfois le glb (probablement Norton). La page recommence alors le téléchargement d'elle-même.
- Le rendu est en dessous de Cycles : ombres très noires, arbres en blocs.

**Autre exploitation** : `visite_generer.py --pieds pieds.geojson --bulletin bulletin.csv`, essayé sur EO1. Rien n'est commité.

### 15/11, 18 h 25 : second tour Kaggle clos, aucun finaliste
- Maladies : 19 essais, meilleur à 33,69 (F1 : 33,94).
- Comptage : 4 réseaux partant du v5 échouent sur MM, sur les 4 anciennes et sur ReforesTree (≤ 93 %).
- Aucun juge relu.
- `c15b-lot2` toujours en file chez Kaggle, à annuler.
