#!/usr/bin/env python3
"""Banc commun de M-banc, nuit du 13/11 (docs/plan_nuit_2026-11-13.md, sections 4.1 et 4.3).

Jeux de réglage (5) : validation Tanzanie, TDTU, PSFD, Éthiopie (probabilités en cache, m12_banc_commun.charger_reglage ;
morceaux 2 x 2 de la v10b lus sur tous ces jeux par le carnet Kaggle de la nuit du 12/11), AgroVisionBD (probabilités
en cache dans out/controle_nuit_1112/juge_m/vierge/, morceaux lus pour 113 photos, NaN ailleurs).
Jeu « loin » à part : data/roamer_dev_loin_feuilles (probabilités calculées par scripts/m13_banc_calcul_roamer.py,
morceaux par scripts/m13_banc_calcul_g2.py là où une décision en dépend).

Morceaux inconnus (NaN) : méthode des bornes. La décision est prise deux fois, morceaux remplis « saine 100 % » puis
« malade 100 % » ; si l'alerte est la même, elle est sûre ; sinon la photo est « inconnue » et ses morceaux doivent être
lus. Pour F1 et tous les candidats de ce banc, P(saine) du lecteur proche décroît quand P(malade) des morceaux croît
(décision « pas d'alerte » ssi P(saine) du mélange >= seuil), donc les deux bornes encadrent toutes les valeurs.

Les juges (BanSpot, Cordana du Pérou) ne sont jamais chargés ici.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
from fieldscan.modules import maladies  # noqa: E402
import m12_banc_commun as B  # noqa: E402

SORTIE = RACINE / "out/maladies/nuit_1311/banc"
SORTIE.mkdir(parents=True, exist_ok=True)
KAG = RACINE / "out/maladies/nuit_1112/banc/kaggle_morceaux"
VIERGE = RACINE / "out/controle_nuit_1112/juge_m/vierge"
ROAMER = SORTIE / "roamer"
ALERTE = B.ALERTE
JEUX5 = ["validation", "tdtu", "psfd", "ethiopie", "agrovision"]
M_PROCHE_F1 = {**B.M_V10B, "seuil": 0.70}   # jnsp_alerte=True, comme config.yaml (jnsp_alerte: true)
M_LOIN = B.M_V2                              # jnsp_alerte=True, comme config.yaml (jnsp_alerte_loin: true)


def _d(chemin, vraie, malade, P10, Pso, Pv2, pl, G2):
    d = dict(chemin=np.asarray(chemin, dtype=object), vraie=np.asarray(vraie, dtype=object), malade=np.asarray(malade, bool),
             P10=P10.astype("float64"), Pso=Pso.astype("float64"), Pv2=Pv2.astype("float64"),
             p_loin=np.asarray(pl, "float64"), G2=G2.astype("float64"))
    d["sig"] = np.isin(d["vraie"], ["cercosporiose_noire", "black_sigatoka", "sigatoka"])
    d["loin"] = d["p_loin"] >= 0.5
    d["r_loin"] = maladies.decider_convnext(d["Pv2"], M_LOIN)[0]
    return d


def charger(roamer=True):
    jeux = {}
    for j, d in B.charger_reglage().items():
        G2 = np.load(KAG / f"morceaux_{j}.npz")["g2"].astype("float64")
        assert G2.shape[0] == len(d["chemin"])
        jeux[j] = _d(d["chemin"], d["vraie"], d["malade"], d["P10"], d["Pso"], d["Pv2"], d["p_loin"], G2)
    rep = pd.read_csv(VIERGE / "reponses_installee.csv")
    jeux["agrovision"] = _d(rep.chemin, rep.classe, rep.classe.ne("saine").values, np.load(VIERGE / "p_v10b.npy"),
                            np.load(VIERGE / "p_soupe.npy"), np.load(VIERGE / "p_v2.npy"), np.load(VIERGE / "p_loin.npy"),
                            np.load(VIERGE / "p_g2.npy"))
    assert np.allclose(jeux["agrovision"]["p_loin"].round(4), rep.p_loin.values, atol=1e-4)
    g2_ag = SORTIE / "g2_agrovision.npz"   # morceaux lus cette nuit (scripts/m13_banc_calcul_g2.py)
    if g2_ag.exists():
        z = np.load(g2_ag)
        jeux["agrovision"]["G2"][z["indices"]] = z["g2"]
    if roamer:
        jeux["roamer"] = charger_roamer()
    return jeux


def charger_roamer():
    c = pd.read_csv(ROAMER / "chemins.csv")
    P = {k: np.load(ROAMER / f"p_{k}.npy") for k in ("loin", "v2", "soupe", "v10b")}
    # Photos utilisables : « fait_tout » = tous les lecteurs lus ; « fait_f1 » = v2 lue, et soupe + v10b lues sauf si la
    # photo est « loin » avec la v2 en alerte (réponse de la v2 pour F1 et pour toute règle qui garde cette branche).
    v2_lu = ~np.isnan(P["v2"][:, 0])
    rl = maladies.decider_convnext(np.nan_to_num(P["v2"], nan=1 / 3), M_LOIN)[0]
    lv = (P["loin"] >= 0.5) & np.isin(rl, list(ALERTE)) & v2_lu
    fait_tout = ~np.isnan(P["v10b"][:, 0]) & v2_lu
    fait = fait_tout | lv
    P["v10b"] = np.where(np.isnan(P["v10b"]), 0.25, P["v10b"])   # valeurs neutres là où non lues (jamais utilisées
    P["soupe"] = np.where(np.isnan(P["soupe"]), 1 / 3, P["soupe"])   # dans une mesure : masques ci-dessus)
    P["v2"] = np.where(np.isnan(P["v2"]), 1 / 3, P["v2"])
    G2 = np.full((len(c), 4, 4), np.nan)
    g = ROAMER / "g2_roamer.npz"
    if g.exists():
        z = np.load(g)
        G2[z["indices"]] = z["g2"]
    d = _d(np.array([str(RACINE / "data/roamer_dev_loin_feuilles" / x) for x in c.image], dtype=object), c.etat,
           c.etat.eq("malade").values, P["v10b"], P["soupe"], P["v2"], P["loin"], G2)
    d["fait"] = fait
    d["fait_f1"], d["fait_tout"] = fait, fait_tout
    d["projet"] = c.projet.to_numpy(dtype=object)
    return d


# --------------------------------------------------------------------------------------------------------------------
# F1 et outils de décision
# --------------------------------------------------------------------------------------------------------------------
def remplir(G2, valeur):
    """Morceaux inconnus remplis par « saine 100 % » (valeur = 0) ou « malade 100 % » (valeur = 1, mis en fusariose ;
    seule P(saine) des morceaux compte dans la lecture)."""
    G = G2.copy()
    nan = np.isnan(G[:, :, 0])
    G[nan] = np.array([1.0, 0, 0, 0]) if valeur == 0 else np.array([0.0, 0, 1.0, 0])
    return G


def f1(d, G2):
    """Réponses de F1 (code installé, maladies.decider_melange) avec des morceaux sans NaN."""
    return maladies.decider_melange(d["P10"], d["Pso"], d["Pv2"], d["p_loin"], G2, M_PROCHE_F1, M_LOIN, True)[0]


def bornes(d, regle):
    """regle(d, G2) -> réponses. Renvoie (alerte, réponses avec morceaux « saine », masque des photos inconnues)."""
    if not np.isnan(d["G2"][:, :, 0]).any():
        r = regle(d, d["G2"])
        return np.isin(r, list(ALERTE)), r, np.zeros(len(r), bool)
    r0, r1 = regle(d, remplir(d["G2"], 0)), regle(d, remplir(d["G2"], 1))
    a0, a1 = np.isin(r0, list(ALERTE)), np.isin(r1, list(ALERTE))
    return a0, r0, a0 != a1


def mesure(d, alerte, inconnu=None, masque=None):
    m = np.ones(len(alerte), bool) if masque is None else masque
    mal, sai = d["malade"] & m, ~d["malade"] & m
    nm, ns = int(mal.sum()), int(sai.sum())
    msa, sea = int((mal & ~alerte).sum()), int((sai & alerte).sum())
    out = dict(msa=msa, nm=nm, sea=sea, ns=ns, cout=100 * (3 * msa / nm + (sea / ns if ns else 0.0)))
    if inconnu is not None:
        out["inconnues"] = int((inconnu & m).sum())
    return out


def evaluer(jeux, regle, noms=JEUX5):
    """Mesure de la règle sur les jeux donnés ; coût de réglage = moyenne des coûts des 5 jeux."""
    r = {}
    for j in noms:
        d = jeux[j]
        a, rep, inc = bornes(d, regle)
        masque = d.get("fait")
        r[j] = mesure(d, a, inc, masque)
        r[j]["sea_averif"] = int((~d["malade"] & (rep == "a_verifier") & (masque if masque is not None else True)).sum())
        if j == "agrovision" or j == "roamer":
            lo = d["loin"] & ~d["malade"] & (masque if masque is not None else True)
            r[j]["saines_loin_alerte"] = int((lo & a).sum())
            r[j]["saines_loin"] = int(lo.sum())
        r[j]["_alerte"] = a
    if all(j in r for j in JEUX5):
        r["cout_reglage"] = float(np.mean([r[j]["cout"] for j in JEUX5]))
    return r


def finaliste(r, ref, temps_ratio=None):
    """Règle « finaliste » du plan 4.3 (sans le temps si temps_ratio est None)."""
    c = {}
    c["cout"] = r["cout_reglage"] <= ref["cout_reglage"] - 1.0
    c["tanzanie"] = r["validation"]["msa"] <= 14 and r["validation"]["sea"] <= 77
    c["pays"] = all(100 * (r[j]["msa"] / r[j]["nm"] - ref[j]["msa"] / ref[j]["nm"]) <= 2.0 for j in JEUX5)
    if "roamer" in r and "roamer" in ref:
        c["roamer"] = r["roamer"]["msa"] <= ref["roamer"]["msa"] + 2
    if temps_ratio is not None:
        c["temps"] = temps_ratio <= 1.2
    inconnues = sum(r[j].get("inconnues", 0) for j in r if isinstance(r[j], dict) and j in JEUX5 + ["roamer"])
    return bool(all(c.values())), c, inconnues


def ecart_alertes(r, ref, noms=JEUX5):
    """Nombre de décisions d'alerte différentes de la référence et malades sans alerte en plus (somme des jeux)."""
    diff = sum(int((r[j]["_alerte"] != ref[j]["_alerte"]).sum()) for j in noms)
    n = sum(len(r[j]["_alerte"]) for j in noms)
    plus = sum(max(0, r[j]["msa"] - ref[j]["msa"]) for j in noms)
    return diff, n, plus


def ligne(nom, r, noms=None):
    noms = noms or [j for j in JEUX5 + ["roamer"] if j in r]
    t = []
    for j in noms:
        m = r[j]
        s = f"{j[:4]} {m['msa']}/{m['nm']}"
        if m["ns"]:
            s += f" {m['sea']}/{m['ns']}({m['sea_averif']}av)"
        if "saines_loin" in m:
            s += f" loinS {m['saines_loin_alerte']}/{m['saines_loin']}"
        if m.get("inconnues"):
            s += f" ?{m['inconnues']}"
        s += f" c={m['cout']:.2f}"
        t.append(s)
    cr = f"moy5={r['cout_reglage']:.2f}" if "cout_reglage" in r else ""
    return f"{nom:42s} {cr} | " + " | ".join(t)


def propre(r):
    """Copie sérialisable (sans les tableaux d'alerte)."""
    return {k: ({kk: vv for kk, vv in v.items() if not kk.startswith("_")} if isinstance(v, dict) else v) for k, v in r.items()}


class Compteur:
    """Compte les essais (une configuration évaluée sur le réglage = un essai) et les garde dans un fichier json."""

    def __init__(self, nom):
        self.f = SORTIE / f"essais_{nom}.json"
        self.essais = []

    def ajouter(self, famille, nom, r, ok=None, det=None):
        self.essais.append(dict(famille=famille, nom=nom, finaliste=ok, detail=det, **propre(r)))

    def ecrire(self):
        self.f.write_text(json.dumps(self.essais, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        return len(self.essais)


if __name__ == "__main__":
    jeux = charger(roamer=(ROAMER / "p_v10b.npy").exists())
    ref = evaluer(jeux, f1, [j for j in JEUX5 + ["roamer"] if j in jeux])
    print(ligne("F1 (référence, même code)", ref))
    (SORTIE / "reference_f1.json").write_text(json.dumps(propre(ref), ensure_ascii=False, indent=1), encoding="utf-8")
