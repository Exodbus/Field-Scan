#!/usr/bin/env python3
"""Juge maladies, journée du 15/11 : une lecture des juges relus (BanSpot, Cordana du Pérou) pour le seul finaliste
gelé, MC1-OU-proche (out/controle_jour_1511/liste_gelee.md). Règle : plan du 13/11, section 4.3, telle qu'écrite.

Définition (out/maladies/nuit_1311/piste2/finalistes_piste2.md, section 3 ; scripts/m14_banc.mc1_ou_proche) :
  r_F1  = F1 installé (maladies.decider_melange, via m13_banc_finalistes.f1) ;
  r_d3b = maladies.decider_convnext(P_d3b, {**M_V10B, "seuil": 0.50}), P_d3b = moyenne des 2 réseaux de
          modeles/maladies_nuit_1311/d3b (graine 0), 384 px, 4 vues ;
  réponse = r_d3b si photo « proche » (p_loin < 0,5), r_F1 sans alerte et r_d3b en alerte ; sinon r_F1.

Sources : probabilités de F1 et de l'aiguilleur en cache (out/controle_nuit_1112/juge_m, celles qu'a relues le juge
du 14/11, recoupées avec out/controle_nuit_1311/juge_m/reponses_<jeu>.csv) ; probabilités de d3b déjà lues le 14/11
(out/controle_nuit_1311/juge_m/p_d3b_<jeu>.npy), complétées ici seulement sur les photos dont la décision dépend de d3b
(proches où F1 n'alerte pas).

Étapes :
  sha      : empreintes (poids d3b, finalistes_piste2.md) contre les listes gelées du 14/11 et du 15/11.
  temoin   : F1 recalculé à partir des caches ; arrêt s'il ne redonne pas 4 / 646, 56 / 646, 502 / 505.
  lire     : lecture de d3b (6 fils, lots de 8, sauvegarde après chaque lot) sur les photos à lire ; contrôle sur
             4 photos déjà lues le 14/11 (mêmes probabilités attendues).
  bilan    : décisions, comptes, verdict de la règle 4.3, malades gagnées / perdues contre F1.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_1511_m_juge.py sha
"""
import argparse
import datetime as dt
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import juge_1311_m_juges as JG  # noqa: E402   (caches(), JEUX ; aucune écriture à l'import hors mkdir existant)
import m12_banc_commun as B  # noqa: E402
import m13_banc_finalistes as MB  # noqa: E402
from fieldscan.modules import maladies  # noqa: E402

SORTIE = RACINE / "out/controle_jour_1511/juge_m"
SORTIE.mkdir(parents=True, exist_ok=True)
HIER = RACINE / "out/controle_nuit_1311/juge_m"
D3B = RACINE / "modeles/maladies_nuit_1311/d3b"
JEUX = JG.JEUX
AL = list(B.ALERTE)
M_D3B = {**B.M_V10B, "seuil": 0.50}
LIMITES = dict(msa=6, sea=56, cordana=0.97)
F1_ATTENDU = dict(banspot=(4, 56), cordana_perou=(3, 0))


def journal(t):
    print(f"[{dt.datetime.now():%H:%M:%S}] {t}", flush=True)


def _sha(p):
    return hashlib.sha256((RACINE / p).read_bytes()).hexdigest()


def sha():
    att = {}
    for f, sep in ((RACINE / "out/controle_nuit_1311/empreintes_liste_gelee.txt", None),
                   (RACINE / "out/controle_jour_1511/liste_gelee.md", None)):
        for l in f.read_text(encoding="utf-8").splitlines():
            l = l.strip()
            if len(l) > 66 and all(c in "0123456789abcdef" for c in l[:64]):
                h, p = l.split(None, 1)
                att[p.lstrip("*").strip()] = h
    vis = [str(p.relative_to(RACINE)).replace("\\", "/") for p in sorted(D3B.iterdir())]
    vis += ["out/maladies/nuit_1311/piste2/finalistes_piste2.md", "modeles/maladies_aiguilleur/aiguilleur.npz",
            "modeles/maladies_binome/v10b/seuils.json", "fieldscan/modules/maladies.py", "scripts/m14_banc.py",
            "scripts/m13_banc_finalistes.py", "scripts/m12_banc_commun.py", "docs/plan_nuit_2026-11-13.md"]
    res = {}
    for p in vis:
        h = _sha(p)
        res[p] = dict(sha256=h, attendu=att.get(p), identique=(att.get(p) == h) if p in att else None)
        journal(f"{p} : {'identique' if res[p]['identique'] else ('sans référence' if res[p]['identique'] is None else 'DIFFÉRENT')}")
    (SORTIE / "sha.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return all(v["identique"] is not False for v in res.values())


def donnees():
    """Caches de F1 et de l'aiguilleur, recoupés avec les fichiers du juge du 14/11 ; F1 recalculé."""
    C = JG.caches()
    for j in JEUX:
        d = C[j]
        r0 = MB.f1(d["P10"], d["Pso"], d["Pv2"], d["p_loin"], MB._remplir(d["G2"], MB.G_SAINE))
        r1 = MB.f1(d["P10"], d["Pso"], d["Pv2"], d["p_loin"], MB._remplir(d["G2"], MB.G_MALADE))
        assert (np.isin(r0, AL) == np.isin(r1, AL)).all(), "alerte de F1 dépendant de morceaux non lus"
        d["rF1"] = r0
        d["loin"] = d["p_loin"] >= 0.5
        h = pd.read_csv(HIER / f"reponses_{j}.csv")
        assert list(h.photo) == [str(x) for x in d["photo"]]
        assert np.allclose(h.p_loin.values, d["p_loin"]) and (h.malade.values == d["malade"].astype(int)).all()
        assert (h.rep_F1.values.astype(object) == r0).all()
        P = np.load(HIER / f"p_d3b_{j}.npy").astype("float64")
        assert np.allclose(np.nan_to_num(P, nan=-1), np.nan_to_num(h[[f"d3b_{c}" for c in range(4)]].to_numpy("float64"), nan=-1))
        d["P_hier"] = P
        d["a_lire"] = ~d["loin"] & ~np.isin(r0, AL)   # photos dont la décision dépend de d3b
    return C


def temoin():
    C = donnees()
    res = {}
    for j in JEUX:
        d = C[j]
        al = np.isin(d["rF1"], AL)
        msa, sea = int((d["malade"] & ~al).sum()), int((~d["malade"] & al).sum())
        manque = d["a_lire"] & np.isnan(d["P_hier"]).any(1)
        res[j] = dict(photos=len(al), msa=msa, sea=sea, nm=int(d["malade"].sum()), ns=int((~d["malade"]).sum()),
                      proches=int((~d["loin"]).sum()), a_lire=int(d["a_lire"].sum()),
                      a_lire_tachees=int((d["a_lire"] & d["malade"]).sum()), a_lire_saines=int((d["a_lire"] & ~d["malade"]).sum()),
                      deja_lues_14_11=int((d["a_lire"] & ~np.isnan(d["P_hier"]).any(1)).sum()), a_lire_aujourdhui=int(manque.sum()))
        journal(f"{j} : F1 {msa}/{res[j]['nm']} tachées sans alerte ; {sea}/{res[j]['ns']} saines en alerte ; "
                f"proches {res[j]['proches']} ; décision dépendant de d3b {res[j]['a_lire']} "
                f"(déjà lues {res[j]['deja_lues_14_11']}, à lire {res[j]['a_lire_aujourdhui']})")
        assert (msa, sea) == F1_ATTENDU[j], "le témoin F1 ne redonne pas les chiffres attendus"
    (SORTIE / "temoin.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


def lire(lot=8):
    import torch
    torch.set_num_threads(6)
    C = donnees()
    m = maladies.charger_convnext(D3B)
    journal(f"d3b : {len(m['reseaux'])} réseaux, vues {m['vues']}, taille {m['taille']} ; 6 fils")
    # contrôle : 4 photos déjà lues le 14/11 (BanSpot) relues ici, probabilités identiques attendues
    ctl = SORTIE / "controle_relecture.json"
    if not ctl.exists():
        d = C["banspot"]
        idx = np.flatnonzero(~np.isnan(d["P_hier"]).any(1))[:4]
        t0 = time.time()
        Q = maladies.predire_convnext([str(d["photo"][i]) for i in idx], m)
        ecart = float(np.abs(Q - d["P_hier"][idx]).max())
        ctl.write_text(json.dumps(dict(indices=idx.tolist(), ecart_max=ecart, s_par_photo=(time.time() - t0) / len(idx)),
                                  indent=1), encoding="utf-8")
        journal(f"contrôle de relecture : écart max {ecart:.2e} sur 4 photos ({(time.time() - t0) / 4:.2f} s par photo)")
        assert ecart < 1e-4
    for j in ["cordana_perou", "banspot"]:
        d = C[j]
        f = SORTIE / f"p_d3b_{j}.npy"
        P = np.load(f) if f.exists() else d["P_hier"].copy()
        reste = np.flatnonzero(d["a_lire"] & np.isnan(P).any(1))
        journal(f"{j} : {len(reste)} photos à lire")
        t0, fait = time.time(), 0
        for k in range(0, len(reste), lot):
            idx = reste[k:k + lot]
            P[idx] = maladies.predire_convnext([str(d["photo"][i]) for i in idx], m)
            np.save(f, P)
            fait += len(idx)
            if (k // lot) % 5 == 0 or fait == len(reste):
                journal(f"{j} : {fait}/{len(reste)} ({(time.time() - t0) / fait:.2f} s par photo)")
        np.save(f, P)
        journal(f"{j} : terminé")


def compte(mal, rep):
    al = np.isin(rep, AL)
    return dict(msa=int((mal & ~al).sum()), nm=int(mal.sum()), sea=int((~mal & al).sum()), ns=int((~mal).sum()),
                sea_averif=int((~mal & (rep == "a_verifier")).sum()), inconnues=int((rep == "inconnue").sum()),
                noms_tachees=dict(Counter(rep[mal].tolist())), noms_saines=dict(Counter(rep[~mal].tolist())))


def bilan():
    C = donnees()
    out, reps = {}, {}
    for j in JEUX:
        d = C[j]
        P = np.load(SORTIE / f"p_d3b_{j}.npy").astype("float64")
        manque = d["a_lire"] & np.isnan(P).any(1)
        rd = np.full(len(P), "non_lue", dtype=object)
        ok = ~np.isnan(P).any(1)
        rd[ok] = maladies.decider_convnext(P[ok], M_D3B)[0]
        prend = d["a_lire"] & ok & np.isin(rd, AL)
        rep = np.where(prend, rd, d["rF1"]).astype(object)
        rep[manque] = "inconnue"
        reps[j] = rep
        # contrôle : même réponse que scripts/m14_banc.mc1_ou_proche importé tel quel (photos non lues sans effet :
        # elles sont « loin » ou déjà en alerte avec F1 ; remplies « saine 100 % »)
        import m14_banc as M14
        import m13_banc_commun as C13
        dd = C13._d(np.array(d["photo"], dtype=object), d["malade"], d["malade"], d["P10"], d["Pso"], d["Pv2"],
                    d["p_loin"], d["G2"])
        dd["D"] = np.where(np.isnan(P), [1.0, 0, 0, 0], P)
        G = MB._remplir(d["G2"], MB.G_SAINE)
        r14 = M14.mc1_ou_proche(dd, G)
        egal = (r14 == rep) | (rep == "inconnue")
        journal(f"{j} : contrôle contre m14_banc.mc1_ou_proche : {int(egal.sum())}/{len(rep)} réponses identiques")
        assert egal.all()
        mal = d["malade"]
        aF, aM = np.isin(d["rF1"], AL), np.isin(rep, AL)
        r = dict(F1=compte(mal, d["rF1"]), MC1=compte(mal, rep), photos_lues_d3b_utiles=int((d["a_lire"] & ok).sum()),
                 non_lues=int(manque.sum()), alertes_ajoutees=int(prend.sum()),
                 tachees_gagnees=int((mal & ~aF & aM).sum()), tachees_perdues=int((mal & aF & ~aM).sum()),
                 saines_ajoutees=int((~mal & ~aF & aM).sum()),
                 libelles_ajoutes=dict(Counter(rep[prend].tolist())))
        r["par_ferme"] = {f: dict(F1=compte(mal[d["ferme"] == f], d["rF1"][d["ferme"] == f]),
                                  MC1=compte(mal[d["ferme"] == f], rep[d["ferme"] == f])) for f in sorted(set(d["ferme"]))}
        out[j] = r
        df = pd.DataFrame(dict(photo=d["photo"], ferme=d["ferme"], malade=mal.astype(int), p_loin=d["p_loin"],
                               decision_depend_d3b=d["a_lire"].astype(int)))
        for c in range(4):
            df[f"d3b_{c}"] = P[:, c]
        df["rep_F1"], df["rep_d3b_proche"], df["rep_MC1"] = d["rF1"], rd, rep
        df["alerte_F1"], df["alerte_MC1"] = aF.astype(int), aM.astype(int)
        df.to_csv(SORTIE / f"reponses_{j}.csv", index=False)
    b, c = out["banspot"]["MC1"], out["cordana_perou"]["MC1"]
    taux = (c["nm"] - c["msa"]) / c["nm"]
    conds = dict(banspot_tachees=b["msa"] <= LIMITES["msa"], banspot_saines=b["sea"] <= LIMITES["sea"],
                 cordana=taux >= LIMITES["cordana"])
    out["cordana_en_alerte"] = c["nm"] - c["msa"]
    out["cordana_taux"] = taux
    out["conditions"] = conds
    out["inconnues"] = b["inconnues"] + c["inconnues"]
    out["verdict"] = "PASSE" if all(conds.values()) and out["inconnues"] == 0 else "NE PASSE PAS"
    (SORTIE / "bilan.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for j in JEUX:
        r = out[j]
        journal(f"{j} : F1 {r['F1']['msa']}/{r['F1']['nm']} ; {r['F1']['sea']}/{r['F1']['ns']} | MC1-OU-proche "
                f"{r['MC1']['msa']}/{r['MC1']['nm']} ; {r['MC1']['sea']}/{r['MC1']['ns']} (à vérifier {r['MC1']['sea_averif']}) ; "
                f"gagnées {r['tachees_gagnees']}, perdues {r['tachees_perdues']}, saines ajoutées {r['saines_ajoutees']} ; "
                f"inconnues {r['MC1']['inconnues']} ; libellés ajoutés {r['libelles_ajoutes']}")
    journal(f"Cordana en alerte {out['cordana_en_alerte']}/505 ({100 * taux:.1f} %) ; conditions {conds} -> {out['verdict']}")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("etape", choices=["sha", "temoin", "lire", "bilan"])
    x = a.parse_args()
    if x.etape == "sha":
        sys.exit(0 if sha() else 1)
    {"temoin": temoin, "lire": lire, "bilan": bilan}[x.etape]()
