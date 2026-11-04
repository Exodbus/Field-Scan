#!/usr/bin/env python3
"""Prépare les tuiles du détecteur de comptage v3 à 5 cm par pixel, d'après le découpage figé (decouper_comptage.py).

Règles (docs/protocole_comptage_v3.md, section « Préparation ») :
- échelle : un facteur par source d'images (même orthomosaïque ou même jeu de vols) ; la couronne médiane annotée
  de la source est ramenée à sa taille réelle typique à 5 cm/pixel (20 px par mètre) : bananier 3 m, cacaoyer 3 m,
  palmier à huile 9 m, cocotier 7 m ; photos DJI des jeunes bananiers : 1,1 cm/pixel mesuré (facteur 0,22) ;
  ReforesTree : déjà à 5 cm (tuiles de preparer_deepforest.py) ;
- entraînement seulement : chaque image Roboflow est en plus multipliée par un facteur tiré entre 0,75 et 1,4
  (graine fixe), comme pour le v2 ;
- tuiles de 512 px qui se recouvrent de 20 % ; une boîte est gardée si au moins 50 % de sa surface est dans la tuile ;
- jeunes bananiers DJI : points manuels (taille de cible 2,5 m = 50 px), disque gardé de 2 000 px (440 px à 5 cm)
  autour du centre de la photo ; hors du disque, zone ignorée (colonnes masque_* de tuiles.csv) ; rejets ignorés.

Sorties dans --out : images/, tuiles.csv (une ligne par tuile : ensemble, groupe, source, facteur, masque, nombre de
bananiers et d'autres arbres), objets.csv (une ligne par pied : centre, taille en px, type), mm/ et cg/ (références
manuelles, format de preparer_validation_points.py), parametres.json, et <nom du dossier>.zip pour Kaggle.

Ensembles : train ; val_dense (segmento est) ; val_jeunes (dji_0544) ; val_negatifs (palmiers, cacaoyère, cocotiers
de validation) ; test_negatifs ; plus mm/ (validation) et cg/ (test).

Exemple :
    python scripts/preparer_comptage_v3.py
"""
import argparse
import io
import json
import random
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preparer_validation_points  # noqa: E402

PX_PAR_M = 20                                     # 5 cm par pixel
COURONNE_M = {"Banana": 3.0, "Banana-plant": 3.0, "Cacao": 3.0, "Oil Palm Tree": 9.0, "coconut_tree": 7.0}
BANANE = {"Banana", "Banana-plant"}
ENSEMBLE = {"val": {"segmento_est": "val_dense", "jeunes_dji_0544": "val_jeunes"},
            "test": {}}


def source_echelle(groupe):
    """Groupes qui partagent la même échelle d'image (même orthomosaïque ou même jeu de vols)."""
    if groupe.startswith("segmento"):
        return "segmento"
    if groupe in ("vols_100_022x", "corte"):
        return "count_100_022x_corte"
    if groupe.startswith("cocotier"):
        return "cocotiers"
    return groupe


def tuiles_classes(img, boites, taille, recouvrement=0.2, part_min=0.5):
    """Comme tuiles() de preparer_roboflow_deepforest.py, en gardant la classe de chaque boîte :
    image plus petite que la tuile -> placée dans un cadre noir ; sinon tuiles qui se recouvrent ; boîte gardée
    si au moins part_min de sa surface est dans la tuile (puis rognée au bord)."""
    l, h = img.size
    if l <= taille and h <= taille:
        cadre = Image.new("RGB", (taille, taille))
        cadre.paste(img, (0, 0))
        return [(cadre, list(boites))]
    pas = int(taille * (1 - recouvrement))
    pos = lambda n: sorted(set(list(range(0, max(n - taille, 0) + 1, pas)) + [max(n - taille, 0)]))
    sorties = []
    for y0 in pos(h):
        for x0 in pos(l):
            t = Image.new("RGB", (taille, taille))
            t.paste(img.crop((x0, y0, min(x0 + taille, l), min(y0 + taille, h))), (0, 0))
            garde = []
            for c, a0, b0, a1, b1 in boites:
                a0, b0, a1, b1 = a0 - x0, b0 - y0, a1 - x0, b1 - y0
                aire = max(a1 - a0, 0) * max(b1 - b0, 0)
                r0, s0, r1, s1 = max(a0, 0), max(b0, 0), min(a1, taille), min(b1, taille)
                if aire > 0 and r1 > r0 and s1 > s0 and (r1 - r0) * (s1 - s0) >= part_min * aire:
                    garde.append((c, r0, s0, r1, s1))
            sorties.append((t, garde))
    return sorties


def lire_boites(chemin_zip):
    """{'partie/fichier': [(classe, x0, y0, x1, y1)]} pour toutes les classes."""
    z = zipfile.ZipFile(chemin_zip)
    out = {}
    for part in ["train", "valid", "test"]:
        d = json.loads(z.read(f"{part}/_annotations.coco.json"))
        cat = {c["id"]: c["name"] for c in d["categories"]}
        noms = {im["id"]: f"{part}/{im['file_name']}" for im in d["images"]}
        for n in noms.values():
            out.setdefault(n, [])
        for a in d["annotations"]:
            x, y, w, h = a["bbox"]
            out[noms[a["image_id"]]].append((cat[a["category_id"]], x, y, x + w, y + h))
    return z, out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--decoupage", default="data/drone/decoupage_comptage/decoupage.csv")
    ap.add_argument("--roboflow", default="data/roboflow")
    ap.add_argument("--reforestree", default="data/drone/reforestree/deepforest_5cm", help="tuiles ReforesTree à 5 cm (train.csv)")
    ap.add_argument("--jeunes", default="data/drone/jeunes_bananiers")
    ap.add_argument("--out", default="data/drone/comptage_v3_5cm")
    ap.add_argument("--taille", type=int, default=512)
    ap.add_argument("--echelle-min", type=float, default=0.75)
    ap.add_argument("--echelle-max", type=float, default=1.4)
    ap.add_argument("--cm-dji", type=float, default=1.1, help="résolution mesurée des photos DJI (cm/pixel)")
    ap.add_argument("--rayon-dji", type=float, default=2000, help="disque gardé, en pixels de la photo d'origine")
    ap.add_argument("--taille-jeune-m", type=float, default=2.5)
    ap.add_argument("--graine", type=int, default=2026)
    args = ap.parse_args(argv)
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    (out / "images").mkdir(parents=True)
    rng = random.Random(args.graine)
    dec = pd.read_csv(args.decoupage)
    dec = dec[dec.partie.isin(["train", "val", "test"])]
    lignes_t, lignes_o, facteurs = [], [], {}

    def ensemble(r):
        if r.partie == "train":
            return "train"
        if r.groupe in ENSEMBLE.get(r.partie, {}):
            return ENSEMBLE[r.partie][r.groupe]
        return f"{r.partie}_negatifs"

    def ajouter_tuile(nom, img, ens, r, facteur, boites, masque=None, points=None):
        img.save(out / "images" / nom, quality=95)
        ban = [b for b in boites if b[0] in BANANE]
        autres = [b for b in boites if b[0] not in BANANE]
        for c, x0, y0, x1, y1 in ban:
            lignes_o.append(dict(image_path=nom, cx=round((x0 + x1) / 2, 1), cy=round((y0 + y1) / 2, 1),
                                 taille=round(((x1 - x0) + (y1 - y0)) / 2, 1), type="mere"))
        for cx, cy, t, typ in (points or []):
            lignes_o.append(dict(image_path=nom, cx=round(cx, 1), cy=round(cy, 1), taille=round(t, 1), type=typ))
        n_ban = len(ban) + sum(1 for p in (points or []) if p[3] == "mere")
        mx, my, mr = masque if masque else (np.nan, np.nan, np.nan)
        lignes_t.append(dict(image_path=nom, ensemble=ens, partie=r.partie, groupe=r.groupe, source=r.source,
                             facteur=round(facteur, 4), largeur=img.width, hauteur=img.height, n_bananiers=n_ban,
                             n_autres_arbres=len(autres), masque_cx=mx, masque_cy=my, masque_r=mr))

    # 1. Images Roboflow (bananiers, cacaoyers, palmiers, cocotiers)
    zips = {}
    for nom_zip in sorted(dec.zip.dropna().unique()):
        zips[nom_zip] = lire_boites(Path(args.roboflow) / nom_zip)
    rob = dec[dec.source.isin(["plants_bana", "count_banana_plants", "multiple_tree"]) & ~dec.groupe.str.startswith("jeunes_dji")]
    for se, g in rob.groupby(rob.groupe.map(source_echelle)):
        tailles, ref = {}, None
        for _, r in g.iterrows():
            for c, x0, y0, x1, y1 in zips[r.zip][1][r.image]:
                tailles.setdefault(c, []).append(((x1 - x0) + (y1 - y0)) / 2)
        classe = next((c for c in ("Banana", "Banana-plant") if c in tailles), None) or max(tailles, key=lambda c: len(tailles[c]))
        facteur = COURONNE_M[classe] * PX_PAR_M / float(np.median(tailles[classe]))
        facteurs[se] = dict(classe_de_reference=classe, couronne_m=COURONNE_M[classe], mediane_px=round(float(np.median(tailles[classe])), 1),
                            facteur=round(facteur, 4), images=len(g))
        print(f"{se:22s} : {len(g):4d} images, {classe} médian {np.median(tailles[classe]):.0f} px -> facteur {facteur:.3f}")
        for k, (_, r) in enumerate(g.sort_values("image").iterrows()):
            z, boites = zips[r.zip]
            ens = ensemble(r)
            f = facteur * (rng.uniform(args.echelle_min, args.echelle_max) if ens == "train" else 1.0)
            img = Image.open(io.BytesIO(z.read(r.image))).convert("RGB")
            img = img.resize((max(1, round(img.width * f)), max(1, round(img.height * f))), Image.LANCZOS)
            b = [(c, x0 * f, y0 * f, x1 * f, y1 * f) for c, x0, y0, x1, y1 in boites[r.image]]
            for j, (t, garde) in enumerate(tuiles_classes(img, b, args.taille)):
                ajouter_tuile(f"{r.groupe}_{k:04d}_{j}.jpg", t, ens, r, f, garde)

    # 2. Jeunes bananiers DJI : points manuels, échelle mesurée, disque gardé
    import geopandas as gpd
    pts = gpd.read_file(Path(args.jeunes) / "points_jeunes_bananiers.geojson")
    f = args.cm_dji / 5.0
    taille_pt = args.taille_jeune_m * PX_PAR_M
    for _, r in dec[dec.groupe.str.startswith("jeunes_dji", na=False)].iterrows():
        z, _ = zips[r.zip]
        img = Image.open(io.BytesIO(z.read(r.image))).convert("RGB")
        W, H = img.size
        img = img.resize((round(W * f), round(H * f)), Image.LANCZOS)
        cx0, cy0, rr = W / 2 * f, H / 2 * f, args.rayon_dji * f
        p = pts[pts.image == r.photo]
        dans = np.hypot(p.colonne * f - cx0, p.ligne * f - cy0) <= rr
        p = p[dans]
        points = [(c * f, l * f, taille_pt, typ) for c, l, typ in zip(p.colonne, p.ligne, p["type"])]
        ens = ensemble(r)
        facteurs[r.groupe] = dict(cm_par_pixel=args.cm_dji, facteur=round(f, 4), rayon_px_5cm=round(rr, 1),
                                  points_gardes=int(dans.sum()), points_hors_disque=int((~dans).sum()))
        if ens == "train":
            T = args.taille
            pas = int(T * 0.8)
            pos = lambda n: sorted(set(list(range(0, max(n - T, 0) + 1, pas)) + [max(n - T, 0)]))
            for j, (y0, x0) in enumerate([(y, x) for y in pos(img.height) for x in pos(img.width)]):
                t = Image.new("RGB", (T, T))
                t.paste(img.crop((x0, y0, min(x0 + T, img.width), min(y0 + T, img.height))))
                pp = [(cx - x0, cy - y0, s, typ) for cx, cy, s, typ in points if 0 <= cx - x0 < T and 0 <= cy - y0 < T]
                ajouter_tuile(f"{r.groupe}_{j}.jpg", t, ens, r, f, [], masque=(round(cx0 - x0, 1), round(cy0 - y0, 1), round(rr, 1)), points=pp)
        else:
            ajouter_tuile(f"{r.groupe}.jpg", img, ens, r, f, [], masque=(round(cx0, 1), round(cy0, 1), round(rr, 1)), points=points)
        print(f"{r.groupe:22s} : {int(dans.sum())} points gardés dans le disque ({int((~dans).sum())} hors disque), "
              f"image {img.width} x {img.height} px, ensemble {ens}")

    # 3. ReforesTree (entraînement) : tuiles à 5 cm déjà préparées, boîtes -> centres
    rt = pd.read_csv(Path(args.reforestree) / "train.csv")
    rt_sites = dec[(dec.source == "reforestree") & (dec.partie == "train")].image.tolist()
    garde_rt = rt[rt.image_path.str.replace("_5cm_.*", "", regex=True).str.replace("_", " ").isin(rt_sites)]
    for nom, g in garde_rt.groupby("image_path"):
        site = nom.split("_5cm_")[0].replace("_", " ")
        r = dec[dec.image == site].iloc[0]
        img = Image.open(Path(args.reforestree) / "images" / nom).convert("RGB")
        b = [("Banana", x0, y0, x1, y1) for x0, y0, x1, y1 in g[["xmin", "ymin", "xmax", "ymax"]].to_numpy() if x1 > x0 and y1 > y0]
        ajouter_tuile(f"rt_{Path(nom).stem}.jpg", img, "train", r, 1.0, b)
    print(f"ReforesTree : {garde_rt.image_path.nunique()} tuiles d'entraînement ({', '.join(rt_sites)})")

    # 4. Références manuelles : MM (validation), CG (test)
    for sous, zonesv in (("mm", ["MM1", "MM2"]), ("cg", [f"CG{i}" for i in range(1, 10)])):
        preparer_validation_points.main(["--zones-evaluees", *zonesv, "--resolution", "5", "--out", str(out / sous)])
        (out / sous / f"{sous}.zip").unlink(missing_ok=True)

    T_, O_ = pd.DataFrame(lignes_t), pd.DataFrame(lignes_o)
    T_.to_csv(out / "tuiles.csv", index=False)
    O_.to_csv(out / "objets.csv", index=False)
    parametres = dict(vars(args), couronnes_m=COURONNE_M, facteurs=facteurs)
    (out / "parametres.json").write_text(json.dumps(parametres, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    bilan = T_.groupby(["ensemble", "groupe"]).agg(tuiles=("image_path", "size"), bananiers=("n_bananiers", "sum"),
                                                  autres_arbres=("n_autres_arbres", "sum")).reset_index()
    bilan.to_csv(out / "bilan.csv", index=False)
    print("\n" + bilan.to_string(index=False))
    print("\nObjets par type :", O_.groupby("type").size().to_dict())
    nom_zip = out / f"{out.name}.zip"
    with zipfile.ZipFile(nom_zip, "w", zipfile.ZIP_STORED) as zz:
        for f_ in ("tuiles.csv", "objets.csv", "parametres.json", "bilan.csv"):
            zz.write(out / f_, f_)
        for sous in ("mm", "cg"):
            for f_ in sorted((out / sous).rglob("*")):
                if f_.is_file():
                    zz.write(f_, f_.relative_to(out).as_posix())
        for f_ in sorted((out / "images").iterdir()):
            zz.write(f_, f"images/{f_.name}")
    print(f"\nArchive pour Kaggle : {nom_zip} ({nom_zip.stat().st_size / 1e6:.0f} Mo)")


if __name__ == "__main__":
    main()
