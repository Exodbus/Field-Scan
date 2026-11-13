#!/usr/bin/env python3
"""Planche de contrôle des annotations d'un export COCO (boîtes ou points dessinés), sans aucun modèle.

Classe bananier en magenta, autres classes en jaune ; points (keypoints) en disques magenta.
Écrit planche.jpg à côté du zip (6 images tirées avec une graine fixe, ou --images).

Exemple :
    python scripts/v6_prosp_planche.py data/roboflow_nuit_1112/comptage/conteo_banano/conteo_banano.zip
"""
import argparse
import io
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.v6_prosp_inspecter import BANANE, lire  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zips", nargs="+")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--cote", type=int, default=640)
    ap.add_argument("--graine", type=int, default=2026)
    ap.add_argument("--suffixe", default="")
    args = ap.parse_args(argv)
    for zp in args.zips:
        z, images, annots, _ = lire(zp)
        par = {}
        for a in annots:
            par.setdefault(a["img"], []).append(a)
        cles = sorted(images, key=str)
        random.Random(args.graine).shuffle(cles)
        cles = cles[:args.n]
        cols = 3
        rangs = -(-len(cles) // cols)
        c = args.cote
        planche = Image.new("RGB", (cols * c, rangs * (c + 18)), "white")
        dp = ImageDraw.Draw(planche)
        for k, cle in enumerate(cles):
            info = images[cle]
            im = Image.open(io.BytesIO(z.read(info["fichier"]))).convert("RGB")
            d = ImageDraw.Draw(im)
            ep = max(2, im.width // 300)
            for a in par.get(cle, []):
                coul = (255, 43, 214) if BANANE.search(str(a["cls"])) else (255, 230, 0)
                if a["bbox"] and a["bbox"][2] > 0:
                    x, y, w, h = a["bbox"]
                    d.rectangle([x, y, x + w, y + h], outline=coul, width=ep)
                if a["kp"]:
                    for i in range(0, len(a["kp"]), 3):
                        px, py = a["kp"][i], a["kp"][i + 1]
                        d.ellipse([px - 2 * ep, py - 2 * ep, px + 2 * ep, py + 2 * ep], fill=coul)
            im.thumbnail((c, c))
            x0, y0 = (k % cols) * c, (k // cols) * (c + 18)
            planche.paste(im, (x0, y0))
            dp.text((x0 + 2, y0 + c + 2), f"{info['fichier'][-60:]} ({len(par.get(cle, []))})", fill="black")
        sortie = Path(zp).with_name(f"planche{args.suffixe}.jpg")
        planche.save(sortie, quality=85)
        print(sortie)


if __name__ == "__main__":
    main()
