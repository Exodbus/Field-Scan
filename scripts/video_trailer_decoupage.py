"""Découpage minuté du trailer Field Scan (partagé par la bande-son et le montage).

Tous les temps sont en secondes ; le film dure DUREE s à 24 i/s. Une seule définition évite que le son et l'image
se décalent.
"""
FPS = 24
DUREE = 78.0

# plans 3D rendus par scripts/video_trailer_rendu3d.py : durée (s) de chaque plan complet
DUREE_PLANS = dict(aube=5.5, rangs=4.5, orbite=4.5, fpv=3.2, grue=10.0, final=7.0, descente=5.0, oblique=2.9, contre=2.1)

# montée : chaque plan n'est utilisé qu'une fois ou deux, sur des moments différents
# (début dans le film, plan, début dans le plan, durée)
MONTEE = [
    (12.0, "oblique", 0.0, 1.8),
    (13.8, "contre", 0.0, 1.5),
    (15.3, "rangs", 0.6, 1.2),
    (16.5, "fpv", 0.6, 1.0),
    (17.5, "aube", 2.5, 0.8),
    (18.3, "oblique", 2.2, 0.7),
]

T = dict(
    texte1=(0.5, 3.0),          # « Chaque matin, des milliers de bananiers. » sur noir
    reel=(3.0, 7.4),            # photo aérienne réelle, contours RPG, « Impossible de tous les voir. »
    descente=(7.0, 12.0),       # fondu photo -> 3D, la caméra plonge vers les rangs ; « Jusqu'à aujourd'hui. »
    texte3=(9.4, 11.9),
    montee=(12.0, 19.0),
    parcelles=(19.0, 26.0),     # « Voir chaque parcelle. »
    reseau=(26.0, 33.0),        # tuile de drone -> réseau de neurones -> carte des centres
    comptage=(33.0, 40.0),      # « Compter les bananiers. »
    maladie=(40.0, 47.0),       # « Repérer la maladie. »
    visite=(47.0, 58.0),        # « Se promener dans son exploitation. » (vraie visite 3D web)
    grue=(58.0, 67.0),
    silence=(67.0, 67.6),
    titre=(67.6, 73.0),         # plan « final » sous le titre
    fin=(73.0, 78.0),           # carton de fin
)
COUPES_FORTES = [12.0, 19.0, 26.0, 33.0, 40.0, 47.0, 58.0]
TITRE_IMPACT = 67.6
SLOGAN = 70.6
VITESSE_GRUE = 10.0 / 9.0       # la révélation (10 s rendues) est jouée en 9 s
