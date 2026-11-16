"""Juge du banc d'anomalies injectées (15/11/2026) : mesure UNE fois, après le gel de 15 h 50, les finalistes de télédétection.

À lancer par le juge seulement :
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/t15_juge.py --je-suis-le-juge [--module vigueur|stress|temporel|drone]

- Sentinel-2 (vigueur, stress, temporel) : Côte d'Ivoire, mêmes règles d'injection que le réglage, graines + 50 000.
- Drone : moitié « mesure » des sites ReforesTree (Carlos Vera Guevara, Leonor Aspiazu, Nestor Macias), graines + 50 000.
- Finalistes lus dans out/teledetection/jour_1511/reglage/decision_<module>.csv (colonne « finaliste »), écrits avant 15 h 45.
- Pour le drone, les écarts minimaux de VARI et GLI sont ceux calibrés sur le réglage (colonne « em » de
  reglage/resume_drone.csv) : rien n'est recalibré sur la moitié mesurée.
- Règle « amélioration proposée » (plan, section 3) : rappel moyen >= référence + 0,03 et
  fausses alertes sans injection <= référence x 1,10.
Sorties : out/teledetection/jour_1511/mesure/ (résumés, zones, verdict_<module>.csv). Un fichier de verrou empêche une
seconde lecture.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

import t15_commun as tc


def finalistes(module):
    p = tc.SORTIE / "reglage" / f"decision_{module}.csv"
    if not p.exists():
        return []
    d = pd.read_csv(p)
    return list(d.variante[d.finaliste.astype(bool)]) if "finaliste" in d else []


def verdict(res):
    ref = res[res.variante == "REF"].iloc[0]
    out = []
    for _, r in res.iterrows():
        if r.variante == "REF":
            continue
        a = r.rappel_moyen >= ref.rappel_moyen + 0.03 - 1e-9
        b = r.fa_ha_sans_injection <= ref.fa_ha_sans_injection * 1.10 + 1e-9
        out.append(dict(variante=r.variante, rappel_moyen=r.rappel_moyen, rappel_ref=ref.rappel_moyen,
                        fa_sans_injection=r.fa_ha_sans_injection, fa_ref=ref.fa_ha_sans_injection,
                        c_rappel=a, c_fa=b, amelioration_proposee=bool(a and b)))
    return pd.DataFrame(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--je-suis-le-juge", action="store_true", required=True)
    ap.add_argument("--module", choices=["vigueur", "stress", "temporel", "drone"], action="append")
    a = ap.parse_args()
    os.environ["T15_MESURE_AUTORISEE"] = "oui"
    sortie = tc.SORTIE / "mesure"
    sortie.mkdir(parents=True, exist_ok=True)
    for module in a.module or ["vigueur", "stress", "temporel", "drone"]:
        verrou = sortie / f"LU_{module}.txt"
        if verrou.exists():
            print(f"{module} : déjà mesuré ({verrou.read_text(encoding='utf-8').strip()}) ; pas de seconde lecture.")
            continue
        fin = finalistes(module)
        if not fin:
            print(f"{module} : aucun finaliste, rien à mesurer.")
            continue
        import datetime
        verrou.write_text(f"lu le {datetime.datetime.now():%Y-%m-%d %H:%M}, finalistes {fin}\n", encoding="utf-8")
        if module == "drone":
            import t15_banc_drone as bd
            em = pd.read_csv(tc.SORTIE / "reglage" / "resume_drone.csv").set_index("variante")["em"]
            var = {k: dict(v, em=float(em[k])) for k, v in bd.VARIANTES.items() if k in em.index}
            res = bd.lancer("mesure", fin, tc.N_TIRAGES, decalage=tc.DECALAGE_MESURE, sortie=sortie, variantes=var)
        else:
            import t15_banc_s2 as bs
            res = bs.lancer(module, tc.PAYS_MESURE, fin, decalage=tc.DECALAGE_MESURE, sortie=sortie)
        v = verdict(res)
        v.to_csv(sortie / f"verdict_{module}.csv", index=False)
        print(v.to_string(index=False))


if __name__ == "__main__":
    main()
