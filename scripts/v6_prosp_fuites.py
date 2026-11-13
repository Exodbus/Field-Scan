#!/usr/bin/env python3
"""Contrôle de fuite des jeux neufs de comptage contre tous nos jeux (nuit du 12 novembre 2026, C-prospection).

Trois contrôles, du plus sûr au plus large :
1. nom d'origine (avant « _jpg.rf. ») commun avec un jeu de référence ;
2. MD5 des octets de l'image identique ;
3. empreinte dHash 8 x 8 (64 bits) sous les 8 symétries : distance de Hamming minimale à toutes les images de
   référence ; au plus --seuil bits = doublon probable (même principe que scripts/verifier_fuites_roboflow.py).
Les références sont : les zips de data/roboflow/, les images de data/drone/comptage_v6_5cm/images (tuiles 5 cm),
et les autres jeux neufs eux-mêmes (copies entre jeux neufs). Les empreintes de référence sont gardées en cache
(--out/reference.npz). Les JPEG sont lus en mode réduit (draft) ; rien n'est décompressé sur disque.

Limite : une tuile recadrée autrement ou à une autre échelle qu'une image de référence échappe à l'empreinte
globale ; la planche des doublons sert à juger à l'oeil.

Exemple :
    python scripts/v6_prosp_fuites.py data/roboflow_nuit_1112/comptage/*/*.zip --out data/roboflow_nuit_1112/comptage/_fuites
"""
import argparse
import hashlib
import io
import re
import zipfile
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageOps

MOTIF = re.compile(r"^(.*?)_(?:jpg|jpeg|png|tif|tiff)\.rf\.", re.IGNORECASE)
EXT = (".jpg", ".jpeg", ".png")


def origine(nom):
    b = PurePosixPath(nom).name
    m = MOTIF.match(b)
    return (m.group(1) if m else b.rsplit(".", 1)[0]).lower()


def ouvrir(octets):
    im = Image.open(io.BytesIO(octets))
    if im.format == "JPEG":
        im.draft("L", (64, 64))
    return ImageOps.grayscale(im.convert("RGB"))


def dhash(g):
    a = np.asarray(g.resize((9, 8), Image.BILINEAR), dtype="float32")
    return np.packbits((a[:, 1:] > a[:, :-1]).ravel())


def huit(g):
    for k in range(4):
        r = g.rotate(90 * k, expand=True)
        yield r
        yield ImageOps.mirror(r)


def sources_reference(racine_rf, dossier_v6):
    for zp in sorted(Path(racine_rf).glob("*.zip")):
        z = zipfile.ZipFile(zp)
        for n in z.namelist():
            if n.lower().endswith(EXT):
                yield zp.stem, n, (lambda z=z, n=n: z.read(n))
    for f in sorted(Path(dossier_v6).glob("*.jpg")):
        yield "comptage_v6_5cm", f.name, (lambda f=f: f.read_bytes())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidats", nargs="+")
    ap.add_argument("--roboflow", default="data/roboflow")
    ap.add_argument("--v6", default="data/drone/comptage_v6_5cm/images")
    ap.add_argument("--seuil", type=int, default=6)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cache = out / "reference.npz"
    if cache.exists():
        c = np.load(cache, allow_pickle=True)
        R, rjeu, rnom, rmd5, rorig = c["R"], list(c["jeu"]), list(c["nom"]), list(c["md5"]), list(c["orig"])
    else:
        R, rjeu, rnom, rmd5, rorig = [], [], [], [], []
        for k, (jeu, nom, lire) in enumerate(sources_reference(args.roboflow, args.v6)):
            b = lire()
            try:
                R.append(dhash(ouvrir(b)))
            except Exception:
                continue
            rjeu.append(jeu); rnom.append(nom); rmd5.append(hashlib.md5(b).hexdigest()); rorig.append(origine(nom))
            if k % 2000 == 0:
                print(f"  référence : {k} images", flush=True)
        R = np.stack(R)
        np.savez(cache, R=R, jeu=np.array(rjeu), nom=np.array(rnom), md5=np.array(rmd5), orig=np.array(rorig))
    print(f"{len(rnom)} images de référence ({pd.Series(rjeu).value_counts().to_dict()})", flush=True)
    Rb = np.unpackbits(R, axis=1).astype(bool)
    md5_ref = {m: (j, n) for m, j, n in zip(rmd5, rjeu, rnom)}
    orig_ref = {}
    for o, j in zip(rorig, rjeu):
        if j != "comptage_v6_5cm":
            orig_ref.setdefault(o, set()).add(j)

    cand = []
    for zp in args.candidats:
        jeu = Path(zp).parent.name
        z = zipfile.ZipFile(zp)
        for n in z.namelist():
            if n.lower().endswith(EXT):
                b = z.read(n)
                g = ouvrir(b)
                cand.append(dict(jeu=jeu, zip=zp, image=n, md5=hashlib.md5(b).hexdigest(), orig=origine(n),
                                 H=np.stack([np.unpackbits(dhash(o)).astype(bool) for o in huit(g)])))
        print(f"  {jeu} : empreintes faites", flush=True)
    H0 = np.stack([c["H"][0] for c in cand])
    jeux = np.array([c["jeu"] for c in cand])
    lignes, paires = [], []
    for c in cand:
        d = np.stack([(Rb != h).sum(1) for h in c["H"]]).min(0)
        j = int(d.argmin())
        dc = np.stack([(H0 != h).sum(1) for h in c["H"]]).min(0).astype(float)
        dc[jeux == c["jeu"]] = 99
        kc = int(dc.argmin())
        lignes.append(dict(jeu=c["jeu"], image=c["image"], origine=c["orig"],
                           nom_commun="|".join(sorted(orig_ref.get(c["orig"], []))),
                           md5_commun=":".join(md5_ref[c["md5"]]) if c["md5"] in md5_ref else "",
                           dist_ref=int(d[j]), plus_proche_ref=f"{rjeu[j]}:{rnom[j]}",
                           dist_neufs=int(dc[kc]), plus_proche_neuf=f"{cand[kc]['jeu']}:{cand[kc]['image']}"))
        if d[j] <= args.seuil and len(paires) < 40:
            paires.append((c, rjeu[j], rnom[j], int(d[j])))
    df = pd.DataFrame(lignes)
    df["doublon_ref"] = df.dist_ref <= args.seuil
    df["doublon_neuf"] = df.dist_neufs <= args.seuil
    df.to_csv(out / "fuites.csv", index=False)
    res = df.groupby("jeu").agg(images=("image", "size"), origines=("origine", "nunique"),
                                nom_commun=("nom_commun", lambda s: int((s != "").sum())),
                                md5_commun=("md5_commun", lambda s: int((s != "").sum())),
                                doublon_ref=("doublon_ref", "sum"), dist_ref_mediane=("dist_ref", "median"),
                                doublon_neuf=("doublon_neuf", "sum"))
    res.to_csv(out / "resume.csv")
    print(res.to_string())
    for jeu, g in df[df.doublon_ref].groupby("jeu"):
        print(jeu, "plus proches (doublons) :", g.plus_proche_ref.str.split(":").str[0].value_counts().to_dict())
    for jeu, g in df[df.nom_commun != ""].groupby("jeu"):
        print(jeu, "noms communs :", g.nom_commun.value_counts().to_dict(), "ex.", g.origine.head(4).tolist())
    if paires:
        cc = 220
        pl = Image.new("RGB", (2 * cc + 10, len(paires) * (cc + 16)), "white")
        dr = ImageDraw.Draw(pl)
        for k, (c, jr, nr, dist) in enumerate(paires):
            a = Image.open(io.BytesIO(zipfile.ZipFile(c["zip"]).read(c["image"]))).convert("RGB")
            if jr == "comptage_v6_5cm":
                b = Image.open(Path(args.v6) / nr).convert("RGB")
            else:
                b = Image.open(io.BytesIO(zipfile.ZipFile(Path(args.roboflow) / f"{jr}.zip").read(nr))).convert("RGB")
            for m, im in enumerate((a, b)):
                im.thumbnail((cc, cc)); pl.paste(im, (m * (cc + 10), k * (cc + 16)))
            dr.text((2, k * (cc + 16) + cc + 2), f"{c['jeu']} | {jr} ({dist} bits)", fill="black")
        pl.save(out / "planche_doublons.jpg", quality=85)


if __name__ == "__main__":
    main()
