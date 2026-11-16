#!/usr/bin/env python3
"""Contrôle de non-régression ReforesTree du second tour (agent C-kaggle2, 15/11 ; avenant_tour2_kaggle.md).

Tuiles rt_* de data/drone/comptage_v5_5cm dont partie = ensemble = « train » et facteur = 1 (vérifié par assert, comme
scripts/rendu_preparer.py) : ce sont des données d'entraînement, aucun juge n'est lu. Pics du v5 au seuil 0,30 contre
pics du candidat à son seuil 5.3 (cartes `bc.cartes_image(..., "base")`, pics `bc.pics`, fenêtre 7) ; appariement un à
un (hongrois) à 20 px au plus (1 m à 5 cm). Règle : le candidat retrouve au moins 95 % des pieds du v5.
Pour information seulement : rappel des mères annotées (même appariement) pour les deux.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/c15b_controle_rt.py c15b_a 0.35 [--onnx chemin]
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.optimize import linear_sum_assignment  # noqa: E402
from scipy.spatial.distance import cdist  # noqa: E402

import v6_banc_commun as bc  # noqa: E402

D = RACINE / "data/drone/comptage_v5_5cm"
SORTIE = RACINE / "out/comptage/jour_1511/kaggle2"
FICHIER = SORTIE / "controle_rt.json"
RAYON, SEUIL_V5, FILS = 20.0, 0.30, 2


def tuiles_rt():
    t = pd.read_csv(D / "tuiles.csv")
    r = t[t.groupe.str.startswith("rt_")].reset_index(drop=True)
    assert len(r) and (r.partie == "train").all() and (r.ensemble == "train").all(), "tuile ReforesTree hors entraînement"
    assert (r.facteur.astype(float) == 1.0).all(), "tuile ReforesTree rééchantillonnée"
    assert not r.image_path.str.startswith("cg/").any()
    return r


def apparier(a, b):
    """Nombre de points de a retrouvés dans b (un à un, distance <= RAYON)."""
    if not len(a) or not len(b):
        return 0
    d = cdist(a, b)
    li, co = linear_sum_assignment(np.where(d <= RAYON, d, 1e6))
    return int((d[li, co] <= RAYON).sum())


def detections(onnx, seuil, r):
    import onnxruntime as ort
    o = ort.SessionOptions(); o.intra_op_num_threads = FILS; o.inter_op_num_threads = 1
    s = ort.InferenceSession(str(onnx), o, providers=["CPUExecutionProvider"])
    out = {}
    for nom in r.image_path:
        xy, sc = bc.pics(bc.cartes_image(s, bc.lire(D / "images" / nom), "base")["base"])
        out[nom] = xy[sc >= seuil].tolist()
    return out


def main():
    nom, seuil = sys.argv[1], float(sys.argv[2])
    onnx = sys.argv[sys.argv.index("--onnx") + 1] if "--onnx" in sys.argv else f"modeles/comptage_jour_1511/centres_5cm_{nom}.onnx"
    r = tuiles_rt()
    E = json.loads(FICHIER.read_text(encoding="utf-8")) if FICHIER.exists() else {}
    t0 = time.time()
    if "v5_detections" not in E:
        E["v5_detections"] = detections(RACINE / "modeles/centres_5cm_v5.onnx", SEUIL_V5, r)
    det = detections(RACINE / onnx, seuil, r)
    obj = pd.read_csv(D / "objets.csv")
    obj = obj[obj.image_path.isin(set(r.image_path)) & (obj.type == "mere")]
    n_v5 = retrouves = n_cand = vp_v5 = vp_c = 0
    par_site = {}
    for g, nom_t in zip(r.groupe, r.image_path):
        a, b = np.asarray(E["v5_detections"][nom_t]).reshape(-1, 2), np.asarray(det[nom_t]).reshape(-1, 2)
        k = apparier(a, b)
        n_v5 += len(a); retrouves += k; n_cand += len(b)
        ps = par_site.setdefault(g, [0, 0]); ps[0] += len(a); ps[1] += k
        m = obj[obj.image_path == nom_t][["cx", "cy"]].to_numpy("float64").reshape(-1, 2)
        vp_v5 += apparier(m, a); vp_c += apparier(m, b)
    taux = retrouves / max(n_v5, 1)
    E[nom] = dict(seuil=seuil, onnx=str(onnx), tuiles=len(r), pieds_v5=n_v5, retrouves=retrouves, taux=round(taux, 4),
                  passe=bool(taux >= 0.95), detections_candidat=n_cand,
                  par_site={g: dict(pieds_v5=v[0], retrouves=v[1], taux=round(v[1] / max(v[0], 1), 4)) for g, v in par_site.items()},
                  info_meres_annotees=int(len(obj)), info_rappel_meres_v5=round(vp_v5 / max(len(obj), 1), 4),
                  info_rappel_meres_candidat=round(vp_c / max(len(obj), 1), 4), heure=time.strftime("%H:%M"))
    FICHIER.write_text(json.dumps(E, indent=1, ensure_ascii=False), encoding="utf-8")
    e = E[nom]
    print(f"{time.strftime('%H:%M:%S')} {nom} (seuil {seuil}, {time.time() - t0:.0f} s) : {e['retrouves']} / {e['pieds_v5']} pieds du v5 "
          f"retrouvés ({e['taux']:.2%}) -> {'passe' if e['passe'] else 'ÉCHOUE'} ; détections {n_cand} ; par site "
          + ", ".join(f"{g} {v['taux']:.2%}" for g, v in e["par_site"].items())
          + f" | info rappel des mères annotées : v5 {e['info_rappel_meres_v5']:.3f}, candidat {e['info_rappel_meres_candidat']:.3f}", flush=True)


if __name__ == "__main__":
    main()
