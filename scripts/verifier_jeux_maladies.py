#!/usr/bin/env python3
"""Vérification de jeux Roboflow candidats pour le module maladies, sans modèle.

Pour chaque export COCO (détection ou segmentation) :
  - étiquette par image : l'ensemble des classes présentes dans ses annotations (la catégorie racine de
    Roboflow, de supercatégorie « none », et toute classe du même nom, comme le contour de la feuille,
    sont ignorées) ; « sans_annotation » sinon ;
  - copies augmentées : Roboflow garde le nom d'origine dans images[].extra.name ; les images qui partagent
    ce nom sont des copies d'une même photo ;
  - fuites : chaque image, sous ses 8 symétries (miroirs, rotations de 90, 180 et 270°, transpositions),
    est comparée aux jeux déjà utilisés (index des feuilles : Tanzanie 2021 et 2022, Pérou, BananaLSD ;
    et les originaux de Banana Disease Recognition, futur test) avec la méthode du module maladies :
    empreinte dHash 64 bits (au plus --seuil-candidat bits) puis vignette 16 x 16 en couleur (écart moyen
    au plus --seuil-vignette sur 255) ;
  - doublons internes : même méthode entre photos d'origine différentes d'un même jeu ; le nombre de
    photos distinctes compte les groupes de copies ;
  - copies entre candidats : même méthode, d'un candidat à l'autre ;
  - planches : 48 photos d'origine tirées au hasard (graine 2026) avec leur étiquette ; les paires les
    plus proches d'une référence (contrôle à l'œil des quasi-fuites) ; les doublons internes les moins
    sûrs (contrôle à l'œil des regroupements).

Sorties dans --out : <jeu>/images.csv, <jeu>/doublons.csv, <jeu>/planche.jpg, <jeu>/paires_references.jpg,
<jeu>/paires_internes.jpg, bilan.csv. Aucun modèle n'est utilisé.

Exemple :
    python scripts/verifier_jeux_maladies.py data/roboflow_maladies/*.zip
"""
import argparse
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageOps

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
from preparer_feuilles import dhash, vignette  # noqa: E402

COTE = 256
NV = 8  # variantes par image : les 8 symétries du carré


def reduire(im, cote=COTE):
    im = ImageOps.exif_transpose(im).convert("RGB")
    r = cote / min(im.size)
    return im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS) if r < 1 else im


def variantes(im):
    """Identité, miroirs, rotations de 180, 90 et 270°, transpositions (dans cet ordre)."""
    T = Image.Transpose
    return (im, im.transpose(T.FLIP_LEFT_RIGHT), im.transpose(T.FLIP_TOP_BOTTOM), im.transpose(T.ROTATE_180),
            im.transpose(T.ROTATE_90), im.transpose(T.ROTATE_270), im.transpose(T.TRANSPOSE),
            im.transpose(T.TRANSVERSE))


def selection_references(index_csv, bdr):
    idx = pd.read_csv(index_csv)
    idx = idx[(idx.retenue | idx.source.eq("bananalsd")) & idx.chemin.notna() & idx.dhash.notna()]
    fichiers_bdr = sorted(Path(bdr).rglob("*.jpg"))
    chemins = [Path(index_csv).parent / c for c in idx.chemin] + fichiers_bdr
    src = [f"{s}/{e}" for s, e in zip(idx.source, idx.ensemble)] + ["banana_disease_recognition/test"] * len(fichiers_bdr)
    return chemins, src, [int(x, 16) for x in idx.dhash]


def references(index_csv, bdr, cache):
    chemins, src, h_index = selection_references(index_csv, bdr)
    if cache.exists():
        d = np.load(cache, allow_pickle=True)
        if list(d["src"]) == src:
            return list(d["h"]), np.asarray(d["v"], dtype=np.int16), src, chemins
    h, v = list(h_index), []
    for k, c in enumerate(chemins):
        im = reduire(Image.open(c))
        v.append(vignette(im))
        if k >= len(h_index):
            h.append(dhash(im))
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, h=np.array(h, dtype=object), v=np.stack(v), src=np.array(src))
    return h, np.stack(v).astype(np.int16), src, chemins


def comparer(hA, VA, hB, VB, seuil_h, seuil_v, exclure=None, morceau=500, lot=20000):
    """Pour chaque ligne de A : plus petit écart de vignette parmi les lignes de B à au plus seuil_h bits
    d'empreinte (inf sans candidat) et l'indice correspondant ; plus toutes les paires (i, j, écart) à au
    plus seuil_v. exclure(i, j) renvoie le masque des paires à ignorer."""
    a, b = np.asarray(hA, dtype=np.uint64), np.asarray(hB, dtype=np.uint64)
    meilleur, arg = np.full(len(a), np.inf), np.full(len(a), -1)
    I, J, E = [], [], []
    for s in range(0, len(a), morceau):
        li, j = np.nonzero(np.bitwise_count(a[s:s + morceau, None] ^ b[None, :]) <= seuil_h)
        i = li + s
        if exclure is not None:
            g = ~exclure(i, j)
            i, j = i[g], j[g]
        for t in range(0, len(i), lot):
            ii, jj = i[t:t + lot], j[t:t + lot]
            e = np.abs(VA[ii] - VB[jj]).mean(axis=(1, 2, 3))
            np.minimum.at(meilleur, ii, e)
            m = e <= meilleur[ii]
            arg[ii[m]] = jj[m]
            m = e <= seuil_v
            I.append(ii[m]); J.append(jj[m]); E.append(e[m])
    cat = lambda L, t: np.concatenate(L) if L else np.array([], t)  # noqa: E731
    return meilleur, arg, cat(I, int), cat(J, int), cat(E, float)


def par_image(meilleur, arg):
    """Réduit les NV variantes de chaque image à la meilleure."""
    m = meilleur.reshape(-1, NV)
    k = m.argmin(axis=1)
    return m[np.arange(len(m)), k], arg.reshape(-1, NV)[np.arange(len(m)), k]


def lire_export(chemin):
    z = zipfile.ZipFile(chemin)
    lignes = []
    for n in z.namelist():
        if not n.endswith("_annotations.coco.json"):
            continue
        part = n.rsplit("/", 1)[0] if "/" in n else ""
        d = json.loads(z.read(n))
        # catégorie racine (supercatégorie « none ») et classe homonyme du contour de la feuille : pas des étiquettes
        noms_racine = {c["name"] for c in d["categories"] if c.get("supercategory") == "none"}
        racine = {c["id"] for c in d["categories"] if c["name"] in noms_racine}
        cat = {c["id"]: c["name"] for c in d["categories"]}
        par_image = {}
        for a in d["annotations"]:
            if a["category_id"] not in racine:
                par_image.setdefault(a["image_id"], []).append(cat[a["category_id"]])
        for im in d["images"]:
            chemin_zip = f"{part}/{im['file_name']}" if part else im["file_name"]
            classes = sorted(set(par_image.get(im["id"], [])))
            origine = (im.get("extra") or {}).get("name") or re.sub(r"_(jpe?g|png)\.rf\.[0-9a-f]+\.(jpe?g|png)$", r".\1",
                                                                       im["file_name"], flags=re.I)
            lignes.append(dict(image=chemin_zip, partie=part, origine=origine, classes="+".join(classes) or "sans_annotation",
                               n_annotations=len(par_image.get(im["id"], []))))
    return pd.DataFrame(lignes), z


def ouvrir(z, nom):
    return Image.open(io.BytesIO(z.read(nom)))


def planche(df, z, sortie, n=48, graine=2026):
    orig = df.drop_duplicates("origine")
    tirage = orig.sample(min(n, len(orig)), random_state=graine)
    c, t = 8, 160
    L = (len(tirage) + c - 1) // c
    pl = Image.new("RGB", (c * t, L * (t + 28)), "white")
    dr = ImageDraw.Draw(pl)
    for i, r in enumerate(tirage.itertuples()):
        x, y = (i % c) * t, (i // c) * (t + 28)
        im = ouvrir(z, r.image).convert("RGB")
        im.thumbnail((t, t))
        pl.paste(im, (x, y))
        dr.text((x + 2, y + t + 2), r.classes[:26], fill="black")
        dr.text((x + 2, y + t + 14), r.origine[:26], fill="gray")
    pl.save(sortie, quality=85)


def planche_paires(paires, sortie, t=150):
    """paires : liste de (image gauche, image droite, texte) ; 4 paires par ligne."""
    if not paires:
        return
    c, marge = 4, 14
    L = (len(paires) + c - 1) // c
    pl = Image.new("RGB", (c * 2 * t + (c - 1) * marge, L * (t + 18)), "white")
    dr = ImageDraw.Draw(pl)
    for i, (g, d, texte) in enumerate(paires):
        x, y = (i % c) * (2 * t + marge), (i // c) * (t + 18)
        for k, im in enumerate((g, d)):
            im = im.convert("RGB")
            im.thumbnail((t, t))
            pl.paste(im, (x + k * t, y))
        dr.text((x + 2, y + t + 3), texte[:48], fill="black")
    pl.save(sortie, quality=85)


def groupes(n_origines, paires):
    """Nombre de photos distinctes : composantes connexes des photos d'origine reliées par une paire."""
    parent = list(range(n_origines))

    def racine(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in paires:
        ra, rb = racine(a), racine(b)
        if ra != rb:
            parent[ra] = rb
    return len({racine(x) for x in range(n_origines)})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("exports", nargs="+")
    ap.add_argument("--index", default="data/feuilles/index.csv")
    ap.add_argument("--bdr", default="data/raw/banana_disease_recognition/extrait/Original Images")
    ap.add_argument("--out", default="out/maladies/roboflow")
    ap.add_argument("--seuil-candidat", type=int, default=10)
    ap.add_argument("--seuil-vignette", type=float, default=5.0)
    ap.add_argument("--limite-paires", type=float, default=25.0, help="écart maximal des paires montrées à l'œil")
    args = ap.parse_args(argv)
    sh, sv = args.seuil_candidat, args.seuil_vignette
    out = Path(args.out)
    ref_h, ref_v, ref_src, ref_chemins = references(args.index, args.bdr, out / "references.npz")
    print(f"références : {len(ref_h)} images ({pd.Series(ref_src).value_counts().to_dict()})")

    bilan, candidats = [], {}
    for chemin in args.exports:
        nom = Path(chemin).stem
        df, z = lire_export(chemin)
        hs, vs = [], []
        for r in df.itertuples():
            for t in variantes(reduire(ouvrir(z, r.image))):
                hs.append(dhash(t)); vs.append(vignette(t))
        V = np.stack(vs).astype(np.int16)
        d = out / nom
        d.mkdir(parents=True, exist_ok=True)

        # fuites vers les références
        m, j = par_image(*comparer(hs, V, ref_h, ref_v, sh, sv)[:2])
        df["ecart_min"] = np.where(np.isfinite(m), np.round(m, 2), np.nan)
        df["fuite"] = m <= sv
        df["fuite_source"] = [ref_src[k] if f else "" for k, f in zip(j, df.fuite)]
        df["reference_proche"] = [str(ref_chemins[k]) if k >= 0 else "" for k in j]
        df["source_proche"] = [ref_src[k] if k >= 0 else "" for k in j]
        proches = df[df.ecart_min <= args.limite_paires].sort_values("ecart_min").head(24)
        planche_paires([(ouvrir(z, r.image), Image.open(r.reference_proche),
                         f"{r.ecart_min:.1f} {r.source_proche}")
                        for r in proches.itertuples()], d / "paires_references.jpg")

        # doublons internes, entre photos d'origine différentes
        org = pd.factorize(df.origine)[0]
        _, _, I, J, E = comparer(hs, V, hs[::NV], V[::NV], sh, sv, exclure=lambda i, j: org[i // NV] == org[j])
        dbl = pd.DataFrame(dict(a=I // NV, b=J, ecart=E))
        dbl[["a", "b"]] = np.sort(dbl[["a", "b"]].to_numpy(), axis=1)
        dbl = dbl.sort_values("ecart").drop_duplicates(["a", "b"])
        distinctes = groupes(org.max() + 1, zip(org[dbl.a], org[dbl.b]))
        pd.DataFrame(dict(image_a=df.image.to_numpy()[dbl.a], image_b=df.image.to_numpy()[dbl.b],
                          ecart=dbl.ecart.round(2))).to_csv(d / "doublons.csv", index=False)
        douteux = dbl.assign(oa=org[dbl.a], ob=org[dbl.b]).drop_duplicates(["oa", "ob"]).tail(24)
        planche_paires([(ouvrir(z, df.image.iat[a]), ouvrir(z, df.image.iat[b]),
                         f"{e:.1f} {df.classes.iat[a][:14]} / {df.classes.iat[b][:14]}")
                        for a, b, e in zip(douteux.a, douteux.b, douteux.ecart)], d / "paires_internes.jpg")

        df.to_csv(d / "images.csv", index=False)
        planche(df, z, d / "planche.jpg")
        candidats[nom] = (hs, V)
        orig = df.drop_duplicates("origine")
        bilan.append(dict(jeu=nom, images=len(df), photos_d_origine=len(orig), photos_distinctes=distinctes,
                          classes=json.dumps(orig.classes.value_counts().to_dict(), ensure_ascii=False),
                          fuites_images=int(df.fuite.sum()),
                          fuites_par_source=json.dumps(df[df.fuite].fuite_source.value_counts().to_dict()),
                          paires_proches=int((df.ecart_min <= args.limite_paires).sum())))
        print(f"{nom} : {len(df)} images, {len(orig)} photos d'origine, {distinctes} distinctes ; "
              f"fuites {int(df.fuite.sum())} {df[df.fuite].fuite_source.value_counts().to_dict()} ; "
              f"écart minimal {np.nanmin(df.ecart_min) if df.ecart_min.notna().any() else '-'}")

    noms = list(candidats)
    for n1 in noms:
        for n2 in noms:
            if n1 == n2:
                continue
            (h1, V1), (h2, V2) = candidats[n1], candidats[n2]
            m, _ = par_image(*comparer(h1, V1, h2[::NV], V2[::NV], sh, sv)[:2])
            if (m <= sv).sum():
                print(f"copies de {n1} dans {n2} : {int((m <= sv).sum())} images")
                next(b for b in bilan if b["jeu"] == n1)[f"copies_dans_{n2}"] = int((m <= sv).sum())
    pd.DataFrame(bilan).to_csv(out / "bilan.csv", index=False)
    print("->", out)


if __name__ == "__main__":
    main()
