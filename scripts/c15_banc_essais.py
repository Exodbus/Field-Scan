#!/usr/bin/env python3
"""Essais du comptage sans entraînement de l'agent C-banc (15/11) : familles G, S, W, T, sur le réglage à 5 et 11 cm.

Code importé sans modification : scripts/v6_banc_commun.py (mesure du protocole v5), scripts/c13_banc_commun.py
(garde-fou des juges, règle 5.3), scripts/c13_banc_candidats.py (promouvoir), scripts/c14_essais.py (fabriques de
C-piste2 et lecture des cartes de c13h, lecture seule ; son essais.json n'est jamais réécrit).
Règles écrites avant calcul : docs/journee_2026-11-15/journal_c_banc.md.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c15_banc_essais.py <noms> [--cm11]

Résultats : out/comptage/jour_1511/banc/essais.json.
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import cv2  # noqa: E402
import numpy as np  # noqa: E402

import c14_essais as ce  # noqa: E402  (installe sa lecture des cartes ; importe c13_banc_commun et c13_banc_candidats)

cc, bc, cd = ce.cc, ce.bc, ce.cd
REGLAGE = cc.REGLAGE
SORTIE = RACINE / "out/comptage/jour_1511/banc"
CACHE = SORTIE / "cache"
FICHIER = SORTIE / "essais.json"
STATS = {}                     # (variante, jeu) -> [images où c13h est calculé, images]

_MEM = {}


def carte_reduite(ctx, variante):
    """Carte de c13h calculée sur l'image réduite (cache de c15_banc_cache.py), ramenée sur la grille du v5."""
    if ce.FORCE["variante"] == "d11":
        variante = "d11" + variante
    p = CACHE / f"c13h_{variante}_{ctx.nom_jeu}"
    cle = (variante, ctx.nom_jeu)
    if cle not in _MEM:
        _MEM[cle] = (np.memmap(p.with_suffix(".f32"), dtype="float32", mode="r"),
                     json.loads(p.with_suffix(".json").read_text(encoding="utf-8")))
    mm, idx = _MEM[cle]
    a, h, w = idx[ctx.nom]
    c = np.asarray(mm[a:a + h * w]).reshape(h, w)
    b = ctx.carte("v5")
    return cv2.resize(c, (b.shape[1], b.shape[0]), interpolation=cv2.INTER_LINEAR)


def compte(ctx, calcule):
    k = (ce.FORCE["variante"] or "base", ctx.nom_jeu)
    s = STATS.setdefault(k, [0, 0])
    s[0] += int(calcule); s[1] += 1


def melange(c5, ch, w5=0.5):
    return (w5 * c5.astype("float64") + (1 - w5) * ch.astype("float64")).astype("float32")


def f_porte(tau, reduite=None):
    """Famille G : mélange 0,5 / 0,5 seulement si le v5 hésite (90e centile des scores de ses pics >= 0,15 < tau)."""
    def f(ctx):
        c5 = ctx.carte("v5")
        _, s5 = bc.pics(c5, bc.K_PICS, 0.15)
        if len(s5) >= 1 and float(np.quantile(s5, 0.90)) < tau:
            compte(ctx, True)
            ch = carte_reduite(ctx, reduite) if reduite else ctx.carte("c13h")
            return bc.pics(melange(c5, ch))
        compte(ctx, False)
        return bc.pics(c5)
    return f


def f_reduit(variante, w5=0.5):
    """Famille S : c13h calculé sur l'image réduite, mélangé au v5."""
    def f(ctx):
        compte(ctx, True)
        return bc.pics(melange(ctx.carte("v5"), carte_reduite(ctx, variante), w5))
    return f


def f_logit(w5=0.5):
    def f(ctx):
        compte(ctx, True)
        p5 = np.clip(ctx.carte("v5").astype("float64"), 1e-6, 1 - 1e-6)
        ph = np.clip(ctx.carte("c13h").astype("float64"), 1e-6, 1 - 1e-6)
        z = w5 * np.log(p5 / (1 - p5)) + (1 - w5) * np.log(ph / (1 - ph))
        return bc.pics((1 / (1 + np.exp(-z))).astype("float32"))
    return f


def f_trous(base, bas=0.20):
    """Famille T : pics bas de la base dans les places vides de la grille, promus à 0,30 (même règle qu'A1)."""
    def f(ctx):
        xy, sc = base(ctx)
        xy, sc = np.asarray(xy, "float64").reshape(-1, 2), np.asarray(sc, "float64").copy()
        if len(xy):
            a = sc >= 0.30
            b = (~a) & (sc >= bas)
            pm = cd.promouvoir(xy[a], xy[b], "reseau", 0.30, 25.0)
            sc[np.nonzero(b)[0][pm]] = 0.30
        return xy, sc
    return f


def blocs_hesitants(c5, taille, haut=0.60, bas=0.10):
    """Famille B : masque (sur la grille au quart) des blocs carrés de `taille` cases qui contiennent un pic du v5
    (fenêtre 7, score >= bas) de score < haut. Rend aussi (blocs hésitants, blocs)."""
    xy, s = bc.pics(c5, bc.K_PICS, bas)
    H, W = c5.shape
    nb = ((H + taille - 1) // taille, (W + taille - 1) // taille)
    h = np.zeros(nb, bool)
    if len(s):
        j = (xy[:, 1] / bc.STRIDE - 0.5).round().astype(int) // taille
        i = (xy[:, 0] / bc.STRIDE - 0.5).round().astype(int) // taille
        g = s < haut
        h[j[g], i[g]] = True
    m = np.kron(h, np.ones((taille, taille), bool))[:H, :W]
    return m, int(h.sum()), int(h.size)


def f_blocs(taille, reduite=None):
    def f(ctx):
        c5 = ctx.carte("v5")
        m, nh, n = blocs_hesitants(c5, taille)
        k = (ce.FORCE["variante"] or "base", ctx.nom_jeu + "@blocs")
        s = STATS.setdefault(k, [0, 0]); s[0] += nh; s[1] += n
        compte(ctx, nh > 0)
        if not nh:
            return bc.pics(c5)
        c = c5.copy()
        ch = carte_reduite(ctx, reduite) if reduite else ctx.carte("c13h")
        c[m] = melange(c5, ch)[m]
        return bc.pics(c)
    return f


def construire(nom):
    """Définitions écrites dans le journal avant mesure."""
    if nom == "B1_bloc64":
        return f_blocs(64)
    if nom == "B2_bloc32":
        return f_blocs(32)
    if nom == "B1r_bloc64":                                 # B1 mesuré avec le calcul réel par morceaux (c15_banc_reel.py)
        return f_blocs(64, "blocs64")
    if nom == "BS70_bloc64":
        return f_blocs(64, "s70")
    if nom in ("v5", "CC1_v5h_50", "CC3_a1_a35"):          # contrôles : fabriques de C-piste2
        return ce.construire(nom)
    if nom == "G1_p90_55":
        return f_porte(0.55)
    if nom == "G2_p90_70":
        return f_porte(0.70)
    if nom == "S70_v5h_50":
        return f_reduit("s70")
    if nom == "S50_v5h_50":
        return f_reduit("s50")
    if nom == "W_v5h_60":
        return ce.f_melange(["v5", "c13h"], [0.6, 0.4])
    if nom == "W_logit_50":
        return f_logit(0.5)
    if nom == "T_cc1_trous20":
        return f_trous(ce.construire("CC1_v5h_50"))
    if nom.startswith("GS_"):                               # GS_<tau>_<s50|s70>
        _, t, r = nom.split("_")
        return f_porte(int(t) / 100, r)
    raise KeyError(nom)


def charger():
    return json.loads(FICHIER.read_text(encoding="utf-8")) if FICHIER.exists() else {}


def sauver(E):
    tmp = FICHIER.with_suffix(".tmp")
    tmp.write_text(json.dumps(E, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, FICHIER)


def main():
    noms = [a for a in sys.argv[1:] if not a.startswith("--")]
    cm11 = "--cm11" in sys.argv
    E = charger()
    for nom in noms:
        t0 = time.time()
        STATS.clear()
        m = cc.mesurer(construire(nom), REGLAGE + ["neg"])
        L = cc.lignes(m)
        b = cc.choisir(L)
        e = dict(lignes=L, retenu=b)
        ref = [l for l in (E.get("v5", {}).get("lignes") or L) if l["seuil"] == 0.30][0]
        if b is not None:
            e["statut"] = cc.statut(b, ref)
        if cm11 and b is not None:
            s = 0.30 if nom == "v5" else b["seuil"]
            ce.FORCE["variante"] = "d11"
            try:
                m11 = cc.mesurer(construire(nom), REGLAGE)
            finally:
                ce.FORCE["variante"] = None
            L11 = cc.lignes(m11, neg="aucun")
            l11 = [l for l in L11 if abs(l["seuil"] - s) < 1e-9][0]
            e["cm11"] = dict(seuil=s, **{k: v for k, v in l11.items() if k.startswith("f1_") or k in ("moyenne", "moy4", "err_compte")})
            e["lignes11"] = L11
        e["part_c13h"] = {f"{v}:{j}": [g, n] for (v, j), (g, n) in STATS.items()}
        e["heure"] = time.strftime("%H:%M")
        E[nom] = e
        sauver(E)
        r = b or {}
        print(f"{time.strftime('%H:%M:%S')} {nom} ({time.time() - t0:.0f} s) seuil {r.get('seuil')} : "
              + " ".join(f"{j} {r.get('f1_' + j, float('nan')):.4f}" for j in REGLAGE)
              + f" | moy {r.get('moyenne', float('nan')):.4f} moy4 {r.get('moy4', float('nan')):.4f} err {r.get('err_compte', float('nan')):.3f}"
              f" neg {r.get('fp_neg')} | finaliste {e.get('statut', {}).get('finaliste')}"
              + (f" | 11 cm {e['cm11']['moyenne']:.4f} (4 anc. {e['cm11']['moy4']:.4f})" if 'cm11' in e else "")
              + " | c13h " + " ".join(f"{k} {g}/{n}" for k, (g, n) in e["part_c13h"].items()), flush=True)


if __name__ == "__main__":
    main()
