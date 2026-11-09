#!/usr/bin/env python3
"""Mesure unique du protocole « deux branches » (docs/protocole_maladies_deux_branches.md, sections 2 et 3, amendement 1).

A. Aiguilleur loin / près : régression logistique (recette des sondes du diagnostic DINOv2, deux classes de même poids)
   sur les caractéristiques DINOv2 figées ; « loin » si P(loin) >= 0,5. Réussite : >= 95 % « proche » sur la validation
   et sur BananaLSD, >= 90 % « loin » sur le téléphone ROAMER bunchy top + saines. Le reste est indicatif.
B. Désaccord : réponse de DINOv2-FT ; nom retiré (« malade, non identifiée ») quand la v2 ne donne pas le même nom.
   Contrôle TDTU (écart >= 20 points entre autre_maladie et black_sigatoka), puis adoption et départage avec la soupe.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/mesurer_deux_branches.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
from mesurer_adoption_v5 import NOMMEE, mesures  # noqa: E402
from mesurer_dinov2 import ajustement_chemins  # noqa: E402
from mesurer_dinov2_ft import equilibre  # noqa: E402

DOS = RACINE / "out/maladies/deux_branches"
DINO = RACINE / "out/maladies/dinov2"
GPU = RACINE / "out/maladies/kaggle_adoption_finale"
FT = RACINE / "out/maladies/dinov2_ft"
SOUPE = RACINE / "out/maladies/melange"


def sonde_binaire(x, y):
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
    return lambda z: torch.softmax(lin(torch.tensor((z - mu) / sd)), 1)[:, 1].detach().numpy()


def partie_a():
    e = np.load(DINO / "dinov2_entrainement.npz", allow_pickle=True)
    m = np.isin(e["chemin"], list(ajustement_chemins()))
    assert m.sum() == 2500
    loin = np.load(DOS / "dinov2_photos_loin.npz", allow_pickle=True)
    xl, role, source = loin["car"][0].astype(np.float64), loin["role"], loin["source"]
    app = role == "apprentissage_loin"
    f = sonde_binaire(np.vstack([e["car"][0][m].astype(np.float64), xl[app]]), np.r_[np.zeros(m.sum(), int), np.ones(app.sum(), int)])
    res = {}
    for j in ("validation", "bananalsd"):
        res[f"proche_{j}"] = float((f(np.load(DINO / f"dinov2_{j}.npz", allow_pickle=True)["car"][0].astype(np.float64)) < 0.5).mean())
    p = f(xl)
    for r in sorted(set(role) - {"apprentissage_loin"}):
        res[f"loin_{r}"] = float((p[role == r] >= 0.5).mean())
    res["loin_par_source"] = {s: round(float((p[source == s] >= 0.5).mean()), 3) for s in sorted(set(source[~app]))}
    c = {"validation : proche >= 95 %": res["proche_validation"] >= 0.95, "BananaLSD : proche >= 95 %": res["proche_bananalsd"] >= 0.95,
         "téléphone bunchy top + saines : loin >= 90 %": res["loin_mesure_loin_telephone"] >= 0.90}
    return dict(mesures=res, conditions=c, reussite=all(c.values()))


def desaccord(ft, v2):
    return ft.reponse.isin(NOMMEE) & (v2.reponse != ft.reponse)


def partie_b():
    t2, tf = pd.read_csv(DOS / "predictions_tdtu_v2.csv"), pd.read_csv(DOS / "predictions_tdtu_dinov2_ft.csv")
    assert (t2.chemin == tf.chemin).all()
    nomme, perdu = tf.reponse.isin(NOMMEE), desaccord(tf, t2)
    part = {c: float(perdu[nomme & tf.classe_vraie.eq(c)].mean()) for c in ("autre_maladie", "black_sigatoka")}
    controle = part["autre_maladie"] - part["black_sigatoka"] >= 0.20
    out = dict(tdtu_part_nom_retire=part, tdtu_nommees={c: int((nomme & tf.classe_vraie.eq(c)).sum()) for c in part}, controle_tdtu=controle)
    if not controle:
        return out
    for j in ("validation", "bananalsd"):
        v2, ft = pd.read_csv(GPU / f"predictions_v2_{j}.csv"), pd.read_csv(FT / f"predictions_dinov2_ft_{j}.csv")
        assert (v2.chemin == ft.chemin).all()
        v2.to_csv(DOS / f"predictions_v2_{j}.csv", index=False)
        pd.read_csv(SOUPE / f"predictions_soupe_{j}.csv").to_csv(DOS / f"predictions_soupe_{j}.csv", index=False)
        ft.assign(reponse=np.where(desaccord(ft, v2), "malade_non_identifiee", ft.reponse)).to_csv(DOS / f"predictions_proche_{j}.csv", index=False)
    r, m, s = mesures(DOS, "v2"), mesures(DOS, "proche"), mesures(DOS, "soupe")
    p = lambda x, k: x[k]["part"]  # noqa: E731
    c = {
        "validation_malades_dites_saines <= v2 + 0,005": p(m, "validation_malades_dites_saines") <= p(r, "validation_malades_dites_saines") + 0.005,
        "validation_fausses_alertes <= v2 + 0,01": p(m, "validation_fausses_alertes") <= p(r, "validation_fausses_alertes") + 0.01,
        "validation_nommee_juste >= 0,95": p(m, "validation_nommee_juste") >= 0.95,
        "bananalsd_sigatoka_nommee >= v2 - 0,02": p(m, "bananalsd_sigatoka_nommee") >= p(r, "bananalsd_sigatoka_nommee") - 0.02,
        "bananalsd_saines_bien_classees >= v2 - 0,02": p(m, "bananalsd_saines_bien_classees") >= p(r, "bananalsd_saines_bien_classees") - 0.02,
        "bananalsd_inconnues_dites_saines <= v2 + 0,01": p(m, "bananalsd_inconnues_dites_saines") <= p(r, "bananalsd_inconnues_dites_saines") + 0.01,
        "garde : inconnues dites Sigatoka <= v2 + 0,05": p(m, "bananalsd_inconnues_dites_sigatoka") <= p(r, "bananalsd_inconnues_dites_sigatoka") + 0.05,
        "gain : rappel équilibré BananaLSD >= v2 + 0,01": equilibre(m) >= equilibre(r) + 0.01,
    }
    adoptable = all(c.values())
    out.update(mesures=dict(v2=r, proche=m, soupe=s), equilibre=dict(v2=equilibre(r), proche=equilibre(m), soupe=equilibre(s)),
               conditions=c, adoptable=adoptable, remplace_la_soupe=adoptable and equilibre(m) >= equilibre(s) + 0.01)
    return out


def main():
    sortie = DOS / "bilan_deux_branches.json"
    if sortie.exists():
        sys.exit(f"{sortie} existe déjà : mesure unique, rien n'est refait.")
    a, b = partie_a(), partie_b()
    sortie.write_text(json.dumps(dict(partie_a=a, partie_b=b), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
    print("=== A : aiguilleur")
    for k, v in a["mesures"].items():
        print(f"  {k:42s} {v if isinstance(v, dict) else round(v, 4)}")
    for k, ok in a["conditions"].items():
        print("   OK   " if ok else "   ÉCHEC", k)
    print("  aiguilleur réussi :", a["reussite"])
    print("=== B : désaccord ; TDTU, part des noms retirés :", {k: round(v, 3) for k, v in b["tdtu_part_nom_retire"].items()},
          "nommées :", b["tdtu_nommees"], "contrôle :", b["controle_tdtu"])
    if b["controle_tdtu"]:
        cles = ["validation_malades_dites_saines", "validation_fausses_alertes", "validation_nommee_juste", "bananalsd_sigatoka_nommee",
                "bananalsd_saines_bien_classees", "bananalsd_inconnues_dites_saines", "bananalsd_inconnues_dites_sigatoka",
                "bananalsd_inconnues_non_identifiees_ou_jnsp"]
        for k in cles:
            print(f"  {k:46s}" + "".join(f"  {n} {b['mesures'][n][k]['k']}/{b['mesures'][n][k]['n']}" for n in ("v2", "proche", "soupe")))
        print("  rappel équilibré BananaLSD", {k: round(v, 4) for k, v in b["equilibre"].items()})
        for k, ok in b["conditions"].items():
            print("   OK   " if ok else "   ÉCHEC", k)
        print("  branche « proche » adoptable :", b["adoptable"], "| remplace la soupe :", b["remplace_la_soupe"])


if __name__ == "__main__":
    main()
