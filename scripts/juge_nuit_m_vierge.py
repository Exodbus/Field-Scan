#!/usr/bin/env python3
"""Juge maladies : lecture unique du test vierge AgroVisionBD (plan 4.5), accord de Corentin le 13/11 vers 9 h 30.

Chaînes : installée (témoin), F1_trois_morceaux2x2 (t = 0,70), F3_trois (t = 0,74, pour information). Décisions du
code gelé de M-banc (m12_banc_finalistes.repondre, CANDIDATS). Méthode des bornes (journal, 6 h 50) : les morceaux
2 x 2 ne sont lus que pour les photos dont la décision de F1 en dépend. Probabilités sauvées par lots (reprise).
Rien ne se règle sur ce test.

Étapes : probas (aiguilleur, v10b, v2, soupe), morceaux, bilan.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_nuit_m_vierge.py probas
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")   # -I ignore PYTHONIOENCODING

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
from fieldscan.modules import maladies  # noqa: E402
import m12_banc_commun as B  # noqa: E402
import m12_banc_finalistes as MF  # noqa: E402
import juge_nuit_m_juges as JJ  # noqa: E402

V = RACINE / "out/controle_nuit_1112/juge_m/vierge"
V.mkdir(parents=True, exist_ok=True)
LISTE = RACINE / "data/raw/nuit_1112/figshare_agrovisionbd_bangladesh/liste.csv"
MODELES = {"loin": "modeles/maladies_aiguilleur/aiguilleur.npz", "v10b": "modeles/maladies_binome/v10b",
           "v2": "modeles/maladies_binome/maladies_v2/poids", "soupe": "modeles/maladies_soupe_v2_v8/poids"}
CHAINES = ["installee", "F1_trois_morceaux2x2", "F3_trois"]


def journal(t):
    print(f"[{dt.datetime.now():%H:%M:%S}] {t}", flush=True)


def liste():
    d = pd.read_csv(LISTE)
    d = d[d.retenue].reset_index(drop=True)
    assert len(d) == 1082 and (d.classe == "saine").sum() == 366
    d["photo"] = [str(RACINE / c) for c in d.chemin]
    return d


def calcul(nom, fonction, chemins, n_col, lot):
    """Probabilités par lots, sauvées à chaque lot ; NaN = pas encore lu."""
    f = V / f"p_{nom}.npy"
    P = np.load(f) if f.exists() else np.full((len(chemins),) + ((n_col,) if n_col else ()), np.nan)
    reste = np.flatnonzero(np.isnan(P).reshape(len(chemins), -1).any(1))
    t0 = time.time()
    for k in range(0, len(reste), lot):
        idx = reste[k:k + lot]
        P[idx] = fonction([chemins[i] for i in idx])
        np.save(f, P)
        journal(f"{nom} : {k + len(idx)}/{len(reste)} ({(time.time() - t0) / (k + len(idx)):.2f} s par photo)")
    return P


def probas():
    import torch
    torch.set_num_threads(8)
    sha = JJ.verifier_sha()
    journal(f"SHA-256 : {sum(sha.values())}/{len(sha)} identiques ; différents : {[f for f, ok in sha.items() if not ok]}")
    assert all(sha.values())
    (V / "sha.json").write_text(json.dumps(sha, indent=1), encoding="utf-8")
    d = liste()
    f = list(d.photo)
    assert all(Path(p).exists() for p in f)
    a = maladies.charger_aiguilleur(RACINE / MODELES["loin"])
    calcul("loin", lambda c: maladies.p_loin(c, a, lot=32), f, 0, 64)
    for nom in ("v10b", "v2", "soupe"):
        m = maladies.charger_convnext(RACINE / MODELES[nom])
        for r in m["reseaux"]:
            r.to(memory_format=torch.channels_last)
        calcul(nom, lambda c, m=m: maladies.predire_convnext(c, m), f, len(m["classes"]), 32)


def charger():
    d = liste()
    return d, dict(P10=np.load(V / "p_v10b.npy"), Pso=np.load(V / "p_soupe.npy"), Pv2=np.load(V / "p_v2.npy"),
                   p_loin=np.load(V / "p_loin.npy"), malade=(d.classe != "saine").to_numpy())


def morceaux():
    import torch
    torch.set_num_threads(8)
    d, z = charger()
    n = len(d)
    F1 = MF.CANDIDATS["F1_trois_morceaux2x2"]
    lo = JJ.alertes(MF.repondre(z["P10"], z["Pso"], z["Pv2"], z["p_loin"], F1, G2=np.tile(JJ.SAINE, (n, 4, 1))))
    hi = JJ.alertes(MF.repondre(z["P10"], z["Pso"], z["Pv2"], z["p_loin"], F1, G2=np.tile(JJ.MALADE, (n, 4, 1))))
    assert not (lo & ~hi).any(), "monotonie F1 violée"
    a_lire = np.flatnonzero(lo != hi)
    journal(f"bornes F1 : {len(a_lire)} photos sur {n} à lire en 2 x 2")
    f = V / "p_g2.npy"
    G = np.load(f) if f.exists() else np.full((n, 4, 4), np.nan)
    m = maladies.charger_convnext(RACINE / MODELES["v10b"])
    for r in m["reseaux"]:
        r.to(memory_format=torch.channels_last)
    reste = [i for i in a_lire if np.isnan(G[i]).any()]
    t0 = time.time()
    for k in range(0, len(reste), 4):
        idx = reste[k:k + 4]
        tuiles = [t for i in idx for t in JJ.morceaux(d.photo[i])]
        G[idx] = maladies.predire_convnext(tuiles, m).reshape(len(idx), 4, -1)
        np.save(f, G)
        journal(f"g2 : {k + len(idx)}/{len(reste)} ({(time.time() - t0) / (k + len(idx)):.2f} s par photo)")
    (V / "a_lire_g2.json").write_text(json.dumps([int(i) for i in a_lire]), encoding="utf-8")


def mesure(mal, al, averif, s):
    msa, nm = int((mal & ~al & s).sum()), int((mal & s).sum())
    sea, ns = int((~mal & al & s).sum()), int((~mal & s).sum())
    return dict(msa=msa, nm=nm, sea=sea, ns=ns, sea_averif=int((~mal & averif & s).sum()),
                cout=round(100 * (3 * msa / nm + (sea / ns if ns else 0.0)), 2) if nm else None)


def bilan():
    d, z = charger()
    n = len(d)
    f = V / "p_g2.npy"
    G = np.load(f) if f.exists() else np.full((n, 4, 4), np.nan)
    inc = np.isnan(G).any((1, 2))
    mal = z["malade"]
    cl = d.classe.to_numpy()
    out = dict(photos=n, saines=int((~mal).sum()), malades=int(mal.sum()), photos_loin=int((z["p_loin"] >= 0.5).sum()),
               photos_loin_par_classe=pd.Series(cl[z["p_loin"] >= 0.5]).value_counts().to_dict(),
               morceaux_lus=int((~inc).sum()))
    alertes = {}
    for nom in CHAINES:
        rep = {}
        for cote, rem in (("lo", JJ.SAINE), ("hi", JJ.MALADE)):
            Gc = G.copy()
            Gc[inc] = rem
            rep[cote] = MF.repondre(z["P10"], z["Pso"], z["Pv2"], z["p_loin"], MF.CANDIDATS[nom], G2=Gc)
        a_lo, a_hi = JJ.alertes(rep["lo"]), JJ.alertes(rep["hi"])
        r = rep["lo"]
        inconnues = int((a_lo != a_hi).sum())
        al = a_lo
        alertes[nom] = (a_lo, a_hi)
        res = dict(inconnues=inconnues, total=mesure(mal, al, r == "a_verifier", np.ones(n, bool)))
        # par maladie : les malades de la classe contre toutes les saines (coût de la classe)
        for c in ("black_sigatoka", "fusarium", "autre"):
            s = (cl == c) | (cl == "saine")
            res[c] = mesure(mal, al, r == "a_verifier", s)
            res[c]["noms"] = pd.Series(r[cl == c]).value_counts().to_dict()
        res["noms_saines"] = pd.Series(r[~mal]).value_counts().to_dict()
        out[nom] = res
        pd.DataFrame({"chemin": d.chemin, "classe": cl, "p_loin": z["p_loin"].round(4), "reponse": r}).to_csv(
            V / f"reponses_{nom}.csv", index=False)
    # deuxième avis : code du Contrôleur, deux remplissages des morceaux non lus
    dos = V / "second_avis"
    dos.mkdir(exist_ok=True)
    for k, x in (("v10b", z["P10"]), ("soupe", z["Pso"]), ("v2", z["Pv2"]), ("loin", z["p_loin"])):
        np.save(dos / f"{k}.npy", x)
    pd.DataFrame({"malade": mal.astype(int)}).to_csv(dos / "verite.csv", index=False)
    ecarts = {}
    for cote, rem in (("lo", JJ.SAINE), ("hi", JJ.MALADE)):
        Gc = G.copy()
        Gc[inc] = rem
        np.save(dos / f"g2_{cote}.npy", Gc)
        sortie = dos / f"alertes_{cote}.csv"
        subprocess.run([sys.executable, "-I", "-u", str(RACINE / "scripts/controle_nuit_m_appliquer.py"),
                        "--v10b", str(dos / "v10b.npy"), "--soupe", str(dos / "soupe.npy"), "--v2", str(dos / "v2.npy"),
                        "--loin", str(dos / "loin.npy"), "--v10b_g2", str(dos / f"g2_{cote}.npy"),
                        "--verite", str(dos / "verite.csv"), "--sortie", str(sortie)],
                       check=True, capture_output=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        ctrl = pd.read_csv(sortie)
        for nom, col in (("installee", "reference_v10b"), ("F1_trois_morceaux2x2", "F1_trois_morceaux2x2"), ("F3_trois", "F3_trois")):
            a = alertes[nom][0 if cote == "lo" else 1]
            ecarts[f"{nom}_{cote}"] = int((ctrl[col].astype(bool).to_numpy() != a).sum())
    out["ecarts_second_avis"] = ecarts
    (V / "bilan_vierge.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=int), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1, default=int))


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("etape", choices=["probas", "morceaux", "bilan"])
    x = a.parse_args()
    {"probas": probas, "morceaux": morceaux, "bilan": bilan}[x.etape]()
