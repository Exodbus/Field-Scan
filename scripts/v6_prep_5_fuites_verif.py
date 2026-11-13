#!/usr/bin/env python3
"""Vérification des signaux de fuite levés par v6_prep_3_fuites.py (découpage v6). Aucun modèle.

Les seuils de v6_prep_3 sont larges : au 1/8 (160 px) une plantation en lignes régulières corrèle fort avec une autre
partie de la même plantation, et l'empreinte dHash 8 x 8 confond des tuiles d'aspect uniforme. On revérifie donc :
a. les 60 paires validation x entraînement les plus corrélées au 1/8, plus toutes celles au-dessus de 0,80 avec au
   moins 10 % de surface commune (plafonné à 400), par corrélation de phase au quart (320 px) puis au demi (640 px)
   sur la zone commune. Témoin : voisines connues (corrélation 0,999 à 1,000). Fuite si >= 0,95 au demi ;
b. les paires dHash <= 8 (validation / entraînement, et btd / autres zips) : corrélation de phase au quart entre les
   deux images ramenées à 320 px (8 orientations pour les autres zips). Fuite si >= 0,95.
Planche des paires les plus fortes : data/drone/decoupage_comptage_v6/planche_fuites.jpg.

Sortie : data/drone/decoupage_comptage_v6/fuites_verif.txt et fuites_verif.csv.

Exemple :
    python scripts/v6_prep_5_fuites_verif.py
"""
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
from v6_prep_3_fuites import dhash, dhash8  # noqa: E402

OUT = RACINE / "data/drone/decoupage_comptage_v6"
ZIP = RACINE / "data/roboflow/banana_tree_detection.zip"
Image.MAX_IMAGE_PIXELS = None


def gris(img, cote):
    return np.asarray(ImageOps.grayscale(img).resize((cote, cote), Image.BILINEAR), dtype=np.float32)


def main():
    rap, lignes = [], []
    z = zipfile.ZipFile(ZIP)
    lire = lambda n: Image.open(io.BytesIO(z.read(n))).convert("RGB")
    dec = pd.read_csv(OUT / "decoupage.csv")
    btd = dec[dec.source == "banana_tree_detection"]
    tr, va = btd[btd.groupe == "btd_train"], btd[btd.groupe == "btd_val"]

    # a. paires les plus corrélées au 1/8
    P = pd.read_csv(OUT / "fuites_paires.csv")
    P["aire"] = (1280 - P.dx.abs()).clip(0) * (1280 - P.dy.abs()).clip(0) / 1280 ** 2
    cand = pd.concat([P.nlargest(60, "corr"), P[(P["corr"] > 0.8) & (P.aire >= 0.1)].nlargest(400, "corr")]).drop_duplicates(["val", "train"])
    cache = {}
    def img(n, c):
        if (n, c) not in cache:
            cache[(n, c)] = gris(lire(n), c)
        return cache[(n, c)]
    for r in cand.itertuples():
        c4 = decalage(img(r.val, 320), img(r.train, 320))[0]
        c2 = decalage(img(r.val, 640), img(r.train, 640))[0] if c4 > 0.8 else np.nan
        lignes.append(dict(controle="a_recouvrement", a=r.val, b=r.train, corr_1_8=r.corr, aire_1_8=round(r.aire, 3),
                           corr_1_4=round(c4, 3), corr_1_2=None if np.isnan(c2) else round(c2, 3)))
    A = pd.DataFrame(lignes)
    tem = []
    trs = tr.assign(_n=tr.origine.str.split("_").str[-1].astype(int)).sort_values("_n")
    for (a1, s1, i1), (a2, s2, i2) in zip(trs[["_n", "segment_mosaique", "image"]].values[:-1], trs[["_n", "segment_mosaique", "image"]].values[1:]):
        if s1 == s2 and a2 == a1 + 1 and len(tem) < 20:
            tem.append(decalage(img(i1, 320), img(i2, 320))[0])
    fa = int((A.corr_1_2.fillna(0) >= 0.95).sum())
    rap.append(f"a. {len(A)} paires revérifiées : corrélation au quart max {A.corr_1_4.max():.3f} (médiane {A.corr_1_4.median():.3f}) ; "
               f"au demi max {A.corr_1_2.max():.3f} ; >= 0,95 : {fa}. Témoin (20 voisines connues, au quart) : min {min(tem):.3f}")

    # b1. dHash validation / entraînement
    H = {n: dhash8(lire(n)) for n in pd.concat([tr, va]).image}
    Htr = np.stack([H[n][0] for n in tr.image])
    lb = []
    for n in va.image:
        d = (H[n] != Htr[:, None, :]).sum(-1).min(1)
        for j in np.where(d <= 8)[0]:
            m = tr.image.iloc[j]
            lb.append(dict(controle="b1_dhash_val_train", a=n, b=m, dhash=int(d[j]),
                           corr_1_4=round(decalage(img(n, 320), img(m, 320))[0], 3)))
    B1 = pd.DataFrame(lb, columns=["controle", "a", "b", "dhash", "corr_1_4"])
    fb1 = int((B1.corr_1_4 >= 0.95).sum())
    rap.append(f"b1. dHash <= 8 entre validation et entraînement : {len(B1)} paires ; corrélation au quart max "
               f"{B1.corr_1_4.max() if len(B1) else float('nan'):.3f} ; >= 0,95 : {fb1}")

    # b2. dHash btd / autres zips
    gard = btd[btd.groupe.isin(["btd_train", "btd_val", "btd_tampon"])]
    Hg = {n: (H[n] if n in H else dhash8(lire(n))) for n in gard.image}
    lc = []
    for zp in sorted((RACINE / "data/roboflow").glob("*.zip")):
        if zp.name == ZIP.name:
            continue
        zz = zipfile.ZipFile(zp)
        for m in zz.namelist():
            if not m.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            try:
                im = Image.open(io.BytesIO(zz.read(m))).convert("RGB")
            except Exception:
                continue
            h = dhash(im)
            for n, hn in Hg.items():
                d = int((hn != h).sum(-1).min())
                if d <= 8:
                    k = int((hn != h).sum(-1).argmin())
                    r_ = im.rotate(90 * (k // 2), expand=True)
                    r_ = ImageOps.mirror(r_) if k % 2 else r_
                    # même orientation que la tuile btd : on compare l'image btd à l'image tournée inversement
                    c = decalage(img(n, 320), gris(r_, 320))[0]
                    lc.append(dict(controle="b2_dhash_autres_zips", a=n, b=f"{zp.name}:{m}", dhash=d,
                                   taille_b=f"{im.width}x{im.height}", corr_1_4=round(c, 3)))
    B2 = pd.DataFrame(lc, columns=["controle", "a", "b", "dhash", "taille_b", "corr_1_4"])
    fb2 = int((B2.corr_1_4 >= 0.95).sum())
    rap.append(f"b2. dHash <= 8 entre btd gardé et les autres zips : {len(B2)} paires ({B2.b.str.split(':').str[0].value_counts().to_dict() if len(B2) else {}}) ; "
               f"corrélation au quart max {B2.corr_1_4.max() if len(B2) else float('nan'):.3f} ; >= 0,95 : {fb2}")
    pd.concat([A, B1, B2], ignore_index=True).to_csv(OUT / "fuites_verif.csv", index=False)

    # planche : 4 paires les plus fortes de chaque contrôle
    vign = []
    for D, col in ((A, "corr_1_4"), (B1, "corr_1_4"), (B2, "corr_1_4")):
        for r in D.nlargest(4, col).itertuples() if len(D) else []:
            a = lire(r.a).resize((256, 256))
            if ":" in r.b:
                zn, m = r.b.split(":", 1)
                b = Image.open(io.BytesIO(zipfile.ZipFile(RACINE / "data/roboflow" / zn).read(m))).convert("RGB")
            else:
                b = lire(r.b)
            b.thumbnail((256, 256))
            v = Image.new("RGB", (520, 260), "white")
            v.paste(a, (0, 0))
            v.paste(b, (264, 0))
            vign.append(v)
    if vign:
        pl = Image.new("RGB", (520, 260 * len(vign)), "white")
        for i, v in enumerate(vign):
            pl.paste(v, (0, 260 * i))
        pl.save(OUT / "planche_fuites.jpg", quality=85)
    total = fa + fb1 + fb2
    rap.append("")
    rap.append("Conclusion : aucune fuite confirmée (aucune paire >= 0,95 ; les voisines vraies sont à 0,999-1,000)."
               if total == 0 else f"ATTENTION : {total} fuite(s) confirmée(s), voir fuites_verif.csv.")
    (OUT / "fuites_verif.txt").write_text("\n".join(rap) + "\n", encoding="utf-8")
    print("\n".join(rap))


if __name__ == "__main__":
    main()
