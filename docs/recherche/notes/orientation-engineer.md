# Notes d'orientation-engineer (équipe VISION)

Rédacteur unique : orientation-engineer. Ouvert le 7 novembre 2026 pour la concertation C-001 (examen des modèles A et B de `docs/recherche/modele_feuille.md`).

## 0. Conventions

- φ = direction du **gradient** dominant (ou du vecteur d'onde d'un Gabor), en angle doublé ; ψ = arg(x − c), direction du centre c vers le pixel x.
- s = cos 2(φ − ψ). **s > 0** : gradient radial (stries perpendiculaires à la nervure, ou bord d'une tache isotrope, HF-06). **s < 0** : gradient tangentiel, donc **structure linéaire radiale** (bord de limbe, nervure, ligne d'ombre entre limbes).
- Code : `comptage_math/orientation.py` (tenseur, tenseur à gradients normalisés, banc de Gabor complexe, fiabilité). Sorties : `out/comptage_math/orientation-engineer/`.

## 1. Mesures

### 1.1 Décomposition synthétique du plant B (aucune image réelle)

Commande :
```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/orientation-engineer/decomposition_synthetique_B.py
```
Plant de `diagnostic_signe_B.py` (graine 777, 9 feuilles, λ 6 à 13 cm, β 73 à 88°, W 0,34 à 0,60 m). Moyenne de s sur les pixels de limbe, anneau 0,4–1,5 m. Sortie : `decomposition_synthetique_B.json`.

| Canal | complet | sans stries | sans nervure | stries fortes (0,9) |
| --- | --- | --- | --- | --- |
| T_B (σ_g 2,5 cm, σ_t 10 cm : réglage de B) | −0,94 | −0,95 | −0,47 | −0,84 |
| T_fin (σ_g 1,5 cm, σ_t 3 cm) | −0,43 | −0,91 | **+0,40** | −0,11 |
| U_fin (gradients normalisés, 1,5/3 cm) | +0,04 | −0,82 | **+0,60** | +0,18 |
| Gabor complexe λ 6 cm | +0,06 | −0,91 | **+0,61** | +0,35 |
| Gabor complexe λ 10 cm | −0,58 | −0,92 | +0,26 | −0,28 |
| T_feuille (σ_g 4 cm, σ_t 10 cm) | −0,91 | −0,92 | −0,64 | −0,89 |

[M synthétique] **100 %** des pixels de limbe de l'anneau sont à moins de 20 cm (2 σ_t de B) d'un bord ou de la nervure.

Lecture :
- à l'échelle de B (σ_t = 10 cm), ce sont les **bords** qui dominent : même sans nervure, s = −0,47 ;
- à l'échelle fine, c'est la **nervure** : sans elle, les trois canaux fins deviennent nettement positifs (+0,40 à +0,61) ;
- le tenseur à gradients normalisés et le Gabor court récupèrent en partie les stries (+0,04 à +0,35), mais pas assez pour l'emporter sur la nervure.

### 1.2 Mesure exploratoire sur banavista (développement)

Identifiant d'expérience à attribuer par le chef d'orchestre ; noté **E-expl-OE-01**.

Commande :
```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/orientation-engineer/mesure_alignement.py
```
(`--figure-seule` refait la figure à partir du CSV.)

**Données.** `data/roboflow/banavista.zip`, filtré par `decoupage.csv` (groupe ∈ {bv_session_a, bv_b_train}, partie = train ; assertion contre les groupes interdits et bv_b_val). Graine 20261107. Images : DJI_0557, DJI_0642, DJI_0646 (bv_session_a) ; DJI_0800, DJI_0804 (bv_b_train). Seules les boîtes de catégorie « Bananas » sont gardées ; le centre est le centre de boîte. Les pixels viennent du disque central de 1 000 px (vue presque verticale), avec un masque provisoire : ExG lissé > 0,05 et luminance > 0,18. On tire 150 000 pixels par image et par condition. Résolutions : native (1,07 à 1,13 cm/px) et 2 cm/px (INTER_AREA).

**Statistique et lecture.** Elles sont écrites dans l'en-tête du script avant le lancement. On calcule la moyenne de s dans l'anneau 0,4–1,5 m autour du centre le plus proche. Contrôles :
- demi-maille : chaque centre est décalé de 0,5 × la distance médiane au plus proche voisin, dans une direction aléatoire ;
- orientations mélangées entre les pixels.

Règle de lecture : un canal est « informatif » si |réel − demi-maille| > 3 × l'écart-type entre images de la demi-maille, avec le même signe sur au moins 4 images sur 5. C'est une règle d'exploration, pas un critère d'E-NNN.

Résultats [M exploratoire, E-expl-OE-01], anneau 0,4–1,5 m, moyenne sur 5 images (écart-type entre images) :

| Canal | réel 1,1 cm/px | demi-maille | mélange | réel 2 cm/px | demi-maille 2 cm/px | images de signe < 0 (réel) |
| --- | --- | --- | --- | --- | --- | --- |
| T_feuille (4/10 cm) | **−0,245 (0,148)** | −0,018 (0,078) | 0,000 | **−0,245 (0,148)** | −0,018 (0,077) | 5/5 |
| T_B (2,5/10 cm) | −0,204 (0,187) | −0,026 (0,073) | 0,000 | −0,207 (0,184) | −0,026 (0,072) | 5/5 |
| T_fin (1,5/3 cm) | −0,092 (0,103) | −0,015 (0,033) | −0,002 | −0,097 (0,101) | −0,014 (0,035) | 5/5 |
| U_fin (1,5/3 cm, normalisé) | −0,072 (0,074) | −0,009 (0,022) | 0,001 | −0,077 (0,071) | −0,009 (0,023) | 5/5 |
| Gabor λ 6 cm | −0,044 (0,109) | −0,017 (0,026) | −0,001 | −0,046 (0,112) | −0,015 (0,024) | 3/5 |

Écart apparié réel − demi-maille pour T_feuille, image par image (1,1 cm/px) : −0,166, −0,352, −0,212, −0,222, −0,178. Les cinq sont négatifs.

**Selon la règle de lecture écrite avant**, aucun canal ne passe nettement :
- T_feuille : écart 0,226 contre un seuil de 3 × 0,078 = 0,235. Il échoue de peu, parce que l'écart-type de la demi-maille est gonflé par DJI_0642, où la demi-maille vaut elle-même −0,157 ;
- U_fin est à la limite à 2 cm/px (0,068 contre 0,068) ;
- les autres canaux échouent.

Le signe est pourtant constant (5/5) pour les quatre tenseurs, et l'écart apparié de T_feuille va de 0,17 à 0,35 sur chaque image. **Conclusion prudente : un signal « axes linéaires radiaux » (s < 0) existe, il ne vient pas des stries, et sa marge contre la demi-maille reste à établir sur plus d'images avec un critère fixé par independent-evaluator.**

**Fiabilité** (T_feuille, s moyen par tercile de cohérence) : −0,115, −0,224, −0,395 à 1,1 cm/px ; −0,113, −0,225, −0,396 à 2 cm/px. Une cohérence plus haute va avec un meilleur alignement : la cohérence est une fiabilité valide pour ce canal [M, E-expl-OE-01].

**Anneau interne 0,15–0,4 m** : s réel ≈ −0,11 pour T_feuille et T_B (0/5 positifs), demi-maille ≈ +0,05. La tache centrale ne domine donc pas au sens « gradient radial ». Les pétioles et les bases de limbes, radiaux, l'emportent.

[O] `histogrammes_alignement.png` : la courbe réelle croît de façon monotone vers |φ − ψ| = 90°. Il n'y a aucun excès près de 0°, là où les stries donneraient un signal. Les courbes à 1,1 et à 2 cm/px sont superposables.
[O] `carte_orientation_T_feuille_2cm.jpg` (DJI_0557) : canopée dense mais pas entièrement fermée (sol visible entre les rangs), environ 80 centres annotés, limbes allongés nets. La carte montre des domaines cohérents de la taille d'un limbe, non organisés à l'œil autour des points : l'effet est statistique (concentration faible, de l'ordre de κ ≈ 0,5).

Fichiers : `alignement_detail.csv`, `alignement_resume.csv`, `histogrammes_alignement.png`, `carte_orientation_T_feuille_2cm.jpg`.

**Limites** :
- 5 images ;
- les centres sont des centres de boîte (HF-11 : pas forcément des mères) ;
- l'attribution se fait au centre le plus proche, pas par un vote ;
- le masque est provisoire, en attendant vegetation-color-engineer ;
- pas de tache synthétique (HF-06, contrôle 1), pas de palmiers.

## 2. Objections (C-001)

### OBJ-V1 — Le signe de B est mal posé : stries et structures linéaires portent le même axe avec des signes opposés
- **Énoncé.** En angle doublé du gradient, les stries perpendiculaires à la nervure donnent s > 0, tandis que la nervure et les bords du même limbe donnent s < 0. Le modèle B les additionne dans un seul tenseur : par construction, ils se détruisent. L'échec de B n'est donc pas « les stries sont faibles » mais une **interférence de deux mécanismes de signes contraires** dans une même bande.
- **Appui.** [M synthétique] (§ 1.1) : sans nervure, les canaux fins valent +0,40 à +0,61 ; avec la nervure, −0,43 à +0,06. [M] `diagnostic_signe_B.json` de leaf-mathematician : −242 complet, −123 sans nervure.
- **Correction.** Séparer deux canaux de signes connus et ne jamais les mélanger avant le vote :
  - canal « axes linéaires » (s < 0 attendu, signe −1, B′) ;
  - canal « stries » (s > 0 attendu), qui n'est gardé que s'il passe ses propres contrôles.
- **Expérience qui tranche.** E-expl-OE-01 étendu (§ 3).

### OBJ-V2 — Le diagnostic « bords et nervure dominent » est juste, mais il vient d'un choix d'échelles et de pondération autant que de la physique
- **Énoncé.** Avec σ_t = λ = 10 cm et une demi-largeur de limbe de 17 à 30 cm, chaque pixel du limbe a dans sa fenêtre d'intégration un bord ou la nervure. Le tenseur pondéré par l'énergie |∇I|² laisse alors le saut de bord, au fort contraste, l'emporter sur des stries de faible contraste. Dans le synthétique, c'est d'abord une **erreur d'échelle d'intégration et de pondération**. À l'échelle fine, la nervure reste dans la même bande que les stries (largeur 2 à 6 cm ≈ λ/2) : aucun filtre passe-bande ne la sépare. Ça, c'est une propriété réelle.
- **Appui.** [M synthétique] 100 % des pixels de limbe à moins de 2 σ_t d'un bord ou de la nervure. T_B reste à −0,47 sans nervure (les bords), alors que T_fin passe à +0,40 (§ 1.1). Les gradients normalisés avant intégration (U_fin) font passer le plant complet de −0,43 à +0,04.
- **Correction.**
  - Pour viser les stries : σ_t ≤ λ/2, gradients normalisés avant intégration (`tenseur_unitaire`), Gabor à enveloppe allongée le long des stries (γ < 1, plusieurs périodes), et masque d'exclusion de la nervure (ligne claire détectée à σ ≈ largeur de nervure, dilatée de 2 σ).
  - Pour la symétrie radiale fondée sur le gradient (Loy et Zelinsky) : elle vote le long du gradient, donc elle détecte le mécanisme s > 0, c'est-à-dire les taches et les anneaux. Elle votera perpendiculairement aux limbes. **Ne pas l'utiliser pour les axes de feuilles.** Il faut voter le long de la direction de la structure (gradient + 90°), ce qui revient au noyau de B avec signe −1.
- **Expérience qui tranche.** Sur le synthétique (nouvelle graine), puis sur le développement : s des canaux « stries » avec et sans masque de nervure. Critère proposé, à fixer avec independent-evaluator : le canal stries est retenu s'il donne s > 0 sur au moins 4 images sur 5 avec masque de nervure, et un écart à la demi-maille supérieur à 3 écarts-types.

### OBJ-V3 — Sur banavista (1,1 cm/px), les stries ne donnent pas d'alignement radial : P-B1 n'est pas soutenue ; le signal vient des axes linéaires, à l'échelle de la feuille
- **Énoncé.** À la résolution la plus fine disponible en dense, aucun canal fin n'a de moyenne positive. Le seul signal net est négatif (structures linéaires radiales), il est maximal à l'échelle de la feuille (σ_g = 4 cm), et il est identique à 1,1 et à 2 cm/px.
- **Appui.** [M exploratoire E-expl-OE-01] (§ 1.2) : T_fin −0,09, U_fin −0,07, Gabor λ 6 cm −0,04 (3/5 négatifs) ; T_feuille −0,245 contre −0,018 en demi-maille, 5/5. Les histogrammes ne montrent aucun excès près de 0°.
- **Correction.**
  - Abandonner B « stries » comme vote en dense.
  - Adopter, pour les votes de convergence-engineer, un champ « axes linéaires » : tenseur multi-échelle (σ_g de 3 à 6 cm, σ_t de 8 à 15 cm), échelle choisie par pixel au maximum de cohérence, signe −1, fiabilité égale à la cohérence (validée par les terciles).
  - Calculer ce champ à 2 cm/px, quatre fois moins cher qu'à 1 cm/px pour le même signal.
  - Les stries peuvent rester un indice d'**espèce** (limbe déchiré contre foliole), pas d'orientation.
- **Expérience qui tranche.** E-NNN pré-enregistrée :
  - 20 images de développement banavista et en plus lasuiza, vols_100_022x et corte, à 2, 3 et 5 cm/px ;
  - comparaison au contrôle demi-maille et à la tache synthétique (HF-06) ;
  - critère fixé par independent-evaluator, par exemple un écart apparié médian réel − demi-maille < −0,1 avec un intervalle de bootstrap par image excluant 0.
  - Prédiction : le signal survit à 3 cm/px et disparaît à 5 cm/px.

### OBJ-V4 — Le vote d'orientation (A comme B) n'a pas de polarité : en dense, les axes passent aussi par les voisins et par les milieux
- **Énoncé.** L'angle doublé est indifférent au sens : un limbe orienté vers un voisin vote autant pour son centre que pour le voisin et pour la demi-maille entre les deux. En plantation dense en quinconce, une part des limbes pointe justement vers les voisins. A souffre du même défaut : sa matrice de Fisher est surtout transversale, et le gabarit gaussien symétrique ne distingue pas la base de la pointe (un limbe est compatible avec un centre à sa base et avec un centre « miroir » à 2μ).
- **Appui.** [H] géométrique. [O] `carte_orientation_T_feuille_2cm.jpg` : domaines cohérents non organisés autour des points à l'œil. [M] la demi-maille reste près de 0 au niveau du pixel, mais cette statistique utilise l'attribution au centre le plus proche, pas un vote ouvert.
- **Correction.** Introduire une polarité :
  - profil de largeur du limbe (pétiole étroit à la base) ;
  - gradient radial de luminance du limbe ;
  - noyau de vote limité à r ∈ [r_in, ≈ 0,6 × maille] pour que les voisins ne votent pas.
  
  À traiter avec convergence-engineer.
- **Expérience qui tranche.** Carte de vote du noyau B (signe −1) sur le champ T_feuille : rapport du score aux centres sur le score aux milieux de Delaunay, sur le développement, avec et sans troncature à 0,6 × maille. Seuil fixé avant par independent-evaluator.

### OBJ-V5 — Modèle A : la précision de 0,22 à 0,26 vient du seuil relatif et d'une séparabilité faible, et en dense A sur ExG sera aveugle
- **Énoncé.**
  - (a) τ × max est un point de fonctionnement arbitraire : sur une scène à plants isolés avec beaucoup de fond, la suppression des non-maxima à 0,8 m laisse un grand nombre de maxima locaux au-dessus de 25 % du maximum. La précision mesure alors surtout la surface de fond.
  - (b) La séparabilité reste faible même avec un seuil idéal : médiane aux centres 2,35 contre 95e centile au hasard 1,75 [M, E-002]. Au-delà de 5 % de faux candidats par position, la précision restera basse quelle que soit la règle.
  - (c) En dense, A travaille sur l'ExG normalisé, qui est **chromatique** et efface les ombres entre limbes. Or le seul signal mesuré est dans la **luminance** à l'échelle de la feuille (OBJ-V3). Les jointifs synthétiques (précision 0,46 à 0,53) ne sont pas un bon signe : la densité de vrais centres remplit l'espace, ce qui monte mécaniquement la précision au même seuil.
- **Appui.** [M] E-002 (`resultats.md`) ; [M] E-expl-OE-01 ; [H] pour (c), à mesurer.
- **Correction.**
  - Évaluer A par la précision au budget égal au nombre vrai, ou par l'aire sous la courbe rappel-précision, plutôt que par un τ.
  - Pré-enregistrer A′ (seuil MAD) comme le propose leaf-mathematician.
  - Ajouter une variante A-luminance (passe-haut de la clarté à l'échelle de W).
- **Expérience qui tranche.** Sur le développement dense (banavista, lasuiza), contraste de S_A aux centres contre les points de demi-maille : A-ExG contre A-luminance. En dense, la prédiction est que le rapport A-ExG tombe sous celui de la demi-maille (P-A5), et qu'A-luminance fait mieux.

### OBJ-V6 — HF-06 : sur banavista, le signe contredit l'explication « tache seule », mais le contrôle décisif manque
- **Énoncé.**
  - Une tache isotrope produit un gradient radial (s > 0). On mesure s < 0, y compris dans l'anneau interne 0,15–0,4 m (≈ −0,11). L'alignement observé n'est donc pas celui d'une tache : ce sont des structures allongées radiales.
  - Ce constat ne remplace pas le contrôle 1 de HF-06 (gaussiennes isotropes aux centres). Une tache entourée d'un anneau sombre, par exemple d'ombre, donnerait aussi des bords tangents à l'anneau (s > 0), pas s < 0. Le risque restant est donc plutôt celui des **rangs** (bords d'inter-rangs radiaux vus depuis des centres alignés), visible dans la demi-maille de DJI_0642 (−0,157).
- **Appui.** [M exploratoire E-expl-OE-01].
- **Correction.**
  - Ajouter le contrôle « image tournée de 90° autour du centre de l'image, centres non tournés », qui conserve les rangs mais rompt les plants.
  - Ajouter le contrôle tache synthétique de scientific-challenger.
- **Expérience qui tranche.** Celle d'OBJ-V3, avec ces deux contrôles en plus.

## 3. Suite proposée

1. Faire attribuer un identifiant à E-expl-OE-01 (exploratoire, développement).
2. Fixer avec independent-evaluator le critère de l'E-NNN d'OBJ-V3 avant tout nouveau lancement.
3. Dans `orientation.py` : choix d'échelle par pixel au maximum de cohérence ; format (angle de la structure, fiabilité, échelle) à convenir avec convergence-engineer.
