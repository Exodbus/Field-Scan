#!/usr/bin/env python3
"""Archive d'entraînement du détecteur de comptage v6 à 5 cm (format de data/drone/comptage_v5_5cm). Aucun modèle.

Contenu :
- toutes les tuiles du v5 (images, lignes de tuiles.csv et d'objets.csv) recopiées telles quelles, SAUF l'ensemble
  test_espace (ancien test banana_tree_detection), retiré ;
- banana_tree_detection d'après data/drone/decoupage_comptage_v6/decoupage.csv :
  * btd_train -> ensemble « train » : image x facteur 0,628 (protocole v4 : espacement médian 79,6 px ramené à 2,5 m,
    3,14 cm/px) x tirage uniforme 0,75 à 1,4 (graine 2026, comme le v5), tuiles de 512 px recouvrement 20 %, boîte
    gardée si au moins 50 % de sa surface est dans la tuile (fonction tuiles_classes de preparer_comptage_v3.py) ;
  * btd_val -> ensemble « val_espace » : image entière au facteur 0,628, boîtes dont le centre est dans l'image ;
- mm/ et cg/ recopiés du v5 ; segmento est, CG et banano_dense gardent leur rôle (ensembles test_*, juges).

Sorties dans data/drone/comptage_v6_5cm : images/, tuiles.csv, objets.csv, parametres.json, bilan.csv, mm/, cg/ et
kaggle/comptage_v6_5cm.zip (+ dataset-metadata.json) pour Kaggle.

Exemple :
    python scripts/v6_prep_4_archive.py
"""
import io
import json
import random
import shutil
import sys
import zipfile
from pathlib import Path

import pandas as pd
from PIL import Image

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
from preparer_comptage_v3 import lire_boites, tuiles_classes  # noqa: E402  (lecture seule, script existant)

V5 = RACINE / "data/drone/comptage_v5_5cm"
DEC = RACINE / "data/drone/decoupage_comptage_v6/decoupage.csv"
OUT = RACINE / "data/drone/comptage_v6_5cm"
FACTEUR_BTD = 0.628          # parametres.json du v5 : facteurs.btd (espacement 79,6 px, 3,14 cm/px)
TAILLE, ECH_MIN, ECH_MAX, GRAINE = 512, 0.75, 1.4, 2026


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "images").mkdir(parents=True)
    t5 = pd.read_csv(V5 / "tuiles.csv")
    o5 = pd.read_csv(V5 / "objets.csv")
    retire = set(t5[t5.ensemble == "test_espace"].image_path)
    t = t5[~t5.image_path.isin(retire)].copy()
    o = o5[~o5.image_path.isin(retire)].copy()
    print(f"v5 : {len(t5)} tuiles ; test_espace retiré : {len(retire)} tuiles ; gardées : {len(t)}", flush=True)
    for n in t.image_path:
        shutil.copy2(V5 / "images" / n, OUT / "images" / n)
    for sous in ("mm", "cg"):
        shutil.copytree(V5 / sous, OUT / sous)

    dec = pd.read_csv(DEC)
    btd = dec[dec.groupe.isin(["btd_train", "btd_val"])].sort_values("image")
    z, boites = lire_boites(RACINE / "data/roboflow/banana_tree_detection.zip")
    rng = random.Random(GRAINE)
    lt, lo = [], []

    def ajouter(nom, img, ens, r, f, bb):
        img.save(OUT / "images" / nom, quality=95)
        for c, x0, y0, x1, y1 in bb:
            lo.append(dict(image_path=nom, cx=round((x0 + x1) / 2, 1), cy=round((y0 + y1) / 2, 1),
                           taille=round(((x1 - x0) + (y1 - y0)) / 2, 1), type="mere"))
        lt.append(dict(image_path=nom, ensemble=ens, partie=r.partie, groupe=r.groupe, source=r.source,
                       facteur=round(f, 4), largeur=img.width, hauteur=img.height, n_bananiers=len(bb),
                       n_autres_arbres=0, masque_cx=None, masque_cy=None, masque_r=None))

    for k, r in enumerate(btd.itertuples()):
        b0 = [bb for bb in boites[r.image] if bb[0] == "banana-tree"]
        assert len(b0) == len(boites[r.image])
        img0 = Image.open(io.BytesIO(z.read(r.image))).convert("RGB")
        if r.groupe == "btd_train":
            f = FACTEUR_BTD * rng.uniform(ECH_MIN, ECH_MAX)
            img = img0.resize((round(img0.width * f), round(img0.height * f)), Image.LANCZOS)
            b = [(c, x0 * f, y0 * f, x1 * f, y1 * f) for c, x0, y0, x1, y1 in b0]
            for j, (tt, garde) in enumerate(tuiles_classes(img, b, TAILLE)):
                ajouter(f"btd_train_{k:04d}_{j}.jpg", tt, "train", r, f, garde)
        else:
            f = FACTEUR_BTD
            img = img0.resize((round(img0.width * f), round(img0.height * f)), Image.LANCZOS)
            b = [(c, x0 * f, y0 * f, x1 * f, y1 * f) for c, x0, y0, x1, y1 in b0]
            garde = [bb for bb in b if 0 <= (bb[1] + bb[3]) / 2 < img.width and 0 <= (bb[2] + bb[4]) / 2 < img.height]
            ajouter(f"btd_val_{k:04d}.jpg", img, "val_espace", r, f, garde)
    T = pd.concat([t, pd.DataFrame(lt)], ignore_index=True)
    O = pd.concat([o, pd.DataFrame(lo)], ignore_index=True)
    assert T.image_path.is_unique and set(O.image_path) <= set(T.image_path)
    T.to_csv(OUT / "tuiles.csv", index=False)
    O.to_csv(OUT / "objets.csv", index=False)
    p = json.loads((V5 / "parametres.json").read_text(encoding="utf-8"))
    p.update(version="v6", decoupage="data/drone/decoupage_comptage_v6/decoupage.csv", out="data/drone/comptage_v6_5cm",
             construction=("tuiles du v5 recopiées sans changement, ensemble test_espace retiré ; banana_tree_detection "
                           "reclassé (btd_train en entraînement, btd_val en validation val_espace) par "
                           "scripts/v6_prep_4_archive.py"))
    p["facteurs"]["btd_v6"] = dict(regle="facteur du v4/v5 (espacement médian 79,6 px ramené à 2,5 m)",
                                   cm_par_pixel_estime=3.14, facteur=FACTEUR_BTD,
                                   tirage_entrainement=[ECH_MIN, ECH_MAX], graine=GRAINE,
                                   images_train=int((btd.groupe == "btd_train").sum()),
                                   images_val=int((btd.groupe == "btd_val").sum()))
    (OUT / "parametres.json").write_text(json.dumps(p, indent=2, ensure_ascii=False), encoding="utf-8")
    bilan = T.groupby(["ensemble", "groupe"]).agg(tuiles=("image_path", "size"), bananiers=("n_bananiers", "sum"),
                                                 autres_arbres=("n_autres_arbres", "sum")).reset_index()
    bilan.to_csv(OUT / "bilan.csv", index=False)
    print(bilan.to_string(index=False), flush=True)

    kag = OUT / "kaggle"
    kag.mkdir()
    nom_zip = kag / "comptage_v6_5cm.zip"
    with zipfile.ZipFile(nom_zip, "w", zipfile.ZIP_STORED) as zz:
        for f_ in ("tuiles.csv", "objets.csv", "parametres.json", "bilan.csv"):
            zz.write(OUT / f_, f_)
        for sous in ("mm", "cg"):
            for f_ in sorted((OUT / sous).rglob("*")):
                if f_.is_file():
                    zz.write(f_, f_.relative_to(OUT).as_posix())
        for f_ in sorted((OUT / "images").iterdir()):
            zz.write(f_, f"images/{f_.name}")
    (kag / "dataset-metadata.json").write_text(json.dumps(
        {"title": "comptage-v6-5cm", "id": "affilecorentin/comptage-v6-5cm", "licenses": [{"name": "CC-BY-4.0"}]}),
        encoding="utf-8")
    print(f"Archive : {nom_zip} ({nom_zip.stat().st_size / 1e6:.0f} Mo)")


if __name__ == "__main__":
    main()
