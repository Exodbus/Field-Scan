#!/usr/bin/env python3
"""Contrôleur, nuit du 13/11 : recalcul INDÉPENDANT des candidats de comptage sur le réglage (plan, section 5.3).

Code repris de mon prédécesseur (scripts/controle_nuit_c_recalcul.py, écrit par le Contrôleur, sans code des agents) :
pics 7 x 7, appariement un-à-un rayon 20 px, points non-mères ignorés, disque DJI, zones MM ; fausses détections sans
bananier = fausses / autres arbres (val_negatifs). Cartes lues dans les caches (banc v6, banc de cette nuit pour les
images dégradées, mes propres cartes ONNX pour les réseaux neufs). Garde-fou : aucun juge (segmento, cg, banano,
test_*) ni test vierge (banana_trees_kp).
Ajouts : aiguillage étendu (densité, espacement, accord, seuil propre), règle 5.3 dans les deux lectures du v5
(0,30 en service ; 0,20 = seuil que la règle donne au v5), finaliste « résolution » (variante d'images dégradées).
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_1311_c_recalcul.py --spec specs.json [--d11 variante]
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
OUT = RACINE / "out/controle_nuit_1311"
CACHE13 = RACINE / "out/comptage/nuit_1311/banc/cache"
CACHE_MOI = OUT / "cache_c"
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


DEGRADE = None          # "d11" / "d8" : réglage dégradé (cartes du cache de la nuit)
_NATIF = {}


def cm_natif(jeu, nom):
    """Résolution d'origine (cm/px) : 5 x facteur de tuiles.csv (ensembles de réglage seulement) ; MM : 2 ; dégradé : 11 ou 8."""
    if DEGRADE:
        return float(DEGRADE[1:])
    if jeu == "mm":
        return 2.0
    if not _NATIF:
        for D in (D5, D6):
            T = pd.read_csv(D / "tuiles.csv", usecols=["image_path", "ensemble", "facteur"])
            T = T[T.ensemble.isin(["val_dense_bv", "val_plantain", "val_jeunes", "val_negatifs", "val_espace"])]
            _NATIF.update(dict(zip(T.image_path, 5.0 * T.facteur)))
    return _NATIF[nom]


def carte(modele, jeu, nom, variante="base"):
    if DEGRADE:
        variante = {"base": DEGRADE, "sh": DEGRADE + "sh"}.get(variante, variante)
    cle = (modele, variante, jeu)
    if cle not in _C:
        p = CACHE / f"{modele}_{variante}_{jeu}"
        for base in (CACHE_MOI, CACHE13):      # mes cartes (modèles neufs), puis cache de la nuit (images dégradées)
            if (base / f"{modele}_{variante}_{jeu}.json").exists():
                p = base / f"{modele}_{variante}_{jeu}"
                break
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
        return maxima(carte(spec["modele"], jeu, nom, spec.get("variante", "base")), spec.get("plancher", 0.10))
    if t == "melange":
        cs = [carte(m, jeu, nom, spec.get("variante", "base")) for m in spec["membres"]]
        w = np.asarray(spec.get("poids", [1.0] * len(cs)), "f8"); w /= w.sum()
        if spec["mode"] == "moyenne":
            c = sum(a * b for a, b in zip(w, cs))
        elif spec["mode"] == "geometrique":
            c = np.exp(sum(a * np.log(np.maximum(b, 1e-6)) for a, b in zip(w, cs)))
        elif spec["mode"] == "minimum":
            c = np.min(cs, 0)
        elif spec["mode"] == "maximum":
            c = np.max(cs, 0)
        elif spec["mode"] == "logit":
            z = sum(a * np.log(np.clip(b, 1e-6, 1 - 1e-6) / (1 - np.clip(b, 1e-6, 1 - 1e-6))) for a, b in zip(w, cs))
            c = 1 / (1 + np.exp(-z))
        else:
            raise KeyError(spec["mode"])
        return maxima(c.astype("float32").astype("f8"), spec.get("plancher", 0.10))
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
    if t == "resolution":
        cm = cm_natif(jeu, nom)
        if cm < spec.get("cm_bascule", 8):
            return candidat(spec["cinq"], jeu, nom)
        if spec.get("dens_min") is not None:
            c5 = carte("v5", jeu, nom)
            xy5, _ = maxima(c5, 0.15)
            if len(xy5) < 5 or len(xy5) / (c5.size * 16 * 0.0025 / 1e4) < spec["dens_min"]:
                return maxima(c5, 0.10)
        xy, sc = candidat(spec["grossier"], jeu, nom)
        return xy, sc + spec.get("beta_par_cm", 0.0) * (cm - 5)
    if t == "p90v2":
        return aiguillage_v2(spec, jeu, nom)
    if t == "p90":
        var = spec.get("variante", "base")
        c5 = carte(spec.get("signal", "v5"), jeu, nom, var)
        xy5, sc = maxima(c5, spec.get("smin", 0.15))
        vers = len(sc) >= max(spec.get("n_min", 1), 1) and float(np.quantile(sc, spec.get("q", 0.90))) < spec["tau"]
        if vers and spec.get("dens_min") is not None:   # densité des pics du signal (par ha, 5 cm/px, grille au quart)
            ha = c5.size * 16 * 0.0025 / 1e4
            vers = len(xy5) >= 5 and len(xy5) / ha >= spec["dens_min"]
        if vers and spec.get("esp_max") is not None:     # espacement médian au plus proche voisin (px à 5 cm)
            d = np.sqrt(((xy5[:, None] - xy5[None]) ** 2).sum(-1)); np.fill_diagonal(d, np.inf)
            vers = len(xy5) >= 5 and float(np.median(d.min(1))) <= spec["esp_max"]
        if vers:
            xy, s = candidat(spec["petit"], jeu, nom)
            if spec.get("accord") is not None and len(xy):   # carte du signal >= a dans le carré 3 x 3 du point
                from scipy.ndimage import maximum_filter
                m = maximum_filter(c5, size=3, mode="constant")
                j = np.clip((xy[:, 1] / 4).astype(int), 0, c5.shape[0] - 1); i = np.clip((xy[:, 0] / 4).astype(int), 0, c5.shape[1] - 1)
                g = m[j, i] >= spec["accord"]; xy, s = xy[g], s[g]
            if spec.get("seuil_petit") is not None:          # seuil propre fixe : gardé à tout seuil de la grille
                g = s >= spec["seuil_petit"]
                return xy[g], np.ones(int(g.sum()))
            return xy, s + spec.get("decalage", 0.0)
        return candidat(spec["grand"], jeu, nom)
    raise KeyError(t)


def _max3(c, xy):
    """Valeur maximale de la carte (grille au quart) dans le carré 3 x 3 de la cellule de chaque point."""
    from scipy.ndimage import maximum_filter
    m = maximum_filter(c, size=3, mode="constant")
    j = np.clip((xy[:, 1] / 4).astype(int), 0, c.shape[0] - 1)
    i = np.clip((xy[:, 0] / 4).astype(int), 0, c.shape[1] - 1)
    return m[j, i]


def places_vides(A, P, tol=0.30):
    """Géométrie de plantation (réécrite d'après la description de C-banc, journal 23:51 et 23:58) :
    d = médiane des distances au plus proche voisin des ancres A ; directions du réseau = vecteurs au plus proche voisin
    ramenés au demi-plan x >= 0, regroupés par angle (classes de 10°), les deux plus fréquentes (au moins 3 vecteurs,
    directions écartées de plus de 30°), vecteur médian de la classe ; places prédites A +/- v à plus de 0,5 d de toute
    ancre ; un pic bas de P est promu s'il est à plus de 0,5 d de toute ancre et à au plus tol x d d'une place prédite."""
    from scipy.spatial import cKDTree
    out = np.zeros(len(P), bool)
    if len(A) < 6 or not len(P):
        return out
    arbre = cKDTree(A)
    dist, idx = arbre.query(A, k=2)
    d = float(np.median(dist[:, 1]))
    if not d > 0:
        return out
    V = A[idx[:, 1]] - A
    V[V[:, 0] < 0] *= -1
    ang = np.degrees(np.arctan2(V[:, 1], V[:, 0])) % 180
    classe = np.minimum((ang // 10).astype(int), 17)
    eff = np.bincount(classe, minlength=18)
    dirs = []
    for b in np.argsort(-eff, kind="stable")[:4]:
        if eff[b] < 3:
            continue
        v = np.median(V[classe == b], 0)
        a = np.degrees(np.arctan2(v[1], v[0]))
        if all(abs(a - np.degrees(np.arctan2(w[1], w[0]))) % 180 > 30 for w in dirs):
            dirs.append(v)
        if len(dirs) == 2:
            break
    if not dirs:
        return out
    pred = np.concatenate([A + sg * v for v in dirs for sg in (1, -1)])
    pred = pred[arbre.query(pred, k=1)[0] > 0.5 * d]
    if not len(pred):
        return out
    loin = arbre.query(P, k=1)[0] > 0.5 * d
    return loin & (cKDTree(pred).query(P, k=1)[0] <= tol * d)


def aiguillage_v2(spec, jeu, nom):
    """Aiguillage de C-banc (CB1 + CB3), réécrit : signal p90 du v5 (pics >= 0,15) < tau ; densité des pics du v5
    >= dens_min /ha (et au moins 5) ; branche « petits » = moyenne v3 + v4, tous les maxima locaux, gardés si la carte
    du v5 vaut >= accord dans le carré 3 x 3, score + décalage ; trous : pics de score rendu dans [bas, 0,30) promus à
    0,30 s'ils tombent sur une place vide du réseau des ancres (score rendu >= 0,30) ; l'image n'est aiguillée que si la
    branche porte au moins n_min_petit points de score rendu >= 0,30. Sinon : v5 seul."""
    c5 = carte("v5", jeu, nom)
    xy5, s5 = maxima(c5, 0.15)
    vers = len(s5) >= 1 and float(np.quantile(s5, 0.90)) < spec["tau"]
    if vers and spec.get("dens_min") is not None:
        ha = c5.size * 16 * 0.0025 / 1e4
        vers = len(xy5) >= 5 and len(xy5) / ha >= spec["dens_min"]
    if vers:
        cp = np.mean([carte(m, jeu, nom) for m in spec.get("petits", ["v3", "v4"])], 0)
        xy, sc = maxima(cp.astype("float32").astype("f8"), 0.10 - spec["decalage"])
        if spec.get("accord") is not None and len(xy):
            g = _max3(c5, xy) >= spec["accord"]
            xy, sc = xy[g], sc[g]
        sc = sc + spec["decalage"]
        if spec.get("trous_bas") is not None and len(xy):
            anc = sc >= 0.30
            bas = (~anc) & (sc >= spec["trous_bas"])
            pm = places_vides(xy[anc], xy[bas], spec.get("trous_tol", 0.30))
            sc = sc.copy(); sc[np.nonzero(bas)[0][pm]] = 0.30
        if int((sc >= 0.30).sum()) >= spec.get("n_min_petit", 0):
            return xy, sc
    return maxima(c5, 0.10)


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



ANCIENS = ["dense", "plantain", "jeunes", "mm"]


def ligne(m, s, jeux=JEUX):
    f = {j: m[j][s]["f1"] for j in jeux}
    return dict(seuil=s, f1=f, moyenne=float(np.mean(list(f.values()))), moy4=float(np.mean([f[j] for j in ANCIENS])),
                err=float(np.mean([m[j][s]["err"] for j in jeux])), fp=m["neg"][s]["fp"] if "neg" in m else None,
                taux=m["neg"][s]["taux"] if "neg" in m else None)


def regle_seuil(m):
    """Plan 5.3 : seuil qui maximise la moyenne des 5 F1 sous val_negatifs < 1 %."""
    el = [ligne(m, s) for s in SEUILS if m["neg"][s]["taux"] < 0.01]
    return max(el, key=lambda l: l["moyenne"]) if el else None


def finaliste(b, ref):
    c = dict(c1=b["moyenne"] > ref["moyenne"] + 0.010 and b["moy4"] >= ref["moy4"],
             c2=min(b["f1"][j] - ref["f1"][j] for j in JEUX) >= -0.020,
             c3=b["err"] <= ref["err"], c4=b["taux"] < 0.01)
    return all(c.values()), c


def finaliste_resolution(b, ref, b11, ref11):
    c = dict(r1=b11["moyenne"] >= ref11["moyenne"] + 0.030, r2=b["moyenne"] >= ref["moyenne"] - 0.005,
             c2=min(b["f1"][j] - ref["f1"][j] for j in JEUX) >= -0.020, c3=b["err"] <= ref["err"], c4=b["taux"] < 0.01)
    return all(c.values()), c


def fmt(nom, l):
    return (f"{nom:40s} seuil {l['seuil']:.2f} moy5 {l['moyenne']:.4f} moy4 {l['moy4']:.4f} "
            + " ".join(f"{j} {v:.4f}" for j, v in l["f1"].items())
            + f" err {l['err']:.3f}" + (f" fausses {l['fp']} ({l['taux']:.2%})" if l.get("fp") is not None else ""))


V5 = {"type": "seul", "modele": "v5"}
V3V4 = {"type": "melange", "membres": ["v3", "v4"], "mode": "moyenne"}
SPECS_DEFAUT = {"v5": V5, "E5p90b_moy34_v5_d0.1": {"type": "p90", "tau": 0.55, "decalage": 0.10, "petit": V3V4, "grand": V5}}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", help="JSON {nom: spec}")
    ap.add_argument("--sortie", default="c_recalcul")
    ap.add_argument("--degrade", help="d11 ou d8 : mesure aussi le réglage dégradé, au seuil choisi à 5 cm")
    a = ap.parse_args()
    specs = json.loads(Path(a.spec).read_text(encoding="utf-8")) if a.spec else SPECS_DEFAUT
    specs = {"v5": V5, **specs}
    res, lignes = {}, []
    for nom, spec in specs.items():
        cle = json.dumps(spec, sort_keys=True)  # 5 cm
        memo = OUT / "c_memo.json"
        M = json.loads(memo.read_text(encoding="utf-8")) if memo.exists() else {}
        if cle in M:
            m = {j: {float(s): v for s, v in r.items()} for j, r in M[cle].items()}
        else:
            m = {j: mesurer(spec, j) for j in JEUX + ["neg"]}
            M[cle] = {j: {str(s): v for s, v in r.items()} for j, r in m.items()}
            memo.write_text(json.dumps(M, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
        b = regle_seuil(m)
        res[nom] = dict(regle=b, grille={str(s): ligne(m, s) for s in SEUILS})
        lignes.append(fmt(nom, b)); print(lignes[-1], flush=True)
    if a.degrade:
        DEGRADE = a.degrade
        for nom, spec in specs.items():
            cle = a.degrade + "|" + json.dumps(spec, sort_keys=True)
            memo = OUT / "c_memo.json"
            M = json.loads(memo.read_text(encoding="utf-8")) if memo.exists() else {}
            if cle in M:
                m = {j: {float(s): v for s, v in r.items()} for j, r in M[cle].items()}
            else:
                m = {j: mesurer(spec, j) for j in JEUX}
                M[cle] = {j: {str(s): v for s, v in r.items()} for j, r in m.items()}
                memo.write_text(json.dumps(M, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
            res[nom]["degrade"] = {str(s): ligne(m, s) for s in SEUILS}
            s5 = res[nom]["regle"]["seuil"]
            lignes.append(f"   {a.degrade} au seuil choisi à 5 cm : " + fmt(nom, res[nom]["degrade"][str(s5)]))
            print(lignes[-1], flush=True)
        DEGRADE = None
    r030, r020 = res["v5"]["grille"]["0.3"], res["v5"]["regle"]
    for nom in specs:
        if nom == "v5":
            continue
        b = res[nom]["regle"]
        f30, d30 = finaliste(b, r030)
        f20, d20 = finaliste(b, r020)
        res[nom].update(finaliste_v5_030=[f30, d30], finaliste_v5_regle=[f20, d20])
        lignes.append(f"   {nom} : finaliste contre v5 0,30 {f30} {d30} ; contre v5 à son seuil 5.3 ({r020['seuil']}) {f20} {d20}")
        if a.degrade:
            b11 = res[nom]["degrade"][str(b["seuil"])]
            for sv in ("0.3", "0.2"):
                fr, dr = finaliste_resolution(b, r030, b11, res["v5"]["degrade"][sv])
                res[nom][f"resolution_v5d_{sv}"] = [fr, dr]
                lignes.append(f"   {nom} : finaliste « résolution » (v5 dégradé lu à {sv}, 5 cm contre v5 0,30) {fr} {dr}")
        print(lignes[-1], flush=True)
    (OUT / f"{a.sortie}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
    (OUT / f"{a.sortie}.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
