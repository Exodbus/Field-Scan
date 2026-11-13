#!/usr/bin/env python3
"""M-analyste (nuit du 12/11) : le raccourci « pays = malade » existe-t-il ? Réglage seulement, aucun réseau lancé.

1. P(malade) des feuilles SAINES selon la source, pour chaque modèle en cache (v10b, soupe, v2, et les candidats v12
   lus dans le pli qui n'a pas appris le pays : a1, c1, c2, ...). Quantiles et part au-dessus de 0,5.
2. Le style de la source se lit-il dans les caractéristiques DINOv3 figées (carnet m12-extraire-dinov3) ?
   Classifieur logistique de la source, appris sur 80 % des photos, mesuré sur 20 % (tirage graine 0).
3. Pour chaque pays X (TDTU, Éthiopie) : classifieur de source appris SANS X ni la validation (les sources
   d'apprentissage des plis v12), lu sur les saines de X -> P(PSFD), P(PSFD + Éthiopie), P(Tanzanie). Corrélation de
   rang (Spearman) avec la P(malade) de chaque modèle sur ces mêmes saines. Un raccourci donnerait une corrélation
   positive avec P(PSFD) pour les candidats qui ont appris PSFD, et pas (ou moins) pour la v10b.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_analyse_raccourci.py [candidats ...]
Sorties : out/maladies/analyse/raccourci_*.csv / .json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

RACINE = Path(__file__).resolve().parents[1]
torch.set_num_threads(1)
CARAC = RACINE / "out/maladies/nuit_1112/kaggle/caract_dinov3"
KAG = RACINE / "out/maladies/nuit_1112/kaggle"
SORTIE = RACINE / "out/maladies/analyse"
CANDS = sys.argv[1:] or ["a1", "c1", "c2"]
PAYS = ["tdtu", "psfd", "ethiopie"]
TAB = pd.read_csv(SORTIE / "table_reglage.csv")


def spearman(a, b):
    return float(np.corrcoef(pd.Series(a).rank(), pd.Series(b).rank())[0, 1])


def pm_candidat(c):
    """P(malade) du candidat c par chemin : pays lu dans son pli ; validation = moyenne des plis présents."""
    out = {}
    d = KAG / c
    for p in PAYS:
        f = d / f"predictions_{c}_{p}.csv"
        if f.exists():
            x = pd.read_csv(f)
            out.update(dict(zip(x.chemin, 1 - x.p_saine)))
    v = [pd.read_csv(d / f"predictions_{c}_validation_pli_{p}.csv") for p in PAYS
         if (d / f"predictions_{c}_validation_pli_{p}.csv").exists()]
    if v:
        m = np.mean([1 - x.p_saine.to_numpy() for x in v], 0)
        out.update(dict(zip(v[0].chemin, m)))
    return out


def partie1():
    modeles = {"v10b": 1 - TAB.ps_v10b, "soupe": 1 - TAB.ps_soupe, "v2": 1 - TAB.ps_v2,
               "F1_lecteur_proche": 1 - TAB.ps_F1_trois_morceaux2x2}
    for c in CANDS:
        if (KAG / c).exists():
            modeles[c] = TAB.chemin.map(pm_candidat(c))
    lignes = []
    for nom, pm in modeles.items():
        for j in ["validation", "tdtu", "ethiopie"]:
            s = pm[(TAB.jeu == j) & ~TAB.malade].dropna()
            if len(s) == 0:
                continue
            q = s.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).to_numpy()
            lignes.append(dict(modele=nom, jeu=j + " (saines)", n=len(s), q10=q[0], q25=q[1], mediane=q[2], q75=q[3],
                               q90=q[4], part_sup_0_5=float((s >= 0.5).mean()), part_sup_0_3=float((s >= 0.3).mean())))
        for j in ["validation", "tdtu", "psfd", "ethiopie"]:
            s = pm[(TAB.jeu == j) & TAB.malade].dropna()
            if len(s):
                q = s.quantile([0.1, 0.25, 0.5]).to_numpy()
                lignes.append(dict(modele=nom, jeu=j + " (malades)", n=len(s), q10=q[0], q25=q[1], mediane=q[2],
                                   part_sup_0_5=float((s >= 0.5).mean()), part_sup_0_3=float((s >= 0.3).mean())))
    t = pd.DataFrame(lignes)
    t.to_csv(SORTIE / "raccourci_pmalade_par_source.csv", index=False)
    print(t.to_string(float_format=lambda x: f"{x:.3f}"))
    return modeles


def logistique(X, y, k, n_iter=150, l2=1e-3):
    X, y = torch.from_numpy(X), torch.from_numpy(y.astype("int64"))
    m = torch.nn.Linear(X.shape[1], k)
    opt = torch.optim.LBFGS(m.parameters(), lr=1, max_iter=n_iter, history_size=20, line_search_fn="strong_wolfe")
    poids = 1.0 / torch.bincount(y, minlength=k).float().clamp(min=1)
    poids = poids / poids.mean()

    def f():
        opt.zero_grad()
        l = torch.nn.functional.cross_entropy(m(X), y, weight=poids) + l2 * (m.weight ** 2).sum()
        l.backward()
        return l
    opt.step(f)
    return m


def partie2_3(modeles):
    idx = pd.read_csv(CARAC / "index_reglage.csv")
    Fe = np.load(CARAC / "caracteristiques_reglage.npy", mmap_mode="r")[:, 0].astype("float32")
    X = (Fe - Fe.mean(0)) / (Fe.std(0) + 1e-6)
    # réduction à 128 composantes principales (machine saturée : calcul rapide sur un fil)
    sous = X[np.random.default_rng(1).choice(len(X), 6000, replace=False)]
    _, _, Vt = np.linalg.svd(sous, full_matrices=False)
    X = np.ascontiguousarray(X @ Vt[:128].T, dtype="float32")
    X /= X.std(0) + 1e-6
    sources = sorted(idx.jeu.unique())
    y = idx.jeu.map({s: i for i, s in enumerate(sources)}).to_numpy()
    test = np.random.default_rng(0).random(len(idx)) < 0.2
    m = logistique(X[~test], y[~test], len(sources))
    with torch.no_grad():
        pr = m(torch.from_numpy(X[test])).argmax(1).numpy()
    acc = {s: float((pr[y[test] == i] == i).mean()) for i, s in enumerate(sources)}
    print("\nexactitude du classifieur de source (20 % tenus à part) :", {k: round(v, 3) for k, v in acc.items()})
    sa = idx.classe_vraie.eq("saine").to_numpy()
    src_s = [s for s in sources if (sa & (idx.jeu == s).to_numpy()).sum() > 50]
    ms = sa & idx.jeu.isin(src_s).to_numpy()
    ys = idx.jeu.map({s: i for i, s in enumerate(src_s)}).fillna(-1).to_numpy().astype(int)
    m2 = logistique(X[ms & ~test], ys[ms & ~test], len(src_s))
    with torch.no_grad():
        pr2 = m2(torch.from_numpy(X[ms & test])).argmax(1).numpy()
    yt = ys[ms & test]
    acc2 = {s: float((pr2[yt == i] == i).mean()) for i, s in enumerate(src_s)}
    print("saines seules : exactitude par source", {k: round(v, 3) for k, v in acc2.items()})
    res = dict(exactitude_source=acc, exactitude_source_saines=acc2, correlations=[])
    pm_par_chemin = {k: dict(zip(TAB.chemin, v)) for k, v in modeles.items()}
    for X_ in ["tdtu", "ethiopie"]:
        app = ~idx.jeu.isin([X_, "validation"]).to_numpy()
        src = sorted(idx.jeu[app].unique())
        yy = idx.jeu.map({s: i for i, s in enumerate(src)}).fillna(-1).to_numpy().astype(int)
        mm = logistique(X[app], yy[app], len(src))
        cible = (idx.jeu == X_).to_numpy() & sa
        with torch.no_grad():
            P = torch.softmax(mm(torch.from_numpy(X[cible])), 1).numpy()
        ch = idx.chemin[cible].to_numpy()
        p_psfd = P[:, src.index("psfd")]
        p_tz = P[:, src.index("tanzanie_2021")]
        autres_malades = [s for s in ("psfd", "ethiopie", "tdtu", "mendeley_bd") if s in src]
        p_pm = P[:, [src.index(s) for s in autres_malades]].sum(1)
        plus = pd.Series(np.array(src)[P.argmax(1)]).value_counts().to_dict()
        print(f"\n{X_} : saines ({int(cible.sum())}) rangées par le classifieur de source appris sans {X_} :", plus)
        pd.DataFrame(dict(chemin=ch, p_tanzanie=p_tz, p_psfd=p_psfd, p_autres_pays=p_pm,
                          **{f"psrc_{s}": P[:, i] for i, s in enumerate(src)})).to_csv(
            SORTIE / f"raccourci_source_saines_{X_}.csv", index=False)
        for nom, d in pm_par_chemin.items():
            pm = np.array([d.get(c, np.nan) for c in ch], float)
            ok = ~np.isnan(pm)
            if ok.sum() < 30:
                continue
            haut = p_pm[ok] >= np.median(p_pm[ok])
            r = dict(pays=X_, modele=nom, n=int(ok.sum()), rho_p_psfd=spearman(p_psfd[ok], pm[ok]),
                     rho_p_autres_pays=spearman(p_pm[ok], pm[ok]), rho_p_tanzanie=spearman(p_tz[ok], pm[ok]),
                     pm_moitie_style_autres_pays=float(pm[ok][haut].mean()), pm_moitie_style_tanz=float(pm[ok][~haut].mean()),
                     fa05_moitie_style_autres_pays=float((pm[ok][haut] >= 0.5).mean()),
                     fa05_moitie_style_tanz=float((pm[ok][~haut] >= 0.5).mean()))
            res["correlations"].append(r)
            print(f"  {nom:18s} n={r['n']} rho(P psfd)={r['rho_p_psfd']:+.3f} rho(P autres pays)={r['rho_p_autres_pays']:+.3f} "
                  f"rho(P tanz)={r['rho_p_tanzanie']:+.3f} | P(malade)>=0,5 : moitié « autres pays » "
                  f"{r['fa05_moitie_style_autres_pays']:.2f} contre moitié « Tanzanie » {r['fa05_moitie_style_tanz']:.2f}")
    (SORTIE / "raccourci_bilan.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    import functools, builtins
    print = functools.partial(builtins.print, flush=True)  # noqa: A001
    partie2_3(partie1())
