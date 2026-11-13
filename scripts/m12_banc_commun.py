#!/usr/bin/env python3
"""Banc commun de l'agent M-banc (nuit du 12/11, docs/plan_nuit_2026-11-12.md, sections 4.3 et 4.4).

Chaîne installée : aiguilleur (p_loin >= 0,5 -> v2, politique b) ; sinon v10b (règle B, seuil v11). Tout vient des
probabilités en cache (aucun passage de réseau). Coût d'un jeu = 3 × taux de malades sans alerte + taux de saines en
alerte (un jeu sans saine : premier terme seul). Réglage = validation + tdtu + psfd + ethiopie. Les juges (BanSpot,
Cordana du Pérou) ne sont chargés que par charger_juges(), appelé par le seul script m12_banc_juges.py.
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
SORTIE = RACINE / "out/maladies/nuit_1112/banc"
SORTIE.mkdir(parents=True, exist_ok=True)
ALERTE = {"cercosporiose_noire", "fusariose", "malade_non_identifiee", "cordana", "pestalotiopsis", "a_verifier"}
REGLAGE = ["validation", "tdtu", "psfd", "ethiopie"]
REFERENCE = {"validation": (9, 2001, 57, 1000), "tdtu": (83, 1059, 177, 577), "psfd": (149, 738, 0, 0),
             "ethiopie": (179, 1134, 43, 155)}   # chiffres du 11/11 (docs/protocole_maladies_v10b.md, section 7)


def seuils(dossier, **en_plus):
    s = json.loads((RACINE / dossier / "seuils.json").read_text(encoding="utf-8"))
    mb = (s.get("membres") or [{}])[0]
    return dict(classes=[maladies.NOMS_CHAINE[c] for c in s["classes"]], seuil=float(s["seuil_confiance"]),
                seuil_alerte=float(s["seuil_alerte"]), seuil_nom=float(s["seuil_nom"]), nommer_autre=not mb,
                regle_b=bool(s.get("regle_b")), seuil_inconnu_malade=s.get("seuil_inconnu_malade"), **en_plus)


M_SOUPE = seuils("modeles/maladies_soupe_v2_v8/poids", jnsp_alerte=True)
M_V2 = seuils("modeles/maladies_binome/maladies_v2/poids", jnsp_alerte=True)
M_V10B = seuils("modeles/maladies_binome/v10b", jnsp_alerte=True)


def _probas(df):
    cols = [c for c in ("p_saine", "p_black_sigatoka", "p_fusarium", "p_autre") if c in df.columns]
    return df[cols].to_numpy(dtype="float64")


def _lire(m, j):
    if m == "v10b":
        return pd.read_csv(V10B / f"predictions_v10b_{j}.csv")
    return pd.read_csv((ANCIENS if j == "validation" else DOS) / f"predictions_{m}_{j}.csv")


def fichier(c):
    return str(RACINE / c) if c.startswith("data/") else str(RACINE / "out/maladies/maladies_nuit" / c)


def charger_reglage():
    """{jeu: dict(chemin, vraie, malade, sig, P10, Pso, Pv2, loin, r_loin)} pour les 4 jeux de réglage."""
    jeux = {}
    for j in REGLAGE:
        v2, so, v10 = _lire("v2", j), _lire("soupe", j), _lire("v10b", j)
        pl = pd.read_csv(DOS / f"p_loin_{j}.csv")
        assert list(v2.chemin) == list(so.chemin) == list(v10.chemin) == list(pl.chemin), j
        vraie = v10.classe_vraie.to_numpy(dtype=object)
        jeux[j] = dict(chemin=v10.chemin.to_numpy(dtype=object), vraie=vraie, malade=~np.isin(vraie, ["saine"]),
                       sig=np.isin(vraie, ["cercosporiose_noire", "black_sigatoka", "sigatoka"]),
                       P10=_probas(v10), Pso=_probas(so), Pv2=_probas(v2), p_loin=pl.p_loin.values,
                       loin=pl.p_loin.values >= 0.5)
        jeux[j]["r_loin"] = maladies.decider_convnext(jeux[j]["Pv2"], M_V2)[0]
    return jeux


def charger_juges():
    """BanSpot et Cordana du Pérou, même structure. À n'appeler qu'une fois, après l'écriture des finalistes."""
    b = RACINE / "out/maladies/banspot"
    liste = pd.read_csv(RACINE / "data/raw/partage_binome_v10b/partage_corentin_2026-11-11/banspot_liste_test.csv")
    pl = np.load(b / "p_loin.npy")
    malade = liste.classe.eq("taches").values
    jeux = {"banspot": dict(chemin=liste.fichier.to_numpy(dtype=object), vraie=np.where(malade, "taches", "saine").astype(object),
                            malade=malade, sig=np.zeros(len(liste), bool), P10=np.load(b / "p_v10b.npy").astype("float64"),
                            Pso=np.load(b / "p_soupe.npy").astype("float64"), Pv2=np.load(b / "p_v2.npy").astype("float64"),
                            p_loin=pl, loin=pl >= 0.5)}
    v2, so, v10 = (pd.read_csv(V10B / f"predictions_{m}_cordana_perou.csv") for m in ("v2", "soupe", "v10b"))
    plc = pd.read_csv(V10B / "p_loin_cordana_perou.csv")
    assert list(v2.chemin) == list(so.chemin) == list(v10.chemin) == list(plc.chemin)
    jeux["cordana_perou"] = dict(chemin=v10.chemin.to_numpy(dtype=object), vraie=v10.classe_vraie.to_numpy(dtype=object),
                                 malade=np.ones(len(v10), bool), sig=np.zeros(len(v10), bool), P10=_probas(v10),
                                 Pso=_probas(so), Pv2=_probas(v2), p_loin=plc.p_loin.values, loin=plc.p_loin.values >= 0.5)
    for d in jeux.values():
        d["r_loin"] = maladies.decider_convnext(d["Pv2"], M_V2)[0]
    return jeux


def decider_v10b(P, **modifs):
    """Décision de la chaîne sur des probabilités à 4 classes, seuils de la v10b sauf ceux donnés dans modifs."""
    return maladies.decider_convnext(P, {**M_V10B, **modifs})[0]


def chaine(d, r_proche):
    """Réponse du module : branche « loin » (v2) inchangée, branche « proche » = r_proche."""
    return np.where(d["loin"], d["r_loin"], r_proche)


def mesure(d, rep):
    rep = np.asarray(rep, dtype=object)
    al = np.isin(rep, list(ALERTE))
    nm, ns = int(d["malade"].sum()), int((~d["malade"]).sum())
    msa, sea = int((d["malade"] & ~al).sum()), int((~d["malade"] & al).sum())
    out = dict(msa=msa, nm=nm, sea=sea, ns=ns, sea_averif=int((~d["malade"] & (rep == "a_verifier")).sum()),
               cout=100 * (3 * msa / nm + (sea / ns if ns else 0.0)))
    if d["sig"].any():
        out["sig_nommee"], out["n_sig"] = int((d["sig"] & (rep == "cercosporiose_noire")).sum()), int(d["sig"].sum())
    return out


def evaluer(jeux, f_proche):
    """f_proche(d) -> réponses « proche » pour toutes les photos du jeu. Renvoie {jeu: mesure} + coût moyen (points)."""
    r = {j: mesure(d, chaine(d, f_proche(d))) for j, d in jeux.items()}
    r["cout_moyen"] = float(np.mean([r[j]["cout"] for j in jeux]))
    return r


def finaliste(r, ref):
    """Règle « finaliste » du plan 4.4 (r et ref : sorties d'evaluer sur le réglage)."""
    c1 = r["cout_moyen"] <= ref["cout_moyen"] - 1.0
    c2 = r["validation"]["msa"] <= 14 and r["validation"]["sea"] <= 77
    c3 = all(100 * (r[j]["msa"] / r[j]["nm"] - ref[j]["msa"] / ref[j]["nm"]) <= 2.0 for j in ("tdtu", "psfd", "ethiopie"))
    return bool(c1 and c2 and c3), dict(cout=bool(c1), tanzanie=bool(c2), pays=bool(c3))


def ligne(nom, r, jeux=REGLAGE):
    t = []
    for j in jeux:
        m = r[j]
        s = f"{j[:4]} {m['msa']}/{m['nm']}"
        if m["ns"]:
            s += f" {m['sea']}/{m['ns']}({m['sea_averif']}av)"
        s += f" c={m['cout']:.1f}"
        if j == "validation":
            s += f" sig={m['sig_nommee']}"
        t.append(s)
    return f"{nom:44s} moy={r['cout_moyen']:.2f} | " + " | ".join(t)


def reference(jeux):
    return evaluer(jeux, lambda d: decider_v10b(d["P10"]))


if __name__ == "__main__":
    jeux = charger_reglage()
    ref = reference(jeux)
    for j, (a, b, c, e) in REFERENCE.items():
        m = ref[j]
        assert (m["msa"], m["nm"], m["sea"], m["ns"]) == (a, b, c, e), (j, m)
    print("référence du 11/11 retrouvée exactement")
    print(ligne("chaîne installée", ref))
    print({j: int(d["loin"].sum()) for j, d in jeux.items()}, "photos « loin »")
    (SORTIE / "reference.json").write_text(json.dumps(ref, ensure_ascii=False, indent=1), encoding="utf-8")
