#!/usr/bin/env python3
"""Juge comptage, 15/11/2026 (plan de la journée, section 2 ; règle du plan du 13/11, section 5.3) : UNE lecture des
juges relus (segmento est, CG mères seules, banano_dense, test_negatifs) pour la liste gelée. Jamais banana_trees_kp.

Mesure reprise À L'IDENTIQUE de scripts/juge_1311_c_mesure.py (juge du 14/11) : code du banc importé sans modification
(scripts/v6_banc_commun.py : bc.jeu pour lire les jeux, bc.ecrire_cache pour les cartes ONNX à 2 fils, pics fenêtre 7,
bc.mesurer_jeu = rayon 20 px, appariement un-à-un, non-mères ignorées, disque DJI, zones = protocole v5), mêmes comptes
par image, même contrôle somme des images = mesure. Seul changement : la liste des candidats.

Candidats (définitions des fichiers de finalistes gelés, empreintes dans out/controle_jour_1511/liste_gelee.md) :
  - v5_030      : v5 seul, seuil 0,30 (référence, contrôle contre le 14/11) ;
  - CC1_v5h_50  : moyenne 0,5 / 0,5 des cartes de probabilité du v5 et de c13h sur la grille au quart, pics fenêtre 7,
                  seuil 0,30 (f_melange de scripts/c14_essais.py, recopiée à l'identique) ;
  - c15d        : réseau c15d seul (ca.f_seul, comme notebooks/c15_mesure.py), seuil 0,35.
Cartes écrites dans MON cache (out/controle_jour_1511/juge_c/cache_<jeu>). Le v5 est recalculé et comparé, carte par
carte, au cache du juge du 14/11 (out/controle_nuit_1311/juge_c/cache_<jeu>). Option --v5_hier : pour test_negatifs
seulement, les cartes du v5 sont LUES dans le cache du 14/11 (même ONNX, SHA-256 vérifié) au lieu d'être recalculées,
faute de temps ; c'est écrit dans la sortie.
Chaque jeu n'est lu qu'une fois : le script refuse d'écrire une sortie qui existe déjà.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_1511_c_mesure.py --jeu cg
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import numpy as np  # noqa: E402

import v6_banc_commun as bc  # noqa: E402
import v6_banc_candidats as ca  # noqa: E402

SORTIE = RACINE / "out/controle_jour_1511/juge_c"
HIER = RACINE / "out/controle_nuit_1311/juge_c"
JEUX = ["segmento", "cg", "banano", "neg_test"]
FILS = 2
bc.MODELES["c13h"] = RACINE / "modeles/comptage_nuit_1311/centres_5cm_c13h.onnx"
bc.MODELES["c15d"] = RACINE / "modeles/comptage_jour_1511/centres_5cm_c15d.onnx"
EMPREINTES = {  # v5 et c15d : liste gelée du 15/11 ; c13h : aucune empreinte écrite avant, relevée ici (contrôle sur le réglage)
    "v5": "12f9b4caa5735767c454de99edf1a6616765718243555f8559c2cfcc0722f1ea",
    "c15d": "d9a7301d916c61c052a96265332f2c22bd41b4ae82ce763d3aaefcb1d8a8157e",
    "c13h": "ff26f875b0641dd5c71a5fc1d1314779e9cce7bb340bd415edb6a1d8f9bb2077",
}


def f_melange(membres, poids):
    """CC1 : moyenne arithmétique pondérée des cartes de probabilité, puis pics fenêtre 7 (copie de c14_essais.f_melange)."""
    w = np.asarray(poids, "float64"); w = w / w.sum()

    def f(ctx):
        c = sum(wi * ctx.carte(m).astype("float64") for wi, m in zip(w, membres))
        return bc.pics(c.astype("float32"))
    return f


CANDIDATS = {  # nom : (fonction, seuil, modèles)
    "v5_030": (ca.f_seul("v5"), 0.30, ["v5"]),
    "CC1_v5h_50": (f_melange(["v5", "c13h"], [0.5, 0.5]), 0.30, ["v5", "c13h"]),
    "c15d": (ca.f_seul("c15d"), 0.35, ["c15d"]),
}
V5_HIER = {"actif": False}


def chemin_cache(modele, variante, nom_jeu):
    if V5_HIER["actif"] and modele == "v5":
        return HIER / f"cache_{nom_jeu}" / f"{modele}_{variante}_{nom_jeu}"
    return bc.CACHE / f"{modele}_{variante}_{nom_jeu}"


def comparer_v5_hier(nom_jeu):
    """Cartes du v5 recalculées aujourd'hui contre celles du juge du 14/11 : même index, mêmes valeurs."""
    a, b = bc.CACHE / f"v5_base_{nom_jeu}", HIER / f"cache_{nom_jeu}" / f"v5_base_{nom_jeu}"
    ia, ib = (json.loads(p.with_suffix(".json").read_text(encoding="utf-8")) for p in (a, b))
    xa, xb = (np.fromfile(p.with_suffix(".f32"), dtype="float32") for p in (a, b))
    return dict(index_identique=ia == ib, valeurs_identiques=bool(np.array_equal(xa, xb)),
                ecart_max=float(np.abs(xa.astype("float64") - xb).max()) if xa.shape == xb.shape else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jeu", required=True, choices=JEUX)
    ap.add_argument("--v5_hier", action="store_true", help="test_negatifs : cartes du v5 lues dans le cache du 14/11")
    a = ap.parse_args()
    assert not a.v5_hier or a.jeu == "neg_test"
    SORTIE.mkdir(parents=True, exist_ok=True)
    sortie = SORTIE / f"mesure_{a.jeu}.json"
    assert not sortie.exists(), f"{sortie} existe déjà : ce jeu a déjà été lu"
    bc.CACHE = SORTIE / f"cache_{a.jeu}"
    V5_HIER["actif"] = a.v5_hier
    bc.chemin_cache = chemin_cache
    for m, h in EMPREINTES.items():
        assert hashlib.sha256(bc.MODELES[m].read_bytes()).hexdigest() == h, f"SHA-256 de {m} différent"
    t0 = time.time()
    items = bc.jeu(a.jeu)
    assert all("banana_trees_kp" not in str(e["chemin"]) for e in items)
    print(f"{time.strftime('%H:%M:%S')} {a.jeu} : {len(items)} éléments", flush=True)
    temps = {}
    for m in ["v5", "c13h", "c15d"]:
        if m == "v5" and a.v5_hier:
            temps[m] = None
            print(f"{time.strftime('%H:%M:%S')}   cartes v5 : lues dans le cache du 14/11", flush=True)
            continue
        t1 = time.time()
        bc.ecrire_cache(m, "base", a.jeu, fils=FILS)
        temps[m] = time.time() - t1
        print(f"{time.strftime('%H:%M:%S')}   cartes {m} : {temps[m]:.0f} s", flush=True)
    controle_v5 = None if a.v5_hier else comparer_v5_hier(a.jeu)
    print(f"  v5 contre le 14/11 : {controle_v5 or 'cartes du 14/11 lues'}", flush=True)
    res = {"jeu": a.jeu, "n_elements": len(items), "fils": FILS, "temps_cartes_s": temps,
           "v5_cartes": "lues dans le cache du 14/11 (même ONNX)" if a.v5_hier else "recalculées",
           "controle_v5_contre_14_11": controle_v5, "candidats": {},
           "note": "juge RELU (plan du 13/11, section 3) : lu une fois par finaliste, rien n'y est réglé"}
    brut = {}
    for n, (f0, s, _) in CANDIDATS.items():
        sorties = {}

        def f(ctx, f0=f0, sorties=sorties):
            xy, sc = f0(ctx)
            xy, sc = np.asarray(xy, "float64").reshape(-1, 2), np.asarray(sc, "float64")
            sorties[ctx.nom] = np.c_[xy, sc]
            return xy, sc

        r = bc.mesurer_jeu(f, a.jeu, items)[s]
        par_image, tot = {}, np.zeros(4, int)
        for e in items:
            d = sorties[e["nom"]]
            xy, sc = d[:, :2], d[:, 2]
            if e["zone"] is not None:
                x0, y0, x1, y1 = e["zone"]
                g = (xy[:, 0] >= x0) & (xy[:, 0] <= x1) & (xy[:, 1] >= y0) & (xy[:, 1] <= y1)
            else:
                g = bc.dans_masque(xy, e["masque"])
            det = xy[g][sc[g] >= s]
            c = (0, len(det), 0) if a.jeu.startswith("neg") else bc.compter(det, e["pts"], e["ign"])
            par_image[e["nom"]] = dict(vp=int(c[0]), fp=int(c[1]), fn=int(c[2]), det=len(det), reels=len(e["pts"]),
                                       autres_arbres=int(e["n_autres"]))
            tot += (c[0], c[1], c[2], len(det))
        if a.jeu.startswith("neg"):
            assert tot[1] == r["fp"], (n, tot, r)
        else:
            assert (tot[0], tot[1], tot[2], tot[3]) == (r["vp"], r["fp"], r["fn"], r["detectes"]), (n, tot, r)
        r = {k: (float(v) if isinstance(v, (float, np.floating)) else int(v)) for k, v in r.items()}
        r.update(seuil=s, par_image=par_image)
        res["candidats"][n] = r
        for nom, d in sorties.items():
            brut[f"{n}|{nom}"] = d.astype("float32")
        if a.jeu.startswith("neg"):
            print(f"{n:12s} seuil {s:.2f} : fausses {r['fp']} / {r['arbres']} ({r['taux']:.2%})", flush=True)
        else:
            print(f"{n:12s} seuil {s:.2f} : P {r['p']:.4f} R {r['r']:.4f} F1 {r['f1']:.4f} ; {r['detectes']} / {r['reels']} ; "
                  f"erreur {r['err_compte']:.3f}", flush=True)
    res["duree_s"] = time.time() - t0
    np.savez_compressed(SORTIE / f"detections_{a.jeu}.npz", **brut)
    sortie.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{time.strftime('%H:%M:%S')} fini en {res['duree_s']:.0f} s", flush=True)


if __name__ == "__main__":
    main()
