# -*- coding: utf-8 -*-
"""E-010 — Cycle 3 : extension du vote B′ (r_max, échelles σ_t), règle de rotation, attributs des candidats.

Règles écrites avant le calcul : docs/recherche/notes/convergence-engineer.md § 3.
bv_session_a (dev_reglage, sans pépinière) pour la sélection ; dev_transfert rapporté au seuil figé ;
bv_b_train, bv_b_val, groupes test ou exclus : exclus par assertion.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/convergence-engineer/e010_extension.py
"""
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
sys.path.insert(0, str(ICI))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

from comptage_math import votes as VT  # noqa: E402
import math_evaluer as me  # noqa: E402
import evaluer_comptage as ec  # noqa: E402
import e008_votes as E8  # noqa: E402  (maxima, échantillons, évaluateur : fonctions reprises sans changement)

SORTIE = ICI / "E-010"
DET = SORTIE / "detections"
R_MAX = [1.6, 2.0, 2.4]
ECHELLES = {"simple": (0.10,), "multi": (0.06, 0.10, 0.15)}
R_NMS = 1.0
P_COH = 1.0
B = 2000


def passe1(arg):
    nom, chemin, cm, points = arg
    cv2.setNumThreads(1)
    rgb = E8.lire(chemin)
    valide = rgb.sum(2) > 15
    res = cm / 100.0
    out = dict(dets={}, z={}, t={})
    if valide.sum() < 100:
        return out
    t0 = time.perf_counter()
    champs = {}
    for st in ECHELLES["multi"]:
        z, m = VT.champ(rgb, res, st)
        champs[st] = (z, m & valide)
    t_champ = (time.perf_counter() - t0) / 3
    for rm in R_MAX:
        zan = {}
        for st, (z, m) in champs.items():
            t1 = time.perf_counter()
            zan[st] = VT.carte_votes(z, m, res, rm, P_COH, valide=valide)["z_an"]
            if rm == 2.0:
                out["t"][st] = t_champ + time.perf_counter() - t1
        for e, sts in ECHELLES.items():
            Z = VT.zrob(sum(zan[s] for s in sts), valide)
            out["dets"][(rm, e)] = E8.detecter(Z, valide, R_NMS / res)
            out["z"][(rm, e)] = {k: E8.echantillon(Z, v) for k, v in points.items()}
    return out


def passe2(arg):
    """Configuration retenue : détections sur l'image d'origine (avec attributs) et sur l'image tournée de 90°."""
    nom, chemin, cm, cfg, tourner = arg
    cv2.setNumThreads(1)
    rgb = E8.lire(chemin)
    if tourner:
        assert rgb.shape[0] == rgb.shape[1]
        rgb = np.ascontiguousarray(np.rot90(rgb))
    res = cm / 100.0
    if (rgb.sum(2) > 15).sum() < 100:
        return None
    r = VT.carte_votes_multi(rgb, res, cfg[0], P_COH, ECHELLES[cfg[1]])
    pts, sc = E8.detecter(r["z"], r["valide"], R_NMS / res)
    att = None if tourner else VT.attributs_candidats(r["champ"], r["masque"], res, pts, cfg[0])
    return pts, sc, att


def budget(ims, dets, refs, cm, n_ref):
    tous = np.sort(np.concatenate([dets[i][1] for i in ims if i in dets] or [np.zeros(0)]))[::-1]
    s_k = tous[n_ref - 1] if 0 < n_ref <= len(tous) else (tous[-1] if len(tous) else np.inf)
    return me.comptes(ims, dets, refs, cm, [s_k])[:, 0, :], float(s_k)


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
    reg = Ld.set_index("image_path")
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
        points[i] = dict(meres=c, milieux=np.array(mil).reshape(-1, 2))

    def en_region(dd):
        return {i: (xy[me.dans_region(xy, reg.loc[i])], z[me.dans_region(xy, reg.loc[i])]) for i, (xy, z) in dd.items()}

    def seuil_et_f1(dets, images=sel):
        sc = np.concatenate([dets[i][1] for i in images if i in dets] or [np.zeros(1)])
        g = np.unique(np.quantile(sc, np.linspace(0, 0.995, 200)))
        c = me.comptes(images, dets, refs, cm, g).sum(0)
        P, Rr, Fv = me.prf(c)[:3]
        k = int(np.argmax(Fv))
        return float(g[k]), float(Fv[k]), float(P[k]), float(Rr[k]), k in (0, len(g) - 1)

    # ---------------- passe 1 : grille
    with ProcessPoolExecutor(8) as ex:
        R1 = list(ex.map(passe1, [(i, me.DONNEES / "images" / i, cm[i], points[i]) for i in ims], chunksize=4))
    print(f"passe 1 : {time.time() - t_debut:.0f} s", flush=True)
    grille, dets_cfg = [], {}
    for rm in R_MAX:
        for e in ECHELLES:
            k = (rm, e)
            d = en_region({i: r["dets"][k] for i, r in zip(ims, R1) if k in r["dets"]})
            dets_cfg[k] = d
            s_, f_, p_, r_, bord = seuil_et_f1(d)
            grille.append(dict(r_max=rm, echelles=e, seuil_z=s_, f1=round(f_, 4), precision=round(p_, 4), rappel=round(r_, 4),
                               seuil_au_bord=bord))
            print(grille[-1], flush=True)
    G = pd.DataFrame(grille)
    G.to_csv(SORTIE / "grille_bv_session_a.csv", index=False)
    ex_ = G[G.f1 >= G.f1.max() - 0.005].copy()
    ex_["o1"], ex_["o2"] = (ex_.echelles != "simple").astype(int), (ex_.r_max - 1.6).abs()
    ch = ex_.sort_values(["o1", "o2"]).iloc[0]
    kV = (float(ch.r_max), str(ch.echelles))
    seuilV = float(ch.seuil_z)
    bilan = dict(identifiant="E-010", choix=dict(r_max=kV[0], echelles=kV[1], sigmas_t_m=list(ECHELLES[kV[1]]), p=P_COH, r_nms=R_NMS,
                                                 seuil_z=seuilV, f1=float(ch.f1), precision=float(ch.precision), rappel=float(ch.rappel)),
                 grille_f1_max=float(G.f1.max()))
    gain = {rm: round(float(G[(G.r_max == rm) & (G.echelles == "multi")].f1.iloc[0] - G[(G.r_max == rm) & (G.echelles == "simple")].f1.iloc[0]), 4)
            for rm in R_MAX}
    bilan["gain_multi_moins_simple"] = gain
    th = [{st: v / ((512 * cm[i] / 100) ** 2 / 1e4) for st, v in r["t"].items()} for i, r in zip(ims, R1) if r["t"]]
    t_simple = float(np.median([t[0.10] for t in th]))
    t_multi = float(np.median([sum(t.values()) for t in th]))
    bilan["temps_s_par_ha_8_coeurs"] = dict(simple=round(t_simple / 8, 3), multi=round(t_multi / 8, 3),
                                            note="champ + une carte de votes (r_max 2,0) par échelle, un cœur ÷ 8, hors lecture et maxima")

    # ---------------- passe 2 : configuration retenue, origine (toutes images) et rotation (bv_session_a)
    args = [(i, me.DONNEES / "images" / i, cm[i], kV, False) for i in ims] + \
           [(i, me.DONNEES / "images" / i, cm[i], kV, True) for i in sel]
    with ProcessPoolExecutor(8) as ex:
        R2 = list(ex.map(passe2, args, chunksize=4))
    print(f"passe 2 : {time.time() - t_debut:.0f} s", flush=True)
    orig = {i: r for i, r in zip(ims, R2[:len(ims)]) if r is not None}
    rot = {i: r for i, r in zip(sel, R2[len(ims):]) if r is not None}
    # contrôle : la passe 2 redonne les détections de la passe 1
    n1 = sum(len(dets_cfg[kV][i][0]) for i in sel if i in dets_cfg[kV])
    d_orig = en_region({i: (r[0], r[1]) for i, r in orig.items()})
    n2 = sum(len(d_orig[i][0]) for i in sel if i in d_orig)
    bilan["controle_passe2_identique"] = dict(n_passe1=n1, n_passe2=n2)
    E8.ecrire_csv(DET / "vote_e010.csv", {i: (r[0], r[1]) for i, r in orig.items()})
    E8.ecrire_csv(SORTIE / "rotation_vote_e010.csv", {i: (r[0], r[1]) for i, r in rot.items()})
    # attributs (tous candidats z ≥ 0,5, repère pixel de la tuile)
    lignes = []
    for i, (pts, sc, att) in orig.items():
        for (x, y), s, a in zip(pts, sc, att):
            lignes.append(dict(image_path=i, x=round(float(x), 2), y=round(float(y), 2), score=round(float(s), 5), **a))
    A = pd.DataFrame(lignes)
    A.to_csv(DET / "vote_e010_attributs.csv", index=False)

    # ---------------- règle de rotation (test_final.md § 4.3)
    Ls = Ld[Ld.groupe == "bv_session_a"]
    u = Ls.unite.to_numpy()
    n_ref = int(sum((refs[i][1] == "mere").sum() for i in sel))
    detO = me.lire_detections(DET / "vote_e010.csv", L)
    detR = me.lire_detections(SORTIE / "rotation_vote_e010.csv", L)
    detVeg = me.lire_detections(me.EVAL / "niveaux_nuls/vegetation_uniforme.csv", L)
    c_o, s_o = budget(sel, detO, refs, cm, n_ref)
    c_r, s_r = budget(sel, detR, refs, cm, n_ref)
    c_v = me.comptes(sel, detVeg, refs, cm, [-1.0])[:, 0, :]
    fo, fr, fv = (E8.f1(c.sum(0)) for c in (c_o, c_r, c_v))
    idx = me.tirages(len(np.unique(u)), B, 2026)
    aR, aV = me.par_unite(c_r, u), me.par_unite(c_v, u)
    d = me.f1_tirages(aR, idx) - me.f1_tirages(aV, idx)
    fr_seuil = float(me.prf(me.comptes(sel, detR, refs, cm, [seuilV]).sum(0))[2][0])
    c1, c2 = (fr - fv) <= 0.05, (fr - fv) <= 0.25 * (fo - fv)
    bilan["regle_rotation"] = dict(n_ref=n_ref, f1_orig_budget=round(fo, 4), f1_rot_budget=round(fr, 4), f1_veg=round(fv, 4),
                                   exces_rot=round(fr - fv, 4), exces_orig=round(fo - fv, 4), condition_1=bool(c1), condition_2=bool(c2),
                                   passe=bool(c1 and c2),
                                   rapporte_sans_decider=dict(ic95_f1rot_moins_f1veg=np.percentile(d, [2.5, 97.5]).round(4).tolist(),
                                                              f1_rot_au_seuil=round(fr_seuil, 4)),
                                   interpretation="détections de l'image tournée lues dans le repère pixel de la tuile, sans rotation inverse")
    # ---------------- double comptage, OBJ-C3, F1 au seuil
    c_s = me.comptes(sel, detO, refs, cm, [seuilV])[:, 0, :]
    aS = me.par_unite(c_s, u)
    autres = dict(f1_seuil=round(E8.f1(c_s.sum(0)), 4),
                  ic95_f1=np.percentile([E8.f1(aS[k].sum(0)) for k in idx], [2.5, 97.5]).round(4).tolist(),
                  double_comptage=me.double_comptage(sel, detO, refs, cm, seuilV))
    for g in ["bv_session_a", "vols_100_022x"]:
        ig = set(Ld[Ld.groupe == g].image_path)
        zc = np.concatenate([R1[n]["z"][kV]["meres"] for n, i in enumerate(ims) if i in ig and kV in R1[n]["z"]])
        zm = np.concatenate([R1[n]["z"][kV]["milieux"] for n, i in enumerate(ims) if i in ig and kV in R1[n]["z"]])
        autres[f"OBJ_C3_{g}"] = dict(mediane_meres=round(float(np.median(zc)), 3), p75_milieux=round(float(np.percentile(zm, 75)), 3),
                                     auc_meres_vs_milieux=round(E8.auc(zc, zm), 4), passe=bool(np.median(zc) > np.percentile(zm, 75)))
    bilan["bv_session_a"] = autres
    # ---------------- attributs : vrais et faux positifs au seuil, bv_session_a (rapport seulement)
    rows = []
    for i in sel:
        if i not in detO:
            continue
        xy, sc = detO[i]
        k = sc >= seuilV
        xy = xy[k]
        rxy, ty = refs[i]
        cert = np.isin(ty, list(ec.TYPES_CERTAINS))
        paires = ec.apparier(xy * cm[i] / 100, rxy[cert] * cm[i] / 100, 1.0)
        vp = {a for a, _, _ in paires}
        Ai = A[A.image_path == i].set_index(["x", "y"])
        for n, (x, y) in enumerate(xy):
            try:
                a = Ai.loc[(round(float(x), 2), round(float(y), 2))]
            except KeyError:
                continue
            a = a.iloc[0] if isinstance(a, pd.DataFrame) else a
            rows.append(dict(vp=n in vp, **{c: a[c] for c in ("n_soutien", "fraction_soutien", "couverture", "rayon")}))
    T = pd.DataFrame(rows)
    att = {}
    for lab, g in T.groupby("vp"):
        att["vrais_positifs" if lab else "faux_positifs"] = dict(
            n=int(len(g)), **{f"mediane_{c}": round(float(g[c].median()), 3) for c in ("n_soutien", "fraction_soutien", "couverture", "rayon")},
            **{f"q25_q75_{c}": g[c].quantile([0.25, 0.75]).round(3).tolist() for c in ("fraction_soutien", "couverture", "rayon")})
    att["auc_vp_vs_fp"] = {c: round(E8.auc(T[T.vp][c].dropna(), T[~T.vp][c].dropna()), 4)
                           for c in ("n_soutien", "fraction_soutien", "couverture", "rayon")}
    bilan["attributs_bv_session_a"] = att
    print(json.dumps({k: bilan[k] for k in ("choix", "gain_multi_moins_simple", "regle_rotation", "bv_session_a", "attributs_bv_session_a")},
                     ensure_ascii=False, default=str), flush=True)
    # ---------------- dev_transfert au seuil figé
    r = E8.lancer_evaluateur(DET / "vote_e010.csv", "vote_e010", ["dev_transfert"], SORTIE / "transfert", seuilV)
    bilan["dev_transfert"] = {k: r["roles"]["dev_transfert"].get(k)
                              for k in ("precision", "rappel", "f1", "ic95_f1", "detections", "meres", "par_groupe", "double_comptage")}
    bilan["empreinte_script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    bilan["empreinte_votes_sha256"] = hashlib.sha256((RACINE / "comptage_math/votes.py").read_bytes()).hexdigest()
    bilan["empreinte_orientation_sha256"] = hashlib.sha256((RACINE / "comptage_math/orientation.py").read_bytes()).hexdigest()
    bilan["duree_totale_s"] = round(time.time() - t_debut, 1)
    (SORTIE / "bilan_E-010.json").write_text(json.dumps(bilan, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(bilan, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
