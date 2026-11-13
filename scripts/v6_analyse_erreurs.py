#!/usr/bin/env python3
"""Analyse des erreurs du comptage (agent C-analyste, nuit du 12 au 13 novembre 2026).

Pour chaque modèle (v3, v4, v5, ou un candidat dont la carte est en cache) et chaque jeu de RÉGLAGE, à son seuil :
  - une ligne par pied annoté (mère) : retrouvé ou non, taille de boîte, distance au plus proche voisin annoté,
    distance au bord (image, disque ou zone), maximum de la carte dans le rayon de 20 px, score du meilleur pic
    dans le rayon, pic déjà pris par une autre mère (fusion), proxy de taille sur l'image (vert) ;
  - une ligne par fausse détection : score, distance à la mère la plus proche, catégorie (doublon d'un pied déjà
    retrouvé, décalée, bord, isolée).
La mesure (pics fenêtre 7, rayon 20 px, appariement un-à-un, disque, points non-mères ignorés) est celle du banc
de C-banc (scripts/v6_banc_commun.py), importée telle quelle. Les cartes viennent du cache de C-banc (lecture seule)
ou de out/comptage/analyse/cache/ (images sans bananier, recalculées ici, 3 fils).
Les juges ne sont jamais chargés ici.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/v6_analyse_erreurs.py --modeles v3 v4 v5
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import maximum_filter
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import v6_banc_commun as bc  # noqa: E402

SORTIE = RACINE / "out/comptage/analyse"
CACHE_A = SORTIE / "cache"
SEUILS_ADOPTES = {"v3": 0.20, "v4": 0.40, "v5": 0.30}
JEUX = ["dense", "plantain", "jeunes", "mm"]
INTERDITS = {"segmento", "cg", "banano", "neg_test"}
ENSEMBLES = {"dense": "val_dense_bv", "plantain": "val_plantain", "jeunes": "val_jeunes", "btd_val": "test_espace"}
# moitié validation de banana_tree_detection (découpage v6, agent C-découpage, « DÉCOUPAGE PRÊT » à 22:48) :
# correspondance tuile v5 (btd_NNNN, ordre des lignes btd du découpage v5, effectifs vérifiés identiques sur les 396)
# -> groupe btd_val du découpage v6, écrite dans out/comptage/analyse/btd_val_tuiles.csv
BTD_VAL = SORTIE / "btd_val_tuiles.csv"


def items_complets(nom_jeu):
    """Comme bc.jeu, avec en plus : taille de boîte des mères, tous les points annotés (pour le voisinage), taille image."""
    assert nom_jeu not in INTERDITS
    D = bc.D
    if nom_jeu in ENSEMBLES:
        T, O = pd.read_csv(D / "tuiles.csv"), pd.read_csv(D / "objets.csv")
        T = T[T.ensemble == ENSEMBLES[nom_jeu]]
        if nom_jeu == "btd_val":
            T = T[T.image_path.isin(set(pd.read_csv(BTD_VAL).tuile))]
        O = {k: g for k, g in O[O.image_path.isin(set(T.image_path))].groupby("image_path")}
        out = []
        for r in T.itertuples():
            o = O.get(r.image_path)
            masque = None if np.isnan(r.masque_r) else (r.masque_cx, r.masque_cy, r.masque_r)
            if o is None:
                o = pd.DataFrame(columns=["cx", "cy", "taille", "type"])
            m = o[o.type == "mere"]
            xy = m[["cx", "cy"]].to_numpy("float64")
            g = bc.dans_masque(xy, masque)
            out.append(dict(nom=r.image_path, chemin=str(D / "images" / r.image_path), pts=xy[g],
                            taille=m.taille.to_numpy("float64")[g],
                            ign=o[o.type != "mere"][["cx", "cy"]].to_numpy("float64"),
                            tous=o[["cx", "cy"]].to_numpy("float64"), masque=masque, zone=None,
                            l=int(r.largeur), h=int(r.hauteur)))
        return out
    if nom_jeu == "mm":
        P, Z = pd.read_csv(D / "mm/points.csv"), pd.read_csv(D / "mm/zones.csv")
        out = []
        for z in Z.itertuples():
            p = P[P.zone_id == z.zone_id]
            from PIL import Image
            with Image.open(D / "mm/images" / z.image_path) as im:
                l, h = im.size
            pts = p[p.type == "mere"][["x", "y"]].to_numpy("float64")
            out.append(dict(nom=z.image_path, chemin=str(D / "mm/images" / z.image_path), pts=pts,
                            taille=np.full(len(pts), np.nan), ign=p[p.type != "mere"][["x", "y"]].to_numpy("float64"),
                            tous=p[["x", "y"]].to_numpy("float64"), masque=None, zone=(z.x0, z.y0, z.x1, z.y1), l=l, h=h))
        return out
    raise KeyError(nom_jeu)


def dist_bord(xy, e):
    """Distance (px à 5 cm) au bord de la zone comptée : disque si présent, sinon zone, sinon image."""
    if not len(xy):
        return np.zeros(0)
    if e["masque"] is not None:
        mx, my, mr = e["masque"]
        d = mr - np.hypot(xy[:, 0] - mx, xy[:, 1] - my)
        d_img = np.minimum.reduce([xy[:, 0], xy[:, 1], e["l"] - xy[:, 0], e["h"] - xy[:, 1]])
        return np.minimum(d, d_img)
    if e["zone"] is not None:
        x0, y0, x1, y1 = e["zone"]
        return np.minimum.reduce([xy[:, 0] - x0, xy[:, 1] - y0, x1 - xy[:, 0], y1 - xy[:, 1]])
    return np.minimum.reduce([xy[:, 0], xy[:, 1], e["l"] - xy[:, 0], e["h"] - xy[:, 1]])


def dans_compte(xy, e):
    if e["zone"] is not None:
        x0, y0, x1, y1 = e["zone"]
        return (xy[:, 0] >= x0) & (xy[:, 0] <= x1) & (xy[:, 1] >= y0) & (xy[:, 1] <= y1)
    return bc.dans_masque(xy, e["masque"])


def apparier(det, certains, rayon=bc.RAYON_PX):
    """Même appariement que bc.compter, mais rend les couples (indice détection -> indice mère)."""
    couples = {}
    if len(det) and len(certains):
        d = cdist(det, certains)
        li, co = linear_sum_assignment(np.where(d <= rayon, d, 1e6))
        for a, b in zip(li, co):
            if d[a, b] <= rayon:
                couples[int(a)] = int(b)
    return couples


def proxy_vert(img, xy):
    """[H] Rayon (px) du plant estimé sur l'image : plus grand rayon r (4 à 60 px) où la part de pixels « verts »
    (ExG = 2G - R - B > 20) dans l'anneau r-4..r reste au-dessus de 0,5. NaN si le centre n'est pas vert."""
    if not len(xy):
        return np.zeros(0)
    f = img.astype("int16")
    vert = (2 * f[..., 1] - f[..., 0] - f[..., 2]) > 20
    h, w = vert.shape
    yy, xx = np.mgrid[-60:61, -60:61]
    rr = np.hypot(xx, yy)
    res = []
    for x, y in xy:
        xi, yi = int(round(x)), int(round(y))
        x0, x1, y0, y1 = max(0, xi - 60), min(w, xi + 61), max(0, yi - 60), min(h, yi + 61)
        sous = vert[y0:y1, x0:x1]
        r = rr[(y0 - yi + 60):(y1 - yi + 60), (x0 - xi + 60):(x1 - xi + 60)]
        rayon = np.nan
        for rext in range(4, 61, 4):
            a = (r >= rext - 4) & (r < rext)
            if not a.any():
                break
            if sous[a].mean() > 0.5:
                rayon = rext
            else:
                break
        res.append(rayon)
    return np.array(res, "float64")


def carte(modele, variante, nom_jeu, nom):
    # mon cache d'abord (btd_val : mes noms de tuiles v5 ; C-banc lit l'archive v6, autres noms)
    p = bc.chemin_cache(modele, variante, nom_jeu)
    q = CACHE_A / f"{modele}_{variante}_{nom_jeu}"
    if p.with_suffix(".json").exists() and not q.with_suffix(".json").exists():
        return bc.carte_cache(modele, variante, nom_jeu, nom)
    if q.with_suffix(".json").exists():
        cle = ("A", modele, variante, nom_jeu)
        if cle not in bc._MEM:
            bc._MEM[cle] = (np.memmap(q.with_suffix(".f32"), dtype="float32", mode="r"),
                            json.loads(q.with_suffix(".json").read_text(encoding="utf-8")))
        mm, idx = bc._MEM[cle]
        a, h, w = idx[nom]
        return np.asarray(mm[a:a + h * w]).reshape(h, w)
    raise FileNotFoundError(f"pas de carte pour {modele} {variante} {nom_jeu}")


def analyser(modele, variante, nom_jeu, seuil, img_cache):
    lignes_p, lignes_d = [], []
    for e in items_complets(nom_jeu):
        c = carte(modele, variante, nom_jeu, e["nom"])
        f = bc.ECHELLES.get(variante, 1.0)      # variantes d'échelle : pics à la résolution propre, ramenés à 5 cm
        # tous les pics au-dessus de 0,02 (pour le profil des oubliés), même fenêtre que la mesure
        xy_all, sc_all = bc.pics(c, bc.K_PICS, 0.02, echelle=f)
        g = dans_compte(xy_all, e) if len(xy_all) else np.zeros(0, bool)
        xy_all, sc_all = xy_all[g], sc_all[g]
        sel = sc_all >= seuil
        det, sdet = xy_all[sel], sc_all[sel]
        couples = apparier(det, e["pts"])
        retrouve = np.zeros(len(e["pts"]), bool)
        retrouve[list(couples.values())] = True
        # voisinage annoté (tous points, y compris hors disque et non-mères)
        arbre = cKDTree(e["tous"]) if len(e["tous"]) > 1 else None
        if arbre is not None and len(e["pts"]):
            dd, _ = arbre.query(e["pts"], k=2)
            ppv = dd[:, 1]
        else:
            ppv = np.full(len(e["pts"]), np.nan)
        db = dist_bord(e["pts"], e)
        if e["nom"] not in img_cache:
            img_cache[e["nom"]] = bc.lire(e["chemin"])
        img = img_cache[e["nom"]]
        rv = proxy_vert(img, e["pts"])
        # maximum de la carte dans le rayon (cellules au quart)
        H, W = c.shape
        jj, ii = np.mgrid[0:H, 0:W]
        cx, cy = (ii + 0.5) * bc.STRIDE / f, (jj + 0.5) * bc.STRIDE / f
        det_prises = {k for k in couples}
        for k, (x, y) in enumerate(e["pts"]):
            j0, j1 = max(0, int((y - 24) * f // 4)), min(H, int((y + 24) * f // 4) + 1)
            i0, i1 = max(0, int((x - 24) * f // 4)), min(W, int((x + 24) * f // 4) + 1)
            fen = c[j0:j1, i0:i1]
            dd2 = np.hypot(cx[j0:j1, i0:i1] - x, cy[j0:j1, i0:i1] - y) <= bc.RAYON_PX
            vmax = float(fen[dd2].max()) if dd2.any() else 0.0
            # meilleur pic (≥ 0,02) dans le rayon
            if len(xy_all):
                dp = np.hypot(xy_all[:, 0] - x, xy_all[:, 1] - y)
                ok = dp <= bc.RAYON_PX
                pic = float(sc_all[ok].max()) if ok.any() else 0.0
            else:
                pic = 0.0
            # détection au-dessus du seuil dans le rayon, prise par une autre mère
            fusion = False
            if not retrouve[k] and len(det):
                dp = np.hypot(det[:, 0] - x, det[:, 1] - y)
                for a in np.nonzero(dp <= bc.RAYON_PX)[0]:
                    if int(a) in det_prises:
                        fusion = True
            lignes_p.append(dict(modele=modele, variante=variante, jeu=nom_jeu, image=e["nom"], x=x, y=y,
                                 retrouve=bool(retrouve[k]), taille=e["taille"][k], ppv=ppv[k], bord=db[k],
                                 rayon_vert=rv[k], vmax=vmax, pic=pic, fusion=fusion))
        # fausses détections
        pris_m = set(couples.values())
        for a in range(len(det)):
            if a in couples:
                continue
            x, y = det[a]
            if len(e["ign"]) and np.hypot(e["ign"][:, 0] - x, e["ign"][:, 1] - y).min() <= bc.RAYON_PX:
                cat = "rejet_annote_ignore"
                lignes_d.append(dict(modele=modele, variante=variante, jeu=nom_jeu, image=e["nom"], x=x, y=y,
                                     score=sdet[a], d_mere=np.nan, cat=cat, bord=dist_bord(det[a:a + 1], e)[0]))
                continue
            if len(e["pts"]):
                dm = np.hypot(e["pts"][:, 0] - x, e["pts"][:, 1] - y)
                kk = int(dm.argmin()); d_m = float(dm[kk])
            else:
                kk, d_m = -1, np.inf
            # mères hors disque (tous points) : une détection près du bord peut viser un plant coupé par le disque
            d_tous = float(np.hypot(e["tous"][:, 0] - x, e["tous"][:, 1] - y).min()) if len(e["tous"]) else np.inf
            bd = dist_bord(det[a:a + 1], e)[0]
            if d_m <= 2 * bc.RAYON_PX and kk in pris_m:
                cat = "doublon"            # deuxième pic sur un pied déjà retrouvé
            elif d_m <= 2 * bc.RAYON_PX:
                cat = "decalee"            # près d'une mère non retrouvée, mais à plus de 20 px
            elif bd <= bc.RAYON_PX:
                cat = "bord"
            elif d_tous <= 2 * bc.RAYON_PX:
                cat = "annote_hors_zone"
            else:
                cat = "isolee"             # rien d'annoté à moins de 40 px : herbe, rejet non annoté, autre arbre, oubli d'annotation
            lignes_d.append(dict(modele=modele, variante=variante, jeu=nom_jeu, image=e["nom"], x=x, y=y,
                                 score=sdet[a], d_mere=d_m, cat=cat, bord=bd))
    return pd.DataFrame(lignes_p), pd.DataFrame(lignes_d)


def cache_negatifs(modele, fils=3):
    """Cartes des images sans bananier de validation (val_negatifs), dans out/comptage/analyse/cache/."""
    q = CACHE_A / f"{modele}_base_neg"
    if q.with_suffix(".json").exists() or bc.chemin_cache(modele, "base", "neg").with_suffix(".json").exists():
        return
    CACHE_A.mkdir(parents=True, exist_ok=True)
    sess = bc.session(modele, fils)
    blocs, index, pos = [], {}, 0
    for e in bc.jeu("neg"):
        c = bc.cartes_image(sess, bc.lire(e["chemin"]), "base")["base"]
        blocs.append(c.ravel()); index[e["nom"]] = [pos, c.shape[0], c.shape[1]]; pos += c.size
    np.concatenate(blocs).astype("float32").tofile(q.with_suffix(".f32"))
    q.with_suffix(".json").write_text(json.dumps(index), encoding="utf-8")


def analyser_neg(modele, seuil):
    lignes = []
    for e in bc.jeu("neg"):
        c = carte(modele, "base", "neg", e["nom"])
        xy, sc = bc.pics(c, bc.K_PICS, seuil)
        for (x, y), s in zip(xy, sc):
            lignes.append(dict(modele=modele, image=e["nom"], groupe=e["nom"].split("_")[0], x=x, y=y, score=s,
                               n_arbres=e["n_autres"]))
    return pd.DataFrame(lignes)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--modeles", nargs="+", default=["v3", "v4", "v5"])
    ap.add_argument("--variante", default="base")
    ap.add_argument("--jeux", nargs="+", default=JEUX)
    ap.add_argument("--seuils", nargs="*", type=float, default=None)
    ap.add_argument("--tag", default="")
    ap.add_argument("--neg", action="store_true", help="analyser aussi les images sans bananier (cache long à calculer)")
    a = ap.parse_args()
    assert not set(a.jeux) & INTERDITS
    SORTIE.mkdir(parents=True, exist_ok=True)
    img_cache = {}
    P, Dd, N = [], [], []
    for i, m in enumerate(a.modeles):
        s = a.seuils[i] if a.seuils else SEUILS_ADOPTES[m]
        for j in a.jeux:
            t0 = time.time()
            p, d = analyser(m, a.variante, j, s, img_cache)
            p["seuil"] = s; d["seuil"] = s
            P.append(p); Dd.append(d)
            print(f"{time.strftime('%H:%M:%S')} {m} {a.variante} {j} seuil {s} : {p.retrouve.sum()}/{len(p)} retrouvés, "
                  f"{len(d)} fausses ({time.time() - t0:.0f} s)", flush=True)
        if a.variante == "base" and a.neg:
            cache_negatifs(m)
            n = analyser_neg(m, s); n["seuil"] = s; N.append(n)
            print(f"{time.strftime('%H:%M:%S')} {m} sans bananier : {len(n)} fausses", flush=True)
    tag = a.tag or a.variante
    pd.concat(P).to_csv(SORTIE / f"pieds_{tag}.csv", index=False)
    pd.concat(Dd).to_csv(SORTIE / f"fausses_{tag}.csv", index=False)
    if N:
        pd.concat(N).to_csv(SORTIE / f"neg_{tag}.csv", index=False)
