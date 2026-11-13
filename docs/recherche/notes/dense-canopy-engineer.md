# Notes de dense-canopy-engineer

## 1. E-024 : distance aux trouées (7 novembre 2026)

Pré-enregistrement : `docs/experiment-log.md`, entrée E-024 (écrite avant tout calcul). Ce qui suit précise la mise en œuvre là où l'entrée est muette. **Écrit le 7 novembre 2026 à 19 h 20, avant tout calcul, y compris le contrôle synthétique.** Les grilles (p, a, σ_d, w) et les seuils des critères A et B ne sont pas modifiés.

Code : `comptage_math/dense.py` ; scripts `out/comptage_math/dense-canopy-engineer/e024_synthetique.py` et `e024_trouees.py` ; sorties `out/comptage_math/dense-canopy-engineer/E-024/`. Patron : `out/comptage_math/convergence-engineer/e023_frst.py` (E-023), repris pour les groupes, l'échantillonnage, l'étape B et le critère B.

### 1.0 Précisions de mise en œuvre (avant calcul)

- **Pixels valides** : somme RGB > 15 (comme `votes.carte_votes_image` et E-023).
- **Masque végétation** : celui que renvoie `votes.champ` avec ses défauts (B′ figé, `masque="provisoire"`), c'est-à-dire `orientation.masque_vegetation(bgr)`. `dense.py` appelle directement `orientation.masque_vegetation` (le tenseur de `champ` est inutile ici) ; le script vérifie l'égalité au pixel près avec `votes.champ(...)[1]` sur 3 tuiles de bv_session_a avant l'étape A.
- **Luminance** : `orientation.luminance` (même canal que `votes.champ`), lissée par une gaussienne d'écart-type 5 cm / res px (bord réfléchi).
- **Centile p** : calculé sur la luminance lissée des pixels végétation ∩ valides de la tuile.
- **Trouées brutes** = (non végétation) ∪ (luminance lissée < centile p), à la lettre de l'entrée : les pixels non valides (bords noirs) sont hors du masque végétation, donc trouées.
- **Nettoyage** :
  - ouverture morphologique du masque des trouées par un disque de rayon max(1, round(2,5 cm / res)) px (élément elliptique OpenCV ; 3 × 3 à 3,6 cm/px) ;
  - puis suppression des composantes connexes (8-connexité) de trouées d'aire < a / res² px.
- **D** = `scipy.ndimage.distance_transform_edt` des pixels non-trouées à la trouée la plus proche, × res (mètres). L'extérieur de la tuile n'est pas une trouée. Si une tuile n'a aucune trouée après nettoyage, z_D = 0 partout (cas consigné).
- **Lissage** : gaussienne d'écart-type σ_d / res px, bord réfléchi.
- **z robuste** : médiane et MAD × 1,4826 de D lissé sur le masque végétation ∩ valides (repli sur toute la tuile si moins de 100 pixels), appliquées à toute la tuile (comme `symetrie.zrob_masque`).
- **Échantillonnage** : valeur de z_D au pixel entier du point (comme `e008_votes.echantillon`, E-021 et E-023).
- **Groupes** (CSV d'E-021, lecture seule), comme E-023 § 13.0 :
  - « signal absent » = `groupe_cmp == "G_oub"`, `d_bord_m ≥ 1`, `cas == "signal radial absent"` (477 sur bv_session_a, 598 sur dev_transfert) ;
  - trouvées = `G_deux`, `d_bord_m ≥ 1` (2 742 ; 4 725) ;
  - milieux = toutes les lignes de `nul_milieux_*.csv` ; T = P90 de z_D sur les milieux du même jeu, configuration par configuration.
- **Critère A** : part ≥ seuil sans fenêtre (les seuils de l'entrée sont lus à la lettre : 40 %, 60 %, 30 %). Configuration retenue = plus grand nombre de « signal absent » au-dessus de T parmi celles qui passent les trois conditions.
- **Égalité au critère A** (même effectif) : σ_d 10 cm avant 25 cm, puis a 0,02 avant 0,08 m², puis p 15 avant 25.
- **Planche** : 12 « signal absent » de bv_session_a tirés par `DataFrame.sample(12, random_state=2026)`, fenêtre de 6 m, colonnes RGB / trouées nettoyées / z_D ; configuration retenue, ou, si A échoue, celle qui a la plus forte part « signal absent » sur bv_session_a (illustration seulement).
- **Étape B** (si A passe), comme E-023 § 13.0 :
  - B′ figé = `votes.carte_votes_image(r_max 1,6, p 1)["z"]`, maxima et NMS 1,0 m de `e008_votes.detecter` (z ≥ 0,5) ; contrôle : même nombre de détections que `E-010/detections/vote_e010.csv` sur bv_session_a ;
  - z_D seul : mêmes maxima et NMS sur z_D ;
  - fusion z = zrob(z_vote + w z_D) (`votes.zrob` sur les pixels valides), mêmes maxima et NMS ;
  - seuil de chaque carte = maximum du F1 cumulé sur bv_session_a (200 quantiles, règle d'E-008) ;
  - choix de w ∈ {0,5 ; 1,0} : meilleur F1 cumulé ; à 0,001 près (D-008), w = 0,5 ;
  - gain apparié contre B′ (chacun à son seuil) ; IC 95 % par blocs de 7 photos : colonne `unite` triée par ordre alphabétique, blocs consécutifs de 7 (dernier bloc incomplet), 2 000 tirages, graine 2026 ; IC par photo rapporté à côté, sans effet sur la décision ;
  - oubli des mères de **2,8 m et plus** (taille × cm/px ≥ 2,8, à la lettre de l'entrée ; E-023 utilisait > 2,8, la différence est de mesure nulle sur une taille continue), appariement à 1 m (`evaluer_comptage.apparier`), région comptée seulement ; baisse = oubli(B′) − oubli(fusion) ;
  - dev_transfert : `scripts/math_evaluer.py --roles dev_transfert --seuil-fixe` (lecture seule) pour B′, la fusion retenue et z_D seul ; perte = F1(B′) − F1(fusion) ;
  - fenêtre d'égalité 0,001 (D-008) : gain ≥ 0,010 − 0,001 avec borne basse de l'IC par blocs > 0 ; baisse ≥ 0,05 − 0,001 ; perte ≤ 0,005 + 0,001 ;
  - un gain < 0,02 est déclaré ambigu.
- **Données** : bv_session_a (rôle `dev_reglage`, sans pépinière) et dev_transfert. Assertions : aucun groupe bv_b_*, aucun rôle val_*, aucun chemin `cg/` ni `D-013`, aucun groupe de `math_evaluer.INTERDITS`.
- **Parallélisme** : 4 processus.

### 1.1 Contrôle synthétique (critère écrit dans l'en-tête du script, avant de le lancer)

Critère (en-tête de `e024_synthetique.py`, écrit avant le premier lancement) : scène 3,6 cm/px, trois disques de feuillage de 1,5 m jointifs (triangle de côté 2,7 m, trouée centrale), fond sombre, bruit de luminance σ 15 niveaux, 12 taches sombres de 1,5 px ; pour chacune des 8 configurations, les 3 plus hauts maxima de z_D (NMS 1,0 m, z ≥ 0,5) à moins de 0,20 m d'un centre distinct.

Résultat [M, E-024s] (`PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/dense-canopy-engineer/e024_synthetique.py` ; `E-024/controle_synthetique.json`) — écrit après le contrôle, avant l'étape A :

- **Échoue** : aucune des 8 configurations ne passe (écart maximal 0,63 à 2,35 m). 1 178 à 2 364 pixels de trouées nettoyées restent dans le feuillage.
- Diagnostic fait **après** l'échec, sans valeur de critère (script jetable dans le bloc-notes, non conservé) : même scène sans taches, bruit σ 0 → les 8 configurations placent les 3 maxima à 0,01–0,05 m des centres ; bruit σ 5 → 2 configurations sur 8 seulement (p 15, a 0,02) ; bruit σ 15 → aucune.
- Lecture [H] : le code de distance est juste (cas sans texture) ; c'est la **règle du centile** qui fragmente le feuillage : par construction, p % des pixels de végétation deviennent des trouées, et sur une texture fine une partie forme des amas plus grands que a ou reliés au bord, que le nettoyage ne retire pas. Les maxima de D tombent alors entre ces amas, pas au centre.
- Conséquence : l'étape A est lancée comme pré-enregistré (l'entrée E-024 ne la conditionne pas au contrôle synthétique, comme en E-023) ; l'échec est un écart signalé. Prédiction [H] écrite avant l'étape A : sur les vraies couronnes, dont les limbes alternent avec des ombres internes, z_D sera dominé par cette fragmentation et le critère A a peu de chances de passer.

### 1.2 Étape A [M, E-024] (après calcul ; § 1.0 non modifié)

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/dense-canopy-engineer/e024_trouees.py` (148 s, 4 processus). Sorties : `E-024/bilan_E-024.json`, `etapeA_*.csv`, `critere_A.csv`, `planche_signal_absent.png` et `.csv`, `E-024.log`. Contrôle : masque de `dense.py` identique au masque de `votes.champ` sur 3 tuiles.

Part au-dessus de T = P90 des milieux (« absent » : n = 477 bv_session_a, 598 dev_transfert ; trouvées : 2 742 et 4 725) :

| Config. (p, a m², σ_d cm) | absent bv_a | trouvées bv_a | absent dev | trouvées dev |
| --- | --- | --- | --- | --- |
| 15, 0,02, 10 | 43,2 % | 49,5 % | 39,5 % | 41,9 % |
| 25, 0,02, 10 | 30,4 % | 34,9 % | 33,8 % | 33,0 % |
| 15, 0,08, 10 | 42,4 % | 45,6 % | 37,6 % | 42,0 % |
| 25, 0,08, 10 | 40,0 % | 42,6 % | 36,8 % | 37,5 % |
| **15, 0,02, 25** | **44,9 %** | **50,4 %** | 41,6 % | 43,1 % |
| 25, 0,02, 25 | 33,8 % | 38,2 % | 34,1 % | 35,4 % |
| 15, 0,08, 25 | 42,6 % | 44,1 % | 35,6 % | 41,4 % |
| 25, 0,08, 25 | 43,6 % | 43,5 % | 35,8 % | 38,7 % |

**Critère A : échoue.** Condition 1 (≥ 40 %) remplie par 6 configurations sur 8 ; condition 3 (dev ≥ 30 %) par les 8 ; **condition 2 (trouvées ≥ 60 %) par aucune** (maximum 50,4 %). Selon la règle : arrêt, étape B non lancée, distance aux trouées réfutée comme complément du vote au sens du critère.

Lecture :
- [M] Contrairement à la FRST (E-023), le signe est le bon : médiane de z_D aux mères (« absent » 0,4 à 1,2 ; trouvées 0,5 à 1,3) au-dessus des milieux (−0,33 à −0,43), sur les deux jeux. Les parts (30 à 50 %) sont 3 à 5 fois le taux de base de 10 %. La carte porte de l'information, mais trop peu pour la condition des mères trouvées.
- [M] Le centile p = 15 fait mieux que p = 25 dans 3 couples sur 4 : plus on déclare de trouées par le centile, plus le feuillage est fragmenté (cohérent avec le contrôle synthétique, § 1.1).
- [O] Planche (`planche_signal_absent.png`, configuration 15, 0,02, 25 à titre d'illustration ; 4 cas sur 12 au-dessus de T) : les trouées nettoyées découpent la canopée en crêtes allongées ; les maxima de z_D suivent ces crêtes (souvent un limbe clair ou l'espace entre deux plants) plutôt que le centre de la couronne. Sur 0118_5 et 0105_5, le centre est sur une crête qui longe une grande trouée de sol.
- [H] En canopée fermée, les trouées visibles sont surtout des ombres internes et des bandes de sol entre rangs, pas un contour fermé autour de chaque couronne ; la distance aux trouées dessine des crêtes, pas des sommets isolés aux centres.

## 2. E-025 : fusion vote B′ + distance aux trouées, mesurée en F1 (7 novembre 2026)

Pré-enregistrement : `docs/experiment-log.md`, entrée E-025 (non modifiée). Configuration figée p 15, a 0,02 m², σ_d 25 cm ; étape A d'E-024 non relancée, aucune autre configuration mesurée. Code : `out/comptage_math/dense-canopy-engineer/e025_fusion.py`, qui importe `e024_trouees.py` (fonction `tache_b`, inchangée) et recopie le corps d'`etape_b` avec les sorties E-025. `comptage_math/dense.py` et `votes.py` non modifiés.

Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/dense-canopy-engineer/e025_fusion.py` (186 s, 4 processus). Sorties : `E-025/bilan_E-025.json` (empreintes SHA-256), `E-025/detections/`, `E-025/evaluateur/`, `E-025/E-025.log`.

**Contrôle [M, E-025].** Le vote B′ recalculé retrouve E-010 : 16 650 détections sur bv_session_a (identique au fichier E-010), même seuil 2,2382, F1 0,6368 ; dev_transfert 0,5455.

**Résultats [M, E-025]** (seuil par la règle d'E-008 sur bv_session_a ; dev_transfert au même seuil) :

| Candidat | Seuil | F1 bv_session_a | F1 dev_transfert | Oubli mères ≥ 2,8 m (n = 5 079) |
| --- | --- | --- | --- | --- |
| Vote B′ (E-010) | 2,238 | 0,6368 | 0,5455 | 29,47 % |
| Fusion w = 0,5 | 1,823 | **0,6580** | **0,5468** | **23,19 %** |
| Fusion w = 1,0 | 1,224 | 0,6442 | 0,5141 | 20,52 % |
| z_D seul (information) | 0,522 | 0,5074 | 0,4123 | 37,23 % |

w retenu : 0,5 (F1 le plus haut sur bv_session_a). Critère pour w = 0,5 :
1. gain apparié +0,0212, IC 95 % par blocs de 7 photos [+0,0082 ; +0,0362] (10 blocs) : rempli ;
2. oubli des grandes mères 29,47 % → 23,19 %, baisse de 6,3 points : rempli ;
3. dev_transfert 0,5468 contre 0,5455 (perte −0,0013) : rempli.

**Verdict selon la règle écrite : succès** (gain ≥ 0,02, donc pas « ambigu » ; la marge est de 0,0012). Réserves écrites d'avance : seuil et w choisis sur les images du verdict ; aucun test indépendant (val_scellee consommée) : résultat de développement, pas une adoption.

Lecture :
- [M] La fusion gagne surtout en rappel (0,643 → 0,703) pour une précision un peu plus basse (0,630 → 0,619) ; avec w = 1,0 la précision chute (0,575) et le transfert se dégrade.
- [H] Cohérent avec la remarque après E-024 : z_D, faible seul, apporte une information peu corrélée au vote.
