#!/usr/bin/env python3
"""Juge comptage, 14/11/2026 : DEUXIÈME AVIS sur un juge relu, par le code du Contrôleur (indépendant de celui des agents).

- Candidats : fonction `candidat` de scripts/controle_1311_c_recalcul.py (réécriture des aiguillages par le Contrôleur,
  sans code des agents), specs gelées out/controle_nuit_1311/specs_c_kaggle_c13e.json et specs_c_banc_0030.json ;
  appariement : `apparier` du même fichier (hongrois, 20 px, non-mères ignorées).
- Cartes v3, v4, v5 : celles calculées la NUIT DERNIÈRE par le code du Contrôleur du 12/11
  (out/controle_nuit_1112/juge_c/cache_<jeu>, mêmes ONNX : SHA-256 identiques dans les deux listes gelées) ;
  cartes c13e : mon cache de la mesure principale (seule pièce partagée). Le script compare aussi, image par image, la
  carte v5 de la nuit dernière à celle de ce soir.
- Le garde-fou `garde` du Contrôleur n'est pas appelé (je ne passe pas par sa fonction `items`) : les éléments viennent
  de bc.jeu (mêmes lectures de tuiles.csv / zones.csv que la mesure principale).
Aucun réglage ; sortie : out/controle_nuit_1311/juge_c/second_avis_<jeu>.json.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_1311_c_second_avis.py --jeu cg
"""
import argparse
import json
import os
import sys
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import numpy as np  # noqa: E402

import controle_1311_c_recalcul as R  # noqa: E402
import v6_banc_commun as bc  # noqa: E402

OUT = RACINE / "out/controle_nuit_1311"
SORTIE = OUT / "juge_c"
HIER = RACINE / "out/controle_nuit_1112/juge_c"
SPECS = {"v5_030": {"type": "seul", "modele": "v5"},
         **json.loads((OUT / "specs_c_kaggle_c13e.json").read_text(encoding="utf-8")),
         **json.loads((OUT / "specs_c_banc_0030.json").read_text(encoding="utf-8"))}
JEU = None
_C = {}


def carte(modele, jeu, nom, variante="base"):
    """Remplace R.carte : v3 / v4 / v5 du cache du 12/11 (code du Contrôleur), c13e de mon cache de ce soir."""
    assert variante == "base"
    if JEU == "vierge":
        assert modele in ("v5", "c13e")
        p = SORTIE / "vierge" / "cache_vierge" / f"{modele}_base_vierge"
    elif modele == "c13e":
        p = SORTIE / f"cache_{JEU}" / f"c13e_base_{JEU}"
    else:
        p = HIER / f"cache_{JEU}" / f"{modele}_base_{'neg' if JEU == 'neg_test' else 'jeu'}"
    cle = (modele, JEU)
    if cle not in _C:
        _C[cle] = (np.memmap(p.with_suffix(".f32"), dtype="float32", mode="r"), json.loads(p.with_suffix(".json").read_text()))
    mm, idx = _C[cle]
    a, h, w = idx[nom]
    return np.asarray(mm[a:a + h * w], dtype="float64").reshape(h, w)


def main():
    global JEU
    ap = argparse.ArgumentParser()
    ap.add_argument("--jeu", required=True, choices=["segmento", "cg", "banano", "neg_test", "vierge"])
    ap.add_argument("--candidats", nargs="+", default=["v5_030", "E5p90b_c13e_d-0.1", "CB13_trous_b0.20_reseau"])
    a = ap.parse_args()
    JEU = a.jeu
    R.carte = carte
    if a.jeu == "vierge":
        assert set(a.candidats) <= {"v5_030", "E5p90b_c13e_d-0.1"}
        items = bc._tuiles("test_vierge", D=RACINE / "data/roboflow_nuit_1112/comptage/banana_trees_kp/prepare")
        principal = json.loads((SORTIE / "vierge" / "mesure_vierge.json").read_text(encoding="utf-8"))["candidats"]
        ecart = None                 # pas de carte du 12/11 : mêmes cartes que la mesure principale
    else:
        items = bc.jeu(a.jeu)
        principal = json.loads((SORTIE / f"mesure_{a.jeu}.json").read_text(encoding="utf-8"))["candidats"]
        # cartes v5 : nuit dernière contre ce soir
        bc.CACHE = SORTIE / f"cache_{a.jeu}"
        ecart = max(float(np.abs(carte("v5", a.jeu, e["nom"]) - bc.carte_cache("v5", "base", a.jeu, e["nom"])).max()) for e in items)
    res = {"jeu": a.jeu, "ecart_max_cartes_v5_hier_ce_soir": ecart, "candidats": {}}
    print(f"{a.jeu} : écart maximal des cartes v5 (12/11 contre ce soir) : {ecart}", flush=True)
    for n in a.candidats:
        vp = fp = fn = det = reels = arbres = 0
        for e in items:
            xy, sc = R.candidat(SPECS[n], a.jeu, e["nom"])
            if e["zone"] is not None:
                x0, y0, x1, y1 = e["zone"]
                g = (xy[:, 0] >= x0) & (xy[:, 0] <= x1) & (xy[:, 1] >= y0) & (xy[:, 1] <= y1)
            elif e["masque"] is not None:
                mx, my, mr = e["masque"]
                g = (xy[:, 0] - mx) ** 2 + (xy[:, 1] - my) ** 2 <= mr ** 2
            else:
                g = np.ones(len(xy), bool)
            d = xy[g][sc[g] >= 0.30]
            reels += len(e["pts"]); arbres += e["n_autres"]; det += len(d)
            if a.jeu == "neg_test":
                fp += len(d)
            else:
                x, y, z = R.apparier(d, e["pts"], e["ign"])
                vp += x; fp += y; fn += z
        r = dict(vp=vp, fp=fp, fn=fn, detectes=det, reels=reels, arbres=arbres)
        P = principal[n]
        if a.jeu == "neg_test":
            r["taux"] = fp / max(arbres, 1)
            r["identique_principal"] = fp == P["fp"]
            print(f"{n:28s} fausses {fp} / {arbres} ({r['taux']:.2%}) ; principal {P['fp']} -> {'identique' if r['identique_principal'] else 'ÉCART'}", flush=True)
        else:
            p = vp / (vp + fp) if vp + fp else 0.0
            rc = vp / (vp + fn) if vp + fn else 0.0
            r.update(p=p, r=rc, f1=2 * p * rc / (p + rc) if p + rc else 0.0, err=abs(det / reels - 1))
            r["identique_principal"] = (vp, fp, fn, det) == (P["vp"], P["fp"], P["fn"], P["detectes"])
            print(f"{n:28s} P {p:.4f} R {rc:.4f} F1 {r['f1']:.4f} ; {det} / {reels} ; principal F1 {P['f1']:.4f} ({P['detectes']}) -> "
                  f"{'identique' if r['identique_principal'] else 'ÉCART'}", flush=True)
        res["candidats"][n] = r
    (SORTIE / ("vierge/" if a.jeu == "vierge" else "") / f"second_avis_{a.jeu}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
