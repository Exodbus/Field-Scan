# Finalistes du banc de comptage v6 (agent C-banc), écrits le 13 novembre 2026 à 04:22

Écrits **avant toute lecture des juges** (aucun juge n'a été lu par C-banc). Règles : `docs/plan_nuit_2026-11-12.md`, 3.4.
Réglage : dense, plantain, jeunes, mm, btd_val (btd_val = moitié validation de banana_tree_detection, découpage v6, archive `data/drone/comptage_v6_5cm`, ensemble `val_espace`). Fausses détections : 1 424 tuiles sans bananier de validation (6 459 arbres).

**Référence v5** (règle 3.4 sur le même réglage) : seuil 0.2, moyenne 0.7923, dense 0.759, plantain 0.842, jeunes 0.869, mm 0.776, btd_val 0.716, erreur de compte 0.371, fausses sans bananier 61 (0.94%).
Pour information, v5 au seuil 0,30 de la chaîne : moyenne 0.7777, dense 0.779, plantain 0.886, jeunes 0.893, mm 0.857, btd_val 0.473, erreur de compte 0.262, fausses 16.

| finaliste | seuil | dense | plantain | jeunes | mm | btd_val | moyenne | gain / v5 | pire perte | erreur de compte | fausses sans bananier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `E10_moy_v6e+v5` | 0.30 | 0.781 | 0.889 | 0.887 | 0.863 | 0.991 | 0.8822 | +0.090 | +0.019 | 0.153 | 8 (0.12%) |
| `E5p90b_moy34_v5_d0.1` | 0.30 | 0.779 | 0.877 | 0.893 | 0.857 | 0.868 | 0.8549 | +0.063 | +0.020 | 0.154 | 16 (0.25%) |
| `E7_union_v5+v3_d0.05_r30` | 0.30 | 0.765 | 0.863 | 0.908 | 0.859 | 0.780 | 0.8352 | +0.043 | +0.006 | 0.219 | 20 (0.31%) |

## Définitions exactes

### `E10_moy_v6e+v5` (10 mélange nuit)

- fabrique : `melange` dans `scripts/v6_banc_candidats.py` ; réglages :

```json
{"membres": ["v6e", "v5"], "mode": "moyenne"}
```

- seuil (règle 3.4) : **0.30** sur le score rendu par le candidat ;
- rapports détectés / annotés : dense 1.146, plantain 1.126, jeunes 1.212, mm 1.275, btd_val 0.996.

### `E5p90b_moy34_v5_d0.1` (5 aiguillage p90 branches)

- fabrique : `aiguillage_p90` dans `scripts/v6_banc_candidats.py` ; réglages :

```json
{"tau": 0.55, "decalage": 0.1, "petit_spec": ["melange", {"membres": ["v3", "v4"], "mode": "moyenne"}], "grand_spec": null}
```

- seuil (règle 3.4) : **0.30** sur le score rendu par le candidat ;
- rapports détectés / annotés : dense 1.077, plantain 1.139, jeunes 1.161, mm 1.290, btd_val 0.896.

### `E7_union_v5+v3_d0.05_r30` (7 réunion de pics)

- fabrique : `union` dans `scripts/v6_banc_candidats.py` ; réglages :

```json
{"membres": [["v5", "base", 0.0], ["v3", "base", 0.05]], "rayon": 30}
```

- seuil (règle 3.4) : **0.30** sur le score rendu par le candidat ;
- rapports détectés / annotés : dense 1.201, plantain 1.204, jeunes 1.153, mm 1.203, btd_val 0.668.

## Recalcul

Les cartes de chaleur sont en cache dans `out/comptage_v6/banc/cache/` (une carte par modèle, variante et jeu) ; pour un juge, il faut d'abord calculer ses cartes (`bc.ecrire_cache(modele, groupe, jeu)` avec jeu = `segmento`, `cg`, `banano`, `neg_test`, groupe `base`, ou `tta` si le finaliste lit une variante m8/x8/g8), puis :

```python
import sys; sys.path.insert(0, 'scripts')
import v6_banc_commun as bc, v6_banc_candidats as ca, v6_banc_essais as es
e = es.charger()['<finaliste>']
f = ca.construire(e['fabrique'], e['reglages'])          # Contexte -> (points xy à 5 cm, scores)
for m in ('v3', 'v4', 'v5'): bc.ecrire_cache(m, 'base', '<jeu>')
r = bc.mesurer_jeu(f, '<jeu>')[<seuil>]                  # vp, fp, fn, p, r, f1, detectes, reels, err_compte
```

Réglage seul : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/v6_banc_essais.py` (tableau complet). Points par image : `scripts/v6_banc_points.py --candidats <finaliste>` (`out/comptage_v6/banc/points/`).

Mesure : celle du carnet v5 (pics fenêtre 7, rayon 20 px, appariement un-à-un, disque de 2 000 px, points non-mères ignorés), vérifiée par l'essai 1 (`out/comptage_v6/banc/controle.txt`). Juges segmento est (`segmento`), CG1-CG9 mères seules (`cg`), banano (`banano`), sans bananier du test (`neg_test`) : définis dans `bc.jeu`, jamais chargés par C-banc.

## En clair

1. `E10_moy_v6e+v5` (mélange avec un modèle de la nuit) : moyenne des cartes de probabilité du **v6e** (C-entraîneur, lot 2 : recette v6a + jeux neufs dmpcs2 et geostar ; `out/comptage_v6/kaggle/lot2/v6e/centres_5cm_v6e.onnx`, déclaré dans `out/comptage_v6/banc/modeles_nuit.json`) et du **v5**, poids égaux ; pics fenêtre 7 ; seuil **0,30**.
2. `E5p90b_moy34_v5_d0.1` (aiguillage par image, sans modèle de la nuit) : on calcule la carte du v5 ; on prend ses pics (fenêtre 7) d'au moins 0,15 sur l'image entière ; si leur 90e centile est **sous 0,55** (réponses faibles : petits plants), on compte sur la **moyenne des cartes v3 et v4** au seuil **0,20** (score + 0,10 comparé au seuil 0,30) ; sinon sur le **v5 au seuil 0,30**. Sur le réglage, images aiguillées : dense 0 / 84, plantain 15 / 165, jeunes 0 / 1, MM 0 / 2, btd 177 / 178.
3. `E7_union_v5+v3_d0.05_r30` (réunion de pics) : pics du v5 (score tel quel) et pics du v3 (score + 0,05) réunis ; de deux points à moins de 30 px (1,5 m), on garde le plus haut score ; seuil 0,30 (donc v3 à 0,25).

## Réserves à lire avec les juges

- **324 variantes** ont été mesurées sur ce réglage : les chiffres de réglage sont optimistes.
- Le gain vient **entièrement** de btd_val (plantation tout juste plantée). Sur les 4 autres jeux (« moy4 »), aucun candidat ne bat nettement le v5 au seuil 0,30 de la chaîne (0,854) : finaliste 1 0,855, finaliste 2 0,852, finaliste 3 0,849.
- Le v6e a appris btd_train, l'autre moitié de la même orthomosaïque que btd_val : son 0,99 sur btd_val est très optimiste. Les juges ne contiennent pas cette orthomosaïque : ils diront ce qu'il en reste.
- Le v3 a choisi son époque et son seuil sur **segmento est** (aujourd'hui juge) : les finalistes 2 et 3 contiennent le v3, ils sont avantagés sur ce juge (le 2 seulement si des images de segmento sont aiguillées) ; donner aussi la moyenne des juges sans segmento est.
- La règle d'aiguillage (finaliste 2) décide **par image** ; dans la chaîne, il faudrait la décider par fenêtre de lecture ou par parcelle.
- Coût indicatif (machine partagée) : finaliste 1 = v5 + v6e partout (environ 2 fois le v5, 6 à 10 s/ha) ; 2 = v5 seul (3 à 4,5 s/ha) hors zones aiguillées, v5 + v3 + v4 (9 à 15 s/ha) dans les zones aiguillées ; 3 = v5 + v3 partout (6 à 10 s/ha).
- `v6a_soupe` (moyenne des poids des 3 graines) est cassée : aucune détection ; elle n'entre dans aucun finaliste.