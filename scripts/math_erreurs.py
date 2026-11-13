#!/usr/bin/env python3
"""E-011 — Analyse descriptive des erreurs du vote des axes linéaires B′ (E-008), mères seules (error-analyst).

Rédacteur : error-analyst. Analyse descriptive : aucune méthode nouvelle n'est réglée ici.
Règles de classement écrites AVANT le calcul : constante REGLES ci-dessous et
docs/recherche/notes/error-analyst.md § 1 (7 novembre 2026).

Données (développement seulement) :
- bv_session_a sans pépinière (rôle dev_reglage, groupe bv_session_a) : analyse principale et planches ;
- dev_transfert (corte, lasuiza, vols_100_022x) : complément, tableaux seulement.
Interdits par assertion : bv_b_train, bv_b_val, val_*, groupes exclus ou de test, cg/.

Entrées :
- vote E-008 : out/comptage_math/convergence-engineer/E-008/detections/vote.csv (tous les candidats après NMS 1 m,
  score z), seuil z figé lu dans bilan_E-008.json ;
- v5 : out/comptage_math/evaluation/v5/detections_val_iter_dev.csv, seuil figé 0,30 (E-001) ;
- références : data/drone/comptage_v5_5cm/objets.csv (via la liste images_dense.csv d'independent-evaluator) ;
- appariement : evaluer_comptage.apparier (importé par scripts/math_evaluer.py, non modifié), rayon 1 m.

Commande :
    .venv/Scripts/python.exe -I -u scripts/math_erreurs.py
Sorties : out/comptage_math/error-analyst/E-011/
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

import math_evaluer as me  # noqa: E402
from comptage_math import votes as V  # noqa: E402

ec = me.ec
IMAGES = me.DONNEES / "images"
E008 = RACINE / "out/comptage_math/convergence-engineer/E-008"
VOTE = E008 / "detections/vote.csv"
V5 = RACINE / "out/comptage_math/evaluation/v5/detections_val_iter_dev.csv"
SORTIE = RACINE / "out/comptage_math/error-analyst/E-011"
GRAINE = 2026

# --------------------------------------------------------------------------------------------------------------
# Règles écrites avant le calcul (7 novembre 2026). Toute modification est datée dans les notes.
# --------------------------------------------------------------------------------------------------------------
REGLES = dict(
    rayon_appariement_m=1.0,
    rayon_attributs_m=0.5,          # fenêtre carrée de demi-côté 0,5 m pour luminance, ExG, cohérence, végétation
    seuil_v5=0.30,                  # E-001
    # Oubliés : état du candidat (priorité dans cet ordre)
    bord_tuile_m=1.0,               # distance au bord de l'image ou à un pixel invalide
    fusion_rayon_m=1.0,             # détection retenue à < 1 m, appariée à une autre mère
    sous_seuil_rayon_m=1.0,         # candidat du vote sous le seuil à < 1 m
    # Oubliés : facteur image (priorité dans cet ordre), seuils = centiles des mères du même rôle
    petit_centile=20,               # taille de boîte < P20
    ombre_centile=20,               # luminance locale < P20
    jointives_centile=10,           # distance à la mère voisine < P10
    echelle_taille_m=3.2,           # couronne > 2 × r_max (1,6 m) : le noyau ne couvre pas la couronne
    coherence_centile=20,           # cohérence locale du tenseur < P20
    # Fausses détections (priorité dans cet ordre)
    region_m=1.0,                   # mère hors région comptée à < 1 m : artefact de l'évaluation
    milieu_m=0.5, milieu_dmax_m=3.5,  # à < 0,5 m du milieu de deux mères distantes de < 3,5 m
    doublon_m=2.0,                  # mère la plus proche à < 2 m et déjà appariée à une autre détection
    rejet_m=1.6,                    # point non « mere » à < 1,6 m
    refmanq_dmin_m=1.6, refmanq_v5_score=0.5, refmanq_veg=0.5,  # aucune mère à < 1,6 m, v5 ≥ 0,5 aussi FP à < 1 m, végétation
    sol_veg=0.3,                    # fraction de masque de végétation < 0,3
    feuille_min_m=1.0, feuille_max_m=2.0,  # mère non trouvée à 1–2 m : pic décalé sur une feuille
    # Maille locale (piste plant-geometry), à partir des seules détections retenues du vote (pas des références)
    maille_ext=(0.7, 1.3),          # paires à s·[0,7 ; 1,3] : nœud extrapolé b + (b − a) et a − (b − a)
    maille_mil=(1.6, 2.4),          # paires à s·[1,6 ; 2,4] : nœud au milieu
    maille_occupe=0.6,              # nœud déjà occupé si une détection retenue est à < 0,6 s
    maille_tol=0.3,                 # tolérance 0,3 s
    maille_support=2,               # au moins 2 prédictions concordantes
)
INTERDITS = {"bv_b_train", "bv_b_val"} | set(me.INTERDITS)


def apparie(det_m, ref_m, cert):
    """Même logique qu'evaluer_points : retourne (det→ref certaine, détections ignorées)."""
    idx_c = np.flatnonzero(cert)
    paires = ec.apparier(det_m, ref_m[cert], REGLES["rayon_appariement_m"]) if len(det_m) and len(idx_c) else []
    d2r = {i: int(idx_c[j]) for i, j, _ in paires}
    rest = [i for i in range(len(det_m)) if i not in d2r]
    ign = set()
    if (~cert).any() and rest:
        for i, _, _ in ec.apparier(det_m[rest], ref_m[~cert], REGLES["rayon_appariement_m"]):
            ign.add(rest[i])
    return d2r, ign


def predictions_maille(R):
    """Nœuds prévus par la maille locale des détections retenues R (m). Retourne (P, s)."""
    if len(R) < 5:
        return np.zeros((0, 2)), np.nan
    t = cKDTree(R)
    s = float(np.median(t.query(R, k=2)[0][:, 1]))
    pr = t.query_pairs(REGLES["maille_mil"][1] * s, output_type="ndarray")
    if not len(pr):
        return np.zeros((0, 2)), s
    a, b = R[pr[:, 0]], R[pr[:, 1]]
    d = np.linalg.norm(b - a, axis=1)
    e = (d >= REGLES["maille_ext"][0] * s) & (d <= REGLES["maille_ext"][1] * s)
    m = (d >= REGLES["maille_mil"][0] * s) & (d <= REGLES["maille_mil"][1] * s)
    P = np.vstack([b[e] + (b[e] - a[e]), a[e] - (b[e] - a[e]), (a[m] + b[m]) / 2])
    if len(P):
        P = P[t.query(P)[0] >= REGLES["maille_occupe"] * s]
    return P, s


def support(P, X, s):
    if not len(P) or not len(X) or not np.isfinite(s):
        return np.zeros(len(X), int)
    return cKDTree(P).query_ball_point(X, REGLES["maille_tol"] * s, return_length=True).astype(int)


def traiter(t):
    im, reg, rxy, rty, rtaille, cxy, csc, vxy, vsc, seuil_z = t
    cm = float(reg["cm_par_px"])
    res = cm / 100
    rgb = np.asarray(Image.open(IMAGES / im).convert("RGB"), np.float32)
    H, W = rgb.shape[:2]
    valide = rgb.sum(2) > 15
    zc, msk = V.champ(rgb, res)
    msk &= valide
    somme = rgb.sum(2) + 1e-6
    exg = (2 * rgb[..., 1] - rgb[..., 0] - rgb[..., 2]) / somme
    lum = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) / 255
    k = 2 * int(round(REGLES["rayon_attributs_m"] / res)) + 1

    def f(a):
        return ndimage.uniform_filter(a.astype(np.float32), k, mode="nearest")
    LUM, EXG, COH, VEG = f(lum), f(exg), f(np.abs(zc)), f(msk)
    DB = ndimage.distance_transform_edt(np.pad(valide, 1))[1:-1, 1:-1] * res

    def ech(A, xy):
        if not len(xy):
            return np.zeros(0)
        j = np.clip(np.round(xy[:, 0]).astype(int), 0, W - 1)
        i = np.clip(np.round(xy[:, 1]).astype(int), 0, H - 1)
        return A[i, j]

    class R_:  # région comptée
        pass
    r = R_()
    for c in ("zx0", "zx1", "zy0", "zy1", "disque_cx", "disque_cy", "disque_r"):
        setattr(r, c, float(reg[c]))
    rin = me.dans_region(rxy, r)
    din = me.dans_region(cxy, r)
    vin = me.dans_region(vxy, r)
    ret = csc >= seuil_z
    M = lambda a: a * res  # noqa: E731  pixels → m

    # références de la région
    Rp, Rt, Rs = rxy[rin], rty[rin], rtaille[rin]
    cert = Rt == "mere"
    Dp = cxy[ret & din]
    Dsc = csc[ret & din]
    d2r, ign = apparie(M(Dp), M(Rp), cert)
    trouve = set(d2r.values())
    # v5
    sel5 = vin & (vsc >= REGLES["seuil_v5"])
    V5p, V5s = vxy[sel5], vsc[sel5]
    d2r5, ign5 = apparie(M(V5p), M(Rp), cert)
    trouve5 = set(d2r5.values())
    fp5 = [i for i in range(len(V5p)) if i not in d2r5 and i not in ign5]

    # maille locale à partir de toutes les détections retenues de l'image (méthode seule, sans référence)
    P, s = predictions_maille(M(cxy[ret]))
    subm = (~ret) & din
    Sp, Ss = cxy[subm], csc[subm]
    sup_sub = support(P, M(Sp), s)
    # règle « nœud » sans réglage : candidats sous le seuil à un nœud, glouton par score, exclusion 0,6 s
    ajout = []
    if np.isfinite(s):
        occ = list(M(cxy[ret]))
        for i in np.argsort(-Ss):
            if sup_sub[i] >= REGLES["maille_support"]:
                x = M(Sp[i])
                if not occ or np.min(np.linalg.norm(np.asarray(occ) - x, axis=1)) >= REGLES["maille_occupe"] * s:
                    ajout.append(i)
                    occ.append(x)
    Dn = np.vstack([Dp, Sp[ajout]]) if ajout else Dp
    d2rn, ignn = apparie(M(Dn), M(Rp), cert)

    def cpt(n_det, d2r_, ign_):
        vp = len(d2r_)
        return [vp, n_det - vp - len(ign_), int(cert.sum()) - vp]
    comptes = dict(vote=cpt(len(Dp), d2r, ign), v5=cpt(len(V5p), d2r5, ign5), noeud=cpt(len(Dn), d2rn, ignn),
                   ajouts=len(ajout), ajouts_vp=sum(1 for i in range(len(Dp), len(Dn)) if i in d2rn))

    # arbres
    tc = cKDTree(M(cxy)) if len(cxy) else None
    tsub_all = cKDTree(M(cxy[~ret])) if (~ret).any() else None
    allm = M(rxy[rty == "mere"])
    tall = cKDTree(allm) if len(allm) else None
    hors = M(rxy[(~rin) & (rty == "mere")])
    nonm = M(rxy[rty != "mere"])
    ref_rows = []
    Rm = M(Rp)
    supr = support(P, Rm, s)
    for j in range(len(Rp)):
        if not cert[j]:
            continue
        x = Rm[j]
        row = dict(image_path=im, x=Rp[j, 0], y=Rp[j, 1], statut="VP" if j in trouve else "FN",
                   taille_m=Rs[j] * res, cm_par_px=cm, lum=float(ech(LUM, Rp[j:j + 1])[0]),
                   exg=float(ech(EXG, Rp[j:j + 1])[0]), coh=float(ech(COH, Rp[j:j + 1])[0]),
                   veg=float(ech(VEG, Rp[j:j + 1])[0]), d_bord_m=float(ech(DB, Rp[j:j + 1])[0]),
                   v5_trouve=j in trouve5, support_noeud_ref=int(supr[j]), maille_s_m=s)
        if tall is not None and len(allm) > 1:
            dd, _ = tall.query(x, k=2)
            row["d_nn_mere_m"] = float(dd[1])
        else:
            row["d_nn_mere_m"] = np.nan
        if tc is not None:
            d, i = tc.query(x)
            row["d_cand_proche_m"], row["z_cand_proche"] = float(d), float(csc[i])
        else:
            row["d_cand_proche_m"], row["z_cand_proche"] = np.nan, np.nan
        row["z_det_appariee"] = next((float(Dsc[i]) for i, jj in d2r.items() if jj == j), np.nan)
        if j not in trouve:
            # sous le seuil à < 1 m (tous les candidats de l'image)
            zs = np.nan
            if tsub_all is not None:
                ii = tsub_all.query_ball_point(x, REGLES["sous_seuil_rayon_m"])
                if ii:
                    zs = float(np.max(csc[~ret][ii]))
            row["sous_seuil_1m"] = bool(np.isfinite(zs))
            row["z_sous_seuil_max"] = zs
            # fusion : détection retenue à < 1 m appariée à une autre mère
            fus = [i for i, jj in d2r.items() if jj != j and np.linalg.norm(M(Dp[i]) - x) < REGLES["fusion_rayon_m"]]
            row["fusion"] = bool(fus)
            # candidat sous le seuil de la région, à < 1 m, sur un nœud prévu (support ≥ 2)
            near = np.linalg.norm(M(Sp) - x, axis=1) < REGLES["sous_seuil_rayon_m"] if len(Sp) else np.zeros(0, bool)
            row["noeud_candidat"] = bool((near & (sup_sub >= REGLES["maille_support"])).any())
            row["support_noeud_cand"] = int(sup_sub[near].max()) if near.any() else 0
            row["recupere_regle_noeud"] = j in set(d2rn.values())
        ref_rows.append(row)

    fp_rows = []
    for i in range(len(Dp)):
        if i in d2r or i in ign:
            continue
        x = M(Dp[i])
        row = dict(image_path=im, x=Dp[i, 0], y=Dp[i, 1], statut="FP", score=float(Dsc[i]), cm_par_px=cm,
                   lum=float(ech(LUM, Dp[i:i + 1])[0]), exg=float(ech(EXG, Dp[i:i + 1])[0]),
                   coh=float(ech(COH, Dp[i:i + 1])[0]), veg=float(ech(VEG, Dp[i:i + 1])[0]),
                   d_bord_m=float(ech(DB, Dp[i:i + 1])[0]), maille_s_m=s,
                   support_noeud=int(support(P, x[None], s)[0]))
        # mère la plus proche dans la région
        if cert.any():
            dd = np.linalg.norm(Rm[cert] - x, axis=1)
            jj = np.flatnonzero(cert)[int(np.argmin(dd))]
            row["d_mere_m"], row["mere_appariee"] = float(dd.min()), jj in trouve
        else:
            row["d_mere_m"], row["mere_appariee"] = np.inf, False
        row["d_mere_hors_region_m"] = float(np.min(np.linalg.norm(hors - x, axis=1))) if len(hors) else np.inf
        row["d_non_mere_m"] = float(np.min(np.linalg.norm(nonm - x, axis=1))) if len(nonm) else np.inf
        # milieu de deux mères
        mil = False
        if len(allm) >= 2:
            tt = cKDTree(allm)
            pr = tt.query_pairs(REGLES["milieu_dmax_m"], output_type="ndarray")
            if len(pr):
                mid = (allm[pr[:, 0]] + allm[pr[:, 1]]) / 2
                mil = bool((np.linalg.norm(mid - x, axis=1) < REGLES["milieu_m"]).any())
        row["milieu"] = mil
        # v5 à < 1 m
        if len(V5p):
            dv = np.linalg.norm(M(V5p) - x, axis=1)
            k5 = int(np.argmin(dv))
            row["v5_proche"] = bool(dv[k5] < 1.0)
            row["v5_score"] = float(V5s[k5]) if dv[k5] < 1.0 else np.nan
            row["v5_proche_fp"] = bool(dv[k5] < 1.0 and k5 in fp5)
        else:
            row["v5_proche"], row["v5_score"], row["v5_proche_fp"] = False, np.nan, False
        fp_rows.append(row)

    # FP du v5 évités par le vote
    v5fp_partage = 0
    for k5 in fp5:
        x = M(V5p[k5])
        fpv = [M(Dp[i]) for i in range(len(Dp)) if i not in d2r and i not in ign]
        if fpv and np.min(np.linalg.norm(np.asarray(fpv) - x, axis=1)) < 1.0:
            v5fp_partage += 1
    comptes["v5_fp"] = len(fp5)
    comptes["v5_fp_aussi_vote"] = v5fp_partage

    dessin = dict(cm=cm, refs=rxy, rty=rty, rin=rin, trouve=[j for j in range(len(Rp))],
                  Rp=Rp, Rstat=np.array(["VP" if j in trouve else ("FN" if cert[j] else "inc") for j in range(len(Rp))]),
                  Dp=Dp, Dstat=np.array(["VP" if i in d2r else ("ign" if i in ign else "FP") for i in range(len(Dp))]),
                  Sp=cxy[~ret], V5p=V5p)
    return im, ref_rows, fp_rows, comptes, dessin


# --------------------------------------------------------------------------------------------------------------
def classer_fn(F, A):
    """F : oubliés ; A : toutes les mères du même rôle (seuils en centiles)."""
    q = dict(petit=np.percentile(A.taille_m, REGLES["petit_centile"]),
             ombre=np.percentile(A.lum, REGLES["ombre_centile"]),
             jointives=np.nanpercentile(A.d_nn_mere_m, REGLES["jointives_centile"]),
             coherence=np.percentile(A.coh, REGLES["coherence_centile"]))
    etat = np.where(F.d_bord_m < REGLES["bord_tuile_m"], "bord de tuile",
           np.where(F.fusion, "couronnes jointives (fusion)",
           np.where(F.sous_seuil_1m, "candidat sous le seuil", "aucun candidat")))
    fac = np.where(F.taille_m < q["petit"], "petit plant",
          np.where(F.lum < q["ombre"], "ombre",
          np.where(F.d_nn_mere_m < q["jointives"], "couronnes jointives (voisine proche)",
          np.where(F.taille_m >= REGLES["echelle_taille_m"], "échelle (couronne > 2 r_max)",
          np.where(F.coh < q["coherence"], "cohérence faible", "sans facteur")))))
    return etat, fac, {k: round(float(v), 4) for k, v in q.items()}


def classer_fp(P):
    c = np.full(len(P), "indéterminé", object)
    regles = [
        ("bord de région (artefact d'évaluation)", P.d_mere_hors_region_m < REGLES["region_m"]),
        ("milieu de deux mères", P.milieu),
        ("doublon d'un plant apparié", (P.d_mere_m < REGLES["doublon_m"]) & P.mere_appariee),
        ("rejet compté", P.d_non_mere_m < REGLES["rejet_m"]),
        ("référence manquante probable", (P.d_mere_m >= REGLES["refmanq_dmin_m"]) & P.v5_proche_fp
         & (P.v5_score >= REGLES["refmanq_v5_score"]) & (P.veg >= REGLES["refmanq_veg"])),
        ("sol ou débris", P.veg < REGLES["sol_veg"]),
        ("feuille isolée (pic décalé d'une mère oubliée)", (P.d_mere_m >= REGLES["feuille_min_m"])
         & (P.d_mere_m < REGLES["feuille_max_m"]) & ~P.mere_appariee),
        ("autre végétal", P.d_mere_m >= REGLES["feuille_max_m"]),
    ]
    for nom, m in reversed(regles):
        c[np.asarray(m, bool)] = nom
    return c


MODULE_FN = {"bord de tuile": "tuiles (bord du noyau de vote)",
             "couronnes jointives (fusion)": "séparation des couronnes denses / nettoyage (R_nms 1 m)",
             "candidat sous le seuil": "seuil (et score du vote)",
             "aucun candidat": "orientation / vote (pas de pic)"}
MODULE_FAC = {"petit plant": "vote (échelle du noyau r_min, r_max)", "ombre": "orientation (luminance) / couleur",
              "couronnes jointives (voisine proche)": "séparation des couronnes denses",
              "échelle (couronne > 2 r_max)": "vote (r_max)", "cohérence faible": "orientation",
              "sans facteur": "indéterminé"}
MODULE_FP = {"bord de région (artefact d'évaluation)": "évaluation (independent-evaluator)",
             "milieu de deux mères": "vote / séparation des couronnes denses",
             "doublon d'un plant apparié": "nettoyage", "rejet compté": "nettoyage (rejets)",
             "référence manquante probable": "annotation-manager (signalement)",
             "sol ou débris": "couleur (masque de végétation)",
             "feuille isolée (pic décalé d'une mère oubliée)": "vote (localisation du pic)",
             "autre végétal": "vote / seuil / couleur", "indéterminé": "indéterminé"}


def tableau(serie, total=None):
    vc = serie.value_counts()
    total = total or len(serie)
    return {k: dict(n=int(v), part=round(v / total, 4)) for k, v in vc.items()}


def prf(c):
    vp, fp, fn = c
    p = vp / (vp + fp) if vp + fp else 0
    r = vp / (vp + fn) if vp + fn else 0
    return dict(vp=int(vp), fp=int(fp), fn=int(fn), precision=round(p, 4), rappel=round(r, 4),
                f1=round(2 * p * r / (p + r), 4) if p + r else 0)


def planche(df, titre, fichier, dessins, graine=GRAINE, n=24):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    if not len(df):
        return 0
    ech = df.sample(min(n, len(df)), random_state=graine)
    fig, axes = plt.subplots(4, 6, figsize=(19, 13.5))
    for ax in axes.flat:
        ax.axis("off")
    for ax, r in zip(axes.flat, ech.itertuples()):
        d = dessins[r.image_path]
        res = d["cm"] / 100
        h = 3.5 / res
        ax.imshow(Image.open(IMAGES / r.image_path).convert("RGB"))
        ax.set_xlim(r.x - h, r.x + h)
        ax.set_ylim(r.y + h, r.y - h)
        hors = d["refs"][(~d["rin"]) & (d["rty"] == "mere")]
        ax.scatter(hors[:, 0], hors[:, 1], s=90, facecolors="none", edgecolors="lightgray", lw=1)
        for st, col in (("VP", "deepskyblue"), ("FN", "yellow")):
            q = d["Rp"][d["Rstat"] == st]
            ax.scatter(q[:, 0], q[:, 1], s=110, facecolors="none", edgecolors=col, lw=1.8)
        ax.scatter(d["Sp"][:, 0], d["Sp"][:, 1], s=10, c="white", alpha=0.8)
        for st, col, mk in (("VP", "blue", "o"), ("FP", "red", "x")):
            q = d["Dp"][d["Dstat"] == st]
            ax.scatter(q[:, 0], q[:, 1], s=30, c=col, marker=mk, lw=2)
        ax.scatter(d["V5p"][:, 0], d["V5p"][:, 1], s=60, c="magenta", marker="+", lw=1.5)
        ax.add_patch(Circle((r.x, r.y), 1.0 / res, fill=False, ec="white", ls="--", lw=1))
        if r.statut == "FN":
            t = f"z sous-seuil={r.z_sous_seuil_max:.2f}" if r.sous_seuil_1m else f"z proche={r.z_cand_proche:.2f}"
            t += f" | {r.taille_m:.1f} m | v5 {'oui' if r.v5_trouve else 'non'}"
        else:
            t = f"z={r.score:.2f} | mère {r.d_mere_m:.1f} m | v5 {'oui' if r.v5_proche else 'non'}"
        ax.set_title(f"{r.image_path.replace('.jpg', '')}\n{t}", fontsize=7.5)
    fig.suptitle(f"E-011 — {titre} ({len(ech)} sur {len(df)}, graine {graine})\n"
                 "cercles : mère trouvée (bleu clair), oubliée (jaune), hors région (gris) ; vote retenu : VP (point bleu),"
                 " FP (croix rouge) ; candidats sous le seuil : points blancs ; v5 ≥ 0,30 : + magenta ;"
                 " tirets : 1 m autour de l'erreur", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(fichier, dpi=80)
    plt.close(fig)
    return len(ech)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    bilan = json.loads((E008 / "bilan_E-008.json").read_text(encoding="utf-8"))
    seuil_z = float(bilan["choix_vote"]["seuil_z"])
    L = me.charger_liste()
    jeux = {"bv_session_a": L[(L.role == "dev_reglage") & (L.groupe == "bv_session_a")],
            "dev_transfert": L[L.role == "dev_transfert"]}
    for nom, Lr in jeux.items():
        assert not (set(Lr.groupe) & INTERDITS), nom
        assert not any(str(x).startswith("val") for x in Lr.role), nom
        assert not any("cg/" in p for p in Lr.image_path)
    ims = set().union(*[set(x.image_path) for x in jeux.values()])
    O = pd.read_csv(me.DONNEES / "objets.csv")
    O = O[O.image_path.isin(ims)]
    D = pd.read_csv(VOTE)
    D = D[D.image_path.isin(ims)]
    W5 = pd.read_csv(V5)
    W5 = W5[W5.image_path.isin(ims)]   # le fichier contient bv_b_train : filtré immédiatement, jamais lu au-delà
    for df in (O, D, W5):
        assert not df.image_path.str.contains("bv_b_train|bv_b_val").any()
    go, gd, gv = (dict(tuple(x.groupby("image_path"))) for x in (O, D, W5))
    vide = np.zeros((0, 2))
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / "planches").mkdir(exist_ok=True)
    resultat = dict(identifiant="E-011", nature="analyse descriptive", seuil_z_vote=seuil_z, regles=REGLES)
    dessins_bv = {}
    for nom, Lr in jeux.items():
        taches = []
        for reg in Lr.to_dict("records"):
            im = reg["image_path"]
            o, d, v = go.get(im), gd.get(im), gv.get(im)
            taches.append((im, reg,
                           o[["cx", "cy"]].to_numpy(float) if o is not None else vide,
                           o["type"].to_numpy() if o is not None else np.zeros(0, object),
                           o["taille"].to_numpy(float) if o is not None else np.zeros(0),
                           d[["x", "y"]].to_numpy(float) if d is not None else vide,
                           d["score"].to_numpy(float) if d is not None else np.zeros(0),
                           v[["x", "y"]].to_numpy(float) if v is not None else vide,
                           v["score"].to_numpy(float) if v is not None else np.zeros(0), seuil_z))
        with ProcessPoolExecutor(8) as ex:
            out = list(ex.map(traiter, taches, chunksize=4))
        A = pd.DataFrame([r for o_ in out for r in o_[1]])
        P = pd.DataFrame([r for o_ in out for r in o_[2]])
        A["groupe"] = A.image_path.map(dict(zip(Lr.image_path, Lr.groupe)))
        P["groupe"] = P.image_path.map(dict(zip(Lr.image_path, Lr.groupe)))
        C = {k: np.sum([o_[3][k] for o_ in out], axis=0) for k in ("vote", "v5", "noeud", "ajouts", "ajouts_vp",
                                                                     "v5_fp", "v5_fp_aussi_vote")}
        F = A[A.statut == "FN"].copy()
        etat, fac, q = classer_fn(F, A)
        F["etat"], F["facteur"] = etat, fac
        F["module_etat"] = F.etat.map(MODULE_FN)
        F["module_facteur"] = F.facteur.map(MODULE_FAC)
        P["classe"] = classer_fp(P)
        P["module"] = P.classe.map(MODULE_FP)
        F.to_csv(SORTIE / f"oublies_{nom}.csv", index=False)
        P.to_csv(SORTIE / f"fausses_detections_{nom}.csv", index=False)
        A.to_csv(SORTIE / f"meres_{nom}.csv", index=False)
        nfn = len(F)
        R = dict(images=len(Lr), meres=len(A),
                 controle_vote=prf(C["vote"]), controle_v5=prf(C["v5"]),
                 seuils_centiles=q,
                 oublies=dict(n=nfn, etat=tableau(F.etat), facteur=tableau(F.facteur),
                              croise=pd.crosstab(F.etat, F.facteur).to_dict()),
                 fausses_detections=dict(n=len(P), classe=tableau(P.classe),
                                         part_indeterminee=round(float((P.classe == "indéterminé").mean()), 4)),
                 modules_oublis=tableau(F.module_etat), modules_fp=tableau(P.module))
        # comparaison avec le v5
        R["v5_croise_meres"] = {f"vote_{a}_v5_{b}": int(((A.statut == ("VP" if a == "oui" else "FN"))
                                                         & (A.v5_trouve == (b == "oui"))).sum())
                                for a in ("oui", "non") for b in ("oui", "non")}
        R["oublies_vote_trouves_v5"] = dict(n=int(F.v5_trouve.sum()), etat=tableau(F[F.v5_trouve].etat),
                                            facteur=tableau(F[F.v5_trouve].facteur))
        R["oublies_vote_et_v5"] = dict(n=int((~F.v5_trouve).sum()), etat=tableau(F[~F.v5_trouve].etat))
        R["fp_vote"] = dict(avec_fp_v5_a_1m=int(P.v5_proche_fp.sum()), sans_detection_v5_a_1m=int((~P.v5_proche).sum()),
                            classe_sans_v5=tableau(P[~P.v5_proche].classe))
        R["fp_v5"] = dict(n=int(C["v5_fp"]), aussi_fp_vote_a_1m=int(C["v5_fp_aussi_vote"]))
        # attributs médians
        cols = ["taille_m", "lum", "exg", "coh", "veg", "d_nn_mere_m", "d_bord_m"]
        R["medianes_meres"] = {s: {c: round(float(A[A.statut == s][c].median()), 4) for c in cols} for s in ("VP", "FN")}
        R["medianes_fp"] = {c: round(float(P[c].median()), 4) for c in ["score", "lum", "exg", "coh", "veg",
                                                                        "d_mere_m", "d_bord_m"]}
        # chiffre clé : récupérables à un nœud de maille
        R["chiffre_cle"] = dict(
            fn=nfn,
            sous_seuil_1m=int(F.sous_seuil_1m.sum()), part_sous_seuil_1m=round(float(F.sous_seuil_1m.mean()), 4),
            noeud_candidat=int(F.noeud_candidat.sum()), part_noeud_candidat=round(float(F.noeud_candidat.mean()), 4),
            ref_a_un_noeud=int((F.support_noeud_ref >= REGLES["maille_support"]).sum()),
            recuperes_regle_noeud=int(F.recupere_regle_noeud.sum()),
            regle_noeud=dict(ajouts=int(C["ajouts"]), ajouts_vp=int(C["ajouts_vp"]), **prf(C["noeud"])),
            note="borne haute descriptive, paramètres de maille fixés avant, aucun réglage ; pas une méthode adoptée")
        if nom == "dev_transfert":
            R["par_groupe"] = {g: dict(oublies=tableau(F[F.groupe == g].etat),
                                       fp=tableau(P[P.groupe == g].classe),
                                       noeud_candidat=round(float(F[F.groupe == g].noeud_candidat.mean()), 4))
                               for g in sorted(F.groupe.unique())}
        resultat[nom] = R
        print(nom, json.dumps(R, ensure_ascii=False, default=str)[:6000], flush=True)
        if nom == "bv_session_a":
            dessins_bv = {o_[0]: o_[4] for o_ in out}
            Fb, Pb, Ab = F, P, A
    # planches (bv_session_a seulement)
    pl = {}
    d = SORTIE / "planches"
    for e in Fb.etat.unique():
        pl[f"FN_etat_{e}"] = planche(Fb[Fb.etat == e], f"oubliés — {e}", d / f"fn_etat_{slug(e)}.png", dessins_bv)
    for fa in Fb.facteur.unique():
        sous = Fb[(Fb.facteur == fa) & Fb.etat.isin(["candidat sous le seuil", "aucun candidat"])]
        pl[f"FN_facteur_{fa}"] = planche(sous, f"oubliés (sous le seuil ou sans candidat) — {fa}",
                                         d / f"fn_facteur_{slug(fa)}.png", dessins_bv)
    for c in Pb.classe.unique():
        pl[f"FP_{c}"] = planche(Pb[Pb.classe == c], f"fausses détections — {c}", d / f"fp_{slug(c)}.png", dessins_bv)
    pl["FN_vote_trouve_v5"] = planche(Fb[Fb.v5_trouve], "oubliés du vote que le v5 trouve",
                                      d / "fn_vote_trouves_v5.png", dessins_bv)
    pl["FN_noeud_candidat"] = planche(Fb[Fb.noeud_candidat], "oubliés avec candidat sous le seuil sur un nœud prévu",
                                      d / "fn_noeud_candidat.png", dessins_bv)
    vpv = Ab[(Ab.statut == "VP") & ~Ab.v5_trouve].assign(sous_seuil_1m=False, z_cand_proche=Ab.z_det_appariee,
                                                         statut="FN")
    pl["VP_vote_oublie_v5"] = planche(vpv, "mères trouvées par le vote et oubliées par le v5 (z = détection appariée)",
                                      d / "vp_vote_oubliees_v5.png", dessins_bv)
    resultat["planches"] = pl
    (SORTIE / "bilan_E-011.json").write_text(json.dumps(resultat, ensure_ascii=False, indent=1, default=str),
                                             encoding="utf-8")
    print("planches", pl)


def slug(s):
    import re
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:40]


if __name__ == "__main__":
    main()
