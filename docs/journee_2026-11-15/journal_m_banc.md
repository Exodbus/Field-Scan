# Journal de l'agent M-banc (journée du 15 novembre 2026)

Cadre : `docs/plan_journee_2026-11-15.md` ; règles du plan du 13/11, section 4.3, sans changement ; familles A, B, C. Processeur, 2 fils au plus (`OMP_NUM_THREADS=2`, `torch.set_num_threads(2)`). Juges relus (BanSpot, Cordana du Pérou) et tests : jamais lus. Aucun commit, aucun téléchargement, aucun fichier existant modifié. Écriture seulement dans `out/maladies/jour_1511/banc/`, `scripts/m15_banc_*.py` et ce journal.

Compte des essais : une règle (une configuration) mesurée sur le réglage = un essai. Le recalcul de F1 et de MC1-OU-proche (références) n'est pas compté.

## 13 h 57 : lecture

Lus : `CLAUDE.md`, le plan de la journée, le plan du 13/11 (sections 3, 4, 6), les journaux M-banc et M-piste2 de la nuit du 13 au 14/11, `docs/veille_2026-11-14/synthese.md` (M1, M2), `scripts/m13_banc_commun.py`, `scripts/m14_banc.py`.

Ce qui est fermé et n'est pas refait : MB1 (seuils « loin », proche seul, aiguillage, marge des trois lecteurs), MB3, MB4 (pire morceau quand les lecteurs hésitent), MC1 / MC2, M2 de la veille avec **au moins 2 morceaux sur 4** au-dessus de 0,70 ou 0,90 sur toutes les photos (V1, V2 : Éthiopie saines en alerte), M5 conformel.

Données (caches, rien de recalculé par réseau) : `m14_banc.charger()` (4 anciens jeux, AgroVisionBD avec les morceaux lus par M-banc et M-piste2, roamer complet par le maître de F1). AgroVisionBD : morceaux connus pour 186 photos sur 1 082 ; ailleurs, méthode des bornes.

## 14 h 00 : règles écrites avant tout calcul

### Référence

F1 recalculé par `m14_banc.f1` (= `m13_banc_commun.f1`, `maladies.decider_melange`), même code, mêmes photos : il doit redonner **33,94**, 243 ratées sur les 5 jeux et roamer 227, au chiffre près ; sinon arrêt. MC1-OU-proche (d3b) doit redonner 32,83.

### Lecteur kNN (idée M1 de la veille), sur des traits déjà extraits

Il n'existe aucun trait d'image (sortie d'encodeur) en cache. Extraire les traits DINOv3 de l'entraînement et des 7 746 photos de réglage demande 2 à 4 h de processeur à 8 cœurs : impossible à 2 fils avant 15 h 45 (à faire sur GPU, voir plus bas). Le kNN de ce jour est donc construit sur les **traits déjà extraits** : les probabilités des trois lecteurs de F1.

- Trait d'une photo : x = (√P10, √Psoupe, √Pv2), 10 nombres (plongement de Hellinger) ; distance euclidienne. Les morceaux ne sont pas dans les traits (inconnus sur 896 photos d'AgroVisionBD).
- **Validation croisée par jeu (pays)** : les voisins d'une photo d'un jeu de réglage sont cherchés **seulement dans les 4 autres jeux de réglage**. roamer : voisins dans les 5 jeux de réglage (aucun roamer en mémoire).
- P_kNN(malade) = vote des k voisins, **équilibré** : chaque voisin malade pèse 1 / (nombre de malades en mémoire), chaque voisin sain 1 / (nombre de saines en mémoire) ; P = poids malades / poids total.
- **k** ∈ {5, 10, 20}, fixé avant de regarder les 3 autres jeux : le k qui donne la plus haute AUROC moyenne de P_kNN sur validation Tanzanie et TDTU (3 essais de mesure, comptés). Égalité à 0,002 près : le plus grand k.

Règles (k fixé), toutes famille A :
- **K1, kNN rattrape sur les photos proches** : réponse de F1 ; sur une photo « proche » où F1 n'alerte pas, « à vérifier » si P_kNN ≥ s, s ∈ {0,80 ; 0,90 ; 0,95} (3 essais).
- **K2, kNN rattrape partout** : idem sur toutes les photos, s ∈ {0,90 ; 0,95} (2 essais).
- **K3, « à vérifier » → « saine » sur les photos « loin »** : réponse de F1 ; sur une photo « loin » où F1 répond « à vérifier », « saine » si P_kNN ≤ q, q ∈ {0,10 ; 0,20 ; 0,30} (3 essais).
- **K4, « à vérifier » → « saine » partout** : idem sur toutes les photos, q ∈ {0,05 ; 0,10} (2 essais).

### Morceaux comptés par seuil (idée M2), variantes non mesurées

- **N(m, s)** : réponse de F1 ; sur une photo « proche » où F1 n'alerte pas, « à vérifier » si au moins m morceaux sur 4 (v10b, 2 × 2) ont P(malade) ≥ s. m ∈ {3 ; 4}, s ∈ {0,60 ; 0,70 ; 0,80 ; 0,90} (8 essais). Famille A. Différence avec V1-V2 : m = 3 ou 4 (et non 2), photos proches seulement.
- AgroVisionBD : règle croissante en P(malade) des morceaux, méthode des bornes. Les photos inconnues ne sont lues que si la conclusion en dépend et que le temps le permet ; sinon les deux bornes sont données et la règle n'est pas déclarée finaliste.

### Combinaisons (écrites maintenant, réglages choisis après lecture de K1 à K4, comptées et signalées comme telles)

- **C1** : K1 (meilleur s) + K3 (meilleur q) ensemble (1 essai) ; « meilleur » = coût de réglage le plus bas de sa famille.
- **C2** : MC1-OU-proche (d3b) + K3 (meilleur q) (1 essai). Famille C.
- **C3, MC1-OU-proche filtré par le kNN** : l'alerte apportée par d3b (photo proche, F1 sans alerte) n'est gardée que si P_kNN ≥ 0,50. Mesuré avec les 4 graines de d3b (0 à 3 ; `m14_banc.lire_kaggle`) (4 essais). Famille C.
- **Stabilité** (règle de M-piste2, 18 h 43) : un candidat de famille C est dit « stable » s'il passe les conditions de réglage avec **les 4 graines**. C2 est aussi mesuré avec les graines 1 à 3 s'il passe avec la graine 0 (3 essais).

Au plus 3 + 10 + 8 + 2 + 4 + 3 = 30 essais. Rien d'autre sans l'écrire ici avant.

### Règle de choix

- Finaliste : règle 4.3 sans changement (coût ≤ 32,94 ; Tanzanie ≤ 14 et ≤ 77 ; aucun jeu ne perd plus de 2 points de malades sans alerte ; roamer ≤ F1 + 2 = 229 ; temps ≤ 1,2 × F1), ou « variante rapide ».
- Entre plusieurs : coût de réglage le plus bas ; à 0,1 près, le moins de malades sans alerte sur les 5 jeux. Au plus 2 dans `finalistes.md` (meilleur coût, puis meilleur d'une autre famille).
- Pour information, à côté : coût croisé (choix sur 4 jeux, mesure sur le 5e, comme M-piste2), plateau (les voisins de grille passent-ils ?), malades rattrapées et perdues par rapport à F1.
- Temps : le kNN coûte une recherche dans 7 746 vecteurs de 10 nombres (mesuré) ; les règles N demandent les morceaux sur les photos proches où F1 n'alerte pas (part mesurée sur les 5 jeux, temps composé à partir de `out/maladies/nuit_1311/banc/temps_bilan.json` ; comparé à F1 installé et à F1_bornes).

### Traits d'image calculés par réseau (pour M-kaggle ou plus tard)

Le vrai lecteur kNN de la veille (similarité cosinus dans l'encodeur ConvNeXt-Tiny DINOv3, affiné et figé) demande les traits de l'apprentissage et des 7 746 photos de réglage + 2 985 de roamer : à extraire sur GPU (≈ 0,5 h selon la veille). Non fait ici.

Essais cumulés : 0.

## 14 h 01 : référence retrouvée ; étape 1 (K1 à K4, N) : 21 essais, aucun ne passe [M]

Commande : `PYTHONIOENCODING=utf-8 OMP_NUM_THREADS=2 .venv/Scripts/python.exe -I -u scripts/m15_banc_knn.py etape1` ; journal `out/maladies/jour_1511/banc/etape1.log`, bilan `bilan_etape1.json`, P_kNN `pk_k20.npz`.

**Références retrouvées au chiffre près** (même code, `m14_banc.f1` = `maladies.decider_melange`) : F1 33,94 (validation 0 ; 62 | TDTU 19 ; 241 | PSFD 102 | Éthiopie 117 ; 28 | AgroVisionBD 5 ; 87), 243 ratées sur les 5 jeux, roamer 227 / 1 715. MC1-OU-proche (d3b) 32,83, 208 ratées, roamer 224.

**Choix de k** (3 essais) : AUROC de P_kNN, validation / TDTU : k = 5 : 0,989 / 0,842 ; k = 10 : 0,996 / 0,876 ; **k = 20 : 0,999 / 0,890 → k = 20**. Pour information ensuite : Éthiopie 0,930, AgroVisionBD 0,982, **roamer 0,619**. Temps du kNN : 0,2 ms par photo.

| Essai | Coût de réglage | Val. | TDTU | PSFD | Éth. | AgroVisionBD | Ratées (5 jeux) | roamer | Perdues / rattrapées vs F1 | Passe |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | 33,94 | 0 ; 62 | 19 ; 241 | 102 | 117 ; 28 | 5 ; 87 | 243 | 227 | — | — |
| K1, s = 0,80 / 0,90 / 0,95 | 33,94 | = F1 | = F1 | = F1 | = F1 | = F1 | 243 | 227 | 0 / 0 (0 alerte changée) | non |
| K2, s = 0,90 / 0,95 | 33,94 | = F1 | | | | | 243 | 227 | 0 / 0 | non |
| K3, q = 0,10 | 33,93 | 0 ; 62 | 19 ; 240 | 103 | 117 ; 28 | 5 ; 86 | 244 | 230 | 1 / 0 | non (coût, roamer) |
| K3, q = 0,20 | 34,13 | 1 ; 62 | 21 ; 238 | 108 | 120 ; 25 | 5 ; 85 | 255 | 252 | 12 / 0 | non |
| K3, q = 0,30 | 34,78 | 1 ; 62 | 22 ; 236 | 113 | 127 ; 25 | 5 ; 83 | 268 | 271 | 25 / 0 | non |
| K4, q = 0,05 | 34,18 | 0 ; 62 | 19 ; 241 | 104 | 121 ; 27 | 5 ; 87 | 249 | 231 | 6 / 0 | non |
| K4, q = 0,10 | 34,52 | 0 ; 61 | 19 ; 238 | 109 | 129 ; 25 | 5 ; 85 | 262 | 233 | 19 / 0 | non |
| N m = 3, s = 0,60 | 38,74 | 0 ; 78 | 13 ; 279 | 92 | 62 ; 84 | 5 ; 87 (?192) | 172 | 223 | 0 / 71 | non (coût, Tanzanie) |
| N m = 3, s = 0,70 | 37,10 | 0 ; 70 | 16 ; 268 | 92 | 77 ; 68 | (?192) | 190 | 225 | 0 / 53 | non |
| N m = 3, s = 0,80 | 36,71 | 0 ; 63 | 17 ; 256 | 97 | 91 ; 60 | (?192) | 210 | 225 | 0 / 33 | non |
| N m = 3, s = 0,90 | 34,66 | 0 ; 62 | 17 ; 246 | 102 | 110 ; 36 | (?192) | 234 | 226 | 0 / 9 | non |
| N m = 4, s = 0,60 | 35,28 | 0 ; 63 | 17 ; 254 | 98 | 93 ; 48 | (?192) | 213 | 226 | 0 / 30 | non |
| N m = 4, s = 0,70 | 34,89 | 0 ; 62 | 17 ; 250 | 100 | 105 ; 40 | (?192) | 227 | 226 | 0 / 16 | non |
| N m = 4, s = 0,80 | 34,51 | 0 ; 62 | 17 ; 244 | 100 | 109 ; 37 | (?192) | 231 | 226 | 0 / 12 | non |
| N m = 4, s = 0,90 | 33,99 | 0 ; 62 | 18 ; 242 | 102 | 116 ; 29 | (?192) | 241 | 226 | 0 / 2 | non |

(N : AgroVisionBD donné à la borne « morceaux inconnus = sains » ; 192 photos inconnues. Même à la borne la plus favorable — les 192 rattrapant au plus les 5 malades ratées d'AgroVisionBD, soit − 0,42 point —, aucun point N ne descend à 32,94 : la conclusion ne dépend pas des morceaux non lus.)

Lecture :
- **Le kNN sur les probabilités des trois lecteurs n'apporte rien de neuf** : là où F1 dit « saine », ses voisins dans les autres pays sont des saines (aucune photo sans alerte de F1 n'a P_kNN ≥ 0,80). Il redit F1. Sur roamer, il ne sépare presque pas (AUROC 0,62).
- **« À vérifier » → « saine » (K3, K4)** : chaque saine retirée coûte une malade ratée ou plus (roamer d'abord : 227 → 230 à 271). Pas de gain.
- **Morceaux comptés (N)** : même défaut que V1-V2 et MB4, atténué mais pas supprimé : les morceaux rattrapent le Xanthomonas d'Éthiopie (117 → 62) mais mettent les saines d'Éthiopie en alerte (28 → 84). Plus la règle est stricte, moins elle change, sans jamais gagner.
- Coût croisé de chaque piste : 33,94 (F1 partout).

Essais cumulés : **21** (3 pour k + 18 règles).

## 14 h 03 : étape 2, écrite avant calcul (choisie après lecture de l'étape 1, à signaler)

- **C1** (K1 + K3) : K1 ne change aucune alerte, donc C1 = K3 q = 0,10, déjà mesuré : non calculé, 0 essai.
- **K5, kNN rattrape sur les photos proches à seuil plus bas** : s ∈ {0,30 ; 0,40 ; 0,50 ; 0,60 ; 0,70} (5 essais). Ajouté parce que K1 ne touchait rien.
- **C2** : MC1-OU-proche (d3b) + K3 q = 0,10 (1 essai) ; s'il passe, graines 1 à 3 (3 essais).
- **C3** : MC1-OU-proche filtré (alerte de l'élève gardée si P_kNN ≥ 0,50), graines 0 à 3 (4 essais).
- **C4** : MC1-OU-proche + K5 au s de plus bas coût de K5 (union des deux rattrapages), graines 0 à 3 (4 essais), seulement si ce K5 rattrape au moins une malade.
- Stabilité : un candidat de famille C n'est dit « stable » que s'il passe avec les 4 graines. Choix : règle de 14 h 00 inchangée.
- Plafond porté à 21 + 5 + 1 + 3 + 4 + 4 = **38 essais**.

## 14 h 02 : étape 2 (K5, C2, C3) : 13 essais ; C2 passe avec la graine 0 seulement [M]

Commande : `scripts/m15_banc_knn.py etape2` ; journal `etape2.log`, bilan `bilan_etape2.json`. Contrôle : MC1-OU-proche relu depuis les plis (graine 0) redonne 32,83.

| Essai | Coût de réglage | Val. | TDTU | PSFD | Éth. | AgroVisionBD | Ratées (5 jeux) | roamer | Perdues / rattrapées vs F1 | Passe (sans temps) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | 33,94 | 0 ; 62 | 19 ; 241 | 102 | 117 ; 28 | 5 ; 87 | 243 | 227 | — | — |
| K5, s = 0,30 | 35,34 | 0 ; 77 | 18 ; 250 | 102 | 114 ; 29 | 5 ; 103 | 239 | 224 | 0 / 4 | non |
| K5, s = 0,40 | 34,00 | 0 ; 66 | 19 ; 242 | 102 | 116 ; 28 | 5 ; 87 | 242 | 226 | 0 / 1 | non |
| K5, s = 0,50 | 33,96 | 0 ; 63 | = F1 | | | | 243 | 227 | 0 / 0 | non |
| K5, s = 0,60 / 0,70 | 33,94 | = F1 | | | | | 243 | 227 | 0 / 0 | non |
| **C2, MC1-OU-proche + K3 q = 0,10, graine 0** | **32,82** | 0 ; 67 | 18 ; 249 | 90 | 96 ; 33 | 5 ; 87 | 209 | 227 | 1 / 35 | **oui** (− 1,12) |
| C2, graine 1 | 33,10 | 0 ; 67 | 19 ; 249 | 91 | 111 ; 28 | 5 ; 87 | 226 | 226 | 1 / 18 | non (coût) |
| C2, graine 2 | 33,28 | 0 ; 69 | 19 ; 249 | 93 | 108 ; 29 | 5 ; 87 | 225 | 227 | 1 / 19 | non (coût) |
| C2, graine 3 | 33,70 | 0 ; 67 | 19 ; 247 | 96 | 111 ; 30 | 5 ; 87 | 231 | 227 | 1 / 13 | non (coût) |
| C3, MC1-OU-proche filtré, graines 0 à 3 | 33,94 | = F1 | | | | | 243 | 227 | 0 / 0 | non |
| [réf.] MC1-OU-proche, graines 0 / 1 / 2 / 3 | 32,83 / 33,11 / 33,29 / 33,71 | | | | | | 208 / 225 / 224 / 230 | 224 / 223 / 224 / 224 | | 1 / 4 |

- C1 non calculé (= K3 q = 0,10). **C4 non calculé** : le K5 de plus bas coût (s = 0,60) ne rattrape aucune malade (condition de 14 h 03).
- **C3 = F1 exactement** : toutes les malades rattrapées par l'élève ont P_kNN < 0,50. Le kNN sur les probabilités des anciens lecteurs ne voit pas ce que l'élève voit ; il ne peut donc ni confirmer ni stabiliser ses alertes.
- **C2 passe la règle 4.3 avec la graine 0** (coût 32,82 ≤ 32,94 ; Tanzanie 0 et 67 ; aucun jeu ne perd de malades ; roamer 227 ≤ 229). Mais :
  - il ne passe avec **aucune des 3 autres graines** : **instable** (règle de 14 h 00) ;
  - il ne fait que retirer de MC1-OU-proche une saine « loin » d'AgroVisionBD (88 → 87) et quelques « à vérifier » de TDTU (250 → 249), au prix d'une malade de PSFD en plus (89 → 90) et de 3 malades de roamer en plus (224 → 227) ;
  - à 0,01 point de MC1-OU-proche (32,83), avec une malade ratée de plus sur les 5 jeux : selon la règle de choix (à 0,1 près, le moins de ratées), **MC1-OU-proche, finaliste de réserve d'hier, passe devant lui** ;
  - règle choisie après lecture de l'étape 1 : chiffre optimiste.
- Temps de C2 : celui de MC1-OU-proche en lecture paresseuse (estimation de M-piste2, 14/11, 18 h 52 : ≈ 11,1 s par photo contre 27,0 s pour F1 installé et 10,2 s pour F1_bornes sur la même machine chargée, soit 0,41 × F1 installé, 1,09 × F1_bornes) + 0,2 ms de kNN. Estimation composée, pas une mesure de bout en bout. Condition « ≤ 1,2 × F1 » remplie dans les deux lectures.

Essais cumulés : **34** (21 + 13).

## 14 h 05 : arrêt des essais et bilan

- Pas d'autre essai : aucune des familles d'idées de la consigne (kNN, morceaux comptés, « à vérifier » → « saine », combinaison avec MC1-OU-proche) ne donne de gain propre ; chercher encore dans les mêmes caches serait de la pêche après lecture.
- **Le vrai lecteur kNN de la veille reste à mesurer** : il lui faut des traits d'image (encodeur ConvNeXt-Tiny DINOv3, affiné et figé) pour l'apprentissage, les 7 746 photos de réglage et les 2 985 de roamer. À 2 fils, plus d'une heure rien que pour le réglage et roamer, sans l'apprentissage : **à extraire sur GPU** (M-kaggle ou une prochaine session), puis à mesurer avec la même grille (k ∈ {5, 10, 20} sur validation + TDTU, K1 à K4). Le résultat de ce jour (probabilités : redit F1) laisse attendre un gain seulement si les traits d'image séparent des malades que les trois têtes jugent saines.
- `finalistes.md` écrit à 14 h 06.
