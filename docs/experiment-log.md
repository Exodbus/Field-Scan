# Journal des expériences et des décisions : comptage mathématique

**Rédacteur unique** : experiment-engineer. Le chef d'orchestre n'y écrit que lorsque experiment-engineer n'est pas actif (`docs/team-structure.md`, section 3).

**Ordre** : les entrées sont ajoutées à la suite, jamais réécrites. Une correction se fait par une nouvelle entrée qui renvoie à l'ancienne.

## Identifiants

| Préfixe | Objet | Où |
| --- | --- | --- |
| H1 à H8 | hypothèses | `docs/research-brief.md`, section 3 |
| E-NNN | expérience | ce journal ; configuration dans `experiences/comptage_math/E-NNN.yaml` ; sorties dans `out/comptage_math/experiences/E-NNN/` |
| D-NNN | décision | ce journal |
| C-NNN | concertation | `docs/recherche/concertations/C-NNN.md` |

## Gabarit d'une expérience

La partie « avant » est remplie et datée **avant** le lancement. La partie « après » ne la modifie jamais.

```
### E-NNN — titre court
Avant (date) :
- Hypothèse : H… ; responsable : … ; demandée par : … (C-NNN éventuelle)
- Données : développement | validation — liste ou identifiant de jeu (aucune image du test)
- Configuration : experiences/comptage_math/E-NNN.yaml ; empreinte : …
- Mesure : … ; contrôle : … ; critère qui confirme : … ; critère qui réfute : … (fixés avec independent-evaluator)
- Nombre de variantes déjà essayées sur ces données pour cette question : …
Après (date) :
- Commit et état du dépôt : … ; commande : … ; durée, mémoire : …
- Résultat [M] : …
- Conclusion : confirmée | réfutée | non concluante (pourquoi)
- Décision liée : D-NNN
```

## Gabarit d'une décision

```
### D-NNN — titre court (date)
- Décision : …
- Prise par : chef d'orchestre | responsable d'équipe | Corentin ; à la suite de : E-NNN, C-NNN
- Raison : … (faits [O], sources [S], mesures [M])
- Ce qui la remettrait en cause : …
```

## Journal

### D-001 — Mise en place de l'équipe de recherche (7 novembre 2026)

- **Décision.** Les éléments suivants sont créés :
  - les 18 profils de sous-agents dans `.claude/agents/` ;
  - `CLAUDE.md` ;
  - `docs/team-structure.md`, `docs/research-brief.md`, `docs/communication-protocol.md` et ce journal.

  Aucun code, aucune donnée et aucune configuration existants ne sont modifiés.
- **Prise par :** chef d'orchestre, à la demande de Corentin.
- **Raison.** Construire une méthode mathématique de comptage des plants principaux à partir des indices d'une présentation orale (gaussiennes, formes, couleurs, stries, orientations), dont la fonction originale est inconnue.
- **Ce qui la remettrait en cause.** Une demande de Corentin, ou une limite de Claude Code constatée à l'usage, par exemple des profils non chargés.

**Expériences lancées : aucune. Score annoncé : aucun.**

## Points ouverts avant la première expérience

1. Choix du test final : options A, B ou C de `docs/research-brief.md`, section 5. Décision de Corentin, commitée avant toute expérience.
2. Découpage développement / validation proposé par annotation-manager, à valider par Corentin.
3. Frontière de la « méthode mathématique » : réglage de paramètres, classifieur simple, usage du v5 (`docs/research-brief.md`, section 4).
4. Notes ou support de la présentation de Philemon, s'ils existent.

### D-002 — Lancement de la vague 0 réduite et mode de lancement des agents (7 novembre 2026)

- **Décision.**
  - Quatre missions parallèles au plus au démarrage (consigne de Corentin, plus stricte que les six de `CLAUDE.md`) : M1 image-analyst (images et résolution), M2 scientific-researcher (bibliographie), M3 leaf-mathematician (deux modèles de feuille et de centre), M4 scientific-challenger (hypothèses fragiles).
  - Les profils de `.claude/agents/` **ne sont pas chargés comme types d'agents** dans la session en cours (ouverte dans le dossier parent). Chaque agent est lancé comme sous-agent `general-purpose` réel, avec l'ordre de lire et d'appliquer son profil, ses outils et sa zone d'écriture. Ce n'est pas une simulation, mais la restriction d'outils du profil n'est garantie que par le brief.
  - Les propositions mathématiques de M3 seront examinées par orientation-engineer (vision) et scientific-challenger ; les objections seront renvoyées à leaf-mathematician.
  - Zones d'écriture vérifiées sans recoupement : notes et sorties propres à chaque agent, `docs/recherche/bibliographie.md`, `docs/recherche/modele_feuille.md`, `comptage_math/feuille.py`.
  - Toutes les images des groupes `test` et `exclu` du découpage v5 sont scellées pour ces missions, le test final n'étant pas encore choisi.
- **Prise par :** chef d'orchestre, à la demande de Corentin.
- **Raison.** Avancer le cadrage sans expérience ni score, en attendant la décision de Corentin sur le test final.
- **Ce qui la remettrait en cause.** Redémarrage de la session dans `Field-Scan` (profils alors chargés nativement) ; demande de Corentin.

### D-003 — Objectif recentré sur la plantation dense (7 novembre 2026)

- **Décision.** Corentin fixe l'objectif : battre le détecteur appris v5 et la baseline explicite en plantation dense ou industrielle, mères seulement. Les rejets sont laissés de côté pour l'instant. La boucle d'expériences continue jusqu'à ce que l'objectif soit atteint ou que la règle d'arrêt d'independent-evaluator s'applique.
- **Points non tranchés par Corentin, voie prudente retenue en attendant sa réponse :**
  - **Commits.** Aucun. Les règles sont écrites et datées dans les fichiers avant chaque mesure, et le commit attend son accord.
  - **Test final.** Il reste scellé (banano, segmento est, etc.) et n'est pas encore choisi.
- **Mise en œuvre.** independent-evaluator écrit avant toute mesure :
  - le code d'évaluation commun ;
  - la référence E-001 (v5 et baseline, mesurés avec le même code) ;
  - le découpage de `bv_b_val` en `val_iter` et `val_scellee` ;
  - le critère de victoire et le plafond de variantes.
- **Ce qui la remettrait en cause.** Une réponse de Corentin sur le test final, les commits ou l'arrêt.

### E-002 — Contrôle synthétique des modèles A et B (leaf-mathematician, 7 novembre 2026)
- Avant : le critère est écrit dans `docs/recherche/notes/leaf-mathematician.md` avant le lancement. Données synthétiques seulement, graine 20261107.
- Après :
  - Commande : `out/comptage_math/leaf-mathematician/controle_synthetique.py`.
  - Résultat [M] : `resultats.md`.
    - A, plants isolés : rappel 0,94 à 1,00, précision 0,22 à 0,26.
    - A, plants jointifs : rappel 0,73 à 0,82, précision 0,46 à 0,53.
    - B : rappel 0.
  - Conclusion : critère manqué pour A (précision) et pour B.
  - Portée limitée par OBJ-C1 : le rendu et le filtre ont la même forme. E-002 vaut test de non-régression du code, pas appui au modèle.

### E-003 — Alignement radial des orientations sur banavista, développement (orientation-engineer, 7 novembre 2026)
- Avant : la règle de lecture (écart réel − demi-maille, au-delà de 3 écarts-types de la demi-maille) est écrite dans le script avant le lancement.
- Données : DJI_0557, DJI_0642, DJI_0646 (bv_session_a) et DJI_0800, DJI_0804 (bv_b_train). Une assertion du script exclut validation et test.
- Après :
  - Commande : `out/comptage_math/orientation-engineer/mesure_alignement.py`.
  - Résultat [M] dans l'anneau de 0,4 à 1,5 m : T_feuille s = −0,245 (demi-maille −0,018, 5 images négatives sur 5) ; Gabor 6 cm s = −0,04. Valeurs identiques à 1,1 et à 2 cm/px.
  - Conclusion : **non concluante de peu** (écart 0,226 contre un seuil de 0,235). Le signal vient des axes linéaires à l'échelle de la feuille, pas des stries.

### E-004 — Décomposition synthétique du signe de B (orientation-engineer, 7 novembre 2026)
- Résultat [M] : `decomposition_synthetique_B.json`. Les stries donnent s > 0, la nervure et les bords s < 0, et ils se compensent dans un même tenseur (OBJ-V1, OBJ-V2).

### E-005 — Rendus synthétiques hors famille (OBJ-C1) (leaf-mathematician, 7 novembre 2026)
- Avant : critère écrit dans `docs/recherche/notes/leaf-mathematician.md` ; graine 20261108, 2 cm/px, 100 plants ; détecteurs inchangés.
- Après :
  - Commande : `out/comptage_math/leaf-mathematician/controle_hors_famille.py`.
  - Résultat [M] : `resultats_hors_famille.json`, rappel au budget à 0,5 m.
    - A : 0,48 (centre marqué), 0,47 (centre non marqué), 0,46 (vide sombre au centre), 0,18 (limbes de 1,6 à 2,5 m).
    - A-iso : 0,05 à 0,11.
  - Conclusion : **circularité confirmée**. E-002 n'appuie pas A. C'est le désaccord d'échelle qui casse A, pas l'absence de marquage du centre. 37 à 54 % des fausses détections tombent entre deux voisins.

### D-004 — Issue de la concertation C-001 : contenu du cycle 1 (7 novembre 2026)
- **Décision.**
  - Une seule candidate au cycle 1 : **A′**, définie et pré-enregistrée dans `docs/recherche/modele_feuille.md` § 8. Elle comprend :
    - un seuil robuste par la MAD, calculé par image ;
    - une grille réglée sur le seul développement dense, qui porte sur le canal (ExG ou luminance), l'échelle, le rayon de suppression et z0 ;
    - un témoin obligatoire, A-iso ;
    - quatre conditions d'envoi sur `val_iter`, vérifiées sur le développement.
  - B′ (vote des axes linéaires, signe −1, tronqué) est reporté au cycle 2, avec les contrôles d'OBJ-C5 et d'OBJ-C6. Les stries (B″) sont écartées pour le dense tant que E-003 n'est pas renversée.
- **Prise par :** chef d'orchestre, sur l'accord des deux examinateurs et de l'auteur.
- **Désaccords maintenus.**
  - leaf-mathematician contre orientation-engineer sur le canal (ExG ou luminance). Tranché par la grille.
  - leaf-mathematician contre scientific-challenger sur le statut de B′. Sans effet sur le cycle 1.
- **Questions en attente**, toutes deux bloquantes pour l'envoi :
  - liste des photos de pépinière à retirer de `bv_session_a` (annotation-manager) ;
  - statut des hyperparamètres de la grille par rapport au plafond de variantes (independent-evaluator).
- **Ce qui la remettrait en cause.** Échec des conditions d'envoi sur le développement, ou E-001 qui montre que la baseline est déjà au niveau du v5.

### E-001 — Référence en dense : v5 et baseline ExG, avec le même code (independent-evaluator, 7 novembre 2026)
- **Avant.** Découpage, critère de victoire et plafond de variantes sont écrits dans `docs/recherche/test_final.md` (sections 1 à 3), avant toute mesure.
  - `val_iter` : L3-L4, soit DJI_0904 à 0945.
  - `val_scellee` : L1-L2, soit DJI_0862 à 0903.
  - Empreinte du découpage : `out/comptage_math/evaluation/decoupage_bv_b_val.csv`.
- **Après.** Évaluation `scripts/math_evaluer.py` ; résultats [M] dans `out/comptage_math/evaluation/E-001/`, relus par le chef d'orchestre. F1 sur les mères seules, appariement à 1 m :

  | Jeu | v5 au seuil 0,30 | Baseline ExG |
  | --- | --- | --- |
  | `val_iter` | **0,719** [0,703 ; 0,735] (P 0,612, R 0,871) | 0,405 |
  | `dev_reglage` | 0,824 | 0,554 |

  - `dev_reglage` = bv_session_a sans pépinière + bv_b_train. Le v5 y est mesuré sur ses propres données d'entraînement, pour information seulement.
  - À budget égal (k = N_réf) sur `val_iter` : v5 0,732, baseline 0,298.
  - Niveau nul de la demi-maille : 0,08 à 0,10.
- **Contrôle de reproductibilité.** dji_0544 : 0,8926 (identique au protocole v5). pp_100_metros : 0,8830, contre 0,8846 au protocole.
- **Point ouvert.** Sur `val_iter`, le v5 détecte 42 % de plants de plus que les références. Les références sont peut-être incomplètes ; à contrôler par annotation-manager.

### D-005 — Règle de sélection du cycle 1 (7 novembre 2026)
- **Décision.** La grille de A′ est sélectionnée sur le **F1 cumulé de `dev_reglage`**, comme le demande independent-evaluator dans `test_final.md` § 3.1. La moyenne des F1 des 5 groupes, proposée au § 8.3 par leaf-mathematician, n'est pas retenue.
  - `dev_transfert` (lasuiza dédoublonné, vols_100_022x, corte) est rapporté, mais ne sert à choisir aucun réglage.
- **Prise par :** chef d'orchestre, qui arbitre un désaccord entre équipes.
- **Raison.** Les références de lasuiza et de vols_100_022x sont incomplètes ([O] annotation-manager : ratio médian 0,56 sur lasuiza, 205 unités suspectes en tout). Les règles de mesure appartiennent à l'évaluation.
- **Ce qui la remettrait en cause.** Une planche montrant que les unités suspectes sont de la végétation non bananière.

### Constat du 7 novembre 2026 : références incomplètes sur `val_iter` (annotation-manager, vérifié par le chef d'orchestre)
- **Constat [O].** Ratio des références à la surface végétale : médiane 0,53 sur `val_iter`, contre 1,11 sur `dev_reglage`.
  - 36 photos sur 42 sont sous le 10e centile de `dev_reglage`.
  - Contrôle visuel sur `zoom_val_iter_0905_0909.png` : sur DJI_0909, des rosettes nettes n'ont aucune référence.
  - Sources : `docs/recherche/conventions_comptage.md` § 5 et `out/comptage_math/annotation-manager/completude_val_iter.csv`.
- **Conséquences.**
  - Le F1 de 0,719 du v5 sur `val_iter` (E-001) sous-estime sa précision et surestime son rappel. Il ne peut pas servir de critère de victoire en l'état.
  - `val_scellee`, issue de la même mission, est probablement touchée aussi. Elle n'a pas été examinée.
- **Mesure conservatoire du chef d'orchestre.** La grille du cycle 1 est restreinte à bv_session_a sans pépinière, pour garder bv_b_train vierge en vue d'une nouvelle validation.
- **Décision demandée à Corentin.** Redéfinir la validation dense ; c'est un découpage, donc de son ressort.

### E-006 — Cycle 1 : grille A′ et témoin A-iso sur le développement dense (leaf-mathematician, 7 novembre 2026)
- **Avant.** Grille et règles pré-enregistrées dans `docs/recherche/modele_feuille.md` § 8. Les amendements 1 et 2 du § 8.3 sont écrits avant tout calcul :
  - la sélection se fait sur le F1 cumulé de bv_session_a sans pépinière ;
  - bv_b_train est exclu par assertion. Aucune donnée ni aucun score n'en ont été lus.
- **Après.**
  - Commande : `out/comptage_math/leaf-mathematician/cycle1_grille.py`. Empreintes dans les notes de l'auteur. Durée : 1 364 s sur 8 cœurs.
  - Résultat [M] dans `out/comptage_math/leaf-mathematician/E-006/bilan_E-006.json`, relu par le chef d'orchestre. Configuration retenue pour A′ : luminance, échelle 1,25, rayon de suppression 1,0 m.

    | Méthode | F1 sur bv_session_a | F1 sur dev_transfert |
    | --- | --- | --- |
    | A′ | 0,541 | 0,355 |
    | A-iso | 0,423 | 0,267 |
    | v5, pour information (E-001, entraîné sur ces photos) | 0,821 | 0,876 |

  - Niveaux nuls : demi-maille 0,109, végétation uniforme 0,331.
  - Temps : environ 1,7 s par hectare sur 8 cœurs.
  - Conditions d'envoi : 3 passent sur 5. Échecs :
    - centres contre milieux de voisins, sur vols (0,561 contre 0,732) ;
    - rotation (0,349 sur image tournée, contre 0,109 pour la demi-maille).
- **Conclusion.** A′ n'est pas envoyé sur `val_iter` : aucune variante consommée. Écart avec le v5 sur le développement : environ −0,28 de F1.
- **Désaccord ouvert.** La règle de rotation compare à la demi-maille et non au nul « végétation uniforme ». À trancher avant le cycle 2 seulement (C-002).

### Constat du 7 novembre 2026 : complétude de `val_scellee` et de `bv_b_train` (annotation-manager)
- **Règles.** Écrites avant le calcul dans `test_final.md` § 6. Le calcul porte sur les références et l'ExG seulement : aucune détection, aucune image produite.
- **`val_scellee`** : 40 photos conformes sur 42, ratio médian 1,07. Verdict : **utilisable**.
  - Photos retirées : DJI_0867 et DJI_0903.
- **`bv_b_train`** : 67 photos conformes sur 71, ratio médian 1,12.
  - Photos sous 0,83 : DJI_0795, DJI_0796, DJI_0832 et DJI_0834.
- **Conséquence.** L'option 1b d'independent-evaluator est praticable : `bv_b_train` sert aux cycles et `val_scellee` à la confirmation. Le choix entre 1a et 1b revient à Corentin.

### E-007 — Cycle 2 : termes de polarité de A″ (leaf-mathematician, 7 novembre 2026)
- **Avant.** Pré-enregistrement dans `docs/recherche/modele_feuille.md` § 9.
  - Grille : β (anisotropie angulaire) ∈ {0 ; 1} × w_trou (vide central sombre) ∈ {0 ; 0,5 ; 1}.
  - Données : bv_session_a sans pépinière. bv_b_train et bv_b_val sont exclus par assertion.
- **Après.**
  - Commandes : `out/comptage_math/leaf-mathematician/cycle2_polarite.py` et `regle_rotation_e007.py`. Bilan dans `E-007/`.
  - Résultat [M], F1 sur bv_session_a :

    | β \ w_trou | 0 | 0,5 | 1 |
    | --- | --- | --- | --- |
    | 0 | 0,541 | 0,500 | 0,439 |
    | 1 | 0,535 | 0,498 | 0,440 |

    La grille retient (0, 0), c'est-à-dire A′.
  - Contrôles :
    - centres contre milieux sur vols : échoue toujours ;
    - rotation, selon l'amendement 2 : passe (excès −0,040).
- **Conclusion.** **Polarité réfutée.** En canopée dense, le milieu entre deux voisins est plus sombre que le centre. Rien n'est envoyé : la configuration est identique à A′ (§ 4.1) et la condition centres contre milieux échoue.
- **Pistes suivantes.**
  - Fusion de A′ avec le vote B′ (E-008, convergence-engineer, en cours).
  - A priori de maille ou de rangées (plant-geometry).

### E-008 — Vote des axes linéaires B′ et fusion avec A′ (convergence-engineer, 7 novembre 2026)
- **Avant.** Pré-enregistrement dans `docs/recherche/notes/convergence-engineer.md` § 1.
  - Réglage sur bv_session_a sans pépinière.
  - Assertions contre bv_b_train, bv_b_val et les groupes interdits.
- **Étape 0 (résolution).** Sur 10 tuiles préparées à 3,6–5,7 cm/px, l'écart d'alignement réel − demi-maille vaut −0,20 (10 négatifs sur 10). Le signal survit à la résolution préparée.
- **Après.**
  - Commande : `out/comptage_math/convergence-engineer/e008_votes.py` (1 104 s sur 8 cœurs).
  - Résultat [M] dans `E-008/bilan_E-008.json`, relu par le chef d'orchestre. Configuration du vote : r_max 1,6 m (bord de la grille), p = 1, R_nms 1,0 m.

    | Méthode | F1 bv_session_a | F1 dev_transfert |
    | --- | --- | --- |
    | Vote B′ seul | **0,637** [0,624 ; 0,649] | **0,546** |
    | A′ (E-006) | 0,541 | 0,355 |
    | Fusion A′ + vote, w = 2 (bord) | 0,638 | 0,533 |

  - Contrôles :
    - orientations mélangées : 0,335 ;
    - végétation uniforme : 0,331 ;
    - demi-maille : 0,109 ;
    - OBJ-C3 (centres contre milieux de voisins) passe, y compris sur vols (1,41 contre 0,36) ;
    - double comptage : 0,051.
  - Temps : environ 0,5 s par hectare sur 8 cœurs.
- **Conclusion.** Le vote des axes linéaires est **le premier modèle explicite nettement au-dessus de la baseline et de A′**. A′ n'ajoute rien de mesurable au vote. L'écart au v5 reste d'environ −0,18 sur bv_session_a, où le v5 a été entraîné.

### D-006 — Candidate principale du cycle 3 : le vote B′ (7 novembre 2026)
- **Décision.**
  - Le vote des axes linéaires devient la candidate principale ; A′ devient un témoin.
  - Cycle 3, sur le développement :
    - grille d'extension r_max ∈ {1,6 ; 2,0 ; 2,4} m et σ_t multi-échelle, pré-enregistrée ;
    - mesure de la règle de rotation (amendement 2) ;
    - a priori géométrique sur les candidats du vote (E-009, plant-geometry).
- **Prise par :** chef d'orchestre, sur proposition de convergence-engineer. Le désaccord avec leaf-mathematician sur le rôle de A′ est tranché par E-008.
- **Ce qui la remettrait en cause.** L'échec du vote à la règle de rotation, ou une perte du signal sur la validation dense.

### E-009 et E-009b — A priori de répulsion (Strauss, solution exacte par MILP) sur A′ et sur le vote (plant-geometry, 7 novembre 2026)
- **Avant.** Pré-enregistrement dans `docs/recherche/notes/plant-geometry.md`. Grille de 27 configurations, sélection sur bv_session_a sans pépinière.
- **Après [M].**
  - E-009 : A′ 0,5408 → 0,5412 avec la répulsion ; différence appariée +0,0004, IC [−0,0009 ; +0,0018].
  - E-009b : vote 0,6368 → 0,6364 ; différence −0,0003, IC [−0,0013 ; +0,0007].
  - Avec la répulsion, A′ échoue toujours au test centres contre milieux sur vols, et le vote le passe toujours.
  - Les deux passent la règle de rotation. Le vote seul aussi (excès −0,039).
- **Conclusion.** **La répulsion est réfutée comme levier de F1.** Elle fait double emploi avec la suppression des non-maxima à 1,0 m. Le gain restant est à chercher dans les faux négatifs : le rappel du vote est de 0,64.

### E-010 — Extension du vote (r_max, multi-échelle), rotation et attributs (convergence-engineer, 7 novembre 2026)
- **Avant.** Pré-enregistrement dans `docs/recherche/notes/convergence-engineer.md` § 3.
- **Après [M].**
  - Commande : `out/comptage_math/convergence-engineer/e010_extension.py`. Résultats dans `E-010/bilan_E-010.json`.
  - Grille sur bv_session_a :
    - r_max 1,6 m : 0,6368 ; 2,0 m : 0,6304 ; 2,4 m : 0,6180 ;
    - multi-échelle : au mieux +0,0003.
  - Configuration retenue : **la même qu'en E-008**.
  - Règle de rotation (amendement 2) : **remplie**, excès −0,039 [−0,050 ; −0,027].
  - Autres contrôles :
    - double comptage : 0,051 ;
    - OBJ-C3 passe ;
    - dev_transfert : 0,546.
  - Les attributs des candidats séparent faiblement vrais et faux positifs (AUC de 0,55 à 0,67).
- **Conclusion.** Le vote B′ est figé dans sa configuration d'E-008. Toutes les conditions d'envoi mesurées sur le développement sont remplies ; il reste à fixer la validation dense (décision de Corentin).

### E-011 — Analyse des erreurs du vote sur bv_session_a (error-analyst, 7 novembre 2026)
- **Avant.** Règles de classement écrites dans `docs/recherche/notes/error-analyst.md` § 1, avant le calcul.
- **Après [M].**
  - Commande : `scripts/math_erreurs.py`. Résultats dans `out/comptage_math/error-analyst/E-011/`.
  - Le calcul reproduit les chiffres connus : F1 du vote 0,6368.
  - **Oubliés** (3 086) :

    | Situation près de la mère | Part |
    | --- | --- |
    | Aucun candidat à moins de 1 m | 39,9 % |
    | Candidat sous le seuil | 36,6 % |
    | Bord de tuile | 22,1 % |
    | Couronnes jointives | 1,5 % |

    - Taux d'oubli selon la taille de la couronne : 0,647 sous 2 m, 0,289 au-delà de 3,6 m. Pour le v5 : 0,480 et 0,087.
    - 22 à 37 % des oubliés ont une fausse détection retenue à 1–2 m. Le pic est donc mal placé, sans direction privilégiée.
  - **Fausses détections** (3 261) :

    | Classe | Part |
    | --- | --- |
    | Autre végétal | 38,7 % |
    | Feuille isolée près d'une mère oubliée | 25,2 % |
    | Doublon | 19,0 % |
    | Milieu de deux mères | 6,7 % |
    | Sol | 3,8 % |

  - **Maille locale** : borne haute de récupération de 4,5 %, et le F1 baisse sans réglage (0,628). Piste écartée.
- **Leviers retenus.**
  - Recentrage du pic, borne arithmétique F1 ≈ 0,716 (E-012, convergence-engineer).
  - Filtre couleur et texture contre l'autre végétal et le sol (E-013, vegetation-color-engineer).
  - Grandes couronnes : échelle du noyau.

### E-013 — Descripteurs de couleur et de texture contre les fausses détections du vote (vegetation-color-engineer, 7 novembre 2026)
- **Avant.** Pré-enregistrement dans `docs/recherche/notes/vegetation-color-engineer.md` § 1.
- **Après [M].**
  - Commandes : `out/comptage_math/vegetation-color-engineer/e013_couleur.py` et `e013_complement.py`. Résultats dans `E-013/bilan_E-013.json`.
  - Aucun descripteur ne sépare l'« autre végétal » au-delà d'une AUC de 0,65. La teinte Lab (d2) a le sens contraire de la prédiction, et le limbe large (d1) est confondu avec l'herbe rase à 5 cm/px.
  - La combinaison retenue est vote + 0,25 × (fraction non végétale d̃3), au seuil 1,86.

    | Jeu | Vote seul | Vote + 0,25 × d̃3 | Gain apparié |
    | --- | --- | --- | --- |
    | bv_session_a | 0,637 | **0,652** | +0,015 [+0,007 ; +0,023] |
    | dev_transfert | 0,546 | 0,570 | +0,025 |

  - Effets secondaires : double comptage de 0,051 à 0,064 ; le surcomptage sur bv_session_a passe de +2 % à +11 %.
- **Conclusion.** Gain faible mais significatif, et confirmé sur dev_transfert. La couleur et la texture fine sont **réfutées contre l'autre végétal** à 3,6–5,7 cm/px. Le gain vient surtout du rappel : le seuil peut baisser sans laisser passer le sol.
- **Réserve.** Le choix a été fait parmi 17 configurations sur les mêmes données. Revue de scientific-challenger demandée, avec un témoin « rejet dur d3 ».

### E-012 — Recentrage du pic et noyau adaptatif (convergence-engineer, 7 novembre 2026)
- **Avant.** Pré-enregistrement dans `docs/recherche/notes/convergence-engineer.md` § 5.
- **Après [M].**
  - Commande : `out/comptage_math/convergence-engineer/e012_recentrage.py`. Résultats dans `E-012/bilan_E-012.json`.
  - Les 15 configurations restent à moins de 0,01 de la base (0,637). La meilleure, Kfus avec moindres carrés et suppression des non-maxima, fait 0,640, avec un IC du gain de [−0,003 ; +0,010].
  - Le recentrage ne déplace le pic que de 0,10 à 0,15 m.
- **Conclusion.** **Négatif.** La base d'E-008 est maintenue. Les candidats situés à environ 1,3 m des mères oubliées sont probablement des maxima distincts, pas des flancs. La borne de 0,716 d'E-011 n'est pas atteignable par un recentrage local.
- **État du développement après E-013.** Meilleure méthode : vote + 0,25 × d̃3 (E-013), F1 0,652 sur bv_session_a et 0,570 sur dev_transfert.

### Correction (7 novembre 2026, chef d'orchestre) : bv_b_train n'est pas vierge
- J'ai écrit plus haut que « personne n'a ouvert bv_b_train ». C'est **inexact**. E-003 (orientation-engineer) a mesuré l'alignement des orientations sur DJI_0800 et DJI_0804, deux photos de bv_b_train, sans aucun score de détection. Cette mesure a orienté l'équipe vers le vote B′. E-001 a aussi mesuré le v5 et la baseline en agrégat sur dev_reglage, qui contient bv_b_train.
- Relevé par scientific-challenger (audit, AF1). Pour l'option 1b, Corentin doit décider s'il faut déclarer ces deux photos ou les retirer de `val_iter_v2` (T10).

### D-007 — Issue de l'audit des cycles 1 à 4 (7 novembre 2026)
- **Décision.**
  - La **seule candidate** à envoyer en validation est **le vote B′ seul**, dans la configuration figée d'E-008/E-010.
  - vote + d̃3 (E-013) n'est pas retenu. Raisons : gain du même ordre que l'optimisme de sélection, mécanisme inverse sur dev_transfert, erreur de comptage qui passe de +2 % à +10,7 %. Il ne sera réintroduit que si les témoins T1, T5 et T6 lui sont favorables.
  - Témoins à mesurer sur le développement avant tout envoi. Aucun ne consomme de variante.
    - **T3** : baseline réglée sur bv_session_a. Si le vote ne la bat pas, il n'y a pas d'envoi.
    - **T5** : comparaison à budget égal et erreur de comptage.
    - **T6** : validation croisée par blocs de photos.
    - **T2** : vote calculé sur l'ExG.
    - **T7 à T9** : effet de l'échelle, effet du bord, stabilité du seuil.
- **Estimation de scientific-challenger, notée [H] et non mesurée.** Probabilité que la candidate batte le v5 sur `val_scellee` : environ 2 %, au plus 5 %. Le développement a été exploré par environ 144 configurations.
- **Prise par :** chef d'orchestre, sur l'audit de scientific-challenger.

### E-014 — Normalisation du vote et masque de couleur (convergence-engineer, 7 novembre 2026)
- **Avant.** Pré-enregistrement dans `docs/recherche/notes/convergence-engineer.md` § 7. Référence : vote + 0,25 × d̃3 (E-013).
- **Après [M].** Résultats dans `E-014/bilan_E-014.json`.
  - La règle d'égalité retient la configuration « Nsd + masque couleur » : F1 0,654, gain +0,003 [−0,0001 ; +0,006]. **Critère non rempli.** Sur dev_transfert : 0,582.
  - La configuration « ρ constant + masque couleur » fait 0,659, avec un gain de +0,007 [+0,002 ; +0,013]. Elle a été écartée par la fenêtre d'égalité de 0,005, que son auteur juge trop large.

### D-008 — Pas d'adoption a posteriori (7 novembre 2026)
- **Décision.** La règle pré-enregistrée s'applique telle quelle : « ρ constant + masque couleur » n'est **pas** adopté, et la référence reste E-013.
  - Une fenêtre d'égalité de 0,001 vaudra pour les expériences futures seulement.
  - D'après D-007, la candidate envoyée en validation reste le vote B′ seul.
- **Raison.** Adopter après coup la variante qui a gagné reviendrait à choisir sur les résultats (règle 3). Le gain (+0,007) est de l'ordre de l'optimisme de sélection estimé par l'audit (0,005 à 0,02).
- **Pause.** Le chef d'orchestre suspend les nouvelles variantes de méthode sur bv_session_a, en attendant :
  - les témoins T3, T5 et T6 (E-015) ;
  - la réponse de Corentin sur la suite de la boucle.

### E-015 — Témoins T3, T5 et T6 du vote B′ (independent-evaluator, 7 novembre 2026)
- **Avant.** Critères de T1 à T10 écrits dans `test_final.md` § 7, avant la mesure.
- **Après [M].** Résultats dans `out/comptage_math/evaluation/E-015/bilan_E-015.json` ; intervalles de confiance calculés par blocs de 7 photos.

  | Témoin | Mesure | Verdict |
  | --- | --- | --- |
  | **T3** — baseline ExG réglée à nouveau sur bv_session_a | baseline 0,567 ; le vote la bat de +0,070 [+0,037 ; +0,098] | passe |
  | **T5** — à budget égal | écart vote − baseline de +0,162 ; erreur de comptage +2 % pour le vote contre +53 % | passe |
  | **T6** — validation croisée par blocs | vote 0,632 hors pli, baseline 0,567 ; optimisme du seuil 0,005 | passe |

  - Les bootstraps depuis E-006 sont bien par photo d'origine. Comme ces photos se recouvrent à 80 %, les décisions se prennent désormais par blocs de 7 photos.
- **Conclusion.** Le vote B′ est une méthode réellement meilleure que la baseline explicite réglée sur les mêmes images.
- **Reste bloquant pour l'envoi :**
  - T9 : stabilité du seuil selon la luminance ;
  - la décision de Corentin sur la validation dense ;
  - le commit des règles.

### E-016 — Témoins T9, T2, T7 et T8 du vote B′ (convergence-engineer, 7 novembre 2026)
- **Avant.** Critères écrits dans `test_final.md` § 7. Aucune nouvelle configuration du vote.
- **Après [M].** Résultats dans `out/comptage_math/convergence-engineer/E-016/bilan_E-016.json`.

  | Témoin | Mesure | Verdict |
  | --- | --- | --- |
  | **T9** — stabilité selon la luminance (bloquant) | r = −0,23 sur 64 photos | **passe** |
  | **T2** — vote calculé sur l'ExG | 0,563 contre 0,637 en luminance | la luminance est maintenue |
  | **T7** — échelle de la tuile | vote de 0,625 à 0,662 selon la tranche, sans dégradation quand la résolution baisse ; v5 de 0,817 à 0,827 | rapporté |
  | **T8** — bord de 1,6 m exclu | vote 0,632, T3 0,577, v5 0,830 | rapporté |

- **Conclusion.** Plus aucun témoin ne bloque l'envoi du vote B′ figé.
  - Prédiction de l'auteur, notée [H] : F1 ≈ 0,64 à 5 cm/px sur des données de type bv_session_a, et ≈ 0,54 sur des données de type dev_transfert.
  - L'envoi attend la décision de Corentin (validation dense, T10, commits).

### D-009 — Changement de cap : la géométrie produit les étiquettes, un réseau apprend dessus (7 novembre 2026)
- **Contexte [O].** Corentin montre une diapositive Horama, « Compter les bananiers : la méthode, étape par étape ». La chaîne qu'elle décrit :
  1. photo ;
  2. axe de chaque feuille par tenseur de structure ;
  3. votes le long des axes, les feuilles d'un plant se croisent en son cœur ;
  4. réseau SegFormer : classe de chaque pixel ;
  5. réseau : un vecteur par pixel vers le cœur de son bananier.

  Les étapes 1 à 3 produisent les étiquettes d'entraînement. Le réseau est ensuite ré-entraîné sur ses propres prédictions. Aucune annotation manuelle.
- **Constat.** Les étapes 2 et 3 correspondent à notre vote B′ (E-008, E-010), trouvé de façon indépendante. Ce qui manque, c'est l'étape d'apprentissage.
- **Décision.**
  - Le vote B′ figé devient le **professeur**. Un réseau **élève** s'entraîne sur ses pseudo-étiquettes, puis sur ses propres prédictions (auto-entraînement).
  - Les annotations existantes ne servent qu'à évaluer, jamais à entraîner. Une pseudo-étiquette n'est pas une référence (CLAUDE.md).
  - Pas de téléchargement : le squelette resnet18 ImageNet est déjà en cache local (`~/.cache/torch/hub/checkpoints/resnet18-f37072fd.pth`), et c'est le même que celui du v5. SegFormer demanderait un téléchargement, soumis à accord.
  - Entraînement sur processeur, 3 h au plus par tour. Un GPU gratuit ne serait lancé que par Corentin.
  - Propriété :
    - pseudo-étiquettes : convergence-engineer (`out/comptage_math/convergence-engineer/E-017/`) ;
    - élève : performance-engineer (`comptage_math/eleve.py`, `scripts/math_eleve.py`, `out/comptage_math/performance-engineer/`) ;
    - évaluation : independent-evaluator.
- **Prise par :** chef d'orchestre, sur la diapositive transmise par Corentin et sa demande de continuer à améliorer le modèle.

### E-017 — Élève entraîné sur les pseudo-étiquettes du vote B′ : pré-enregistrement (7 novembre 2026)
- **Question.** Un réseau entraîné sans annotation, sur les seules sorties du vote B′, compte-t-il mieux les mères en plantation dense que le vote lui-même ?
- **Réserve d'images d'entraînement**, images préparées de `data/drone/comptage_v5_5cm/images/` :
  - plantations denses hors bv_session_a ;
  - exclusions : bv_session_a (évaluation), val_iter (DJI_0904–0945), val_scellee (DJI_0862–0903), toute image de test (dont banano), et les photos à moins de 3 numéros de ces plages (recouvrement d'environ 80 %).
  - La liste exacte est écrite par convergence-engineer **avant** l'entraînement, avec son empreinte MD5.
- **Pseudo-étiquettes (professeur figé E-010, aucun réglage).**
  - Positifs : pics du vote avec z ≥ 2,238.
  - Zone ignorée : disque de 0,5 m autour des pics avec 1,5 ≤ z < 2,238.
  - Fond : tout le reste.
- **Élève.**
  - Architecture : resnet18 ImageNet (cache local) + décodeur FPN, sortie au quart, carte de chaleur gaussienne. C'est l'architecture du v5 : la seule différence porte sur l'origine des étiquettes.
  - Entraînement : graine 2026 ; nombre d'époques fixé à l'avance par performance-engineer selon le budget de 3 h ; **dernière époque retenue**, sans arrêt précoce sur des références.
  - Augmentations : miroir, quarts de tour, luminosité et contraste 0,8 à 1,2.
- **Seuil de l'élève, non supervisé.** C'est celui pour lequel le nombre total de détections sur la réserve d'entraînement égale celui du professeur. NMS de 1,0 m. Un seuil réglé sur bv_session_a est rapporté en second, sans décider.
- **Tours.** Au plus 2 :
  - tour 1 : sur les étiquettes du professeur ;
  - tour 2 : sur les prédictions de l'élève du tour 1, mêmes règles, depuis l'initialisation ImageNet.
- **Mesure.** F1 des mères, appariement à 1 m, sur bv_session_a sans pépinière (règle v2), avec `scripts/math_evaluer.py`. bv_session_a n'est vu ni par le professeur ni par l'élève à l'entraînement.
- **Critère, écrit avant.**
  - Succès du tour 1 : F1 élève − F1 vote (0,637) ≥ +0,03, et borne basse de l'IC à 95 % (bootstrap par blocs de 7 photos) > 0.
  - Le tour 2 n'est retenu que si sa différence appariée avec le tour 1 a une borne basse > 0.
  - Rapportés, sans décider : erreur de comptage, dev_transfert, v5 (0,821, vu à l'entraînement).
- **Contrôle.** Un élève entraîné sur les pseudo-étiquettes **décalées de la demi-maille** (même nombre de points) doit faire nettement moins bien. Sinon, le réseau apprend la densité de végétation et non les cœurs.

### E-017, amendement 1 — Objections de scientific-challenger (7 novembre 2026, avant tout entraînement)
Source : `docs/recherche/notes/scientific-challenger.md`, section E-017 (OBJ-E1 à OBJ-E12). Les amendements ci-dessous remplacent les règles correspondantes d'E-017.
- **OBJ-E1 (acceptée) — témoins.** Le témoin demi-maille est conservé, mais à titre indicatif seulement : un réseau convolutif apprend aussi bien un décalage constant. Deux témoins deviennent décisifs :
  - **T-E1a** : élève entraîné sur des points tirés au hasard dans la végétation, même nombre de points par image. L'élève principal doit le dépasser d'au moins +0,10 de F1.
  - **T-E1b** : élève entraîné sur les détections de la baseline ExG réglée (T3). Il est rapporté pour savoir si le gain vient du vote ou de la distillation en général. Il ne bloque pas.
  - Les témoins suivent les mêmes réglages et le même nombre d'époques que l'élève principal. Ils ne sont lancés que si l'élève principal passe son critère.
- **OBJ-E2 (acceptée) — réserve d'images.**
  - La marge autour des plages exclues passe de ±3 à **±5 numéros**.
  - **dev_transfert est exclu de la réserve** (lasuiza, vols_100_022x, corte), pour rester une vraie mesure de transfert.
  - Sont aussi exclus : segmento_ouest, jeunes 0546 et 0548, pp_lote_2.
  - Banavista : le disque de 2 000 px est repris.
  - **bv_b_train** entre dans la réserve **en images seulement**, sans ses références. Conséquence : bv_b_train ne pourra plus servir de développement vierge pour les élèves ; la confirmation finale reste `val_scellee`.
  - Toute photo banavista préparée hors références et hors exclusions peut aussi entrer.
- **OBJ-E3 (acceptée) — candidate pour val_scellee.**
  - Si l'élève passe tous ses critères (critère E-017, deux graines, T-E1a), il **remplace** le vote B′ comme candidate unique.
  - Sinon, la candidate reste le vote B′ seul (D-007).
  - Un élève de tour 2 ne remplace celui du tour 1 que selon la règle d'E-017.
- **OBJ-E4 (acceptée) — graines.** Si la graine 2026 passe, une seconde graine (2027) est entraînée. Le succès exige que les deux passent.
- **Non bloquantes, retenues.**
  - Le seuil est égalisé sur la réserve hors un bloc de photos de bv_b_train mis de côté (choisi par convergence-engineer et listé avant l'entraînement). On rapporte aussi le F1 à k = N_réf et la courbe rappel-budget.
  - Nombre d'époques modéré, fixé par performance-engineer, sans viser à remplir les 3 h. On rapporte le désaccord élève-professeur.
  - Étiquettes du tour 2 : positifs = détections de l'élève du tour 1 au-dessus de son seuil non supervisé ; zone ignorée = disque de 0,5 m autour des détections entre 0,5 fois ce seuil et ce seuil.
  - Les têtes de segmentation et de vecteurs vers le cœur sont reportées à E-018, après le verdict d'E-017.

### D-010 — Réserve E-017 réduite à 280 tuiles (7 novembre 2026)
- **[O]** Après l'amendement 1, la réserve compte 280 tuiles : 57 photos de bv_b_train, DJI_0778 à 0836. Le bloc de seuil fait 50 tuiles (DJI_0757 et 0767 à 0774). Les MD5 sont dans `docs/recherche/notes/convergence-engineer.md` § 10.
- **Décision.** Le tour 1 part sur ces 280 tuiles, sans rouvrir dev_transfert.
  - Avec la règle de performance-engineer, N = 30 époques, soit environ 45 min.
  - L'extérieur du disque compté est traité comme une zone ignorée.
- **Raison.** Le squelette est pré-entraîné et le tour coûte peu. Une réserve plus grande ne sera discutée que si le tour 1 échoue de peu, par une nouvelle décision datée.

### D-011 — Retour aux mathématiques ; E-017 arrêté avant toute mesure (7 novembre 2026)
- **Contexte [S].** Corentin transmet le résumé de sa discussion avec Baptiste. L'équipe de référence **n'entraîne aucun réseau**. Elle modélise mathématiquement la feuille (forme, couleur, stries ou nervures, orientation ; fonctions gaussiennes citées, formule non donnée), place des **vecteurs sur les feuilles** dont les directions désignent les centres, puis compte les centres distincts. Limites citées :
  - première version ;
  - moins bon sur les vues moins zoomées ;
  - maillage et découpage des images à travailler ;
  - rejets laissés de côté.
- **Décision.**
  - E-017 est **arrêté** pendant le tour 1. Aucune prédiction ni mesure n'a été produite ; aucun processus ne reste actif.
  - Le code (`comptage_math/eleve.py`) et les pseudo-étiquettes sont conservés, sans suite prévue.
  - D-009 est suspendue.
  - Le vote B′ reste la candidate (D-007).
  - Rappel de la règle 1 : la fonction de Philemon reste inconnue. On écrit « formulation compatible avec l'indice X ».
- **Piste ouverte : concertation C-003.** Passer du vote **par pixel le long des axes** (B′) à un modèle **de feuille entière** : chaque feuille est détectée comme un objet, avec sa position, son orientation et sa longueur, et porte **un vecteur** vers le centre de son plant. Motifs [M] :
  - E-011 : 40 % des mères oubliées n'ont aucun candidat à moins de 1 m.
  - Le taux d'oubli est de 0,65 pour les couronnes de moins de 2 m, contre 0,29 au-delà de 3,6 m. Le vote a une échelle fixe (r_max 1,6 m), alors qu'une feuille détectée donne sa propre échelle.
- **Prise par :** chef d'orchestre, sur le résumé transmis par Corentin.

### E-018s — Modèle de feuille entière F, contrôle synthétique (leaf-mathematician, 7 novembre 2026)
- **Avant.** Le pré-enregistrement est dans `docs/recherche/modele_feuille.md` § 10. Le critère synthétique, écrit avant la mesure, exige :
  - au moins 50 % des feuilles retrouvées ;
  - un rappel des centres au budget d'au moins 0,80 sur plants isolés.
- **Formulation F.**
  - Gabarit gaussien de feuille entière h_{L,θ}, avec L ∈ {0,8 ; 1,2 ; 1,8} m et 12 orientations, appliqué à la luminance normalisée.
  - Les feuilles sont les maxima de la réponse ; chacune vote en deux points de son axe, à la distance 0,25 + L/2.
- **Après [M, synthétique].**
  - Feuilles retrouvées : 1,6 % et 8,6 % selon l'essai.
  - Rappel des centres sur plants isolés : 0,25 et 0,38. B′ fait 0,98 à 0,99 sur le même rendu.
  - Diagnostic : la position tombe souvent sur l'axe, mais l'axe est faux (écart médian de 37°) et la longueur est surestimée d'un facteur 1,35.
- **Conclusion.** **Échec.** À 4 à 7 cm/px, un gabarit gaussien lisse ne donne ni l'orientation ni la longueur ; seul le tenseur de structure de B′ donne l'orientation. Nervure et polarité ne sont pas identifiables, car nervure et pétiole occupent environ 1 px.
  - E-018 n'est pas lancé sur le réel ; son pré-enregistrement (§ 10.3) est gardé.
- **Suite décidée par le chef d'orchestre : F′** (C-003).
  - Une feuille est un segment connexe et cohérent du champ d'orientation de B′.
  - Sa longueur mesurée fixe la distance de vote ; chaque segment vote en un point de chaque côté.
  - F′ doit d'abord passer le même contrôle synthétique.

### E-019s — F′ : feuilles comme segments du champ d'orientation, contrôle synthétique (convergence-engineer, 7 novembre 2026)
- **Avant.** Formulation et critère écrits dans `docs/recherche/notes/convergence-engineer.md` § 11.0, avant le calcul. Le critère est le même qu'E-018s. Aucun paramètre n'est réglé.
- **Après [M, synthétique].**
  - Feuilles retrouvées : 0,531 sur plants isolés (passe), 0,491 sur plants jointifs.
  - Orientation bonne : écart médian de 9°.
  - **Rappel des centres sur plants isolés : 0,757, sous le seuil de 0,80 : échec.**
  - Témoin à distance fixe : 0,854. B′ : 0,979.
  - Cause : la longueur mesurée sous-estime la feuille (rapport médian 0,78). L'échelle adaptative fait moins bien que la distance fixe, et le vote en un point moins bien que le vote le long de l'axe.
- **Conclusion.** **Échec.** E-019 n'est pas lancé sur le réel.

### Issue de C-003 (7 novembre 2026, chef d'orchestre)
- Les deux formulations de « feuille entière + vecteur ponctuel », F (E-018s) et F′ (E-019s), échouent en synthétique, où B′ fait 0,98.
- À cette résolution, **le vote le long de l'axe (B′) reste la meilleure façon connue de transformer les feuilles en centres.** C'est cohérent avec la diapositive transmise par Corentin (étape 3 : « votes le long des axes »).
- Les gains restants ne viendront pas d'une meilleure fonction de feuille sur le développement actuel, exploré par plus de 150 configurations. Ils viendront :
  - d'une comparaison directe avec la méthode de Baptiste sur une même image, qu'il a lui-même proposée ;
  - d'une mesure unique sur `val_scellee`.

### D-012 — Corentin choisit la mesure unique sur val_scellee (7 novembre 2026)
- **Décision de Corentin** (« Mesurer val_scellee »). Le vote B′ figé (E-010) est mesuré **une seule fois** sur `val_scellee`, sur les seules photos conformes (§ 6 de `test_final.md`, 40 photos sur 42). Il est comparé au v5 (seuil 0,30) et à la baseline T3 figée, selon la règle § 2.5.
  - `val_scellee` reste la confirmation, comme dans l'option 1b. On passe directement à la confirmation, sans cycle sur `val_iter_v2` : la candidate est unique et figée depuis D-007.
  - T10 (DJI_0800 et 0804) ne concerne que `bv_b_train` : il n'entre pas dans cette mesure.
- **Ordre.**
  1. independent-evaluator écrit le § 8 de `test_final.md` : candidates figées et empreintes SHA-256, photos mesurées, blocs, critère, prédictions chiffrées.
  2. Les règles sont commitées, avec l'accord explicite de Corentin, demandé pour ce commit.
  3. independent-evaluator, et lui seul, fait la mesure.

### D-013 — Simulateur v2 : rendu réaliste et non circulaire (7 novembre 2026)
- **Demande de Corentin.** Rendre le contrôle synthétique fidèle au réel. Aujourd'hui, le vote y fait 0,98, contre 0,637 sur bv_session_a. Il faut reproduire :
  - des tailles de plants très variées ;
  - les feuilles sèches ;
  - les ombres ;
  - l'herbe ;
  - les recouvrements complexes ;

  et corriger la circularité relevée en E-005.
- **Principe anti-circularité.** Le simulateur est **calibré sur des statistiques d'images réelles, jamais sur des scores de détection**. Il est **validé** sur sa capacité à **prédire les scores réels déjà mesurés** des méthodes connues :
  - vote B′ 0,637 ;
  - baseline T3 0,567 ;
  - vote ExG 0,563 ;
  - A′ 0,541 ;
  - A-iso 0,423.

  Aucun de ces scores ne sert à régler le simulateur.
- **Données de calibration.** bv_session_a sans pépinière (développement) uniquement : images, et références pour les tailles et espacements. Ni bv_b_train/bv_b_val, ni val_iter, ni val_scellee, ni le test.
- **Rôles et fichiers.**
  - **scientific-challenger** : critères d'acceptation du simulateur, écrits avant, dans sa note.
  - **image-analyst** : statistiques photométriques réelles (ombres, feuilles sèches, herbe et sol, spectre de luminance, distribution de cohérence du tenseur), dans `out/comptage_math/image-analyst/D-013/`.
  - **plant-geometry** : statistiques géométriques réelles (tailles de couronne, distances aux voisins, recouvrements), dans `out/comptage_math/plant-geometry/D-013/`.
  - **leaf-mathematician** : rendu v2, dans un nouveau fichier `comptage_math/simulateur.py` dont il est seul rédacteur. Il est lancé quand les trois livrables précédents existent.
- **Prise par :** chef d'orchestre, à la demande de Corentin.
- **En attente, sans changement :** le commit des règles et la mesure E-020 sur val_scellee, qui attendent l'accord de Corentin.

### D-013, suite — Cibles scellées du test de prédiction (independent-evaluator, 7 novembre 2026)
- **Cibles sur VAL-S :** `out/comptage_math/evaluation/D-013/cibles_VAL-S.json`, SHA-256 `6351313d…`.
- **Cibles des tests cachés :** `cibles_cachees_VAL-S.json`, SHA-256 `e97be160…`.
- **Aucune méthode relancée.** Les détections existantes ont été réutilisées : E-001, E-006, E-010, E-015, E-016.
- **Précision sur la métrique.** Les cinq chiffres publics (0,637, 0,567, 0,563, 0,541, 0,423) sont des F1 **au seuil figé**. Le test de prédiction se décide **au budget k = N_réf**, où les valeurs diffèrent. En particulier, l'écart B′ − T3 n'est pas le même.
  - Les chiffres au budget ne sont pas écrits ici : ce journal est lisible par leaf-mathematician.
  - Ils seront consignés ici, comme le demande le § 3.1 du contrat, une fois le test de prédiction fait.
- **Garde.** Le dossier `out/comptage_math/evaluation/D-013/` n'est pas communiqué au constructeur du simulateur.

### D-013, simulateur v2.1 (leaf-mathematician, 7 novembre 2026) — 1re version sur 3 : fidélité non atteinte
- **[M]** `out/comptage_math/leaf-mathematician/D-013/fidelite_v2.1.json`. Empreintes et paramètres dans `docs/recherche/modele_feuille.md` § 11.
  - Passent : F1, F2, F5, G1, G3, G6.
  - Échouent :
    - F3 : herbe 0,23 contre 0,14 ;
    - F4 : dispersion du sec et de l'herbe ;
    - G2 : distance au plus proche voisin ;
    - G4 : g(r) ;
    - G5 : contact.
  - L'ancien rendu échoue à tous les tests : le contrôle de non-trivialité est passé.
- **Conséquence.** Le test de prédiction n'est pas lancé. On passe à la v2.2, corrigée uniquement à partir des statistiques de CAL :
  - un processus de positions calé sur g(r) de CAL ;
  - une texture des limbes calée sur la classification de la canopée de CAL ;
  - la dispersion entre tuiles du sec et de l'herbe ;
  - 176 tuiles, comme VAL-S, conformément au contrat.

### D-013, simulateur v2.2 (leaf-mathematician, 7 novembre 2026) — 2e version sur 3 : fidélité non atteinte
- **[M]** `out/comptage_math/leaf-mathematician/D-013/fidelite_v2.2.json`, 176 tuiles, graines 20261113 + i. Empreintes consignées avant la passe VAL-S (`modele_feuille.md` § 11.3) et revérifiées par le chef d'orchestre : `simulateur.py` c929b074…, `parametres_v2.2.json` b422d22e…, `fonds_cal.npz` f8b7962c….
  - Passent : F1 à F5, G1, G4 (0,27 pour 0,29), G5 (0,027), G6.
  - Échouent :
    - G2 : KS de d1 0,18 pour un seuil de 0,14 ; les d1 simulés sont trop courts ;
    - G3 : densité −15 % (seuil 11 %) et CV des densités entre tuiles 1,11 (seuil 0,97). L'amincissement crée des trouées trop grandes.
- **Écart de méthode relevé par l'auteur.** La géométrie a été calée avec des allées à p = 0,5, puis p a été ramené à 0,3 pour la photométrie sans recaler la géométrie : cause probable de G3.
- **Conséquence.** Le test de prédiction n'est pas lancé. Le chef d'orchestre lance la v2.3, **dernière version permise**, corrigée uniquement sur CAL : géométrie recalée avec p = 0,3, amincissement plafonné par la part de cellules de 10 m vides de CAL (3,1 %), densité et d1 vérifiés sur CAL avant la passe VAL-S. Si la v2.3 échoue, le simulateur est déclaré non fidèle et ne sert pas au test de prédiction.

### E-020 — Mesure unique sur val_scellee : vote B′, v5 et baseline T3 (independent-evaluator, 7 novembre 2026)
- **Règles :** `docs/recherche/test_final.md` § 8, commitées avant la mesure (commit d084589, branche `comptage-math/val-scellee`, accord de Corentin, D-012).
- **Empreintes :** les 17 SHA-256 du § 8.4 ont été vérifiées avant le lancement, toutes identiques (script `05536ad3…`, `votes.py` `eff3fb21…`, ONNX v5 `12f9b4ca…`, `math_evaluer.py` `934585b1…`, etc.). Le script les a revérifiées et les consigne dans `bilan_E-020.json` (`empreintes`, `empreinte_script`). Aucun fichier `VERROU` n'existait avant le lancement.
- **Commande, lancée une seule fois** (16 h 37 → 16 h 39, détections en 76 s) :
  `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/evaluation/e020_val_scellee.py --mesure E-020`
- **Données :** 40 photos conformes de `val_scellee` (DJI_0862 à 0902 sans 0867 ni 0903), 6 blocs, 5 336 mères. Mères seules, appariement un à un à 1 m, disque de 2 000 px. Bootstrap par blocs, 10 000 tirages, graine 2026.
- **[M, E-020]** Résultats, chaque méthode à son seuil figé :

| Méthode | P | R | F1 [IC 95 % par blocs] | F1 à k = N_réf | Erreur de comptage | Double comptage | Prédiction § 8.7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Vote B′ (z ≥ 2,238) | 0,697 | 0,667 | **0,682** [0,668 ; 0,693] | 0,684 | −4,2 % | 0,056 | 0,62 [0,55 ; 0,68] |
| v5 (0,30) | 0,870 | 0,774 | **0,819** [0,816 ; 0,823] | 0,833 | −11,0 % | 0,008 | 0,83 [0,78 ; 0,88] |
| Baseline T3 (0,1688) | 0,483 | 0,732 | **0,582** [0,570 ; 0,597] | 0,487 | +51,4 % | 0,072 | 0,54 [0,46 ; 0,60] |

- **Vote − v5 :** −0,138, IC 95 % [−0,149 ; −0,128], borne basse unilatérale −0,147 ; au budget, 0,684 contre 0,833. Par bloc : de −0,118 (L2B1) à −0,163 (L2B3). Prédiction : −0,21 [−0,30 ; −0,12].
- **Vote − baseline T3 :** +0,100, IC 95 % [+0,082 ; +0,114], borne basse unilatérale +0,085 ; au budget, 0,684 contre 0,487. Par bloc : de +0,068 (L1B1) à +0,124 (L1B3). Prédiction : +0,08 [+0,02 ; +0,14].
- **Baseline − v5 (rapporté) :** −0,237, IC 95 % [−0,250 ; −0,224].
- **Écart aux prédictions :** le F1 du vote (0,6817) dépasse de peu la borne haute de la fourchette à 80 % (0,68), sans atteindre le seuil de surprise (0,72). Les autres grandeurs sont dans leurs fourchettes.
- **Lecture (§ 8.6 et 8.8) :**
  - « **Non confirmé** : sur `val_scellee` (40 photos conformes, 6 blocs), le vote B′ figé (E-010) ne bat pas le v5 au seuil 0,30. » Aucune des trois conditions n'est remplie.
  - Contre la baseline T3 (rapporté, sans effet sur le verdict principal) : les trois conditions sont remplies.
  - `val_scellee` est consommée. Aucune variante du vote n'y sera plus mesurée, et ces chiffres ne servent à régler aucun paramètre ni aucun seuil.
- **Sorties :** `out/comptage_math/evaluation/E-020/` : `VERROU`, `detections_vote_B_prime.csv` (`52b7c6a7…`), `detections_v5.csv` (`e1e02711…`), `detections_baseline_T3.csv` (`6a882e68…`), `bilan_E-020.json` (`ab8f5276…`), et `evaluation/` (résumés, détails par image et courbes rappel-budget de chaque évaluation). Journal de la console : `out/comptage_math/evaluation/E-020.log`.

### D-013, simulateur v2.3 (leaf-mathematician, 7 novembre 2026) — 3e et dernière version : fidélité non atteinte, simulateur clos
- **[M]** `out/comptage_math/leaf-mathematician/D-013/fidelite_v2.3.json`, 176 tuiles. `simulateur.py` 26668ddd… (revérifié par le chef d'orchestre), `parametres_v2.3.json` 5124e5b8…, consignés avant la passe (`modele_feuille.md` § 11.5). Contrôles sur CAL écrits avant et tous passés.
  - Passent : F2, F3, F5 et, pour la première fois, les six tests géométriques G1 à G6.
  - Échouent :
    - F1 : KS de luminance 0,112 pour un seuil de 0,10 ; l'image est trop sombre (ombre 0,126 contre 0,109) ;
    - F4 : rapport de dispersion du sol 1,69 pour un seuil de 1,5. Sur CAL, il était déjà de 1,46.
- **Conséquence (contrat D-013, § 5).** Les trois versions sont consommées et aucune n'atteint la fidélité. Le simulateur n'a aucun usage permis : pas de test de prédiction, pas de diagnostic du vote par facteur. Les cibles scellées restent fermées. Le code et les scènes sont conservés pour référence.

### E-021 — Diagnostic de l'écart vote–v5, développement seulement (error-analyst, 7 novembre 2026)
- **Règles** écrites avant le calcul dans `docs/recherche/notes/error-analyst.md` (section E-021). Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/error-analyst/e021_ecart_v5.py`. Sorties dans `out/comptage_math/error-analyst/E-021/`, relues par le chef d'orchestre. Comptes d'E-011 reproduits à l'identique.
- **[M] Oracle sur bv_session_a** (écart v5 − vote 0,184 ; bornes hautes, en ne corrigeant que ce que le v5 réussit) :
  - FN sans candidat : +0,056 ;
  - FN sous le seuil : +0,052 ;
  - FP autre végétal : +0,042 ;
  - bord : +0,025 (environ +0,006 une fois le taux de base retiré, [H]) ;
  - feuille isolée : +0,022 ;
  - doublon : +0,018 ;
  - chacune des autres classes : moins de +0,006.
  - Sur dev_transfert, le premier levier est l'autre végétal (+0,140).
- **[M] Grandes couronnes (≥ 2,8 m) trouvées par le v5 et oubliées par le vote, hors bord (n = 857) :**
  - signal radial absent : 55,7 %, contre 13,8 % pour les mères trouvées ;
  - pic déplacé : 23,6 % ;
  - signal présent mais trop faible au centre : 20,8 %.
  - Seule l'**alignement radial à 0,4–1,6 m** sépare oubliées et trouvées (AUC 0,15). Cohérence, végétation et contraste ne les séparent pas.
  - Le signal situé uniquement au-delà de r_max = 1,6 m ne concerne que 4,5 % des oubliées : **la troncature est réfutée comme cause**.
- **Écarts au protocole signalés par l'auteur :**
  - une relance, après un plantage à l'étape des planches ;
  - un amendement daté de la règle « pic déplacé », fait avant la lecture des planches et sans effet sur les effectifs.

### E-022 — Échelle de dérivation σ_g du vote : pré-enregistrement (7 novembre 2026, avant tout calcul)
- **Hypothèse [H], tirée d'E-021.** Sur les grands limbes, le tenseur à σ_g = 4 cm suit les nervures secondaires plutôt que les axes radiaux des feuilles. σ_g n'a jamais été varié : E-010 n'a varié que σ_t.
- **Données :** bv_session_a sans pépinière ; dev_transfert en contrôle. Interdits : bv_b_*, val_*, D-013.
- **Étape A — diagnostic, sans F1.**
  - Alignement radial à 0,4–1,6 m aux grandes couronnes hors bord, pour σ_g ∈ {4, 6, 8, 12} cm, avec σ_t = 2,5 σ_g.
  - Seuil de présence recalculé à chaque échelle : 90e centile sur les milieux de paires de mères.
  - **Critère A :** retenir la plus petite échelle σ_g* pour laquelle :
    - la part des oubliées avec signal passe de 39,7 % à au moins 55 % ;
    - la part des mères trouvées avec signal (85,6 %) ne baisse pas de plus de 2 points.
  - Si aucune échelle ne passe : arrêt, et l'hypothèse « nervures » est réfutée.
- **Étape B — seulement si A passe.**
  - Fusion z = zrob(z_an(4 cm) + z_an(σ_g*)), comme `carte_votes_multi`.
  - Seul réglage permis : le seuil, choisi sur bv_session_a selon la règle d'E-008.
  - **Critère B, tous requis :**
    - gain de F1 apparié d'au moins +0,010 sur bv_session_a, avec un IC 95 % par blocs de 7 photos qui exclut 0 ;
    - taux d'oubli des mères de 2,8 m et plus en baisse d'au moins 5 points ;
    - F1 sur dev_transfert sans perte de plus de 0,005 ;
    - fenêtre d'égalité de 0,001 (D-008).
  - Réserve : l'optimisme de sélection est estimé entre 0,005 et 0,02, donc un gain inférieur à 0,02 sera déclaré ambigu.
- **Pas de nouvelle mesure de test :** val_scellee est consommée. Une éventuelle validation fera l'objet d'une décision distincte, soumise à Corentin.

### E-022 — Échelle de dérivation σ_g : résultat (convergence-engineer, 7 novembre 2026)
- **[M]** Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/convergence-engineer/e022_sigma_g.py`. Sorties dans `out/comptage_math/convergence-engineer/E-022/`, relues par le chef d'orchestre. Contrôle de départ conforme (39,7 % et 85,6 % à 4 cm).
- **Étape A, part des oubliées avec signal (bv_session_a) :**
  - 39,7 % à 4 cm ; 50,4 % à 6 cm ; **54,96 % à 8 cm (471 sur 857, alors qu'il en fallait 472)** ; 53,8 % à 12 cm.
  - Mères trouvées : de 85,6 % à 89,8 %.
  - L'AUC entre oubliées et trouvées monte de 0,15 à 0,22 : les deux groupes se séparent moins.
  - Sur dev_transfert, la part des oubliées avec signal **baisse** à chaque échelle (de 41,8 % à 24,8 %).
- **Conclusion.** **Critère A manqué** : l'étape B n'est pas lancée et l'hypothèse « nervures » est réfutée au sens du critère. Le quasi-passage sur bv_session_a ne se transfère pas ; il ressemble à un effet de lissage commun aux deux groupes [H]. Le seuil n'est pas réinterprété (D-008).
- **Code.** `comptage_math/votes.py` reçoit deux paramètres, dont les valeurs par défaut gardent B′ figé : `sigma_g_m` et `sigmas_g`.
  - Les cartes z sont identiques au bit près sur 3 tuiles.
  - Nouvelle empreinte : b3131dcc…. La version mesurée en E-020 (eff3fb21…) reste celle du commit d084589.

### E-023 — Symétrie radiale de la couronne (FRST) : pré-enregistrement (7 novembre 2026, avant tout calcul)
- **Décision de Corentin**, après E-022 : explorer la symétrie radiale.
- **Hypothèse [H].** Sur les grandes couronnes « sans signal » d'E-021, l'orientation fine des feuilles ne converge pas, mais la couronne entière reste un objet à symétrie radiale à son échelle : contours, alternance limbes/ombres. Une transformée de symétrie radiale rapide **[S] Loy et Zelinsky, « Fast Radial Symmetry for Detecting Points of Interest », IEEE TPAMI 25(8), 2003** capterait ce signal à partir des gradients de luminance à l'échelle de la couronne. Ce serait une information complémentaire du vote B′, qui n'utilise que l'orientation des axes.
- **Formulation.**
  - Luminance lissée à σ_s ∈ {8, 16} cm.
  - Gradients, puis votes en p ± n·ĝ pour les rayons n ∈ {0,6 ; 0,9 ; 1,2 ; 1,5} m.
  - Polarité : positive, négative ou les deux.
  - Images O_n (orientation) et M_n (magnitude), exposant radial α ∈ {1, 2}, lissage A_n de largeur 0,25 n.
  - Score S = moyenne sur n de F_n * A_n, normalisé en z robuste par tuile, dans le masque végétation de `votes.champ`.
  - Le vote B′ n'est pas modifié.
- **Données :** bv_session_a sans pépinière ; dev_transfert en contrôle. Interdits : bv_b_*, val_*, `out/comptage_math/evaluation/D-013/`.
- **Étape A — diagnostic sans F1.** Groupes et milieux d'E-021 : 857 grandes couronnes oubliées hors bord, dont 477 « signal radial absent » ; 2 742 trouvées par les deux ; milieux de paires de mères.
  - Pour chaque configuration (σ_s × polarité × α, soit 12), seuil T = 90e centile de S sur les milieux.
  - **Critère A, sur bv_session_a :** retenir la configuration qui maximise la part des 477 « signal absent » avec S ≥ T, sous trois conditions :
    1. cette part est d'au moins 40 % (le taux de base des milieux est de 10 %) ;
    2. la part des 2 742 trouvées avec S ≥ T est d'au moins 60 % ;
    3. sur dev_transfert, la part des « signal absent » avec S ≥ T de la même configuration est d'au moins 30 %.
  - Si aucune configuration ne passe : arrêt, FRST réfutée comme complément.
- **Étape B — seulement si A passe.**
  - Fusion z = zrob(z_vote + w · z_FRST), avec w ∈ {0,5 ; 1,0}. Mêmes NMS 1,0 m et maxima que le vote.
  - Seul autre réglage : le seuil, choisi sur bv_session_a selon la règle d'E-008.
  - FRST seule est aussi mesurée, pour information.
  - **Critère B, tous requis :**
    - gain de F1 apparié contre B′ figé d'au moins +0,010 sur bv_session_a, avec un IC 95 % par blocs de 7 photos qui exclut 0 ;
    - taux d'oubli des mères de 2,8 m et plus en baisse d'au moins 5 points ;
    - F1 sur dev_transfert sans perte de plus de 0,005 ;
    - fenêtre d'égalité de 0,001 (D-008).
  - Un gain inférieur à 0,02 est déclaré ambigu (optimisme de sélection).
- **Pas de mesure de test :** val_scellee est consommée. Toute validation fera l'objet d'une décision distincte, soumise à Corentin.

### E-023 — Symétrie radiale FRST : résultat (convergence-engineer, 7 novembre 2026)
- **[M]** Commandes : `out/comptage_math/convergence-engineer/e023_frst.py` et `e023_synthetique.py`. Sorties dans `E-023/`, critère A relu par le chef d'orchestre (`critere_A.csv`). Précisions de formulation fixées avant le calcul dans la note de l'auteur, § 13.0.
- **Contrôle synthétique.**
  - Disque : le maximum tombe au centre, à 1 cm près.
  - Étoile de 8 bandes radiales : le maximum tombe à 1,2 m du centre. La FRST capte le contour d'un objet compact, pas une étoile de limbes, car les bords des bandes ont un gradient tangentiel [H].
- **Étape A.** Aucune des 12 configurations n'approche les seuils.
  - « Signal absent » au-dessus de T : 8,6 % au mieux, pour 40 % requis.
  - Mères trouvées : 1,5 % au mieux, pour 60 % requis.
  - Toutes les parts sont sous le taux de base de 10 % : **le signal est inversé**. Le z de la FRST est négatif au centre des mères (médiane de −0,27 à −0,68) et positif aux milieux entre mères (+0,29 à +0,68), sur les deux jeux.
- **Conclusion.** **Critère A manqué** ; l'étape B n'est pas lancée. La FRST de couronne est réfutée comme complément du vote. Les maxima de symétrie compacte tombent dans les trouées et sur des limbes isolés, pas au centre des couronnes.

### E-024 — Distance aux trouées : pré-enregistrement (7 novembre 2026, avant tout calcul)
- **Décision de Corentin**, après E-023.
- **Hypothèse [H].** E-023 montre que les objets compacts de la canopée dense sont les trouées entre couronnes. Le centre d'un plant serait donc le point de feuillage le plus éloigné des trouées. C'est une formulation compatible avec la délimitation de couronnes par carte de distance et bassins versants **[S] méthode classique en télédétection forestière, par exemple Wang, Gong et Biging 2004, PE&RS 70(3)**. Elle n'utilise ni l'orientation des limbes ni la forme d'étoile.
- **Formulation.**
  - **Trouées** : pixels hors du masque végétation de `votes.champ`, ou de luminance (lissée à 5 cm) sous le centile p ∈ {15, 25} de la végétation de la tuile.
  - **Nettoyage** : ouverture puis suppression des composantes de moins de a ∈ {0,02 ; 0,08} m².
  - **Carte** : D = distance euclidienne aux trouées, en mètres, lissée à σ_d ∈ {10, 25} cm, puis normalisée en z robuste dans le masque, par tuile.
  - Grille de 2 × 2 × 2 = 8 configurations.
  - Le vote B′ n'est pas modifié.
- **Données :** bv_session_a sans pépinière ; dev_transfert en contrôle. Interdits : bv_b_*, val_*, `out/comptage_math/evaluation/D-013/`.
- **Étape A — diagnostic sans F1, groupes et milieux d'E-021.** Seuil T de chaque configuration = 90e centile de z_D sur les milieux de paires de mères.
  - **Critère A** : retenir la configuration qui maximise la part des 477 grandes couronnes « signal absent » avec z_D ≥ T, à trois conditions :
    1. cette part est d'au moins 40 % ;
    2. la part des 2 742 mères trouvées par les deux méthodes avec z_D ≥ T est d'au moins 60 % ;
    3. sur dev_transfert, la même configuration donne au moins 30 % pour les « signal absent ».
  - Si aucune configuration ne passe : arrêt, et la distance aux trouées est réfutée.
- **Étape B — seulement si A passe.**
  - Candidats : maxima locaux de z_D seul, et fusion z = zrob(z_vote + w · z_D) avec w ∈ {0,5 ; 1,0}.
  - Même NMS de 1,0 m que le vote. Seul autre réglage : le seuil, choisi sur bv_session_a selon la règle d'E-008.
  - **Critère B**, tous requis, pour la meilleure fusion :
    - gain de F1 apparié contre B′ figé d'au moins +0,010 sur bv_session_a, avec un IC 95 % par blocs de 7 photos qui exclut 0 ;
    - taux d'oubli des mères de 2,8 m et plus en baisse d'au moins 5 points ;
    - perte de F1 sur dev_transfert d'au plus 0,005 ;
    - fenêtre d'égalité de 0,001 (D-008).
  - Un gain inférieur à 0,02 est déclaré ambigu. z_D seul est rapporté pour information.
- **Pas de mesure de test** : val_scellee est consommée.

### E-024 — Distance aux trouées : résultat (dense-canopy-engineer, 7 novembre 2026)
- **[M]** Commandes : `out/comptage_math/dense-canopy-engineer/e024_synthetique.py` et `e024_trouees.py`. Sorties dans `E-024/`. Le critère A a été relu par le chef d'orchestre (`critere_A.csv`). Les points muets ont été fixés avant le calcul (note de l'auteur, § 1.0).
- **Contrôle synthétique : échec.**
  - Avec le bruit prévu, aucune des 8 configurations ne place les maxima aux centres (écarts de 0,6 à 2,4 m).
  - Diagnostic après coup : sans bruit, les maxima tombent à 1 à 5 cm des centres. La règle du centile p fragmente un feuillage texturé [H].
- **Étape A.** Pour la meilleure configuration (p 15, a 0,02 m², σ_d 25 cm) :
  - « signal absent » : 44,9 % (condition 1 remplie) ;
  - dev_transfert : 41,6 % (condition 3 remplie) ;
  - mères trouvées : **50,4 %, pour 60 % requis** (condition 2 manquée). Aucune configuration ne la remplit.
  - Le signe est le bon, contrairement à la FRST : la médiane de z_D vaut de +0,4 à +1,3 aux mères, contre environ −0,35 aux milieux. C'est 3 à 5 fois le taux de base.
  - [O] Les maxima suivent les crêtes de canopée entre ombres internes, pas les centres.
- **Conclusion.** **Critère A manqué** ; l'étape B n'est pas lancée. Selon la règle écrite, la distance aux trouées est réfutée comme complément. Le résultat n'est pas réinterprété (D-008).
- **[O] Remarque du chef d'orchestre, pour une éventuelle expérience future et sans valeur de verdict ici.** z_D signale à peu près autant les oubliées « signal absent » (45 %) que les trouvées (50 %). Son information semble donc peu corrélée au vote, ce que la condition 2 ne mesurait pas.

### E-025 — Fusion vote + distance aux trouées, mesurée en F1 : pré-enregistrement (7 novembre 2026, avant tout calcul)
- **Décision de Corentin**, après E-024. C'est une **nouvelle expérience**, pas une reprise d'E-024 : le verdict d'E-024 (critère A manqué, distance réfutée selon sa règle) reste tel quel (D-008).
- **Motif [O].** z_D signale à peu près autant les grandes couronnes « signal absent » (45 %) que les mères trouvées par le vote (50 %). Son information paraît peu corrélée au vote. Seul le F1 dira si elle le complète.
- **Configuration figée, sans F1** : p 15, a 0,02 m², σ_d 25 cm. C'est celle qui maximise la part « signal absent » à l'étape A d'E-024 (règle de choix d'E-024, appliquée sans les conditions). Aucune autre configuration n'est mesurée.
- **Candidats.**
  - Fusion z = zrob(z_vote + w · z_D), w ∈ {0,5 ; 1,0} ; z_vote = vote B′ figé (E-010) ; même NMS de 1,0 m.
  - Seul autre réglage : le seuil, choisi sur bv_session_a selon la règle d'E-008. w est choisi sur le F1 de bv_session_a ; à égalité (0,001), w = 0,5.
  - z_D seul est rapporté pour information, sans verdict.
- **Données :** bv_session_a sans pépinière (réglage et verdict) ; dev_transfert en contrôle. Interdits : bv_b_*, val_*, `out/comptage_math/evaluation/D-013/`.
- **Critère**, tous requis, pour le w retenu :
  1. gain de F1 apparié contre B′ figé d'au moins +0,010 sur bv_session_a, IC 95 % par blocs de 7 photos excluant 0 ;
  2. taux d'oubli des mères de 2,8 m et plus en baisse d'au moins 5 points ;
  3. perte de F1 sur dev_transfert d'au plus 0,005, au seuil choisi sur bv_session_a ;
  4. fenêtre d'égalité 0,001 (D-008).
- **Réserve écrite d'avance.** Le seuil et w sont choisis sur les mêmes images que le verdict : un gain inférieur à 0,02 est déclaré **ambigu** (optimisme de sélection). Aucun test indépendant n'est disponible (val_scellee consommée) : même un succès reste un résultat de développement, pas une adoption.

### E-025 — Fusion vote + distance aux trouées : résultat (dense-canopy-engineer, 7 novembre 2026)
- **[M]** Commande : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/dense-canopy-engineer/e025_fusion.py` (186 s). Sorties dans `E-025/`. Le chef d'orchestre a relu `bilan_E-025.json`.
- **Contrôle** : le vote B′ recalculé retrouve E-010 à l'identique (16 650 détections, seuil 2,2382, F1 0,6368 ; dev_transfert 0,5455).
- **F1 sur bv_session_a (seuil par la règle d'E-008) et sur dev_transfert (au même seuil)** :
  - vote B′ : 0,6368 et 0,5455 ;
  - fusion w = 0,5 : **0,6580** et 0,5468 ;
  - fusion w = 1,0 : 0,6442 et 0,5141 ;
  - z_D seul, pour information : 0,5074 et 0,4123.
- **Critère pour w = 0,5**, retenu sur le F1 de bv_session_a :
  1. gain apparié +0,0212, IC 95 % par blocs [+0,0082 ; +0,0362] : rempli ;
  2. oubli des mères ≥ 2,8 m de 29,5 % à 23,2 % (−6,3 points) : rempli ;
  3. dev_transfert : +0,0013, donc sans perte : rempli.
- **Verdict : succès selon la règle écrite.** Le gain dépasse le seuil d'ambiguïté (0,02) de seulement 0,0012. La réserve écrite d'avance s'applique : w et le seuil ont été choisis sur les mêmes images, et aucun test indépendant n'existe. C'est donc un résultat de développement, **pas une adoption**.
- **Mécanisme [M]** : le rappel passe de 0,643 à 0,703 ; la précision baisse de 0,630 à 0,619.
- **Écart restant** : la fusion reste loin de v5 sur ces photos (0,821 en E-006, v5 entraîné dessus).
- **Note** : l'empreinte de `votes.py` (b3131dcc) diffère de celle du bilan d'E-010 (993bff46). Les détections et le F1 sont pourtant identiques, et c'est la même empreinte que pour E-022 à E-024.
