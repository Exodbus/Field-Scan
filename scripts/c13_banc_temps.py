#!/usr/bin/env python3
"""Temps par tuile (processeur, 3 fils onnxruntime) d'un candidat de la nuit du 13/11, calculé de bout en bout sur des
images de RÉGLAGE : passages de réseau (calculés ici, pas lus dans le cache) + post-traitement du candidat.
Machine partagée : chiffres indicatifs ; le v5 est mesuré dans le même passage pour donner un rapport.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c13_banc_temps.py --candidats v5 CB1_npet30_dens200_acc0.05_c
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c13_banc_commun as cc  # noqa: E402
import c13_banc_candidats as cd  # noqa: E402
import c13_banc_resolution  # noqa: E402,F401  (fabriques CB2)

bc = cc.bc


class CtxDirect:
    """Contexte qui calcule les cartes à la demande (et mesure le temps des réseaux)."""

    def __init__(self, img, sessions, chrono):
        self.img, self.sessions, self.cartes, self.chrono, self.cm = img, sessions, {}, chrono, 5

    def carte(self, modele, variante="base"):
        assert variante in ("base", "sh")
        if variante == "sh" and self.cm < 8:
            variante = "base"                         # image fine : pas de renforcement (comme ContexteR)
        cle = (modele, variante)
        if cle not in self.cartes:
            t0 = time.perf_counter()
            img = self.img
            if variante == "sh":
                import c13_banc_degrade as dg
                img = dg.renforcer(img, self.cm)
            self.cartes[cle] = bc.cartes_image(self.sessions[modele], img, "base")["base"]
            self.chrono["reseaux"] += time.perf_counter() - t0
        return self.cartes[cle]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidats", nargs="+", required=True)
    ap.add_argument("--n", type=int, default=15, help="images par jeu")
    a = ap.parse_args()
    E = {}
    for f in ("essais.json", "essais_resolution.json"):
        p = cc.SORTIE / f
        if p.exists():
            E.update({k: v for k, v in json.loads(p.read_text(encoding="utf-8")).items() if k not in E})
    c13d = cc.RACINE / "modeles/comptage_nuit_1311/centres_5cm_c13d.onnx"      # spécialiste de C-entraîneur (famille C)
    if c13d.exists():
        bc.MODELES["c13d"] = c13d
    sessions = {m: bc.session(m, cc.FILS) for m in bc.MODELES if m in ("v5", "v3", "v4", "c13d")}
    items = []
    for j in ("dense", "plantain", "btd_val", "neg"):
        it = cc.jeu(j)
        items += [(j, e) for e in it[:: max(1, len(it) // a.n)][: a.n]]
    imgs = [(j, e, bc.lire(e["chemin"])) for j, e in items]
    for j, e, img in imgs[:2]:                       # échauffement
        w = CtxDirect(img, sessions, {"reseaux": 0.0}); w.carte("v5")
    res = {}
    for nom in a.candidats:
        f = cd.construire(E[nom]["fabrique"], E[nom]["reglages"])
        par, ident = {}, []
        for j, e, img in imgs:
            ch = {"reseaux": 0.0}
            t0 = time.perf_counter()
            ctx = CtxDirect(img, sessions, ch)
            ctx.nom_jeu, ctx.nom = j, e["nom"]
            ctx.cm = c13_banc_resolution.cm_natif(j, e["nom"])      # résolution d'origine (val_negatifs : 10 à 12 cm)
            xy, sc = f(ctx)
            t = time.perf_counter() - t0
            # contrôle : mêmes points qu'avec les cartes en cache du banc (au seuil 0,30)
            xc, scc = f(c13_banc_resolution.ContexteR(j, e, 5))
            a_, b_ = np.asarray(xy)[np.asarray(sc) >= 0.30], np.asarray(xc)[np.asarray(scc) >= 0.30]
            ident.append(len(a_) == len(b_) and (len(a_) == 0 or np.allclose(np.sort(a_, 0), np.sort(b_, 0))))
            ha = img.shape[0] * img.shape[1] * 0.05 ** 2 / 1e4
            par.setdefault(j, []).append((t, ch["reseaux"], ha))
        res[nom] = {j: dict(s_par_tuile=float(np.mean([x[0] for x in v])), s_par_ha=float(sum(x[0] for x in v) / sum(x[2] for x in v)),
                            part_reseaux=float(sum(x[1] for x in v) / sum(x[0] for x in v))) for j, v in par.items()}
        tot = [x for v in par.values() for x in v]
        res[nom]["identiques_au_cache"] = f"{sum(ident)} / {len(ident)}"
        res[nom]["tout"] = dict(s_par_tuile=float(np.mean([x[0] for x in tot])), s_par_ha=float(sum(x[0] for x in tot) / sum(x[2] for x in tot)))
        print(nom, json.dumps({k: ({kk: round(vv, 3) for kk, vv in v.items()} if isinstance(v, dict) else v) for k, v in res[nom].items()}), flush=True)
    p = cc.SORTIE / "temps.json"
    old = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    old.update({k: dict(v, heure=time.strftime("%H:%M")) for k, v in res.items()})
    p.write_text(json.dumps(old, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
