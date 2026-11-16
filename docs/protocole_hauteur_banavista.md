# Protocole : essai « hauteur » sur banavista (14/11/2026)

**Validé par Corentin le 14/11/2026 vers 19 h 40** (« Oui, lance »). Empreinte : `docs/protocole_hauteur_banavista.sha256`.

Écrit avant toute reconstruction et avant tout calcul. Origine :
- la question de Corentin du 14/11 (« utiliser la hauteur pour différencier les bananiers ») ;
- `docs/veille_2026-11-14/hauteur.md`.

## 1. Question

Un modèle de surface (MNS) tiré par photogrammétrie des photos brutes du drone aide-t-il à séparer les couronnes de bananiers qui se touchent ?

- Méthode testée : les sommets locaux du MNS.
- Point de comparaison : le détecteur de centres v5, sur les mêmes photos.

## 2. Données

- Seule source : `data/roboflow/banavista.zip`, déjà sur le disque. Photos DJI brutes en 4 000 × 3 000, environ 1,1 cm/px, recouvrement médian de 81 %.
- **Pas de GPS** : 0 champ EXIF sur les photos vérifiées le 14/11. La reconstruction est donc relative. L'échelle est remise à partir de la taille connue d'un pixel au sol.
- **Phase 1 et phase 2 : photos d'entraînement du v5 seulement** (session A et lignes DJI_0757 à DJI_0841, `docs/protocole_comptage_v5.md`). Une seule ligne de vol suivie, choisie avant tout calcul selon une seule règle : la plus longue suite de numéros DJI consécutifs de la session A.
- Les photos de **validation** du v5 ne servent pas ici. Elles ne pourront servir, une seule fois, qu'à une phase 3 décidée plus tard par Corentin. Aucun juge ni test n'est utilisé.

## 3. Outil

- OpenDroneMap 3.6.2 : `ODM_Setup_3.6.2.exe`, licence AGPL-3.0, téléchargé le 14/11 avec l'accord de Corentin. SHA-256 vérifié contre celui publié par GitHub.
- Installé hors du dépôt.
- Réglages : ceux par défaut, avec la sortie du MNS demandée. Tout autre réglage est écrit dans le journal avant d'être essayé, et compté.

## 4. Phase 1 : la reconstruction tient-elle ?

Critère, écrit avant :
- au moins 80 % des photos de la ligne sont placées par la reconstruction ;
- le MNS couvre au moins 70 % de la zone vue.

Si l'un des deux échoue, l'essai s'arrête : la piste « hauteur » n'est pas faisable sur banavista sans GPS. Le contrôle visuel est noté pour information ; il ne fait pas foi.

## 5. Phase 2 : les sommets aident-ils ?

- Les annotations de banavista (boîtes sur les photos) sont projetées dans le repère du MNS avec les poses des caméras calculées par ODM. Les boîtes vues sur plusieurs photos sont fusionnées en un point par plant (règle de fusion écrite dans le journal avant le calcul).
- **Méthode « hauteur »** :
  - sommets locaux du MNS lissé ;
  - distance minimale entre sommets réglée sur la **moitié** des photos de la ligne (première moitié dans l'ordre DJI) ;
  - mesure sur l'autre moitié.
- **Point de comparaison** : le v5 au seuil 0,30, lu sur l'orthophoto produite par ODM, sur la même seconde moitié.
- Appariement et rayon : ceux du protocole v5.
- **Résultat jugé** : le rappel sur les plants dont la couronne touche au moins une voisine (boîtes qui se chevauchent sur la photo d'origine), puis le F1 sur tous les plants.
- **La piste est jugée prometteuse** si, sur la seconde moitié :
  - le rappel « couronnes jointives » de la méthode hauteur, ou d'une fusion simple v5 + sommets écrite avant, dépasse celui du v5 d'au moins 0,03 ;
  - et le F1 total ne baisse pas de plus de 0,01.
- Réserve à écrire avec le résultat : ce sont des photos d'**entraînement** du v5, donc le v5 y est avantagé, et la ligne de vol vient d'une seule ferme.

## 6. Ce que l'essai ne décide pas

- Aucune adoption. Une piste prometteuse ne mène qu'à une proposition à Corentin, soit des données avec photos brutes et GPS, soit une phase 3 sur la validation.
- Aucune modification de `fieldscan/`, `config.yaml` ou des protocoles existants.
- Aucun commit sans accord.
