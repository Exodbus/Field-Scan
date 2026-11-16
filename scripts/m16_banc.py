#!/usr/bin/env python3
"""Essai m16 (basse résolution) : récupération et mesure sur le réglage
(avenant docs/journee_2026-11-16/avenant_m16_basse_resolution.md, §3).

Importe scripts/m14_banc.py sans le modifier (comme scripts/a1_kaggle_banc.py) : chaîne « élève » au couple de d3b
(0,50 ; 0,70), lecture « ensemble livrable », règle 4.3. Décision sur la moyenne des 4 graines (comptes moyennés), plus
le contrôle propre : E1 Éthiopie malades sans alerte < 117 (strict), E2 coût Éthiopie ≤ celui de F1.

    ... -I -u scripts/m16_banc.py controle     # F1 = 33,94 et d3b = 32,77 retrouvés (aucune donnée neuve)
    ... -I -u scripts/m16_banc.py recuperer    # sorties de affilecorentin/m16-lot1
    ... -I -u scripts/m16_banc.py mesurer      # une seule fois
"""
import hashlib
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

OUT = RACINE / "out/maladies/jour_1611/m16"
LOT = OUT / "lot1"
POIDS = OUT / "lot1_poids"
GRAINES = [0, 1, 2, 3]
ETHIOPIE_F1 = 117
AV = RACINE / "docs/journee_2026-11-16/avenant_m16_basse_resolution.md"
EMP = RACINE / "docs/journee_2026-11-16/empreinte_avenant_m16.txt"
D3B_GRAINES = RACINE / "out/maladies/nuit_1311/piste2/bilan_graines.json"


def verifier_avenant():
    assert hashlib.sha256(AV.read_bytes()).hexdigest() == EMP.read_text(encoding="utf-8").split()[0], "avenant modifié"


def references():
    jeux = M.charger()
    M.jeux_global = jeux
    M.lire_eleve(jeux, M.KAG / "pour_banc/d3b", "d3b")
    ref, rd = M.evaluer(jeux, M.f1), M.evaluer(jeux, M.chaine_eleve)
    assert abs(ref["cout_reglage"] - 33.939195228918834) < 1e-9 and abs(rd["cout_reglage"] - 32.76629831358695) < 1e-9
    assert ref["ethiopie"]["msa"] == ETHIOPIE_F1
    return jeux, ref, rd


def recuperer():
    LOT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
               SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
    r = subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "output", "affilecorentin/m16-lot1", "-p", str(LOT), "-o"],
                       env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout[-600:], r.stderr[-600:])
    pts = list(LOT.glob("*.pt"))
    if pts:
        POIDS.mkdir(parents=True, exist_ok=True)
        for f in pts:
            shutil.move(str(f), POIDS / f.name)
    print(sorted(p.name for p in LOT.iterdir()))


def cout_ethiopie(r):
    e = r["ethiopie"]
    return 100 * (3 * e["msa"] / e["nm"] + e["sea"] / e["ns"])


def controle_propre(r, ref):
    return dict(E1=r["ethiopie"]["msa"] < ETHIOPIE_F1, E2=cout_ethiopie(r) <= cout_ethiopie(ref) + 1e-12)


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
    verifier_avenant()
    bilan = OUT / "bilan_lot1.json"
    assert not bilan.exists(), "mesure déjà faite : une seule lecture du réglage"
    for g in GRAINES:   # 4 graines complètes exigées (avenant §2)
        for j in ("tdtu", "ethiopie"):
            assert (LOT / f"predictions_m16g{g}_{j}.csv").exists(), (g, j)
        for j in ("validation", "psfd", "agrovision", "roamer_dev_loin"):
            assert len(list(LOT.glob(f"predictions_m16g{g}_{j}_pli_*.csv"))) == 2, (g, j)
    jeux, ref, rd = references()
    res, rs = {"F1": M.resume("F1", ref, ref), "d3b": M.resume("d3b", rd, ref)}, []
    res["F1"]["cout_ethiopie"] = cout_ethiopie(ref)
    for g in GRAINES:
        M.lire_kaggle(jeux, [(LOT, f"m16g{g}")])
        R = M.evaluer(jeux, M.chaine_eleve)
        s = M.resume(f"m16g{g}", R, ref)
        s["controle_propre"] = controle_propre(R, ref)
        s["cout_ethiopie"] = cout_ethiopie(R)
        s["passe_seule"] = bool(s["finaliste_sans_temps"] and all(s["controle_propre"].values()))
        res[f"m16g{g}"] = s
        rs.append(R)
        print(M.ligne(f"m16g{g}", R), "| contrôle propre :", s["controle_propre"], "| passe seule :", s["passe_seule"])
    moy = moyenne(rs)
    passe, cond, _ = M.conditions(moy, ref)
    cp = controle_propre(moy, ref)
    seules = [f"m16g{g}" for g in GRAINES if res[f"m16g{g}"]["passe_seule"]]
    fin = bool(passe and all(cp.values()))
    livrable = min(seules, key=lambda n: res[n]["cout_reglage"]) if (fin and seules) else None
    res["moyenne_4_graines"] = dict(cout_reglage=moy["cout_reglage"], conditions=cond, controle_propre=cp,
                                    cout_ethiopie=cout_ethiopie(moy), finaliste=fin, livrable=livrable,
                                    par_jeu={j: moy[j] for j in M.TOUS})
    # pour information seulement : d3b graines 0 à 3 (appariées)
    b = json.loads(D3B_GRAINES.read_text(encoding="utf-8"))
    res["info_d3b_graines"] = {f"g{g}": dict(cout=b["graines"][f"eleve g{g}"]["cout_reglage"],
                                            ethiopie_msa=b["graines"][f"eleve g{g}"]["par_jeu"]["ethiopie"]["msa"],
                                            ethiopie_sea=b["graines"][f"eleve g{g}"]["par_jeu"]["ethiopie"]["sea"]) for g in GRAINES}
    print("moyenne des 4 graines :", json.dumps(res["moyenne_4_graines"], ensure_ascii=False))
    bilan.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    q = sys.argv[1]
    if q == "controle":
        verifier_avenant()
        _, ref, rd = references()
        print(f"contrôle : F1 {ref['cout_reglage']:.2f} (Éthiopie {ref['ethiopie']['msa']} / {ref['ethiopie']['nm']}, "
              f"saines en alerte {ref['ethiopie']['sea']} / {ref['ethiopie']['ns']}, coût Éthiopie {cout_ethiopie(ref):.2f}), "
              f"d3b {rd['cout_reglage']:.2f}")
    else:
        {"recuperer": recuperer, "mesurer": mesurer}[q]()
