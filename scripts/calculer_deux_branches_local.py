#!/usr/bin/env python3
"""Calculs du protocole « deux branches » sur le processeur local (même contenu que notebooks/deux_branches_kaggle.py,
qui attendait un GPU Kaggle). N'affiche aucun score.

  - caractéristiques DINOv2 ViT-B/14 figées des photos de loin (C:/Users/coren/kaggle_tmp/photos_loin), vue d'origine ;
  - probabilités et réponses de la v2 (3 réseaux, 4 vues) et de DINOv2-FT (ses seuils) sur TDTU.
Sorties dans out/maladies/deux_branches/. Poids DINOv2 téléchargés par torch.hub (accord de Corentin).

    PYTHONIOENCODING=utf-8 SSL_CERT_FILE=... .venv/Scripts/python.exe -I -u scripts/calculer_deux_branches_local.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "modeles/maladies_binome/maladies_v2"))
import classifieur  # noqa: E402

LOIN = Path("C:/Users/coren/kaggle_tmp/photos_loin")
SORTIE = RACINE / "out/maladies/deux_branches"
FT = RACINE / "out/maladies/dinov2_ft/dinov2_ft"
VERS_COMMUN = {"saine": "saine", "black_sigatoka": "cercosporiose_noire", "fusarium": "fusariose",
               "malade_non_identifiee": "malade_non_identifiee", "inconnu": "je_ne_sais_pas"}
torch.set_num_threads(8)


def lots(fichiers, n=32):
    for i in range(0, len(fichiers), n):
        yield torch.stack([classifieur.PREPARATION(classifieur.preparer(f)) for f in fichiers[i:i + n]])


class Modele(torch.nn.Module):   # comme dans notebooks/entrainer_maladies_dinov2_kaggle.py
    def __init__(self):
        super().__init__()
        self.dino = torch.hub.load("facebookresearch/dinov2", "dinov2_vitb14", trust_repo=True)
        self.tete = torch.nn.Linear(1536, 3)

    def caracteristiques(self, x):
        f = self.dino.forward_features(x)
        return torch.cat([f["x_norm_clstoken"], f["x_norm_patchtokens"].mean(1)], 1)

    def forward(self, x):
        return self.tete(self.caracteristiques(x))


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    # 1. Caractéristiques DINOv2 figées des photos de loin
    l = pd.read_csv(LOIN / "liste_photos_loin.csv")
    dino = torch.hub.load("facebookresearch/dinov2", "dinov2_vitb14", trust_repo=True).eval()
    t0, car = time.time(), []
    with torch.no_grad():
        for k, x in enumerate(lots([str(LOIN / f) for f in l.fichier])):
            f = dino.forward_features(x)
            car.append(torch.cat([f["x_norm_clstoken"], f["x_norm_patchtokens"].mean(1)], 1).numpy().astype(np.float16))
            if k % 20 == 0:
                print(f"  loin {(k + 1) * 32}/{len(l)} ({time.time() - t0:.0f} s)", flush=True)
    np.savez_compressed(SORTIE / "dinov2_photos_loin.npz", car=np.concatenate(car)[None], fichier=np.array(l.fichier),
                        source=np.array(l.source), role=np.array(l.role))
    print(f"photos de loin : {len(l)} en {(time.time() - t0) / 60:.1f} min", flush=True)

    # 2. TDTU : v2 et DINOv2-FT, chacun avec ses seuils
    a = pd.read_csv(RACINE / "data/feuilles_v3_ajouts/images.csv")
    t = a[a.jeu.eq("tdtu") & a.classe.isin(["autre_maladie", "black_sigatoka"])]
    rel = [i.removeprefix("ajouts_v3/") for i in t.image]
    tdtu = pd.DataFrame(dict(chemin=["data/feuilles_v3_ajouts/" + r for r in rel], classe_vraie=t.classe.values))
    fichiers = [str(RACINE / c) for c in tdtu.chemin]
    r2, s2 = classifieur.charger(RACINE / "modeles/maladies_binome/maladies_v2/poids")
    t0 = time.time()
    P2 = classifieur.probabilites(r2, fichiers, lot=32)
    tdtu.assign(p_saine=P2[:, 0].round(6), p_black_sigatoka=P2[:, 1].round(6), p_fusarium=P2[:, 2].round(6),
                reponse=[VERS_COMMUN[x] for x in classifieur.decider(P2, s2)]).to_csv(SORTIE / "predictions_tdtu_v2.csv", index=False)
    print(f"TDTU v2 : {len(tdtu)} en {(time.time() - t0) / 60:.1f} min", flush=True)
    sft = json.loads((FT / "seuils.json").read_text(encoding="utf-8"))
    reseaux = []
    for k in range(1, sft["nb_reseaux"] + 1):
        m = Modele()
        w = torch.load(FT / f"maladies_dinov2_ft_{k}.pt", map_location="cpu", weights_only=True)
        m.load_state_dict({n: v.float() if v.is_floating_point() else v for n, v in w.items()})
        reseaux.append(m.eval())
    vues = classifieur.VUES if sft["quatre_vues"] else classifieur.VUES[:1]
    t0 = time.time()
    with torch.no_grad():
        PF = np.concatenate([torch.stack([sum(torch.softmax(r(v(x)), 1) for v in vues) / len(vues) for r in reseaux]).mean(0).numpy()
                             for x in lots(fichiers)])
    tdtu.assign(p_saine=PF[:, 0].round(6), p_black_sigatoka=PF[:, 1].round(6), p_fusarium=PF[:, 2].round(6),
                reponse=[VERS_COMMUN[x] for x in classifieur.decider(PF, sft)]).to_csv(SORTIE / "predictions_tdtu_dinov2_ft.csv", index=False)
    print(f"TDTU DINOv2-FT : {len(reseaux)} réseau(x), {len(vues)} vue(s), {(time.time() - t0) / 60:.1f} min", flush=True)
    print("fini", flush=True)


if __name__ == "__main__":
    main()
