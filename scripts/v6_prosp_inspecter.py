#!/usr/bin/env python3
"""Inventaire d'un ou plusieurs exports COCO Roboflow (lecture dans le zip, rien n'est décompressé ni exécuté).

Pour chaque jeu : licence et URL (README), prétraitements et augmentations déclarés, images par partie, images
d'origine distinctes (nom avant « _jpg.rf. »), tailles d'image, annotations par classe, taille médiane des boîtes,
distance médiane au plus proche voisin entre centres de la classe bananier, et estimation d'échelle :
- règle des couronnes : côté médian des boîtes (moyenne largeur/hauteur) ramené à 3 m ;
- règle du plus proche voisin : distance médiane ramenée à 2,5 m (protocole v4, section 3).
Écrit inventaire.json à côté de chaque zip et une ligne par jeu sur la sortie.

Exemple :
    python scripts/v6_prosp_inspecter.py data/roboflow_nuit_1112/comptage/*/*.zip
"""
import argparse
import io
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

import numpy as np
from scipy.spatial import cKDTree

MOTIF = re.compile(r"^(.*?)_(?:jpg|jpeg|png|tif|tiff)\.rf\.", re.IGNORECASE)
BANANE = re.compile(r"banan|platan|plantain|pisang|musa|^0$|^planta", re.I)


def origine(nom):
    b = PurePosixPath(nom).name
    m = MOTIF.match(b)
    return (m.group(1) if m else b.rsplit(".", 1)[0]).lower()


def lire(zp):
    z = zipfile.ZipFile(zp)
    images, annots, cats = {}, [], {}
    for n in z.namelist():
        if n.endswith("_annotations.coco.json"):
            part = PurePosixPath(n).parent.name
            d = json.loads(z.read(n))
            c = {k["id"]: k["name"] for k in d["categories"]}
            cats.update({(part, k): v for k, v in c.items()})
            for im in d["images"]:
                images[(part, im["id"])] = dict(fichier=f"{part}/{im['file_name']}" if part else im["file_name"],
                                                w=im["width"], h=im["height"], part=part)
            for a in d["annotations"]:
                annots.append(dict(img=(part, a["image_id"]), cls=c[a["category_id"]], bbox=a.get("bbox"),
                                   kp=a.get("keypoints")))
    readme = ""
    for n in z.namelist():
        if n.lower().startswith("readme"):
            readme += z.read(n).decode("utf-8", "replace") + "\n"
    return z, images, annots, readme


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zips", nargs="+")
    args = ap.parse_args(argv)
    for zp in args.zips:
        z, images, annots, readme = lire(zp)
        lic = re.search(r"License:\s*(.+)", readme)
        url = re.search(r"https://universe\.roboflow\.com/\S+", readme)
        pre = re.findall(r"^\* (.+)$", readme, re.M)
        par_classe = Counter(a["cls"] for a in annots)
        classes_b = [c for c in par_classe if BANANE.search(str(c))] or list(par_classe)[:1]
        bans = [a for a in annots if a["cls"] in classes_b]
        cotes = [(a["bbox"][2] + a["bbox"][3]) / 2 for a in bans if a["bbox"] and a["bbox"][2] > 0]
        par_img = {}
        for a in bans:
            if a["bbox"] and a["bbox"][2] > 0:
                x, y, w, h = a["bbox"]; c = (x + w / 2, y + h / 2)
            elif a["kp"]:
                c = (a["kp"][0], a["kp"][1])
            else:
                continue
            par_img.setdefault(a["img"], []).append(c)
        ppv = []
        for pts in par_img.values():
            if len(pts) >= 3:
                t = cKDTree(np.array(pts))
                d, _ = t.query(pts, k=2)
                ppv.extend(d[:, 1].tolist())
        tailles = Counter((v["w"], v["h"]) for v in images.values())
        parts = Counter(v["part"] for v in images.values())
        origines = {origine(v["fichier"]) for v in images.values()}
        cote_med = float(np.median(cotes)) if cotes else None
        ppv_med = float(np.median(ppv)) if ppv else None
        inv = dict(zip=str(zp), licence=lic.group(1).strip() if lic else None, url=url.group(0) if url else None,
                   pretraitements=pre, images=len(images), parties=dict(parts), origines_distinctes=len(origines),
                   tailles=[f"{w}x{h}:{n}" for (w, h), n in tailles.most_common(5)], classes=dict(par_classe),
                   classes_bananier=classes_b, annotations_bananier=len(bans),
                   images_avec_bananier=len(par_img), cote_median_px=cote_med, ppv_median_px=ppv_med,
                   cm_px_couronne_3m=round(300 / cote_med, 2) if cote_med else None,
                   cm_px_ppv_2_5m=round(250 / ppv_med, 2) if ppv_med else None)
        Path(zp).with_name("inventaire.json").write_text(json.dumps(inv, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(inv, ensure_ascii=False))


if __name__ == "__main__":
    main()
