# Test final et validation dense : proposition d'independent-evaluator

Rédacteur unique : independent-evaluator. Les ajouts sont datés ; une section écrite n'est jamais réécrite après une mesure qui la concerne (une correction est une nouvelle section datée qui renvoie à l'ancienne).

## 0. État

- **Test final : non choisi.** Les options A, B et C (`docs/research-brief.md`, section 5) attendent la décision de Corentin. Tous les groupes `test` et `exclu` du découpage v5 restent scellés (banano, btd, segmento_est, bv_b_tampon, palmier_44000_4000, cocotier_1300_plus, CG, Carlos Vera Arteaga, dossiers `cg/`). Aucun agent ne les ouvre.
- **Validation dense : découpée ci-dessous** (section 1), le 7 novembre 2026, **avant toute mesure** d'une méthode, du v5 ou de la baseline sur l'une ou l'autre moitié.

## 1. Validation dense (écrit le 7 novembre 2026, avant toute mesure sur `bv_b_val`)

### 1.1 Pourquoi couper `bv_b_val` en deux

D-003 lance une boucle d'expériences qui compare plusieurs variantes de méthode explicite au v5 sur la plantation dense. Si chaque variante est mesurée sur toute la validation dense et que l'on garde la meilleure, le F1 de la gagnante est optimiste (sélection sur la mesure). On garde donc une moitié **scellée**, mesurée une seule fois, pour confirmer la seule variante retenue.

### 1.2 Unités : lignes de vol et blocs

[O] `out/analyse_banavista/groupes_photos.json` (calcul de recouvrement entre photos voisines, `scripts/analyser_jeu_roboflow.py`, sans modèle ni annotation) : la session B de validation forme **4 lignes de vol de 21 photos**, sans recouvrement entre la dernière photo d'une ligne et la première de la suivante :

| Ligne | Photos |
| --- | --- |
| L1 | DJI_0862 à DJI_0882 |
| L2 | DJI_0883 à DJI_0903 |
| L3 | DJI_0904 à DJI_0924 |
| L4 | DJI_0925 à DJI_0945 |

[O] Recouvrement médian de 0,81 entre photos consécutives : deux photos à 5 rangs d'écart ne se recouvrent presque plus (environ 0,81 − 4 × 0,19 ≈ 0,05). **Bloc** = 7 photos consécutives d'une même ligne (B1 : rangs 1 à 7, B2 : 8 à 14, B3 : 15 à 21), soit 3 blocs par ligne. Le bloc est l'unité du bootstrap (section 2.4) ; la photo serait trop dépendante de ses voisines.

### 1.3 Découpage

- Deux moitiés **contiguës** : A = {L1, L2} (DJI_0862 à 0903), B = {L3, L4} (DJI_0904 à 0945).
- Pourquoi contiguës plutôt que deux lignes tirées au hasard : le recouvrement latéral entre lignes voisines n'est pas exclu (protocole v5, section 2 : non détecté, mais une canopée répétitive peut le masquer). Avec des moitiés contiguës, une seule frontière (L2-L3) touche les deux moitiés ; avec {L1, L3} contre {L2, L4}, il y en aurait trois.
- Tirage : `numpy.random.default_rng(2026).integers(0, 2)` vaut 1, donc **`val_iter` = B = {L3, L4}, DJI_0904 à DJI_0945 (42 photos, 6 blocs)** et **`val_scellee` = A = {L1, L2}, DJI_0862 à DJI_0903 (42 photos, 6 blocs)**. Le tirage ne dépend d'aucune mesure.
- Liste complète, une ligne par photo (photo DJI, image préparée `data/drone/comptage_v5_5cm/images/bv_bv_b_val_NNNN.jpg`, image Roboflow, ligne, bloc, rôle, SHA-256 de l'image préparée) : `out/comptage_math/evaluation/decoupage_bv_b_val.csv`, **SHA-256 du fichier : `7aafb1fe8fd936421ad76373551d822ca2de7fc86b2881039cc0415e3dc0e741`**. Correspondance image préparée ↔ photo DJI : ordre alphabétique des noms Roboflow dans le groupe (`scripts/preparer_comptage_v3.py`, boucle `enumerate(g.sort_values("image"))`), vérifiée par l'égalité du nombre de boîtes sur les 84 photos.
- **Limites** : les deux moitiés viennent de la même mission et de la même ferme que l'entraînement du v5 (bv_b_train) et que le développement dense ; `val_scellee` protège contre la sélection de variantes, pas contre le biais de ferme. Le v5 a choisi son époque et son seuil sur une moyenne qui inclut tout `bv_b_val` (protocole v5, section 5) : sur les deux moitiés, le v5 est donc légèrement favorisé, ce qui rend la comparaison prudente pour la méthode explicite.

### 1.4 Qui voit quoi

- `val_iter` : mesurée à chaque cycle par independent-evaluator ; les chiffres agrégés et, sur demande d'error-analyst, les appariements par image, peuvent circuler. Chaque mesure compte comme une variante (section 2.3).
- `val_scellee` : **aucune image, aucune détection, aucun chiffre** avant la confirmation. Ni le v5 ni la baseline n'y sont mesurés maintenant. Ils le seront **une seule fois, en même temps que la variante candidate**, avec le même code.
- Contrôle de reproductibilité du code : **pas sur `bv_b_val`** (cela exposerait `val_scellee`) ; il se fait sur deux autres validations du v5 dont le F1 est publié (protocole v5, section 9) : jeunes bananiers dji_0544 (F1 0,893) et plantain `pp_100_metros` (F1 0,885), au seuil 0,30.

## 2. Critère de victoire « la méthode X bat le v5 en dense » (écrit le 7 novembre 2026, avant toute mesure)

### 2.1 Mesure

- Code unique : `scripts/math_evaluer.py` (appariement un à un, distance totale minimale, paires à moins de 1 m, `apparier()` de `scripts/evaluer_comptage.py` importé sans modification ; **mères seules** : un point de référence non `mere` n'est ni à trouver ni une fausse détection).
- Région comptée : disque de 2 000 px de la photo d'origine (426,5 px à 5 cm/px), comme la validation du v5 ; détections et références hors disque ignorées.
- Métrique principale : **F1 mères seules, cumulé sur les photos** de la moitié (somme des VP, FP, FN). Rapportés aussi : précision, rappel, erreur de comptage relative, rappel au budget k = N_réf, niveau nul « demi-maille ».

### 2.2 Réglages permis

- Tout paramètre de la méthode X, **y compris son seuil de score**, est choisi sur le **développement dense** seul : `bv_session_a`, `bv_b_train`, `lasuiza`, `vols_100_022x`, `corte` (cumul de ces cinq groupes, mères seules). `segmento_ouest` (environ 11 cm/px) est mesuré à part et ne sert pas au choix.
- Le seuil est figé par `math_evaluer.py` (meilleur F1 du développement) puis appliqué tel quel à `val_iter`. Aucun paramètre n'est choisi sur `val_iter`.
- Références : **v5 au seuil 0,30** (seuil officiel, `modeles/centres_5cm_v5.json`) ; **baseline ExG + maxima** (`out/comptage_math/evaluation/baseline.py`) réglée sur le développement dense par une grille déclarée dans E-001.

### 2.3 Plafond de variantes et correction

- **Au plus 8 variantes mesurées sur `val_iter`**, tous cycles confondus. Une variante = une configuration figée (code, paramètres, seuil) dont le F1 sur `val_iter` est calculé, même une seule fois, même « pour voir ». Le compteur figure dans chaque E-NNN.
- Correction de Bonferroni sur le plafond : niveau unilatéral **α = 0,05 / 8 = 0,00625** pour chaque test sur `val_iter`, quel que soit le rang de la variante (pas de bonus pour les premières).

### 2.4 Règle sur `val_iter` (sélection)

Une variante X est **candidate** si, sur `val_iter` :
1. F1(X) > F1(v5 à 0,30) ;
2. la borne basse unilatérale à 1 − 0,00625 (percentile 0,625 %) de la différence appariée F1(X) − F1(v5), par **bootstrap par blocs** (6 blocs de 7 photos, 10 000 tirages, graine 2026, mêmes tirages pour X et le v5), est **> 0** ;
3. même règle (1 et 2) contre la baseline ExG réglée sur le développement ;
4. F1(X) dépasse le niveau nul demi-maille de `val_iter` (contrôle HF-01).

La **première** variante candidate arrête la boucle sur `val_iter` et passe à la confirmation. On ne cherche pas « mieux » après coup sur `val_iter`.

### 2.5 Confirmation sur `val_scellee` (une seule fois)

- Avant la mesure : la variante est figée, son code et sa configuration sont empreintés (SHA-256) dans ce fichier, avec la date.
- Mesure unique, par independent-evaluator, de X (au seuil figé sur le développement), du v5 à 0,30 et de la baseline, avec le même code.
- **« X bat le v5 en dense (validation) »** si F1(X) > F1(v5) sur `val_scellee` **et** si la borne basse unilatérale à 95 % de la différence appariée (bootstrap par blocs, 6 blocs, 10 000 tirages, graine 2026) est > 0. Un seul test, donc pas de correction.
- En cas d'échec : la conclusion est « non confirmé », rapportée telle quelle ; `val_scellee` est consommée. Une nouvelle confirmation demanderait un nouvel ensemble scellé, décidé par Corentin.
- La phrase finale du rapport reste limitée à cette ferme (section 1.3, limites) ; le jugement sur une zone jamais vue appartient au test final, non encore choisi.

### 2.6 Arrêt

La boucle s'arrête : (a) à la première candidate (puis confirmation) ; (b) après 8 variantes sans candidate : résultat négatif documenté (H8) ; (c) sur décision de Corentin.

### 2.7 Pourquoi ce critère (justification)

- Bootstrap par blocs et non par photo : recouvrement de 81 % entre photos voisines ; un intervalle par photo serait trop étroit. Avec 6 blocs, l'intervalle est large : le critère exige un gain **régulier d'un bloc à l'autre**, ce qui est le sens de « bat le v5 ».
- Différence appariée : X et le v5 sont mesurés sur les mêmes plants ; la variabilité commune (densité, lumière du bloc) s'annule.
- Bonferroni sur le plafond fixe plutôt que Holm séquentiel : le nombre de variantes n'est pas connu d'avance et les variantes arrivent l'une après l'autre ; un α fixe par test, écrit avant, est simple à vérifier.
- Le seuil de score figé sur le développement empêche le gain par « meilleur seuil sur la validation ». Le v5 garde son seuil officiel, choisi en partie sur `bv_b_val` : avantage au v5, assumé.

## 3. Amendement 1 (7 novembre 2026, avant toute mesure sur le développement dense et sur `val_iter`)

Écrit après les messages d'annotation-manager et de leaf-mathematician relayés par le chef d'orchestre. À ce moment, aucune mesure d'E-001 n'a été lue sur le développement ni sur `val_iter`. Seul le contrôle de reproductibilité (dji_0544, pp_100_metros) a été lu. Une première passe de réglage de la baseline sur l'ancien développement à 5 groupes a été **interrompue sans être lue**, et ses sorties ont été effacées. Les sections 1 et 2 restent valables, sauf les points ci-dessous, qui les remplacent.

### 3.1 Développement dense : pépinière, doublons, complétude

- **Pépinière et bordures retirées** (règle v2 d'annotation-manager, `docs/recherche/conventions_comptage.md` § 1.4 : densité de références < 0,05 plant/m²). 59 photos de `bv_session_a` sur 123 sortent du développement dense. Source : `data/comptage_math/references/dev_dense_images.csv` (1 849 tuiles gardées). `math_evaluer.py` filtre sur ce fichier. Les tuiles exclues sont gardées sous le rôle `dev_exclu`, mesurables pour information, jamais pour régler.
- **Doublons de lasuiza** : 409 images pour 316 tuiles d'origine (colonne `photo` de `dev_dense_images.csv`). On ne garde que la première copie (plus petit numéro k), les autres passent en `dev_exclu`.
- **Unité du bootstrap sur le développement** = **photo ou tuile d'origine** (colonne `photo`). Les 401 découpes de `vols_100_022x` forment 78 unités.
- **Complétude, règle retenue** : le réglage se fait sur les groupes de banavista seulement.
  - **`dev_reglage`** = `bv_session_a` (sans pépinière) + `bv_b_train`. Références jugées complètes : ratio médian 1,10 à 1,12, aucune unité suspecte. Même ferme, même capteur et même mode de prise de vue que `val_iter`.
  - **`dev_transfert`** = `lasuiza` (dédoublonné), `vols_100_022x`, `corte`. Mesuré et rapporté par groupe, mais **ne sert à choisir ni un seuil ni un paramètre**. Raison : les références incomplètes de lasuiza (ratio médian 0,56) et de vols (75 unités suspectes) biaisent la précision vers le bas. Un réglage qui les inclut pousse vers moins de détections que la vérité.
  - Pondérer ces groupes n'est pas retenu : il n'existe aucun poids objectif de complétude par image.
  - Conséquence : la phrase « réglé sur le développement » de la section 2.2 se lit désormais « réglé sur `dev_reglage` ». Le F1 de sélection est le **F1 cumulé sur `dev_reglage`**.
  - Ce qui remettrait cette règle en cause : une planche d'annotation-manager montrant que les unités « suspectes » de lasuiza et de vols sont de la végétation non bananière et non des oublis d'annotation.
- **Paramètres des méthodes** (et non seulement le seuil) : même règle. La grille et le critère sont déclarés avant ; le critère est calculé sur `dev_reglage`. La moyenne des F1 des 5 groupes prévue au § 8.3 de `docs/recherche/modele_feuille.md` n'est pas acceptée comme critère d'envoi : elle doit être remplacée par le F1 cumulé sur `dev_reglage`, avant la mesure. Les groupes de transfert restent rapportés.

### 3.2 Ajout au critère de victoire (OBJ-C8)

Une condition 5 s'ajoute à la section 2.4 : **à budget égal**, le F1 de X au budget k = N_réf, avec le classement global des scores sur `val_iter`, est ≥ celui du v5 au même budget (estimation ponctuelle). La même condition s'ajoute en 2.5 sur `val_scellee`. Une victoire au seul point de fonctionnement, ou au seul budget, est rapportée comme « non concluante ».

### 3.3 Réponses à leaf-mathematician (D-004, cycle 1 = A′)

- **(a) Hyperparamètres réglés sur le développement : hors plafond.** Le plafond de 8 ne compte que les configurations dont le F1 sur `val_iter` est calculé. Une grille déclarée avant et évaluée sur le développement ne consomme rien, quelle que soit sa taille. Le canal, l'échelle, le rayon et z0 sont donc hors plafond ; ils sont choisis sur `dev_reglage`.
- **Témoin A-iso** : la condition A′ > A-iso (§ 8.5 et 8.6.4) se juge **sur le développement**, donc hors plafond. Si A-iso est aussi mesuré sur `val_iter`, il compte pour une variante. Il ne peut pas devenir candidat au cycle où il sert de témoin.
- **(b) Double comptage : seuil de 15 % confirmé, avec cette définition opérationnelle.**
  - Paires = paires de **plus proches voisins mutuels** parmi les mères annotées de la région, à moins de 3,5 m l'une de l'autre.
  - Une paire est **doublement comptée** si une détection (au seuil retenu sur le développement) tombe à moins de 0,5 m du milieu de la paire et à plus de 0,5 m des deux centres.
  - Taux = paires doublement comptées / paires, cumulé sur `dev_reglage`.
  - Condition d'envoi : taux ≤ 0,15. Le même taux est rapporté pour le v5 et pour le niveau nul de demi-maille.
  - Code : `math_evaluer.py`, champ `double_comptage` du résumé.
- **(c) Critères OBJ-C1 à OBJ-C8 conditionnant l'envoi sur `val_iter`.** Tous sont mesurés sur le développement, avec `math_evaluer.py` ou avec un code de leaf-mathematician dont la commande est donnée. L'intervalle se calcule par bootstrap par photo d'origine, 2 000 tirages, graine 2026.
  - **OBJ-C1** : un résultat synthétique ne compte jamais comme appui pour l'envoi. Condition : sur `dev_reglage`, le rappel de A′ au budget k = N_réf dépasse celui du niveau nul de demi-maille de plus de 2 erreurs types bootstrap.
  - **OBJ-C2** : règle du § 8.5 acceptée telle quelle (A′ > A-iso au même budget, borne basse de l'intervalle bootstrap à 95 % de la différence appariée > 0, sur au moins 2 groupes sur 3 parmi `bv_b_train`, `vols_100_022x` et `lasuiza`). L'unité du bootstrap est la photo d'origine, pas la tuile. Ici, les groupes de transfert sont admis : la comparaison entre deux méthodes subit le même biais de références.
  - **OBJ-C3** : la médiane de S_A aux centres dépasse le **75e centile** de S_A aux milieux des paires de plus proches voisins (définition de 3.3 b), sur `bv_b_train` **et** sur `vols_100_022x`. Le taux de double comptage reste ≤ 0,15.
  - **OBJ-C4** : les prédictions sont enregistrées (§ 8.7) et ne bloquent pas l'envoi. Elles sont confrontées aux mesures dans l'E-NNN. Si la corrélation (c) dépasse 0,5 en valeur absolue avec A′, l'envoi reste permis, mais la normalisation photométrique devient obligatoire au cycle 2.
  - **OBJ-C5 à OBJ-C7** : non applicables au cycle 1 (B, B′ et B″ ne sont pas envoyés). Les conditions d'entrée de B′ et B″ dans un cycle sont celles proposées par scientific-challenger, avec l'intervalle défini ci-dessus.
  - **OBJ-C8** : le point de fonctionnement est le seuil choisi par `math_evaluer.py` (meilleur F1 cumulé sur `dev_reglage`). La méthode fournit toutes ses détections, avec le score z, et laisse l'évaluateur fixer le seuil. La lecture à budget égal est la condition 5 (3.2).
  - **Rotation (OBJ-V6, § 8.6.3)** : acceptée. Le F1 des détections calculées sur l'image tournée de 90°, évaluées contre les centres non tournés, est ≤ le F1 du niveau nul de demi-maille sur `dev_reglage`.
- **Ordre** : les conditions 8.6.1 à 8.6.4 et OBJ-C1 sont toutes vérifiées sur le développement avant l'envoi. Si une seule échoue, rien n'est envoyé et rien n'est consommé.

## 4. Amendement 2 (7 novembre 2026) — règle de rotation (C-002, question 3), en vigueur avant toute mesure du cycle 2

### 4.1 Ce qui est connu au moment d'écrire

- [M, E-006] Sur `bv_session_a` (sans pépinière), A′ obtient un F1 de 0,541 sur l'image d'origine et de 0,349 sur l'image tournée de 90°, centres non tournés. Pour comparaison, le nul de demi-maille vaut 0,109 et le nul de végétation uniforme 0,331.
- La règle 3.3 (« F1 tourné ≤ nul de demi-maille ») a été écrite avant E-006. A′ y a échoué. **Ce résultat reste acquis** : l'amendement ci-dessous vaut pour le cycle 2 et les suivants, sans effet rétroactif. A′ n'est pas envoyé au titre du cycle 1 ; il a d'ailleurs échoué aussi à la condition « centres contre milieux » sur vols.
- Cet amendement est écrit après avoir vu le chiffre de rotation de A′. Il ne sert donc pas à juger A′ tel quel. Une variante du cycle 2 qui ne différerait de A′ que par cette règle n'aurait pas le droit d'être envoyée sans une autre modification pré-enregistrée.

### 4.2 Pourquoi la règle 3.3 est mal posée

- Le contrôle de rotation (OBJ-V6) répond à une question précise : une fois les plants rompus, la méthode garde-t-elle une information sur la position des centres, venue par exemple des rangs ou de la seule végétation ? Sur l'image tournée, une méthode sans aucune information de plant place encore ses détections dans le feuillage. Son niveau attendu est donc celui des **points uniformes dans la végétation**, pas celui de la demi-maille.
- Le nul de demi-maille est construit pour tomber juste au-delà de 1 m de chaque centre (a/2 vaut 1,04 à 1,26 m). Il est donc **anti-corrélé** aux centres, et plus bas que le hasard. Exiger d'une image tournée qu'elle tombe sous la demi-maille revient à exiger qu'elle évite les centres, ce qu'aucune méthode sans information ne fait. La demi-maille reste le bon nul pour l'image **non tournée** (HF-01 : dans le feuillage, mais pas au centre). Elle n'est pas le bon nul pour l'image tournée.
- Le F1 au seuil de fonctionnement dépend du nombre de détections, alors que les nuls ont exactement N_réf points. La comparaison doit donc se faire **au même budget**.

### 4.3 Règle retenue (à partir du cycle 2)

Mesure sur `dev_reglage`, réduit à `bv_session_a` sans pépinière tant que `bv_b_train` est réservé, avec `math_evaluer.py` : F1 au budget k = N_réf (`courbe_budget_*.csv`, multiple 1,0), classement global des scores. Notations :
- F1_orig : méthode sur l'image d'origine ;
- F1_rot : méthode sur l'image tournée de 90° autour de son centre, détections ramenées dans le repère de l'image d'origine sans tourner les centres, région comptée inchangée ;
- F1_veg : nul de végétation uniforme (`out/comptage_math/evaluation/niveaux_nuls/vegetation_uniforme.csv`, N_réf points).

La condition de rotation est **remplie** si les deux points suivants sont vrais :
1. **Pas d'information résiduelle notable** : F1_rot − F1_veg ≤ 0,05 (estimation ponctuelle, au budget N_réf).
2. **L'essentiel du signal vient des plants** : F1_rot − F1_veg ≤ 0,25 × (F1_orig − F1_veg). Au plus un quart de l'excès de la méthode sur le nul de végétation survit à la rotation.

Rapportés sans servir à décider :
- l'intervalle bootstrap par photo (2 000 tirages, graine 2026) de F1_rot − F1_veg ;
- le F1_rot au seuil de fonctionnement.

### 4.4 Pourquoi ces deux bornes

- La borne absolue de 0,05 correspond à la largeur typique de l'intervalle à 95 % d'un F1 sur un groupe de développement : ±0,01 sur `dev_reglage`, ±0,03 à 0,04 sur des groupes plus petits (E-001). Un écart sous 0,05 n'est pas distinguable du nul à l'échelle d'un groupe.
- La borne relative empêche une méthode faible de passer seulement parce que son excès est petit dans les deux cas.
- Ce que je n'ai pas retenu :
  - un test « non significativement au-dessus du nul » : l'absence de preuve n'est pas une preuve, et un grand bootstrap rendrait la règle plus dure sans raison ;
  - la demi-maille comme nul de rotation : voir 4.2.

## 5. Projet d'amendement « validation dense v2 » (7 novembre 2026) — **PROJET, en attente de la décision de Corentin**

### 5.0 Constat

- [O] `docs/recherche/conventions_comptage.md` § 5 : les références de `val_iter` couvrent environ 48 % des plants. 36 photos sur 42 sont incomplètes ; seules DJI_0905, 0906, 0910, 0912, 0924 et 0930 sont conformes.
- Le F1 de 0,719 du v5 sur `val_iter` (E-001) **n'est pas un critère valable**. Il reste consigné tel quel dans les notes, avec cette réserve.
- Aucune variante n'a encore été mesurée sur `val_iter` : le compteur de variantes est à 0 sur 8.

Rien n'est mesuré sur `bv_b_train`, ni sur `val_scellee`, pour préparer ce projet. Seules des métadonnées ont été lues : les numéros de photos de `decoupage.csv` et les groupes de recouvrement de `out/analyse_banavista/groupes_photos.json`.

### 5.1 Ce que l'on sait déjà de `bv_b_train` (à déclarer : ce n'est pas un jeu vierge)

- Le v5 a été **entraîné** dessus, ce qui l'avantage. La comparaison est donc prudente pour une méthode explicite.
- Dans E-001, j'ai mesuré et rapporté le v5 et la baseline sur `bv_b_train` **en agrégé** : v5 F1 0,827, baseline 0,546. **La baseline d'E-001 a été réglée sur `dev_reglage`, qui contenait `bv_b_train`.** Dans les deux options, elle doit donc être **réglée de nouveau sur `bv_session_a` sans pépinière seul**, avec la même grille, avant toute mesure sur la nouvelle validation.
- leaf-mathematician en a vu 4 lignes d'`images_dense.csv` et la maille médiane (2,24 m). annotation-manager en a calculé la complétude (ratio médian 1,12, aucune photo suspecte). Aucune méthode explicite n'y a été lancée (E-006 l'a exclu par assertion).

### 5.2 Structure de `bv_b_train` (métadonnées seules)

- 71 photos, de DJI_0757 à 0841. Il manque 758 à 766, 775 à 777, 785 et 786 (écartées par le découpage v5).
- Groupes de recouvrement [O, `groupes_photos.json`] : 757 ; 767 à 774 ; 778 ; 779 à 784 ; 787 à 799 ; 800 à 820 (ligne complète de 21 photos) ; 821 à 841 (ligne complète de 21 photos).
- Les coupures de 757 à 799 tombent sur les numéros manquants. On ne sait pas si ces photos forment une ou deux lignes.
- La ligne 821 à 841 touche la bande tampon (842 à 861), qui touche L1 de `val_scellee`. Il n'y a pas de contact direct avec `val_scellee`.

### 5.3 Option 1a — `bv_b_train` coupé en deux (proposition du chef d'orchestre)

- **Moitiés contiguës** : T1 = DJI_0757 à 0799 (29 photos, lignes partielles) et T2 = DJI_0800 à 0841 (42 photos, 2 lignes complètes). Une seule frontière (799/800) touche les deux moitiés.
- **Tirage** : `numpy.random.default_rng(2026).integers(0, 2)` vaut 1. **`val_iter_v2` = T2 (0800 à 0841) ; `val_scellee_v2` = T1 (0757 à 0799).** Le tirage est fait ; il ne dépend d'aucune mesure.
- **Blocs du bootstrap** : 7 photos consécutives dans la liste triée des photos présentes.
  - T2 : 6 blocs (800 à 806, 807 à 813, 814 à 820, 821 à 827, 828 à 834, 835 à 841).
  - T1 : 4 blocs (757 et 767 à 772 ; 773 à 782 ; 783 à 791 ; 792 à 799, soit 7, 7, 7 et 8 photos).
- **Complétude, règle déclarée avant** : une photo de `bv_b_train` est retirée si son ratio références / attendu ExG est inférieur à 0,83 (10e centile de `dev_reglage`, § 5.2 des conventions). Les métriques de § 5.1 des conventions sont calculées par annotation-manager, sur les références seules, sans aucune détection. La liste des photos retirées est écrite ici avant toute mesure. Si plus d'un quart des photos d'une moitié est retiré, l'option 1a est abandonnée.
- **Faiblesses** :
  - les deux moitiés sont des données d'entraînement du v5 ;
  - l'agrégat du v5 sur l'ensemble de `bv_b_train` (0,827) est connu, donc la moitié scellée n'est pas tout à fait vierge **pour le v5**. Elle l'est pour les méthodes ;
  - avec 4 blocs, la confirmation sur T1 a peu de puissance.

### 5.4 Option 1b — `bv_b_train` entier pour les cycles, `val_scellee` (L1-L2 de `bv_b_val`) gardée pour la confirmation (**ma recommandation**)

- **`val_iter_v2` = `bv_b_train` entier**, filtré par la même règle de complétude qu'en 5.3 : 71 photos, 10 blocs de 7 photos consécutives (le dernier en compte 8).
- **`val_scellee` reste la confirmation**, à condition de passer le contrôle de complétude de la section 6. On n'y mesure alors que les photos conformes, dont la liste est fixée avant toute détection.
- **Pour** :
  - la confirmation se fait sur des photos que le v5 n'a jamais vues à l'entraînement, et que personne n'a mesurées ;
  - les cycles disposent de deux fois plus de photos qu'en 1a ;
  - une seule complétude reste à contrôler.
- **Contre** :
  - `val_scellee` vient de la même mission que `val_iter`, dont les références sont mauvaises. Le risque est réel, et la section 6 le contrôle ;
  - si `val_scellee` échoue au contrôle, on revient à 1a.

### 5.5 Option 2 — `val_iter` réduit aux 6 photos conformes

- `val_iter_v2` = DJI_0905, 0906, 0910, 0912, 0924, 0930. Elles se répartissent en 4 blocs (L3B1 : 0905, 0906, 0910 ; L3B2 : 0912 ; L3B3 : 0924 ; L4B1 : 0930).
- La sélection a été faite sur les seules références, sans détection : elle ne favorise aucune méthode. Mais la sélection d'après la complétude peut retenir des photos plus faciles (plus nettes, moins denses).
- **Je la déconseille.** Il y a 6 photos, de l'ordre de quelques centaines de plants [H], 4 blocs, et les photos 0905 et 0906 se recouvrent. Avec α = 0,05/8, la borne basse se réduit à peu près au pire bloc : le critère deviendrait presque impossible à atteindre ou, à l'inverse, dépendrait d'une seule photo.

### 5.6 Adaptation du critère de victoire (sections 2 et 3) selon l'option retenue

- **Inchangé** : métrique (mères seules, 1 m) ; seuil figé sur le développement ; v5 au seuil 0,30 ; conditions 1 à 5 de la section 2.4 et de l'amendement 3.2 ; plafond de 8 variantes avec α = 0,05/8 ; une seule confirmation, unilatérale à 95 %.
- **Développement de réglage** : `bv_session_a` sans pépinière seul, dans les trois options, puisque `bv_b_train` sort du développement en 1a et 1b. Les groupes de transfert restent rapportés.
- **Baseline** : réglée de nouveau sur `bv_session_a` seul (5.1), puis mesurée sur `val_iter_v2`. Ce sera une nouvelle entrée de référence (E-NNN), avec le v5 mesuré au même moment.
- **Bootstrap** : blocs de 7 photos consécutives. Si un ensemble compte moins de 6 blocs, la condition sur la borne basse est remplacée par un **test de signe sur les blocs** : tous les blocs doivent avoir une différence positive. Un bootstrap sur 4 unités est trop grossier pour un percentile à 5 % ou à 0,6 %.
- **Lecture** : en 1a et 1b, le v5 est mesuré sur ses données d'entraînement pendant les cycles. Battre le v5 sur `val_iter_v2` est donc un signal fort. Ne pas le battre n'est pas une réfutation : seule la confirmation tranche.
- **Variantes déjà consommées** : aucune. Le compteur repart de 0 sur `val_iter_v2`, puisque `val_iter` n'a reçu aucune variante.

## 6. Contrôle de complétude de `val_scellee` (7 novembre 2026, règle écrite avant tout calcul) — à faire **dans les trois options**

**Réponse** : oui, il faut contrôler. Les références de L3-L4 manquent à environ 50 %, et L1-L2 vient de la même mission, avec les mêmes annotateurs. Si L1-L2 ont le même défaut, une confirmation y mesurerait surtout la complétude. Le contrôle ne lit aucune détection : il ne révèle rien de la performance d'une méthode. La section 1.4 (« aucune image ») est assouplie pour ce seul calcul, fait par annotation-manager.

- **Qui et quoi** : annotation-manager, avec son script `completude_val_iter.py` étendu au rôle `val_scellee` par une option explicite. Le script lit les références dans la région comptée et les pixels des images préparées, uniquement pour l'attendu ExG. **Aucune détection d'aucune méthode, ni du v5.** Aucune planche ni aucune image n'est transmise aux équipes qui construisent la méthode. Le zoom visuel, s'il en faut un, est examiné par annotation-manager et par le chef d'orchestre seulement.
- **Sortie autorisée** : une ligne par photo, avec photo, ratio, densité et verdict (conforme ou incomplète), dans `out/comptage_math/annotation-manager/completude_val_scellee.csv`, plus le verdict global. Aucun autre chiffre.
- **Règles**, mêmes seuils que le § 5.1 des conventions, figés sur `dev_reglage` :
  - **photo conforme** si ratio ≥ 0,83 (10e centile de `dev_reglage`) et si sa fraction de trous ne dépasse pas le 90e centile de `dev_reglage` ;
  - **`val_scellee` utilisable** pour la confirmation si au moins 28 photos sur 42 (deux tiers) sont conformes **et** si le ratio médian est ≥ 0,89 (0,8 × 1,11) ;
  - dans ce cas, la confirmation ne porte **que sur les photos conformes**. Leur liste est écrite ici avant toute détection. Les blocs de 7 photos sont gardés, et un bloc sans photo conforme est retiré ;
  - **sinon**, `val_scellee` est déclarée non utilisable pour la confirmation, et c'est consigné. On applique l'option 1a, avec T1 scellée.
- **Ordre** : ce contrôle se fait avant la décision finale entre 1a et 1b, et avant tout cycle 2 sur une validation.

## 7. Critères des témoins T1 à T9 (E-015 et suivants), écrits le 7 novembre 2026 avant toute mesure de ces témoins

Contexte : D-007 et l'audit de scientific-challenger (section « Audit cycles 1-4 », D). La candidate est le vote B′ seul, figé dans sa configuration d'E-008/E-010. Tous les témoins se mesurent sur `bv_session_a` sans pépinière (rôle `dev_reglage`, groupe `bv_session_a`), avec `dev_transfert` en lecture. **Aucun ne touche `bv_b_train`, `bv_b_val` ni le test, et aucun ne consomme de variante.** Un témoin « bloquant » qui échoue interdit l'envoi.

### 7.0 Unité du bootstrap sur le développement

- [O] Toutes les expériences depuis E-006 (E-006, E-008, E-010, E-012, E-013, d'après leurs scripts) tirent leurs unités de `me.charger_liste()`, donc de la colonne `unite` d'`images_dense.csv`. Pour `bv_session_a`, cette colonne vaut la **photo d'origine** (64 unités pour 359 tuiles), et non la tuile. Les intervalles déjà publiés sont donc bien par photo.
- **Mais** deux photos consécutives de `bv_session_a` se recouvrent d'environ 80 % (`groupes_photos.json`), et un bootstrap par photo reste trop optimiste. **À partir d'E-015, toute décision sur le développement utilise des blocs** de 7 photos consécutives : on trie les 64 photos gardées par numéro DJI et on les coupe en tranches de 7 (9 blocs, le dernier de 8). L'intervalle par photo est rapporté à côté, pour information.

### 7.1 Critères

| N° | Mesuré par | Critère, écrit avant | Effet |
| --- | --- | --- | --- |
| T1 | vegetation-color-engineer | Rejet dur des candidats avec d3 > 0,1, puis seuil du vote re-choisi. Si F1(T1) ≥ F1(E-013) − 0,005, « vote + d̃3 » n'a aucun avantage sur la règle simple. | Conditionne seulement la réintroduction de vote + d̃3 (D-007) |
| T2 | convergence-engineer | Vote sur l'ExG au lieu de la luminance, même configuration, seuil re-choisi. Si F1(ExG) ≥ F1(lum) − 0,02, l'ExG remplace la luminance : c'est une seule variante déclarée, et la candidate reste unique. Si F1(ExG) < 0,55, la dépendance à l'éclairage est déclarée dans le rapport d'envoi. | Choix du canal ; pas bloquant |
| **T3** | independent-evaluator | Baseline ExG + maxima **réglée de nouveau sur `bv_session_a` seul** : grille σ ∈ {0,15 ; 0,2 ; 0,25 ; 0,3 ; 0,35 ; 0,5 ; 0,75 ; 1,0 ; 1,25 ; 1,5} m × distance ∈ {0,8 ; 1,0 ; 1,25 ; 1,5 ; 2,0 ; 2,5 ; 3,0 ; 3,5 ; 4,0} m, soit 90 couples, chacun avec son seuil choisi parmi 200 quantiles, comme pour le vote. Différence appariée F1(vote) − F1(T3), chacun à son seuil choisi sur `bv_session_a`. **Condition : borne basse de l'IC bilatéral à 95 % > 0 par blocs de photos.** | **Bloquant** |
| T4 | vegetation-color-engineer | d3 appliqué à la baseline T3 et à A-iso, même w, seuil re-choisi. Si le gain sur T3 ≥ le gain sur le vote, d3 est un post-filtre générique. | Interprétation ; pas bloquant |
| **T5** | independent-evaluator | Courbe rappel-budget, F1 à k = N_réf et erreur de comptage au seuil, pour le vote, la baseline T3 et A′. **Condition : F1(vote) − F1(T3) à k = N_réf, borne basse de l'IC à 95 % par blocs > 0.** Rapporté sans servir à décider : l'erreur de comptage relative (le bulletin la note). Pour vote + d̃3 (E-013), le gain sur le vote à k = N_réf doit exclure 0 par blocs, faute de quoi le gain d'E-013 est un effet de point de fonctionnement. | **Bloquant** (vote contre T3) |
| **T6** | independent-evaluator | Validation croisée par blocs : 4 plis de photos consécutives (photos triées par numéro, 16 par pli). Pour chaque pli, le seuil du vote et celui de T3 (couple σ et distance figé par T3) sont choisis sur les 3 autres plis, puis mesurés sur le pli retiré. F1 hors pli = cumul des VP, FP et FN sur les 4 plis retirés ; la moyenne des 4 F1 de pli est rapportée aussi. Optimisme = F1 au seuil choisi sur tout `bv_session_a` − F1 hors pli. **Conditions : (i) F1 hors pli du vote > F1 hors pli de T3 ; (ii) si l'optimisme du vote dépasse 0,02, tous les chiffres du vote sur le développement sont rapportés avec cette décote.** Limite : seuls les seuils sont re-choisis par pli ; r_max, p et R_nms ont été choisis sur tout `bv_session_a`. | (i) bloquant ; (ii) rapporté |
| T7 | convergence-engineer ou independent-evaluator | F1 du vote et du v5 par tranche d'échelle de tuile (3,6 à 4,5 ; 4,5 à 5,5 ; 5,5 à 6,7 cm/px), au seuil figé. Le F1 de la tranche 4,5 à 5,5 est rapporté comme prédiction pour une validation à 5 cm/px. | Rapporté |
| T8 | même | Mêmes mesures en excluant une bande de r_max = 1,6 m le long du bord réel de chaque tuile (bords 0 et 512 px, pas les frontières de zone propre), pour toutes les méthodes, v5 compris. | Rapporté |
| **T9** | même | Corrélation de Pearson, par photo, entre le rapport détections / références du vote (au seuil figé) et la luminance médiane de la photo, sur les 64 photos. **Si \|r\| > 0,5, un seuil normalisé par photo est pré-enregistré avant l'envoi.** | Bloquant tant que cette normalisation n'est pas écrite |
| T10 | Corentin | Déclaration ou retrait de DJI_0800 et DJI_0804 (E-003) de `val_iter_v2` en option 1b. | Sans calcul ; avant tout cycle sur `bv_b_train` |

- **Envoi de la candidate** : T3, T5 (vote contre T3), T6 (i) et T9 passent, et toutes les conditions de la section 3.3 et de l'amendement 2 restent remplies (elles le sont d'après E-010). L'envoi attend en outre la décision de Corentin sur la validation dense (section 5) et le contrôle de complétude (section 6).

## 8. Confirmation sur `val_scellee` (D-012), écrit le 7 novembre 2026, **avant toute détection sur `val_scellee`**

Mesure E-020, décidée par Corentin (D-012). Au moment d'écrire, aucune méthode, ni le v5, ni la baseline n'a été lancée sur `val_scellee`. independent-evaluator n'a lu aucune de ses références. Seules des métadonnées ont été lues : `decoupage_bv_b_val.csv` (§ 1.3) et `completude_val_scellee.csv` (§ 6, calculé par annotation-manager sur les références et l'ExG seulement). Cette section n'est pas réécrite après la mesure ; le résultat sera une section 9, datée.

### 8.1 Ordre

1. Ce § 8 et le script de mesure sont commités, avec l'accord explicite de Corentin (D-012, étape 2).
2. independent-evaluator, et lui seul, lance **une fois** `--mesure E-020`. Le script crée `out/comptage_math/evaluation/E-020/VERROU` avant toute détection et refuse de repartir si ce fichier existe.
3. Le résultat est écrit tel quel (§ 9), avec les trois méthodes côte à côte. Aucun réglage ne suit.

### 8.2 Photos mesurées : les 40 photos conformes, en 6 blocs

[O] `out/comptage_math/annotation-manager/completude_val_scellee.csv` (SHA-256 `e8007a8baf3178e189aa2a07225a5f1bc8e142972d8414172fa5f1da2e596882`) : 40 photos conformes sur 42, ratio médian 1,07, verdict « utilisable » (règle du § 6). **Retirées : DJI_0867 (ratio 0,72) et DJI_0903 (0,69).**

| Bloc (§ 1.2) | Photos conformes mesurées | Nombre |
| --- | --- | --- |
| L1B1 | DJI_0862, 0863, 0864, 0865, 0866, 0868 | 6 |
| L1B2 | DJI_0869, 0870, 0871, 0872, 0873, 0874, 0875 | 7 |
| L1B3 | DJI_0876, 0877, 0878, 0879, 0880, 0881, 0882 | 7 |
| L2B1 | DJI_0883, 0884, 0885, 0886, 0887, 0888, 0889 | 7 |
| L2B2 | DJI_0890, 0891, 0892, 0893, 0894, 0895, 0896 | 7 |
| L2B3 | DJI_0897, 0898, 0899, 0900, 0901, 0902 | 6 |

- Aucun bloc n'est vide. Avec **6 blocs**, le bootstrap par blocs s'applique ; le test de signe du § 5.6 (moins de 6 blocs) ne s'applique pas.
- Image préparée et SHA-256 de chaque photo : `out/comptage_math/evaluation/decoupage_bv_b_val.csv` (SHA-256 `7aafb1fe8fd936421ad76373551d822ca2de7fc86b2881039cc0415e3dc0e741`, inchangé depuis le § 1.3). Le script vérifie l'empreinte de chacune des 40 images avant de la lire.
- Région comptée, résolution (5 cm/px) et unité de bootstrap (colonne `bloc`) : `math_evaluer.construire_liste(avec_scellee=True)`, restreinte à ces 40 photos. Les deux photos retirées ne sont ni détectées ni évaluées.

### 8.3 Méthodes figées

| Méthode | Configuration | Seuil | Origine du réglage |
| --- | --- | --- | --- |
| **Candidate : vote B′** | E-010 : canal luminance, σ_t 0,10 m (une échelle), r_max 1,6 m, p = 1,0, R_nms 1,0 m, candidats z ≥ 0,5 ; `VT.carte_votes_multi` puis `e008_votes.detecter`, comme la passe 2 d'E-010 | **z ≥ 2,2381955265998843** (`bilan_E-010.json`, `choix.seuil_z`) | `bv_session_a` sans pépinière (E-010) ; T2 (E-016) maintient la luminance |
| **v5** | `modeles/centres_5cm_v5.onnx` via `fieldscan.drone.DetecteurCentres`, `seuil_min` 0,05, image à 5 cm/px (aucun rééchantillonnage), mêmes appels que `v5_detecter.py` (E-001) | **0,30** (officiel) | protocole v5 |
| **Baseline T3** | ExG + lissage gaussien normalisé + maxima, `baseline.detecter_image`, **σ 0,35 m, distance 1,25 m** | **0,16876235716044902** (`bilan_E-015.json`, `T3_choix`) | `bv_session_a` sans pépinière (E-015) |

Format des détections : `image_path,x,y,score`, en pixels de l'image préparée.
- Vote et v5 : x et y à 2 décimales, score à 5 décimales, comme les fichiers d'E-010 et d'E-001.
- Baseline : score en pleine précision, comme les détections sur lesquelles E-015 a choisi son seuil.

### 8.4 Commande unique et empreintes SHA-256

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/evaluation/e020_val_scellee.py --mesure E-020
```

- **Sorties.** Le script produit `out/comptage_math/evaluation/E-020/detections_vote_B_prime.csv`, `detections_v5.csv` et `detections_baseline_T3.csv`, puis le bilan `E-020/bilan_E-020.json`.
- **Évaluation.** Chaque fichier passe par `math_evaluer.evaluer`, importé sans modification : mères seules, 1 m, disque de 2 000 px. Options : `--seuil-fixe`, `--roles val_scellee`, `--ouvrir-scellee E-020`, `--m-comparaisons 1`.
- **Pourquoi un script de lancement**, et non `v5_detecter.py` et `baseline.py` tels quels : ces deux scripts lisent `images_dense.csv`, qui ne contient pas `val_scellee` par construction (§ 1.4). Le script reprend les mêmes appels : `DetecteurCentres.predire`, `baseline.detecter_image`, `VT.carte_votes_multi` et `E8.detecter`.
- Le script refuse de mesurer si une seule des empreintes ci-dessous diffère.

| Fichier | SHA-256 |
| --- | --- |
| `out/comptage_math/evaluation/e020_val_scellee.py` (script de mesure) | `05536ad3a0bc0d3f885aa27195de07cbaddac194c2bc4c7542bcc740bd6ccc17` |
| `comptage_math/votes.py` | `eff3fb21f6782f73b14eb7309613c1666144b7cacec0f4e114c14d8a05d76625` |
| `comptage_math/orientation.py` | `e3343982eea20c7f8dcc4db34ab30f366fdb56eac0bb808324e9f728e7f356be` |
| `comptage_math/feuille.py` (importé par `e008_votes.py`) | `e01989cb1f9820940106e945e32c319cddde7246d8668c3155a3503b5f981bf3` |
| `out/comptage_math/convergence-engineer/e008_votes.py` (`lire`, `detecter`, `ecrire_csv`) | `133b4aceeeb3c0dd7b8837527ea7f26ad288a8116b0a0a3f2c5e7ee2242a5b27` |
| `out/comptage_math/convergence-engineer/e010_extension.py` (lancement d'E-010) | `212b8a56d76816dfaf92b18f40d69f92c379ead463985ae89ada582011fbb614` |
| `out/comptage_math/convergence-engineer/E-010/bilan_E-010.json` (configuration et seuil du vote) | `0e60267e27a0c0043165d3aa19f417b5ac1c86033f0a97c57c9a1556f34244bb` |
| `out/comptage_math/evaluation/baseline.py` | `f58f03e2b509b42ecc018d708ea5a5b5e1d44a8574912acf5d09a14758e49bae` |
| `out/comptage_math/evaluation/E-015/bilan_E-015.json` (paramètres et seuil de T3) | `965600d6ff5c4e5b53e606fad3d595213d83cf8827aedec00432a312c414c2f8` |
| `out/comptage_math/evaluation/v5_detecter.py` (E-001) | `ba76a523da4e32e99fed74a6164189f71a4d7f76a9033bdf784d5c6e95308b9a` |
| `modeles/centres_5cm_v5.onnx` | `12f9b4caa5735767c454de99edf1a6616765718243555f8559c2cfcc0722f1ea` |
| `modeles/centres_5cm_v5.json` (seuil 0,30, normalisation) | `47246578af1f00bf52cf4816cc78f531b5d83d9781db8d78123c37217e76dd2a` |
| `fieldscan/drone.py` (`DetecteurCentres`, non modifié depuis le dernier commit) | `7e3e951cb590c2469d3fc63bf6a71fb18a3b7c6504bc4e246491598ab0940b9c` |
| `scripts/math_evaluer.py` (identique à E-001) | `934585b1eae50751b6b961bc6cae46455a45d3dfe47547c69b490049b3a99260` |
| `scripts/evaluer_comptage.py` (`apparier`) | `6a13441d7be7233b5773d76cb94ebaf474090e2a29acb17864d72f60f3470ff6` |
| `out/comptage_math/evaluation/decoupage_bv_b_val.csv` | `7aafb1fe8fd936421ad76373551d822ca2de7fc86b2881039cc0415e3dc0e741` |
| `out/comptage_math/annotation-manager/completude_val_scellee.csv` | `e8007a8baf3178e189aa2a07225a5f1bc8e142972d8414172fa5f1da2e596882` |

[O] `comptage_math/votes.py` a changé depuis E-010 (`993bff46…` dans `bilan_E-010.json`) : E-014 et E-016 y ont ajouté des options (`masque="couleur"`, `canal="exg"`). Avec les valeurs par défaut, celles du vote figé, les détections restent les mêmes : voir l'essai à blanc (8.5).

### 8.5 Essai à blanc (7 novembre 2026), sans rien lire de `val_scellee`

- **Commande** : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/evaluation/e020_val_scellee.py --essai-a-blanc`. Sorties dans `out/comptage_math/evaluation/E-020_essai/` (`bilan_essai.json`, journal).
- **Tuiles** : `bv_bv_session_a_0000_0.jpg` et `bv_bv_session_a_0001_0.jpg`, du développement, issues de deux photos d'origine.
  - La liste vient d'`images_dense.csv`, qui ne contient pas `val_scellee`.
  - Les tuiles reçoivent en mémoire le rôle `val_scellee`. Elles passent ainsi par le même chemin d'évaluation que la mesure : bootstrap de 10 000 tirages, comparaison appariée, verdict (ici dans la branche du test de signe, puisqu'il n'y a que 2 blocs).
- [O] **Reproduction exacte des détections figées** sur ces deux tuiles :
  - vote : 177 détections sur 177 contre `E-010/detections/vote_e010.csv`, écart nul ;
  - v5 : 155 sur 155 contre `v5/detections_val_iter_dev.csv` (E-001), écart nul ;
  - baseline : 171 sur 171 contre `E-015/T3_detections_baseline_bv_session_a.csv`, écart nul.
- Toute la chaîne tourne sans erreur : détections, cinq évaluations, F1 au budget, différences par bloc, verdict. Le refus d'un identifiant autre que `E-020` est vérifié. Les chiffres de l'essai portent sur 57 mères et ne valent rien comme mesure.

### 8.6 Critère (§ 2.5, avec § 3.2)

Mesure : F1 **mères seules**, appariement un à un à 1 m, disque de 2 000 px, cumulé sur les 40 photos. Bootstrap par blocs : 6 blocs, 10 000 tirages, graine 2026, mêmes tirages pour les deux méthodes comparées.

- **« Le vote B′ bat le v5 en dense (validation) »** si les trois conditions suivantes sont remplies :
  1. F1(vote) > F1(v5 à 0,30) ;
  2. la borne basse unilatérale à 95 % (5e centile) de la différence appariée F1(vote) − F1(v5) est > 0 ;
  3. au budget k = N_réf (classement global des scores), F1(vote) ≥ F1(v5), en estimation ponctuelle (§ 3.2).
- Si 1 et 2 sont remplies sans 3, ou si 3 l'est seule : **« non concluant »** (§ 3.2). Si aucune ne l'est : **« non confirmé »**.
- Un seul test principal, donc pas de correction.
- **Contre la baseline T3** : même règle, **rapportée** à côté. Elle ne change pas le verdict principal.
- **Rapportés sans servir à décider** : précision, rappel, erreur de comptage relative, IC à 95 % de chaque F1 et de chaque différence, différence par bloc, taux de double comptage, courbe rappel-budget, baseline contre v5.
- **Portée** : la lecture vaut pour cette ferme seulement (§ 1.3), qui vient de la même mission que l'entraînement du v5. Le seuil du v5 a été choisi en partie sur une moyenne qui inclut `bv_b_val` : avantage au v5, assumé.

### 8.7 Prédictions d'independent-evaluator, notées [H], écrites avant la mesure

**Appuis** :
- E-015 : vote 0,637 et T3 0,567 sur `bv_session_a`, optimisme du seuil 0,005 ;
- E-016 : T7, vote de 0,625 à 0,662 selon l'échelle, sans perte à 5 cm/px ; T8, vote 0,632, T3 0,577 et v5 0,830 ; prédiction de l'auteur, 0,64 ;
- dev_transfert : vote 0,546, T3 0,481 ;
- v5 : 0,824 sur `dev_reglage` (ses données d'entraînement), et 0,7767 « dense » sur tout `bv_b_val` dans `modeles/centres_5cm_v5.json` (protocole v5, autre code, avec la moitié `val_iter` aux références incomplètes) ;
- complétude de `val_scellee` proche de celle du développement (ratio médian 1,07) ;
- changement de session : la maille est plus grande sur `bv_b_val` (2,52 m contre 2,18 m). [H] Donc moins de fusions et un peu moins de doubles détections.

| Grandeur | Prédiction ponctuelle | Fourchette à 80 % |
| --- | --- | --- |
| F1 vote B′ (z ≥ 2,238) | 0,62 | 0,55 à 0,68 |
| F1 v5 (0,30) | 0,83 | 0,78 à 0,88 |
| F1 baseline T3 (0,1688) | 0,54 | 0,46 à 0,60 |
| Différence vote − v5 | −0,21 | −0,30 à −0,12 |
| Différence vote − baseline | +0,08 | +0,02 à +0,14 |
| Erreur de comptage du vote | 0 % | −15 % à +15 % |

- **Verdict principal attendu : « non confirmé »**, avec une probabilité d'environ 97 %. « Confirmé » : 2 % au plus, comme l'estimation de scientific-challenger (D-007).
- **Contre la baseline** : borne basse > 0 avec une probabilité d'environ 65 %.
- **Ce qui me surprendrait** : un vote au-dessus de 0,72 ou sous 0,50, ou un v5 sous 0,75. Dans ce cas, je chercherais d'abord une différence de références entre sessions, avant toute conclusion sur la méthode.

### 8.8 Si le critère n'est pas rempli

- **Phrase écrite telle quelle**, selon 8.6 :
  - « **Non confirmé** : sur `val_scellee` (40 photos conformes, 6 blocs), le vote B′ figé (E-010) ne bat pas le v5 au seuil 0,30. »
  - ou « **Non concluant** ».
  - Suivent les chiffres des trois méthodes, les IC et le verdict contre la baseline.
- **`val_scellee` est consommée.** Aucune variante du vote n'y sera plus mesurée. Une nouvelle confirmation demanderait un nouvel ensemble scellé, choisi par Corentin (§ 2.5). Les chiffres d'E-020 ne servent à régler aucun paramètre ni aucun seuil.
- **Erreur de code découverte après coup** : elle est corrigée et consignée. Les deux chiffres sont rapportés, et la mesure n'est pas relancée pour choisir.
