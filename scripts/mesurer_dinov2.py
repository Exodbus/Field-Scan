#!/usr/bin/env python3
"""Mesure unique du diagnostic DINOv2 (docs/protocole_maladies_dinov2.md, sections 3 et 4). À lancer une seule fois.

D1 : détecteur de nouveauté (Mahalanobis c et d) dans l'espace DINOv2 ; réussite si AUC TDTU >= 0,65, puis règles de la
     partie B du protocole « mélange + nouveauté » appliquées aux réponses de la v2.
D2 : sondes linéaires (régression logistique, L2 1e-4, L-BFGS, Pérou x 3) sur DINOv2 et sur ConvNeXt ImageNet ;
     fine-tuning proposé si BananaLSD équilibré DINOv2 >= ConvNeXt + 0,03 et validation équilibrée >= ConvNeXt - 0,01.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/mesurer_dinov2.py --dossier out/maladies/dinov2
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
from mesurer_adoption_v5 import NOMMEE, mesures, part  # noqa: E402
from mesurer_melange_nouveaute import auc, decider, inverse_reduite, regler  # noqa: E402

GPU = RACINE / "out/maladies/kaggle_adoption_finale"
P = ["p_saine", "p_black_sigatoka", "p_fusarium"]
VRAIE = {"saine": 0, "cercosporiose_noire": 1, "fusariose": 2}


def charger(dos, reseau, jeu):
    d = np.load(dos / f"{reseau}_{jeu}.npz", allow_pickle=True)
    return d["car"].astype(np.float64), np.array(d["chemin"]), np.array(d["classe"]), np.array(d["source"])


def ajustement_chemins():
    idx = pd.read_csv(RACINE / "data/feuilles/index.csv")
    idx = idx[idx.retenue.astype(bool) & idx.chemin.notna()]
    ent = idx[idx.ensemble.eq("entrainement")]
    aj = ent.groupby(["source", "classe"], group_keys=False).apply(lambda g: g.sample(min(500, len(g)), random_state=2026))
    return set("data/feuilles/" + aj.chemin)


def mahalanobis(xa, cla, z):
    """Variantes c et d du protocole « mélange + nouveauté »."""
    mus = {c: xa[cla == c].mean(0) for c in sorted(set(cla))}
    icov = inverse_reduite(np.concatenate([xa[cla == c] - mus[c] for c in mus]))
    mu0, icov0 = xa.mean(0), inverse_reduite(xa)
    d = np.stack([np.einsum("ij,jk,ik->i", z - m, icov, z - m) for m in mus.values()], 1)
    d0 = np.einsum("ij,jk,ik->i", z - mu0, icov0, z - mu0)
    return {"c": d.min(1), "d": (d - d0[:, None]).min(1)}


def sonde(x, y, w):
    mu, sd = x.mean(0), x.std(0) + 1e-6
    X, Y, W = torch.tensor((x - mu) / sd), torch.tensor(y), torch.tensor(w / w.sum())
    lin = torch.nn.Linear(X.shape[1], 3).double()
    torch.nn.init.zeros_(lin.weight); torch.nn.init.zeros_(lin.bias)
    opt = torch.optim.LBFGS(lin.parameters(), max_iter=500, line_search_fn="strong_wolfe", tolerance_grad=1e-9, tolerance_change=1e-12)

    def perte():
        opt.zero_grad()
        l = (torch.nn.functional.cross_entropy(lin(X), Y, reduction="none") * W).sum() + 1e-4 * (lin.weight ** 2).sum()
        l.backward()
        return l
    opt.step(perte)
    print(f"  perte finale {float(perte()):.4f}", flush=True)
    return lambda z: torch.softmax(lin(torch.tensor((z - mu) / sd)), 1).detach().numpy()


def equilibre_validation(d):
    return float(np.mean([(g.reponse == c).mean() for c, g in d.groupby("classe_vraie")]))


def equilibre_bananalsd(m):
    return (m["bananalsd_sigatoka_nommee"]["part"] + m["bananalsd_saines_bien_classees"]["part"]) / 2


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default="out/maladies/dinov2")
    dos = RACINE / ap.parse_args(argv).dossier
    sortie = dos / "bilan_dinov2.json"
    if sortie.exists():
        sys.exit(f"{sortie} existe déjà : mesure unique, rien n'est refait.")
    gpu = {j: pd.read_csv(GPU / f"predictions_v2_{j}.csv") for j in ("validation", "bananalsd")}
    for j, g in gpu.items():
        g.to_csv(dos / f"predictions_v2_{j}.csv", index=False)
    aj = ajustement_chemins()
    bilan = {}

    # contrôles : mêmes photos, même ordre ; même tirage d'ajustement que le protocole précédent
    for r in ("dinov2", "convnext_in"):
        for j in ("validation", "bananalsd"):
            assert (charger(dos, r, j)[1] == gpu[j].chemin.to_numpy()).all(), f"ordre différent {r} {j}"
    ancien = set(np.load(RACINE / "out/maladies/nouveaute/caracteristiques_ajustement.npz", allow_pickle=True)["chemin"])
    assert aj == ancien, "tirage d'ajustement différent"
    print("contrôles : ordre des photos et tirage d'ajustement identiques", flush=True)

    # ---------- D1 ----------
    d1 = {}
    for r in ("dinov2", "convnext_in"):
        x, ch, cl, _ = charger(dos, r, "entrainement")
        m = np.isin(ch, list(aj))
        t, _, clt, _ = charger(dos, r, "tdtu")
        s = mahalanobis(x[0][m], cl[m], t[0])
        d1[r] = {k: auc(v, clt == "autre_maladie") for k, v in s.items()}
    best = max(d1["dinov2"].values())
    bilan["d1"] = dict(auc_tdtu=d1, reussite=best >= 0.65)
    if bilan["d1"]["reussite"]:
        var = "d" if d1["dinov2"]["d"] >= d1["dinov2"]["c"] + 0.01 else "c"
        x, ch, cl, _ = charger(dos, "dinov2", "entrainement")
        m = np.isin(ch, list(aj))
        sc = {j: mahalanobis(x[0][m], cl[m], charger(dos, "dinov2", j)[0][0])[var] for j in ("validation", "bananalsd")}
        seuil = float(np.quantile(sc["validation"], 0.98))
        for j, g in gpu.items():
            g = g.copy()
            g["reponse"] = np.where(g.reponse.isin(NOMMEE) & (sc[j] >= seuil), "malade_non_identifiee", g.reponse)
            g.to_csv(dos / f"predictions_nouveaute_dinov2_{j}.csv", index=False)
        r2, mn = mesures(dos, "v2"), mesures(dos, "nouveaute_dinov2")

        def nommees(mod, j, masque):
            d = pd.read_csv(dos / f"predictions_{mod}_{j}.csv")
            return part(d.reponse.isin(NOMMEE), masque(d))
        vm = lambda d: d.classe_vraie.ne("saine")  # noqa: E731
        bi = lambda d: d.classe_vraie.str.startswith("inconnue")  # noqa: E731
        vn = (nommees("v2", "validation", vm), nommees("nouveaute_dinov2", "validation", vm))
        bn = (nommees("v2", "bananalsd", bi), nommees("nouveaute_dinov2", "bananalsd", bi))
        c = {"validation_malades_nommees >= v2 - 0,02": vn[1]["part"] >= vn[0]["part"] - 0.02,
             "validation_nommee_juste >= 0,95": mn["validation_nommee_juste"]["part"] >= 0.95,
             "bananalsd_sigatoka_nommee >= v2 - 0,02": mn["bananalsd_sigatoka_nommee"]["part"] >= r2["bananalsd_sigatoka_nommee"]["part"] - 0.02,
             "gain : bananalsd_inconnues_nommees <= v2 - 0,10": bn[1]["part"] <= bn[0]["part"] - 0.10}
        bilan["d1"].update(variante=var, seuil=seuil, validation_malades_nommees=vn, bananalsd_inconnues_nommees=bn,
                           mesures=mn, conditions=c, adopte=all(c.values()))

    # ---------- D2 ----------
    d2 = {}
    for r in ("dinov2", "convnext_in"):
        print("sonde", r, flush=True)
        x, ch, cl, src = charger(dos, r, "entrainement")
        f = sonde(x[0], np.array([VRAIE[c] for c in cl]), np.where(src == "perou_2026", 3.0, 1.0))
        tab = {}
        for j, g in gpu.items():
            z = charger(dos, r, j)[0]
            tab[j] = g.copy(); tab[j][P] = np.mean([f(v) for v in z], 0)
        s = regler(tab["validation"][P].to_numpy(), tab["validation"].classe_vraie.map(VRAIE).to_numpy())
        for j, d in tab.items():
            d["reponse"] = decider(d[P].to_numpy(), s)
            d.to_csv(dos / f"predictions_sonde_{r}_{j}.csv", index=False)
        m = mesures(dos, f"sonde_{r}")
        d2[r] = dict(seuils=s, mesures=m, validation_equilibre=equilibre_validation(tab["validation"]), bananalsd_equilibre=equilibre_bananalsd(m))
    mv2 = mesures(dos, "v2")
    d2["v2"] = dict(mesures=mv2, validation_equilibre=equilibre_validation(gpu["validation"]), bananalsd_equilibre=equilibre_bananalsd(mv2))
    a, b = d2["dinov2"], d2["convnext_in"]
    regle = {"bananalsd_equilibre DINOv2 >= ConvNeXt + 0,03": a["bananalsd_equilibre"] >= b["bananalsd_equilibre"] + 0.03,
             "validation_equilibre DINOv2 >= ConvNeXt - 0,01": a["validation_equilibre"] >= b["validation_equilibre"] - 0.01}
    bilan["d2"] = dict(d2, regle=regle, fine_tuning_propose=all(regle.values()))
    sortie.write_text(json.dumps(bilan, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")

    print("=== D1 : AUC TDTU", {r: {k: round(v, 3) for k, v in d.items()} for r, d in d1.items()}, "réussite :", bilan["d1"]["reussite"])
    if bilan["d1"]["reussite"]:
        e = bilan["d1"]
        print("  variante", e["variante"], "seuil", round(e["seuil"], 2))
        for k in ("validation_malades_nommees", "bananalsd_inconnues_nommees"):
            print(f"  {k:36s} v2 {e[k][0]['k']}/{e[k][0]['n']}  avec détecteur {e[k][1]['k']}/{e[k][1]['n']}")
        for k, ok in e["conditions"].items():
            print("   OK   " if ok else "   ÉCHEC", k)
        print("  détecteur adopté :", e["adopte"])
    cles = ["validation_malades_dites_saines", "validation_fausses_alertes", "validation_nommee_juste", "bananalsd_sigatoka_nommee",
            "bananalsd_saines_bien_classees", "bananalsd_inconnues_dites_saines", "bananalsd_inconnues_dites_sigatoka"]
    print("=== D2")
    for k in cles:
        print(f"  {k:38s}" + "".join(f"  {r} {d2[r]['mesures'][k]['k']}/{d2[r]['mesures'][k]['n']}" for r in ("v2", "dinov2", "convnext_in")))
    for k in ("validation_equilibre", "bananalsd_equilibre"):
        print(f"  {k:38s}" + "".join(f"  {r} {d2[r][k]:.4f}" for r in ("v2", "dinov2", "convnext_in")))
    for k, ok in regle.items():
        print("   OK   " if ok else "   ÉCHEC", k)
    print("  fine-tuning DINOv2 proposé :", bilan["d2"]["fine_tuning_propose"])


if __name__ == "__main__":
    main()
