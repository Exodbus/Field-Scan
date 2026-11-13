#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : optimisme du banc de comptage par validation croisée « un jeu dehors ».

Lit out/comptage_v6/banc/essais.json (toutes les variantes mesurées par C-banc sur le réglage, à tous les seuils ;
les chiffres des finalistes y sont recalculés à part par controle_nuit_c_recalcul.py). Pour chaque jeu de réglage
laissé dehors : la variante et le seuil sont re-choisis sur les 4 autres (règle 3.4 et règle « finaliste » de C-banc
restreintes à ces 4 jeux : moyenne > v5 + 0,010, aucun jeu sous v5 − 0,020, erreur de compte <= celle du v5 à 0,30,
fausses détections sans bananier < 1 %), le v5 de référence aussi (règle 3.4 sur les 4 jeux), puis on lit le F1 du
jeu dehors. Optionnel : --familles pour restreindre (ex. aiguillage_p90).
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_c_loo.py [--prefixe E5p90]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
OUT = RACINE / "out/controle_nuit_1112"
JEUX = ["dense", "plantain", "jeunes", "mm", "btd_val"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefixe", default="")
    ap.add_argument("--essais", default=str(RACINE / "out/comptage_v6/banc/essais.json"))
    ap.add_argument("--sortie", default="c_loo")
    a = ap.parse_args()
    E = json.loads(Path(a.essais).read_text(encoding="utf-8"))
    seuils = sorted(E["v5"]["res"]["dense"], key=float)

    def neg(e, s):
        r = e["res"].get("neg") or e["res"].get("neg_q")
        return r[s]["taux"]

    def f1(e, j, s):
        return e["res"][j][s]["f1"]

    def err(e, j, s):
        return e["res"][j][s]["err_compte"]

    def ref_v5(quels):
        el = [s for s in seuils if neg(E["v5"], s) < 0.01]
        return max(el, key=lambda s: np.mean([f1(E["v5"], j, s) for j in quels]))

    noms = [n for n, e in E.items() if all(j in e["res"] for j in JEUX) and (e["res"].get("neg") or e["res"].get("neg_q"))
            and (n.startswith(a.prefixe) or n == "v5")]
    lignes, out = [f"variantes : {len(noms)} (préfixe « {a.prefixe} »)"], {}

    def choisir(quels):
        s5 = ref_v5(quels)
        m5 = np.mean([f1(E["v5"], j, s5) for j in quels])
        e530 = np.mean([err(E["v5"], j, "0.3") for j in quels])
        best = None
        for n in noms:
            e = E[n]
            el = [s for s in seuils if neg(e, s) < 0.01]
            if not el:
                continue
            s = max(el, key=lambda s: np.mean([f1(e, j, s) for j in quels]))
            m = np.mean([f1(e, j, s) for j in quels])
            ok = (m > m5 + 0.010 and all(f1(e, j, s) >= f1(E["v5"], j, s5) - 0.020 for j in quels)
                  and np.mean([err(e, j, s) for j in quels]) <= e530)
            if ok and (best is None or m > best[1]):
                best = (n, m, s)
        return best, s5

    plein, s5p = choisir(JEUX)
    lignes.append(f"choix sur les 5 jeux : {plein} ; v5 au seuil {s5p}")
    gains_d, gains_p = [], []
    for h in JEUX:
        quels = [j for j in JEUX if j != h]
        ch, s5 = choisir(quels)
        if ch is None:
            lignes.append(f"{h} dehors : aucun finaliste sur les 4 autres")
            continue
        n, m, s = ch
        gd = f1(E[n], h, s) - f1(E["v5"], h, s5)
        gp = f1(E[plein[0]], h, plein[2]) - f1(E["v5"], h, s5p)
        g30 = f1(E[n], h, s) - f1(E["v5"], h, "0.3")
        gains_d.append(gd); gains_p.append(gp)
        out[h] = dict(choix=n, seuil=s, f1_dehors=f1(E[n], h, s), v5=f1(E["v5"], h, s5), seuil_v5=s5,
                      gain_dehors=gd, gain_plein=gp, gain_dehors_contre_v5_030=g30)
        lignes.append(f"{h} dehors : choix {n} au seuil {s} ; F1 dehors {f1(E[n], h, s):.4f} contre v5 "
                      f"{f1(E['v5'], h, s5):.4f} (seuil {s5}) : gain {gd:+.4f} (contre v5 à 0,30 : {g30:+.4f}) ; "
                      f"gain du choix plein sur ce jeu {gp:+.4f}")
    if gains_d:
        lignes.append(f"gain moyen hors échantillon {np.mean(gains_d):+.4f} contre {np.mean(gains_p):+.4f} en réglage plein "
                      f"(optimisme {np.mean(gains_p) - np.mean(gains_d):+.4f})")
    (OUT / f"{a.sortie}.json").write_text(json.dumps(dict(plein=plein, par_jeu=out), ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / f"{a.sortie}.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))


if __name__ == "__main__":
    main()
