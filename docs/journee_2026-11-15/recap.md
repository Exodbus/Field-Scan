# Récapitulatif de la journée du 15/11 : améliorer tous les modules

Écrit à 15 h 50, après la lecture des juges. Le cadre et les règles ont été écrits avant tout calcul : `docs/plan_journee_2026-11-15.md`, empreinte enregistrée à 13 h 56. Les admissions, la liste gelée et les verdicts sont dans `out/controle_jour_1511/`.

## En bref

| Module | Ce qui a été essayé | Verdict | En service |
| --- | --- | --- | --- |
| Maladies | lecteur kNN, morceaux comptés, graines de d3b moyennées, MC1-OU-proche | **aucune adoption** : MC1-OU-proche échoue sur BanSpot (62 saines en alerte, limite 56) | F1 (F1_bornes toujours en attente de ton accord) |
| Comptage | CC1 moins coûteux, mélanges, c15d (Kaggle, réseau neuf distillé du v5) | **aucune adoption** : CC1 et c15d s'effondrent sur l'agroforesterie CG | v5 au seuil 0,30 |
| Suivi temporel | zones de dégradation par pixel (banc d'anomalies injectées) | **TT1 passe** sur la Côte d'Ivoire, mesurée une seule fois | méthode actuelle, en attendant ta décision |
| Vigueur Sentinel-2, stress | 28 variantes | aucun finaliste | inchangés |
| Vigueur drone | indice VARI (DS1) | échoue sur les sites de mesure | ExG |

GPU Kaggle consommé : environ 0,5 h (m15-soupe 0,15 h, c15-lot1 0,37 h). Le carnet `m15-traits` est resté en file d'attente et doit être annulé à la main.

## 1. Maladies

- **M-banc** (34 essais) : le kNN construit sur les probabilités des trois lecteurs redit F1 (coût 33,94). Les morceaux comptés par seuil font 33,99 au mieux.
- **M-kaggle** (4 essais) : moyenner les 4 graines de d3b ne passe pas la règle (de 33,22 à 34,31). d3b était un tirage favorable. Le kNN sur traits d'image n'a pas tourné, le carnet étant resté en file chez Kaggle.
- **Juge MC1-OU-proche (juges relus)** :
  - BanSpot : 4 / 646 tachées sans alerte et **62 / 646 saines en alerte**, pour une limite de 56 ;
  - Cordana du Pérou : 99,4 % en alerte.
  - Pas une malade de plus que F1 n'est rattrapée.
  - **Il ne passe pas.** L'échec était prévisible : F1 était déjà à 56, pile à la limite.

## 2. Comptage

- **C-banc** (9 essais) : le gain de CC1 ne se garde pas à moindre coût. Le v5 hésite dans 73 à 100 % des blocs d'une bananeraie.
- **C-kaggle** (4 essais, 0,37 h de GPU) : **c15d**, c13h distillé du v5, est un seul réseau robuste à 11 cm/px (0,85 contre 0,60 pour le v5) et coûte 1,7 fois le v5.
- **Juges relus** (règle : F1 moyen ≥ 0,5901 et erreur ≤ 0,382) :

| | segmento est | CG mères | banano | F1 moyen | erreur | sans bananier |
| --- | --- | --- | --- | --- | --- | --- |
| v5 (retrouvé) | 0,677 | 0,315 | 0,808 | 0,600 | 0,382 | 0,46 % |
| CC1_v5h_50 | 0,730 | **0,128** | 0,809 | 0,556 | 0,394 | 0,10 % |
| c15d | 0,724 | **0,047** | 0,802 | 0,524 | 0,425 | 0,09 % |

- **Leçon** : tout ce qui descend de v6f perd l'agroforesterie (CG), même mélangé à 50 % avec le v5. Le gain hors CG (segmento +0,05, beaucoup moins de fausses détections sans bananier) est réel, mais il ne compense pas.

## 3. Vigueur, stress hydrique, suivi temporel (banc d'anomalies injectées)

- Il n'existe aucune référence de terrain : on injecte des anomalies synthétiques connues dans de vraies images. Le banc favorise les méthodes qui collent au modèle d'injection.
- **Suivi temporel, TT1** : zones de dégradation par pixel, comparées à leur parcelle, à la place de l'alerte de parcelle entière.
  - Réglage (Équateur) : 79 % des anomalies détectées, contre 9 % pour la méthode actuelle.
  - **Mesure (Côte d'Ivoire, une lecture)** : 52 % contre 12,5 %, avec 0,39 ha en alerte sur les images sans anomalie, contre 6,0 ha.
  - Correctif prêt, non appliqué : `out/teledetection/jour_1511/correctifs/`.
  - **Point à trancher avant d'installer** : sur la vraie paire d'Équateur, TT1 met 10 parcelles sur 13 en alerte temporelle, contre 1 aujourd'hui. Il faut une surface minimale de zone avant de pénaliser le score d'une parcelle.
- Vigueur Sentinel-2 et stress : tout gain de détection multiplie les fausses alertes par 2 à 15.
- Vigueur drone : DS1 (VARI) échoue sur les sites de mesure (2,5 % de détection, plus de fausses alertes).

## 4. Décisions qui t'attendent

1. ~~F1_bornes~~ : **appliqué le 15/11 vers 16 h avec l'accord de Corentin** (« Oui, applique »).
   - Modifications :
     - `fieldscan/modules/maladies.py` : nouvelles fonctions `_melange_bornes`, `_lire_morceaux`, `_sorties_melange` ;
     - `config.yaml` : `morceaux_bornes: true`, et `false` pour revenir à la lecture complète.
   - Contrôle sur les caches des 5 jeux de réglage, avec `scripts/verifier_f1_bornes.py` :
     - **0 alerte différente de F1 sur 7 746 photos** ;
     - 60 noms différents (0,8 %) ;
     - morceaux lus sur 832 photos au lieu de 7 070.
   - Contrôle sur les 12 photos de `data/demo_feuilles` : mêmes réponses dans les deux cas ; 128 s au lieu de 279 s.
2. **TT1** pour le suivi temporel : appliquer le correctif et choisir une surface minimale par parcelle pour le bulletin.
3. **Carnet Kaggle `m15-traits`** à annuler sur sa page.
4. **Commit** : rien n'est commité. Les `.pt` et `.onnx` des dossiers du jour (`modeles/*_jour_1511/`) ne sont pas exclus par `.gitignore`.

## 5. En cours

- Visiteur web de la parcelle (`out/visite_parcelle/`) : l'agent construit la page three.js. Je la vérifierai dans le navigateur avant de te l'envoyer.

## 6. Second tour Kaggle (16 h – 18 h 20) : aucun finaliste

Le cadre est `avenant_tour2_kaggle.md`, écrit avant tout calcul. Comme il n'y a aucun finaliste, aucun juge n'a été relu.

**Maladies (M-kaggle2, 19 essais, 0,3 h de GPU)**
- Lecteur kNN sur les traits d'image : il redit F1 à 0,05 près.
- Tête logistique sur ces traits : même constat.
- Adaptation TENT : le réseau s'effondre vers « saine » (636 malades ratées en Éthiopie au lieu de 158).
- Meilleur essai : 33,69, contre 33,94 pour F1 et une limite de 32,94.
- **Constat** : le Xanthomonas n'existe que dans le jeu éthiopien. Une validation par pays ne peut donc pas l'apprendre. Il faudrait des photos d'un autre pays (téléchargement à demander).

**Comptage (C-kaggle2, 4 essais, 1,15 h de GPU)**
- Quatre réseaux partent du v5 et apprennent à l'imiter, de plus en plus fort selon la recette. Ils deviennent robustes à 11 cm/px (0,85, contre 0,60 pour le v5).
- Ils échouent pourtant tous sur trois points :
  - MM : 0,814 à 0,826, pour une limite de 0,837 ;
  - les 4 anciennes : au plus 0,848, pour une limite de 0,8539 ;
  - le contrôle ReforesTree : 88 à 93 %, pour une limite de 95 %.
- Le contrôle ReforesTree aurait écarté c15d (86,6 %), celui qui s'est effondré sur CG. Il est donc utile pour la suite.
- Le lot 2 est resté en file chez Kaggle et a été abandonné. Le carnet `c15b-lot2` n'est pas supprimé.

**Bilan de la journée** : le seul gain confirmé reste TT1 (suivi temporel). Pour les maladies comme pour le comptage, les pistes accessibles sans données neuves sont épuisées. La suite utile passe par :
- un jeu de test neuf ;
- des photos de Xanthomonas venant d'un autre pays ;
- un jeu de réglage qui ressemble à CG (bananiers cachés sous d'autres arbres).

## 7. TT1 appliqué (15/11, vers 18 h 45, accord de Corentin : « oui ca me parait bien »)

**Fichiers modifiés**
- `fieldscan/modules/temporel.py` : correctif TT1 de l'agent Télédétection.
- `fieldscan/bulletin.py` : les zones temporelles dont la surface totale est inférieure à `temporel.surface_min_penalite_ha` restent affichées, mais ne pénalisent pas le score. Une phrase l'explique dans le bulletin.
- `config.yaml` : `zones_temporel: parcelle` et `surface_min_penalite_ha: 0.5`.
- `README.md` : ligne du suivi temporel.

**Contrôle sur les deux sites, avec `run.py --modules vigueur stress temporel`**

| Site | Avant | Avec TT1 et le seuil de 0,5 ha |
| --- | --- | --- |
| Équateur | 1 parcelle pénalisée (P06), passée en orange | 11 zones de dégradation dans 10 parcelles, toutes sous 0,5 ha, donc sans pénalité ; 13 parcelles en vert |
| Côte d'Ivoire | 2 parcelles pénalisées | 2 zones sans pénalité ; une parcelle repasse d'orange à vert |

**Non-régression** : le module maladies tourne toujours. Avec `zones_temporel: null`, on retrouve le module d'avant.
