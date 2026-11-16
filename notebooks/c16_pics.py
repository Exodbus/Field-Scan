#!/usr/bin/env python3
"""Essai c16 (16/11) : pics d'un ONNX de centres sur le réglage dégradé, val_negatifs dégradé, tuiles ReforesTree
d'entraînement (contrôle agroforesterie) et Ghana (A2), selon docs/journee_2026-11-16/avenant_c16_aiguillage_resolution.md.

Reprend sans les modifier :
  - la lecture des jeux gardée de scripts/c13_banc_commun.py (`cc.jeu` : réglage et val_negatifs seulement, assert) ;
  - la carte `bc.cartes_image(..., "base")` et les pics `bc.pics` (fenêtre 7, seuil plancher 0,10) de scripts/v6_banc_commun.py ;
  - `degrader` de scripts/c13_entr_mesure.py (5 cm -> c cm LANCZOS -> taille d'origine LANCZOS -> JPEG 95).
Seuls les pics (x, y, score >= 0,10) sont gardés, pas les cartes : la mesure par seuil (`bc.mesurer_jeu`) n'en lit pas plus,
puisqu'un candidat « réseau seul » est `bc.pics(carte)` (`v6_banc_candidats.f_seul`).

Cache des images dégradées (hors dépôt, C:/Users/coren/kaggle_tmp/c16/degr) : les octets JPEG produits par la dernière
étape de `degrader` sont écrits tels quels ; les relire redonne exactement le tableau de `degrader` (vérifié par assert
sur la première image de chaque groupe).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/c16_pics.py --nom v5 --onnx modeles/centres_5cm_v5.onnx \
        --taches d11:dense d11:neg d11:rt ... [--fils 3]
Tâches : <variante>:<jeu>, variante base (5 cm) ou d<cm> ; jeu dans dense, plantain, jeunes, mm, btd_val, neg, rt, ghana.
Sorties : out/comptage/jour_1611/pics/<nom>_<variante>_<jeu>.npz. Aucun juge.
"""
import argparse
import io
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

import c13_banc_commun as cc  # noqa: E402  (garde-fou des juges)
import v6_banc_commun as bc  # noqa: E402
from c13_entr_mesure import degrader  # noqa: E402

PICS = RACINE / "out/comptage/jour_1611/pics"
DEGR = Path("C:/Users/coren/kaggle_tmp/c16/degr")
D5 = RACINE / "data/drone/comptage_v5_5cm"
A2 = RACINE / "data/raw/plantain_ghana_m2"
Image.MAX_IMAGE_PIXELS = 60_000_000


def tuiles_rt():
    """Tuiles ReforesTree d'entraînement (copie des contrôles de notebooks/c15b_controle_rt.py)."""
    t = pd.read_csv(D5 / "tuiles.csv")
    r = t[t.groupe.str.startswith("rt_")].reset_index(drop=True)
    assert len(r) and (r.partie == "train").all() and (r.ensemble == "train").all(), "tuile ReforesTree hors entraînement"
    assert (r.facteur.astype(float) == 1.0).all(), "tuile ReforesTree rééchantillonnée"
    assert not r.image_path.str.startswith("cg/").any()
    return [dict(nom=n, chemin=str(D5 / "images" / n)) for n in r.image_path]


def photos_ghana():
    return [dict(nom=p.stem, chemin=str(p)) for p in sorted((A2 / "images").glob("*.JPG"))]


def items_de(jeu):
    if jeu == "rt":
        return tuiles_rt()
    if jeu == "ghana":
        return photos_ghana()
    return cc.jeu(jeu)


def octets_degrades(img, cm):
    """Les octets JPEG de la dernière étape de `degrader` (copie exacte de son code)."""
    h, w = img.shape[:2]
    im = Image.fromarray(img)
    petit = im.resize((max(1, round(w * 5 / cm)), max(1, round(h * 5 / cm))), Image.LANCZOS)
    retour = petit.resize((w, h), Image.LANCZOS)
    tampon = io.BytesIO(); retour.save(tampon, format="JPEG", quality=95)
    return tampon.getvalue()


def lire_5cm(jeu, e):
    if jeu != "ghana":
        return bc.lire(e["chemin"])
    f = float(json.loads((RACINE / "out/jeux_neufs_1511/a2_echelle.json").read_text(encoding="utf-8"))["facteur"])
    assert abs(f - 0.4) < 1e-9, f
    with Image.open(e["chemin"]) as im:            # comme scripts/jeux_neufs_a2_mesure_v5.py
        im = im.convert("RGB")
        return np.asarray(im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS))


_VERIFIE = set()


def image(jeu, e, k, cm):
    """Image à 5 cm (cm = 5) ou dégradée à cm cm/px, lue dans le cache hors dépôt ou calculée puis mise en cache."""
    if cm == 5:
        return lire_5cm(jeu, e)
    p = DEGR / f"d{cm}" / jeu / f"{k:05d}.jpg"
    if not p.exists():
        img = lire_5cm(jeu, e)
        b = octets_degrades(img, cm)
        if (jeu, cm) not in _VERIFIE:
            assert np.array_equal(np.asarray(Image.open(io.BytesIO(b)).convert("RGB")), degrader(img, cm)), "écart avec degrader"
            _VERIFIE.add((jeu, cm))
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp"); tmp.write_bytes(b); os.replace(tmp, p)
        (p.parent / "noms.txt").open("a", encoding="utf-8").write(f"{k:05d}\t{e['nom']}\n")
    return np.asarray(Image.open(p).convert("RGB"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nom", required=True); ap.add_argument("--onnx", required=True)
    ap.add_argument("--taches", nargs="+", required=True); ap.add_argument("--fils", type=int, default=3)
    ap.add_argument("--preparer", action="store_true", help="seulement le cache des images dégradées (pas de réseau)")
    a = ap.parse_args()
    assert a.fils <= 3, "machine partagée : 3 fils au plus"
    sess = None
    if not a.preparer:
        import onnxruntime as ort
        o = ort.SessionOptions(); o.intra_op_num_threads = a.fils; o.inter_op_num_threads = 1
        sess = ort.InferenceSession(str(RACINE / a.onnx), o, providers=["CPUExecutionProvider"])
    PICS.mkdir(parents=True, exist_ok=True)
    for t in a.taches:
        variante, jeu = t.split(":")
        cm = 5 if variante == "base" else int(variante[1:])
        sortie = PICS / f"{a.nom}_{variante}_{jeu}.npz"
        if not a.preparer and sortie.exists():
            print(f"{sortie.name} déjà là", flush=True); continue
        items = items_de(jeu)
        t0, noms, blocs, debut = time.time(), [], [], [0]
        for k, e in enumerate(items):
            img = image(jeu, e, k, cm)
            if a.preparer:
                continue
            xy, sc = bc.pics(bc.cartes_image(sess, img, "base")["base"])
            blocs.append(np.c_[xy, sc].astype("float32").reshape(-1, 3)); noms.append(e["nom"]); debut.append(debut[-1] + len(sc))
        if a.preparer:
            print(f"{time.strftime('%H:%M:%S')} préparé {variante} {jeu} : {len(items)} images, {time.time() - t0:.0f} s", flush=True)
            continue
        tmp = sortie.with_name(sortie.stem + ".tmp.npz")
        np.savez_compressed(tmp, noms=np.array(noms), pics=np.concatenate(blocs) if blocs else np.zeros((0, 3), "float32"),
                            debut=np.array(debut, "int64"), onnx=np.array(str(a.onnx)))
        os.replace(tmp, sortie)
        print(f"{time.strftime('%H:%M:%S')} {a.nom} {variante} {jeu} : {len(items)} images, {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
