#!/usr/bin/env python3
"""Mesure locale d'un ONNX de centres sur le réglage, à 5 cm et dégradé (agent C-entraîneur, nuit du 13/11).

Code du banc (scripts/v6_banc_commun.py) : jeux `bc.jeu` (dense, plantain, jeunes, mm, btd_val, neg), carte
`bc.cartes_image(..., "base")`, pics fenêtre 7, `bc.mesurer_jeu` (rayon 20 px, appariement un-à-un, disque, zones).
Dégradation : `degrader` recopiée de scripts/v6_analyse_degradation.py (LANCZOS aller-retour, JPEG 95).
Aucun juge : seuls les 5 jeux de réglage et `neg` (val_negatifs) sont lus.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c13_entr_mesure.py --nom v5 --onnx modeles/centres_5cm_v5.onnx --cm 5 11 --fils 2

Sorties (out/comptage/nuit_1311/kaggle/mesures/) : <nom>_<cm>cm.csv (une ligne par seuil) ; cartes en cache au format du banc
dans out/comptage/nuit_1311/kaggle/cache/ (<nom>_base_<jeu> à 5 cm, <nom>_d<cm>_<jeu> dégradé) si --cache.
"""
import argparse
import io
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import v6_banc_commun as bc  # noqa: E402

SORTIE = RACINE / "out/comptage/nuit_1311/kaggle"
CACHE = SORTIE / "cache"
JEUX = ["dense", "plantain", "jeunes", "mm", "btd_val"]
INTERDITS = ("segmento", "cg", "banano", "neg_test")


def degrader(img, cm):
    """Identique à scripts/v6_analyse_degradation.py."""
    h, w = img.shape[:2]
    im = Image.fromarray(img)
    petit = im.resize((max(1, round(w * 5 / cm)), max(1, round(h * 5 / cm))), Image.LANCZOS)
    retour = petit.resize((w, h), Image.LANCZOS)
    tampon = io.BytesIO(); retour.save(tampon, format="JPEG", quality=95)
    return np.asarray(Image.open(io.BytesIO(tampon.getvalue())).convert("RGB"))


def mesurer(nom, onnx, cm, fils, jeux, neg, cache):
    import onnxruntime as ort
    o = ort.SessionOptions(); o.intra_op_num_threads = fils; o.inter_op_num_threads = 1
    sess = ort.InferenceSession(str(onnx), o, providers=["CPUExecutionProvider"])
    variante = "base" if cm == 5 else f"d{cm}"
    res = {}
    for j in jeux + (["neg"] if neg else []):
        assert j not in INTERDITS
        t0 = time.time()
        items = bc.jeu(j)
        chemins = {e["nom"]: e["chemin"] for e in items}
        blocs, index, pos = [], {}, 0

        def cand(ctx):
            nonlocal pos
            img = bc.lire(chemins[ctx.nom])
            if cm != 5:
                img = degrader(img, cm)
            c = bc.cartes_image(sess, img, "base")["base"]
            if cache:
                blocs.append(c.ravel()); index[ctx.nom] = [pos, c.shape[0], c.shape[1]]; pos += c.size
            return bc.pics(c)

        res[j] = bc.mesurer_jeu(cand, j, items)
        if cache:
            CACHE.mkdir(parents=True, exist_ok=True)
            p = CACHE / f"{nom}_{variante}_{j}"
            np.concatenate(blocs).astype("float32").tofile(p.with_suffix(".f32"))
            p.with_suffix(".json").write_text(json.dumps(index), encoding="utf-8")
        print(f"{time.strftime('%H:%M:%S')} {nom} {cm} cm {j} : {time.time() - t0:.0f} s", flush=True)
    lignes = []
    for s in bc.SEUILS:
        l = dict(nom=nom, cm=cm, seuil=s)
        for j in jeux:
            r = res[j][s]
            l[f"f1_{j}"] = round(r["f1"], 4); l[f"ratio_{j}"] = round(r["detectes"] / r["reels"], 3); l[f"err_{j}"] = round(r["err_compte"], 4)
        l["moyenne"] = round(float(np.mean([l[f"f1_{j}"] for j in jeux])), 4)
        l["moyenne_4"] = round(float(np.mean([l[f"f1_{j}"] for j in jeux if j != "btd_val"])), 4)
        l["err_compte"] = round(float(np.mean([l[f"err_{j}"] for j in jeux])), 4)
        if neg:
            l["fp_neg"], l["taux_fp"] = res["neg"][s]["fp"], round(res["neg"][s]["taux"], 5)
        lignes.append(l)
    D = pd.DataFrame(lignes)
    (SORTIE / "mesures").mkdir(parents=True, exist_ok=True)
    D.to_csv(SORTIE / "mesures" / f"{nom}_{cm}cm.csv", index=False)
    return D


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nom", required=True); ap.add_argument("--onnx", required=True)
    ap.add_argument("--cm", type=int, nargs="+", default=[5, 11]); ap.add_argument("--fils", type=int, default=2)
    ap.add_argument("--cache", action="store_true"); ap.add_argument("--neg-degrade", action="store_true")
    a = ap.parse_args()
    for cm in a.cm:
        D = mesurer(a.nom, RACINE / a.onnx, cm, a.fils, JEUX, cm == 5 or a.neg_degrade, a.cache)
        print(D.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
