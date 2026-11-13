# Notes de scientific-researcher

## Mission 2 — 7 novembre 2026 : méthodes explicites de comptage de couronnes

Livrable : `docs/recherche/bibliographie.md` (25 références, 10 vérifiées « oui »).

### Requêtes web (36 recherches ou lectures environ)

| # | Requête ou page | Résultat |
| --- | --- | --- |
| 1 | PLOS One 2019 banana plant counting UAV RGB | Neupane et al. 2019 trouvé ; texte intégral lu sur PMC (PMC6797093) |
| 2 | Remote Sensing 2021 banana multispectral multi-date | Aeberli et al. 2021 trouvé |
| 3 | mdpi.com (www et sans www), doaj.org, dépôt UNE (PDF) | 403 ou 404 ; résumé lu via la notice UNE et l'API Crossref |
| 4 | Wulder Niemann 2000 local maximum filtering | Notice ; Crossref confirme Wulder, Niemann, **Goodenough** (pas White) |
| 5 | Loy Zelinsky fast radial symmetry | Notice ANU lue |
| 6 | Lindeberg 1998 scale selection | Résumé de l'auteur (KTH) lu ; pages 77-116 (auteur) contre 79-116 (catalogue) |
| 7 | Perrin Descombes Zerubia 2005 EMMCVPR | Titre retrouvé (« Adaptive simulated annealing… ») ; HAL bloqué par anti-robot ; volume LNCS non vérifié |
| 8 | Perrin et al. EUSIPCO 2004 | Notice IEEE/EURASIP ; ordre des auteurs discordant entre sources |
| 9 | ERCIM News 61 (Zerubia, Cournède) | Lu : ellipses, peupleraies IFN, pas de chiffres |
| 10 | Pollock 1996 thèse UBC | Notice UBC (DOI 10.14288/1.0051597) |
| 11 | Larsen et al. 2011 six algorithmes | Notice Crossref + résumé relayé |
| 12 | Freeman Adelson steerable filters | Page MIT de l'auteur lue |
| 13 | Aeberli + GEOBIA + GSD | Rien de nouveau ; GSD et lieu non trouvés |
| 14 | oil palm UAV local maxima LoG | Pistes : Manandhar 2016, Daliakopoulos 2009 |
| 15 | Bigün Granlund structure tensor | Thèse de Bigün et cours ; ICCV 1987 p. 433-438 confirmé par deux catalogues |
| 16 | Gougeon 1995 valley-following | Notice ; écarté du tableau (voir plus bas) |
| 17 | Woebbecke 1995 ExG | Notice ASABE |
| 18 | Gitelson 2002 VARI | Notice et résumé relayé |
| 19 | marker-controlled watershed UAV RGB | Yu et al. 2022 ; Dong et al. 2020 (vergers, F 0,99 relayé, non retenu faute de vérification) |
| 20 | Ballard 1981 Hough généralisée | Notice DOI |
| 21 | palm Hough circular radial voting | Al Mansoori et al. 2018 (SPIE) ; Manandhar 2016 |
| 22 | Manandhar 2016 (page ISPRS Annals) | Lu |
| 23 | radial symmetry tree crown | Ozdarici-Ok 2015 ; Ok & Ozdarici-Ok 2017, 2018 |
| 24 | AGRIS Ozdarici-Ok 2015 | Lu |
| 25 | API Semantic Scholar | 429 (trop de requêtes) ; remplacé par l'API Crossref |
| 26 | Crossref rs13112123, rs14020295 | Résumés Aeberli et Yu lus |
| 27 | banana UAV YOLO F1 dense | Jiang et al. 2023 (MIoP-NMS) ; Sönmez et al. 2025 |
| 28 | Gomez Selvaraj 2020 | Notice Crossref ; chiffres relayés |
| 29 | ReforesTree | Résumé arXiv lu ; correspond à la ressource « Agroforestry inventory » de la consigne (`docs/carnet_de_donnees.md`, section 6) |
| 30 | Gabor texture tree crown orchard | Aksoy et al. 2012 ; Recio et al. 2005 (non retenu) |
| 31 | LoG blob tree crown UAV | Daliakopoulos 2009 ; Wang, Gong, Biging 2004 |
| 32 | Fourier crop row detection UAV | Brevets et articles de rangs ; rien de spécifique au comptage de couronnes |
| 33 | Srestasathiern 2014 ; Shafri 2011 ; Pouliot 2002 | Notices ; Shafri non retenu |
| 34 | Philemon banana counting gaussian orientation stripes | **Aucune trace publique** |
| 35 | Larsen Rudemo 1998 ; Daugman 1985 | Notices |
| 36 | coconut palm UAV dense canopy | Étude d'Exeter 2019 (palmiers, hauteur) : page en 403, non retenue |

### Sources écartées ou non retenues dans le tableau, et pourquoi

- **Sönmez, Ashyrov, Toylan (2025)**, bananiers YOLOv8/v9, Kırklareli Univ. J. Eng. Sci. : deux résumés relayés **se contredisent** sur le F1 (94,9 % contre 85 %). Non retenu tant que la source n'est pas lue.
- **Dong et al. (2020)**, partage des eaux sur vergers, Remote Sensing : F 0,99 relayé par un moteur de recherche, page non lue. Écarté faute de vérification ; à lire si dense-canopy-engineer en a besoin.
- **Al Mansoori, Kunhu, Al Ahmad (2018)**, palmiers, NDVI + Hough circulaire, SPIE 10792 : « plus de 95 % » relayé ; multispectral ; page non lue.
- **Gougeon (1995)**, suivi de vallées, Can. J. Remote Sens. 21 : 274-284 : 81 % à 31 cm/px relayé par la page du Service canadien des forêts. Écarté pour rester sous 25 références ; méthode pour forêts de conifères à ombre entre couronnes.
- **Ke & Quackenbush (2011)**, revue, IJRS 32(17) : 4725-4747, DOI 10.1080/01431161.2010.494184 : revue utile mais sans chiffre propre.
- **Daugman (1985)**, filtres de Gabor 2D, JOSA A 2(7) : 1160-1169 : fondement des filtres de Gabor ; remplacé par Freeman & Adelson, plus directement utile.
- **Shafri, Hamdan, Saripan (2011)**, palmiers, IJRS 32(8) : 2095-2115 : 95 % relayé ; méthode en six étapes non lue.
- **Daley et al. (1998)**, Wassenaar et al. (Fourier, vignes), Recio et al. (2005, Gabor) : vus seulement comme citations dans d'autres résultats.
- **Article d'Exeter 2019 (palmiers, modèle de hauteur)** : page en 403.

### Incidents

- **Deux PDF enregistrés malgré moi par l'outil WebFetch** : en lisant en ligne `manandhar_co_stilla_isprs16_pap.pdf` (TUM) et `tgars_orchard_detection.pdf` (Bilkent), l'outil a écrit le contenu binaire dans son cache de résultats, hors du dépôt :
  `C:\Users\coren\.claude\projects\C--00-DATA-02---Cours-ING4-06---intelligence-lab-projet-field-scan\73d9db29-34df-41fd-8288-592ba7541c26\tool-results\webfetch-1794014618471-fjsiym.pdf` (4,8 Mo) et `...\tool-results\webfetch-1794014787848-d2swbm.pdf` (7,5 Mo). Je ne les ai ni ouverts ni exécutés. Je n'ai pas Bash pour les supprimer. Après ces deux cas, je n'ai plus ouvert d'adresse de PDF.
- Plusieurs éditeurs refusent la lecture automatique (MDPI, DOAJ, HAL : 403 ou anti-robot). L'API Crossref a servi pour les notices et certains résumés.

### Points à vérifier plus tard

- Aeberli et al. 2021 : résolution, lieu, paramètres du LMF et du TM, tolérance d'appariement (texte intégral).
- Chiffres de Wulder 2000, Pouliot 2002, Daliakopoulos 2009, Srestasathiern 2014 : relayés, non lus dans la source.
- Volume LNCS de Perrin et al., EMMCVPR 2005.
