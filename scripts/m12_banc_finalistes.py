#!/usr/bin/env python3
"""Finalistes de M-banc (nuit du 12/11) : décision de chaque candidat sur n'importe quel jeu de probabilités.

Entrée : fichiers .npy ou .csv de probabilités, dans l'ordre des photos :
  --v10b  (n, 4) saine, black_sigatoka, fusarium, autre   (modeles/maladies_binome/v10b)
  --soupe (n, 3) saine, black_sigatoka, fusarium          (modeles/maladies_soupe_v2_v8/poids)
  --v2    (n, 3) saine, black_sigatoka, fusarium          (modeles/maladies_binome/maladies_v2/poids)
  --loin  (n,)   P(photo prise de loin) de l'aiguilleur
  --v10b_512      (n, 4)    v10b lue en 512 px (candidat F2) ; facultatif
  --v10b_g2       (n, 4, 4) v10b sur les 4 morceaux 2 x 2 (candidat F1) ; facultatif
  Pour calculer ces deux lectures sur une liste de photos : option --photos liste.txt (un chemin par ligne) avec
  --calculer dossier_sortie : écrit p_v10b_512.npy et p_v10b_g2.npy (processeur : compter environ 10 s par photo ;
  sur Kaggle, reprendre scripts/m12_banc_kaggle_morceaux.py, même préparation).
  --verite (facultatif) fichier texte ou CSV avec une colonne « malade » (0/1) : affiche malades sans alerte et
           saines en alerte.
Un .csv est lu par colonnes p_saine, p_black_sigatoka, p_fusarium[, p_autre] (ou p_loin) ; un .npy tel quel.
Sortie : un CSV avec la réponse de chaque candidat (et de la chaîne installée) par photo.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_banc_finalistes.py --v10b p_v10b.npy \
        --soupe p_soupe.npy --v2 p_v2.npy --loin p_loin.npy [--verite verite.csv] --sortie reponses.csv
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
from fieldscan.modules import maladies  # noqa: E402
import m12_banc_commun as B  # noqa: E402

# Définition exacte des candidats. poids = (v10b, soupe, v2) de la moyenne géométrique ; None = v10b seule.
# seuil = seuil_confiance (règle B) de la décision v10b appliquée au lecteur proche ; les autres seuils sont ceux de
# modeles/maladies_binome/v10b/seuils.json. loin_ou = photo « loin » en alerte si la v2 OU le lecteur proche alerte.
# lecture = façon de lire la v10b avant le mélange : « 384 » (lecture installée), « 384+512 » (moyenne des
# probabilités 384 et 512 px), « g2_2fortes » (P(malade) = moyenne de celle de l'entière et de la moyenne des 2 plus
# fortes P(malade) des 4 morceaux 2 x 2 ; P(saine) remplacée, maladies gardant leurs proportions).
CANDIDATS = {
    "installee": dict(poids=None, seuil=B.M_V10B["seuil"], loin_ou=False, lecture="384"),
    "F1_trois_morceaux2x2": dict(poids=(1, 1, 1), seuil=0.70, loin_ou=True, lecture="g2_2fortes"),
    "F2_trois_384_512": dict(poids=(1, 1, 1), seuil=0.72, loin_ou=True, lecture="384+512"),
    "F3_trois": dict(poids=(1, 1, 1), seuil=0.74, loin_ou=True, lecture="384"),
    "reserve_geo_v10b_soupe_loin": dict(poids=(1, 1, 0), seuil=0.68, loin_ou=True, lecture="384"),
    # Famille C (13/11, 4 h) : à quatre v10b + soupe + v2 + v12a14 (modèle final modeles/maladies_v12_essais/v12a14/),
    # géométrique à poids égaux, « autre » = moyenne des « autre » de la v10b et de la v12 (poids 1/4 chacune).
    "C_quatre_v12a14": dict(poids=(1, 1, 1, 1), seuil=0.76, loin_ou=True, lecture="384", v12=True),
}


def geo(P10, Pso, Pv2, poids):
    """Moyenne géométrique pondérée sur saine / black_sigatoka / fusarium ; « autre » de la v10b gardée avec son poids."""
    w = np.asarray(poids, "float64") / sum(poids)
    lg = w[0] * np.log(np.clip(P10[:, :3], 1e-9, 1)) + w[1] * np.log(np.clip(Pso, 1e-9, 1)) + w[2] * np.log(np.clip(Pv2, 1e-9, 1))
    q = np.hstack([np.exp(lg), w[0] * P10[:, 3:]])
    return q / q.sum(1, keepdims=True)


def avec_saine(P, ps):
    reste = np.clip(1 - P[:, 0], 1e-9, None)
    Q = P * ((1 - ps) / reste)[:, None]
    Q[:, 0] = ps
    return Q


def lecture_v10b(P10, c, P512=None, G2=None):
    if c["lecture"] == "384":
        return P10
    if c["lecture"] == "384+512":
        return (P10 + P512) / 2
    m = 1 - G2[:, :, 0]
    pm = ((1 - P10[:, 0]) + np.sort(m, 1)[:, -2:].mean(1)) / 2
    return avec_saine(P10, 1 - pm)


def geo4(P10, Pso, Pv2, P12):
    """À quatre, poids égaux (même calcul que scripts/m12_banc_v12.py, geo)."""
    lg = sum(0.25 * np.log(np.clip(P[:, :3], 1e-9, 1)) for P in (P10, Pso, Pv2, P12))
    q = np.hstack([np.exp(lg), (0.25 * P10[:, 3] + 0.25 * P12[:, 3])[:, None]])
    return q / q.sum(1, keepdims=True)


def repondre(P10, Pso, Pv2, p_loin, c, P512=None, G2=None, P12=None):
    if c.get("v12"):
        P = geo4(P10, Pso, Pv2, P12)
        rp = maladies.decider_convnext(P, {**B.M_V10B, "seuil": c["seuil"]})[0]
        rl = maladies.decider_convnext(Pv2, B.M_V2)[0]
        rl = np.where(np.isin(rl, list(B.ALERTE)), rl, rp)
        return np.where(p_loin >= 0.5, rl, rp)
    P10 = lecture_v10b(P10, c, P512, G2)
    P = P10 if c["poids"] is None else geo(P10, Pso, Pv2, c["poids"])
    rp = maladies.decider_convnext(P, {**B.M_V10B, "seuil": c["seuil"]})[0]
    rl = maladies.decider_convnext(Pv2, B.M_V2)[0]
    if c["loin_ou"]:
        rl = np.where(np.isin(rl, list(B.ALERTE)), rl, rp)
    return np.where(p_loin >= 0.5, rl, rp)


def lire(f, n_classes):
    f = Path(f)
    if f.suffix == ".npy":
        return np.load(f).astype("float64")
    d = pd.read_csv(f)
    if n_classes == 0:
        return d["p_loin"].to_numpy("float64")
    cols = ["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"][:n_classes]
    return d[cols].to_numpy("float64")


def calculer(chemins, dossier):
    """Lectures 512 px et 2 x 2 de la v10b, préparation identique au carnet scripts/m12_banc_kaggle_morceaux.py."""
    import io
    from PIL import Image, ImageOps
    m = maladies.charger_convnext(RACINE / "modeles/maladies_binome/v10b")

    def morceaux(chemin):
        with Image.open(chemin) as im:
            im.draft("RGB", (896, 896))
            im = ImageOps.exif_transpose(im).convert("RGB")
        w, h = im.size
        mw, mh = max(1, round(0.6 * w)), max(1, round(0.6 * h))
        sortie = []
        for iy in range(2):
            for ix in range(2):
                x0, y0 = round(ix * (w - mw)), round(iy * (h - mh))
                t = io.BytesIO()
                im.crop((x0, y0, x0 + mw, y0 + mh)).save(t, format="PNG")
                t.seek(0)
                sortie.append(t)
        return sortie
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    np.save(dossier / "p_v10b_512.npy", maladies.predire_convnext(chemins, {**m, "taille": 512}))
    tuiles = [t for c in chemins for t in morceaux(c)]
    np.save(dossier / "p_v10b_g2.npy", maladies.predire_convnext(tuiles, m).reshape(len(chemins), 4, -1))


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    if "--calculer" in sys.argv:
        a.add_argument("--photos", required=True)
        a.add_argument("--calculer", required=True)
        x = a.parse_args()
        calculer([l.strip() for l in Path(x.photos).read_text(encoding="utf-8").splitlines() if l.strip()], x.calculer)
        sys.exit(0)
    for k in ("v10b", "soupe", "v2", "loin", "sortie"):
        a.add_argument(f"--{k}", required=True)
    a.add_argument("--v10b_512")
    a.add_argument("--v10b_g2")
    a.add_argument("--v12", help="(n, 4) probabilités de la v12a14 (modèle final) ; candidat C_quatre_v12a14")
    a.add_argument("--verite")
    x = a.parse_args()
    P10, Pso, Pv2, pl = lire(x.v10b, 4), lire(x.soupe, 3), lire(x.v2, 3), lire(x.loin, 0)
    P512 = lire(x.v10b_512, 4) if x.v10b_512 else None
    G2 = np.load(x.v10b_g2).astype("float64") if x.v10b_g2 else None
    P12 = lire(x.v12, 4) if x.v12 else None
    choisis = {k: c for k, c in CANDIDATS.items()
               if (c["lecture"] != "384+512" or P512 is not None) and (c["lecture"] != "g2_2fortes" or G2 is not None)
               and (not c.get("v12") or P12 is not None)}
    out = pd.DataFrame({k: repondre(P10, Pso, Pv2, pl, c, P512, G2, P12) for k, c in choisis.items()})
    if x.verite:
        m = pd.read_csv(x.verite)["malade"].astype(bool).to_numpy()
        for k in choisis:
            al = out[k].isin(B.ALERTE).to_numpy()
            print(f"{k:26s} malades sans alerte {int((m & ~al).sum())}/{int(m.sum())} ; saines en alerte "
                  f"{int((~m & al).sum())}/{int((~m).sum())} (dont à vérifier {int((~m & (out[k] == 'a_verifier').to_numpy()).sum())})")
    out.to_csv(x.sortie, index=False)
    print("écrit :", x.sortie)
