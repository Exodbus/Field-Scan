#!/usr/bin/env python3
"""Mesure de réglage de M-kaggle (15/11) : d3b moyenné sur ses 4 graines (probabilités : J1, J2 ; soupe de poids : J3, J4).
Règles écrites avant tout calcul : docs/journee_2026-11-15/journal_m_kaggle.md (14 h 00). Règle « finaliste » : plan du
13/11, section 4.3. Même code que la veille : scripts/m14_banc.py (M-piste2), importé sans modification.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/m15_mesurer.py

Aucun juge, aucun test : seuls les 5 jeux de réglage et roamer_dev_loin_feuilles (via m14_banc.charger).
"""
import os

for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[v] = "2"   # 2 fils au plus
import json  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import m14_banc as M  # noqa: E402

SORTIE = RACINE / "out/maladies/jour_1511/kaggle"
KAG = RACINE / "out/maladies/nuit_1311/kaggle"
P2 = RACINE / "out/maladies/nuit_1311/piste2/kaggle"
GRAINES = [(KAG / "lot2p", "d3b"), (P2 / "lot1", "d3g1"), (P2 / "lot2", "d3g2"), (P2 / "lot2", "d3g3")]
SOUPE = [(SORTIE / "lot_soupe", "s4")]
# Temps composés (mesures du 14/11, out/maladies/nuit_1311/piste2/temps.json et part_d3b_a_lire.json)
T_F1B, T_F1, T_D3B, PART = 10.2, 27.0, 4.1, 0.224


def temps(nom):
    k = 4 if "moy4" in nom else 1          # réseaux élèves lus, en multiples de d3b (2 réseaux)
    if nom.startswith("MC1"):
        t = T_F1B + PART * k * T_D3B       # lecture paresseuse : élève lu sur les photos proches où F1 n'alerte pas
    else:
        t = k * T_D3B                      # chaîne élève (aiguilleur et v2 compris dans la mesure de d3b du 14/11)
    return dict(s_par_photo=round(t, 2), rapport_F1_bornes=round(t / T_F1B, 2), rapport_F1_installe=round(t / T_F1, 2),
                passe_temps=t <= 1.2 * T_F1B)


def main():
    jeux = M.charger()
    M.jeux_global = jeux
    M.lire_eleve(jeux, KAG / "pour_banc/d3b", "d3b")
    ref = M.evaluer(jeux, M.f1)
    rd = M.evaluer(jeux, M.chaine_eleve)
    print(M.ligne("F1 (contrôle, attendu 33,94)", ref))
    print(M.ligne("d3b (contrôle, attendu 32,77)", rd))
    assert abs(ref["cout_reglage"] - 33.94) < 0.005 and abs(rd["cout_reglage"] - 32.77) < 0.005
    res = {"F1": M.resume("F1", ref, ref), "d3b": M.resume("d3b", rd, ref)}
    essais = {"J1 d3-moy4": (GRAINES, M.chaine_eleve), "J2 MC1-OU-proche (d3-moy4)": (GRAINES, M.mc1_ou_proche),
              "J3 d3-soupe4": (SOUPE, M.chaine_eleve), "J4 MC1-OU-proche (d3-soupe4)": (SOUPE, M.mc1_ou_proche)}
    for nom, (src, regle) in essais.items():
        if not all((d / f"predictions_{n}_tdtu.csv").exists() for d, n in src):
            print("absent :", nom)
            continue
        M.lire_kaggle(jeux, src)
        R = M.evaluer(jeux, regle)
        s = M.resume(nom, R, ref)
        s["temps"] = temps(nom.split(" ", 1)[1])
        s["finaliste"] = bool(s["finaliste_sans_temps"] and s["temps"]["passe_temps"])
        res[nom] = s
        print(M.ligne(nom, R))
        print("   ", s["finaliste_sans_temps"], s["conditions"], s["temps"],
              {k: s[k] for k in ("alertes_differentes", "malades_perdues_vs_F1", "malades_rattrapees_vs_F1")})
    (SORTIE / "bilan_m15.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("écrit :", SORTIE / "bilan_m15.json")
    _ = np


if __name__ == "__main__":
    main()
