# Protocole de communication de l'équipe de recherche

Écrit le 7 novembre 2026. Ce document est tenu par la session principale, le chef d'orchestre. Il complète `CLAUDE.md` (règles communes) et `docs/team-structure.md` (composition, propriété des fichiers).

## 1. Principe : une étoile autour du chef d'orchestre

Ce protocole repose seulement sur les mécanismes réels de Claude Code 2.1.211.

- **Lancement.** Le chef d'orchestre lance un agent avec l'outil Agent (type = nom du profil). Il lui donne un brief qui contient :
  - l'objectif ;
  - les entrées ;
  - les fichiers qu'il peut écrire ;
  - ce qui est déjà exclu ;
  - le critère de fin.
- **Reprise.** Pour continuer avec un agent en gardant son contexte, le chef d'orchestre lui écrit avec SendMessage, à l'aide de l'identifiant renvoyé au lancement.
- **Pas d'agent qui en lance un autre.** Les profils ne contiennent ni l'outil Agent ni SendMessage. Un agent qui a besoin d'un autre passe par une **demande** (section 4), relayée par le chef d'orchestre. Cela garde le compte des agents actifs (six au plus) et la trace de chaque échange.
- **Mémoire partagée.** Elle passe par des fichiers. Chaque agent écrit dans ses propres notes (`docs/recherche/notes/<nom>.md`) et lit librement celles des autres.

## 2. Les canaux

| Canal | Qui écrit | Contenu |
| --- | --- | --- |
| Brief de lancement ou de reprise | chef d'orchestre | tâche, entrées, fichiers autorisés, critère de fin |
| Rapport final (section 3) | chaque agent, à la fin de chaque tâche | résultat, fichiers modifiés, demandes, désaccords |
| Notes `docs/recherche/notes/<nom>.md` | l'agent seul | journal de travail, mesures, commandes |
| Fiche de concertation `docs/recherche/concertations/C-NNN.md` | chef d'orchestre | question, positions, issue |
| `docs/experiment-log.md` | experiment-engineer | expériences E-NNN, décisions D-NNN |

## 3. Format du rapport final de chaque agent

```
STATUT : terminé | partiel (raison) | bloqué (raison)
FAITS OBSERVÉS [O] : … (image ou fichier nommé)
SOURCES [S] : … (référence exacte)
HYPOTHÈSES [H] : … (avec l'expérience qui les testerait)
RÉSULTATS MESURÉS [M] : … (E-NNN, commande, données de développement ou de validation)
FICHIERS MODIFIÉS : … (tous dans ma zone de propriété)
DEMANDES : destinataire | question | raison | bloquant ou non
DÉSACCORDS : avec qui | sur quoi | expérience ou décision proposée
SUITE PROPOSÉE : …
```

Un rapport qui annonce un score sans E-NNN est renvoyé à son auteur (règle 8).

## 4. Demandes entre agents

Une demande est **nécessaire** dès que :
- un agent a besoin d'une donnée, d'une mesure ou d'une interface qu'un autre produit ;
- un agent veut une modification dans un fichier qui ne lui appartient pas ;
- un résultat d'un agent contredit l'hypothèse ou le module d'un autre.

**Cheminement.**
1. L'agent écrit la demande dans son rapport (section 3).
2. Le chef d'orchestre la transmet au destinataire, en le lançant ou en le reprenant, sans dépasser six agents actifs.
3. Il rapporte la réponse au demandeur.

**Demande bloquante.** Si la demande bloque le travail, l'agent s'arrête avec le statut « bloqué » au lieu de contourner le problème. Il ne modifie jamais lui-même le fichier d'un autre.

## 5. Concertations

### 5.1 Quand en ouvrir une

- **Désaccord technique** entre deux agents : par exemple, l'orientation donnée par les gabarits contre celle du tenseur de structure, ou qui décide que deux pics sont un seul plant.
- **Dépendance entre modules** : création ou changement d'une interface, ou paramètre partagé (rayon de vote, échelle, règle de fusion).
- **Résultat qui réfute une hypothèse** sur laquelle d'autres modules reposent.
- **Objection de scientific-challenger** non close.
- **Toute question qui touche au test final.** independent-evaluator y participe toujours.

### 5.2 Comment elle se déroule

1. Le chef d'orchestre ouvre la fiche `C-NNN`. Elle contient :
   - la question, en une phrase ;
   - les participants, de deux à quatre agents, dont les responsables des équipes touchées ;
   - ce qui est déjà établi, avec les étiquettes [O], [S], [M].
2. Chaque participant donne sa position dans un rapport, avec :
   - les faits et les mesures qui l'appuient ;
   - l'expérience qui la départagerait ;
   - ce qu'il accepterait comme réfutation.
3. Le chef d'orchestre transmet les positions aux autres participants. Il y a un seul tour de réponse, deux au plus.
4. **Issue obligatoire** (règle 5) :
   - soit une **décision** D-NNN : ce qui est décidé, par qui, pourquoi, et ce qui la remettrait en cause ;
   - soit une **expérience** E-NNN : hypothèse, données, critère fixé avec independent-evaluator, responsable.

   « On verra plus tard » n'est pas une issue.
5. experiment-engineer consigne l'issue dans `docs/experiment-log.md`. La fiche C-NNN renvoie à cette entrée.

### 5.3 Arbitrage

- Un désaccord interne à une équipe est d'abord tranché par son responsable.
- Un désaccord entre équipes est tranché par le chef d'orchestre, de préférence par une expérience.
- Ce qui touche aux règles du projet est tranché par Corentin : test final, découpage, adoption, modification de l'existant, téléchargement, commit.

## 6. Escalade vers Corentin

Le chef d'orchestre soumet à Corentin, en une question claire, sans rien faire d'irréversible avant la réponse :
- le choix du test final et du découpage ;
- toute règle d'adoption ou de choix final, avant les résultats ;
- tout téléchargement : données, bibliothèque, PDF ;
- toute modification de l'existant : `fieldscan/`, `run.py`, `config.yaml`, scripts, données, protocoles ;
- tout commit et tout push ;
- tout besoin qui supposerait une annotation à la main. La réponse attendue est non : il faut chercher une autre voie.

## 7. Ce qui ne circule jamais

- Une image, un chiffre ou une liste d'erreurs du test final avant la mesure finale (seul independent-evaluator y a accès).
- Un score sans E-NNN.
- Une clé d'API, un identifiant ou un mot de passe.
- Une affirmation de mémoire présentée comme une source.

## 8. Rythme

- Chaque vague (`docs/team-structure.md`, section 4) se termine par un rapport de chaque responsable d'équipe concerné. Le chef d'orchestre en fait la synthèse pour Corentin.
- Un agent qui n'avance plus, par exemple après plusieurs essais sans information nouvelle, s'arrête selon ses conditions d'arrêt et rend un rapport « partiel ». Il ne boucle pas.
