#!/usr/bin/env python3
"""Essai 7 du plan docs/plan_nuit_10h.md : mélange à trois (v10b + soupe + v2) et températures par modèle (réglage seul).

Lecteur proche : moyenne géométrique pondérée (v10b, soupe, v2) sur les 3 classes communes, « autre » de la v10b gardée
avec le poids de la v10b, renormalisée ; températures appliquées avant (maladies.calibrer). Branche loin : « v2 ou
proche » (meilleure du premier tour). Seuil sur P(saine) : 0,58 à 0,74 par pas de 0,04.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/m12_banc_trois.py
"""
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402
from fieldscan.modules import maladies  # noqa: E402

jeux = B.charger_reglage()
ref = B.reference(jeux)
GRILLE = [0.58, 0.62, 0.66, 0.70, 0.74]
ESSAIS = []


def geo3(d, w10, wso, wv2, t10=None, tso=None, tv2=None):
    a = maladies.calibrer(d["P10"], t10)
    b = maladies.calibrer(d["Pso"], tso)
    c = maladies.calibrer(d["Pv2"], tv2)
    s = w10 + wso + wv2
    w10, wso, wv2 = w10 / s, wso / s, wv2 / s
    lg = w10 * np.log(np.clip(a[:, :3], 1e-9, 1)) + wso * np.log(np.clip(b, 1e-9, 1)) + wv2 * np.log(np.clip(c, 1e-9, 1))
    q = np.hstack([np.exp(lg), w10 * a[:, 3:]])
    return q / q.sum(1, keepdims=True)


def reponses(d, f_P, t):
    rp = B.decider_v10b(f_P(d), seuil=t)
    rl = np.where(np.isin(d["r_loin"], list(B.ALERTE)), d["r_loin"], rp)
    return np.where(d["loin"], rl, rp)


def balayer(nom, f_P):
    lignes = []
    for t in GRILLE:
        r = {j: B.mesure(d, reponses(d, f_P, t)) for j, d in jeux.items()}
        r["cout_moyen"] = float(np.mean([r[j]["cout"] for j in jeux]))
        ok, det = B.finaliste(r, ref)
        ESSAIS.append(dict(famille="essai 7", nom=f"{nom} t={t}", finaliste=ok, detail=det, **r))
        lignes.append((t, r, ok))
    fin = [x for x in lignes if x[2]]
    meilleur = min(fin, key=lambda x: x[1]["cout_moyen"]) if fin else min(lignes, key=lambda x: x[1]["cout_moyen"])
    print(("F " if meilleur[2] else "  ") + B.ligne(f"{nom} t={meilleur[0]}", meilleur[1])
          + f"  [finaliste pour t={[x[0] for x in fin]}]", flush=True)


if __name__ == "__main__":
    print("réf " + B.ligne("chaîne installée", ref))
    print("\n--- rappel : géométrique v10b + soupe 0,5 / 0,5 (premier tour) ---")
    balayer("géo v10b+soupe", lambda d: geo3(d, 1, 1, 0))
    print("\n--- mélange à trois, poids (v10b, soupe, v2) ---")
    for w in [(1, 1, 1), (2, 1, 1), (2, 2, 1), (1, 1, 0.5), (2, 1, 0), (1, 2, 0), (1, 0, 1), (3, 2, 1)]:
        balayer(f"géo {w}", lambda d, w=w: geo3(d, *w))
    print("\n--- températures par modèle (géométrique v10b + soupe 0,5 / 0,5) ---")
    for t10, tso in [(0.79, 0.61), (0.79, 1.0), (1.0, 0.61), (1.5, 1.0), (1.0, 1.5), (0.6, 0.6), (1.5, 1.5)]:
        balayer(f"géo v10b+soupe T={t10}/{tso}", lambda d, a=t10, b=tso: geo3(d, 1, 1, 0, t10=a, tso=b))
    print("\n--- températures, mélange à trois (1, 1, 1) ---")
    for t in [(0.79, 0.61, 0.59), (1.0, 1.0, 0.59)]:
        balayer(f"géo (1,1,1) T={t}", lambda d, t=t: geo3(d, 1, 1, 1, *t))
    print(f"\nessais : {len(ESSAIS)}")
    (B.SORTIE / "essais_trois.json").write_text(json.dumps(ESSAIS, ensure_ascii=False, indent=1), encoding="utf-8")
