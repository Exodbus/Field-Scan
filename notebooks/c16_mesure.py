#!/usr/bin/env python3
"""Essai c16 (16/11) : mesure et règle de docs/journee_2026-11-16/avenant_c16_aiguillage_resolution.md (sections 3 et 4).

Lit les pics écrits par notebooks/c16_pics.py (out/comptage/jour_1611/pics/) et mesure avec le code du banc importé sans
modification : `bc.mesurer_jeu` (scripts/v6_banc_commun.py : appariement un à un dans 20 px, non-mères ignorées,
disque DJI, zones MM), `cc.jeu` et `cc.lignes` (scripts/c13_banc_commun.py : garde-fou des juges, grille 0,10-0,60).
Le candidat « réseau seul » rend ses pics enregistrés, qui sont exactement `bc.pics(carte)` (`v6_banc_candidats.f_seul`).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/c16_mesure.py v5 c13a c15d ...
Résultats : out/comptage/jour_1611/mesures/<nom>.json, un fichier par modèle (deux chaînes peuvent mesurer en même temps) ;
le v5 doit être mesuré en premier : c'est la référence.
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.optimize import linear_sum_assignment  # noqa: E402
from scipy.spatial.distance import cdist  # noqa: E402

import c13_banc_commun as cc  # noqa: E402
import v6_banc_commun as bc  # noqa: E402

SORTIE = RACINE / "out/comptage/jour_1611"
PICS = SORTIE / "pics"
MESURES = SORTIE / "mesures"
REGLAGE = cc.REGLAGE
RES = (8, 11, 14)
SEUIL_V5 = 0.30
D5 = RACINE / "data/drone/comptage_v5_5cm"
A2 = RACINE / "data/raw/plantain_ghana_m2"
_PICS = {}


def pics(nom, variante, jeu):
    cle = (nom, variante, jeu)
    if cle not in _PICS:
        z = np.load(PICS / f"{nom}_{variante}_{jeu}.npz")
        p, d = z["pics"], z["debut"]
        _PICS[cle] = {str(n): p[d[i]:d[i + 1]] for i, n in enumerate(z["noms"])}
    return _PICS[cle]


def candidat(nom, variante, jeu):
    P = pics(nom, variante, jeu)

    def f(ctx):
        a = P[ctx.nom]
        return a[:, :2].astype("float64"), a[:, 2].astype("float64")
    return f


def lignes_res(nom, cm):
    v = f"d{cm}"
    m = {j: bc.mesurer_jeu(candidat(nom, v, j), j, cc.jeu(j)) for j in REGLAGE + ["neg"]}
    return cc.lignes(m)


def ligne(L, s):
    return [l for l in L if abs(l["seuil"] - s) < 1e-9][0]


# ------------------------------------------------------------------------------------------- M3 : agroforesterie
def apparier(a, b, rayon=20.0):
    """Nombre de points de a retrouvés dans b (un à un, distance <= rayon), comme notebooks/c15b_controle_rt.py."""
    if not len(a) or not len(b):
        return 0
    d = cdist(a, b)
    li, co = linear_sum_assignment(np.where(d <= rayon, d, 1e6))
    return int((d[li, co] <= rayon).sum())


def controle_rt(nom, seuil, cm):
    ref = pics("v5", "base", "rt")                                  # v5 à 5 cm, seuil 0,30 : les « pieds du v5 »
    cand = pics(nom, f"d{cm}", "rt")
    obj = pd.read_csv(D5 / "objets.csv")
    obj = obj[obj.image_path.isin(set(ref)) & (obj.type == "mere")]
    n_v5 = retr = meres = vp = det = 0
    for t in ref:
        a = ref[t][ref[t][:, 2] >= SEUIL_V5][:, :2].astype("float64")
        b = cand[t][cand[t][:, 2] >= seuil][:, :2].astype("float64")
        m = obj[obj.image_path == t][["cx", "cy"]].to_numpy("float64").reshape(-1, 2)
        n_v5 += len(a); retr += apparier(a, b); meres += len(m); vp += apparier(m, b); det += len(b)
    return dict(tuiles=len(ref), pieds_v5_5cm=n_v5, retrouves=retr, part_pieds_v5=retr / max(n_v5, 1),
                meres=meres, meres_vues=vp, rappel_meres=vp / max(meres, 1), detections=det)


# ------------------------------------------------------------------------------------------- M4 : Ghana
def ghana(nom, seuil, cm=11):
    """F1 du total des 199 photos (somme vp, fp, fn), comme scripts/jeux_neufs_a2_mesure_v5.py."""
    f = float(json.loads((RACINE / "out/jeux_neufs_1511/a2_echelle.json").read_text(encoding="utf-8"))["facteur"])
    P = pics(nom, f"d{cm}", "ghana")
    vp = fp = fn = det = reels = 0
    for photo in sorted(P):
        b = pd.read_csv(A2 / "annotations" / (photo + ".csv"))
        ref = b[["cx", "cy"]].to_numpy("float64") * f
        d = P[photo][P[photo][:, 2] >= seuil][:, :2].astype("float64")
        a, b_, c = bc.compter(d, ref, np.zeros((0, 2)))
        vp += a; fp += b_; fn += c; det += len(d); reels += len(ref)
    p, r, f1 = bc.prf(vp, fp, fn)
    return dict(photos=len(P), vp=vp, fp=fp, fn=fn, precision=p, rappel=r, f1=f1, detectes=det, reels=reels)


# ------------------------------------------------------------------------------------------- règle (avenant, section 4)
def choisir(L):
    """4.1 : seuil qui maximise la moyenne à 11 cm sous val_negatifs dégradé < 1 % à 8, 11 et 14 cm ; égalité : le plus bas."""
    el = [s for s in cc.SEUILS if all(ligne(L[c], s)["taux_fp"] < 0.01 for c in RES)]
    if not el:
        return None
    meilleur = max(ligne(L[11], s)["moyenne"] for s in el)
    return min(s for s in el if ligne(L[11], s)["moyenne"] == meilleur)


def sauver(nom, e):
    tmp = MESURES / f"{nom}.tmp"
    tmp.write_text(json.dumps(e, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, MESURES / f"{nom}.json")


def main():
    noms = [a for a in sys.argv[1:] if not a.startswith("--")]
    MESURES.mkdir(exist_ok=True)
    E = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in MESURES.glob("*.json")}
    for nom in noms:
        t0 = time.time()
        e = E.get(nom, {})
        L = {c: lignes_res(nom, c) for c in RES}
        e["lignes"] = {str(c): L[c] for c in RES}
        s = SEUIL_V5 if nom == "v5" else choisir(L)
        e["seuil"] = s
        if s is None:
            e["statut"] = dict(finaliste=False, raison="aucun seuil sous 1 % de val_negatifs dégradé à 8, 11 et 14 cm")
            E[nom] = e; sauver(nom, e)
            print(f"{nom} : aucun seuil éligible", flush=True); continue
        e["au_seuil"] = {str(c): ligne(L[c], s) for c in RES}
        e["rt"] = {str(c): controle_rt(nom, s, c) for c in RES}
        if nom == "v5":
            e["ghana_11"] = ghana("v5", s)
        else:
            assert "v5" in E, "le v5 (référence) doit être mesuré d'abord"
            v = E["v5"]
            st = {}
            st["c1_gain"] = e["au_seuil"]["11"]["moyenne"] >= v["au_seuil"]["11"]["moyenne"] + 0.030
            pertes = {f"{j}@{c}": e["au_seuil"][str(c)][f"f1_{j}"] - v["au_seuil"][str(c)][f"f1_{j}"] for c in RES for j in REGLAGE}
            st["pire_perte"] = min(pertes.values()); st["pire_jeu"] = min(pertes, key=pertes.get)
            st["c2_pertes"] = bool(st["pire_perte"] >= -0.020
                                   and e["au_seuil"]["8"]["moyenne"] >= v["au_seuil"]["8"]["moyenne"]
                                   and e["au_seuil"]["14"]["moyenne"] >= v["au_seuil"]["14"]["moyenne"])
            st["c3_negatifs"] = all(e["au_seuil"][str(c)]["taux_fp"] < 0.01 for c in RES)
            r, rv = e["rt"]["11"], v["rt"]["11"]
            st["c4a_meres"] = r["rappel_meres"] >= rv["rappel_meres"] - 0.010
            st["c4b_pieds_v5"] = r["part_pieds_v5"] >= rv["part_pieds_v5"] - 0.010
            avant = all(st[k] for k in ("c1_gain", "c2_pertes", "c3_negatifs", "c4a_meres", "c4b_pieds_v5"))
            if avant and (PICS / f"{nom}_d11_ghana.npz").exists():
                e["ghana_11"] = ghana(nom, s)
                st["c5_ghana"] = e["ghana_11"]["f1"] >= v["ghana_11"]["f1"] - 0.020
            elif avant:
                st["c5_ghana"] = None                   # à mesurer (M4 seulement pour qui a passé 1 à 4)
            else:
                st["c5_ghana"] = False
                e.pop("ghana_11", None)
            st["finaliste"] = bool(avant and st["c5_ghana"])
            e["statut"] = st
        E[nom] = e
        sauver(nom, e)
        a = e["au_seuil"]
        print(f"{time.strftime('%H:%M:%S')} {nom} ({time.time() - t0:.0f} s) seuil {s} | "
              + " | ".join(f"{c} cm moy {a[str(c)]['moyenne']:.4f} (" + " ".join(f"{a[str(c)]['f1_' + j]:.3f}" for j in REGLAGE)
                           + f") neg {a[str(c)]['fp_neg']} ({a[str(c)]['taux_fp']:.2%})" for c in RES)
              + " | RT11 mères " + f"{e['rt']['11']['rappel_meres']:.3f} pieds v5 {e['rt']['11']['part_pieds_v5']:.3f}"
              + (f" | Ghana11 F1 {e['ghana_11']['f1']:.4f}" if "ghana_11" in e else "")
              + (f" | statut {json.dumps(e.get('statut'), ensure_ascii=False)}" if nom != "v5" else ""), flush=True)


if __name__ == "__main__":
    main()
