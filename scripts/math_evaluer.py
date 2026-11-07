#!/usr/bin/env python3
"""Évaluation unique des méthodes de comptage en plantation dense (mères seules), équipe de recherche mathématique.

Rédacteur : independent-evaluator. Règles écrites avant toute mesure : docs/recherche/test_final.md (section 2)
et docs/recherche/notes/independent-evaluator.md (interface, E-001).

Interface
---------
1. Liste des images : `--liste` écrit out/comptage_math/evaluation/images_dense.csv (une ligne par image préparée de
   data/drone/comptage_v5_5cm/images/) avec groupe, rôle (dev, annexe_segmento, val_iter, controle_repro), résolution
   réelle `cm_par_px`, région comptée (disque_cx/cy/r, zx0/zx1/zy0/zy1 en pixels) et unité de bootstrap.
   Le rôle val_scellee n'est jamais écrit dans ce fichier.
2. Détections : CSV `image_path,x,y,score`, x et y en pixels de l'image préparée (origine en haut à gauche),
   score croissant avec la confiance. Image absente = aucune détection. Hors région = ignoré.
3. Évaluation : appariement un à un à distance totale minimale, paires à moins de 1 m (apparier() de
   scripts/evaluer_comptage.py, importé sans modification), en mètres (pixels × cm_par_px / 100) ; mères seules
   (un point non « mere » est incertain : une détection appariée à lui est ignorée).
   Seuil : figé (--seuil-fixe) ou choisi sur le développement (meilleur F1 cumulé) puis appliqué tel quel ailleurs.
   Sorties : P, R, F1, erreur de comptage, courbe rappel-budget, bootstrap par unité, différence appariée avec
   une référence (--comparer), borne basse unilatérale corrigée (--m-comparaisons).

Exemples :
    python scripts/math_evaluer.py --liste
    python scripts/math_evaluer.py --auto-test
    python scripts/math_evaluer.py --niveaux-nuls --roles dev_reglage dev_transfert val_iter
    python scripts/math_evaluer.py --detections out/comptage_math/evaluation/v5/detections.csv --nom v5 \\
        --seuil-fixe 0.30 --roles dev_reglage dev_transfert val_iter --out out/comptage_math/evaluation/E-001/v5
"""
import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import evaluer_comptage as ec  # noqa: E402  (apparier, scores, definir_types_certains : lecture seule)

DONNEES = RACINE / "data/drone/comptage_v5_5cm"
DECOUPAGE = RACINE / "data/drone/decoupage_comptage_v5/decoupage.csv"
EVAL = RACINE / "out/comptage_math/evaluation"
LISTE = EVAL / "images_dense.csv"
DECOUPAGE_VAL = EVAL / "decoupage_bv_b_val.csv"
RAYON_M = 1.0
TUILE, PAS = 512, int(512 * 0.8)                 # comme scripts/preparer_comptage_v3.py (tuiles à 20 % de recouvrement)
GROUPES_DEV = ["bv_session_a", "bv_b_train", "lasuiza", "vols_100_022x", "corte"]
GROUPES_REGLAGE = ["bv_session_a", "bv_b_train"]   # test_final.md, amendement 1 (3.1)
DEV_GARDE = RACINE / "data/comptage_math/references/dev_dense_images.csv"   # annotation-manager : sans pépinière
GROUPES_ANNEXE = ["segmento_ouest"]
GROUPES_CONTROLE = ["jeunes_dji_0544", "pp_100_metros"]
INTERDITS = {"banano", "btd", "segmento_est", "bv_b_tampon", "cocotier_1300_plus", "palmier_44000_4000"}
SOURCES_V5 = ["plants_bana", "count_banana_plants", "multiple_tree", "plantas_platano", "platano_lasuiza",
              "banana_tree_detection", "banavista", "banano_dense"]
GRAINE = 2026
ec.definir_types_certains(meres_seules=True)


# ----------------------------------------------------------------------------------------------------------------
# Liste des images et régions comptées
# ----------------------------------------------------------------------------------------------------------------
def source_echelle(groupe):
    """Copie de preparer_comptage_v3.source_echelle (groupes qui partagent une échelle et une numérotation k)."""
    if groupe.startswith("segmento"):
        return "segmento"
    if groupe in ("vols_100_022x", "corte"):
        return "count_100_022x_corte"
    if groupe.startswith("cocotier"):
        return "cocotiers"
    return groupe


def positions(n):
    return sorted(set(list(range(0, max(n - TUILE, 0) + 1, PAS)) + [max(n - TUILE, 0)]))


def zone_propre(P, i, etendue):
    """Intervalle [lo, hi) de la tuile i (axe de positions P) où un point est plus proche de son centre que des voisins."""
    lo = 0.0 if i == 0 else (P[i - 1] + TUILE + P[i]) / 2 - P[i]
    hi = float(min(TUILE, etendue - P[i])) if i == len(P) - 1 else (P[i] + TUILE + P[i + 1]) / 2 - P[i]
    return lo, hi


def construire_liste(avec_scellee=False):
    T = pd.read_csv(DONNEES / "tuiles.csv")
    par = json.loads((DONNEES / "parametres.json").read_text(encoding="utf-8"))["facteurs"]
    dec = pd.read_csv(DECOUPAGE)
    dec = dec[dec.partie.isin(["train", "val", "test"]) & dec.source.isin(SOURCES_V5)
              & ~dec.groupe.str.startswith("jeunes_dji", na=False)]
    groupes = GROUPES_DEV + GROUPES_ANNEXE + GROUPES_CONTROLE + ["bv_b_val"]
    assert not INTERDITS & set(groupes)
    # numéro k de chaque image d'origine dans son groupe d'échelle (ordre alphabétique, comme la préparation)
    k_vers_ligne = {}
    for se, g in dec.groupby(dec.groupe.map(source_echelle)):
        for k, (_, r) in enumerate(g.sort_values("image").iterrows()):
            k_vers_ligne[(se, k)] = r
    val = pd.read_csv(DECOUPAGE_VAL).set_index("image_path")
    garde = pd.read_csv(DEV_GARDE).set_index("image_path")
    photo_lasuiza = {}                            # doublons de lasuiza : première copie (plus petit k) gardée
    for im in sorted(garde[garde.groupe == "lasuiza"].index):     # clé : image d'origine k (toutes ses tuiles)
        photo_lasuiza.setdefault(garde.loc[im, "photo"], im.rsplit("_", 1)[0])
    lignes, anomalies = [], 0
    for _, t in T[T.groupe.isin(groupes)].iterrows():
        se = source_echelle(t.groupe)
        f_nom = par[se]["facteur"] if se in par else par[t.groupe]["facteur"]
        cm = 5.0 * f_nom / t.facteur
        d = dict(image_path=t.image_path, groupe=t.groupe, cm_par_px=round(cm, 4), largeur=t.largeur, hauteur=t.hauteur,
                 disque_cx=t.masque_cx, disque_cy=t.masque_cy, disque_r=t.masque_r,
                 zx0=0.0, zx1=float(t.largeur), zy0=0.0, zy1=float(t.hauteur))
        if t.groupe in GROUPES_DEV + GROUPES_ANNEXE:
            if t.groupe in GROUPES_DEV:
                if t.image_path not in garde.index:
                    d["role"] = "dev_exclu"           # pépinière ou bordure (règle v2 d'annotation-manager)
                elif t.groupe == "lasuiza" and photo_lasuiza[garde.loc[t.image_path, "photo"]] != t.image_path.rsplit("_", 1)[0]:
                    d["role"] = "dev_exclu"           # doublon de lasuiza
                else:
                    d["role"] = "dev_reglage" if t.groupe in GROUPES_REGLAGE else "dev_transfert"
            else:
                d["role"] = "annexe_segmento"
            morceaux = Path(t.image_path).stem.split("_")
            k, j = int(morceaux[-2]), int(morceaux[-1])
            r = k_vers_ligne[(se, k)]
            assert r.groupe == t.groupe, (t.image_path, r.groupe)
            W, H = round(r.largeur * t.facteur), round(r.hauteur * t.facteur)
            d["unite"] = garde.loc[t.image_path, "photo"] if t.image_path in garde.index else f"{t.groupe}_{k:04d}"
            if t.source != "banavista" and W <= TUILE and H <= TUILE:
                d.update(zx1=float(W), zy1=float(H))
            else:
                px, py = positions(W), positions(H)
                n_tuiles = int((T.image_path.str.startswith(f"{'bv_' if t.source == 'banavista' else ''}{t.groupe}_{k:04d}_")).sum())
                if n_tuiles != len(px) * len(py):
                    anomalies += 1               # grille non reconstruite : tuile entière comptée
                else:
                    iy, ix = divmod(j, len(px))
                    d["zx0"], d["zx1"] = zone_propre(px, ix, W)
                    d["zy0"], d["zy1"] = zone_propre(py, iy, H)
        elif t.groupe in GROUPES_CONTROLE:
            d.update(role="controle_repro", unite=t.image_path)
        else:                                    # bv_b_val
            v = val.loc[t.image_path]
            if v.role == "val_scellee" and not avec_scellee:
                continue
            d.update(role=v.role, unite=v.bloc, photo=v.photo)
        lignes.append(d)
    L = pd.DataFrame(lignes)
    return L, anomalies


def charger_liste(avec_scellee=False):
    if avec_scellee:
        return construire_liste(True)[0]
    if not LISTE.exists():
        raise SystemExit("Lancer d'abord : math_evaluer.py --liste")
    return pd.read_csv(LISTE)


def dans_region(xy, r):
    if not len(xy):
        return np.zeros(0, bool)
    ok = (xy[:, 0] >= r.zx0) & (xy[:, 0] < r.zx1) & (xy[:, 1] >= r.zy0) & (xy[:, 1] < r.zy1)
    if not np.isnan(r.disque_r):
        ok &= (xy[:, 0] - r.disque_cx) ** 2 + (xy[:, 1] - r.disque_cy) ** 2 <= r.disque_r ** 2
    return ok


def references(L):
    O = pd.read_csv(DONNEES / "objets.csv")
    O = O[O.image_path.isin(set(L.image_path))]
    par_img = {k: g for k, g in O.groupby("image_path")}
    refs = {}
    for r in L.itertuples():
        o = par_img.get(r.image_path)
        xy = o[["cx", "cy"]].to_numpy(float) if o is not None else np.zeros((0, 2))
        ty = o["type"].to_numpy() if o is not None else np.zeros(0, object)
        m = dans_region(xy, r)
        refs[r.image_path] = (xy[m], ty[m])
    return refs


# ----------------------------------------------------------------------------------------------------------------
# Appariement (règle d'evaluer_comptage.evaluer_zone, en tableaux)
# ----------------------------------------------------------------------------------------------------------------
def evaluer_points(det_m, ref_m, types, rayon=RAYON_M):
    """(vp, fp, fn, detections comptées, mères) : même logique qu'evaluer_zone (incertains ignorés)."""
    cert = np.isin(types, list(ec.TYPES_CERTAINS))
    certains, incertains = ref_m[cert], ref_m[~cert]
    paires = ec.apparier(det_m, certains, rayon)
    pris = {i for i, _, _ in paires}
    restantes = [i for i in range(len(det_m)) if i not in pris]
    ign = len(ec.apparier(det_m[restantes], incertains, rayon)) if len(incertains) and restantes else 0
    vp = len(paires)
    return vp, len(det_m) - vp - ign, len(certains) - vp, len(det_m) - ign, len(certains)


def _travail(lot):
    sortie = []
    for det_m, sc, ref_m, ty, seuils in lot:
        sortie.append([evaluer_points(det_m[sc >= s], ref_m, ty) for s in seuils])
    return sortie


def comptes(images, dets, refs, cm, seuils, paralleles=8):
    """Tableau (n_images, n_seuils, 5) : vp, fp, fn, détections, mères."""
    taches = []
    for im in images:
        xy, sc = dets.get(im, (np.zeros((0, 2)), np.zeros(0)))
        rxy, ty = refs[im]
        taches.append((xy * cm[im] / 100, sc, rxy * cm[im] / 100, ty, list(seuils)))
    if len(taches) * len(seuils) < 4000 or paralleles <= 1:
        res = _travail(taches)
    else:
        n = max(1, len(taches) // (paralleles * 4))
        lots = [taches[i:i + n] for i in range(0, len(taches), n)]
        with ProcessPoolExecutor(paralleles) as ex:
            res = [x for part in ex.map(_travail, lots) for x in part]
    return np.array(res, dtype=float).reshape(len(images), len(seuils), 5)


def prf(c):
    vp, fp, fn = c[..., 0], c[..., 1], c[..., 2]
    with np.errstate(invalid="ignore", divide="ignore"):
        p = np.where(vp + fp > 0, vp / (vp + fp), 0.0)
        r = np.where(vp + fn > 0, vp / (vp + fn), 0.0)
        f = np.where(p + r > 0, 2 * p * r / (p + r), 0.0)
    return p, r, f


def resume(c):
    """c : (5,) cumul."""
    p, r, f = prf(c)
    return dict(vp=int(c[0]), fp=int(c[1]), fn=int(c[2]), detections=int(c[3]), meres=int(c[4]),
                precision=round(float(p), 4), rappel=round(float(r), 4), f1=round(float(f), 4),
                erreur_comptage_relative=round(float((c[3] - c[4]) / c[4]), 4) if c[4] else None)


def lire_detections(chemin, L):
    D = pd.read_csv(chemin)
    manque = {"image_path", "x", "y", "score"} - set(D.columns)
    if manque:
        raise SystemExit(f"Colonnes manquantes dans {chemin} : {manque}")
    scel = set(pd.read_csv(DECOUPAGE_VAL).query("role == 'val_scellee'").image_path)
    connues = set(L.image_path)
    if (set(D.image_path) & scel) - connues:
        raise SystemExit("Refus : détections sur val_scellee sans --ouvrir-scellee (docs/recherche/test_final.md, 1.4).")
    reg = L.set_index("image_path")
    dets = {}
    for im, g in D[D.image_path.isin(connues)].groupby("image_path"):
        xy, sc = g[["x", "y"]].to_numpy(float), g["score"].to_numpy(float)
        m = dans_region(xy, reg.loc[im])
        dets[im] = (xy[m], sc[m])
    return dets


def double_comptage(images, dets, refs, cm, seuil, dmax=3.5, r_milieu=0.5, r_centre=0.5):
    """Part des paires de plus proches voisins mutuels (mères, < dmax m) ayant une détection à moins de r_milieu du
    milieu et à plus de r_centre des deux centres (test_final.md, 3.3 b)."""
    from scipy.spatial import cKDTree
    n_paires = n_doubles = 0
    for im in images:
        rxy, ty = refs[im]
        c = rxy[ty == "mere"] * cm[im] / 100
        if len(c) < 2:
            continue
        dd, j = cKDTree(c).query(c, k=2)
        xy, sc = dets.get(im, (np.zeros((0, 2)), np.zeros(0)))
        d = xy[sc >= seuil] * cm[im] / 100
        arbre = cKDTree(d) if len(d) else None
        for a in range(len(c)):
            b = j[a, 1]
            if a < b and j[b, 1] == a and dd[a, 1] < dmax:
                n_paires += 1
                if arbre is None:
                    continue
                m = (c[a] + c[b]) / 2
                for k in arbre.query_ball_point(m, r_milieu):
                    if np.linalg.norm(d[k] - c[a]) > r_centre and np.linalg.norm(d[k] - c[b]) > r_centre:
                        n_doubles += 1
                        break
    return dict(paires=n_paires, paires_doublees=n_doubles, taux=round(n_doubles / n_paires, 4) if n_paires else None)


# ----------------------------------------------------------------------------------------------------------------
# Bootstrap
# ----------------------------------------------------------------------------------------------------------------
def par_unite(c_img, unites):
    u = pd.Series(unites)
    codes, noms = pd.factorize(u)
    agg = np.zeros((len(noms), 5))
    np.add.at(agg, codes, c_img)
    return agg


def tirages(n_unites, B, graine=GRAINE):
    return np.random.default_rng(graine).integers(0, n_unites, size=(B, n_unites))


def f1_tirages(agg, idx):
    return prf(agg[idx].sum(1))[2]


# ----------------------------------------------------------------------------------------------------------------
# Évaluation d'un fichier de détections
# ----------------------------------------------------------------------------------------------------------------
def evaluer(args):
    roles = args.roles
    L = charger_liste(args.ouvrir_scellee is not None)
    if args.ouvrir_scellee is None and "val_scellee" in roles:
        raise SystemExit("Refus : val_scellee ne se mesure qu'une fois, avec --ouvrir-scellee E-NNN.")
    L = L[L.role.isin(roles + (["dev_reglage"] if "dev_reglage" not in roles and args.seuil_fixe is None else []))]
    cm = dict(zip(L.image_path, L.cm_par_px))
    refs = references(L)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    def charger(chemin, seuil_fixe, nom):
        dets = lire_detections(chemin, L)
        dev = L[L.role == "dev_reglage"].image_path.tolist()
        res = dict(nom=nom, detections=str(chemin))
        if seuil_fixe is not None:
            seuil = float(seuil_fixe)
            res["regle_seuil"] = "figé"
        else:
            sc_dev = np.concatenate([dets[i][1] for i in dev if i in dets]) if dev else np.zeros(0)
            if not len(sc_dev):
                raise SystemExit("Pas de détection sur le développement : seuil impossible à choisir (--seuil-fixe ?).")
            grille = np.unique(np.quantile(sc_dev, np.linspace(0, 0.995, 200)))
            c = comptes(dev, dets, refs, cm, grille).sum(0)
            f = prf(c)[2]
            b = int(np.argmax(f))
            seuil = float(grille[b])
            res["regle_seuil"] = "meilleur F1 cumulé sur dev_reglage (bv_session_a sans pépinière + bv_b_train)"
            pd.DataFrame(dict(seuil=grille, f1_dev=f, precision=prf(c)[0], rappel=prf(c)[1],
                              detections=c[:, 3])).to_csv(out / f"seuils_dev_{nom}.csv", index=False)
            if b in (0, len(grille) - 1):
                res["alerte"] = "seuil au bord de la grille"
        res["seuil"] = seuil
        return dets, res

    dets, R = charger(args.detections, args.seuil_fixe, args.nom)
    comp = None
    if args.comparer:
        dets_c, Rc = charger(args.comparer, args.seuil_comparer, args.nom_comparer)
    lignes_img, courbe = [], []
    R["roles"] = {}
    for role in roles:
        Lr = L[L.role == role]
        ims = Lr.image_path.tolist()
        c_img = comptes(ims, dets, refs, cm, [R["seuil"]])[:, 0, :]
        bloc = dict(images=len(ims), unites=int(Lr.unite.nunique()), **resume(c_img.sum(0)))
        # par groupe
        bloc["par_groupe"] = {g: resume(c_img[(Lr.groupe == g).to_numpy()].sum(0)) for g in sorted(Lr.groupe.unique())}
        # bootstrap par unité
        agg = par_unite(c_img, Lr.unite.to_numpy())
        B = 10000 if role.startswith("val") else 2000
        idx = tirages(len(agg), B)
        fb = f1_tirages(agg, idx)
        bloc["ic95_f1"] = [round(float(np.percentile(fb, 2.5)), 4), round(float(np.percentile(fb, 97.5)), 4)]
        bloc["bootstrap"] = f"{B} tirages, unité = {'bloc de 7 photos' if role.startswith('val') else 'photo ou tuile d origine' if role.startswith(('dev', 'annexe')) else 'image'}"
        bloc["double_comptage"] = double_comptage(ims, dets, refs, cm, R["seuil"])
        # courbe rappel-budget (classement global des scores dans la région)
        n_ref = c_img[:, 4].sum()
        tous = np.sort(np.concatenate([dets[i][1] for i in ims if i in dets] or [np.zeros(0)]))[::-1]
        for m in (0.5, 1.0, 1.5, 2.0, 3.0):
            k = int(round(m * n_ref))
            s_k = tous[k - 1] if 0 < k <= len(tous) else (tous[-1] if len(tous) else np.inf)
            ck = comptes(ims, dets, refs, cm, [s_k])[:, 0, :].sum(0)
            courbe.append(dict(nom=args.nom, role=role, multiple=m, budget=k, seuil=float(s_k),
                               budget_atteint=bool(k <= len(tous)), **resume(ck)))
        if args.comparer:
            c2 = comptes(ims, dets_c, refs, cm, [Rc["seuil"]])[:, 0, :]
            agg2 = par_unite(c2, Lr.unite.to_numpy())
            d = fb - f1_tirages(agg2, idx)
            alpha = 0.05 / args.m_comparaisons
            bloc["comparaison"] = dict(
                reference=Rc["nom"], seuil_reference=Rc["seuil"], reference_resume=resume(c2.sum(0)),
                difference_f1=round(float(prf(c_img.sum(0))[2] - prf(c2.sum(0))[2]), 4),
                m_comparaisons=args.m_comparaisons, alpha_unilateral=alpha,
                borne_basse_unilaterale=round(float(np.percentile(d, 100 * alpha)), 4),
                ic95_difference=[round(float(np.percentile(d, 2.5)), 4), round(float(np.percentile(d, 97.5)), 4)])
        R["roles"][role] = bloc
        for (im, g, u), cc in zip(Lr[["image_path", "groupe", "unite"]].itertuples(index=False), c_img):
            lignes_img.append(dict(nom=args.nom, role=role, image_path=im, groupe=g, unite=u,
                                   vp=int(cc[0]), fp=int(cc[1]), fn=int(cc[2]), detections=int(cc[3]), meres=int(cc[4])))
    pd.DataFrame(lignes_img).to_csv(out / f"par_image_{args.nom}.csv", index=False)
    pd.DataFrame(courbe).to_csv(out / f"courbe_budget_{args.nom}.csv", index=False)
    (out / f"resume_{args.nom}.json").write_text(json.dumps(R, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{args.nom} : seuil {R['seuil']:.4f} ({R['regle_seuil']})")
    for role, b in R["roles"].items():
        txt = (f"  {role:16s} P {b['precision']:.3f} R {b['rappel']:.3f} F1 {b['f1']:.3f} "
               f"[{b['ic95_f1'][0]:.3f} ; {b['ic95_f1'][1]:.3f}]  {b['detections']} / {b['meres']} mères")
        if "comparaison" in b:
            cpa = b["comparaison"]
            txt += (f" | vs {cpa['reference']} (F1 {cpa['reference_resume']['f1']:.3f}) : écart {cpa['difference_f1']:+.3f}, "
                    f"borne basse ({cpa['alpha_unilateral']:.5f}) {cpa['borne_basse_unilaterale']:+.3f}")
        print(txt)
    return R


# ----------------------------------------------------------------------------------------------------------------
# Niveaux nuls (HF-01) : végétation uniforme et demi-maille
# ----------------------------------------------------------------------------------------------------------------
def otsu(v):
    h, b = np.histogram(v, 256)
    c = (b[:-1] + b[1:]) / 2
    w0 = np.cumsum(h)
    w1 = w0[-1] - w0
    m0 = np.cumsum(h * c) / np.maximum(w0, 1)
    m1 = ((h * c).sum() - np.cumsum(h * c)) / np.maximum(w1, 1)
    return c[int(np.argmax(w0 * w1 * (m0 - m1) ** 2))]


def niveaux_nuls(args):
    from PIL import Image
    from scipy.spatial import cKDTree
    L = charger_liste()
    L = L[L.role.isin(args.roles)]
    refs = references(L)
    rng = np.random.default_rng(GRAINE)
    maille = {}
    for g, Lg in L.groupby("groupe"):
        d = []
        for r in Lg.itertuples():
            xy, ty = refs[r.image_path]
            xy = xy[ty == "mere"] * r.cm_par_px / 100
            if len(xy) >= 4:
                dd, _ = cKDTree(xy).query(xy, k=2)
                d += list(dd[:, 1])
        maille[g] = float(np.median(d)) if d else 2.5
    veg_l, dm_l = [], []
    for r in L.itertuples():
        rgb = np.asarray(Image.open(DONNEES / "images" / r.image_path).convert("RGB"), dtype="float32")
        s = rgb.sum(2)
        valide = s > 15
        s[s == 0] = 1
        exg = (2 * rgb[..., 1] - rgb[..., 0] - rgb[..., 2]) / s
        H, W = exg.shape
        yy, xx = np.mgrid[0:H, 0:W]
        pix = np.c_[xx.ravel() + 0.5, yy.ravel() + 0.5]
        reg = dans_region(pix, r).reshape(H, W) & valide
        if reg.sum() < 10:
            continue
        veg = reg & (exg > otsu(exg[reg]))
        xy, ty = refs[r.image_path]
        meres = xy[ty == "mere"]
        n = len(meres)
        if n == 0:
            continue
        # (b) uniforme dans la végétation de la région
        ys, xs = np.nonzero(veg if veg.any() else reg)
        k = rng.integers(0, len(xs), n)
        for x, y in zip(xs[k] + rng.random(n), ys[k] + rng.random(n)):
            veg_l.append(dict(image_path=r.image_path, x=round(float(x), 1), y=round(float(y), 1), score=float(rng.random())))
        # (c) demi-maille : chaque mère déplacée de a/2, dans la végétation et la région
        a2 = maille[r.groupe] / 2 * 100 / r.cm_par_px
        for cx, cy in meres:
            for _ in range(50):
                t = rng.uniform(0, 2 * np.pi)
                x, y = cx + a2 * np.cos(t), cy + a2 * np.sin(t)
                xi, yi = int(x), int(y)
                if 0 <= xi < W and 0 <= yi < H and veg[yi, xi]:
                    break
            dm_l.append(dict(image_path=r.image_path, x=round(float(x), 1), y=round(float(y), 1), score=float(rng.random())))
    dossier = EVAL / "niveaux_nuls"
    dossier.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(veg_l).to_csv(dossier / "vegetation_uniforme.csv", index=False)
    pd.DataFrame(dm_l).to_csv(dossier / "demi_maille.csv", index=False)
    (dossier / "maille_par_groupe.json").write_text(json.dumps(maille, indent=2), encoding="utf-8")
    print("mailles (m) :", {g: round(v, 2) for g, v in maille.items()})
    print(f"écrit : {dossier}")


# ----------------------------------------------------------------------------------------------------------------
# Auto-test : égalité avec evaluer_comptage.evaluer_zone
# ----------------------------------------------------------------------------------------------------------------
def auto_test(detections):
    import geopandas as gpd
    L = charger_liste()
    L = L[L.role.isin(["dev_reglage", "dev_transfert", "controle_repro", "val_iter"])].sample(150, random_state=GRAINE)
    refs = references(L)
    dets = lire_detections(detections, L)
    rng = np.random.default_rng(GRAINE)
    n_ok = n = 0
    for r in L.itertuples():
        xy, sc = dets.get(r.image_path, (np.zeros((0, 2)), np.zeros(0)))
        rxy, ty = refs[r.image_path]
        ty = ty.copy()
        if len(ty):                                   # quelques points rendus incertains pour tester la règle
            ty[rng.random(len(ty)) < 0.1] = "incertain"
        for s in (0.1, 0.3, 0.5):
            d = xy[sc >= s] * r.cm_par_px / 100
            rm = rxy * r.cm_par_px / 100
            a = evaluer_points(d, rm, ty)
            G = lambda p: gpd.GeoDataFrame(geometry=gpd.points_from_xy(p[:, 0], p[:, 1]) if len(p) else gpd.GeoSeries([]))
            gd = G(d)
            gr = G(rm)
            gr["type"] = ty
            b, _, _ = ec.evaluer_zone(gd, gr, RAYON_M)
            n += 1
            n_ok += (a[0], a[1], a[2]) == (b["vrais_positifs"], b["faux_positifs"], b["oublies"])
    print(f"auto-test : {n_ok} / {n} évaluations identiques à evaluer_comptage.evaluer_zone")
    return n_ok == n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--liste", action="store_true", help="écrire out/comptage_math/evaluation/images_dense.csv")
    ap.add_argument("--auto-test", metavar="DETECTIONS", help="comparer à evaluer_zone sur 150 images")
    ap.add_argument("--niveaux-nuls", action="store_true")
    ap.add_argument("--detections")
    ap.add_argument("--nom", default="methode")
    ap.add_argument("--seuil-fixe", type=float)
    ap.add_argument("--comparer", help="détections de la référence (différence appariée)")
    ap.add_argument("--nom-comparer", default="reference")
    ap.add_argument("--seuil-comparer", type=float)
    ap.add_argument("--m-comparaisons", type=int, default=1, help="nombre de comparaisons pour Bonferroni (plafond : 8)")
    ap.add_argument("--roles", nargs="+", default=["dev_reglage", "dev_transfert", "val_iter"])
    ap.add_argument("--ouvrir-scellee", metavar="E-NNN", help="mesure unique de val_scellee (test_final.md, 2.5)")
    ap.add_argument("--out", default=str(EVAL / "sorties"))
    args = ap.parse_args(argv)
    if args.liste:
        L, anomalies = construire_liste()
        L.to_csv(LISTE, index=False)
        print(L.groupby(["role", "groupe"]).agg(images=("image_path", "size"), cm_min=("cm_par_px", "min"),
                                                 cm_max=("cm_par_px", "max"), unites=("unite", "nunique")).to_string())
        print(f"grilles non reconstruites (tuile entière comptée) : {anomalies}")
    elif args.auto_test:
        sys.exit(0 if auto_test(args.auto_test) else 1)
    elif args.niveaux_nuls:
        niveaux_nuls(args)
    elif args.detections:
        evaluer(args)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
