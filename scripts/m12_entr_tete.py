#!/usr/bin/env python3
"""M6 (v12c) : tête légère sur caractéristiques DINOv3 ViT-B figées (photo entière + 4 morceaux), agent M-entraînement.

Caractéristiques : sortie du carnet Kaggle m12-extraire-dinov3 (caracteristiques_reglage.npy, (n, 5, 1536) ; index_reglage.csv).
Même étiquetage, même perte pondérée et même tirage par pays et par classe que les carnets v12 (journal, choix 1 à 3).
Validation croisée par pays : pour chaque pays X, une tête apprise sans X, lue sur X et sur la validation Tanzanie.
Sortie : out/maladies/nuit_1112/kaggle/<candidat>/predictions_<candidat>_<jeu>.csv (+ _validation_pli_<pays>).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/m12_entr_tete.py <dossier caract.> <candidat> <tete> <entree> [final]
      tete   : logistique | mlp
      entree : entiere (1 536) | concat (entière + moyenne et maximum des 4 morceaux, 4 608)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

RACINE = Path(__file__).resolve().parents[1]
CARAC, NOM, TETE, ENTREE = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
FINAL = len(sys.argv) > 5 and sys.argv[5] == "final"
SORTIE = RACINE / "out/maladies/nuit_1112/kaggle" / NOM
SORTIE.mkdir(parents=True, exist_ok=True)
SANS_NOM, PAYS = 4, ["tdtu", "psfd", "ethiopie"]
VERS = {"saine": 0, "cercosporiose_noire": 1, "black_sigatoka": 1, "fusariose": 2, "cordana": 3, "pestalotiopsis": 3,
        "sigatoka_jaune": 3, "xanthomonas": 3, "autre_maladie": SANS_NOM, "sigatoka": SANS_NOM}
import os
SAIN_SOURCE = os.environ.get("SAIN_SOURCE") == "1"
HORS = [j for j in os.environ.get("HORS", "").split(",") if j]   # sources jamais apprises (ex. psfd)
POIDS_RATEE = float(os.environ.get("POIDS_RATEE", "3"))
torch.set_num_threads(int(__import__("os").environ.get("FILS", "1")))

idx = pd.read_csv(CARAC / "index_reglage.csv")
F = np.load(CARAC / "caracteristiques_reglage.npy").astype("float32")
assert len(idx) == len(F)
assert not idx.jeu.isin(["cordana_perou", "bananalsd", "banspot"]).any(), "aucun juge ici"
if ENTREE == "entiere":
    X = F[:, 0]
else:
    X = np.concatenate([F[:, 0], F[:, 1:].mean(1), F[:, 1:].max(1)], 1)
idx["y"] = [VERS[c] for c in idx.classe_vraie]
idx["pays"] = idx.jeu
val = idx.jeu.eq("validation").to_numpy()


def poids_tirage(df):
    fixe = {"tanzanie_2021": 0.40, "perou_2026": 0.10, "mendeley_bd": 0.05}
    sources = list(df.pays.unique())
    autres = [s for s in sources if s not in fixe]
    part = {s: fixe[s] for s in sources if s in fixe}
    part.update({s: (1 - sum(part.values())) / len(autres) for s in autres})
    n_classes = df.groupby("pays").y.nunique()
    n = df.groupby(["pays", "y"]).y.transform("size")
    w = (df.pays.map(part) / df.pays.map(n_classes) / n).to_numpy(dtype="float64").copy()
    if SAIN_SOURCE:   # moitié saines, moitié malades dans chaque source (recommandation de M-analyste)
        s_ = df.y.to_numpy() == 0
        for src in df.pays.unique():
            k_ = (df.pays == src).to_numpy()
            if s_[k_].any() and (~s_[k_]).any():
                t_ = w[k_].sum()
                w[k_ & s_] *= 0.5 * t_ / w[k_ & s_].sum()
                w[k_ & ~s_] *= 0.5 * t_ / w[k_ & ~s_].sum()
    return w


def perte(z, y, w, poids_ratee=None):
    poids_ratee = POIDS_RATEE if poids_ratee is None else poids_ratee
    lp = torch.log_softmax(z, 1)
    l_malade = -torch.logsumexp(lp[:, 1:], 1)
    nomme = y < SANS_NOM
    yc = torch.where(nomme, y, torch.zeros_like(y))
    ce = -lp.gather(1, yc[:, None])[:, 0]
    l = torch.where(nomme, ce + (poids_ratee - 1) * l_malade * (nomme & (y > 0)), poids_ratee * l_malade)
    return (l * w).sum() / w.sum()


def apprendre(masque, graine=0):
    torch.manual_seed(graine)
    Xa, ya = torch.from_numpy(X[masque]), torch.from_numpy(idx.y.to_numpy()[masque])
    w = torch.from_numpy(poids_tirage(idx[masque]).astype("float32"))
    mu, sd = Xa.mean(0), Xa.std(0) + 1e-6
    d = X.shape[1]
    if TETE == "logistique":
        m = torch.nn.Linear(d, 4)
    else:
        m = torch.nn.Sequential(torch.nn.Dropout(0.2), torch.nn.Linear(d, 512), torch.nn.GELU(), torch.nn.Dropout(0.2), torch.nn.Linear(512, 4))
    opt = torch.optim.AdamW(m.parameters(), lr=1e-3, weight_decay=1e-2 if TETE == "logistique" else 5e-2)
    n_pas = 3000
    plan = torch.optim.lr_scheduler.CosineAnnealingLR(opt, n_pas)
    g = torch.Generator().manual_seed(graine)
    for _ in range(n_pas):   # lots de 512 tirés selon les poids (tirage équilibré par pays et par classe)
        i = torch.multinomial(w, 512, replacement=True, generator=g)
        m.train(); opt.zero_grad()
        l = perte(m((Xa[i] - mu) / sd), ya[i], torch.ones(512))
        l.backward(); opt.step(); plan.step()
    m.eval()
    return lambda Z: torch.softmax(m((torch.from_numpy(Z) - mu) / sd), 1).detach().numpy()


def ecrire(P, masque, chemin):
    out = idx.loc[masque, ["chemin", "jeu", "classe_vraie"]].copy()
    for k, c in enumerate(["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]):
        out[c] = P[:, k].round(6)
    out.to_csv(chemin, index=False)


hors = idx.jeu.isin(HORS).to_numpy()
if FINAL:
    f = apprendre(~val & ~hors)
    ecrire(f(X[val]), val, SORTIE / f"predictions_{NOM}_final_validation.csv")
else:
    for x in PAYS:
        if x in HORS:
            continue
        f = apprendre(~val & ~hors & ~idx.jeu.eq(x).to_numpy())
        for h in HORS:   # source jamais apprise : lue par la tête du premier pli
            mh = idx.jeu.eq(h).to_numpy()
            if not (SORTIE / f"predictions_{NOM}_{h}.csv").exists():
                ecrire(f(X[mh]), mh, SORTIE / f"predictions_{NOM}_{h}.csv")
        mx = idx.jeu.eq(x).to_numpy()
        ecrire(f(X[mx]), mx, SORTIE / f"predictions_{NOM}_{x}.csv")
        ecrire(f(X[val]), val, SORTIE / f"predictions_{NOM}_validation_pli_{x}.csv")
        print(NOM, "pli sans", x, "écrit", flush=True)
