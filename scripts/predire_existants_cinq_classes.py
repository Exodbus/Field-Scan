#!/usr/bin/env python3
"""Protocole docs/protocole_maladies_cinq_classes.md, section 5, étape 4 : probabilités et réponses des modèles existants
(v2, soupe v2 + v8, DINOv2-FT), chacun avec ses seuils, sur TDTU (1 636), PSFD (738) et l'Éthiopie (1 289).
Processeur local ; mêmes fonctions que scripts/calculer_deux_branches_local.py. N'affiche aucun score.
Sorties : out/maladies/cinq_classes/predictions_{modele}_{jeu}.csv

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/predire_existants_cinq_classes.py
"""
import json, sys, time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "modeles/maladies_binome/maladies_v2"))
sys.path.insert(0, str(RACINE / "scripts"))
import classifieur  # noqa: E402
from calculer_deux_branches_local import Modele, VERS_COMMUN, lots  # noqa: E402

SORTIE = RACINE / "out/maladies/cinq_classes"
FT = RACINE / "out/maladies/dinov2_ft/dinov2_ft"
torch.set_num_threads(8)


def jeux():
    a = pd.read_csv(RACINE / "data/feuilles_v3_ajouts/images.csv")
    t = a[a.jeu.eq("tdtu")]
    rel = [i.removeprefix("ajouts_v3/") for i in t.image]
    out = {"tdtu": pd.DataFrame(dict(chemin=["data/feuilles_v3_ajouts/" + r for r in rel], jeu="tdtu", classe_vraie=t.classe.values))}
    n = pd.read_csv(RACINE / "out/maladies/maladies_nuit/nuit.csv")
    for j, g in n[n.role.eq("mesure")].groupby("jeu"):
        out[j] = pd.DataFrame(dict(chemin=g.image.values, jeu=j, classe_vraie=g.classe.values))
    return out


def fichier(c):
    return str(RACINE / c) if c.startswith("data/") else str(RACINE / "out/maladies/maladies_nuit" / c)


def ecrire(df, P, rep, nom):
    df.assign(p_saine=P[:, 0].round(6), p_black_sigatoka=P[:, 1].round(6), p_fusarium=P[:, 2].round(6),
              reponse=[VERS_COMMUN[x] for x in rep]).to_csv(SORTIE / f"predictions_{nom}.csv", index=False)


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    J = jeux()
    r, s = classifieur.charger(RACINE / "modeles/maladies_binome/maladies_v2/poids")
    for j, df in J.items():
        if (SORTIE / f"predictions_v2_{j}.csv").exists():
            continue
        t0 = time.time()
        P = classifieur.probabilites(r, [fichier(c) for c in df.chemin], lot=32)
        ecrire(df, P, classifieur.decider(P, s), f"v2_{j}")
        print(f"v2 {j} : {len(df)} en {(time.time() - t0) / 60:.1f} min", flush=True)
    # soupe : les noms de ses poids ne suivent pas le motif de classifieur.charger ; chargeur du module de la chaîne
    # (fieldscan/modules/maladies.py, mêmes calculs, contrôlé contre les fichiers GPU de la soupe)
    sys.path.insert(0, str(RACINE))
    from fieldscan.modules import maladies
    ms = maladies.charger_convnext(RACINE / "modeles/maladies_soupe_v2_v8/poids")
    inverse = {v: k for k, v in VERS_COMMUN.items()}
    for j, df in J.items():
        t0 = time.time()
        P = maladies.predire_convnext([fichier(c) for c in df.chemin], ms)
        rep = maladies.decider_convnext(P, ms)[0]
        ecrire(df, P, [inverse[x] for x in rep], f"soupe_{j}")
        print(f"soupe {j} : {len(df)} en {(time.time() - t0) / 60:.1f} min", flush=True)
    sft = json.loads((FT / "seuils.json").read_text(encoding="utf-8"))
    reseaux = []
    for k in range(1, sft["nb_reseaux"] + 1):
        m = Modele()
        w = torch.load(FT / f"maladies_dinov2_ft_{k}.pt", map_location="cpu", weights_only=True)
        m.load_state_dict({n: v.float() if v.is_floating_point() else v for n, v in w.items()})
        reseaux.append(m.eval())
    vues = classifieur.VUES if sft["quatre_vues"] else classifieur.VUES[:1]
    for j, df in J.items():
        t0 = time.time()
        with torch.no_grad():
            P = np.concatenate([torch.stack([sum(torch.softmax(r(v(x)), 1) for v in vues) / len(vues) for r in reseaux]).mean(0).numpy()
                                for x in lots([fichier(c) for c in df.chemin])])
        ecrire(df, P, classifieur.decider(P, sft), f"dinov2_ft_{j}")
        print(f"dinov2_ft {j} : {len(df)} en {(time.time() - t0) / 60:.1f} min", flush=True)
    print("fini", flush=True)


if __name__ == "__main__":
    main()
