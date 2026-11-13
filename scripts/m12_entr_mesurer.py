#!/usr/bin/env python3
"""Mesure de réglage d'un candidat v12 (agent M-entraînement, nuit du 12/11) : chaîne complète et coût 4.4 du plan.

Chaîne : aiguilleur (p_loin >= 0,5 -> réponse de la v2, politique b) ; photo « proche » -> candidat, décision
fieldscan.modules.maladies.decider_convnext avec les seuils de la v10b (ou des seuils donnés). Comme scripts/mesurer_v10b.py.
Jeux de RÉGLAGE seulement : validation Tanzanie (lue par les 3 plis, moyenne des plis) et TDTU, PSFD, Éthiopie (chacun lu par
le pli qui ne l'a pas appris). Aucun juge n'est lu ici.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/m12_entr_mesurer.py <dossier des CSV> <recette> [recette ...]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from fieldscan.modules import maladies  # noqa: E402

V10B, DOS, ANCIENS = RACINE / "out/maladies/v10b", RACINE / "out/maladies/cinq_classes", RACINE / "out/maladies/dinov2_ft"
ALERTE = {"cercosporiose_noire", "fusariose", "malade_non_identifiee", "cordana", "pestalotiopsis", "a_verifier"}
PAYS = ["tdtu", "psfd", "ethiopie"]
REF = dict(validation=(9, 2001, 57, 1000), tdtu=(83, 1059, 177, 577), psfd=(149, 738, 0, 0), ethiopie=(179, 1134, 43, 155))


def seuils(dossier, **en_plus):
    s = json.loads((RACINE / dossier / "seuils.json").read_text(encoding="utf-8"))
    mb = (s.get("membres") or [{}])[0]
    return dict(classes=[maladies.NOMS_CHAINE[c] for c in s["classes"]], seuil=float(s["seuil_confiance"]),
                seuil_alerte=float(s["seuil_alerte"]), seuil_nom=float(s["seuil_nom"]), nommer_autre=not mb,
                regle_b=bool(s.get("regle_b")), seuil_inconnu_malade=s.get("seuil_inconnu_malade"), **en_plus)


M_V2 = seuils("modeles/maladies_binome/maladies_v2/poids", jnsp_alerte=True)
M_V10B = seuils("modeles/maladies_binome/v10b", jnsp_alerte=True)
COLS = ["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]


def probas(df):
    return df[[c for c in COLS if c in df.columns]].to_numpy(dtype="float64")


_cache = {}


def fixe(j):
    """Ce qui ne dépend pas du candidat : réponse de la branche « loin » (v2), aiguillage, vérité."""
    if j not in _cache:
        v2 = pd.read_csv((ANCIENS if j == "validation" else DOS) / f"predictions_v2_{j}.csv")
        pl = pd.read_csv(DOS / f"p_loin_{j}.csv")
        assert list(v2.chemin) == list(pl.chemin), j
        _cache[j] = dict(chemin=list(v2.chemin), loin=pl.p_loin.values >= 0.5, r_loin=maladies.decider_convnext(probas(v2), M_V2)[0],
                         vrai=v2.classe_vraie.to_numpy(dtype=object))
    return _cache[j]


def compter(j, P, m=M_V10B, chaine=True):
    """(malades sans alerte, malades, saines en alerte, saines) pour le jeu j lu par le candidat (probabilités P)."""
    f = fixe(j)
    rep = maladies.decider_convnext(P, m)[0]
    if chaine:
        rep = np.where(f["loin"], f["r_loin"], rep)
    al, malade = np.isin(rep, list(ALERTE)), f["vrai"] != "saine"
    return int((malade & ~al).sum()), int(malade.sum()), int((~malade & al).sum()), int((~malade).sum())


def cout(c):
    return 100 * (3 * c[0] / c[1] + (c[2] / c[3] if c[3] else 0))


def lire_csv(chemin, j):
    df = pd.read_csv(chemin).set_index("chemin").loc[fixe(j)["chemin"]]
    return probas(df)


def charger_recette(dossier, nom):
    """Probabilités d'une recette : {pays: P} et {pli: P de la validation}. Témoin (une seule validation) accepté."""
    d = Path(dossier) / nom if (Path(dossier) / nom).is_dir() else Path(dossier)
    pays = {x: lire_csv(d / f"predictions_{nom}_{x}.csv", x) for x in PAYS if (d / f"predictions_{nom}_{x}.csv").exists()}
    if (d / f"predictions_{nom}_validation.csv").exists():
        val = {"tous": lire_csv(d / f"predictions_{nom}_validation.csv", "validation")}
    else:
        val = {x: lire_csv(d / f"predictions_{nom}_validation_pli_{x}.csv", "validation") for x in PAYS
               if (d / f"predictions_{nom}_validation_pli_{x}.csv").exists()}
    return pays, val


def bilan(pays, val, m=M_V10B, chaine=True):
    """Coût par jeu, coût moyen et règle « finaliste » (plan, 4.4). Tanzanie = moyenne des plis, pire pli à côté."""
    cv = np.array([compter("validation", P, m, chaine) for P in val.values()], dtype=float)
    tz = tuple(cv.mean(0))
    comptes = dict(validation=tz, **{x: compter(x, P, m, chaine) for x, P in pays.items()})
    couts = {j: cout(c) for j, c in comptes.items()}
    moyen = float(np.mean([couts[j] for j in ["validation"] + PAYS if j in couts]))
    ref_moyen = float(np.mean([cout(REF[j]) for j in ["validation"] + PAYS if j in couts]))
    perte_pays = {x: 100 * (comptes[x][0] / comptes[x][1] - REF[x][0] / REF[x][1]) for x in pays}
    finaliste = bool(moyen <= ref_moyen - 1 and tz[0] <= 14 and tz[2] <= 77 and all(v <= 2 for v in perte_pays.values())
                     and len(pays) == 3)
    return dict(comptes=comptes, couts=couts, cout_moyen=moyen, ref_moyen=ref_moyen, tanzanie_pire_pli=(float(cv[:, 0].max()), float(cv[:, 2].max())),
                perte_pays=perte_pays, finaliste=finaliste)


def ligne(nom, b):
    c = b["comptes"]
    def f(j):
        if j not in c:
            return "—"
        x = c[j]
        return f"{x[0]:.4g}/{x[1]:.0f}" + (f" ; {x[2]:.4g}/{x[3]:.0f}" if x[3] else "") + f" ({b['couts'][j]:.2f})"
    return (f"| {nom} | {f('validation')} | {f('tdtu')} | {f('psfd')} | {f('ethiopie')} | **{b['cout_moyen']:.2f}** | "
            f"{'oui' if b['finaliste'] else 'non'} |")


ENTETE = ("| Recette | Tanzanie (moy. des plis) | TDTU | PSFD | Éthiopie | Coût moyen | Finaliste |\n"
          "| --- | --- | --- | --- | --- | --- | --- |")

if __name__ == "__main__":
    dossier, noms = sys.argv[1], sys.argv[2:]
    print(ENTETE)
    ref = {j: lire_csv(V10B / f"predictions_v10b_{j}.csv", j) for j in ["validation"] + PAYS}
    print(ligne("v10b (3 réseaux, 11/11)", bilan({x: ref[x] for x in PAYS}, {"tous": ref["validation"]})))
    for nom in noms:
        pays, val = charger_recette(dossier, nom)
        b = bilan(pays, val)
        print(ligne(nom, b), f" pire pli Tanzanie {b['tanzanie_pire_pli']}")
        (Path(dossier) / nom if (Path(dossier) / nom).is_dir() else Path(dossier)) .joinpath(f"bilan_{nom}.json").write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
