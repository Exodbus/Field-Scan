#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : recalcul INDÉPENDANT des finalistes de comptage (banc) sur le réglage.

Ne lit que les cartes en cache des jeux de réglage (out/comptage_v6/banc/cache : dense, plantain, jeunes, mm, btd_val,
neg = tuiles sans bananier de VALIDATION) et les annotations de ces jeux. Aucun juge (segmento, cg, banano,
test_negatifs) ni test vierge (banana_trees_kp) n'est ouvert : un garde-fou refuse tout chemin qui les nomme.
N'importe pas le banc de C-banc : pics, appariement, masque et compte sont réécrits d'après la description du protocole
v5 (pics : maximum local 7 x 7, bord à 0, score >= 0,10 ; appariement un-à-un à distance minimale, rayon 20 px ;
détections non appariées à moins de 20 px d'un point non-mère ignorées ; disque DJI ; zones MM).

Candidats reconnus (spécification JSON) :
  {"type": "seul", "modele": "v5"}
  {"type": "melange", "membres": ["v3","v4"], "mode": "moyenne"|"geometrique"|"maximum"}
  {"type": "union", "membres": [["v5", 0.0], ["v3", 0.05]], "rayon": 30}
  {"type": "p90", "tau": 0.55, "decalage": 0.10, "petit": <spec>, "grand": <spec>, "smin": 0.15, "q": 0.9}
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_c_recalcul.py [--spec fichier.json]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from scipy.optimize import linear_sum_assignment

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
OUT = RACINE / "out/controle_nuit_1112"
CACHE = RACINE / "out/comptage_v6/banc/cache"
D5, D6 = RACINE / "data/drone/comptage_v5_5cm", RACINE / "data/drone/comptage_v6_5cm"
JEUX = ["dense", "plantain", "jeunes", "mm", "btd_val"]
SEUILS = [round(0.10 + 0.05 * k, 2) for k in range(11)]
INTERDITS = ("segmento", "test_", "cg", "banano", "banana_trees_kp", "neg_test")


def garde(nom):
    assert not any(m in str(nom) for m in INTERDITS), f"juge ou test refusé : {nom}"


def items(jeu):
    garde(jeu)
    if jeu == "mm":
        P, Z = pd.read_csv(D5 / "mm/points.csv"), pd.read_csv(D5 / "mm/zones.csv")
        out = []
        for z in Z.itertuples():
            p = P[P.zone_id == z.zone_id]
            out.append(dict(nom=z.image_path, pts=p[p.type == "mere"][["x", "y"]].to_numpy("f8"),
                            ign=p[p.type != "mere"][["x", "y"]].to_numpy("f8"), zone=(z.x0, z.y0, z.x1, z.y1),
                            masque=None, arbres=0))
        return out
    ens, D = {"dense": ("val_dense_bv", D5), "plantain": ("val_plantain", D5), "jeunes": ("val_jeunes", D5),
              "btd_val": ("val_espace", D6), "neg": ("val_negatifs", D5)}[jeu]
    T, O = pd.read_csv(D / "tuiles.csv"), pd.read_csv(D / "objets.csv")
    T = T[T.ensemble == ens]
    assert len(T), jeu
    O = dict(tuple(O[O.image_path.isin(set(T.image_path))].groupby("image_path")))
    out = []
    for r in T.itertuples():
        o = O.get(r.image_path)
        m = o[o.type == "mere"][["cx", "cy"]].to_numpy("f8") if o is not None else np.zeros((0, 2))
        ig = o[o.type != "mere"][["cx", "cy"]].to_numpy("f8") if o is not None else np.zeros((0, 2))
        masque = None if pd.isna(r.masque_r) else (r.masque_cx, r.masque_cy, r.masque_r)
        if masque is not None:
            m = m[((m[:, 0] - masque[0]) ** 2 + (m[:, 1] - masque[1]) ** 2) <= masque[2] ** 2]
        out.append(dict(nom=r.image_path, pts=m, ign=ig, zone=None, masque=masque, arbres=int(r.n_autres_arbres)))
    return out


_C = {}


def carte(modele, jeu, nom, variante="base"):
    cle = (modele, variante, jeu)
    if cle not in _C:
        p = CACHE / f"{modele}_{variante}_{jeu}"
        _C[cle] = (np.memmap(p.with_suffix(".f32"), dtype="float32", mode="r"), json.loads(p.with_suffix(".json").read_text()))
    mm, idx = _C[cle]
    a, h, w = idx[nom]
    return np.asarray(mm[a:a + h * w], dtype="float64").reshape(h, w)


def maxima(c, smin, k=7):
    r = k // 2
    pad = np.pad(c, r, constant_values=0.0)
    mx = sliding_window_view(pad, (k, k)).max(axis=(2, 3))
    j, i = np.nonzero((c == mx) & (c >= smin))
    return np.c_[(i + 0.5) * 4.0, (j + 0.5) * 4.0], c[j, i]


def candidat(spec, jeu, nom):
    t = spec["type"]
    if t == "seul":
        return maxima(carte(spec["modele"], jeu, nom, spec.get("variante", "base")), 0.10)
    if t == "melange":
        cs = [carte(m, jeu, nom) for m in spec["membres"]]
        w = np.asarray(spec.get("poids", [1.0] * len(cs)), "f8"); w /= w.sum()
        if spec["mode"] == "moyenne":
            c = sum(a * b for a, b in zip(w, cs))
        elif spec["mode"] == "geometrique":
            c = np.exp(sum(a * np.log(np.maximum(b, 1e-6)) for a, b in zip(w, cs)))
        elif spec["mode"] == "maximum":
            c = np.max(cs, 0)
        elif spec["mode"] == "logit":
            z = sum(a * np.log(np.clip(b, 1e-6, 1 - 1e-6) / (1 - np.clip(b, 1e-6, 1 - 1e-6))) for a, b in zip(w, cs))
            c = 1 / (1 + np.exp(-z))
        else:
            raise KeyError(spec["mode"])
        return maxima(c.astype("float32").astype("f8"), 0.10)
    if t == "union":
        xs, ss = [], []
        for m, dec in spec["membres"]:
            xy, sc = maxima(carte(m, jeu, nom), 0.10 - dec)
            xs.append(xy); ss.append(sc + dec)
        xy, sc = np.concatenate(xs), np.concatenate(ss)
        o = np.argsort(-sc, kind="stable")
        xy, sc = xy[o], sc[o]
        garde = np.ones(len(xy), bool)
        for i in range(len(xy)):          # glouton : un point gardé efface ses voisins plus faibles dans le rayon
            if garde[i]:
                d2 = ((xy[i + 1:] - xy[i]) ** 2).sum(1)
                garde[i + 1:][d2 <= spec["rayon"] ** 2] = False
        return xy[garde], sc[garde]
    if t == "p90":
        _, sc = maxima(carte("v5", jeu, nom), spec.get("smin", 0.15))
        if len(sc) >= 1 and float(np.quantile(sc, spec.get("q", 0.90))) < spec["tau"]:
            xy, s = candidat(spec["petit"], jeu, nom)
            return xy, s + spec["decalage"]
        return candidat(spec["grand"], jeu, nom)
    raise KeyError(t)


def apparier(det, ver, ign, rayon=20.0):
    if not len(det):
        return 0, 0, len(ver)
    vp, libres = 0, np.ones(len(det), bool)
    if len(ver):
        d = np.sqrt(((det[:, None, :] - ver[None, :, :]) ** 2).sum(-1))
        li, co = linear_sum_assignment(np.where(d <= rayon, d, 1e6))
        ok = d[li, co] <= rayon
        vp = int(ok.sum())
        libres[li[ok]] = False
    reste = det[libres]
    n_ign = 0
    if len(ign) and len(reste):
        n_ign = int((np.sqrt(((reste[:, None, :] - ign[None, :, :]) ** 2).sum(-1)).min(1) <= rayon).sum())
    return vp, len(det) - vp - n_ign, len(ver) - vp


def mesurer(spec, jeu):
    acc = {s: np.zeros(4, "i8") for s in SEUILS}
    reels = arbres = 0
    for e in items(jeu):
        xy, sc = candidat(spec, jeu, e["nom"])
        if e["zone"] is not None:
            x0, y0, x1, y1 = e["zone"]
            g = (xy[:, 0] >= x0) & (xy[:, 0] <= x1) & (xy[:, 1] >= y0) & (xy[:, 1] <= y1)
        elif e["masque"] is not None:
            mx, my, mr = e["masque"]
            g = (xy[:, 0] - mx) ** 2 + (xy[:, 1] - my) ** 2 <= mr ** 2
        else:
            g = np.ones(len(xy), bool)
        xy, sc = xy[g], sc[g]
        reels += len(e["pts"]); arbres += e["arbres"]
        for s in SEUILS:
            d = xy[sc >= s]
            if jeu == "neg":
                acc[s] += (0, len(d), 0, len(d))
            else:
                acc[s] += (*apparier(d, e["pts"], e["ign"]), len(d))
    res = {}
    for s, (vp, fp, fn, det) in acc.items():
        if jeu == "neg":
            res[s] = dict(fp=int(fp), taux=fp / max(arbres, 1))
        else:
            p = vp / (vp + fp) if vp + fp else 0.0
            r = vp / (vp + fn) if vp + fn else 0.0
            res[s] = dict(f1=2 * p * r / (p + r) if p + r else 0.0, err=abs(det / reels - 1), det=int(det), reels=reels)
    return res


def regle_34(m):
    """Seuil qui maximise la moyenne des 5 F1 sous moins de 1 % de fausses détections sans bananier."""
    best = None
    for s in SEUILS:
        if m["neg"][s]["taux"] >= 0.01:
            continue
        moy = float(np.mean([m[j][s]["f1"] for j in JEUX]))
        if best is None or moy > best[1]:
            best = (s, moy)
    return best


def resumer(nom, m, s):
    return dict(nom=nom, seuil=s, moyenne=float(np.mean([m[j][s]["f1"] for j in JEUX])),
                f1={j: round(m[j][s]["f1"], 4) for j in JEUX}, err=float(np.mean([m[j][s]["err"] for j in JEUX])),
                fp_neg=m["neg"][s]["fp"], taux=m["neg"][s]["taux"])


V3V4 = {"type": "melange", "membres": ["v3", "v4"], "mode": "moyenne"}
V5 = {"type": "seul", "modele": "v5"}
SPECS_DEFAUT = {"v5": V5, "E5p90b_moy34_v5_d0.1": {"type": "p90", "tau": 0.55, "decalage": 0.10, "petit": V3V4, "grand": V5}}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", help="JSON {nom: spec}")
    a = ap.parse_args()
    specs = json.loads(Path(a.spec).read_text(encoding="utf-8")) if a.spec else SPECS_DEFAUT
    res, lignes = {}, []
    for nom, spec in specs.items():
        m = {j: mesurer(spec, j) for j in JEUX + ["neg"]}
        s, moy = regle_34(m)
        res[nom] = dict(regle=resumer(nom, m, s), a030=resumer(nom, m, 0.30),
                        grille={str(t): resumer(nom, m, t) for t in SEUILS})
        r = res[nom]["regle"]
        lignes.append(f"{nom:34s} seuil {s:.2f} moyenne {r['moyenne']:.4f} {r['f1']} err {r['err']:.3f} "
                      f"fausses {r['fp_neg']} ({r['taux']:.2%})")
        print(lignes[-1], flush=True)
    (OUT / "c_recalcul.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "c_recalcul.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
