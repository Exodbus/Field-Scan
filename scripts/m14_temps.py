#!/usr/bin/env python3
"""M-piste2 : temps par photo de MC1-OU-proche (F1_bornes + élève d3b sur les photos « proches »), même machine, mêmes
photos que M-banc (12 photos, graine 1314, scripts/m13_banc_temps_bout.py), 3 fils, modèles chargés avant.
  1. F1 installé (maladies._executer_melange, code en service) ;
  2. F1_bornes (copie de M-banc, modèles en mémoire) ;
  3. d3b (2 réseaux, 384 px, 4 vues) sur les photos « proches » de l'échantillon, et sur toutes pour information.
Temps de MC1-OU-proche = 2 + 3 (les morceaux lus restent ceux de F1_bornes, ce qui majore le temps).
Contrôle : réponses de MC1-OU-proche sur l'échantillon comparées à celles du banc (scripts/m14_banc.py).

    PYTHONIOENCODING=utf-8 OMP_NUM_THREADS=3 .venv/Scripts/python.exe -I -u scripts/m14_temps.py
"""
import json
import sys
import time
import types
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import torch  # noqa: E402

torch.set_num_threads(3)
from fieldscan.modules import maladies  # noqa: E402
import m13_banc_commun as C  # noqa: E402
import m13_banc_temps_bout as TB  # noqa: E402
import m14_banc as MB  # noqa: E402

AL = list(C.ALERTE)


def main():
    jeux = MB.charger()
    MB.jeux_global = jeux
    MB.lire_eleve(jeux, MB.KAG / "pour_banc/d3b", "d3b")
    tous = [(j, i) for j in C.JEUX5 for i in range(len(jeux[j]["chemin"]))]
    rng = np.random.default_rng(1314)
    ech = [tous[k] for k in rng.choice(len(tous), 12, replace=False)]
    chemins = [str(RACINE / jeux[j]["chemin"][i]) if j == "agrovision" else C.B.fichier(jeux[j]["chemin"][i]) for j, i in ech]
    banc = {j: C.bornes(jeux[j], MB.mc1_ou_proche)[0] for j in C.JEUX5}
    a_banc = np.array([banc[j][i] for j, i in ech])
    mod = {"aig": maladies.charger_aiguilleur(RACINE / "modeles/maladies_aiguilleur/aiguilleur.npz"),
           "v10b": maladies.charger_convnext(RACINE / "modeles/maladies_binome/v10b"),
           "soupe": maladies.charger_convnext(RACINE / "modeles/maladies_soupe_v2_v8/poids"),
           "v2": maladies.charger_convnext(RACINE / "modeles/maladies_binome/maladies_v2/poids"),
           "d3b": maladies.charger_convnext(RACINE / "modeles/maladies_nuit_1311/d3b")}
    orig_c, orig_a = maladies.charger_convnext, maladies.charger_aiguilleur
    par_dossier = {str(RACINE / "modeles/maladies_soupe_v2_v8/poids"): mod["soupe"],
                   str(RACINE / "modeles/maladies_binome/maladies_v2/poids"): mod["v2"]}
    maladies.charger_convnext = lambda d: par_dossier[str(RACINE / d) if not Path(d).is_absolute() else str(d)]
    maladies.charger_aiguilleur = lambda p: mod["aig"]
    reg = {"melange_proche": ["modeles/maladies_soupe_v2_v8/poids", "modeles/maladies_binome/maladies_v2/poids"],
           "seuil_confiance_melange": 0.70, "loin_ou_proche": True, "morceaux_2x2": True,
           "aiguilleur": "modeles/maladies_aiguilleur/aiguilleur.npz", "jnsp_alerte": True, "jnsp_alerte_loin": True}
    ctx = types.SimpleNamespace(journal=TB.Journal())
    res = {}
    t = time.perf_counter()
    r_inst = maladies._executer_melange(ctx, reg, mod["v10b"], chemins, {})[0]
    res["F1_installe_s"] = (time.perf_counter() - t) / len(chemins)
    maladies.charger_convnext, maladies.charger_aiguilleur = orig_c, orig_a
    t = time.perf_counter()
    r_b, dep, lv = TB.chaine_bornes(chemins, mod)
    res["F1_bornes_s"] = (time.perf_counter() - t) / len(chemins)
    pl = maladies.p_loin(chemins, mod["aig"])   # déjà calculé dans F1_bornes : non compté
    proche = np.flatnonzero(pl < 0.5)
    t = time.perf_counter()
    D = np.full((len(chemins), 4), np.nan)
    if len(proche):
        D[proche] = maladies.predire_convnext([chemins[i] for i in proche], mod["d3b"])
    res["d3b_proches_s"] = (time.perf_counter() - t) / len(chemins)
    t = time.perf_counter()
    maladies.predire_convnext(chemins, mod["d3b"])
    res["d3b_toutes_s"] = (time.perf_counter() - t) / len(chemins)
    res["MC1_OU_proche_s"] = res["F1_bornes_s"] + res["d3b_proches_s"]
    res["rapport_MC1_OU_proche_sur_F1_installe"] = res["MC1_OU_proche_s"] / res["F1_installe_s"]
    res["rapport_MC1_OU_proche_sur_F1_bornes"] = res["MC1_OU_proche_s"] / res["F1_bornes_s"]
    # réponses de MC1-OU-proche sur l'échantillon (contrôle contre le banc)
    rd = maladies.decider_convnext(np.nan_to_num(D, nan=0.25), MB.M_P(0.50))[0]
    rep = np.array(r_b, dtype=object)
    ajout = (pl < 0.5) & ~np.isin(rep, AL) & np.isin(rd, AL)
    rep[ajout] = rd[ajout]
    res.update(photos_proches=int(len(proche)), photos_dep=dep, photos_loin_v2=lv, echantillon=[(j, int(i)) for j, i in ech],
               alertes_candidat_vs_banc=int((np.isin(rep, AL) != a_banc).sum()),
               alertes_bornes_vs_installe=int((np.isin(r_b, AL) != np.isin(r_inst, AL)).sum()))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    (MB.SORTIE / "temps.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
