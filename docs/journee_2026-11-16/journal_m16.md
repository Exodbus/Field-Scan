# Journal m16 : robustesse à la basse résolution (maladies), 16/11/2026

Rédacteur : l'agent m16, lancé par la session principale. Règles : `CLAUDE.md` section 1, `docs/plan_nuit_2026-11-13.md` 4.3, et l'avenant `avenant_m16_basse_resolution.md`.

- **2 h 05.** Lecture de `CLAUDE.md`, de la règle 4.3, de l'avenant A1 et des scripts A1 (`a1_kaggle_pousser.py`, `a1_kaggle_banc.py`), du carnet m13 et de `m14_banc.py`.
- **2 h 10.** Constats avant l'avenant (fichiers existants, aucun calcul neuf sur le réglage) [O] :
  - photos éthiopiennes : 150 × 113 px, JPEG de qualité voisine de 75 (65 photos, une sur vingt) ;
  - d3b contient déjà `BasseRes` (p 0,3 ; 100 à 160 px ; sans JPEG) ;
  - d3b graines 0 à 3 : Éthiopie 120, 160, 157, 165 malades sans alerte (`bilan_graines.json`).
- **2 h 13.** Avenant écrit **avant tout envoi et toute mesure**. SHA-256 `bdcbab99…78f6da`, dans `empreinte_avenant_m16.txt`. Il fixe :
  - une seule variante : d3b + `ReduitJPEG` (p 0,4 ; côté 64 à 128 px ; JPEG 50 à 90 ; en tête des augmentations) ;
  - 4 graines (0 à 3), plis comme d3b ;
  - la règle 4.3 inchangée sur la moyenne des 4 graines, plus E1 (Éthiopie < 117, strict) et E2 (coût Éthiopie ≤ F1) ;
  - l'ordre des lectures et un plafond de 2 h de GPU.
- **2 h 14.** Carnet `notebooks/m16_entrainer_kaggle.py`, copie de m13 avec les seuls changements (a) à (d) de l'avenant. Test local de `ReduitJPEG` et de la chaîne d'augmentations complète (1 fil) : sortie 3 × 224 × 224, appliquée 385 fois sur 1 000.
- **2 h 15.** `scripts/m16_pousser.py --essai` : contrôles passés (empreinte de l'avenant, 19 lignes changées toutes attendues, recettes = d3b + 3 clés, dossier d'envoi = carnet + métadonnées, fuite des outils vide, refus des juges présents).
- **2 h 15.** Kaggle : `c16-lot1` COMPLETE, `a1-lot1` RUNNING : une place GPU libre.
- **2 h 16.** **Envoi de `affilecorentin/m16-lot1`** (version 1, T4 × 2, maître repris de `m13-lot1`). Statut RUNNING aussitôt.
- **2 h 17.** `scripts/m16_banc.py controle` (2 fils) : F1 33,94 et d3b 32,77 retrouvés ; F1 en Éthiopie 117 / 1 134 malades sans alerte, 28 / 155 saines en alerte, coût Éthiopie 49,02.
  - Écart d'écriture noté : l'avenant écrit « ≈ 49,01 » pour le coût Éthiopie de F1 ; la valeur exacte est 49,017 (49,02 arrondi). La règle E2 est « ≤ celui de F1 » : c'est la valeur exacte qui sert.
- **2 h 16 à 3 h 07.** Attente par `kernels status` toutes les 10 min (boucle en arrière-plan). `m16-lot1` COMPLETE à 3 h 07.
- **3 h 08.** `scripts/m16_banc.py recuperer` : 40 fichiers de probabilités, 4 recettes (`reduit_jpeg` 0,4 ; 64-128 ; 50-90 vérifiés dans `recette_m16g*.json`), 8 poids rangés dans `out/maladies/jour_1611/m16/lot1_poids/` (jamais commités). Journal Kaggle : maître repris de `m13-lot1`, 4 recettes de 20 à 21 min, 2 par carte, « fini en 49,0 min ; échecs : [] ». **GPU : ≈ 0,85 h** de session (plafond 2 h), aucun renvoi.
- **3 h 09.** `scripts/m16_banc.py mesurer`, **une seule lecture du réglage** [M] :
  - coûts m16g0 à g3 : 35,41 ; 34,61 ; 35,36 ; 34,98 ; moyenne 35,09 (F1 33,94 ; d3b g0 à g3 en moyenne 33,95) ;
  - Éthiopie, malades sans alerte : 179 ; 167 ; 174 ; 175 (moyenne 173,75, contre 117 pour F1) ; saines en alerte : 20 ; 21 ; 23 ; 23 (F1 28) ;
  - moyenne : 4.3 échoue sur le coût, la perte de plus de 2 points (Éthiopie) et le roamer (229,5 > 229) ; E1 et E2 échouent. Aucune graine ne passe seule.
- **3 h 10.** `out/maladies/jour_1611/m16_finalistes.md` : **aucun finaliste**. Juges et A1-test non lus (ordre des lectures). L'hypothèse « basse résolution » n'est pas confirmée : l'élève rate plus de malades éthiopiennes, en alertant un peu moins sur les saines.
- Rien n'est commité ni téléchargé hors des sorties de mon carnet ; aucun fichier existant modifié. Fichiers neufs : avenant, empreinte, ce journal, `notebooks/m16_entrainer_kaggle.py`, `scripts/m16_pousser.py`, `scripts/m16_banc.py`, `out/maladies/jour_1611/`.
