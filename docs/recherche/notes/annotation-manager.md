# Notes d'annotation-manager

## 7 novembre 2026 : références du développement dense, cycle 1 (question bloquante de D-004)

**Question.** Quelles photos de `bv_session_a` montrent la pépinière en pots, et quelles sont les références du développement dense au format commun ?

**Déroulé.**
1. J'ai écrit la règle v1 avant de regarder les données (`docs/recherche/conventions_comptage.md` § 1.2). Elle portait sur la taille médiane des boîtes : moins de 1,5 m signale la pépinière.
2. J'ai appliqué v1 et fait un contrôle visuel sur la planche `out/comptage_math/annotation-manager/planche_bv_session_a.png`. **v1 est réfutée** : elle n'exclut qu'une photo, alors que la planche montre une pépinière sur environ 55 photos, dont les boîtes sont *plus grandes* que celles de la plantation dense. Le cadrage diffère : dans la pépinière, le plant isolé est encadré feuilles comprises.
3. J'ai écrit la règle v2 (§ 1.4), datée, après la planche et avant son application. Elle porte sur la densité de références dans la région comptée : moins de 0,05 /m² signale une photo hors du dense. Après application, la séparation est nette : 0,029 contre 0,060.
4. Résultat : **59 photos exclues**, dont 55 de pépinière et 4 de bordure, route ou friche (DJI_0542, 0579, 0606, 0634). **64 photos gardées.**

**Points à retenir.**
- Toutes les références denses sont des boîtes Roboflow typées `mere`. Le rappel mesure donc les « boîtes retrouvées » et la précision est une borne basse si des rejets sont détectés (§ 2).
- La règle v2 a été écrite après une inspection visuelle. Elle n'est pas aveugle, mais elle ne dépend d'aucun score.
- Échelle : seule l'erreur statistique est chiffrée. La convention des 3 m domine l'incertitude.
- Complétude : `lasuiza` (ratio médian 0,56, 130 unités suspectes) et `vols_100_022x` (75 unités suspectes) sont à surveiller. `bv_*` et `corte` sont cohérents.
- Unités non indépendantes : `lasuiza` contient 93 vrais doublons (même tuile dans deux parties Roboflow) ; `vols_100_022x` regroupe 401 découpes tirées de 78 photos.

**Reste à faire (hors de cette mission).**
- Inventaire complet des références et contrôle de fuite.
- `comptage_math/references.py`, non écrit : le CSV suffit pour le cycle 1.
- Planche des unités suspectes de `lasuiza` et de `vols_100_022x`.

## 7 novembre 2026 : complétude des références de val_iter

- J'ai écrit les critères avant le calcul (§ 5.1 de `conventions_comptage.md`). Aucune détection n'a été lue, et `val_scellee` est bloquée par une assertion.
- Verdict : **incomplètes**. Ratio médian 0,53 contre 1,11 sur `dev_reglage`, densité 0,045 contre 0,107 /m². 36 photos sur 42 sont incomplètes, et seules DJI_0905, 0906, 0910, 0912, 0924 et 0930 sont conformes. Environ la moitié des plants ne sont pas annotés. Le zoom sur DJI_0909 montre des rosettes visibles non annotées.
- La mesure des trous de 10 m s'est révélée inutile : les manques sont dispersés et ne laissent aucune cellule vide. À ne pas reprendre telle quelle.
- Question ouverte (pour independent-evaluator) : `val_scellee` est probablement touchée par le même défaut.

## 7 novembre 2026 : complétude de val_scellee et de bv_b_train (test_final.md § 6)

- J'ai appliqué les règles d'independent-evaluator, écrites avant le calcul. Aucune détection lue, aucune image produite. val_scellee n'a été ouverte que par option explicite, et l'assertion a été vérifiée.
- **val_scellee utilisable** : 40 photos conformes sur 42, ratio médian 1,07. DJI_0867 et 0903 sont incomplètes.
- **bv_b_train** : 67 photos conformes sur 71. DJI_0795, 0796, 0832 et 0834 ont un ratio inférieur à 0,83.
- Le défaut de val_iter est donc propre à L3-L4.
