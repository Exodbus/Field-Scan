# -*- coding: utf-8 -*-
"""E-008 — Vote des axes linéaires (B′) : carte de preuve des centres et complémentarité avec A′ (convergence-engineer).

Règles écrites avant le calcul : docs/recherche/notes/convergence-engineer.md § 1.2 à 1.7.
Images : bv_session_a (rôle dev_reglage, sans pépinière) pour la sélection ; dev_transfert rapporté au seuil figé.
bv_b_train, bv_b_val, groupes test ou exclus : exclus par assertion, jamais lus.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/convergence-engineer/e008_votes.py
"""
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

from comptage_math import feuille as F  # noqa: E402
from comptage_math import votes as VT  # noqa: E402
import math_evaluer as me  # noqa: E402

SORTIE = ICI / "E-008"
DET = SORTIE / "detections"
R_MAX = [1.0, 1.3, 1.6]
P_COH = [1.0, 2.0]
R_NMS = [0.8, 1.0, 1.2]
W_FUSION = [0.0, 0.25, 0.5, 1.0, 2.0]
Z_MIN = 0.5
GRAINE = 20261108
B = 2000


# ---------------------------------------------------------------------------------------------------------------
def maxima(S, valide, rayon_px):
    r = max(1, int(round(rayon_px)))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disque = ((xx ** 2 + yy ** 2) <= r * r).astype(np.uint8)
    mx = cv2.dilate(S.astype(np.float32), disque, borderType=cv2.BORDER_REPLICATE)
    pic = (S.astype(np.float32) >= mx) & valide & (S > 0)
    lab, n = ndimage.label(pic)
    if n == 0:
        return np.zeros((0, 2))
    c = np.array(ndimage.center_of_mass(pic, lab, range(1, n + 1)))
    return np.c_[c[:, 1] + 0.5, c[:, 0] + 0.5]


def echantillon(Z, pts):
    if not len(pts):
        return np.zeros(0)
    H, W = Z.shape
    x = np.clip(pts[:, 0].astype(int), 0, W - 1)
    y = np.clip(pts[:, 1].astype(int), 0, H - 1)
    return Z[y, x]


def detecter(Z, valide, rayon_px):
    pts = maxima(Z, valide, rayon_px)
    z = echantillon(Z, pts)
    return pts[z >= Z_MIN], z[z >= Z_MIN]


def lire(chemin):
    return np.asarray(Image.open(chemin).convert("RGB"), dtype=np.float32)


def passe1(arg):
    """Grille du vote, contrôle mélangé, z aux points de contrôle."""
    nom, chemin, cm, points, graine = arg
    cv2.setNumThreads(1)
    rgb = lire(chemin)
    valide = rgb.sum(2) > 15
    res = cm / 100.0
    out = dict(dets={}, dets_mel={}, z={}, t=None)
    if valide.sum() < 100:
        return out
    t0 = time.perf_counter()
    z, m = VT.champ(rgb, res)
    t_champ = time.perf_counter() - t0
    m &= valide
    for rm in R_MAX:
        for p in P_COH:
            t1 = time.perf_counter()
            Zv = VT.carte_votes(z, m, res, rm, p, valide=valide)["z"]
            if rm == 1.3 and p == 1.0:
                out["t"] = t_champ + time.perf_counter() - t1
            Zm = VT.carte_votes(z, m, res, rm, p, valide=valide, melanger=np.random.default_rng(graine))["z"]
            out["z"][(rm, p)] = {k: echantillon(Zv, v) for k, v in points.items()}
            out["z"][(rm, p, "mel")] = {k: echantillon(Zm, v) for k, v in points.items()}
            for rn in R_NMS:
                out["dets"][(rm, p, rn)] = detecter(Zv, valide, rn / res)
                out["dets_mel"][(rm, p, rn)] = detecter(Zm, valide, rn / res)
    return out


def carte_A(rgb, valide, res):
    """z_A figé d'E-006 : luminance, échelle 1,25 (comme cycle1_grille.travail)."""
    img = rgb / 255.0
    v = img.mean(-1).astype(np.float32)
    v[~valide] = np.median(v[valide])
    p = F.ParamsA(canal="luminance", echelle=1.25, res_travail=res)
    th = 2 * math.pi * np.arange(p.n_theta) / p.n_theta
    R = np.stack([F._correler(v, F.gabarit_A(t, p, res)) for t in th])
    return VT.zrob(F.score_etoile(R, p.m_top), valide)


def passe2(arg):
    """z_A, z_vote retenu, fusion z_A + w z_vote."""
    nom, chemin, cm, points, cfg = arg
    cv2.setNumThreads(1)
    rgb = lire(chemin)
    valide = rgb.sum(2) > 15
    res = cm / 100.0
    out = dict(dets={}, z={})
    if valide.sum() < 100:
        return out
    ZA = carte_A(rgb, valide, res)
    Zv = VT.carte_votes_image(rgb, res, cfg[0], cfg[1])["z"]
    out["z"]["A"] = {k: echantillon(ZA, v) for k, v in points.items()}
    out["z"]["V"] = {k: echantillon(Zv, v) for k, v in points.items()}
    for w in W_FUSION:
        out["dets"][w] = detecter(ZA + w * Zv, valide, 1.0 / res)
    return out


# ---------------------------------------------------------------------------------------------------------------
def ecrire_csv(chemin, dets):
    lignes = [dict(image_path=im, x=round(float(x), 2), y=round(float(y), 2), score=round(float(z), 5))
              for im, (xy, z) in dets.items() for (x, y), z in zip(xy, z)]
    pd.DataFrame(lignes, columns=["image_path", "x", "y", "score"]).to_csv(chemin, index=False)


def lancer_evaluateur(det_csv, nom, roles, dossier, seuil_fixe):
    cmd = [sys.executable, "-I", "-u", str(RACINE / "scripts/math_evaluer.py"), "--detections", str(det_csv),
           "--nom", nom, "--roles", *roles, "--out", str(dossier), "--seuil-fixe", repr(float(seuil_fixe))]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run(cmd, cwd=RACINE, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    return json.loads((Path(dossier) / f"resume_{nom}.json").read_text(encoding="utf-8"))


def f1(c):
    return 2 * c[0] / max(1.0, 2 * c[0] + c[1] + c[2])


def auc(pos, neg):
    pos, neg = np.asarray(pos), np.asarray(neg)
    if not len(pos) or not len(neg):
        return None
    r = pd.Series(np.r_[pos, neg]).rank().to_numpy()
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def spearman(a, b):
    return float(np.corrcoef(pd.Series(a).rank(), pd.Series(b).rank())[0, 1])


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t_debut = time.time()
    DET.mkdir(parents=True, exist_ok=True)
    L = me.charger_liste()
    interdits = set(pd.read_csv(me.DECOUPAGE_VAL).image_path)
    Ld = L[((L.role == "dev_reglage") & (L.groupe == "bv_session_a")) | (L.role == "dev_transfert")].reset_index(drop=True)
    assert not (set(Ld.image_path) & interdits), "image de bv_b_val dans la liste"
    assert not (Ld.groupe == "bv_b_train").any(), "bv_b_train est réservé"
    assert not Ld.groupe.isin(me.INTERDITS | {"bv_b_val"}).any()
    assert not Ld.image_path.str.contains("cg/").any()
    refs = me.references(Ld)
    cm = dict(zip(Ld.image_path, Ld.cm_par_px))
    ims = Ld.image_path.tolist()
    sel = Ld[Ld.groupe == "bv_session_a"].image_path.tolist()
    sel_set = set(sel)
    # points de contrôle (pixels) : mères, milieux de voisins mutuels < 3,5 m, nuls de l'évaluateur
    Lall = me.charger_liste()
    nul_veg = me.lire_detections(me.EVAL / "niveaux_nuls/vegetation_uniforme.csv", Lall)
    nul_dm = me.lire_detections(me.EVAL / "niveaux_nuls/demi_maille.csv", Lall)
    points = {}
    for i in ims:
        rxy, ty = refs[i]
        c = rxy[ty == "mere"]
        mil = []
        if len(c) >= 2:
            dd, j = cKDTree(c).query(c, k=2)
            for a in range(len(c)):
                b = j[a, 1]
                if a < b and j[b, 1] == a and dd[a, 1] * cm[i] / 100 < 3.5:
                    mil.append((c[a] + c[b]) / 2)
        points[i] = dict(meres=c, milieux=np.array(mil).reshape(-1, 2),
                         veg=nul_veg.get(i, (np.zeros((0, 2)),))[0], dm=nul_dm.get(i, (np.zeros((0, 2)),))[0])
    print(f"{len(ims)} images ({Ld.groupe.value_counts().to_dict()})", flush=True)

    # ---------------- passe 1 : grille du vote
    args = [(i, me.DONNEES / "images" / i, cm[i], points[i], GRAINE + n) for n, i in enumerate(ims)]
    with ProcessPoolExecutor(8) as ex:
        R1 = list(ex.map(passe1, args, chunksize=4))
    t1 = time.time() - t_debut
    print(f"passe 1 : {t1:.0f} s", flush=True)

    def seuil_et_f1(dets, images=sel):
        sc = np.concatenate([dets[i][1] for i in images if i in dets] or [np.zeros(1)])
        g = np.unique(np.quantile(sc, np.linspace(0, 0.995, 200)))
        c = me.comptes(images, dets, refs, cm, g).sum(0)
        P, Rr, Fv = me.prf(c)[:3]
        k = int(np.argmax(Fv))
        return float(g[k]), float(Fv[k]), float(P[k]), float(Rr[k]), k in (0, len(g) - 1)

    def en_region(dd):
        """Filtre les détections par région comptée (comme lire_detections)."""
        reg = Ld.set_index("image_path")
        return {i: (xy[me.dans_region(xy, reg.loc[i])], z[me.dans_region(xy, reg.loc[i])]) for i, (xy, z) in dd.items()}

    grille = []
    dets_cfg = {}
    for rm in R_MAX:
        for p in P_COH:
            for rn in R_NMS:
                k = (rm, p, rn)
                d = en_region({i: r["dets"][k] for i, r in zip(ims, R1) if k in r["dets"]})
                dets_cfg[k] = d
                s_, f_, p_, r_, bord = seuil_et_f1(d)
                grille.append(dict(r_max=rm, p=p, r_nms=rn, seuil_z=s_, f1=round(f_, 4), precision=round(p_, 4),
                                   rappel=round(r_, 4), seuil_au_bord=bord))
                print(grille[-1], flush=True)
    G = pd.DataFrame(grille)
    G.to_csv(SORTIE / "grille_bv_session_a.csv", index=False)
    ex_ = G[G.f1 >= G.f1.max() - 0.005].copy()
    ex_["o1"], ex_["o2"], ex_["o3"] = (ex_.r_max - 1.3).abs(), (ex_.p - 1).abs(), (ex_.r_nms - 1.0).abs()
    ch = ex_.sort_values(["o1", "o2", "o3"]).iloc[0]
    kV = (float(ch.r_max), float(ch.p), float(ch.r_nms))
    seuilV = float(ch.seuil_z)
    bilan = dict(identifiant="E-008", choix_vote=dict(r_max=kV[0], p=kV[1], r_nms=kV[2], seuil_z=seuilV, f1=float(ch.f1),
                                                      precision=float(ch.precision), rappel=float(ch.rappel)),
                 grille_f1_max=float(G.f1.max()), grille_f1_min=float(G.f1.min()))
    ecrire_csv(DET / "vote.csv", dets_cfg[kV])

    # ---------------- contrôles (bv_session_a)
    regs = Ld[Ld.groupe == "bv_session_a"]
    u = regs.unite.to_numpy()
    idx = me.tirages(len(np.unique(u)), B, 2026)

    def c_img(dets, s):
        return me.comptes(sel, dets, refs, cm, [s])[:, 0, :]

    cV = c_img(dets_cfg[kV], seuilV)
    dmel = en_region({i: r["dets_mel"][kV] for i, r in zip(ims, R1) if kV in r["dets_mel"]})
    cMel_fige = c_img(dmel, seuilV)
    s_mel, f_mel, *_ = seuil_et_f1(dmel)
    cMel = c_img(dmel, s_mel)
    cVeg = c_img(nul_veg, -np.inf)
    cDM = c_img(nul_dm, -np.inf)
    aV, aMel, aVeg, aDM = (me.par_unite(c, u) for c in (cV, cMel, cVeg, cDM))
    f_null = {"vegetation_uniforme": f1(cVeg.sum(0)), "melange_meilleur_seuil": f1(cMel.sum(0))}
    nul_max = max(f_null, key=f_null.get)
    aN = aVeg if nul_max == "vegetation_uniforme" else aMel
    dboot = np.array([f1(aV[k].sum(0)) - f1(aN[k].sum(0)) for k in idx])
    ctrl = dict(f1_vote=round(f1(cV.sum(0)), 4), ic95_f1_vote=np.percentile([f1(aV[k].sum(0)) for k in idx], [2.5, 97.5]).round(4).tolist(),
                f1_melange_seuil_fige=round(f1(cMel_fige.sum(0)), 4), f1_melange_meilleur_seuil=round(f_mel, 4),
                f1_vegetation_uniforme=round(f1(cVeg.sum(0)), 4), f1_demi_maille=round(f1(cDM.sum(0)), 4),
                nul_le_plus_fort=nul_max, ecart_vs_nul=round(f1(cV.sum(0)) - f_null[nul_max], 4),
                ic95_ecart=np.percentile(dboot, [2.5, 97.5]).round(4).tolist(),
                meilleur_que_hasard=bool(np.percentile(dboot, 2.5) > 0),
                double_comptage=me.double_comptage(sel, dets_cfg[kV], refs, cm, seuilV))
    # scores aux points (vote retenu, sans dépendre de R_nms)
    kz = kV[:2]
    zs = {t: np.concatenate([R1[n]["z"][kz][t] for n, i in enumerate(ims) if i in sel_set and kz in R1[n]["z"]])
          for t in ("meres", "milieux", "veg", "dm")}
    zsm = {t: np.concatenate([R1[n]["z"][kz + ("mel",)][t] for n, i in enumerate(ims) if i in sel_set and kz in R1[n]["z"]])
           for t in ("meres", "veg")}
    ctrl["scores"] = dict(mediane_meres=round(float(np.median(zs["meres"])), 3), p75_milieux=round(float(np.percentile(zs["milieux"], 75)), 3),
                          mediane_milieux=round(float(np.median(zs["milieux"])), 3),
                          OBJ_C3_passe=bool(np.median(zs["meres"]) > np.percentile(zs["milieux"], 75)),
                          auc_meres_vs_veg=round(auc(zs["meres"], zs["veg"]), 4), auc_meres_vs_demi_maille=round(auc(zs["meres"], zs["dm"]), 4),
                          auc_meres_vs_milieux=round(auc(zs["meres"], zs["milieux"]), 4),
                          auc_melange_meres_vs_veg=round(auc(zsm["meres"], zsm["veg"]), 4))
    # même chose pour vols_100_022x (rapport, comme OBJ-C3 d'E-006)
    vols = set(Ld[Ld.groupe == "vols_100_022x"].image_path)
    zc = np.concatenate([R1[n]["z"][kz]["meres"] for n, i in enumerate(ims) if i in vols and kz in R1[n]["z"]])
    zm = np.concatenate([R1[n]["z"][kz]["milieux"] for n, i in enumerate(ims) if i in vols and kz in R1[n]["z"]])
    ctrl["scores_vols_100_022x"] = dict(mediane_meres=round(float(np.median(zc)), 3), p75_milieux=round(float(np.percentile(zm, 75)), 3),
                                        OBJ_C3_passe=bool(np.median(zc) > np.percentile(zm, 75)))
    bilan["controles_bv_session_a"] = ctrl
    print(json.dumps(ctrl, ensure_ascii=False), flush=True)
    # temps
    t_ha = [r["t"] / ((512 * cm[i] / 100) ** 2 / 1e4) for i, r in zip(ims, R1) if r["t"]]
    bilan["temps_vote_s_par_ha_un_coeur_mediane"] = round(float(np.median(t_ha)), 3)
    bilan["temps_vote_s_par_ha_8_coeurs"] = round(float(np.median(t_ha)) / 8, 3)
    bilan["note_temps"] = "champ T_feuille + masque + une carte de votes (r_max 1,3, p 1), un cœur, hors lecture"

    # ---------------- passe 2 : A′ et fusion
    args2 = [(i, me.DONNEES / "images" / i, cm[i], points[i], kV[:2]) for i in ims]
    with ProcessPoolExecutor(8) as ex:
        R2 = list(ex.map(passe2, args2, chunksize=4))
    print(f"passe 2 : {time.time() - t_debut:.0f} s", flush=True)
    zA = {t: np.concatenate([R2[n]["z"]["A"][t] for n, i in enumerate(ims) if i in sel_set and "A" in R2[n]["z"]]) for t in ("meres", "veg")}
    zV = {t: np.concatenate([R2[n]["z"]["V"][t] for n, i in enumerate(ims) if i in sel_set and "V" in R2[n]["z"]]) for t in ("meres", "veg")}
    comp = dict(pearson_meres=round(float(np.corrcoef(zA["meres"], zV["meres"])[0, 1]), 4),
                spearman_meres=round(spearman(zA["meres"], zV["meres"]), 4),
                pearson_veg=round(float(np.corrcoef(zA["veg"], zV["veg"])[0, 1]), 4),
                spearman_veg=round(spearman(zA["veg"], zV["veg"]), 4), n_meres=int(len(zA["meres"])),
                auc_A_meres_vs_veg=round(auc(zA["meres"], zA["veg"]), 4))
    fus = []
    dets_w = {}
    for w in W_FUSION:
        d = en_region({i: r["dets"][w] for i, r in zip(ims, R2) if w in r["dets"]})
        dets_w[w] = d
        s_, f_, p_, r_, bord = seuil_et_f1(d)
        fus.append(dict(w=w, seuil_z=s_, f1=round(f_, 4), precision=round(p_, 4), rappel=round(r_, 4), seuil_au_bord=bord))
        print(fus[-1], flush=True)
    Fz = pd.DataFrame(fus)
    Fz.to_csv(SORTIE / "fusion_bv_session_a.csv", index=False)
    w_star = float(Fz[Fz.f1 >= Fz.f1.max() - 0.005].sort_values("w").iloc[0].w)
    s_star = float(Fz.set_index("w").loc[w_star, "seuil_z"])
    s_0 = float(Fz.set_index("w").loc[0.0, "seuil_z"])
    a_w = me.par_unite(c_img(dets_w[w_star], s_star), u)
    a_0 = me.par_unite(c_img(dets_w[0.0], s_0), u)
    dd = np.array([f1(a_w[k].sum(0)) - f1(a_0[k].sum(0)) for k in idx])
    comp.update(w_star=w_star, seuil_w_star=s_star, f1_w_star=round(f1(a_w.sum(0)), 4), f1_w0_A_prime=round(f1(a_0.sum(0)), 4),
                ic95_gain=np.percentile(dd, [2.5, 97.5]).round(4).tolist(),
                complementaire=bool(comp["spearman_meres"] < 0.5 and np.percentile(dd, 2.5) > 0))
    for w in W_FUSION:
        ecrire_csv(DET / f"fusion_w{w}.csv", dets_w[w])
    bilan["complementarite"] = comp
    print(json.dumps(comp, ensure_ascii=False), flush=True)

    # ---------------- dev_transfert, au seuil figé, par l'évaluateur
    garde = ("precision", "rappel", "f1", "ic95_f1", "detections", "meres", "par_groupe", "double_comptage")
    tr = {}
    for nom, csv, s in [("vote", DET / "vote.csv", seuilV), ("fusion_w0", DET / "fusion_w0.0.csv", s_0),
                        (f"fusion_w{w_star}", DET / f"fusion_w{w_star}.csv", s_star)]:
        r = lancer_evaluateur(csv, nom, ["dev_transfert"], SORTIE / "transfert", s)
        tr[nom] = {k: r["roles"]["dev_transfert"].get(k) for k in garde}
    bilan["dev_transfert"] = tr
    bilan["empreinte_script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    bilan["empreinte_votes_sha256"] = hashlib.sha256((RACINE / "comptage_math/votes.py").read_bytes()).hexdigest()
    bilan["empreinte_orientation_sha256"] = hashlib.sha256((RACINE / "comptage_math/orientation.py").read_bytes()).hexdigest()
    bilan["duree_totale_s"] = round(time.time() - t_debut, 1)
    (SORTIE / "bilan_E-008.json").write_text(json.dumps(bilan, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(bilan, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
