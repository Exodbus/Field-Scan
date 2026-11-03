#!/usr/bin/env python3
"""Évalue le détecteur de pieds (DeepForest affiné) sur un jeu Roboflow au format COCO, image par image.

Les images de drone de ces jeux n'ont pas de résolution connue (et sont souvent prises plus bas que
ReforesTree). On les ramène à l'échelle du détecteur (10 cm par pixel, couronne de bananier d'environ
30 pixels) : facteur = boite_cible / taille médiane des boîtes annotées. Chaque image réduite est placée
dans un cadre de 400 pixels (la taille des fenêtres d'entraînement), pour que le détecteur la voie à la
même échelle interne qu'en production.

Mesure (celle du sujet) : centres des détections appariés aux centres des boîtes annotées à moins de
1 m (soit `rayon_px` pixels à 10 cm), affectation optimale ; précision, rappel, F1, erreur de comptage.
Seules les parties sans augmentation sont évaluées par défaut (valid et test).

Exemple :
    python scripts/evaluer_comptage_roboflow.py data/roboflow/count_banana_plants.zip --parties valid test
"""
import argparse
import io
import json
import zipfile
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from scipy.optimize import linear_sum_assignment


def apparier(pred, vrai, rayon):
    """Nombre de vrais positifs : affectation optimale des centres à moins de `rayon`."""
    if len(pred) == 0 or len(vrai) == 0:
        return 0
    d = np.linalg.norm(pred[:, None, :] - vrai[None, :, :], axis=2)
    lignes, colonnes = linear_sum_assignment(np.where(d <= rayon, d, 1e6))
    return int((d[lignes, colonnes] <= rayon).sum())


def charger(zip_, parties):
    z = zipfile.ZipFile(zip_)
    images = []
    for a in [n for n in z.namelist() if n.endswith("_annotations.coco.json")]:
        partie = PurePosixPath(a).parent.name
        if partie not in parties:
            continue
        coco = json.loads(z.read(a))
        cats = {c["id"]: c["name"] for c in coco["categories"]}
        base = str(PurePosixPath(a).parent)
        for im in coco["images"]:
            bb = [an["bbox"] for an in coco["annotations"] if an["image_id"] == im["id"]
                  and "banana" in cats.get(an["category_id"], "").lower()]
            images.append(dict(partie=partie, chemin=f"{base}/{im['file_name']}", boites=np.array(bb, float).reshape(-1, 4)))
    return z, images


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip")
    ap.add_argument("--parties", nargs="+", default=["valid", "test"])
    ap.add_argument("--modele", default="modeles/bananiers_deepforest_v3_40.ckpt")
    ap.add_argument("--boite-cible", type=float, default=None,
                    help="taille d'une couronne en pixels (défaut : 30 à 10 cm pour DeepForest, 60 à 5 cm pour un détecteur de centres)")
    ap.add_argument("--rayon-px", type=float, default=None, help="rayon d'appariement en pixels, 1 m (défaut : 10 ou 20)")
    ap.add_argument("--seuils", type=float, nargs="+", default=[0.2, 0.3, 0.4, 0.5])
    ap.add_argument("--cadre", type=int, default=None, help="cadre en pixels (défaut : 400 ou 512)")
    ap.add_argument("--out", default="out/comptage/roboflow")
    args = ap.parse_args(argv)
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from fieldscan.drone import Detecteur, DetecteurCentres
    centres = str(args.modele).lower().endswith(".onnx")          # détecteur de centres (5 cm) ou DeepForest (10 cm)
    args.boite_cible = args.boite_cible or (60.0 if centres else 30.0)
    args.rayon_px = args.rayon_px or (20.0 if centres else 10.0)
    args.cadre = args.cadre or (512 if centres else 400)

    z, images = charger(args.zip, args.parties)
    tailles = np.concatenate([(im["boites"][:, 2] + im["boites"][:, 3]) / 2 for im in images if len(im["boites"])])
    mediane = float(np.median(tailles))
    facteur = args.boite_cible / mediane
    print(f"{len(images)} images ({', '.join(args.parties)}), {sum(len(i['boites']) for i in images)} bananiers annotés")
    print(f"Taille médiane des couronnes : {mediane:.0f} px -> facteur {facteur:.3f} "
          f"(couronne ramenée à {args.boite_cible:g} pixels ; rayon d'appariement {args.rayon_px:g} pixels)")
    det = DetecteurCentres(args.modele) if centres else Detecteur(args.modele)
    out = Path(args.out) / Path(args.zip).stem
    out.mkdir(parents=True, exist_ok=True)
    resultats, exemples = [], []
    for k, im in enumerate(images):
        rgb = Image.open(io.BytesIO(z.read(im["chemin"]))).convert("RGB")
        l, h = max(1, round(rgb.width * facteur)), max(1, round(rgb.height * facteur))
        petit = np.asarray(rgb.resize((l, h), Image.LANCZOS), dtype="float32")
        cadre = np.zeros((args.cadre, args.cadre, 3), "float32")
        cadre[:min(h, args.cadre), :min(l, args.cadre)] = petit[:args.cadre, :args.cadre]
        valide = np.zeros((args.cadre, args.cadre), bool)
        valide[:min(h, args.cadre), :min(l, args.cadre)] = True
        if centres:
            centres_p, scores = det.predire(np.moveaxis(cadre, -1, 0), valide)
        else:
            boites, scores = det.predire(np.moveaxis(cadre, -1, 0), valide)
            centres_p = np.c_[(boites[:, 0] + boites[:, 2]) / 2, (boites[:, 1] + boites[:, 3]) / 2] if len(boites) else np.empty((0, 2))
        dans = (centres_p[:, 0] < l) & (centres_p[:, 1] < h) if len(centres_p) else np.empty(0, bool)
        centres_p, scores = centres_p[dans], scores[dans]
        vrai = np.c_[im["boites"][:, 0] + im["boites"][:, 2] / 2, im["boites"][:, 1] + im["boites"][:, 3] / 2] * facteur
        for s in args.seuils:
            p = centres_p[scores >= s]
            vp = apparier(p, vrai, args.rayon_px)
            resultats.append(dict(image=PurePosixPath(im["chemin"]).name, partie=im["partie"], seuil=s,
                                  reference=len(vrai), detections=len(p), vrais_positifs=vp))
        if k < 12:
            exemples.append((rgb, im["boites"], centres_p[scores >= 0.4] / facteur))
        if (k + 1) % 25 == 0:
            print(f"  {k + 1}/{len(images)} images")
    df = pd.DataFrame(resultats)
    df.to_csv(out / "par_image.csv", index=False)
    lignes = []
    for s, g in df.groupby("seuil"):
        vp, det_, ref = g.vrais_positifs.sum(), g.detections.sum(), g.reference.sum()
        p, r = vp / max(det_, 1), vp / max(ref, 1)
        erreur = (g.detections - g.reference)
        lignes.append(dict(seuil=s, reference=int(ref), detections=int(det_), vrais_positifs=int(vp), precision=round(p, 3),
                           rappel=round(r, 3), f1=round(2 * p * r / max(p + r, 1e-9), 3),
                           erreur_comptage_totale=int(det_ - ref), erreur_absolue_moyenne_par_image=round(float(erreur.abs().mean()), 2),
                           rapport_reel_sur_detecte=round(ref / max(det_, 1), 3)))
    bilan = pd.DataFrame(lignes)
    bilan.to_csv(out / "bilan.csv", index=False)
    print("\n" + bilan.to_string(index=False))
    # Planche : annotations en vert, détections (seuil 0,4) en rouge
    c, col = 300, 4
    planche = Image.new("RGB", (col * c, ((len(exemples) + col - 1) // col) * (c + 14)), "white")
    d = ImageDraw.Draw(planche)
    for k, (rgb, bb, pts) in enumerate(exemples):
        im = rgb.copy(); dd = ImageDraw.Draw(im)
        for x, y, w, hh in bb:
            dd.rectangle([x, y, x + w, y + hh], outline=(0, 220, 0), width=2)
        for x, y in pts:
            dd.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(255, 0, 0))
        im.thumbnail((c - 4, c - 4))
        planche.paste(im, ((k % col) * c + 2, (k // col) * (c + 14) + 2))
        d.text(((k % col) * c + 3, (k // col) * (c + 14) + c - 4), f"{len(bb)} annotés | {len(pts)} détectés (0,4)", fill="black")
    planche.save(out / "planche.jpg", quality=88)
    print(f"\nRésultats : {out}")


if __name__ == "__main__":
    main()
