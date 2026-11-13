# Verdicts du Contrôleur sur les finalistes (nuit du 12 au 13 novembre 2026)

Agent Contrôleur (contradicteur). Règles : `docs/plan_nuit_2026-11-12.md` (SHA-256 vérifié à 0 h 21 : 7b19e2215c4717363d9e9db1b374b806e8fe78d1693a49fd352f322af6d4df48, identique à l'empreinte de 22 h 14), sections 2, 3.4, 3.5, 4.4, 4.5. Journal : `docs/nuit_2026-11-12/journal_controleur.md`. Je n'ai lu **aucun juge ni aucun test vierge** : tous mes calculs portent sur les probabilités ou cartes en cache des jeux de réglage.

Verdicts possibles : ADMIS, ADMIS AVEC RÉSERVE, REFUSÉ. Je ne peux pas ajouter de candidat.

*Version 12, 7 h 00 : LISTE GELÉE ci-dessous.* *Version 11, 6 h 44 (graines du v6f : réserve renforcée).* *Version 10, 5 h 46 (comptage entraîné : v6f, v6a, v6d).* *Version 9, 4 h 27 (comptage banc, liste de 4 h 22 : E10_moy_v6e+v5 admis, E10_p90_v6b sans objet).* *Version 8, 4 h 10 (famille C maladies : C_quatre_v12a14 ; règle de gel reçue).* *Version 7, 3 h 22 (modèles finaux a13 et a14 contrôlés).* *Version 6, 2 h 53 (liste v12 de 2 h 55 : a13, a14, a4).* *Version 5, 2 h 16 (v12a9 et v12a10 contrôlés).* *Version 4, 1 h 45 (comptage banc réécrit à 1 h 36 : E10 entre, E3 sort ; v12a7 contrôlé d'avance).* *Version 3, 1 h 30. Finalistes présents : maladies sans entraînement (M-banc, réécrit à 0 h 39 sans changement), maladies entraînées (v12a4), comptage banc (C-banc). Attendu : comptage entraîné ; v12a7 annoncé par M-entraîneur.*

## LISTE GELÉE (7 h 00) : les seuls finalistes que le Juge lit

Règle appliquée : `docs/nuit_2026-11-12/regle_gel_finalistes.md` (SHA-256 recalculé à 6 h 59 : 73017722045aa8711af85c59cdcde8aa0cb3ef613122d1f1e43aa0bec231b6ab ; plan de nuit toujours 7b19e2215c4717363d9e9db1b374b806e8fe78d1693a49fd352f322af6d4df48). Candidats pris en compte : ceux écrits dans un `finalistes.md` (ou `finalistes_famille_c.md`) **et** admis par moi avant 6 h 45 (aucune admission après). Fichiers de finalistes vérifiés inchangés de 6 h 42 à 6 h 59.

### Maladies (score = coût moyen de réglage, le plus bas d'abord)

| Famille | Candidats admis (coût de réglage) |
| --- | --- |
| A, mélanges anciens | F1_trois_morceaux2x2 35,96 ; F2_trois_384_512 36,48 ; F3_trois 37,83 |
| B, v12 seul | v12a13 41,50 ; v12a14 42,28 ; v12a4 47,89 |
| C, mélange avec un v12 | C_quatre_v12a14 36,07 |

| Place | Finaliste gelé | Famille | Coût de réglage | Pourquoi cette place |
| --- | --- | --- | --- | --- |
| 1 | **F1_trois_morceaux2x2** (t = 0,70) | A | 35,96 | meilleur toutes familles (écart 0,11 avec le suivant, > 0,001) |
| 2 | **C_quatre_v12a14** (t = 0,76) | C | 36,07 | meilleur d'une autre famille que A |
| 3 | **v12a13** (seuils de la v10b) | B | 41,50 | meilleur de la troisième famille |

Non retenus par la règle (admis, mais hors liste) : F2, F3, v12a14 seul, v12a4. Ils ne sont pas lus sur les juges.

### Comptage (score = moyenne des 5 F1 de réglage, la plus haute d'abord ; chiffres ONNX du banc)

| Famille | Candidats admis (moyenne des 5 F1) |
| --- | --- |
| A, anciens seuls | E5p90b_moy34_v5_d0.1 0,8549 ; E7_union_v5+v3_d0.05_r30 0,8352 |
| B, v6 seul | v6f (graine 0) 0,8780 (carnet 0,8771) ; v6a 0,8740 ; v6d 0,8710 |
| C, mélange ou aiguillage avec un v6 | E10_moy_v6e+v5 0,8822 |

| Place | Finaliste gelé | Famille | Moyenne des 5 F1 | Pourquoi cette place |
| --- | --- | --- | --- | --- |
| 1 | **E10_moy_v6e+v5** (seuil 0,30) | C | 0,8822 | meilleur toutes familles (écart 0,004 avec v6f) |
| 2 | **v6f, graine 0** (seuil 0,35) | B | 0,8780 | meilleur d'une autre famille que C |
| 3 | **E5p90b_moy34_v5_d0.1** (seuil 0,30) | A | 0,8549 | meilleur de la troisième famille |

Non retenus : v6a, v6d, E7. Rappel pour le Juge : pour E5p90b (il contient le v3, réglé sur segmento est), la moyenne des juges doit aussi être donnée **sans segmento est**.

### Réserves à lire avec les chiffres des juges (détail dans les sections 1 à 4)

- **F1** : 1 733 essais de M-banc ; optimisme de la recherche ≈ 2,7 points ; la moitié de l'avance des morceaux 2 × 2 sur F3 vient du seuil ; fausses alertes TDTU 241 / 577 (risque pour la limite BanSpot ≤ 61 / 646) ; ≈ 10 s par photo proche ; la lecture 2 × 2 n'existe pas encore sur les juges.
- **C_quatre_v12a14** : optimisme ≈ 4 points (le plus fort) ; avance sur F3 de −1,8 ± 0,9 (bruit) ; fausses alertes TDTU 260 / 577, Tanzanie 68 à 69 / 1 000 ; ≈ 5 s par photo ; v12a14 appris sur TDTU, l'Éthiopie et 1 405 photos du Bangladesh (pays du test vierge).
- **v12a13** : choisi parmi 44 recettes (≈ 1 point d'optimisme) ; aucun seuil réglé ; modèle final : 60 / 1 000 saines en alerte en Tanzanie ; Bangladesh appris (pays du test vierge).
- **Les trois maladies** : la v10b a été installée par le binôme après lecture de BanSpot ; la soupe et la v2 ont appris le même jeu péruvien que la Cordana du Pérou.
- **Les trois comptages** : tout le gain de réglage vient de btd_val ; hors btd, aucun ne bat le v5 en service (E10_moy 0,855, v6f 0,851, E5p90b 0,852, contre 0,854) ; gain nul sur banano_finca. Aucun juge ni le test vierge ne contient de plantation jeune espacée : les juges ne peuvent montrer que la non-régression. E10_moy et v6f ont appris btd_train. v6f est une graine chanceuse (sa graine 1 échoue à la règle). E5p90b : sur du dense à 11 cm/px, 39 % des images partent vers v3 + v4 (le test vierge est à ≈ 11 cm/px). Une tuile d'apprentissage dmpcs2 du v6e est à 5 bits de dHash d'une tuile « sans bananier » de juge (faux positif selon C-prospection).

### Fichiers et empreintes exacts (SHA-256, recalculés à 6 h 41 ; `out/controle_nuit_1112/empreintes_liste_gelee.txt`)

Maladies : F1 = v10b + soupe + v2 + aiguilleur ; C_quatre = les mêmes + v12a14 ; v12a13 = v12a13 + v2 + aiguilleur (branche loin). Comptage : E10_moy = v5 + v6e ; v6f = v6f seul ; E5p90b = v3 + v4 + v5. Code de décision : `scripts/m12_banc_finalistes.py` (M-banc), `fieldscan/modules/maladies.py`, `scripts/v6_banc_*.py` (C-banc) ; deuxième avis : mes `scripts/controle_nuit_*_appliquer.py`.

```
cdb4091179ed5389b97b5e1d30735224069c096b2c51de17fba3c2a32195b0dd  modeles/maladies_binome/v10b/maladies_v10b_0.pt
b09cd2a544477b28ea48048192f6f75ace61b6bb7491b102e655c0f551395378  modeles/maladies_binome/v10b/maladies_v10b_1.pt
cce6222527df7360f947089f645c44911f4bac00a50b9ab801e3ca09961dcef8  modeles/maladies_binome/v10b/maladies_v10b_2.pt
c8add9b2f3d0ac0c9e9fed1323f96055e4479b15c3b6abcf12254b1a0a29404c  modeles/maladies_binome/v10b/seuils.json
b707bf75542daeabfe39518cec6eb4716942681b77507d7bff33a5e6748011bd  modeles/maladies_soupe_v2_v8/poids/maladies_soupe_convnext_tiny_1.pt
8ce41ace3bdf5c252aca9b7eb938a4d86a2d7887534979774696333b94c75f99  modeles/maladies_soupe_v2_v8/poids/maladies_soupe_convnext_tiny_2.pt
8386d304b7f5223fff4ba3bf6b6e8f3fe662108ddd03b47e300b2280c67f8d71  modeles/maladies_soupe_v2_v8/poids/maladies_soupe_convnext_tiny_3.pt
3c15a3fbe3428700df84e4af8fcf7f9f5b4eb5d8c264f57868e35feb291ea86d  modeles/maladies_soupe_v2_v8/poids/seuils.json
276630d275c32c83a6f05942d6eb00036980c1a0a5fdb3c7130ab848265229b7  modeles/maladies_binome/maladies_v2/poids/maladies_v2_convnext_tiny_1.pt
1ad6e8981463a36eeefe5b130c709c8a3fb00de42779c0f6afd062da561db683  modeles/maladies_binome/maladies_v2/poids/maladies_v2_convnext_tiny_2.pt
711a202fc6f2d151c2ee75bf82d89f085ea02df35d0b6ad6d4bfdf2afff4e395  modeles/maladies_binome/maladies_v2/poids/maladies_v2_convnext_tiny_3.pt
a5a52d957b172a86e7737f8903a6f0bb3bf798af84321d0a56d374e80e4fd418  modeles/maladies_binome/maladies_v2/poids/seuils.json
4eaaf855d6f4ce8a543552d3767f79bc73467a81416f025ceea8551232351c23  modeles/maladies_aiguilleur/aiguilleur.npz
d38246afb6a3cc07e2072a38376bf6ea843667a1497b85c17828fb5059a72982  modeles/maladies_v12_essais/v12a14/maladies_v12a14_0.pt
aa56c54e139142fc294859dc0cb1272cd6fc0086f1ef44d4c9e1be4d044c1046  modeles/maladies_v12_essais/v12a14/maladies_v12a14_1.pt
9dc36406b26938fb995449ffd74c5e1ba06b314646f152139949ab001540caaa  modeles/maladies_v12_essais/v12a14/maladies_v12a14_2.pt
6c55cf6a4498e5b1e92a2405b902c09d2223879e043a14550128b5e4a4d2996f  modeles/maladies_v12_essais/v12a14/seuils.json
3d2a5da451f453da632622ae00ff30ff3b59b0a572a4135a2675a7222d8a3b73  modeles/maladies_v12_essais/v12a13/maladies_v12a13_0.pt
07cdfd53d29f1570ab486addeb6a42daff1c0ec50398af4ec42f9beff9aa5aa3  modeles/maladies_v12_essais/v12a13/maladies_v12a13_1.pt
427ea28930f70ac0b3e2de22b52b146939e71ff3d006ca285b84b193379e698d  modeles/maladies_v12_essais/v12a13/maladies_v12a13_2.pt
1fbb8223ae89a637c45edb55aaf31bbfc0dbc34a0588cf14998d64ddd7ce2e04  modeles/maladies_v12_essais/v12a13/seuils.json
b112a4945ada3dde17167e0b68af17affc0403afc7efc1dbeea82b55d160c0ae  modeles/centres_5cm_v3.onnx
b776af75d6709bfc8927d5f0e2f2f45cb33288faf998f2dd1597ea81290a7fb2  modeles/centres_5cm_v4.onnx
12f9b4caa5735767c454de99edf1a6616765718243555f8559c2cfcc0722f1ea  modeles/centres_5cm_v5.onnx
93fb659befd669e229a6af50eb08c83968468219b483e1b48ee9b8c993737f01  modeles/comptage_v6_essais/centres_5cm_v6e.onnx
49602a142a8c7ebacddf761cddb337a9001d5a24e655df8e001716544f4a80af  modeles/comptage_v6_essais/centres_5cm_v6f.onnx
54952aeb2d6ce7dd86b115e4870f48789d3fea52e526aec57bfd924d33e8c51f  scripts/m12_banc_finalistes.py
0762c999f60b87690dda535adb24b2be912965c89a90efa1e14adc8055a716da  scripts/m12_banc_commun.py
09a82097166858a37e34deb883a0a500dbe1906df9b8d39c4d92dbcfaa3d5239  scripts/v6_banc_commun.py
25c718b81d6190ee2f9aec496129067cadd34ddaf817cfcbd0fd3e02993b801c  scripts/v6_banc_candidats.py
b3351f422fc1dad7d6b6e18f2a78bf70cf968513eadf4334567904bd04937753  scripts/controle_nuit_m_appliquer.py
248674ed49feb831595611c9a4321d97d8f1686fdc217906e0615c165c5ef813  scripts/controle_nuit_c_appliquer.py
14916db8899528672fbc1b95b09fd7fd61f12551c8c2cb8446c3c159f1303490  scripts/controle_nuit_c_recalcul.py
5c4b83a53c2906079cf897dd64b24cbd8ce6fb13a0c616165fd0483b169b3080  scripts/controle_nuit_m_recalcul.py
b96ff98e128f14fc9f0b87c23421262e64213100987c193f69bfdc27841d8f9b  fieldscan/modules/maladies.py
```

### Prêt pour le Juge : commandes de recalcul (depuis la racine du dépôt)

**Maladies**, sur une liste de photos `liste.txt` (un chemin par ligne) avec `verite.csv` (colonne `malade` 0/1, même ordre) :

1. Probabilités (chaîne locale, 32 bits). Pour BanSpot, v10b, soupe, v2 et p_loin existent déjà dans `out/maladies/banspot/*.npy` ; pour la Cordana du Pérou dans `out/maladies/v10b/*cordana_perou.csv`. v12a13 et v12a14 sont à calculer :

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -c "import sys, numpy as np; sys.path.insert(0, '.'); from fieldscan.modules import maladies as M; ch=[l.strip() for l in open('liste.txt', encoding='utf-8') if l.strip()]; [np.save(f'p_{n}.npy', M.predire_convnext(ch, M.charger_convnext(d))) for n, d in [('v10b','modeles/maladies_binome/v10b'), ('soupe','modeles/maladies_soupe_v2_v8/poids'), ('v2','modeles/maladies_binome/maladies_v2/poids'), ('v12a14','modeles/maladies_v12_essais/v12a14'), ('v12a13','modeles/maladies_v12_essais/v12a13')]]; np.save('p_loin.npy', M.p_loin(ch, M.charger_aiguilleur('modeles/maladies_aiguilleur/aiguilleur.npz')))"
```

2. Lecture 2 × 2 de la v10b (pour F1 ; même préparation que sur le réglage ; écrit aussi la lecture 512 px, inutile ici) :

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_banc_finalistes.py --photos liste.txt --calculer lectures/
```

3. Décisions, code de M-banc (colonnes `F1_trois_morceaux2x2`, `C_quatre_v12a14`, `installee`) :

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_banc_finalistes.py --v10b p_v10b.npy --soupe p_soupe.npy --v2 p_v2.npy --loin p_loin.npy --v10b_g2 lectures/p_v10b_g2.npy --v12 p_v12a14.npy --verite verite.csv --sortie reponses_mbanc.csv
```

4. Décisions, mon code indépendant (colonnes `F1_trois_morceaux2x2`, `C_quatre_v12a14`, `v12a13`, `reference_v10b` ; les comptes de F1 et C_quatre doivent être identiques à l'étape 3) :

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_m_appliquer.py --v10b p_v10b.npy --soupe p_soupe.npy --v2 p_v2.npy --loin p_loin.npy --v10b_g2 lectures/p_v10b_g2.npy --v12a14 p_v12a14.npy --v12a13 p_v12a13.npy --verite verite.csv --sortie alertes_controleur.csv
```

   Pour v12a13, la chaîne donne la même décision : `decider_convnext` avec `modeles/maladies_v12_essais/v12a13/seuils.json` (seuils de la v10b), branche loin = v2 (politique b).

**Comptage**, un dossier au format de l'archive. Les cartes ONNX sont calculées depuis les images et les SHA-256 des v6e et v6f sont vérifiés au lancement ; prendre un dossier `--cache` différent par jeu :

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_c_appliquer.py --dossier data/drone/comptage_v5_5cm --ensemble test_dense --cache cache_juge/segmento --sortie segmento.json
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_c_appliquer.py --dossier data/drone/comptage_v5_5cm --ensemble test_banano --cache cache_juge/banano --sortie banano.json
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_c_appliquer.py --dossier data/drone/comptage_v5_5cm/cg --cache cache_juge/cg --sortie cg.json
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_c_appliquer.py --dossier data/drone/comptage_v5_5cm --ensemble test_negatifs --negatif --cache cache_juge/neg_test --sortie neg_test.json
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_c_appliquer.py --dossier data/roboflow_nuit_1112/comptage/banana_trees_kp/prepare --ensemble test_vierge --cache cache_juge/test_vierge --sortie test_vierge.json
```

Chaque commande rend E10_moy_v6e+v5 (0,30), v6f (0,35), E5p90b (0,30), E7 (non retenu, pour information) et le v5 à 0,30 et 0,20 : F1, détectés / annotés, erreur de compte (ou fausses détections avec `--negatif`). Ces outils ont été vérifiés sur le réglage seulement (identiques au banc de C-banc à 10⁻⁴ près) ; je ne les ai jamais lancés sur un juge ni sur le test vierge. Deuxième code (C-banc) : section « Recalcul » de `out/comptage_v6/banc/finalistes.md` (`bc.ecrire_cache`, `ca.construire`, `bc.mesurer_jeu`), avec le v6e et le v6f déclarés dans les modèles supplémentaires du banc.

---

## 1. Maladies, sans entraînement (`out/maladies/nuit_1112/banc/finalistes.md`, 23 h 48)

### 1.1 Recalcul (règle 4.4)

Code indépendant (`scripts/controle_nuit_m_recalcul.py`) : règle d'alerte réécrite depuis le code de `decider_convnext` (photo proche en alerte si et seulement si P(saine) du lecteur < t ; branche loin v2 en alerte si et seulement si P_v2(saine) ≤ 0,70), mélange réécrit depuis le texte de `finalistes.md`.

| Candidat | Coût annoncé | Coût recalculé | Comptes par jeu | Règle 4.4 (coût ≤ 48,23 ; Tanzanie ≤ 14 et ≤ 77 ; aucun pays + 2 points de ratées) |
| --- | --- | --- | --- | --- |
| Référence v10b | 49,23 | 49,226 | identiques au 11/11 | — |
| F1 à trois + 2 × 2, t = 0,70 | 35,96 | 35,958 | identiques (0 ; 62 / 19 ; 241 / 102 / 117 ; 28) | oui (0 ≤ 14 ; 62 ≤ 77 ; tous les pays gagnent) |
| F2 à trois + 384/512, t = 0,72 | 36,48 | 36,477 | identiques | oui |
| F3 à trois, t = 0,74 | 37,83 | 37,829 | identiques | oui |
| Réserve v10b + soupe, t = 0,68 | 39,24 | 39,244 | identiques | oui (mais hors des 3 : **n'est pas un finaliste**) |

Décisions photo par photo : 0 désaccord avec `scripts/m12_banc_finalistes.py` sur les 6 664 photos de réglage.

### 1.2 Sur-réglage

- **Essais** : 947 configurations au moment du choix, 1 215 à 0 h 39 (finalistes inchangés), sur les mêmes 6 664 photos.
- **Bruit de mesure** (bootstrap apparié des photos, `m_a4.txt`) : écart de coût contre la v10b F1 −13,3 (é.-t. 1,6), F2 −12,8 (1,5), F3 −11,4 (1,5) : très au-delà du bruit.
- **Plateaux** (pas 0,02, `m_recalcul.txt`) : F1 finaliste de 0,58 à 0,72, F2 de 0,62 à 0,74, F3 de 0,64 à 0,76 ; les seuils retenus ont leurs deux voisins finalistes. Partout, le coût continue de baisser au-delà du seuil retenu et **seule la limite « 77 saines en alerte en Tanzanie » arrête** (F1 : 62 à 0,70, 72 à 0,72, 86 à 0,74).
- **Un jeu dehors** (`scripts/controle_nuit_m_loo.py`, 1 080 configurations reconstruites, même règle de choix avec plateau) :

| Jeu laissé dehors | Coût du choix refait sans lui | Coût du choix sur les 4 jeux | Référence v10b |
| --- | --- | --- | --- |
| Validation Tanzanie | 9,10 (0 ratée ; **91 / 1 000** saines en alerte, au-delà de 77) | 6,15 | 7,05 |
| TDTU | 45,83 | 45,83 | 54,19 |
| PSFD | 41,46 | 41,46 | 60,57 |
| Éthiopie | 56,76 | 49,02 | 75,10 |
| **Gain moyen sur la référence** | **10,9 points** | **13,6 points** | |

  Optimisme de la recherche entière : environ **2,7 points** sur 13,6. Le gain survit hors échantillon sur TDTU, PSFD et Éthiopie ; **il disparaît sur la Tanzanie laissée dehors** : sans elle, le choix pousse les fausses alertes au-dessus de la limite. Seuil seul re-choisi (famille fixée) : optimisme F1 0,25 ; F2 0,51 ; F3 1,53 ; réserve 2,05.
- **Morceaux 2 × 2** (constat de M-analyste, vérifié) : l'AUC du lecteur ne bouge presque pas (F1 contre F3 : TDTU 0,938 / 0,938, Éthiopie 0,939 / 0,938) et la v10b seule lue en 2 × 2 perd de l'AUC (Éthiopie 0,879 → 0,862). Environ la moitié du gain de coût de F1 sur F3 (1,87 point) est un déplacement de seuil (F3 à 0,76 : 36,84). À fausses alertes égales, F1 rate quand même 8 à 9 malades de moins sur TDTU et Éthiopie (19 contre 27, 117 contre 126) : petit gain local dans la zone d'alerte, mesuré sur le réglage seulement. **Confirmé en partie.**
- **Prix caché** : sur TDTU, les saines en alerte passent de 177 à 232–241 / 577 (+10 points) ; aucune règle de réglage ne borne les fausses alertes hors Tanzanie. C'est le risque principal pour la limite BanSpot (≤ 61 / 646 saines en alerte).

### 1.3 Fuites

- Aucun juge ni test vierge lu par M-banc, M-entraîneur, M-analyste (scripts et carnets lus ; `charger_juges()` jamais appelé ; carnet Kaggle des morceaux limité aux 4 jeux de réglage, vérifié dans son journal ; `out/maladies/banspot/` inchangé depuis le 11/11).
- Membres (v10b, soupe v2 + v8, v2) : aucun n'a appris un jeu de réglage ni un juge (protocole v10b, amendement 1 ; protocole v8 ; LISEZMOI de la v2).
- **Biais connus des juges** (pas des fuites, communs à la référence et aux finalistes) : la v10b a été installée par le binôme après lecture de BanSpot ; la soupe et la v2 ont appris les saines et la Sigatoka du jeu péruvien dont vient la Cordana du Pérou (style familier : peut faire baisser les alertes sur ce juge). BananaLSD : appris par la v10b, hors de toute comparaison (respecté). AgroVisionBD (test vierge) : Bangladesh, pays déjà appris par la v10b (BananaLSD, cm8zf62kzh) ; son chiffre devra le dire.

### 1.4 Faisabilité

- Temps par photo proche sur ce PC (estimations de M-banc) : installée 1,8 s ; F3 ≈ 3,2 s ; F2 ≈ 6 s ; F1 ≈ 10 s. Les photos « loin » doivent aussi passer par le lecteur proche (règle « v2 ou proche ») : tout le lot paie ce prix.
- Modèles : 3 × v10b + 3 × soupe + 3 × v2 (ConvNeXt-Tiny) déjà sur disque ; aucun modèle nouveau.
- Reproductibilité : aucun tirage au hasard dans la décision ; les lectures 512 px et 2 × 2 du réglage viennent de Kaggle en demi-précision (écart ≤ 2 × 10⁻⁴ avec le 32 bits, mesuré par M-banc sur 2 photos) ; 7 (F1), 14 (F2), 7 (F3) photos sur 6 664 sont à moins de 0,002 du seuil.
- **Sur les juges, F1 et F2 demandent des lectures qui n'existent pas encore** (2 × 2 et 512 px de la v10b sur BanSpot et la Cordana) : elles doivent être calculées avec la même préparation que `scripts/m12_banc_kaggle_morceaux.py` (ou `m12_banc_finalistes.py --calculer`), sans rien regarder d'autre.

### 1.5 Verdicts

| Finaliste | Verdict | Raison |
| --- | --- | --- |
| **F1** à trois + morceaux 2 × 2, t = 0,70 | **ADMIS AVEC RÉSERVE** | Règle 4.4 remplie exactement, chiffres recalculés à l'identique, plateau large, seuil stable hors échantillon (optimisme 0,25). Réserves : 947 essais (optimisme de la recherche ≈ 2,7 points) ; la moitié de l'avantage sur F3 vient du seuil, pas des morceaux ; fausses alertes hors Tanzanie en hausse (TDTU +64) ; 5,5 fois le temps de la chaîne ; lectures 2 × 2 à calculer sur les juges. |
| **F2** à trois + 384/512 px, t = 0,72 | **ADMIS AVEC RÉSERVE** | Mêmes constats ; optimisme du seuil 0,51 ; lecture 512 px à calculer sur les juges ; 3,3 fois le temps. M-analyste a mesuré que la lecture 512 px abîme l'AUC de la v10b sur les petites photos (Éthiopie 0,879 → 0,799) : le gain repose sur le mélange, pas sur le 512. |
| **F3** à trois, t = 0,74 | **ADMIS AVEC RÉSERVE** | Mêmes constats ; le plus simple et le seul calculable sur les juges avec les probabilités en cache ; optimisme du seuil 1,53 (le seuil re-choisi sans la Tanzanie monte à 0,82 et la Tanzanie dehors coûte 12,1). |
| Réserve v10b + soupe | non jugée | Hors des 3 finalistes de M-banc ; je ne peux pas l'ajouter. |

Plafond du plan : 3 finalistes au plus par module. Si M-entraîneur écrit un finaliste, le module maladies en aurait 4 : le chef d'orchestre devra trancher avant 7 h par une règle écrite (celle de M-banc, « les 3 coûts de réglage les plus bas », est la seule écrite à ce jour).

## 2. Maladies, entraînés (`out/maladies/nuit_1112/kaggle/finalistes.md`)

### 2.1 v12a4 (écrit à 1 h 17)

Recette : départ v10b, 3 époques en 224 px, EMA, perte « malade dite saine » × 3, tirage par pays puis moitié saines / moitié malades, **PSFD jamais appris** ; seuils de la v10b inchangés. Modèle final : 3 réseaux (départs v10b 0-1-2) appris sur tout (TDTU et Éthiopie compris), `modeles/maladies_v12_essais/v12a4/`.

- **Recalcul** (`scripts/controle_nuit_m_v12.py a4`, code indépendant) : validation (moyenne de 2 plis) 7,5 ; 46,5 (pire pli 11 ; 55) ; TDTU 57 ; 258 ; PSFD 147 ; Éthiopie 178 ; 28 ; coût moyen **47,887** = annoncé. Règle 4.4 remplie (≤ 48,23 ; Tanzanie dans les limites même au pire pli ; aucun pays ne perd en ratées).
- **Sur-réglage et bruit** : 28 essais de M-entraîneur ; recette a4 conçue après lecture des plis de a1 à a3 (diagnostic de M-analyste sur TDTU). Marge sur la barre : 0,34 point. Bootstrap apparié : écart à la v10b **−1,31 (é.-t. 1,28 ; IC 95 % −3,8 à +1,3)**, et 40 % des tirages sous le gain d'un point exigé. Par jeu : validation −1,3 ; **TDTU +6,7** (258 saines en alerte contre 177) ; PSFD −0,8 ; Éthiopie −9,9, dont −9,7 dus à **15 saines éthiopiennes sur 155** (43 → 28). Éthiopie laissée dehors, a4 est moins bon que la v10b sur les trois autres jeux (42,13 contre 40,60) : **le gain disparaît**.
- **Fuites** : carnet `notebooks/m12_entrainer_v12_kaggle.py` relu (apprentissage = index `entrainement` + wfzpdmc5vx + pays ; validation jamais apprise, assert ; juges jamais lus). Le modèle final apprend TDTU et l'Éthiopie : comparaison par empreintes déjà calculées (`scripts/controle_nuit_m_fuites_v12.py`, aucune image de juge ouverte) : **0 copie** de BanSpot ni de la Cordana du Pérou dans son apprentissage (vignettes sous 8 symétries ; témoin positif 200 / 200).
- **Faisabilité** : même architecture et même temps que la v10b (≈ 1,8 s par photo proche) ; 3 × 56 Mo. Le modèle jugé (3 graines, appris sur tout) n'est pas celui que la règle a mesuré (un réseau par pli) ; contrôle du modèle final sur la validation : 10 ; 44.

| Finaliste | Verdict | Raison |
| --- | --- | --- |
| **v12a4** | **ADMIS AVEC RÉSERVE** | Aucune règle violée, aucune fuite, chiffres exacts. Réserves fortes : gain de réglage dans le bruit (IC 95 % de −3,8 à +1,3) ; il repose sur 15 saines d'Éthiopie et paie 81 fausses alertes de plus sur TDTU ; modèle jugé différent des modèles mesurés. **Plafond** : avec F1, F2, F3, le module compte 4 finalistes ; selon l'ordre de 4.4 (« le coût de réglage le plus bas »), v12a4 (47,89) est 4e et sort de la liste. Au chef d'orchestre de geler la liste avant 7 h. |

### 2.2 v12a7 (écrit à 1 h 22)

Recette : comme a4, avec tirage 50/50 saines / malades dans chaque source, perte × 2, augmentation « basse résolution » (p = 0,3) ; PSFD jamais appris ; **règle B réglée à 0,69** sur le réglage. Modèle final : **pas encore entraîné** à 1 h 45.

- **Recalcul** (`scripts/controle_nuit_m_v12_seuil.py a7 0.69`) : validation (2 plis) 7 ; 56,5 (pire pli 11 ; 72) ; TDTU 55 ; 248 ; PSFD 129 ; Éthiopie 184 ; 23 ; coût **45,304** = annoncé. Règle 4.4 remplie.
- **Sur-réglage** : 28 essais de M-entraîneur, dont le seuil. Plateau finaliste large (t de 0,64 à 0,82) ; un jeu dehors, t re-choisi : 0,68 à 0,69, optimisme du seuil 0,40. Bootstrap : −3,90 (é.-t. 1,24 ; IC 95 % −6,4 à −1,4) : gain réel sur le réglage, mais petit à côté de F1 à F3 (−11 à −13). Par jeu contre la v10b : validation 6,70 / 7,05 ; **TDTU 58,56 / 54,19 (perd 4,4)** ; PSFD 52,44 / 60,57 ; Éthiopie 63,52 / 75,10.
- **Fuites** : mêmes données que a4 (empreintes : 0 copie des juges). Aucune.
- **Faisabilité** : comme la v10b. Mais le seuil 0,69 a été réglé sur des réseaux de pli (un réseau, pays exclus) et serait appliqué à un modèle final de 3 réseaux appris sur tout : son étalonnage peut différer.

| Finaliste | Verdict | Raison |
| --- | --- | --- |
| **v12a7** (règle B 0,69) | **ADMIS AVEC RÉSERVE, sous condition** | Règle et chiffres exacts, pas de fuite, seuil stable. Condition : le modèle final doit exister avant 7 h et, lu au seuil 0,69 sur la validation Tanzanie, rester dans les limites (≤ 14 ratées, ≤ 77 fausses alertes) ; sinon il n'y a rien à juger. Réserves : perd sur TDTU ; seuil réglé sur d'autres réseaux que ceux jugés. **Plafond** : 5 candidats pour 3 places dans le module ; par le coût de réglage (ordre de 4.4) : F1 35,96 < F2 36,48 < F3 37,83 < v12a7 45,30 < v12a4 47,89 : v12a7 et v12a4 sortent si le chef d'orchestre applique cet ordre. |

### 2.3 v12a9 et v12a10 (annoncés à 2 h 15, liste de M-entraîneur arrêtée à 5 h)

- **v12a9** = a7 + jeux neufs `feuilles-nuit-1112` (Bangladesh, 1 405 photos : `5nfjzntwd8` et `6yy9522rdy`), règle B 0,65. Recalcul (`controle_nuit_m_v12_seuil.py a9 0.65`) : validation 5 ; 57 (pire pli 7 ; 59), TDTU 59 ; 217, PSFD 113, Éthiopie 173 ; 21, coût **41,506** = annoncé ; finaliste. Plateau plat (41,5 à 42,3 de t = 0,55 à 0,77). Un jeu dehors : le seuil re-choisi saute de 0,50 à 0,75 selon le jeu, **optimisme du seuil 2,44** (gain hors échantillon 5,3 contre 7,7). Bootstrap −7,71 (é.-t. 1,26). Par jeu : TDTU 54,32 contre 54,19 (égal) ; PSFD 45,9 contre 60,6 ; Éthiopie 59,3 contre 75,1. AUC du pays tenu à l'écart (M-entraîneur) : 0,928 / 0,928, premier gain de séparation de la nuit.
- **v12a10** = a7 + morceaux (p = 0,3), règle B 0,61 : coût **43,253** = annoncé ; optimisme du seuil 1,15 ; bootstrap −5,98 (é.-t. 1,22) ; TDTU 56,3 contre 54,2 (perd).
- **Fuites** des jeux neufs (bilan de D-maladies relu, `bilan_fuites.json`) : aucune copie de BanSpot, de la Cordana du Pérou ni d'AgroVisionBD (test vierge) dans `5nfjzntwd8` et `6yy9522rdy` (« copies_autres_jeux_neufs » vides ; les copies de `cm8zf62kzh` et de BDR déjà retirées). Réserve : **le test vierge AgroVisionBD est du Bangladesh** ; v12a9 apprend 1 405 photos du Bangladesh (autres régions, autres sources ; une auteure commune avec `cm8zf62kzh`) : son chiffre sur le test vierge sera moins « lointain » que celui de la v10b, à écrire.

| Candidat | Verdict | Raison |
| --- | --- | --- |
| **v12a9** (règle B 0,65) | **ADMIS AVEC RÉSERVE, sous condition** | Règle et chiffres exacts, pas de fuite. Condition : modèle final produit avant 7 h et contrôlé sur la validation au seuil 0,65. Réserves : seuil le plus optimiste de la nuit (2,4 points perdus hors échantillon) ; même pays que le test vierge dans l'apprentissage. |
| **v12a10** (règle B 0,61) | **ADMIS AVEC RÉSERVE, sous condition** | Idem (modèle final à produire) ; perd sur TDTU ; dominé par v12a9 sur le réglage. |

Rappel du plafond : le module maladies compte à 2 h 16 sept candidats admissibles pour 3 places (coûts de réglage : F1 35,96 ; F2 36,48 ; F3 37,83 ; a9 41,51 ; a10 43,25 ; a7 45,30 ; a4 47,89). La liste gelée devra venir du chef d'orchestre avant 7 h ; je ne contrôle que ce qui y figure.

### 2.4 Liste v12 arrêtée par M-entraîneur à 2 h 55 : v12a13, v12a14, v12a4 (seuils de la v10b, aucun seuil réglé)

v12a7, v12a9, v12a10 **ne sont plus dans la liste** de M-entraîneur (sans objet ; mes contrôles 2.2 et 2.3 restent pour mémoire). Sa liste ne garde que des candidats aux seuils de la v10b.

- **Recalcul** (`controle_nuit_m_v12_seuil.py <c> 0.5186470150947571`) : a13 **41,498** (validation 6 ; 65,5, **pire pli 9 ; 76**, à 1 de la limite 77 ; TDTU 64 ; 201 ; PSFD 114 ; Éthiopie 141 ; 34) ; a14 **42,276** (5 ; 54, pire pli 7 ; 55 ; TDTU 59 ; 209 ; PSFD 119 ; Éthiopie 194 ; 16). Identiques aux annonces ; règle 4.4 remplie (moyenne des plis comme écrit à 22 h 25).
- **Sur-réglage** : 44 essais de M-entraîneur ; aucun seuil réglé. Un jeu dehors sur le seuil (pour mesurer la stabilité) : a13 garde 0,50 partout, optimisme −0,77 (le seuil v10b n'est pas avantagé) ; a14 1,39. Bootstrap des photos : a13 −7,73 (é.-t. 1,25), a14 −6,95 (1,26). **Bruit de graine** (a9 contre a16, même recette, mesuré par M-entraîneur et recalculé ici : 42,90 contre 42,76 ; Éthiopie 208 contre 183 ratées ; pire pli de Tanzanie de a16 : 16 ratées, au-delà de 14) : l'écart a13 / a9 (1,4 point) est de l'ordre du bruit, et le choix de a13 parmi 44 recettes est optimiste d'environ 1 point. Le gain sur la v10b (7 à 8 points) dépasse nettement ce bruit ; il vient surtout de PSFD (−14) et de l'Éthiopie (−16) ; TDTU gagne peu (−1,2), la Tanzanie perd un peu pour a13 (7,45 contre 7,05).
- **Fuites** : mêmes données que a9 (jeux neufs du Bangladesh sans copie des juges ni d'AgroVisionBD ; empreintes de l'apprentissage commun : 0 copie des juges). Réserve « même pays que le test vierge » pour a13 et a14.
- **Faisabilité** : architecture et temps de la v10b (chaîne locale : 3,8 à 4,0 s par photo sur 2 fils d'une machine chargée). Modèles finaux de a13 et a14 rangés à 3 h 20 (3 réseaux 16 bits de 56 Mo chacun ; appris sur tout sauf PSFD et la validation : vérifié dans le carnet et son journal). Leurs chiffres « pays » ne sont plus mesurables (TDTU et Éthiopie appris) : seuls les plis les portent.

| Finaliste (liste de 2 h 55) | Verdict | Raison |
| --- | --- | --- |
| **v12a13** | **ADMIS AVEC RÉSERVE** (condition remplie à 3 h 21) | Règle et chiffres exacts, aucun seuil réglé, pas de fuite, gain très au-delà du bruit. Modèle final (`modeles/maladies_v12_essais/v12a13/`, poids identiques au carnet par SHA-256, PSFD bien exclu, chargé par la chaîne locale à 6 × 10⁻⁵ près) : validation 7 ratées, 60 saines en alerte (limites 14 et 77). Réserves : choix parmi 44 recettes (≈ 1 point d'optimisme) ; Bangladesh appris (comme le test vierge) ; fausses alertes Tanzanie en hausse (57 → 65,5). |
| **v12a14** | **ADMIS AVEC RÉSERVE** (condition remplie à 3 h 21) | Modèle final : validation 9 ; 48, poids identiques au carnet ; Éthiopie moins bonne que a13 (194 ratées), optimisme du seuil 1,4 s'il fallait le régler. |
| **v12a4** | **ADMIS AVEC RÉSERVE** | Inchangé (2.1 ; modèle final contrôlé : validation 10 ; 44, poids identiques au carnet, chaîne locale à 1,6 × 10⁻⁴) : gain dans le bruit (IC 95 % −3,8 à +1,3), porté par 15 saines d'Éthiopie ; 3e de la liste de M-entraîneur. |

Plafond : le module compte maintenant 6 candidats pour 3 places (F1 35,96 ; F2 36,48 ; F3 37,83 ; a13 41,50 ; a14 42,28 ; a4 47,89). Par l'ordre de 4.4, les trois de M-banc passent devant ; le chef d'orchestre doit écrire la liste gelée avant 7 h.

### 2.5 Famille C : `C_quatre_v12a14` (`out/maladies/nuit_1112/banc/finalistes_famille_c.md`, 4 h 06)

Mélange géométrique à poids égaux de v10b, soupe, v2 et **v12a14 (modèle final)** sur les 3 classes communes, « autre » = (P_autre v10b + P_autre v12a14) / 4, règle B **t = 0,76**, branche loin « v2 ou proche », lecture entière.

- **Recalcul** (`scripts/controle_nuit_m_famille_c.py`, code indépendant) : validation 2 ; 68, TDTU 15 ; 260, PSFD 86, Éthiopie 122 ; 32, coût **36,072** = annoncé (36,07). Pays lus par le pli qui ne les a pas appris (fichiers `predictions_a14_tdtu.csv`, `_ethiopie.csv` ; PSFD jamais appris, lu par le pli sans TDTU) : vérifié. Validation : M-banc moyenne les **probabilités** des 2 plis, M-entraîneur moyennait les **comptes** ; les deux lectures donnent 36,07 et 36,06 : sans effet.
- **Modèle final** : `predictions_a14_final_validation.csv` (poids identiques à `modeles/maladies_v12_essais/v12a14/`, contrôle de 3 h 21) relu dans le mélange : **3 ratées, 69 saines en alerte** = annoncé ; limites 14 et 77 respectées.
- **Règle 4.4** : remplie ; plateau finaliste de t = 0,62 à 0,78 ; t = 0,76 a ses deux voisins finalistes (règle de M-banc écrite à 4 h 00, avant la mesure).
- **Sur-réglage** : 518 essais pour la famille C (1 733 pour M-banc dans la nuit). Un jeu dehors sur l'espace de la grille de 4 h (a13, a14, a4 × 4 mélanges × 16 seuils, même règle de plateau) : gain hors échantillon 9,1 contre 13,2 en plein, **optimisme 4,1 points** (le plus fort des maladies) ; validation laissée dehors : 9,75 (pire que la v10b, 7,05) ; Éthiopie dehors 62,8 contre 52,9. Avec le lot 6 : optimisme 3,5. Bootstrap : contre la v10b −13,2 (é.-t. 1,5) ; **contre F3 −1,78 (é.-t. 0,90 ; IC 95 % −3,5 à −0,02)** : l'avantage sur le mélange à trois sans v12 est à la limite du bruit, et plus petit que l'optimisme estimé.
- **Fuites** : v12a14 contrôlé (2.4 et 3 h 21 : aucune copie des juges dans son apprentissage ; même pays que le test vierge). Aucune nouvelle.
- **Faisabilité** : ≈ 5 s par photo (quatre modèles, aussi sur les photos « loin ») ; 12 ConvNeXt-Tiny chargés (3 v10b, 3 soupe, 3 v2, 3 v12a14). Sur les juges, il faut les probabilités du modèle final v12a14 (`charger_convnext(modeles/maladies_v12_essais/v12a14)`), à calculer par le Juge.

| Candidat | Verdict | Raison |
| --- | --- | --- |
| **C_quatre_v12a14** (t = 0,76) | **ADMIS AVEC RÉSERVE** | Règle 4.4 remplie, chiffres et modèle final exacts, pas de fuite. Réserves : optimisme le plus fort (≈ 4 points) après 518 essais ; avantage sur F3 dans le bruit (−1,8 ± 0,9) ; fausses alertes TDTU 260 / 577 et Tanzanie 68 à 69 / 1 000 (limite 77) ; 2,8 fois le temps de la chaîne. |
| Mélange à quatre avec a19 | non admis | Sans modèle final (M-entraîneur a fini à 4 h 10) ; pas candidat selon le chef d'orchestre. |

## 3. Comptage, banc (`out/comptage_v6/banc/finalistes.md`, 0 h 39, réécrit à 1 h 36 puis à 4 h 22)

**Liste de 4 h 22** (finale de C-banc) : `E10_moy_v6e+v5` (nouveau), `E5p90b_moy34_v5_d0.1`, `E7_union_v5+v3_d0.05_r30`. **`E10_p90_v6b_v5_d0.1` n'est plus dans aucun `finalistes.md` : il n'est plus candidat** (section 3.0 gardée pour mémoire). `E3_log_v3+v4+v5` reste hors liste.

### 3.00 `E10_moy_v6e+v5` (ajouté à 4 h 22)

Moyenne des cartes de probabilité du **v6e** (`modeles/comptage_v6_essais/centres_5cm_v6e.onnx`, SHA-256 **93fb659befd669e229a6af50eb08c83968468219b483e1b48ee9b8c993737f01**) et du **v5** (`modeles/centres_5cm_v5.onnx`, SHA-256 12f9b4caa5735767…, complet dans `empreintes_finalistes_0400.txt`), pics 7 × 7, seuil **0,30**.

- **Recalcul** (`scripts/controle_nuit_c_recalcul.py --spec out/controle_nuit_1112/specs_c_banc3.json`) : dense 0,7809, plantain 0,8887, jeunes 0,8871, MM 0,8630, btd 0,9913 ; moyenne **0,8822**, erreur de compte 0,153, 8 fausses (0,12 %) : identique à C-banc. Cache du v6e = ONNX (écart ≤ 3 × 10⁻⁸ sur 15 images). Règle 3.4 remplie **dans les deux lectures** (contre le v5 en service, pire perte : jeunes −0,006 ; moyenne des 4 jeux hors btd 0,855 contre 0,854).
- **Sur-réglage** : 324 variantes ; égalité avec `v6a_g1 + v5` (0,88217 contre 0,88220) : le choix entre graines ou entre v6 est du bruit (écart entre graines 0,003 à 0,004 selon C-banc ; MM de v6a_g2 seul −0,092). Un jeu dehors sur les 318 variantes de `essais.json` (`c_loo_0422.txt`) : **sans btd_val, aucun finaliste** ; MM dehors, le choix refait perd −0,052 contre le v5 à 0,30, dense dehors −0,032 ; optimisme moyen +0,023. Bloc par bloc dans btd_val : 0,993 / 0,991 / 0,991 (v5 à 0,30 : 0,463 / 0,491 / 0,435). **banano_finca, pour information** : 0,751 contre 0,754 pour le v5 à 0,30 : le gain disparaît hors de btd.
- **Fuites** : le v6e apprend en plus `dmpcs2_objets` et `geostar_tree` (`centres_5cm_v6e.json` : `jeux_neufs` = ces deux dossiers ; `banano_finca` mesuré pour information seulement ; aucun ensemble test_* accepté, assert du carnet). Contrôle de C-prospection relu (`_fuites/fuites.csv`) : aucun MD5 ni nom commun avec nos jeux ; **aucune image à moins de 6 bits du test vierge `banana_trees_kp`** (plus proche : 8 bits) ; 4 tuiles de dmpcs2 à 3 à 6 bits d'images de référence, dont **une à 5 bits d'une tuile `cocotier_1300_plus` (sans bananier du test, juge)**, déclarée faux positif à l'œil par C-prospection (planche `paire_dmpcs2.jpg`) ; je ne l'ai pas rouvert (image de juge). Réserve faible : une tuile sur 463 d'apprentissage, effet possible seulement sur les fausses détections « sans bananier » des juges.
- **Faisabilité** : deux passages de réseau partout (≈ 2 fois le v5 : 6 à 10 s/ha sur la machine partagée) ; v6e graine 0, EMA de la dernière époque, versions dans `centres_5cm_v6e.json`.
- **Famille (règle de gel)** : C (mélange contenant un v6).



**Liste de 1 h 36** : `E10_p90_v6b_v5_d0.1` (nouveau), `E5p90b_moy34_v5_d0.1`, `E7_union_v5+v3_d0.05_r30`. `E3_log_v3+v4+v5` sort de la liste (4e famille) : il n'est plus finaliste et ne doit pas être jugé.

### 3.0 `E10_p90_v6b_v5_d0.1` (ajouté à 1 h 36)

Même aiguillage que E5p90b (p90 des pics du v5 < 0,55 → branche « petits », décalage 0,10, seuil 0,30), branche « petits » = **v6b** de C-entraîneur (ONNX `modeles/comptage_v6_essais/centres_5cm_v6b.onnx`, SHA-256 f006a49b74671b1c8eb38472845142b6def2bdd8bd62e1336e69ffda9a35ae00 ; sortie à la demi-résolution ramenée au quart par maximum 2 × 2).

- **Recalcul** (`scripts/controle_nuit_c_recalcul.py --spec out/controle_nuit_1112/specs_c_banc2.json`) : dense 0,7795, plantain 0,8823, jeunes 0,8926, MM 0,8571, btd 0,9815 ; moyenne **0,8786**, erreur de compte 0,136, 12 fausses (0,19 %) : identique. Cache du v6b recalculé depuis l'ONNX sur 15 images (`scripts/controle_nuit_c_cache_v6.py v6b`) : écart ≤ 3 × 10⁻⁸. Règle 3.4 remplie **dans les deux lectures** (pire perte contre le v5 en service : plantain −0,004).
- **Sur-réglage** : 244 variantes ; même constat que E5p90b : hors btd, le candidat **est** le v5 sur 98 % des images (moyenne des 4 autres jeux 0,853 contre 0,854 pour le v5 à 0,30). Tout le gain vient de btd_val, sur lequel le v6b a appris l'autre moitié de la même orthomosaïque (btd_train, découpage du plan 3.2 avec bande tampon : permis, mais pas indépendant). Bloc par bloc (`scripts/controle_nuit_c_e10.py`) : 0,978 / 0,981 / 0,986, uniforme. **banano_finca, pour information** : v6b seul 0,730 (moins bien que le v5, 0,754) ; E10 0,754 = v5 (aiguillage éteint) : le gain disparaît hors de btd.
- **Fuites** : le carnet v6 retire tous les ensembles test_* et ne lit jamais `cg/` (relu) ; btd_val jamais appris. Pas de fuite ; proximité de domaine btd_train / btd_val à écrire avec le chiffre.
- **Faisabilité** : v5 partout (3 à 4,5 s/ha) + v6b sur les zones aiguillées (≈ 1,7 fois le v5). Modèle de graine 0, sans choix d'époque (EMA de la dernière), versions dans `centres_5cm_v6b.json` (torch 2.11, T4).
- **Gel** : C-banc écrit que E10 « se recalcule » si C-entraîneur retient un autre modèle final. Un finaliste doit être figé : **seul l'ONNX ci-dessus (SHA-256 donné) est admis** ; un autre réseau dans la branche « petits » est un autre candidat, à contrôler avant 7 h ou à écarter.


### 3.1 Recalcul (règle 3.4)

Code indépendant (`scripts/controle_nuit_c_recalcul.py` : pics 7 × 7, appariement hongrois à 20 px, non-mères ignorées, disque DJI, zones MM, réécrits ; seules les cartes en cache du réglage sont lues). Chiffres **identiques** à ceux de C-banc (écart < 10⁻⁴).

| Candidat | Seuil | dense | plantain | jeunes | MM | btd_val | Moyenne | Erreur de compte | Fausses sans bananier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v5, règle 3.4 (référence) | 0,20 | 0,759 | 0,842 | 0,869 | 0,776 | 0,716 | 0,7923 | 0,371 | 61 (0,94 %) |
| v5 en service | 0,30 | 0,780 | 0,887 | 0,893 | 0,857 | 0,473 | 0,7777 | 0,262 | 16 |
| `E5p90b_moy34_v5_d0.1` | 0,30 | 0,780 | 0,877 | 0,893 | 0,857 | 0,868 | 0,8549 | 0,154 | 16 (0,25 %) |
| `E7_union_v5+v3_d0.05_r30` | 0,30 | 0,765 | 0,863 | 0,908 | 0,859 | 0,780 | 0,8352 | 0,219 | 20 (0,31 %) |
| `E3_log_v3+v4+v5` | 0,25 | 0,758 | 0,873 | 0,898 | 0,863 | 0,773 | 0,8331 | 0,180 | 10 (0,15 %) |

Règle 3.4 telle que lue par C-banc (écrit à 22 h 35, avant mesure) : moyenne > 0,8023, aucun jeu sous le v5 à 0,20 − 0,020, erreur de compte ≤ 0,262 (v5 à 0,30), fausses < 1 % : **les trois passent**. Lecture plus stricte (perte par jeu contre le v5 **en service**, à 0,30) : E5p90b passe (pire −0,009, plantain) ; **E7 échoue (plantain −0,023)** ; **E3 échoue (dense −0,022)**. Le plan dit seulement « v5 » ; la lecture de C-banc est écrite avant et défendable : réserve, pas refus.

### 3.2 Sur-réglage

- **Essais** : environ 200 variantes de C-banc sur le même réglage ; le signal p90 et tau 0,50 ont été proposés par C-analyste après lecture de btd_val ; règle de choix « une par famille » écrite à 0 h 38, après les mesures (mais avant les juges).
- **Un jeu dehors** (`scripts/controle_nuit_c_loo.py`, 177 variantes de `essais.json`) : **sans btd_val, aucune variante n'est finaliste** ; les quatre autres jeux ne gagnent que contre le v5 à 0,20 (mauvais seuil pour eux), et contre le v5 à 0,30 ils font 0 (jeunes, MM) ou perdent (dense −0,019, plantain −0,034 pour le choix refait). Sur les 4 jeux hors btd, moyenne des finalistes contre le v5 à 0,30 : E5p90b −0,002, E7 −0,005, E3 −0,006. **Tout le gain vient de btd_val**, une seule orthomosaïque, sur laquelle l'aiguillage a été réglé.
- **Bloc par bloc dans btd_val** (`scripts/controle_nuit_c_blocs.py`) : E5p90b 0,842 / 0,868 / 0,906 contre v5 à 0,30 : 0,463 / 0,491 / 0,435 ; gain stable sur les trois blocs. (tau, d) re-choisis sur deux blocs : le bloc dehors ne perd rien. À l'intérieur de btd, le réglage de tau n'est pas optimiste ; tau 0,55 est au début du plateau (0,50 : −0,017 ; 0,45 : −0,064 sur btd).
- **Autre plantation jeune, pour information** (banano_finca, ni juge ni test vierge du projet ; `scripts/controle_nuit_c_finca.py`) : 1 image sur 25 aiguillée ; E5p90b 0,753 contre v5 à 0,30 0,754 : **le gain disparaît** (plants de 80 px, pas de petits plants). L'aiguillage ne s'allume que pour des plants de moins de 2 m (cas btd).
- Aucun juge ne contient de plantation jeune espacée ; le test vierge (`banana_trees_kp`) est dense : **le gain annoncé ne sera vérifié par aucune lecture**. Les juges ne peuvent montrer que la non-régression. Risque à lire avec le test vierge : ses photos sont agrandies 2,2 fois (environ 11 cm/px) ; si le v5 y répond faiblement, l'aiguillage peut envoyer des images denses vers v3 + v4 (non mesuré, à rapporter).

### 3.3 Fuites

- Membres v3, v4, v5 : aucun n'a appris un jeu de réglage (fuites_membres.txt relu ; btd était le test du v4 et du v5, absent du v3). Aucun juge lu par C-banc (`bc.jeu` ne charge segmento, cg, banano, neg_test que pour `v6_banc_juges.py`, non lancé ; le cache ne contient aucune carte de juge).
- **Réserve « segmento est »** : les trois finalistes contiennent le v3, qui a choisi son époque et son seuil sur segmento est : la moyenne des juges doit aussi être donnée sans segmento est.
- btd_val et btd_train viennent de la même orthomosaïque (découpage géographique avec bande tampon, contrôle de fuite de D-comptage relu : aucune paire ≥ 0,95). Sans effet sur ces finalistes (aucun membre n'a appris btd_train).

### 3.4 Faisabilité

Temps (C-banc, machine partagée) : un passage de réseau 2,7 à 3,1 s/ha ; E5p90b 3,1 s/ha hors zones aiguillées, 8,8 s/ha sur les zones aiguillées (v5 pour le signal, puis v3 et v4) ; E7 5,8 s/ha ; E3 8,8 s/ha. Modèles ONNX déjà installés (v3, v4, v5), aucun tirage au hasard : reproductible.

### 3.5 Verdicts

| Finaliste | Verdict | Raison |
| --- | --- | --- |
| **`E5p90b_moy34_v5_d0.1`** | **ADMIS AVEC RÉSERVE** | Règle 3.4 remplie sous les deux lectures, chiffres recalculés à l'identique, gain stable sur les trois blocs de btd_val. Réserves : sur du dense dégradé à 11 cm/px (simulation de C-analyste, `out/comptage/analyse/rapport_cycle3_echelle.md`), l'aiguillage envoie 39 % des images denses vers v3 + v4 (85 % à 14 cm) sans perte (+0,010), mais le test vierge mesurera alors en partie v3 + v4 sur du dense flou, et le v5 lui-même y chute à 0,622 ; tout le gain vient de btd_val (aucun finaliste sans lui ; nul sur banano_finca) et aucun juge ne peut le confirmer ; v3 dedans (segmento est) ; aiguillage non éprouvé sur des images de résolution différente (test vierge). |
| **`E7_union_v5+v3_d0.05_r30`** | **ADMIS AVEC RÉSERVE** | Passe 3.4 dans la lecture écrite par C-banc ; échoue dans la lecture « v5 en service » (plantain −0,023). Dominé par E5p90b sur dense, plantain et btd ; mêmes réserves (btd seul, v3). |
| **`E10_moy_v6e+v5`** | **ADMIS AVEC RÉSERVE** | Règle 3.4 remplie dans les deux lectures, chiffres exacts, ONNX figé (SHA-256 93fb659b…). Réserves : gain entièrement sur btd_val dont l'autre moitié est apprise par le v6e ; nul sur banano_finca ; choix entre graines dans le bruit ; une tuile d'apprentissage dmpcs2 proche (5 bits) d'une tuile « sans bananier » de juge, jugée faux positif par C-prospection ; 2 réseaux partout. |
| ~~`E3_log_v3+v4+v5`~~ | sans objet | Retiré par C-banc à 1 h 36 (4e famille). Pour mémoire : échouait dans la lecture « v5 en service » (dense −0,022). |
| ~~`E10_p90_v6b_v5_d0.1`~~ | sans objet depuis 4 h 22 (retiré de la liste de C-banc) ; avant : ADMIS AVEC RÉSERVE | Règle 3.4 remplie dans les deux lectures, chiffres exacts, cache conforme à l'ONNX. Réserves : gain entièrement sur btd_val, dont l'autre moitié a été apprise par le v6b (F1 0,98 très optimiste) ; nul sur banano_finca ; non vérifiable par les juges ; finaliste figé sur l'ONNX de SHA-256 f006a49b… (pas de remplacement après coup). |

## 4. Comptage, entraîné (`out/comptage_v6/kaggle/finalistes.md`, version de 5 h 34)

Finalistes proposés par C-entraîneur (famille B de la règle de gel, « v6 seul ») : **v6f** (ResNet-34, graine 0, 0,35), **v6a** (graine 0, 0,35), **v6d** (graine 0, 0,35). ONNX identiques (SHA-256) dans `out/comptage_v6/kaggle/<m>/` et `modeles/comptage_v6_essais/` : v6f 49602a142a8c7ebacddf761cddb337a9001d5a24e655df8e001716544f4a80af ; v6a 766f52631abb7db1642cd76878d5730c19896f026dc6a954ca36317384b28886 ; v6d 6cacee68e4e4d910bf80… (complet dans `empreintes_finalistes_0400.txt`).

- **Recalcul** (mon code, ONNX, processeur ; cartes du v6f calculées par moi, `scripts/controle_nuit_c_cache_modele.py v6f` ; caches de C-banc pour v6a et v6d vérifiés contre l'ONNX à 3 × 10⁻⁸) :

| Modèle | Seuil (règle 3.4, recalculé) | dense | plantain | jeunes | MM | btd_val | Moyenne | Erreur de compte | Fausses | Carnet (GPU) | Lecture stricte (contre v5 à 0,30) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v6f | 0,35 | 0,780 | 0,884 | 0,888 | 0,851 | 0,988 | **0,8780** | 0,106 | 2 | 0,8771 | passe (pire −0,006, MM) |
| v6a | 0,35 | 0,777 | 0,887 | 0,895 | 0,822 | 0,988 | 0,8740 | 0,138 | 11 | 0,8730 | **échoue** (MM −0,035) |
| v6d | 0,35 | 0,777 | 0,890 | 0,892 | 0,808 | 0,988 | 0,8710 | 0,153 | 4 | 0,8694 | **échoue** (MM −0,049) |

  Écarts ONNX / carnet : +0,0009 (v6f), +0,0010 (v6a), +0,0016 (v6d) sur la moyenne, jusqu'à 0,007 sur MM : GPU contre ONNX ; les seuils retenus sont les mêmes. Pour le Juge, les chiffres de référence sont ceux de l'ONNX.
- **Règle 3.4** (lecture de C-entraîneur, écrite à 23 h 37) : les trois passent. Lecture stricte : seul v6f passe.
- **Sur-réglage** : 16 recettes entraînées ; graine unique pour v6f et v6d ; écart entre graines de v6a 0,007 (MM de 0,765 à 0,822) : l'avance de v6f sur v6a (0,004) est dans le bruit. MM (2 images, 69 plants) bouge de 0,803 à 0,851 entre les seuils 0,30 et 0,35 pour v6f. **Un jeu dehors** : sans btd_val, aucun v6 seul n'est finaliste (moyenne des 4 anciennes : v6f 0,851, v6a 0,844, v6d 0,840 contre 0,854 pour le v5 en service). banano_finca (information, C-entraîneur) : v6f 0,739, v6a 0,754, v6d 0,736 contre 0,754 : **le gain disparaît hors de btd**, et v6f y perd 0,015.
- **Fuites** : aucun jeu neuf dans v6f ni v6a (json : `jeux_neufs` vide) ; v6d lit banano_finca pour information seulement. Carnet relu : ensembles test_* retirés, `cg/` jamais lu. btd_train et btd_val : même orthomosaïque (réserve, pas fuite).
- **Faisabilité** : v6a, v6d : même réseau que le v5 (ResNet-18, 45 Mo). v6f : ResNet-34 (86 Mo de poids), environ 1,5 à 2 fois le temps du v5 [H, non mesuré par moi]. Graines 1 et 2 du v6f attendues vers 7 h, après la limite de 6 h 45 : **seule la graine 0 (SHA-256 ci-dessus) est admise**.

| Finaliste | Verdict | Raison |
| --- | --- | --- |
| **v6f** (graine 0, seuil 0,35) | **ADMIS AVEC RÉSERVE** | Règle 3.4 remplie dans les deux lectures, chiffres ONNX à 0,001 du carnet, pas de fuite. Réserves : gain entièrement sur btd_val (apprise à moitié) ; aucun gain hors btd (4 anciennes −0,003 ; banano_finca −0,015) ; **graine chanceuse** : mise à jour de C-entraîneur à 6 h 42, la même recette en graine 1 (0,8611, MM 0,744) **ne passe pas** la règle par jeu, la graine 2 fait 0,8685 ; moyenne des 3 graines 0,8689, sous celle de v6a (0,8699) ; c'est la graine 0 seule (SHA-256 49602a14…) qui est admise ; ResNet-34 plus lent (≈ 1,5 fois). |
| **v6a** (graine 0, 0,35) | **ADMIS AVEC RÉSERVE** | Passe dans la lecture de C-entraîneur, échoue dans la lecture stricte (MM −0,035) ; mêmes réserves. |
| **v6d** (graine 0, 0,35) | **ADMIS AVEC RÉSERVE** | Idem (MM −0,049). |

