#!/usr/bin/env python3
"""Candidats de M-banc (nuit du 13/11) : réponses de chaque candidat à partir des probabilités, comme
scripts/m12_banc_finalistes.py. Définitions : out/maladies/nuit_1311/banc/finalistes.md.

Entrée : fichiers .npy dans l'ordre des photos (mêmes conventions que m12_banc_finalistes.py) :
  --v10b (n, 4) ; --soupe (n, 3) ; --v2 (n, 3) ; --loin (n,) ;
  --v10b_g2 (n, 4, 4) morceaux 2 x 2 de la v10b, NaN pour les photos non lues (facultatif : tout NaN si absent).
  Pour F1_bornes, la soupe et la v10b peuvent être NaN sur les photos « loin » où la v2 alerte (non lues).
Sortie : CSV des réponses (F1 et candidats) ; une réponse « inconnue_lire_morceaux » signale une photo dont l'alerte
dépend de morceaux non lus. --a_lire liste.json écrit les indices des photos dont F1_bornes a besoin des morceaux.
--verite fichier CSV avec une colonne « malade » (0/1) : affiche malades sans alerte et saines en alerte.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_banc_finalistes.py --v10b p_v10b.npy \
        --soupe p_soupe.npy --v2 p_v2.npy --loin p_loin.npy [--v10b_g2 p_g2.npy] [--a_lire a_lire.json] --sortie rep.csv

Chaîne complète « F1_bornes » sur des photos (lecteurs lus seulement là où il le faut) : fonction executer_f1_bornes.
"""
import argparse
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

AL = list(B.ALERTE)
M_PROCHE = {**B.M_V10B, "seuil": 0.70}   # seuils de la v10b, confiance 0,70, jnsp_alerte vrai (config.yaml)
M_LOIN = B.M_V2                          # seuils de la v2, jnsp_alerte vrai (jnsp_alerte_loin: true)
G_SAINE, G_MALADE = np.array([1.0, 0, 0, 0]), np.array([0.0, 0, 1.0, 0])


def _remplir(G2, v):
    G = G2.copy()
    G[np.isnan(G[:, :, 0])] = v
    return G


def f1(P10, Pso, Pv2, pl, G2):
    """F1 installé (maladies.decider_melange) ; G2 sans NaN."""
    return maladies.decider_melange(P10, Pso, Pv2, pl, G2, M_PROCHE, M_LOIN, True)[0].astype(object)


def masques_f1_bornes(P10, Pso, Pv2, pl):
    """lv : photos « loin » où la v2 alerte (réponse de la v2, soupe et v10b inutiles) ;
    dep : photos dont l'alerte de F1 change entre morceaux « saine 100 % » et « malade 100 % » (morceaux à lire)."""
    n = len(pl)
    rl = maladies.decider_convnext(Pv2, M_LOIN)[0]
    lv = (pl >= 0.5) & np.isin(rl, AL)
    P10s, Psos = np.where(lv[:, None], 0.5, P10), np.where(lv[:, None], 0.5, Pso)   # valeurs neutres si non lues
    a0 = np.isin(f1(P10s, Psos, Pv2, pl, np.tile(G_SAINE, (n, 4, 1))), AL)
    a1 = np.isin(f1(P10s, Psos, Pv2, pl, np.tile(G_MALADE, (n, 4, 1))), AL)
    return lv, (a0 != a1) & ~lv


def f1_bornes(P10, Pso, Pv2, pl, G2):
    """Variante rapide de F1 : mêmes alertes que F1 par construction. G2 n'est lu que sur les photos « dep » ; ailleurs
    réponse du mélange à trois sans morceaux. Réponse « inconnue_lire_morceaux » si G2 manque là où il faut."""
    lv, dep = masques_f1_bornes(P10, Pso, Pv2, pl)
    P10s, Psos = np.where(lv[:, None], 0.5, P10), np.where(lv[:, None], 0.5, Pso)
    sans = f1(P10s, Psos, Pv2, pl, None)
    avec = f1(P10s, Psos, Pv2, pl, _remplir(G2, G_SAINE))
    rep = np.where(dep, avec, sans)
    rep[dep & np.isnan(G2[:, :, 0]).any(1)] = "inconnue_lire_morceaux"
    return rep


CANDIDATS = {"F1": None, "F1_bornes": f1_bornes}


def executer_f1_bornes(chemins, dossiers=None, aiguilleur=None):
    """Chaîne complète F1_bornes sur des photos : aiguilleur et v2 sur toutes ; soupe et v10b sauf « loin » + v2 en
    alerte ; morceaux 2 x 2 seulement pour les photos « dep ». Renvoie (réponses, p_loin, P10, Pso, Pv2, G2)."""
    dossiers = dossiers or {"v10b": RACINE / "modeles/maladies_binome/v10b",
                            "soupe": RACINE / "modeles/maladies_soupe_v2_v8/poids",
                            "v2": RACINE / "modeles/maladies_binome/maladies_v2/poids"}
    aiguilleur = aiguilleur or RACINE / "modeles/maladies_aiguilleur/aiguilleur.npz"
    n = len(chemins)
    pl = maladies.p_loin(chemins, maladies.charger_aiguilleur(Path(aiguilleur)))
    m = {k: maladies.charger_convnext(Path(v)) for k, v in dossiers.items()}
    Pv2 = maladies.predire_convnext(chemins, m["v2"]).astype("float64")
    lv = (pl >= 0.5) & np.isin(maladies.decider_convnext(Pv2, M_LOIN)[0], AL)
    P10, Pso = np.full((n, 4), np.nan), np.full((n, 3), np.nan)
    a_lire = [chemins[i] for i in np.flatnonzero(~lv)]
    if a_lire:
        P10[~lv] = maladies.predire_convnext(a_lire, m["v10b"])
        Pso[~lv] = maladies.predire_convnext(a_lire, m["soupe"])
    _, dep = masques_f1_bornes(P10, Pso, Pv2, pl)
    G2 = np.full((n, 4, 4), np.nan)
    idx = np.flatnonzero(dep)
    for k in range(0, len(idx), 8):
        lot = idx[k:k + 8]
        G2[lot] = maladies.predire_convnext([t for i in lot for t in maladies.morceaux_2x2(chemins[i])], m["v10b"]).reshape(len(lot), 4, -1)
    return f1_bornes(P10, Pso, Pv2, pl, G2), pl, P10, Pso, Pv2, G2


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    for k in ("v10b", "soupe", "v2", "loin", "sortie"):
        a.add_argument(f"--{k}", required=True)
    a.add_argument("--v10b_g2")
    a.add_argument("--a_lire")
    a.add_argument("--verite")
    x = a.parse_args()
    P10, Pso, Pv2, pl = (np.load(getattr(x, k)).astype("float64") for k in ("v10b", "soupe", "v2", "loin"))
    G2 = np.load(x.v10b_g2).astype("float64") if x.v10b_g2 else np.full((len(pl), 4, P10.shape[1]), np.nan)
    out = {"F1_bornes": f1_bornes(P10, Pso, Pv2, pl, G2)}
    lv = (pl >= 0.5) & np.isin(maladies.decider_convnext(Pv2, M_LOIN)[0], AL)
    inc_f1 = np.isnan(G2[:, :, 0]).any(1) & ~lv
    r0, r1 = f1(P10, Pso, Pv2, pl, _remplir(G2, G_SAINE)), f1(P10, Pso, Pv2, pl, _remplir(G2, G_MALADE))
    rf1 = np.where(inc_f1, "noms_inexacts_morceaux_non_lus", r0).astype(object)   # F1 installé lit les morceaux partout
    rf1[np.isin(r0, AL) != np.isin(r1, AL)] = "inconnue_lire_morceaux"
    out["F1"] = rf1
    df = pd.DataFrame(out)
    if x.a_lire:
        _, dep = masques_f1_bornes(P10, Pso, Pv2, pl)
        Path(x.a_lire).write_text(json.dumps([int(i) for i in np.flatnonzero(dep & np.isnan(G2[:, :, 0]).any(1))]), encoding="utf-8")
    if x.verite:
        mal = pd.read_csv(x.verite)["malade"].astype(bool).to_numpy()
        al = df["F1_bornes"].isin(AL).to_numpy()
        print(f"F1_bornes : malades sans alerte {int((mal & ~al).sum())}/{int(mal.sum())} ; saines en alerte "
              f"{int((~mal & al).sum())}/{int((~mal).sum())}")
    df.to_csv(x.sortie, index=False)
    print("écrit :", x.sortie)
