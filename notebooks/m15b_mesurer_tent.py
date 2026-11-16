#!/usr/bin/env python3
"""Mesure de la piste 3 de M-kaggle2 (15/11) : soupes s4 adaptées pendant la lecture (TENT), essais T1 et T2.
Règles écrites avant calcul : docs/journee_2026-11-15/journal_m_kaggle2.md (16 h 22). Règle « finaliste » : plan du 13/11, 4.3.
Banc : scripts/m14_banc.py (sans modification). Aucun juge, aucun test.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/m15b_mesurer_tent.py [--sans-telechargement]
"""
import os

for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[v] = "2"   # 2 fils au plus
import json  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import m14_banc as M  # noqa: E402

SORTIE = RACINE / "out/maladies/jour_1511/kaggle2"
LOT = SORTIE / "lot_tent"
KAG = RACINE / "out/maladies/nuit_1311/kaggle"
SOUPE = RACINE / "out/maladies/jour_1511/kaggle/lot_soupe"
T_F1B, T_F1, T_D3B, PART = 10.2, 27.0, 4.1, 0.224
T_ADAPT = 6 / 8 * T_D3B   # estimation écrite à 16 h 22
COLS = ["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]


def temps(nom):
    t = T_D3B + T_ADAPT if nom.startswith("T1") else T_F1B + T_ADAPT + PART * T_D3B
    return dict(s_par_photo=round(t, 2), rapport_F1_bornes=round(t / T_F1B, 2), rapport_F1_installe=round(t / T_F1, 2),
                passe_temps=t <= 1.2 * T_F1B, note="estimation composée (16 h 22)")


def main():
    LOT.mkdir(parents=True, exist_ok=True)
    if "--sans-telechargement" not in sys.argv:
        env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
                   SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
        r = subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "output", "affilecorentin/m15b-tent", "-p", str(LOT), "-o"],
                           env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(r.stdout[-400:], r.stderr[-400:])
    ctrl = {"fichiers": sorted(p.name for p in LOT.iterdir())}
    # contrôle : s4 relu sans adaptation = probabilités de m15-soupe
    a = pd.read_csv(LOT / "controle_s4_validation_pli_tdtu.csv").set_index("chemin")
    b = pd.read_csv(SOUPE / "predictions_s4_validation_pli_tdtu.csv").set_index("chemin")
    ctrl["s4_relu_ecart_max"] = float((a.loc[b.index, COLS] - b[COLS]).abs().max().max())
    ctrl["infos_tent"] = json.loads((LOT / "infos_tent.json").read_text(encoding="utf-8"))
    print(json.dumps(ctrl, ensure_ascii=False, indent=1))
    jeux = M.charger()
    M.jeux_global = jeux
    M.lire_eleve(jeux, KAG / "pour_banc/d3b", "d3b")
    ref = M.evaluer(jeux, M.f1)
    print(M.ligne("F1 (contrôle, attendu 33,94)", ref))
    assert abs(ref["cout_reglage"] - 33.94) < 0.005
    res = {"controles": ctrl, "F1": M.resume("F1", ref, ref)}
    M.lire_kaggle(jeux, [(SOUPE, "s4")])
    r3, r4 = M.evaluer(jeux, M.chaine_eleve), M.evaluer(jeux, M.mc1_ou_proche)
    print(M.ligne("J3 d3-soupe4 (contrôle, attendu 34,31)", r3))
    print(M.ligne("J4 MC1-OU-proche (d3-soupe4) (contrôle, attendu 33,41)", r4))
    assert abs(r3["cout_reglage"] - 34.31) < 0.006 and abs(r4["cout_reglage"] - 33.41) < 0.006
    res["J3"], res["J4"] = M.resume("J3", r3, ref), M.resume("J4", r4, ref)
    D_s4_val = jeux["validation"]["D"].copy()
    M.lire_kaggle(jeux, [(LOT, "s4t")])
    for nom, regle in (("T1 s4-tent", M.chaine_eleve), ("T2 MC1-OU-proche (s4-tent)", M.mc1_ou_proche)):
        R = M.evaluer(jeux, regle)
        s = M.resume(nom, R, ref)
        s["temps"] = temps(nom)
        s["finaliste"] = bool(s["finaliste_sans_temps"] and s["temps"]["passe_temps"])
        res[nom] = s
        print(M.ligne(nom, R))
        print("   ", s["finaliste"], s["conditions"], s["temps"],
              {k: s[k] for k in ("alertes_differentes", "malades_perdues_vs_F1", "malades_rattrapees_vs_F1")})
    # garde-fou (information) : flux de validation à 90 % de saines, chaîne élève avec et sans adaptation
    dv = jeux["validation"]
    fs = sorted(LOT.glob("predictions_s4t_valdeseq_pli_*.csv"))
    assert len(fs) == 2
    dfs = [pd.read_csv(f).set_index("chemin") for f in fs]
    ch = list(dfs[0].index)
    pos = {c: i for i, c in enumerate(dv["chemin"])}
    idx = np.array([pos[c] for c in ch])
    sous = {k: (v[idx] if isinstance(v, np.ndarray) and len(v) == len(dv["chemin"]) else v) for k, v in dv.items()}
    g = {}
    for nom, D in (("sans adaptation", D_s4_val[idx]), ("adapté sur le flux à 90 % de saines", np.mean([d.loc[ch, COLS].to_numpy() for d in dfs], 0))):
        sous["D"] = D
        rep = M.chaine_eleve(sous)
        al = np.isin(rep, M.ALERTE)
        g[nom] = dict(malades=int(sous["malade"].sum()), malades_sans_alerte=int((~al & sous["malade"]).sum()),
                      saines=int((~sous["malade"]).sum()), saines_en_alerte=int((al & ~sous["malade"]).sum()))
    res["garde_fou_desequilibre"] = g
    print("garde-fou :", g)
    res["essais"] = 2
    (SORTIE / "bilan_tent.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("écrit :", SORTIE / "bilan_tent.json")


if __name__ == "__main__":
    main()
