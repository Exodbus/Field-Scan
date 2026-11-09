#!/usr/bin/env python3
"""Sélection des images de la mesure khadavy (docs/protocole_maladies_test_khadavy.md, section 3), sans modèle.

khadavy (export « folder ») :
  - photo d'origine = nom du fichier sans le suffixe Roboflow « _jpg.rf.<empreinte>.jpg » ;
  - photos distinctes = groupes de photos d'origine reliées par un quasi-doublon (même méthode que
    scripts/verifier_jeux_maladies.py : dHash à au plus 10 bits puis vignette 16 x 16 à au plus 5, sous les
    8 symétries) ; un groupe qui mêlerait deux classes arrête le script ;
  - une image par groupe : d'abord les parties test ou valid (non augmentées), sinon train ; la première par nom.
Jeux indicatifs (section 7) : ROAMER Black-sigatoka et panama wilt in banana, une image par photo d'origine
(test ou valid d'abord), étiquette d'image = ensemble des classes de ses annotations.

Sorties dans --out : images/<jeu>/<fichier> (copies extraites des zips), liste.csv (jeu, groupe, classe,
image, partie, fichier, sha256), empreinte.txt (SHA-256 de liste.csv). Aucun modèle n'est utilisé.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/selectionner_test_khadavy.py
"""
import argparse
import hashlib
import io
import json
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
from verifier_jeux_maladies import NV, comparer, reduire, variantes  # noqa: E402

ORDRE_PARTIES = {"test": 0, "valid": 1, "train": 2}
SUFFIXE = re.compile(r"_(jpe?g|png)\.rf\.[0-9a-f]+\.(jpe?g|png)$", re.I)


def origine(nom):
    return SUFFIXE.sub(r".\1", nom)


def lire_khadavy(chemin):
    z = zipfile.ZipFile(chemin)
    lignes = []
    for n in sorted(z.namelist()):
        if not n.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        partie, classe, fichier = n.split("/")[0], n.split("/")[1], n.split("/")[-1]
        lignes.append(dict(image=n, partie=partie, classe=classe, origine=f"{classe}/{origine(fichier)}"))
    return pd.DataFrame(lignes), z


def lire_coco(chemin):
    z = zipfile.ZipFile(chemin)
    lignes = []
    for n in sorted(z.namelist()):
        if not n.endswith("_annotations.coco.json"):
            continue
        partie = n.rsplit("/", 1)[0]
        d = json.loads(z.read(n))
        racine = {c["id"] for c in d["categories"] if c.get("supercategory") == "none"}
        cat = {c["id"]: c["name"] for c in d["categories"]}
        par_image = {}
        for a in d["annotations"]:
            if a["category_id"] not in racine:
                par_image.setdefault(a["image_id"], set()).add(cat[a["category_id"]])
        for im in d["images"]:
            nom = (im.get("extra") or {}).get("name") or origine(im["file_name"])
            lignes.append(dict(image=f"{partie}/{im['file_name']}", partie=partie, origine=nom,
                               classe="+".join(sorted(par_image.get(im["id"], set()))) or "sans_annotation"))
    return pd.DataFrame(lignes), z


def groupes_quasi_doublons(df, z, seuil_h, seuil_v):
    """Indice de groupe par image : photos d'origine reliées par un quasi-doublon (union-find)."""
    hs, vs = [], []
    for n in df.image:
        for t in variantes(reduire(Image.open(io.BytesIO(z.read(n))))):
            hs.append(dhash(t)); vs.append(vignette(t))
    V = np.stack(vs).astype(np.int16)
    org = pd.factorize(df.origine)[0]
    _, _, I, J, _ = comparer(hs, V, hs[::NV], V[::NV], seuil_h, seuil_v,
                             exclure=lambda i, j: org[i // NV] == org[j])
    parent = list(range(org.max() + 1))

    def racine(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in zip(org[I // NV], org[J]):
        parent[racine(a)] = racine(b)
    return np.array([racine(o) for o in org])


def choisir(df, cle):
    """Une image par valeur de cle : test, puis valid, puis train ; la première par nom."""
    return (df.assign(_o=df.partie.map(ORDRE_PARTIES).fillna(9))
              .sort_values(["_o", "image"]).drop_duplicates(cle).drop(columns="_o"))


def extraire(sel, z, jeu, dossier):
    d = dossier / "images" / jeu
    d.mkdir(parents=True, exist_ok=True)
    fichiers, empreintes = [], []
    for k, n in enumerate(sel.image):
        octets = z.read(n)
        f = f"{k:04d}_{Path(n).name}"
        (d / f).write_bytes(octets)
        fichiers.append(f"images/{jeu}/{f}")
        empreintes.append(hashlib.sha256(octets).hexdigest())
    return sel.assign(jeu=jeu, fichier=fichiers, sha256=empreintes)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dossier", default="data/roboflow_maladies/nouveaux")
    ap.add_argument("--out", default="data/test_khadavy")
    ap.add_argument("--seuil-candidat", type=int, default=10)
    ap.add_argument("--seuil-vignette", type=float, default=5.0)
    args = ap.parse_args(argv)
    src, out = Path(args.dossier), Path(args.out)
    if (out / "liste.csv").exists():
        sys.exit(f"{out / 'liste.csv'} existe déjà : la liste est figée, rien n'est réécrit.")

    df, z = lire_khadavy(src / "khadavy.zip")
    df["groupe"] = groupes_quasi_doublons(df, z, args.seuil_candidat, args.seuil_vignette)
    melanges = df.groupby("groupe").classe.nunique()
    if (melanges > 1).any():
        sys.exit(f"{int((melanges > 1).sum())} groupes mêlent deux classes : à examiner avant toute sélection.")
    k = extraire(choisir(df, "groupe"), z, "khadavy", out)
    print(f"khadavy : {len(df)} fichiers, {df.origine.nunique()} photos d'origine, {len(k)} photos distinctes "
          f"{k.classe.value_counts().to_dict()} ; parties {k.partie.value_counts().to_dict()}")

    parts = [k]
    for jeu, fichier in (("roamer_black_sigatoka", "roamer_black_sigatoka.zip"), ("research_panama", "research_panama.zip")):
        d, zz = lire_coco(src / fichier)
        d["groupe"] = pd.factorize(d.origine)[0]
        s = extraire(choisir(d, "origine"), zz, jeu, out)
        print(f"{jeu} : {len(d)} fichiers, {len(s)} photos d'origine {s.classe.value_counts().to_dict()}")
        parts.append(s)

    liste = pd.concat(parts)[["jeu", "groupe", "classe", "partie", "image", "fichier", "sha256"]]
    liste.to_csv(out / "liste.csv", index=False, encoding="utf-8", lineterminator="\n")
    h = hashlib.sha256((out / "liste.csv").read_bytes()).hexdigest()
    (out / "empreinte.txt").write_text(f"{h}  liste.csv\n", encoding="utf-8")
    print("SHA-256 de liste.csv :", h)


if __name__ == "__main__":
    main()
