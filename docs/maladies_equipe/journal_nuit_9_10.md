# Journal de la nuit du 9 au 10 novembre 2026 (module maladies)

Rien n'est commité cette nuit (consigne de Corentin). L'empreinte SHA-256 de chaque protocole est notée ici avant toute mesure.

| Heure | Événement |
| --- | --- |
| avant 01:20 | Demande de Corentin : « fais-moi un module meilleur », carte blanche, ne rien demander. Récap du binôme (artefact) illisible : introuvable pour ce compte. |
| avant 01:20 | Recherche web (sous-agent) : jeu Mendeley wfzpdmc5vx (Cordana, Pestalotiopsis), DINOv3 timm non restreint, outlier exposure (Fort et al. 2021). |
| 01:20 | Téléchargement de wfzpdmc5vx (424 photos, SHA-256 vérifiés), contrôle de fuites lancé. BLADE écarté : tableau de caractéristiques, pas d'images. |
| 01:23 | Protocole docs/protocole_maladies_cinq_classes.md écrit avant tout entraînement ; SHA-256 3e6f4004bcb2a7a1b5581f312af8198bcbf91fec818ee3fd9e95eaf4cf025e88 |
| 01:29 | Kaggle : maladies-nuit créé (wfzpdmc5vx sans les 2 copies de banana_buddy : 422 photos ; PSFD 738 ; Éthiopie 1 289). Essais locaux des 3 réseaux réussis. Lancés : entrainer-maladies-cinq-d5 et entrainer-maladies-cinq-c5 (version 1). |
| 01:31 | Les deux carnets échouent au démarrage, avant tout calcul : images.csv s'appelle images_ajouts.csv dans le jeu Kaggle. Corrigé, relancés (version 2). |
| 01:43 | Aiguilleur réajusté et enregistré (modeles/maladies_aiguilleur/, mesures de la partie A retrouvées à l'identique). Module maladies généralisé (3 ou 5 classes, ConvNeXt ou ViT, deux branches, température). Contrôle d'intégration avec la soupe : réussi. Températures en validation : v2 0,59, soupe 0,61. |
| 01:44 | Amendement 1 (E5 en attente d'un GPU ; ajout de L5, DINOv2 ViT-L, 2 réseaux), avant tout résultat ; SHA-256 du protocole 5670007ec940559e5e2a02daf0f0462f296e9892904329389b4dee2d9fb58eb6 |
| 01:46 | Planche de contrôle de wfzpdmc5vx (out/maladies/mendeley_bd/planche_classes.jpg) : étiquettes plausibles (Cordana : taches ovales à halo jaune ; Pestalotiopsis : taches gris-brun ; Sigatoka : stries). Dossier Kaggle de L5 prêt, lancé dès qu'un GPU se libère après C5 et D5. |
| 02:17 | Prédictions locales de la v2 sur TDTU, PSFD, Éthiopie : faites. La soupe échouait (noms de poids hors du motif de classifieur.charger) : relancée avec le chargeur du module de la chaîne, puis DINOv2-FT. |
| 03:04 | C5 et D5 terminés (Kaggle, sans relance), sorties rapatriées. E5 lancé à 02:18. L5 lancé. |
| 03:05 | Script de mesure essayé sur de faux fichiers (sorties des essais locaux, classes recopiées) : il tourne de bout en bout. Aucune mesure réelle encore : on attend E5 et les prédictions locales de la soupe et de DINOv2-FT. |
| 03:24 | Prédictions locales finies : v2, soupe, DINOv2-FT sur TDTU (1 636), Éthiopie (1 289), PSFD (738). |
| 03:45 | E5 terminé (Kaggle, sans relance). Avant la mesure unique : SHA-256 du protocole 5670007ec940559e5e2a02daf0f0462f296e9892904329389b4dee2d9fb58eb6 (inchangé depuis l'amendement 1). |
| 03:47 | Mesure unique faite (C5, D5, E5, C5 + D5 avec v2, soupe, DINOv2-FT) : aucun candidat adoptable, branche « proche » = soupe (section 6 du protocole). L5 sera mesuré à part (amendement 1). |
| 03:48 | Chaîne complète (run.py, module maladies seul, photos de démonstration) : tourne, deux branches actives. Amendement 2 écrit avant calcul (« je ne sais pas » avec P(malade) au-dessus du seuil d'alerte) ; SHA-256 aa038b7b2736bbc6bff04c526bff284d5324e9b629536ebc1ce98eeaaf98cb9f |
| 03:49 | Amendement 2 mesuré : politique (b) adoptée (coût de validation 233 -> 33) et intégrée (jnsp_alerte). |
| 03:53 | Contrôle d'intégration (soupe + aiguilleur + v2 de loin + politique b) : réussi. |
| 04:12 | Module complet comparé à l'ancienne chaîne (rapport, sans décision) : malades sans alerte, validation 107 -> 9, BananaLSD 88 -> 0, TDTU 424 -> 264, PSFD 490 -> 377, Éthiopie 592 -> 414 ; fausses alertes en validation 7 -> 15 / 1 000. README mis à jour. |
| 04:12 | Amendement 3 écrit avant calcul (politique b pour la branche « loin », décision sur dev_loin) ; SHA-256 e6410ea7f8b785d1bec62c0bd2dd9914927eb553c4a429f72a328e8195383d55 |
| 04:30 | L5 version 1 : réseau 1 entraîné en entier (6 époques), puis manque de mémoire GPU au début du réseau 2 (le réseau 1 restait sur le GPU). Relance technique (version 2) : réseaux finis gardés sur le processeur, réseau 1 repris tel quel (jeu Kaggle maladies-l5-reseau1), seul le réseau 2 est entraîné. |
| 04:52 | Amendement 3 mesuré : politique (b) adoptée aussi pour la branche « loin » (coût dev_loin 934 -> 423 ; saines en alerte 98 -> 345 / 438). Alertes « loin » de confiance faible dans le bulletin. |
| 04:55 | Module complet recalculé avec l'amendement 3 (TDTU 424 -> 153 malades sans alerte, saines en alerte 59 -> 119). Contrôle d'intégration et chaîne de démonstration : réussis. |
| 06:13 | L5 version 2 terminé (Kaggle) : réseau 1 repris, réseau 2 entraîné (6 époques), sorties rapatriées (out/maladies/cinq_classes/kaggle/l5/). La règle de la v2 retient la moyenne des 2 réseaux (coût de validation 21 contre 36 pour un réseau). Avant la mesure de L5 : SHA-256 du protocole 612ead63442b071d1718350b4323fd6524face86ccbbf0e441628be45ec35d10. Depuis l'amendement 1, seuls ont été ajoutés les résultats (section 6), les amendements 2 et 3 et la note de relance ; les sections 2, 3 et 5 sont inchangées. |
| 06:15 | Mesure de L5 (amendement 1, même script et même règle) : non adoptable (Sigatoka nommée sur BananaLSD 388 / 473 ; gain ; maladies inconnues dites saines sur TDTU, PSFD et l'Éthiopie). Garde 82 / 334, la meilleure de la nuit ; noms nouveaux justes 84 %. Choix refait avec tous les candidats : la branche « proche » reste la soupe, la chaîne ne change pas. Résultat écrit dans le protocole. |
