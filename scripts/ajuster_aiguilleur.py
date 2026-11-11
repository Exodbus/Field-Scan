#!/usr/bin/env python3
"""Aiguilleur « loin / près » du module maladies, réajusté à l'identique du protocole « deux branches » (partie A) et
enregistré pour la chaîne (docs/protocole_maladies_cinq_classes.md, section 4).

Mêmes caractéristiques (DINOv2 ViT-B/14 figé, [jeton de classe, moyenne des jetons d'image]), mêmes photos (500 par source
et classe de l'apprentissage de la v2 ; robot ROAMER de dev_loin), même recette (scripts/mesurer_deux_branches.py,
sonde_binaire). Vérifie que les mesures de la partie A sont retrouvées, puis écrit modeles/maladies_aiguilleur/aiguilleur.npz
(moyenne, écart, poids, biais) : P(loin) = softmax(W ((x - moyenne) / écart) + b)[1].

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/ajuster_aiguilleur.py
"""
import json, sys
from pathlib import Path

import numpy as np
import torch

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
from mesurer_dinov2 import ajustement_chemins  # noqa: E402

DINO, DOS = RACINE / "out/maladies/dinov2", RACINE / "out/maladies/deux_branches"
SORTIE = RACINE / "modeles/maladies_aiguilleur"


def ajuster(x, y):   # copie de mesurer_deux_branches.sonde_binaire, qui renvoie aussi les paramètres
    mu, sd = x.mean(0), x.std(0) + 1e-6
    w = np.where(y == 1, 0.5 / (y == 1).sum(), 0.5 / (y == 0).sum())
    X, Y, W = torch.tensor((x - mu) / sd), torch.tensor(y), torch.tensor(w)
    lin = torch.nn.Linear(X.shape[1], 2).double()
    torch.nn.init.zeros_(lin.weight); torch.nn.init.zeros_(lin.bias)
    opt = torch.optim.LBFGS(lin.parameters(), max_iter=500, line_search_fn="strong_wolfe", tolerance_grad=1e-9, tolerance_change=1e-12)

    def perte():
        opt.zero_grad()
        l = (torch.nn.functional.cross_entropy(lin(X), Y, reduction="none") * W).sum() + 1e-4 * (lin.weight ** 2).sum()
        l.backward()
        return l
    opt.step(perte)
    return mu, sd, lin.weight.detach().numpy(), lin.bias.detach().numpy()


def p_loin(x, a):
    z = ((x - a["moyenne"]) / a["ecart"]) @ a["poids"].T + a["biais"]
    z = z - z.max(1, keepdims=True)
    e = np.exp(z)
    return e[:, 1] / e.sum(1)


def main():
    e = np.load(DINO / "dinov2_entrainement.npz", allow_pickle=True)
    m = np.isin(e["chemin"], list(ajustement_chemins()))
    loin = np.load(DOS / "dinov2_photos_loin.npz", allow_pickle=True)
    xl, role = loin["car"][0].astype(np.float64), loin["role"]
    app = role == "apprentissage_loin"
    mu, sd, W, b = ajuster(np.vstack([e["car"][0][m].astype(np.float64), xl[app]]), np.r_[np.zeros(m.sum(), int), np.ones(app.sum(), int)])
    a = dict(moyenne=mu, ecart=sd, poids=W, biais=b)
    verif = {f"proche_{j}": float((p_loin(np.load(DINO / f"dinov2_{j}.npz", allow_pickle=True)["car"][0].astype(np.float64), a) < 0.5).mean())
             for j in ("validation", "bananalsd")}
    verif["loin_mesure_loin_telephone"] = float((p_loin(xl[role == "mesure_loin_telephone"], a) >= 0.5).mean())
    attendu = json.loads((DOS / "bilan_deux_branches.json").read_text(encoding="utf-8"))["partie_a"]["mesures"]
    for k, v in verif.items():
        assert abs(v - attendu[k]) < 1e-9, (k, v, attendu[k])
    SORTIE.mkdir(parents=True, exist_ok=True)
    np.savez(SORTIE / "aiguilleur.npz", **{k: v.astype(np.float64) for k, v in a.items()})
    (SORTIE / "aiguilleur.json").write_text(json.dumps(dict(
        caracteristiques="DINOv2 ViT-B/14 figé (torch.hub facebookresearch/dinov2, dinov2_vitb14), [x_norm_clstoken, moyenne de x_norm_patchtokens], préparation de la v2 (224 px, JPEG 95), vue d'origine",
        decision="loin si P(loin) >= 0,5", seuil=0.5, protocole="docs/protocole_maladies_deux_branches.md (partie A, réussie)",
        verification=verif), ensure_ascii=False, indent=1), encoding="utf-8")
    print("aiguilleur enregistré ; mesures de la partie A retrouvées :", verif)


if __name__ == "__main__":
    main()
