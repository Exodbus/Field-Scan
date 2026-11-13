#!/usr/bin/env python3
"""Planches du contrôle visuel de fin de test du v5 (protocole v5, section 8), sur les images tirées à l'avance
(docs/controle_visuel_v5.json : liste du v4 et 6 tuiles banano_dense) : v4 et v5 côte à côte, détections comparées
aux boîtes Roboflow (appariement à 1 m). Sur banano_dense, les boîtes aberrantes sont retirées comme au test
(taille moyenne des côtés au-dessus de 328,5 px, data/drone/comptage_v5_5cm/parametres.json).

Couleurs : vert = détection appariée à une boîte ; rouge = détection sans boîte (fausse détection, ou bananier non
annoté) ; jaune = boîte sans détection (oubli, ou boîte en double). Le jugement à l'œil est rapporté tel quel et ne
change ni le choix ni l'adoption.

Exemple :
    python scripts/planches_controle_v5.py
"""
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from fieldscan.drone import DetecteurCentres  # noqa: E402

BANANE = {"Banana", "Banana-plant", "banana-tree", "banana"}
FACTEURS = {"segmento_est": ("plants_bana_originaux.zip", 2.2222), "banana_tree_detection": ("banana_tree_detection.zip", 0.628),
            "banano_dense": ("banano_dense.zip", 0.5505)}
LIMITE_BOITE = {"banano_dense": 328.5}
MODELES = {"v4": "modeles/centres_5cm_v4.onnx", "v5": "modeles/centres_5cm_v5.onnx"}


def boites(z, nom, limite=None):
    part = nom.split("/")[0]
    d = json.loads(z.read(f"{part}/_annotations.coco.json"))
    cat = {c["id"]: c["name"] for c in d["categories"]}
    im = next(i for i in d["images"] if f"{part}/{i['file_name']}" == nom)
    return [(a["bbox"][0] + a["bbox"][2] / 2, a["bbox"][1] + a["bbox"][3] / 2) for a in d["annotations"]
            if a["image_id"] == im["id"] and cat[a["category_id"]] in BANANE
            and (limite is None or (a["bbox"][2] + a["bbox"][3]) / 2 <= limite)]


def apparier(det, ref, rayon=20):
    ok_d, ok_r = np.zeros(len(det), bool), np.zeros(len(ref), bool)
    if len(det) and len(ref):
        d = cdist(det, ref); i, j = linear_sum_assignment(np.where(d <= rayon, d, 1e6)); g = d[i, j] <= rayon
        ok_d[i[g]], ok_r[j[g]] = True, True
    return ok_d, ok_r


def main():
    choix = json.loads(Path("docs/controle_visuel_v5.json").read_text(encoding="utf-8"))
    dets = {k: DetecteurCentres(v) for k, v in MODELES.items()}
    out = Path("out/controle_visuel_v5"); out.mkdir(parents=True, exist_ok=True)
    bilan = []
    for groupe, (nom_zip, f) in FACTEURS.items():
        z = zipfile.ZipFile(f"data/roboflow/{nom_zip}")
        for k, nom in enumerate(choix[groupe]):
            img = Image.open(io.BytesIO(z.read(nom))).convert("RGB")
            img = img.resize((round(img.width * f), round(img.height * f)), Image.LANCZOS)
            ref = np.array([(x * f, y * f) for x, y in boites(z, nom, LIMITE_BOITE.get(groupe))]).reshape(-1, 2)
            vues = []
            for m, det in dets.items():
                rgb = np.moveaxis(np.asarray(img), -1, 0)
                xy, sc = det.predire(rgb, np.ones(rgb.shape[1:], bool))
                xy = xy[sc >= det.seuil]
                ok_d, ok_r = apparier(xy, ref)
                v = img.copy(); dr = ImageDraw.Draw(v)
                for (x, y), ok in zip(ref, ok_r):
                    if not ok:
                        dr.ellipse([x - 9, y - 9, x + 9, y + 9], outline=(255, 220, 0), width=3)
                for (x, y), ok in zip(xy, ok_d):
                    c = (0, 230, 0) if ok else (255, 30, 30)
                    dr.ellipse([x - 5, y - 5, x + 5, y + 5], fill=c)
                dr.rectangle([0, 0, v.width, 22], fill=(0, 0, 0))
                dr.text((4, 5), f"{m} | {groupe} {nom.split('/')[-1][:30]} | {len(ref)} annotés, {len(xy)} détectés : "
                                f"{int(ok_d.sum())} appariés, {int((~ok_d).sum())} sans boîte, {int((~ok_r).sum())} oubliés",
                        fill=(255, 255, 255))
                vues.append(v)
                bilan.append(dict(groupe=groupe, image=nom, modele=m, annotes=len(ref), detectes=len(xy),
                                  apparies=int(ok_d.sum()), sans_boite=int((~ok_d).sum()), oublies=int((~ok_r).sum())))
            W = sum(v.width for v in vues) + 10
            c = Image.new("RGB", (W, vues[0].height), "white"); x0 = 0
            for v in vues:
                c.paste(v, (x0, 0)); x0 += v.width + 10
            s = min(1.0, 2600 / c.width)
            c.resize((round(c.width * s), round(c.height * s))).save(out / f"{groupe}_{k}.jpg", quality=85)
            print(f"{groupe} {k} : " + " | ".join(f"{b['modele']} {b['apparies']}/{b['annotes']} (+{b['sans_boite']} sans boîte)"
                                                  for b in bilan[-2:]))
    (out / "bilan.json").write_text(json.dumps(bilan, indent=1, ensure_ascii=False), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
