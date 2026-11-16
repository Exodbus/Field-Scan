# Journal de M-kaggle (maladies avec entraînement sur Kaggle), journée du 15/11/2026

Cadre : `docs/plan_journee_2026-11-15.md` ; règle de finaliste : `docs/plan_nuit_2026-11-13.md`, section 4.3, sans changement. Aucun juge relu (BanSpot, Cordana du Pérou) ni aucun test n'est lu ; aucune de leurs images n'est envoyée sur Kaggle. Processeur local : 2 fils au plus. Aucun commit.

## 14 h 00 : état des lieux (avant tout calcul)

- d3b (graine 0) et les 3 autres tirages de la même recette existent déjà, avec leurs poids : `modeles/maladies_nuit_1311/d3b/` (graine 0), `modeles/maladies_nuit_1411/lot1/` (d3g1) et `lot2/` (d3g2, d3g3) ; 2 réseaux par graine (sans TDTU, sans Éthiopie), tous partis du **même réseau** (réseau 0 de la v10b, tête comprise) : la graine ne change que le tirage des images, les augmentations et l'ordre.
- Leurs probabilités par photo existent aussi (5 jeux de réglage + `roamer_dev_loin`) : `out/maladies/nuit_1311/kaggle/lot2p/` et `out/maladies/nuit_1311/piste2/kaggle/lot1|lot2/`.
- **Déjà fait (M-piste2, 14/11)** : chaque graine seule (33,44 à 35,12), d3b + d3g1 en moyenne de probabilités (K2 : 33,20), MC1-OU-proche avec chaque graine et avec d3b + d3g1 (K8 : 33,07).
- **Pas encore fait** : la moyenne des **4** graines, ni en probabilités, ni en poids (soupe). Aucun fichier `out/maladies/jour_1511/` n'existait à 14 h ; M-banc n'a pas encore de journal.

## 14 h 00 : choix et règles, écrits avant tout calcul

### Choix : stabiliser d3b en moyennant ses 4 tirages, de deux façons

1. **Moyenne des probabilités** des 8 réseaux (4 graines × 2 plis), sur processeur, à partir des fichiers existants : aucune image relue, aucun GPU. Mais elle coûte 4 fois le temps de d3b à la lecture.
2. **Soupe de poids** : pour chaque pli, moyenne uniforme des poids des 4 réseaux (graines 0 à 3), ce qui donne 2 réseaux, exactement comme d3b, donc **le même temps par photo que d3b** par construction. Les 4 réseaux d'un pli partent du même réseau et ont la même recette (3 époques, petits pas), ce qui rend la soupe sensée (Wortsman et al., 2022, « model soups »). Il faut lire les 7 746 photos de réglage + le roamer avec ces 2 nouveaux réseaux : **un seul lot Kaggle court**, sans entraînement (`notebooks/m15_soupe_kaggle.py`, carnet `affilecorentin/m15-soupe`, T4 × 2). Les poids des graines sont pris dans les sorties des carnets Kaggle `m13-lot2p`, `m14-lot1` et `m14-lot2` (rien à téléverser) ; le carnet affiche leur SHA-256, comparé ensuite aux fichiers locaux.

Pourquoi pas un nouvel entraînement : le seul défaut connu de d3b est sa dispersion selon la graine (32,77 à 35,12). Moyenner les 4 tirages existants vise directement ce défaut, sans graine choisie, en ~15 min de GPU. Un lecteur kNN demanderait d'extraire les traits de toutes les images d'apprentissage et de régler k : trop long pour 1 h 30.

### Candidats (4 essais, fixés maintenant ; aucun autre ne sera ajouté)

Seuils inchangés de d3b : confiance 0,50 (proche) et 0,70 (loin) ; **aucun nouveau réglage, aucune graine choisie**. Lecture « ensemble livrable » comme M-entraîneur : TDTU lu par les réseaux sans TDTU, Éthiopie par les réseaux sans Éthiopie, les 4 autres jeux par la moyenne des 2 plis.

| Essai | Nom | Définition | Famille |
| --- | --- | --- | --- |
| J1 | `d3-moy4` | chaîne élève de d3b, P = moyenne des probabilités des 4 graines | B |
| J2 | `MC1-OU-proche (d3-moy4)` | règle MC1-OU-proche de M-piste2 (`scripts/m14_banc.py`, `mc1_ou_proche`), élève = `d3-moy4` | C |
| J3 | `d3-soupe4` | chaîne élève de d3b, réseaux = soupes uniformes des 4 graines (une par pli) | B |
| J4 | `MC1-OU-proche (d3-soupe4)` | règle MC1-OU-proche, élève = `d3-soupe4` | C |

Contrôles (pas des essais) : F1 doit redonner **33,94** et d3b **32,77** avec mon code ; le carnet relit d3b (graine 0, pli sans TDTU) sur la validation et doit retrouver les probabilités de `lot2p` (écart maximal < 0,01, lecture en 16 bits sur un autre GPU).

### Règle de finaliste et de choix

- Finaliste : règle 4.3 telle quelle (coût de réglage ≤ F1 − 1 ; Tanzanie ≤ 14 et ≤ 77 ; aucun jeu ne perd plus de 2 points de malades sans alerte ; roamer ≤ F1 + 2 = 229 ; temps ≤ 1,2 × F1).
- **Temps** : la référence est **F1_bornes** (plan du 15/11 : il « compte comme F1 pour les règles »), la plus sévère ; je donne aussi le rapport au code installé. Pas de nouvelle mesure de bout en bout (processeur partagé) : temps composés à partir des mesures du 14/11 (`out/maladies/nuit_1311/piste2/temps.json` : F1_bornes 10,2 s, F1 installé 27,0 s, d3b 2 réseaux 4,1 s par photo lue ; part des photos où MC1-OU-proche lit l'élève : 22,4 %). La soupe a exactement l'architecture et le nombre de réseaux de d3b : même temps.
- Entre finalistes : coût de réglage le plus bas (4.3). Tous les finalistes sont pourtant écrits dans `finalistes.md`, avec leur famille.
- Stabilité : aucune nouvelle graine n'est tirée ; je rappelle à côté la dispersion des 4 graines (M-piste2). Si un candidat moyenné passe, sa stabilité n'est pas mesurée (il faudrait un 2e lot de 4 graines) : je l'écrirai.

### Budget

GPU : 1 carnet, sans entraînement, estimé à 0,25 h (borne : 3 h). Arrêt des calculs à 15 h 30 au plus tard.

## 14 h 01 : envoi du lot Kaggle `m15-soupe`

- `notebooks/m15_soupe_kaggle.py` : données et contrôles anti-juges repris de `notebooks/m14_entrainer_kaggle.py` (refus par chemin et par SHA-256 de `test_perou`), images d'apprentissage non chargées, puis soupe des 4 graines par pli, lecture des 6 jeux, contrôle d3b relu. Envoi : `notebooks/m15_pousser.py` (dossier d'envoi = carnet + métadonnées seulement ; contrôle de fuite des outils de M-entraîneur : aucun MD5 commun, aucun nom de juge). Forme T4. Poids pris dans les sorties des carnets `m13-lot2p`, `m14-lot1`, `m14-lot2` ; aucune image envoyée.

## 14 h 01 : contrôles et essais J1, J2 (processeur, 2 fils) — [M] `notebooks/m15_mesurer.py`, `out/maladies/jour_1511/kaggle/bilan_m15.json`

- Contrôles : **F1 = 33,94** et **d3b = 32,77** retrouvés avec le code de la veille (`scripts/m14_banc.py`).
- **J1 `d3-moy4`** (moyenne des probabilités des 4 graines) : coût **33,57** (F1 − 0,37) ; Éthiopie 149 / 1 134 malades sans alerte (F1 : 117, + 2,8 points > 2) ; 286 ratées sur les 5 jeux (F1 : 243) ; roamer 194. Temps ≈ 16,4 s (4 × d3b) = 1,61 × F1_bornes. **Non finaliste** (coût, Éthiopie, temps).
- **J2 `MC1-OU-proche (d3-moy4)`** : coût **33,22** (F1 − 0,72) ; 0 malade perdue, 20 rattrapées (223 ratées) ; roamer 224 ; Tanzanie 0 ; 67. Temps composé ≈ 13,9 s = 1,36 × F1_bornes (0,51 × F1 installé). **Non finaliste** (coût, temps contre F1_bornes).
- Lecture : la moyenne des graines retombe sur la moyenne des graines prises une à une (33,95 pour l'élève seul, 33,23 pour MC1-OU-proche, M-piste2) ; d3b (graine 0) était bien un tirage favorable. Le défaut de l'élève sur l'Éthiopie (Xanthomonas) n'est pas du bruit de graine : il est dans la recette.

## 14 h 10 : `m15-soupe` fini ; essais J3, J4 [M] (`bilan_m15.json`, `controle_soupe.json`)

- Carnet : T4 × 2, 7,9 min de calcul (session ≤ 9 min, envoi 14 h 01, COMPLETE avant 14 h 10 m 29 s) : **≈ 0,15 h de GPU**.
- Contrôles : les 8 poids lus par le carnet ont les SHA-256 des fichiers locaux ; d3b relu sur Kaggle = probabilités de `lot2p` à 0,0014 près. Soupes : `modeles/maladies_jour_1511/s4/` (`maladies_m15s4_sans_tdtu.pt` 49cdc09c…, `maladies_m15s4_sans_ethiopie.pt` 53496744…, + `seuils.json` de d3b).
- **J3 `d3-soupe4`** : coût **34,31** (pire que F1) ; Éthiopie 158 ratées (+ 3,6 points) ; PSFD 102 ; 313 ratées sur 5 jeux ; roamer 214. Temps = d3b. **Non finaliste.**
- **J4 `MC1-OU-proche (d3-soupe4)`** : coût **33,41** (F1 − 0,53) ; 0 perdue, 14 rattrapées ; roamer 225 ; temps composé 1,09 × F1_bornes. **Non finaliste** (coût).
- **Bilan J1 à J4 : aucun finaliste.** Moyenner les graines (probabilités ou poids) donne un élève proche de la moyenne des graines, pas de d3b : la soupe est même un peu moins bonne que la moyenne des probabilités. 4 essais.

## 14 h 15 : deuxième lot court, écrit avant calcul : lecteur kNN dans l'encodeur affiné (idée M1 de la veille)

M-banc (journal, 14 h 00) a fait le kNN sur les probabilités de F1 et laisse explicitement « le vrai lecteur kNN (traits de l'encodeur ConvNeXt-Tiny DINOv3) » à M-kaggle. Il reste 1 h 15 et 2,85 h de GPU.

**Traits** (carnet `notebooks/m15_traits_kaggle.py`, `affilecorentin/m15-traits`, sans entraînement) : sortie avant la tête (`forward_head(pre_logits=True)`, 768 nombres, normalisés L2), une vue, **224 px** pour la mémoire comme pour les requêtes, lus par les **soupes s4** (pas de graine choisie), un jeu de traits par pli.
- Mémoire du pli sans x : les images d'apprentissage du pli (mêmes que l'apprentissage de d3b : sans PSFD, sans x), étiquette malade = classe ≠ saine.
- Requêtes : TDTU dans l'espace et la mémoire du pli sans TDTU ; Éthiopie, pli sans Éthiopie ; validation, PSFD, AgroVisionBD, roamer : moyenne des P_kNN des 2 plis (comme la lecture « ensemble livrable »).
- P_kNN(malade) : vote des k plus proches voisins (cosinus), **équilibré** comme M-banc (un voisin malade pèse 1 / nombre de malades en mémoire, un sain 1 / nombre de saines).

**k** ∈ {5, 10, 20} : AUROC moyenne de P_kNN sur validation + TDTU la plus haute (égalité à 0,002 près : le plus grand k). 3 essais.

**Règles** (famille C : un réseau neuf dans le mélange), toutes partent de la réponse de F1 :
- **KD1(s)** : photo « proche » où F1 n'alerte pas → « à vérifier » si P_kNN ≥ s ; s ∈ {0,50 ; 0,70 ; 0,90} (3 essais).
- **KD2(q)** : photo « loin » où F1 répond « à vérifier » → « saine » si P_kNN ≤ q ; q ∈ {0,05 ; 0,10 ; 0,20} (3 essais).
- **KD3** : KD1 au s de plus bas coût + KD2 au q de plus bas coût (1 essai).
- Au plus 3 + 7 = 10 essais. Finaliste : règle 4.3 ; temps composé = F1_bornes + 2 lectures 224 px à 1 vue de ConvNeXt-Tiny sur les photos concernées (≈ 0,13 × d3b par lecture, rapport des pixels et des vues : 224² / 384² / 4 × 2 réseaux ≈ 0,085 × d3b, arrondi vers le haut), estimé et dit comme tel. Entre finalistes : coût le plus bas. Rien d'autre sans l'écrire ici.
- Arrêt : si les traits ne sont pas rapatriés à 15 h 10, la piste est abandonnée.

## 14:58 : piste kNN abandonnée (règle d'arrêt de 14 h 15)

- `m15-traits` envoyé à 14 h 13 ; resté **QUEUED** chez Kaggle (encore à 14 h 58) : les GPU du compte étaient pris par d'autres carnets. Les traits ne pouvaient pas être rapatriés avant 15 h 10 : **piste abandonnée, 0 essai KD**. `notebooks/m15_knn.py` est écrit mais n'a jamais tourné.
- La CLI Kaggle n'a pas de commande pour annuler une session. Je n'ai pas supprimé le carnet. S'il démarre après 15 h 30, il consommera environ 0,2 h de GPU pour rien. Corentin peut l'annuler sur la page Kaggle du carnet. Ses sorties ne seront pas utilisées aujourd'hui.

## Bilan

- Essais comptés : **4** (J1 à J4), plus les contrôles F1 (33,94) et d3b (32,77). **Aucun finaliste.**
- GPU : `m15-soupe` ≈ 0,15 h ; `m15-traits` : 0 h tant qu'il reste en file d'attente.
