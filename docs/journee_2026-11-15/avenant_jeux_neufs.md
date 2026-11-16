# Avenant : trois jeux neufs, rôle et découpage écrits avant téléchargement (15/11, vers 19 h 30)

Corentin a accepté le « minimum recommandé » de la prospection (`out/prospection_jour_1511/candidats.md`, section 4.1) avec ces mots : « Oui, le minimum ». Cet avenant est écrit **avant tout téléchargement**. Son empreinte SHA-256 est dans `empreinte_avenant_jeux_neufs.txt`.

## Règles communes
- Chaque jeu va dans son propre dossier sous `data/raw/`. Il n'est jamais exécuté. Python le lit en mode `-I`.
- **Contrôle de fuite avant toute lecture par un modèle**. Le contrôle compare SHA-256, noms d'origine et dHash (distance ≤ 6 sur 64 bits) avec :
  - `data/raw/*`, `data/feuilles*`, `data/roboflow*`, `data/test_*` ;
  - la liste d'apprentissage de la v10b (`liste_apprentissage_v10.csv`) ;
  - l'index `out/prospection_nuit_1311/index_noms_locaux.json`.

  Toute image en double avec un jeu vu par F1 ou par le v5 est retirée du rôle « test » ou « réglage ».
- Le rapport de contrôle va dans `out/jeux_neufs_1511/controle_fuite.md`.
- Le rôle ci-dessous ne change plus une fois le premier modèle lancé.

## A1. PlantVillage / Penn State, `bxw-leaf.zip` + `banana_annotations_all.zip` (+ README)
- **Licence et provenance** : CC BY-NC-SA 4.0. Téléchargé **à la main par Corentin** (contrôle anti-robot), dans `data/raw/plantvillage_psu/`.
- **Rôle** : deux moitiés disjointes.
  - **A1-test** : un test vierge de rappel sur le Xanthomonas. Mesure : la part de feuilles malades **sans alerte**, pour F1 (installé en F1_bornes) et pour tout futur candidat. Il est lu **une seule fois** pour F1, puis une fois par candidat proposé à l'adoption. Il ne contient que des malades : il ne mesure pas les fausses alertes, et le rapport le dira.
  - **A1-appr** : Xanthomonas d'une seconde source pour l'entraînement (validation croisée « Éthiopie contre PlantVillage »).
- **Découpage, fixé maintenant** : par lot.
  - Le lot est le champ « ferme », « lieu » ou « date » des annotations s'il existe : on prend le premier des trois qui existe. Lots triés par nom, un sur deux : impairs → A1-test, pairs → A1-appr.
  - Sans aucun de ces champs : blocs de 50 noms de fichiers consécutifs (tri alphabétique), un bloc sur deux, en commençant par A1-test.
  - Les doublons trouvés par le contrôle de fuite sortent d'A1-test.
- `hl-leaf.zip` (saines) n'est pas téléchargé pour l'instant.

## A2. Plantain du Ghana (`m2-eewev/plantain-detection`, vol `20230131_WN_ADABOKROM_1_Flight_04`)
- **Licence et méthode** : CC BY 4.0. Il s'agit des 199 photos d'origine publiques (`original.jpg`), environ 4 Go, téléchargées par un script en lecture seule dans `data/raw/plantain_ghana_m2/`. Les boîtes viennent de l'export déjà présent (`plantain_m2.zip`), remises à l'échelle des originaux, ou de l'API image publique.
- **Rôle** : **réglage « agroforesterie »** du comptage, l'équivalent ouvert de CG. Il n'est jamais utilisé en apprentissage, ni en juge, ni en test.
- **Mesure** :
  - F1 des pieds, à 5 cm/px, avec le banc du v5 (appariement un à un, rayon du protocole v5) ;
  - centre de boîte = position du pied ;
  - échelle de réduction fixée **une fois**, avant toute détection : elle ramène la médiane de la plus petite distance entre boîtes voisines à 2,5 m (écartement typique), avec un facteur arrondi à 0,1. Le calcul et le facteur sont notés avant la première détection.
- **Découpage** : un seul rôle, donc aucun partage. Les photos se recouvrent : chaque photo est mesurée seule, et le rapport le dit.
- **Usage dans les règles futures** : une condition de non-régression sur A2 (F1 ≥ v5 − 0,02) pourra être ajoutée aux règles de comptage. Elle ne s'appliquera qu'aux candidats **écrits après** la mesure du v5 sur A2.

## B3. Stress hydrique en Colombie (Beltrán 2026, Mendeley `t9b2bf53jj`, `wmb385343f`, `wyhw7zyxmm`)
- **Licence et emplacement** : CC BY 4.0, 4,7 Mo, dans `data/raw/colombie_stress_beltran/`.
- **Rôle** : **calibration**. Ce jeu sert à mesurer la baisse réelle du NDVI et du NDRE par plant sous 30, 50 et 75 % de l'ETc, comparée à 100 %. Cet ordre de grandeur réglera l'amplitude des anomalies injectées du banc de télédétection.
- Ce n'est pas un test d'images, et il ne décide d'aucune adoption.
