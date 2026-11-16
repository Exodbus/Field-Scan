# Plan de la journée du 15 novembre 2026 : améliorer tous les modules

Écrit par Claude (session principale) le 15/11/2026 vers 13 h 55, **avant tout calcul de la journée**. Empreinte SHA-256 : `docs/journee_2026-11-15/empreinte_plan.txt`.

## Demande et accords de Corentin

- Demande : « Tentes des améliorations dans tous les modules », puis « Lance les kaggle et l'amélioration des modeles ».
- Kaggle autorisé : 3 h de GPU au plus par agent, compte `affilecorentin`. Avec l'échéance, les calculs doivent en pratique se terminer avant 15 h 30.
- Récapitulatif à **17 h**.

## Ce qui reste interdit

- Télécharger des données, une bibliothèque ou un modèle.
- Commiter ou pousser.
- Annoter à la main ; payer ; créer un compte ; afficher une clé.
- Modifier `fieldscan/`, `run.py`, `config.yaml`, les scripts déjà présents ou les protocoles. Une adoption est seulement **proposée**, avec le correctif prêt dans un fichier à part.

Les règles du plan du 13/11 (`docs/plan_nuit_2026-11-13.md`) restent valables quand ce plan ne dit rien d'autre.

## 1. Références en service

- **Maladies : F1.** Coût de réglage de F1 recalculé le 14/11 : 33,94 sur les 5 jeux. F1_bornes (mêmes alertes, plus rapide) a passé les juges le 14/11 mais n'est pas encore appliqué. Il compte comme F1 pour les règles.
- **Comptage : v5 au seuil 0,30.** Le 14/11, c13e a passé les juges mais a fait moins bien que le v5 sur `banana_trees_kp`. Corentin a gardé le v5.
- **Vigueur, stress hydrique, suivi temporel** : les méthodes de `fieldscan/modules/vigueur.py`, `stress.py`, `temporel.py`, avec les réglages de `config.yaml`. Il n'existe **aucune référence de terrain** pour ces modules (`docs/carnet_de_donnees.md`).

## 2. Maladies et comptage

- **Règles inchangées** : plan du 13/11, sections 4.3 (maladies) et 5.3 (comptage), familles A/B/C comprises.
- **Jeux** : mêmes niveaux que le 13/11 (réglage, juges relus).
  - Le test vierge `banana_trees_kp` a été lu le 14/11 : il n'est plus vierge et **n'est pas relu** aujourd'hui.
  - Il n'existe plus aucun test vierge pour ces deux modules : toute adoption reposera sur des juges relus, et le récapitulatif le dira.
- **Pistes déjà fermées, à ne pas refaire à l'identique** : celles des plans des 12 et 13/11, et des journaux de la nuit du 13 au 14/11 (`docs/nuit_2026-11-13/journal_*.md`). En particulier :
  - d3b est instable d'une graine à l'autre ;
  - c13e seul a échoué sur `banana_trees_kp`.
- **Idées à tester en priorité** : celles de la veille (`docs/veille_2026-11-14/synthese.md`) qui n'ont pas encore été mesurées. Exemples : lecteur kNN, morceaux comptés par seuil (maladies), suppression à l'écartement et cartes moyennées (comptage).
- **Finalistes de réserve du 14/11** : `CC1_v5h_50`, `CC3_a1_a35` (comptage) et `MC1-OU-proche` (maladies).
  - Ils ont passé la règle sur le réglage hier soir, avant toute lecture de juge.
  - Ils concourent au gel d'aujourd'hui comme les nouveaux candidats, avec leurs fragilités connues écrites à côté :
    - CC1 : 3,2 fois plus lent, gain fragile hors `btd_val` ;
    - MC1 : instable selon la graine de d3b.
- **Gel** : 2 places par module, par la règle par familles (plan du 13/11, section 6).
  - Seuls comptent les candidats écrits dans un `finalistes.md` **avant 15 h 45** et vérifiés par la session principale.
  - La session principale gèle la liste à **15 h 50**.
  - Les juges relus sont lus de 15 h 50 à 16 h 40, une lecture par finaliste.

## 3. Vigueur, stress hydrique, suivi temporel : banc d'anomalies injectées

Sans référence de terrain, une amélioration ne peut se mesurer que sur des **anomalies synthétiques connues**, injectées dans de vraies images. C'est la seule mesure de la journée pour ces modules. Elle favorise les méthodes qui collent au modèle d'injection, et le rapport doit le dire.

**Données**
- Sentinel-2 de `data/sentinel2` : Équateur et Côte d'Ivoire, 2 dates chacun.
- Pour l'ExG drone : orthomosaïques ReforesTree.

**Découpage**
- Sentinel-2 : **réglage = Équateur** (les 2 dates). **Mesure = Côte d'Ivoire**, lue une seule fois, pour les finalistes.
- Drone : réglage sur la moitié des sites ReforesTree, mesure sur l'autre moitié. Le partage est tiré par ordre alphabétique des noms de site (un sur deux), avant tout calcul.

**Injection**
- Zones en disque de 0,1 à 1 ha, placées dans des parcelles fiables (nuages < 50 %).
- Trois niveaux de gravité, et un type par module :
  - **vigueur** : baisse de la réflectance proche infrarouge, qui fait baisser NDVI et NDRE ;
  - **stress** : hausse de B11, qui fait baisser le NDMI à NDVI égal ;
  - **temporel** : baisse sur la seconde date seulement ;
  - **drone** : baisse du vert relatif sur l'orthomosaïque.
- Nombre de zones, graines, tailles et gravités sont écrits dans le journal **avant** le premier calcul. Une scène n'a jamais de zones qui se recoupent.

**Mesures**
- **Rappel** : part des zones injectées touchées à au moins 50 % de leur surface par une zone d'alerte du module.
- **Fausses alertes** : surface en alerte, en ha, hors des zones injectées. La même surface est mesurée sur les scènes sans injection.
- **Alerte de parcelle** : part des parcelles qui contiennent une zone injectée de gravité forte et passent en alerte.

**Règles, écrites avant**
- La référence est la méthode en service, recalculée par le même banc.
- **Finaliste** si, sur le réglage :
  - rappel moyen ≥ référence + 0,05 ;
  - aucun niveau de gravité ne perd plus de 0,02 ;
  - fausses alertes sur scènes sans injection ≤ référence (en ha).
- **Amélioration proposée** si, sur la mesure (lue une fois) :
  - rappel ≥ référence + 0,03 ;
  - fausses alertes ≤ référence × 1,10.
- **Robustesse** : variantes de méthode (indice, lissage, seuils, masque de nuages, correction de la variation commune au site, etc.). Une variante qui ne change que les seuils de `config.yaml` compte comme un essai.
- Toute règle propre (grilles, ordre des essais) est écrite dans le journal avant son calcul. Le nombre d'essais y est compté.

## 4. Équipe (cinq agents, puis les juges)

| Agent | Travail | Écrit dans |
| --- | --- | --- |
| M-banc | maladies sans entraînement (processeur, 2 fils) | `out/maladies/jour_1511/banc/`, `scripts/m15_banc_*.py` |
| M-kaggle | maladies avec entraînement, Kaggle 3 h au plus | `notebooks/m15_*.py`, `out/maladies/jour_1511/kaggle/`, `modeles/maladies_jour_1511/` |
| C-banc | comptage sans entraînement (processeur, 2 fils) | `out/comptage/jour_1511/banc/`, `scripts/c15_banc_*.py` |
| C-kaggle | comptage avec entraînement, Kaggle 3 h au plus | `notebooks/c15_*.py`, `out/comptage/jour_1511/kaggle/`, `modeles/comptage_jour_1511/` |
| Télédétection | banc d'anomalies injectées, section 3 (processeur, 2 fils) | `out/teledetection/jour_1511/`, `scripts/t15_*.py` |
| Juges (15 h 50) | une lecture des juges relus pour la liste gelée ; mesure Côte d'Ivoire pour les finalistes de télédétection | `out/controle_jour_1511/` |

- La session principale joue le rôle du Contrôleur : elle relit règles, fuites et chiffres, et admet les finalistes.
- Chaque agent tient un journal `docs/journee_2026-11-15/journal_<agent>.md` et n'écrit que dans ses dossiers.
- Avant 15 h 50, aucun agent ne lit les juges relus, ni `banana_trees_kp`, ni les images Sentinel-2 de Côte d'Ivoire.
