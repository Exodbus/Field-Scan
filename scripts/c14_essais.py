#!/usr/bin/env python3
"""Essais CC1 à CC3 de l'agent C-piste2 (14/11) sur le réglage du comptage, à 5 cm et dégradé à 11 cm.

Code du banc importé sans modification : scripts/v6_banc_commun.py (mesure du protocole v5 : pics fenêtre 7, rayon 20 px,
appariement un-à-un, disque, zones MM), scripts/v6_banc_candidats.py, scripts/c13_banc_commun.py (garde-fou des juges,
règle 5.3), scripts/c13_banc_candidats.py (aiguillage_v2, promouvoir). Cartes lues en lecture seule dans les caches
du banc v6, de C-banc, de C-entraîneur, et dans out/comptage/nuit_1311/piste2/cache (c13h, modèles c14).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c14_essais.py <liste> [--cm11]

Résultats : out/comptage/nuit_1311/piste2/essais.json (une entrée par candidat : lignes par seuil à 5 cm, seuil retenu,
statut 5.3, moyenne à 11 cm au seuil retenu).
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import numpy as np  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

import c13_banc_candidats as cd  # noqa: E402  (importe c13_banc_commun : garde-fou + caches de la nuit)
import c13_banc_commun as cc  # noqa: E402
import v6_banc_candidats as ca  # noqa: E402

bc = cc.bc
SORTIE = RACINE / "out/comptage/nuit_1311/piste2"
MON_CACHE = SORTIE / "cache"
FICHIER = SORTIE / "essais.json"
REGLAGE = cc.REGLAGE

# ------------------------------------------------------------------------------------------------ cartes
_carte_c13 = bc.carte_cache          # déjà remplacée par c13_banc_commun (banc de la nuit, C-entraîneur, banc v6)
_MEM = {}
FORCE = {"variante": None}           # réglage dégradé : « base » est lu comme « d11 »


def carte_cache(modele, variante, nom_jeu, nom):
    if FORCE["variante"] and variante == "base":
        variante = FORCE["variante"]
    p = MON_CACHE / f"{modele}_{variante}_{nom_jeu}"
    if not p.with_suffix(".json").exists():
        if modele not in ("v3", "v4", "v5", "c13d", "c13e"):
            raise FileNotFoundError(p)          # jamais de repli silencieux pour un modèle de la piste
        return _carte_c13(modele, variante, nom_jeu, nom)
    cle = (modele, variante, nom_jeu)
    if cle not in _MEM:
        _MEM[cle] = (np.memmap(p.with_suffix(".f32"), dtype="float32", mode="r"),
                     json.loads(p.with_suffix(".json").read_text(encoding="utf-8")))
    mm, idx = _MEM[cle]
    a, h, w = idx[nom]
    return np.asarray(mm[a:a + h * w]).reshape(h, w)


bc.carte_cache = carte_cache


# ------------------------------------------------------------------------------------------------ fabriques
def f_melange(membres, poids):
    """CC1 : moyenne arithmétique pondérée des cartes de probabilité, puis pics fenêtre 7."""
    w = np.asarray(poids, "float64"); w = w / w.sum()

    def f(ctx):
        c = sum(wi * ctx.carte(m).astype("float64") for wi, m in zip(w, membres))
        return bc.pics(c.astype("float32"))
    return f


def f_e5(modele="c13e", tau=0.55, decalage=-0.10, trous=None, smin=0.15):
    """E5p90b avec un spécialiste seul dans la branche « petits » (même calcul que aiguillage_p90 de
    v6_banc_candidats avec petit_spec = seul), et en option les trous de plantation de C-banc dans cette branche
    (ancres = score rendu >= 0,30, pics bas = score rendu dans [bas, 0,30), promus à 0,30 par cd.promouvoir)."""
    def f(ctx):
        _, s5 = bc.pics(ctx.carte("v5"), bc.K_PICS, smin)
        if len(s5) >= 1 and float(np.quantile(s5, 0.90)) < tau:
            xy, s2 = bc.pics(ctx.carte(modele))
            g = s2 + decalage >= bc.SEUILS[0]
            xy, sc = xy[g], s2[g] + decalage
            if trous is not None and len(xy):
                a = sc >= 0.30
                b = (~a) & (sc >= trous["bas"])
                pm = cd.promouvoir(xy[a], xy[b], trous.get("mode", "reseau"), trous.get("tol_d", 0.30), 25.0)
                idx = np.nonzero(b)[0][pm]
                sc = sc.copy(); sc[idx] = 0.30
            return xy, sc
        return bc.pics(ctx.carte("v5"))
    return f


def nms_grille(xy, sc, alpha, ancre=0.30, n_min=8, r_max=60.0):
    """CC3 : écartement d = médiane des distances au 2e plus proche voisin des ancres (score >= ancre) ; suppression
    gloutonne par score décroissant dans un rayon alpha x d (au plus r_max px)."""
    xy, sc = np.asarray(xy, "float64").reshape(-1, 2), np.asarray(sc, "float64")
    A = xy[sc >= ancre]
    if len(A) < n_min:
        return xy, sc
    dd, _ = cKDTree(A).query(A, k=3)
    d = float(np.median(dd[:, 2]))
    r = min(alpha * d, r_max)
    if not np.isfinite(r) or r <= 0:
        return xy, sc
    return ca.supprimer_doublons(xy, sc, r)


def f_nms(base, alpha):
    def f(ctx):
        xy, sc = base(ctx)
        return nms_grille(xy, sc, alpha)
    return f


A1 = dict(tau=0.55, decalage=0.1, petits=["v3", "v4"], mode_petit="moyenne", n_min_petit=30, dens_min=200, accord_v5=0.05,
          compte_30=True, trous={"bas": 0.2, "mode": "reseau"})


def construire(nom):
    """Définitions écrites dans le journal (docs/nuit_2026-11-13/journal_c_piste2.md) avant mesure."""
    if nom == "v5":
        return ca.f_seul("v5")
    if nom == "E5p90b_c13e_d-0.1":                       # contrôle : finaliste de C-entraîneur (fabrique d'origine)
        return ca.construire("aiguillage_p90", dict(tau=0.55, decalage=-0.1, petit_spec=["seul", {"modele": "c13e"}], grand_spec=None))
    if nom == "E5p90b_c13e_d-0.1_moi":                   # contrôle : ma fabrique sans trous doit rendre le même
        return f_e5("c13e")
    if nom == "A1":                                      # contrôle : CB13_trous_b0.20_reseau de C-banc
        return cd.construire("aiguillage_v2", A1)
    if nom == "c13h":
        return ca.f_seul("c13h")
    poids = {"CC1_v5h_50": ([0.5, 0.5, 0]), "CC1_v5h_70": [0.7, 0.3, 0], "CC1_v5h_30": [0.3, 0.7, 0],
             "CC1_v5he_333": [1, 1, 1], "CC1_v5he_50": [0.5, 0.25, 0.25]}
    if nom in poids:
        w = poids[nom]
        m = [x for x, wi in zip(["v5", "c13h", "c13e"], w) if wi]
        return f_melange(m, [wi for wi in w if wi])
    if nom == "CC2_e5c13e_trous20":
        return f_e5("c13e", trous={"bas": 0.20, "mode": "reseau"})
    if nom == "CC2_e5c13e_trous25":
        return f_e5("c13e", trous={"bas": 0.25, "mode": "reseau"})
    if nom == "CC2_a1c13e":
        return cd.construire("aiguillage_v2", dict(A1, petits=["c13e"], decalage=-0.1))
    if nom.startswith("NMS35+"):                          # CC3 (alpha 0,35) appliqué à un autre candidat
        return f_nms(construire(nom[len("NMS35+"):]), 0.35)
    if nom.startswith("CC3_"):
        _, base, a = nom.split("_")
        alpha = int(a[1:]) / 100
        b = {"v5": "v5", "e5c13e": "E5p90b_c13e_d-0.1", "a1": "A1"}[base]
        return f_nms(construire(b), alpha)
    if nom.startswith("CC4_"):                            # CC4 : modèles c14 (cartes dans le cache de la piste)
        reste = nom[4:]
        if reste.startswith("e5_"):                     # E5p90b au décalage -0,10 fixé
            return f_e5(reste[3:])
        return ca.f_seul(reste)
    if nom.startswith("CC1@"):                           # « CC1@<modèle>|CC1_v5h_50 » : <modèle> à la place de c13h, mêmes poids
        modele, reste = nom[4:].split("|")
        w = poids[reste]
        m = [x for x, wi in zip(["v5", modele, "c13e"], w) if wi]
        return f_melange(m, [wi for wi in w if wi])
    raise KeyError(nom)


LISTES = {
    "controle": ["v5", "E5p90b_c13e_d-0.1", "E5p90b_c13e_d-0.1_moi", "A1"],
    "cc2": ["CC2_e5c13e_trous20", "CC2_e5c13e_trous25", "CC2_a1c13e"],
    "cc3": ["CC3_v5_a35", "CC3_v5_a45", "CC3_v5_a55"],
    "cc1": ["c13h", "CC1_v5h_50", "CC1_v5h_70", "CC1_v5h_30", "CC1_v5he_333", "CC1_v5he_50"],
}


# ------------------------------------------------------------------------------------------------ mesure
def charger():
    return json.loads(FICHIER.read_text(encoding="utf-8")) if FICHIER.exists() else {}


def sauver(E):
    tmp = FICHIER.with_suffix(".tmp")
    tmp.write_text(json.dumps(E, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, FICHIER)


def mesure5(nom):
    f = construire(nom)
    m = cc.mesurer(f, REGLAGE + ["neg"])
    L = cc.lignes(m)
    return L


def mesure11(nom, seuil, variante="d11"):
    FORCE["variante"] = variante
    try:
        f = construire(nom)
        m = cc.mesurer(f, REGLAGE)
    finally:
        FORCE["variante"] = None
    L = cc.lignes(m, neg="aucun")
    return [l for l in L if abs(l["seuil"] - seuil) < 1e-9][0], L


def main():
    noms = []
    for a in sys.argv[1:]:
        if not a.startswith("--"):
            noms += LISTES.get(a, [a])
    cm11 = "--cm11" in sys.argv
    seul11 = "--seul11" in sys.argv
    E = charger()
    for nom in noms:
        t0 = time.time()
        e = E.get(nom, {})
        if not seul11 or "lignes" not in e:
            L = mesure5(nom)
            e["lignes"] = L
            b = cc.choisir(L)
            e["retenu"] = b
        b = e["retenu"]
        if b is not None:
            ref = [l for l in (E.get("v5", {}).get("lignes") or e["lignes"]) if l["seuil"] == 0.30][0] if nom != "v5" else \
                [l for l in e["lignes"] if l["seuil"] == 0.30][0]
            e["statut"] = cc.statut(b, ref)
        if cm11 and b is not None:
            s = 0.30 if nom == "v5" else b["seuil"]
            l11, L11 = mesure11(nom, s)
            e["cm11"] = dict(seuil=s, **{k: v for k, v in l11.items() if k.startswith("f1_") or k in ("moyenne", "moy4", "err_compte")})
            e["lignes11"] = L11
        if "--cm8" in sys.argv and b is not None:
            s8 = 0.30 if nom == "v5" else b["seuil"]
            l8, L8 = mesure11(nom, s8, "d8")
            e["cm8"] = dict(seuil=s8, **{k: v for k, v in l8.items() if k.startswith("f1_") or k in ("moyenne", "moy4", "err_compte")})
        E[nom] = e
        sauver(E)
        r = b or {}
        print(f"{time.strftime('%H:%M:%S')} {nom} ({time.time() - t0:.0f} s) seuil {r.get('seuil')} : "
              + " ".join(f"{j} {r.get('f1_' + j, float('nan')):.4f}" for j in REGLAGE)
              + f" | moy {r.get('moyenne', float('nan')):.4f} moy4 {r.get('moy4', float('nan')):.4f} err {r.get('err_compte', float('nan')):.3f}"
              f" neg {r.get('fp_neg')} | finaliste {e.get('statut', {}).get('finaliste')}"
              + (f" | 11 cm {e['cm11']['moyenne']:.4f}" if 'cm11' in e else "")
              + (f" | 8 cm {e['cm8']['moyenne']:.4f}" if 'cm8' in e else ""), flush=True)


if __name__ == "__main__":
    main()
