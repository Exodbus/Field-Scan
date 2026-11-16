#!/usr/bin/env python3
"""Essai c16 (16/11) : UNE lecture des juges dégradés pour le finaliste c16_a (docs/journee_2026-11-16/avenant_c16_juges.md).

Juges : segmento est, CG mères seules, banano_dense, test_negatifs (chargés par `bc.jeu` de scripts/v6_banc_commun.py,
comme les juges des 14 et 15/11). Jamais banana_trees_kp. Chaque image entière est dégradée par `degrader`
(scripts/c13_entr_mesure.py) à la résolution demandée ; v5 (seuil 0,30) et c16_a (seuil 0,35) sont lus sur les mêmes
images. Mesure : `bc.mesurer_jeu` (pics fenêtre 7, appariement un à un dans 20 px, non-mères ignorées, disque DJI,
zones CG), code du banc importé sans modification ; contrôle : somme des comptes par image = mesure.

Avant toute lecture : empreinte de l'avenant, garde-fou de scripts/c13_banc_commun.py (il doit refuser les juges),
SHA-256 des deux ONNX. Le script refuse d'écrire une sortie qui existe déjà (une lecture par juge et par résolution).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c16_juges.py --cm 11 [--fils 6]
Sorties : out/comptage/jour_1611/juges/mesure_d<cm>_<jeu>.json
"""
import argparse
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import c13_banc_commun as cc  # noqa: E402  (seulement pour vérifier son garde-fou)
import v6_banc_commun as bc  # noqa: E402
from c13_entr_mesure import degrader  # noqa: E402

AVENANT = RACINE / "docs/journee_2026-11-16/avenant_c16_juges.md"
EMPREINTE_AVENANT = "d2e29e834d8daca5050476be6d0d31f8f202f17c27eb8513420b583a8590033b"
MODELES = {"v5": (RACINE / "modeles/centres_5cm_v5.onnx", "12f9b4caa5735767c454de99edf1a6616765718243555f8559c2cfcc0722f1ea", 0.30),
           "c16_a": (RACINE / "modeles/comptage_jour_1611/centres_5cm_c16_a.onnx", None, 0.35)}
JEUX = ["segmento", "cg", "banano", "neg_test"]
SORTIE = RACINE / "out/comptage/jour_1611/juges"
DEGR = Path("C:/Users/coren/kaggle_tmp/c16/juges")


def controles():
    assert hashlib.sha256(AVENANT.read_bytes()).hexdigest() == EMPREINTE_AVENANT, "empreinte de l'avenant différente"
    for j in JEUX:                                       # le garde-fou de la mesure c16 refuse bien les juges
        try:
            cc.jeu(j)
        except AssertionError:
            continue
        raise RuntimeError(f"le garde-fou de c13_banc_commun n'a pas refusé {j}")
    attendu_c16a = (RACINE / "docs/journee_2026-11-16/journal_c16.md").read_text(encoding="utf-8")
    for m, (p, h, _) in MODELES.items():
        d = hashlib.sha256(p.read_bytes()).hexdigest()
        if h:
            assert d == h, f"SHA-256 de {m} différent"
        else:
            assert f"`{d[:8]}…{d[-5:]}`" in attendu_c16a, f"SHA-256 de {m} absent du journal c16"
    return "empreinte de l'avenant, garde-fou c13_banc_commun et SHA-256 des ONNX vérifiés"


def image_degradee(jeu, k, chemin, cm):
    p = DEGR / f"d{cm}" / jeu / f"{k:05d}.jpg"
    if not p.exists():
        img = bc.lire(chemin)
        h, w = img.shape[:2]
        im = Image.fromarray(img)
        petit = im.resize((max(1, round(w * 5 / cm)), max(1, round(h * 5 / cm))), Image.LANCZOS)
        retour = petit.resize((w, h), Image.LANCZOS)
        t = io.BytesIO(); retour.save(t, format="JPEG", quality=95); b = t.getvalue()
        if k == 0:
            assert np.array_equal(np.asarray(Image.open(io.BytesIO(b)).convert("RGB")), degrader(img, cm)), "écart avec degrader"
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp"); tmp.write_bytes(b); os.replace(tmp, p)
    return np.asarray(Image.open(p).convert("RGB"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cm", type=int, required=True); ap.add_argument("--fils", type=int, default=6)
    ap.add_argument("--jeux", nargs="+", default=JEUX, choices=JEUX)
    a = ap.parse_args()
    assert a.fils <= 6
    msg = controles()
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)
    import onnxruntime as ort
    o = ort.SessionOptions(); o.intra_op_num_threads = a.fils; o.inter_op_num_threads = 1
    sess = {m: ort.InferenceSession(str(p), o, providers=["CPUExecutionProvider"]) for m, (p, _, _) in MODELES.items()}
    SORTIE.mkdir(parents=True, exist_ok=True)
    for jeu in a.jeux:
        sortie = SORTIE / f"mesure_d{a.cm}_{jeu}.json"
        assert not sortie.exists(), f"{sortie} existe déjà : ce juge a déjà été lu à {a.cm} cm"
        t0 = time.time()
        items = bc.jeu(jeu)
        assert all("banana_trees_kp" not in str(e["chemin"]) for e in items)
        pics = {m: {} for m in MODELES}
        for k, e in enumerate(items):
            img = image_degradee(jeu, k, e["chemin"], a.cm)
            for m in MODELES:
                xy, sc = bc.pics(bc.cartes_image(sess[m], img, "base")["base"])
                pics[m][e["nom"]] = (xy, sc)
        res = dict(jeu=jeu, cm=a.cm, n_elements=len(items), fils=a.fils, controles=msg,
                   note="juge relu à 5 cm (12 au 15/11), première lecture dégradée ; une lecture, rien n'y est réglé", candidats={})
        for m, (_, _, s) in MODELES.items():
            P = pics[m]
            r = bc.mesurer_jeu(lambda ctx, P=P: P[ctx.nom], jeu, items)[s]
            tot = np.zeros(4, int)
            for e in items:
                xy, sc = P[e["nom"]]
                if e["zone"] is not None:
                    x0, y0, x1, y1 = e["zone"]
                    g = (xy[:, 0] >= x0) & (xy[:, 0] <= x1) & (xy[:, 1] >= y0) & (xy[:, 1] <= y1)
                else:
                    g = bc.dans_masque(xy, e["masque"])
                det = xy[g][sc[g] >= s]
                c = (0, len(det), 0) if jeu.startswith("neg") else bc.compter(det, e["pts"], e["ign"])
                tot += (c[0], c[1], c[2], len(det))
            if jeu.startswith("neg"):
                assert tot[1] == r["fp"], (m, tot, r)
            else:
                assert tuple(tot) == (r["vp"], r["fp"], r["fn"], r["detectes"]), (m, tot, r)
            res["candidats"][m] = dict(seuil=s, **r)
        sortie.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{time.strftime('%H:%M:%S')} {jeu} à {a.cm} cm : {len(items)} éléments, {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
