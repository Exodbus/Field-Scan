#!/usr/bin/env python3
"""Sélection du test banana-buddy (docs/protocole_maladies_v3_convnext.md, section 7), sans modèle.

  - photo d'origine = classe + nom du fichier sans le suffixe Roboflow ; toute photo nommée « Image_N »
    (format de la Tanzanie) est exclue ;
  - groupes de quasi-doublons entre photos d'origine (dHash à au plus 10 bits puis vignette 16 x 16 à au
    plus 5, sous les 8 symétries) ;
  - un groupe est exclu si l'une de ses images est proche (écart <= 5) d'une référence : index des feuilles
    (Tanzanie 2021, Tanzanie 2022-2023 locale, Pérou, BananaLSD, Banana Disease Recognition), campagne 2021
    complète (zips à tiret bas), khadavy, TDTU ; ou s'il mêle deux classes de référence ;
  - une image par groupe : test, puis valid, puis train ; la première par nom.

Sorties dans --out : images/banana_buddy/<fichier>, liste.csv, empreinte.txt, planche.jpg, exclusions.csv.
Refuse de réécrire une liste existante.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/selectionner_test_banana_buddy.py
"""
import argparse
import hashlib
import io
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
from preparer_feuilles import dhash, vignette  # noqa: E402
from selectionner_test_khadavy import choisir, extraire, lire_khadavy  # noqa: E402
from verifier_jeux_maladies import NV, comparer, par_image, planche, reduire, references, variantes  # noqa: E402

CLASSE_REF = {"Healthy": "saine", "Healthy Leaf": "saine", "Panama": "fusariose", "Panama Leaf": "fusariose",
              "Leafspot": "taches", "Leafspot Leaf": "taches"}


def empreintes(images):
    hs, vs = [], []
    for im in images:
        for t in variantes(reduire(im)):
            hs.append(dhash(t)); vs.append(vignette(t))
    return hs, np.stack(vs).astype(np.int16)


def simples(images):
    hs, vs = [], []
    for im in images:
        im = reduire(im); hs.append(dhash(im)); vs.append(vignette(im))
    return hs, np.stack(vs).astype(np.int16)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", default="data/roboflow_maladies/nouveaux/banana_buddy.zip")
    ap.add_argument("--out", default="data/test_banana_buddy")
    ap.add_argument("--seuil-candidat", type=int, default=10)
    ap.add_argument("--seuil-vignette", type=float, default=5.0)
    args = ap.parse_args(argv)
    out, sh, sv = RACINE / args.out, args.seuil_candidat, args.seuil_vignette
    if (out / "liste.csv").exists():
        sys.exit(f"{out / 'liste.csv'} existe déjà : la liste est figée, rien n'est réécrit.")

    df, z = lire_khadavy(RACINE / args.zip)
    df["nom"] = df.origine.str.split("/").str[-1]
    n0 = df.origine.nunique()
    tanz = df.nom.str.match(r"^Image_\d+\.", na=False)
    exclusions = [dict(origine=o, motif="nom_tanzanien") for o in df[tanz].origine.unique()]
    df = df[~tanz].reset_index(drop=True)
    df["classe_ref"] = df.classe.map(CLASSE_REF)
    print(f"{n0} photos d'origine, {len(exclusions)} au format tanzanien exclues, reste {df.origine.nunique()} "
          f"({len(df)} fichiers)", flush=True)

    hs, V = empreintes(Image.open(io.BytesIO(z.read(n))) for n in df.image)

    # références : index des feuilles (cache existant), campagne 2021 complète (cache), khadavy, TDTU
    rh, rv, rsrc, _ = references(RACINE / "data/feuilles/index.csv",
                                 RACINE / "data/raw/banana_disease_recognition/extrait/Original Images",
                                 RACINE / "out/maladies/roboflow/references.npz")
    rv = [np.asarray(rv)]
    c = np.load(RACINE / "out/maladies/roboflow_nouveaux/fuite_tanzanie_complete/references_tanzanie_2022_complete.npz",
                allow_pickle=True)  # nom historique : ce sont les zips 2021 (tiret bas) et healthy_1 2022
    rh = list(rh) + list(c["h"]); rv.append(c["v"]); rsrc = list(rsrc) + ["tanzanie_2021_complete"] * len(c["h"])
    kh = sorted((RACINE / "data/test_khadavy/images/khadavy").glob("*"))
    h, v = simples(Image.open(f) for f in kh)
    rh += h; rv.append(v); rsrc += ["khadavy"] * len(h)
    zt = zipfile.ZipFile(RACINE / "data/roboflow_maladies/tdtu_vietnam.zip")
    nt = [n for n in zt.namelist() if n.lower().endswith((".jpg", ".jpeg", ".png"))]
    h, v = simples(Image.open(io.BytesIO(zt.read(n))) for n in nt)
    rh += h; rv.append(v); rsrc += ["tdtu"] * len(h)
    RV = np.concatenate(rv).astype(np.int16)
    print(f"références : {len(rh)} images {pd.Series(rsrc).value_counts().to_dict()}", flush=True)

    m, j = par_image(*comparer(hs, V, rh, RV, sh, sv)[:2])
    df["ecart_ref"] = np.round(m, 2)
    df["source_ref"] = [rsrc[k] if k >= 0 else "" for k in j]

    # groupes de quasi-doublons entre photos d'origine
    org = pd.factorize(df.origine)[0]
    _, _, I, J, _ = comparer(hs, V, hs[::NV], V[::NV], sh, sv, exclure=lambda i, j: org[i // NV] == org[j])
    parent = list(range(org.max() + 1))

    def racine(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in zip(org[I // NV], org[J]):
        parent[racine(a)] = racine(b)
    df["groupe"] = [racine(o) for o in org]

    g = df.groupby("groupe")
    fuite = g.ecart_ref.min() <= sv
    melange = g.classe_ref.nunique() > 1
    for gr in fuite[fuite].index:
        exclusions += [dict(origine=o, motif=f"proche_{df[df.groupe.eq(gr)].sort_values('ecart_ref').source_ref.iat[0]}")
                       for o in df[df.groupe.eq(gr)].origine.unique()]
    for gr in melange[melange & ~fuite].index:
        exclusions += [dict(origine=o, motif="groupe_deux_classes") for o in df[df.groupe.eq(gr)].origine.unique()]
    garde = df[~df.groupe.isin(fuite[fuite].index.union(melange[melange].index))]
    sel = choisir(garde, "groupe")
    print(f"groupes : {df.groupe.nunique()} ; exclus pour proximité {int(fuite.sum())}, pour deux classes "
          f"{int((melange & ~fuite).sum())} ; retenus {len(sel)}", flush=True)

    out.mkdir(parents=True, exist_ok=True)
    k = extraire(sel, z, "banana_buddy", out)
    liste = k.assign(classe_ref=k.classe.map(CLASSE_REF),
                     vue=np.where(k.classe.str.endswith(" Leaf"), "gros_plan", "vue_large"))
    liste = liste[["jeu", "groupe", "classe", "classe_ref", "vue", "partie", "image", "fichier", "sha256"]]
    liste.to_csv(out / "liste.csv", index=False, encoding="utf-8", lineterminator="\n")
    pd.DataFrame(exclusions).to_csv(out / "exclusions.csv", index=False, encoding="utf-8", lineterminator="\n")
    planche(sel.assign(classes=sel.classe), z, out / "planche.jpg")
    hl = hashlib.sha256((out / "liste.csv").read_bytes()).hexdigest()
    (out / "empreinte.txt").write_text(f"{hl}  liste.csv\n", encoding="utf-8")
    print(pd.crosstab(liste.classe, liste.partie, margins=True).to_string())
    print(pd.Series([e["motif"] for e in exclusions]).value_counts().to_string())
    print("SHA-256 de liste.csv :", hl)


if __name__ == "__main__":
    main()
