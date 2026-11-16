#!/usr/bin/env python3
"""Mesure des essais de l'agent C-kaggle (15/11) sur le réglage du comptage, à 5 cm et dégradé à 11 cm.

Reprise de scripts/c14_essais.py (C-piste2), mêmes fonctions de mesure. Code du banc importé sans modification :
scripts/v6_banc_commun.py, v6_banc_candidats.py, c13_banc_commun.py (garde-fou des juges, règle 5.3),
c13_banc_candidats.py. Cartes lues en lecture seule : mon cache (out/comptage/jour_1511/kaggle/cache), puis celui de
C-piste2 (c13h), puis ceux du banc (v3, v4, v5, c13d, c13e, cartes dégradées du v5).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/c15_mesure.py v5 c14h_g1 --cm11

Résultats : out/comptage/jour_1511/kaggle/essais.json (lignes par seuil à 5 cm, seuil retenu, statut 5.3 ordinaire et
« résolution », lecture à 11 cm au seuil retenu).
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

import c13_banc_candidats as cd  # noqa: E402,F401  (importe c13_banc_commun : garde-fou + caches de la nuit)
import c13_banc_commun as cc  # noqa: E402
import v6_banc_candidats as ca  # noqa: E402

bc = cc.bc
SORTIE = RACINE / "out/comptage/jour_1511/kaggle2"
CACHES = [SORTIE / "cache"]
FICHIER = SORTIE / "essais.json"
REGLAGE = cc.REGLAGE
_carte_c13 = bc.carte_cache
_MEM = {}
FORCE = {"variante": None}


def carte_cache(modele, variante, nom_jeu, nom):
    if FORCE["variante"] and variante == "base":
        variante = FORCE["variante"]
    for dossier in CACHES:
        p = dossier / f"{modele}_{variante}_{nom_jeu}"
        if p.with_suffix(".json").exists():
            break
    else:
        if modele not in ("v3", "v4", "v5", "c13d", "c13e"):
            raise FileNotFoundError(f"{modele}_{variante}_{nom_jeu}")   # jamais de repli silencieux
        return _carte_c13(modele, variante, nom_jeu, nom)
    cle = (modele, variante, nom_jeu)
    if cle not in _MEM:
        _MEM[cle] = (np.memmap(p.with_suffix(".f32"), dtype="float32", mode="r"),
                     json.loads(p.with_suffix(".json").read_text(encoding="utf-8")))
    mm, idx = _MEM[cle]
    a, h, w = idx[nom]
    return np.asarray(mm[a:a + h * w]).reshape(h, w)


bc.carte_cache = carte_cache


def f_melange(membres, poids):
    """CC1 : moyenne arithmétique pondérée des cartes de probabilité, puis pics fenêtre 7 (comme c14_essais)."""
    w = np.asarray(poids, "float64"); w = w / w.sum()

    def f(ctx):
        c = sum(wi * ctx.carte(m).astype("float64") for wi, m in zip(w, membres))
        return bc.pics(c.astype("float32"))
    return f


def construire(nom):
    """Définitions écrites dans docs/journee_2026-11-15/journal_c_kaggle.md avant mesure."""
    if nom.startswith("CC1@"):                      # v5 0,50 + <modèle> 0,50
        return f_melange(["v5", nom[4:]], [0.5, 0.5])
    return ca.f_seul(nom)                            # v5, c13h, c14h_g1, c15w, c15d : réseau seul


def charger():
    return json.loads(FICHIER.read_text(encoding="utf-8")) if FICHIER.exists() else {}


def sauver(E):
    tmp = FICHIER.with_suffix(".tmp")
    tmp.write_text(json.dumps(E, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, FICHIER)


def mesure11(nom, seuil):
    FORCE["variante"] = "d11"
    try:
        m = cc.mesurer(construire(nom), REGLAGE)
    finally:
        FORCE["variante"] = None
    L = cc.lignes(m, neg="aucun")
    return [l for l in L if abs(l["seuil"] - seuil) < 1e-9][0], L


def main():
    noms = [a for a in sys.argv[1:] if not a.startswith("--")]
    cm11 = "--cm11" in sys.argv
    E = charger()
    for nom in noms:
        t0 = time.time()
        e = E.get(nom, {})
        if "lignes" not in e:
            e["lignes"] = cc.lignes(cc.mesurer(construire(nom), REGLAGE + ["neg"]))
        b = e["retenu"] = cc.choisir(e["lignes"])
        if nom == "v5":
            b = e["retenu"] = [l for l in e["lignes"] if l["seuil"] == 0.30][0]
        ref = [l for l in E["v5"]["lignes"] if l["seuil"] == 0.30][0] if "v5" in E else b
        if b is not None:
            e["statut"] = cc.statut(b, ref)
        if cm11 and b is not None and "cm11" not in e:
            l11, L11 = mesure11(nom, b["seuil"])
            e["cm11"] = dict(seuil=b["seuil"], **{k: v for k, v in l11.items() if k.startswith("f1_") or k in ("moyenne", "moy4", "err_compte")})
            e["lignes11"] = L11
        if b is not None and "cm11" in e and "v5" in E and "cm11" in E["v5"]:
            s = e["statut"]
            s["resolution"] = bool(e["cm11"]["moyenne"] >= E["v5"]["cm11"]["moyenne"] + 0.030
                                   and b["moyenne"] >= ref["moyenne"] - 0.005 and s["c2"] and s["c3"] and s["c4"])
        E[nom] = e
        sauver(E)
        r = b or {}
        s = e.get("statut", {})
        print(f"{time.strftime('%H:%M:%S')} {nom} ({time.time() - t0:.0f} s) seuil {r.get('seuil')} : "
              + " ".join(f"{j} {r.get('f1_' + j, float('nan')):.4f}" for j in REGLAGE)
              + f" | moy {r.get('moyenne', float('nan')):.4f} moy4 {r.get('moy4', float('nan')):.4f} err {r.get('err_compte', float('nan')):.3f}"
              f" neg {r.get('fp_neg')} | finaliste {s.get('finaliste')} résolution {s.get('resolution')} pire {s.get('pire_jeu')} {s.get('pire_perte', float('nan')):+.4f}"
              + (f" | 11 cm {e['cm11']['moyenne']:.4f} ({' '.join(f'{j} {e[chr(99)+'m11']['f1_'+j]:.3f}' for j in REGLAGE)})" if 'cm11' in e else ""), flush=True)


if __name__ == "__main__":
    main()
