# Notes d'image-analyst — mission 1 : images disponibles, résolution, visibilité des indices

Rédigé le 7 novembre 2026. Aucune expérience E-NNN n'est ouverte : les chiffres ci-dessous sont des **mesures descriptives** (étiquetées [O], avec fichier et commande), pas des scores. Aucun comptage.

## 0. Périmètre et précautions

- [O] Liste des images autorisées : lignes `partie` = `train` ou `val` de `data/drone/decoupage_comptage_v5/decoupage.csv` (21 groupes). Chaque script vérifie par assertion qu'aucun groupe scellé n'est lu (`banano`, `btd`, `segmento_est`, `rt_carlos_vera_guevara`, `rt_carlos_vera_arteaga`, `bv_b_tampon`, `cocotier_1300_plus`, `palmier_44000_4000`).
- Je n'ai ouvert ni les orthomosaïques Carlos Vera Guevara / Arteaga (ni leurs métadonnées), ni `data/drone/comptage_v*_5cm/cg/`, ni aucune image des groupes `exclu`. J'ai lu `boites.geojson` (qui contient aussi des boîtes de CG et d'Arteaga) en filtrant par site avant tout usage : aucune coordonnée de ces sites n'a été exploitée ou affichée.
- J'ai lu, pour en tirer les facteurs d'échelle des groupes train/val, `data/drone/comptage_v5_5cm/parametres.json`, qui contient aussi les facteurs des groupes de test (ce sont des métadonnées, déjà publiées dans les protocoles ; je ne les reprends pas ici).
- [O] `data/roboflow/banana_drone.zip` (46 photos DJI_02xx) n'apparaît pas dans le découpage v5 : non classé, donc **non ouvert**. À faire classer par annotation-manager.
- Examen visuel : 22 planches d'aperçu (4 images ou recadrages chacune, 64 images sources) + 5 planches multi-résolution. Les images exactes sont listées dans `out/comptage_math/image-analyst/apercus/liste.csv`.

## 1. Commandes (depuis la racine du dépôt)

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/image-analyst/inventaire.py            # -> inventaire.csv
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/image-analyst/apercus.py               # -> apercus/<groupe>.jpg, apercus/liste.csv
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/image-analyst/apercus_reforestree.py   # -> apercus/rt_<site>.jpg
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/image-analyst/planches.py              # -> planches/P*.jpg, planches/energie_bandes.csv
```

Règles appliquées (protocoles v3 à v5) :
- échelle « couronne » : côté médian des boîtes ramené à 3 m (bananier), 7 m (cocotier), 9 m (palmier à huile) ;
- échelle « espacement » : distance médiane au plus proche voisin, dans une même image, ramenée à 2,5 m ;
- échelle retenue : métadonnée si elle existe (ReforesTree), 1,1 cm/px pour les photos DJI des jeunes bananiers (mesure du protocole v3, section 2), espacement pour les jeux en points, couronne sinon ;
- netteté : écart-type du laplacien 3×3 en niveaux de gris **après réduction à 5 cm/px** (échelle commune), médiane sur 12 images tirées (graine 2026) ; ReforesTree : fenêtres de 10 m sans vide ;
- ombre : part des pixels HSV V < 60 à la résolution native, **hors vide** ; vide : part des pixels noirs (max RVB ≤ 8, hors mosaïque).

## 2. Tableau par groupe train/val

Source des chiffres : `out/comptage_math/image-analyst/inventaire.csv` [O]. « px couronne » = côté médian des boîtes ; « px NN » = espacement médian.

| Partie | Groupe | Chemin | Images | Dimensions (px) | Annotations | px couronne / px NN | Résolution (cm/px) | Netteté (lap. à 5 cm) | Ombre / vide |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| train | rt_flora_pluas | `data/drone/reforestree/wwf_ecuador/RGB Orthomosaics/Flora Pluas RGB.tif` | 1 ortho | 16 782 × 15 578, RVBA | boîtes ReforesTree (872 bananiers) | 322 / — | **0,97 [O]** géoréférencement EPSG:4326 (règle couronne : 0,93) | 149 | 0,6 % / 0 |
| train | rt_nestor_macias | `.../Nestor Macias RGB.tif` | 1 ortho | 15 003 × 13 024 | boîtes (854) | 273 / — | **1,10 [O]** (couronne : 1,10) | 169 | 0,4 % / 0 |
| train | rt_leonor_aspiazu | `.../Leonor Aspiazu RGB.tif` | 1 ortho | 17 134 × 13 855 | boîtes (322) | 281 / — | **1,06 [O]** (couronne : 1,07) | 140 | 0 / 0 |
| val | rt_manuel_macias | `.../Manuel Macias RGB.tif` | 1 ortho | 13 748 × 10 879 | boîtes (247) + points MM1-MM2 | 251 / — | **1,13 [O]** (couronne : 1,19) | 151 | 0,1 % / zones vides blanches (alpha) |
| train | bv_session_a | `data/roboflow/banavista.zip` | 123 | 4 000 × 3 000 (photos DJI brutes) | boîtes `Bananas` | 265 / 199 | **1,13 [H]** couronne (espacement : 1,25) | 174 | 7,2 % / 0 |
| train | bv_b_train | idem | 71 | 4 000 × 3 000 | boîtes | 281 / 205 | **1,07 [H]** (1,22) | 175 | 7,8 % / 0 |
| val | bv_b_val | idem | 84 | 4 000 × 3 000 | boîtes | 281 / 213 | **1,07 [H]** (1,17) | 161 | 9,8 % / 0 |
| train | jeunes_dji_0546 | `data/drone/jeunes_bananiers/dji_0546.jpg` (+ zip `plants_bana_originaux`) | 1 | 5 472 × 3 648, sans EXIF [O] | points manuels typés | — | **1,1 [H]** ± 15 % (ornières et espacement, protocole v3 §2) | 112 | 2,7 % / 0 |
| train | jeunes_dji_0548 | `.../dji_0548.jpg` | 1 | idem | points manuels | — | **1,1 [H]** | 111 | 1,9 % / 0 |
| val | jeunes_dji_0544 | `.../dji_0544.jpg` | 1 | idem | points manuels | — | **1,1 [H]** | 112 | 2,7 % / 0 |
| train | lasuiza | `data/roboflow/platano_lasuiza.zip` | 409 | 640 × 640 | boîtes `platano` | 94,5 / 76 | **3,17 [H]** couronne (espacement : 3,29) | 122 | 0,6 % / 10,9 % |
| train | vols_100_022x | `data/roboflow/count_banana_plants.zip` | 401 | 456 ou 480 carrés | boîtes `Banana-plant` | 110 / 76 | **2,73 [H]** (3,30) | 124 | 2,3 % / 2,9 % |
| train | corte | idem | 49 | 483 × 480 | boîtes | 104 / 77 | **2,89 [H]** (3,24) | 135 | 1,3 % / 1,4 % |
| train | pp_lote_2 | `data/roboflow/plantas_platano.zip` | 101 | 640 × 640 | points (boîtes de ~14 px) | — / 96 | **2,60 [H]** espacement | 111 | 1,0 % / **41 %** |
| train | pp_lote_2_parte_2 | idem | 38 | 640 × 640 | points | — / 86 | **2,92 [H]** | 132 | 0,4 % / 9,6 % |
| val | pp_100_metros | idem | 165 | 640 × 640 | points | — / 103 | **2,42 [H]** | 136 | 1,0 % / 10,9 % |
| train | segmento_ouest | `data/roboflow/plants_bana_originaux.zip` | 51 | 640 × 640 (tuiles au pas de 640 px de l'ortho) | boîtes `Banana` | 25,5 / 24 | **≈ 10 à 12 [H]** couronne 11,8 ; espacement 10,4 | 76 | 0,2 % / 0 |
| train | palmier_52000_20000 | `data/roboflow/multiple_tree.zip` | 180 tuiles (1 photo) | 512 × 512 | boîtes palmiers | 75 / 92 | **≈ 12 [H]** couronne 9 m | 46 | 0,8 % / 0 |
| val | palmier_44000_16000 | idem | 144 tuiles (1 photo) | 512 × 512 | boîtes palmiers | 88,5 / 94 | **≈ 10 [H]** | 29 | 3,7 % / 0 |
| train | cocotier_0000_0899 | idem | 389 | 112 × 112 | boîtes cocotiers (≈ 1 par tuile) | 59,5 / 55 | **échelle très incertaine : 4,6 à 12 [H]** | 78 | 4,0 % / 0 |
| val | cocotier_0900_1299 | idem | 128 | 112 × 112 | idem | 58,5 / 55 | **idem** | 105 | 17,9 % / 0 |

Remarques sur le tableau :
- [O] **segmento ouest n'est pas à 1,1 cm/px** comme l'écrit `docs/research-brief.md` §2.2 (« environ 1,1 cm/px ») : les tuiles sont espacées de 640 px dans les noms de fichiers (`segmento_11520_26240` …, pas de 640), donc non réduites, et un plant y fait 25 px (planche `apercus/segmento_ouest.jpg`, ex. `segmento_14720_24960`). Les deux règles donnent 10 à 12 cm/px ; le facteur 2,22 du v5 (`comptage_v5_5cm/parametres.json`, clé `segmento`) est cohérent avec cette valeur. L'erreur du brief porte sur un facteur 10. segmento est (test, non ouvert) partage la même orthomosaïque [S : protocole v4, limites].
- [O] La « part d'ombre » de pp_lote_2 était à 42 % avant correction : c'est du **vide de mosaïque** (bords noirs, `lote_2_chunk_7_x4096_y512`, `lote_2_chunk_94_x0_y6656`), pas de l'ombre. Après exclusion des pixels noirs, l'ombre tombe à 1 %. 41 % des pixels de ce groupe sont vides.
- [H] Les écarts entre les deux règles d'échelle restent sous 20 % pour tous les jeux de bananiers, sauf les jeunes DJI (plants espacés à plus de 2,5 m dans les zones annotées : la règle d'espacement y donne 0,6 à 1,0) et les cocotiers (≈ 1 boîte par tuile de 112 px : espacement non significatif ; la règle « 7 m » est peu fiable sur des tuiles de 13 m).
- [O] Les photos banavista sont des photos DJI **brutes**, vues de biais sur les bords (`bv_session_a`, `test/DJI_0556`, recadrage en bas à droite de la planche : rangs vus obliquement). Les jeunes DJI aussi (le v3 ne garde qu'un disque de 2 000 px).
- [O] Défauts de mosaïquage (traînées, feuilles « fondues ») dans plantas_platano : `100_metros_chunk_1_x2560_y0`, `100_metros_chunk_114_x0_y5120`, `100_metros_chunk_93_x1536_y4096`, `lote_2_chunk_94_x0_y6656`, `lote_2_parte_2_chunk_1_x2048_y0`. Ces traînées produisent des **pseudo-stries** orientées selon le défaut, pas selon la feuille.
- [O] `vols_100_022x` : tuiles pivotées avec coins noirs (`100_0221_0138_2880_960`, `100_0222_0304_960_1920`) ; bâtiments, route (`corte__5`) et zones sans bananier.
- [O] Les orthos ReforesTree Flora Pluas et Nestor Macias montrent des limbes très clairs, presque blancs, peu saturés (planches P4, P5), plus pâles que Manuel Macias et Leonor Aspiazu (`apercus/rt_*.jpg`). Cause inconnue (surexposition, reflet, face inférieure) : à examiner avec vegetation-color-engineer.
- [O] Netteté (à 5 cm/px) : les palmiers (29 à 46) et segmento (76) sont nettement plus flous que les jeux fins (110 à 175). Pour les jeux natifs sous 5 cm/px, la valeur dépend aussi du contenu (canopée dense contre sol nu) : c'est un repère, pas un classement.

## 3. Visibilité des indices par groupe (à la résolution native)

« visible / douteux / invisible » d'après l'examen à l'œil des planches nommées [O]. Les indices : contour de feuille ; nervure centrale ; stries ou déchirures du limbe ; centre de rosette.

| Groupe | Natif (cm/px) | Contour de feuille | Nervure centrale | Stries / déchirures | Centre de rosette | Images d'appui |
| --- | --- | --- | --- | --- | --- | --- |
| bv_session_a | 1,13 | visible | visible | **visible** (limbes en peigne) | visible si plant isolé ; caché en canopée | `train/DJI_0574` (planche P1), `train/DJI_0555`, `train/DJI_0591` |
| bv_b_train | 1,07 | visible | visible | **visible** | visible | `train/DJI_0840` (P2), `train/DJI_0819` |
| bv_b_val | 1,07 | visible | visible | **visible** | douteux (couronnes jointives) | `train/DJI_0939`, `train/DJI_0934`, `train/DJI_0916` |
| rt_flora_pluas | 0,97 | visible | visible | **visible** | visible à douteux (sous-étage) | P4 (`RT03010`), `apercus/rt_flora_pluas.jpg` |
| rt_nestor_macias | 1,10 | visible | visible | **visible** (moins fréquentes) | visible | P5 (`RT05323`) |
| rt_leonor_aspiazu | 1,06 | visible | visible | **visible** (`RT03754`) | visible à douteux (arbres voisins) | `apercus/rt_leonor_aspiazu.jpg` |
| rt_manuel_macias (val) | 1,13 | visible | visible | **visible** sur les grands plants, rares sur les jeunes | visible | `apercus/rt_manuel_macias.jpg` (`RT04448`, `RT04506`) |
| jeunes_dji_0546 / 0548 / 0544 | 1,1 | visible | visible | visible mais **rares** (jeunes feuilles presque entières) | visible | P3 (`dji_0548`, mère en (2671, 1776)), recadrages de `DJI_0546`, `DJI_0544` |
| lasuiza | 3,17 | visible | visible | **douteux** (seules les grandes déchirures) | visible (plants espacés) | `train/tile_0015_0010`, `valid/tile_0002_0014` |
| vols_100_022x | 2,73 | visible | visible | douteux | visible à douteux | `valid/100_0223_0015_2400_2400`, `train/100_0222_0002_2880_1920` |
| corte | 2,89 | visible | visible (trait clair) | douteux à invisible | visible (feuille cigare claire) | `test/corte__43`, `test/corte__0` |
| pp_lote_2 / pp_lote_2_parte_2 | 2,6 / 2,9 | visible (plants de ~1 m) | douteux | **invisible** (et pseudo-stries de mosaïquage) | visible | `lote_2_chunk_68_x3072_y3584`, `lote_2_parte_2_chunk_7_x2560_y512` |
| pp_100_metros (val) | 2,42 | douteux (canopée jointive, traînées) | douteux | **invisible / non fiable** (artefacts) | douteux | `100_metros_chunk_138_x512_y6144`, `100_metros_chunk_1_x2560_y0` |
| segmento_ouest | ≈ 10-12 | douteux (étoile de quelques pixels) | invisible | invisible | visible comme point de convergence de l'étoile, sur les plants isolés | `segmento_14720_24960`, `segmento_15360_25600` |
| palmier_* (négatifs) | ≈ 10-12 | folioles en texture | rachis visible comme rayon | **texture striée visible** (folioles) | visible | `44000_16000_1283_1474`, `44000_16000_2309_1597` (52000_20000 : même source, non regardée en détail) |
| cocotier_* (négatifs) | incertaine | douteux | douteux | douteux | invisible (tuiles trop petites) | `000757`, `000522` (0900-1299 : même source, non regardée en détail) |

## 4. Seuils de visibilité par rééchantillonnage (planches multi-résolution)

Planches : `out/comptage_math/image-analyst/planches/P1_bv_session_a.jpg` … `P5_rt_nestor_macias.jpg`. Chaque planche : carré de 4 m autour du plant (haut) et zoom de 1,2 m sur le limbe (bas), à 1, 2, 3, 5 et 6,4 cm/px (INTER_AREA depuis la résolution native, affichage au plus proche voisin).

Plants de développement (tous en partie `train`) :
- P1 : bv_session_a, `train/DJI_0574_JPG.rf.12b8ec29…` (grand plant à limbes déchirés) ;
- P2 : bv_b_train, `train/DJI_0840_JPG.rf.1fd9b8af…` (plant isolé sur herbe) ;
- P3 : jeunes_dji_0548, mère la plus proche du centre, colonne 2671, ligne 1776 ;
- P4 : ReforesTree Flora Pluas, boîte `RT03010` ;
- P5 : ReforesTree Nestor Macias, boîte `RT05323`.

Verdict à l'œil, commun aux cinq plants [O] :

| Indice | 1 cm/px | 2 cm/px | 3 cm/px | 5 cm/px | 6,4 cm/px |
| --- | --- | --- | --- | --- | --- |
| Contour de feuille | visible | visible | visible | visible | visible (grandes feuilles) |
| Nervure centrale | visible | visible | visible (trait de 1 px) | douteux (seulement les grandes feuilles, P1, P2) | invisible sauf exception |
| Stries / déchirures fines | visible | visible | douteux (bandes larges seulement) | invisible (reste un bord dentelé, P1) | invisible |
| Centre de rosette | visible si dégagé (P2, P3, P5) | idem | idem | visible comme convergence (P2, P3) | douteux |

Mesure descriptive [O] (`planches/energie_bandes.csv`, commande `planches.py`) : énergie de détail retenue par rapport à 1 cm/px, sur le carré de 4 m.

| cm/px | 1 | 2 | 3 | 5 | 6,4 |
| --- | --- | --- | --- | --- | --- |
| bande « stries » (DoG σ 1,5 / 4 cm), min-max des 5 plants | 1 | 0,93-0,98 | 0,84-0,91 | 0,63-0,72 | 0,50-0,60 |
| bande « nervure / bord » (DoG σ 4 / 12 cm) | 1 | 0,99-1,00 | 0,99-1,00 | 0,97-0,98 | 0,94-0,95 |

Lecture : la bande fine perd un tiers de son énergie à 5 cm/px et la moitié à 6,4 cm/px, alors que la bande des bords et des nervures reste au-dessus de 94 %. Cette mesure est indirecte (interpolation bicubique incluse, aucune référence de stries annotée) et ne remplace pas le verdict visuel.

## 5. Conclusion

- **Résolution minimale plausible** [H, appuyée sur P1-P5] :
  - stries ou déchirures du limbe : **≤ 2 cm/px** ; 3 cm/px est la limite (seules les grandes déchirures) ; perdues à 5 cm/px ;
  - nervure centrale : **≤ 3 cm/px** ; douteuse à 5 cm/px ; perdue à 6,4 cm/px ;
  - contour de feuille et forme en étoile : jusqu'à 6,4 cm/px ; vers 10-12 cm/px (segmento) l'étoile ne fait plus que quelques pixels.
  - Conséquence : le pipeline actuel à 5 cm/px (v3 à v5) **ne voit pas les stries**. Une formulation compatible avec l'indice « stries » doit travailler à 1-2 cm/px.
- **Jeux où l'indice « stries » est testable** (natif ≤ 1,2 cm/px) :
  - développement : bv_session_a, bv_b_train, rt_flora_pluas, rt_nestor_macias, rt_leonor_aspiazu, jeunes_dji_0546 / 0548 (stries rares : jeunes plants) ;
  - validation : bv_b_val, rt_manuel_macias (MM1-MM2), jeunes_dji_0544 ;
  - limite (≈ 2,7-3,2 cm/px, seulement les grandes déchirures) : lasuiza, vols_100_022x, corte ;
  - non testable : plantas_platano (2,4-2,9 cm/px, jeunes plants, artefacts de mosaïquage qui imitent des stries), segmento ouest (≈ 11 cm/px).
- **Contre-exemple H3** [O] : les palmiers à huile (`palmier_44000_16000`) montrent une texture striée (folioles) **même à ≈ 10 cm/px**, résolution où les déchirures du bananier ont disparu. Une texture striée à basse résolution signale donc plutôt un palmier [H, à tester par orientation-engineer sur les négatifs du développement].
- **Échelle inconnue ou fragile** : cocotiers (4,6 à 12 cm/px selon la règle), segmento (10-12, contredit le brief), jeunes DJI (1,1 ± 15 %, sans EXIF).
- **Hors comptage** [O] : Sentinel-2 (`..\datas\cotedivoire\*.zip`, `..\datas\equateur\*.zip`) : 10 bandes + couleur vraie + carte de classification, 804 × 483 px (EPSG:32630) et 402 × 242 px (EPSG:32717), **9,95 à 9,98 m/px**, un plant de 3 m y fait 0,3 px : inutilisable pour le comptage (vigueur seulement). `..\datas\parcelles\` : 33 polygones (Côte d'Ivoire) et 13 (Équateur), champs `parcelle_id`, `site`, `split`. El Oro (`El Oro OAM RGB.tif`, contrôle visuel, ni train ni val) : 6,44 cm/px [O, métadonnée], 10 989 × 10 699 px, image non ouverte.
- Données dérivées déjà à 5 cm/px (`data/drone/comptage_v*_5cm`, `roboflow_centres_5cm`, `roboflow_deepforest*`, `validation_points_5cm`, `reforestree/deepforest_5cm`) : inutilisables pour les stries et les nervures ; non inventoriées image par image.

## 6. Limites de cette note

- Aucune annotation de stries ou de nervures n'existe : tous les verdicts sont visuels (5 plants pour les seuils, 64 images sources pour les groupes).
- Les verdicts des groupes `palmier_52000_20000` et `cocotier_0900_1299` sont repris de leur source sœur sans examen détaillé.
- La netteté par laplacien dépend du contenu ; aucune mesure de bougé directionnel n'a été faite.

## D-013 — Statistiques photométriques réelles pour le simulateur v2 (7 novembre 2026)

### D-013.1 Données, partage, commande

- Données [O] : tuiles `bv_session_a` de `data/comptage_math/references/dev_dense_images.csv` (déjà filtrées par la règle pépinière v2, `conventions_comptage.md` § 1.4), région comptée = disque ∩ zone propre, moins les grandes plages noires de bord (≥ 400 px). Aucun autre groupe lu (assertion), aucune détection.
- Partage [O] (`out/comptage_math/image-analyst/D-013/partage.csv`, règle de scientific-challenger § D-013 1.1, MD5 des tuiles concaténées de chaque photo — les photos DJI d'origine ne sont pas dans le dépôt) : **CAL = 32 photos (DJI_0543 à 0620), 183 tuiles, 4,38 ha ; VAL-S = 32 photos (DJI_0628 à 0682), 176 tuiles, 4,38 ha ; aucune photo exclue** (écart de 8 numéros à la coupure 0620 | 0628).
- Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/image-analyst/D-013/stats_photometriques.py` (≈ 2 min, 7 processus). Sorties : `stats_photometriques.json` (blocs `CAL`, `VAL_S`, `distance_CAL_VAL_S`, `par_image`), `stats_validation_cachees.json` (quantités réservées F6–F7, non commentées ici, à ne pas transmettre à leaf-mathematician), 6 vignettes `vignette_*.png`.
- Transparence [O] : les seuils ont été posés sur trois tuiles de CAL (DJI_0550, 0556, 0576). Avant que le partage ne soit connu, j'avais aussi regardé une planche de 6 tuiles (dont DJI_0646, 0678, 0681, aujourd'hui en VAL-S) et les quantiles globaux de L*, a*, b*, ExG d'un tuile sur neuf des deux moitiés. Aucun seuil n'a été retouché d'après VAL-S ; les deux retouches (normalisation de Weber de A_g, exclusion des seules grandes plages noires) ont été faites sur les vignettes de CAL.

### D-013.2 Règles de classes (figées, en tête du script)

Lab OpenCV (L* 0–100), lissé σ 3 cm ; C chroma, h teinte ; « vert » = ExG > 0,05 ou a* < −4 (couleur.py). Priorité dans l'ordre :

| Classe | Règle |
| --- | --- |
| ombre (végétale / non végétale) | L* < 0,55 × médiane(L*) de la tuile ; végétale si a* < −3 ou ExG > 0,05 |
| artificiel | b* < −6 (sacs bleus, tuyaux) ou (C < 8 et L* > 75) (béton, plastique) |
| herbe | vert et (A_g < 0,065 ou (A_g < 0,095 et (A_f/A_g > 1 ou h < 108°))) ; A_g = contraste de Weber de la bande 12–30 cm (DoG) intégré sur 20 cm, A_f idem 4–8 cm |
| feuillage_vert | vert, non herbe |
| sec | non vert, C ≥ 22, 55° ≤ h < 85°, L* ≥ 30 (brun doré) |
| sol_nu | le reste (sol, litière brune broyée, chemin) |

La règle d'herbe n'utilise **ni tenseur ni orientation** (grandeurs internes de B′, réservées à la validation) : elle dit « végétation sans structure à l'échelle d'une feuille ».

### D-013.3 Résultats principaux [M] (D-013, commande ci-dessus ; CAL puis VAL-S)

- **Résolution** : 4,12 cm/px médiane en CAL (q5–q95 3,63–6,13), 4,53 en VAL-S ; incertitude relative de la règle des couronnes ≈ 0,5 % [O, `dev_dense.csv`]. La résolution diffère entre moitiés (KS 0,20) : le simulateur doit tirer la résolution dans la distribution de CAL.
- **Fractions poolées (CAL / VAL-S)** : feuillage vert 0,594 / 0,637 ; herbe 0,171 / 0,136 ; sol nu 0,106 / 0,089 ; ombre 0,104 / 0,109 (dont végétale 0,074 / 0,079) ; artificiel 0,019 / 0,024 ; sec 0,0066 / 0,0065. Dispersion par tuile (CAL, q5–q95) : feuillage 0,32–0,76, herbe 0,06–0,36, sol 0,03–0,22, ombre 0,05–0,16, sec 0,0003–0,025. Écart CAL↔VAL-S des moyennes par tuile ≤ 0,04 (herbe −0,033, feuillage +0,039) ; rapport des écarts-types 0,65 (herbe) à 1,54 (artificiel).
- **Couleurs Lab moyennes (CAL)** : feuillage (59,3 ; −16,6 ; 24,0), σ (17,2 ; 6,0 ; 7,5) ; herbe (57,0 ; −13,4 ; 27,8) ; sec (51,0 ; 6,2 ; 23,2) ; sol (53,0 ; 4,7 ; 13,5) ; ombre végétale (19,4 ; −8,5 ; 15,2) ; ombre non végétale (20,1 ; 5,3 ; 10,2). Covariances complètes dans le JSON. ΔE CAL↔VAL-S : 0,6 à 1,7, sauf herbe 3,0 et sec 4,2.
- **Luminance** (Y 0–1, pixels CAL) : q5 0,17, médiane 0,51, q95 0,82 ; KS CAL↔VAL-S 0,044. ExG : médiane 0,165 ; KS 0,036.
- **Spectre radial de la luminance** : loi de puissance, pente β = 1,71 ± 0,22 (CAL, 1/256–1/4 cycle/px) ; en cycles/m (0,3–5 c/m) β = 1,88 ± 0,14 ; log10 DSP (Y²·m²) ≈ −2,17 à 0,31 c/m, −2,83 à 1,13 c/m, −4,20 à 4,17 c/m, dispersion entre tuiles 0,13 à 0,25 dex. Écart CAL↔VAL-S : 0,037 dex en moyenne, pente −0,035.
- **Longueur de corrélation** (premier ρ < 1/e, médiane par tuile, CAL) : ombre 0,21 m (q5–q95 0,14–0,34), sec 0,13 m, sol nu 0,35 m (0,17–1,10), herbe 0,36 m. Taches (diamètre équivalent pondéré par l'aire, médiane) : ombre 0,83 m, sec 0,27 m, sol 1,39 m, herbe 1,55 m ; la plupart des taches d'ombre ou de sec font 0,12–0,14 m (2 à 3 px).
- **Direction des ombres** : autocorrélation des ombres quasi isotrope (rapport d'axes 1,03, concentration de direction 0,17) [M] : ciel couvert, pas d'ombre portée orientée mesurable ; les « ombres » sont des trous sombres entre feuilles.
- **Flou et bruit** : variance du laplacien (3 × 3, niveaux 0–255) médiane 35 200 en natif, 26 900 après ramenée à 6,67 cm/px ; σ du bruit (Immerkær) 10,8 niveaux, **borne haute** car la texture y entre ; JPEG des tuiles préparées : qualité ≈ 95 partout (c'est la compression de la préparation v5, pas celle de la caméra).

### D-013.4 Limites et ce qui n'est pas mesurable

- [O, vignettes] **Herbe contre feuillage** : la règle d'herbe prend aussi les intérieurs de grands limbes pâles et peu contrastés et une partie des jeunes feuilles claires (vignettes `herbe_max`, `ombre_max` : quelques taches d'« herbe » sur la canopée, ≈ 5 à 13 % de la tuile). La fraction d'herbe est donc **surestimée**, de l'ordre de quelques points, au détriment du feuillage [H]. Herbe et couvre-sol bas (DJI_0551) sont bien séparés des bananiers.
- [O] **Sec contre sol** : la litière broyée au sol est faite de feuilles mortes ; à 4–5 cm/px elle est brun-rouge et classée sol_nu. « sec » ne retient que les feuilles brun doré saturées (feuilles pendantes, débris clairs), d'où une fraction faible (0,7 %). Sur la vignette `sec_max` (DJI_0543), une partie du « sec » est de l'herbe sèche du bord de chemin.
- [O] **Ombre** : seuil relatif à la tuile (une tuile sombre a moins d'ombre qu'elle n'en paraît) ; sous ciel couvert, ni direction ni longueur d'ombre portée ne sont mesurables : le simulateur ne peut pas les calibrer sur CAL.
- **Non mesurable à cette résolution** : nervures fines et stries des limbes (sous-pixel à 4–6 cm/px, voir § 4), pseudo-tronc et cigare (masqués), séparation litière / sol vraiment nu, PSF de la caméra (les tuiles sont rééchantillonnées : le flou mesuré mêle optique et préparation), bruit capteur pur (la méthode d'Immerkær le confond avec la texture).
- Les distances CAL↔VAL-S du JSON sont la variabilité naturelle de référence des tests F1–F5 ; les quantités réservées (F6, F7) sont dans un fichier à part et ne sont pas résumées ici.
