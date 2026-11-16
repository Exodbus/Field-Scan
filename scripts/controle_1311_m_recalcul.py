#!/usr/bin/env python3
"""Contrôleur, nuit du 13/11 : recalcul INDÉPENDANT (n'importe aucun code des agents) de la référence F1 et des
candidats maladies sur le réglage du plan 4.3 : validation Tanzanie, TDTU, PSFD, Éthiopie, AgroVisionBD (reclassé en
réglage par le plan, section 3 ; cache out/controle_nuit_1112/juge_m/vierge/), plus roamer_dev_loin_feuilles.

Aucun juge relu (BanSpot, Cordana du Pérou) : un garde-fou refuse tout chemin qui les nomme.

Règle d'alerte de F1 (démontrée par mon prédécesseur sur decider_convnext, vérifiée ici par les comptes) :
  P(saine) du lecteur proche = mélange géométrique (v10b lue en morceaux 2 x 2 « deux plus fortes », soupe, v2) ;
  photo proche en alerte ssi P(saine) < 0,70 ; photo loin (p_loin >= 0,5) en alerte ssi P_v2(saine) <= 0,70 ou
  alerte du lecteur proche.
Morceaux inconnus : bornes (tous « saine 100 % », puis tous « malade 100 % ») ; décision sûre si les deux concordent.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_1311_m_recalcul.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
OUT = RACINE / "out/controle_nuit_1311"
OUT.mkdir(parents=True, exist_ok=True)
JEUX4 = ["validation", "tdtu", "psfd", "ethiopie"]
JEUX5 = JEUX4 + ["agrovision"]
K = RACINE / "out/maladies/nuit_1112/banc/kaggle_morceaux"
VIERGE = RACINE / "out/controle_nuit_1112/juge_m/vierge"
BANC = RACINE / "out/maladies/nuit_1311/banc"
C4 = ["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]
INTERDITS = ("banspot", "cordana", "perou", "test_")
T_F1 = 0.70


def garde(p):
    assert not any(m in str(p).lower() for m in INTERDITS), f"juge refusé : {p}"
    return p


def charger(roamer=True):
    jeux = {}
    for j in JEUX4:
        v10 = pd.read_csv(garde(RACINE / f"out/maladies/v10b/predictions_v10b_{j}.csv"))
        dos = RACINE / ("out/maladies/dinov2_ft" if j == "validation" else "out/maladies/cinq_classes")
        so = pd.read_csv(garde(dos / f"predictions_soupe_{j}.csv"))
        v2 = pd.read_csv(garde(dos / f"predictions_v2_{j}.csv"))
        pl = pd.read_csv(garde(RACINE / f"out/maladies/cinq_classes/p_loin_{j}.csv"))
        for d in (so, v2, pl):
            assert list(d.chemin) == list(v10.chemin), j
        G2 = np.load(garde(K / f"morceaux_{j}.npz"))["g2"].astype("f8")
        assert G2.shape[0] == len(v10)
        jeux[j] = dict(malade=(v10.classe_vraie != "saine").to_numpy(), vraie=v10.classe_vraie.to_numpy(object),
                       P10=v10[C4].to_numpy("f8"), Pso=so[C4[:3]].to_numpy("f8"), Pv2=v2[C4[:3]].to_numpy("f8"),
                       pl=pl.p_loin.to_numpy("f8"), G2=G2, chemin=v10.chemin.to_numpy(object))
    rep = pd.read_csv(VIERGE / "reponses_installee.csv", usecols=["chemin", "classe", "p_loin"])
    G2 = np.load(VIERGE / "p_g2.npy").astype("f8")
    lus = json.loads((VIERGE / "a_lire_g2.json").read_text(encoding="utf-8"))
    jeux["agrovision"] = dict(malade=rep.classe.ne("saine").to_numpy(), vraie=rep.classe.to_numpy(object),
                              P10=np.load(VIERGE / "p_v10b.npy").astype("f8"), Pso=np.load(VIERGE / "p_soupe.npy").astype("f8"),
                              Pv2=np.load(VIERGE / "p_v2.npy").astype("f8"), pl=np.load(VIERGE / "p_loin.npy").astype("f8"),
                              G2=G2, chemin=rep.chemin.to_numpy(object), lus=lus)
    assert np.allclose(jeux["agrovision"]["pl"], rep.p_loin.to_numpy("f8"), atol=1e-4)
    if roamer and (BANC / "roamer/p_v10b.npy").exists():
        c = pd.read_csv(BANC / "roamer/chemins.csv")
        P = {k: np.load(BANC / f"roamer/p_{k}.npy").astype("f8") for k in ("loin", "v2", "soupe", "v10b")}
        G2 = np.full((len(c), 4, 4), np.nan)
        if (BANC / "roamer/g2_roamer.npz").exists():
            z = np.load(BANC / "roamer/g2_roamer.npz")
            G2[z["indices"]] = z["g2"]
        fait = ~np.isnan(P["v10b"][:, 0])
        jeux["roamer"] = dict(malade=c.etat.eq("malade").to_numpy()[fait], vraie=c.etat.to_numpy(object)[fait],
                              P10=P["v10b"][fait], Pso=P["soupe"][fait], Pv2=P["v2"][fait], pl=P["loin"][fait],
                              G2=G2[fait], chemin=c.image.to_numpy(object)[fait], complet=bool(fait.all()),
                              n_total=len(c))
    for d in jeux.values():
        d["loin"] = d["pl"] >= 0.5
    return jeux


def lecture_g2(P10, G2):
    """v10b lue en morceaux : P(malade) = moyenne de la photo entière et des deux morceaux les plus malades."""
    pm = ((1 - P10[:, 0]) + np.sort(1 - G2[:, :, 0], 1)[:, -2:].mean(1)) / 2
    Q = P10 * (pm / np.clip(1 - P10[:, 0], 1e-9, None))[:, None]
    Q[:, 0] = 1 - pm
    return Q


def ps_geo(listes, autres):
    """Moyenne géométrique des 3 classes communes ; « autre » ajouté au dénominateur (moyenne arithmétique / n)."""
    n = len(listes)
    g = np.exp(sum(np.log(np.clip(P[:, :3], 1e-9, 1)) for P in listes) / n)
    return g[:, 0] / (g.sum(1) + sum(autres) / n)


def alerte_f1(d, G2=None, t=T_F1):
    G2 = d["G2"] if G2 is None else G2
    Q = lecture_g2(d["P10"], G2)
    ap = ps_geo([Q, d["Pso"], d["Pv2"]], [Q[:, 3]]) < t
    return np.where(d["loin"], (d["Pv2"][:, 0] <= 0.70) | ap, ap)


def bornes(fonction, d):
    """Décision sûre / inconnue quand des morceaux manquent : bornes « saine 100 % » et « malade 100 % »."""
    inc = np.isnan(d["G2"]).any(axis=(1, 2))
    G_s, G_m = d["G2"].copy(), d["G2"].copy()
    G_s[inc] = np.nan_to_num(G_s[inc], nan=0.0); G_s[inc, :, 0] = np.where(np.isnan(d["G2"][inc, :, 0]), 1.0, G_s[inc, :, 0])
    G_m[inc] = np.nan_to_num(G_m[inc], nan=0.0); G_m[inc, :, 0] = np.where(np.isnan(d["G2"][inc, :, 0]), 0.0, G_m[inc, :, 0])
    a_s, a_m = fonction(d, G_s), fonction(d, G_m)
    return a_m, a_s != a_m   # alerte (borne « malade », la plus prudente) et masque des inconnues


def mesure(d, al, inconnu=None):
    m = d["malade"]
    msa, sea, nm, ns = int((m & ~al).sum()), int((~m & al).sum()), int(m.sum()), int((~m).sum())
    r = dict(msa=msa, nm=nm, sea=sea, ns=ns, cout=100 * (3 * msa / nm + (sea / ns if ns else 0.0)))
    r["sea_loin"] = int((~m & al & d["loin"]).sum()); r["ns_loin"] = int((~m & d["loin"]).sum())
    if inconnu is not None:
        r["inconnues"] = int(inconnu.sum())
    return r


def evaluer(jeux, fonction, noms=None):
    noms = noms or [j for j in JEUX5 + ["roamer"] if j in jeux]
    r, alertes = {}, {}
    for j in noms:
        al, inc = bornes(fonction, jeux[j])
        r[j] = mesure(jeux[j], al, inc)
        alertes[j] = al
    r["cout_reglage"] = float(np.mean([r[j]["cout"] for j in JEUX5]))
    return r, alertes


def regle_finaliste(r, ref, ratio_temps):
    """Plan 4.3, règle « finaliste »."""
    c = {}
    c["cout"] = r["cout_reglage"] <= ref["cout_reglage"] - 1.0
    c["tanzanie"] = r["validation"]["msa"] <= 14 and r["validation"]["sea"] <= 77
    c["pays"] = all(100 * (r[j]["msa"] / r[j]["nm"] - ref[j]["msa"] / ref[j]["nm"]) <= 2.0 for j in JEUX5)
    c["roamer"] = ("roamer" in r) and r["roamer"]["msa"] <= ref["roamer"]["msa"] + 2
    c["temps"] = ratio_temps is not None and ratio_temps <= 1.2
    return all(c.values()), c


def regle_rapide(al, al_ref, jeux, ratio_temps):
    """Plan 4.3, « variante rapide » : <= 0,5 % de décisions différentes sur les 5 jeux, pas de malade ratée en plus,
    au moins 30 % de temps en moins."""
    diff = sum(int((al[j] != al_ref[j]).sum()) for j in JEUX5)
    n = sum(len(al[j]) for j in JEUX5)
    rat_plus = sum(int((jeux[j]["malade"] & ~al[j]).sum() - (jeux[j]["malade"] & ~al_ref[j]).sum()) for j in JEUX5)
    c = dict(diff=diff <= 0.005 * n, ratees=rat_plus <= 0, temps=ratio_temps is not None and ratio_temps <= 0.70)
    return all(c.values()), c, dict(diff=diff, n=n, taux=diff / n, ratees_en_plus=rat_plus)


def texte(nom, r):
    return (f"{nom:28s} coût de réglage {r['cout_reglage']:.3f} ; "
            + " ; ".join(f"{j} {r[j]['msa']}/{r[j]['nm']} {r[j]['sea']}/{r[j]['ns']} (loin {r[j]['sea_loin']}/{r[j]['ns_loin']}"
                         f"{', inc ' + str(r[j]['inconnues']) if r[j].get('inconnues') else ''})"
                         for j in JEUX5 + ["roamer"] if j in r))


if __name__ == "__main__":
    jeux = charger()
    ref, al_ref = evaluer(jeux, lambda d, G2: alerte_f1(d, G2))
    print(texte("F1 (référence)", ref))
    if "roamer" in jeux:
        print(f"roamer : {len(jeux['roamer']['malade'])} / {jeux['roamer']['n_total']} photos calculées")
    (OUT / "m_reference_f1.json").write_text(json.dumps(ref, ensure_ascii=False, indent=1), encoding="utf-8")
