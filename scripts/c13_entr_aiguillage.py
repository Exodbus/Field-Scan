#!/usr/bin/env python3
"""CE2 dans l'aiguillage E5p90b (agent C-entraîneur, nuit du 13/11) : la branche « petits » (v3 + v4) est remplacée
par un modèle de la nuit, mesuré sur le réglage par le code du banc (scripts/v6_banc_commun.py, v6_banc_candidats.py,
importés sans modification). Cartes v3, v4, v5 : cache du banc (out/comptage_v6/banc/cache) ; cartes des modèles
c13* : out/comptage/nuit_1311/kaggle/cache (écrites par scripts/c13_entr_mesure.py --cache). Aucun juge.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c13_entr_aiguillage.py c13d [c13e ...]
Sortie : out/comptage/nuit_1311/kaggle/aiguillage.csv (une ligne par candidat et seuil) et le retenu (règle 5.3).
"""
import os
import sys
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import v6_banc_commun as bc  # noqa: E402
import v6_banc_candidats as ca  # noqa: E402

MON_CACHE = RACINE / "out/comptage/nuit_1311/kaggle/cache"
_orig = bc.chemin_cache
CM = os.environ.get("C13_CM")          # réglage dégradé : cartes <modele>_d<CM>_<jeu> (scripts/c13_entr_mesure.py --cm CM --cache)


def _chemin(modele, variante, nom_jeu):
    if CM:
        return MON_CACHE / f"{modele}_d{CM}_{nom_jeu}"
    return MON_CACHE / f"{modele}_{variante}_{nom_jeu}" if modele.startswith("c13") else _orig(modele, variante, nom_jeu)


bc.chemin_cache = _chemin
JEUX = ["dense", "plantain", "jeunes", "mm", "btd_val"]
E5 = dict(tau=0.55, decalage=0.1)


DECALAGES = [float(x) for x in os.environ.get("C13_DEC", "0.1,0.0").split(",")]   # variantes écrites avant mesure (journal)


def candidats(modeles):
    c = {} if os.environ.get("C13_DEC") else {"E5p90b (v3+v4)": ("aiguillage_p90", dict(E5, petit_spec=["melange", {"membres": ["v3", "v4"], "mode": "moyenne"}], grand_spec=None))}
    for m in modeles:
        for d in DECALAGES:
            c[f"E5p90b_{m}_d{d}"] = ("aiguillage_p90", dict(tau=0.55, decalage=d, petit_spec=["seul", {"modele": m}], grand_spec=None))
    return c


def main_degrade():
    """Réglage dégradé : 5 jeux sans val_negatifs ; lignes par seuil (le seuil du candidat est celui choisi à 5 cm)."""
    lignes = []
    for nom, (fab, reg) in candidats(sys.argv[1:]).items():
        f = ca.construire(fab, reg)
        m = {j: bc.mesurer_jeu(f, j) for j in JEUX}
        for s_ in bc.SEUILS:
            l = dict(candidat=nom, cm=CM, seuil=s_, **{f"f1_{j}": round(m[j][s_]["f1"], 4) for j in JEUX})
            l["moyenne"] = round(sum(l[f"f1_{j}"] for j in JEUX) / 5, 4)
            l["err_compte"] = round(sum(m[j][s_]["err_compte"] for j in JEUX) / 5, 4)
            lignes.append(l)
            if s_ in (0.2, 0.3):
                print(l, flush=True)
    pd.DataFrame(lignes).to_csv(RACINE / f"out/comptage/nuit_1311/kaggle/aiguillage_{'_'.join(sys.argv[1:])}{os.environ.get('C13_DEC', '')}_{CM}cm.csv", index=False)


def main():
    if CM:
        return main_degrade()
    lignes, retenus = [], []
    for nom, (fab, reg) in candidats(sys.argv[1:]).items():
        f = ca.construire(fab, reg)
        m = bc.mesurer(f, JEUX)
        ret, L = bc.resume(m, JEUX)
        for l in L:
            l["candidat"] = nom
            l["moyenne_4"] = sum(l[f"f1_{j}"] for j in JEUX[:4]) / 4
        lignes += L
        retenus.append(dict(ret, candidat=nom, moyenne_4=sum(ret[f"f1_{j}"] for j in JEUX[:4]) / 4) if ret else dict(candidat=nom))
        print(nom, "->", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in (retenus[-1]).items()}, flush=True)
    sortie = RACINE / "out/comptage/nuit_1311/kaggle"
    pd.DataFrame(lignes).to_csv(sortie / f"aiguillage_{'_'.join(sys.argv[1:])}{os.environ.get('C13_DEC', '')}.csv", index=False)
    pd.DataFrame(retenus).to_csv(sortie / f"aiguillage_{'_'.join(sys.argv[1:])}{os.environ.get('C13_DEC', '')}_retenus.csv", index=False)


if __name__ == "__main__":
    main()
