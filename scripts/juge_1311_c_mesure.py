#!/usr/bin/env python3
"""Juge comptage, 14/11/2026 (plan de la nuit du 13 au 14/11, sections 3 et 5.3) : mesure PRINCIPALE de la liste gelée
sur un juge relu (segmento est, CG mères seules, banano_dense, test_negatifs). Jamais banana_trees_kp.

Code des agents importé SANS modification :
  - scripts/v6_banc_commun.py (bc) : jeux (bc.jeu), cartes ONNX (bc.ecrire_cache, 2 fils), pics fenêtre 7,
    mesure bc.mesurer_jeu (rayon 20 px, appariement un-à-un, non-mères ignorées, disque DJI, zones) = protocole v5 ;
  - scripts/c13_entr_aiguillage.py (C-entraîneur) : définition du finaliste `E5p90b_c13e_d-0.1` par sa fonction
    candidats(["c13e"]) avec C13_DEC=-0.1 (fabrique aiguillage_p90 de v6_banc_candidats.py) ;
  - scripts/c13_banc_candidats.py (C-banc) : fabrique aiguillage_v2 ; réglages de `CB13_trous_b0.20_reseau` lus dans
    out/comptage/nuit_1311/banc/essais.json (SHA-256 gelé).
Seul changement d'environnement : les cartes sont écrites dans MON cache (out/controle_nuit_1311/juge_c/cache_<jeu>),
en remplaçant bc.CACHE et bc.chemin_cache (le détour de c13_entr_aiguillage vers le cache Kaggle est annulé : ce cache
n'a aucune carte de juge). Les SHA-256 des ONNX sont vérifiés contre out/controle_nuit_1311/empreintes_liste_gelee.txt.
Ajouts : part d'images aiguillées, détections par image (sorties brutes, avant zone et disque) et comptes par image.
Chaque jeu n'est lu qu'une fois : le script refuse d'écrire une sortie qui existe déjà.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_1311_c_mesure.py --jeu cg
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
os.environ.pop("C13_CM", None)
os.environ["C13_DEC"] = "-0.1"            # le finaliste gelé de C-entraîneur : décalage -0,10

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import numpy as np  # noqa: E402

import v6_banc_commun as bc  # noqa: E402
import v6_banc_candidats as ca  # noqa: E402
import c13_entr_aiguillage as ea  # noqa: E402  (remplace bc.chemin_cache : annulé plus bas)
import c13_banc_commun as cc  # noqa: E402  (remplace bc.carte_cache : retombe sur bc.chemin_cache pour les juges)
import c13_banc_candidats as cd  # noqa: E402

SORTIE = RACINE / "out/controle_nuit_1311/juge_c"
EMPREINTES = RACINE / "out/controle_nuit_1311/empreintes_liste_gelee.txt"
JEUX = ["segmento", "cg", "banano", "neg_test"]
# test vierge banana_trees_kp : seulement sur confirmation de Corentin (14/11, 19 h 47), une lecture, v5 et place 1
DV = RACINE / "data/roboflow_nuit_1112/comptage/banana_trees_kp/prepare"
PERMIS_VIERGE = {"v5_030", "E5p90b_c13e_d-0.1"}
FILS = 2
bc.MODELES["c13e"] = RACINE / "modeles/comptage_nuit_1311/centres_5cm_c13e.onnx"

E_BANC = json.loads((RACINE / "out/comptage/nuit_1311/banc/essais.json").read_text(encoding="utf-8"))
E_ENTR = ea.candidats(["c13e"])
CANDIDATS = {
    # nom : (fabrique, réglages, seuil, modèles, type d'aiguillage)
    "v5_030": ("seul", {"modele": "v5"}, 0.30, ["v5"], None),
    "E5p90b_c13e_d-0.1": (*E_ENTR["E5p90b_c13e_d-0.1"], 0.30, ["v5", "c13e"], "p90"),
    "CB13_trous_b0.20_reseau": (E_BANC["CB13_trous_b0.20_reseau"]["fabrique"], E_BANC["CB13_trous_b0.20_reseau"]["reglages"],
                                0.30, ["v3", "v4", "v5"], "v2"),
    # information seulement (consigne : effet du remplissage des trous sur CG) : A1 sans les trous
    "CB1_npet30_dens200_acc0.05_c": (E_BANC["CB1_npet30_dens200_acc0.05_c"]["fabrique"],
                                     E_BANC["CB1_npet30_dens200_acc0.05_c"]["reglages"], 0.30, ["v3", "v4", "v5"], "v2"),
}


def chemin_cache(modele, variante, nom_jeu):
    return bc.CACHE / f"{modele}_{variante}_{nom_jeu}"


def verifier_empreintes(modeles):
    att = {}
    for l in EMPREINTES.read_text(encoding="utf-8").splitlines():
        if l.strip() and not l.startswith("#"):
            h, p = l.split(None, 1)
            att[p.strip()] = h
    for m in modeles:
        p = bc.MODELES[m].relative_to(RACINE).as_posix()
        assert att.get(p) == hashlib.sha256(bc.MODELES[m].read_bytes()).hexdigest(), f"SHA-256 de {p} différent"
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jeu", required=True, choices=JEUX + ["plantain", "vierge"])
    ap.add_argument("--candidats", nargs="+", default=["v5_030", "E5p90b_c13e_d-0.1", "CB13_trous_b0.20_reseau"])
    ap.add_argument("--essai", help="essai du script sur un jeu de RÉGLAGE (plantain), sorties dans ce dossier (hors dépôt)")
    a, reste = ap.parse_known_args()
    assert a.jeu != "plantain" or a.essai, "plantain : essai seulement"
    global SORTIE
    if a.essai:
        assert a.jeu == "plantain", "essai : réglage seulement"
        SORTIE = Path(a.essai)
        SORTIE.mkdir(parents=True, exist_ok=True)
    if a.jeu == "vierge":
        assert set(a.candidats) <= PERMIS_VIERGE, "test vierge : v5 et E5p90b_c13e_d-0.1 seulement"
        SORTIE = SORTIE / "vierge"
        SORTIE.mkdir(parents=True, exist_ok=True)
        _jeu = bc.jeu
        bc.jeu = lambda n: bc._tuiles("test_vierge", D=DV) if n == "vierge" else _jeu(n)
    sortie = SORTIE / f"mesure_{a.jeu}.json"
    assert not sortie.exists(), f"{sortie} existe déjà : ce jeu a déjà été lu"
    # cartes : mon cache seulement ; les caches de C-banc et de C-entraîneur n'ont aucune carte de juge
    bc.CACHE = SORTIE / f"cache_{a.jeu}"
    bc.chemin_cache = chemin_cache
    for base in (cc.CACHE, cc.KAGGLE_CACHE) if not a.essai else ():
        assert not list(base.glob(f"*_{a.jeu}.json")), f"carte de juge inattendue dans {base}"
    modeles = sorted({m for n in a.candidats for m in CANDIDATS[n][3]})
    verifier_empreintes(modeles)
    t0 = time.time()
    items = bc.jeu(a.jeu)
    print(f"{time.strftime('%H:%M:%S')} {a.jeu} : {len(items)} éléments ; modèles {modeles}", flush=True)
    for m in ["v5"] + [x for x in modeles if x != "v5"]:
        t1 = time.time()
        bc.ecrire_cache(m, "base", a.jeu, fils=FILS)          # écrit dès qu'un modèle est fini (sauvegarde progressive)
        print(f"{time.strftime('%H:%M:%S')}   cartes {m} : {time.time() - t1:.0f} s", flush=True)
    res = {"jeu": a.jeu, "n_elements": len(items), "modeles": modeles, "candidats": {},
           "note": "juge RELU (plan du 13/11, section 3) : lu une fois par finaliste, rien n'y est réglé"}
    brut = {}
    for n in a.candidats:
        fab, reg, s, _, typ = CANDIDATS[n]
        f0 = cd.construire(fab, reg)            # cd.FABRIQUES = fabriques du banc v6 + aiguillage_v2 et trous
        sorties, aig = {}, {}

        def f(ctx, f0=f0, typ=typ, reg=reg, sorties=sorties, aig=aig):
            xy, sc = f0(ctx)
            xy, sc = np.asarray(xy, "float64").reshape(-1, 2), np.asarray(sc, "float64")
            sorties[ctx.nom] = np.c_[xy, sc]
            if typ == "p90":         # même test que f_aiguillage_p90 (source v5, pics >= 0,15, 90e centile < tau)
                _, s5 = bc.pics(ctx.carte("v5", "base"), bc.K_PICS, 0.15)
                aig[ctx.nom] = bool(len(s5) >= 1 and float(np.quantile(s5, 0.90)) < reg["tau"])
            elif typ == "v2":        # aiguillée si la sortie n'est pas celle du v5 seul (dernière ligne de f_aiguillage_v2)
                xy5, s5 = bc.pics(ctx.carte("v5", "base"), bc.K_PICS)
                aig[ctx.nom] = not (np.array_equal(xy5, xy) and np.array_equal(s5, sc))
            return xy, sc

        r = bc.mesurer_jeu(f, a.jeu, items)[s]
        # comptes par image (même filtre et même appariement que bc.mesurer_jeu) ; la somme doit redonner la mesure
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
            if a.jeu.startswith("neg"):
                c = (0, len(det), 0)
            else:
                c = bc.compter(det, e["pts"], e["ign"])
            par_image[e["nom"]] = dict(vp=int(c[0]), fp=int(c[1]), fn=int(c[2]), det=len(det), reels=len(e["pts"]),
                                       autres_arbres=int(e["n_autres"]), aiguillee=aig.get(e["nom"]))
            tot += (c[0], c[1], c[2], len(det))
        if a.jeu.startswith("neg"):
            assert tot[1] == r["fp"], (n, tot, r)
        else:
            assert (tot[0], tot[1], tot[2], tot[3]) == (r["vp"], r["fp"], r["fn"], r["detectes"]), (n, tot, r)
        r = {k: (float(v) if isinstance(v, (float, np.floating)) else int(v)) for k, v in r.items()}
        r.update(seuil=s, fabrique=fab, reglages=reg, par_image=par_image)
        if aig:
            r.update(aiguillees=int(sum(aig.values())), n_images=len(aig), part_aiguillee=sum(aig.values()) / len(aig))
        res["candidats"][n] = r
        for nom, d in sorties.items():
            brut[f"{n}|{nom}"] = d.astype("float32")
        ag = f" ; aiguillées {r['aiguillees']} / {r['n_images']}" if aig else ""
        if a.jeu.startswith("neg"):
            print(f"{n:30s} seuil {s:.2f} : fausses {r['fp']} / {r['arbres']} ({r['taux']:.2%}){ag}", flush=True)
        else:
            print(f"{n:30s} seuil {s:.2f} : P {r['p']:.4f} R {r['r']:.4f} F1 {r['f1']:.4f} ; {r['detectes']} / {r['reels']} ; "
                  f"erreur {r['err_compte']:.3f}{ag}", flush=True)
    res["duree_s"] = time.time() - t0
    np.savez_compressed(SORTIE / f"detections_{a.jeu}.npz", **brut)
    sortie.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{time.strftime('%H:%M:%S')} fini en {res['duree_s']:.0f} s", flush=True)


if __name__ == "__main__":
    main()
