#!/usr/bin/env python3
"""CB2 (agent C-banc, nuit du 13/11) : robustesse à la résolution d'origine, sur le RÉGLAGE seulement.

Le réglage (5 jeux) est dégradé à 8 et 11 cm/px puis remis à 5 cm (c13_banc_degrade.py) ; `val_negatifs` reste à 5 cm.
Un candidat « résolution » connaît la résolution d'origine de l'image (dans la chaîne : lue dans le GeoTIFF ; ici : la
variante d8 / d11, ou 5 pour l'image d'origine), par ctx.cm. ctx.carte(m) rend la carte du modèle m sur l'image telle
qu'elle arrive (dégradée ou non) ; ctx.carte(m, "sh") la carte sur l'image renforcée (masque flou).

Règle « finaliste résolution » (plan 5.3) : moyenne des 5 F1 à 11 cm >= v5 dégradé (seuil 0,30) + 0,030 ; moyenne des
5 F1 à 5 cm >= v5 - 0,005 ; et les autres conditions de 5.3 à 5 cm (aucun jeu à moins de -0,020, erreur de compte <= v5,
val_negatifs < 1 %). Le seuil du candidat est choisi à 5 cm par la règle 5.3 (grille 0,10 à 0,60) et appliqué tel quel
aux images dégradées.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c13_banc_resolution.py --liste cb2a
"""
import argparse
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c13_banc_commun as cc  # noqa: E402
import c13_banc_candidats as cd  # noqa: E402

bc = cc.bc
FICHIER = cc.SORTIE / "essais_resolution.json"
RESOLUTIONS = [5, 8, 11]


_NATIF = {}


def cm_natif(nom_jeu, nom):
    """Résolution d'origine (cm/px) d'une image de réglage : 5 x facteur de tuiles.csv (facteur = cm d'origine / 5 ;
    banano_dense : 0,5505 pour 2,74 cm/px). MM (ReforesTree, orthomosaïques d'environ 2 cm) : 2. val_negatifs vient
    d'images d'environ 10 à 12 cm/px (facteur 2,03 à 2,37) : un candidat « résolution » y prend sa branche grossière."""
    if nom_jeu == "mm":
        return 2.0
    if not _NATIF:
        import pandas as pd
        for d in (bc.D, bc.D6):
            T = pd.read_csv(d / "tuiles.csv", usecols=["image_path", "ensemble", "facteur"])
            T = T[T.ensemble.isin(["val_dense_bv", "val_plantain", "val_jeunes", "val_negatifs", "val_espace"])]
            _NATIF.update(dict(zip(T.image_path, 5.0 * T.facteur)))
    return _NATIF[nom]


class ContexteR(bc.Contexte):
    """degr : 5 = image du réglage telle quelle (résolution d'origine lue dans tuiles.csv) ; 8 / 11 = image dégradée
    (résolution d'origine simulée = degr). ctx.cm = résolution d'origine (ce que la chaîne lit dans le GeoTIFF)."""

    def __init__(self, nom_jeu, item, cm=5):
        super().__init__(nom_jeu, item)
        self.degr = cm
        self.cm = cm if cm != 5 else cm_natif(nom_jeu, item["nom"])

    def carte(self, modele, variante="base"):
        if self.degr == 5:
            if variante == "sh":
                if self.cm < 8:
                    variante = "base"                # image fine : pas de renforcement
                else:
                    return cc.carte_cache(modele, "sh", self.nom_jeu, self.nom)   # image grossière d'origine renforcée
            return super().carte(modele, variante)
        v = {"base": f"d{self.degr}", "sh": f"d{self.degr}sh"}[variante]
        return cc.carte_cache(modele, v, self.nom_jeu, self.nom)


def mesurer_jeu(candidat, nom_jeu, items, cm):
    """Copie de bc.mesurer_jeu avec un contexte qui connaît la résolution d'origine."""
    acc = {s: [0, 0, 0, 0] for s in bc.SEUILS}
    reels = arbres = 0
    for e in items:
        xy, sc = candidat(ContexteR(nom_jeu, e, cm))
        xy, sc = np.asarray(xy, "float64").reshape(-1, 2), np.asarray(sc, "float64")
        if e["zone"] is not None:
            x0, y0, x1, y1 = e["zone"]
            g = (xy[:, 0] >= x0) & (xy[:, 0] <= x1) & (xy[:, 1] >= y0) & (xy[:, 1] <= y1)
        else:
            g = bc.dans_masque(xy, e["masque"])
        xy, sc = xy[g], sc[g]
        reels += len(e["pts"]); arbres += e["n_autres"]
        for s in bc.SEUILS:
            d = xy[sc >= s]
            acc[s][3] += len(d)
            if nom_jeu == "neg":
                acc[s][1] += len(d)
            else:
                for k, v in enumerate(bc.compter(d, e["pts"], e["ign"])):
                    acc[s][k] += v
    res = {}
    for s, (vp, fp, fn, det) in acc.items():
        if nom_jeu == "neg":
            res[str(s)] = dict(fp=fp, arbres=arbres, taux=fp / max(arbres, 1))
        else:
            p, r, f = bc.prf(vp, fp, fn)
            res[str(s)] = dict(vp=vp, fp=fp, fn=fn, p=p, r=r, f1=f, detectes=det, reels=reels,
                               err_compte=abs(det / reels - 1) if reels else float("nan"))
    return res


# ------------------------------------------------------------------------------------------------ fabriques CB2
def f_par_resolution(cinq=("seul", {"modele": "v5"}), grossier=None, cm_bascule=8, beta=0.0, beta_par_cm=None):
    """Sous-candidat `cinq` pour les images d'origine plus fines que cm_bascule, `grossier` (défaut : `cinq`) sinon.
    beta : décalage ajouté aux scores des images grossières (seuil abaissé d'autant) ; beta_par_cm : décalage
    proportionnel, beta_par_cm x (cm - 5)."""
    f5 = cd.construire(*cinq)
    fg = cd.construire(*grossier) if grossier else f5

    def f(ctx):
        cm = getattr(ctx, "cm", 5)
        if cm < cm_bascule:
            return f5(ctx)
        xy, sc = fg(ctx)
        b = beta + (beta_par_cm * (cm - 5) if beta_par_cm else 0.0)
        return xy, np.asarray(sc, "float64") + b
    return f


def f_par_resolution_dens(cinq=("seul", {"modele": "v5"}), grossier=None, cm_bascule=8, beta_par_cm=0.0, dens_min=200,
                          smin=0.15, k=bc.K_PICS):
    """Comme par_resolution, mais le seuil n'est abaissé sur une image grossière que si elle porte une plantation :
    densité des pics du v5 (>= smin) d'au moins dens_min par hectare. Sinon : v5 tel quel."""
    f5 = cd.construire(*cinq)
    fg = cd.construire(*grossier) if grossier else f5

    def f(ctx):
        cm = getattr(ctx, "cm", 5)
        if cm < cm_bascule:
            return f5(ctx)
        c5 = ctx.carte("v5")
        xy5, _ = bc.pics(c5, k, smin)
        ha = c5.size * bc.STRIDE ** 2 * 0.05 ** 2 / 1e4
        if len(xy5) < 5 or len(xy5) / ha < dens_min:
            return bc.pics(c5, k)
        xy, sc = fg(ctx)
        return xy, np.asarray(sc, "float64") + beta_par_cm * (cm - 5)
    return f


def f_seul_sh(modele="v5", k=bc.K_PICS):
    """v5 sur l'image renforcée (masque flou) ; à 5 cm, image d'origine."""
    return lambda ctx: bc.pics(ctx.carte(modele, "sh"), k)


def f_max_sh(modele="v5", k=bc.K_PICS):
    """Maximum des cartes du v5 sur l'image telle quelle et renforcée."""
    return lambda ctx: bc.pics(np.maximum(ctx.carte(modele), ctx.carte(modele, "sh")), k)


cd.FABRIQUES.update(par_resolution=f_par_resolution, seul_sh=f_seul_sh, max_sh=f_max_sh, par_resolution_dens=f_par_resolution_dens)
cd.ca.FABRIQUES.update(par_resolution=f_par_resolution, seul_sh=f_seul_sh, max_sh=f_max_sh, par_resolution_dens=f_par_resolution_dens)


# ------------------------------------------------------------------------------------------------ listes
FAM = "A résolution"
V5 = ("seul", {"modele": "v5"})


def liste_cb2a():
    """CB2, première passe (écrite à 23:54 avant toute mesure dégradée)."""
    r = {"v5": ("référence", "seul", {"modele": "v5"})}
    for b in (0.05, 0.10, 0.15):
        r[f"CB2_v5_beta{b:.2f}"] = (FAM, "par_resolution", dict(beta_par_cm=b / 6))           # -b au seuil à 11 cm
    r["CB2_v5_sh"] = (FAM, "par_resolution", dict(grossier=["seul_sh", {"modele": "v5"}]))
    r["CB2_v5_maxsh"] = (FAM, "par_resolution", dict(grossier=["max_sh", {"modele": "v5"}]))
    for b in (0.05, 0.10):
        r[f"CB2_v5_sh_beta{b:.2f}"] = (FAM, "par_resolution", dict(grossier=["seul_sh", {"modele": "v5"}], beta_par_cm=b / 6))
    for b in (0.0, 0.05, 0.10):
        r[f"CB2_moy345_beta{b:.2f}"] = (FAM, "par_resolution",
                                        dict(grossier=["melange", {"membres": ["v3", "v4", "v5"], "mode": "moyenne"}], beta_par_cm=b / 6))
    r["CB2_E5p90b_partout"] = ("A aiguillage (nuit 12/11)", "aiguillage_p90",
                               dict(tau=0.55, decalage=0.1, petit_spec=["melange", {"membres": ["v3", "v4"], "mode": "moyenne"}]))
    import c13_banc_listes as li
    for nom in ("CB1_npet30_dens200_acc0.05_c", "CB13_trous_b0.20_reseau"):    # choix CB1 et CB3, pour information
        r[nom] = {**li.liste_cb1d(), **li.liste_cb3b()}[nom]
    return r


def _cb13():
    import c13_banc_listes as li
    fam, fab, reg = li.liste_cb3b()["CB13_trous_b0.20_reseau"]
    return [fab, reg]


def liste_cb2b():
    """CB2, deuxième passe (écrite à 00:36 avant mesure). Constat de cb2a : un candidat qui rend le v5 tel quel à 5 cm prend
    le seuil 0,20 par la règle 5.3 (celui du v5 seul) et perd alors le plantain à 5 cm. La branche 5 cm devient donc le
    choix CB3 (`CB13_trous_b0.20_reseau`, seuil 0,30) ; à 8 cm et plus : branche grossière avec seuil abaissé de b à 11 cm
    (b x (cm - 5) / 6)."""
    r = {}
    C = _cb13()
    for b in (0.10, 0.15, 0.20):
        r[f"CB2_cb13_v5_b{b:.2f}"] = (FAM, "par_resolution", dict(cinq=C, grossier=["seul", {"modele": "v5"}], beta_par_cm=b / 6))
        r[f"CB2_cb13_moy345_b{b:.2f}"] = (FAM, "par_resolution",
                                         dict(cinq=C, grossier=["melange", {"membres": ["v3", "v4", "v5"], "mode": "moyenne"}], beta_par_cm=b / 6))
    for b in (0.10, 0.15):
        r[f"CB2_cb13_cb13_b{b:.2f}"] = (FAM, "par_resolution", dict(cinq=C, grossier=C, beta_par_cm=b / 6))
        r[f"CB2_cb13_v5sh_b{b:.2f}"] = (FAM, "par_resolution", dict(cinq=C, grossier=["seul_sh", {"modele": "v5"}], beta_par_cm=b / 6))
    return r


def liste_cb2c():
    """CB2, troisième passe (écrite à 00:42 avant mesure) : le seuil n'est abaissé sur une image grossière que si elle
    porte une plantation (densité des pics du v5 >= 200 ou 400 /ha) ; sinon v5 tel quel. But : ne pas toucher les tuiles
    sans bananier, qui sont elles-mêmes grossières (10 à 12 cm)."""
    r = {}
    C = _cb13()
    G = {"moy345": ["melange", {"membres": ["v3", "v4", "v5"], "mode": "moyenne"}], "v5": ["seul", {"modele": "v5"}]}
    for g, spec in G.items():
        for b in (0.15, 0.20):
            for d in (200, 400):
                r[f"CB2_cb13_{g}_b{b:.2f}_dens{d}"] = (FAM, "par_resolution_dens",
                                                       dict(cinq=C, grossier=spec, beta_par_cm=b / 6, dens_min=d))
    return r


def liste_cb2d():
    """CB2, quatrième passe (écrite à 01:01, après avoir vu le réglage dégradé des variantes « image renforcée » mais
    avant leur mesure sur val_negatifs) : branche grossière = v5 sur image renforcée, seuil abaissé de b à 11 cm,
    avec la porte « plantation » (densité des pics du v5 >= 200 /ha) ; b = 0,10 / 0,15 / 0,20."""
    r = {}
    C = _cb13()
    for b in (0.10, 0.15, 0.20):
        r[f"CB2_cb13_v5sh_b{b:.2f}_dens200"] = (FAM, "par_resolution_dens",
                                               dict(cinq=C, grossier=["seul_sh", {"modele": "v5"}], beta_par_cm=b / 6, dens_min=200))
    return r


def liste_cb2e():
    """CB2, cinquième passe (écrite le 14/11 à 13:12 avant mesure ; demande les cartes v3 et v4 sur image renforcée) :
    branche grossière = moyenne des cartes v3 + v4 + v5 calculées sur l'image renforcée, seuil abaissé b = 0,15 / 0,20
    à 11 cm, avec ou sans la porte « plantation » (densité >= 200 /ha)."""
    r = {}
    C = _cb13()
    M = ["melange", {"membres": ["v3", "v4", "v5"], "mode": "moyenne", "variante": "sh"}]
    for b in (0.15, 0.20):
        r[f"CB2_cb13_moy345sh_b{b:.2f}"] = (FAM, "par_resolution", dict(cinq=C, grossier=M, beta_par_cm=b / 6))
        r[f"CB2_cb13_moy345sh_b{b:.2f}_dens200"] = (FAM, "par_resolution_dens",
                                                   dict(cinq=C, grossier=M, beta_par_cm=b / 6, dens_min=200))
    return r


LISTES = dict(cb2a=liste_cb2a, cb2b=liste_cb2b, cb2c=liste_cb2c, cb2d=liste_cb2d, cb2e=liste_cb2e)

_ITEMS = {}


def _tache(t):
    nom, fab, reg, j, cm = t
    if j not in _ITEMS:
        _ITEMS[j] = cc.jeu(j)
    try:
        return nom, j, cm, mesurer_jeu(cd.construire(fab, reg), j, _ITEMS[j], cm)
    except FileNotFoundError:
        return nom, j, cm, None                          # carte pas encore en cache : mesure reportée


def charger():
    return json.loads(FICHIER.read_text(encoding="utf-8")) if FICHIER.exists() else {}


def resume(E):
    """Pour chaque candidat : seuil 5.3 à 5 cm, puis moyennes à 8 et 11 cm à ce seuil ; statut « finaliste résolution »."""
    def ls(e, cm):
        m = {j: {float(s): v for s, v in e["res"][f"{j}@{cm}"].items()} for j in cc.REGLAGE}
        if cm == 5:
            m["neg"] = {float(s): v for s, v in e["res"]["neg@5"].items()}
        return cc.lignes(m, neg="neg" if cm == 5 else "-")
    v5 = E["v5"]
    cms = [cm for cm in RESOLUTIONS if all(f"{j}@{cm}" in v5["res"] for j in cc.REGLAGE)]
    ref = {cm: [l for l in ls(v5, cm) if l["seuil"] == 0.30][0] for cm in cms}
    out = []
    for nom, e in E.items():
        if any(f"{j}@{cm}" not in e["res"] for j in cc.REGLAGE for cm in cms) or "neg@5" not in e["res"]:
            continue
        b = cc.choisir(ls(e, 5))
        if b is None:
            continue
        s = b["seuil"]
        par = {cm: [l for l in ls(e, cm) if l["seuil"] == s][0] for cm in cms}
        st = cc.statut(b, ref[5])
        fin_r = bool(par[11]["moyenne"] >= ref[11]["moyenne"] + 0.030 and b["moyenne"] >= ref[5]["moyenne"] - 0.005
                     and st["c2"] and st["c3"] and st["c4"])
        out.append(dict(nom=nom, famille=e["famille"], seuil=s, fin_res=fin_r, fin_53=st["finaliste"], fp_neg=b["fp_neg"],
                        **{f"moy@{cm}": par[cm]["moyenne"] for cm in cms},
                        **{f"f1_{j}@{cm}": par[cm][f"f1_{j}"] for j in cc.REGLAGE for cm in cms},
                        **{f"err@{cm}": par[cm]["err_compte"] for cm in cms}))
    out.sort(key=lambda d: -d.get("moy@11", 0))
    return out, ref, cms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--liste", nargs="*", default=[])
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--cm", nargs="+", type=int, default=RESOLUTIONS)
    a = ap.parse_args()
    E = charger()
    for l in a.liste:
        for nom, (fam, fab, reg) in LISTES[l]().items():
            E.setdefault(nom, dict(famille=fam, fabrique=fab, reglages=reg, res={}))
    taches = [(n, e["fabrique"], e["reglages"], j, cm) for n, e in E.items() for cm in a.cm for j in cc.REGLAGE
              if f"{j}@{cm}" not in e["res"] and (cm == 5 or all(cc.chemin_cache(m, f"d{cm}", j).with_suffix(".json").exists()
                                                                   for m in ("v5",)))]
    taches += [(n, e["fabrique"], e["reglages"], "neg", 5) for n, e in E.items() if "neg@5" not in e["res"]]
    t0 = time.time()
    if taches:
        with Pool(a.procs) as p:
            for k, (n, j, cm, r) in enumerate(p.imap_unordered(_tache, taches, chunksize=1)):
                if r is None:
                    continue
                E[n]["res"][f"{j}@{cm}"] = r
                if k % 20 == 19:
                    FICHIER.write_text(json.dumps(E), encoding="utf-8")
        FICHIER.write_text(json.dumps(E), encoding="utf-8")
    out, ref, cms = resume(E)
    print(f"{time.strftime('%H:%M')} {len(taches)} mesures en {time.time() - t0:.0f} s ; {len(E)} candidats")
    print("v5 à 0,30 : " + " | ".join(f"{cm} cm moy {ref[cm]['moyenne']:.4f} (" + " ".join(f"{ref[cm]['f1_' + j]:.3f}" for j in cc.REGLAGE)
                                     + f") err {ref[cm]['err_compte']:.3f}" for cm in cms))
    for d in out:
        print(f"{d['nom']:34s} s{d['seuil']:.2f} " + " | ".join(
            f"{cm}: {d[f'moy@{cm}']:.4f} (" + " ".join(f"{d[f'f1_{j}@{cm}']:.3f}" for j in cc.REGLAGE) + f") e{d[f'err@{cm}']:.3f}"
            for cm in cms) + f" fp{d['fp_neg']} {'FIN_RES' if d['fin_res'] else ''} {'FIN_53' if d['fin_53'] else ''}")
    (cc.SORTIE / "tableau_resolution.json").write_text(json.dumps(dict(reference=ref, lignes=out), indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
