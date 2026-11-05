#!/usr/bin/env python3
"""Contrôles SANS modèle d'un nouveau jeu Roboflow (COCO), avant de décider de son usage.

1. Export : README (version, prétraitement, augmentations), images par partie, tailles, classes, boîtes.
2. Doublons : même nom d'origine, même fichier (MD5), quasi-doublons (empreinte de gradient, tuiles noires exclues).
3. Fuites avec les jeux déjà utilisés (data/roboflow/*.zip) : noms d'origine et MD5 communs.
4. Regroupement : tuiles d'orthomosaïque (nom avec position) ou photos (numéro DJI) ; pour des photos, recouvrement au
   sol entre photos de numéros voisins (points SIFT + homographie), pour former des groupes qui ne se recouvrent pas.
5. Échelle : taille médiane des boîtes et distance médiane au plus proche voisin entre plants.
6. Planches de contrôle (boîtes dessinées) dans --out.

Exemple :
    python scripts/analyser_jeu_roboflow.py data/roboflow/banavista.zip --out out/analyse_banavista
"""
import argparse
import collections
import hashlib
import io
import json
import random
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verifier_sources_communes import origine  # noqa: E402

BANANE = re.compile(r"banan|platan|^0$", re.I)


def empreinte_gradient(octets):
    a = np.asarray(Image.open(io.BytesIO(octets)).convert("L").resize((64, 64)), float)
    if (a < 8).mean() > 0.2:
        return None
    g = np.asarray(Image.fromarray(a.astype("uint8")).resize((17, 16), Image.BILINEAR), float)
    return (g[:, 1:] > g[:, :-1]).ravel()


def recouvrement(oa, ob):
    """Part de l'image A recouverte par B (SIFT + homographie RANSAC), 0 si pas d'appariement fiable."""
    import cv2
    sift = cv2.SIFT_create(3000)
    res = []
    for o in (oa, ob):
        im = cv2.imdecode(np.frombuffer(o, np.uint8), cv2.IMREAD_GRAYSCALE)
        f = 1200 / max(im.shape)
        im = cv2.resize(im, (round(im.shape[1] * f), round(im.shape[0] * f)))
        res.append((im.shape, *sift.detectAndCompute(im, None)))
    (sh, ka, da), (_, kb, db) = res
    if da is None or db is None or len(da) < 20 or len(db) < 20:
        return 0.0
    m = [x for x, y in cv2.BFMatcher().knnMatch(da, db, k=2) if x.distance < 0.7 * y.distance]
    if len(m) < 25:
        return 0.0
    pa = np.float32([ka[x.queryIdx].pt for x in m]); pb = np.float32([kb[x.trainIdx].pt for x in m])
    H, msk = cv2.findHomography(pa, pb, cv2.RANSAC, 5.0)
    if H is None or msk.sum() < 25:
        return 0.0
    h, w = sh
    return float(cv2.warpPerspective(np.ones((h, w), np.uint8), H, (w, h)).mean())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-planche", type=int, default=9)
    args = ap.parse_args(argv)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    z = zipfile.ZipFile(args.zip)
    rapport = []
    p = lambda *a: (print(*a), rapport.append(" ".join(str(x) for x in a)))

    # 1. Export
    for r in [n for n in z.namelist() if "README" in n.upper()]:
        t = z.read(r).decode("utf-8", "ignore")
        p("README :", " | ".join(l.strip() for l in t.splitlines() if l.strip() and "roboflow.com" not in l
                                 and not l.startswith("* ") and "notebooks" not in l)[:900])
    images, boites = [], collections.defaultdict(list)
    for a in [n for n in z.namelist() if n.endswith("_annotations.coco.json")]:
        d = json.loads(z.read(a)); part = a.split("/")[0]
        cat = {c["id"]: c["name"] for c in d["categories"]}
        ids = {}
        for im in d["images"]:
            nom = f"{part}/{im['file_name']}"; ids[im["id"]] = nom
            images.append(dict(nom=nom, partie=part, origine=origine(nom), l=im["width"], h=im["height"]))
        for an in d["annotations"]:
            x, y, w, h = an["bbox"]; boites[ids[an["image_id"]]].append((cat[an["category_id"]], x, y, x + w, y + h))
    p("images :", len(images), "| parties :", dict(collections.Counter(i["partie"] for i in images)),
      "| tailles :", collections.Counter((i["l"], i["h"]) for i in images).most_common(4))
    cl = collections.Counter(c for b in boites.values() for c, *_ in b)
    p("classes :", dict(cl))

    # 2. Doublons
    md5 = {}
    for i in images:
        i["md5"] = hashlib.md5(z.read(i["nom"])).hexdigest(); md5.setdefault(i["md5"], []).append(i["nom"])
    orig = collections.Counter(i["origine"] for i in images)
    p("noms d'origine :", len(orig), "| présents plusieurs fois :", sum(v > 1 for v in orig.values()),
      "| fichiers identiques en double :", sum(len(v) - 1 for v in md5.values() if len(v) > 1))
    gens = [(i["nom"], empreinte_gradient(z.read(i["nom"]))) for i in images]
    gens = [(n, g) for n, g in gens if g is not None]
    if len(gens) > 1:
        G = np.array([g for _, g in gens]); dd = (G[:, None, :] != G[None, :, :]).sum(2); np.fill_diagonal(dd, 999)
        a_, b_ = np.nonzero(np.triu(dd <= 20))
        p("quasi-doublons (empreinte, <= 20 bits sur 256) :", len(a_), [(gens[x][0].split('/')[-1][:30], gens[y][0].split('/')[-1][:30]) for x, y in zip(a_[:5], b_[:5])])

    # 3. Fuites avec les jeux déjà utilisés
    autres_noms, autres_md5 = set(), set()
    for f in sorted(Path("data/roboflow").glob("*.zip")):
        if f.resolve() == Path(args.zip).resolve():
            continue
        zz = zipfile.ZipFile(f)
        for n in zz.namelist():
            if n.lower().endswith((".jpg", ".jpeg", ".png")):
                autres_noms.add(origine(n))
                if f.stat().st_size < 2e9:
                    autres_md5.add(hashlib.md5(zz.read(n)).hexdigest())
    p("noms d'origine communs avec les autres jeux :", len(set(orig) & autres_noms),
      "| fichiers identiques :", len({i['md5'] for i in images} & autres_md5))

    # 4. Regroupement
    dji = {i["origine"]: i for i in images if re.match(r"^dji_\d+", i["origine"])}
    if dji:
        num = lambda o: int(re.match(r"^dji_(\d+)", o).group(1))
        uniq = {}
        for o, i in dji.items():
            uniq.setdefault(num(o), i)
        ns = sorted(uniq)
        p("photos DJI :", len(ns), "| numéros", ns[0], "à", ns[-1], "| trous > 5 :", [(a, b) for a, b in zip(ns, ns[1:]) if b - a > 5][:15])
        rec = []
        for a, b in zip(ns, ns[1:]):
            r_ = recouvrement(z.read(uniq[a]["nom"]), z.read(uniq[b]["nom"])) if b - a <= 3 else 0.0
            rec.append((a, b, round(r_, 2)))
        vals = [r for *_, r in rec if r > 0]
        p("recouvrement entre photos voisines : médiane", round(float(np.median(vals)), 2) if vals else None,
          "| paires sans recouvrement :", sum(r == 0 for *_, r in rec), "sur", len(rec))
        # groupes = suites de photos qui se recouvrent
        groupes, cour = [], [ns[0]]
        for a, b, r_ in rec:
            if r_ > 0.05:
                cour.append(b)
            else:
                groupes.append(cour); cour = [b]
        groupes.append(cour)
        p("groupes de photos qui se recouvrent :", len(groupes), "| tailles :", sorted((len(g) for g in groupes), reverse=True)[:20])
        (out / "groupes_photos.json").write_text(json.dumps(dict(recouvrements=rec, groupes=groupes), indent=1), encoding="utf-8")
    else:
        grp = collections.Counter(re.sub(r"[_\-]?(chunk|tile|x\d|\d).*$", "", o) or "?" for o in orig)
        p("préfixes de noms (orthomosaïques ?) :", grp.most_common(10))

    # 5. Échelle
    tl = [((x1 - x0) + (y1 - y0)) / 2 for b in boites.values() for c, x0, y0, x1, y1 in b if BANANE.search(c)]
    nn = []
    for b in boites.values():
        c_ = np.array([((x0 + x1) / 2, (y0 + y1) / 2) for c, x0, y0, x1, y1 in b if BANANE.search(c)])
        if len(c_) >= 4:
            d_, _ = cKDTree(c_).query(c_, k=2); nn += list(d_[:, 1])
    if tl:
        p(f"boîte bananier médiane {np.median(tl):.1f} px | plus proche voisin médian {np.median(nn):.1f} px | "
          f"échelle estimée : {300 / np.median(tl):.2f} cm/px (couronne 3 m), {250 / np.median(nn):.2f} cm/px (espacement 2,5 m)")

    # 6. Planches
    rng = random.Random(2026); tir = images[:]; rng.shuffle(tir)
    vs = []
    for i in tir[:args.n_planche]:
        im = Image.open(io.BytesIO(z.read(i["nom"]))).convert("RGB"); f = 640 / max(im.size)
        im = im.resize((round(im.width * f), round(im.height * f))); dr = ImageDraw.Draw(im)
        for c, x0, y0, x1, y1 in boites[i["nom"]]:
            dr.rectangle([x0 * f, y0 * f, x1 * f, y1 * f], outline=(255, 43, 214) if BANANE.search(c) else (0, 229, 255), width=2)
        dr.rectangle([0, 0, im.width, 15], fill=(0, 0, 0)); dr.text((3, 2), f"{i['nom'].split('/')[-1][:45]} | {len(boites[i['nom']])}", fill=(255, 255, 255))
        vs.append(im)
    if vs:
        H = max(v.height for v in vs); c = Image.new("RGB", (3 * 646, ((len(vs) + 2) // 3) * (H + 6)), "white")
        for k, v in enumerate(vs): c.paste(v, ((k % 3) * 646, (k // 3) * (H + 6)))
        c.save(out / "planche.jpg", quality=85)
    (out / "rapport.txt").write_text("\n".join(rapport), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
