#!/usr/bin/env python3
"""Planches d'images tirées au hasard dans chaque sous-dossier d'un dossier, avec en option la
réponse du modèle de maladies sous chaque image (v2, moyenne sur 4 vues, processeur).

Sert à regarder un jeu de données inconnu, par exemple pour comprendre pourquoi le modèle s'y trompe.

Exemple :
    python scripts/planche_dossier.py data/raw/ethiopie_2021/resized --modele modeles/maladies/meilleur_v2.pt
"""
import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw

EXT = {".jpg", ".jpeg", ".png"}
CLASSES = ["cercosporiose_noire", "fusariose", "saine"]
COURT = {"cercosporiose_noire": "cerco", "fusariose": "fusa", "saine": "saine"}


def predire(chemin_modele, images, lot=48):
    import torch
    import torch.nn as nn
    import torchvision.transforms as T
    from torchvision.models import efficientnet_b0
    m = efficientnet_b0(weights=None)
    m.classifier[1] = nn.Linear(m.classifier[1].in_features, len(CLASSES))
    m.load_state_dict(torch.load(chemin_modele, map_location="cpu"))
    m.eval()
    prep = T.Compose([T.Resize(224), T.CenterCrop(224), T.ToTensor(),
                      T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
    vues = [lambda x: x, lambda x: torch.flip(x, [3]), lambda x: torch.flip(x, [2]), lambda x: torch.flip(x, [2, 3])]
    sorties = []
    with torch.no_grad():
        for i in range(0, len(images), lot):
            x = torch.stack([prep(Image.open(c).convert("RGB")) for c in images[i:i + lot]])
            P = torch.softmax(torch.stack([m(v(x)) for v in vues]).mean(0), 1)
            sorties += [(CLASSES[int(p.argmax())], float(p.max())) for p in P]
    return sorties


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier")
    ap.add_argument("--modele", help="poids du modèle (meilleur_v2.pt) pour afficher sa réponse sous chaque image")
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--graine", type=int, default=2026)
    ap.add_argument("--cote", type=int, default=180)
    ap.add_argument("--colonnes", type=int, default=6)
    ap.add_argument("--out", default="out/feuilles/planches_dossier")
    ap.add_argument("--tous", action="store_true", help="avec --modele : répartition des réponses sur toutes les images de chaque dossier")
    args = ap.parse_args(argv)
    racine, out = Path(args.dossier), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sous = sorted({f.parent for f in racine.rglob("*") if f.suffix.lower() in EXT})
    if not sous:
        raise SystemExit(f"Aucune image dans {racine}")
    c = args.cote
    for d in sous:
        images = sorted(str(f) for f in d.iterdir() if f.suffix.lower() in EXT)
        tirage = random.Random(f"{args.graine}-{d.name}").sample(images, min(args.n, len(images)))
        reponses = predire(args.modele, tirage) if args.modele else [None] * len(tirage)
        lignes = (len(tirage) + args.colonnes - 1) // args.colonnes
        feuille = Image.new("RGB", (args.colonnes * c, lignes * (c + 16) + 22), "white")
        dessin = ImageDraw.Draw(feuille)
        dessin.text((4, 4), f"{d.relative_to(racine)} : {len(tirage)} images tirées au hasard sur {len(images)}", fill="black")
        for k, (chemin, rep) in enumerate(zip(tirage, reponses)):
            im = Image.open(chemin).convert("RGB")
            taille = im.size
            im.thumbnail((c - 6, c - 6))
            x, y = (k % args.colonnes) * c, 22 + (k // args.colonnes) * (c + 16)
            feuille.paste(im, (x + (c - im.width) // 2, y + (c - im.height) // 2))
            texte = f"{taille[0]}x{taille[1]}" + (f" | {COURT[rep[0]]} {rep[1]:.2f}" if rep else "")
            dessin.text((x + 3, y + c), texte, fill="red" if rep else "black")
        nom = str(d.relative_to(racine)).replace("\\", "_").replace("/", "_") or "racine"
        if args.modele and args.tous:
            from collections import Counter
            toutes = Counter(r[0] for r in predire(args.modele, images))
            print(f"{nom} : réponses du modèle sur les {len(images)} images : "
                  + ", ".join(f"{k} {v} ({v / len(images):.1%})" for k, v in toutes.most_common()))
        feuille.save(out / f"{nom}.jpg", quality=88)
        print(f"{nom} : {len(images)} images, planche de {len(tirage)}")
    print(f"Planches dans {out}")


if __name__ == "__main__":
    main()
