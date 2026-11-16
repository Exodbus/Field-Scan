# Journal de l'agent Rendu (rendu 3D Blender), nuit du 13-14 nov. 2026

Zone d'écriture : `out/rendu_blender/`, `scripts/blender_*.py`, `scripts/rendu_*.py`, ce journal. Aucun commit, aucun téléchargement, aucun fichier existant modifié.

## 20 h 57 — lecture et choix de la tuile

- [O] `data/drone/comptage_v5_5cm/tuiles.csv` : tuiles de 512 px (25,6 m). Choix parmi le split `train` seulement (colonne `partie`), sans ouvrir d'image de validation, de juge ou de test.
- Planche de 12 candidates d'entraînement (lasuiza, pp_lote_2, segmento_ouest, ReforesTree, vols_100, banavista, corte). Les tuiles rééchantillonnées (facteur ≠ 1) ont des bords noirs ou sont floues.
- [O] Retenue : `rt_Flora_Pluas_5cm_818_818.jpg` (groupe `rt_flora_pluas`, partie `train`, facteur 1,0 donc 5 cm natifs, 55 pieds mères annotés), plantation en rangs réguliers, couronnes nettes.

## 21 h 05 — quelle donnée « santé » existe vraiment

- [O] La chaîne sort un bulletin **par parcelle** (score, niveau) et des **zones d'alerte** ; le module vigueur drone écrit une carte ExG (50 cm, lissée sur 3 m) par parcelle dans `cartes/`.
- [O] `out/adoption_f1/demo_*` : parcelles « non évaluées », rien d'utilisable.
- [O] `resultats/essai_drone/` (1er nov.) : run.py sur les orthomosaïques ReforesTree, Flora Pluas orange (75) avec 3 zones moins vertes (A002 à A004).
- Relance de la chaîne actuelle, vigueur seule, dans ma zone : `out/rendu_blender/chaine_vigueur/` (4 min 12 s). Mêmes niveaux et alertes que le 1er nov.
- [O] Aucune des zones A002-A004 ne touche la tuile 818_818 (A004 touche 818_2045, mais c'est une tache de sol nu en bord de tuile). La donnée réelle par zone qui existe pour la tuile est donc la **carte ExG** de la chaîne : le rendu « santé » colore chaque plant par son ExG réel (écart à la médiane de la parcelle), **sans alerte**.

## 21 h 20 — données de la parcelle (`scripts/rendu_preparer.py`)

- Détecteur v5 (`fieldscan.drone.DetecteurCentres`, importé tel quel), seuil 0,30 : **60 centres** en 2,5 s (55 pieds annotés sur cette tuile d'entraînement ; le modèle a vu cette tuile, ce n'est pas une mesure de performance).
- Géoréférencement refait comme `scripts/preparer_deepforest.py` (origine 818, 818 dans l'orthomosaïque rééchantillonnée à 5 cm) : corrélation 0,998 entre la tuile et la fenêtre relue dans l'orthomosaïque ; côtés au sol 25,60 × 25,60 m.
- ExG aux 60 pieds : 0,080 à 0,238 (médiane de la parcelle d'après le bulletin : 0,125) ; écart de −0,045 à +0,113.

## 21 h 25 — bananier procédural et scène

- `scripts/blender_bananier.py` : maillage généré par script (numpy + bpy), sans Geometry Nodes. Faux-tronc conique au pied évasé avec gaines brunes, feuille cigare, 8 à 12 feuilles en spirale (137,5°). Chaque feuille : pétiole, limbe oblong, nervure saillante et plus claire, section en Λ, courbure qui retombe (élévation de φ0 à φ1), 1 à 7 déchirures du bord vers la nervure (faces retirées, bords écartés). Les vieilles feuilles ont le bord jauni ou sec. S'y ajoutent 0 à 2 feuilles sèches pendantes et 0 à 3 rejets épées. Matériaux : couleur des sommets, part translucide, nervures latérales en relief.
- Paramètres de forme inspirés de `docs/recherche/modele_feuille.md` (modèle B : nervure parabolique et limbe en bande ; L, W/L, r0, K). Le fichier n'a pas été modifié.
- Défauts trouvés sur les essais à 640 × 360 :
  - faux-troncs tous placés à l'origine (décalage du plant oublié), corrigé ;
  - couronnes trop étroites vues de dessus (bouts trop tombants), corrigé ;
  - photo du sol floue de près : mêlée à 60 % à une terre procédurale, vue rapprochée seulement ;
  - comparaison de dessus plus lisible sur sol nu.
- Couronne : rayon 1,5 m ± 12 %, plafonné à 0,45 × distance au voisin + 0,25 (voisin médian à 2,6 m). Feuilles jusqu'à 2,0 à 2,3 m du centre.

## 21 h 27 — rendus finaux lancés (2 fils)

`scripts/rendu_lancer.py --fils 2` : drone naturel et santé (48 échantillons), proche (64), dessus naturel et santé (32, 900 × 900), débruiteur OpenImageDenoise.

## 21 h 48 — rendus terminés (tous à 2 fils)

| Image | Résolution | Échantillons | Temps |
| --- | --- | --- | --- |
| vue_drone_naturel.png | 1600 × 900 | 48 | 265 s |
| vue_drone_sante.png | 1600 × 900 | 48 | 212 s |
| vue_proche_naturel.png | 1600 × 900 | 64 | 257 s (second cadrage, pied du plant visible ; premier cadrage 284 s) |
| vue_dessus_naturel.png | 900 × 900 | 32 | 102 s |
| vue_dessus_sante.png | 900 × 900 | 32 | 102 s |

- Planches composées (PIL) : `planche_dessus_comparaison.png` (tuile réelle et 60 centres | rendu 3D, même cadrage), `planche_dessus_sante.png` et `planche_drone_sante.png` (légende : mesure réelle ExG, aucune alerte dans la tuile, indice relatif).
- [O] Contrôle visuel de la planche de dessus : chaque couronne 3D tombe sur une couronne de la photo ; la trouée du coin nord-est (arbre non bananier) est respectée.
- Scène : `out/rendu_blender/parcelle_bananiers.blend`. README : `out/rendu_blender/README.md`.
- Limites :
  - faux-troncs trop nus, l'ensemble rappelle un peu un palmier ;
  - pas de relief ;
  - rejets illustratifs, aucune donnée ;
  - la photo au sol double les couronnes en vue oblique.
- Rien de commité ; aucun fichier existant modifié ; aucun téléchargement.
