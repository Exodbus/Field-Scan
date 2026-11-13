#!/usr/bin/env python3
"""Juge comptage, nuit du 12 au 13 novembre 2026 : DEUXIÈME AVIS, indépendant de la mesure principale.

Reprend le banc de C-banc (scripts/v6_banc_commun.py : lecture des jeux par bc.jeu, cartes ONNX par bc.cartes_image,
pics par maximum_filter, appariement par cdist + hongrois ; scripts/v6_banc_candidats.py : fabriques des finalistes,
réglages lus dans out/comptage_v6/banc/essais.json). Les cartes sont RECALCULÉES dans un cache à part
(out/controle_nuit_1112/juge_c/cache2_<jeu>) : rien n'est partagé avec la mesure principale, sauf les images.
Modèles de la nuit pris dans modeles/comptage_v6_essais/ (SHA-256 vérifiés contre empreintes_liste_gelee.txt).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_nuit_c_second_avis.py --jeu banano --candidats ...
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import v6_banc_commun as bc  # noqa: E402
import v6_banc_candidats as ca  # noqa: E402
import v6_banc_essais as es  # noqa: E402

SORTIE = RACINE / "out/controle_nuit_1112/juge_c"
EMPREINTES = RACINE / "out/controle_nuit_1112/empreintes_liste_gelee.txt"
DV = RACINE / "data/roboflow_nuit_1112/comptage/banana_trees_kp/prepare"
NUIT = {"v6e": "modeles/comptage_v6_essais/centres_5cm_v6e.onnx", "v6f": "modeles/comptage_v6_essais/centres_5cm_v6f.onnx"}
CANDIDATS = {  # nom : (fabrique, réglages, seuil) ; E10 et E5p90b relus dans essais.json de C-banc
    "E10_moy_v6e+v5": None, "E5p90b_moy34_v5_d0.1": None,
    "v6f": ("seul", {"modele": "v6f"}, 0.35),
    "v5_030": ("seul", {"modele": "v5"}, 0.30), "v5_020": ("seul", {"modele": "v5"}, 0.20),
}
JEUX_PERMIS = ["segmento", "banano", "cg", "neg_test", "vierge"]
SEUILS_BANC = {"E10_moy_v6e+v5": 0.30, "E5p90b_moy34_v5_d0.1": 0.30}


def verifier_empreintes(modeles):
    att = {}
    for l in EMPREINTES.read_text(encoding="utf-8").splitlines():
        if l.strip():
            h, p = l.split(None, 1)
            att[p.strip()] = h
    for m in modeles:
        p = bc.MODELES[m].relative_to(RACINE).as_posix()
        h = hashlib.sha256(bc.MODELES[m].read_bytes()).hexdigest()
        assert att.get(p) == h, f"SHA-256 de {p} différent de la liste gelée"
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jeu", required=True, choices=JEUX_PERMIS)
    ap.add_argument("--candidats", nargs="+", required=True)
    ap.add_argument("--fils", type=int, default=2)
    a = ap.parse_args()
    sortie = SORTIE / f"second_avis_{a.jeu}.json"
    assert not sortie.exists(), f"{sortie} existe déjà"
    bc.CACHE = SORTIE / f"cache2_{a.jeu}"
    bc.MODELES.update({k: RACINE / v for k, v in NUIT.items()})
    jeu_origine = bc.jeu
    bc.jeu = lambda n: bc._tuiles("test_vierge", D=DV) if n == "vierge" else jeu_origine(n)
    E = es.charger()
    specs = {}
    for n in a.candidats:
        if CANDIDATS[n] is None:
            specs[n] = (E[n]["fabrique"], E[n]["reglages"], SEUILS_BANC[n])
        else:
            specs[n] = CANDIDATS[n]
    besoin = {"E10_moy_v6e+v5": ["v6e", "v5"], "E5p90b_moy34_v5_d0.1": ["v3", "v4", "v5"], "v6f": ["v6f"],
              "v5_030": ["v5"], "v5_020": ["v5"]}
    modeles = sorted({m for n in a.candidats for m in besoin[n]})
    verifier_empreintes(modeles)
    nom_jeu = a.jeu if a.jeu != "neg_test" else "neg_test"
    t0 = time.time()
    items = bc.jeu(nom_jeu)
    for m in modeles:
        bc.ecrire_cache(m, "base", nom_jeu, fils=a.fils)
    print(f"{a.jeu} : {len(items)} éléments ; cartes {modeles} prêtes en {time.time() - t0:.0f} s", flush=True)
    res = {"jeu": a.jeu, "n_elements": len(items), "modeles": modeles, "candidats": {}}
    for n, (fab, reg, s) in specs.items():
        f = ca.construire(fab, reg)
        r = bc.mesurer_jeu(f, nom_jeu, items)[s]
        r = {k: (float(v) if not isinstance(v, int) else v) for k, v in r.items()}
        r.update(fabrique=fab, reglages=reg, seuil=s)
        res["candidats"][n] = r
        if a.jeu == "neg_test":
            print(f"{n:24s} seuil {s:.2f} : fausses {r['fp']} / {r['arbres']} ({r['taux']:.2%})", flush=True)
        else:
            print(f"{n:24s} seuil {s:.2f} : P {r['p']:.4f} R {r['r']:.4f} F1 {r['f1']:.4f} ; {r['detectes']} / {r['reels']} ; "
                  f"erreur {r['err_compte']:.3f}", flush=True)
    res["duree_s"] = time.time() - t0
    sortie.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
