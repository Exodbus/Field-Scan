# Équipe de recherche : composition et responsabilités

Écrit le 7 novembre 2026. L'équipe construit une méthode mathématique de comptage des plants principaux de bananiers sur images aériennes.

Ce document est tenu par la session principale, le chef d'orchestre. Les règles communes sont dans `CLAUDE.md`.

## 1. Ce que sont les agents, concrètement

- Chaque agent est un **sous-agent Claude Code**, défini par un fichier `.claude/agents/<nom>.md` :
  - format de la version installée (2.1.211) : en-tête YAML `name`, `description`, `tools`, `model`, `color`, puis les consignes du rôle ;
  - aucun autre mécanisme d'équipe n'est configuré.
- Les six équipes sont une **organisation de travail**, décrite ici. Elles ne correspondent à aucun réglage de Claude Code. La couleur commune de chaque équipe sert seulement à les reconnaître à l'écran.
- La session principale lance un agent avec l'outil Agent, en donnant le nom du profil comme type. Elle peut le reprendre ensuite avec SendMessage et son identifiant.
- L'outil Agent n'est donné à aucun profil : un agent ne lance pas d'autre agent. Tout passe par le chef d'orchestre, qui garde ainsi le compte des agents actifs.
- Tous les profils ont `model: inherit` : ils utilisent le modèle de la session principale.
- Les profils ont été créés dans un dossier `.claude/agents/` qui n'existait pas. Une session déjà ouverte doit être **redémarrée** pour les voir ; les sessions ouvertes ensuite dans `Field-Scan` les chargent.

## 2. Composition

| Équipe | Agent | Responsable | Rôle en une ligne |
| --- | --- | --- | --- |
| DONNÉES | image-analyst | **oui** | résolution, netteté, ombres, visibilité des feuilles et des stries |
| DONNÉES | banana-morphology | | morphologie, rejets, différences avec les autres végétaux |
| DONNÉES | annotation-manager | | conventions de comptage, références existantes, découpage par parcelle ou vol |
| RECHERCHE ET MATHÉMATIQUES | leaf-mathematician | **oui** | modèles paramétriques des feuilles (gaussiennes, nervures, stries) |
| RECHERCHE ET MATHÉMATIQUES | scientific-researcher | | bibliographie, sources primaires, comparaison des méthodes |
| RECHERCHE ET MATHÉMATIQUES | plant-geometry | | organisation des feuilles et contraintes géométriques autour du centre |
| VISION | orientation-engineer | **oui** | axes, nervures, textures, fiabilité des orientations |
| VISION | leaf-template-engineer | | gabarits de feuilles à plusieurs tailles et orientations |
| VISION | vegetation-color-engineer | | couleur, végétation, ombres, feuilles malades |
| COMPTAGE | convergence-engineer | **oui** | votes géométriques et centres candidats |
| COMPTAGE | dense-canopy-engineer | | séparation des plants proches, feuillages superposés |
| COMPTAGE | detection-cleanup-engineer | | faux positifs, doublons, fusion entre tuiles |
| ÉVALUATION | independent-evaluator | **oui** | métriques, appariement des centres, protection du test final |
| ÉVALUATION | error-analyst | | classification et visualisation des erreurs |
| ÉVALUATION | scientific-challenger | | hypothèses alternatives, contre-exemples, tests de contrôle |
| INTÉGRATION | pipeline-architect | **oui** | interfaces communes et assemblage |
| INTÉGRATION | experiment-engineer | | configurations, versions, journal des expériences |
| INTÉGRATION | performance-engineer | | temps, mémoire, grandes images |

**Responsables d'équipe.** Chacun :
- rassemble l'état de son équipe à la fin de chaque vague ;
- arbitre d'abord en interne les désaccords de son équipe ;
- ne remonte au chef d'orchestre que les désaccords entre équipes, ou ceux qu'il n'a pas pu trancher.

Un responsable n'a pas d'autorité sur les fichiers des autres membres.

**Indépendance de l'évaluation.** L'équipe ÉVALUATION ne construit pas la méthode. independent-evaluator est seul à connaître le contenu du test final et seul à le mesurer.

## 3. Propriété des fichiers (un seul rédacteur par fichier)

Les chemins ci-dessous n'existent pas encore. Chaque propriétaire les crée à son premier travail.

| Fichier ou dossier | Seul rédacteur |
| --- | --- |
| `CLAUDE.md`, `docs/team-structure.md`, `docs/research-brief.md`, `docs/communication-protocol.md`, `docs/recherche/concertations/` | chef d'orchestre |
| `docs/experiment-log.md`, `experiences/comptage_math/`, `scripts/math_lancer.py`, `out/comptage_math/experiences/` | experiment-engineer (le chef d'orchestre seulement quand il n'est pas actif) |
| `comptage_math/__init__.py`, `interfaces.py`, `pipeline.py` | pipeline-architect |
| `comptage_math/qualite.py` | image-analyst |
| `comptage_math/references.py`, `docs/recherche/conventions_comptage.md`, `data/comptage_math/references/` | annotation-manager |
| `docs/recherche/morphologie.md` | banana-morphology |
| `docs/recherche/bibliographie.md` | scientific-researcher |
| `comptage_math/feuille.py`, `comptage_math/simulateur.py` (D-013), `docs/recherche/modele_feuille.md` | leaf-mathematician |
| `comptage_math/geometrie.py` | plant-geometry |
| `comptage_math/gabarits.py` | leaf-template-engineer |
| `comptage_math/orientation.py` | orientation-engineer |
| `comptage_math/couleur.py` | vegetation-color-engineer |
| `comptage_math/votes.py`, `comptage_math/symetrie.py` (E-023) | convergence-engineer |
| `comptage_math/dense.py` (E-024 : distance aux trouées) | dense-canopy-engineer |
| `comptage_math/nettoyage.py` | detection-cleanup-engineer |
| `comptage_math/tuiles.py`, `scripts/math_performance.py` | performance-engineer |
| `scripts/math_evaluer.py`, `docs/recherche/test_final.md`, `out/comptage_math/evaluation/` | independent-evaluator |
| `scripts/math_erreurs.py` | error-analyst |
| `scripts/math_controles.py` | scientific-challenger |
| `docs/recherche/notes/<nom>.md`, `out/comptage_math/<nom>/` | l'agent `<nom>` |
| Tout le reste du dépôt (code, données, modèles, protocoles existants) | personne sans l'accord de Corentin |

**Changer de propriétaire.** Un fichier change de propriétaire par une décision D-NNN, prise sur demande de pipeline-architect ou d'un responsable. Le chef d'orchestre met alors cette table à jour.

**Besoin d'une modification chez un autre.** Un agent qui en a besoin ne la fait pas lui-même : il la demande au propriétaire (`docs/communication-protocol.md`, section 4).

**Note sur `data/comptage_math/` et `out/`.** Ils sont exclus de git par `.gitignore`, comme le reste de `data/` et de `out/`. Ce qui doit être versionné va dans `docs/`, `comptage_math/`, `scripts/` ou `experiences/`.

## 4. Vagues de travail (au plus six agents actifs à la fois)

Le chef d'orchestre peut changer cet ordre. Il note alors la raison dans le journal.

| Vague | Agents (6 au plus) | Ce qui doit en sortir | Porte de sortie |
| --- | --- | --- | --- |
| 0. Cadrage | annotation-manager, independent-evaluator, image-analyst, banana-morphology, scientific-researcher, pipeline-architect | inventaire et découpage ; proposition de test final et métriques ; qualité des images ; contraintes morphologiques ; bibliographie ; interfaces | **Corentin valide** le test final et le découpage ; commit des règles avant toute expérience |
| 1. Modèles et indices | leaf-mathematician, plant-geometry, orientation-engineer, leaf-template-engineer, vegetation-color-engineer, experiment-engineer | modèles de feuille et de plant, contraintes, champs d'orientation, gabarits, masques ; premières expériences E-NNN sur le développement | chaque hypothèse H a au moins une expérience réalisée, résultat consigné |
| 1 bis. Contradiction | scientific-challenger (avec deux ou trois agents de la vague 1 repris) | contrôles des hypothèses H1 à H8 | chaque objection close par une expérience ou une décision |
| 2. Comptage | convergence-engineer, dense-canopy-engineer, detection-cleanup-engineer, performance-engineer, independent-evaluator, error-analyst | candidats, séparation, nettoyage, temps par hectare ; mesures sur la validation ; analyse des erreurs | règle de choix finale écrite et commitée avant la mesure finale |
| 3. Test final | independent-evaluator (avec error-analyst après la mesure) | mesure unique de la méthode retenue et du v5 | résultats consignés tels quels |

Les agents en dehors de la vague en cours ne sont lancés que pour une concertation précise, sans dépasser six agents actifs.
