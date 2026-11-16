#!/usr/bin/env python3
"""Essai Kaggle A1 : récupération et mesure sur le réglage (avenant docs/journee_2026-11-16/avenant_a1_kaggle.md, §4).

Importe scripts/m14_banc.py sans le modifier : chaîne « élève » au couple de d3b (0,50 ; 0,70), lecture « ensemble
livrable », règle 4.3. Décision sur la moyenne des 4 graines (comptes moyennés), contrôle Éthiopie ≤ F1 (117).

    ... -I -u scripts/a1_kaggle_banc.py controle     # F1 = 33,94 et d3b = 32,77 retrouvés (aucune donnée neuve)
    ... -I -u scripts/a1_kaggle_banc.py recuperer    # sorties de affilecorentin/a1-lot1
    ... -I -u scripts/a1_kaggle_banc.py mesurer      # une seule fois
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")
import m14_banc as M  # noqa: E402

OUT = RACINE / "out/jeux_neufs_1611/a1_kaggle"
LOT = OUT / "lot1"
GRAINES = [0, 1, 2, 3]
ETHIOPIE_F1 = 117


def references():
    jeux = M.charger()
    M.jeux_global = jeux
    M.lire_eleve(jeux, M.KAG / "pour_banc/d3b", "d3b")
    ref, rd = M.evaluer(jeux, M.f1), M.evaluer(jeux, M.chaine_eleve)
    assert abs(ref["cout_reglage"] - 33.939195228918834) < 1e-9 and abs(rd["cout_reglage"] - 32.76629831358695) < 1e-9
    return jeux, ref, rd


def recuperer():
    LOT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
               SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
    r = subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "output", "affilecorentin/a1-lot1", "-p", str(LOT), "-o"],
                       env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout[-600:], r.stderr[-600:])
    pts = list(LOT.glob("*.pt"))
    if pts:
        m = RACINE / "modeles/maladies_a1_1611/lot1"
        m.mkdir(parents=True, exist_ok=True)
        for f in pts:
            shutil.move(str(f), m / f.name)
    print(sorted(p.name for p in LOT.iterdir()))


def moyenne(rs):
    """Comptes moyennés sur les graines ; coût recalculé (linéaire : égal à la moyenne des coûts)."""
    out = {}
    for j in M.TOUS:
        d = {k: float(np.mean([r[j][k] for r in rs])) for k in ("msa", "sea")}
        d.update(nm=rs[0][j]["nm"], ns=rs[0][j]["ns"], cout=float(np.mean([r[j]["cout"] for r in rs])))
        out[j] = d
    out["cout_reglage"] = float(np.mean([out[j]["cout"] for j in M.JEUX5]))
    return out


def mesurer():
    jeux, ref, rd = references()
    res, rs = {"F1": M.resume("F1", ref, ref), "d3b": M.resume("d3b", rd, ref)}, []
    for g in GRAINES:
        M.lire_kaggle(jeux, [(LOT, f"a1g{g}")])
        R = M.evaluer(jeux, M.chaine_eleve)
        s = M.resume(f"a1g{g}", R, ref)
        s["controle_ethiopie"] = R["ethiopie"]["msa"] <= ETHIOPIE_F1
        res[f"a1g{g}"] = s
        rs.append(R)
        print(M.ligne(f"a1g{g}", R), "| passe seule :", s["finaliste_sans_temps"] and s["controle_ethiopie"])
    moy = moyenne(rs)
    passe, cond, _ = M.conditions(moy, ref)
    eth = moy["ethiopie"]["msa"] <= ETHIOPIE_F1
    seules = [f"a1g{g}" for g in GRAINES if res[f"a1g{g}"]["finaliste_sans_temps"] and res[f"a1g{g}"]["controle_ethiopie"]]
    livrable = min(seules, key=lambda n: res[n]["cout_reglage"]) if (passe and eth and seules) else None
    res["moyenne_4_graines"] = dict(cout_reglage=moy["cout_reglage"], conditions=cond, controle_ethiopie=eth,
                                    finaliste=bool(passe and eth and livrable), livrable=livrable,
                                    par_jeu={j: moy[j] for j in M.TOUS})
    print("moyenne des 4 graines :", json.dumps(res["moyenne_4_graines"], ensure_ascii=False))
    (OUT / "bilan_lot1.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    q = sys.argv[1]
    if q == "controle":
        _, ref, rd = references()
        print(f"contrôle : F1 {ref['cout_reglage']:.2f}, d3b {rd['cout_reglage']:.2f}")
    else:
        {"recuperer": recuperer, "mesurer": mesurer}[q]()
