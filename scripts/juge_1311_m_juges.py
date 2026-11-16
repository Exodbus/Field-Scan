#!/usr/bin/env python3
"""Juge maladies, nuit du 13/11 (lecture le 14/11 au soir) : une lecture des juges relus (BanSpot, Cordana du Pérou)
pour la liste gelée (place 1 d3b, place 2 F1_bornes), règle du plan du 13/11, section 4.3, sans modification.

Alerte = maladie nommée, « malade, non identifiée » ou « à vérifier » (m12_banc_commun.ALERTE).
Adoption proposée si BanSpot tachées sans alerte <= 6 / 646 et saines en alerte <= 56 / 646 et Cordana du Pérou en
alerte >= 97 % ; entre finalistes qui passent : coût de réglage le plus bas.

Étapes :
  sha        : SHA-256 des fichiers de out/controle_nuit_1311/empreintes_liste_gelee.txt (sha.json) ; arrêt si un
               fichier maladies diffère.
  reglage    : contrôle sans juge : le chemin de décision de d3b utilisé ici (m13_entr_seuils2.reponse2 importé tel quel)
               redonne les chiffres de lot2p/bilan_d3b_ensemble_livrable.json.
  f1         : témoin F1 et F1_bornes à partir des caches du 13/11 (out/controle_nuit_1112/juge_m), sans lecture de modèle
               (sauf morceaux manquants pour F1_bornes, lus avec la v10b).
  lire       : lecture de d3b (2 réseaux, 4 vues) sur les photos des deux juges, 4 fils, sauvegarde après chaque lot.
  temps      : temps par photo de la chaîne d3b (aiguilleur + d3b + v2) sur 12 photos de réglage (validation Tanzanie).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_1311_m_juges.py sha
"""
import argparse
import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))

J = RACINE / "out/controle_nuit_1311/juge_m"
J.mkdir(parents=True, exist_ok=True)
CACHE = RACINE / "out/controle_nuit_1112/juge_m"
D3B = RACINE / "modeles/maladies_nuit_1311/d3b"
JEUX = ["banspot", "cordana_perou"]
COUPLE = (0.50, 0.70)


def journal(t):
    print(f"[{dt.datetime.now():%H:%M:%S}] {t}", flush=True)


def est_maladies(f):
    return ("maladies" in f or f.startswith("docs/") or f.startswith("scripts/m1") or f.startswith("scripts/controle_1311_m")
            or f.startswith("notebooks/m13") or f.startswith("scripts/controle_1311_empreintes")
            or f.startswith("scripts/controle_1311_interdits"))


def sha():
    attendu = {}
    for l in (RACINE / "out/controle_nuit_1311/empreintes_liste_gelee.txt").read_text(encoding="utf-8").splitlines():
        if l.strip() and not l.startswith("#"):
            h, f = l.split(None, 1)
            attendu[f.strip()] = h
    res = {}
    for f, h in attendu.items():
        p = RACINE / f
        res[f] = dict(maladies=est_maladies(f), identique=p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == h)
    (J / "sha.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    m = {f: v for f, v in res.items() if v["maladies"]}
    a = {f: v for f, v in res.items() if not v["maladies"]}
    journal(f"maladies : {sum(v['identique'] for v in m.values())}/{len(m)} identiques ; "
            f"différents : {[f for f, v in m.items() if not v['identique']]}")
    journal(f"autres (comptage) : {sum(v['identique'] for v in a.values())}/{len(a)} identiques ; "
            f"différents : {[f for f, v in a.items() if not v['identique']]}")
    return all(v["identique"] for v in m.values())


def _decision_d3b():
    """Importe le code de M-entraîneur tel quel ; renvoie (M, S2)."""
    import m13_entr_mesurer as M
    import m13_entr_seuils2 as S2
    return M, S2


def reglage():
    M, S2 = _decision_d3b()
    ref = M.reference_f1()
    P = M.charger(M.KAG / "lot2p", "d3b")
    E = {j: (Ps if j in ("tdtu", "ethiopie") else [np.mean(Ps, 0)]) for j, Ps in P.items()}
    r = M.bilan(E, ref, COUPLE)   # M.reponse_eleve = reponse2 (installé par m13_entr_seuils2)
    attendu = json.loads((M.KAG / "lot2p/bilan_d3b_ensemble_livrable.json").read_text(encoding="utf-8"))
    ok = True
    for j in M.TOUS:
        a, b = (r[j]["msa"], r[j]["sea"]), (attendu[j]["msa"], attendu[j]["sea"])
        ok &= a == b
        journal(f"réglage {j} : {a} (attendu {b})")
    journal(f"coût de réglage {r['cout_reglage']:.4f} (attendu {attendu['cout_reglage']:.4f}) ; F1 {ref['cout_reglage']:.4f} ; identique : {ok}")
    (J / "controle_reglage.json").write_text(json.dumps(dict(identique=bool(ok), cout=r["cout_reglage"], cout_f1=ref["cout_reglage"]),
                                                        indent=1), encoding="utf-8")
    assert ok


def caches():
    z = dict(np.load(CACHE / "juges.npz", allow_pickle=True))
    out = {}
    for j in JEUX:
        d = {k.split("__", 1)[1]: v for k, v in z.items() if k.startswith(j + "__")}
        d["G2"] = np.load(CACHE / f"p_g2_{j}.npy").astype("float64")
        for k in ("P10", "Pso", "Pv2", "p_loin"):
            d[k] = d[k].astype("float64")
        d["malade"] = d["malade"].astype(bool)
        out[j] = d
    return out


def f1_et_bornes():
    import m13_banc_finalistes as MB
    from fieldscan.modules import maladies
    C = caches()
    res = {}
    for j in JEUX:
        d = C[j]
        n = len(d["p_loin"])
        lu = ~np.isnan(d["G2"][:, :, 0]).any(1)
        r0 = MB.f1(d["P10"], d["Pso"], d["Pv2"], d["p_loin"], MB._remplir(d["G2"], MB.G_SAINE))
        r1 = MB.f1(d["P10"], d["Pso"], d["Pv2"], d["p_loin"], MB._remplir(d["G2"], MB.G_MALADE))
        a0, a1 = np.isin(r0, MB.AL), np.isin(r1, MB.AL)
        rb = MB.f1_bornes(d["P10"], d["Pso"], d["Pv2"], d["p_loin"], d["G2"])
        inc = np.flatnonzero(rb == "inconnue_lire_morceaux")
        journal(f"{j} : {n} photos ; morceaux en cache {int(lu.sum())} ; F1 alertes différentes entre remplissages "
                f"{int((a0 != a1).sum())} ; F1_bornes inconnues {len(inc)}")
        if len(inc):   # morceaux nécessaires et absents du cache : lus avec la v10b
            import torch
            torch.set_num_threads(4)
            m = maladies.charger_convnext(RACINE / "modeles/maladies_binome/v10b")
            for i in inc:
                d["G2"][i] = maladies.predire_convnext(maladies.morceaux_2x2(str(d["photo"][i])), m).reshape(4, -1)
            np.save(J / f"p_g2_complement_{j}.npy", d["G2"])
            rb = MB.f1_bornes(d["P10"], d["Pso"], d["Pv2"], d["p_loin"], d["G2"])
            journal(f"{j} : {len(inc)} photos lues en 2 x 2 ; inconnues restantes {int((rb == 'inconnue_lire_morceaux').sum())}")
        _, dep = MB.masques_f1_bornes(d["P10"], d["Pso"], d["Pv2"], d["p_loin"])
        res[j] = dict(f1=np.where(a0 == a1, r0, "inconnue").astype(object), f1_haut=r1.astype(object),
                      f1_bornes=rb.astype(object), dep=dep)
    return C, res


def lire(lot=8):
    import torch
    torch.set_num_threads(4)
    from fieldscan.modules import maladies
    C = caches()
    m = maladies.charger_convnext(D3B)
    journal(f"d3b : {len(m['reseaux'])} réseaux, vues {m['vues']}, taille {m['taille']}, lecture {m['lecture']}")
    # Ordre de lecture (19 h 07, avant tout compte de d3b) : BanSpot tachées, puis Cordana, puis BanSpot saines.
    # L'ordre ne change aucune décision ; il rend complète le plus tôt possible la condition la plus serrée.
    F = {j: J / f"p_d3b_{j}.npy" for j in JEUX}
    P = {j: (np.load(F[j]) if F[j].exists() else np.full((len(C[j]["p_loin"]), 4), np.nan)) for j in JEUX}
    blocs = [("banspot", C["banspot"]["malade"]), ("cordana_perou", np.ones(len(C["cordana_perou"]["p_loin"]), bool)),
             ("banspot", ~C["banspot"]["malade"])]
    for j, masque in blocs:
        reste = np.flatnonzero(np.isnan(P[j]).any(1) & masque)
        journal(f"{j} ({'tachées' if j == 'banspot' and masque.all() == False and masque[C[j]['malade']].all() else 'bloc'}) : "
                f"{int(masque.sum())} photos, {len(reste)} restantes")
        t0, fait = time.time(), 0
        for k in range(0, len(reste), lot):
            idx = reste[k:k + lot]
            P[j][idx] = maladies.predire_convnext([str(C[j]["photo"][i]) for i in idx], m)
            np.save(F[j], P[j])
            fait += len(idx)
            if (k // lot) % 10 == 0 or fait == len(reste):
                journal(f"{j} : {fait}/{len(reste)} ({(time.time() - t0) / fait:.2f} s par photo)")
        journal(f"{j} : bloc terminé")


def temps(npho=12):
    """Chaîne d3b complète sur 12 photos de validation Tanzanie (réglage), 4 fils, machine partagée."""
    import torch
    torch.set_num_threads(4)
    from fieldscan.modules import maladies
    import m12_banc_commun as B
    ch = [str(c) for c in list(B.charger_reglage()["validation"]["chemin"])[:npho]]
    ch = [c if Path(c).exists() else B.fichier(c) for c in ch]
    t = {}
    a = maladies.charger_aiguilleur(RACINE / "modeles/maladies_aiguilleur/aiguilleur.npz")
    md = maladies.charger_convnext(D3B)
    mv2 = maladies.charger_convnext(RACINE / "modeles/maladies_binome/maladies_v2/poids")
    maladies.predire_convnext(ch[:1], md)   # échauffement
    t0 = time.time(); maladies.p_loin(ch, a); t["aiguilleur"] = (time.time() - t0) / npho
    t0 = time.time(); maladies.predire_convnext(ch, md); t["d3b_2reseaux_4vues"] = (time.time() - t0) / npho
    t0 = time.time(); maladies.predire_convnext(ch, mv2); t["v2"] = (time.time() - t0) / npho
    t.update(photos=npho, fils=4, machine="partagée (autres agents actifs, 2 fils chacun)", heure=f"{dt.datetime.now():%H:%M}")
    (J / "temps.json").write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
    journal(f"temps par photo : {t}")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("etape", choices=["sha", "reglage", "f1", "lire", "temps"])
    x = a.parse_args()
    if x.etape == "sha":
        sys.exit(0 if sha() else 1)
    elif x.etape == "f1":
        f1_et_bornes()
    elif x.etape == "reglage":
        reglage()
    elif x.etape == "lire":
        lire()
    else:
        temps()
