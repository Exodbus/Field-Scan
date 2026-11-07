#!/usr/bin/env python3
"""E-020 — Mesure unique de val_scellee (D-012) : vote B′ figé (E-010), v5 au seuil 0,30, baseline T3 figée (E-015).

Rédacteur : independent-evaluator. Règles écrites avant toute détection sur val_scellee :
docs/recherche/test_final.md § 8 (et § 2.5, § 3.2, § 5.6, § 6).

Deux modes, exclusifs :

  --essai-a-blanc
      Essai des trois détecteurs et de l'évaluation sur 2 tuiles de bv_session_a (développement). Aucune image,
      aucune référence ni aucune détection de val_scellee n'est lue. Les détections recalculées sont comparées aux
      détections figées d'E-010 (vote), d'E-001 (v5) et d'E-015 (baseline T3) sur les mêmes tuiles.
      Sorties : out/comptage_math/evaluation/E-020_essai/.

  --mesure E-020
      Mesure unique. Refusée si out/comptage_math/evaluation/E-020/VERROU existe (créé au début de la mesure).
      Vérifie les empreintes SHA-256 du § 8, puis les empreintes des 40 images (decoupage_bv_b_val.csv), produit
      les détections des trois méthodes sur les 40 photos conformes seulement, et les évalue avec
      scripts/math_evaluer.py (fonction evaluer, importée sans modification ; seule la liste d'images est
      restreinte aux 40 photos conformes). Sorties : out/comptage_math/evaluation/E-020/.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/evaluation/e020_val_scellee.py --essai-a-blanc
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u out/comptage_math/evaluation/e020_val_scellee.py --mesure E-020
"""
import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]
CONV = RACINE / "out/comptage_math/convergence-engineer"
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(CONV))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

import math_evaluer as me  # noqa: E402  (lecture seule)
import baseline as BL  # noqa: E402  (detecter_image, lecture seule)
import e008_votes as E8  # noqa: E402  (lire, detecter, ecrire_csv : lecture seule, comme E-010)
from comptage_math import votes as VT  # noqa: E402

IDENT = "E-020"
SORTIE = ICI / IDENT
ESSAI = ICI / "E-020_essai"

# ---------------- candidates figées (test_final.md § 8.3)
VOTE = dict(r_max=1.6, p=1.0, sigmas_t=(0.10,), r_nms=1.0, canal="luminance", seuil_z=2.2381955265998843)
V5 = dict(modele="modeles/centres_5cm_v5.onnx", seuil_min=0.05, seuil=0.30)
T3 = dict(sigma=0.35, distance=1.25, seuil=0.16876235716044902)

# ---------------- photos mesurées (test_final.md § 8.2) : 40 conformes sur 42
EXCLUES = {"DJI_0867", "DJI_0903"}
PHOTOS = [f"DJI_{n:04d}" for n in range(862, 904) if f"DJI_{n:04d}" not in EXCLUES]
BLOCS_ATTENDUS = {"L1B1": 6, "L1B2": 7, "L1B3": 7, "L2B1": 7, "L2B2": 7, "L2B3": 6}

# ---------------- empreintes figées (test_final.md § 8.4) ; ce script lui-même est empreinté dans le § 8.4
FIGES = {
    "comptage_math/votes.py": "eff3fb21f6782f73b14eb7309613c1666144b7cacec0f4e114c14d8a05d76625",
    "comptage_math/orientation.py": "e3343982eea20c7f8dcc4db34ab30f366fdb56eac0bb808324e9f728e7f356be",
    "comptage_math/feuille.py": "e01989cb1f9820940106e945e32c319cddde7246d8668c3155a3503b5f981bf3",
    "out/comptage_math/convergence-engineer/e008_votes.py": "133b4aceeeb3c0dd7b8837527ea7f26ad288a8116b0a0a3f2c5e7ee2242a5b27",
    "out/comptage_math/convergence-engineer/e010_extension.py": "212b8a56d76816dfaf92b18f40d69f92c379ead463985ae89ada582011fbb614",
    "out/comptage_math/convergence-engineer/E-010/bilan_E-010.json": "0e60267e27a0c0043165d3aa19f417b5ac1c86033f0a97c57c9a1556f34244bb",
    "out/comptage_math/evaluation/baseline.py": "f58f03e2b509b42ecc018d708ea5a5b5e1d44a8574912acf5d09a14758e49bae",
    "out/comptage_math/evaluation/v5_detecter.py": "ba76a523da4e32e99fed74a6164189f71a4d7f76a9033bdf784d5c6e95308b9a",
    "out/comptage_math/evaluation/E-015/bilan_E-015.json": "965600d6ff5c4e5b53e606fad3d595213d83cf8827aedec00432a312c414c2f8",
    "out/comptage_math/evaluation/decoupage_bv_b_val.csv": "7aafb1fe8fd936421ad76373551d822ca2de7fc86b2881039cc0415e3dc0e741",
    "out/comptage_math/annotation-manager/completude_val_scellee.csv": "e8007a8baf3178e189aa2a07225a5f1bc8e142972d8414172fa5f1da2e596882",
    "scripts/math_evaluer.py": "934585b1eae50751b6b961bc6cae46455a45d3dfe47547c69b490049b3a99260",
    "scripts/evaluer_comptage.py": "6a13441d7be7233b5773d76cb94ebaf474090e2a29acb17864d72f60f3470ff6",
    "fieldscan/drone.py": "7e3e951cb590c2469d3fc63bf6a71fb18a3b7c6504bc4e246491598ab0940b9c",
    "modeles/centres_5cm_v5.onnx": "12f9b4caa5735767c454de99edf1a6616765718243555f8559c2cfcc0722f1ea",
    "modeles/centres_5cm_v5.json": "47246578af1f00bf52cf4816cc78f531b5d83d9781db8d78123c37217e76dd2a",
}


def sha(p):
    return hashlib.sha256((RACINE / p).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------------------------
# Détecteurs (mêmes appels que E-010 passe 2, v5_detecter.py et baseline.py)
# ---------------------------------------------------------------------------------------------------------------
def vote_image(arg):
    chemin, cm = arg
    cv2.setNumThreads(1)
    rgb = E8.lire(chemin)
    res = cm / 100.0
    if (rgb.sum(2) > 15).sum() < 100:
        return np.zeros((0, 2)), np.zeros(0)
    r = VT.carte_votes_multi(rgb, res, VOTE["r_max"], VOTE["p"], VOTE["sigmas_t"])
    return E8.detecter(r["z"], r["valide"], VOTE["r_nms"] / res)


def detections_vote(L):
    args = [(me.DONNEES / "images" / i, c) for i, c in zip(L.image_path, L.cm_par_px)]
    with ProcessPoolExecutor(8) as ex:
        R = list(ex.map(vote_image, args, chunksize=2))
    return {i: r for i, r in zip(L.image_path, R)}


def detections_v5(L):
    from fieldscan.drone import DetecteurCentres
    det = DetecteurCentres(RACINE / V5["modele"])
    out = {}
    for r in L.itertuples():
        img = Image.open(me.DONNEES / "images" / r.image_path).convert("RGB")
        f = r.cm_par_px / 5.0
        if abs(f - 1) > 1e-3:
            img = img.resize((max(1, round(img.width * f)), max(1, round(img.height * f))), Image.LANCZOS)
        rgb = np.moveaxis(np.asarray(img), -1, 0)
        xy, sc = det.predire(rgb, np.ones(rgb.shape[1:], bool), seuil_min=V5["seuil_min"])
        out[r.image_path] = (xy / f, sc)
    return out


def detections_t3(L):
    couples = [(T3["sigma"], T3["distance"])]
    taches = [(me.DONNEES / "images" / i, c, couples) for i, c in zip(L.image_path, L.cm_par_px)]
    with ProcessPoolExecutor(8) as ex:
        R = list(ex.map(BL.detecter_image, taches, chunksize=2))
    return {i: (s[couples[0]][:, :2], s[couples[0]][:, 2]) for i, s in zip(L.image_path, R)}


def ecrire(chemin, dets, score_complet=False):
    """Format image_path,x,y,score. Vote et v5 : x, y à 2 décimales et score à 5, comme E-010 et v5_detecter.py.
    Baseline T3 : score en pleine précision, comme les détections d'E-015 sur lesquelles son seuil a été choisi."""
    if not score_complet:
        return E8.ecrire_csv(chemin, dets)
    lignes = [dict(image_path=im, x=round(float(x), 2), y=round(float(y), 2), score=float(z))
              for im, (xy, z) in dets.items() for (x, y), z in zip(xy, z)]
    pd.DataFrame(lignes, columns=["image_path", "x", "y", "score"]).to_csv(chemin, index=False)


# ---------------------------------------------------------------------------------------------------------------
# Évaluation : math_evaluer.evaluer, liste restreinte
# ---------------------------------------------------------------------------------------------------------------
def evaluer(L, det, nom, seuil, out, comparer=None, nom_c=None, seuil_c=None):
    me.charger_liste = lambda avec_scellee=False, _L=L: _L.copy()      # liste restreinte (40 photos conformes)
    argv = ["--detections", str(det), "--nom", nom, "--seuil-fixe", repr(float(seuil)), "--roles", "val_scellee",
            "--ouvrir-scellee", IDENT, "--m-comparaisons", "1", "--out", str(out)]
    if comparer:
        argv += ["--comparer", str(comparer), "--nom-comparer", nom_c, "--seuil-comparer", repr(float(seuil_c))]
    ap_args = me.argparse.ArgumentParser()
    for a, k in (("--detections", {}), ("--nom", {}), ("--seuil-fixe", dict(type=float)), ("--comparer", {}),
                 ("--nom-comparer", dict(default="reference")), ("--seuil-comparer", dict(type=float)),
                 ("--m-comparaisons", dict(type=int, default=1)), ("--roles", dict(nargs="+")),
                 ("--ouvrir-scellee", {}), ("--out", {})):
        ap_args.add_argument(a, **k)
    return me.evaluer(ap_args.parse_args(argv))


def f1_blocs(out, nom):
    P = pd.read_csv(out / f"par_image_{nom}.csv")
    g = P.groupby("unite")[["vp", "fp", "fn"]].sum()
    return {u: float(me.prf(r.to_numpy(float))[2]) for u, r in g.iterrows()}


def f1_budget(out, nom):
    C = pd.read_csv(out / f"courbe_budget_{nom}.csv")
    return float(C[C.multiple == 1.0].f1.iloc[0])


def verdict(f1x, f1r, borne, blocs_x, blocs_r, n_blocs, f1x_k, f1r_k):
    """§ 2.5 + § 3.2 + § 5.6."""
    if n_blocs >= 6:
        point = bool(f1x > f1r and borne > 0)
        regle = "F1(X) > F1(réf) et borne basse unilatérale 95 % (bootstrap par blocs) > 0"
    else:
        point = bool(f1x > f1r and all(blocs_x[u] - blocs_r[u] > 0 for u in blocs_x))
        regle = "F1(X) > F1(réf) et test de signe : différence positive dans tous les blocs (§ 5.6)"
    budget = bool(f1x_k >= f1r_k)
    v = "confirmé" if point and budget else ("non concluant" if point or budget else "non confirmé")
    return dict(regle=regle, point_de_fonctionnement=point, budget_N_ref=budget, verdict=v)


def campagne(L, dossier, avec_bilan):
    dossier.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    dv, d5, db = detections_vote(L), detections_v5(L), detections_t3(L)
    chemins = dict(vote=dossier / "detections_vote_B_prime.csv", v5=dossier / "detections_v5.csv",
                   baseline=dossier / "detections_baseline_T3.csv")
    for k, d in zip(chemins, (dv, d5, db)):
        ecrire(chemins[k], d, score_complet=(k == "baseline"))
    print(f"détections : {time.time() - t0:.0f} s", flush=True)
    ev = dossier / "evaluation"
    s = dict(vote=VOTE["seuil_z"], v5=V5["seuil"], baseline=T3["seuil"])
    R = dict(
        vote_contre_v5=evaluer(L, chemins["vote"], "vote_contre_v5", s["vote"], ev, chemins["v5"], "v5", s["v5"]),
        vote_contre_baseline=evaluer(L, chemins["vote"], "vote_contre_baseline", s["vote"], ev, chemins["baseline"], "baseline_T3", s["baseline"]),
        baseline_contre_v5=evaluer(L, chemins["baseline"], "baseline_contre_v5", s["baseline"], ev, chemins["v5"], "v5", s["v5"]),
        v5=evaluer(L, chemins["v5"], "v5", s["v5"], ev),
        baseline_T3=evaluer(L, chemins["baseline"], "baseline_T3", s["baseline"], ev),
    )
    if not avec_bilan:
        return R, chemins
    n_blocs = int(L.unite.nunique())
    fb = {n: f1_blocs(ev, n) for n in ("vote_contre_v5", "v5", "baseline_T3")}
    fk = {n: f1_budget(ev, n) for n in ("vote_contre_v5", "v5", "baseline_T3")}
    b = {}
    for cle, ref, nref in (("contre_v5", "v5", "v5"), ("contre_baseline", "baseline_T3", "baseline_T3")):
        rr = R[f"vote_{cle}"]["roles"]["val_scellee"]
        cp = rr["comparaison"]
        b[cle] = dict(f1_vote=rr["f1"], f1_reference=cp["reference_resume"]["f1"], difference=cp["difference_f1"],
                      borne_basse_unilaterale_95=cp["borne_basse_unilaterale"], ic95_difference=cp["ic95_difference"],
                      f1_budget_vote=fk["vote_contre_v5"], f1_budget_reference=fk[nref],
                      difference_par_bloc={u: round(fb["vote_contre_v5"][u] - fb[nref][u], 4) for u in fb[nref]},
                      **verdict(rr["f1"], cp["reference_resume"]["f1"], cp["borne_basse_unilaterale"],
                                fb["vote_contre_v5"], fb[nref], n_blocs, fk["vote_contre_v5"], fk[nref]))
    return R, chemins, b


# ---------------------------------------------------------------------------------------------------------------
def essai_a_blanc():
    """2 tuiles de bv_session_a ; rien de val_scellee n'est lu."""
    L = me.charger_liste()
    D = pd.read_csv(CONV / "E-010/detections/vote_e010.csv")
    n = D[D.image_path.str.startswith("bv_bv_session_a_")].groupby("image_path").size()
    Ls = L[(L.role == "dev_reglage") & (L.groupe == "bv_session_a") & L.image_path.isin(n[n > 40].index)]
    L2 = Ls.drop_duplicates("unite").head(2).copy()
    assert len(L2) == 2 and not L2.image_path.str.contains("bv_b_").any()
    L2["role"] = "val_scellee"          # étiquette en mémoire seulement, pour passer par le chemin de la mesure
    R, chemins, criteres = campagne(L2, ESSAI, avec_bilan=True)   # 2 blocs : branche du test de signe (§ 5.6)
    # reproduction des détections figées sur les mêmes tuiles
    ref = {"vote": CONV / "E-010/detections/vote_e010.csv",
           "v5": ICI / "v5/detections_val_iter_dev.csv",
           "baseline": ICI / "E-015/T3_detections_baseline_bv_session_a.csv"}
    rep = {}
    for k in ref:
        A = pd.read_csv(chemins[k]).sort_values(["image_path", "x", "y"]).reset_index(drop=True)
        F = pd.read_csv(ref[k])
        F = F[F.image_path.isin(L2.image_path)].sort_values(["image_path", "x", "y"]).reset_index(drop=True)
        same_n = len(A) == len(F)
        dxy = float(np.abs(A[["x", "y"]].to_numpy() - F[["x", "y"]].to_numpy()).max()) if same_n and len(A) else None
        dsc = float(np.abs(A.score.to_numpy() - F.score.to_numpy()).max()) if same_n and len(A) else None
        rep[k] = dict(n_recalcule=len(A), n_fige=len(F), ecart_xy_max=dxy, ecart_score_max=dsc,
                      identique=bool(same_n and dxy is not None and dxy <= 0.011 and dsc <= 2e-5))
    bilan = dict(identifiant="E-020 essai à blanc", tuiles=L2.image_path.tolist(), reproduction=rep,
                 evaluation={k: {kk: v["roles"]["val_scellee"].get(kk) for kk in ("f1", "precision", "rappel", "detections", "meres")}
                             for k, v in R.items()},
                 criteres=criteres,
                 empreintes_actuelles={p: sha(p) for p in FIGES},
                 empreinte_script=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (ESSAI / "bilan_essai.json").write_text(json.dumps(bilan, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(bilan, indent=1, ensure_ascii=False))


def mesure(ident):
    if ident != IDENT:
        raise SystemExit(f"Identifiant attendu : {IDENT}")
    verrou = SORTIE / "VERROU"
    if verrou.exists():
        raise SystemExit("Refus : val_scellee a déjà été mesurée (VERROU présent). Aucune deuxième mesure (§ 2.5).")
    faux = {p: (sha(p), h) for p, h in FIGES.items() if h is None or sha(p) != h}
    if faux:
        raise SystemExit(f"Refus : empreintes non conformes au § 8.4 : {faux}")
    SORTIE.mkdir(parents=True, exist_ok=True)
    verrou.write_text(time.strftime("%Y-%m-%d %H:%M:%S") + " début de la mesure unique\n", encoding="utf-8")
    V = pd.read_csv(me.DECOUPAGE_VAL)
    V = V[(V.role == "val_scellee") & V.photo.isin(PHOTOS)]
    assert len(V) == 40 and set(V.photo) == set(PHOTOS)
    assert V.groupby("bloc").size().to_dict() == BLOCS_ATTENDUS
    C = pd.read_csv(RACINE / "out/comptage_math/annotation-manager/completude_val_scellee.csv")
    assert set(C[C.verdict == "conforme"].photo) == set(PHOTOS)
    for r in V.itertuples():
        assert hashlib.sha256((me.DONNEES / "images" / r.image_path).read_bytes()).hexdigest() == r.sha256, r.image_path
    L = me.charger_liste(True)
    L = L[(L.role == "val_scellee") & L.image_path.isin(V.image_path)].copy()
    assert len(L) == 40 and L.unite.nunique() == 6 and (L.cm_par_px == 5.0).all()
    R, chemins, b = campagne(L, SORTIE, avec_bilan=True)
    bilan = dict(identifiant=IDENT, decision="D-012", regles="docs/recherche/test_final.md § 8",
                 photos=PHOTOS, blocs=BLOCS_ATTENDUS, candidates=dict(vote=VOTE, v5=V5, baseline_T3=T3),
                 resultats={k: v["roles"]["val_scellee"] for k, v in R.items()}, criteres=b,
                 empreintes={p: sha(p) for p in FIGES},
                 empreinte_script=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (SORTIE / f"bilan_{IDENT}.json").write_text(json.dumps(bilan, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    verrou.write_text(verrou.read_text(encoding="utf-8") + time.strftime("%Y-%m-%d %H:%M:%S") + " fin\n", encoding="utf-8")
    print(json.dumps(b, indent=1, ensure_ascii=False))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--essai-a-blanc", action="store_true")
    g.add_argument("--mesure", metavar="E-NNN")
    a = ap.parse_args()
    if a.essai_a_blanc:
        essai_a_blanc()
    else:
        mesure(a.mesure)


if __name__ == "__main__":
    main()
