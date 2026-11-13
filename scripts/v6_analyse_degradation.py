#!/usr/bin/env python3
"""Robustesse à l'échelle de l'image de l'aiguillage p90 (agent C-analyste, cycle 3, nuit du 12 au 13 novembre 2026).

Images de réglage (dense, plantain, jeunes, MM) dégradées comme si elles venaient d'un capteur à c cm/px puis ramenées
à 5 cm comme le fait scripts/v6_prosp_preparer.py (mode évaluation : resize LANCZOS, JPEG qualité 95) :
    5 cm -> c cm (LANCZOS) -> 5 cm, taille d'origine (LANCZOS) -> JPEG 95 aller-retour.
Puis : v5 (ONNX installé) ; aiguillage p90 et branches recopiés de f_aiguillage_p90 (scripts/v6_banc_candidats.py,
importé tel quel) ; les cartes v3 / v4 / v6b ne sont calculées que pour les images aiguillées. Mesure au seuil 0,30
comme le banc. Juges et test vierge jamais chargés.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/v6_analyse_degradation.py --cm 11 8 14 --fils 2
Sorties : out/comptage/analyse/degradation_images.csv (une ligne par image et résolution), degradation.md.
"""
import argparse
import io
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import v6_banc_commun as bc  # noqa: E402
import v6_banc_candidats as ca  # noqa: E402

SORTIE = RACINE / "out/comptage/analyse"
JEUX = ["dense", "plantain", "jeunes", "mm"]
SEUIL = 0.30
FINALISTES = {
    "E10_p90_v6b_v5_d0.1": ("aiguillage_p90", {"tau": 0.55, "decalage": 0.1, "petit_spec": ["seul", {"modele": "v6b"}]}),
    "E5p90b_moy34_v5_d0.1": ("aiguillage_p90", {"tau": 0.55, "decalage": 0.1,
                                                 "petit_spec": ["melange", {"membres": ["v3", "v4"], "mode": "moyenne"}],
                                                 "grand_spec": None}),
}


def degrader(img, cm):
    """img : tableau HxWx3 à 5 cm/px. Rend la même taille, comme une source à `cm` cm/px préparée par v6_prosp_preparer."""
    h, w = img.shape[:2]
    im = Image.fromarray(img)
    petit = im.resize((max(1, round(w * 5 / cm)), max(1, round(h * 5 / cm))), Image.LANCZOS)
    retour = petit.resize((w, h), Image.LANCZOS)
    tampon = io.BytesIO(); retour.save(tampon, format="JPEG", quality=95)
    return np.asarray(Image.open(io.BytesIO(tampon.getvalue())).convert("RGB"))


class Ctx:
    """Contexte minimal pour les fabriques du banc : cartes calculées à la demande sur l'image dégradée."""

    def __init__(self, img, sessions, compte):
        self.img, self.sessions, self.cartes, self.compte = img, sessions, {}, compte

    def carte(self, modele, variante="base"):
        assert variante == "base"
        if modele not in self.cartes:
            self.cartes[modele] = bc.cartes_image(self.sessions[modele], self.img, "base")["base"]
            self.compte[modele] = self.compte.get(modele, 0) + 1
        return self.cartes[modele]


def filtre(xy, e):
    if e["zone"] is not None:
        x0, y0, x1, y1 = e["zone"]
        return (xy[:, 0] >= x0) & (xy[:, 0] <= x1) & (xy[:, 1] >= y0) & (xy[:, 1] <= y1)
    return bc.dans_masque(xy, e["masque"])


def mesure(xy, sc, e):
    xy, sc = np.asarray(xy, "float64").reshape(-1, 2), np.asarray(sc, "float64")
    g = filtre(xy, e) if len(xy) else np.zeros(0, bool)
    d = xy[g][sc[g] >= SEUIL]
    vp, fp, fn = bc.compter(d, e["pts"], e["ign"])
    return vp, fp, fn, len(d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cm", nargs="+", type=float, default=[11, 8, 14])
    ap.add_argument("--fils", type=int, default=2)
    ap.add_argument("--jeux", nargs="+", default=JEUX)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sessions = {m: bc.session(m, a.fils) for m in ("v5", "v3", "v4", "v6b")}
    cands = {k: ca.construire(f, r) for k, (f, r) in FINALISTES.items()}
    sortie = SORTIE / "degradation_images.csv"
    deja = pd.read_csv(sortie) if sortie.exists() else pd.DataFrame()
    lignes = deja.to_dict("records")
    fait = {(r["cm"], r["jeu"], r["image"]) for r in lignes}
    for cm in a.cm:
        for j in a.jeux:
            items = bc.jeu(j)
            t0 = time.time()
            compte = {}
            for n, e in enumerate(items):
                if (cm, j, e["nom"]) in fait:
                    continue
                img = degrader(bc.lire(e["chemin"]), cm)
                ctx = Ctx(img, sessions, compte)
                _, sc5 = bc.pics(ctx.carte("v5"), bc.K_PICS, 0.15)
                p90 = float(np.quantile(sc5, 0.90)) if len(sc5) else float("nan")
                # p90 de l'image non dégradée (cache de C-banc, lecture seule)
                try:
                    _, s0 = bc.pics(bc.carte_cache("v5", "base", j, e["nom"]), bc.K_PICS, 0.15)
                    p90_0 = float(np.quantile(s0, 0.90)) if len(s0) else float("nan")
                except Exception:
                    p90_0 = float("nan")
                r = dict(cm=cm, jeu=j, image=e["nom"], p90=p90, p90_5cm=p90_0, n_pics=len(sc5),
                         aiguillee=bool(len(sc5) >= 1 and p90 < 0.55), annotes=len(e["pts"]))
                xy, sc = bc.pics(ctx.carte("v5"), bc.K_PICS)
                r.update({f"v5_{k}": v for k, v in zip(("vp", "fp", "fn", "det"), mesure(xy, sc, e))})
                for nom, f in cands.items():
                    xy, sc = f(ctx)
                    r.update({f"{nom}_{k}": v for k, v in zip(("vp", "fp", "fn", "det"), mesure(xy, sc, e))})
                lignes.append(r)
                if n % 20 == 0:
                    print(f"{time.strftime('%H:%M:%S')} {cm} cm {j} {n}/{len(items)} p90 {p90:.2f}", flush=True)
                    pd.DataFrame(lignes).to_csv(sortie, index=False)
            pd.DataFrame(lignes).to_csv(sortie, index=False)
            print(f"{time.strftime('%H:%M:%S')} {cm} cm {j} fini en {time.time() - t0:.0f} s ; cartes {compte}", flush=True)
    resumer(pd.DataFrame(lignes))


def resumer(D):
    out = ["# Aiguillage p90 sur images de réglage dégradées [M]\n",
           "`scripts/v6_analyse_degradation.py` ; seuil 0,30 ; F1 du jeu entier (somme des vp, fp, fn sur les images).\n",
           "| cm/px simulé | jeu | images | aiguillées (p90 < 0,55) | p90 médian (5 cm -> dégradé) | F1 v5 | F1 E10 (v6b) | écart | F1 E5p90b (v3+v4) | écart | dét./annotés v5 | E10 | E5p90b |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    noms = list(FINALISTES)
    for (cm, j), g in D.groupby(["cm", "jeu"], sort=True):
        f1 = {}
        rat = {}
        for m in ["v5"] + noms:
            vp, fp, fn, det = (g[f"{m}_{k}"].sum() for k in ("vp", "fp", "fn", "det"))
            f1[m] = bc.prf(vp, fp, fn)[2]; rat[m] = det / max(vp + fn, 1)
        out.append(f"| {cm:g} | {j} | {len(g)} | {g.aiguillee.sum()} ({g.aiguillee.mean():.0%}) | "
                   f"{np.nanmedian(g.p90_5cm):.2f} -> {np.nanmedian(g.p90):.2f} | {f1['v5']:.3f} | {f1[noms[0]]:.3f} | "
                   f"{f1[noms[0]] - f1['v5']:+.3f} | {f1[noms[1]]:.3f} | {f1[noms[1]] - f1['v5']:+.3f} | "
                   f"{rat['v5']:.2f} | {rat[noms[0]]:.2f} | {rat[noms[1]]:.2f} |")
    (SORTIE / "degradation.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--resumer":
        sys.stdout.reconfigure(encoding="utf-8")
        resumer(pd.read_csv(SORTIE / "degradation_images.csv"))
    else:
        main()
