#!/usr/bin/env python3
"""MB2 : temps de bout en bout, même machine, mêmes photos, 3 fils, modèles chargés avant (non comptés) :
  1. F1 installé : maladies._executer_melange (code en service, réglages de config.yaml) ;
  2. F1_bornes : scripts/m13_banc_finalistes.executer_f1_bornes ;
  3. F1_bornes_1vue : idem, morceaux lus en 1 vue.
Plus, sur les mêmes photos, les morceaux seuls en 4 vues et en 1 vue (photo par photo).
Échantillon fixé avant la mesure : 12 photos tirées au hasard (graine 1314) parmi les 7 746 photos des 5 jeux de réglage.
Contrôle : les alertes des trois chaînes sont comparées entre elles et au cache (F1 sur le réglage).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_banc_temps_bout.py
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
import m13_banc_finalistes as F  # noqa: E402

AL = list(C.ALERTE)


class Journal:
    def info(self, x):
        print("   ", x, flush=True)


def chaine_bornes(chemins, mod, une_vue=False):
    """Copie de F.executer_f1_bornes avec modèles déjà chargés (pour ne pas compter le chargement)."""
    n = len(chemins)
    pl = maladies.p_loin(chemins, mod["aig"])
    Pv2 = maladies.predire_convnext(chemins, mod["v2"]).astype("float64")
    lv = (pl >= 0.5) & np.isin(maladies.decider_convnext(Pv2, F.M_LOIN)[0], AL)
    P10, Pso = np.full((n, 4), np.nan), np.full((n, 3), np.nan)
    a = [chemins[i] for i in np.flatnonzero(~lv)]
    if a:
        P10[~lv] = maladies.predire_convnext(a, mod["v10b"])
        Pso[~lv] = maladies.predire_convnext(a, mod["soupe"])
    _, dep = F.masques_f1_bornes(P10, Pso, Pv2, pl)
    G2 = np.full((n, 4, 4), np.nan)
    mg = {**mod["v10b"], "vues": ["identite"]} if une_vue else mod["v10b"]
    idx = np.flatnonzero(dep)
    for k in range(0, len(idx), 8):
        lot = idx[k:k + 8]
        G2[lot] = maladies.predire_convnext([t for i in lot for t in maladies.morceaux_2x2(chemins[i])], mg).reshape(len(lot), 4, -1)
    return F.f1_bornes(P10, Pso, Pv2, pl, G2), int(dep.sum()), int(lv.sum())


def main():
    jeux = C.charger(roamer=False)
    tous = [(j, i) for j in C.JEUX5 for i in range(len(jeux[j]["chemin"]))]
    rng = np.random.default_rng(1314)
    ech = [tous[k] for k in rng.choice(len(tous), 12, replace=False)]
    chemins = [str(RACINE / jeux[j]["chemin"][i]) if j == "agrovision" else C.B.fichier(jeux[j]["chemin"][i]) for j, i in ech]
    a_cache = np.array([C.bornes(jeux[j], C.f1)[0][i] for j, i in ech])
    mod = {"aig": maladies.charger_aiguilleur(RACINE / "modeles/maladies_aiguilleur/aiguilleur.npz"),
           "v10b": maladies.charger_convnext(RACINE / "modeles/maladies_binome/v10b"),
           "soupe": maladies.charger_convnext(RACINE / "modeles/maladies_soupe_v2_v8/poids"),
           "v2": maladies.charger_convnext(RACINE / "modeles/maladies_binome/maladies_v2/poids")}
    # chaîne installée, avec les modèles déjà chargés : on remplace les chargements par les objets en mémoire
    orig_c, orig_a = maladies.charger_convnext, maladies.charger_aiguilleur
    par_dossier = {str(RACINE / "modeles/maladies_soupe_v2_v8/poids"): mod["soupe"],
                   str(RACINE / "modeles/maladies_binome/maladies_v2/poids"): mod["v2"]}
    maladies.charger_convnext = lambda d: par_dossier[str(RACINE / d) if not Path(d).is_absolute() else str(d)]
    maladies.charger_aiguilleur = lambda p: mod["aig"]
    reg = {"melange_proche": ["modeles/maladies_soupe_v2_v8/poids", "modeles/maladies_binome/maladies_v2/poids"],
           "seuil_confiance_melange": 0.70, "loin_ou_proche": True, "morceaux_2x2": True,
           "aiguilleur": "modeles/maladies_aiguilleur/aiguilleur.npz", "jnsp_alerte": True, "jnsp_alerte_loin": True}
    ctx = types.SimpleNamespace(journal=Journal())
    res = {}
    t = time.perf_counter()
    r_inst = maladies._executer_melange(ctx, reg, mod["v10b"], chemins, {})[0]
    res["F1_installe_s"] = (time.perf_counter() - t) / len(chemins)
    maladies.charger_convnext, maladies.charger_aiguilleur = orig_c, orig_a
    t = time.perf_counter()
    r_b, dep, lv = chaine_bornes(chemins, mod)
    res["F1_bornes_s"] = (time.perf_counter() - t) / len(chemins)
    t = time.perf_counter()
    r_b1, _, _ = chaine_bornes(chemins, mod, une_vue=True)
    res["F1_bornes_1vue_s"] = (time.perf_counter() - t) / len(chemins)
    t4, t1 = [], []
    for c in chemins:
        t = time.perf_counter(); maladies.predire_convnext(maladies.morceaux_2x2(c), mod["v10b"]); t4.append(time.perf_counter() - t)
        t = time.perf_counter(); maladies.predire_convnext(maladies.morceaux_2x2(c), {**mod["v10b"], "vues": ["identite"]}); t1.append(time.perf_counter() - t)
    res.update(morceaux_4vues_s=float(np.mean(t4)), morceaux_1vue_s=float(np.mean(t1)), photos_dep=dep, photos_loin_v2=lv,
               echantillon=[(j, int(i)) for j, i in ech],
               alertes_installe_vs_cache=int((np.isin(r_inst, AL) != a_cache).sum()),
               alertes_bornes_vs_installe=int((np.isin(r_b, AL) != np.isin(r_inst, AL)).sum()),
               noms_bornes_vs_installe=int((r_b != r_inst).sum()),
               alertes_1vue_vs_installe=int((np.isin(r_b1, AL) != np.isin(r_inst, AL)).sum()))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    (C.SORTIE / "temps_bout.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
