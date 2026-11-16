# Avenant c16 (3) : installation de l'aiguillage du comptage v5 / c16_a (16/11, vers 11 h 30)

Accord de Corentin : « super installe ça » (transmis par la session principale), pour l'aiguillage v5 / c16_a. Cet accord vaut pour modifier `fieldscan/modules/comptage.py` et `config.yaml`, et `fieldscan/drone.py` seulement si R1 l'exige. Cet avenant est écrit **avant toute mesure de l'installation**. Son empreinte SHA-256 est dans `empreinte_avenant_c16_installation.txt`. Aucun commit, aucun juge ni test lu.

Rappels : avenant c16 (règles et finalistes), avenant c16 (2) (juges à 11 cm : F1 moyen 0,519 contre 0,457 pour le v5 dégradé, adoption proposée), `out/comptage/jour_1611/finalistes.md`, `juges_c16_a.md`, `note_integration.md`.

## R1. Contrôle du rééchantillonnage réel (réglage seulement)
- **Source réellement basse résolution** : chaque image des 5 jeux de réglage (dense, plantain, jeunes, MM, btd_val ; jamais les juges, lecture gardée par `cc.jeu` de `scripts/c13_banc_commun.py`) est réduite de 5 à 11 cm/px (LANCZOS, taille `round(w × 5 / 11)`, comme la première étape de `degrader`), puis enregistrée en JPEG qualité 95 et relue. Elle est écrite dans un **GeoTIFF temporaire** hors dépôt (`C:/Users/coren/kaggle_tmp/c16/installation/`), 3 bandes uint8, EPSG:32717, pixel de 0,11 m.
- **Relecture par le vrai chemin de la chaîne** : `fieldscan.drone.lire_fenetre(chemin, "EPSG:32717", emprise de l'image d'origine à 5 cm, 0,05)`, c'est-à-dire `WarpedVRT` avec `Resampling.average`, sans modification.
- **Mesure** : c16_a au seuil 0,35, carte et pics du banc (`bc.cartes_image`, `bc.pics`) sur l'image relue, mesure `bc.mesurer_jeu` sur les 5 jeux. Seul le chemin de l'image change par rapport à la mesure simulée (moyenne des 5 F1 = **0,8614**).
- **Critère** : moyenne des 5 F1 ≥ 0,8614 − 0,020 = **0,8414** → on garde la lecture actuelle (`Resampling.average`), `drone.py` n'est pas touché.
- **Sinon** : même mesure avec `Resampling.bilinear` (copie locale de `lire_fenetre` qui ne change que ce paramètre), **pour la branche spécialiste seulement** (le v5 ne change pas). Retenu si la moyenne ≥ 0,8414 ; il faudrait alors ajouter à `drone.lire_fenetre` un paramètre de rééchantillonnage (défaut `average`). Sinon : **pas d'installation**, et le rapport le dit.
- Pour information (ne décide rien) : le v5 au seuil 0,30 par le même chemin.

## R2. Fourchette de c16_a (règle de la section 7 bis du protocole v5)
- Rapports **réels / détectés** de c16_a au seuil 0,35, **avec le détecteur de la chaîne** (`fieldscan.drone.DetecteurCentres`, fenêtres de 1 024 px, marge 128), comme `scripts/mesurer_fourchette_v3.py`, sur les 4 validations du v5 :
  - banavista session B (`val_dense_bv`, plants et détections dans le disque de 2 000 px) ;
  - `plantas_platano` 100_metros (`val_plantain`, tuiles entières) ;
  - jeunes bananiers dji_0544 (`val_jeunes`, disque) ;
  - MM1-MM2, mères seules, détections dans le carré.
- Images passées par **le chemin retenu en R1** (source réduite + JPEG, GeoTIFF, `lire_fenetre`), à **8, 11 et 14 cm/px**.
- `coefficient_bas` = le plus petit des 12 rapports, `coefficient_haut` = le plus grand, arrondis à 0,01 comme pour le v5. Jamais le test.

## R3. Non-régression de la chaîne (après installation)
- **≤ 7,5 cm/px** : `run.py --modules comptage` sur El Oro (6,4 cm/px, `data/drone/reforestree/wwf_ecuador/RGB Orthomosaics/El Oro OAM RGB.tif`, seule dans un dossier temporaire hors dépôt), parcelles `out/demo_eloro/parcelles_auto.geojson`, sortie hors dépôt. Comparé à `out/demo_eloro/chaine/pieds.geojson` du 15/11 : **exactement les mêmes pieds** (1 105 ; mêmes parcelles, mêmes positions, mêmes scores). Le journal doit dire v5, 0,30, résolution d'origine 6,4 cm.
- **> 7,5 cm/px** : une copie d'El Oro réduite à 11 cm/px (GeoTIFF temporaire hors dépôt, `Resampling.average` par GDAL, même géoréférence) passe par `run.py --modules comptage` ; le journal doit dire **c16_a, seuil 0,35**, résolution d'origine 11 cm, empreinte du modèle et coefficients de R2. Pas de critère chiffré sur le nombre de pieds (aucune référence) : le compte est donné pour information.
- Sans le bloc `aiguillage_resolution` dans la configuration, le code doit garder le comportement d'aujourd'hui (contrôlé par lecture du code, et par R3-a qui passe par la branche v5).

## Cadre
- 2 fils de processeur pour moi (l'agent du trailer Blender en a 4) : onnxruntime à 2 fils dans mes scripts, et **affinité du processus à 2 cœurs** pour `run.py` (dont le détecteur ne fixe pas le nombre de fils).
- Écrit dans : `config.yaml`, `fieldscan/modules/comptage.py`, `README.md` (ligne du comptage), `modeles/centres_5cm_c16_a.onnx` et `.json` (copies), `scripts/c16_*.py`, `out/comptage/jour_1611/`, `docs/journee_2026-11-16/`, et le dossier temporaire hors dépôt.
