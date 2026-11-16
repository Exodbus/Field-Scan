# Journal de l'agent Télédétection, 15/11/2026

Modules : vigueur (Sentinel-2 et drone), stress hydrique, suivi temporel. Règle appliquée : `docs/plan_journee_2026-11-15.md`, section 3, telle quelle.
Écriture seulement dans `out/teledetection/jour_1511/`, `scripts/t15_*.py` et ce journal. Processeur : 2 fils au plus. Aucune image Sentinel-2 de Côte d'Ivoire lue.

## 13 h 57 : lectures

Lu : `CLAUDE.md`, plan du jour (section 3), `fieldscan/modules/vigueur.py`, `stress.py`, `temporel.py`, `fieldscan/anomalies.py`, `fieldscan/sentinel2.py`, `fieldscan/drone.py`, `config.yaml`, `fieldscan/config.py` (valeurs par défaut), carnet de données (Sentinel-2, anomalies, ReforesTree).

Constats [O] utiles au banc :
- vigueur S2 : zones faibles (NDVI et NDRE, pixel contre médiane de sa parcelle, z < −2 et écart < −0,05, 5 pixels au moins) et parcelles faibles (médiane contre les autres parcelles « ok »). Le bulletin ne garde que la date de référence de chaque parcelle.
- stress : résidu de la droite NDMI ~ NDVI ajustée sur tout le site, z < −2 et résidu < −0,03.
- temporel : **aucune zone**, seulement des alertes de parcelle (delta de médiane moins la variation médiane du site, z < −2, écart < −0,05 en NDVI, −0,03 en NDMI).
- drone : ExG lissé sur 3 m, grille 50 cm, bordure de 3 m exclue, z < −2 et écart < −0,03, zones de 25 m² au moins.
- Équateur : 13 parcelles, toutes « ok » aux 2 dates (aucun nuage). Côte d'Ivoire : 33 parcelles (non lue).
- ReforesTree : 6 orthomosaïques de sites d'environ 2 à 2,6 ha (≈ 160 m de côté, ≈ 1 cm/pixel, EPSG:4326). `El Oro OAM RGB.tif` n'est pas un site ReforesTree : exclu.

## 14 h 01 : protocole d'injection, écrit avant tout calcul

### Découpage
- Sentinel-2 : réglage = Équateur (2023-02-10 et 2023-08-29). Mesure = Côte d'Ivoire, lue une fois après 15 h 50 par le juge, pour les finalistes seulement.
- Drone : les 6 sites ReforesTree par ordre alphabétique : 1 Carlos Vera Arteaga, 2 Carlos Vera Guevara, 3 Flora Pluas, 4 Leonor Aspiazu, 5 Manuel Macias, 6 Nestor Macias. Un sur deux, en commençant par le premier :
  - **réglage = Carlos Vera Arteaga, Flora Pluas, Manuel Macias** (rangs 1, 3, 5) ;
  - **mesure = Carlos Vera Guevara, Leonor Aspiazu, Nestor Macias** (rangs 2, 4, 6).
  - Réserve : Carlos Vera Arteaga et Carlos Vera Guevara sont voisins (≈ 200 m) et tombent de part et d'autre. Aucun apprentissage ici, le risque de fuite est faible ; je le note.
- Parcelles drone : il n'existe pas de parcelles sur ReforesTree. Une parcelle = le polygone du site (`data/drone/reforestree/prepare/sites.geojson`). La comparaison au site se fait entre les 3 sites d'une même moitié.

### Scènes
- Vigueur S2 et stress : une scène = une date d'un pays, traitée seule (le module ne voit que cette date, donc sa date de référence est celle-là). Réglage : 2 scènes.
- Temporel : une scène = la paire de dates (date 1 intacte, injection sur la date 2 seulement). Réglage : 1 scène.
- Drone : une scène = les 3 sites d'une moitié, injectés ensemble.
- Scènes sans injection : les mêmes, intactes (2 en vigueur et stress, 1 en temporel, 1 en drone).

### Tirages
- Sentinel-2 : **20 tirages par scène**, graines `1000 × k_module + 100 × k_scène + t` (t = 0 à 19 ; k_module : vigueur 1, stress 2, temporel 3 ; k_scène : rang de la date ou de la paire, à partir de 0). **6 zones par tirage**, chacune dans une parcelle différente, tirée au hasard parmi les parcelles « ok » (nuages < 50 %, aux deux dates pour le temporel). Gravités : 2 zones par niveau, dans l'ordre tiré.
- Surface : tirée uniformément en log entre 0,1 et 1 ha (rayon = √(S/π)). Le disque doit tenir entier dans la parcelle rétrécie de 10 m ; sinon nouveau tirage de taille, puis de parcelle (100 essais au plus ; la zone est alors abandonnée et comptée dans le journal).
- Drone : **20 tirages**, graine `4000 + t`. **2 zones par site et par tirage**, sans recouvrement (écart de 5 m entre bords au moins), surface log-uniforme entre **0,1 et 0,4 ha** (dans la plage du plan, bornée parce qu'un site ne fait que 2 à 2,6 ha), disque entier dans le site rétréci de 6 m. Gravités : tirage t, site s, zone j → niveau (t + s + j) mod 3.
- Mesure (juges, plus tard) : mêmes règles, graines décalées de + 50 000.

### Gravités (3 niveaux par module, valeurs fixées avant calcul)
| Module | Modification | Faible | Moyenne | Forte |
| --- | --- | --- | --- | --- |
| Vigueur S2 | réflectance PIR (B08 et B8A) × (1 − g) | g = 0,10 | 0,20 | 0,35 |
| Stress | B11 × (1 + g) | g = 0,05 | 0,10 | 0,20 |
| Temporel | PIR (B08, B8A) × (1 − g), date 2 seulement | g = 0,10 | 0,20 | 0,35 |
| Drone | canal vert × (1 − g) sur l'image RGB lue à 50 cm | g = 0,03 | 0,06 | 0,12 |

Ordres de grandeur attendus [H, calcul à la main sur des valeurs typiques] : vigueur, NDRE −0,03 / −0,06 / −0,12 (le NDVI bouge peu, saturé en Équateur) ; stress, NDMI −0,02 / −0,04 / −0,09 ; drone, ExG −0,02 / −0,045 / −0,09. Le niveau faible est volontairement au bord des seuils actuels.

### Forme des zones
- Disque. Part de chaque pixel dans le disque calculée par sur-échantillonnage 5 × 5 (f entre 0 et 1) ; la bande est modifiée par f × g.
- Bandes à 20 m natifs (B05, B8A, B11) : la carte f est d'abord lissée par une moyenne 2 × 2 pixels (empreinte d'un pixel de 20 m), pour imiter le flou réel de ces bandes. B08 (10 m) : f sans lissage.
- Drone : f calculée à la résolution de 50 cm, sans lissage.
- Injection Sentinel-2 dans les bandes lues par `fieldscan.sentinel2._lire_scene`, puis indices recalculés par `indice_normalise`, avec les mêmes pixels exclus que la préparation du module (nuages, halo, eau). Les statuts des parcelles et la carte des parcelles sont ceux de `preparer`, intacts.

### Mesures (plan, section 3)
- Pixels d'une zone injectée : pixels dont le centre est dans le disque (f ≥ 0,5).
- **Rappel** : part des zones dont au moins 50 % des pixels sont en alerte (zone d'alerte du module). Rapporté par gravité ; **rappel moyen** = moyenne des 3 rappels par gravité.
- **Fausses alertes (ha)** : surface en alerte hors des zones injectées, la zone étant élargie de 1 pixel (10 m) en Sentinel-2 et de 3 m (lissage) en drone, pour ne pas compter le flou de l'injection elle-même. Rapportées par tirage (moyenne), et **sur les scènes sans injection** (somme des scènes intactes) : c'est cette dernière qui entre dans la règle.
- **Alerte de parcelle** : part des parcelles contenant une zone de gravité forte qui passent en alerte de parcelle (vigueur : `parcelle_faible` ; stress : `parcelle_stress` ; temporel : `degradation` ; drone : `parcelle_faible`).
- Zone d'alerte du module :
  - vigueur S2 : union des zones faibles NDVI et NDRE ;
  - stress : zones de stress ;
  - temporel (référence) : le module n'a pas de zones ; la zone d'alerte est **la parcelle entière** quand elle passe en `degradation` (NDVI ou NDMI). Une variante à zones est permise (essai) ;
  - drone : zones faibles ExG.
- Référence : la méthode en service appelée **telle quelle** (fonctions de `fieldscan.modules.*` avec un contexte dont le cache Sentinel-2 contient les indices injectés ; pour le drone, `fieldscan.drone.lire_fenetre` remplacé à l'exécution, dans le banc seulement, par une lecture en cache suivie de l'injection). Les géométries d'alerte rendues (WGS84) sont reprojetées et rastérisées sur la grille. Les variantes sont réécrites dans le banc avec les fonctions de `fieldscan.anomalies` ; la variante « service » réécrite doit redonner la référence (contrôle).

### Règle (plan, section 3, recopiée)
- **Finaliste** si, sur le réglage : rappel moyen ≥ référence + 0,05 ; aucun niveau de gravité ne perd plus de 0,02 ; fausses alertes sur scènes sans injection ≤ référence (ha).
- Si plusieurs variantes d'un module passent : **2 finalistes au plus par module**, classées par rappel moyen décroissant, puis fausses alertes sans injection croissantes (règle propre, écrite ici avant calcul).
- Chaque variante calculée compte pour un essai, y compris celles qui ne changent qu'un seuil.

## Compte des essais
(tenu plus bas, au fil des calculs)

## 14 h 03 : liste et ordre des essais, écrits avant leur calcul

Code : `scripts/t15_commun.py`, `scripts/t15_banc_s2.py` (dictionnaire `VARIANTES`), `scripts/t15_banc_drone.py`. Tous les essais d'un module sont calculés ensemble, sur les mêmes tirages ; la décision suit la règle du plan, sans retouche après lecture.

Réglages du service (référence) : z < −2 ; écart 0,05 (NDVI, NDRE), 0,03 (résidu NDMI), 0,03 (ExG) ; plancher σ 0,01 ; 5 pixels (S2) ou 25 m² (drone).

Contrôles (pas des essais) : `VS0r`, `SS0r`, `TS0r`, `DS0r` = la méthode du service réécrite dans le banc ; elle doit redonner la référence (écart toléré : quelques pixels dus à la rastérisation aller-retour).

**Vigueur S2 (6 essais)**
- VS1 : NDRE seul (NDVI retiré).
- VS2 : lissage 3 × 3 pixels dans la parcelle (NDVI et NDRE), seuils du service.
- VS3 : écart minimal NDRE 0,03 (seuil seulement).
- VS4 : lissage 3 × 3 + écart minimal NDRE 0,03.
- VS5 : seuil z −1,5 (seuil seulement).
- VS6 : NDRE seul + lissage 3 × 3 + écart minimal 0,03.

**Stress (6 essais)**
- SS1 : droite NDMI ~ NDVI ajustée par parcelle (30 pixels valides au moins, sinon droite du site) pour les zones.
- SS2 : correction du flou de B11 : NDVI lissé par le noyau « tente » 3 × 3 (empreinte d'un pixel de 20 m) avant la droite et le résidu.
- SS3 : résidu lissé 3 × 3 dans la parcelle.
- SS4 : SS2 + SS3.
- SS5 : écart minimal du résidu 0,02 (seuil seulement).
- SS6 : SS1 + SS3.
- Alerte de parcelle des variantes : comme le service (droite du site, résidu non lissé), avec le NDVI de la variante.

**Temporel (4 essais)**
- Les alertes de parcelle restent celles du service ; les variantes ajoutent des **zones** (le service n'en a pas) et la zone d'alerte devient ces zones seules.
- TS1 : delta par pixel moins la variation commune au site (médiane des deltas de parcelle), z robuste sur tous les pixels « ok » du site.
- TS2 : delta par pixel comparé à la médiane du delta de **sa parcelle** (z dans la parcelle).
- TS3 : TS1 + lissage 3 × 3 du delta.
- TS4 : TS2 + lissage 3 × 3 du delta.
- NDVI et NDMI, écarts 0,05 et 0,03, z < −2, 5 pixels au moins.

**Drone (5 essais)**
- DS1 : VARI = (G − R) / (G + R − B).
- DS2 : GLI = (2G − R − B) / (2G + R + B).
- DS3 : ExG, lissage 5 m.
- DS4 : ExG, écart minimal 0,02 (seuil seulement).
- DS5 : ExG, lissage 2 m.
- Écart minimal de VARI et GLI : 0,03 × (médiane des σ robustes intra-site de l'indice / même chose pour l'ExG), mesurée sur les images **intactes** des 3 sites de réglage, avant toute injection (règle écrite ici).

**Total prévu : 21 essais.** Un essai rapide de fonctionnement (1 tirage) ne porte que sur la référence et les contrôles.

## 14 h 07 : essais de fonctionnement (référence et contrôles seulement, 1 à 2 tirages, dossier `essai_rapide/`)

- Les contrôles réécrits (`VS0r`, `SS0r`, `TS0r`, `DS0r`) redonnent exactement la référence du service (mêmes rappels, mêmes fausses alertes au mètre carré près) : le banc rastérise correctement les alertes du module.
- Lecture drone : fenêtre de chaque site à 50 cm par `fieldscan.drone.lire_fenetre` (16 à 26 s par site), mise en cache dans `out/teledetection/jour_1511/cache_drone/`.
- Contrôle mécanique de l'injection drone (tirage 4000, sans détection) : baisse moyenne de l'ExG dans les zones −0,021 (faible), −0,041 à −0,043 (moyenne), −0,088 (forte), conforme aux ordres de grandeur prévus.
- σ robuste intra-site (images intactes, réglage) : ExG 0,0480, VARI 0,0570, GLI 0,0335 → écarts minimaux par la règle de 14 h 03 : VARI 0,0356, GLI 0,0209.
- Remarque [O] : le σ intra-site de l'ExG (0,048) est grand devant la baisse forte (0,088) : sites agroforestiers hétérogènes (arbres, sol nu). La référence drone détectera peu.

## 14 h 08 : lancement du banc complet de réglage (20 tirages, tous les essais), modules l'un après l'autre (2 fils au plus)
Fin à 14 h 10 (≈ 1 min de calcul). Résultats : `out/teledetection/jour_1511/reglage/resume_*.csv`, décision : `decision_*.csv` (`scripts/t15_decider.py`).

## 14 h 12 : tour 1, décision par la règle (21 essais comptés)

| Module | Référence : rappel moyen (faible / moyenne / forte) ; FA sans injection | Passent la règle | Finalistes |
| --- | --- | --- | --- |
| Vigueur S2 | 0,463 (0,013 / 0,388 / 0,988) ; 0,365 ha | aucun (VS3, VS4, VS6 gagnent du rappel mais FA × 4,6 à 4,8) | — |
| Stress | 0,525 (0,038 / 0,550 / 0,988) ; 0,049 ha | aucun (SS5 gagne +0,14 mais FA 0,78 ha) | — |
| Temporel | 0,092 (0,075 / 0,125 / 0,075) ; 5,44 ha | TS1, TS2, TS3, TS4 | **TS2** (0,792 ; 1,74 ha), **TS1** (0,767 ; 2,30 ha) |
| Drone | 0,000 (0 / 0 / 0) ; 0,012 ha | DS1 | **DS1** VARI (0,067 ; 0,011 ha) |

Constats [M, banc de réglage] :
- VS5 (z −1,5) = référence à l'identique : en Équateur, c'est l'écart minimal qui décide, pas le z.
- Le lissage 3 × 3 (VS2, SS3) fait perdre la gravité moyenne : il étale les petites zones sous les 50 %.
- SS1 et SS2 ramènent les fausses alertes sans injection de 0,049 à 0 ha, à rappel presque égal.
- Temporel : le gain vient surtout de la définition. La référence n'a pas de zones : sa zone d'alerte est la parcelle entière (P06, 5,4 ha sur la paire intacte) ; les variantes n'ont que leurs zones. Écrit avant (14 h 03), donc appliqué, mais à dire dans le rapport.
- Drone DS1 : marge de fausses alertes de 0,001 ha (4 pixels de 50 cm) : très fragile ; 8 zones fortes touchées sur 40.

## 14 h 14 : tour 2, écrit avant son calcul (7 essais de plus, total 28)

Idée : le lissage à l'échelle des bandes à 20 m et la droite par parcelle ôtent des fausses alertes ; ils peuvent permettre un écart minimal plus bas. Même banc, mêmes graines, même règle, même plafond de 2 finalistes par module (tours 1 et 2 réunis, classés par rappel moyen puis FA).
- VS7 : NDVI et NDRE lissés par le noyau « tente » 3 × 3 (empreinte 20 m), écart NDRE 0,03.
- VS8 : lissage 3 × 3 + écart NDRE 0,04.
- SS7 : SS2 (NDVI 20 m) + écart 0,02.
- SS8 : SS1 (droite par parcelle) + écart 0,02.
- SS9 : SS1 + SS2 + écart 0,02.
- DS6 : VARI, lissage 5 m (écart 0,0356, déjà calibré).
- DS7 : ExG, z −1,5.
- Information seulement (pas un essai, hors décision) : `TS1u`, `TS2u` = zones de TS1/TS2 **réunies** aux parcelles en alerte, pour chiffrer l'effet de la définition de la zone d'alerte du temporel.
Calcul du tour 2 à 14 h 12 (≈ 40 s). Résultats : `reglage/resume_*_tour2.csv`. Référence identique au tour 1 (contrôlé par `t15_decider.py`).

## 14 h 13 : décision finale (tours 1 et 2 réunis, 28 essais)

| Module | Essais | Passent la règle | Finalistes |
| --- | --- | --- | --- |
| Vigueur S2 | 8 (VS1 à VS8) | aucun : VS7 gagne +0,13 mais FA 1,76 ha (réf. 0,37) ; VS8 +0,01 seulement | — |
| Stress | 9 (SS1 à SS9) | aucun : SS7 à SS9 gagnent +0,18 environ mais FA 0,62 à 0,75 ha (réf. 0,05) | — |
| Temporel | 4 (TS1 à TS4) | TS1 à TS4 | **TS2**, **TS1** |
| Drone | 7 (DS1 à DS7) | DS1 (DS6 et DS7 : FA trop hautes) | **DS1** |

Informations (pas des essais) : TS2u et TS1u (zones réunies aux parcelles en alerte) donnent 6,83 et 6,97 ha de FA sans injection, au-dessus de la référence (5,44) : le passage de TS1 et TS2 tient à la définition écrite à 14 h 03 (zones seules).

## 14 h 13 : correctifs et juge

- Correctifs non appliqués dans `out/teledetection/jour_1511/correctifs/` : `temporel.diff`, `vigueur.diff`, `config.diff`, et les fichiers complets `*_propose.py`. Le temporel proposé est **désactivé par défaut** (`temporel.zones_temporel` absent = module d'avant).
- `scripts/t15_verif_correctifs.py` : chargés depuis leur fichier, les correctifs redonnent au pixel près les alertes de TS2, TS1 (paire intacte et 2 tirages) et DS1 (scène intacte et 1 tirage), sur le réglage.
- Juge : `scripts/t15_juge.py --je-suis-le-juge`. Il lit les finalistes dans `reglage/decision_*.csv`, mesure la Côte d'Ivoire (temporel) et la moitié drone de mesure, avec graines + 50 000, et pose un verrou par module. L'écart minimal de VARI est repris du réglage. Chemin du juge testé sur le réglage seulement (drone, 1 tirage, sortie dans le dossier temporaire de la session) ; les gardes `T15_MESURE_AUTORISEE` bloquent toute lecture de la mesure hors du juge.
- `out/teledetection/jour_1511/finalistes.md` écrit à 14 h 15.

## Compte final des essais : 28 (vigueur S2 8, stress 9, temporel 4, drone 7), plus 4 contrôles et 2 lignes d'information.

## 14 h 18 : contrôle de la session principale, tour 3 du temporel, écrit avant calcul

Contrôle (`out/controle_jour_1511/admissions.md`) : DS1 admis ; **TS2 et TS1 refusés**. Le plan compte comme fausse alerte toute la surface en alerte, et mon correctif gardait les alertes de parcelle à côté des zones : la comparaison valable était TS2u / TS1u (6,83 et 6,97 ha contre 5,44 ha). Ma règle de 14 h 03 (zones seules alors que le correctif gardait les parcelles) contredisait le plan ; le plan prime. Je l'accepte.

Tour 3 : variantes **cohérentes avec le correctif qui serait installé**. La surface comptée est toute la surface en alerte que ce correctif émettrait : zones ∪ parcelles en alerte. La règle reste celle du plan (rappel ≥ réf. + 0,05 ; perte ≤ 0,02 par gravité ; surface en alerte sans injection ≤ 5,436 ha). Au plus 2 finalistes temporel, classés comme avant. TS1 à TS4 ne sont plus admissibles ; seules les variantes TT ci-dessous concourent.

**4 essais (total 32) :**
- TT1 : zones TS2 (delta comparé à sa parcelle) **seules** ; plus aucune alerte de parcelle émise par le module.
- TT2 : zones TS1 (delta comparé au site) **seules** ; plus aucune alerte de parcelle.
- TT3 : zones TS1, et une alerte de parcelle (la parcelle entière entre dans la surface d'alerte) seulement si la règle de parcelle du service la déclenche **et** que les zones couvrent au moins **x = 25 %** des pixels de la parcelle.
- TT4 : même chose avec **x = 50 %**.
- Grille de x : {25 %, 50 %}, rien d'autre. Zones TS1 pour TT3 et TT4, parce que des zones relatives à la parcelle (TS2) ne peuvent presque jamais couvrir la moitié de leur propre parcelle.
- Alerte de parcelle mesurée : TT1 et TT2 = aucune (0 par construction) ; TT3 et TT4 = parcelles retenues.
- Si une variante passe : mise à jour de `finalistes.md`, `decision_temporel.csv` et du correctif, conforme à la variante. Sinon : « aucun finaliste temporel », et les fichiers sont marqués comme tels.
- Transparence : la surface d'alerte de TT1 et TT2 est par construction celle de TS2 et TS1. Leurs chiffres sont donc prévisibles d'après le tour 1, déjà lu. Ce qui change, c'est le module installé (sans alertes de parcelle), plus la perte d'information qui va avec. TT3 et TT4 sont nouveaux.

## 14 h 18 : tour 3, résultats et décision (4 essais, total 32)

Calcul : `t15_banc_s2.py --module temporel --variantes TT1,TT2,TT3,TT4 --tour 3` (5 s). Résultats : `reglage/resume_temporel_tour3.csv`. Référence identique.

| Variante | Rappel faible / moyenne / forte | Moyen | Surface en alerte sans injection | Décision |
| --- | --- | --- | --- | --- |
| Référence | 0,075 / 0,125 / 0,075 | 0,092 | 5,436 ha | — |
| TT1 | 0,450 / 0,925 / 1,000 | 0,792 | 1,736 ha | **finaliste 1** |
| TT2 | 0,350 / 0,950 / 1,000 | 0,767 | 2,299 ha | **finaliste 2** |
| TT3 (x = 25 %) | = TT2 | 0,767 | 2,299 ha | passe, ex æquo, non retenu |
| TT4 (x = 50 %) | = TT2 | 0,767 | 2,299 ha | passe, ex æquo, non retenu |

- TT3 et TT4 = TT2 : aucune parcelle en alerte de service n'a 25 % ou plus de sa surface en zones TS1, sur aucun tirage.
- Égalité exacte entre TT2, TT3 et TT4 : la règle écrite ne départage pas. Je retiens TT2 par l'ordre d'écriture des essais (tri stable dans `t15_decider.py`). Ce départage **n'avait pas été écrit avant** : je le signale.
- Constat hors règle [M, paire intacte de l'Équateur] : parcelles qui recevraient au moins une alerte temporelle dans le bulletin. Référence 1 sur 13 (P06), TT1 10 sur 13 (zones de 5 à 49 pixels), TT2 6 sur 13. Moins de surface en alerte, mais plus de parcelles pénalisées dans le score.
- Mis à jour : `reglage/decision_temporel.csv` (TS1 à TS4 marqués non admissibles ; TT1 et TT2 finalistes), `finalistes.md`, `rapport.md`.
- Correctif : `correctifs/temporel_propose.py` et `temporel.diff`. Avec `temporel.zones_temporel` réglé, les zones **remplacent** les alertes de parcelle (`parcelle` = TT1, `site` = TT2) ; sans ce réglage, le module reste celui d'avant. `config.diff` est mis à jour.
- Contrôle : `t15_verif_correctifs.py` compare **toute** la surface émise par le correctif (zones et parcelles éventuelles) à celle du banc : 0 pixel de différence pour TT1 et TT2 (paire intacte et 2 tirages), et pour DS1.

## Compte final des essais : 32 (vigueur S2 8, stress 9, temporel 4 + 4 au tour 3, drone 7), plus 4 contrôles et 2 lignes d'information. Finalistes : TT1, TT2 (temporel), DS1 (drone, admis).
