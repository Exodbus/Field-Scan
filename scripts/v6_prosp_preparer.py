#!/usr/bin/env python3
"""Préparation d'un jeu neuf de comptage au format de data/drone/comptage_v6_5cm (nuit du 12 novembre 2026).

Entrée : un export COCO Roboflow (zip, lu sans être décompressé). Sortie dans --out (par défaut <dossier du zip>/prepare) :
images/, tuiles.csv, objets.csv, parametres.json, bilan.csv, mêmes colonnes que comptage_v6_5cm.

Règles (protocole v4, section 3, reprises par les v5 et v6) :
- échelle de la source : côté médian des boîtes de la classe bananier ramené à 3 m (règle des couronnes), ou, avec
  --regle ppv, distance médiane au plus proche voisin ramenée à 2,5 m ; facteur = (cm/px estimé) / 5 ;
- une seule copie par image d'origine (nom avant « _jpg.rf. ») : celle qui a le moins de pixels noirs de bord
  (copies tournées par l'augmentation Roboflow) ;
- --mode entrainement : facteur x tirage uniforme 0,75 à 1,4 (graine 2026), tuiles de 512 px recouvrement 20 %,
  boîte gardée si au moins 50 % est dans la tuile (tuiles_classes de preparer_comptage_v3.py, lecture seule) ;
- --mode evaluation : image entière ramenée à 5 cm/px, objets gardés si leur centre est dans l'image ;
- les autres classes d'arbres (--autres, ex. « Coconut Tree ») ne sont pas des cibles : comptées dans n_autres_arbres.

Exemple :
    python scripts/v6_prosp_preparer.py data/roboflow_nuit_1112/comptage/dmpcs2_objets/dmpcs2_objets.zip \\
        --prefixe dmpcs2 --classes "Banana Plant" --autres "Coconut Tree" --mode entrainement
"""
import argparse
import io
import json
import random
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd
from PIL import Image
from scipy.spatial import cKDTree

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
from preparer_comptage_v3 import tuiles_classes  # noqa: E402  (lecture seule, script existant)


def lire_boites(chemin_zip):
    """Comme lire_boites de preparer_comptage_v3.py, mais tolère les exports sans partie valid ou test."""
    z = zipfile.ZipFile(chemin_zip)
    out = {}
    for n in z.namelist():
        if not n.endswith("_annotations.coco.json"):
            continue
        part = PurePosixPath(n).parent.name
        d = json.loads(z.read(n))
        cat = {c["id"]: c["name"] for c in d["categories"]}
        noms = {im["id"]: f"{part}/{im['file_name']}" for im in d["images"]}
        for nom in noms.values():
            out.setdefault(nom, [])
        for a in d["annotations"]:
            x, y, w, h = a["bbox"]
            out[noms[a["image_id"]]].append((cat[a["category_id"]], x, y, x + w, y + h))
    return z, out

MOTIF = re.compile(r"^(.*?)_(?:jpg|jpeg|png|tif|tiff)\.rf\.", re.IGNORECASE)
TAILLE, ECH_MIN, ECH_MAX, GRAINE, CM_CIBLE = 512, 0.75, 1.4, 2026, 5.0


def origine(nom):
    b = PurePosixPath(nom).name
    m = MOTIF.match(b)
    return (m.group(1) if m else b.rsplit(".", 1)[0]).lower()


def part_noire(im):
    a = np.asarray(im.convert("L").resize((64, 64)))
    return float((a < 4).mean())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip")
    ap.add_argument("--prefixe", required=True)
    ap.add_argument("--classes", nargs="+", required=True, help="classes bananier (cibles)")
    ap.add_argument("--autres", nargs="*", default=[], help="autres arbres (non cibles, comptés)")
    ap.add_argument("--regle", choices=["couronne", "ppv"], default="couronne")
    ap.add_argument("--mode", choices=["entrainement", "evaluation"], required=True)
    ap.add_argument("--ensemble", default=None)
    ap.add_argument("--exclure", nargs="*", default=[], help="noms d'origine à exclure (fuites)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    out = Path(args.out or Path(args.zip).parent / "prepare")
    (out / "images").mkdir(parents=True, exist_ok=True)
    z, boites = lire_boites(args.zip)

    # une copie par image d'origine
    copies = {}
    for n in sorted(boites):
        copies.setdefault(origine(n), []).append(n)
    choix = {}
    for o, ns in copies.items():
        if o in {e.lower() for e in args.exclure}:
            continue
        choix[o] = min(ns, key=lambda n: part_noire(Image.open(io.BytesIO(z.read(n)))))

    # échelle de la source
    cotes, ppv = [], []
    for n in choix.values():
        b = [bb for bb in boites[n] if bb[0] in args.classes]
        cotes += [((x1 - x0) + (y1 - y0)) / 2 for _, x0, y0, x1, y1 in b]
        if len(b) >= 3:
            p = np.array([((x0 + x1) / 2, (y0 + y1) / 2) for _, x0, y0, x1, y1 in b])
            d, _ = cKDTree(p).query(p, k=2)
            ppv += d[:, 1].tolist()
    if args.regle == "couronne":
        med = float(np.median(cotes)); cm = 300 / med
    else:
        med = float(np.median(ppv)); cm = 250 / med
    facteur = cm / CM_CIBLE
    print(f"{args.prefixe} : {len(choix)} images d'origine, règle {args.regle}, médiane {med:.1f} px, "
          f"{cm:.2f} cm/px, facteur {facteur:.4f}", flush=True)

    ens = args.ensemble or ("train" if args.mode == "entrainement" else f"test_{args.prefixe}")
    partie = "train" if args.mode == "entrainement" else "test"
    rng = random.Random(GRAINE)
    lt, lo = [], []
    for k, (o, n) in enumerate(sorted(choix.items())):
        img0 = Image.open(io.BytesIO(z.read(n))).convert("RGB")
        b0 = [bb for bb in boites[n] if bb[0] in args.classes]
        autres0 = [bb for bb in boites[n] if bb[0] in args.autres]
        f = facteur * (rng.uniform(ECH_MIN, ECH_MAX) if args.mode == "entrainement" else 1.0)
        img = img0.resize((max(1, round(img0.width * f)), max(1, round(img0.height * f))), Image.LANCZOS)
        mise = lambda bb: (bb[0], bb[1] * f, bb[2] * f, bb[3] * f, bb[4] * f)
        b, autres = [mise(bb) for bb in b0], [mise(bb) for bb in autres0]
        if args.mode == "entrainement":
            morceaux = tuiles_classes(img, b + autres, TAILLE)
        else:
            dedans = lambda bb: 0 <= (bb[1] + bb[3]) / 2 < img.width and 0 <= (bb[2] + bb[4]) / 2 < img.height
            morceaux = [(img, [bb for bb in b + autres if dedans(bb)])]
        for j, (tt, garde) in enumerate(morceaux):
            nom = f"{args.prefixe}_{k:04d}_{j}.jpg"
            tt.save(out / "images" / nom, quality=95)
            gb = [bb for bb in garde if bb[0] in args.classes]
            for c, x0, y0, x1, y1 in gb:
                lo.append(dict(image_path=nom, cx=round((x0 + x1) / 2, 1), cy=round((y0 + y1) / 2, 1),
                               taille=round(((x1 - x0) + (y1 - y0)) / 2, 1), type="mere"))
            lt.append(dict(image_path=nom, ensemble=ens, partie=partie, groupe=args.prefixe, source=Path(args.zip).stem,
                           facteur=round(f, 4), largeur=tt.width, hauteur=tt.height, n_bananiers=len(gb),
                           n_autres_arbres=len(garde) - len(gb), masque_cx=None, masque_cy=None, masque_r=None,
                           origine=o))
    T, O = pd.DataFrame(lt), pd.DataFrame(lo)
    T.to_csv(out / "tuiles.csv", index=False)
    O.to_csv(out / "objets.csv", index=False)
    bilan = T.groupby(["ensemble", "groupe"]).agg(tuiles=("image_path", "size"), bananiers=("n_bananiers", "sum"),
                                                 autres_arbres=("n_autres_arbres", "sum")).reset_index()
    bilan.to_csv(out / "bilan.csv", index=False)
    (out / "parametres.json").write_text(json.dumps(dict(
        source=str(Path(args.zip).as_posix()), mode=args.mode, classes=args.classes, autres=args.autres,
        regle=args.regle, mediane_px=round(med, 1), cm_par_pixel_estime=round(cm, 2), facteur=round(facteur, 4),
        cm_cible=CM_CIBLE, taille=TAILLE if args.mode == "entrainement" else None,
        echelle_min=ECH_MIN if args.mode == "entrainement" else None,
        echelle_max=ECH_MAX if args.mode == "entrainement" else None, graine=GRAINE,
        images_origine=len(choix), exclues=args.exclure,
        note="colonne origine ajoutée à tuiles.csv (nom d'origine Roboflow), absente de comptage_v6_5cm"),
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(bilan.to_string(index=False))


if __name__ == "__main__":
    main()
