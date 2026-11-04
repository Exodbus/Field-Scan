#!/usr/bin/env python3
"""Compare deux annotations Roboflow des MÊMES découpes (ex. Plants-bana et Count banana plants), sans aucun modèle.

Les deux jeux contiennent des découpes identiques sous le même nom d'origine (au suffixe « _jpg » près), à des
tailles différentes (Count : 480 px ; Plants-bana : 256 px). Pour chaque découpe commune : nombre de boîtes de
chaque jeu, et appariement des centres (une boîte de A et une de B « se correspondent » si leurs centres, ramenés à
la même échelle, sont à moins de --distance fois la taille médiane des boîtes). Sorties : comparaison.csv,
bilan par groupe à l'écran, planches côte à côte (A à gauche, B à droite) pour un tirage de découpes.

Exemple :
    python scripts/comparer_annotations_roboflow.py --groupes 100_022 corte --n 12
"""
import argparse
import io
import json
import random
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verifier_sources_communes import origine  # noqa: E402

BANANE = {"Banana", "Banana-plant"}


def charger(chemin_zip):
    """{origine sans _jpg: (nom dans le zip, largeur, liste de boîtes bananier x, y, w, h)}"""
    z = zipfile.ZipFile(chemin_zip)
    out = {}
    for part in ["train", "valid", "test"]:
        d = json.loads(z.read(f"{part}/_annotations.coco.json"))
        cat = {c["id"]: c["name"] for c in d["categories"]}
        bo = {}
        for a in d["annotations"]:
            if cat[a["category_id"]] in BANANE:
                bo.setdefault(a["image_id"], []).append(a["bbox"])
        for im in d["images"]:
            o = re.sub(r"_(jpg|jpeg|png)$", "", origine(im["file_name"]))
            out.setdefault(o, (f"{part}/{im['file_name']}", im["width"], np.array(bo.get(im["id"], []), float).reshape(-1, 4)))
    return z, out


def centres(b, f):
    return np.c_[b[:, 0] + b[:, 2] / 2, b[:, 1] + b[:, 3] / 2] * f if len(b) else np.zeros((0, 2))


def apparier(ca, cb, seuil):
    if not len(ca) or not len(cb):
        return 0
    d = np.linalg.norm(ca[:, None] - cb[None], axis=2)
    i, j = linear_sum_assignment(d)
    return int((d[i, j] <= seuil).sum())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", default="data/roboflow/plants_bana_originaux.zip")
    ap.add_argument("--b", default="data/roboflow/count_banana_plants.zip")
    ap.add_argument("--groupes", nargs="+", default=["100_022", "corte"], help="préfixes des noms d'origine")
    ap.add_argument("--distance", type=float, default=0.5, help="seuil d'appariement, en tailles médianes de boîte")
    ap.add_argument("--n", type=int, default=12, help="découpes dans la planche")
    ap.add_argument("--cote", type=int, default=640)
    ap.add_argument("--graine", type=int, default=2026)
    ap.add_argument("--out", default="out/comparaison_annotations")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    za, A = charger(args.a)
    zb, B = charger(args.b)
    communs = sorted(o for o in set(A) & set(B) if o.startswith(tuple(args.groupes)))
    lignes = []
    for o in communs:
        (na, la, ba), (nb, lb, bb) = A[o], B[o]
        # tout ramené à l'échelle de B
        ca, cb = centres(ba, lb / la), centres(bb, 1.0)
        tailles = np.r_[(ba[:, 2:] * lb / la).mean(1), bb[:, 2:].mean(1)] if len(ba) + len(bb) else np.array([1.0])
        seuil = args.distance * float(np.median(tailles))
        m = apparier(ca, cb, seuil)
        lignes.append(dict(origine=o, groupe=next(g for g in args.groupes if o.startswith(g)), boites_a=len(ba),
                           boites_b=len(bb), communes=m, seulement_a=len(ba) - m, seulement_b=len(bb) - m,
                           taille_mediane_px_b=round(float(np.median(tailles)), 1)))
    df = pd.DataFrame(lignes)
    df.to_csv(out / "comparaison.csv", index=False)
    print(f"A = {Path(args.a).name}, B = {Path(args.b).name} ; {len(df)} découpes communes ; appariement à "
          f"{args.distance} taille de boîte")
    bilan = df.groupby("groupe")[["boites_a", "boites_b", "communes", "seulement_a", "seulement_b"]].sum()
    bilan["decoupes"] = df.groupby("groupe").size()
    print(bilan.to_string())
    print(f"découpes où A a plus de boîtes : {(df.boites_a > df.boites_b).sum()} ; où B en a plus : "
          f"{(df.boites_b > df.boites_a).sum()} ; égalité : {(df.boites_a == df.boites_b).sum()}")

    # Planche : A à gauche, B à droite ; boîtes communes en blanc, propres à un jeu en magenta
    tirage = list(communs)
    random.Random(args.graine).shuffle(tirage)
    paires = []
    for o in tirage[:args.n]:
        (na, la, ba), (nb, lb, bb) = A[o], B[o]
        ca, cb = centres(ba, lb / la), centres(bb, 1.0)
        tailles = np.r_[(ba[:, 2:] * lb / la).mean(1), bb[:, 2:].mean(1)] if len(ba) + len(bb) else np.array([1.0])
        seuil = args.distance * float(np.median(tailles))
        ok_a, ok_b = np.zeros(len(ba), bool), np.zeros(len(bb), bool)
        if len(ca) and len(cb):
            d = np.linalg.norm(ca[:, None] - cb[None], axis=2)
            i, j = linear_sum_assignment(d)
            garde = d[i, j] <= seuil
            ok_a[i[garde]], ok_b[j[garde]] = True, True
        vues = []
        for z, nom, larg, bo, ok, titre in [(za, na, la, ba, ok_a, "A"), (zb, nb, lb, bb, ok_b, "B")]:
            img = Image.open(io.BytesIO(z.read(nom))).convert("RGB")
            f = args.cote / img.width
            img = img.resize((args.cote, round(img.height * f)))
            dr = ImageDraw.Draw(img)
            for (x, y, w, h), commun in zip(bo, ok):
                dr.rectangle([x * f, y * f, (x + w) * f, (y + h) * f], outline=(255, 255, 255) if commun else (255, 43, 214), width=3)
            dr.rectangle([0, 0, args.cote, 22], fill=(0, 0, 0))
            dr.text((5, 5), f"{titre} : {o[:40]} | {len(bo)} boîtes, {int((~ok).sum())} propres à {titre}", fill=(255, 255, 255))
            vues.append(img)
        paires.append(vues)
    if paires:
        h = max(v.height for p in paires for v in p)
        planche = Image.new("RGB", (2 * args.cote + 10, len(paires) * (h + 12)), "white")
        for k, (va, vb) in enumerate(paires):
            planche.paste(va, (0, k * (h + 12)))
            planche.paste(vb, (args.cote + 10, k * (h + 12)))
        for debut in range(0, len(paires), 4):            # planches de 4 paires, lisibles
            planche.crop((0, debut * (h + 12), planche.width, min(len(paires), debut + 4) * (h + 12))).save(
                out / f"planche_{debut // 4 + 1}.jpg", quality=88)
        print(f"planches -> {out}")


if __name__ == "__main__":
    main()
