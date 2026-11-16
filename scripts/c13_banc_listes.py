#!/usr/bin/env python3
"""Listes de candidats de la nuit du 13/11 (agent C-banc). Chaque liste rend {nom: (famille, fabrique, réglages)}.
Les listes sont ajoutées au fil de la nuit, aucune n'est retirée : le compte d'essais reste exact."""

E5P90B = dict(tau=0.55, decalage=0.1, petit_spec=["melange", {"membres": ["v3", "v4"], "mode": "moyenne"}], grand_spec=None)


def liste_ref():
    """Références : v5 (référence de la nuit, lue au seuil 0,30) et E5p90b recalculé par ce banc (point de départ de CB1)."""
    return {"v5": ("référence", "seul", dict(modele="v5")),
            "E5p90b": ("A aiguillage (nuit 12/11)", "aiguillage_p90", E5P90B)}


FAM_A = "A aiguillage v2"
P34 = ["v3", "v4"]


def _v2(**k):
    base = dict(tau=0.55, decalage=0.10, petits=P34, mode_petit="moyenne")
    base.update(k)
    return (FAM_A, "aiguillage_v2", base)


def liste_cb1a():
    """CB1, première passe (écrite à 23:41 avant mesure) : un facteur à la fois autour d'E5p90b."""
    r = {"CB1_v2_temoin": _v2()}                                     # doit redonner E5p90b
    for d in (100, 200, 300):
        r[f"CB1_dens{d}"] = _v2(dens_min=d)
    for e in (60, 70):
        r[f"CB1_esp{e}"] = _v2(esp_max=e)
    for a in (0.05, 0.10, 0.15):
        r[f"CB1_acc{a:.2f}"] = _v2(accord_v5=a)
    for s in (0.20, 0.25, 0.30, 0.35):
        r[f"CB1_sp{s:.2f}"] = _v2(seuil_petit=s)
    for d in (0.0, 0.05, 0.15):
        r[f"CB1_dec{d:.2f}"] = _v2(decalage=d)
    for d in (0.10, 0.15, 0.20):
        r[f"CB1_geo345_dec{d:.2f}"] = _v2(petits=["v3", "v4", "v5"], mode_petit="geometrique", decalage=d)
    for d in (0.10, 0.15):
        r[f"CB1_min34_dec{d:.2f}"] = _v2(mode_petit="minimum", decalage=d)
    for t in (0.50, 0.60):
        r[f"CB1_tau{t:.2f}"] = _v2(tau=t)
    return r


def liste_cb1b():
    """CB1, combinaisons (écrites à 23:41 avant mesure) : densité x accord du v5 x seuil de la branche x tau."""
    r = {}
    for t in (0.55, 0.60):
        for a in (None, 0.05, 0.10):
            for nom, k in (("dec0.10", dict(decalage=0.10)), ("dec0.05", dict(decalage=0.05)),
                           ("sp0.25", dict(seuil_petit=0.25)), ("sp0.30", dict(seuil_petit=0.30))):
                r[f"CB1_dens200_tau{t:.2f}_acc{a}_{nom}"] = _v2(tau=t, dens_min=200, accord_v5=a, **k)
    return r


def liste_cb1c():
    """CB1, troisième passe (écrite à 23:47 avant mesure) : preuve minimale pour aiguiller. Après cb1a/cb1b, toute la perte
    vient de 15 tuiles plantain aiguillées (5 pieds de plus, 66 fausses de plus). Deux signaux :
    n_min_petit (au moins N pics dans la branche « petits » de l'image) et ratio_min (la branche « petits » voit au moins
    R fois ce que voit le v5 à 0,30), seuls ou avec la densité >= 200 /ha et l'accord du v5 >= 0,05."""
    r = {}
    for n in (20, 30, 40):
        r[f"CB1_npet{n}"] = _v2(n_min_petit=n)
        r[f"CB1_npet{n}_dens200_acc0.05"] = _v2(n_min_petit=n, dens_min=200, accord_v5=0.05)
    for q in (1.5, 2.0, 2.5):
        r[f"CB1_rmin{q}"] = _v2(ratio_min=q)
        r[f"CB1_rmin{q}_dens200_acc0.05"] = _v2(ratio_min=q, dens_min=200, accord_v5=0.05)
    for n in (20, 30):
        for q in (1.5, 2.0):
            r[f"CB1_npet{n}_rmin{q}_dens200_acc0.05"] = _v2(n_min_petit=n, ratio_min=q, dens_min=200, accord_v5=0.05)
    for n in (30,):
        for d in (0.15,):
            r[f"CB1_npet{n}_dec{d}_dens200_acc0.05"] = _v2(n_min_petit=n, decalage=d, dens_min=200, accord_v5=0.05)
            r[f"CB1_npet{n}_geo345dec0.20_dens200"] = _v2(n_min_petit=n, petits=["v3", "v4", "v5"], mode_petit="geometrique",
                                                         decalage=0.20, dens_min=200)
    return r


FAM_T = "A trous de plantation"


def liste_cb3a():
    """CB3 (écrite à 23:51 avant mesure) : seconde passe à seuil bas dans les trous de la géométrie de plantation, sur le v5.
    Ancres = points du v5 >= 0,30 ; pics bas du v5 dans [0,30 - delta, 0,30) ou de la moyenne v3 + v4 >= plancher ;
    promotion si le pic bouche un trou au milieu d'un rang (« milieu »), tombe sur une place vide du réseau (« reseau »),
    ou l'un des deux."""
    r = {}
    for dl in (0.10, 0.15, 0.20):
        for mode in ("milieu", "reseau", "les_deux"):
            r[f"CB3_v5_d{dl:.2f}_{mode}"] = (FAM_T, "trous", dict(delta=dl, mode=mode))
    for pl in (0.15, 0.20):
        for mode in ("milieu", "les_deux"):
            r[f"CB3_v5_bas34p{pl:.2f}_{mode}"] = (FAM_T, "trous", dict(carte_bas=["v3", "v4"], plancher=pl, mode=mode))
    for mode in ("milieu", "les_deux"):
        r[f"CB3_v5_d0.15_{mode}_tol0.20"] = (FAM_T, "trous", dict(delta=0.15, mode=mode, tol_d=0.20, tol_angle=20.0))
    return r


def liste_cb1d():
    """CB1 (23:52) : la même grille que cb1c, avec le compte des pics « petits » corrigé (au seuil de service 0,30 sur le
    score rendu, compte_30). Écrite avant mesure."""
    r = {}
    for nom, (fam, fab, reg) in liste_cb1c().items():
        r[nom + "_c"] = (fam, fab, dict(reg, compte_30=True))
    return r


CB1_CHOIX = dict(n_min_petit=30, dens_min=200, accord_v5=0.05, compte_30=True)      # CB1_npet30_dens200_acc0.05_c


def liste_cb3b():
    """CB3 dans la branche « petits » du choix CB1 (écrite à 23:58 avant mesure) : sur les images aiguillées seulement,
    les pics bas de la branche (score rendu dans [bas, 0,30)) sont promus s'ils bouchent un trou de la plantation."""
    r = {}
    for bas in (0.20, 0.25):
        for mode in ("milieu", "reseau", "les_deux"):
            r[f"CB13_trous_b{bas:.2f}_{mode}"] = ("A aiguillage v2 + trous", "aiguillage_v2",
                                                 dict(_v2(**CB1_CHOIX)[2], trous=dict(bas=bas, mode=mode)))
    return r


def liste_cb3c():
    """CB3, voisinage du meilleur de cb3b (« reseau », bas 0,20), écrite à 00:04 avant mesure : bas 0,15 / 0,10 ;
    tolérance de position 0,20 / 0,40 x d ; au moins 12 ancres au lieu de 6 (non : min_ancres fixe à 6 dans promouvoir)."""
    r = {}
    for bas in (0.15, 0.10):
        r[f"CB13_trous_b{bas:.2f}_reseau"] = ("A aiguillage v2 + trous", "aiguillage_v2",
                                             dict(_v2(**CB1_CHOIX)[2], trous=dict(bas=bas, mode="reseau")))
    for tol in (0.20, 0.40):
        r[f"CB13_trous_b0.20_reseau_tol{tol:.2f}"] = ("A aiguillage v2 + trous", "aiguillage_v2",
                                                     dict(_v2(**CB1_CHOIX)[2], trous=dict(bas=0.20, mode="reseau", tol_d=tol)))
    return r


def liste_cb1e():
    """CB1 sans dépendance à la taille de l'image (écrite à 00:16 avant mesure) : la preuve minimale (30 pics par image)
    est remplacée par « jeune plantation sur sol nu » : part de pixels verts (ExG > 0,10) au plus vert_max ; garde-fous
    densité >= 200 /ha et accord du v5 >= 0,05 ; avec ou sans les trous (« reseau », bas 0,20)."""
    r = {}
    base = dict(dens_min=200, accord_v5=0.05, compte_30=True)
    for vm in (0.25, 0.30, 0.40, 0.50):
        r[f"CB1_vert{vm:.2f}_dens200_acc0.05"] = _v2(vert_max=vm, **base)
        r[f"CB13_vert{vm:.2f}_trous_b0.20_reseau"] = ("A aiguillage v2 + trous", "aiguillage_v2",
                                                     dict(_v2(vert_max=vm, **base)[2], trous=dict(bas=0.20, mode="reseau")))
    r["CB13_npet30_vert0.40_trous_b0.20_reseau"] = ("A aiguillage v2 + trous", "aiguillage_v2",
                                                    dict(_v2(vert_max=0.40, **CB1_CHOIX)[2], trous=dict(bas=0.20, mode="reseau")))
    return r


def liste_plateau():
    """Contrôle du plateau autour du choix CB3 (écrit à 00:24 avant mesure ; mesure seulement, le choix ne change pas) :
    tau 0,50 / 0,60, sans accord du v5, sans densité minimale, 40 pics au lieu de 30."""
    T = dict(trous=dict(bas=0.20, mode="reseau"))
    r = {}
    for nom, k in (("tau0.50", dict(tau=0.50)), ("tau0.60", dict(tau=0.60)), ("sansacc", dict(accord_v5=None)),
                   ("sansdens", dict(dens_min=None)), ("npet40", dict(n_min_petit=40))):
        r[f"CB13_plateau_{nom}"] = ("A aiguillage v2 + trous", "aiguillage_v2", dict(_v2(**{**CB1_CHOIX, **k})[2], **T))
    return r


def liste_cb1f():
    """CB1, famille C (écrite le 14/11 à 13:20 avant mesure ; cartes du spécialiste c13d de C-entraîneur, seuil propre
    0,35) : c13d dans la branche « petits » des choix CB1 et CB3 (mêmes garde-fous), décalage -0,05 (c13d à 0,35 quand
    la grille est à 0,30) / 0 / +0,05 ; et moyenne v3 + v4 + c13d (décalage 0,10)."""
    r = {}
    for d in (-0.05, 0.0, 0.05):
        r[f"CB1C_c13d_dec{d:+.2f}"] = ("C aiguillage v2 + c13d", "aiguillage_v2", _v2(petits=["c13d"], decalage=d, **CB1_CHOIX)[2])
        r[f"CB13C_c13d_dec{d:+.2f}_trous"] = ("C aiguillage v2 + c13d + trous", "aiguillage_v2",
                                             dict(_v2(petits=["c13d"], decalage=d, **CB1_CHOIX)[2], trous=dict(bas=0.20, mode="reseau")))
    r["CB1C_moy34c13d"] = ("C aiguillage v2 + c13d", "aiguillage_v2", _v2(petits=["v3", "v4", "c13d"], **CB1_CHOIX)[2])
    r["CB13C_moy34c13d_trous"] = ("C aiguillage v2 + c13d + trous", "aiguillage_v2",
                                  dict(_v2(petits=["v3", "v4", "c13d"], **CB1_CHOIX)[2], trous=dict(bas=0.20, mode="reseau")))
    return r


LISTES = dict(ref=liste_ref, cb1a=liste_cb1a, cb1b=liste_cb1b, cb1c=liste_cb1c, cb1d=liste_cb1d, cb3a=liste_cb3a,
              cb3b=liste_cb3b, cb3c=liste_cb3c, cb1e=liste_cb1e, plateau=liste_plateau, cb1f=liste_cb1f)
