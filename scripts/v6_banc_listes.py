#!/usr/bin/env python3
"""Listes de candidats du banc v6 (agent C-banc), rangées selon la file du plan docs/plan_nuit_10h.md, section 4.
Chaque liste rend {nom: (famille, fabrique, réglages)}. Un nom = un essai (au sens du compte d'essais).
Les listes sont ajoutées au fil de la nuit ; aucune n'est retirée (le compte d'essais reste exact)."""
import itertools

M3 = ["v3", "v4", "v5"]


def liste_ref():
    """Essai 1 (références) : chaque membre seul, à sa fenêtre de pics d'origine."""
    return {m: ("1 référence", "seul", dict(modele=m)) for m in M3}


def liste_e2():
    """Essai 2 : 8 symétries (moyenne des probabilités m8, maximum x8, moyenne des logits g8)."""
    return {f"E2_{m}_{v}": ("2 symétries", "seul", dict(modele=m, variante=v)) for m in M3 for v in ("m8", "x8", "g8")}


def liste_e3(variante="base"):
    """Essai 3 : mélanges v3 + v4 + v5 (moyenne, maximum, géométrique, logit, calibré, poids par grille de 0,25)."""
    r, suf = {}, "" if variante == "base" else f"_{variante}"
    for c in [("v3", "v4", "v5"), ("v3", "v5"), ("v4", "v5"), ("v3", "v4")]:
        for mode in ("moyenne", "maximum", "geometrique", "logit"):
            r[f"E3_{mode[:3]}_{'+'.join(c)}{suf}"] = ("3 mélange", "melange", dict(membres=list(c), mode=mode, variante=variante))
        for mode in ("moyenne", "maximum"):
            r[f"E3_{mode[:3]}cal_{'+'.join(c)}{suf}"] = ("3 mélange calibré", "melange",
                                                         dict(membres=list(c), mode=mode, variante=variante, calibre=True))
    for w in itertools.product(range(5), repeat=3):
        if sum(w) == 4 and max(w) < 4 and len(set(w)) > 1:
            for cal in (False, True):
                r[f"E3_poids{'cal' if cal else ''}_{w[0]}{w[1]}{w[2]}{suf}"] = (
                    "3 mélange poids", "melange", dict(membres=M3, mode="moyenne", poids=list(w), variante=variante, calibre=cal))
    return r


def liste_e4():
    """Essai 4 : échelles 3,5 / 5 / 7 cm ; fusion par maximum ou moyenne des cartes, ou par vote (réunion des pics)."""
    r = {}
    for m in M3:
        for v in ("s35", "s70"):
            r[f"E4_{m}_{v}_seule"] = ("4 échelle seule", "seul", dict(modele=m, variante=v))
        for nom, vs in (("3ech", ["base", "s35", "s70"]), ("5+35", ["base", "s35"]), ("5+7", ["base", "s70"])):
            for fusion in ("maximum", "moyenne"):
                r[f"E4_{m}_{nom}_{fusion[:3]}"] = ("4 échelles", "echelles", dict(modele=m, variantes=vs, fusion=fusion))
            for rayon in (12, 20):
                r[f"E4_{m}_{nom}_pts{rayon}"] = ("4 échelles", "echelles", dict(modele=m, variantes=vs, fusion="points", rayon=rayon))
    return r


C5_TAILLES = (8, 10, 12, 14, 16)
C5_ESPACEMENTS = (40, 50, 60)


def liste_e5():
    """Essai 5 : aiguillage v3 / v5 selon la taille des pics ou l'espacement médian mesurés sur l'image."""
    r = {}
    for source in ("v5", "v3"):
        for st in C5_TAILLES:
            for dec in (0.05, 0.10):
                r[f"E5_{source}_taille{st}_d{dec}"] = ("5 aiguillage", "aiguillage",
                                                       dict(source=source, critere="taille", s_taille=st, decalage=dec))
        for se in C5_ESPACEMENTS:
            r[f"E5_{source}_esp{se}_d0.1"] = ("5 aiguillage", "aiguillage", dict(source=source, critere="esp", s_esp=se, decalage=0.10))
    return r


def liste_e6():
    """Essai 6 : fenêtre des pics k_pics 3 / 5 / 9 (7 = référence), k adaptatif, seuil relatif (image, maximum local)."""
    r = {}
    for m in M3:
        for k in (3, 5, 9):
            r[f"E6_{m}_k{k}"] = ("6 k_pics", "seul", dict(modele=m, k=k))
    for m in ("v5", "v3"):
        for part in (0.4, 0.5, 0.6):
            r[f"E6_kadapt_{m}_{part}"] = ("6 k adaptatif", "k_adaptatif", dict(modele=m, part=part))
    for cible in (0.5, 0.6, 0.7):
        for plancher in (0.2, 0.3):
            for gmax in (1.5, 2.5):
                r[f"E6_relimage_v5_c{cible}_p{plancher}_g{gmax}"] = ("6 seuil relatif (image)", "relatif",
                                                                     dict(modele="v5", cible=cible, plancher=plancher, gain_max=gmax))
    for part in (0.3, 0.4, 0.5):
        for fen in (21, 41):
            r[f"E6_rellocal_v5_{part}_{fen}"] = ("6 seuil relatif (local)", "relatif_local", dict(modele="v5", part=part, fenetre=fen))
    return r


def liste_e7():
    """Essai 7 : suppression des doublons par distance (0,8 à 1,5 m = 16 à 30 px à 5 cm), sur un membre ou après fusion."""
    r = {}
    for m in ("v5", "v3"):
        for k in (3, 5):
            for rayon in (16, 20, 25, 30):
                r[f"E7_{m}_k{k}_r{rayon}"] = ("7 doublons", "doublons", dict(modele=m, k=k, rayon=rayon))
        r[f"E7_lisse_{m}_3"] = ("7 lissage", "lisse", dict(modele=m, taille=3))
    for dec in (0.05, 0.10, 0.15):
        for rayon in (16, 20, 25, 30):
            r[f"E7_union_v5+v3_d{dec}_r{rayon}"] = ("7 réunion de pics", "union",
                                                    dict(membres=[["v5", "base", 0.0], ["v3", "base", dec]], rayon=rayon))
    return r


def liste_e5b():
    """Essai 5 bis (C-analyste) : aiguillage sur le 90e centile des scores des pics du v5 ; grille tau x décalage."""
    r = {}
    for tau in (0.40, 0.45, 0.50, 0.55, 0.60):
        for dec in (0.05, 0.10, 0.15):
            r[f"E5p90_t{tau}_d{dec}"] = ("5 aiguillage p90", "aiguillage_p90", dict(tau=tau, decalage=dec))
    return r


PETITS = {"v3": None,
          "geo34": ["melange", dict(membres=["v3", "v4"], mode="geometrique")],
          "moy34": ["melange", dict(membres=["v3", "v4"], mode="moyenne")],
          "uni53": ["union", dict(membres=[["v5", "base", 0.0], ["v3", "base", 0.05]], rayon=30)]}
GRANDS = {"v5": None,
          "log345": ["melange", dict(membres=["v3", "v4", "v5"], mode="logit")],
          "uni53": ["union", dict(membres=[["v5", "base", 0.0], ["v3", "base", 0.05]], rayon=30)]}


def liste_e5c():
    """Essai 5 ter : on creuse l'aiguillage p90 (tau 0,55, plateau) en changeant les branches (mélanges, réunion)."""
    r = {}
    for np_, ps in PETITS.items():
        for ng, gs in GRANDS.items():
            if np_ == "v3" and ng == "v5":
                continue
            for dec in (0.10, 0.15):
                r[f"E5p90b_{np_}_{ng}_d{dec}"] = ("5 aiguillage p90 branches", "aiguillage_p90",
                                                  dict(tau=0.55, decalage=dec, petit_spec=ps, grand_spec=gs))
    return r


def liste_e2c():
    """Essai 2 bis : les symétries du v5 dans la branche « grands » de l'aiguillage p90 (petits = moyenne v3+v4)."""
    r = {}
    for v in ("m8", "g8", "x8"):
        for dec in (0.10, 0.15):
            r[f"E2c_p90_moy34_v5{v}_d{dec}"] = ("2 symétries dans l'aiguillage", "aiguillage_p90",
                                               dict(tau=0.55, decalage=dec, petit_spec=PETITS["moy34"],
                                                    grand_spec=["seul", dict(modele="v5", variante=v)]))
    return r


def liste_e10():
    """Essai 10 : modèles entraînés de la nuit (déclarés dans out/comptage_v6/banc/modeles_nuit.json), seuls et mélangés
    au v3 et au v5 ; et dans l'aiguillage p90 (branche petits ou grands)."""
    import v6_banc_commun as bc
    r = {}
    for m in [k for k in bc.MODELES if k not in M3]:
        r[f"E10_{m}"] = ("10 modèle de la nuit", "seul", dict(modele=m))
        for c in ([m, "v5"], [m, "v3"], [m, "v3", "v5"], [m, "v3", "v4", "v5"]):
            for mode in ("moyenne", "logit"):
                r[f"E10_{mode[:3]}_{'+'.join(c)}"] = ("10 mélange nuit", "melange", dict(membres=c, mode=mode))
        r[f"E10_union_{m}+v3"] = ("10 réunion nuit", "union", dict(membres=[[m, "base", 0.0], ["v3", "base", 0.05]], rayon=30))
        for dec in (0.10, 0.15):
            r[f"E10_p90_moy34{m[2:]}_v5_d{dec}"] = ("10 aiguillage nuit", "aiguillage_p90", dict(
                tau=0.55, decalage=dec, petit_spec=["melange", dict(membres=["v3", "v4", m], mode="moyenne")]))
            r[f"E10_p90_moy34_{m}_d{dec}"] = ("10 aiguillage nuit", "aiguillage_p90", dict(
                tau=0.55, decalage=dec, petit_spec=PETITS["moy34"], grand_spec=["seul", dict(modele=m)]))
            r[f"E10_p90_{m}_v5_d{dec}"] = ("10 aiguillage nuit", "aiguillage_p90", dict(
                tau=0.55, decalage=dec, petit_spec=["seul", dict(modele=m)]))
    return r


def liste_plateau():
    """Contrôle du plateau du finaliste 1 (tau autour de 0,55, petits = moyenne v3+v4, d 0,10)."""
    return {f"E5p90b_moy34_v5_d0.1_t{t}": ("5 aiguillage p90 plateau", "aiguillage_p90",
                                          dict(tau=t, decalage=0.10, petit_spec=PETITS["moy34"]))
            for t in (0.45, 0.50, 0.60, 0.65)}


LISTES = dict(plateau=liste_plateau, e10=liste_e10, e2c=liste_e2c, e5c=liste_e5c, e5b=liste_e5b, ref=liste_ref, e2=liste_e2, e3=liste_e3, e3m8=lambda: liste_e3("m8"), e4=liste_e4, e5=liste_e5, e6=liste_e6, e7=liste_e7)
