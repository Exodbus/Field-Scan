# Robustesse à l'échelle de l'image de l'aiguillage p90 (agent C-analyste, cycle 3, 13 novembre 2026)

Question du Contrôleur : le test vierge (banana_trees_kp, dense) vient de photos à environ 11 cm/px agrandies à 5 cm. Si le v5 y répond faiblement, l'aiguillage p90 des finalistes `E10_p90_v6b_v5_d0.1` et `E5p90b_moy34_v5_d0.1` (branche « petits » quand le 90e centile des pics du v5 >= 0,15 est sous 0,55) peut envoyer des images denses vers le v6b ou vers v3 + v4. **Ni le test vierge ni les juges n'ont été lus** : simulation sur le réglage seulement.

Étiquettes : [M] mesuré (script donné), [O] observé, [H] hypothèse.

## 1. Règle de lecture (écrite à 04:02, avant toute mesure, journal `docs/nuit_2026-11-12/journal_c_analyste.md`)

« Risque confirmé si plus de 20 % des images denses sont aiguillées, ou si un finaliste perd plus de 0,020 de F1 contre le v5 à 0,30 sur les images dégradées. » Lecture principale à 11 cm/px ; 8 et 14 cm/px pour la pente.

## 2. Verdict

- **Risque confirmé par la première condition, à 11 cm/px (et à 14), pas à 8.** Dense : 33 images sur 84 aiguillées à 11 cm (39 %), 71 sur 84 à 14 cm (85 %), aucune à 8 cm [M].
- **La seconde condition n'est remplie nulle part.** Aucun finaliste ne perd plus de 0,020 contre le v5 à 0,30, sur aucun jeu ni aucune résolution. La pire perte est de -0,010 (E5p90b, plantain, 11 cm).
- **Sur le dense dégradé, l'aiguillage aide au lieu de nuire** [M] :
  - à 11 cm : E10 +0,051, E5p90b +0,010 ;
  - à 14 cm : E10 +0,170, E5p90b +0,076.

  La raison : le v5 lui-même s'effondre sur ces images. Sa F1 dense passe de 0,779 à 0,622 à 11 cm, et il ne détecte plus que 55 % des pieds. La branche « petits » remonte ce rapport à 0,68 (E10) ou 0,59 (E5p90b).
- Lecture : l'aiguillage se trompe de raison (il prend du dense flou pour de petits plants), mais il vise juste : le v5 sous-détecte, et la branche « petits » détecte plus. **Le vrai risque pour le test vierge n'est pas l'aiguillage, c'est la chute du v5 lui-même sur des photos à 11 cm** (-0,157 de F1 et -45 % de pieds sur le dense simulé). Cette chute touche aussi la référence.

## 3. Méthode [M]

- Images : toutes les images de réglage, sans échantillon : dense (84 photos, disque), plantain (165 tuiles), jeunes (1), MM (2). btd_val n'est pas utilisé (pas dense, une orthomosaïque) ; les juges non plus.
- Dégradation qui reproduit `scripts/v6_prosp_preparer.py` (mode évaluation : `resize(LANCZOS)` vers 5 cm/px, enregistrement JPEG qualité 95) :
  1. on réduit l'image à 5 cm vers c cm/px (LANCZOS) ;
  2. on la ramène à sa taille d'origine (LANCZOS) ;
  3. on fait un aller-retour JPEG qualité 95.

  Les annotations ne changent pas, la géométrie étant la même. c vaut 8, 11 et 14.
- Modèles : v5 ONNX installé, v3, v4 et v6b (`out/comptage_v6/kaggle/lot1/v6b/centres_5cm_v6b.onnx`), 2 fils. Les cartes des branches ne sont calculées que sur les images aiguillées : ailleurs, les finalistes rendent exactement le v5.
- Aiguillage et branches : `f_aiguillage_p90` de `scripts/v6_banc_candidats.py`, importé sans modification, avec les réglages exacts de `finalistes.md`.
- Mesure : celle du banc (pics fenêtre 7, rayon 20 px, appariement un-à-un, disque, zone MM, rejets ignorés), au seuil 0,30.
- Scripts : `scripts/v6_analyse_degradation.py --cm 11 8 14 --fils 2`, puis `scripts/v6_analyse_degradation_detail.py`.
- Sorties : `degradation_images.csv` (une ligne par image et résolution), `degradation.md`, `degradation_detail.md`.
- Essais : 3 résolutions x 3 candidats (v5 et les 2 finalistes) = 9 mesures, aucune décision.

## 4. Résultats [M]

### 4.1 Part d'images aiguillées et F1 au seuil 0,30

| cm/px | jeu | aiguillées | p90 médian du v5 (5 cm -> dégradé) | F1 v5 | F1 E10 (v6b) | écart | F1 E5p90b (v3+v4) | écart | détectés / annotés v5 / E10 / E5p90b |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 (référence, `finalistes.md`) | dense | 0 / 84 | 0,71 | 0,779 | 0,779 | 0 | 0,779 | 0 | 1,08 / 1,08 / 1,08 |
| 5 (référence) | plantain | 15 / 165 | 0,73 | 0,886 | 0,882 | -0,004 | 0,877 | -0,009 | 1,11 / 1,12 / 1,14 |
| 8 | dense | 0 / 84 (0 %) | 0,71 -> 0,66 | 0,756 | 0,756 | 0 | 0,756 | 0 | 0,88 / 0,88 / 0,88 |
| 8 | plantain | 23 / 165 (14 %) | 0,73 -> 0,70 | 0,886 | 0,882 | -0,004 | 0,877 | -0,009 | 1,04 / 1,06 / 1,08 |
| **11** | **dense** | **33 / 84 (39 %)** | 0,71 -> 0,56 | 0,622 | 0,673 | **+0,051** | 0,632 | **+0,010** | 0,55 / 0,68 / 0,59 |
| 11 | plantain | 41 / 165 (25 %) | 0,73 -> 0,65 | 0,875 | 0,869 | -0,006 | 0,865 | -0,010 | 0,93 / 0,99 / 1,01 |
| 14 | dense | 71 / 84 (85 %) | 0,71 -> 0,50 | 0,479 | 0,649 | +0,170 | 0,555 | +0,076 | 0,36 / 0,61 / 0,48 |
| 14 | plantain | 54 / 165 (33 %) | 0,73 -> 0,61 | 0,846 | 0,850 | +0,005 | 0,843 | -0,003 | 0,84 / 0,94 / 0,96 |

Jeunes et MM : aucune image aiguillée, quelle que soit la résolution. Le v5 seul y recule : jeunes 0,893 (5 cm), 0,899 (8 cm), 0,768 (11 cm), 0,630 (14 cm) ; MM 0,857, 0,770, 0,724, 0,655.

### 4.2 Images aiguillées seules

| cm/px | jeu | images (annotés) | F1 v5 (dét./ann.) | F1 E10 | F1 E5p90b |
| --- | --- | --- | --- | --- | --- |
| 11 | dense | 33 (2 766) | 0,595 (0,55) | 0,732 (0,93) | 0,626 (0,67) |
| 14 | dense | 71 (6 707) | 0,469 (0,36) | 0,673 (0,66) | 0,562 (0,51) |
| 8 | plantain | 23 (108) | 0,578 (1,56) | 0,556 (2,00) | 0,519 (2,39) |
| 11 | plantain | 41 (293) | 0,651 (0,93) | 0,661 (1,49) | 0,646 (1,66) |
| 14 | plantain | 54 (513) | 0,649 (0,69) | 0,717 (1,22) | 0,691 (1,32) |

Les tuiles plantain aiguillées sont des tuiles pauvres : 108 à 513 plants en tout, soit 5 à 10 plants par tuile. Les finalistes y **surcomptent** fortement (1,2 à 2,4 fois les annotés). Sur ces tuiles, l'erreur de compte des finalistes est pire que celle du v5. Sur le jeu entier elle reste petite : plantain à 11 cm, détectés / annotés 0,99 et 1,01, contre 0,93 pour le v5.

### 4.3 Erreur de compte (|détectés / annotés - 1|)

| cm/px | dense v5 / E10 / E5p90b | plantain v5 / E10 / E5p90b |
| --- | --- | --- |
| 8 | 0,12 / 0,12 / 0,12 | 0,04 / 0,06 / 0,08 |
| 11 | 0,45 / 0,32 / 0,41 | 0,07 / 0,01 / 0,01 |
| 14 | 0,64 / 0,39 / 0,52 | 0,16 / 0,06 / 0,04 |

À 11 et 14 cm, les finalistes ont une erreur de compte plus basse que le v5 sur le dense. À 8 cm, elle est un peu plus haute sur le plantain (+0,02 à +0,04).

### 4.4 Le signal p90 (quantiles 10 / 50 / 90 % des images)

| cm/px | dense | plantain |
| --- | --- | --- |
| 5 | 0,66 / 0,71 / 0,75 | 0,56 / 0,73 / 0,81 |
| 8 | 0,60 / 0,66 / 0,70 | 0,50 / 0,70 / 0,79 |
| 11 | 0,52 / 0,56 / 0,61 | 0,44 / 0,65 / 0,75 |
| 14 | 0,45 / 0,50 / 0,56 | 0,37 / 0,61 / 0,70 |

Le p90 du dense baisse d'environ 0,05 par palier de 3 cm/px, et la coupure 0,55 tombe au milieu de la distribution à 11 cm. Le signal mesure la confiance du v5 et non la taille des plants : il ne distingue pas « petits plants » et « image floue ». Le cycle 1 l'avait signalé : agrandir l'image ne remonte pas les scores des petits plants (`rapport_cycle1.md`, section 3.7). Ici, c'est l'inverse : une image floue fait baisser les scores des grands plants.

## 5. Ce que cela implique (pour le chef d'orchestre et le Contrôleur ; aucune décision prise ici)

1. Sur un test vierge à environ 11 cm/px, il faut s'attendre à ce qu'environ 40 % des images denses partent vers la branche « petits » [H, si la simulation est fidèle]. **Dans la simulation, ce n'est pas une perte de F1, c'est plutôt un gain** : E10 +0,05, E5p90b +0,01 sur le dense. Le résultat du test mesurera donc en partie le v6b ou v3 + v4 sur du dense flou, et non la seule branche v5 : à écrire avec le chiffre du test.
2. La perte qui compte est celle du v5 lui-même : sur le dense, F1 de 0,779 à 0,622 et détectés / annotés de 1,08 à 0,55 à 11 cm. Tous les candidats et la référence la subissent. Le bulletin sous-compterait d'environ 45 % sur des images de cette résolution, hors fourchette (0,78 à 0,93).
3. Si l'on voulait un aiguillage qui ne réagisse qu'à la taille des plants, il faudrait un signal insensible au flou : par exemple l'espacement médian des pics ramené en mètres, ou la résolution d'origine connue (cm/px de la source). [H] À écrire avant toute mesure. Ce n'est pas proposé pour cette nuit : la règle de choix des finalistes est déjà écrite.

## 6. Limites

- La simulation part d'images déjà à 5 cm, elles-mêmes tirées de photos à 1,1 cm (banavista) ou d'orthomosaïques (plantain). Une vraie photo à 11 cm a un autre bruit, une autre netteté et une autre compression. La dégradation LANCZOS + JPEG 95 est plutôt douce [H] : le vrai test pourrait être plus dur encore.
- Le test vierge est dense « kp » (points clés) : sa mesure et sa géométrie diffèrent peut-être (par exemple sans disque). Rien n'en a été lu.
- Le v6b a appris btd_train ; son comportement sur le dense flou (0,732 sur les 33 images aiguillées à 11 cm) n'a été mesuré nulle part ailleurs.
- Petits effectifs : jeunes (1 image), MM (2 images), plantain aiguillé (108 à 513 plants).
