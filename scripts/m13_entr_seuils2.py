#!/usr/bin/env python3
"""Essais 9 à 12 (M-entraîneur, 13/11) : deux confiances pour un élève, s_p (photos « proche ») et s_l (élève dans la
branche « loin », la v2 inchangée). Grille s_p 0,40-0,80 et s_l 0,50-0,90 par pas de 0,02 ; couple retenu = coût de
réglage le plus bas parmi les couples qui remplissent les conditions « finaliste » sans le temps. Coût croisé à côté.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_entr_seuils2.py <dossier> <candidat> [...]
"""
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
sys.path.insert(0, str(RACINE))
import m13_entr_mesurer as M  # noqa: E402
import m12_banc_commun as B  # noqa: E402
from fieldscan.modules import maladies  # noqa: E402


def reponse2(j, P, sp, sl):
    d = M.JEUX[j]
    rp = maladies.decider_convnext(P, {**B.M_V10B, "seuil": sp})[0]
    rpl = maladies.decider_convnext(P, {**B.M_V10B, "seuil": sl})[0]
    rl = np.where(np.isin(d["r_loin"], list(B.ALERTE)), d["r_loin"], rpl)
    return np.where(d["loin"], rl, rp)


M.reponse_eleve = lambda j, P, s: reponse2(j, P, *s)   # bilan() passe le couple tel quel
SP, SL = np.round(np.arange(0.40, 0.801, 0.02), 2), np.round(np.arange(0.50, 0.901, 0.02), 2)
ref = M.reference_f1()
for nom in (sys.argv[2:] if __name__ == "__main__" else []):
    P = M.charger(sys.argv[1], nom)
    res = {(float(a), float(b)): M.bilan(P, ref, (float(a), float(b))) for a in SP for b in SL}
    ok = {s: r for s, r in res.items() if r["finaliste_sans_temps"]}
    best = min(ok, key=lambda s: ok[s]["cout_reglage"]) if ok else min(res, key=lambda s: res[s]["cout_reglage"])
    croise = []
    for j in M.REGLAGE5:
        autres = [k for k in M.REGLAGE5 if k != j]
        cand = ok if ok else res
        s = min(cand, key=lambda s: np.mean([res[s][k]["cout"] for k in autres]))
        croise.append(res[s][j]["cout"])
    r = res[best]
    print(M.ligne(f"{nom} s_p={best[0]:.2f} s_l={best[1]:.2f}", r))
    print(f"   finaliste (sans temps) : {r['finaliste_sans_temps']} {r['conditions_sans_temps']} | couples valides {len(ok)} | "
          f"coût croisé {np.mean(croise):.2f} | décisions ≠ F1 {r['decisions_differentes_F1']}")
    (Path(sys.argv[1]) / f"seuils2_{nom}.json").write_text(json.dumps(dict(couple=best, cout=r["cout_reglage"], cout_croise=float(np.mean(croise)),
        n_valides=len(ok), bilan=r), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
