# Récapitulatif de la nuit du 9 au 10 novembre 2026 : module maladies

Détail heure par heure : `docs/maladies_equipe/journal_nuit_9_10.md`. Règles, amendements et résultats : `docs/protocole_maladies_cinq_classes.md`. **Rien n'a été commité ni poussé.**

## En une phrase

**Le module maladies de la chaîne est meilleur** : il rate 12 fois moins de feuilles malades en validation (107 → 9 sur 2 001), et de 39 à 64 % de moins dans trois pays qu'aucun modèle n'avait vus (Vietnam, Inde, Éthiopie). Le prix : plus de fausses alertes (0,7 % → 1,5 % en validation). Chaque changement a été décidé par une règle écrite avant la mesure.

## Ce qui a changé dans la chaîne (`config.yaml`, bloc `maladies`, et `fieldscan/modules/maladies.py`)

1. **Deux branches** : l'aiguilleur « loin / près », réussi le 9 novembre, est branché. Il est réajusté à l'identique et enregistré dans `modeles/maladies_aiguilleur/`.
   - Plante entière : la v2, avec « à confirmer par un gros plan de la zone malade ». Ces alertes ont une confiance « faible » dans le bulletin.
   - Gros plan : la **soupe v2 + v8**, retenue par la règle de la nuit, aucun nouveau candidat n'étant adoptable.
2. **« Je ne sais pas » avec une forte probabilité de maladie devient une alerte « malade, non identifiée »**. C'était ton choix ouvert d'hier ; je l'ai tranché par la règle de coût du seuil d'alerte (2 × ratées + fausses alertes) :
   - gros plans (validation) : coût 233 → 33 ;
   - plantes entières (photos du robot) : coût 934 → 423.

   On découvre au passage que la mesure « malades dites saines » (4 sur 2 001) cachait **112 malades sans alerte**, dites « je ne sais pas ».
3. **Probabilités affichées calibrées** : température réglée sur la validation (0,61 pour la soupe, 0,59 pour la v2). Les décisions ne changent pas.
4. Le module accepte aussi les modèles à 5 classes et les réseaux DINOv2 et DINOv3. Rien de cela n'est utilisé aujourd'hui.

Module complet contre l'ancienne chaîne (v2 seule) :

| Jeu | Malades sans alerte | Saines en alerte | Sigatoka nommée |
| --- | --- | --- | --- |
| Validation (Tanzanie) | 107 → **9** / 2 001 | 7 → 15 / 1 000 | 961 → 965 / 1 000 |
| BananaLSD (Bangladesh) | 88 → **0** / 807 | 0 → 3 / 90 | 445 → 452 / 473 |
| TDTU (Vietnam) | 424 → **153** / 1 059 | 59 → 119 / 577 | 85 → 112 / 404 |
| PSFD (Inde) | 490 → **298** / 738 | — | 63 → 108 / 474 |
| Éthiopie | 592 → **338** / 1 134 | 1 → 2 / 155 | 38 → 48 / 320 |

Contrôles :
- intégration : réponses de la chaîne identiques aux fichiers du modèle, probabilités égales à 10⁻⁴ près ;
- chaîne complète (`run.py --modules maladies` sur les photos de démonstration) : réussie.

## Les essais de la nuit : apprendre Cordana et Pestalotiopsis

- **Idée, trouvée par la recherche web** : un jeu Mendeley public du Bangladesh (`wfzpdmc5vx`, CC BY 4.0, 424 photos) contient Cordana et Pestalotiopsis, les deux maladies que tous nos modèles appellent « Sigatoka ». Sources : Fort et al. 2021, quelques exemples des classes voisines suffisent.
- **Contrôles du jeu** :
  - aucune copie de BananaLSD ;
  - 2 copies de banana-buddy, retirées ;
  - étiquettes vérifiées sur une planche.
- **Modèles entraînés** sur Kaggle, avec 5 classes : ConvNeXt (C5), DINOv2 (D5), DINOv3 (E5), plus l'ensemble C5 + D5. Le résultat de L5 (DINOv2 ViT-L) est plus bas.

| | v2 | soupe | C5 | D5 | E5 |
| --- | --- | --- | --- | --- | --- |
| Cordana et Pestalotiopsis dites Sigatoka (garde ≤ 246 / 334) | 230 | 273 | **109** | **124** | **119** |
| Cordana bien nommée (sur 162) | — | — | 39 | 36 | 33 |
| Pestalotiopsis bien nommée (sur 172) | — | — | 6 | 2 | 1 |
| Rappel équilibré BananaLSD (≥ 0,958) | 0,948 | 0,956 | 0,908 | 0,931 | 0,948 |

**Aucun n'est adoptable.** C'est la première méthode qui divise par deux les maladies inconnues dites Sigatoka. Mais Cordana n'est bien nommée qu'une fois sur quatre, Pestalotiopsis presque jamais, et le reste part en « je ne sais pas ». Avec 100 photos par maladie venant d'un seul jeu, le modèle apprend surtout que « ce n'est pas de la Sigatoka ». À écrire comme piste prometteuse, pas comme résultat.

**Nouveaux jeux de mesure**, jamais vus par nos modèles : PSFD (Inde), Éthiopie, TDTU en entier. Ils confirment que **la soupe est meilleure que la v2 partout**, comme sur twakihasan chez ton binôme.

**L5, un DINOv2 ViT-L (300 M de paramètres, 2 réseaux), fini à 6 h 13 et mesuré à part par la même règle : pas adoptable non plus.**
- C'est le meilleur sur les nouvelles maladies :
  - Cordana et Pestalotiopsis dites Sigatoka : **82** sur 334 ;
  - Cordana bien nommée 50 fois ;
  - 84 % de noms nouveaux justes, le seul au-dessus de 80 %.

  C'est aussi le plus sobre : 1 fausse alerte sur 1 000 en validation.
- Il échoue ailleurs :
  - Sigatoka nommée sur BananaLSD : 388 sur 473, contre 445 pour la v2 ;
  - il dit « saine » plus souvent devant les maladies qu'il ne connaît pas (TDTU 116 contre 69, Xanthomonas 309 contre 245) ;
  - en validation, il appelle « Pestalotiopsis » 52 Sigatoka.
- Le choix refait avec tous les candidats ne change rien : **la soupe reste la branche « proche »**. Un réseau plus gros ne compense pas une centaine de photos par maladie.

## Limites à connaître

- **De loin**, la v2 distingue mal les plantes malades des saines. Avec la nouvelle règle, 79 % des plantes saines du robot reçoivent une alerte « à confirmer par un gros plan », de confiance faible. Pour revenir à l'ancienne règle : `jnsp_alerte_loin: false` dans `config.yaml`.
- **Maladies inconnues** : toutes déclenchent maintenant une alerte, mais la soupe les nomme encore « Sigatoka » dans 82 % des cas (v2 : 69 %).
- **TDTU** : les fausses alertes passent de 10 % à 21 %. 29 % de ses photos sont aiguillées « loin ».
- Le **nouveau récap de ton binôme** (artefact claude.ai) n'a pas pu être lu : il est introuvable pour ce compte, peut-être pas partagé. Je ne sais donc pas ce qu'il a fait d'autre.

## Ce qui t'attend (ton accord)

1. **Commit** sur `maladies/test-khadavy`, si tu es d'accord :
   - protocole, journal et ce récap :
     - `docs/protocole_maladies_cinq_classes.md` ;
     - `docs/maladies_equipe/journal_nuit_9_10.md` ;
     - `docs/maladies_equipe/recap_matin_10_nov.md` ;
   - chaîne :
     - `fieldscan/modules/maladies.py` ;
     - `README.md` (lignes maladies) ;
     - **le bloc `maladies` de `config.yaml` seulement**, car le reste du fichier porte des changements de comptage qui ne sont pas les miens ;
   - carnet : `notebooks/entrainer_maladies_cinq_classes_kaggle.py` ;
   - scripts :
     - `telecharger_mendeley.py`, `controle_fuites_mendeley_bd.py` ;
     - `predire_existants_cinq_classes.py`, `mesurer_cinq_classes.py` ;
     - `ajuster_aiguilleur.py`, `regler_temperature.py` ;
     - `verifier_module_maladies.py`, `evaluer_module_maladies.py` ;
     - `mesurer_jnsp_alerte.py`, `mesurer_jnsp_loin.py` ;
   - à ne pas commiter : les poids (`modeles/maladies_aiguilleur/`, `out/maladies/cinq_classes/kaggle/*/*.pt`) et les données (`data/raw/mendeley_wfzpdmc5vx/`, `out/maladies/maladies_nuit/`).
2. **Ton binôme** : le module de la chaîne utilise désormais la soupe pour les gros plans. Il voudra sans doute le savoir, ainsi que les chiffres des jeux neufs.
3. **Ménage** (si tu veux) :
   - sur ton Kaggle : jeux privés `maladies-nuit` et `maladies-l5-reseau1` ; carnets `entrainer-maladies-cinq-c5`, `-d5`, `-e5` et `-l5` ;
   - sur ton PC :
     - le jeu Mendeley téléchargé, dans `data/raw/mendeley_wfzpdmc5vx/` (34 Mo) ;
     - les poids des candidats non retenus, dans `out/maladies/cinq_classes/kaggle/` (2,3 Go, dont 1,2 Go pour L5).

## Pour le rapport

- Architecture finale : aiguilleur, puis deux branches, puis décision en deux étapes. Chaque élément a été décidé par une règle écrite avant sa mesure.
- Un résultat simple et fort : **compter « je ne sais pas » comme une alerte quand la maladie est probable** fait passer les malades sans alerte de 107 à 9 en validation.
- Limites : la vue de loin reste faible (elle ne fait qu'orienter vers un gros plan) ; les maladies inconnues sont mal nommées ; apprendre de nouvelles maladies demande plus de 100 photos par maladie et plusieurs sources.
