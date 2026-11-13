#!/usr/bin/env python3
"""M-analyste (nuit du 12/11) : table par photo des 4 jeux de réglage (validation Tanzanie, TDTU, PSFD, Éthiopie).

Réponses de la chaîne installée et des finalistes F1 / F3 de M-banc (fonctions de scripts/m12_banc_finalistes.py,
importées telles quelles), probabilités en cache, p_loin, et mesures simples sur chaque photo (taille, poids du fichier,
qualité JPEG estimée, netteté, luminosité, parts de vert / jaune / brun). Aucun réseau n'est lancé. Juges jamais lus.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_analyse_table.py
Sortie : out/maladies/analyse/table_reglage.csv
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
cv2.setNumThreads(2)
import m12_banc_commun as B  # noqa: E402
import m12_banc_finalistes as F  # noqa: E402
from fieldscan.modules import maladies  # noqa: E402

SORTIE = RACINE / "out/maladies/analyse"
SORTIE.mkdir(parents=True, exist_ok=True)
MORC = RACINE / "out/maladies/nuit_1112/banc/kaggle_morceaux"

LUM = np.array([16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55, 14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22,
                29, 51, 87, 80, 62, 18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92, 49, 64, 78, 87, 103,
                121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99], float)


def qualite_jpeg(im):
    q = getattr(im, "quantization", None)
    if not q or 0 not in q:
        return np.nan
    t = np.asarray(q[0], float)
    best, bq = 1e18, np.nan
    for qual in range(1, 101):
        s = 5000 / qual if qual < 50 else 200 - 2 * qual
        ref = np.clip(np.floor((LUM * s + 50) / 100), 1, 255)
        d = abs(ref.sum() - t.sum())
        if d < best:
            best, bq = d, qual
    return bq


def mesures_image(chemin):
    out = dict(larg=np.nan, haut=np.nan, octets=np.nan, qjpeg=np.nan, nettete=np.nan, lum=np.nan, contraste=np.nan,
               sat=np.nan, f_vert=np.nan, f_jaune=np.nan, f_brun=np.nan, f_sombre=np.nan, f_gris=np.nan)
    try:
        out["octets"] = os.path.getsize(chemin)
        with Image.open(chemin) as im:
            out["larg"], out["haut"] = im.size
            out["qjpeg"] = qualite_jpeg(im)
            a = np.asarray(im.convert("RGB"))
    except Exception:
        return out
    h, w = a.shape[:2]
    s = 256 / max(h, w)
    if s < 1:
        a = cv2.resize(a, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(a, cv2.COLOR_RGB2HSV)
    H, S, V = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    out["nettete"] = float(cv2.Laplacian(g, cv2.CV_64F).var())
    out["lum"], out["contraste"], out["sat"] = float(g.mean()), float(g.std()), float(S.mean())
    vert = (H >= 30) & (H <= 90) & (S >= 40) & (V >= 40)
    jaune = (H >= 18) & (H < 30) & (S >= 60) & (V >= 80)
    brun = ((H < 18) | (H > 165)) & (S >= 40) & (V >= 30) & (V < 200)
    sombre = V < 40
    gris = (S < 40) & (V >= 40)
    n = float(H.size)
    for k, m in dict(f_vert=vert, f_jaune=jaune, f_brun=brun, f_sombre=sombre, f_gris=gris).items():
        out[k] = float(m.sum() / n)
    return out


def main():
    jeux = B.charger_reglage()
    lignes = []
    for j, d in jeux.items():
        n = len(d["chemin"])
        p512 = pd.read_csv(MORC / f"p512_{j}.csv")
        assert list(p512.chemin) == list(d["chemin"]), j
        P512 = p512[["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]].to_numpy("float64")
        z = np.load(MORC / f"morceaux_{j}.npz")
        G2 = z["g2"].astype("float64")
        assert G2.shape[0] == n
        rep = {k: F.repondre(d["P10"], d["Pso"], d["Pv2"], d["p_loin"], c, P512, G2) for k, c in F.CANDIDATS.items()}
        # P(saine) du lecteur proche de chaque candidat (avant décision)
        ps = {}
        for k, c in F.CANDIDATS.items():
            P10 = F.lecture_v10b(d["P10"], c, P512, G2)
            P = P10 if c["poids"] is None else F.geo(P10, d["Pso"], d["Pv2"], c["poids"])
            ps[k] = P[:, 0]
        # réponses de chaque modèle seul (seuils propres) pour l'accord
        r_v10b = B.decider_v10b(d["P10"])
        r_so = maladies.decider_convnext(d["Pso"], B.M_SOUPE)[0]
        r_v2 = d["r_loin"]
        for i in range(n):
            L = dict(jeu=j, chemin=d["chemin"][i], vraie=d["vraie"][i], malade=bool(d["malade"][i]),
                     p_loin=float(d["p_loin"][i]), loin=bool(d["loin"][i]),
                     ps_v10b=d["P10"][i, 0], ps_soupe=d["Pso"][i, 0], ps_v2=d["Pv2"][i, 0], ps_v10b512=P512[i, 0],
                     pa_v10b=d["P10"][i, 3], pbs_v10b=d["P10"][i, 1], pfu_v10b=d["P10"][i, 2],
                     pm_g2_max=float((1 - G2[i, :, 0]).max()), pm_g2_min=float((1 - G2[i, :, 0]).min()),
                     r_v10b_seule=r_v10b[i], r_soupe_seule=r_so[i], r_v2_seule=r_v2[i])
            for k in F.CANDIDATS:
                L[f"r_{k}"] = rep[k][i]
                L[f"ps_{k}"] = ps[k][i]
            lignes.append(L)
    t = pd.DataFrame(lignes)
    for k in list(F.CANDIDATS) + ["v10b_seule", "soupe_seule", "v2_seule"]:
        t[f"al_{k}"] = t[f"r_{k}"].isin(B.ALERTE)
    # contrôle : retrouver les chiffres publiés
    for j, (a, b_, c, e) in B.REFERENCE.items():
        s = t[t.jeu == j]
        assert ((s.malade & ~s.al_installee).sum(), (~s.malade & s.al_installee).sum()) == (a, c), j
    print("référence retrouvée")
    f1 = {j: ((t[(t.jeu == j)].malade & ~t[(t.jeu == j)].al_F1_trois_morceaux2x2).sum(),
              (~t[(t.jeu == j)].malade & t[(t.jeu == j)].al_F1_trois_morceaux2x2).sum()) for j in B.REGLAGE}
    print("F1 :", f1)
    # mesures d'image
    mes = []
    for k, c in enumerate(t.chemin):
        mes.append(mesures_image(B.fichier(c)))
        if k % 1000 == 0:
            print(k, flush=True)
    t = pd.concat([t, pd.DataFrame(mes)], axis=1)
    t["octets_par_px"] = t.octets / (t.larg * t.haut)
    t.to_csv(SORTIE / "table_reglage.csv", index=False)
    print("écrit", SORTIE / "table_reglage.csv", len(t))


if __name__ == "__main__":
    main()
