# Notes d'error-analyst

## E-011 — Erreurs du vote des axes linéaires B′ (E-008), mères seules (7 novembre 2026)

Analyse descriptive, pas une nouvelle méthode. Aucun paramètre du vote n'est réglé ici.

### 1. Règles écrites avant le calcul (7 novembre 2026)

Les valeurs exactes sont dans la constante `REGLES` de `scripts/math_erreurs.py`.

**Données.**
- Analyse principale et planches : bv_session_a sans pépinière (rôle dev_reglage, groupe bv_session_a).
- Complément, en tableaux seulement : dev_transfert.
- Interdits par assertion : bv_b_train, bv_b_val, les rôles val_*, les groupes exclus et `cg/`.
- Le vote vient d'E-008 (`vote.csv`, seuil z figé 2,238). Le v5 vient d'E-001 (seuil figé 0,30). L'appariement est celui d'independent-evaluator : un à un, rayon 1 m.

**Attributs mesurés pour chaque erreur :**
- le score z ;
- la distance aux mères ;
- la taille de la boîte ;
- la luminance, l'ExG, la cohérence |z| du tenseur (σ_t 10 cm) et la fraction de végétation, moyennées dans un carré de 1 m ;
- la distance au bord de l'image ou à un pixel invalide ;
- l'appariement du v5 ;
- les candidats sous le seuil ;
- le support d'un nœud de maille.

**Maille locale.**
- Elle est construite à partir des seules détections retenues du vote, jamais des références. On note s la distance médiane au plus proche voisin.
- Nœuds prévus :
  - b + (b − a) et a − (b − a), pour les paires distantes de 0,7 à 1,3 s ;
  - le milieu, pour les paires distantes de 1,6 à 2,4 s.
- Un nœud est retiré s'il est occupé, c'est-à-dire si une détection est à moins de 0,6 s.
- Un point est « à un nœud » s'il a au moins 2 prédictions à moins de 0,3 s.

**Oubliés : état du candidat.** Les règles s'appliquent dans cet ordre, la première qui correspond l'emporte.

| État | Règle | Module |
| --- | --- | --- |
| bord de tuile | à moins de 1 m du bord ou d'un pixel invalide | tuiles |
| couronnes jointives (fusion) | une détection retenue à moins de 1 m est appariée à une autre mère | séparation dense / nettoyage |
| candidat sous le seuil | un candidat du vote sous le seuil est à moins de 1 m | seuil |
| aucun candidat | aucun des cas précédents | orientation / vote |

**Oubliés : facteur image.** Les règles s'appliquent dans cet ordre. Les centiles sont calculés sur les mères du même jeu.

| Facteur | Règle | Module |
| --- | --- | --- |
| petit plant | taille inférieure au P20 | vote (échelle du noyau) |
| ombre | luminance inférieure au P20 | orientation / couleur |
| couronnes jointives (voisine proche) | distance à la mère voisine inférieure au P10 | séparation dense |
| échelle | taille d'au moins 3,2 m, soit 2 r_max | vote (r_max) |
| cohérence faible | cohérence inférieure au P20 | orientation |
| sans facteur | aucun des cas précédents | indéterminé |

**Fausses détections.** Les règles s'appliquent dans cet ordre.

| Classe | Règle | Module |
| --- | --- | --- |
| bord de région | une mère hors de la région comptée est à moins de 1 m | évaluation |
| milieu de deux mères | à moins de 0,5 m du milieu de deux mères distantes de moins de 3,5 m (catégorie ajoutée le 7 novembre, avant le calcul) | vote / séparation dense |
| doublon d'un plant apparié | la mère la plus proche est à moins de 2 m et déjà appariée | nettoyage |
| rejet compté | un point non « mere » est à moins de 1,6 m | nettoyage |
| référence manquante probable | aucune mère à moins de 1,6 m, un FP du v5 de score ≥ 0,5 à moins de 1 m, végétation ≥ 0,5 | annotation-manager |
| sol ou débris | végétation inférieure à 0,3 | couleur |
| feuille isolée | une mère non trouvée est à une distance comprise entre 1 et 2 m | vote (localisation) |
| autre végétal | la mère la plus proche est à au moins 2 m | vote / seuil / couleur |
| indéterminé | aucun des cas précédents | — |

**Chiffre clé.**
- Le chiffre clé est la part des oubliés qui ont, à moins de 1 m, un candidat sous le seuil situé à un nœud prévu. C'est une borne haute.
- Contrôle de coût, sans réglage : on ajoute de façon gloutonne, par score, tous les candidats sous le seuil situés à un nœud, avec une exclusion de 0,6 s, puis on réapparie. C'est une mesure descriptive : cette règle n'est pas une méthode adoptée.
- Planches : 24 exemples par cause, tirés avec la graine 2026.

### 2. Résultats [M] (E-011)

Commande : `.venv/Scripts/python.exe -I -u scripts/math_erreurs.py`, environ 3 min sur 8 cœurs. Sorties dans `out/comptage_math/error-analyst/E-011/` :
- `bilan_E-011.json` ;
- `oublies_*.csv`, `fausses_detections_*.csv` et `meres_*.csv`, avec un attribut par erreur ;
- `planches/`, soit 20 planches de 24 exemples tirés avec la graine 2026.

Les compléments (taux d'oubli par classe d'attribut, paires oubli–FP, centres de triangles) ont été calculés en ligne de commande à partir de ces CSV. Ils sont décrits plus bas.

**Contrôle de reproduction.**

| Méthode | P | R | F1 | Référence |
| --- | --- | --- | --- | --- |
| Vote sur bv_session_a | 0,6304 | 0,6432 | 0,6368 | identique à E-008 |
| v5 sur bv_session_a | — | — | 0,821 | identique à E-001 |

Les comptes sont VP 5563, FP 3261 et FN 3086, sur 359 tuiles et 8 649 mères. 100 % des erreurs sont classées et aucune n'est indéterminée.

#### 2.1 Oubliés (bv_session_a, 3 086 ; dev_transfert, 3 227)

| État du candidat | bv_session_a | dev_transfert | Module |
| --- | --- | --- | --- |
| aucun candidat à moins de 1 m | 1 232 (39,9 %) | 1 503 (46,6 %) | orientation / vote |
| candidat sous le seuil | 1 128 (36,6 %) | 1 085 (33,6 %) | seuil / score |
| bord de tuile | 681 (22,1 %) | 593 (18,4 %) | tuiles |
| couronnes jointives (fusion) | 45 (1,5 %) | 46 (1,4 %) | séparation dense |

| Facteur image | bv_session_a | dev_transfert |
| --- | --- | --- |
| petit plant (moins de 2,43 m) | 29,6 % | 31,6 % |
| échelle (au moins 3,2 m) | 23,6 % | 20,5 % |
| sans facteur | 22,7 % | 21,9 % |
| ombre | 11,2 % | 15,1 % |
| cohérence faible | 7,5 % | 4,9 % |
| voisine à moins de 1,54 m | 5,4 % | 6,0 % |

**Lecture correcte : la part brute n'est pas l'excès.** Taux d'oubli du vote et du v5 par classe d'attribut sur bv_session_a. Le taux global du vote est de 0,357.

| Attribut | Vote | v5 |
| --- | --- | --- |
| taille ≤ 2,0 m (n = 583) | 0,647 | 0,480 |
| taille 2,0–2,4 m | 0,475 | 0,403 |
| taille 2,8–3,2 m | 0,300 | 0,200 |
| taille 3,2–3,6 m | 0,293 | 0,139 |
| taille > 3,6 m (n = 1 271) | 0,289 | 0,087 |
| bord < 1 m | 0,39–0,41 | 0,32–0,38 |
| bord > 1 m | 0,33–0,36 | 0,17–0,24 |
| voisine < 1,5 m (n = 739) | 0,537 | 0,430 |
| voisine 2–3 m | 0,31 | 0,13–0,20 |
| luminance, quintile bas puis haut | 0,400 → 0,326 | 0,308 → 0,188 |
| cohérence, quintile bas puis haut | 0,418 → 0,347 | 0,249 → 0,228 |
| résolution (5 quintiles de cm/px) | 0,32–0,39, sans tendance | — |

Excès d'oubliés au-delà du taux du reste, sur bv_session_a (calcul arithmétique sur ces classes) :

| Facteur | Excès | Part des oubliés |
| --- | --- | --- |
| petit plant | ≈ 360 | 12 % |
| voisine proche | ≈ 150 | 5 % |
| cohérence faible | ≈ 130 | 4 % |
| ombre | ≈ 90 | 3 % |
| bord de tuile | ≈ 75 | 2,5 % |

Au total, environ un quart des oubliés est attribuable à un facteur mesurable. **Le reste, environ trois quarts, est un plancher diffus.** Le vote oublie environ 29 % des mères bien formées de plus de 2,8 m, alors que le v5 n'en oublie que 9 à 14 %.

**Conséquences sur les classes brutes.**
- « Bord de tuile » (22 %) est surtout un taux de base sur bv_session_a : 20 % des mères sont à moins de 1 m du bord. La classe est plus réelle sur dev_transfert (0,34–0,43 contre 0,25).
- « Échelle » n'est pas une cause absolue : les grandes couronnes sont les moins oubliées. C'est en revanche la première cause **relative au v5**.

**Où sont les pics manquants.**
- Distance au candidat le plus proche, quel que soit son score :
  - médiane de 1,0 m sur tous les oubliés ;
  - 1,29 m pour la classe « aucun candidat », dont le candidat le plus proche a un z médian de 2,47, au-dessus du seuil.
- 37,4 % des oubliés (1 154) ont une **fausse détection retenue à 1–2 m**, et 22,3 % (689) à 1–1,5 m. Sur dev_transfert, les parts sont de 41 % et 28 %.
- Le décalage FP − oublié n'a pas de direction privilégiée sur bv_session_a : |moyenne| / moyenne des normes = 0,04, histogramme des 8 secteurs plat, norme médiane de 1,36 m. Sur dev_transfert, il est faiblement orienté (0,15).
- Le décalage n'est donc pas une convention d'annotation. Le pic tombe sur le flanc de la couronne ou entre couronnes.
- Contrôle [M] : les FP ne sont pas aux centres de triangles de 3 mères (1,6 %, contre 4,3 % pour des points aléatoires). L'impression visuelle d'un « pic de jonction » n'est pas confirmée.

#### 2.2 Fausses détections (bv_session_a, 3 261 ; dev_transfert, 10 065)

| Classe | bv_session_a | dev_transfert | Module |
| --- | --- | --- | --- |
| autre végétal (mère la plus proche à au moins 2 m) | 1 262 (38,7 %) | 6 379 (63,4 %) | vote / seuil / couleur |
| feuille isolée (mère oubliée à 1–2 m) | 823 (25,2 %) | 1 244 (12,4 %) | vote (localisation) |
| doublon d'un plant apparié | 620 (19,0 %) | 919 (9,1 %) | nettoyage |
| milieu de deux mères | 218 (6,7 %) | 120 (1,2 %) | vote / séparation dense |
| bord de région (artefact d'évaluation) | 165 (5,1 %) | 42 (0,4 %) | évaluation |
| sol ou débris | 124 (3,8 %) | 1 255 (12,5 %) | couleur |
| référence manquante probable | 49 (1,5 %) | 106 (1,1 %) | annotation-manager |
| rejet compté | 0 | 0 | non mesurable : bv_session_a n'a que des « mere » |

« Autre végétal » sur bv_session_a :
- seuls 34 % sont à au moins 3 m d'une mère et 16,5 % ont une végétation inférieure à 0,7 ;
- sur la planche, la majorité tombe dans la canopée entre plants, et une minorité (environ 6 sur 24) dans des buissons, de l'herbe ou des plantes aquatiques.

Sur dev_transfert, 63 % de cette classe est à au moins 3 m d'une mère et 53 % a une végétation inférieure à 0,7 : c'est du vrai végétal hors bananier.

Le z médian des FP (2,66) est proche de celui des VP (3,15) et très au-dessus du seuil.

#### 2.3 Comparaison avec le v5 (bv_session_a)

| Mères | v5 trouve | v5 oublie |
| --- | --- | --- |
| vote trouve | 4 873 | 690 |
| vote oublie | 1 783 | 1 303 |

**Oubliés du vote que le v5 trouve (1 783).**
- État : aucun candidat 42 %, sous le seuil 39 %, bord 18 %.
- Facteur : **échelle (au moins 3,2 m) 32 %**, sans facteur 24 %, petit plant 22 %.
- Ce sont surtout de grandes couronnes bien formées.

**Mères trouvées par le vote et oubliées par le v5 (690).** Planche : `vp_vote_oubliees_v5.png`.

**Fausses détections.**
- 2 541 des 3 261 FP du vote n'ont aucune détection du v5 à moins de 1 m. Le v5 les évite.
- 490 des 910 FP du v5 (54 %) coïncident à moins de 1 m avec un FP du vote. Ce sont des structures en forme de plant, ou des références manquantes.

#### 2.4 Chiffre clé : candidats sous le seuil à un nœud de maille

| Mesure | bv_session_a | dev_transfert |
| --- | --- | --- |
| oubliés avec un candidat sous le seuil à moins de 1 m, sans condition de maille | 1 480 (48,0 %) | 1 437 (44,5 %) |
| **oubliés avec un candidat sous le seuil sur un nœud prévu (borne haute)** | **140 (4,5 %)** | **157 (4,9 %)** |
| règle nœud sans réglage : candidats ajoutés, dont VP | 678, dont 142 | 1 350, dont 156 |
| règle nœud sans réglage : F1 | 0,628, contre 0,637 | 0,532, contre 0,546 |

- La maille issue des détections du vote prédit mal : s médian 2,15 m, et seulement 26 % des oubliés ont même une seule prédiction à 0,3 s.
- Les z des candidats sous le seuil des oubliés (médiane 1,91, P90 2,18) recouvrent la queue des FP. Baisser le seuil ne sépare rien, comme le montre la courbe d'E-008.
- **La piste « maille locale » n'est pas un levier de rappel avec ces paramètres.**

### 3. Rattachement aux modules et expériences proposées

1. **Localisation du pic (vote, convergence-engineer).** Les paires oubli–FP à 1–1,5 m sont 689. Borne arithmétique si chacune était recentrée : P 0,709, R 0,723, F1 ≈ 0,716. C'est une borne haute, car un même FP peut être le plus proche de plusieurs oubliés.
   - Expérience proposée : recentrage explicite du pic retenu à moins de 1,5 m, par le centre de symétrie radiale du champ d'orientation ou par le barycentre de la carte z, sans changer la liste des candidats.
   - Critère : gain de F1 apparié dont l'IC exclut 0 sur bv_session_a.
2. **Plancher diffus sur les grandes couronnes (vote, échelle du noyau).** Le vote oublie 29 % des mères de plus de 3,2 m, contre 9 à 14 % pour le v5. C'est la première source d'écart au v5.
   - Expérience proposée : la grille r_max ∈ {1,6 ; 2,0 ; 2,4} déjà prévue par D-006 ; mesurer en plus le taux d'oubli par classe de taille.
   - Critère : baisse du taux d'oubli au-delà de 3,2 m sans hausse des FP « autre végétal ».
3. **FP en canopée et hors bananier (couleur et vote, vegetation-color-engineer).** C'est 39 % des FP sur bv_session_a et 76 % sur dev_transfert (autre végétal et sol).
   - Expérience proposée : un terme de couleur ou de texture propre au bananier, testé comme filtre des FP à au moins 2 m d'une mère.
   - Critère : précision sur dev_transfert sans perte de rappel de plus de 0,01.
4. **Doublons (nettoyage) : 19 %.** E-009b a déjà réfuté la répulsion. Aucune nouvelle expérience n'est proposée ici.
5. **Petits plants (≈ 12 % d'excès)** : r_min et σ_t multi-échelle, déjà prévus par D-006.
6. **À signaler, sans correction :**
   - 49 références manquantes probables (planche `fp_reference_manquante_probable.png`), pour annotation-manager ;
   - 165 FP « bord de région » (artefact d'évaluation), pour independent-evaluator.

## E-021 — Diagnostic de l'écart vote–v5 sur le développement

### 1. E-021 — règles écrites avant le calcul (7 novembre 2026)

Analyse descriptive, sans réglage : le vote B′ reste dans sa configuration figée d'E-008/E-010 (r_max 1,6 m, p = 1, R_nms 1,0 m, z ≥ 2,238, masque provisoire, normalisation « sd »). Aucun seuil du vote n'est changé.

**Données.**
- Analyse principale et planches : bv_session_a sans pépinière (mêmes images qu'E-011).
- Contrôle : dev_transfert, tableaux seulement.
- Interdits par assertion : bv_b_train, bv_b_val, val_scellee et tout rôle val_*, `cg/`, `out/comptage_math/evaluation/D-013/`. Le simulateur D-013 n'est pas utilisé.
- Entrées réutilisées sans recalcul : CSV d'E-011 (`meres_*`, `oublies_*`, `fausses_detections_*`, appariement d'independent-evaluator à 1 m, v5 d'E-001 au seuil 0,30), détections du vote d'E-008 (`vote.csv`). Le v5 n'est pas relancé. La carte z du vote est recalculée avec `comptage_math/votes.py` (non modifié), dans la configuration figée ; contrôle de reproduction : z recalculé aux candidats de `vote.csv` (écart médian absolu attendu < 0,01).

**Partie 1 — décomposition oracle (arithmétique sur les CSV d'E-011).**
- Base : comptes VP, FP, FN du vote (E-011). F1 = 2 VP / (2 VP + FP + FN).
- Classes de fausses détections (classes d'E-011, inchangées) : autre végétal, feuille isolée, doublon, milieu de deux mères, sol ou débris ; rapportées aussi : bord de région, référence manquante probable.
  Correction oracle d'une classe : ses FP sont retirés (FP − n).
- Classes d'oubliés : états d'E-011 (aucun candidat, candidat sous le seuil, bord de tuile, fusion) ; partition séparée par taille de couronne : < 2,0 ; 2,0–2,4 ; 2,4–2,8 ; 2,8–3,2 ; 3,2–3,6 ; ≥ 3,6 m.
  Correction oracle : ses FN deviennent VP (VP + n, FN − n), sans ajouter de FP.
- Deux variantes par classe : « oracle total » (toute la classe) et « oracle v5 » (seulement les FN que le v5 trouve ; seulement les FP sans détection v5 à < 1 m). La variante v5 répond à « combien de l'écart au v5 la classe explique ».
- Cumul : sur l'ensemble disjoint {classes FP} ∪ {états FN}, classes triées par gain individuel décroissant (oracle total), corrections ajoutées une à une. La partition par taille est cumulée à part (elle recoupe les états).
- Écart de référence : F1 v5 − F1 vote sur le même jeu (contrôles d'E-011). Chaque gain est aussi exprimé en part de cet écart.
- Ce sont des **bornes hautes** : correction parfaite, sans coût en FP ni en VP perdus, et sans couplage (en réalité, déplacer une « feuille isolée » sur sa mère corrige un FP et un FN à la fois, ce que la somme compte deux fois).

**Partie 2 — grandes couronnes.**
- Groupes (par jeu) : mères certaines de taille ≥ 2,8 m que le v5 trouve ;
  - G_oub : oubliées par le vote ;
  - G_deux : trouvées par le vote.
- Mesures en chaque mère (point de référence p, en mètres via cm/px) :
  - z0 : z du vote en p ;
  - zmax1, d1 : maximum de z dans le disque de 1 m et sa distance à p ; zmax2, d2 : idem à 2 m ;
  - alignement radial A(anneau) = Σ c·t / Σ c sur les pixels du masque de végétation et valides de l'anneau, t = −cos(arg z − 2ψ) (t = 1 : axe linéaire radial, comme `attributs_candidats`), anneaux 0,4–1,0 ; 1,0–1,6 ; 1,6–3,0 m ; A_in = même calcul sur 0,4–1,6 m (support du noyau) ;
  - cohérence moyenne : moyenne de c = |z| sur le masque dans 0,4–3,0 m ;
  - contraste de luminance : luminance moyenne du disque 0–0,4 m moins celle de l'anneau 0,4–1,6 m ;
  - part de végétation : fraction du masque dans le disque 0–1,6 m ;
  - voisine retenue : distance à la détection retenue du vote la plus proche, son z, et si elle est appariée à une autre mère (appariement recalculé à 1 m, un à un, avec `evaluer_comptage.apparier` comme E-011) ;
  - distance au bord (reprise d'E-011).
- Nul de l'alignement : milieux des paires de mères (toutes les mères de l'image, y compris hors région) distantes de 2 à 4 m, gardés si aucune mère n'est à moins de 1,2 m et si le bord est à plus de 1 m. T_in = P90 de A_in sur ces milieux ; T_out = P90 de A(1,6–3,0) sur ces milieux. Seuils calculés par jeu.
- Classement des mères de G_oub (premier cas qui s'applique) :
  0. **bord** : d_bord < 1 m (rapporté à part, hors des trois cas) ;
  1. **signal radial absent** : A_in < T_in et A(1,6–3,0) < T_out ;
  2. **pic déplacé ou absorbé** : une détection retenue du vote est à moins de 2 m de p (appariée à une autre mère ou FP) ;
  3. **signal présent mais trop faible au centre** : les autres (aucune détection retenue à < 2 m, donc zmax2 < 2,238 ou pic supprimé hors région).
  Sous-indicateur rapporté, sans changer le classement : « signal seulement au-delà de r_max » = A_in < T_in et A(1,6–3,0) ≥ T_out (hypothèse de troncature r_max).
- Le même classement est appliqué à G_deux (pour lire le taux de base de chaque cas).
- Comparaison G_oub contre G_deux : médianes et AUC (Mann–Whitney) de chaque mesure, par jeu ; également par classe de taille 2,8–3,2 ; 3,2–3,6 ; ≥ 3,6 m pour A et z0.
- Planches (bv_session_a) : pour chacun des trois cas, 24 exemples tirés avec la graine 2026, répartis en 2 planches de 12 (RGB + carte z, anneaux 1,0 / 1,6 / 3,0 m). Si un cas a moins de 13 exemples, une seule planche.

**Partie 3 — conclusion.** Leviers classés par gain borné de la partie 1 (variante v5). Pour le premier levier mathématique, une expérience avec critère écrit d'avance, non lancée.

**Amendement daté (7 novembre 2026, après le premier passage, avant toute lecture des planches).** Pour le cas 2, la « voisine retenue » exclut la détection appariée à la mère elle-même : sans cela, toute mère de G_deux tombait trivialement dans le cas 2. Le classement de G_oub est inchangé (aucune détection n'y est appariée à la mère ; effectifs identiques aux deux passages : 477 / 202 / 178 / 175). Le premier passage s'est aussi arrêté aux planches (colonne `image_path` manquante) ; ses CSV ont été effacés et tout a été relancé.

### 2. E-021 — résultats [M]

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/error-analyst/e021_ecart_v5.py` (4 processus, quelques minutes). Sorties dans `out/comptage_math/error-analyst/E-021/` : `bilan_E-021.json`, `oracle_*.csv`, `grandes_couronnes_*.csv`, `nul_milieux_*.csv`, `E-021.log`, `planches/` (6 planches de 12).

Contrôles : comptes de base identiques à E-011 (bv_session_a VP 5 563, FP 3 261, FN 3 086, F1 0,6368 ; v5 0,821) ; z recalculé égal à `vote.csv` sur 16 650 + 38 633 candidats (écart P99 = 0).

#### 2.1 Oracle (bornes hautes : correction parfaite, sans coût, sans couplage)

bv_session_a, écart v5 − vote = 0,184. « v5 » : seulement les FN que le v5 trouve, ou les FP sans détection v5 à < 1 m.

| Classe | n (v5) | F1 oracle | gain | gain v5 | part de l'écart (v5) |
| --- | --- | --- | --- | --- | --- |
| FN aucun candidat | 1 232 (748) | 0,727 | +0,090 | +0,056 | 30 % |
| FN candidat sous le seuil | 1 128 (694) | 0,719 | +0,083 | +0,052 | 28 % |
| FP autre végétal | 1 262 (1 075) | 0,686 | +0,050 | +0,042 | 23 % |
| FN bord de tuile | 681 (322) | 0,688 | +0,051 | +0,025 | 13 % |
| FP feuille isolée | 823 (584) | 0,668 | +0,032 | +0,022 | 12 % |
| FP doublon | 620 (488) | 0,660 | +0,023 | +0,018 | 10 % |
| FP milieu de deux mères | 218 (153) | 0,645 | +0,008 | +0,006 | 3 % |
| FP bord de région | 165 (118) | 0,643 | +0,006 | +0,004 | 2 % |
| FP sol ou débris | 124 (123) | 0,641 | +0,005 | +0,005 | 2 % |
| FN fusion | 45 (19) | 0,640 | +0,004 | +0,002 | 1 % |
| FP référence manquante probable | 49 (0) | 0,639 | +0,002 | 0 | 0 % |

Cumul (oracle total) : 0,727 → 0,799 → 0,839 (avec bord de tuile) → 0,894 (avec autre végétal) → 0,934 → 0,966 → … → 1. Cumul variante v5 : 0,693 → 0,741 → 0,785 → 0,807 → 0,834 → 0,858 → … → 0,879.

Par taille (FN, gain total / gain v5) : < 2,0 m +0,029 / +0,012 ; 2,0–2,4 +0,037 / +0,016 ; 2,4–2,8 +0,054 / +0,029 ; 2,8–3,2 +0,048 / +0,029 ; 3,2–3,6 +0,037 / +0,027 ; ≥ 3,6 +0,028 / +0,023. Les mères ≥ 2,8 m que le v5 trouve et que le vote oublie (1 032) valent au plus +0,076.

dev_transfert (écart 0,331) : le premier levier est l'autre végétal (+0,152, variante v5 +0,140), puis aucun candidat (+0,071 / +0,053), sous le seuil (+0,052 / +0,039), sol (+0,025), feuille isolée (+0,024), bord de tuile (+0,029 / +0,016).

Lecture : le « bord de tuile » brut est surtout un taux de base (E-011 : excès ≈ 75 oubliés) ; sa borne réaliste est donc proche de +0,006, pas +0,025.

#### 2.2 Grandes couronnes (≥ 2,8 m, trouvées par le v5)

bv_session_a : G_oub 1 032, G_deux 3 278. Nul (25 468 milieux) : T_in = 0,118, T_out = 0,168.

| Mesure | médiane G_oub | médiane G_deux | AUC oub. contre deux |
| --- | --- | --- | --- |
| z0 | 0,47 | 1,81 | 0,18 |
| zmax 1 m | 2,12 | 3,26 | 0,10 |
| zmax 2 m (distance) | 2,79 (1,50 m) | 3,37 (0,55 m) | 0,26 |
| A 0,4–1,0 m | 0,047 | 0,265 | 0,23 |
| A 1,0–1,6 m | 0,094 | 0,299 | 0,18 |
| **A 1,6–3,0 m** | **0,001** | **−0,003** | **0,51** |
| cohérence moyenne | 0,474 | 0,478 | 0,47 |
| contraste de luminance | 0,013 | 0,021 | 0,47 |
| végétation 0–1,6 m | 0,967 | 0,965 | 0,51 |
| taille | 3,32 | 3,30 | 0,52 |

Classement des G_oub (hors bord, n = 857 ; bord = 175, 17 %) :

| Cas | bv_session_a | dev_transfert (hors bord, n = 1 129) | G_deux bv (taux de base) |
| --- | --- | --- | --- |
| signal radial absent | 477 (55,7 %) | 598 (53,0 %) | 13,8 % |
| pic déplacé (détection retenue à < 2 m) | 202 (23,6 %) | 325 (28,8 %) | 25,4 % |
| signal présent, trop faible au centre | 178 (20,8 %) | 206 (18,2 %) | 60,8 % |
| dont signal seulement au-delà de r_max | 4,5 % des G_oub | 4,9 % | 0,5 % |

Bornes (oracle, bv_session_a) : signal absent +0,036 ; pic déplacé +0,016 ; trop faible +0,014 ; bord +0,014.

Les voisines retenues à < 2 m des G_oub sont surtout des FP (471, contre 159 VP d'une autre mère). Sur les planches [O], ce sont des pics posés sur les limbes de la même couronne, à 1–1,8 m du centre. Le centre a un z modéré mais n'est pas un maximum au-dessus du seuil. Ce n'est pas une absorption par la NMS : au-delà de 1 m, la NMS ne supprime pas le centre.

**Lecture.**
- [M] La troncature r_max n'explique pas l'oubli : l'alignement à 1,6–3,0 m est nul dans les deux groupes (AUC 0,51 ; 0,46 sur dev_transfert), et le cas « seulement au-delà de r_max » ne touche que 4,5 % des G_oub. Cela confirme la grille r_max négative d'E-010.
- [M] Ni la cohérence, ni la végétation, ni le contraste ne séparent les groupes (AUC 0,47–0,53). La seule différence nette est l'alignement radial à 0,4–1,6 m (AUC 0,15 ; 0,12 sur dev_transfert), et elle est stable dans les trois classes de taille.
- [O] Sur `signal_radial_absent_*.png`, la couronne est souvent nette en RGB (par exemple bv_session_a_0014_4, 0096_0), mais la carte z est sombre au centre.
- [H] Sur ces grands limbes, le tenseur à σ_g = 4 cm / σ_t = 10 cm suivrait les nervures secondaires ou les déchirures du limbe, obliques ou perpendiculaires à la nervure principale, plutôt que les axes radiaux (bords et nervure principale). Non vérifié.

### 3. Leviers classés (gain borné, variante v5, bv_session_a) et expérience proposée

1. FN aucun candidat, +0,056, et FN sous le seuil, +0,052. Les deux tiennent au signal radial au centre. La part « grandes couronnes, signal absent » vaut +0,036. Module : orientation / vote.
2. FP autre végétal : +0,042, et +0,140 sur dev_transfert. Déjà attaqué par E-013 : gain faible, couleur réfutée.
3. FN bord de tuile : +0,025 au plus, ≈ +0,006 après correction du taux de base. Module : tuiles.
4. FP feuille isolée : +0,022. Le recentrage est négatif (E-012).
5. FP doublon : +0,018. La répulsion est réfutée (E-009b).
6. Le reste fait moins de +0,006 chacun.

**Expérience proposée E-022 (non lancée) : échelle de dérivation σ_g du champ du vote.** Elle n'a jamais été variée dans le vote : E-010 n'a varié que σ_t.
- Étape A, diagnostic sans F1, sur bv_session_a :
  - recalculer A_in aux mères ≥ 2,8 m trouvées par le v5 (G_oub hors bord, G_deux hors bord) pour σ_g ∈ {4, 6, 8, 12} cm, avec σ_t = 2,5 σ_g ;
  - T_in est recalculé à chaque échelle sur les mêmes milieux (P90).
- Critère A, écrit avant : une échelle σ_g* est retenue si la part des G_oub hors bord avec A_in ≥ T_in passe de 39,7 % (à 4 cm, mesuré dans `grandes_couronnes_bv_session_a.csv`) à au moins 55 %, et si celle des G_deux (85,6 % à 4 cm) ne baisse pas de plus de 2 points. Si plusieurs échelles passent, on retient la plus petite. Si aucune ne passe, on arrête : l'hypothèse « nervures » est réfutée et l'étape B n'est pas lancée.
- Étape B, sur bv_session_a : z = zrob(z_an(4 cm) + z_an(σ_g*)), comme `carte_votes_multi`, sans autre réglage que le seuil choisi sur bv_session_a selon la règle d'E-008.
- Critère B, écrit avant :
  - gain de F1 apparié ≥ +0,010 avec un IC 95 % par blocs qui exclut 0 ;
  - taux d'oubli des mères ≥ 2,8 m en baisse d'au moins 5 points ;
  - F1 sur dev_transfert sans baisse de plus de 0,005 ;
  - fenêtre d'égalité 0,001 (D-008).
- Réserve : le développement a déjà été exploré par environ 144 configurations, et l'optimisme de sélection est de 0,005 à 0,02 (audit). Un gain inférieur à 0,02 resterait du même ordre.
