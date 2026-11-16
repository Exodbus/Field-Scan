#!/usr/bin/env python3
"""Mesure des candidats de la nuit du 13/11 sur le RÉGLAGE (agent C-banc). Les juges ne sont jamais lus.

Résultats cumulés dans out/comptage/nuit_1311/banc/essais.json (un candidat déjà mesuré sur un jeu n'est pas
recalculé). Un essai = un candidat distinct mesuré (tous seuils de la grille confondus).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c13_banc_essais.py --liste ref cb1a
"""
import argparse
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c13_banc_commun as cc  # noqa: E402
import c13_banc_candidats as cd  # noqa: E402
import c13_banc_listes as li  # noqa: E402

FICHIER = cc.SORTIE / "essais.json"
_ITEMS = {}


def _tache(t):
    nom, fabrique, reglages, nom_jeu = t
    if nom_jeu not in _ITEMS:
        _ITEMS[nom_jeu] = cc.jeu(nom_jeu)
    r = cc.bc.mesurer_jeu(cd.construire(fabrique, reglages), nom_jeu, _ITEMS[nom_jeu])
    return nom, nom_jeu, {str(s): v for s, v in r.items()}


def charger():
    return json.loads(FICHIER.read_text(encoding="utf-8")) if FICHIER.exists() else {}


def tableau(E, noms=None):
    ref = cc.reference_v5({"v5": {"res": cc.res_float(E["v5"]["res"])}})
    out = []
    for nom, e in E.items():
        if noms is not None and nom not in noms:
            continue
        if any(j not in e["res"] for j in cc.REGLAGE + ["neg"]):
            continue
        b = cc.choisir(cc.lignes(cc.res_float(e["res"])))
        if b is None:
            out.append(dict(nom=nom, famille=e["famille"], seuil=None)); continue
        out.append(dict(nom=nom, famille=e["famille"], **b, **cc.statut(b, ref)))
    out.sort(key=lambda b: -(b.get("moyenne") or 0))
    return out, ref


def afficher(lignes, ref, n=None):
    J = cc.REGLAGE
    print(f"{'candidat':48s} seuil " + " ".join(f"{j[:7]:>7s}" for j in J) + "  moy5   moy4   gain  pire  errC  fpneg  fin")
    print(f"{'RÉFÉRENCE v5 à 0,30':48s} 0.30  " + " ".join(f"{ref['f1_' + j]:7.3f}" for j in J)
          + f" {ref['moyenne']:.4f} {ref['moy4']:.4f}                {ref['err_compte']:.3f} {ref['fp_neg']:5d}")
    for b in lignes[:n]:
        if b.get("seuil") is None:
            print(f"{b['nom']:48s} aucun seuil sous 1 %"); continue
        print(f"{b['nom']:48s} {b['seuil']:.2f}  " + " ".join(f"{b['f1_' + j]:7.3f}" for j in J)
              + f" {b['moyenne']:.4f} {b['moy4']:.4f} {b['gain']:+.3f} {b['pire_perte']:+.3f} {b['err_compte']:.3f} {b['fp_neg']:5d}  "
              + ("OUI" if b["finaliste"] else "".join(k for k, c in (("1", "c1"), ("2", "c2"), ("3", "c3"), ("4", "c4")) if not b[c])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--liste", nargs="*", default=[])
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--affiche", type=int, default=60)
    ap.add_argument("--tous", action="store_true", help="afficher tous les candidats, pas seulement ceux des listes")
    a = ap.parse_args()
    E = charger()
    registre = {}
    for l in a.liste:
        registre.update(li.LISTES[l]())
    for nom, (fam, fab, reg) in registre.items():
        E.setdefault(nom, dict(famille=fam, fabrique=fab, reglages=reg, res={}))
    jeux = cc.REGLAGE + ["neg"]
    taches = [(nom, e["fabrique"], e["reglages"], j) for nom, e in E.items() for j in jeux if j not in e["res"]]
    t0 = time.time()
    if taches:
        taches.sort(key=lambda t: t[3])
        with Pool(a.procs) as p:
            for k, (nom, j, r) in enumerate(p.imap_unordered(_tache, taches, chunksize=1)):
                E[nom]["res"][j] = r
                if k % 20 == 19:
                    FICHIER.write_text(json.dumps(E), encoding="utf-8")
        FICHIER.write_text(json.dumps(E), encoding="utf-8")
    lignes, ref = tableau(E, None if (a.tous or not registre) else set(registre) | {"v5"})
    print(f"{time.strftime('%H:%M')} {len(taches)} mesures en {time.time() - t0:.0f} s ; {len(E)} candidats (essais) au total")
    afficher(lignes, ref, a.affiche)
    tous, _ = tableau(E)
    (cc.SORTIE / "tableau_reglage.json").write_text(json.dumps(dict(reference=ref, lignes=tous), indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
