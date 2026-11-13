#!/usr/bin/env python3
"""Mesure des candidats sur le RÉGLAGE (agent C-banc). Les juges ne sont jamais lus ici.

Les résultats (par candidat et par jeu, tous seuils) sont gardés dans out/comptage_v6/banc/essais.json : un candidat
déjà mesuré sur un jeu n'est pas recalculé. Le nombre d'essais = nombre de candidats distincts mesurés.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/v6_banc_essais.py --liste a   (listes : voir LISTES)
"""
import argparse
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v6_banc_commun as bc  # noqa: E402
import v6_banc_candidats as ca  # noqa: E402
import v6_banc_listes as li  # noqa: E402

FICHIER = bc.SORTIE / "essais.json"
_ITEMS = {}


def _tache(t):
    nom, fabrique, reglages, nom_jeu = t
    try:
        if nom_jeu not in _ITEMS:
            _ITEMS[nom_jeu] = bc.jeu(nom_jeu)
        r = bc.mesurer_jeu(ca.construire(fabrique, reglages), nom_jeu, _ITEMS[nom_jeu])
    except FileNotFoundError:
        if nom_jeu != "neg":
            return nom, nom_jeu, None                  # cache absent : mesure reportée
        return _tache((nom, fabrique, reglages, "neg_q"))
    return nom, nom_jeu, {str(s): v for s, v in r.items()}


def charger():
    return json.loads(FICHIER.read_text(encoding="utf-8")) if FICHIER.exists() else {}


def jeux_reglage():
    return [j for j in bc.REGLAGE if j != "btd_val" or bc.noms_btd_validation() is not None]


def ligne(res, jeux):
    neg = bc.neg_de(res)
    m = {j: {float(s): v for s, v in res[j].items()} for j in jeux + [neg]}
    return bc.resume(m, jeux, neg)


def tableau(E, jeux, noms=None, tri=True):
    """Tableau des candidats au seuil de la règle 3.4, et statut « finaliste » par rapport au v5."""
    r5 = E.get("v5", {}).get("res", {})
    if any(j not in r5 for j in jeux) or "neg" not in r5:
        return [], None
    ref, lignes_ref = ligne(r5, jeux)
    ref30 = [l for l in lignes_ref if l["seuil"] == 0.30][0]
    base = ref if ref["moyenne"] >= ref30["moyenne"] else ref30         # référence la plus exigeante des deux
    out = []
    for nom, e in E.items():
        if noms is not None and nom not in noms:
            continue
        if any(j not in e["res"] for j in jeux) or ("neg" not in e["res"] and "neg_q" not in e["res"]):
            continue
        b, _ = ligne(e["res"], jeux)
        if b is None:
            out.append(dict(nom=nom, famille=e["famille"], seuil=None)); continue
        pertes = {j: b[f"f1_{j}"] - base[f"f1_{j}"] for j in jeux}
        b = dict(nom=nom, famille=e["famille"], **b, gain=b["moyenne"] - base["moyenne"], pire_perte=min(pertes.values()),
                 moy4=float(np.mean([b[f"f1_{j}"] for j in jeux if j != "btd_val"])),
                 finaliste=bool(b["moyenne"] > base["moyenne"] + 0.010 and min(pertes.values()) >= -0.020
                                and b["err_compte"] <= base["err_compte"]))
        out.append(b)
    if tri:
        out.sort(key=lambda b: -(b.get("moyenne") or 0))
    return out, base


def afficher(lignes, jeux, n=None):
    print(f"{'candidat':44s} seuil  " + " ".join(f"{j[:8]:>8s}" for j in jeux) + "   moy.   gain  pire  err.cpte  fp_neg  fin.  moy4")
    for b in lignes[:n]:
        if b.get("seuil") is None:
            print(f"{b['nom']:44s} aucun seuil sous 1 % de fausses détections"); continue
        print(f"{b['nom']:44s} {b['seuil']:.2f}   " + " ".join(f"{b['f1_' + j]:8.3f}" for j in jeux)
              + f"  {b['moyenne']:.4f} {b['gain']:+.3f} {b['pire_perte']:+.3f}  {b['err_compte']:.3f}   {b['fp_neg']:5d}   "
              + ("OUI " if b["finaliste"] else "    ") + f" {b['moy4']:.4f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--liste", nargs="*", default=[])
    ap.add_argument("--procs", type=int, default=7)
    ap.add_argument("--affiche", type=int, default=40)
    ap.add_argument("--neg-complet", nargs="*", default=[], help="candidats à contrôler sur toutes les tuiles sans bananier")
    a = ap.parse_args()
    E = charger()
    jeux = jeux_reglage()
    registre = {}
    for l in a.liste:
        registre.update(li.LISTES[l]())
    for nom, (fam, fab, reg) in registre.items():
        E.setdefault(nom, dict(famille=fam, fabrique=fab, reglages=reg, res={}))
    taches = [(nom, e["fabrique"], e["reglages"], j) for nom, e in E.items() for j in jeux if j not in e["res"]]
    taches += [(nom, e["fabrique"], e["reglages"], "neg") for nom, e in E.items() if "neg" not in e["res"]
               and ("neg_q" not in e["res"] or nom in a.neg_complet)]
    t0 = time.time()
    if taches:
        taches.sort(key=lambda t: t[3])
        with Pool(a.procs) as p:
            for k, (nom, j, r) in enumerate(p.imap_unordered(_tache, taches, chunksize=1)):
                if r is None:
                    print(f"  cache absent : {nom} sur {j} reporté", flush=True); continue
                E[nom]["res"][j] = r
                if k % 50 == 49:
                    FICHIER.write_text(json.dumps(E), encoding="utf-8")
        FICHIER.write_text(json.dumps(E), encoding="utf-8")
    lignes, base = tableau(E, jeux)
    if base is None:
        print("référence v5 incomplète (cache sans bananier en cours) : tableau reporté"); FICHIER.write_text(json.dumps(E), encoding="utf-8"); return
    print(f"{time.strftime('%H:%M')} {len(taches)} mesures en {time.time() - t0:.0f} s ; {len(E)} candidats (essais) au total ; jeux : {jeux}")
    print(f"référence v5 : seuil {base['seuil']}, moyenne {base['moyenne']:.4f}, erreur de compte {base['err_compte']:.3f}, fp {base['fp_neg']}")
    afficher([l for l in lignes if l["nom"] in registre or not registre], jeux, a.affiche)
    print("(fp_neg : sur toutes les tuiles sans bananier, ou sur le quart (neg_q) pour les variantes coûteuses non encore contrôlées)")
    (bc.SORTIE / "tableau_reglage.json").write_text(json.dumps(dict(jeux=jeux, reference=base, lignes=lignes), indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
