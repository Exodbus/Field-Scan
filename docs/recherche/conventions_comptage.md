# Conventions de comptage et références du développement dense

Rédacteur unique : annotation-manager (équipe DONNÉES). Dernière mise à jour : 7 novembre 2026.

## 1. Règle d'exclusion de la pépinière en pots (`bv_session_a`)

### 1.1 Constat de départ

- [S] `docs/protocole_comptage_v5.md`, section 1 et section 2 : banavista contient « des bananeraies denses et une pépinière en pots » ; la session A (DJI_0542 à 0682) mêle « bandes de plantation dense et pépinière en pots ».
- [S] D-004 (`docs/experiment-log.md`) : la liste des photos de pépinière est bloquante pour l'envoi de A′ ; la grille de A′ se règle sur le seul développement dense.
- Une pépinière en pots est hors domaine : plants de quelques dizaines de centimètres, alignés sur bâche ou sol nu, sans couronne jointive.

### 1.2 Critère écrit AVANT application (7 novembre 2026, aucune donnée de `bv_session_a` regardée avant cette écriture)

Unité de décision : la **photo d'origine** (DJI_XXXX), toutes ses tuiles préparées ensemble. Données : `data/drone/comptage_v5_5cm/objets.csv` (colonne `taille`, côté de boîte en pixels de la tuile préparée) et la résolution réelle `cm_par_px` de `out/comptage_math/evaluation/images_dense.csv`. Taille d'une boîte en mètres : `taille × cm_par_px / 100`. Toutes les boîtes de la tuile comptent (avant disque et zone propre), pour juger la photo entière.

- **C1, critère principal.** Une photo est exclue si la **médiane** de la taille de ses boîtes est **inférieure à 1,5 m**.
  Justification [S]/[H] : la préparation v5 ramène la couronne médiane à 3 m (règle des couronnes, protocole v5 § 3) ; un bananier de plantation dense a une couronne de 2,5 à 4 m, un plant en pot de pépinière moins de 1 m. 1,5 m est à mi-chemin, en échelle logarithmique, de ces deux ordres de grandeur.
- **C2, photo mixte.** Une photo non exclue par C1 est aussi exclue si **au moins 30 % de ses boîtes** mesurent moins de 1,5 m (une partie notable de la photo est de la pépinière ; on exclut la photo entière, voie prudente : pas de découpe à la main d'une zone).
- **C3, photo sans boîte.** Une photo de `bv_session_a` sans aucune boîte est signalée (ni gardée ni exclue en silence) : elle est gardée si elle ne déclenche aucun critère, avec la mention « 0 référence ».
- **Contrôle visuel, non décisionnel.** Une planche de vignettes (une tuile centrale par photo, à 5 cm/px) est produite dans `out/comptage_math/annotation-manager/`. Elle sert à vérifier que C1 et C2 trient bien pépinière et plantation. Si l'inspection contredit le critère sur une photo, la contradiction est écrite ci-dessous ; la règle n'est pas modifiée après coup sans une nouvelle version datée.

Aucun seuil n'a été réglé sur un score de détection : la règle ne dépend que des annotations existantes.

### 1.3 Application de la version 1 : critère réfuté par le contrôle visuel

- [O] `out/comptage_math/annotation-manager/pepiniere_photos.csv` : C1 n'exclut **aucune** photo (médiane des photos de 2,39 à 4,76 m) ; C2 exclut une seule photo, DJI_0604 (31 % de boîtes < 1,5 m) ; C3 : aucune photo sans boîte.
- [O] Planche `out/comptage_math/annotation-manager/planche_bv_session_a.png` (tuile centrale de chaque photo) : la pépinière en pots est bien visible (jeunes plants espacés sur sol nu, pots bleus, rangs bâchés), sur une quarantaine de photos de DJI_0566 à DJI_0642, **et ses boîtes sont plus grandes** (médiane 3,5 à 4,8 m) que celles de la plantation dense (2,4 à 3,4 m).
- Explication [H] : dans la pépinière, chaque plant isolé est encadré feuilles comprises ; en plantation jointive, la boîte couvre surtout le centre de la couronne. De plus l'échelle de `bv_session_a` est fixée par la couronne médiane du groupe entier (pépinière comprise), donc les tailles absolues ne disent pas « petit plant ». L'hypothèse de départ de C1 (pépinière = petites boîtes) est fausse.
- Conformément au § 1.2, la version 1 n'est pas retouchée : elle est remplacée par une version 2 datée, écrite ci-dessous **après** l'inspection visuelle (ce n'est donc pas une règle aveugle ; elle ne dépend d'aucun score de détection).

### 1.4 Version 2 de la règle (7 novembre 2026, écrite après la planche, avant son application)

Le trait qui distingue la pépinière de la plantation dense, sur la planche, est l'**espacement** : plants isolés sur sol nu contre couronnes jointives. Critère objectif, sur les annotations seules :

- **D1.** Densité de références dans la région comptée par `math_evaluer.py` (disque de 2 000 px et zones propres, toutes tuiles de la photo) : `n_ref / aire_m2`. Une photo est **exclue du développement dense si la densité est inférieure à 0,05 plant par m²**, soit une maille équivalente de plus de 4,5 m. Justification [S]/[H] : une plantation dense de bananiers est plantée à 2 à 3,5 m (0,08 à 0,25 plant/m²) ; au-delà de 4,5 m de maille équivalente, la photo n'est pas « dense », qu'il s'agisse de pépinière, de bordure, de route ou de friche.
- **D2.** C2 de la version 1 est maintenu (photo mixte exclue).
- **Contrôle.** La liste issue de D1/D2 est comparée à la liste visuelle (photos où la tuile centrale montre la pépinière) ; les désaccords sont écrits au § 4 sans changer la règle.

Les photos exclues par D1 qui ne sont pas de la pépinière (bordures herbeuses, friche) sortent elles aussi du développement dense : elles sont hors domaine « plantation dense » par la même raison d'espacement.

## 2. Convention « mère » pour le développement dense

- [O] Toutes les références du développement dense viennent de boîtes Roboflow (`Bananas` pour banavista, classes bananier des autres sources) converties en points au centre de boîte ; dans `objets.csv`, le type est `mere` pour toutes (comptes dans la section 4).
- Convention retenue : **chaque boîte = une mère**, point au centre de la boîte, appariement à 1 m, mères seules (`definir_types_certains(meres_seules=True)` dans `scripts/math_evaluer.py`).
- **Limite.** Les annotateurs Roboflow n'ont pas distingué mère et rejet. En plantation dense, un rejet haut annoté comme boîte séparée sera compté comme une mère ; un rejet non annoté et détecté devient un faux positif. Aucun point n'est `rejet` ou `incertain`, donc la règle « rejets et incertains ne comptent ni comme bons ni comme faux » ne s'applique jamais sur le dense : la précision mesurée y est une **borne basse** si les méthodes détectent des rejets, et le rappel mesure « boîtes Roboflow retrouvées », pas « mères retrouvées ». À noter dans tout rapport de score dense.

## 3. Format commun des références (`data/comptage_math/references/dev_dense.csv`)

Une ligne par point, colonnes :
`image_path, x, y, type, groupe, source, unite, photo, cm_par_px, cm_par_px_incertitude, taille_m, dans_region`

- `image_path`, `x`, `y` : tuile préparée de `data/drone/comptage_v5_5cm/images/` et centre de boîte en pixels de cette tuile (origine en haut à gauche), comme les détections attendues par `scripts/math_evaluer.py`.
- `dans_region` : vrai si le point est compté par `math_evaluer.py` (disque de 2 000 px pour banavista, zone propre de la tuile). Seuls les points `dans_region` entrent dans l'évaluation ; les autres sont gardés pour information.
- `cm_par_px` : résolution réelle de la tuile (copie d'`images_dense.csv`). `cm_par_px_incertitude` : écart relatif estimé de la règle des couronnes (voir section 4).
- Les tuiles des photos exclues (section 1) ne figurent pas dans le fichier ; la liste des tuiles gardées est dans `data/comptage_math/references/dev_dense_images.csv`.

## 4. Résultats (7 novembre 2026)

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/annotation-manager/references_dense.py` ; journal : `out/comptage_math/annotation-manager/journal_references_dense.txt`. Aucun score de détection calculé.

### 4.1 Photos exclues de `bv_session_a` (règle v2, D1 ; D2 n'ajoute rien)

[O] `out/comptage_math/annotation-manager/pepiniere_photos.csv` : **59 photos exclues sur 123, 64 gardées.** Séparation nette : densité des photos gardées ≥ 0,060 /m², des photos exclues ≤ 0,029 /m² (aucune photo entre les deux).

- **Pépinière en pots (55 photos)**, raison D1, confirmée par la planche : DJI_0566, 0570, 0572, 0573, 0575, 0577, 0578, 0583 à 0605 (23 photos), 0607 à 0611, 0613, 0616, 0617, 0621 à 0627, 0629, 0631, 0632, 0636 à 0642.
- **Hors plantation dense, pas pépinière (4 photos)**, raison D1 ; désaccord avec la liste visuelle de pépinière, sans effet sur la décision :
  - DJI_0542 (0,029 /m², route et bordure) ;
  - DJI_0579, DJI_0606, DJI_0634 (0,004 à 0,006 /m², bordure herbeuse, fossé, friche).
- DJI_0604, seule photo exclue par C2 en v1, est aussi exclue par D1.
- Photos gardées : DJI_0543 à 0557, 0564, 0565, 0567 à 0569, 0571, 0574, 0576, 0580 à 0582, 0612, 0614, 0615, 0618 à 0620, 0628, 0630, 0633, 0635, 0643 à 0661, 0666 à 0668, 0677 à 0682.
- [H] Limite : décision sur la photo entière ; une photo gardée peut contenir une bande de bordure (DJI_0543 à 0546 montrent route et bâtiments sur la tuile centrale). Effet attendu : quelques fausses détections sur la végétation non bananière, pas de référence perdue.

### 4.2 Références du développement dense

[O] `data/comptage_math/references/dev_dense.csv` : 58 075 points, dont **30 792 dans la région comptée** ; 994 unités (photos ou images d'origine), 1 849 tuiles (`dev_dense_images.csv`). Types : 100 % `mere` (61 135 boîtes du développement avant exclusion, aucune `rejet` ni `incertain`).

| Groupe | Points comptés | Unités | cm/px médian |
| --- | --- | --- | --- |
| bv_b_train | 9 471 | 71 | 4,60 |
| bv_session_a (sans pépinière) | 8 649 | 64 | 4,53 |
| lasuiza | 7 159 | 409 | 4,60 |
| vols_100_022x | 4 704 | 401 | 4,71 |
| corte | 809 | 49 | 4,75 |

- Échelle : règle des couronnes (couronne médiane = 3 m) par groupe d'échelle ([S] `data/drone/comptage_v5_5cm/parametres.json`). La colonne `cm_par_px_incertitude` ne contient que l'erreur-type statistique de la médiane (0,1 à 0,6 %). **L'incertitude dominante est systématique** : la convention « 3 m » elle-même [H], plusieurs dizaines de pour cent, non chiffrée ici. Après retrait de la pépinière, la taille médiane des boîtes de `bv_session_a` vaut 2,97 m au lieu de 3 m : l'échelle du groupe, calée pépinière comprise, n'est biaisée que d'environ 1 %.

### 4.3 Contrôle de complétude (sans annotation nouvelle)

Critère écrit dans le script avant le calcul : attendu = surface végétale (ExG > 0,05) dans la région comptée / 9 m² ; unité suspecte si références / attendu < 0,3 (et attendu ≥ 5). Fichier : `out/comptage_math/annotation-manager/completude_photos.csv`.

| Groupe | Unités | Ratio médian | Décile bas | Suspectes |
| --- | --- | --- | --- | --- |
| bv_b_train | 71 | 1,12 | 0,88 | 0 |
| bv_session_a | 64 | 1,10 | 0,77 | 0 |
| corte | 49 | 0,99 | 0,74 | 0 |
| vols_100_022x | 401 | 0,88 | 0,19 | 75 |
| lasuiza | 409 | 0,56 | 0,14 | 130 |

- Avant exclusion, les 9 photos suspectes de `bv_session_a` étaient toutes des photos de pépinière ou de bordure (DJI_0577, 0578, 0579, 0605, 0606, 0607, 0634, 0636, 0637) : contrôle cohérent avec la règle.
- **lasuiza et vols_100_022x** : un tiers et un cinquième des unités ont moins de 30 % des références attendues. [H] Deux causes possibles, non tranchées : annotations Roboflow incomplètes, ou végétation non bananière (adventices, autres cultures) dans les tuiles. À vérifier sur une planche de ces unités avant d'utiliser ces groupes pour régler un seuil ; en attendant, la précision mesurée sur eux est une borne basse.
- **Unités non indépendantes** [O] (`data/drone/decoupage_comptage_v5/decoupage.csv`) :
  - `lasuiza` : 409 unités pour 316 origines distinctes. Une même tuile d'orthomosaïque figure dans plusieurs parties Roboflow (exemple : `tile_0007_0007` présente en `test/` et en `train/` de l'export, sous deux noms `rf.`). Ce sont de **vrais doublons** : 93 images comptées deux fois ou plus dans le développement.
  - `vols_100_022x` : 401 unités pour 78 photos. Ce sont des **découpes de 480 px** d'une même photo, à des décalages différents (exemple : 100_0221_0146 découpée en `_480_2400`, `_2880_960`, etc.). Il n'y a pas de doublon, mais les découpes ne sont pas indépendantes.
  - Conséquence : le bootstrap par `unite` d'`images_dense.csv` est trop optimiste pour ces deux groupes. Il faudrait regrouper par photo (colonne `photo` de `dev_dense.csv`) et dédoublonner lasuiza par MD5. Signalé à independent-evaluator.

## 5. Complétude des références de `val_iter` (7 novembre 2026)

### 5.1 Contexte et critères écrits avant le calcul

- [S] E-001 (independent-evaluator) : sur `val_iter` (bv_b_val, lignes L3-L4, DJI_0904 à 0945), le v5 a 42 % de détections en plus par rapport aux références, contre 9 % de moins sur `dev_reglage`. Hypothèse à tester [H] : les références de L3-L4 sont incomplètes.
- Données : références `objets.csv` dans la région comptée de `math_evaluer.py` et pixels des images préparées. **Aucune détection lue**, ni du v5 ni d'une autre méthode. **`val_scellee` (L1-L2, DJI_0862 à 0903) n'est pas ouverte** : une assertion du script refuse toute image dont le rôle n'est pas `val_iter` ou `dev_reglage`.
- Comparaison : même calcul sur `dev_reglage` (`bv_session_a` sans pépinière + `bv_b_train`), par photo d'origine.
- Mesures par photo :
  1. **ratio** = références / (surface ExG > 0,05 dans la région / 9 m²) ; photo suspecte si ratio < 0,3 (même critère qu'au § 4.3) ;
  2. **densité** = références / m² de région ;
  3. **trous** : la région est quadrillée en cellules de 10 m × 10 m entièrement comprises dans la région. Un trou est une cellule où la végétation ExG couvre au moins 50 % et où il n'y a **aucune** référence. On mesure la fraction de cellules végétales qui sont des trous ;
  4. **espacement** : distance médiane au plus proche voisin entre références (m).
- Règle de verdict, écrite avant :
  - **incomplètes** si, sur `val_iter`, le ratio médian est inférieur à 0,8 × celui de `dev_reglage`, **ou** si la fraction de trous médiane dépasse le 90e centile des photos de `dev_reglage` ;
  - **complètes** si aucune des deux conditions n'est remplie et si aucune photo n'est suspecte ;
  - **douteuses** dans les autres cas, par exemple une ou deux photos isolées seulement.
  - Une photo est dite « incomplète » si sa fraction de trous dépasse le 90e centile de `dev_reglage` ou si son ratio est inférieur au 10e centile de `dev_reglage`.

### 5.2 Résultats

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/annotation-manager/completude_val_iter.py`. Journal : `out/comptage_math/annotation-manager/journal_completude_val_iter.txt`. Table : `completude_val_iter.csv`. Planches : `planche_val_iter.png` et `zoom_val_iter_0905_0909.png`. Aucune détection n'a été lue.

| Médiane par photo | dev_reglage (135 photos) | dont bv_b_train | val_iter (42 photos) |
| --- | --- | --- | --- |
| ratio références / attendu ExG | 1,11 (10e centile : 0,83) | 1,12 | **0,53** (L3 : 0,59 ; L4 : 0,51) |
| densité (références/m²) | 0,107 | 0,108 | **0,045** |
| couverture végétale ExG | 0,87 | | 0,78 |
| plus proche voisin (m) | 2,25 | 2,29 | 2,65 |
| fraction de trous de 10 m | 0 | | 0 |

- Condition 1 remplie [O] : le ratio médian de `val_iter` (0,53) est inférieur à 0,8 × 1,11. Condition 2 non remplie : la mesure des trous de 10 m ne discrimine rien, car elle vaut 0 presque partout des deux côtés. Les références manquantes sont donc **dispersées**, sans zone vide de 100 m² ; c'est cohérent avec un plus proche voisin qui passe de 2,25 à 2,65 m.
- **36 photos sur 42 sont incomplètes** au sens du § 5.1 (ratio inférieur au 10e centile de `dev_reglage`, 0,83) :
  - 0904, 0907 à 0909, 0911, 0913 à 0923 en L3 ;
  - toutes les photos de L4 sauf 0930.
  - 1 photo suspecte au sens fort (ratio < 0,3) : DJI_0945 (0,23).
- **6 photos conformes à `dev_reglage`** : DJI_0905, 0906, 0910, 0912, 0924, 0930 (ratio de 0,96 à 1,29).
- **Contrôle visuel** [O] (`zoom_val_iter_0905_0909.png`, centre de l'image) : sur DJI_0905, chaque rosette visible porte une référence. Sur DJI_0909, plusieurs rosettes nettement visibles, isolées sur sol nu, n'en portent pas. Ce n'est pas un effet de végétation non bananière.
- **Proportion estimée** [H] : si `dev_reglage` est complet, les références de `val_iter` couvrent environ 0,53 / 1,11 ≈ **48 %** des plants attendus (médiane par photo ; de 20 % à 100 % selon la photo). Il manquerait donc environ la moitié des plants. La couverture végétale plus faible de val_iter est déjà normalisée par le ratio. Une plantation réellement moins dense en L3-L4 n'expliquerait pas les rosettes non annotées du zoom.

### 5.3 Verdict

**Références de `val_iter` incomplètes**, sur 36 des 42 photos, avec environ la moitié des plants non annotés. Le défaut est diffus, sans zone vide, et touche les deux lignes : L4 un peu plus que L3.

Conséquences, sans aucune correction manuelle :
- sur `val_iter`, la précision mesurée est fortement sous-estimée et le rappel surestimé ;
- l'écart du v5 (+42 % de détections contre −9 % sur `dev_reglage`) s'explique en grande partie par ce défaut.

Je n'ai pas examiné les références de `val_scellee`, qui vient de la même mission et du même export. Il serait prudent de supposer le même défaut tant qu'independent-evaluator ne l'a pas contrôlé selon ses propres règles.

## 6. Complétude de `val_scellee` et de `bv_b_train` (7 novembre 2026)

### 6.1 Règles et protections

- [S] Les règles ont été écrites avant tout calcul par independent-evaluator, dans `docs/recherche/test_final.md` § 6 (photo conforme si ratio ≥ 0,83 et trous ≤ 90e centile de `dev_reglage` ; `val_scellee` utilisable si au moins 28 photos sur 42 sont conformes et si le ratio médian est ≥ 0,89). Le 90e centile des trous vaut 0, calculé sur `completude_val_iter.csv` sans les valeurs absentes.
- Le calcul est celui du § 5.1 : références dans la région comptée et ExG. **Aucune détection lue, aucune planche ni vignette produite.**
- Script : `out/comptage_math/annotation-manager/completude_validation.py`.
  - `val_scellee` n'est lue qu'avec l'option `--ouvrir-scellee-completude`. Sans cette option, l'assertion refuse ; le refus a été vérifié avant le calcul.
  - L'assertion de `completude_val_iter.py` n'a pas été modifiée.
  - La sortie de `val_scellee` se limite à photo, bloc, ratio, densité et verdict.
- Une photo sans cellule de 10 m évaluable a une fraction de trous absente. Elle est jugée sur le ratio seul. C'est le cas de 25 photos de `bv_b_train`, découpées en tuiles.

### 6.2 `val_scellee` (L1-L2, DJI_0862 à 0903)

- **Verdict global : UTILISABLE.** 40 photos conformes sur 42, ratio médian 1,07 (seuils : 28 photos et 0,89).
- **Photos incomplètes** (ratio < 0,83) : DJI_0867 (L1B1, ratio 0,72) et DJI_0903 (L2B3, ratio 0,69).
- **Photos conformes**, les seules à mesurer pour la confirmation : DJI_0862 à 0866, DJI_0868 à 0902. Tous les blocs gardent au moins 6 photos conformes : L1B1 6, L1B2 7, L1B3 7, L2B1 7, L2B2 7, L2B3 6. Aucun bloc n'est retiré.
- Table : `out/comptage_math/annotation-manager/completude_val_scellee.csv`.
- [H] Le défaut de L3-L4 ne s'étend donc pas à L1-L2 : il est propre aux deux lignes de `val_iter`.

### 6.3 `bv_b_train` (DJI_0757 à 0841)

- **67 photos conformes sur 71**, ratio médian 1,12.
- **Ratio < 0,83 :**
  - DJI_0795 (0,50) et DJI_0796 (0,49), dans T1 = 0757 à 0799 ;
  - DJI_0832 (0,55) et DJI_0834 (0,60), dans T2 = 0800 à 0841.
- Aucune photo n'est exclue par les seuls trous.
- Option 1a (test_final.md § 5.3) : 2 photos retirées sur 29 en T1 et 2 sur 42 en T2, sous le seuil d'abandon d'un quart. L'option reste donc possible.
- Table : `out/comptage_math/annotation-manager/completude_bv_b_train.csv`.
