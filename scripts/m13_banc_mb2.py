#!/usr/bin/env python3
"""MB2 (vitesse) : F1 avec morceaux lus seulement là où l'alerte en dépend (bornes exactes), et sans soupe ni v10b pour
les photos « loin » où la v2 alerte. Grille écrite dans docs/nuit_2026-11-13/journal_m_banc.md (23 h 52).

Variante « F1_bornes » (réponses, sur des probabilités déjà calculées) :
  1. photo « loin » (p_loin >= 0,5) où la v2 alerte : réponse de la v2 (comme F1) ; soupe et v10b inutiles ;
  2. sinon, bornes : décision du lecteur proche de F1 avec morceaux « saine 100 % » et « malade 100 % » ;
     même alerte -> réponse du lecteur proche SANS morceaux (mélange à trois, seuil 0,70 ; son alerte est forcément
     la même, car P(malade) de la v10b entière est entre les deux bornes) ;
     alerte différente -> morceaux lus, réponse de F1.
Les alertes sont donc celles de F1 par construction ; seuls les noms (maladie nommée, « malade, non identifiée »,
« à vérifier ») peuvent changer, sur les photos dont les morceaux ne sont pas lus.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_banc_mb2.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m13_banc_commun as C  # noqa: E402
from fieldscan.modules import maladies  # noqa: E402

AL = list(C.ALERTE)


def masques(d):
    """(lv, dep) : photos « loin » où la v2 alerte ; photos dont l'alerte dépend des morceaux (hors lv)."""
    lv = d["loin"] & np.isin(d["r_loin"], AL)
    n = len(lv)
    G0 = np.tile(np.array([1.0, 0, 0, 0]), (n, 4, 1))
    G1 = np.tile(np.array([0.0, 0, 1.0, 0]), (n, 4, 1))
    a0 = np.isin(C.f1(d, G0), AL)
    a1 = np.isin(C.f1(d, G1), AL)
    return lv, (a0 != a1) & ~lv


def f1_bornes(d, G2):
    """Réponses de la variante ; G2 n'est utilisé que sur les photos « dep »."""
    lv, dep = masques(d)
    sans = maladies.decider_melange(d["P10"], d["Pso"], d["Pv2"], d["p_loin"], None, C.M_PROCHE_F1, C.M_LOIN, True)[0]
    avec = C.f1(d, G2)
    return np.where(dep, avec, sans), lv, dep


if __name__ == "__main__":
    jeux = C.charger(roamer=False)
    res = {}
    for j in C.JEUX5:
        d = jeux[j]
        a0, rf1, inc = C.bornes(d, C.f1)
        assert not inc.any()
        G = C.remplir(d["G2"], 0)   # morceaux connus partout où dep (vérifié ci-dessous)
        rv, lv, dep = f1_bornes(d, G)
        assert not np.isnan(d["G2"][dep, :, 0]).any(), j
        av = np.isin(rv, AL)
        diff_alerte = int((av != a0).sum())
        assert diff_alerte == 0, (j, diff_alerte)
        connu = ~np.isnan(d["G2"][:, :, 0]).any(1)   # noms de F1 exacts seulement là où ses morceaux sont connus
        rf1_ex = C.f1(d, G)
        dn = connu & (rv != rf1_ex)
        res[j] = dict(n=len(rv), loin_v2_alerte=int(lv.sum()), morceaux_lus=int(dep.sum()),
                      morceaux_lus_F1_installe=int((~lv).sum()), diff_alertes=diff_alerte,
                      noms_comparables=int(connu.sum()), noms_differents=int(dn.sum()),
                      changements=pd.Series([f"{a} -> {b}" for a, b in zip(rf1_ex[dn], rv[dn])]).value_counts().to_dict(),
                      sig_nommee_F1=int((d["sig"] & connu & (rf1_ex == "cercosporiose_noire")).sum()),
                      sig_nommee_variante=int((d["sig"] & connu & (rv == "cercosporiose_noire")).sum()))
        print(j, json.dumps(res[j], ensure_ascii=False), flush=True)
    tot = {k: sum(res[j][k] for j in res) for k in ("n", "loin_v2_alerte", "morceaux_lus", "morceaux_lus_F1_installe",
                                                    "diff_alertes", "noms_comparables", "noms_differents")}
    res["total"] = tot
    print("total", tot)
    (C.SORTIE / "mb2_bornes.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
