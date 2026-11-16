# Journal de l'agent M-banc (nuit du 13 au 14 novembre 2026)

Essais MB1 à MB4 du plan `docs/plan_nuit_2026-11-13.md` (section 4.1), sans entraînement, processeur (3 fils torch au plus). Règles 4.3 appliquées telles quelles, sans les changer. Juges (BanSpot, Cordana du Pérou) jamais lus ; `out/controle_nuit_1112/juge_m/` lu seulement dans `vierge/`. Aucun commit, aucun téléchargement, aucun fichier existant modifié.

Comptage des essais : une configuration évaluée sur le réglage = un essai (chaque point de grille compte). Le recalcul de F1 n'est pas compté.

## 23 h 35 : départ

- Lu : `CLAUDE.md`, le plan (sections 1 à 4, 6, 7), `docs/nuit_2026-11-12/recap.md` section 2, le journal M-banc du 12/11, `scripts/m12_banc_commun.py`, `scripts/m12_banc_finalistes.py`, `fieldscan/modules/maladies.py`.
- Lancé en tâche de fond (23 h 38) : `scripts/m13_banc_calcul_roamer.py`, probabilités des lecteurs de F1 (aiguilleur, v2, soupe, v10b entière) sur les 2 985 feuilles de `data/roamer_dev_loin_feuilles` (1 715 malades, 1 270 saines ; aucune probabilité en cache trouvée). Malades d'abord. Sauvegarde tous les 32. Sortie `out/maladies/nuit_1311/banc/roamer/`.
- Banc : `scripts/m13_banc_commun.py`. Morceaux 2 × 2 : cache Kaggle du 12/11 pour les 4 anciens jeux (toutes les photos), cache du test vierge pour AgroVisionBD (113 photos lues), NaN ailleurs, avec la méthode des bornes.

## 23 h 40 : F1 recalculé sur les 5 jeux, même code (référence, règle 4.3) [M]

Code : `maladies.decider_melange` (installé), lecteur proche à 0,70, `jnsp_alerte` vrai pour les deux branches, comme `config.yaml`. Commande : `python -I -u scripts/m13_banc_commun.py`.

| Jeu | Malades sans alerte | Saines en alerte (dont « à vérifier ») | Coût (points) |
| --- | --- | --- | --- |
| Validation Tanzanie | 0 / 2 001 | 62 / 1 000 (53) | 6,20 |
| TDTU | 19 / 1 059 | 241 / 577 (143) | 47,15 |
| PSFD | 102 / 738 | pas de saine | 41,46 |
| Éthiopie | 117 / 1 134 | 28 / 155 (28) | 49,02 |
| AgroVisionBD | 5 / 716 | 87 / 366 (66) ; saines « loin » 50 / 119 | 25,87 |
| **Coût de réglage (moyenne des 5)** | | | **33,94** |

Les 4 anciens jeux redonnent exactement les chiffres du 12/11 (moyenne à 4 : 35,96) ; AgroVisionBD redonne ceux du test vierge (5 ; 87 dont 66 ; 50 / 119 « loin »), sans aucune photo inconnue. `roamer_dev_loin_feuilles` : en calcul.

Essais cumulés : 0.

## 23 h 42 : d'où viennent les fausses alertes « loin » de F1 (description de F1, pas un essai) [M]

- AgroVisionBD, 119 saines « loin » : 50 en alerte, dont 20 par la v2 (10 « malade, non identifiée », 10 « fusariose ») et 30 par le lecteur proche (toutes « à vérifier »).
- TDTU, 167 saines « loin » : 107 en alerte, dont 71 par la v2 et 36 « à vérifier » du lecteur proche.
- Malades « loin » sans alerte : TDTU 3 / 306, PSFD 37 / 211, Éthiopie 3 / 189, AgroVisionBD 0 / 23.

## 23 h 43 : grille MB1 et règle de choix, écrites avant le calcul

Toutes les variantes gardent F1 pour les photos « proches » (sauf C et D, qui peuvent toucher toutes les photos) ; morceaux 2 × 2 lus comme dans F1.
- **MB1-A, seuil propre aux photos « loin »** : photo « loin » : v2 si elle alerte, sinon lecteur proche au seuil t_L ∈ {0,40 ; 0,45 ; 0,50 ; 0,55 ; 0,60 ; 0,65} (6 essais).
- **MB1-B, règle « loin » plus stricte** : « loin » en alerte seulement si la v2 **et** le lecteur proche (seuil t_L ∈ {0,70 ; 0,80 ; 0,90}) alertent (3) ; « loin » = lecteur proche seul, sans la v2, t_L ∈ {0,60 ; 0,70} (2).
- **MB1-C, aiguilleur en probabilité** : seuil d'aiguillage s ∈ {0,3 ; 0,7 ; 0,9} au lieu de 0,5 (3) ; seuil du lecteur proche t(p) = 0,70 − δ × p_loin pour toutes les photos, δ ∈ {0,1 ; 0,2 ; 0,3}, branche « loin » inchangée (3).
- **MB1-D, « à vérifier » → « saine »** si la v10b entière, la soupe et la v2 donnent toutes P(saine) ≥ m, m ∈ {0,5 ; 0,6 ; 0,7 ; 0,8}, sur les photos « loin » seulement ou sur toutes (8).
- Ensuite, au plus 12 combinaisons des deux meilleures familles (A à D), fixées après la lecture de A à D et écrites ici avant leur calcul.
- **Choix** : parmi les points qui remplissent la règle « finaliste » 4.3 (temps et `roamer_dev_loin_feuilles` compris) et dont les deux voisins de grille la remplissent aussi (plateau), le coût de réglage le plus bas. Égalité à 0,1 point près : le moins d'« à vérifier » sur les saines « loin » d'AgroVisionBD.

## 23 h 44 : MB1, grille de 23 h 43 (25 essais ; cumul 25) [M]

Script `scripts/m13_banc_mb1.py` (règles dans `scripts/m13_banc_regles.py`), journal `out/maladies/nuit_1311/banc/mb1.log`. `roamer_dev_loin_feuilles` pas encore prêt : règle « finaliste » vérifiée ici sans lui ni le temps (les deux sont ajoutés plus bas pour les points qui passent). « ? n » = photos d'AgroVisionBD dont l'alerte dépend de morceaux pas encore lus (bornes) : leurs chiffres sont provisoires.

| Candidat | Coût de réglage | Val. | TDTU | PSFD | Éth. | AgroVisionBD (saines « loin » en alerte) | Règle sans roamer ni temps |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | 33,94 | 0 ; 62 | 19 ; 241 | 102 | 117 ; 28 | 5 ; 87 (50 / 119) | |
| A, tL = 0,55 | 34,10 | 1 ; 62 | 32 ; 222 | 117 | 127 ; 25 | 7 ; 60 (23) ?3 | non (pays) |
| A, tL = 0,65 | 34,23 | 1 ; 62 | 25 ; 238 | 108 | 119 ; 28 | 6 ; 75 (38) ?2 | non (coût) |
| B, v2 et proche, tL = 0,70 | 36,31 | 1 ; 62 | 59 ; 202 | 131 | 152 ; 25 | 7 ; 40 (3) ?17 | non |
| B, proche seul, tL = 0,60 | 33,30 | 1 ; 62 | 26 ; 220 | 120 | 125 ; 26 | 7 ; 48 (11) ?15 | non (pays) |
| **B, proche seul, tL = 0,70** | **32,91** | 0 ; 62 | 19 ; 238 | 102 | 117 ; 28 | 5 ; 70 (33) **?17** | oui, au ras (1,03 point) |
| C, aiguillage à 0,9 | 33,56 | 0 ; 62 | 19 ; 238 | 102 | 117 ; 28 | 5 ; 82 (45) ?5 | non (coût) |
| C, t = 0,70 − 0,1 × p_loin | 33,90 | 1 ; 61 | 27 ; 228 | 116 | 119 ; 26 | 7 ; 65 (32) ?4 | non |
| D, marge 0,7, « loin » | 33,97 | 0 ; 62 | 19 ; 241 | 103 | 117 ; 28 | 5 ; 86 (49) | non |
| D, marge 0,5, toutes | 36,28 | 4 ; 46 | 36 ; 222 | 124 | 142 ; 25 | 9 ; 72 (41) | non |

Lecture :
- Baisser le seuil des photos « loin » (A, C) fait bien tomber les saines « loin » en alerte d'AgroVisionBD (50 → 20 à 23), mais fait rater des malades « loin » dans TDTU, PSFD et l'Éthiopie : le coût de réglage ne baisse pas.
- La marge des trois lecteurs (D) ne touche presque rien : les « à vérifier » des saines ont en général un lecteur sous 0,5.
- Seul point qui passe sans roamer : « loin » = lecteur proche seul, sans la réponse propre de la v2, au seuil de F1 (0,70). Il garde les malades de F1 sur les 4 anciens jeux et gagne sur les saines « loin » (TDTU 241 → 238, AgroVisionBD 87 → 70). Mais il passe au ras, son voisin 0,60 ne passe pas, et 17 photos d'AgroVisionBD sont inconnues.

## 23 h 46 : suite écrite avant calcul

- **MB1-B, grille fine « proche seul »** (choisie après lecture de la grille de 23 h 43, donc comptée et signalée comme telle) : tL ∈ {0,65 ; 0,675 ; 0,725 ; 0,75 ; 0,80} (5 essais). Morceaux d'AgroVisionBD à lire pour les photos inconnues de toute la grille MB1.
- **MB3** : mélange géométrique de la v10b (entière + morceaux, comme F1), de la soupe, de la v2 et de la v12 (a13 ou a14), « autre » = moyenne pondérée des « autre » de la v10b et de la v12 ; poids (1, 1, 1, 1), (1, 1, 1, 0,5) ou (1, 1, 0, 1) ; t ∈ {0,66 ; 0,68 ; … ; 0,80} (8) ; branche « loin » de F1. 2 × 3 × 8 = 48 essais. Probabilités de la v12 : pli qui n'a pas appris le pays (TDTU, Éthiopie), PSFD, validation = moyenne des 2 plis (comme le 12/11). AgroVisionBD : la v12 n'y est pas en cache ; elle ne sera lue (modèle final, environ 1 h 30 de processeur) que si un mélange gagne au moins 1 point sur F1 en moyenne sur les 4 anciens jeux (F1 : 35,96).
- **MB4** : quand F1 ne donne pas d'alerte mais que les lecteurs hésitent, alerte « malade, non identifiée » si la plus forte P(malade) des 4 morceaux (v10b) atteint h. « Hésitent » = P(saine) du mélange de F1 < u, u ∈ {0,80 ; 0,85 ; 0,90}, ou bien un des trois lecteurs (v10b entière, soupe, v2) a P(saine) < 0,5 ; h ∈ {0,5 ; 0,7 ; 0,9}. 4 × 3 = 12 essais. Ratées par maladie notées pour PSFD (Sigatoka jaune) et l'Éthiopie (Xanthomonas).
- **MB2** : (1) morceaux lus seulement là où l'alerte en dépend (bornes exactes), (2) en plus, la soupe et la v10b ne sont pas lues pour les photos « loin » où la v2 alerte (leur réponse est celle de la v2). Les deux gardent exactement les alertes de F1 ; effet sur les noms mesuré sur les 4 anciens jeux (morceaux tous connus). Temps de chaque lecteur mesuré par `scripts/m13_banc_temps.py` (30 photos, 6 par jeu, graine 2026, 2 fils), lancé à 23 h 46.
- Note machine : le calcul roamer (3 fils, PID 12300) ne peut pas être arrêté (arrêt refusé par l'environnement) ; il continue sur les malades puis les saines. Les autres calculs de M-banc tournent à côté, à 2 fils.

## 23 h 49 : MB2, bornes exactes (1 essai ; cumul 26) [M]

Script `scripts/m13_banc_mb2.py`, sortie `out/maladies/nuit_1311/banc/mb2_bornes.json`. Variante « F1_bornes » : soupe et v10b non lues pour les photos « loin » où la v2 alerte ; morceaux lus seulement si l'alerte change entre les bornes « saine 100 % » et « malade 100 % » ; sinon réponse du mélange à trois sans morceaux (même alerte, prouvé par monotonie et vérifié).

| Jeu | Photos | « Loin », v2 en alerte (ni soupe ni v10b) | Morceaux lus : variante / F1 installé | Alertes différentes | Noms différents (photos comparables) |
| --- | --- | --- | --- | --- | --- |
| Validation | 3 001 | 5 | 83 / 2 996 | 0 | 4 / 3 001 |
| TDTU | 1 636 | 334 | 249 / 1 302 | 0 | 17 / 1 636 |
| PSFD | 738 | 145 | 180 / 593 | 0 | 14 / 738 |
| Éthiopie | 1 289 | 151 | 207 / 1 138 | 0 | 25 / 1 289 |
| AgroVisionBD | 1 082 | 41 | 113 / 1 041 | 0 | 0 / 113 (morceaux de F1 inconnus ailleurs) |
| **Total** | **7 746** | **676 (8,7 %)** | **832 (10,7 %) / 7 070 (91,3 %)** | **0** | **60 / 6 777 (0,9 %)** |

- Noms changés : surtout « malade, non identifiée » → « à vérifier » (43), et quelques échanges « fusariose » ↔ « malade, non identifiée ». Toutes restent des alertes. Sigatoka nommée inchangée (validation 919, TDTU 60, PSFD 61, Éthiopie 27).
- Temps : en attente de `m13_banc_temps.py`.

## 23 h 51 : MB1-B fin, MB4 et MB3 (5 + 12 + 48 = 65 essais ; cumul 91) [M]

Script `scripts/m13_banc_mb34.py`, journaux `mb1fin_mb4.log`, `mb3.log`, `essais_*.json`.

**MB1-B, « loin » = lecteur proche seul** (photos inconnues d'AgroVisionBD remplies « saine », chiffres provisoires) :

| tL | Coût de réglage | Val. | TDTU | PSFD | Éth. | AgroVisionBD (saines « loin ») | inconnues | Règle (sans roamer ni temps) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0,60 | 33,30 | 1 ; 62 | 26 ; 220 | 120 | 125 ; 26 | 7 ; 48 (11) | 15 | non |
| 0,65 | 33,10 | 1 ; 62 | 25 ; 234 | 108 | 119 ; 28 | 6 ; 57 (20) | 18 | non (coût) |
| 0,675 | 32,84 | 0 ; 62 | 21 ; 236 | 105 | 117 ; 28 | 6 ; 62 (25) | 19 | oui |
| 0,70 | 32,91 | 0 ; 62 | 19 ; 238 | 102 | 117 ; 28 | 5 ; 70 (33) | 17 | oui |
| 0,725 | 33,44 | 0 ; 62 | 18 ; 245 | 102 | 116 ; 29 | 5 ; 75 (38) | 26 | non (coût) |
| 0,75 | 34,23 | | | | | | 36 | non |
| 0,80 | 34,59 | | | | | | 57 | non |

Aucun point n'a ses deux voisins finalistes : pas de plateau (règle de choix de 23 h 43). À revoir après lecture des morceaux d'AgroVisionBD (73 photos, liste `liste_g2_agrovision_mb1.json`) et roamer.

**MB4, pire morceau quand les lecteurs hésitent : aucun finaliste.** Meilleur coût 36,51 (« un lecteur < 0,5 », h = 0,9). Les règles rattrapent bien les maladies peu tachées, mais au prix de beaucoup de saines en alerte (Éthiopie surtout) :
- « P(saine) du mélange < 0,85, h = 0,5 » : PSFD 102 → 48 ratées (Sigatoka jaune 65 → 33), Éthiopie 117 → 18 (Xanthomonas 113 → 16) ; mais saines en alerte validation 62 → 300, Éthiopie 28 → 130 ; coût 46,13.
- « un lecteur < 0,5 », h = 0,5 à 0,9 : PSFD 97-98, Éthiopie 93-96 (Xanthomonas 91-94) ; Éthiopie 54 saines en alerte ; coût 36,5.
- Ratées de F1 par maladie : PSFD Sigatoka jaune 65, Sigatoka noire 37 ; Éthiopie Xanthomonas 113, Sigatoka 4.

**MB3, mélanges avec v12a13 / v12a14 (4 anciens jeux seulement)** : meilleur coût à 4 jeux **34,66** (a14, poids (1, 1, 1, 0,5), t = 0,74 ; F1 35,96, gain 1,30) ; ses voisins t = 0,72 et 0,76 : 35,29 et 35,45 (gains 0,67 et 0,51). Suivants : a13 (1, 1, 1, 0,5) t = 0,72 : 35,05 ; a13 (1, 1, 1, 1) t = 0,72 : 35,21. Les mélanges avec la v12 rattrapent des malades (PSFD 102 → 78, Éthiopie 117 → 98) mais ajoutent des saines en alerte (TDTU 241 → 266).
- La condition écrite à 23 h 46 (gain ≥ 1 point à 4 jeux) est remplie par un seul point. **Je ne lance pas pour autant la lecture de la v12 sur AgroVisionBD**, et je l'écris ici :
  - pour que ce point soit choisi, il faut un plateau : ses deux voisins devraient passer aussi, ce qui demande un coût AgroVisionBD ≤ 23,5 et ≤ 22,9 (F1 : 25,87) avec une v12 qui ajoute des fausses alertes partout ailleurs ;
  - la règle demande aussi `roamer_dev_loin_feuilles`, donc la v12 sur ses 1 715 malades en plus ;
  - au rythme mesuré cette nuit sur la machine partagée (v10b ≈ 10 s par photo à 2 fils), cela fait plus de 7 h de calcul. Impossible avant 5 h 40.
  - MB3 est donc fermé sans finaliste, faute de calcul, et non mesuré sur AgroVisionBD.

## 23 h 55 : MB2, variante sans morceaux du tout (écrit avant calcul)

- Mélange à trois sans morceaux (F3), branche « loin » de F1, seuil t ∈ {0,70 ; 0,72 ; 0,74 ; 0,76} (4 essais). Règle « variante rapide » 4.3 : au plus 0,5 % d'alertes différentes de F1 sur les 5 jeux, sans malade sans alerte de plus.
- Contrôle du script `scripts/m13_banc_finalistes.py` (F1_bornes, lecteurs mis à NaN là où ils ne sont pas lus) : mêmes réponses que `m13_banc_mb2.py` sur les 5 jeux, 0 alerte différente de F1, 0 photo inconnue.
- Résultat (4 essais ; cumul 95) [M] : aucune variante sans morceaux ne passe. t = 0,74 : 77 / 7 746 alertes différentes (0,99 %), 38 malades sans alerte de plus ; t = 0,76 : 70 (0,90 %), 9 de plus. Journal `mb2_f3.log`.

## 0 h 23 : temps de chaque lecteur mesuré (30 photos) [M]

`scripts/m13_banc_temps.py` terminé (journal `temps.log`, `temps.json`). Contrôle : la v10b relue redonne le cache à 6 × 10⁻⁷ près. Temps moyens sur les 30 photos (2 fils, lot de 1, machine partagée et chargée à 100 % par les autres agents, donc temps absolus gonflés) : aiguilleur 1,8 s ; v2 6,5 s ; soupe 6,2 s ; v10b 13,9 s ; morceaux 2 × 2 42,7 s. Les rapports entre lecteurs sont ceux du 13/11 (morceaux ≈ 3 × la v10b).

## Arrêt vers 1 h 05 et reprise le 14/11 à 13 h 10

- La session s'est arrêtée vers 1 h 05 ; mes calculs en arrière-plan ont été tués avec elle. État des sauvegardes : `temps.json` complet (0 h 23) ; roamer : 352 / 2 985 feuilles lues (toutes malades, ordre tiré au hasard), sauvegardées.
- Reprise demandée par Corentin (message du chef d'orchestre, `docs/nuit_2026-11-13/avenant_horaires.md`) : seuls les horaires changent, `finalistes.md` avant **18 h 40**. Règles inchangées. Je repars de ce journal (95 essais) sans refaire ce qui est mesuré.
- Désormais un seul calcul torch à la fois, 3 fils.

## 13 h 10 : MB2, temps par photo de F1 et de F1_bornes [M]

`scripts/m13_banc_temps_bilan.py` (sortie `temps_bilan.json`). Temps de chaque lecteur pris sur les 6 photos du jeu ; parts de photos lues prises sur le jeu entier (`m13_banc_mb2.masques`). F1 = code installé (`_executer_melange` : tous les lecteurs partout, morceaux sur toutes les photos décidées par le lecteur proche).

| Jeu | F1 installé (s / photo) | F1_bornes (s / photo) | Gain |
| --- | --- | --- | --- |
| Validation | 57,1 | 22,1 | 61 % |
| TDTU | 58,8 | 28,3 | 52 % |
| PSFD | 61,9 | 34,2 | 45 % |
| Éthiopie | 76,1 | 39,5 | 48 % |
| AgroVisionBD | 77,7 | 36,5 | 53 % |
| **5 jeux (pondéré par photos)** | **63,9** | **29,5** | **54 %** |

- **F1_bornes remplit la règle « variante rapide » (4.3)** : 0 alerte différente de F1 sur les 7 746 photos des 5 jeux (0 %), aucune malade sans alerte de plus, 54 % de temps en moins (≥ 30 %).
- Réserve : les temps absolus sont gonflés par la charge (2 fils, machine pleine). Sur une machine libre, le 13/11 donnait aiguilleur 0,58 s, v10b 3,2-3,5 s, v2 0,88 s, soupe 0,95 s, morceaux 10,7 s ; avec les mêmes parts, cela donnerait environ 15 s pour F1 installé et 6,6 s pour F1_bornes (calcul, pas mesure).
- Le chiffre « F1 : 6,8 s par photo » du plan (section 1) est en fait celui de F1 **déjà lu avec les bornes** par le Juge du 13/11 ; le code installé lit les morceaux sur 91 % des photos. Par rapport à ce 6,8 s, F1_bornes ne gagne que le temps de la soupe et de la v10b sur les photos « loin » où la v2 alerte (8,7 %).

## 13 h 10 : reprise des calculs

- Lancé : `scripts/m13_banc_calcul_g2.py agrovision liste_g2_agrovision_mb1.json` (3 fils) : morceaux des 73 photos d'AgroVisionBD inconnues pour la grille MB1.
- Ensuite : reprise du calcul roamer.

## 13 h 12 : roamer, premier regard sur les 352 malades lues (aucun essai nouveau) [M]

- `p_loin` de roamer repris du fichier de M-entraîneur (`out/maladies/nuit_1311/kaggle/p_loin_roamer_dev_loin.csv`) : identique au mien à 2 × 10⁻¹⁶ près sur les 352 feuilles communes. 93 % des feuilles (92 % des malades) sont « loin ».
- Script `scripts/m13_banc_roamer_eval.py`. Morceaux pas encore lus : chiffres avec morceaux « saine 100 % » (plus haute borne des ratées), entre crochets la borne basse.
  - F1 : 90 / 352 malades sans alerte [≥ 38] ; 52 inconnues.
  - MB1-B « loin = proche seul », tL = 0,70 : 161 / 352 [≥ 38] ; 123 inconnues. tL = 0,675 : 170 ; 0,725 : 147.
  - MB1-A, tL = 0,55 à 0,65 : 90 à 91 (21 à 34 inconnues).
- Lecture : sur les feuilles du robot, la v2 porte l'essentiel des alertes de F1 ; la retirer (« proche seul ») risque de faire rater beaucoup de malades. Les morceaux des 164 feuilles inconnues sont lus pour trancher (`liste_g2_352.json`, à la suite des 73 photos d'AgroVisionBD).
- Script de suite du calcul roamer par étapes écrit : `scripts/m13_banc_calcul_roamer2.py` (v2 sur toutes les malades, puis soupe + v10b là où F1 en a besoin, puis le reste).

## 13 h 40 : morceaux d'AgroVisionBD lus (73 photos) ; MB1 recalculé sans inconnue [M]

- `m13_banc_calcul_g2.py agrovision` terminé à 13 h 38 (23 s par photo, 3 fils) ; sortie `g2_agrovision.npz`, chargée par `m13_banc_commun.charger`. F1 inchangé (33,94 ; ses 113 photos étaient déjà lues).
- MB1 et MB1-B fin relancés sur les mêmes configurations (pas d'essai nouveau ; journaux `mb1_g2.log`, `mb1fin_g2.log`). Plus aucune photo inconnue.

| Candidat | Coût de réglage | AgroVisionBD : ratées ; saines en alerte (saines « loin ») | Avant lecture des morceaux | Règle |
| --- | --- | --- | --- | --- |
| F1 | 33,94 | 5 ; 87 (50) | | |
| B, « proche seul », tL = 0,65 | 33,60 | 6 ; 66 (29) | 33,10 | non (coût) |
| B, « proche seul », tL = 0,675 | 33,28 | 6 ; 70 (33) | 32,84 | non (coût) |
| B, « proche seul », tL = 0,70 | 33,23 | 5 ; 76 (39) | 32,91 | non (coût) |
| B, « proche seul », tL = 0,725 | 33,77 | 5 ; 81 (44) | 33,44 | non |
| C, aiguillage à 0,9 | 33,67 | 5 ; 84 (47) | 33,56 | non |
| A, tL = 0,55 | 34,13 | 6 ; 62 (25) | 34,10 | non |

- **MB1 fermé sans finaliste.** Les deux points qui passaient avec les morceaux remplis « saine » ne passent plus une fois les morceaux lus : la marge de 1 point n'est atteinte nulle part (meilleur : 33,23, soit 0,71 point sous F1).
- Ce que MB1 apprend quand même : on peut faire tomber les saines « loin » en alerte d'AgroVisionBD de 50 à 20-25 sur 119 (A, tL = 0,45 à 0,55), mais au prix de malades « loin » ratées dans TDTU (19 → 32 à 49), PSFD (102 → 117 à 124) et l'Éthiopie (117 → 127 à 139).
- Le calcul roamer n'est donc plus nécessaire pour la règle (aucun candidat MB1, MB3 ou MB4 ne passe ; F1_bornes a les alertes de F1 par construction). Les morceaux des 164 feuilles roamer en cours (lancés automatiquement à 13 h 38) donnent seulement les chiffres exacts de F1 sur les 352 malades lues, pour information. La suite par étapes (`m13_banc_calcul_roamer2.py`) n'est pas lancée.

## 13 h 40 : MB2, essai « morceaux en 1 vue », écrit avant calcul

- Variante « F1_bornes_1vue » : F1_bornes, mais morceaux 2 × 2 lus avec la seule vue d'origine (au lieu des 4 vues). Les photos dont l'alerte dépend des morceaux sont les mêmes (bornes indépendantes de la lecture) : seules ces 832 photos sont lues (`scripts/m13_banc_calcul_g2_1vue.py`, 3 fils), après les morceaux roamer.
- 1 essai. Règle « variante rapide » 4.3 contre F1 (≤ 0,5 % d'alertes différentes sur les 5 jeux, aucune malade sans alerte de plus, ≥ 30 % de temps en moins). Temps des morceaux en 1 vue et en 4 vues remesurés sur les mêmes 10 photos.
- Choix entre F1_bornes et F1_bornes_1vue, écrit avant : si les deux passent, je ne garde F1_bornes_1vue que si elle a 0 alerte différente de F1 ; sinon F1_bornes (identique à F1 par construction) reste seule, la 1 vue étant signalée en réserve.

## 14 h 13 : roamer, 352 malades lues avec leurs morceaux (pour information) [M]

Morceaux des 164 feuilles inconnues lus (12,4 s par feuille). Sur les 352 malades lues (tirées au hasard parmi les 1 715), plus aucune inconnue (`roamer_eval.json`) :
- F1 : **54 / 352** malades sans alerte ;
- MB1-B « proche seul » : tL = 0,65 : 91 ; 0,675 : 83 ; 0,70 : 71 ; 0,725 : 56 ;
- MB1-A : tL = 0,55 : 73 ; 0,60 : 70 ; 0,65 : 65.

Sur ce sous-échantillon, tous les points MB1 de la règle « loin plus douce » font rater plus de malades du robot que F1 (de 2 à 37 de plus). Cela confirme la fermeture de MB1. La règle « roamer » n'a pas été vérifiée sur les 1 715 malades, faute de candidat qui en ait besoin.

## 14 h 45 : MB2, morceaux en 1 vue (1 essai ; cumul 96) [M]

`scripts/m13_banc_calcul_g2_1vue.py` : 832 photos lues (2,3 s par photo, 3 fils, machine moins chargée qu'hier soir). Résultat (`mb2_1vue.log`, `mb2_1vue.json`) :
- P(saine) des morceaux, 1 vue contre 4 vues : écart jusqu'à 0,21 à 0,38 selon le jeu.
- Alertes différentes de F1 : **11 / 7 746 (0,14 %)** (validation 1, TDTU 3, PSFD 1, Éthiopie 2, AgroVisionBD 4) ; malades sans alerte en plus : 0 (PSFD 102 → 101).
- Coût de réglage 34,09 (F1 33,94) : AgroVisionBD 87 → 91 saines en alerte.
- Elle remplit la règle « variante rapide » si le temps suit. Mais, selon le choix écrit à 13 h 40, **F1_bornes reste le candidat** (0 alerte différente). F1_bornes_1vue est notée en réserve.
- Lancé à 14 h 45 : `scripts/m13_banc_temps_bout.py`, temps de bout en bout (code installé contre F1_bornes et F1_bornes_1vue) sur 12 photos tirées au hasard (graine 1314), 3 fils.

## 14 h 52 : MB2, temps de bout en bout (12 photos, 3 fils) [M]

`scripts/m13_banc_temps_bout.py` (sortie `temps_bout.json`), modèles chargés avant (chargement non compté), même machine, mêmes 12 photos tirées au hasard dans les 5 jeux (graine 1314) :
- **F1 installé** (`maladies._executer_melange`, réglages de `config.yaml`) : **11,1 s par photo** ; il a lu les morceaux sur 10 photos sur 12 (85 s).
- **F1_bornes** (`executer_f1_bornes`) : **3,7 s par photo**, soit **67 % de moins**. Sur cet échantillon, aucune photo n'avait besoin de ses morceaux (attendu : 10,7 % en moyenne) ; 2 photos « loin » + v2 en alerte.
- F1_bornes_1vue : 3,8 s (aucun morceau lu non plus : même chaîne ici, l'écart est du bruit).
- Morceaux seuls, 4 vues : 9,8 s par photo ; 1 vue : 2,5 s.
- Contrôles : alertes du code installé = cache (0 écart sur 12) ; F1_bornes = F1 installé (0 alerte différente ; 1 nom différent sur 12).
- Les deux mesures concordent : gain de 54 % avec les parts de chaque jeu (13 h 10), 67 % sur ces 12 photos (moins de morceaux qu'en moyenne). Pour la 1 vue, calcul à partir des mesures : environ 26 s contre 29,5 s pour F1_bornes avec les temps de 0 h 23, soit 59 % de moins que F1 installé.

## 14 h 55 : bilan et `finalistes.md`

- **Un seul candidat : F1_bornes (famille A, « variante rapide »).** Alertes identiques à F1 (0 / 7 746), coût de réglage 33,94 (= F1), 54 % de temps en moins sur le code installé (67 % de bout en bout sur 12 photos). Réserve : F1_bornes_1vue (11 alertes différentes, 0,14 %).
- Aucun finaliste « coût » : MB1 (meilleur 33,23), MB3 (non mesuré sur AgroVisionBD, faute de calcul), MB4 (meilleur 36,51).
- **Total : 96 essais de réglage** (MB1 25 + 5 ; MB4 12 ; MB3 48 ; MB2 1 + 4 + 1). Juges jamais lus. Aucun commit, aucun téléchargement, aucun fichier existant modifié.
- Aucun calcul de M-banc ne tourne plus.
