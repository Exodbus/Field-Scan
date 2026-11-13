#!/usr/bin/env python3
"""Contrôle de fuite du découpage v6 (banana_tree_detection reclassé). Aucun modèle.

1. Entre btd_train et btd_val (et avec la bande tampon) :
   a. nom d'origine (numéro de tuile) dans une seule partie ;
   b. MD5 des fichiers ;
   c. recouvrement géométrique : écart minimal entre une tuile d'entraînement et une de validation d'un même bloc
      (coordonnées de v6_prep_1, tuiles de 1280 px) ; doit être > 0 px ;
   d. recouvrement mesuré sur l'image : corrélation de phase (images au huitième, 160 px) entre CHAQUE tuile de
      validation et CHAQUE tuile d'entraînement (les blocs n'ont pas tous une position relative connue) ; une paire
      dont la zone commune corrèle à plus de 0,6 est signalée ; témoin : même mesure sur les paires voisines connues ;
   e. empreinte dHash (8 orientations) : distance de Hamming <= 8 entre une validation et un entraînement.
2. Avec les autres jeux : MD5 et dHash des tuiles btd gardées contre toutes les images des autres zips Roboflow
   utilisés (data/roboflow/*.zip sauf banana_tree_detection) ; et toutes les parties du découpage v6 : origine et
   photo chacune dans une seule partie.

Sortie : data/drone/decoupage_comptage_v6/fuites.txt et fuites_paires.csv.

Exemple :
    python scripts/v6_prep_3_fuites.py
"""
import hashlib
import multiprocessing as mp
import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageOps

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
from v6_prep_1_positions_btd import decalage  # noqa: E402

OUT = RACINE / "data/drone/decoupage_comptage_v6"
ZIP = RACINE / "data/roboflow/banana_tree_detection.zip"
PAS, T = 896, 1280


def dhash(im):
    g = np.asarray(ImageOps.grayscale(im).resize((9, 8), Image.BILINEAR), dtype="float32")
    return (g[:, 1:] > g[:, :-1]).ravel()


def dhash8(im):
    out = []
    for k in range(4):
        r = im.rotate(90 * k, expand=True)
        out += [dhash(r), dhash(ImageOps.mirror(r))]
    return np.stack(out)


_Q = None


def huitieme(octets):
    im = Image.open(io.BytesIO(octets)).convert("L")
    return np.asarray(im.resize((im.width // 8, im.height // 8), Image.BILINEAR), dtype=np.float32)


def _init(q):
    global _Q
    _Q = q


def _decalage_q(a, b):
    return decalage(a, b)


def _paire(t):
    return decalage(_Q[t[0]], _Q[t[1]])


def main():
    rap, erreurs = [], 0
    dec = pd.read_csv(OUT / "decoupage.csv")
    btd = dec[dec.source == "banana_tree_detection"]
    z = zipfile.ZipFile(ZIP)
    gard = btd[btd.groupe.isin(["btd_train", "btd_val", "btd_tampon"])]
    tr, va = gard[gard.groupe == "btd_train"], gard[gard.groupe == "btd_val"]
    rap.append(f"btd : {len(tr)} tuiles d'entraînement, {len(va)} de validation, "
               f"{int((gard.groupe == 'btd_tampon').sum())} en bande tampon")

    # 1a. noms d'origine
    commun = set(tr.origine) & set(va.origine)
    rap.append(f"1a. noms d'origine communs entraînement / validation : {len(commun)}")
    erreurs += len(commun)
    # 1b. MD5
    md5 = {r.image: hashlib.md5(z.read(r.image)).hexdigest() for r in btd.itertuples()}
    m_tr, m_va = {md5[i] for i in tr.image}, {md5[i] for i in va.image}
    rap.append(f"1b. MD5 communs entraînement / validation : {len(m_tr & m_va)} ; MD5 distincts dans tout le zip : "
               f"{len(set(md5.values()))} / {len(md5)}")
    erreurs += len(m_tr & m_va)
    # 1c. écart géométrique (même bloc)
    ecart = np.inf
    for bl in set(tr.bloc_mosaique) & set(va.bloc_mosaique):
        A_ = tr[tr.bloc_mosaique == bl][["x_mosaique_px", "y_mosaique_px"]].to_numpy()
        B_ = va[va.bloc_mosaique == bl][["x_mosaique_px", "y_mosaique_px"]].to_numpy()
        dx = np.abs(A_[:, None, 0] - B_[None, :, 0]) - T
        dy = np.abs(A_[:, None, 1] - B_[None, :, 1]) - T
        ecart = min(ecart, float(np.maximum(dx, dy).min()))
    rap.append(f"1c. écart minimal entre une tuile d'entraînement et une de validation d'un même bloc : {ecart:.0f} px "
               f"({'aucun pixel commun' if ecart > 0 else 'RECOUVREMENT'})")
    erreurs += int(ecart <= 0)
    # 1d. recouvrement mesuré, toutes les paires
    Q = {r.image: huitieme(z.read(r.image)) for r in pd.concat([tr, va]).itertuples()}
    taches = [(i, j) for i in va.image for j in tr.image]
    with mp.Pool(8, initializer=_init, initargs=(Q,)) as pool:
        res = pool.map(_paire, taches, chunksize=200)
    P = pd.DataFrame([dict(val=i, train=j, corr=round(c, 3), dx=dx * 8, dy=dy * 8) for (i, j), (c, dx, dy) in zip(taches, res)])
    P.to_csv(OUT / "fuites_paires.csv", index=False)
    n_f = int((P["corr"] > 0.6).sum())
    # témoin : paires de voisines connues (même segment, numéros consécutifs) dans l'entraînement
    trs = tr.assign(_n=tr.origine.str.split("_").str[-1].astype(int)).sort_values("_n")
    tem = []
    for (a1, s1, i1), (a2, s2, i2) in zip(trs[["origine", "segment_mosaique", "image"]].values[:-1], trs[["origine", "segment_mosaique", "image"]].values[1:]):
        if s1 == s2 and int(a2.split("_")[-1]) == int(a1.split("_")[-1]) + 1:
            tem.append(_decalage_q(Q[i1], Q[i2])[0])
    rap.append(f"1d. recouvrement mesuré (corrélation de phase au 1/8) : {len(P)} paires validation x entraînement ; "
               f"corrélation > 0,6 : {n_f} ; maximum {P['corr'].max():.3f} ; 99e centile {P['corr'].quantile(0.99):.3f} "
               f"(témoin, voisines connues : médiane {np.median(tem):.3f}, minimum {np.min(tem):.3f}, {len(tem)} paires)")
    erreurs += n_f
    # 1e. dHash
    H = {r.image: dhash8(Image.open(io.BytesIO(z.read(r.image))).convert("RGB")) for r in btd.itertuples()}
    Htr = np.stack([H[i][0] for i in tr.image]) if len(tr) else np.zeros((0, 64), bool)
    dmin = min((int((H[i] != Htr[:, None, :]).sum(-1).min()) for i in va.image), default=64) if len(tr) else 64
    rap.append(f"1e. dHash : distance minimale validation / entraînement (8 orientations) : {dmin} bits (doublon si <= 8)")
    erreurs += int(dmin <= 8)

    # 2. autres jeux
    autres_md5, autres_h, noms = set(), [], []
    for zp in sorted((RACINE / "data/roboflow").glob("*.zip")):
        if zp.name == ZIP.name:
            continue
        zz = zipfile.ZipFile(zp)
        for n in zz.namelist():
            if n.lower().endswith((".jpg", ".jpeg", ".png")):
                b = zz.read(n)
                autres_md5.add(hashlib.md5(b).hexdigest())
                try:
                    autres_h.append(dhash(Image.open(io.BytesIO(b)).convert("RGB")))
                    noms.append(f"{zp.name}:{n}")
                except Exception:
                    pass
    Hs = np.stack(autres_h)
    m_btd = {md5[i] for i in gard.image}
    d2 = [int((H[i] != Hs[:, None, :]).sum(-1).min()) for i in gard.image]
    proches = sum(d <= 8 for d in d2)
    rap.append(f"2a. autres zips Roboflow ({len(Hs)} images) : MD5 communs avec btd gardé : {len(m_btd & autres_md5)} ; "
               f"dHash <= 8 bits : {proches} (distance minimale {min(d2)})")
    erreurs += len(m_btd & autres_md5) + proches
    act = dec[dec.partie.isin(["train", "val", "test"])]
    for col in ("origine", "photo"):
        nb = act.groupby(col).partie.nunique()
        rap.append(f"2b. {col} dans plusieurs parties (tout le découpage v6) : {int((nb > 1).sum())}")
        erreurs += int((nb > 1).sum())
    rap.append("")
    rap.append("Aucune fuite détectée." if erreurs == 0 else f"ATTENTION : {erreurs} signal(s) de fuite.")
    (OUT / "fuites.txt").write_text("\n".join(rap) + "\n", encoding="utf-8")
    print("\n".join(rap))


if __name__ == "__main__":
    main()
