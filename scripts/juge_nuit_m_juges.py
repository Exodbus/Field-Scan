#!/usr/bin/env python3
"""Juge maladies, nuit du 12/11 : lecture unique des juges (BanSpot, Cordana du Pérou) pour la liste gelée.

Règles (plan 4.4, non modifiées) : alerte = maladie nommée, « malade, non identifiée » ou « à vérifier ». Adoption
proposée si BanSpot tachées sans alerte <= 12 / 646 et saines en alerte <= 61 / 646 et Cordana du Pérou en alerte
>= 97 % ; entre finalistes qui passent : coût de réglage le plus bas.

Décisions : celles de scripts/m12_banc_finalistes.py (repondre, CANDIDATS), importé tel quel (non modifié).
Calculs évités par bornes exactes (voir docs/nuit_2026-11-12/journal_juge_maladies.md, 6 h 50) :
  F1 : décision connue si elle est la même avec des morceaux « saine 100 % » (x = 0) et « malade 100 % » (x = 1) ;
  C_quatre_v12a14 : alerte certaine si le mélange alerte même avec une v12a14 « saine 100 % » ;
  v12a13 : lu sur toutes les photos proches (les photos loin vont à la v2).

Étapes :
  bornes            : vérifie les SHA-256, charge les juges UNE fois (B.charger_juges), sauve juge_m/juges.npz,
                      mesure le témoin (chaîne installée), écrit les listes de photos à lire.
  lire --quoi Q     : Q = g2 (F1), v12a14, v12a13 ; lit les photos de la liste, sauve au fur et à mesure (reprise
                      possible) ; --jusqua HH:MM arrête proprement.
  etat              : bornes des comptes et verdict déjà certain ou non, pour chaque finaliste.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_nuit_m_juges.py bornes
"""
import argparse
import datetime as dt
import hashlib
import io
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")   # -I ignore PYTHONIOENCODING

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
from fieldscan.modules import maladies  # noqa: E402
import m12_banc_commun as B  # noqa: E402
import m12_banc_finalistes as MF  # noqa: E402

J = RACINE / "out/controle_nuit_1112/juge_m"
J.mkdir(parents=True, exist_ok=True)
JEUX = ["banspot", "cordana_perou"]
DOSSIERS = {"g2": "modeles/maladies_binome/v10b", "v12a14": "modeles/maladies_v12_essais/v12a14",
            "v12a13": "modeles/maladies_v12_essais/v12a13"}
F1, C4 = MF.CANDIDATS["F1_trois_morceaux2x2"], MF.CANDIDATS["C_quatre_v12a14"]
SAINE = np.array([1.0, 0.0, 0.0, 0.0])
MALADE = np.array([0.0, 1.0, 0.0, 0.0])


def journal(t):
    print(f"[{dt.datetime.now():%H:%M:%S}] {t}", flush=True)


def verifier_sha():
    attendu = {}
    for l in (RACINE / "out/controle_nuit_1112/empreintes_liste_gelee.txt").read_text(encoding="utf-8").splitlines():
        if l.strip():
            h, f = l.split(None, 1)
            attendu[f.strip()] = h
    res = {}
    for f, h in attendu.items():
        p = RACINE / f
        if "maladies" in f or f.startswith("scripts/m12") or f.startswith("scripts/controle_nuit_m"):
            res[f] = p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == h
    return res


def charger():
    return dict(np.load(J / "juges.npz", allow_pickle=True))


def jeu(z, j):
    return {k.split("__", 1)[1]: v for k, v in z.items() if k.startswith(j + "__")}


def alertes(rep):
    return np.isin(np.asarray(rep, dtype=object), list(B.ALERTE))


def rep_f1(d, G2):
    return MF.repondre(d["P10"], d["Pso"], d["Pv2"], d["p_loin"], F1, G2=G2)


def rep_c4(d, P12):
    return MF.repondre(d["P10"], d["Pso"], d["Pv2"], d["p_loin"], C4, P12=P12)


def rep_v12a13(d, P13):
    """Chaîne installée où la v12a13 remplace la v10b en « proche » (seuils de la v10b) ; « loin » : v2, politique b."""
    rp = maladies.decider_convnext(P13, {**B.M_V10B})[0]
    return np.where(d["p_loin"] >= 0.5, maladies.decider_convnext(d["Pv2"], B.M_V2)[0], rp)


def mesure_fermes(d, r):
    out = B.mesure(dict(malade=d["malade"].astype(bool), sig=np.zeros(len(r), bool)), r)
    out["par_ferme"] = {}
    for f in sorted(set(d["ferme"])):
        s = d["ferme"] == f
        out["par_ferme"][f] = B.mesure(dict(malade=d["malade"][s].astype(bool), sig=np.zeros(int(s.sum()), bool)), r[s])
    return out


def bornes():
    assert not (J / "juges.npz").exists(), "juges déjà chargés : une seule lecture"
    sha = verifier_sha()
    journal(f"SHA-256 : {sum(sha.values())}/{len(sha)} identiques ; différents : {[f for f, ok in sha.items() if not ok]}")
    assert all(sha.values())
    juges = B.charger_juges()   # SEULE lecture des juges
    liste = pd.read_csv(RACINE / "data/raw/partage_binome_v10b/partage_corentin_2026-11-11/banspot_liste_test.csv")
    assert list(liste.fichier) == list(juges["banspot"]["chemin"])
    photos = {"banspot": [str(RACINE / "data/raw/banspot/DATASET" / Path(f).parent.name / Path(f).name) for f in liste.fichier],
              "cordana_perou": [str(RACINE / c) if (RACINE / c).exists() else B.fichier(c) for c in juges["cordana_perou"]["chemin"]]}
    fermes = {"banspot": liste.ferme.to_numpy(dtype=str), "cordana_perou": np.array(["cordana_perou"] * len(photos["cordana_perou"]))}
    z = {}
    for j in JEUX:
        d = juges[j]
        assert all(Path(p).exists() for p in photos[j]), j
        for k in ("P10", "Pso", "Pv2", "p_loin", "malade"):
            z[f"{j}__{k}"] = d[k]
        z[f"{j}__photo"] = np.array(photos[j], dtype=str)
        z[f"{j}__ferme"] = fermes[j]
    np.savez(J / "juges.npz", **z)
    z = charger()
    temoin, a_lire = {}, {"g2": [], "v12a14": [], "v12a13": []}
    for j in JEUX:
        d = jeu(z, j)
        n = len(d["P10"])
        r = MF.repondre(d["P10"], d["Pso"], d["Pv2"], d["p_loin"], MF.CANDIDATS["installee"])
        temoin[j] = mesure_fermes(d, r)
        temoin[j]["photos_loin"] = int((d["p_loin"] >= 0.5).sum())
        lo = alertes(rep_f1(d, np.tile(SAINE, (n, 4, 1))))
        hi = alertes(rep_f1(d, np.tile(MALADE, (n, 4, 1))))
        assert not (lo & ~hi).any(), "monotonie F1 violée"
        a_lire["g2"] += [(j, int(i)) for i in np.flatnonzero(lo != hi)]
        c_hi = alertes(rep_c4(d, np.tile(SAINE, (n, 1))))
        c_lo = alertes(rep_c4(d, np.tile(MALADE, (n, 1))))
        assert not (c_hi & ~c_lo).any(), "monotonie C_quatre violée"
        a_lire["v12a14"] += [(j, int(i)) for i in np.flatnonzero(~c_hi)]
        a_lire["v12a13"] += [(j, int(i)) for i in np.flatnonzero(d["p_loin"] < 0.5)]
        journal(f"{j} : {n} photos ; F1 à lire {int((lo != hi).sum())} ; C_quatre à lire {int((~c_hi).sum())} ; "
                f"v12a13 à lire {int((d['p_loin'] < 0.5).sum())}")
    (J / "temoin.json").write_text(json.dumps(temoin, ensure_ascii=False, indent=1), encoding="utf-8")
    (J / "a_lire.json").write_text(json.dumps(a_lire), encoding="utf-8")
    (J / "sha.json").write_text(json.dumps(sha, indent=1), encoding="utf-8")
    for j in JEUX:
        t = temoin[j]
        fe = " | ".join(f"{f} : {v['msa']}/{v['nm']} ; {v['sea']}/{v['ns']}" for f, v in t["par_ferme"].items())
        journal(f"témoin {j} : malades sans alerte {t['msa']}/{t['nm']} ; saines en alerte {t['sea']}/{t['ns']} "
                f"(à vérifier {t['sea_averif']}) ; photos loin {t['photos_loin']} ; par ferme {fe}")


def morceaux(chemin):
    """Copie exacte de la fonction interne de m12_banc_finalistes.calculer (préparation du carnet Kaggle des morceaux)."""
    from PIL import Image, ImageOps
    with Image.open(chemin) as im:
        im.draft("RGB", (896, 896))
        im = ImageOps.exif_transpose(im).convert("RGB")
    w, h = im.size
    mw, mh = max(1, round(0.6 * w)), max(1, round(0.6 * h))
    sortie = []
    for iy in range(2):
        for ix in range(2):
            x0, y0 = round(ix * (w - mw)), round(iy * (h - mh))
            t = io.BytesIO()
            im.crop((x0, y0, x0 + mw, y0 + mh)).save(t, format="PNG")
            t.seek(0)
            sortie.append(t)
    return sortie


def fichier_proba(quoi, j, n):
    f = J / f"p_{quoi}_{j}.npy"
    if f.exists():
        return f, np.load(f)
    return f, np.full((n, 4, 4) if quoi == "g2" else (n, 4), np.nan)


def lire(quoi, jusqua, lot, ordre=None):
    import torch
    torch.set_num_threads(4)
    z = charger()
    liste = json.loads((J / "a_lire.json").read_text(encoding="utf-8"))[quoi]
    if ordre:
        liste = sorted(liste, key=lambda e: ordre.index(e[0]))
    m = maladies.charger_convnext(RACINE / DOSSIERS[quoi])
    for r in m["reseaux"]:
        r.to(memory_format=torch.channels_last)   # même calcul (écart mesuré : 0), un peu plus rapide
    tab = {j: fichier_proba(quoi, j, len(z[f"{j}__P10"])) for j in JEUX}
    reste = [(j, i) for j, i in liste if np.isnan(tab[j][1][i]).any()]
    journal(f"{quoi} : {len(liste)} photos à lire, {len(reste)} restantes")
    t0, fait = time.time(), 0
    for k in range(0, len(reste), lot):
        if jusqua and dt.datetime.now().strftime("%H:%M") >= jusqua:
            journal(f"{quoi} : arrêt à l'heure limite {jusqua}")
            break
        part = reste[k:k + lot]
        for j in JEUX:
            idx = [i for jj, i in part if jj == j]
            if not idx:
                continue
            chemins = [str(z[f"{j}__photo"][i]) for i in idx]
            if quoi == "g2":
                tuiles = [t for c in chemins for t in morceaux(c)]
                P = maladies.predire_convnext(tuiles, m).reshape(len(chemins), 4, -1)
            else:
                P = maladies.predire_convnext(chemins, m)
            tab[j][1][idx] = P
            np.save(tab[j][0], tab[j][1])
        fait += len(part)
        journal(f"{quoi} : {fait}/{len(reste)} ({(time.time() - t0) / fait:.2f} s par photo)")
    return fait


def remplis(z, j, nom):
    """(tableau rempli « le moins d'alertes », tableau rempli « le plus d'alertes », masque des photos non lues)."""
    d = jeu(z, j)
    n = len(d["P10"])
    quoi = {"F1_trois_morceaux2x2": "g2", "C_quatre_v12a14": "v12a14", "v12a13": "v12a13"}[nom]
    f = J / f"p_{quoi}_{j}.npy"
    P = np.load(f) if f.exists() else np.full((n, 4, 4) if quoi == "g2" else (n, 4), np.nan)
    inc = np.isnan(P).any((1, 2)) if quoi == "g2" else np.isnan(P).any(1)
    lo, hi = P.copy(), P.copy()
    lo[inc], hi[inc] = SAINE, MALADE
    return d, lo, hi, inc


def repondre_nom(d, nom, P):
    if nom == "F1_trois_morceaux2x2":
        return rep_f1(d, P)
    if nom == "C_quatre_v12a14":
        return rep_c4(d, P)
    return rep_v12a13(d, P)


def etat():
    """Comptes certains et bornes ; renvoie {candidat: dict}."""
    z = charger()
    res = {}
    for nom in ("F1_trois_morceaux2x2", "C_quatre_v12a14", "v12a13"):
        par = {}
        for j in JEUX:
            d, lo, hi, inc = remplis(z, j, nom)
            a_lo, a_hi = alertes(repondre_nom(d, nom, lo)), alertes(repondre_nom(d, nom, hi))
            mal = d["malade"].astype(bool)
            par[j] = dict(inconnues=int((a_lo != a_hi).sum()),
                          msa=(int((mal & ~a_hi).sum()), int((mal & ~a_lo).sum())), nm=int(mal.sum()),
                          sea=(int((~mal & a_lo).sum()), int((~mal & a_hi).sum())), ns=int((~mal).sum()))
        b, c = par["banspot"], par["cordana_perou"]
        # passe certainement si le pire cas passe ; échoue certainement si le meilleur cas échoue
        pire = b["msa"][1] <= 12 and b["sea"][1] <= 61 and (c["nm"] - c["msa"][1]) / c["nm"] >= 0.97
        meilleur = b["msa"][0] <= 12 and b["sea"][0] <= 61 and (c["nm"] - c["msa"][0]) / c["nm"] >= 0.97
        res[nom] = dict(par=par, verdict="PASSE" if pire else ("NE PASSE PAS" if not meilleur else "indéterminé"))
        journal(f"{nom} : BanSpot tachées sans alerte {b['msa'][0]}..{b['msa'][1]}/{b['nm']} (≤ 12), saines en alerte "
                f"{b['sea'][0]}..{b['sea'][1]}/{b['ns']} (≤ 61) ; Cordana sans alerte {c['msa'][0]}..{c['msa'][1]}/{c['nm']} "
                f"(≤ 15) ; inconnues {b['inconnues']} + {c['inconnues']} -> {res[nom]['verdict']}")
    return res


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("etape", choices=["bornes", "lire", "etat"])
    a.add_argument("--quoi", choices=list(DOSSIERS))
    a.add_argument("--jusqua", default="08:30")
    a.add_argument("--lot", type=int, default=8)
    a.add_argument("--ordre", help="ordre des jeux, ex. cordana_perou,banspot")
    x = a.parse_args()
    if x.etape == "bornes":
        bornes()
    elif x.etape == "lire":
        lire(x.quoi, x.jusqua, x.lot, x.ordre.split(",") if x.ordre else None)
    else:
        etat()
