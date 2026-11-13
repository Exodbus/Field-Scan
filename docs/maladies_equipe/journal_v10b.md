# Journal : intégration de la v10b du binôme (11 novembre 2026)

Rien n'est commité. L'empreinte SHA-256 du protocole est notée ici avant chaque mesure.

| Heure | Événement |
| --- | --- |
| 11:5x | Protocole `docs/protocole_maladies_v10b.md` (sections 0 à 5) écrit avant d'avoir les poids ; SHA-256 29f63dc3481614fa3a0908032a342cec07d2f71a3a4082f45328641f07b295f7 |
| 12:2x | Fichiers du binôme reçus ; contrôle d'intégration réussi (40 / 40, écart 7,2e-7) ; recouvrements par SHA-256 ; amendement 1 écrit avant toute prédiction de la v10b sur nos jeux ; SHA-256 aebb8e4f8b94bc36dbf4662fad1616cb069f68fef2f953efc95878e72d739c63 |
| 12:28 | Prédictions de la v10b lancées sur le processeur local (`scripts/predire_v10b.py`), environ 4 h prévues. |
| 12:45 | Calcul local arrêté avant tout fichier écrit. Remplacé, à la demande de Corentin, par le carnet Kaggle `affilecorentin/predire-v10b` (T4, 32 bits, même préparation que la chaîne), avec le jeu privé `maladies-v10b-poids` (poids, `seuils.json`, liste des 8 066 photos). Soupe, v2 et aiguilleur sur la Cordana du Pérou : calculés en local. |
| 13:10 | Carnet Kaggle fini (22 min de calcul). Contrôle : 20 photos refaites en local, écart maximal 6,3e-7. Avant la mesure unique : SHA-256 du protocole aebb8e4f8b94bc36dbf4662fad1616cb069f68fef2f953efc95878e72d739c63 (inchangé depuis l'amendement 1). |
| 13:15 | Mesure unique : G1 rempli (9 / 2 001 ; limite 19). v10b installée (`config.yaml`, température 0,79). Chaîne complète sur `data/demo_feuilles` : réussie. Résultats en section 7 du protocole. |
| 14:26 | Protocole v10c (BanSpot, fermes libres) écrit avant le téléchargement de BanSpot ; SHA-256 463cff79435675b23a1b1105ff636685ad07ab87c433d7a86d8ac5cdc562a686 |
| 14:49 | BanSpot ouvert : 1 300 photos, 2 fermes seulement (pas de ferme libre). Aucun entraînement (protocole v10c, section 5). |
| 14:56 | Section 6 (test BanSpot de la chaîne installée) écrite avant tout calcul ; SHA-256 02fe2f73719cd35b9d30a04a8ee3b9f5ba442d391669d488a22c11c8fdf0a7dc |
| 16:15 | Test BanSpot, mesure unique (`scripts/mesurer_banspot.py`), protocole inchangé (SHA-256 02fe2f73…). Chaîne installée : 6 / 646 tachées sans alerte, 61 / 646 saines en alerte (26 « à vérifier ») ; ancienne chaîne : 30 / 646 et 19 / 646. Aucune décision. Résultats dans le protocole v10c, section 6. |
