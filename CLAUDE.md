# Field Scan : consignes pour Claude Code

Field Scan est le projet ING4 « Intelligence Lab » de Corentin. Une chaîne IA (`run.py`) transforme des images aériennes de bananeraies en bulletin de santé par parcelle. Elle couvre le comptage des pieds, la vigueur, le stress hydrique et les maladies.

Où trouver le contexte :
- présentation générale : `README.md` ;
- données : `docs/carnet_de_donnees.md` ;
- règles et résultats de chaque version : les protocoles `docs/protocole_*.md`.

Ce fichier s'applique à toutes les sessions et à tous les sous-agents ouverts dans ce dépôt.

## 1. Règles permanentes du projet

- **Langue** : français partout (réponses, code commenté, documents).
- **Protocole** :
  - toute règle de choix (modèle, époque, seuil, paramètre, adoption) est écrite et commitée avant de voir les résultats qu'elle départage ;
  - le test n'est regardé qu'une fois ;
  - **aucune décision de modèle ou de seuil n'est prise sur un test**.
- **Aucune annotation à la main.** Corentin n'annote plus rien et on ne le lui demande pas. Seules les annotations existantes servent de référence. Une pré-annotation produite par un modèle n'est jamais une référence.
- **Découpage** : par site, parcelle, vol ou pays, jamais au hasard. Chaque nouveau jeu passe un contrôle de fuite : nom de photo d'origine, MD5, recouvrement entre photos voisines.
- **Git** : commit et push seulement avec l'accord explicite de Corentin, demandé à chaque fois. Fichiers à ne jamais commiter :
  - `CONTEXTE_FIELD_SCAN.md` ;
  - `dataverse_fichiers.json` ;
  - `modeles/maladies/meilleur_v*.pt`.
- **Téléchargements** : tout téléchargement demande l'accord explicite de Corentin, qu'il s'agisse de données, d'une bibliothèque Python, d'un modèle ou d'un PDF à enregistrer. Les données téléchargées vont dans un dossier à elles et ne sont jamais exécutées.
- **Secrets** : aucune clé d'API, aucun identifiant ni mot de passe, ni dans le dépôt ni dans les échanges.
- **Aucun service payant**, aucun compte à créer.
- **Préserver l'existant** : `fieldscan/`, `run.py`, `config.yaml`, les scripts déjà présents dans `scripts/`, `notebooks/`, `data/`, `modeles/` et les protocoles `docs/protocole_*.md` ne sont modifiés qu'avec l'accord de Corentin.
- **Python** :
  - lancement : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u script.py` (Python 3.14) ;
  - en mode `-I`, le dossier du script n'est pas dans le chemin : chaque script ajoute lui-même la racine du dépôt à `sys.path` ;
  - fichiers toujours en UTF-8 ; zips créés avec Python, chemins au format posix.
- **Bibliothèques** :
  - installées : numpy, scipy, OpenCV (headless), kornia, torch (processeur), rasterio, geopandas, shapely, pandas, matplotlib, Pillow, onnxruntime, PyYAML ;
  - absentes : scikit-image et scikit-learn. En ajouter une est un téléchargement, donc soumis à accord.
- **Matériel** : processeur à 8 cœurs, pas de GPU local. Les GPU gratuits (Kaggle, Colab) ne sont lancés que par Corentin.

## 2. Équipe de recherche : comptage mathématique des plants principaux

L'équipe construit une méthode mathématique, à base de modèles explicites et non d'un réseau appris, pour compter les plants principaux (pieds mères) de bananiers sur des images aériennes.

Documents de l'équipe :

| Document | Contenu |
| --- | --- |
| `docs/team-structure.md` | composition, responsabilités, propriété des fichiers, vagues |
| `docs/research-brief.md` | problème, connaissances établies, hypothèses, inconnues, options de test |
| `docs/communication-protocol.md` | demandes, concertations, rapports, escalade |
| `docs/experiment-log.md` | journal des expériences et des décisions |
| `.claude/agents/*.md` | les 18 profils |

### Règles communes

1. **La fonction originale de Philemon est inconnue.** Les gaussiennes, formes, couleurs, stries et orientations sont des indices issus d'une présentation orale. Personne n'écrit « la fonction de Philemon » : on écrit « formulation compatible avec l'indice X ».
2. **Distinguer faits observés, sources, hypothèses et résultats mesurés.** Chaque affirmation porte une étiquette :
   - **[O]** observé : sur une image nommée, ou dans un fichier ;
   - **[S]** source : référence exacte ;
   - **[H]** hypothèse ;
   - **[M]** mesuré : identifiant d'expérience E-NNN et commande.
3. **Chaque proposition conduit à une expérience** capable de la confirmer ou de la réfuter. Le critère est écrit avant le lancement.
4. **Les agents se concertent** lors des désaccords techniques et des dépendances entre modules (`docs/communication-protocol.md`, section 5).
5. **Chaque concertation produit une décision (D-NNN) ou une expérience précise (E-NNN).**
6. **Aucun fichier n'est modifié simultanément par plusieurs agents.** Chaque fichier a un seul rédacteur (`docs/team-structure.md`, section 3).
7. **Aucun réglage sur le test final.** Le réglage se fait sur le développement. La validation sert à mesurer selon des règles écrites avant. Le test est mesuré une fois, par independent-evaluator.
8. **Aucun score n'est annoncé sans annotations et évaluation** : une référence annotée existante, le code d'independent-evaluator, un identifiant E-NNN.
9. **Au maximum six agents actifs simultanément au démarrage.** Les vagues sont décrites dans `docs/team-structure.md`, section 4.
10. **Aucun service payant à lancer.**

### Rôle de la session principale : chef d'orchestre

La session principale :
- **pilote** : elle ne développe pas les modules confiés aux agents ;
- **lance** les agents avec l'outil Agent (type = nom du profil), au plus six actifs à la fois. Avant chaque lancement parallèle, elle vérifie dans la table de propriété que les zones d'écriture des agents ne se recoupent pas ;
- **transmet** les demandes d'un agent à un autre, en reprenant un agent avec son contexte par SendMessage, avec son identifiant. Les sous-agents ne lancent pas d'autres agents : l'outil Agent ne figure pas dans leurs profils ;
- **organise les concertations**, rédige leur fiche (`docs/recherche/concertations/C-NNN.md`) et fait consigner la décision ou l'expérience dans `docs/experiment-log.md` ;
- **tient** ce fichier, `docs/team-structure.md`, `docs/research-brief.md` et `docs/communication-protocol.md`. Elle n'écrit dans `docs/experiment-log.md` que lorsqu'experiment-engineer n'est pas actif ;
- **vérifie** les rapports avant de les relayer : un rapport n'est pas une preuve. Elle relit les fichiers et les chiffres annoncés ;
- **soumet à Corentin** : le test final et le découpage, toute adoption, tout téléchargement, toute modification de l'existant, tout commit ;
- **n'annonce aucun score** sans identifiant E-NNN ni évaluation d'independent-evaluator.
