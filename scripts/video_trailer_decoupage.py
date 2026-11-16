"""Découpage minuté du trailer Field Scan (partagé par la bande-son et le montage).

Tous les temps sont en secondes ; le film dure DUREE s à 24 i/s. Une seule définition évite que le son et l'image
se décalent.
"""
FPS = 24
DUREE = 72.0

# plans 3D rendus par scripts/video_trailer_rendu3d.py : durée (s) de chaque plan complet
DUREE_PLANS = dict(aube=5.5, rangs=4.5, orbite=4.5, fpv=3.2, grue=10.0, final=7.0)

# (début dans le film, plan, début dans le plan, durée)
MONTEE = [
    (11.2, "rangs", 0.0, 2.6),
    (13.8, "orbite", 0.0, 2.0),
    (15.8, "fpv", 0.0, 1.6),
    (17.4, "rangs", 2.6, 1.3),
    (18.7, "orbite", 2.5, 1.0),
    (19.7, "fpv", 1.6, 0.8),
    (20.5, "final", 0.0, 0.7),
    (21.2, "aube", 3.0, 0.6),
    (21.8, "orbite", 3.9, 0.6),
    (22.4, "fpv", 2.4, 0.5),
    (22.9, "rangs", 4.0, 0.5),
    (23.4, "final", 3.0, 0.6),
]

T = dict(
    texte1=(0.5, 3.2),          # « Chaque matin, des milliers de bananiers. » sur noir
    aube=(3.2, 8.7),            # plan d'aube
    texte2=(5.0, 8.4),          # « Impossible de tous les voir. » sur l'image
    texte3=(8.7, 11.2),         # « Jusqu'à aujourd'hui. » sur noir
    montee=(11.2, 24.0),
    parcelles=(24.0, 32.0),     # « Voir chaque parcelle. »
    comptage=(32.0, 40.0),      # « Compter les bananiers. »
    maladie=(40.0, 48.0),       # « Repérer la maladie. »
    grue=(48.0, 58.0),
    silence=(58.0, 58.6),
    titre=(58.6, 65.6),         # plan « final » sous le titre
    fin=(65.6, 72.0),           # carton de fin
)
COUPES_FORTES = [11.2, 24.0, 32.0, 40.0, 48.0]
TITRE_IMPACT = 58.6
SLOGAN = 62.2
