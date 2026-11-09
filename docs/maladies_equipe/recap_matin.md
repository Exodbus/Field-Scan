# Récapitulatif de la nuit du 8 au 9 novembre 2026 : module maladies

Détail heure par heure : `docs/maladies_equipe/journal.md`. Règles et résultats de chaque version : `docs/protocole_maladies_*.md`. **Rien n'a été commité.**

## En une phrase

**La v2 ConvNeXt de ton binôme reste le meilleur modèle** : aucune des versions de la nuit (v5, v7, v8, v9) ni aucune méthode mathématique ne la bat sans régression, selon des règles écrites avant chaque mesure. La nuit a surtout produit des mesures solides et des limites claires, utiles pour le rapport.

## Les modèles de la nuit

| Version | Idée | Verdict (règle écrite avant) | Point clé |
| --- | --- | --- | --- |
| **v2** (binôme) | 3 ConvNeXt, Tanzanie + Pérou | **reste dans la chaîne** | validation F1 0,960 ; BananaLSD Sigatoka 94 % ; banana-buddy fusariose 73 % (réserve : voir section 9 du protocole v5) |
| v5 | + khadavy, TDTU, classe « autre maladie » | non adoptée | plus de fausses alertes (3,0 % contre 0,7 %) ; la classe « autre » ne généralise pas : inconnues dites Sigatoka 89 % contre 69 % |
| v7 | v5 + feuilles ROAMER vues de loin | non adoptée | mêmes régressions que la v5 ; pas de gain de loin |
| **v8** | v2 + feuilles ROAMER de loin (3 classes) | non adoptée (gain de loin manqué) | **passe toute la non-régression**, un peu meilleure en gros plan hors domaine (BananaLSD Sigatoka 95,1 %, banana-buddy fausses alertes 1,3 % contre 3,9 %), mais plus mauvaise de loin |
| v9 | classeur spécialisé « de loin » (saine / malade) | règle remplie, **à ne pas intégrer** | AUC 0,870 contre 0,672 sur le robot ROAMER, mais 0,639 contre 0,629 sur des photos de téléphone : raccourci propre au robot |

## Ce que l'équipe a appris (5 agents)

- **Maths seules** (couleur, texture, forme, orientation des stries) : loin du réseau (F1 0,71 à 0,76 contre 0,96). Un indicateur robuste et explicable : la texture des nervures « cassée » par la maladie. Les stries parallèles aux nervures ne distinguent pas les maladies.
- **Fusion maths + IA** : échoue partout (améliore le développement, dégrade la validation et le Bangladesh). Une seule réussite : la **mise à l'échelle de température** (T = 0,60), qui rend les probabilités affichées fiables sans changer les décisions.
- **Vue de loin** : le problème n'est pas de trouver la feuille (même un recadrage parfait ne bat pas l'image entière), mais d'avoir des données de loin variées. Toutes les données ROAMER viennent d'un seul robot : elles ne suffisent pas. **La vue de loin reste non résolue**, à écrire comme limite.
- **Première mesure de la fusariose hors de Tanzanie** (banana-buddy, Sri Lanka probable, jeu déjà consulté) : la v2 en nomme 73 %. Alerte de fuite du binôme (9 novembre) vérifiée : les copies tanzaniennes qu'il a trouvées sont les photos `Image_N`, déjà exclues de notre liste ; reste à comparer la liste aux 8 765 photos de Tanzanie 2022-2023 non téléchargées (détail : `docs/protocole_maladies_v3_convnext.md`, section 9).

## Ce qui t'attend (ton accord)

1. **Sécurité** : **régénérer la clé API Roboflow** (elle est apparue dans un message d'erreur de la nuit) et **révoquer le premier jeton Kaggle** (capture d'écran d'hier soir) si ce n'est pas fait.
2. **Commit** des fichiers de la nuit, sur la branche `maladies/test-khadavy` (PR Exodbus/Field-Scan#1) :
   - protocoles : `docs/protocole_maladies_v3_convnext.md` (résultats v5), `docs/protocole_maladies_v7.md`, `v8.md`, `v9_loin.md` ;
   - équipe : `docs/maladies_equipe/` (brief, fiches des 5 agents, journal, ce récapitulatif) ;
   - scripts : `scripts/preparer_recadrages_v7.py`, `preparer_feuilles_val_loin.py`, `mesurer_adoption_v5.py`, `mesurer_adoption_loin.py` ; carnets `notebooks/entrainer_maladies_v7_kaggle.py`, `v8`, `v9_loin`.
   - à ne pas commiter : les poids (`modeles/maladies_v*_kaggle/`, `modeles/maladies_binome/`) et les données.
3. **Décision possible (la tienne, pas celle de la règle)** : la v8 est un candidat sérieux pour les **gros plans** (aucune régression, un peu meilleure hors domaine), mais l'adopter maintenant serait une décision prise après avoir vu ses résultats, en partie sur un jeu consulté. Je recommande de garder la v2 et de citer la v8 dans le rapport comme essai.
4. **Ménage** (si tu veux) : 6 projets ROAMER copiés dans ton espace Roboflow ; sur ton Kaggle, 5 jeux privés (`maladies-v2-binome`, `roamer-recadrages-v7`, `roamer-val-loin-feuilles`, `roamer-dev-loin-feuilles`, `test-banana-buddy`) et 5 carnets créés cette nuit.

## Pour le rapport

- Tableau des versions ci-dessus, avec la phrase : « chaque version a été jugée par une règle écrite avant l'entraînement ; aucune n'a battu la v2 sans régression ».
- Limites : vue de loin non résolue ; maladies inconnues rangées dans la Sigatoka (69 % au Bangladesh) ; Sigatoka jaune prise pour la fusariose ; test khadavy à 0,62 de F1 (taches précoces).
