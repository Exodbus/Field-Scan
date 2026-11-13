#!/usr/bin/env python3
"""Idées libres, suite : mélange v10b + soupe en gros plan combiné à un changement de la branche « loin » (réglage seul).

Modes de la branche « loin » : « v2 » (installé) ; « v2 ou proche » (photo loin : alerte si la v2 ou le lecteur proche
alerte) ; « sans aiguilleur » (tout passe par le lecteur proche). Lecteurs proches : v10b seule, moyenne 0,25 / 0,5,
moyenne géométrique 0,5. Seuil sur P(saine) : 0,50 à 0,78 par pas de 0,04 (et le seuil installé 0,5186 pour la v10b).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/m12_banc_combinaisons.py
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
ESSAIS = []
GRILLE = [round(x, 2) for x in np.arange(0.50, 0.781, 0.04)]


def so4(d):
    return np.hstack([d["Pso"], np.zeros((len(d["Pso"]), 1))])


def melange(d, w, geo=False):
    a, b = d["P10"], so4(d)
    if not geo:
        return (1 - w) * a + w * b
    q = np.power(np.clip(a[:, :3], 1e-9, 1), 1 - w) * np.power(np.clip(b[:, :3], 1e-9, 1), w)
    q = np.hstack([q, (1 - w) * a[:, 3:]])
    return q / q.sum(1, keepdims=True)


LECTEURS = {"v10b": lambda d: d["P10"], "moy 0,25": lambda d: melange(d, 0.25), "moy 0,5": lambda d: melange(d, 0.5),
            "géo 0,5": lambda d: melange(d, 0.5, geo=True)}


def reponses(d, lecteur, t, mode):
    """Réponse du module complet pour un lecteur proche, un seuil et un mode de branche loin."""
    rp = B.decider_v10b(LECTEURS[lecteur](d), seuil=t)
    if mode == "sans aiguilleur":
        return rp
    if mode == "v2 ou proche":
        rl = np.where(np.isin(d["r_loin"], list(B.ALERTE)), d["r_loin"], rp)
        return np.where(d["loin"], rl, rp)
    return np.where(d["loin"], d["r_loin"], rp)


def evaluer(jeux_, lecteur, t, mode):
    r = {j: B.mesure(d, reponses(d, lecteur, t, mode)) for j, d in jeux_.items()}
    r["cout_moyen"] = float(np.mean([r[j]["cout"] for j in jeux_]))
    return r


if __name__ == "__main__":
    print("réf " + B.ligne("chaîne installée", ref))
    for mode in ("v2 ou proche", "sans aiguilleur"):
        for lecteur in LECTEURS:
            print(f"\n=== loin : {mode} ; proche : {lecteur} ===")
            res = []
            for t in ([0.5186] if lecteur == "v10b" else []) + GRILLE:
                r = evaluer(jeux, lecteur, t, mode)
                ok, detail = B.finaliste(r, ref)
                ESSAIS.append(dict(famille="combinaison", nom=f"{mode} / {lecteur} / t={t}", finaliste=ok, detail=detail, **r))
                res.append((t, r, ok))
                print(("F " if ok else "  ") + B.ligne(f"{lecteur} t={t}", r), flush=True)
    print(f"\nNombre d'essais de ce script : {len(ESSAIS)}")
    (B.SORTIE / "essais_combinaisons.json").write_text(json.dumps(ESSAIS, ensure_ascii=False, indent=1), encoding="utf-8")
