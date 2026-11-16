# Récapitulatif : nuit du 13 au 14 novembre 2026 (reprise le 14/11)

Écrit le 14/11 vers 21 h 15 par la session principale. Chaque chiffre a été relu dans les fichiers des agents. Détail heure par heure : `docs/nuit_2026-11-13/tableau_de_bord.md`.

## 1. En bref

- **Maladies.** Le seul finaliste qui passe les juges est **F1_bornes** : les mêmes alertes que F1, en environ deux fois moins de calcul. Son adoption est proposée. Elle demande de modifier `fieldscan/`, donc l'accord de Corentin. d3b échoue sur BanSpot, et sa recette n'est pas stable d'une graine à l'autre.
- **Comptage.** `E5p90b_c13e_d-0.1` passe les juges relus, mais fait **moins bien que le v5 sur le test vierge** `banana_trees_kp`. Corentin a décidé de **garder le v5** (« Oui, garde le v5 »). `config.yaml` est inchangé.
- **Le vrai point faible du comptage est la basse résolution.** Sur le test vierge (environ 11 cm/px), les deux modèles tombent à un F1 de 0,11-0,13. La piste 2 la plus prometteuse vise exactement ce point : un mélange v5 + c13h, à 0,857 à 11 cm sur le réglage contre 0,601 pour le v5.
- **Rien n'est commité.** Deux logiciels ont été téléchargés avec l'accord de Corentin (OpenDroneMap et Blender). Aucune donnée nouvelle n'a été téléchargée.

## 2. Déroulé

| Heure | Événement |
| --- | --- |
| 13/11, 23 h 30 | Corentin relance les agents : comptage et maladies, processeur local + Kaggle, sans téléchargement de données |
| 14/11, ≈ 1 h 05 | Coupure de la session. Tous les agents s'arrêtent ; rien n'est gelé, aucun juge n'est lu |
| 13 h 10 | Reprise. Avenant d'horaires (`avenant_horaires.md`) : gel à 19 h, juges de 19 h à 20 h 30, récapitulatif à 21 h |
| 13 h 47 à 17 h 56 | Fin de C-banc, M-banc, C-entraîneur et M-entraîneur |
| 18 h 30 | Pistes 2 et veille lancées à la demande de Corentin, hors du gel (`avenant_pistes_2.md`) |
| 18 h 53 | Liste gelée, **avancée à la demande de Corentin** (« n'attends pas si tu as déjà tout »). Aucun candidat admis après 18 h 45 |
| 19 h à 21 h 10 | Lecture des juges relus, puis du test vierge comptage (19 h 49-20 h 13), confirmée par Corentin |

## 3. Maladies

### Liste gelée

| Place | Finaliste | Famille | Coût de réglage (F1 : 33,94) |
| --- | --- | --- | --- |
| 1 | d3b : élève distillé de F1, 2 ConvNeXt-Tiny DINOv3 (sans TDTU / sans Éthiopie) | B | 32,77 |
| 2 | F1_bornes : F1 où chaque lecteur n'est lu que si la décision en dépend | A | 33,94 |

### Juges relus (une lecture par finaliste)

| | BanSpot tachées sans alerte (limite ≤ 6) | BanSpot saines en alerte (limite ≤ 56) | Cordana du Pérou en alerte (limite ≥ 97 %) | Verdict |
| --- | --- | --- | --- | --- |
| Témoin F1 (en service) | 4 / 646 | 56 / 646 | 99,4 % | — |
| **F1_bornes** | 4 / 646 | 56 / 646 | 99,4 % | **passe** |
| d3b | **12 / 646** | non lu | 358 / 368 lues | **ne passe pas** |

- **F1_bornes** : 0 alerte différente de F1 sur 1 797 photos. 113 libellés changent (6,3 %), surtout « à vérifier » ou Sigatoka devenus « non identifiée ». La marge sur les saines est nulle, comme pour F1.
- **d3b** : il perd 8 tachées que F1 mettait en « à vérifier », et n'en gagne aucune. Le verdict était fixé dès 20 h 34. Le Juge a ensuite arrêté la lecture (machine saturée, jusqu'à 20 s par photo), sans relire. Temps de d3b : 3,3 à 4 s par photo, machine partagée.
- Rappel : ce sont des **juges relus**. La v10b avait été installée après une lecture de BanSpot.

### Adoption proposée : F1_bornes

Même décision que F1 sur toute photo, 54 % de temps en moins que le code installé (mesure par lecteur), et 67 % de bout en bout sur 12 photos. **À appliquer seulement avec l'accord de Corentin** : il faut remplacer la lecture des morceaux de `fieldscan/modules/maladies.py::_executer_melange` par la version « bornes ». Le correctif est décrit dans `out/maladies/nuit_1311/banc/finalistes.md`.

### Ce qu'on a appris

- **d3b n'est pas stable.** Avec la même recette et trois autres graines (M-piste2), on obtient 33,44, 34,49 et 35,12. La moyenne sur 4 graines est 33,95, soit F1. d3b était le tirage chanceux. Les autres ratent 157 à 165 malades en Éthiopie, contre 117 pour F1.
- **Réserve des pistes 2 : MC1-OU-proche (famille C).** Sur les photos proches, si F1 n'alerte pas mais d3b oui, la photo passe en « à vérifier ».
  - Il rate 208 malades sur les 5 jeux, contre 243 pour F1, sans en perdre aucune. Coût 32,83.
  - Il est instable : il ne passe la règle qu'avec la graine 0, et vaut 33,11 à 33,71 avec les autres.
  - Il échouera presque sûrement sur BanSpot : ses alertes contiennent celles de F1, déjà à 56 / 56.
- **Ce qui n'a rien donné** :
  - MB1 : réglages des photos « loin » ;
  - MB3 : mélanges avec la v12 ;
  - MB4 : règles pour les malades peu tachées ;
  - mélanges géométriques avec d3b et règles de désaccord ;
  - élève sensible au coût (d3c) ;
  - agrégation des morceaux par seuil.
- Diagnostic conformel (veille) : un seuil réglé sur 4 pays pour promettre 1 % de malades ratées en rate 8,8 % sur PSFD. Le passage d'un pays à l'autre reste le problème de fond.

## 4. Comptage

### Liste gelée

| Place | Finaliste | Famille | Moyenne des 5 F1 de réglage (v5 : 0,778) |
| --- | --- | --- | --- |
| 1 | `E5p90b_c13e_d-0.1` : aiguillage vers c13e, spécialiste des petits plants | C | 0,881 |
| 2 | `CB13_trous_b0.20_reseau` (A1) : aiguillage v3 + v4 et remplissage des trous | A | 0,865 |

Tout le gain de réglage vient de btd_val, de la même orthomosaïque que btd_train.

### Juges relus

| | segmento est | CG mères | banano | F1 moyen (≥ 0,5901) | Erreur de compte (≤ 0,382) | Fausses sans bananier (< 1 %) |
| --- | --- | --- | --- | --- | --- | --- |
| Témoin v5 | 0,677 | 0,315 | 0,808 | 0,600 | 0,382 | 36 (0,46 %) |
| `E5p90b_c13e_d-0.1` | 0,666 | 0,325 | 0,808 | 0,600 | 0,170 | 0 |
| A1 | 0,685 | 0,398 | 0,808 | 0,630 | 0,238 | 36 (0,46 %) |

Les deux passent. La règle désigne `E5p90b_c13e_d-0.1`, qui a la meilleure moyenne de réglage. Sa marge sur le F1 n'est que de 0,0097, et son erreur basse sur CG vient d'une compensation : 168 fausses détections contre des ratés. Le Contrôleur a fait un deuxième avis indépendant : mêmes résultats, à 2 détections près sur segmento pour A1.

### Test vierge `banana_trees_kp` (lu une fois, confirmé par Corentin)

| | P | R | F1 | Erreur de compte |
| --- | --- | --- | --- | --- |
| v5 à 0,30 | 0,186 | 0,096 | **0,126** | **0,485** |
| `E5p90b_c13e_d-0.1` | 0,167 | 0,082 | 0,110 | 0,511 |

- La méthode a été écrite à 19 h 48, avant toute lecture : échelle tirée des annotations seules (11,1 cm/px d'origine, ramenée à 5 cm/px). Empreintes 10 / 10. Deuxième avis identique.
- Le candidat aiguille 148 photos sur 157 et recule. **Décision de Corentin : garder le v5.**
- Les deux modèles s'effondrent : les détections tombent en médiane à 45 px des points annotés, pour un rayon de 20 px. Causes possibles, non vérifiées et non corrigées (ce serait régler sur le test) : la basse résolution, l'étirement en 640 × 640, des points mal centrés, une échelle variable d'une photo à l'autre (8,6 à 14,3 cm/px).

### Pistes 2 (réserve, réglage seulement ; C-piste2 fini à 21 h 47, 27 essais)

- **CC1_v5h_50, moyenne des cartes v5 + c13h** : réglage 0,889 ; 4 anciennes validations **0,863** contre 0,854 pour le v5, le premier gain hors btd_val ; **0,857 à 11 cm/px**, contre 0,601 pour le v5. Réserve : plants mères à 8 cm, 0,750 contre 0,770. Le même mélange avec un réseau frère (c14j) reste finaliste.
- **CC3_a1_a35** (famille A) : A1 puis suppression des pics à 0,35 × l'écartement de plantation : 0,8671, sans btd_val 0,8563 (environ un pied gagné sur MM et sur jeunes).
- **Fragilité de CC1** : avec les 3 autres réseaux robustes (c14j, c13f, c13g), le mélange reste finaliste et tient à 11 cm (0,856 à 0,861), mais ne gagne qu'environ +0,004 sans btd_val ; c13h est le plus favorable. Il est 3,2 fois plus lent que le v5. CG (agroforesterie) n'est pas mesuré.
- Le carnet Kaggle `c14-lot2` est encore en file, abandonné mais non supprimé (environ 0,5 h de GPU s'il démarre).
- **Stabilité de c13e** : 3 graines, moyenne de réglage 0,8808 à 0,8811. La recette est stable, mais cela ne change rien au test vierge.
- c14j (réglage fin plus doux de c13h) ne remonte pas les plants mères (0,825).
- Le test vierge est consommé. Pour juger CC1, il faudra un jeu neuf ou une décision de Corentin sur une relecture des juges.

## 5. Veille, hauteur et rendu

- **Veille** (`docs/veille_2026-11-14/synthese.md`) : 5 idées par module. Deux références vérifiées en ligne (Zhou et al. 2026 ; CountingDINO, WACV 2026). Aucun nouveau jeu ouvert de bananiers.
- **Hauteur** (`docs/veille_2026-11-14/hauteur.md`) :
  - aucun jeu public de bananiers n'a à la fois un modèle de surface et des annotations ;
  - banavista, déjà local, a 348 photos brutes qui se recouvrent, mais sans GPS (vérifié : 0 champ EXIF) ;
  - essai en cours selon `docs/protocole_hauteur_banavista.md`, validé par Corentin. La reconstruction OpenDroneMap compare 4 753 paires de photos ;
  - phase 1 : au moins 80 % de photos placées et au moins 70 % de la zone couverte ;
  - phase 2 : les sommets de la surface contre le v5 sur les couronnes jointives.
- **Rendu Blender** : en cours (`out/rendu_blender/`). Bananier procédural, plants placés sur les détections du v5 d'une tuile d'entraînement. Trois vues : drone oblique, plant rapproché, dessus à côté de l'image réelle.

## 6. Téléchargements, Kaggle et interdits

- **Avec l'accord de Corentin** (rangés hors du dépôt, empreintes identiques aux fichiers publiés, signatures valides) :
  - OpenDroneMap 3.6.2 (245 Mo, AGPL), installé dans `C:\ODM` ;
  - Blender 5.2.4 LTS (406 Mo, GPL), portable, dans `C:\Users\coren\outils\blender_5.2.4\`.
- **Aucune donnée téléchargée.** Candidats de la prospection, en attente de la décision de Corentin (`out/prospection_nuit_1311/candidats.md`) :
  - BBTV-3 (Roboflow, 1 338 images, CC BY 4.0, environ 70 Mo) comme test vierge maladies ; BTDDD l'emporterait selon la règle de comptage du plan ;
  - des négatifs pour le comptage ;
  - environ 450 Mo en tout.
- **Données sur demande** (Fan et al. 2025 à Taïwan, Selvaraj et al. 2025 en RDC et au Vietnam) : les demander relève de Corentin.
- **GPU Kaggle** :
  - M-entraîneur 2,92 h ;
  - C-entraîneur environ 3,05 h ;
  - M-piste2 1,14 h ;
  - C-piste2 environ 0,55 h, plus un lot en file.

  Kaggle a remplacé les P100 par des T4. C-entraîneur a créé un jeu Kaggle **privé**, `comptage-c13-depart`, qui ne contient que ses poids v6f.
- **Interdits** : 13 passages du Contrôleur, aucune alerte. Aucun commit (HEAD 6fb6b42), aucun fichier suivi modifié, aucun accès aux juges ni aux tests en dehors des Juges.
  - Signalés sans être des infractions : lecture des MD5 de BanSpot et de la Cordana par M-entraîneur pour bloquer les envois ; liste des noms du zip `banana_trees_kp` par Prospection.
  - Un PDF bioRxiv a été enregistré tout seul par l'outil web dans un dossier temporaire hors du dépôt. Un PDF CEUR a été refusé par le garde-fou.

## 7. À décider par Corentin

1. **Adopter F1_bornes** : modifier `fieldscan/modules/maladies.py` pour lire avec les bornes. Mêmes alertes, environ deux fois plus rapide.
2. **Comptage, basse résolution** : comment juger CC1_v5h_50 (jeu neuf ? relecture ?), et faut-il chercher d'autres données à 8-11 cm/px.
3. **Téléchargements de la prospection** (BBTV-3, négatifs).
4. **Essai hauteur** : suite selon le verdict des phases 1 et 2.
5. **Commit** de cette nuit : rien n'est commité. Les poids `.pt` des nouveaux dossiers `modeles/maladies_nuit_1311/` et `modeles/maladies_nuit_1411/` ne sont pas couverts par le `.gitignore`.

## 8. Fichiers principaux

- Plan et avenants : `docs/plan_nuit_2026-11-13.md`, `avenant_horaires.md`, `avenant_pistes_2.md`, `docs/protocole_hauteur_banavista.md`.
- Finalistes :
  - `out/maladies/nuit_1311/banc/finalistes.md` ;
  - `out/maladies/nuit_1311/kaggle/finalistes.md` ;
  - `out/comptage/nuit_1311/banc/finalistes.md` ;
  - `out/comptage/nuit_1311/kaggle/finalistes.md` ;
  - les `finalistes_piste2.md` des deux pistes 2.
- Contrôle et juges : `out/controle_nuit_1311/verdicts.md`, `empreintes_liste_gelee.txt`, `juge_maladies.md`, `juge_comptage.md`.
- Journaux : `docs/nuit_2026-11-13/journal_*.md`.
