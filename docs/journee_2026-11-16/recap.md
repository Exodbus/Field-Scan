# Récapitulatif de la nuit du 15 au 16 novembre 2026

Pendant ton sommeil : quatre essais de modèles, une vidéo de démo et une nouvelle visite 3D. **Rien n'est commité, rien n'est adopté, rien n'a coûté d'argent.**

## 1. Ce qu'il y a à voir

| Quoi | Où |
| --- | --- |
| Pitch vidéo de 60 s (version 3, après deux tours de critiques par trois agents) | `out/video_demo/field_scan_pitch_60s_v3.mp4` (1080p) et `_720p.mp4` (21 Mo, pour le téléphone) |
| Visite 3D de 13 parcelles de Basse-Pointe (bordures, panneaux, liste, fiches) | `out/visite_basse_pointe_zone/` |
| Page d'accueil de la démo en trois sites | `out/demo_finale/index.html` |

Pour tout ouvrir, lance la commande ci-dessous, puis va sur <http://localhost:8770/demo_finale/>.

```
.venv/Scripts/python.exe -m http.server 8770 -d out
```

## 2. Modèles

### Comptage : un finaliste (essai c16, 1,2 h de GPU)

**L'idée.** Quand l'image d'origine est nette (7,5 cm/px ou mieux, lu dans le GeoTIFF), on garde le v5. Au-delà, un spécialiste de la basse résolution prend le relais. À 5 cm, il n'y a donc aucune perte possible.

**Le résultat.** La règle a été écrite et figée à 0 h 36, avant toute mesure. Sur 10 candidats, 8 sont finalistes, et le premier est **c16_a au seuil 0,35**.

| Image dégradée à 11 cm/px | v5 | c16_a |
| --- | --- | --- |
| F1 moyen des 5 jeux de réglage | 0,60 | **0,86** |
| Agroforesterie, ReforesTree (rappel des mères) | 0,73 | 0,86 |
| Plantain du Ghana (F1) | 0,13 | 0,38 |
| Erreur de compte | 0,41 | 0,06 |

**À savoir.**
- Les 4 nouveaux réseaux se tiennent en 0,003 : c'est du bruit de graine.
- c16_a est le moins bon des quatre en agroforesterie.
- Aucun juge n'a été lu.
- La fourchette du bulletin serait à recalculer pour ce réseau.
- La note d'intégration est dans `out/comptage/jour_1611/note_integration.md`. **Rien n'est installé.**

### Maladies : deux essais, aucun finaliste (1,65 h de GPU)

- **PlantVillage (Xanthomonas).**
  - Contrôle de fuite : aucune fuite.
  - Mesure unique de la chaîne installée : **0 malade raté sur 183**. Elle nomme toutefois souvent la maladie « fusariose », faute de classe dédiée.
  - Essai d'apprentissage avec 200 photos : le coût monte à 35,1 (la limite est 32,9), et les malades éthiopiennes ratées passent de 117 à 162.
- **Robustesse aux photos de mauvaise qualité.** Elle aggrave l'Éthiopie (174 ratées). L'hypothèse « c'est la résolution » est réfutée : le Xanthomonas éthiopien n'existe dans aucune autre source apprise.
- **F1_bornes reste en service.**

## 3. Ce qui a changé dans le code avec ton accord (non commité)

- **RPG de Basse-Pointe** : téléchargé (IGN, Etalab 2.0) et branché sur la visite.
- **Règle des 0,5 ha pour la vigueur** (`fieldscan/bulletin.py`, `config.yaml`) :
  - les petites zones restent affichées sans pénaliser le score ;
  - Basse-Pointe : 111 parcelles vertes sur 112 ;
  - Côte d'Ivoire : les 2 parcelles rouges passent en orange, et le stress hydrique reste signalé.
- **Higgsfield** : installé et connecté. Ton illimité n'est pas visible par le connecteur, et la seule génération tentée (7,5 crédits) a été bloquée par le garde-fou. **0 crédit dépensé.**

## 4. Ce que tu dois décider

1. **Comptage** : écrire une règle et lire les juges dégradés à 11 cm pour c16_a, avant toute adoption de l'aiguillage.
2. **Vidéo** : valider la v3, ou demander des retouches.
3. **Commit** : la journée et la nuit ne sont pas commitées (visites, scripts, règle de vigueur, notes).
4. **Ménage** :
   - `out/video_demo/travail/` : environ 3 000 images intermédiaires ;
   - `C:/out/video_demo/travail/test_B/` : hors dépôt, à effacer à la main ;
   - `C:/Users/coren/kaggle_tmp/c16/` : 1,1 Go.

**GPU Kaggle de la nuit** : environ 2,9 h (c16 1,2 ; Xanthomonas 0,8 ; basse résolution 0,85). Il restait environ 22 h sur 30 h cette semaine avant ces essais.
