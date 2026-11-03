#!/usr/bin/env python3
"""Inspection de jeux exportés par Roboflow au format COCO (zip), avant toute utilisation.

Pour chaque zip : textes d'accompagnement (licence, prétraitements, augmentations), statistiques par partie
(images, taille, plants par image, taille des boîtes en pixels), nombre d'images d'origine (Roboflow nomme
les copies augmentées « nom_jpg.rf.<code>.jpg »), et une planche d'images tirées au hasard avec leurs boîtes.

Exemple :
    python scripts/inspecter_roboflow.py data/roboflow/count_banana_plants.zip data/roboflow/plants_bana.zip
"""
import argparse
import io
import json
import random
import re
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

import numpy as np
from PIL import Image, ImageDraw

RE_ORIGINE = re.compile(r"^(.*?)(?:_(jpg|jpeg|png))?\.rf\.[0-9a-f]+\.(jpg|jpeg|png)$", re.IGNORECASE)


def origine(nom):
    m = RE_ORIGINE.match(nom)
    return m.group(1) if m else PurePosixPath(nom).stem


def inspecter(chemin_zip, sortie, n_planche, graine):
    z = zipfile.ZipFile(chemin_zip)
    noms = z.namelist()
    nom_jeu = Path(chemin_zip).stem
    dossier = Path(sortie) / nom_jeu
    dossier.mkdir(parents=True, exist_ok=True)
    print(f"\n========== {nom_jeu} ==========")
    for lisez in [n for n in noms if PurePosixPath(n).name.lower().startswith("readme")]:
        texte = z.read(lisez).decode("utf-8", "ignore").strip()
        (dossier / PurePosixPath(lisez).name).write_text(texte, encoding="utf-8")
        print(f"--- {lisez} ---\n{texte[:1500]}")
    annotations = [n for n in noms if n.endswith("_annotations.coco.json")]
    if not annotations:
        print("Aucun fichier _annotations.coco.json : exporter le jeu au format COCO.")
        return None
    bilan, toutes = {}, []
    for a in sorted(annotations):
        partie = PurePosixPath(a).parent.name or "racine"
        coco = json.loads(z.read(a))
        cats = {c["id"]: c["name"] for c in coco.get("categories", [])}
        par_image = Counter(an["image_id"] for an in coco.get("annotations", []))
        boites = np.array([an["bbox"][2:] for an in coco.get("annotations", [])] or [[np.nan, np.nan]], dtype=float)
        tailles = Counter((im["width"], im["height"]) for im in coco["images"])
        n_plants = np.array([par_image.get(im["id"], 0) for im in coco["images"]])
        origines = {origine(im["file_name"]) for im in coco["images"]}
        bilan[partie] = dict(images=len(coco["images"]), images_origine=len(origines),
                             tailles_images=dict(Counter({f"{l}x{h}": n for (l, h), n in tailles.items()}).most_common(3)),
                             categories=sorted(set(cats.values())),
                             annotations_par_categorie=dict(Counter(cats.get(an["category_id"], "?") for an in coco.get("annotations", []))),
                             plants_par_image=dict(min=int(n_plants.min()), mediane=float(np.median(n_plants)), max=int(n_plants.max()),
                                                   images_sans_plant=int((n_plants == 0).sum())),
                             boites_px=dict(largeur_mediane=round(float(np.nanmedian(boites[:, 0])), 1),
                                            hauteur_mediane=round(float(np.nanmedian(boites[:, 1])), 1)))
        base = str(PurePosixPath(a).parent)
        for im in coco["images"]:
            bb = [an["bbox"] for an in coco.get("annotations", []) if an["image_id"] == im["id"]]
            toutes.append((partie, f"{base}/{im['file_name']}" if base != "." else im["file_name"], bb))
    for partie, b in bilan.items():
        print(f"\n[{partie}] {b['images']} images ({b['images_origine']} d'origine) | tailles {b['tailles_images']} | "
              f"catégories {b['annotations_par_categorie']}\n   plants par image : {b['plants_par_image']} | boîtes (px) : {b['boites_px']}")
    total = sum(b["images"] for b in bilan.values())
    orig = len({origine(PurePosixPath(c).name) for _, c, _ in toutes})
    print(f"\nTotal : {total} images, {orig} images d'origine distinctes "
          f"({total / max(orig, 1):.1f} variantes par image d'origine)")
    origines_parties = {}
    for p, c, _ in toutes:
        origines_parties.setdefault(origine(PurePosixPath(c).name), set()).add(p)
    fuites = sum(len(v) > 1 for v in origines_parties.values())
    print(f"Images d'origine présentes dans plusieurs parties (fuite entre entraînement et test) : {fuites}")

    rng = random.Random(graine)
    tirage = rng.sample(toutes, min(n_planche, len(toutes)))
    c, col = 300, 4
    lignes = (len(tirage) + col - 1) // col
    planche = Image.new("RGB", (col * c, lignes * (c + 16)), "white")
    d = ImageDraw.Draw(planche)
    for k, (partie, chemin, bb) in enumerate(tirage):
        try:
            im = Image.open(io.BytesIO(z.read(chemin))).convert("RGB")
        except KeyError:
            continue
        dim = ImageDraw.Draw(im)
        for x, y, l, h in bb:
            dim.rectangle([x, y, x + l, y + h], outline=(255, 0, 0), width=max(1, im.width // 300))
        taille = im.size
        im.thumbnail((c - 4, c - 4))
        x0, y0 = (k % col) * c, (k // col) * (c + 16)
        planche.paste(im, (x0 + 2, y0 + 2))
        d.text((x0 + 3, y0 + c - 2), f"{partie} | {taille[0]}x{taille[1]} | {len(bb)} plants", fill="black")
    planche.save(dossier / "planche.jpg", quality=88)
    (dossier / "bilan.json").write_text(json.dumps(dict(parties=bilan, images=total, images_origine=orig,
                                                        fuites_entre_parties=fuites), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Planche : {dossier / 'planche.jpg'}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zips", nargs="+")
    ap.add_argument("--out", default="out/roboflow")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--graine", type=int, default=2026)
    args = ap.parse_args(argv)
    for z in args.zips:
        inspecter(z, args.out, args.n, args.graine)


if __name__ == "__main__":
    main()
