# Juge maladies : lecture unique des juges (nuit du 12 au 13 novembre 2026)

Agent Juge maladies. Seul agent à avoir lu les juges (BanSpot, Cordana du Pérou), une seule fois, sans rien régler dessus. Règles appliquées telles qu'écrites : `docs/plan_nuit_2026-11-12.md`, 4.4 et 4.5 (SHA-256 7b19e2215c4717363d9e9db1b374b806e8fe78d1693a49fd352f322af6d4df48, inchangé), `docs/nuit_2026-11-12/regle_gel_finalistes.md` (73017722045aa8711af85c59cdcde8aa0cb3ef613122d1f1e43aa0bec231b6ab). Journal horodaté : `docs/nuit_2026-11-12/journal_juge_maladies.md`. Code : `scripts/juge_nuit_m_juges.py`, `scripts/juge_nuit_m_bilan.py`, `scripts/juge_nuit_m_rapport.py` (et `juge_nuit_m_debit.py`, débit sur le réglage). Probabilités et décisions : `out/controle_nuit_1112/juge_m/`.

## 1. Liste gelée (Contrôleur, `verdicts.md` version 12, 7 h 00) et empreintes

| Place | Finaliste | Famille | Coût de réglage | Définition |
| --- | --- | --- | --- | --- |
| 1 | **F1_trois_morceaux2x2**, t = 0,70 | A | 35,96 | v10b (lecture entière + morceaux 2 × 2) + soupe + v2, géométrique ; loin = v2 ou proche |
| 2 | **C_quatre_v12a14**, t = 0,76 | C | 36,07 | v10b + soupe + v2 + v12a14 (modèle final), géométrique ; loin = v2 ou proche |
| 3 | **v12a13**, seuils de la v10b | B | 41,50 | v12a13 (modèle final) à la place de la v10b ; loin = v2 |

Conforme à la liste attendue. Les 26 empreintes de `out/controle_nuit_1112/empreintes_liste_gelee.txt` qui concernent les maladies ont été recalculées à 7 h 05, avant la lecture : **26 / 26 identiques** (`juge_m/sha.json`) : v10b (3 réseaux + seuils), soupe (3 + seuils), v2 (3 + seuils), aiguilleur, v12a14 (3 + seuils), v12a13 (3 + seuils), `scripts/m12_banc_finalistes.py`, `scripts/m12_banc_commun.py`, `scripts/controle_nuit_m_appliquer.py`, `scripts/controle_nuit_m_recalcul.py`, `fieldscan/modules/maladies.py`.

Décisions : celles du code gelé de M-banc (`m12_banc_finalistes.repondre`, `CANDIDATS`), importé sans modification ; v12a13 : `decider_convnext` avec les seuils de la v10b, branche loin v2 (politique b), comme la chaîne.

## 2. Déroulé et coupure

- 7 h 05 : lecture unique des juges (`charger_juges`, probabilités en cache du 11/11 pour v10b, soupe, v2 et aiguilleur), témoin, bornes.
- 7 h 05-7 h 43 : lecture des morceaux 2 × 2 (F1), 88 / 92 photos.
- **≈ 7 h 45 : coupure de la session**, plus aucun calcul jusqu'à 8 h 52. **L'heure limite de 8 h 30 a été dépassée à cause de cette coupure.**
- 8 h 53-8 h 57 : les 4 photos 2 × 2 restantes (les 88 sauvées n'ont pas été relues), puis bilan et deuxième avis, sur consigne du chef d'orchestre.
- **C_quatre_v12a14 et v12a13 : non mesurés, coupure de session.** Leurs lectures (v12a14 sur 1 164 photos, v12a13 sur 1 796) n'ont jamais été lancées. Ils ne pouvaient de toute façon plus être adoptés une fois F1 passé (coûts de réglage plus élevés) ; Corentin pourra les faire lire plus tard, pour information.

**Calculs évités par bornes exactes** (méthode écrite au journal à 6 h 50, avant toute lecture de juge ; elle ne change aucune décision). Une photo proche est en alerte si et seulement si P(saine) du lecteur < t. Pour F1, cette P(saine) décroît quand la moyenne des 2 plus fortes P(malade) des morceaux augmente : j'ai calculé la décision avec des morceaux « saine 100 % » et « malade 100 % ». Quand les deux décisions sont égales, la décision de F1 ne dépend pas des morceaux. Il restait **92 photos sur 1 797** (86 BanSpot, 6 Cordana) dont la décision dépendait des morceaux : ce sont elles qui ont été lues en 2 × 2, avec la préparation de `m12_banc_finalistes.calculer` (copie exacte), en 32 bits. Le deuxième avis (section 6) vérifie ces bornes indépendamment.

## 3. Témoin : chaîne installée (v10b proche, v2 loin)

| | PER_NKA | PER_RDMI | BanSpot total | Cordana du Pérou en alerte |
| --- | --- | --- | --- | --- |
| Tachées sans alerte ; saines en alerte | 2 / 139 ; 8 / 102 | 4 / 507 ; 53 / 544 | **6 / 646 ; 61 / 646** (26 à vérifier) | 500 / 505 (99,0 %) |

**Le témoin retrouve exactement le 11/11** (`docs/protocole_maladies_v10c_banspot.md`, section 6 : 6 / 646 et 61 / 646 ; par ferme, 2 ; 8 et 4 ; 53). Les réponses aux 646 tachées sont les mêmes (336 non identifiées, 280 Sigatoka noire, 19 fusariose, 5 à vérifier, 6 saines). Seule différence : le protocole écrit les effectifs de PER_RDMI 511 et 548, ce qui fait 650 au total ; la liste en compte 507 et 544 (646 au total). C'est une coquille du protocole, les comptes eux-mêmes sont identiques. 1 photo BanSpot est aiguillée « loin », aucune photo de la Cordana. Cordana du Pérou dite Sigatoka par la chaîne : 262 / 505 (52 %).

## 4. Finalistes

### F1_trois_morceaux2x2 (t = 0,70 ; coût de réglage 35,96)

| Mesure | Limite (4.4) | PER_NKA | PER_RDMI | BanSpot total | Cordana du Pérou | Chaîne installée |
| --- | --- | --- | --- | --- | --- | --- |
| Tachées sans alerte | ≤ 12 / 646 | 0 / 139 | 4 / 507 | **4 / 646** | — | 6 / 646 |
| Saines en alerte | ≤ 61 / 646 | 9 / 102 | 47 / 544 | **56 / 646** (52 à vérifier) | — | 61 / 646 |
| Cordana en alerte | ≥ 97 % | — | — | — | **502 / 505 (99,4 %)** | 500 / 505 (99,0 %) |

- Décisions inconnues : 0. Comptes définitifs.
- **Verdict de la règle 4.4 : PASSE** (4 ≤ 12 ; 56 ≤ 61 ; 99,4 % ≥ 97 %). La marge sur les fausses alertes n'est que de 5 photos.
- Réponses aux 646 tachées : 326 Sigatoka noire, 219 non identifiées, 64 à vérifier, 33 fusariose, 4 saines. Saines : 590 saines, 52 à vérifier, 2 fusariose, 2 non identifiées.
- Pour information, hors règle : **la Cordana du Pérou est dite Sigatoka plus souvent** : 357 / 505 (71 %), contre 262 / 505 (52 %) pour la chaîne installée. L'alerte est bonne, mais le nom est faux plus souvent.

### C_quatre_v12a14 (t = 0,76 ; coût de réglage 36,07)

**Non mesuré, coupure de session.** Ne peut plus être adopté : F1, au coût de réglage plus bas, passe. Aucune photo lue par la v12a14 ; les bornes seules laissent 938 + 226 décisions inconnues.

### v12a13 (seuils de la v10b ; coût de réglage 41,50)

**Non mesuré, coupure de session.** Ne peut plus être adopté, pour la même raison. Aucune photo lue.

## 5. Adoption proposée

**F1_trois_morceaux2x2 (t = 0,70)**. C'est le seul finaliste mesuré et il passe la règle 4.4. Il a aussi le coût de réglage le plus bas de la liste gelée (35,96) : aucun autre finaliste ne pourrait lui passer devant, même en passant la règle. La proposition est à soumettre à Corentin. Le correctif de la chaîne est décrit, non appliqué, dans `out/maladies/nuit_1112/banc/finalistes.md`, section 5.

## 6. Deuxième avis (Contrôleur, `scripts/controle_nuit_m_appliquer.py`, SHA-256 vérifié)

J'ai passé son code sur mes probabilités (`juge_m/second_avis/`), avec les deux remplissages des morceaux non lus : « saine 100 % » et « malade 100 % ».

| Comparaison avec mes alertes | BanSpot, bas | BanSpot, haut | Cordana, bas | Cordana, haut |
| --- | --- | --- | --- | --- |
| F1 | 0 écart | 0 | 0 | 0 |
| Témoin (référence v10b) | 0 | 0 | 0 | 0 |

**Aucun écart, sur 1 797 photos et pour les deux remplissages.** Comme le code du Contrôleur redonne les mêmes alertes avec les morceaux à 0 % comme à 100 % sur les photos non lues, la borne exacte qui a évité ces lectures est confirmée par un code indépendant.

## 7. Test vierge (AgroVisionBD)

**Lu une fois, le 13/11 de 9 h 23 à 11 h 44**, avec l'accord de Corentin (vers 9 h 30). Script : `scripts/juge_nuit_m_vierge.py`, SHA-256 26 / 26 identiques.

Le Juge s'est figé à 9 h 46. Son calcul s'est arrêté à 10 h 29, avec 1 024 photos lues sur 1 082 pour la v10b. Le chef d'orchestre a relancé le même script à 10 h 46 ; il a repris les probabilités sauvées sans rien relire. Aucun résultat n'avait été regardé avant la fin.

| Mesure | Installée | F1 | F3 (info) |
| --- | --- | --- | --- |
| Malades sans alerte (sur 716) | 12 | 5 | 8 |
| Saines en alerte (sur 366) | 51 | 87 | 79 |
| dont « à vérifier » | 19 | 66 | 57 |
| Coût | 18,96 | 25,87 | 24,94 |

- Morceaux 2 × 2 lus : 113 photos, celles dont la décision de F1 en dépendait. Il ne reste aucune inconnue.
- Deuxième avis du Contrôleur : 0 écart. Recomptage du chef d'orchestre à partir de `reponses_*.csv` : identique.
- Détails dans `juge_m/vierge/bilan_vierge.json` et dans `docs/nuit_2026-11-12/recap.md`, section 2.

Ce test ne change pas la proposition d'adoption.

Ci-dessous, pour mémoire, l'estimation écrite avant la lecture.

Temps estimé d'une lecture complète sur une machine libre (8 fils), d'après les durées du 11/11 sur BanSpot : aiguilleur 0,37 s par photo, v10b 2,5 s, v2 0,84 s, soupe 0,93 s, soit 2,5 s par lecture v10b d'un morceau.
- **Chaîne installée** (aiguilleur, v10b, v2) : 3,7 s × 1 082 ≈ **1 h 07**.
- **F1** : il ne demande en plus que la soupe (0,93 s par photo, environ 17 min) et les morceaux 2 × 2 des photos dont la décision en dépend (10 s par photo).
  - Avec les bornes exactes ci-dessus : sur les juges, 5 % des photos avaient besoin des morceaux ; s'il en faut 5 à 20 % ici, compter 9 à 36 min.
  - Morceaux lus sur toutes les photos : 3 h.
- **Total chaîne + F1 : environ 1 h 35 à 2 h avec les bornes, environ 4 h 25 sans.** C'est plus long sur une machine partagée : cette nuit, le débit a été divisé par 2 à 2,5.
- À dire avec le chiffre : **le Bangladesh n'est pas un pays neuf.** La v10b l'a appris par BananaLSD (cm8zf62kzh), les v12 par les jeux neufs `5nfjzntwd8` et `6yy9522rdy`. AgroVisionBD n'est neuf que par sa source et sa région (Patuakhali). F1 ne contient pas de v12, mais il contient la v10b.

## 8. Temps par photo (mesuré cette nuit, 4 fils, machine partagée)

- Débit sur 20 photos de réglage, à 6 h 46 (machine encore peu chargée) : 4,15 s par photo pour la v12a14, en lecture de la chaîne ; 3,42 s en mémoire channels_last, avec des probabilités identiques.
- Morceaux 2 × 2 de la v10b, sur les juges, avec un processeur à 100 % : 26 à 33 s par photo, soit 4 lectures (6,5 à 8 s chacune). Après la reprise, le chargement des modèles compris : 52 s par photo.
- Estimations sur une machine libre (8 fils) : chaîne installée 3,7 s par photo, F1 4,6 s par photo sans morceaux et 14,6 s avec. Les estimations de M-banc étaient de 1,8 s et 10 s.

## 9. Réserves du Contrôleur à rappeler avec ce résultat

- **F1** :
  - 1 733 essais de réglage chez M-banc ; optimisme de la recherche d'environ 2,7 points ;
  - la moitié de l'avance des morceaux sur F3 vient du seuil ;
  - fausses alertes de TDTU 241 / 577 au réglage. Sur BanSpot, la limite tient avec 56 / 646, soit 5 de marge : moins de fausses alertes que la chaîne installée (61), mais beaucoup plus de « à vérifier » (52 contre 26) ;
  - temps de calcul environ 4 fois celui de la chaîne.
- **Communes aux maladies** :
  - la v10b a été installée par le binôme après lecture de BanSpot ;
  - la soupe et la v2 ont appris le même jeu péruvien que la Cordana du Pérou. Ce style familier peut changer les alertes sur ce juge, dans un sens ou dans l'autre ; ici, F1 y nomme plus souvent la Sigatoka à tort.
- **Juges** : une lecture chacun, aucune décision prise dessus. Les jeux « loin » de validation ne sont pas à portée de `charger_juges` (BanSpot et Cordana seulement) : non mesurés.
