#!/usr/bin/env python3
"""M-analyste (nuit du 12/11) : planches d'images pour vérifier à l'œil chaque conclusion (réglage seulement).

Chaque vignette porte : jeu, classe vraie, P(saine) v10b (installée), P(saine) du lecteur F1, p_loin, et la réponse.
Tirage aléatoire graine 0 quand le groupe dépasse la taille de la planche.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_analyse_planches.py [groupe ...]
Sortie : out/maladies/analyse/planches/<groupe>.jpg
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageOps

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402

SORTIE = RACINE / "out/maladies/analyse/planches"
SORTIE.mkdir(parents=True, exist_ok=True)
T = pd.read_csv(RACINE / "out/maladies/analyse/table_reglage.csv")
K1 = "F1_trois_morceaux2x2"
COURT = {"a_verifier": "à vérif.", "malade_non_identifiee": "non ident.", "cercosporiose_noire": "Sigatoka",
         "fusariose": "fusariose", "saine": "saine"}


def planche(nom, sub, n=48, col=8, cote=200, tri=None, legende=None):
    if len(sub) == 0:
        print(nom, "vide")
        return
    if len(sub) > n:
        sub = sub.sample(n, random_state=0)
    if tri:
        sub = sub.sort_values(tri)
    lignes = (len(sub) + col - 1) // col
    H = cote + 34
    im = Image.new("RGB", (col * cote, lignes * H + 22), "white")
    dr = ImageDraw.Draw(im)
    dr.text((4, 4), f"{nom} ({len(sub)} photos)", fill="black")
    for k, (_, r) in enumerate(sub.iterrows()):
        x, y = (k % col) * cote, 22 + (k // col) * H
        try:
            with Image.open(B.fichier(r.chemin)) as v:
                v = ImageOps.exif_transpose(v).convert("RGB")
                v.thumbnail((cote - 4, cote - 4))
                im.paste(v, (x + 2 + (cote - 4 - v.width) // 2, y + 2 + (cote - 4 - v.height) // 2))
        except Exception as e:
            dr.text((x + 4, y + 40), str(e)[:30], fill="red")
        t1 = f"{r.jeu[:4]} {str(r.vraie)[:11]} {int(r.larg)}x{int(r.haut)}"
        t2 = f"v10b {r.ps_v10b:.2f} F1 {r[f'ps_{K1}']:.2f} loin {r.p_loin:.2f}"
        if legende:
            t2 = legende(r)
        dr.text((x + 3, y + cote), t1, fill="black")
        dr.text((x + 3, y + cote + 12), t2, fill="navy")
        rep = f"inst: {COURT.get(r.r_installee, r.r_installee)} / F1: {COURT.get(r[f'r_{K1}'], r[f'r_{K1}'])}"
        dr.text((x + 3, y + cote + 23), rep[:34], fill="darkred")
    im.save(SORTIE / f"{nom}.jpg", quality=88)
    print("écrit", nom, len(sub))


M, S = T[T.malade], T[~T.malade]
a1, ai = T[f"al_{K1}"], T.al_installee
GROUPES = {
    "ratees_F1_psfd": lambda: planche("ratees_F1_psfd", T[(T.jeu == "psfd") & T.malade & ~a1], n=64, tri="lum"),
    "ratees_F1_ethiopie": lambda: planche("ratees_F1_ethiopie", T[(T.jeu == "ethiopie") & T.malade & ~a1], n=64),
    "ratees_F1_tdtu": lambda: planche("ratees_F1_tdtu", T[(T.jeu == "tdtu") & T.malade & ~a1]),
    "vues_F1_psfd_temoin": lambda: planche("vues_F1_psfd_temoin", T[(T.jeu == "psfd") & T.malade & a1], n=32),
    "vues_F1_ethiopie_xantho_temoin": lambda: planche("vues_F1_ethiopie_xantho_temoin",
                                                      T[(T.jeu == "ethiopie") & (T.vraie == "xanthomonas") & a1], n=32),
    "ratees_installee_validation": lambda: planche("ratees_installee_validation", T[(T.jeu == "validation") & T.malade & ~ai]),
    "rattrapees_F1_tdtu": lambda: planche("rattrapees_F1_tdtu", T[(T.jeu == "tdtu") & T.malade & ~ai & a1]),
    "rattrapees_F1_ethiopie": lambda: planche("rattrapees_F1_ethiopie", T[(T.jeu == "ethiopie") & T.malade & ~ai & a1]),
    "perdues_F1_ethiopie": lambda: planche("perdues_F1_ethiopie", T[(T.jeu == "ethiopie") & T.malade & ai & ~a1]),
    "fa_F1_tdtu_loin": lambda: planche("fa_F1_tdtu_loin", T[(T.jeu == "tdtu") & ~T.malade & a1 & T.loin]),
    "fa_F1_tdtu_proche": lambda: planche("fa_F1_tdtu_proche", T[(T.jeu == "tdtu") & ~T.malade & a1 & ~T.loin]),
    "saines_sans_alerte_tdtu": lambda: planche("saines_sans_alerte_tdtu", T[(T.jeu == "tdtu") & ~T.malade & ~a1]),
    "fa_F1_ethiopie": lambda: planche("fa_F1_ethiopie", T[(T.jeu == "ethiopie") & ~T.malade & a1]),
    "saines_sans_alerte_ethiopie": lambda: planche("saines_sans_alerte_ethiopie", T[(T.jeu == "ethiopie") & ~T.malade & ~a1], n=32),
    "fa_F1_validation": lambda: planche("fa_F1_validation", T[(T.jeu == "validation") & ~T.malade & a1], n=64, tri=f"ps_{K1}"),
    "fa_F1_nouvelles_tdtu": lambda: planche("fa_F1_nouvelles_tdtu", T[(T.jeu == "tdtu") & ~T.malade & a1 & ~ai]),
}

def groupes_psfd():
    c = pd.read_csv(RACINE / "out/maladies/analyse/psfd_copies.csv")
    gros = c["dino_0.95"].value_counts()
    gros = gros[gros > 1].index[:6]
    sub = pd.concat([c[c["dino_0.95"] == g].head(8) for g in gros])
    sub = T.merge(sub[["chemin", "dino_0.95"]], on="chemin")
    sub["ordre"] = sub["dino_0.95"].map({g: i for i, g in enumerate(gros)})
    planche("psfd_groupes_quasi_copies", sub.sort_values(["ordre", "chemin"]), n=48,
            legende=lambda r: f"groupe {int(r['dino_0.95'])} v10b {r.ps_v10b:.2f} F1 {r[f'ps_{K1}']:.2f}")


GROUPES["psfd_groupes_quasi_copies"] = groupes_psfd

if __name__ == "__main__":
    for g in (sys.argv[1:] or GROUPES):
        GROUPES[g]()
