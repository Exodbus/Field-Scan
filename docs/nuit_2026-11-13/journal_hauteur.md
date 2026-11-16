# Journal de l'agent Hauteur (14/11/2026, soir)

Protocole appliqué à la lettre : `docs/protocole_hauteur_banavista.md`.
Règles : rien à télécharger, aucun commit, aucune photo de validation du v5, aucun juge, aucun test.
Écriture seulement dans `out/hauteur/`, `scripts/hauteur_*.py` et ce journal.

## 19 h 41 : empreinte du protocole au début

SHA-256 de `docs/protocole_hauteur_banavista.md` : `6ad53cb4138944ec743acc670219f2bc47e4d3d2dea356b459eb90542fe0f2cc`, identique à `docs/protocole_hauteur_banavista.sha256`.

## 19 h 44 : choix de la ligne (règle du protocole, section 2, avant tout calcul)

Source de la liste : `data/drone/decoupage_comptage_v5/decoupage.csv` (découpage v5), groupe `bv_session_a`, partie `train` : 123 photos, DJI_0542 à DJI_0682 avec des trous.
Les noms `train/`, `valid/`, `test/` de Roboflow sont ignorés ; seule la colonne `partie` du découpage v5 compte.

Suites de numéros consécutifs de la session A :

| Suite | Photos |
| --- | --- |
| **DJI_0564 à DJI_0661** | **98** |
| DJI_0542 à DJI_0557 | 16 |
| DJI_0677 à DJI_0682 | 6 |
| DJI_0666 à DJI_0668 | 3 |

**Ligne retenue : DJI_0564 à DJI_0661, 98 photos**, toutes en `train` dans le v5.
- Première moitié (réglage) : DJI_0564 à DJI_0612 (49 photos).
- Seconde moitié (mesure) : DJI_0613 à DJI_0661 (49 photos).

[H] Une suite de 98 numéros contient sans doute plusieurs bandes de vol. Le protocole parle d'« une seule ligne de vol » mais fixe la règle par la suite consécutive : j'applique la règle telle quelle.

## 19 h 47 : réglages ODM écrits avant le premier lancement

- Version : ODM 3.6.2 (`C:\ODM\VERSION`).
- Chemin du projet : le chemin du dépôt contient des espaces ; j'utilise son nom court Windows (8.3) `C:\00_DATA\02-COU~1\ING4\06-INT~1\PROJET~1\FIELD-~2\out\hauteur\odm`, qui désigne le même dossier `out/hauteur/odm`. Projet `ligne_a`, photos dans `ligne_a/images/`.
- La variable d'environnement `NoDefaultCurrentDirectoryInExePath=1` empêche `run.bat` de trouver `winrun.bat` : je la retire pour le seul processus ODM (aucun changement de configuration de la machine).
- **Mise en correspondance (photos sans GPS)** : réglages par défaut d'ODM sans GPS, sans option ajoutée.
  - ODM passe de lui-même au « sac de mots » (BOW) avec les points HAHOG quand il n'y a pas de GPS (`opendm/osfm.py`, lignes 286 à 294).
  - `matching_gps_neighbors 0` : sans GPS, toutes les paires sont candidates (98 photos, 4 753 paires). Cela garde les recouvrements latéraux entre bandes, que `--matcher-order` (voisins dans l'ordre des noms) perdrait.
  - Pas de `--matcher-order`, pas de `--matcher-neighbors`, caméra en `auto` (pas de métadonnées : focale estimée par OpenSfM).
- Options : `--dsm` (demandé par le protocole) ; `--max-concurrency 2` (Juges actifs jusqu'à 21 h environ). Pas de `--dtm` : sous couronnes jointives le sol est presque invisible et les sommets se lisent sur le MNS seul.
- **Échelle** : sans GPS, la reconstruction est dans un repère arbitraire, et ODM ne peut pas estimer la taille d'un pixel au sol (il garde alors les 5 « cm » demandés, dans l'unité arbitraire). Je procède en deux temps :
  1. lancement 1 jusqu'à OpenSfM (`--end-with opensfm`) : poses et nuage clairsemé, ce qui suffit pour le premier critère (photos placées) ;
  2. calcul de l'échelle à partir de `reconstruction.json` (hauteur des caméras au-dessus du nuage et focale estimée : taille d'un pixel au sol dans l'unité arbitraire, ramenée à 1,1 cm/px, valeur du v5) ;
  3. lancement 2 (`--rerun-from openmvs`) avec `--dem-resolution` et `--orthophoto-resolution` exprimées dans l'unité de la reconstruction pour viser **2,5 cm au sol pour le MNS** et **2,5 cm pour l'orthophoto** (l'orthophoto est ensuite ramenée à 5 cm pour le v5). Si l'échelle trouvée rend les valeurs par défaut (5 unités) raisonnables, je les garde.
  Ces deux résolutions sont **le réglage n° 1** hors défauts (le découpage en deux temps n'est qu'un arrêt et une reprise).

Essais ODM comptés : 0 pour l'instant.

## 19 h 48 : extraction (`scripts/hauteur_preparer.py`)

98 photos extraites dans `out/hauteur/odm/ligne_a/images/` (4 000 × 3 000, 0 champ EXIF, 98 MD5 distincts). Boîtes : 7 800 `Bananas`, 283 `Others` (`out/hauteur/boites_ligne_a.csv`). Liste et moitiés : `out/hauteur/ligne_a.json`.

## 19 h 49 : lancement ODM n° 1 (essai 1)

`run.bat --project-path <nom court>\out\hauteur\odm ligne_a --dsm --max-concurrency 2 --end-with opensfm`. Journal : `out/hauteur/odm_lancement1.log`.

## 19 h 52 : règles de la phase 2, écrites avant tout calcul (OpenSfM tourne encore, aucun résultat vu)

**Repère et échelle.** Repère de la reconstruction OpenSfM (`opensfm/reconstruction.json`, axe z vers le haut par `align_orientation_prior: vertical`). Facteur d'échelle k (m par unité) : taille d'un pixel au sol en unités = médiane, sur les photos placées, de (hauteur de la caméra au-dessus de la médiane des points clairsemés à moins de 9 voisins, comme ODM) / (focale × 4 000) ; k = 0,011 / cette taille (1,1 cm/px, valeur retenue pour banavista dans le v5). Les hauteurs du MNS sont multipliées par k.

**Grille commune.** Une grille à 5 cm dans le plan (x, y) du repère, alignée sur l'orthophoto d'ODM ramenée à 5 cm (coins de `odm_orthophoto_corners.txt`). Le MNS est rééchantillonné sur cette grille.

**Référence (projection des boîtes).**
- Boîtes `Bananas` seulement (`Others` n'est pas une cible, comme au v5), centre de boîte seulement s'il est dans le disque de 2 000 px autour du centre de la photo (règle du v5).
- Rayon de la caméra (modèle et distorsion de la caméra estimés par OpenSfM) coupé avec le MNS : départ à la médiane du MNS, puis 10 itérations (x, y) ← rayon à la hauteur z, z ← MNS lissé (gaussienne de 0,5 m) en (x, y).
- **Règle de fusion** : photos prises dans l'ordre DJI ; chaque boîte d'une photo est appariée, un pour un (algorithme hongrois), aux plants déjà formés dont le centre est à 1,0 m au plus et qui n'ont pas encore de boîte de cette photo ; sinon elle crée un nouveau plant. Position du plant = moyenne de ses boîtes projetées, recalculée après chaque photo.
- **Couronne jointive** : le plant est « jointif » si, sur la photo où sa boîte est la plus proche du centre de l'image, cette boîte a une intersection d'aire non nulle avec une autre boîte `Bananas` de la même photo.

**Moitiés et zone de mesure.** Chaque point du plan est attribué à la photo dont le centre de prise de vue (projeté sur le plan) est le plus proche. Zone de réglage = points attribués aux photos DJI_0564 à 0612 ; zone de mesure = points attribués aux photos DJI_0613 à 0661. Dans les deux cas, on ne garde que les points situés dans le disque de 2 000 px de leur photo (projeté) et là où l'orthophoto et le MNS sont valides. Plants de référence et détections sont comptés s'ils tombent dans la zone.

**Méthode hauteur.** MNS en mètres, sur la grille à 5 cm, lissé par une gaussienne de σ = 0,3 m (fixé, non réglé). Sommet = pixel égal au maximum du MNS lissé dans un disque de rayon d, et plus haut d'au moins 0,5 m que le minimum du MNS lissé dans un disque de 2 m (fixé, non réglé : écarte les maxima du sol dans les trous). **Seul d est réglé**, sur la zone de réglage, dans la grille 0,8 ; 1,0 ; 1,2 ; 1,4 ; 1,6 ; 1,8 ; 2,0 ; 2,2 ; 2,5 m ; choix = F1 total maximal sur la zone de réglage (égalité : le plus grand d). Puis une seule mesure sur la zone de mesure.

**Point de comparaison.** v5 (`modeles/centres_5cm_v5.onnx`, détecteur de la chaîne `fieldscan.drone.DetecteurCentres`, seuil 0,30 du `.json`) sur l'orthophoto d'ODM ramenée à 5 cm/px (k appliqué), pixels hors orthophoto marqués non valides.

**Fusion simple v5 + sommets (écrite avant)** : détections v5, plus les sommets situés à plus de d (le d choisi) de toute détection v5. Mesurée une fois sur la zone de mesure, avec le même d, sans réglage propre.

**Appariement.** Celui du v5 : algorithme hongrois, rayon 1 m (20 px à 5 cm). P, R, F1 sur tous les plants ; **rappel « jointives »** = plants jointifs appariés / plants jointifs.

**Critère (protocole, section 5)** : prometteur si, sur la zone de mesure, rappel jointives (hauteur ou fusion) ≥ rappel jointives du v5 + 0,03 **et** F1 total (même méthode) ≥ F1 total du v5 − 0,01.

**Contrôles notés pour information (ne décident rien)** : dispersion des boîtes d'un même plant (écart médian au centre), distance médiane plant → détection v5 la plus proche.

**Compte des essais de la phase 2** : 1 balayage de d sur la zone de réglage (9 valeurs), puis 1 mesure (hauteur, v5, fusion) sur la zone de mesure.

## 20 h 01 : constat sur la ligne, avant tout résultat d'OpenSfM

[O] Planche des 98 photos (vignettes, contrôle visuel des photos d'entraînement) et nombre de boîtes par photo (`out/hauteur/boites_ligne_a.csv`) : la suite DJI_0564 à 0661 **mélange deux scènes**, en alternance :
- plantation dense à couronnes jointives (environ 50 photos, 100 à 190 boîtes chacune, boîtes médianes 200 à 300 px) ;
- pépinière de jeunes plants en pots, en rangs sur sol nu (environ 48 photos, 5 à 45 boîtes, boîtes médianes 300 à 400 px, donc sans doute prises plus bas).
Les deux s'entrelacent même d'une photo à l'autre (0612 plantation, 0613 pépinière, 0614-0615 plantation, 0616-0617 pépinière).
[H] Deux vols ou deux cartes mémoire à numérotation entremêlée. La reconstruction risque de se scinder en deux blocs.

Lecture du critère 1, fixée avant de voir le résultat : on compte les photos placées dans la reconstruction qui sert au MNS (la première de `reconstruction.json`, la plus grande). Les photos placées dans une reconstruction secondaire sont rapportées à part mais ne comptent pas, car ODM n'en tire pas de MNS. Je n'ajoute aucun réglage pour forcer la fusion des deux scènes, et je ne change pas la ligne : la règle du protocole est appliquée telle quelle.

## 20 h 33 : avancement

Extraction des points terminée vers 20 h 02 (HAHOG, photos ramenées à 2 000 px). Mise en correspondance de toutes les paires (4 753) avec 2 fils : 1 609 paires faites en 30 min, dont 405 réussies. Fin prévue vers 21 h 30.

## 21 h 08 : consigne du coordinateur

Les Juges ont fini : 4 fils au plus (`--max-concurrency 4`) à partir de la prochaine étape d'ODM. Le lancement n° 1 (jusqu'à OpenSfM) n'est pas interrompu, pour ne pas perdre la mise en correspondance (environ 4 100 paires sur 4 753 faites). Le lancement n° 2 (MNS et orthophoto) se fera avec `--max-concurrency 4`.

## 21 h 21 : fin du lancement ODM n° 1 (essai 1), critère 1 de la phase 1

Durée : 19 h 49 à 21 h 21, soit 92 min avec 2 fils (extraction des points environ 3 min, mise en correspondance 67 min pour 4 753 paires, reconstruction environ 7 min).
Mesure : `scripts/hauteur_phase1.py --etape sfm`, puis `out/hauteur/phase1_sfm.json`.

[M] OpenSfM donne **3 reconstructions séparées** :

| Reconstruction | Photos | Points clairsemés | Contenu (d'après le nombre de boîtes et la planche) |
| --- | --- | --- | --- |
| 0 (la plus grande, celle dont ODM tire le MNS) | 58 | 65 825 | les 58 photos de la pépinière en pots, toutes placées |
| 1 | 31 | 12 245 | plantation dense (31 des 40 photos) |
| 2 | 4 | 868 | plantation dense (DJI_0567, 0568, 0569, 0571) |
| non placées | 5 | — | plantation dense (DJI_0564, 0565, 0574, 0633, 0635) |

**Critère 1 : 58 / 98 = 59 % de photos placées dans la reconstruction qui sert au MNS, sous le seuil de 80 %. Échec.**
- Même en comptant toutes les reconstructions, ce ne serait pas un bloc : les deux scènes n'ont aucun lien entre elles.
- Pour information, la plantation dense seule (la scène qui intéresse la question) : 31 / 40 = 78 % dans sa plus grande reconstruction, sous 80 % elle aussi.

**Conformément au protocole (section 4), l'essai s'arrête ici.** Le MNS n'est pas calculé, donc le critère 2 (couverture) n'est pas évalué, et la phase 2 n'est pas lancée. Le lancement n° 2 prévu (MNS, orthophoto, réglage n° 1 des résolutions) n'a pas lieu.
- Échelle trouvée pour information (reconstruction 0) : k = 36,8 m par unité ; les 5 « cm » par défaut d'ODM auraient donné 1,8 m au sol par pixel. Le réglage n° 1 (0,068 « cm » pour 2,5 cm au sol) était donc nécessaire.

## 21 h 22 : contrôle visuel pour information (`scripts/hauteur_controle_nuage.py`)

Sans MNS ni orthophoto, la planche `out/hauteur/controle_nuage_clairseme.png` montre le nuage clairsemé de dessus, coloré par la hauteur relative :
- [O] pépinière (reconstruction 0) : les pots ressortent en taches plus hautes, alignées sur les rangs ; un dévers d'environ 4 à 6 m d'un bord à l'autre du site (sur environ 100 m) se voit dans la couleur de fond. [H] Basculement résiduel du repère sans GPS, ou vraie pente.
- [O] plantation dense (reconstruction 1) : nuage 5 fois moins dense pour une emprise semblable (canopée répétitive, appariement difficile) ; écart d'environ 5 à 6 m entre les zones, du même ordre que la hauteur d'un bananier. [H] Sans GPS, un dévers ou une cuvette de cette taille devrait être retiré avant de lire des sommets.

Essais comptés : 1 lancement ODM (réglages par défaut, `--dsm`, 2 fils, arrêt après OpenSfM). Aucun réglage hors défauts essayé. Phase 2 : 0 essai.

## 21 h 22 : empreinte du protocole à la fin

SHA-256 de `docs/protocole_hauteur_banavista.md` : `6ad53cb4138944ec743acc670219f2bc47e4d3d2dea356b459eb90542fe0f2cc`, inchangé.
