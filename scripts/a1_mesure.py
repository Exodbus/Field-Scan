#!/usr/bin/env python3
"""A1-test : préparation de la copie des photos, puis bilan de la mesure unique de F1 (F1_bornes, chaîne installée).

Règles : `docs/journee_2026-11-15/avenant_jeux_neufs.md`, section A1. Mesure : part des feuilles malades SANS alerte,
c'est-à-dire de réponses hors de `MALADES` (fieldscan/modules/maladies.py). A1-test ne contient que des malades
(flétrissement bactérien) : la mesure ne dit rien des fausses alertes.

    ... -I -u scripts/a1_mesure.py preparer   # copie d'A1-test (rôle final) dans out/jeux_neufs_1611/a1_test_photos/
    (puis run.py --modules maladies, sans -I, sur cette copie)
    ... -I -u scripts/a1_mesure.py bilan      # lit a1_test_chaine/maladies_photos.csv une seule fois
"""
import collections
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.stdout.reconfigure(encoding="utf-8")

OUT = RACINE / "out/jeux_neufs_1611"
PHOTOS = OUT / "a1_test_photos"
CHAINE = OUT / "a1_test_chaine"
SRC = RACINE / "data/raw/plantvillage_psu/extrait/bxw-leaf"
LISTE = OUT / "a1_test_liste.csv"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def preparer():
    roles = list(csv.DictReader(open(OUT / "a1_roles_finaux.csv", encoding="utf-8")))
    man = {l["nom"]: l["sha256"] for l in csv.DictReader(open(SRC.parent / "manifeste.csv", encoding="utf-8"))}
    test = [r for r in roles if r["role_final"] == "A1-test"]
    PHOTOS.mkdir(parents=True, exist_ok=False)   # jamais deux préparations
    for r in test:
        shutil.copy2(SRC / r["nom"], PHOTOS / r["nom"])
        assert sha(PHOTOS / r["nom"]) == man[r["nom"]], r["nom"]
    with open(LISTE, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["nom", "pays", "lot", "sha256"])
        for r in test:
            w.writerow([r["nom"], r["pays"], r["lot"], man[r["nom"]]])
    print(f"A1-test : {len(test)} photos copiées, SHA-256 vérifiés ; liste gelée {LISTE}")


def bilan():
    from fieldscan.modules.maladies import MALADES, LIBELLES
    liste = {l["nom"]: l for l in csv.DictReader(open(LISTE, encoding="utf-8"))}
    tab = list(csv.DictReader(open(CHAINE / "maladies_photos.csv", encoding="utf-8")))
    par_nom = {Path(t["fichier"]).name: t for t in tab}
    assert set(par_nom) == set(liste), (len(par_nom), len(liste))
    for n, l in liste.items():   # la copie n'a pas changé depuis la liste gelée
        assert sha(PHOTOS / n) == l["sha256"], n
    N = len(liste)
    sans = [n for n, t in par_nom.items() if t["reponse"] not in MALADES]
    rep = collections.Counter(t["reponse"] for t in par_nom.values())
    par_pays = collections.defaultdict(collections.Counter)
    par_branche = collections.defaultdict(collections.Counter)
    for n, t in par_nom.items():
        par_pays[liste[n]["pays"]][t["reponse"] in MALADES] += 1
        par_branche[t["branche"]][t["reponse"] in MALADES] += 1
    res = dict(
        N=N, sans_alerte=len(sans), part_sans_alerte=round(len(sans) / N, 4),
        avec_alerte=N - len(sans), part_avec_alerte=round(1 - len(sans) / N, 4),
        reponses={k: dict(n=v, libelle=LIBELLES.get(k, k), alerte=k in MALADES) for k, v in rep.most_common()},
        par_pays={p: dict(N=c[True] + c[False], sans_alerte=c[False]) for p, c in sorted(par_pays.items())},
        par_branche={b: dict(N=c[True] + c[False], sans_alerte=c[False]) for b, c in sorted(par_branche.items())},
        reponses_par_pays={p: dict(collections.Counter(par_nom[n]["reponse"] for n in liste if liste[n]["pays"] == p))
                           for p in sorted({l["pays"] for l in liste.values()})},
        malades=sorted(MALADES),
    )
    (OUT / "a1_mesure_f1.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(OUT / "a1_mesure_f1_photos.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["nom", "pays", "reponse", "alerte", "p_malade", "confiance", "branche"])
        for n in sorted(liste):
            t = par_nom[n]
            w.writerow([n, liste[n]["pays"], t["reponse"], t["reponse"] in MALADES, t["p_malade"], t["confiance"],
                        t["branche"]])
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    {"preparer": preparer, "bilan": bilan}[sys.argv[1]]()
