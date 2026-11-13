#!/usr/bin/env python3
"""Juge comptage, nuit du 12 au 13 novembre 2026 : mesure PRINCIPALE des finalistes gelés sur un juge ou sur le test vierge.

Reprend telles quelles les fonctions du Contrôleur (scripts/controle_nuit_c_appliquer.py : lecture des jeux, calcul des
cartes ONNX avec SHA-256 vérifiés, 2 fils ; scripts/controle_nuit_c_recalcul.py : candidats, pics 7 x 7, appariement
hongrois à 20 px, non-mères ignorées, disque DJI, zones). Ajoute seulement : précision et rappel (vp, fp, fn), part des
images aiguillées vers la branche « petits » d'E5p90b, et ne mesure QUE les candidats demandés (liste gelée + v5).
Chaque jeu ne se lit qu'une fois : le script refuse d'écrire une sortie qui existe déjà.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_nuit_c_mesure.py --jeu banano --candidats E10_moy_v6e+v5 v6f v5_030 v5_020
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import controle_nuit_c_appliquer as A  # noqa: E402
import controle_nuit_c_recalcul as R  # noqa: E402

SORTIE = RACINE / "out/controle_nuit_1112/juge_c"
D5 = RACINE / "data/drone/comptage_v5_5cm"
DV = RACINE / "data/roboflow_nuit_1112/comptage/banana_trees_kp/prepare"
JEUX = {  # nom : (dossier, ensemble, sans bananier)
    "segmento": (D5, "test_dense", False),
    "banano": (D5, "test_banano", False),
    "cg": (D5 / "cg", "", False),
    "neg_test": (D5, "test_negatifs", True),
    "vierge": (DV, "test_vierge", False),
}


def modeles_de(spec):
    t = spec["type"]
    if t == "seul":
        return {spec["modele"]}
    if t == "melange":
        return set(spec["membres"])
    if t == "union":
        return {m for m, _ in spec["membres"]}
    if t == "p90":
        return {"v5"} | modeles_de(spec["petit"]) | modeles_de(spec["grand"])
    raise KeyError(t)


def aiguillee(spec, nom_jeu, nom):
    """Même test que R.candidat pour le type p90 : vrai si l'image part vers la branche « petits »."""
    _, sc = R.maxima(R.carte("v5", nom_jeu, nom), spec.get("smin", 0.15))
    return bool(len(sc) >= 1 and float(np.quantile(sc, spec.get("q", 0.90))) < spec["tau"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jeu", required=True, choices=sorted(JEUX))
    ap.add_argument("--candidats", nargs="+", required=True)
    a = ap.parse_args()
    sortie = SORTIE / f"mesure_{a.jeu}.json"
    assert not sortie.exists(), f"{sortie} existe déjà : ce jeu a déjà été lu"
    dossier, ensemble, negatif = JEUX[a.jeu]
    nom_jeu = "neg" if negatif else "jeu"
    cache = SORTIE / f"cache_{a.jeu}"
    items = A.items_generiques(dossier, ensemble)
    specs = {n: A.FINALISTES[n] for n in a.candidats}
    modeles = sorted(set().union(*(modeles_de(s) for s, _ in specs.values())))
    t0 = time.time()
    print(f"{a.jeu} : {len(items)} éléments, {len({e['nom'] for e in items})} images ; modèles {modeles}", flush=True)
    A.cartes(dossier, items, cache, modeles, nom_jeu)
    print(f"cartes prêtes en {time.time() - t0:.0f} s", flush=True)
    R.CACHE, R.items = cache, (lambda jeu: items)
    res = {"jeu": a.jeu, "dossier": str(dossier.relative_to(RACINE).as_posix()), "ensemble": ensemble,
           "n_elements": len(items), "n_images": len({e["nom"] for e in items}), "modeles": modeles, "candidats": {}}
    for nom, (spec, s) in specs.items():
        vp = fp = fn = det = 0
        reels = arbres = 0
        for e in items:
            xy, sc = R.candidat(spec, nom_jeu, e["nom"])
            if e["zone"] is not None:
                x0, y0, x1, y1 = e["zone"]
                g = (xy[:, 0] >= x0) & (xy[:, 0] <= x1) & (xy[:, 1] >= y0) & (xy[:, 1] <= y1)
            elif e["masque"] is not None:
                mx, my, mr = e["masque"]
                g = (xy[:, 0] - mx) ** 2 + (xy[:, 1] - my) ** 2 <= mr ** 2
            else:
                g = np.ones(len(xy), bool)
            d = xy[g][sc[g] >= s]
            reels += len(e["pts"]); arbres += e["arbres"]; det += len(d)
            if negatif:
                fp += len(d)
            else:
                a1, b1, c1 = R.apparier(d, e["pts"], e["ign"])
                vp += a1; fp += b1; fn += c1
        r = dict(seuil=s, detectes=int(det))
        if negatif:
            r.update(fp=int(fp), arbres=int(arbres), taux=fp / max(arbres, 1))
        else:
            p = vp / (vp + fp) if vp + fp else 0.0
            rc = vp / (vp + fn) if vp + fn else 0.0
            r.update(vp=int(vp), fp=int(fp), fn=int(fn), reels=int(reels), p=p, r=rc,
                     f1=2 * p * rc / (p + rc) if p + rc else 0.0, err=abs(det / reels - 1) if reels else float("nan"))
        # contrôle : la fonction de mesure du Contrôleur, telle quelle, doit donner le même F1 / la même erreur
        if s in R.SEUILS:
            m = R.mesurer(spec, nom_jeu)[s]
            if negatif:
                assert m["fp"] == r["fp"], (nom, m, r)
            else:
                assert abs(m["f1"] - r["f1"]) < 1e-12 and abs(m["err"] - r["err"]) < 1e-12, (nom, m, r)
            r["controle_mesurer"] = "identique"
        if spec["type"] == "p90":
            ag = [aiguillee(spec, nom_jeu, e["nom"]) for e in items]
            par_image = {}
            for e, x in zip(items, ag):
                par_image[e["nom"]] = x
            r.update(aiguillees=int(sum(ag)), n_elements=len(items), part_aiguillee=sum(ag) / len(items),
                     aiguillees_images=int(sum(par_image.values())), n_images=len(par_image),
                     part_aiguillee_images=sum(par_image.values()) / len(par_image))
        res["candidats"][nom] = r
        if negatif:
            print(f"{nom:24s} seuil {s:.2f} : fausses {r['fp']} / {r['arbres']} arbres ({r['taux']:.2%}) ; détectés {det}", flush=True)
        else:
            print(f"{nom:24s} seuil {s:.2f} : P {r['p']:.4f} R {r['r']:.4f} F1 {r['f1']:.4f} ; {det} / {reels} ; "
                  f"erreur de compte {r['err']:.3f}" + (f" ; aiguillées {r['aiguillees']}/{len(items)}" if 'aiguillees' in r else ""), flush=True)
        if negatif and "aiguillees" in r:
            print(f"   aiguillées {r['aiguillees']}/{len(items)}", flush=True)
    res["duree_s"] = time.time() - t0
    sortie.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
