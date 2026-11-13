# Récapitulatif de la nuit du 12 au 13 novembre 2026

Ce récapitulatif est écrit par le chef d'orchestre le 13 novembre vers 9 h 25. Les règles avaient été écrites avant tout calcul :
- `docs/plan_nuit_2026-11-12.md` (SHA-256 7b19e221…) ;
- `docs/plan_nuit_10h.md` ;
- `docs/nuit_2026-11-12/regle_gel_finalistes.md` (3 h 56, SHA-256 73017722…), écrite avant toute lecture des juges.

Le déroulé heure par heure est dans `tableau_de_bord.md` et les journaux des agents sont dans ce dossier. **Rien n'est commité ni appliqué dans la chaîne.**

## 1. Résultat en une phrase par module

- **Maladies : F1 adopté par Corentin et appliqué dans la chaîne le 13/11.** C'est un mélange des trois anciens modèles (v10b, soupe, v2) avec une lecture en 4 morceaux, au seuil 0,70. Il passe la règle 4.4 sur les juges, en une seule lecture. Le test vierge AgroVisionBD a été lu une fois, le 13/11 au matin. F1 y rate deux fois moins de malades que la chaîne installée (5 au lieu de 12 sur 716), mais donne plus de fausses alertes (87 au lieu de 51 sur 366, surtout des « à vérifier »). Son coût y est donc plus élevé : 25,87 contre 18,96.
- **Comptage : aucune adoption.** Le v5 au seuil 0,30 reste en service. Le meilleur finaliste, E5p90b, gagne nettement sur les juges en F1 et en erreur de compte. Il échoue de peu sur les fausses détections dans les images sans bananier : 1,12 % pour une limite de 1 %.

## 2. Maladies

### Juges (une lecture, Juge maladies, deuxième avis du Contrôleur sans écart)

| Mesure | Limite (4.4) | F1 | Chaîne installée |
| --- | --- | --- | --- |
| BanSpot, tachées sans alerte | ≤ 12 / 646 | **4** (NKA 0, RDMI 4) | 6 |
| BanSpot, saines en alerte | ≤ 61 / 646 | **56** (NKA 9, RDMI 47), dont 52 « à vérifier » | 61, dont 26 « à vérifier » |
| Cordana du Pérou en alerte | ≥ 97 % | **99,4 %** (502 / 505) | 99,0 % |

Le témoin, c'est-à-dire la chaîne installée, retrouve exactement les chiffres du 11/11. Les deux autres finalistes de la liste gelée, C_quatre_v12a14 et v12a13, n'ont pas été mesurés à cause de la coupure de session de 7 h 45. Ils ne pouvaient de toute façon plus être adoptés : leur coût de réglage est plus élevé que celui de F1.

### Réglage (pour mémoire)

Le coût moyen passe de **49,23 à 35,96**. Les malades sans alerte baissent nettement :

| Jeu | Malades sans alerte, chaîne installée | Malades sans alerte, F1 |
| --- | --- | --- |
| Validation Tanzanie (sur 2 001) | 9 | 0 |
| TDTU | 83 | 19 |
| PSFD | 149 | 102 |
| Éthiopie | 179 | 117 |

### Réserves à garder avec ce chiffre

- **Sur-réglage.** 1 733 essais de M-banc. Le Contrôleur estime l'optimisme à environ 2,7 points sur 13,6 de gain. Le gain disparaît quand on laisse la Tanzanie hors du réglage.
- **Fausses alertes hors Tanzanie.** Elles montent : TDTU passe de 177 à 241 sur 577. Sur BanSpot, la marge sur la limite n'est que de 5 photos. Les « à vérifier » doublent sur les saines (26 → 52).
- **Seuil plutôt que morceaux.** La moitié de l'avance de F1 sur F3 (le même mélange sans morceaux) vient du seuil, pas des morceaux. L'AUC est presque identique.
- **Nom de la maladie.** L'alerte sur la Cordana est bonne, mais elle est dite « Sigatoka » plus souvent : 357 / 505, contre 262.
- **Temps.** Environ 10 s par photo proche, contre 1,8 s : 5,5 fois plus lent. Les photos « loin » passent aussi par le lecteur proche.
- **Biais connus des juges, communs à la référence.**
  - La v10b a été installée par le binôme après lecture de BanSpot.
  - La soupe et la v2 ont appris le jeu péruvien d'où vient la Cordana du Pérou.

### Correctif prêt, non appliqué

Le correctif est décrit dans `out/maladies/nuit_1112/banc/finalistes.md`, section 5 :
- **`config.yaml`** : clés `melange_proche`, `seuil_confiance_melange: 0.70`, `loin_ou_proche: true` et `morceaux_2x2: true`.
- **`fieldscan/modules/maladies.py`** : chargement de la soupe et de la v2, puis mélange géométrique, puis lecture 2 × 2.
- **Code de référence** : `scripts/m12_banc_finalistes.py`, qui redonne les chiffres du réglage.

F3, sans les morceaux, est l'option simple : 3,2 s par photo et coût de réglage 37,83. Elle n'a pas été jugée, parce qu'elle ne faisait pas partie de la liste gelée.

### Adoption appliquée (13/11, vers 12 h 30)

Corentin a choisi « Adopter F1 » après avoir vu les chiffres du test vierge. Les deux fichiers d'origine sont sauvegardés dans `out/adoption_f1/sauvegarde_avant/`.

- **`config.yaml`** : 4 clés nouvelles dans le bloc `maladies` : `melange_proche`, `seuil_confiance_melange: 0.70`, `loin_ou_proche: true` et `morceaux_2x2: true`. Pour revenir à la chaîne du 11/11, il suffit de commenter ces lignes.
- **`fieldscan/modules/maladies.py`** :
  - fonctions `morceaux_2x2`, `lecture_morceaux`, `melange_geometrique`, `decider_melange` et `_executer_melange`, copiées exactement de `scripts/m12_banc_finalistes.py` ;
  - `executer` prend ce chemin si `melange_proche` est donné. Sinon, il garde l'ancien code sans changement.
- **Morceaux 2 × 2** : lus sur toutes les photos dont la réponse vient du lecteur proche, pour que les noms des maladies soient exacts eux aussi. Sur les juges, ils n'étaient lus que là où l'alerte en dépendait.
- **Probabilités affichées** : celles du mélange, sans température, parce que la température 0,79 avait été réglée pour la v10b seule. Les décisions n'en dépendent pas.

Vérifications :
- `scripts/verifier_adoption_f1.py` : **0 réponse différente** entre le code installé et la référence, sur 2 879 jeux de probabilités en cache. Il s'agit des 1 082 photos du test vierge avec trois remplissages des morceaux, et des juges BanSpot et Cordana du Pérou avec des morceaux tirés au hasard. Les morceaux découpés sont identiques octet par octet.
- **Démo complète** (`run.py --images data/demo_feuilles --modules maladies`, 12 photos) :
  - avec F1, elle tourne sans erreur et donne les mêmes réponses que la chaîne du 11/11 sur ces 12 photos ;
  - avec l'ancienne configuration, les sorties sont identiques à celles d'avant la modification (`out/adoption_f1/`).
- **Temps sur la démo** : 175 s pour le module avec F1, contre 42 s avec la chaîne du 11/11 (modèles déjà en cache). Les morceaux prennent 112 s pour 12 photos, soit 9,3 s par photo.

### Test vierge AgroVisionBD : lu une fois, le 13/11 de 9 h 23 à 11 h 44

Corentin a donné son accord vers 9 h 30. Le Juge maladies a lancé `scripts/juge_nuit_m_vierge.py`, avec les SHA-256 identiques à la liste gelée (26 / 26). Le Juge s'est figé à 9 h 46. Son calcul s'est arrêté à 10 h 29, avec 1 024 photos lues sur 1 082 pour la v10b. Le chef d'orchestre l'a relancé à 10 h 46 avec le même script, qui reprend les probabilités sauvées sans rien relire. Aucun résultat n'avait été regardé avant la fin.

Le jeu compte 1 082 photos : 366 saines et 716 malades (179 cercosporiose noire, 289 fusariose, 248 autres). 142 photos sont vues « loin », dont 119 saines.

| Mesure | Chaîne installée | F1 (t = 0,70) | F3 (pour information) |
| --- | --- | --- | --- |
| Malades sans alerte | 12 / 716 | **5** / 716 | 8 / 716 |
| dont cercosporiose / fusariose / autres | 1 / 3 / 8 | 0 / 0 / 5 | 0 / 0 / 8 |
| Saines en alerte | 51 / 366 | **87** / 366 | 79 / 366 |
| dont « à vérifier » | 19 | 66 | 57 |
| Saines en alerte ferme (hors « à vérifier ») | 32 | 21 | 22 |
| Saines vues « loin » en alerte | 20 / 119 | 50 / 119 | 44 / 119 |
| Coût (3 × ratées + fausses alertes, en %) | **18,96** | 25,87 | 24,94 |

Contrôles :
- deuxième avis par le code du Contrôleur (`controle_nuit_m_appliquer.py`) : 0 écart pour les trois chaînes et les deux remplissages ;
- recomptage du chef d'orchestre à partir de `reponses_*.csv` : mêmes chiffres ;
- les morceaux 2 × 2 ont été lus pour les 113 photos dont la décision de F1 en dépendait, il ne reste aucune inconnue.

Ce que ça dit :
- **F1 rate deux fois moins de malades** : 5 au lieu de 12. Il ne rate plus aucune cercosporiose ni fusariose.
- **Il le paie en fausses alertes** : 87 au lieu de 51. L'écart vient des « à vérifier », qui passent de 19 à 66. Les alertes fermes baissent : de 32 à 21.
- **Sur le coût de la règle, F1 fait moins bien que la chaîne installée** : 25,87 contre 18,96. Les 36 fausses alertes de plus pèsent davantage que les 7 malades rattrapées.
- Le surcroît de fausses alertes vient surtout des photos vues de loin : 50 saines « loin » en alerte sur 119, contre 20. C'est cohérent avec la réserve du réglage : les photos « loin » passent aussi par le lecteur proche.
- F3 donne à peu près le même compromis, sans le temps des morceaux.

Rien ne se décide sur ce test : la proposition d'adoption reste celle des juges. Le chiffre est à dire à côté :
- le Bangladesh n'est pas un pays neuf, puisque la v10b l'a appris par BananaLSD ;
- AgroVisionBD n'est neuf que par sa source et sa région (Patuakhali).

Temps mesuré (8 fils, machine seule ; le chargement des modèles est compris) :
- aiguilleur : 0,58 s par photo ;
- v10b : 3,2 à 3,5 s ;
- v2 : 0,88 s ;
- soupe : 0,95 s ;
- morceaux 2 × 2 : 10,7 s par photo lue, sur 10 % des photos.

Soit environ 4,7 s par photo pour la chaîne installée et 6,8 s pour F1.

Fichiers : `out/controle_nuit_1112/juge_m/vierge/` (`bilan_vierge.json`, `reponses_*.csv`, `calcul.log`, `second_avis/`).

### Ce qui a été essayé et ce qu'on en retient

- **M-banc** : 1 733 essais sans entraînement.
  - Ce qui marche : le mélange à trois, et la branche « loin » qui alerte si la v2 **ou** le lecteur proche alerte.
  - Pistes fermées : seuils seuls, températures, lecture 3 × 3, lecture 224 px, seuil de nom.
- **M-entraîneur** : 47 essais sur Kaggle.
  - **v12a13** (v10b réentraînée, PSFD retiré, tirage 50/50 par source, jeux neufs du Bangladesh, morceaux) : coût 41,50, sans régler de seuil.
  - Ce qui compte : **retirer PSFD et équilibrer saines / malades dans chaque source**. Sans cela, le réseau apprend « pays inconnu = malade ».
  - Fermés : v12b (augmentations fortes) et v12c (têtes sur DINOv3 figé).
- **Famille C** : le mélange à quatre avec v12a14 atteint 36,07. Son avance sur F3 est à la limite du bruit.
- **M-analyste** : les malades encore ratées sont des feuilles peu tachées (Sigatoka jaune de PSFD, Xanthomonas d'Éthiopie). PSFD contient 123 copies tournées.

## 3. Comptage

### Juges (une lecture, Juge comptage, deuxième avis sur banano identique au chiffre près)

| Candidat | segmento est | CG mères seules | banano | Moyenne des F1 (seuil 0,5901) | Erreur de compte (seuil 0,382) | Fausses sans bananier (< 1 %) | Règle 3.4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v5 à 0,30 (en service) | 0,677 | 0,315 | 0,808 | 0,600 | 0,382 | 36 / 7 876 (0,46 %) | référence |
| **E5p90b** (aiguillage p90 → v3 + v4) | 0,705 | **0,503** | 0,808 | **0,672** | **0,215** | **88 (1,12 %)** | échoue (fausses) |
| E10_moy_v6e+v5 | 0,716 | 0,146 | 0,808 | 0,556 | 0,391 | 18 (0,23 %) | échoue |
| v6f, graine 0 | 0,709 | 0,141 | 0,803 | 0,551 | 0,403 | 10 (0,13 %) | échoue |

Le témoin est le v5 à 0,30. Il retrouve exactement le protocole v5 sur CG et sur les images sans bananier. Sur banano et segmento, il est à 0,004 près, à cause de l'écart entre l'ONNX sur processeur et le carnet sur GPU.

### Ce que ça dit

- **Les v6 entraînés cette nuit n'apportent rien hors de leur orthomosaïque.**
  - Les 17 essais passent tous la règle « finaliste » grâce à btd_val, qui monte de 0,716 à 0,988. Mais btd_val est l'autre moitié de l'orthomosaïque apprise.
  - Sur les juges, ils perdent le CG, l'agroforesterie (rappel 8 %).
  - C'est un échec propre : la plantation espacée ne s'apprend pas sur une seule orthomosaïque.
- **E5p90b est la vraie piste.**
  - Il ne demande aucun modèle neuf : il aiguille entre les anciens. Quand les pics du v5 sont faibles, il compte avec la moyenne v3 + v4 au seuil 0,20.
  - Il trouve 2 fois plus de pieds mères en agroforesterie (CG : F1 0,315 → 0,503).
  - Il divise presque par 2 l'erreur de compte (0,382 → 0,215).
  - Il échoue parce que l'aiguillage envoie aussi 20 % des tuiles sans bananier (328 / 1 667) vers la branche v3 + v4, qui est plus permissive.
- **La règle ne se change pas après coup.**
  - Tout correctif d'E5p90b (seuil de la branche « petits », condition d'aiguillage) serait réglé en ayant vu les juges.
  - Il demande donc un nouveau protocole, avec un nouveau jeu sans bananier pour le régler et des juges neufs pour le confirmer.
- **C-analyste a montré un risque pour le bulletin, quel que soit le modèle.**
  - Sur des images d'origine à 11 cm/px, le v5 ne trouve plus que 55 % des pieds (F1 dense 0,779 → 0,622).
  - Limite à écrire dans le bulletin : la fiabilité n'est annoncée que vers 5 cm/px.

### Test vierge banana_trees_kp : non lu, encore vierge

Il n'y a pas d'adoption, donc pas de lecture.

### Essais

| Agent | Volume | Contenu |
| --- | --- | --- |
| C-banc | 324 variantes | vues multiples, mélanges, échelles, aiguillages, fenêtres de pics, doublons, compte par intégrale (échec), marge au bord |
| C-entraîneur | 17 essais, environ 6,8 h de GPU | v6a à v6i, ResNet-34, deux têtes, distillation, réglage fin du v5 et interpolations ; la soupe des poids est cassée |
| C-analyste | 3 cycles | — |

## 4. Données de la nuit

- **Comptage**
  - Découpage v6 de banana_tree_detection, géographique avec bande tampon. 16 tuiles aux annotations fausses ont été exclues ; le test du v5 en contenait 4.
  - Jeux neufs : dmpcs2_objets et geostar_tree (apprentissage), banano_finca (information).
  - Test vierge : banana_trees_kp.
- **Maladies**
  - Jeux neufs du Bangladesh (1 405 photos, jeu Kaggle privé `feuilles-nuit-1112`).
  - Test vierge : AgroVisionBD (1 082 photos).
  - ScholarSphere tzzb-zd65 (bunchy top, Xanthomonas) est bloqué par une licence NC et un contrôle anti-robot. Corentin peut le télécharger à la main.
- **Jeux Kaggle privés créés** : `comptage-v6-5cm`, `comptage-v6-maitres`, `comptage-v6-neufs`, `feuilles-nuit-1112`.

## 5. Incidents

- **Coût de référence.** Le plan de 10 h écrivait 45,4. La vraie valeur est **49,23**, corrigée à 0 h 55.
- **Carnet DINOv3.** Un premier envoi du carnet de M-entraîneur lisait la Cordana du Pérou. Il a été refusé avant de tourner, puis corrigé avec un `assert`. Le Contrôleur a vérifié qu'aucun juge n'a été lu.
- **Coupure de session vers 7 h 45.** Les deux Juges ont été arrêtés.
  - Le Juge maladies avait déjà sa décision : F1 passait quel que soit le reste.
  - Le Juge comptage a perdu sa mesure sans bananier avant tout comptage, et l'a refaite à 9 h 15.
  - La limite de 8 h 30 a été dépassée à cause de la coupure, pas par choix. Rien n'a été relu deux fois.
- **Coquille du protocole v10c.** Les effectifs RDMI y sont écrits 511 / 548, ce qui donne 650 au total au lieu de 646. Les comptes, eux, sont justes.

## 6. Ce qui demande ta décision

1. ~~Adopter F1 dans la chaîne~~ : **adopté par Corentin le 13/11 vers 12 h, après lecture du test vierge, puis appliqué.** Voir la section 2, « Adoption appliquée ».
2. ~~Faire lire le test vierge AgroVisionBD~~ : fait le 13/11 de 9 h 23 à 11 h 44, voir la section 2. Il ne décide rien, mais il est à prendre en compte pour la décision 1 : F1 rate moins de malades, mais il donne plus d'« à vérifier » sur les saines vues de loin.
3. **Comptage : ouvrir un protocole « aiguillage v2 »** à partir d'E5p90b. Il faudrait un seuil propre à la branche « petits », réglé sur un jeu sans bananier de réglage, et de nouveaux juges.
4. **Commit** (voir la section 7) : seulement avec ton accord.

## 7. Fichiers

### À commiter, si tu es d'accord

- **Documents**
  - `docs/plan_nuit_2026-11-12.md` et `docs/plan_nuit_10h.md` ;
  - `docs/nuit_2026-11-12/` (tableau de bord, règle de gel, empreintes, 13 journaux, ce récapitulatif) ;
  - `docs/protocole_maladies_v10c_banspot.md` : résultats ajoutés à la section 6 le 12/11 au soir, avant le plan. C'est une modification d'un protocole existant, à valider.
- **Code**
  - **Adoption de F1** : `fieldscan/modules/maladies.py` et `config.yaml`, modifiés avec l'accord de Corentin, plus `scripts/verifier_adoption_f1.py` (neuf).
  - `scripts/` : environ 110 scripts neufs (`v6_*`, `m12_*`, `controle_nuit_*`, `juge_nuit_*`). Aucun script existant n'a été modifié.
  - `notebooks/v6_travail_centres.py`, `notebooks/v6_lanceur_kaggle.py`, `notebooks/m12_entrainer_v12_kaggle.py`, `notebooks/m12_extraire_dinov3_kaggle.py`.
- **Rapports de `out/`**
  - Les fichiers `.md` seulement :
    - `out/comptage_v6/banc/finalistes.md` et `out/comptage_v6/kaggle/finalistes.md`, plus `tableau_essais.md` ;
    - `out/maladies/nuit_1112/banc/finalistes*.md` et `out/maladies/nuit_1112/kaggle/finalistes.md` ;
    - `out/comptage/analyse/rapport_*.md` et `out/maladies/analyse/rapport_cycle2.md` ;
    - `out/controle_nuit_1112/verdicts.md`, `juge_maladies.md` et `juge_comptage.md`.
  - À vérifier avant le commit : comment `.gitignore` traite `out/`.

### À ne pas commiter

- **Trop lourds, ou données téléchargées**
  - Modèles et sorties : `modeles/comptage_v6_essais/` (1,6 Go), `modeles/maladies_v12_essais/` (479 Mo), caches et probabilités de `out/` (environ 7 Go).
  - Données : `data/drone/comptage_v6_5cm/` (2 Go), `data/roboflow_nuit_1112/` (702 Mo), `data/raw/nuit_1112/` (5,4 Go).
- **Toujours exclus**
  - `scripts/__pycache__/` et `notebooks/__pycache__/` ;
  - `CONTEXTE_FIELD_SCAN.md`, `dataverse_fichiers.json`, `modeles/maladies/meilleur_v*.pt`.
