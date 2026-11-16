#!/usr/bin/env python3
"""A2 « plantain du Ghana » : boîtes à l'échelle des originaux (7 952 × 5 304). Aucun modèle.

Deux sources :
  - API image Roboflow (métadonnées enregistrées par jeux_neufs_a2_telecharger.py, `meta/<id>.json`) : boîtes en
    pixels d'origine, (x, y) = centre, largeur, hauteur. **Source retenue.**
  - export 640 px (`data/roboflow_nuit_1112/comptage/plantain_m2/plantain_m2.zip`, COCO, « Stretch ») : centre
    × 7 952 / 640 en x et × 5 304 / 640 en y. Sert de contrôle.
Les deux sont appariées un à un (distance minimale) par photo ; écarts et boîtes sans partenaire sont rapportés.
L'orientation EXIF des originaux est contrôlée (l'export a subi une auto-orientation).

Sorties :
  - data/raw/plantain_ghana_m2/annotations/<nom sans extension>.csv : cx, cy, largeur, hauteur (pixels d'origine) ;
  - out/jeux_neufs_1511/a2_boites_comparaison.csv et .json.
"""
import csv
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.stdout.reconfigure(encoding="utf-8")  # en mode -I, PYTHONIOENCODING est ignoré
A2 = RACINE / "data/raw/plantain_ghana_m2"
EXPORT = RACINE / "data/roboflow_nuit_1112/comptage/plantain_m2/plantain_m2.zip"
OUT = RACINE / "out/jeux_neufs_1511"
W, H = 7952, 5304


def boites_export():
    res = {}
    with zipfile.ZipFile(EXPORT) as z:
        for f in [m for m in z.namelist() if m.endswith("_annotations.coco.json")]:
            j = json.loads(z.read(f))
            noms = {im["id"]: (im["extra"]["name"], im["width"], im["height"]) for im in j["images"]}
            for nom, _, _ in noms.values():
                res.setdefault(nom, [])
            for a in j["annotations"]:
                if a["category_id"] != 1:
                    continue
                nom, w, h = noms[a["image_id"]]
                x, y, bw, bh = a["bbox"]
                res[nom].append(((x + bw / 2) * W / w, (y + bh / 2) * H / h, bw * W / w, bh * H / h))
    return {k: np.array(v, float).reshape(-1, 4) for k, v in res.items()}


def main():
    (A2 / "annotations").mkdir(exist_ok=True)
    exp = boites_export()
    lignes, ecarts_tous = [], []
    orient = {}
    for f in sorted((A2 / "meta").glob("*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        nom = j["name"]
        a = j.get("annotation") or {}
        assert not a or (int(a["width"]), int(a["height"])) == (W, H), (nom, a.get("width"), a.get("height"))
        api = np.array([(float(b["x"]), float(b["y"]), float(b["width"]), float(b["height"]))
                        for b in a.get("boxes", []) if b.get("label") == "plantain"], float).reshape(-1, 4)
        autres = [b.get("label") for b in a.get("boxes", []) if b.get("label") != "plantain"]
        with open(A2 / "annotations" / (Path(nom).stem + ".csv"), "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["cx", "cy", "largeur", "hauteur"])
            w.writerows([[f"{v:.2f}" for v in r] for r in api])
        p = A2 / "images" / nom
        if p.exists():
            with Image.open(p) as im:
                orient[nom] = int(im.getexif().get(274, 1))
        e = exp.get(nom)
        l = dict(nom=nom, id=j["id"], n_api=len(api), n_export=None if e is None else len(e), autres_etiquettes=len(autres),
                 apparies=None, ecart_median_px=None, ecart_max_px=None, sans_partenaire_api=None,
                 sans_partenaire_export=None)
        if e is not None and len(api) and len(e):
            d = cdist(api[:, :2], e[:, :2])
            li, co = linear_sum_assignment(d)
            ok = d[li, co] <= 30
            ec = d[li, co][ok]
            ecarts_tous += ec.tolist()
            l.update(apparies=int(ok.sum()), ecart_median_px=round(float(np.median(ec)), 2),
                     ecart_max_px=round(float(ec.max()), 2), sans_partenaire_api=len(api) - int(ok.sum()),
                     sans_partenaire_export=len(e) - int(ok.sum()))
        lignes.append(l)
    with open(OUT / "a2_boites_comparaison.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, list(lignes[0])); w.writeheader(); w.writerows(lignes)
    ec = np.array(ecarts_tous)
    bilan = dict(photos=len(lignes), boites_api=int(sum(l["n_api"] for l in lignes)),
                 photos_sans_boite_api=sum(1 for l in lignes if l["n_api"] == 0),
                 photos_absentes_export=[l["nom"] for l in lignes if l["n_export"] is None],
                 boites_export=int(sum(l["n_export"] or 0 for l in lignes)),
                 apparies=int(sum(l["apparies"] or 0 for l in lignes)),
                 sans_partenaire_api=int(sum(l["sans_partenaire_api"] or 0 for l in lignes)),
                 sans_partenaire_export=int(sum(l["sans_partenaire_export"] or 0 for l in lignes)),
                 ecart_px_mediane=float(np.median(ec)) if len(ec) else None,
                 ecart_px_p95=float(np.percentile(ec, 95)) if len(ec) else None,
                 ecart_px_max=float(ec.max()) if len(ec) else None,
                 autres_etiquettes=int(sum(l["autres_etiquettes"] for l in lignes)),
                 orientation_exif=dict(__import__("collections").Counter(orient.values())),
                 photos_orientation_lue=len(orient))
    (OUT / "a2_boites_comparaison.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(bilan, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
