# Journal de l'agent M-piste2 (maladies, pistes 2, 14 novembre 2026)

Cadre : `docs/nuit_2026-11-13/avenant_pistes_2.md` (SHA-256 vérifié à 18 h 32 : `baf20929…b83b9`, identique à `empreinte_avenant_pistes_2.txt`) ; règles du plan `docs/plan_nuit_2026-11-13.md`, section 4.3, sans changement ; familles A, B, C du plan. Juges relus (BanSpot, Cordana du Pérou) et tests : jamais lus. Aucun commit, aucun téléchargement, aucun fichier existant modifié. Écriture seulement dans `out/maladies/nuit_1311/piste2/`, `scripts/m14_*.py`, `notebooks/m14_*.py`, `modeles/maladies_nuit_1411/` et ce journal.

Compte des essais : une règle (ou un réseau) mesurée sur le réglage = un essai. Le recalcul de F1 et de d3b (références) n'est pas compté.

## 18 h 34 : lecture

Lus : `CLAUDE.md`, l'avenant, le plan (sections 3, 4, 7), `out/maladies/nuit_1311/banc/finalistes.md` (F1_bornes ; MB1 à MB4 sans finaliste), `out/maladies/nuit_1311/kaggle/finalistes.md` (d3b), les journaux de M-banc (début) et de M-entraîneur, `scripts/m13_banc_commun.py`, `scripts/m13_entr_mesurer.py`, `scripts/m13_entr_ensemble.py`, `notebooks/m13_entrainer_kaggle.py`, `scripts/m13_entr_pousser.py`, `fieldscan/modules/maladies.py` (décisions).

Ce qui a déjà échoué et n'est pas refait : seuil propre aux photos « loin » et règles « loin » plus strictes (MB1) ; « à vérifier » → « saine » avec marge des trois lecteurs (MB1-D) ; pire morceau quand les trois anciens lecteurs hésitent (MB4 : trop de saines en alerte en Éthiopie) ; mélanges avec v12a13 / v12a14 (MB3) ; un seul réseau élève (final1 : roamer) ; d2 (instable) ; lecteur « loin » neuf l1b (ME3).

Références (recalculées par mon script, même code, mêmes photos, pas des essais) :
- **F1** : validation 0 ; 62 | TDTU 19 ; 241 | PSFD 102 | Éthiopie 117 ; 28 | AgroVisionBD 5 ; 87 → coût de réglage 33,94 ; **243 malades sans alerte en tout sur les 5 jeux** ; roamer 227 / 1 715 (limite F1 + 2 = 229). F1_bornes a les mêmes alertes.
- **d3b** (ensemble livrable, couple 0,50 ; 0,70) : 32,77 ; 5 + 30 + 86 + 120 + 10 = 251 malades sans alerte ; roamer 182.

## 18 h 50 : règles écrites avant tout calcul

### Données

- F1 sur les 4 anciens jeux : caches de `scripts/m12_banc_commun.charger_reglage` + morceaux 2 × 2 de `out/maladies/nuit_1112/banc/kaggle_morceaux/` (tous lus). AgroVisionBD : caches de `out/controle_nuit_1112/juge_m/vierge/` + morceaux lus (113 photos du 13/11, plus `out/maladies/nuit_1311/banc/g2_agrovision.npz` de M-banc) ; ailleurs, **méthode des bornes** de M-banc (morceaux remplis « saine 100 % » puis « malade 100 % ») : toutes mes règles sont croissantes en P(malade) des morceaux, donc une photo dont l'alerte ne change pas entre les bornes est sûre ; sinon elle est « inconnue » et ses morceaux sont lus (v10b, `maladies.morceaux_2x2`, 3 fils) avant de conclure. roamer : `out/maladies/nuit_1311/kaggle/maitre/maitre_roamer_dev_loin.npz` (P10, G2, Pso, Pv2, tout lu) + `p_loin_roamer_dev_loin.csv`.
- d3b : `out/maladies/nuit_1311/kaggle/pour_banc/d3b/` (TDTU et Éthiopie lus par le réseau qui ne les a pas appris ; les autres jeux par la moyenne des 2 réseaux). Contrôle avant tout essai : la chaîne d3b recalculée doit redonner 32,77 et 182.
- Alerte, coût, coût de réglage, conditions « finaliste » : plan 4.3, sans changement (code de `scripts/m13_banc_commun.py`).

### Notations

- F = probabilités du lecteur proche de F1 (`melange_geometrique(lecture_morceaux(P10, G2), Pso, Pv2)`), décidé à 0,70 ; chaîne F1 = `decider_melange` (photo « loin » : v2 si elle alerte, sinon lecteur proche).
- D = probabilités de d3b ; chaîne d3b = photo « proche » : `decider_convnext(D, v10b, confiance 0,50)` ; photo « loin » : v2 si elle alerte, sinon `decider_convnext(D, v10b, confiance 0,70)`.
- Seuils `M_V10B` et `M_V2` de `scripts/m12_banc_commun.py` (`jnsp_alerte` vrai), comme partout cette nuit.

### MC1 : mélanges F1 + d3b (famille C), 4 essais

1. **MC1-OU** : alerte si la chaîne F1 **ou** la chaîne d3b alerte ; libellé de F1 s'il alerte, sinon celui de d3b.
2. **MC1-V** : réponse de F1 ; si F1 n'alerte pas et que la chaîne d3b donne une alerte **autre que « à vérifier »** (maladie nommée ou « malade, non identifiée »), la réponse devient « à vérifier ». d3b ne fait que transformer « saine » en « à vérifier », et seulement quand il est sûr que c'est malade.
3. **MC1-G25** et 4. **MC1-G50** : lecteur proche = moyenne géométrique pondérée, sur les 4 classes, de F (poids 1 − w) et de D (poids w), renormalisée ; w = 0,25 ou 0,50. Confiance du lecteur proche fixée d'avance par interpolation des deux confiances d'origine : 0,70 × (1 − w) + 0,50 × w, soit **0,65** (w = 0,25) et **0,60** (w = 0,50). Photo « loin » : v2 si elle alerte, sinon le lecteur proche mélangé décidé à **0,70** (confiance « loin » commune à F1 et d3b). Aucun autre poids ni seuil.

### MC2 : règle de désaccord (famille C), 2 essais

Lecteurs : v10b entière (sans morceaux), soupe, v2, d3b. Un lecteur dit « malade » si sa P(saine) < 0,5 (sinon « saine »). Base : réponse de F1. Si F1 n'alerte pas et qu'au moins k lecteurs disent « malade », la réponse devient « à vérifier ». Toutes les photos (proches et « loin »).
5. **MC2-k1** : k = 1 (les lecteurs ne sont pas unanimes, ou tous disent malade).
6. **MC2-k2** : k = 2 (au moins deux lecteurs sur quatre).

Pas de variante sans d3b (famille A) : avec les trois anciens lecteurs, c'est presque MB4 sans la condition du pire morceau, qui a déjà échoué (trop de saines en alerte en Éthiopie).

### MC3 : Kaggle (carnet `notebooks/m14_entrainer_kaggle.py`, copie **identique** de `notebooks/m13_entrainer_kaggle.py` ; seules les recettes sont écrites en dur dans la copie envoyée, comme le faisait M-entraîneur), forme P100, 3 h de GPU au plus

Recettes, toutes en plis (sans TDTU, sans Éthiopie), poids gardés, maître repris des sorties de `m13-lot1` (aucun nouveau calcul de F1 sur Kaggle) :
- **d3g1** : recette d3b, graine 1 (stabilité de d3b, priorité 1) ;
- **d3c** : recette d3b, mais `poids_ratee` = 3 au lieu de 2 (malade dite saine pesée × 3 dans la perte, comme dans notre coût), graine 0 ;
- **d3cg1** : d3c, graine 1 (stabilité de d3c).

Ordre dans le carnet : d3g1, d3c, d3cg1. Mesure de chaque réseau neuf sous la forme « ensemble livrable » de M-entraîneur (TDTU, Éthiopie : réseau qui ne les a pas appris ; autres jeux : moyenne des 2 réseaux), **au couple de d3b (0,50 ; 0,70), sans nouveau réglage**. Essais Kaggle comptés :
7. **d3g1** seul (stabilité : d3b est dit « stable » si d3g1 passe aussi les conditions 4.3, coût ≤ 32,94 compris ; sinon « instable », et on l'écrit à côté de d3b) ;
8. **d3b + d3g1** (4 réseaux, moyenne des probabilités ; TDTU et Éthiopie lus par les 2 réseaux qui ne les ont pas appris), famille B ;
9. **d3c** seul ; 10. **d3cg1** seul ; 11. **d3c + d3cg1** (4 réseaux), famille B ;
12. **meilleur MC1** (choisi par la règle ci-dessous sur les essais 1 à 4) **avec d3c + d3cg1 à la place de d3b**, famille C.

Au plus 12 essais en tout. Rien d'autre ne sera ajouté sans être écrit ici avant.

### Contrôle de fuite avant l'envoi Kaggle

Aucune image n'est envoyée : seul le carnet et `kernel-metadata.json` partent, avec les jeux Kaggle privés déjà contrôlés par M-entraîneur (`out/maladies/nuit_1311/kaggle/controle_fuite_outils.json` : aucun MD5 ni nom de juge). Avant l'envoi, `scripts/m14_pousser.py` vérifie : (1) que la copie ne diffère du carnet m13 que par les lignes `MODE` et `RECETTES` ; (2) que le dossier d'envoi ne contient que ces deux fichiers ; (3) que le contrôle de fuite des outils dit « aucun MD5 commun, aucun nom de juge » ; (4) que le carnet garde ses refus (chemins de juges, SHA-256 de `test_perou`).

### Règle de choix (écrite avant)

- **Finaliste de réserve** : règle 4.3 sans changement (coût ≤ F1 − 1 = 32,94 ; Tanzanie ≤ 14 et ≤ 77 ; aucun jeu ne perd plus de 2 points de malades sans alerte ; roamer ≤ 229 ; temps ≤ 1,2 × F1), ou règle « variante rapide ».
- Dans chaque piste (MC1, MC2, MC3) : le variant qui passe avec le coût de réglage le plus bas ; à 0,1 point près, celui qui a le moins de malades sans alerte sur les 5 jeux.
- **Au plus 2 finalistes de réserve** dans `finalistes_piste2.md` : le meilleur coût de réglage, puis le meilleur d'une autre famille (sinon le suivant), comme la règle de gel.
- **Coût croisé** (pour information, à côté de chaque choix) : pour chaque jeu tenu à l'écart, la règle de choix appliquée sur les 4 autres jeux (coût moyen sur 4, conditions sur 4) choisit un variant de la piste ; on mesure ce variant sur le jeu tenu à l'écart ; coût croisé = moyenne des 5. Pour un essai sans choix (un seul variant), le coût croisé est le coût lui-même.
- Toujours donné aussi : total des malades sans alerte sur les 5 jeux (F1 : 243), roamer (limite 229), décisions d'alerte différentes de F1, chiffres à côté de F1_bornes et de d3b.

### Temps (écrit avant)

Mesure après 20 h 30 (3 fils), `scripts/m14_temps.py`, sur les 12 photos de M-banc (`temps_bout`, graine 1314) : code installé (`maladies._executer_melange`), F1_bornes (`executer_f1_bornes`), et les réseaux élèves (d3b, 2 réseaux, 4 vues). Temps d'un candidat de la famille C = F1_bornes + d3b (+ morceaux supplémentaires éventuels, comptés à part) ; rapport au code installé. Si la machine est trop chargée, je donne l'estimation à partir de `temps_bout.json` et `kaggle/temps.json`, en le disant.

Essais cumulés : 0.

## 18 h 40 : Kaggle `m14-lot1` lancé ; précision du coût croisé (avant calcul)

- `scripts/m14_pousser.py lot1` : contrôles avant envoi passés (copie identique du carnet m13 sauf `MODE` et `RECETTES`, dossier d'envoi = carnet + métadonnées, contrôle de fuite des outils sans MD5 ni nom de juge, refus des juges présents dans le carnet). Recettes d3g1, d3c, d3cg1. Kaggle répond que la forme « P100 » est retirée : la session tourne sur la forme par défaut (T4) ; statut RUNNING dès l'envoi (pas de file). GPU déjà consommé cette semaine sur le compte : de l'ordre de 4 à 5 h sur 30 d'après les journaux (M-entraîneur 2,92 h ; C-entraîneur ≈ 1,8 h et plus) ; aucun carnet de C-piste2 en cours à 18 h 36.
- Coût croisé, précision : si, sur les 4 jeux gardés, aucun variant de la piste ne passe les conditions (calculées sur ces 4 jeux, roamer compris), c'est F1 qui est « choisi » et c'est le coût de F1 qui est compté sur le jeu tenu à l'écart.
- Banc : `scripts/m14_banc.py` (références F1 et d3b recalculées et contrôlées avant les essais 1 à 6, dans le même passage).

## 18 h 39 : essais 1 à 6 (MC1, MC2) [M] — aucun ne passe

Commande : `PYTHONIOENCODING=utf-8 OMP_NUM_THREADS=3 .venv/Scripts/python.exe -I -u scripts/m14_banc.py mc12` ; sortie `out/maladies/nuit_1311/piste2/bilan_mc12.json`. Références redonnées exactement : F1 33,94 (243 ratées sur les 5 jeux, roamer 227) ; d3b 32,77 (251 ratées, roamer 182). Chaque case : malades sans alerte ; saines en alerte.

| Essai | Coût de réglage | Val. | TDTU | PSFD | Éth. | AgroVisionBD | Ratées (5 jeux) | roamer | Alertes ≠ F1 | Malades perdues / rattrapées vs F1 | Passe |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | 33,94 | 0 ; 62 | 19 ; 241 | 102 | 117 ; 28 | 5 ; 87 | 243 | 227 | — | — | — |
| d3b | 32,77 | 5 ; 42 | 30 ; 218 | 86 | 120 ; 35 | 10 ; 70 | 251 | 182 | 269 | — | (finaliste B) |
| 1. MC1-OU | 33,36 | 0 ; 67 | 15 ; 262 | 76 | 93 ; 40 | 5 ; 99 | **189** | 150 | 104 | 0 / 54 | non (coût) |
| 2. MC1-V | 33,96 | 0 ; 63 | 19 ; 241 | 102 | 117 ; 28 | 5 ; 87 | 243 | 224 | 1 | 0 / 0 | non (coût) |
| 3. MC1-G25 | 33,68 | 2 ; 52 | 20 ; 232 | 100 | 122 ; 31 | 8 ; 76 (1 inconnue) | 252 | 212 | 68 | 16 / 7 | non (coût) |
| 4. MC1-G50 | 33,32 | 3 ; 48 | 25 ; 217 | 97 | 123 ; 34 | 8 ; 71 (1 inconnue) | 256 | 199 | 145 | 33 / 20 | non (coût) |
| 5. MC2-k1 | 35,87 | 0 ; 80 | 17 ; 269 | 88 | 83 ; 55 | 5 ; 90 | 193 | 207 | 126 | 0 / 50 | non (coût, Tanzanie 80 > 77) |
| 6. MC2-k2 | 33,81 | 0 ; 64 | 18 ; 244 | 97 | 106 ; 34 | 5 ; 87 | 226 | 221 | 28 | 0 / 17 | non (coût) |

- Choix (règle de 18 h 50) : **aucun variant de MC1 ni de MC2 ne passe**. Coût croisé : MC1 36,19 (choix sur 4 jeux : MC1-OU pour TDTU et AgroVisionBD, MC1-G50 pour l'Éthiopie, F1 ailleurs) ; MC2 33,94 (F1 partout).
- La photo « inconnue » d'AgroVisionBD (G25, G50) change au plus le coût moyen de 0,08 point : sans effet sur la conclusion ; non lue.
- Lecture :
  - **MC1-OU rattrape 54 malades sans en perdre aucune** (243 → 189 ratées ; PSFD 102 → 76, Éthiopie 117 → 93, TDTU 19 → 15 ; roamer 227 → 150) mais ajoute 33 saines en alerte (TDTU + 21, Éthiopie + 12) : coût 33,36, gain 0,58 point seulement. C'est le meilleur résultat pour la consigne « rater un malade est plus grave », mais il ne passe pas la règle du coût.
  - MC2-k2 rattrape 17 malades sans en perdre (226 ratées), coût 33,81. MC2-k1 met trop de saines en alerte (Éthiopie 28 → 55), comme MB4.
  - Les mélanges géométriques (G25, G50) font comme d3b : moins de fausses alertes, plus de malades ratées. Pas la bonne direction.
  - MC1-V ne change rien : quand F1 dit « saine », d3b n'est presque jamais sûr que c'est malade.

Essais cumulés : **6**.

## 18 h 45 : essais 7 et 8 ajoutés (écrits avant calcul, choisis APRÈS avoir lu les essais 1 à 6 : à signaler comme tels)

Idée : garder ce que MC1-OU rattrape, mais retirer les fausses alertes faibles. Une alerte « à vérifier » d'un seul des deux (F1 ou d3b) est faible ; une alerte nommée (maladie ou « malade, non identifiée ») est forte.
7. **MC1-VOTE** : alerte si F1 donne une alerte forte, **ou** d3b donne une alerte forte, **ou** les deux alertent (n'importe laquelle). Libellé : celui de F1 s'il alerte, sinon celui de d3b. (Une photo où seul F1 dit « à vérifier » et d3b dit « saine » devient « saine ».)
8. **MC1-OU-proche** : MC1-OU sur les photos « proches » seulement ; photos « loin » : réponse de F1.

Aucun seuil nouveau. Ces deux essais sont comptés et le chiffre sera dit optimiste (règle choisie après lecture). Pour l'essai 12 (meilleur MC1 avec d3c + d3cg1) : si aucun MC1 ne passe, on prend le MC1 de plus bas coût de réglage (essais 1 à 4, 7, 8).

## 18 h 41 : essais 7 et 8 [M] — MC1-OU-proche passe sur le réglage (sans le temps)

Commande : `scripts/m14_banc.py mc1b` ; sortie `out/maladies/nuit_1311/piste2/bilan_mc1b.json`.

| Essai | Coût de réglage | Val. | TDTU | PSFD | Éth. | AgroVisionBD | Ratées (5 jeux) | roamer | Alertes ≠ F1 | Malades perdues / rattrapées vs F1 | Passe (sans temps) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | 33,94 | 0 ; 62 | 19 ; 241 | 102 | 117 ; 28 | 5 ; 87 | 243 | 227 | — | — | — |
| 7. MC1-VOTE | 33,31 | 5 ; 38 | 33 ; 197 | 112 | 144 ; 23 | 10 ; 58 | 304 | 254 | 165 | 61 / 0 | non (coût, pays, roamer) |
| **8. MC1-OU-proche** | **32,83** | 0 ; 67 | 18 ; 250 | 89 | 96 ; 33 | 5 ; 88 | **208** | 224 | 55 | **0 / 35** | **oui** (− 1,11) |

- MC1-OU-proche remplit les 4 conditions de réglage : coût 32,83 ≤ 32,94 ; Tanzanie 0 ≤ 14 et 67 ≤ 77 ; aucun jeu ne perd de malade (au contraire : TDTU − 1, PSFD − 13, Éthiopie − 21) ; roamer 224 ≤ 229. Temps : à mesurer (essai prévu après 20 h 30).
- **Réserves, à écrire avec le chiffre** :
  - règle choisie après lecture des essais 1 à 6 (8 essais sur le processeur) : chiffre optimiste ;
  - marge faible (1,11 point pour 1 exigé) ;
  - le gain vient de PSFD (+ 5,28 points) et de l'Éthiopie (+ 2,33) ; validation (− 0,50), TDTU (− 1,28) et AgroVisionBD (− 0,27) perdent un peu, par des saines en plus en alerte ;
  - coût croisé de la piste MC1 complète (choix parmi les 6 variants sur 4 jeux, mesure sur le 5e) : **36,04**, au-dessus de F1 : quand l'Éthiopie est tenue à l'écart, la règle choisit MC1-G50, et sans l'Éthiopie MC1-OU-proche ne gagne que 0,81 point sur les 4 autres jeux. Le choix entre variants n'est pas stable d'un jeu à l'autre ;
  - MC1-OU-proche seul n'a aucun seuil réglé : son coût croisé « à variant fixé » est son coût, 32,83.
- MC1-VOTE perd 61 malades : rejeté (contraire à la consigne).

Essais cumulés : **8**.

## 18 h 43 : essais 13 et 14 ajoutés (écrits avant les résultats Kaggle)

La marge de MC1-OU-proche dépend d'un seul réseau d3b. Stabilité du candidat de famille C, avec les réseaux de `m14-lot1` :
13. **MC1-OU-proche avec d3g1** à la place de d3b (même règle, autre graine) ;
14. **MC1-OU-proche avec d3b + d3g1** (4 réseaux, moyenne des probabilités).
Règle : MC1-OU-proche est dit « stable » si l'essai 13 passe aussi les 4 conditions de réglage. L'essai 12 (meilleur MC1 avec d3c + d3cg1) est MC1-OU-proche avec d3c + d3cg1. Choix final dans MC3 / famille C : règle de 18 h 50 inchangée.

## 18 h 50 : idées de la veille (message de la session principale), écrites avant calcul

Source : `docs/veille_2026-11-14/synthese.md`, section 1.
- **M1, lecteur kNN** : non pris. Il faut extraire les traits ConvNeXt DINOv3 de l'apprentissage et des 7 746 photos de réglage (2 à 4 h de processeur sur 8 cœurs, davantage à 3 fils pendant les mesures des Juges) ou écrire un nouveau carnet Kaggle ; pas faisable proprement avant 23 h 30 à côté de MC3.
- **M2, morceaux comptés au-dessus d'un seuil** : différence avec MB4 vérifiée. MB4 = pire morceau (au moins 1 sur 4) et seulement quand les lecteurs hésitent. Ici : **au moins 2 morceaux sur 4**, sans condition d'hésitation. 2 essais, grille fixée maintenant :
  15. **M2-s70** : réponse de F1 ; si F1 n'alerte pas et qu'au moins 2 des 4 morceaux (v10b) ont P(malade) ≥ 0,70 → « à vérifier » ;
  16. **M2-s90** : idem avec 0,90.
  Toutes les photos. Morceaux inconnus d'AgroVisionBD : bornes (la règle croît avec P(malade) des morceaux) ; photos inconnues lues avant de conclure si elles peuvent changer la conclusion. Famille A.
- **M5, contrôle conformel du risque** : diagnostic, pas un candidat (compté comme 1 essai de mesure, 17). Seuil t de confiance du lecteur proche de F1 (grille 0,70 à 0,99 par 0,01 ; la branche « loin » de F1 inchangée) choisi sur 4 jeux comme le plus petit t tel que (n × taux de ratées + 1) / (n + 1) ≤ α, n = malades des 4 jeux mises ensemble ; mesuré sur le 5e ; α ∈ {1 %, 2 %}. Rapporté : taux de ratées observé contre α, saines en alerte, coût. PSFD n'a pas de saine (seulement les ratées).
- Distillation par les logits seuls (Zhou et al.) : d3c distille déjà les probabilités de F1 (entropie croisée douce, pas d'alignement de traits) ; rien à changer à MC3(b).

## 18 h 46 : numérotation (aucun changement de règle)

Les numéros se recoupent (7 et 8 pris deux fois). Étiquettes définitives, sans rien changer aux règles :
- processeur : P1 à P6 = essais 1 à 6 de MC1, MC2 ; P7 = MC1-VOTE ; P8 = MC1-OU-proche ;
- Kaggle : K1 = d3g1 ; K2 = d3b + d3g1 ; K3 = d3c ; K4 = d3cg1 ; K5 = d3c + d3cg1 ; K6 = MC1-OU-proche avec d3c + d3cg1 ; K7 = MC1-OU-proche avec d3g1 ; K8 = MC1-OU-proche avec d3b + d3g1 (« 7 à 14 » ci-dessus) ;
- veille : V1 = M2-s70 ; V2 = M2-s90 ; V3 = M5 (diagnostic) (« 15 à 17 » ci-dessus).
Au plus 19 essais en tout.

## 18 h 52 : temps de MC1-OU-proche [M]

`scripts/m14_temps.py` (12 photos de M-banc, graine 1314, 3 fils, modèles chargés avant ; machine chargée par les autres agents : seuls les rapports comptent ; sortie `out/maladies/nuit_1311/piste2/temps.json`) :
- F1 installé 27,0 s par photo ; F1_bornes 10,2 s ; d3b (2 réseaux, 4 vues) 4,1 s par photo lue ;
- MC1-OU-proche « simple » (F1_bornes + d3b sur toutes les photos proches) : 14,6 s, soit **0,54 × F1 installé**, mais **1,43 × F1_bornes** ;
- contrôle : 0 alerte différente entre la chaîne mesurée et le banc sur l'échantillon.

**Lecture paresseuse, mêmes réponses par construction** : d3b ne sert que sur une photo « proche » où F1 n'alerte pas (si F1 alerte, la réponse est celle de F1). Il suffit donc de lire d3b après F1_bornes, sur les photos proches sans alerte de F1 (et sur celles dont l'alerte de F1 dépend des morceaux, lues avant les morceaux). Part des photos à lire par d3b sur les 5 jeux : **22,4 %** (1 735 / 7 746 ; `scripts/m14_part_d3b.py`, `part_d3b_a_lire.json`). Temps attendu : 10,2 + 0,224 × 4,1 ≈ 11,1 s, soit **≈ 0,41 × F1 installé et ≈ 1,09 × F1_bornes**. Condition « temps ≤ 1,2 × F1 » remplie dans les deux lectures (code en service ou F1_bornes), à condition d'utiliser la lecture paresseuse. Estimation composée (pas une mesure de bout en bout de la version paresseuse) : à dire avec le chiffre.

## 18 h 53 : MC1-OU-proche décrit (pas un essai) et essais de la veille V1 à V3 [M]

**Ce que MC1-OU-proche change** (`scripts/m14_detail.py`, `detail_mc1_ou_proche.json`) : 35 malades rattrapées, toutes en « à vérifier » : Éthiopie 21 Xanthomonas (F1 en ratait 114), PSFD 7 Sigatoka jaune + 6 cercosporiose noire, TDTU 1 « autre ». 20 saines ajoutées en alerte (validation 5, TDTU 9, Éthiopie 5, AgroVisionBD 1), presque toutes « à vérifier ». roamer : 3 malades rattrapées, 3 saines ajoutées.

**V1, V2 (veille M2, au moins 2 morceaux sur 4 au-dessus de s)** : `scripts/m14_banc.py veille`, `bilan_veille.json`.

| Essai | Coût de réglage | Val. | TDTU | PSFD | Éth. | AgroVisionBD | Ratées (5 jeux) | roamer | Passe |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V1. M2-s70 | 41,79 | 0 ; 101 | 12 ; 293 | 90 | 42 ; 106 | 5 ; 97 (193 inconnues) | 149 | 168 | non (coût, Tanzanie) |
| V2. M2-s90 | 38,57 | 0 ; 64 | 17 ; 268 | 98 | 87 ; 72 | 5 ; 87 (193 inconnues) | 207 | 205 | non (coût) |

Comme MB4 : les morceaux rattrapent le Xanthomonas (Éthiopie 117 → 42) mais mettent la moitié des saines d'Éthiopie en alerte (28 → 72 à 106). Les 193 photos inconnues d'AgroVisionBD ne peuvent qu'ajouter des alertes : au mieux 5 malades rattrapées (− 0,42 point sur le coût moyen), ce qui ne change pas la conclusion ; non lues. Coût croisé M2 : 33,94 (F1 partout).

**V3 (veille M5, contrôle conformel du risque, diagnostic)** : seuil de confiance du lecteur proche de F1 choisi sur 4 jeux pour promettre un taux de ratées ≤ α, mesuré sur le 5e.

| Jeu tenu à l'écart | α = 1 % : seuil ; ratées observées ; saines en alerte | α = 2 % : seuil ; ratées ; saines en alerte |
| --- | --- | --- |
| Validation | 0,88 ; 0,0 % ; 498 / 1 000 | 0,84 ; 0,0 % ; 292 / 1 000 |
| TDTU | 0,87 ; 0,19 % ; 407 / 577 | 0,82 ; 0,38 % ; 359 / 577 |
| PSFD | 0,80 ; **8,8 %** ; — | 0,76 ; **11,4 %** ; — |
| Éthiopie | 0,86 ; 0,79 % ; 136 / 155 | 0,78 ; **5,1 %** ; 71 / 155 |
| AgroVisionBD | 0,86 ; ≤ 0,70 % ; ≥ 160 / 366 | 0,82 ; ≤ 0,70 % ; ≥ 144 / 366 |

Lecture : la promesse « ratées ≤ α » tenue sur 4 pays **ne tient pas sur PSFD** (8,8 % pour 1 % promis) **ni sur l'Éthiopie à 2 %** (5,1 %) : les malades difficiles d'un pays (Sigatoka jaune, Xanthomonas) ne ressemblent pas à celles des autres. Et pour la tenir ailleurs, il faut mettre 30 à 90 % des saines en alerte. Un seuil seul ne donne pas de garantie de ratées d'un pays à l'autre ; ce n'est pas un candidat. (AgroVisionBD : bornes, 193 photos aux morceaux non lus ; ratées au plus, saines en alerte au moins.)

Essais cumulés : **11** (P1 à P8, V1 à V3).

## 18 h 58 : consigne de la session principale

Les Juges démarrent plus tôt : jusqu'à 20 h 30, **2 fils au plus** pour tout calcul local (`OMP_NUM_THREADS=2`, `torch.set_num_threads(2)`). Aucun calcul local en cours à cette heure (mesure du temps finie à 18 h 51, avant le départ des Juges). Les calculs restants (mesure des réseaux Kaggle) sont du numpy sur des probabilités en cache ; lancés avec `OMP_NUM_THREADS=2`.

## 19 h 25 : MC3, résultats de `m14-lot1` (essais K1 à K8) [M]

- Kaggle : `m14-lot1` fini (COMPLETE) à 19 h 21, sur **T4 × 2** (la forme P100 est retirée chez Kaggle) ; 2 590 s = **0,72 h** de session GPU (sur 3 h permises). Maître repris de `m13-lot1` (aucun recalcul de F1). d3c et d3g1 en parallèle (19 min chacune), d3cg1 ensuite (15 min). Sorties récupérées par `scripts/m14_recuperer.py lot1` : probabilités dans `out/maladies/nuit_1311/piste2/kaggle/lot1/`, poids (6 réseaux, 16 bits) dans `modeles/maladies_nuit_1411/lot1/` (jamais commités).
- Mesure : `OMP_NUM_THREADS=2 scripts/m14_banc.py mc3 lot1` (`bilan_mc3.json`). Contrôle : d3b relu depuis les fichiers de plis de `lot2p` redonne 32,77 (identique à `pour_banc`). Couple de d3b (0,50 ; 0,70) partout, sans nouveau réglage.

| Essai | Coût de réglage | Val. | TDTU | PSFD | Éth. | AgroVisionBD | Ratées (5 jeux) | roamer | Malades perdues / rattrapées vs F1 | Passe (sans temps) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | 33,94 | 0 ; 62 | 19 ; 241 | 102 | 117 ; 28 | 5 ; 87 | 243 | 227 | — | — |
| d3b (graine 0, finaliste de ce soir) | 32,77 | 5 ; 42 | 30 ; 218 | 86 | 120 ; 35 | 10 ; 70 | 251 | 182 | 62 / 54 | oui |
| **K1. d3g1 (d3b, graine 1)** | **33,44** | 6 ; 43 | 24 ; 220 | 89 | **160** ; 24 | 12 ; 66 | 291 | 190 | 86 / 38 | **non** (coût ; Éthiopie + 3,8 points) |
| K2. d3b + d3g1 | 33,20 | 6 ; 43 | 27 ; 219 | 87 | 140 ; 31 | 10 ; 68 | 270 | 185 | 70 / 43 | non (coût ; Éthiopie + 2,0) |
| K3. d3c (perte × 3) | 33,29 | 4 ; 47 | 26 ; 243 | 75 | 111 ; 40 | 8 ; 83 | **224** | 160 | 44 / 63 | non (coût) |
| K4. d3cg1 | 33,77 | 6 ; 45 | 22 ; 232 | 88 | 136 ; 30 | 11 ; 78 | 263 | 187 | 63 / 43 | non (coût) |
| K5. d3c + d3cg1 | 33,55 | 5 ; 44 | 23 ; 236 | 84 | 126 ; 34 | 10 ; 79 | 248 | 174 | 54 / 49 | non (coût) |
| P8. MC1-OU-proche (d3b) | 32,83 | 0 ; 67 | 18 ; 250 | 89 | 96 ; 33 | 5 ; 88 | 208 | 224 | 0 / 35 | oui |
| **K7. MC1-OU-proche (d3g1)** | **33,11** | 0 ; 67 | 19 ; 250 | 90 | 111 ; 28 | 5 ; 88 | 225 | 223 | 0 / 18 | **non** (coût, de 0,17) |
| K8. MC1-OU-proche (d3b + d3g1) | 33,07 | 0 ; 67 | 18 ; 249 | 90 | 107 ; 30 | 5 ; 88 | 220 | 223 | 0 / 23 | non (coût) |
| K6. MC1-OU-proche (d3c + d3cg1) | 33,21 | 0 ; 68 | 18 ; 255 | 89 | 102 ; 32 | 5 ; 88 | 214 | 223 | 0 / 29 | non (coût) |

Lecture, avec les règles écrites avant :
- **d3b n'est pas stable d'une graine à l'autre** (règle de 18 h 50) : la même recette en graine 1 donne 33,44 (au-dessus de 32,94) et rate 43 Xanthomonas de plus en Éthiopie (160 contre 117 pour F1 : + 3,8 points, au-delà de la limite de 2). Les 32,77 de d3b tiennent en partie à la graine. À écrire à côté de d3b avant toute adoption. (La reprise d3 → d3b de M-entraîneur gardait la graine 0 : elle ne mesurait que le bruit du GPU.)
- **MC1-OU-proche est instable** au sens de la règle de 18 h 43 : avec d3g1 il fait 33,11 et ne passe pas (de 0,17 point). Avec 4 réseaux, 33,07. Mais dans **toutes** ses versions (4 réseaux élèves différents) : 0 malade perdue, 18 à 35 malades rattrapées, coût 0,73 à 1,11 point sous F1, roamer 223-224. Le sens est stable ; seule l'ampleur (le passage du seuil de 1 point) ne l'est pas.
- **d3c (perte × 3, MC3 b)** : c'est l'élève qui rate le moins de malades (224 en 5 jeux, moins que F1 : 243 ; roamer 160), mais il met plus de saines en alerte (TDTU 243, AgroVisionBD 83) : 33,29, ne passe pas. Sa reprise en graine 1 (d3cg1) fait 33,77 et rate 263. Même instabilité d'une graine à l'autre, surtout sur l'Éthiopie (111 → 136).
- Choix (règle de 18 h 50) : famille B : seul d3b passe (déjà finaliste) ; famille C : MC1-OU-proche (d3b). Coût croisé : famille B 35,76 ; famille C 34,35 (choix sur 4 jeux : MC1-OU-proche pour validation, TDTU, AgroVisionBD ; F1 pour PSFD et l'Éthiopie, car sans l'un de ces deux jeux MC1-OU-proche ne gagne pas 1 point).

Essais cumulés : **19** (P1 à P8, V1 à V3, K1 à K8). GPU : 0,72 h.

## 19 h 27 : lot 2 (dispersion d'une graine à l'autre), écrit avant envoi

Deux graines de plus pour mesurer la dispersion de d3b et de MC1-OU-proche (pas une sélection) : `m14-lot2`, recettes **d3g2** (graine 2) et **d3g3** (graine 3), recette d3b sinon inchangée, poids gardés, mêmes contrôles d'envoi. Essais : K9 d3g2, K10 d3g3, K11 MC1-OU-proche (d3g2), K12 MC1-OU-proche (d3g3), au couple (0,50 ; 0,70). Usage écrit avant : rapporter la moyenne et l'étendue sur les 4 graines (0 à 3) du coût de réglage, des ratées et du roamer, pour d3b seul et pour MC1-OU-proche. **Aucune graine n'est choisie** ; le candidat reste MC1-OU-proche avec d3b (graine 0), marqué « instable » si une graine ne passe pas (c'est déjà le cas avec la graine 1). GPU prévu ≈ 0,5 h (total ≈ 1,2 h sur 3 h).

## 20 h 03 : lot 2, dispersion sur 4 graines (essais K9 à K12) [M]

- Kaggle `m14-lot2` fini à 19 h 54 (T4 × 2, 25,0 min = **0,42 h** ; maître repris de `m13-lot1`). Une première récupération a été coupée par mon propre délai (fichiers partiels) ; relancée en entier (23 fichiers). Poids : `modeles/maladies_nuit_1411/lot2/`. **GPU total M-piste2 : 0,72 + 0,42 = 1,14 h** sur 3 h.
- `OMP_NUM_THREADS=2 scripts/m14_banc.py graines` (`bilan_graines.json`). Même recette d3b, graines 0 (d3b) à 3, couple (0,50 ; 0,70) :

| Graine | Élève seul : coût ; ratées (5 jeux) ; Éthiopie ratées ; roamer | Passe | MC1-OU-proche : coût ; ratées (5 jeux) ; roamer | Passe |
| --- | --- | --- | --- | --- |
| 0 (d3b) | 32,77 ; 251 ; 120 ; 182 | oui | 32,83 ; 208 ; 224 | oui |
| 1 (d3g1) | 33,44 ; 291 ; 160 ; 190 | non | 33,11 ; 225 ; 223 | non |
| 2 (d3g2) | 34,49 ; 293 ; 157 ; 199 | non | 33,29 ; 224 ; 224 | non |
| 3 (d3g3) | 35,12 ; 319 ; 165 ; 212 | non | 33,71 ; 230 ; 224 | non |
| **Moyenne (étendue)** | **33,95** (32,77 à 35,12) | 1 / 4 | **33,23** (32,83 à 33,71) | 1 / 4 |

Lecture (règle de 19 h 27 : description, aucune sélection) :
- **La recette d3b vaut F1 en moyenne (33,95 contre 33,94)** ; d3b (graine 0) est le meilleur des 4 tirages. Les 3 autres ratent 157 à 165 malades en Éthiopie (F1 : 117), au-delà de la limite de 2 points. Le gain de d3b sur F1 tient au tirage.
- **MC1-OU-proche est meilleur que F1 avec les 4 graines** (− 0,23 à − 1,11 point, moyenne − 0,71), toujours sans malade perdue (208 à 230 ratées contre 243), roamer stable (223-224). Mais il ne passe le seuil d'un point qu'avec la graine 0. Il reste « instable » au sens de la règle de 18 h 43.

Essais cumulés : **23** (P1 à P8, V1 à V3, K1 à K12). Rien d'autre n'est prévu ; `finalistes_piste2.md` est complété.
