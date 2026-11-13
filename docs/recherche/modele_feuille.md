# Modèles mathématiques de la feuille et du plant

Rédacteur : leaf-mathematician. Version du 7 novembre 2026. Implémentation de référence : `comptage_math/feuille.py`. Contrôle synthétique : `out/comptage_math/leaf-mathematician/`. Journal : `docs/recherche/notes/leaf-mathematician.md`.

**Avertissement (règle 1).** La fonction de Philemon est inconnue. Les deux modèles ci-dessous sont des **formulations compatibles avec des indices** (gaussiennes, formes, couleurs, stries, orientations), pas une reconstitution. Tous les intervalles de paramètres sont **[H]** tant que banana-morphology ne les a pas sourcés ; ils viennent de `docs/comprendre_bananier.md` (écrit de mémoire) et de lectures à l'œil sur dji_0546, dji_0548 et Flora Pluas (développement), consignées en [O] dans le journal.

Écrit pour être attaqué : chaque modèle se termine par ses prédictions réfutables, et la section 5 rapporte le contrôle synthétique, y compris ses échecs.

---

## 0. Conventions et notations

- Image RVB I(x) ∈ [0,1]³, x = (x, y) en mètres, résolution Δ (m/px). y vers le bas, angle θ de l'axe x vers l'axe y.
- e(θ) = (cos θ, sin θ), e⊥(θ) = (−sin θ, cos θ).
- Pour un plant de centre c et une feuille de direction θ_k : u = (x − c)·e(θ_k) (le long de la feuille), t = (x − c)·e⊥(θ_k) (en travers).
- v(x) = (2G − R − B)/(R + G + B) : indice de végétation ExG normalisé.
- Un plant = centre c (point de sortie du pseudo-tronc, ce que pointent les annotations) + K feuilles.

## 1. Pourquoi ces deux modèles

| | Modèle A : étoile de gaussiennes anisotropes | Modèle B : bandes nervurées striées et profil radial |
| --- | --- | --- |
| Information utilisée | amplitude basse fréquence de v (où est le vert, en taches allongées) | orientation haute fréquence (stries, nervure) et couleur |
| Estimateur du centre | banque de filtres adaptés **ancrés au centre** ; vraisemblance gaussienne profilée | vraisemblance **von Mises** d'un champ d'orientation ; une convolution complexe |
| Indices couverts (formulation compatible avec…) | gaussiennes, formes, orientations (implicite) | stries, orientations, couleurs |
| Hypothèses du brief | H1 (terme central), H2, H4 (implicite), H7 | H3, H4, H5, H7 |

Le brief suggérait pour A un vote d'orientation. Je l'ai écarté de A et placé dans B : si A et B votaient tous deux le long d'axes, ils ne différeraient que par la façon d'estimer l'orientation, et une expérience ne pourrait guère les départager. Ici, A n'estime aucune orientation locale (il corrèle des gabarits entiers) et B n'utilise aucune amplitude de végétation (seulement l'orientation, pondérée par un masque). Leurs échecs attendus diffèrent (section 4), ce qui rend les expériences discriminantes.

---

## 2. Modèle A — étoile de gaussiennes anisotropes

### 2.1 Équations

**Feuille.** Sur l'indice de végétation :

g_k(x) = a_k · exp( −(u − μ_k)² / (2σ_L,k²) − t² / (2σ_W,k²) ),  avec μ_k = r0_k + L_k/2, σ_L,k = L_k/4, σ_W,k = W_k/4.

La feuille est une gaussienne anisotrope dont le grand axe est **radial** et dont le centre de masse est à μ_k du centre du plant. Le choix σ = longueur/4 place ±2σ sur le limbe.

**Plant.**

v(x) = b(x) + a_c · exp(−|x − c|² / (2σ_c²)) + Σ_{k=1..K} g_k(x) + ε(x),  ε ~ N(0, σ_ε²) i.i.d.

Le terme central a_c (pseudo-tronc, feuille cigare) est la composante H1. b(x) est un fond lent (sol, herbe). Plusieurs plants s'additionnent, puis v est écrêté à [0, 1] (rendu : `rendre_scene_A`).

### 2.2 Paramètres et intervalles

| Paramètre | Sens | Intervalle | Étiquette |
| --- | --- | --- | --- |
| K | feuilles visibles | 4–12 (jeunes plants : 4–8) | [H] ; [O] 4 à 8 sur dji_0546/0548 |
| L | longueur du limbe | 0,8–2,5 m | [H] « feuilles de 2 à 3 m » (comprendre_bananier, de mémoire, pétiole compris ?) ; [O] 1–2 m sur jeunes plants |
| W | largeur maximale | 0,35–0,9 m (W/L ≈ 0,3–0,45) | [H] ; [O] 0,4–0,7 m |
| r0 | centre → base du limbe | 0,1–0,6 m | [H] ; [O] vide central de 0,1–0,4 m |
| θ_k | directions | quasi uniformes, écart minimal ≈ 2π/K ± 15° | [H] phyllotaxie à sourcer |
| a_k | contraste | 0,5–1 (relatif) | [H] |
| a_c, σ_c | tache centrale | 0–0,5 ; 0,05–0,2 m | [H] |
| espacement | entre plants | ≈ 2–2,5 m | [O] 2,1–2,3 m (dji_0546/0548) ; [S de mémoire] comprendre_bananier |

### 2.3 Vraisemblance et filtre

Log-vraisemblance gaussienne, b supposé connu (ou retiré par le filtre) :

ℓ(c, θ, a) = −(1/2σ_ε²) ‖v − b − Σ_k a_k g_k(·; c, θ_k)‖².

Si les feuilles ne se recouvrent pas (⟨g_j, g_k⟩ ≈ 0), on profile les amplitudes : â_k = ⟨v − b, g_k⟩/‖g_k‖², d'où

max_a ℓ = const + (1/2σ_ε²) Σ_k ⟨v − b, ĝ_{θ_k}(· − c)⟩², avec ĝ normalisé.

Puis le maximum sur les θ_k (feuilles distinctes) revient à garder les K plus fortes réponses localement maximales en θ. D'où le **filtre A** :

- R_θ(c) = ⟨v, h_θ(· − c)⟩ pour N_θ = 16 directions, où h_θ = G(μe(θ); σ_L, σ_W)/ΣG − G(μe(θ); σ_L, 3σ_W)/ΣG est la gaussienne de la feuille **moins un surround latéral** de même masse. Le gabarit est à somme nulle : il retire b(x) localement et ne répond pas à une végétation uniforme.
- S_A(c) = ( (1/m) Σ_{les m plus grands} [R_θ(c)]₊² )^{1/2}, restreint aux maxima locaux en θ, avec m = 4.
- Centres = maxima locaux de S_A (suppression des non-maxima, rayon 0,8 m).

Implémentation : `gabarit_A`, `reponses_A`, `score_etoile`, `filtre_A`.

### 2.4 Identifiabilité

**Du centre.** La matrice d'information de Fisher de c est la somme, sur les feuilles, de contributions de rang 1 :
- en travers (direction e⊥(θ_k)), de poids ∝ a_k² σ_L/σ_W³ ;
- le long de l'axe (e(θ_k)), de poids ∝ a_k² σ_W/σ_L³.

Le rapport vaut (σ_L/σ_W)² ≈ (L/W)² ≈ 5 à 10. Le centre est donc estimé surtout comme **l'intersection des axes des feuilles** : A est, sans le dire, un estimateur d'intersection d'axes.
- K = 1 : non identifiable le long de l'axe (c glisse avec r0).
- K = 2 feuilles opposées : non identifiable le long de leur axe commun (c ↔ r0).
- K ≥ 3 directions non colinéaires : identifiable.

**Erreur de modèle dominante.** La précision limitée par le bruit est de l'ordre du centimètre (borne de Cramér-Rao pour la translation d'une gaussienne : écart-type = (σ_ε Δ/a) · (2σ_L/(πσ_W))^{1/2} ≈ 1,5 cm pour σ_ε/a = 0,5, Δ = 2 cm, σ_L = 0,4 m, σ_W = 0,12 m). Ce n'est pas elle qui limite. Si l'axe de la feuille k passe à une distance η_k du centre (pétiole courbe, limbe tombant, [O] quelques dizaines de cm), le biais du centre vaut à peu près (2/K)·Σ_k η_k e⊥(θ_k), d'écart-type ≈ σ_η (2/K)^{1/2}. Pour σ_η = 0,2 m et K = 6 : ≈ 0,16 m, sous la tolérance de 0,5 m [H].

**Selon la résolution.** A n'a besoin que de résoudre σ_W = W/4 (0,09 à 0,22 m).

| Δ | σ_W en px | Verdict |
| --- | --- | --- |
| 1 cm/px | 9–22 | identifiable, calcul à 5 cm/px suffit |
| 2 cm/px | 4,5–11 | identifiable |
| 3 cm/px | 3–7 | identifiable |
| 5 cm/px | 1,8–4,4 | identifiable (limite basse pour W = 0,35 m) |

En dessous d'environ 10 cm/px, σ_W < 1 px : le modèle dégénère en H1 (tache isotrope).

### 2.5 Sensibilité à une erreur d'échelle de ±20 %

Le gabarit est déformé d'un facteur s = 0,8 ou 1,2.
- Décalage le long de l'axe : δ = 0,2μ. La corrélation de deux gaussiennes décalées de δ perd un facteur exp(−δ²/(4σ_L²)), soit ≈ 0,95 pour μ = 0,9 m et σ_L = 0,4 m.
- Largeur : perte ((2s/(1 + s²))^{1/2}) ≈ 0,99 par dimension.
- Position : par symétrie de l'étoile, biais ≈ 0 au premier ordre ; reste (2/K)·Σ 0,2μ_k e(θ_k)·(σ_W/σ_L)², négligeable.

**Prédiction [H] :** A est insensible à ±20 % (perte de réponse < 10 %, rappel inchangé). Le paramètre sensible à l'échelle est le rayon de suppression des non-maxima (0,8 m ; à +20 % il vaut 0,96 m, encore sous la demi-distance entre plants de 1,05–1,15 m).

### 2.6 Coût sur processeur

- ExG et rééchantillonnage à 5 cm/px : 1 hectare = 2 000 × 2 000 px.
- 16 corrélations par transformée de Fourier (noyau d'environ 60 × 60 px), puis un tri sur 16 valeurs par pixel.
- Ordre de grandeur théorique : 17 transformées de 4 Mpx, quelques secondes.
- [M] Contrôle synthétique (section 5, E-002) : **2,4 s par hectare à 2 cm/px** avec OpenCV multi-cœur, hors lecture d'image, à comparer aux ≈ 2 s/ha du v5.

### 2.7 Échecs attendus

- **Canopée dense** : v ≈ constant, le gabarit à somme nulle ne répond plus que par les ombres entre limbes. Pics à mi-chemin entre plants, ou là où trois feuilles de plants différents se rencontrent.
- **Herbe et adventices** : les taches vertes allongées répondent (A ne voit que du vert).
- **Palmiers** : couronne de 8–12 m (à sourcer), palmes de 4–7 m. Le gabarit à L ≤ 2,5 m répond le long des palmes : beaucoup de faux centres le long des rachis, et pas forcément au cœur.
- **Jeunes plants à 2–3 feuilles** : intersection mal posée.

### 2.8 Prédictions réfutables du modèle A

Chaque expérience se fait sur le **développement** seulement. Le seuil chiffré est à fixer par independent-evaluator avant le lancement (règle 3).

| Id | Prédiction | Expérience | Contrôle |
| --- | --- | --- | --- |
| P-A1 (H2) | En un centre annoté, la réponse R_θ en fonction de θ a au moins 3 maxima locaux nettement au-dessus du niveau des pixels de végétation pris au hasard | jeunes bananiers dji_0546/0548, plantas_platano lote_2 : profil angulaire R_θ(c) aux centres annotés | même profil en des points de végétation tirés à plus de 1 m de tout centre ; et aux centres annotés après rotation aléatoire de chaque gabarit autour de son axe d'ancrage (orientations mélangées) |
| P-A2 (H2, H4) | Les directions de ces maxima pointent vers l'extrémité des feuilles visibles, et l'écart angulaire au plus proche axe de feuille est plus petit qu'avec des centres déplacés de 1 m | même données ; le « vrai » axe est remplacé par la direction du maximum de v entre 0,5 et 1,5 m autour du centre (aucune annotation nouvelle) | centres déplacés de 1 m dans une direction aléatoire |
| P-A3 (H1 contre H2) | S_A sépare les centres annotés des points de végétation mieux que le témoin isotrope (laplacien de gaussienne au même σ, terme a_c seul) | rappel des candidats à 1 m, au même budget de candidats que la baseline ExG | baseline `scripts/baseline_comptage.py` |
| P-A4 (H7) | Rappel inchangé à ±5 points quand l'échelle du gabarit varie de ±20 % | balayage s ∈ {0,8 ; 1 ; 1,2} sur le développement | s = 1 |
| P-A5 | En canopée jointive (Flora Pluas, Nestor Macias), le contraste S_A(centre)/S_A(hasard) chute d'au moins un facteur 2 par rapport aux jeunes plants | même mesure | jeunes bananiers |

**A est réfuté comme modèle utile** si P-A1 et P-A3 échouent toutes les deux : le rayonnement des feuilles n'apporterait alors rien au-delà d'une tache.

---

## 3. Modèle B — bandes nervurées striées et profil radial de couleur

### 3.1 Équations

**Nervure.** C'est une parabole dans le repère de la feuille :

t = κ_k u²/2, abscisse le long du limbe s = u − r0_k, écart à la nervure ν = t − κ_k u²/2, avec 0 ≤ s ≤ L_k.

**Limbe.** C'est une bande autour de la nervure :

w_k(s) = (W_k/2) · sin(π s/L_k)^{0,4}  (forme oblongue, pointe et base arrondies),
m_k(x) = 1[|ν| ≤ w_k(s)] (adouci sur un pixel).

**Stries.** Ce sont les déchirures le long des nervures secondaires, d'angle β avec la nervure, d'espacement λ :

φ_k(x) = 2π (s sin β − |ν| cos β)/λ_k + ψ_k(s)  (chevron ; ψ lent et aléatoire),
T_k(x) = 1 − c_s · α_j · ((1 + cos φ_k)/2)^6,  α_j ~ U[0,2 ; 1] tiré à chaque période (déchirures irrégulières).

**Nervure claire.** N_k(x) = exp(−ν²/(2σ_n²)), avec σ_n = largeur de la nervure/2,355.

**Couleur.** Elle suit un profil radial autour du centre (H5b, H5c) :

C_k(x) = [ (base_k · T_k(x) · (1 + ΔL e^{−r²/2r_c²})) (1 − 0,6 N_k) + 0,6 N_k · c_nervure ],  r = |x − c|,

où base_k = vert, ou brun si la feuille est sèche (la plus âgée, en périphérie). S'y ajoutent la feuille cigare (disque vert clair de 8 cm au centre) et les pétioles (segments fins du centre à la base du limbe).

**Plant.** Composition par occultation, des feuilles les plus âgées aux plus jeunes : I ← I(1 − m_k) + C_k m_k. Rendu : `rendre_scene_B`.

### 3.2 Paramètres et intervalles (en plus de ceux de A)

| Paramètre | Sens | Intervalle | Étiquette |
| --- | --- | --- | --- |
| κ | courbure de la nervure | \|κ\| ≤ 0,6/L (flèche ≤ 0,3 L) | [H] ; [O] axes qui manquent le centre de quelques dizaines de cm |
| λ | espacement des déchirures | 0,03–0,20 m | [H] ; [O] Flora Pluas : quelques cm à ≈ 20 cm |
| β | angle stries/nervure | 60°–90° | [H] ; [O] Flora Pluas : presque 90° ; **à sourcer** (banana-morphology) |
| c_s | profondeur des stries | 0–0,8 (0 = feuille intacte) | [H] dépend de l'âge et du vent |
| largeur de nervure | | 0,02–0,06 m | [H] |
| r_c, ΔL | centre plus clair | 0,1–0,3 m ; 0,1–0,35 | [H] H5b ; [O] la jeune feuille claire n'est pas centrée exactement sur le point annoté |
| feuille sèche | | 0–2 par plant, en périphérie | [H] H5c ; [O] sèches surtout au sol, entre les plants |

### 3.3 Vraisemblance et filtre

**Observation.** C'est le champ d'orientation en angle doublé (tenseur de structure, ici à l'échelle des stries) :

z(x) = ⟨(∂_x I_σg + i ∂_y I_σg)²⟩_σt / ⟨|∇I_σg|²⟩_σt,  σ_g = λ/4, σ_t = λ.

arg z = 2 φ(x), où φ est la direction du gradient dominant ; |z| ∈ [0,1] est la cohérence. z est pondéré par un masque de végétation (ExG lissé). Pour des stries perpendiculaires à la nervure (β = 90°), le gradient dominant est **parallèle à la nervure, donc radial**.

**Modèle d'observation.** C'est un mélange : pixel de feuille du plant c, ou fond.

p(φ_i | c) = π_i(c) · VM₂(φ_i ; ψ_i(c), κ) + (1 − π_i(c))/π,  ψ_i(c) = arg(x_i − c),

où VM₂ est une loi de von Mises sur les orientations (période π). π_i(c) est la probabilité qu'un pixel à distance r du centre appartienne à une feuille du plant : K limbes de largeur W couvrent une fraction K W/(2π r) du cercle de rayon r, d'où π(r) = ρ(r) = min(1, K W/(2π r)) sur [r_in, r_out].

**Développement à faible concentration.** On a π·VM₂ − 1 ≈ κ cos 2(φ − ψ), d'où

log p(φ | c)/p₀ ≈ Σ_i ρ(|x_i − c|) κ cos 2(φ_i − ψ_i(c)) = κ · Re[ Σ_i z_i k(x_i − c) ],  k(d) = ρ(|d|) e^{−2i arg d}.

C'est **une seule convolution complexe** du champ z par le noyau k. Comme k(−d) = k(d), corrélation et convolution coïncident. k est à moyenne nulle sur chaque cercle, donc un champ d'orientation uniforme (rangée, labour) ne vote pas. Ce noyau est un filtre de symétrie de rotation d'ordre 2 de la famille de Bigün [S : J. Bigün, T. Bigün, K. Nilsson, « Recognition by symmetry derivatives and the generalized structure tensor », IEEE TPAMI 26(12), 1590–1605, 2004, doi:10.1109/TPAMI.2004.126 ; rapprochement de ma part, la correspondance exacte des notations est à vérifier par scientific-researcher].

**Terme de couleur (H5b).** Λ_col(c) = (Y ⋆ (G_{r_c} − G_{3r_c}))(c), où Y est la clarté.

**Score.** Les deux termes sont normalisés de façon robuste (médiane et MAD sur l'image) :

S_B = sgn · Λ̃ + w_col · Λ̃_col,

où sgn = +1 si les stries dominent le tenseur (prédiction du modèle) et w_col = 0 par défaut. Implémentation : `champ_orientation`, `noyau_B`, `score_orientation_B`, `score_couleur_B`, `filtre_B`.

**Effet de l'angle β (conséquence directe du modèle).** Les deux demi-limbes ont des stries inclinées de ±δ, avec δ = 90° − β. Leurs contributions en angle doublé s'ajoutent en e^{2i(ψ+δ)} + e^{2i(ψ−δ)} = 2 cos(2δ) e^{2iψ}. La direction reste donc sans biais, mais l'amplitude est multipliée par cos 2δ :
- 1 à β = 90° ;
- 0,5 à β = 60° ;
- **0 à β = 45°** ;
- **négative** en dessous de 45°.

### 3.4 Identifiabilité

**Du centre.** C'est l'intersection des axes, comme en A, mais l'axe est estimé par la texture et non par la forme. La précision par feuille est de l'ordre de r · σ_φ/√N_eff, où N_eff est le nombre de périodes de stries indépendantes sur le limbe (≈ L/λ, soit 10 à 40). Avec σ_φ de 15° et K = 6, l'ordre de grandeur est le décimètre [H]. Le biais dû à la courbure est absorbé par κ_VM, pas modélisé dans le filtre.

**Selon la résolution.** B a besoin des stries : une période λ doit couvrir au moins 4 px pour une estimation d'orientation stable (2 px au critère de Nyquist), et la nervure au moins 2 px.

| Δ | λ résolu (≥ 4 px) | Nervure (≥ 2 px) | Verdict |
| --- | --- | --- | --- |
| 1 cm/px | λ ≥ 4 cm : presque toute la plage | oui | identifiable |
| 2 cm/px | λ ≥ 8 cm : la moitié haute de la plage | limite | identifiable si les déchirures sont larges |
| 3 cm/px | λ ≥ 12 cm : grandes déchirures seules | non | partiellement identifiable |
| 5 cm/px | λ ≥ 20 cm : rien | non | **non identifiable** : B dégénère en tenseur de structure des bords de feuille, de **signe opposé** (P-B3) |

Les jeux à 5 cm/px (ré-échantillonnage du v5, Multiple tree) sont donc hors domaine pour B, sauf travail à la résolution native.

### 3.5 Sensibilité à une erreur d'échelle de ±20 %

- **λ faux de ±20 %** : le tenseur de structure à dérivée gaussienne n'est pas sélectif (bande passante de plus d'une octave). Perte faible attendue.
- **ρ(r) étiré de ±20 %** : ρ est large et ∝ 1/r, donc perte faible.
- **Risque réel** : à 5 cm/px annoncés pour 6 cm/px réels, σ_g/λ change et peut faire basculer le tenseur des stries vers les bords, donc changer de signe. B est donc sensible à l'échelle **près du seuil d'identifiabilité** et insensible au-dessus [H].

### 3.6 Coût sur processeur

- Tenseur de structure à la résolution native : 5 filtres gaussiens sur 25 Mpx/ha à 2 cm/px.
- Rééchantillonnage de z à 10 cm/px : 1 Mpx/ha.
- Une convolution complexe, soit 2 corrélations réelles avec un noyau de 37 × 37.
- [M] Contrôle synthétique : **4,9 s par hectare à 2 cm/px** (OpenCV et scipy, hors lecture d'image). L'essentiel du temps passe dans les filtres gaussiens à pleine résolution.

### 3.7 Échecs attendus

- **Canopée dense** : les stries restent visibles ([O] Flora Pluas), donc le champ d'orientation reste informatif là où A s'aveugle. En revanche, les feuilles voisines votent aussi : pics secondaires attendus sur le segment entre deux centres voisins, d'amplitude relative ≈ 2/K [H].
- **Palmiers** : les folioles produisent aussi des stries (contre-exemple de H3). D'après le facteur cos 2δ, la réponse dépend de l'angle d'insertion des folioles sur le rachis : nulle vers 45°, forte vers 90° [H, à sourcer]. Les palmiers à folioles insérées presque à angle droit seront des faux positifs.
- **Feuilles intactes** (jeunes, c_s ≈ 0) : il n'y a plus de stries. Le tenseur voit les bords et la nervure, donc le signe s'inverse. **Le contrôle synthétique montre que ce cas domine même avec des stries** (section 5).
- **Résolution ≥ 5 cm/px** : non identifiable.

### 3.8 Prédictions réfutables du modèle B

| Id | Prédiction | Expérience (développement) | Contrôle |
| --- | --- | --- | --- |
| P-B1 (H3b, H4) | À échelle fine (σ_g = λ/4), l'orientation du gradient dominant sur les pixels de végétation entre 0,4 et 1,5 m d'un centre annoté est concentrée autour de la direction radiale (cos 2(φ − ψ) moyen > 0) | dji_0546/0548 (1,1 cm/px), Flora Pluas (≈ 1 cm/px) : histogramme de φ − ψ | centres tirés au hasard ; orientations permutées entre pixels |
| P-B2 (H3a) | La moyenne de cos 2(φ − ψ) décroît avec la résolution et change de signe entre 2 et 5 cm/px | mêmes images rééchantillonnées à 1, 2, 3, 5 cm/px (planches d'image-analyst) | idem |
| P-B3 (bascule d'échelle) | Le signe de Λ aux centres est **positif** à σ_g = λ/4 et **négatif** à σ_g = W/4 | mesure de Λ aux centres annotés, deux échelles | centres au hasard |
| P-B4 (H5b) | Le profil radial de clarté autour des centres annotés décroît entre 0 et 0,3 m (centre plus clair) | profil moyen de Y(r) aux centres | centres déplacés de 1 m. **Contre-indice déjà vu** : [O] vide sombre au centre sur dji_0546/0548 ; je prédis tout de même le signe positif, pour pouvoir être réfuté |
| P-B5 (H5c) | La fraction de pixels bruns (teinte et saturation à fixer avant) croît avec r entre 0,5 et 2 m | idem | idem |
| P-B6 (H3, palmiers) | Sur les images sans bananier du développement (Multiple tree, zones d'entraînement), Λ aux centres de couronne de palmier est inférieur à Λ aux centres de bananier, à résolution égale | comparaison des distributions | centres au hasard |

**B est réfuté comme modèle « stries »** si P-B1 échoue à 1 cm/px. Le vote pourrait alors survivre en version « bords » (signe négatif), mais ce serait une autre formulation, à pré-enregistrer à part.

---

## 4. Comparaison A / B

| Critère | A : étoile de gaussiennes | B : bandes striées + couleur |
| --- | --- | --- |
| Indices de Philemon couverts (formulation compatible avec…) | gaussiennes, formes, (orientations) | stries, orientations, couleurs |
| Hypothèses | H1, H2, H4 implicite, H7 | H3, H4, H5, H7 |
| Résolution minimale | ≈ 5 cm/px (σ_W ≥ 2 px) ; 10 cm/px = dégénérescence en H1 | ≈ 1–2 cm/px pour les stries ; non identifiable à 5 cm/px |
| Paramètres libres du détecteur | L, W, r0, m, N_θ, surround | λ, r_in, r_out, K·W, signe, w_col |
| Coût [M synthétique] | 2,4 s/ha à 2 cm/px | 4,9 s/ha à 2 cm/px |
| Sensibilité à ±20 % d'échelle | faible (prédite et [M] synthétique) | faible au-dessus du seuil d'identifiabilité, forte près du seuil |
| Canopée dense | échec attendu (v uniforme) ; [M] synthétique : rappel 0,62–0,82 | meilleur en principe (stries visibles) ; non démontré, cf. section 5 |
| Palmiers | faux centres le long des palmes (échelle différente) | faux positifs si folioles proches de 90° |
| Herbe, adventices | sensible (vert = signal) | peu sensible si l'herbe est isotrope |
| Feuilles intactes, jeunes | bon | inversion de signe (bords > stries) |
| Résultat du contrôle synthétique | rappel ≥ 0,94, **précision 0,22–0,26 : critère manqué** | **rappel 0 : échec**, signe de Λ opposé à la prédiction |

**Expérience qui départage A et B (proposée).**
- Sur le développement, mesurer séparément aux centres annotés le contraste centre/hasard de S_A et de Λ_B (au signe pré-enregistré), en jeunes plants et en canopée jointive.
- Prédiction : A > B en jeunes plants, B > A en canopée jointive à 1 cm/px.
- Si A domine partout, l'indice « stries » n'apporte rien au comptage à ces résolutions.

---

## 5. Contrôle synthétique (vérité connue)

Critère écrit avant le lancement dans `docs/recherche/notes/leaf-mathematician.md`.

Commande :

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/leaf-mathematician/controle_synthetique.py
```

Graine 20261107. Résultats complets : `out/comptage_math/leaf-mathematician/resultats.md` et `resultats.json`. Identifiant d'expérience : **E-002** (attribué par le chef d'orchestre). Portée réduite par C-001 (section 7) : test de non-régression du code, pas appui au modèle.

**Résultats [M, synthétique, aucune image réelle].**

| Détecteur sur son propre rendu, « isolés » (36 plants) | 1 cm/px | 2 | 3 | 5 |
| --- | --- | --- | --- | --- |
| A : rappel / précision / erreur médiane | 1,00 / 0,26 / 0,16 m | 1,00 / 0,22 / 0,16 m | 1,00 / 0,24 / 0,16 m | 0,94 / 0,23 / 0,21 m |
| B : rappel / précision | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 (déclaré non identifiable d'avance) |

**Critère : non atteint pour les deux modèles.**
- **A** retrouve chaque centre à moins de 0,5 m (erreur médiane 0,16 m, conforme à l'ordre de grandeur de § 2.4). Mais la règle de seuil pré-enregistrée (τ = 0,25 × max) garde 4 fois trop de pics : touffes d'herbe, milieux de feuilles, sol bruité ([O] `vignette_isoles_renduB_detA_2cm.png`). Le contrôle « centres au hasard » passe (médiane aux centres 2,35 > 95e centile au hasard 1,75), mais la marge est faible.
- **B** échoue complètement : Λ aux vrais centres est **négatif** (médiane −6,7 en score normalisé ; à 1 cm/px, 0 % de centres positifs). Le diagnostic `diagnostic_signe_B.py` (graine distincte, lancé après le contrôle) montre que le code respecte la convention de signe : Λ = +466 sur des stries pures, −309 sur des rayons pleins. Sur un plant B complet, Λ = −242 ; sans stries, −274 ; sans nervure, −123. **Dans le modèle B lui-même, les bords de limbe et la nervure dominent le tenseur de structure, même à σ_g = λ/4 ; les stries ne pèsent qu'environ +30 sur −270.** La prédiction P-B3 (bascule de signe entre échelle fine et grossière) est réfutée sur le synthétique : médiane −166 en fin, −70 en grossier.
- **Contrôle « orientations mélangées » de B** : rappel 0,25 < 0,30, donc formellement atteint, mais sans portée, puisque le rappel non mélangé est nul.
- **Échelle ±20 %** : A garde un rappel de 1,00 et 0,97 (prédiction P-A4 vérifiée en synthétique). B reste à 0.
- **Configuration « jointifs »** (sans critère) : A atteint un rappel de 0,62 à 0,82 et une précision de 0,38 à 0,53, avec une erreur médiane de 0,22 à 0,28 m. B est à 0.
- **Temps** : A 2,4 s/ha, B 4,9 s/ha à 2 cm/px.

Conformément aux conditions d'arrêt, **les modèles ne sont pas retouchés sur ces scènes.** Les corrections possibles sont des **nouvelles formulations**, à pré-enregistrer et à tester sur une nouvelle graine :
- **B′ « bords et nervure »** : sgn = −1, σ_g = largeur de nervure. C'est une formulation compatible avec l'indice « orientations » sans les stries.
- **B″ « stries sélectives »** : remplacer le tenseur de structure par l'énergie d'un banc de Gabor accordé à λ, puis blanchir l'énergie des bords (par exemple en retirant la réponse du tenseur à σ = W/4). C'est la seule version qui teste réellement l'indice « stries ».
- **A′** : seuil absolu sur S_A, normalisé par le MAD de la scène, au lieu de τ × max. Cette règle doit être fixée avant le nouvel essai.

## 6. Ce que ce document ne dit pas

- Aucun score sur image réelle (règle 8). Tout [M] ci-dessus est synthétique.
- Les intervalles sont à sourcer par banana-morphology (`docs/recherche/morphologie.md`, absent au 7 novembre).
- La visibilité réelle des stries à 2–3 cm/px est à mesurer par image-analyst.

---

## 7. Concertation C-001 : réponses aux objections

Objections lues dans `docs/recherche/notes/scientific-challenger.md` (OBJ-C1 à OBJ-C9) et `docs/recherche/notes/orientation-engineer.md` (OBJ-V1 à OBJ-V6).

Mesures utilisées :
- E-002 (mon contrôle) ;
- E-003 (mesure exploratoire d'orientation-engineer sur banavista) ;
- E-004 (sa décomposition synthétique de B) ;
- l'essai synthétique hors famille du § 7.2, sur une graine nouvelle, lancé après avoir écrit son critère dans `docs/recherche/notes/leaf-mathematician.md`. Identifiant à attribuer ; noté ici **E-synth-HF**.

### 7.1 Réponses

| Objection | Réponse | Ce qui change |
| --- | --- | --- |
| OBJ-C1 circularité | **acceptée** | E-002 n'est plus qu'un test de non-régression. Mesuré en E-synth-HF : sur des rendus hors famille, le rappel de A au budget chute de 0,30 (v0 → v3), au-delà du seuil de 0,2. Aucun contrôle synthétique rendu par la famille du détecteur ne sera plus présenté comme appui. |
| OBJ-C2 A = tache ? | **acceptée** | A-iso devient le témoin obligatoire du cycle 1 (`filtre_A_iso`). En synthétique, A dépasse nettement A-iso (rappel au budget 0,46–0,48 contre 0,05–0,11 en v0–v2). C'est indicatif seulement : la question se tranche sur le développement réel (§ 8.5). |
| OBJ-C3 demi-maille | **acceptée avec modification** | Mesuré en E-synth-HF : 37 à 54 % des fausses détections de A sont entre 0,9 et 1,4 m d'un centre dès que le centre n'est plus marqué (v1–v3). La suppression des non-maxima de 0,8 m est donc déclarée inadaptée. Modification : plutôt que d'ajouter une variante « Voronoï », le rayon de suppression entre dans la grille réglée sur le développement ({0,8 ; 1,0 ; 1,2} m), et le contrôle demi-maille sur le développement devient une condition d'envoi sur `val_iter` (§ 8.6). |
| OBJ-C4 borne haute | **acceptée** | Prédictions (a), (b), (c) pré-enregistrées (§ 8.7). E-synth-HF va déjà dans ce sens : au budget, le rappel à 0,5 m n'est que de 0,48 en v0 (contre 0,73–0,82 avec la règle τ d'E-002). |
| OBJ-C5 B corrigé après coup | **acceptée avec modification** | B, B′ et B″ sortent du cycle 1. Je maintiens une nuance : la prémisse de B′ (signe −1, axes linéaires) n'est pas tirée seulement d'E-002 ; elle a un appui indépendant sur le développement réel (E-003, 5/5 images négatives). B′ reste donc une formulation légitime pour le cycle 2, à pré-enregistrer avec les contrôles d'OBJ-C5 et d'OBJ-C6. |
| OBJ-C6 B′ = détecteur de lignes | **acceptée** | Le contrôle « pics près des bords forts » et la rotation de 90° sont des conditions d'entrée de B′ au cycle 2. |
| OBJ-C7 grille JPEG de 8 px | **acceptée** | B″ n'entre pas sans le contrôle de décalage de 4 px et l'exclusion des harmoniques de 1/8 px. L'indice « stries » perd presque tout son domaine en dense (E-003, Gabor 6 cm : −0,04) ; B″ n'est pas prioritaire. |
| OBJ-C8 seuil et comparaison | **acceptée avec modification** | Règle A′ (`pics_mad`) : z = (S − médiane)/MAD ≥ z0. Modification : z0 est choisi sur le développement dense par le même critère que les autres paramètres (§ 8.3), pas par égalisation des comptes, parce que l'objectif D-003 est un F1. L'égalisation des comptes est rapportée à côté. Courbe rappel-budget à 1 m rapportée en plus. |
| OBJ-C9 plafond de variantes | **acceptée** | Une seule méthode complète sur `val_iter` au cycle 1 : A′. A-iso est un témoin. Le choix du canal, de l'échelle et du rayon se fait par grille sur le développement : ce sont des hyperparamètres d'une même méthode, pas des variantes envoyées sur `val_iter`. **Point à valider par independent-evaluator.** |
| OBJ-V1 signes opposés dans B | **acceptée** | Les deux canaux (axes linéaires, s < 0 ; stries, s > 0) ne seront jamais mélangés dans un même tenseur avant le vote. P-B3 était mal posée : elle supposait qu'un seul mécanisme dominait à chaque échelle. |
| OBJ-V2 échelle d'intégration | **acceptée** | Le diagnostic d'E-004 est juste : σ_t = λ place un bord dans chaque fenêtre. La nervure, de même bande que les stries, est une propriété réelle, pas un artefact. Pour un éventuel B″ : σ_t ≤ λ/2, gradients normalisés, masque de nervure. |
| OBJ-V3 stries absentes en dense réel | **acceptée** | Statut de P-B1 : **non soutenue** sur banavista (E-003, exploratoire, règle de lecture non atteinte pour tous les canaux). Les stries ne sont plus un indice d'orientation pour le dense ; elles restent un indice d'espèce possible. |
| OBJ-V4 pas de polarité | **acceptée** | A comme B votent aussi à la demi-maille ; E-synth-HF le confirme. Correctifs : rayon de suppression dans la grille ; contrôle demi-maille obligatoire ; pour le cycle 2, troncature du noyau à r ≤ 0,6 × maille et terme de polarité (vide central sombre ou pétiole étroit, [O] dji_0546), à voir avec convergence-engineer. |
| OBJ-V5 précision de A, canal | **acceptée en (a) et (b), contestée en partie en (c)** | (a) et (b) : règle A′ et lecture au budget. (c) : je conteste que l'ExG « efface » les ombres entre limbes. L'ExG normalisé d'un pixel d'ombre est instable, mais pas nul, et le gabarit à somme nulle répond au contraste vert contre non-vert. Aucune mesure ne départage aujourd'hui. **Expérience qui tranche** : le canal (ExG ou luminance) est un hyperparamètre de la grille du § 8.3, choisi sur le développement dense seul. En synthétique (E-synth-HF), A-L fait moins bien que A-ExG (0,31–0,33 contre 0,46–0,47 au budget), mais le rendu n'a pas d'ombres réalistes : cela ne compte pas. |
| OBJ-V6 tache contre rangs | **acceptée** | Contrôle « image tournée de 90° autour du centre de l'image, centres non tournés », ajouté aux conditions d'envoi (§ 8.6). |

### 7.2 Résultats d'E-synth-HF [M synthétique]

Commande :

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/leaf-mathematician/controle_hors_famille.py
```

Graine 20261108, 2 cm/px, 100 plants par scène, détecteurs non retouchés. Sortie : `resultats_hors_famille.json`.

| Variante de rendu | A au budget, 0,5 m / 1 m | A-iso au budget, 0,5 m / 1 m | A-L au budget, 0,5 m / 1 m | Part des fausses détections de A à 0,9–1,4 m | Médiane aux centres de A > 75e centile aux milieux ? |
| --- | --- | --- | --- | --- | --- |
| v0 : origine, centre marqué | 0,48 / 0,68 | 0,11 / 0,44 | 0,18 / 0,57 | 0,27 | oui |
| v1 : sans cigare, pétioles ni éclaircissement | 0,47 / 0,67 | 0,05 / 0,33 | 0,33 / 0,56 | 0,40 | oui |
| v2 : v1 + vide sombre central | 0,46 / 0,64 | 0,08 / 0,36 | 0,31 / 0,53 | 0,37 | oui |
| v3 : v2 + L de 1,6 à 2,5 m, décalage de 0,6 m | 0,18 / 0,48 | 0,05 / 0,12 | 0,19 / 0,47 | 0,54 | **non** |

Verdicts selon les critères écrits avant :
- **OBJ-C1** : chute maximale de 0,30, supérieure à 0,2. **E-002 ne compte pas comme appui à A.**
- **OBJ-C2 (indicatif)** : A > A-iso en v1, v2 et v3.
- **OBJ-C3** : la suppression des non-maxima de 0,8 m est inadaptée en v1–v3 ; A est non discriminant face à la demi-maille en v3.

Lecture : le marquage du centre ne portait presque rien (v0 ≈ v1 ≈ v2). Ce qui casse A, c'est le **désaccord d'échelle** (v3, des limbes plus longs que le gabarit) : c'est exactement le cas de banavista (couronnes de 3,2 m). D'où l'échelle dans la grille du cycle 1.

---

## 8. Cycle 1 : formulation candidate pré-enregistrée

Écrit le 7 novembre 2026, **avant toute mesure réelle de A**. Aucune image de `bv_b_val`, `val_iter`, `val_scellee` ni du test n'a été ouverte par leaf-mathematician.

### 8.1 Choix de la candidate : A′ seul, sans fusion avec B′

- **Pourquoi A′.**
  - A est le seul modèle dont le score dépasse un contrôle, même si c'est en synthétique.
  - Son défaut mesuré est le seuil, que A′ corrige.
  - Son coût est le plus bas : 2,4 s/ha [M, E-002].
- **Pourquoi pas la fusion A′ + B′ (signe −1, tronqué, sur la luminance).**
  - B′ n'a jamais été vu détecter, ni en synthétique ni en réel. E-003 mesure un alignement au niveau du pixel, pas une détection.
  - La fusion ajouterait au moins deux paramètres (poids et troncature) réglés sans contrôle.
  - OBJ-C6 (détecteur de lignes) n'est pas levée.
  - En cas d'échec, on ne saurait pas quelle moitié a échoué.
- **Ce que j'en garde.** L'information qu'E-003 désigne (luminance, structures allongées à l'échelle de la feuille) est exactement ce que voit le gabarit A sur le canal luminance. Je l'intègre donc par le **canal** de A, choisi sur le développement, et non par un second estimateur. B′ est remis au cycle 2, avec ses contrôles.

### 8.2 Formulation

- Score A (§ 2.3, inchangé) : 16 gabarits ancrés au centre (gaussienne anisotrope moins un surround latéral), ancrage à μ = r0 + L/2, m = 4 directions localement maximales.
- Calcul à 5 cm/px. Les photos brutes banavista sont réduites au disque central de 2 000 px.
- Code : `filtre_A(img, res, ParamsA(canal=…, echelle=…))`, puis `pics_mad(score, res, rayon_nms=…, z0=…)` dans `comptage_math/feuille.py`.

### 8.3 Paramètres

**Fixés** : L = 1,25 m, W = 0,55 m, r0 = 0,25 m, tous multipliés par l'échelle s ; N_θ = 16, m = 4, surround = 3 σ_W, résolution de travail 0,05 m.

**Grille réglée sur le seul développement dense** : `bv_session_a` (sans la pépinière en pots, liste de photos exclues à écrire avant la mesure, voir DEMANDES), `bv_b_train`, `lasuiza`, `vols_100_022x`, `corte`.

| Hyperparamètre | Valeurs |
| --- | --- |
| canal | ExG, luminance |
| échelle s | 0,8 ; 1,0 ; 1,25 ; 1,5 |
| rayon de suppression des non-maxima | 0,8 ; 1,0 ; 1,2 m |
| z0 (seuil A′) | 1,0 à 8,0 par pas de 0,5 |

Soit 24 configurations × 15 seuils.

- **Critère de sélection** : moyenne, sur les 5 groupes, du F1 du groupe (appariement à 1 m, mères seules, code d'independent-evaluator). Le F1 est cumulé sur les images de chaque groupe.
- **Égalités** (à 0,005 près) départagées dans l'ordre :
  1. canal ExG avant luminance ;
  2. s le plus proche de 1 ;
  3. le plus petit rayon ;
  4. le plus petit z0.
- **Résolution d'entrée** : celle du groupe (banavista ≈ 1,1 cm/px ; vols et corte ≈ 2,75 ; lasuiza ≈ 3,2). Aucune résolution n'est réglée.

**Amendement 1 au § 8.3 (7 novembre 2026, écrit avant tout calcul d'E-006 ; D-005 et `docs/recherche/test_final.md`, § 3.1 et 3.3).** Il remplace ce qui précède sur les points suivants.
- **Critère de sélection.** Le critère devient le **F1 cumulé sur `dev_reglage`** : `bv_session_a` sans pépinière + `bv_b_train`, mères seules, appariement à 1 m, calculé par `scripts/math_evaluer.py`. La moyenne des 5 groupes est abandonnée. `dev_transfert` (lasuiza dédoublonné, `vols_100_022x`, `corte`) est rapporté, mais ne sert à aucun choix.
- **Seuil z0.** La grille 1,0–8,0 est remplacée par la règle de l'évaluateur : meilleur F1 cumulé sur `dev_reglage`, sur sa propre grille de quantiles. Je fournis toutes les détections (maxima locaux) de score z ≥ 0,5, avec leur score z.
- **Données.** Ce sont les tuiles préparées de `data/drone/comptage_v5_5cm/images/`, et non plus les photos brutes. Les gabarits sont construits à la résolution réelle de chaque tuile (colonne `cm_par_px` d'`images_dense.csv`, de 3,6 à 6,7 cm/px), sans rééchantillonnage. Les pixels de remplissage (R + G + B ≤ 15) sont remplacés par la médiane du canal sur les pixels valides, et aucune détection n'y est gardée.
- **Inchangés.** La grille canal × échelle × rayon (24 configurations) et l'ordre de départage des égalités, à 0,005 près de F1 : ExG avant luminance ; s le plus proche de 1 ; plus petit rayon.
- **Conditions d'envoi.** Ce sont celles de `docs/recherche/test_final.md` § 3.3, qui remplacent le § 8.6 là où ils diffèrent :
  - rappel au budget k = N_réf qui dépasse la demi-maille de plus de 2 erreurs types (bootstrap apparié par unité, 2 000 tirages, graine 2026) ;
  - double comptage ≤ 0,15 (champ `double_comptage` de l'évaluateur) ;
  - A′ > A-iso au même budget, borne basse de l'IC à 95 % de la différence appariée > 0, sur au moins 2 groupes sur 3 parmi `bv_b_train`, `vols_100_022x` et `lasuiza` ;
  - médiane de z aux centres > 75e centile aux milieux des paires de plus proches voisins mutuels (< 3,5 m), sur `bv_b_train` **et** sur `vols_100_022x` ;
  - F1 sur image tournée de 90° ≤ F1 de la demi-maille sur `dev_reglage`.
- **Identifiant** : E-006. Script : `out/comptage_math/leaf-mathematician/cycle1_grille.py`.

**Amendement 2 au § 8.3 (7 novembre 2026, consigne du chef d'orchestre, écrit avant tout calcul d'E-006).** `bv_b_train` est réservé comme possible nouvelle validation dense : les références de `val_iter` sont incomplètes.
- **Groupe de sélection.** Il se réduit à **`bv_session_a` sans pépinière** (rôle `dev_reglage`, groupe `bv_session_a`). Aucune détection n'est calculée sur `bv_b_train`, aucun résultat le concernant n'est lu, et le script le vérifie par une assertion.
- **Sélection.** F1 cumulé sur `bv_session_a`, calculé dans le script avec les fonctions de `scripts/math_evaluer.py` (`comptes`, `prf`), selon la règle de seuil de l'évaluateur (200 quantiles des scores, meilleur F1 cumulé). Raison : `math_evaluer.py` en ligne de commande choisit son seuil sur le rôle `dev_reglage` entier, qui contient `bv_b_train`.
- **Rapport sans choix.** `dev_transfert` est évalué par `scripts/math_evaluer.py` au seuil figé (`--seuil-fixe`, rôle `dev_transfert` seul).
- **Conditions d'envoi** (même logique que l'amendement 1, `bv_b_train` remplacé) :
  - rappel au budget contre la demi-maille, double comptage et rotation : sur `bv_session_a` ;
  - A′ > A-iso : sur au moins 2 groupes sur 3 parmi **`bv_session_a`**, `vols_100_022x` et `lasuiza` ;
  - centres contre milieux : sur **`bv_session_a`** et `vols_100_022x`.
- **Prédiction (a) du § 8.7.** Elle porte sur `bv_session_a`, et non plus sur `bv_b_train`, avec les mêmes seuils (0,73 et 0,48).
- **Ce qui a été vu de `bv_b_train` avant cet amendement.** Les quatre premières lignes d'`images_dense.csv` (noms de tuiles, résolution 6,04 cm/px, régions), et sa maille médiane (2,24 m) dans `niveaux_nuls/maille_par_groupe.json`. Aucun score, aucune détection, aucune image.

### 8.4 Règle de seuil

- A′ : détections = maxima locaux de z = (S − médiane(S)) / (1,4826 · MAD(S)) ≥ z0. La médiane et le MAD sont pris sur la carte de score de chaque image, ce qui rend la règle indépendante du gain et du pic maximal.
- Rapporté en plus, sans servir à décider :
  - la courbe rappel-budget à 1 m ;
  - le point « nombre de détections = nombre de références » sur le développement.

### 8.5 Témoin A-iso

- Définition : `filtre_A_iso`, avec le même canal, la même échelle, le même rayon, et un seuil fixé par la même règle sur le développement. Le gabarit est la moyenne de h_θ sur θ (un anneau à somme nulle).
- Lecture : A-iso est rapporté sur le développement et sur `val_iter`, à côté de A′.
- Critère d'OBJ-C2 repris :
  - l'indice « feuilles anisotropes » est retenu en dense seulement si A′ dépasse A-iso au même budget, au-delà de l'intervalle bootstrap par tuile, sur au moins 2 groupes denses sur 3 (`bv_b_train`, `vols_100_022x`, `lasuiza`) ;
  - sinon A est déclaré « tache » (H1), et la comparaison utile devient A-iso contre la baseline ExG.

### 8.6 Conditions d'envoi sur `val_iter`

Elles sont mesurées sur le développement, avant tout envoi. Si une condition échoue, A′ n'est pas envoyé et le cycle 1 se clôt sur un résultat négatif, documenté.
1. **Demi-maille (OBJ-C3)** : sur `bv_b_train` et `vols_100_022x`, la médiane de S_A aux centres annotés dépasse le 75e centile de S_A aux milieux des paires de plus proches voisins annotés.
2. **Double comptage (OBJ-C3)** : la part des paires de voisins annotés qui reçoivent deux détections dont l'une est à plus de 0,5 m de tout centre reste à 15 % ou moins. Seuil proposé, à confirmer par independent-evaluator.
3. **Rotation (OBJ-V6)** : sur l'image tournée de 90° autour de son centre, avec les centres non tournés, le F1 à 1 m tombe au niveau nul de demi-maille (HF-01, c) ou en dessous.
4. **A′ > A-iso** selon le § 8.5.

### 8.7 Prédictions pré-enregistrées

Les prédictions d'OBJ-C4 sont reprises et chiffrées.
- **(a)** Sur `bv_b_train`, le rappel de A′ à 0,5 m au budget N_réf est **inférieur à 0,73** (borne haute du jointif synthétique d'E-002). Je prédis même qu'il est inférieur à 0,48 (budget, E-synth-HF v0).
- **(b)** À 1 m, l'excès de rappel de A′ au budget sur le niveau nul de demi-maille est **inférieur à 0,13**. Ce chiffre est l'excès synthétique v0 (0,68), moins le niveau nul dense d'environ 0,55 annoncé en HF-01 et C4 ; le niveau nul réel est celui d'independent-evaluator.
- **(c)** Avec la règle τ × max, la corrélation par photo entre le rapport détections/références et la luminance médiane dépasse 0,5 en valeur absolue. Avec la règle A′, elle passe **sous 0,5**. Si la règle A′ reste au-dessus de 0,5, une normalisation photométrique par photo est obligatoire au cycle 2.

Mes prédictions supplémentaires :
- **P-C1-1** : la grille choisit le canal **luminance** (cohérent avec E-003).
- **P-C1-2** : la grille choisit un rayon de suppression **≥ 1,0 m** et une échelle **≥ 1,25** (couronnes de 3,2 m à banavista, cohérent avec E-synth-HF v3).
- **P-C1-3** : A′ dépasse A-iso (§ 8.5).
- **P-C1-4 (H8)** : sur `val_iter`, A′ **ne bat pas** le v5 en dense. Prédiction écrite pour pouvoir être réfutée ; l'objectif D-003 n'est pas atteint au cycle 1.

### 8.8 Ce qui n'est pas au cycle 1

B, B′, B″, la fusion, la polarité et la règle Voronoï. Diagnostics sans détection autorisés en parallèle, sur le développement : P-B1 et P-B3 réels (OBJ-C5), contrôle JPEG (OBJ-C7), bords forts (OBJ-C6).

### 8.9 Résultats d'E-006 [M, développement seulement, aucune image de `bv_b_train`, `val_iter` ni `val_scellee`]

Commande :

```
.venv/Scripts/python.exe -I -u out/comptage_math/leaf-mathematician/cycle1_grille.py
```

- Données : 1 344 tuiles, soit 359 de `bv_session_a` sans pépinière et 985 de `dev_transfert`.
- Durée : 1 364 s sur 8 cœurs.
- Empreintes SHA-256 : script `9e991c75…6a2106`, `feuille.py` `db9c06e5…aed2c`.
- Sorties : `out/comptage_math/leaf-mathematician/E-006/` (bilan, grille, détections, évaluations de transfert).

**Grille, F1 cumulé sur `bv_session_a`** (mères seules, 1 m ; extrait, la grille complète est dans `E-006/grille_bv_session_a.csv`) :
- ExG : le meilleur F1 est **0,474** (s = 1,0, rayon 1,0 m). Pour s ≥ 1,25, le seuil optimal tombe sur le plancher z = 0,5 des détections fournies, ce qui borne ces points. Ils restent loin de la luminance.
- Luminance : de 0,452 à **0,542**.
- **Configuration retenue : canal luminance, s = 1,25, rayon 1,0 m, z0 = 1,0952.** F1 0,541, précision 0,445, rappel 0,690.
  - La configuration voisine (rayon 1,2 m) fait 0,542 : à moins de 0,005, l'égalité se départage par le plus petit rayon.
- A-iso, même canal, échelle et rayon, seuil réglé par la même règle : F1 0,423.
- Niveaux nuls sur `bv_session_a` (fichiers d'independent-evaluator) :
  - demi-maille : F1 0,109 ;
  - végétation uniforme : F1 0,331.

**`dev_transfert`, au seuil figé, rapporté sans choix :**

| Méthode | F1 global | IC à 95 % | corte | lasuiza | vols_100_022x |
| --- | --- | --- | --- | --- | --- |
| A′ | 0,355 | [0,325 ; 0,383] | 0,496 | 0,298 | 0,422 |
| A-iso | 0,267 | — | 0,316 | 0,245 | 0,292 |

Pour A′ sur `dev_transfert`, la précision est de 0,25 et le rappel de 0,60, avec des références incomplètes sur lasuiza et vols.

**Temps** : 13,5 s par hectare sur un cœur (médiane, filtre A et maxima, une configuration, hors lecture), soit environ 1,7 s/ha sur 8 cœurs.

**Conditions d'envoi (amendements 1 et 2) :**

| Condition | Mesure | Verdict |
| --- | --- | --- |
| Rappel au budget > demi-maille + 2 erreurs types (`bv_session_a`) | 0,497 contre 0,109 ; écart 0,388, erreur type 0,010 | passe |
| Double comptage ≤ 0,15 (`bv_session_a`) | 175 / 2 586 = 0,068 | passe |
| A′ > A-iso au budget, sur au moins 2 groupes sur 3 | `bv_session_a` +0,12 [0,099 ; 0,134] ; vols +0,13 [0,103 ; 0,153] ; lasuiza +0,07 [0,052 ; 0,097] | passe (3 sur 3) |
| z médian aux centres > 75e centile aux milieux, sur `bv_session_a` **et** vols | `bv_session_a` 0,742 > 0,723 ; **vols 0,561 < 0,732** | **échoue** |
| F1 sur image tournée de 90° ≤ F1 de la demi-maille (`bv_session_a`) | **0,349 > 0,109** | **échoue** |

**Conclusion selon les règles écrites : A′ n'est pas envoyé sur `val_iter`. Rien n'est consommé du plafond.**

Lecture, sans changer le verdict :
- Le F1 sur image tournée (0,349) est au niveau du nul « végétation uniforme » (0,331), et non à celui de la demi-maille. Une fois tourné, A′ se comporte comme des points pris au hasard dans la végétation : la rotation détruit bien l'information de position.
- La règle comparait à la demi-maille, un nul plus sévère que le hasard dans la végétation. Je la crois mal posée, mais je ne la change pas après coup (voir DÉSACCORDS du rapport).
- L'échec sur vols (2,75 cm/px, centres moins marqués que les milieux) reste un vrai échec d'OBJ-C3 sur un groupe de transfert.

**Prédictions du § 8.7 :**
- (a) rappel au budget à 0,5 m sur `bv_session_a` = 0,250 : **confirmée** (< 0,73 et < 0,48).
- (b) excès de rappel au budget à 1 m sur la demi-maille = 0,388 : **réfutée** (prédit < 0,13). Mon calcul supposait un nul dense d'environ 0,55 ; la demi-maille réelle vaut 0,109.
- (c) corrélation entre le rapport détections/références par unité et la luminance médiane : r = −0,04 avec la règle τ, r = −0,00 avec A′, sur 64 unités. **Réfutée** pour la règle τ (prédit |r| > 0,5) ; pas de dépendance photométrique visible sur `bv_session_a`.
- P-C1-1, canal luminance : **confirmée**.
- P-C1-2, rayon ≥ 1,0 m et échelle ≥ 1,25 : **confirmée**.
- P-C1-3, A′ > A-iso : **confirmée** (3 groupes sur 3).
- P-C1-4 : non mesurée (`val_iter` non lancé).

---

## 9. Cycle 2 : A″, A′ plus un terme de polarité (C-002, question 1), pré-enregistré

Écrit le 7 novembre 2026, **avant tout calcul d'E-007**. Rien n'a été mesuré sur A″. `bv_b_train`, `val_iter` et `val_scellee` ne sont pas utilisés.

### 9.1 Le problème à résoudre

En E-006 sur `vols_100_022x`, le z médian aux centres (0,561) est sous le 75e centile aux milieux des paires de voisins (0,732).

D'après le § 2.4, A estime le centre comme l'intersection des axes des feuilles. En un milieu m entre deux plants P1 et P2 espacés de D ≈ 2,1–2,4 m :
- le gabarit orienté vers P1 trouve un limbe allongé à μ ≈ 1,1 m (s = 1,25), c'est-à-dire autour de P1 lui-même ;
- de même vers P2 ;
- d'autres feuilles fournissent les 3e et 4e directions.

Le score d'étoile ne sait donc pas si les directions qui répondent forment une **étoile** (centre) ou un **dipôle** (milieu). Il ne sait pas non plus ce qu'il y a **au point lui-même**.

### 9.2 Les deux termes retenus, chacun lié à une observation

**Terme 1 : anisotropie angulaire d'ordre 2 (étoile contre dipôle).** Il n'a aucun paramètre continu nouveau. À partir des réponses R_θ déjà calculées (16 directions) :

a₂(c) = | Σ_θ [R_θ(c)]₊ e^{2iθ} | / ( Σ_θ [R_θ(c)]₊ + ε ) ∈ [0, 1].

- Pour une étoile de K ≥ 3 feuilles réparties, a₂ est petit.
- Pour deux réponses opposées (milieu entre deux voisins), a₂ ≈ 1.
- Score corrigé : S″ = S_A · (1 − β a₂), avec β ∈ {0, 1}.

C'est une formulation compatible avec l'indice « orientations » : on exige des orientations convergentes de **plusieurs** côtés, pas seulement d'un axe.

**Terme 2 : vide central sombre** ([O] dji_0546 et dji_0548 : le point annoté tombe souvent dans un petit vide de sol, d'ombre ou de pétioles, de 0,1 à 0,4 m). Sur la luminance Y :

H(c) = (G_{0,6 m} ∗ Y)(c) − (G_{0,15 m} ∗ Y)(c),

c'est-à-dire la clarté d'un voisinage de 0,6 m moins la clarté du point. H est positif si le point est plus sombre que son entourage. En un milieu entre deux voisins, en canopée dense, je m'attends plutôt à des pointes de limbes clairs qui se recouvrent, donc à H ≤ 0 [H].

Les deux écarts-types (0,15 et 0,6 m) sont **fixés** d'après l'[O] (vide de 0,1 à 0,4 m ; le point est comparé à la base des limbes, à r0 ≈ 0,3 m et au-delà). Ils ne sont pas réglés.

**Combinaison :**

z″ = zrob(S″) + w_trou · zrob(H) + w_vote · z_vote,

où zrob est la normalisation robuste (médiane et MAD sur les pixels valides de la tuile). Les détections sont les maxima locaux de z″, avec le même rayon de suppression que A′.

z_vote est le **point d'entrée de la preuve externe** du vote des axes linéaires (B′, convergence-engineer, `comptage_math/votes.py`). **w_vote = 0 au cycle 2** : rien n'est calculé, l'argument existe seulement dans `comptage_math/feuille.py` (`score_A2`).

Je n'ai pas retenu deux des pistes proposées :
- **La base du limbe plus étroite que la pointe.** À 2,75–3,6 cm/px, le pétiole (5 cm de large environ) occupe 1 à 2 px. Une asymétrie de largeur le long de l'axe n'est pas mesurable de façon fiable (§ 2.4 : seul σ_W est résolu).
- **La troncature à 0,6 × maille.** Elle s'applique surtout au vote B′ ; A n'a pas de noyau de vote. Elle reviendra à convergence-engineer.

### 9.3 Grille (2 paramètres nouveaux) et règle de sélection

- **Fixé**, d'après E-006 : canal luminance, s = 1,25, rayon 1,0 m, N_θ 16, m 4, surround 3. Gabarits à la résolution de chaque tuile, remplissage remplacé par la médiane.
- **Grille** : β ∈ {0 ; 1} × w_trou ∈ {0 ; 0,5 ; 1}, soit 6 configurations. (β = 0, w_trou = 0) reproduit A′ au chiffre près, ce qui sert de contrôle de non-régression : F1 0,541 attendu sur `bv_session_a`.
- **Sélection** : meilleur F1 cumulé sur `bv_session_a` sans pépinière (mères seules, 1 m). Le seuil de z″ est choisi par la règle de l'évaluateur (200 quantiles, meilleur F1), calculée avec les fonctions de `scripts/math_evaluer.py`.
- **Égalités** à 0,005 près : le plus petit w_trou, puis le plus petit β (parcimonie).
- **Détections** : tous les maxima locaux de score z″ ≥ 0,0 (le plancher de 0,5 d'E-006 a borné certains points de la grille ExG ; il est abaissé).
- **Témoin** : A-iso (E-006), inchangé, avec ses détections d'E-006.

### 9.4 Protocole (E-007)

- Même protocole qu'E-006 : `bv_b_train` exclu par assertion, de même que tout `bv_b_val`. `dev_transfert` est évalué par `scripts/math_evaluer.py` au seuil figé et ne sert à aucun choix.
- Mêmes conditions d'envoi qu'E-006 (amendement 2 au § 8.3).
- **Rotation** : je calcule le F1 sur image tournée de 90° et je rapporte les **deux nuls** sur `bv_session_a`, demi-maille et végétation uniforme, sans choisir la règle (C-002, question 3, à independent-evaluator).
- Script : `out/comptage_math/leaf-mathematician/cycle2_polarite.py`.

### 9.5 Prédictions chiffrées, écrites avant

- **P-A″-1** : la configuration retenue a β = 1 **et** w_trou > 0.
- **P-A″-2** : sur `vols_100_022x`, avec la configuration retenue, la médiane de z″ aux centres dépasse le 75e centile aux milieux (contre 0,561 < 0,732 en E-006). C'est la condition qui avait échoué.
- **P-A″-3** : F1 sur `bv_session_a` ≥ 0,551, soit au moins +0,01 sur A′.
- **P-A″-4** : F1 de `dev_transfert` au seuil figé ≥ 0,355 (A′ en E-006), et vols ≥ 0,422.
- **P-A″-5** : le double comptage sur `bv_session_a` passe sous 0,068.
- **P-A″-6** : le F1 sur image tournée reste à ±0,05 du nul « végétation uniforme » (0,331), donc au-dessus du nul demi-maille (0,109).
- **Réfutation de la polarité** : si β = 0 et w_trou = 0 sont retenus, ou si P-A″-2 échoue, aucun des deux termes ne distingue le centre du milieu sur ces données. Il faudra alors chercher l'information de polarité ailleurs (B′, ou une résolution plus fine).

**Amendement au § 9.4 (7 novembre 2026, avant lecture de tout résultat d'E-007).** La règle de rotation devient celle de `docs/recherche/test_final.md` § 4.3 (amendement 2, independent-evaluator). Elle est mesurée sur `bv_session_a`, au budget k = N_réf. Deux conditions doivent être vraies :
- F1_rot − F1_veg ≤ 0,05 ;
- F1_rot − F1_veg ≤ 0,25 × (F1_orig − F1_veg).

Le bootstrap et le F1 au seuil sont rapportés, mais ne servent pas à décider. Script : `out/comptage_math/leaf-mathematician/regle_rotation_e007.py`.

Mon interprétation de « détections ramenées dans le repère de l'image d'origine » : les tuiles sont carrées (512 × 512), donc les coordonnées en pixels des détections calculées sur l'image tournée sont lues telles quelles dans le repère de l'image d'origine, **sans rotation inverse**. Une rotation inverse rendrait les détections de l'image d'origine, puisque le filtre est presque invariant par rotation, et le contrôle serait vide. Interprétation à confirmer par independent-evaluator.

La prédiction P-A″-6 (F1 au seuil à ±0,05 de 0,331) est gardée telle quelle.

### 9.6 Résultats d'E-007 [M, développement seulement, aucune image de `bv_b_train`, `bv_b_val`, `val_iter` ni `val_scellee`]

Commandes :

```
.venv/Scripts/python.exe -I -u out/comptage_math/leaf-mathematician/cycle2_polarite.py
.venv/Scripts/python.exe -I -u out/comptage_math/leaf-mathematician/regle_rotation_e007.py
```

- Données : 1 344 tuiles (359 de `bv_session_a` et 985 de `dev_transfert`). Durée : 474 s.
- Empreintes SHA-256 : script `1b581961…1091bb`, `feuille.py` `66362977…8ed90cf5`.
- Sorties : `out/comptage_math/leaf-mathematician/E-007/`.

**Grille, F1 cumulé sur `bv_session_a`** (mères seules, 1 m) :

| β | w_trou | F1 | précision | rappel |
| --- | --- | --- | --- | --- |
| 0 | 0 | **0,541** | 0,445 | 0,690 |
| 0 | 0,5 | 0,500 | 0,393 | 0,689 |
| 0 | 1 | 0,439 | 0,324 | 0,682 |
| 1 | 0 | 0,535 | 0,436 | 0,693 |
| 1 | 0,5 | 0,498 | 0,389 | 0,692 |
| 1 | 1 | 0,440 | 0,320 | 0,703 |

- Non-régression : (0, 0) donne 0,541, identique à A′ d'E-006.
- **Configuration retenue : β = 0, w_trou = 0, c'est-à-dire A′ lui-même.** Aucun des deux termes de polarité n'améliore le F1. Le vide central le dégrade fortement, et l'anisotropie un peu.

**Centres contre milieux** (z médian aux centres contre 75e centile aux milieux) :

| β, w_trou | `bv_session_a` | `vols_100_022x` |
| --- | --- | --- |
| 0, 0 | 0,742 > 0,723 | 0,561 < 0,732 |
| 0, 0,5 | 0,735 < 0,764 | 0,698 < 0,756 |
| 0, 1 | 0,750 < 0,968 | 0,853 < 0,894 |
| 1, 0 | 0,769 < 0,850 | 0,680 < 0,875 |
| 1, 0,5 | 0,777 < 0,904 | 0,814 < 0,876 |
| 1, 1 | 0,806 < 1,116 | 0,979 > 0,961 |

Lecture :
- Chaque terme **relève davantage les milieux que les centres** sur `bv_session_a`.
- Pour le vide central, c'est la réfutation de mon hypothèse « milieux couverts de pointes de limbes claires » : en canopée dense, entre deux voisins, on trouve plutôt un creux sombre (ombre, inter-rang) qu'au centre d'une rosette, à ces résolutions.
- Pour a₂, le score des milieux remonte aussi : le dipôle attendu ne domine pas aux milieux.
- Une seule configuration passe sur vols (β = 1, w_trou = 1), et elle échoue sur `bv_session_a`.

**Conditions d'envoi de la configuration retenue** (identiques à A′) :
- rappel au budget contre demi-maille : 0,497 contre 0,109, passe ;
- double comptage : 0,068, passe ;
- A″ > A-iso : 3 groupes sur 3, passe ;
- centres contre milieux sur vols : 0,561 < 0,732, **échoue** ;
- rotation, règle de l'amendement 2 (`test_final.md` § 4.3), au budget N_réf : F1_orig 0,497, F1_rot 0,291, F1_veg 0,331. Excès sous rotation −0,040 (≤ 0,05 et ≤ 0,25 × 0,166) : **passe**.
  - Rapportés sans décider : IC bootstrap de F1_rot − F1_veg [−0,053 ; −0,028] ; F1_rot au seuil 0,349.
  - Avec l'ancienne règle (demi-maille, 0,109) : échoue.

**Verdict : A″ n'est pas envoyé sur `val_iter`.** Deux raisons, chacune suffisante :
1. la configuration retenue est A′ lui-même, qui ne diffère d'A′ que par la règle de rotation, ce que `test_final.md` § 4.1 interdit d'envoyer ;
2. la condition centres contre milieux échoue toujours sur vols.

**`dev_transfert`** (seuil figé, sans choix) : F1 0,355 [0,325 ; 0,383] ; corte 0,497 ; lasuiza 0,298 ; vols 0,422 ; double comptage 0,075. Identique à A′.

**Temps** : 27,9 s/ha sur un cœur (médiane, six combinaisons et termes de polarité compris), soit environ 3,5 s/ha sur 8 cœurs. La seule configuration A′ coûte 13,5 s/ha sur un cœur (E-006).

**Prédictions du § 9.5 :**
- P-A″-1 (β = 1 et w_trou > 0) : **réfutée**.
- P-A″-2 (vols, centres > milieux) : **réfutée** (0,561 < 0,732).
- P-A″-3 (F1 ≥ 0,551) : **réfutée** (0,541).
- P-A″-4 (transfert ≥ 0,355 et vols ≥ 0,422) : **réfutée de justesse** (0,3548 et 0,4222). Ce sont les chiffres d'A′ ; le seuil « ≥ 0,355 » est manqué à l'arrondi.
- P-A″-5 (double comptage < 0,068) : confirmée (0,0677), mais c'est A′ inchangé.
- P-A″-6 (rotation à ±0,05 de 0,331) : confirmée (0,349).
- **Clause de réfutation du § 9.5 déclenchée** : sur ces données, ni l'anisotropie angulaire ni le vide central ne distinguent le centre du milieu. L'information de polarité est à chercher ailleurs.

---

## 10. Cycle 3 : modèle F, feuille entière et un vecteur par feuille (C-003, E-018)

Écrit le 7 novembre 2026. **Aucune image réelle n'a été traitée par F** : la formulation a échoué au contrôle synthétique fixé d'avance (§ 10.4), et E-018 n'a pas été lancé sur `bv_session_a`. Ni `bv_b_train`, ni `bv_b_val`, ni `val_iter`, ni `val_scellee`, ni le test n'ont été ouverts.

### 10.1 Critique de la piste suggérée, avant tout calcul

- **Nervure claire.** [H, § 2.4] À 3,6–6,7 cm/px, la nervure (2–5 cm) occupe 1 px. Un terme de nervure n'apporte qu'une fraction σ_n/σ_t ≈ 0,1 de l'énergie du gabarit : non identifiable, retiré du gabarit.
- **Effilement vers le pétiole.** [H] Le limbe du bananier est oblong ; l'asymétrie de largeur est faible et le pétiole fait 1 px. La polarité par effilement est prédite non identifiable ; elle est gardée comme option (`polarite`), jamais testée faute d'avoir passé le synthétique. Le rendu B est symétrique (sin^0,4) : la polarité n'y est pas testable.
- **Ce que F apporte en principe face à B′.** (i) Une voix **par feuille** et non par pixel : une petite couronne (peu de pixels) pèse autant par feuille qu'une grande ; (ii) un **point** de vote à la distance propre de la feuille, au lieu d'une ligne de 0,2 à 1,6 m qui traverse les voisins ; (iii) une échelle par feuille. Ce sont les trois motifs d'E-011 (oubli 0,65 sous 2 m de couronne).

### 10.2 Formulation (compatible avec les indices « forme », « gaussiennes », « orientation », « vecteurs sur les feuilles »)

- Contraste local : Ŷ = (Y − G_{σb} ∗ Y) / √(G_{σb} ∗ (Y − G_{σb} ∗ Y)² + ε), σ_b = 1 m, Y luminance.
- Gabarit de feuille entière, centré au milieu du limbe, axe θ : h_{L,θ}(s, t) = e^{−s²/2σ_s²} [G(t; σ_t) − ⅓ G(t; 3σ_t)], σ_s = L/4, σ_t = ωL/4, ω = 0,4, ‖h‖₂ = 1 (somme nulle en t). L ∈ {0,8 ; 1,2 ; 1,8} m, 12 orientations sur [0, π).
- Réponse R*(x) = max_{L,θ} |h_{L,θ} ⋆ Ŷ|(x) (2e essai ; 1er essai sans valeur absolue), d'où L*(x), θ*(x).
- Feuilles : maxima locaux (0,15 m) de z(R*) ≥ 1,5 dans la végétation, puis suppression anisotrope dans l'ellipse (|s| < L*/2, |t| < ωL*/2) de chaque feuille acceptée.
- Vecteur par feuille : le centre est en p_k ∓ d_k u(θ_k), d_k = r0 + L*_k/2, r0 = 0,25 m. Carte V(c) = Σ_k Σ_± ½ exp(−|c − (p_k ∓ d_k u_k)|²/2σ_k²), σ_k = max(0,15 ; 0,25 d_k) : V compte les feuilles qui désignent c. Centres = maxima de V, NMS 1,0 m.
- Code : `comptage_math/feuille.py`, section « Modèle F » (`ParamsF`, `detecter_feuilles`, `carte_votes_feuilles`).

### 10.3 Pré-enregistrement d'E-018 (réel), qui n'aurait été appliqué qu'après succès synthétique

Écrit avant tout calcul réel ; conservé pour un cycle futur.
- 4 configurations au plus : C1 deux côtés, une voix par feuille ; C2 témoin d'échelle fixe (d = 0,85 m, σ = 0,21 m pour toutes les feuilles) ; C3 polarité douce (q⁻ = (1 + π)/2, π = tanh(0,5 P_z)) ; C4 fusion z_B′ + zrob(V_C1).
- Sélection : meilleur F1 cumulé sur `bv_session_a` sans pépinière (seuil par la règle de l'évaluateur, 200 quantiles), égalités à 0,001 départagées C1 < C2 < C3 < C4.
- Succès : gain apparié de la retenue sur B′ (0,637, seuil figé 2,238) ≥ +0,02 **et** borne basse de l'IC bootstrap par blocs de 7 photos (2 000 tirages, graine 2026), corrigée de Bonferroni (m = 4, percentile 0,625 %), > 0.
- Contrôles sur la retenue : orientations mélangées entre feuilles (F1 au budget N_réf − F1_veg ≤ 0,25 × (F1_orig − F1_veg)) ; demi-maille (z médian aux centres > 75e centile aux milieux, rappel au budget > demi-maille + 2 erreurs types) ; rotation selon `test_final.md` § 4.3. `dev_transfert` rapporté au seuil figé pour la retenue seule.
- Prédictions : C4 retenue ; gain < +0,02 (échec du critère) ; C3 n'apporte rien sur C1 ; C1 seul < 0,637.

### 10.4 Contrôle synthétique E-018s [M synthétique]

Critère écrit avant le lancement (`notes/leaf-mathematician.md`, section C-003) : rendu B à 5 cm/px, scènes « isolés » ; ≥ 50 % des feuilles vraies retrouvées (milieu du limbe à 0,3 m, axe à 20°) **et** rappel des centres au budget ≥ 0,80. Sinon F est déclaré en échec synthétique et E-018 n'est pas lancé.

| Essai | Feuilles retrouvées (isolés) | Rappel au budget, isolés | Jointifs | B′ isolés / jointifs |
| --- | --- | --- | --- | --- |
| 1 (graine 20261109, limbe clair) | 1,6 % | 0,25 | 0,57 | 0,99 / 0,98 |
| 2 (graine 20261110, \|R\|) | 8,6 % | 0,38 | 0,71 | 0,98 / 0,99 |

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/leaf-mathematician/e018_synthetique.py` ; sorties `out/comptage_math/leaf-mathematician/E-018/`.

Diagnostic après coup (`e018_diagnostic.py`, sans effet sur le verdict) : 53 % des feuilles détectées sont à moins de 0,15 m d'un axe vrai, mais l'écart d'axe médian est de 37° (27 % sous 20°), L* surestime L d'un facteur 1,35 et beaucoup de détections tombent sur les touffes d'herbe. Le gabarit de feuille entière **localise** à peu près le limbe mais **n'estime ni son orientation ni sa longueur** : à 5 cm/px, les bords nets, les stries et le recouvrement des limbes dominent la réponse d'un gabarit gaussien lisse. Le tenseur de structure de B′, lui, donne l'orientation (B′ ≈ 0,98).

**Verdict : la formulation F (gabarit gaussien de feuille entière + vote ponctuel) échoue en synthétique, deux fois, y compris sur des plants isolés. E-018 n'est pas lancé.** Les prédictions du § 10.3 restent non mesurées.

### 10.5 Ce qui reste à essayer (non pré-enregistré, pour C-003)

- **F′, feuille comme segment du champ d'orientation** : prendre l'orientation au tenseur de B′ (qui marche), et définir la feuille comme une composante connexe de pixels cohérents de même axe (croissance de région en angle doublé) ; sa longueur mesurée donne d_k, et chaque composante vote une fois en un point. Cela garde les motifs (i)–(iii) du § 10.1 sans demander à un gabarit lisse d'estimer θ et L.
- Contrôle synthétique à repasser avec les mêmes critères avant tout calcul réel.

## 11. D-013 — Simulateur v2 de bananeraie dense (`comptage_math/simulateur.py`)

Contrat : scientific-challenger, note, section « D-013 — Critères d'acceptation du simulateur v2 ». Calibration sur les seuls blocs **CAL** (`partage.csv` d'image-analyst : DJI_0543 à 0620, 183 tuiles) de `stats_photometriques.json`, `stats_geometriques.json`, des tuiles et des références CAL. Non lus : `stats_validation_cachees.json`, `out/comptage_math/evaluation/D-013/`, tout score de détection. Aucune des cinq méthodes (B′, T3, vote ExG, A′, A-iso) ni aucun autre détecteur n'a été lancé sur les rendus v2.1.

### 11.1 Version v2.1 — entrée consignée avant tout test de prédiction (7 novembre 2026)

**Empreintes SHA-256 (figées)** :

| Fichier | SHA-256 |
| --- | --- |
| `comptage_math/simulateur.py` (VERSION = "v2.1") | `92e1ce763207bb35eaf2e1c30c7cd20c1ef60b619b127f5a48d10b4a9cff41ae` |
| `out/comptage_math/leaf-mathematician/D-013/v2.1/parametres_v2.1.json` | `048072b48ca5a5572faac1b705bea11339c490121521f2d3fe1ae15de51c4f78` |
| `out/comptage_math/leaf-mathematician/D-013/v2.1/fonds_cal.npz` (fenêtres de fond CAL) | `3fda3efa596f365e07d2520dd52f72f5fc608692fc4f66c28f439f72ca376c2d` |
| `out/comptage_math/leaf-mathematician/D-013/generer.py` | `14b4aab8e7adce14b34845ca4a7d4c5ef985f497697215d29b75610bc2aef579` |

- **Graines** : 20261113 + i, i = 0 à 59 (contrat § 4). Aucune scène retirée.
- **Jeu** : `out/comptage_math/leaf-mathematician/D-013/v2.1/` :
  - `images/sim_v2.1_0000.jpg` à `_0059.jpg` : 512 px, JPEG 95 tel qu'encodé ;
  - `references.csv` : format `dev_dense.csv`, groupe `sim_v2.1`, 2 805 mères dans les tuiles, dont 1 376 dans la région comptée ;
  - `images.csv` : format `dev_dense_images.csv` (cm/px, disque, zone propre) ;
  - `rejets.csv` : rejets dessinés, **non comptés** ;
  - `manifeste.json` : SHA-256 de chaque image et gabarit CAL de chaque scène.
- **Commande** : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/leaf-mathematician/D-013/generer.py 60` (766 s, 4 processus).
- **Nombre de tuiles** : la mission fixe N = 60 ; le contrat (§ 2, § 3.2) demande « autant que VAL-S » (176). Écart signalé. `generer.py 176` produit 176 scènes avec les mêmes graines ; les 60 premières sont identiques.
- **Imports de `simulateur.py`** [O] : `json`, `math`, `pathlib`, `cv2`, `numpy`, `scipy.ndimage`, plus `scipy.spatial` et `scipy.special` dans `tailles`. Rien de `feuille.py`, de `votes.py`, d'`orientation.py` ni d'un gabarit.

**Forme du rendu.** Le tableau « formes et origines » est en tête de `simulateur.py`. En résumé :
- **plants** :
  - positions par une séquence d'acceptation à inhibition douce : φ = 0 sous h, puis rampe de γ à 1 entre h et R ;
  - tailles de couronne log-normales, couplées à l'espacement local par une copule gaussienne ;
  - une allée sans plants dans la moitié des scènes ;
  - marge de 4 m de plants hors tuile : des plants hors région débordent dans la région comptée ;
- **feuille** (ni profil gaussien ni bande de largeur constante) :
  - **limbe oblong** : demi-largeur (1 − ǀ2s−1ǀ^p)^½ modulée, bords non parallèles, côtés inégaux ;
  - nervure courbe ;
  - **déchirures perpendiculaires à la nervure** : processus de Poisson le long de la nervure, profondeur et largeur tirées, plus fréquentes sur les feuilles âgées ;
  - pétiole et cigare ;
  - côtes du limbe en bandes perpendiculaires à la nervure ;
- **recouvrement** : ordre de dessin aléatoire, visibilité par la hauteur (z-buffer, hauteur décroissante le long de la feuille) ; les feuilles des voisins s'entremêlent ;
- **feuilles sèches** brun doré, pendantes, et marges nécrosées ;
- **ombres** par occultation ambiante : ciel couvert, sans direction ([O] CAL, concentration 0,17) ;
- **fonds** : collage de fenêtres réelles CAL (herbe, sol, mixte, ombre) prises à plus de 1,5 m de toute référence. `preparer_fonds.py` en retient 5 244 d'herbe, 3 539 de sol, 337 d'ombre et 1 088 mixtes, sur 162 tuiles ;
- **dégradation** : rendu à 1 cm/px, puis moyenne par zone vers la résolution d'une tuile CAL tirée au hasard (avec sa région disque ∩ zone propre), gain, bruit, JPEG 95.

**Paramètres, valeur et origine** (`parametres_v2.1.json`). Trois origines :
- « CAL » : statistique d'un bloc CAL ;
- « CAL-ajusté » : valeur choisie en comparant des scènes simulées aux statistiques CAL. Ces scènes de calibration utilisent les graines 5000 + i, distinctes des graines de scène ;
- « [H] » : hypothèse déclarée.

| Paramètre | Valeur | Origine |
| --- | --- | --- |
| tuiles_cal | 183 gabarits (résolution 3,59–6,7 cm/px, disque, zone propre) | CAL |
| densite_log_mu ; densite_log_sigma | 6,830 ; 0,233 (médiane 925 ha⁻¹) | CAL, densités par photo |
| inhib_h_m ; inhib_R_m ; inhib_gamma | 0,9 ; 2,2 ; 0 | CAL-ajusté (g(r), d1, taux de contact ; `calibrer_geometrie.py`, 3e grille) |
| taille_log_mu ; taille_log_sigma | 1,031 ; 0,224 (médiane 2,80 m) | CAL, KS minimal (KS 0,026) |
| copule_rho | 0,6 | CAL-ajusté (Spearman taille–d1 : 0,40 sur CAL, 0,43 simulé) |
| f_env (envergure / (taille/2)) | U(1,6 ; 2,1) | CAL-ajusté (fractions de classes) |
| f_env_log_sigma_scene | 0,30 | CAL-ajusté (dispersion du feuillage entre tuiles) |
| K, phyllotaxie, r0, L, W/L, p, τ, κ | voir le tableau de `simulateur.py` | [H] (`modele_feuille.md` § 2.2) |
| déchirures : λ_t, profondeur, largeur, ψ | 0,04–0,25 m ; 0,1–0,9 w ; 0,5–2 cm ; ≤ 0,2 rad | [H] |
| lab_feuillage_moy | (59,3 ; −16,6 ; 24,0) | CAL |
| decalage_L_feuillage ; decalage_ab_feuillage | +12 ; (−6, +3) | CAL-ajusté (Lab mesuré de la classe feuillage sur les scènes) |
| lab_feuille_ect | (9 ; 4,5 ; 6) | [H] partage de σ_Lab CAL |
| eclairage_demi_limbe ; bruit_limbe_L ; ondulation_L | 10 ; 10 ; 10 | [H] et CAL-ajusté (spectre, part d'« herbe » sur la canopée) |
| texture_limbe_m ; texture_limbe_L | 0,03 m ; 12 | CAL-ajusté (spectre radial F5) |
| lab_sec_moy ; lab_sec_ect | (51,0 ; 6,2 ; 23,2) ; (11,9 ; 2,9 ; 2,1) | CAL |
| n_seches_par_plant ; seches_log_sigma_scene ; p_marge_necrosee | 4 ; 1,2 ; 0,5 | CAL-ajusté (fraction « sec ») ; marge [H] |
| p_allee ; allee_demi_largeur_m | 0,5 ; U(0,8 ; 3,5) | CAL-ajusté (dispersion des fractions) ; largeur [H] |
| beta_part_herbe ; fond_correlation_m ; fond_tuiles_sources | Beta(3, 2) ; 0,6 m ; 3 | CAL-ajusté ; sources [H] |
| ao_rayon_m ; ao_h0_m ; ao_plancher | 0,25 m ; 1,5 m ; 0,25 | CAL-ajusté (fraction et longueur de corrélation des ombres) ; plancher [H] |
| psf_sigma_px ; bruit_sigma_niveaux ; gain_log_sigma ; jpeg_qualite | 0 ; 10 ; 0,08 ; 95 | CAL-ajusté (variance du laplacien, Immerkær) ; CAL |
| marge_m | 4 m | [H] |
| rejets_par_mere ; rejet_distance_m ; rejet_taille_m | 0,7 ; U(0,5 ; 1,2) ; U(0,6 ; 1,5) | [H] entièrement : aucun rejet annoté [O] |

**Dernière comparaison à CAL avant le gel** (32 scènes de calibration, `v2.1/derniere_comparaison_cal.json`) :

| Grandeur | Simulé | CAL |
| --- | --- | --- |
| KS luminance ; KS ExG (simulé contre CAL) | 0,041 ; 0,088 | |
| Écart des fractions (simulé − CAL) | vert −0,006 ; sec −0,003 ; ombre +0,009 ; sol −0,023 ; herbe +0,044 | |
| Spectre (simulé contre CAL) | 0,066 dex ; pente +0,13 | |
| G1 KS ; G2 KS ; G4 | 0,077 ; 0,046 ; 0,27 | |
| Taux de contact | 0,875 | 0,925 |
| Variance du laplacien | 22 000 | 35 200 |
| Bruit d'Immerkær | 10,2 | 10,8 |

### 11.2 Tests de fidélité non réservés de v2.1, contre VAL-S (une passe) [M]

- **Commande** : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/leaf-mathematician/D-013/fidelite.py`.
- **Sortie** : `out/comptage_math/leaf-mathematician/D-013/fidelite_v2.1.json`.
- **Règle** : un test passe si d(sim, VAL-S) ≤ max(seuil, 1,5 × d(CAL, VAL-S)).
- **Variabilité naturelle** : recalculée par le même code. Pour G1–G6, les estimateurs travaillent par tuile, d'où des valeurs un peu différentes de celles de plant-geometry, qui travaille par photo.
- **F6–F8** : réservés, non calculés.

| Test | Écart v2.1 | Seuil effectif | Verdict v2.1 | Ancien rendu B |
| --- | --- | --- | --- | --- |
| F1 luminance, KS | 0,091 | 0,10 | passe | échoue (0,60) |
| F2 ExG, KS | 0,079 | 0,10 | passe | échoue (0,54) |
| F3 fractions moyennes | herbe +0,094 (VAL-S 0,136, simulé 0,230) ; vert −0,056 | 0,05 ; 0,059 | **échoue** (herbe) | échoue (vert −0,63, herbe +0,71, ombre −0,11) |
| F4 dispersion entre tuiles | sec 0,27 ; herbe 1,97 | [0,67 ; 1,5] ou 1,5 ǀln r_natǀ | **échoue** | échoue |
| F5 spectre | 0,088 dex ; pente +0,15 | 0,15 ; 0,3 | passe | échoue (1,25 dex) |
| G1 tailles | KS 0,23 ; W1 0,30 m | 0,28 ; 0,36 | passe | échoue (KS 0,34, W1 0,38) |
| G2 d1 | KS 0,18 ; W1 0,18 m | 0,14 ; 0,15 | **échoue** | échoue |
| G3 densité | −10,9 % ; CV +60 % | 11,1 % ; 97 % | passe | échoue |
| G4 g(r) | 0,46 | 0,29 | **échoue** | échoue (1,38) |
| G5 contact | 0,058 | 0,05 | **échoue** | échoue |
| G6 < 2 m ; > 3,6 m | 0,035 ; 0,089 | 0,063 ; 0,116 | passe | échoue (> 3,6 m) |

- **Verdict de fidélité v2.1 : échec.** F3, F4, G2, G4 et G5 échouent. Selon le contrat § 2, **v2.1 n'est pas soumise au test de prédiction** (§ 3). Elle compte comme une des trois versions.
- **Contrôle de non-trivialité : passé.** L'ancien rendu `rendre_scene_B` (configuration « jointifs » d'E-018s, 5 cm/px) échoue sur F3, F5 et G1, et sur tous les autres tests : les seuils ne sont pas trop lâches.
- **Lecture**, sans retouche de v2.1 :
  - **géométrie** : l'inhibition douce par acceptation séquentielle ne reproduit pas le pic de g(r) vers 2,4 m (réel : 1,3 à 1,5) et donne trop de paires entre 1 et 1,5 m. VAL-S est encore plus régulier que CAL (Clark-Evans 1,39 contre 1,28). Le simulé passe G2 et G5 de justesse contre CAL, mais échoue contre VAL-S ;
  - **photométrie** : les grands limbes simulés sont trop lisses à l'échelle 12–30 cm du classifieur, qui les prend pour de l'« herbe » (simulé 0,23, VAL-S 0,14). La dispersion de l'herbe entre tuiles est double ; celle du « sec » est trop faible ;
  - **aspect** (`vignettes_v2.1.png`) : limbes trop réguliers et trop striés, bords non déchiquetés. Les tuiles CAL réelles contiennent aussi des éléments non rendus : bâtiments, cuves, arbres, personnes, gaines bleues.
- **Pour une v2.2 éventuelle** (non lancée). Chaque changement devra être justifié par une statistique CAL (contrat § 3.4) :
  - processus de positions plus régulier (Strauss à l'équilibre par naissance-mort, ou réseau perturbé), calé sur le pic de g(r) de CAL ;
  - texture des limbes à 12–30 cm, calée sur la part d'« herbe » sur la canopée de CAL ;
  - dispersion du « sec » par tuile.
- **Vignettes** :
  - `out/comptage_math/leaf-mathematician/D-013/vignettes_v2.1.png` : 6 paires réel CAL / simulé, les scènes i = 0 à 5 placées à côté de leur tuile gabarit (règle de choix fixée avant de regarder) ;
  - ancien rendu : `ancien_rendu_0.png`.

### 11.3 Version v2.2 — entrée consignée avant le calcul de fidélité contre VAL-S et avant tout test de prédiction (7 novembre 2026)

Demande du chef d'orchestre après la consignation de v2.1 : corriger v2.1 **uniquement à partir de statistiques CAL**, et produire 176 tuiles, soit la taille de VAL-S fixée par le contrat. C'est la 2e version sur 3.

**Empreintes SHA-256 (figées avant la génération)** :

| Fichier | SHA-256 |
| --- | --- |
| `comptage_math/simulateur.py` (VERSION = "v2.2") | `c929b07405effff6409290f9dfa1725c7ad02dbb9ce9aefbf85ea3d8d36f37cd` |
| `out/comptage_math/leaf-mathematician/D-013/v2.2/parametres_v2.2.json` | `b422d22e5d799c3109508ddb63ad3ac71a57b861dd1943fad74aa2c8671fbbc9` |
| `out/comptage_math/leaf-mathematician/D-013/v2.2/fonds_cal.npz` | `f8b7962cd1710682f608e9a47adbff9e699a88a9a32b4a2e14cf94dd0c773831` |
| `out/comptage_math/leaf-mathematician/D-013/generer.py` | `cc0f14008bc7c4e3421517440754b91223feddb5cb8835582f71ec8e33fdba90` |

- **Code v2.1 conservé** : `v2.1/simulateur_v2.1.py`, dont le SHA-256 est identique à celui du § 11.1. On y trouve aussi les scripts v2.1 de paramètres, de géométrie et de fonds.
- **Graines** : 20261113 + i, pour i de 0 à 175 (contrat § 4).
- **Jeu** : `out/comptage_math/leaf-mathematician/D-013/v2.2/`, même structure que pour v2.1 (`images/sim_v2.2_NNNN.jpg`, `references.csv`, `images.csv`, `rejets.csv`, `manifeste.json`).
- **Commande** : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/leaf-mathematician/D-013/generer.py 176`.
- **Imports de `simulateur.py`** : inchangés, aucun module de détection.

**Changements, chacun avec la statistique CAL qui le justifie** :

| # | Changement | Statistique CAL | Réglage (CAL seulement) |
| --- | --- | --- | --- |
| 1 | **Positions** : le réseau rectangulaire perturbé, aminci et à cœur dur remplace l'inhibition douce séquentielle. Réseau de pas b1 × k·b1, d'orientation et d'origine uniformes, bruit N(0, σ_j²) ; cœur dur h ; puis amincissement logistique(c + σ_f Z), Z étant un champ lisse de longueur 5 m [H] ; c conserve la densité visée | pic de g(r) (1,34 vers 2,4 m), d1, taux de contact G5, CV de densité par tuile | `calibrer_geometrie.py` (v2.2) : grille de 360 points, 32 tuiles simulées par point sur gabarits CAL, mêmes estimateurs que les tests G. Critère : max ǀΔgǀ + 2 KS(d1) + 2 ǀΔcontactǀ + 0,5 ǀCV/CV_CAL − 1ǀ. Retenu : b1 = 2,4 m, k = 1,2, σ_j = 0,6 m, σ_f = 2, h = 0,9 m ; max ǀΔgǀ 0,17, KS d1 0,069, contact 0,927 (CAL 0,925), CV +10 % |
| 2 | **Contact G5** : obtenu par les positions (point 1) et par la copule taille–espacement, réestimée (ρ = 0,6 ; Spearman 0,39 contre 0,40 sur CAL) | taux de contact CAL 0,925 ; Spearman taille–d1 | même script |
| 3 | **Texture des limbes** : ajout d'un bruit isotrope passe-bande (σ 12 et 30 cm), d'amplitude L* 16 | fractions feuillage et herbe de CAL, mesurées par la règle d'image-analyst sur les scènes (la règle « herbe » lit le contraste 12–30 cm) | amplitude 10 puis 16 ; à 16 : herbe −0,012, feuillage +0,042 contre CAL |
| 4 | **Effet tuile « sec »** : fenêtres CAL « sec » (herbe sèche et débris au sol, 263 fenêtres, nouvelle règle de `preparer_fonds.py`) posées sur une part du sol tirée par tuile, log-normale (μ = −4, σ = 0,9), en taches de 0,15 m | moyenne (0,0066) et écart-type entre tuiles (0,0085) de la fraction « sec » de CAL ; longueur de corrélation du « sec » (0,13 m) | σ 1,2 puis 0,9 ; à 0,9 : rapport des écarts-types 0,87 |
| 5 | **Effet tuile « herbe et sol »** : part d'herbe du fond tirée par tuile, Beta(3, 2), inchangée ; allées ramenées de p = 0,5 à 0,3 | dispersion entre tuiles des fractions herbe et sol de CAL : à p = 0,5, le rapport des écarts-types du sol valait 1,89 contre CAL | à 0,3 : herbe 1,08, sol 1,43 |

- **Point de méthode à signaler** : la grille géométrique (point 1) a été évaluée avec des allées à p = 0,5, puis p a été ramené à 0,3 pour la photométrie (point 5). Les paramètres de positions n'ont pas été réajustés après ce changement.
- **Corrections pendant la calibration, toutes sur CAL** :
  - 1er passage de la grille sur une région égale à la tuile entière : le taux de contact y était biaisé vers le bas par les mères de bord. La grille a été repassée sur les gabarits CAL réels ;
  - au 2e passage, la grille retenait σ_f = 2 avec un CV trop fort et une densité trop basse (889 ha⁻¹) : le cœur dur a été placé avant l'amincissement, et le terme de CV a été ajouté au critère.
- **Comparaison à CAL avant le gel** (32 scènes de calibration, graines 5000 + i, `v2.2/derniere_comparaison_cal.json`) :

| Grandeur | Simulé − CAL ou rapport |
| --- | --- |
| KS luminance ; KS ExG | 0,018 ; 0,059 |
| Fractions | vert +0,042, sec −0,002, ombre +0,005, sol −0,014, herbe −0,012 |
| Rapports des écarts-types | vert 1,25, sec 0,87, ombre 1,11, sol 1,43, herbe 1,08 |
| Spectre | 0,087 dex ; pente +0,04 |
| G1 KS ; G2 KS | 0,056 ; 0,098 |
| G3 | −11,6 % ; CV +31 % |
| G4 ; G5 | 0,29 ; 0,030 |

- **Paramètres v2.1 inchangés** : tous les autres, voir le § 11.1.

### 11.4 Tests de fidélité non réservés de v2.2, contre VAL-S (une passe, 176 tuiles) [M]

- **Commande** : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/leaf-mathematician/D-013/fidelite.py v2.2`.
- **Sortie** : `out/comptage_math/leaf-mathematician/D-013/fidelite_v2.2.json`.
- **Jeu mesuré** : 176 scènes générées en 4 746 s (`v2.2/manifeste.json`, SHA-256 identiques au § 11.3), soit 8 060 mères dans les tuiles, dont 3 723 dans la région comptée.
- **Mêmes règles qu'au § 11.2.** L'ancien rendu n'est pas repassé : le contrôle de non-trivialité a été fait avec v2.1.

| Test | Écart v2.2 | Seuil effectif | Verdict | Rappel v2.1 |
| --- | --- | --- | --- | --- |
| F1 luminance, KS | 0,072 | 0,10 | passe | passe |
| F2 ExG, KS | 0,037 | 0,10 | passe | passe |
| F3 fractions moyennes | vert 0,001 ; sec 0,003 ; ombre 0,008 ; sol 0,004 ; herbe 0,015 | 0,05–0,059 | passe | échoue |
| F4 dispersion entre tuiles | vert 1,45 ; sec 0,82 ; ombre 1,25 ; sol 1,49 ; herbe 1,85 (seuil 1,92) | [0,67 ; 1,5] ou 1,5 ǀln r_natǀ | passe | échoue |
| F5 spectre | 0,061 dex ; pente +0,06 | 0,15 ; 0,3 | passe | passe |
| G1 tailles | KS 0,24 ; W1 0,32 m | 0,28 ; 0,36 | passe | passe |
| G2 d1 | KS 0,18 ; W1 0,20 m | 0,14 ; 0,15 | **échoue** | échoue |
| G3 densité | moyenne −15,2 % ; CV +111 % | 11,1 % ; 97 % | **échoue** | passe |
| G4 g(r) | 0,27 | 0,29 | passe | échoue |
| G5 contact | 0,027 | 0,05 | passe | échoue |
| G6 < 2 m ; > 3,6 m | 0,042 ; 0,100 | 0,063 ; 0,116 | passe | passe |

- **Verdict de fidélité v2.2 : échec**, sur G2 et G3 seulement. Les cinq tests photométriques F1–F5 et G1, G4, G5, G6 passent. Selon le contrat § 2, **v2.2 n'est pas soumise au test de prédiction** (§ 3) ; F6–F8, réservés, n'ont pas été calculés.
- **Versions consommées : 2 sur 3.**
- **Lecture**, sans retouche de v2.2 :
  - **G3** : l'amincissement par champ lisse (σ_f = 2) crée de grandes trouées. Le CV des densités par tuile double donc, et la densité moyenne dans la région comptée baisse (−15 % contre VAL-S, qui est lui-même 8 % plus dense que CAL). Deux causes à vérifier sur CAL :
    - le critère de la grille ne pesait le CV que 0,5 fois ;
    - la grille a été évaluée avec des allées à p = 0,5, alors que p = 0,3 a été retenu ensuite (§ 11.3) ;
  - **G2** : les d1 simulés restent plus courts que ceux de VAL-S, qui est plus régulier que CAL (Clark-Evans 1,39 contre 1,28). L'écart était déjà de 0,07–0,10 en KS contre CAL ;
  - **aspect** (`vignettes_v2.2.png`) : la texture passe-bande, qui règle la part d'« herbe » de la règle de classes, donne aux limbes un aspect marbré peu naturel. La statistique est atteinte, l'aspect visuel non.
- **Pour une v2.3 éventuelle, la dernière** : seulement si le chef d'orchestre la demande. Chaque changement doit être justifié par une statistique CAL :
  - poids du CV de densité dans le critère géométrique ;
  - grille réévaluée avec la valeur de p_allee retenue ;
  - σ_f plafonné par la part de cellules de 10 m vides de CAL (3,1 %).

### 11.5 Version v2.3 (3e et dernière) — entrée consignée avant la génération, avant le calcul de fidélité contre VAL-S et avant tout test de prédiction (7 novembre 2026)

Demande du chef d'orchestre après la consignation de v2.2. Les cinq corrections demandées sont toutes tirées de CAL. VAL-S n'a servi à aucun réglage. Aucune v2.4 n'est possible.

**Empreintes SHA-256 (figées)** :

| Fichier | SHA-256 |
| --- | --- |
| `comptage_math/simulateur.py` (VERSION = "v2.3") | `26668ddd39563119970d4a1c5a767fd353b0a65e91736771f57d9e92533f7fe4` |
| `out/comptage_math/leaf-mathematician/D-013/v2.3/parametres_v2.3.json` | `5124e5b8de8284ac7982a5c371ecd84d8ab36700481ff5effaabccd27712e436` |
| `out/comptage_math/leaf-mathematician/D-013/v2.3/fonds_cal.npz` (copie de v2.2 : même règle) | `f8b7962cd1710682f608e9a47adbff9e699a88a9a32b4a2e14cf94dd0c773831` |
| `out/comptage_math/leaf-mathematician/D-013/generer.py` (inchangé) | `cc0f14008bc7c4e3421517440754b91223feddb5cb8835582f71ec8e33fdba90` |
| `out/comptage_math/leaf-mathematician/D-013/calibrer_geometrie.py` (v2.3) | `8f8e00023683b491083f84b7a55a6be78ea14a4047aadf81757886d286b4a3ca` |

- **Code v2.2 conservé** : `v2.2/simulateur_v2.2.py`, avec un SHA-256 identique à celui du § 11.3. On y trouve aussi les scripts v2.2 (`*_v2.2.py`).
- **Graines** : 20261113 + i, pour i de 0 à 175 ; 176 tuiles.
- **Commandes** : `generer.py 176`, puis `fidelite.py v2.3` (une seule passe).
- **Imports de `simulateur.py`** [O] : `json`, `math`, `pathlib`, `cv2`, `numpy`, `scipy.ndimage`, `scipy.spatial`, `scipy.special`. Aucun module de détection.

**Changements, avec leur justification CAL** :

| # | Demande | Changement | Statistique CAL et résultat |
| --- | --- | --- | --- |
| 1 | Grille recalée avec p = 0,3 | `calibrer_geometrie.py` v2.3 simule exactement le processus des scènes : allées à p = 0,3, réseau, cœur dur, amincissement. 270 points de grille, 64 tuiles par point sur gabarits CAL | même processus en géométrie et en photométrie |
| 2 | Plafond de σ_f | point de grille écarté si sa part de cellules de 10 m vides (entièrement dans la région comptée) dépasse 2 × celle de CAL (2,4 % sur 42 cellules, même estimateur par tuile) ; 26 points écartés sur 270, dont tous ceux à σ_f ≥ 1,5 avec certaines formes de réseau. **Retenu : σ_f = 0** (0 cellule vide simulée, contre 1 sur 42 pour CAL) | part de cellules vides CAL |
| 3 | Densité et CV dans le critère | critère = max ǀΔgǀ + 2 KS(d1) + 2 ǀΔ contactǀ + 2 ǀdensité/CAL − 1ǀ + ǀCV/CV_CAL − 1ǀ + 4 ǀΔ cellules videsǀ ; facteur de densité 1,007 au point retenu | densité moyenne par tuile (952 ha⁻¹) et CV (0,346) de CAL |
| 4 | d1 visé sur CAL | même critère (2 KS d1). Retenu : b1 = 2,2 m, k = 1,2, σ_j = 0,45 m, h = 0,9 m, σ_f = 0 ; copule ρ = 0,6 (Spearman 0,36 contre 0,40) | distribution de d1 de CAL |
| 5 | Limbes moins marbrés | la texture 12–30 cm devient un profil 1D passe-bande le long de la nervure (plis perpendiculaires à la nervure, amplitude L* 8), plus une part isotrope faible (L* 4, calculée à 4 cm/px). Ajustements photométriques sur CAL : f_env 1,6–2,1 → 1,4–1,9 (canopée moins fermée sans trouées) ; part d'herbe du fond Beta(3, 2) → Beta(1,5 ; 1) ; sec au sol μ = −4, σ = 1,0, plafond 0,15 | fractions F3, dispersion F4 et spectre F5 de CAL (5 comparaisons de calibration, `v2.3/comparaison_cal_passage*.json`) |

**Contrôles sur CAL avant la passe VAL-S** (règles écrites avant leur résultat dans `notes/leaf-mathematician.md` ; aucune donnée VAL-S) :

Géométrie : 549 tuiles (183 gabarits CAL × 3), `v2.3/geometrie_cal.json`.

| Contrôle | Valeur | Seuil | Verdict |
| --- | --- | --- | --- |
| KS(d1 simulé, d1 CAL) | 0,048 | ≤ 0,10 | passe |
| Densité moyenne | −3,8 % | ± 5 % | passe |
| CV des densités | −12,8 % | ± 30 % | passe |
| max ǀΔgǀ (0,5–6 m) | 0,22 | ≤ 0,30 (niveau de v2.2 sur CAL) | passe |
| ǀΔ contactǀ | 0,034 | ≤ 0,05 | passe |

Photométrie : 64 scènes rendues (graines 5000 à 5063), `v2.3/derniere_comparaison_cal.json`.

| Contrôle | Valeur | Seuil | Verdict |
| --- | --- | --- | --- |
| F1 luminance, KS | 0,028 | ≤ 0,10 | passe |
| F2 ExG, KS | 0,080 | ≤ 0,10 | passe |
| F3 fractions | vert +0,029 ; sec −0,001 ; ombre +0,014 ; sol −0,010 ; herbe −0,013 | ≤ 0,05 | passe |
| F4 rapports des écarts-types | vert 0,94 ; sec 1,29 ; ombre 1,13 ; sol 1,46 ; herbe 0,91 | [0,67 ; 1,5] | passe |
| F5 spectre | 0,065 dex ; pente +0,03 | ≤ 0,15 ; ≤ 0,3 | passe |

Sur ces mêmes 64 scènes : G2 KS 0,082, densité +3,7 %, CV −24 %, G4 0,27, contact 0,011.

**Tous les contrôles CAL passent : la passe VAL-S est autorisée.**

**Limites connues avant la passe** :
- la variance du laplacien simulée reste inférieure à celle de CAL (22 600 contre 35 200), alors que le bruit d'Immerkær est proche (10,3 contre 10,8) ;
- avec σ_f = 0, il n'y a plus de trouées dans la plantation hors allées ;
- l'aspect des limbes reste stylisé (vignettes après génération).

### 11.6 Tests de fidélité non réservés de v2.3, contre VAL-S (une passe, 176 tuiles) [M]

- **Commande** : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/leaf-mathematician/D-013/fidelite.py v2.3`.
- **Sortie** : `out/comptage_math/leaf-mathematician/D-013/fidelite_v2.3.json`.
- **Jeu** : `v2.3/`, 176 scènes générées en 1 894 s, soit 8 416 mères dont 3 889 dans la région comptée. Les SHA-256 du manifeste sont identiques à ceux du § 11.5.
- **Vignettes** : `vignettes_v2.3.png`.

| Test | Écart v2.3 | Seuil effectif | Verdict | v2.2 | v2.1 |
| --- | --- | --- | --- | --- | --- |
| F1 luminance, KS | 0,112 | 0,10 | **échoue** | passe (0,072) | passe |
| F2 ExG, KS | 0,060 | 0,10 | passe | passe | passe |
| F3 fractions | vert 0,020 ; sec 0,003 ; ombre 0,017 ; sol 0,019 ; herbe 0,011 | 0,05–0,059 | passe | passe | échoue |
| F4 dispersion entre tuiles | vert 1,02 ; sec 0,74 ; ombre 1,15 ; **sol 1,69** ; herbe 1,39 | [0,67 ; 1,5] ou 1,5 ǀln r_natǀ (sol : ≤ 1,5) | **échoue** (sol) | passe | échoue |
| F5 spectre | 0,063 dex ; pente +0,10 | 0,15 ; 0,3 | passe | passe | passe |
| G1 tailles | KS 0,25 ; W1 0,32 m | 0,28 ; 0,36 | passe | passe | passe |
| G2 d1 | KS 0,11 ; W1 0,12 m | 0,14 ; 0,15 | passe | échoue | échoue |
| G3 densité | −9,9 % ; CV +43 % | 11,1 % ; 97 % | passe | échoue | passe |
| G4 g(r) | 0,20 | 0,29 | passe | passe | échoue |
| G5 contact | 0,048 | 0,05 | passe | passe | échoue |
| G6 < 2 m ; > 3,6 m | 0,031 ; 0,097 | 0,063 ; 0,116 | passe | passe | passe |

- **Verdict de fidélité v2.3 : échec.**
  - F1 : la distribution de luminance est trop sombre ; l'ombre vaut 0,126 contre 0,109.
  - F4 : la dispersion du sol nu entre tuiles est trop forte.
  - Les six tests géométriques passent pour la première fois.
  - Selon le contrat § 2, **v2.3 n'est pas soumise au test de prédiction** ; F6–F8 réservés ne sont pas calculés.
- **Les 3 versions sont consommées** (v2.1, v2.2, v2.3). Aucune n'a passé la fidélité. Les cibles du § 3 n'ont pas été ouvertes, et aucun détecteur n'a été lancé.
- **Lecture**, sans retouche :
  - les deux échecs portent sur des tests réussis sur CAL avant la passe : F1 KS 0,028 et F4 sol 1,46 sur 64 scènes ;
  - la différence CAL ↔ VAL-S y entre pour une part : F1 naturel 0,044 ; dispersion du sol VAL-S/CAL 0,91 ;
  - le rapport du sol à 1,46 sur CAL n'avait déjà que peu de marge sous 1,5 ;
  - chaque version a corrigé ses échecs propres et en a fait apparaître d'autres, de l'ordre de la variabilité CAL ↔ VAL-S. À cette précision, les seuils du contrat sont atteints test par test, mais pas tous en même temps.
- **Usage permis du simulateur** (contrat § 5) : **aucun**. Il ne peut servir ni de filtre, ni de diagnostic, ni de prévision chiffrée. Les scènes v2.1–v2.3 restent disponibles comme rendus non validés.
