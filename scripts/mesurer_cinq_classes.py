#!/usr/bin/env python3
"""Mesure unique du protocole docs/protocole_maladies_cinq_classes.md (section 3) : règle de choix de la branche « proche ».

Candidats : v2 (référence), soupe, DINOv2-FT, C5, D5, E5 (s'il existe) et l'ensemble C5 + D5 (moyenne des probabilités,
seuils recalculés par les règles de la v2 sur la validation). Définitions de scripts/mesurer_adoption_v5.py, étendues aux
noms Cordana et Pestalotiopsis. Écrit out/maladies/cinq_classes/bilan_cinq_classes.json et un tableau lisible.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/mesurer_cinq_classes.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
import os
DOS = Path(os.environ.get("CINQ_DOS", RACINE / "out/maladies/cinq_classes"))
ANCIENS = Path(os.environ.get("CINQ_ANCIENS", RACINE / "out/maladies/dinov2_ft"))          # validation et BananaLSD de v2, soupe, DINOv2-FT (fichiers de la nuit du 9)
MALADE = {"cercosporiose_noire", "fusariose", "malade_non_identifiee", "cordana", "pestalotiopsis"}
NOMMEE = {"cercosporiose_noire", "fusariose", "cordana", "pestalotiopsis"}
CLASSES5 = ["saine", "black_sigatoka", "fusarium", "cordana", "pestalotiopsis"]
NOMS5 = {"saine": "saine", "black_sigatoka": "cercosporiose_noire", "fusarium": "fusariose", "cordana": "cordana",
         "pestalotiopsis": "pestalotiopsis"}
JEUX = ["validation", "bananalsd", "tdtu", "psfd", "ethiopie"]
COUT = {"v2": 0, "soupe": 0, "c5": 0, "dinov2_ft": 1, "d5": 1, "e5": 1, "c5_d5": 2, "l5": 3}   # amendement 1 : L5 en dernier


def lire(modele, jeu):
    if modele in ("v2", "soupe", "dinov2_ft"):
        f = (ANCIENS if jeu in ("validation", "bananalsd") else DOS) / f"predictions_{modele}_{jeu}.csv"
    else:
        f = DOS / "kaggle" / modele / f"predictions_{modele}_{jeu}.csv"
    return pd.read_csv(f)


def regles_v2(pv, vraie):
    """Seuils par les règles de la v2 sur la validation (comme dans le carnet), probabilités à 5 classes."""
    v = np.array([{"saine": 0, "cercosporiose_noire": 1, "fusariose": 2}[c] for c in vraie])
    pm = 1 - pv[:, 0]
    couts = [(2 * int((~(pm >= s) & (v > 0)).sum()) + int(((pm >= s) & (v == 0)).sum()), s) for s in np.round(np.arange(0.05, 0.96, 0.05), 2)]
    alerte_s = min(couts)[1]   # premier seuil au coût minimal (ordre croissant, comme idxmin)
    part = pv[:, 1:].max(1) / np.maximum(pm, 1e-9)
    maladie, alerte = 1 + pv[:, 1:].argmax(1), (pm >= alerte_s) & (v > 0)
    nom_s = 1.0
    for s in np.round(np.arange(0.50, 1.0, 0.01), 2):
        nn = alerte & (part >= s)
        if nn.sum() and (maladie[nn] == v[nn]).mean() >= 0.95:
            nom_s = float(s); break
    return dict(seuil_alerte=float(alerte_s), seuil_nom=nom_s, seuil_confiance=float(np.quantile(pv.max(1), 0.05)))


def decider5(p, s):
    pm = 1 - p[:, 0]; part = p[:, 1:].max(1) / np.maximum(pm, 1e-9)
    nom = np.array([NOMS5[c] for c in CLASSES5])[1 + p[:, 1:].argmax(1)]
    r = np.where(pm < s["seuil_alerte"], "saine", np.where(part >= s["seuil_nom"], nom, "malade_non_identifiee")).astype(object)
    r[p.max(1) < s["seuil_confiance"]] = "je_ne_sais_pas"
    return r


def ensemble(a, b):
    cols = [f"p_{c}" for c in CLASSES5]
    out, seuils = {}, None
    for j in JEUX:
        x, y = lire(a, j), lire(b, j)
        assert list(x.chemin) == list(y.chemin), j
        out[j] = x.copy()
        out[j][cols] = (x[cols].values + y[cols].values) / 2
    seuils = regles_v2(out["validation"][cols].values, out["validation"].classe_vraie)
    for j in JEUX:
        out[j]["reponse"] = decider5(out[j][cols].values, seuils)
    return out, seuils


def part(masque, total):
    n = int(total.sum())
    return dict(k=int((masque & total).sum()), n=n, part=round(float((masque & total).sum()) / n, 4) if n else None)


def mesures(d):
    v, b, t, ps, e = (d[j] for j in JEUX)
    vm, vs = v.classe_vraie.ne("saine"), v.classe_vraie.eq("saine")
    bi = b.classe_vraie.str.startswith("inconnue")
    nouv = b.reponse.isin(["cordana", "pestalotiopsis"])
    juste_nouv = (b.reponse.eq("cordana") & b.classe_vraie.eq("inconnue_cordana")) | \
                 (b.reponse.eq("pestalotiopsis") & b.classe_vraie.eq("inconnue_pestalotiopsis"))
    m = {
        "validation_malades_dites_saines": part(v.reponse.eq("saine"), vm),
        "validation_fausses_alertes": part(v.reponse.isin(MALADE), vs),
        "validation_nommee_juste": part(v.reponse.eq(v.classe_vraie), v.reponse.isin(NOMMEE) & vm),
        "bananalsd_sigatoka_nommee": part(b.reponse.eq("cercosporiose_noire"), b.classe_vraie.eq("cercosporiose_noire")),
        "bananalsd_saines_bien_classees": part(b.reponse.eq("saine"), b.classe_vraie.eq("saine")),
        "bananalsd_inconnues_dites_saines": part(b.reponse.eq("saine"), bi),
        "bananalsd_inconnues_dites_sigatoka": part(b.reponse.eq("cercosporiose_noire"), bi),
        "bananalsd_noms_nouveaux_justes": part(juste_nouv, nouv),
        "bananalsd_cordana_nommee": part(b.reponse.eq("cordana"), b.classe_vraie.eq("inconnue_cordana")),
        "bananalsd_pestalotiopsis_nommee": part(b.reponse.eq("pestalotiopsis"), b.classe_vraie.eq("inconnue_pestalotiopsis")),
        "bananalsd_inconnues_en_alerte": part(b.reponse.isin(MALADE), bi),
        "tdtu_autre_dite_saine": part(t.reponse.eq("saine"), t.classe_vraie.eq("autre_maladie")),
        "psfd_jaune_dite_saine": part(ps.reponse.eq("saine"), ps.classe_vraie.eq("sigatoka_jaune")),
        "ethiopie_xanthomonas_dite_saine": part(e.reponse.eq("saine"), e.classe_vraie.eq("xanthomonas")),
        "psfd_noire_en_alerte": part(ps.reponse.isin(MALADE), ps.classe_vraie.eq("black_sigatoka")),
        "ethiopie_sigatoka_en_alerte": part(e.reponse.isin(MALADE), e.classe_vraie.eq("sigatoka")),
        "ethiopie_saines_fausses_alertes": part(e.reponse.isin(MALADE), e.classe_vraie.eq("saine")),
        # rapportés sans effet
        "tdtu_sigatoka_nommee": part(t.reponse.eq("cercosporiose_noire"), t.classe_vraie.eq("black_sigatoka")),
        "tdtu_saines_fausses_alertes": part(t.reponse.isin(MALADE), t.classe_vraie.eq("saine")),
        "psfd_noire_nommee": part(ps.reponse.eq("cercosporiose_noire"), ps.classe_vraie.eq("black_sigatoka")),
        "ethiopie_sigatoka_nommee": part(e.reponse.eq("cercosporiose_noire"), e.classe_vraie.eq("sigatoka")),
    }
    m["rappel_equilibre_bananalsd"] = round(((m["bananalsd_sigatoka_nommee"]["part"] or 0) + (m["bananalsd_saines_bien_classees"]["part"] or 0)) / 2, 4)
    m["confusions"] = {j: pd.crosstab(d[j].classe_vraie, d[j].reponse).to_dict() for j in JEUX}
    return m


def conditions(m, r, cinq):
    p = lambda x, k: float("nan") if x[k]["part"] is None else x[k]["part"]   # aucune photo concernée : condition non remplie
    c = {
        "1 validation malades dites saines <= v2 + 0,5 pt": p(m, "validation_malades_dites_saines") <= p(r, "validation_malades_dites_saines") + 0.005,
        "1 validation fausses alertes <= v2 + 1 pt": p(m, "validation_fausses_alertes") <= p(r, "validation_fausses_alertes") + 0.01,
        "1 validation nom juste >= 95 %": p(m, "validation_nommee_juste") >= 0.95,
        "1 BananaLSD Sigatoka nommée >= v2 - 2 pts": p(m, "bananalsd_sigatoka_nommee") >= p(r, "bananalsd_sigatoka_nommee") - 0.02,
        "1 BananaLSD saines bien classées >= v2 - 2 pts": p(m, "bananalsd_saines_bien_classees") >= p(r, "bananalsd_saines_bien_classees") - 0.02,
        "1 BananaLSD Cordana/Pesta dites saines <= v2 + 1 pt": p(m, "bananalsd_inconnues_dites_saines") <= p(r, "bananalsd_inconnues_dites_saines") + 0.01,
        "2 garde : Cordana/Pesta dites Sigatoka <= 246": m["bananalsd_inconnues_dites_sigatoka"]["k"] <= 246,
        "3 gain : rappel équilibré >= v2 + 1 pt": m["rappel_equilibre_bananalsd"] >= r["rappel_equilibre_bananalsd"] + 0.01,
        "5 TDTU autre_maladie dite saine <= v2 + 2 pts": p(m, "tdtu_autre_dite_saine") <= p(r, "tdtu_autre_dite_saine") + 0.02,
        "5 PSFD Sigatoka jaune dite saine <= v2 + 2 pts": p(m, "psfd_jaune_dite_saine") <= p(r, "psfd_jaune_dite_saine") + 0.02,
        "5 Éthiopie Xanthomonas dite saine <= v2 + 2 pts": p(m, "ethiopie_xanthomonas_dite_saine") <= p(r, "ethiopie_xanthomonas_dite_saine") + 0.02,
        "6 PSFD Sigatoka noire en alerte >= v2 - 2 pts": p(m, "psfd_noire_en_alerte") >= p(r, "psfd_noire_en_alerte") - 0.02,
        "6 Éthiopie Sigatoka en alerte >= v2 - 2 pts": p(m, "ethiopie_sigatoka_en_alerte") >= p(r, "ethiopie_sigatoka_en_alerte") - 0.02,
        "6 Éthiopie saines fausses alertes <= v2 + 5 pts": p(m, "ethiopie_saines_fausses_alertes") <= p(r, "ethiopie_saines_fausses_alertes") + 0.05,
    }
    if cinq:
        q = m["bananalsd_noms_nouveaux_justes"]
        c["4 noms Cordana/Pesta justes >= 80 %"] = q["n"] == 0 or q["part"] >= 0.80
    return c


def main():
    modeles = ["v2", "soupe", "dinov2_ft"] + [k for k in ("c5", "d5", "e5", "l5") if (DOS / "kaggle" / k).exists()]
    donnees = {k: {j: lire(k, j) for j in JEUX} for k in modeles}
    seuils_ens = None
    if {"c5", "d5"} <= set(modeles):
        donnees["c5_d5"], seuils_ens = ensemble("c5", "d5")
    M = {k: mesures(d) for k, d in donnees.items()}
    r = M["v2"]
    bilan = {}
    for k, m in M.items():
        if k == "v2":
            continue
        c = conditions(m, r, cinq=k not in ("soupe", "dinov2_ft"))
        bilan[k] = dict(conditions=c, adoptable=all(c.values()), rappel_equilibre=m["rappel_equilibre_bananalsd"])
    adopt = sorted([k for k in bilan if bilan[k]["adoptable"]], key=lambda k: -bilan[k]["rappel_equilibre"])
    if adopt:
        haut = bilan[adopt[0]]["rappel_equilibre"]
        proches = [k for k in adopt if bilan[k]["rappel_equilibre"] > haut - 0.01]
        retenu = min(proches, key=lambda k: (COUT[k], -bilan[k]["rappel_equilibre"]))
    else:
        retenu = "soupe (aucun candidat adoptable)"
    sortie = dict(mesures=M, bilan=bilan, retenu=retenu, seuils_ensemble_c5_d5=seuils_ens)
    (DOS / "bilan_cinq_classes.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    cles = [k for k in r if k not in ("confusions", "rappel_equilibre_bananalsd")]
    lignes = []
    for cle in cles:
        lignes.append([cle] + [f"{M[k][cle]['k']}/{M[k][cle]['n']}" for k in M])
    lignes.append(["rappel_equilibre_bananalsd"] + [f"{M[k]['rappel_equilibre_bananalsd']:.4f}" for k in M])
    tab = pd.DataFrame(lignes, columns=["mesure"] + list(M))
    print(tab.to_string(index=False))
    for k, b in bilan.items():
        echecs = [n for n, ok in b["conditions"].items() if not ok]
        print(f"{k:10s} adoptable={b['adoptable']}  équilibré={b['rappel_equilibre']:.4f}  échecs={echecs}")
    print("RETENU :", retenu)
    tab.to_csv(DOS / "tableau_cinq_classes.csv", index=False)


if __name__ == "__main__":
    main()
