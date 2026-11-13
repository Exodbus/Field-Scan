# Règle de gel des finalistes (chef d'orchestre, 13 novembre 2026, 4 h 00)

Écrite avant toute lecture des juges et du test vierge (aucun agent ne les a lus à cette heure, d'après le Contrôleur, `out/controle_nuit_1112/verdicts.md` version 7). Elle complète `docs/plan_nuit_2026-11-12.md`, qui fixe « 3 finalistes au plus par module » sans dire comment choisir quand il y en a plus. Les règles « finaliste » (3.4, 4.4) et « adoption » (« entre finalistes : la meilleure moyenne de réglage » / « le coût de réglage le plus bas ») ne changent pas.

## Pourquoi une règle par familles

Les trois meilleurs coûts de réglage des maladies (F1, F2, F3) sont la même famille (mélange à trois) et paient le même prix (fausses alertes TDTU 177 → 232 à 241). S'ils échouent sur la limite BanSpot des fausses alertes, ils échouent ensemble. Au comptage, les meilleurs candidats tirent tout leur gain de btd_val, appris à moitié par les v6. Trois places prises par une seule famille ne protègent de rien : la règle répartit le risque.

## Familles

- **Maladies** : (A) mélanges d'anciens réseaux sans réseau de la nuit (F1, F2, F3) ; (B) réseau v12 seul (v12a13, v12a14, v12a4, lot 6) ; (C) mélange contenant un réseau v12 (essai 9 de M-banc).
- **Comptage** : (A) anciens réseaux seuls (E5p90b, E7) ; (B) réseau v6 seul (v6a à v6e, lot 3) ; (C) mélange ou aiguillage contenant un réseau v6 (E10 et voisins).

## Règle

Parmi les candidats écrits dans un `finalistes.md` **et** déclarés ADMIS ou ADMIS AVEC RÉSERVE (conditions remplies) par le Contrôleur **avant 6 h 45** :
1. place 1 : le meilleur score de réglage, toutes familles (maladies : coût le plus bas ; comptage : moyenne des 5 F1 la plus haute) ;
2. place 2 : le meilleur d'une autre famille que la place 1 ;
3. place 3 : le meilleur d'une troisième famille ; s'il n'y en a pas, le suivant au meilleur score, toutes familles.

Égalité à 0,001 près : le moins coûteux en temps de calcul. Le Contrôleur applique cette règle à 7 h et écrit la liste gelée en tête de `verdicts.md`. Le Juge ne lit que cette liste. Entre finalistes qui passent les juges, l'adoption suit les règles 3.4 et 4.4 sans changement.
