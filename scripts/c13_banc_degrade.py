#!/usr/bin/env python3
"""CB2 (agent C-banc, nuit du 13/11) : cartes des images de RÉGLAGE dégradées comme si elles venaient d'un capteur à
c cm/px, puis ramenées à 5 cm (même dégradation que scripts/v6_analyse_degradation.py de C-analyste, recopiée :
5 cm -> c cm LANCZOS -> taille d'origine LANCZOS -> JPEG 95 aller-retour). Les annotations ne changent pas.

Variantes enregistrées dans out/comptage/nuit_1311/banc/cache (modele_variante_jeu) :
  d{c}    : image dégradée telle quelle ;
  d{c}sh  : image dégradée puis renforcée (masque flou : img + 1,0 x (img - flou gaussien sigma = 0,6 x c / 5 px)) ;
  d{c}s35 : image dégradée agrandie de 5 à 3,5 cm/px (carte à sa résolution propre, ramenée à la grille par le banc).
Les juges ne sont jamais chargés (c13_banc_commun.jeu refuse tout autre jeu que le réglage).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c13_banc_degrade.py --cm 11 8 --modeles v5 v3 v4 --formes d dsh
"""
import argparse
import io
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c13_banc_commun as cc  # noqa: E402

bc = cc.bc


def degrader(img, cm):
    h, w = img.shape[:2]
    im = Image.fromarray(img)
    petit = im.resize((max(1, round(w * 5 / cm)), max(1, round(h * 5 / cm))), Image.LANCZOS)
    retour = petit.resize((w, h), Image.LANCZOS)
    tampon = io.BytesIO(); retour.save(tampon, format="JPEG", quality=95)
    return np.asarray(Image.open(io.BytesIO(tampon.getvalue())).convert("RGB"))


def renforcer(img, cm):
    import cv2
    s = 0.6 * cm / 5
    f = img.astype("float32")
    flou = cv2.GaussianBlur(f, (0, 0), s)
    return np.clip(f + 1.0 * (f - flou), 0, 255).astype("uint8")


def carte(sess, img, forme):
    if forme.endswith("s35"):
        h, w = img.shape[:2]
        f = 5 / 3.5
        im = np.asarray(Image.fromarray(img).resize((round(w * f), round(h * f)), Image.BILINEAR))
        x, h2, w2 = bc.entree(im)
        return bc.sigmoide(bc._logits(sess, x))[:(h2 + 3) // 4, :(w2 + 3) // 4].astype("float32")
    return bc.cartes_image(sess, img, "base")["base"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cm", nargs="+", type=int, default=[11, 8])
    ap.add_argument("--modeles", nargs="+", default=["v5", "v3", "v4"])
    ap.add_argument("--formes", nargs="+", default=["d", "dsh"])
    ap.add_argument("--jeux", nargs="+", default=cc.REGLAGE)
    ap.add_argument("--fils", type=int, default=cc.FILS)
    a = ap.parse_args()
    sessions = {m: bc.session(m, a.fils) for m in a.modeles}
    if a.cm == [0]:
        # val_negatifs vient d'images d'environ 10 à 12 cm/px : carte du v5 sur l'image renforcée (variante « sh »),
        # sigma = 0,6 x cm d'origine / 5 (cm d'origine = 5 x facteur), sans dégradation supplémentaire.
        import pandas as pd
        T = pd.read_csv(bc.D / "tuiles.csv", usecols=["image_path", "ensemble", "facteur"])
        fac = dict(zip(T[T.ensemble == "val_negatifs"].image_path, T[T.ensemble == "val_negatifs"].facteur))
        items = cc.jeu("neg")
        for m in a.modeles:
            p = cc.chemin_cache(m, "sh", "neg")
            if p.with_suffix(".json").exists():
                continue
            blocs, index, pos = [], {}, 0
            for e in items:
                k = carte(sessions[m], renforcer(bc.lire(e["chemin"]), 5 * fac[e["nom"]]), "d")
                blocs.append(k.ravel()); index[e["nom"]] = [pos, k.shape[0], k.shape[1]]; pos += k.size
            np.concatenate(blocs).astype("float32").tofile(p.with_suffix(".f32"))
            p.with_suffix(".json").write_text(json.dumps(index), encoding="utf-8")
            print(f"{time.strftime('%H:%M:%S')} sh neg {m} : {len(items)} images", flush=True)
        return
    for c in a.cm:
        for j in a.jeux:
            items = cc.jeu(j)
            for forme in a.formes:
                var = f"d{c}{forme[1:]}"
                todo = [m for m in a.modeles if not cc.chemin_cache(m, var, j).with_suffix(".json").exists()]
                if not todo:
                    continue
                t0 = time.time()
                blocs = {m: [] for m in todo}; index = {m: {} for m in todo}; pos = {m: 0 for m in todo}
                for e in items:
                    img = degrader(bc.lire(e["chemin"]), c)
                    if "sh" in forme:
                        img = renforcer(img, c)
                    for m in todo:
                        k = carte(sessions[m], img, forme)
                        blocs[m].append(k.ravel()); index[m][e["nom"]] = [pos[m], k.shape[0], k.shape[1]]; pos[m] += k.size
                for m in todo:
                    p = cc.chemin_cache(m, var, j)
                    np.concatenate(blocs[m]).astype("float32").tofile(p.with_suffix(".f32"))
                    p.with_suffix(".json").write_text(json.dumps(index[m]), encoding="utf-8")
                print(f"{time.strftime('%H:%M:%S')} {var} {j} {todo} : {len(items)} images en {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
