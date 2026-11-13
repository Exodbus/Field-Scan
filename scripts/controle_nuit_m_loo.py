#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : optimisme des finalistes maladies par validation croisée « un jeu dehors ».

Espace de recherche reconstruit (proche de celui de M-banc, environ 1 000 configurations) : poids du mélange
géométrique (v10b seule, v10b+soupe, à trois 1:1:1, 2:2:1, 2:1:1, v10b+v2), lecture de la v10b (384, 384+512,
2 x 2 : 2 plus fortes, maximum, « ou bruité »), branche loin (v2 seule ou « v2 ou proche »), seuil t de 0,50 à 0,84
par 0,02. Pour chaque jeu de réglage laissé dehors, le choix est refait sur les 3 autres avec la règle de M-banc
(contraintes « finaliste » applicables aux jeux présents, plateau : les deux seuils voisins aussi admissibles,
coût moyen le plus bas), puis mesuré sur le jeu dehors. Deux niveaux :
  A. tout l'espace est re-choisi (famille + seuil) ;
  B. la famille de chaque finaliste est fixée, seul t est re-choisi.
Aucun juge ni test vierge n'est lu (mêmes fichiers que controle_nuit_m_recalcul.py).
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_m_loo.py
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import controle_nuit_m_recalcul as R  # noqa: E402

POIDS = {"v10b": None, "v10b+soupe": (1, 1, 0), "trois": (1, 1, 1), "221": (2, 2, 1), "211": (2, 1, 1), "v10b+v2": (1, 0, 1)}
LECT = ["384", "384+512", "g2_2fortes", "g2_max", "g2_ou"]
TS = [round(x, 2) for x in np.arange(0.50, 0.845, 0.02)]
FAM_FINALISTES = {"F1": ("trois", "g2_2fortes", True), "F2": ("trois", "384+512", True), "F3": ("trois", "384", True),
                  "reserve": ("v10b+soupe", "384", True)}
T_FINALISTES = {"F1": 0.70, "F2": 0.72, "F3": 0.74, "reserve": 0.68}


def main():
    jeux = R.charger()
    ref = R.evaluer(jeux, **R.REF)
    # table[(poids, lecture, loin_ou, t)][jeu] = mesure
    table = {}
    for (pn, w), lec in itertools.product(POIDS.items(), LECT):
        if w is None and lec != "384":
            pass
        ps = {j: R.ps_proche(jeux[j], lec, w) for j in R.JEUX}
        for lo in (False, True):
            for t in TS:
                table[(pn, lec, lo, t)] = {j: R.mesure(jeux[j], R.alertes(jeux[j], ps[j], t, lo)) for j in R.JEUX}
    n_conf = len(table)

    def admissible(m, quels):
        if np.mean([m[j]["cout"] for j in quels]) > np.mean([ref[j]["cout"] for j in quels]) - 1.0:
            return False
        if "validation" in quels and not (m["validation"]["msa"] <= 14 and m["validation"]["sea"] <= 77):
            return False
        return all(100 * (m[j]["msa"] / m[j]["nm"] - ref[j]["msa"] / ref[j]["nm"]) <= 2.0
                   for j in quels if j != "validation")

    def choisir(quels, familles):
        best = None
        for (pn, lec, lo) in familles:
            for i, t in enumerate(TS):
                if i == 0 or i == len(TS) - 1:
                    continue
                if not all(admissible(table[(pn, lec, lo, TS[k])], quels) for k in (i - 1, i, i + 1)):
                    continue
                c = float(np.mean([table[(pn, lec, lo, t)][j]["cout"] for j in quels]))
                if best is None or c < best[0]:
                    best = (c, (pn, lec, lo, t))
        return best

    toutes = sorted({k[:3] for k in table})
    out = {"n_configurations": n_conf, "reference": {j: ref[j]["cout"] for j in R.JEUX}}
    lignes = [f"configurations : {n_conf} ; référence (coût par jeu) : "
              + ", ".join(f"{j} {ref[j]['cout']:.2f}" for j in R.JEUX)]
    plein = choisir(R.JEUX, toutes)
    out["choix_plein"] = plein
    lignes.append(f"choix sur les 4 jeux (espace entier) : {plein}")
    # A. tout re-choisi
    resA = {}
    for h in R.JEUX:
        quels = [j for j in R.JEUX if j != h]
        c, k = choisir(quels, toutes)
        mh = table[k][h]
        mp = table[plein[1]][h]
        resA[h] = dict(choix=k, cout_dehors=mh["cout"], cout_dehors_choix_plein=mp["cout"], ref=ref[h]["cout"],
                       gain_dehors=ref[h]["cout"] - mh["cout"], gain_plein=ref[h]["cout"] - mp["cout"],
                       msa=mh["msa"], sea=mh["sea"])
        lignes.append(f"A, {h} dehors : choix {k} ; coût dehors {mh['cout']:.2f} (choix plein {mp['cout']:.2f}, "
                      f"réf. {ref[h]['cout']:.2f}) ; ratées {mh['msa']}/{mh['nm']}, fausses alertes {mh['sea']}/{mh['ns']}")
    gA = np.mean([v["gain_dehors"] for v in resA.values()])
    gP = np.mean([v["gain_plein"] for v in resA.values()])
    out["A"] = dict(par_jeu=resA, gain_moyen_dehors=gA, gain_moyen_plein=gP)
    lignes.append(f"A : gain moyen sur le jeu dehors {gA:.2f} points contre {gP:.2f} en réglage plein "
                  f"(optimisme {gP - gA:.2f})")
    # B. famille fixée, t re-choisi
    out["B"] = {}
    for nom, fam in FAM_FINALISTES.items():
        k0 = (*fam, T_FINALISTES[nom])
        rb = {}
        for h in R.JEUX:
            quels = [j for j in R.JEUX if j != h]
            ch = choisir(quels, [fam])
            if ch is None:
                rb[h] = dict(choix=None)
                continue
            k = ch[1]
            rb[h] = dict(t=k[3], cout_dehors=table[k][h]["cout"], cout_officiel=table[k0][h]["cout"], ref=ref[h]["cout"],
                         sea=table[k][h]["sea"], msa=table[k][h]["msa"])
        ok = [v for v in rb.values() if v.get("t") is not None]
        gd = float(np.mean([v["ref"] - v["cout_dehors"] for v in ok]))
        go = float(np.mean([v["ref"] - v["cout_officiel"] for v in ok]))
        out["B"][nom] = dict(par_jeu=rb, gain_dehors=gd, gain_officiel=go)
        lignes.append(f"B, {nom} : t re-choisi par jeu dehors " + ", ".join(
            f"{h}:{v.get('t')}→{v.get('cout_dehors', float('nan')):.2f}" for h, v in rb.items())
            + f" ; gain moyen dehors {gd:.2f} contre {go:.2f} au seuil officiel (optimisme du seuil {go - gd:.2f})")
    # C. gain des seules familles, par jeu : F1 - F3 et F3 - réserve hors échantillon (B)
    (R.OUT / "m_loo.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (R.OUT / "m_loo.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))


if __name__ == "__main__":
    main()
