#!/usr/bin/env python3
"""Effet de la résolution sur le classifieur de maladies (validation tanzanienne, processeur).

Chaque image de l'échantillon est réduite pour que son petit côté fasse R pixels, puis passe
dans le modèle retenu (v2, moyenne sur 4 vues) avec la préparation habituelle (agrandissement
à 224, centre). R = 113 correspond aux miniatures du jeu éthiopien (150 x 113).

Question : la chute observée sur le jeu éthiopien (47,6 % de feuilles connues bien classées)
vient-elle de la résolution, ou du pays et du style des photos ?

Exemple :
    python scripts/ablation_resolution.py
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

CLASSES = ["cercosporiose_noire", "fusariose", "saine"]


def degrader(im, petit_cote):
    """Réduit l'image pour que son petit côté fasse `petit_cote` pixels (jamais agrandie)."""
    r = petit_cote / min(im.size)
    if r >= 1:
        return im
    return im.resize((max(1, round(im.width * r)), max(1, round(im.height * r))), Image.LANCZOS)


def predire(modele, images, petit_cote, lot=32):
    """Probabilités moyennes sur 4 vues, pour des images réduites à `petit_cote`."""
    import torch
    import torchvision.transforms as T
    prep = T.Compose([T.Resize(224), T.CenterCrop(224), T.ToTensor(),
                      T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
    vues = [lambda x: x, lambda x: torch.flip(x, [3]), lambda x: torch.flip(x, [2]), lambda x: torch.flip(x, [2, 3])]
    P = []
    with torch.no_grad():
        for i in range(0, len(images), lot):
            x = torch.stack([prep(degrader(Image.open(c).convert("RGB"), petit_cote)) for c in images[i:i + lot]])
            L = torch.stack([modele(v(x)) for v in vues]).mean(0)
            P.append(torch.softmax(L, 1).numpy())
    return np.concatenate(P)


def charger_modele(chemin):
    import torch
    import torch.nn as nn
    from torchvision.models import efficientnet_b0
    m = efficientnet_b0(weights=None)
    m.classifier[1] = nn.Linear(m.classifier[1].in_features, len(CLASSES))
    m.load_state_dict(torch.load(chemin, map_location="cpu"))
    return m.eval()


def mesures(P, vrai):
    pred = np.array(CLASSES)[P.argmax(1)]
    malade = vrai != "saine"
    r = dict(exactitude=(pred == vrai).mean(),
             fausses_alertes_saines=(pred[~malade] != "saine").mean(),
             malades_declarees_saines=(pred[malade] == "saine").mean())
    for c in CLASSES:
        r[f"rappel_{c}"] = (pred[vrai == c] == c).mean()
    r["f1_macro"] = float(np.mean([2 * ((pred == c) & (vrai == c)).sum() / max((pred == c).sum() + (vrai == c).sum(), 1)
                                   for c in CLASSES]))
    return {k: round(float(v), 3) for k, v in r.items()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--feuilles", default="data/feuilles")
    ap.add_argument("--modele", default="modeles/maladies/meilleur_v2.pt")
    ap.add_argument("--par-classe", type=int, default=200, help="images de validation par classe (défaut 200)")
    ap.add_argument("--resolutions", type=int, nargs="+", default=[256, 192, 150, 113, 80, 56])
    ap.add_argument("--graine", type=int, default=2026)
    ap.add_argument("--out", default="out/maladies/resolution")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    index = pd.read_csv(Path(args.feuilles) / "index.csv")
    val = index[index.retenue & (index.ensemble == "validation")]
    ech = pd.concat([g.sample(min(args.par_classe, len(g)), random_state=args.graine) for _, g in val.groupby("classe")])
    images = [str(Path(args.feuilles) / c) for c in ech.chemin]
    vrai = ech.classe.to_numpy()
    print(f"Échantillon : {len(ech)} images de validation ({ech.classe.value_counts().to_dict()})")

    modele = charger_modele(args.modele)
    lignes = []
    for r in args.resolutions:
        P = predire(modele, images, r)
        lignes.append(dict(petit_cote_px=r, **mesures(P, vrai)))
        print(f"  petit côté {r:4d} px : exactitude {lignes[-1]['exactitude']:.3f}")
    tab = pd.DataFrame(lignes)
    tab.to_csv(out / "resolution_validation.csv", index=False)
    print("\n" + tab.to_string(index=False))
    print("\nRepère : sur le jeu éthiopien (petit côté 113 px), 47,6 % des feuilles connues étaient bien classées.")
    (out / "parametres.json").write_text(json.dumps(dict(modele=args.modele, par_classe=args.par_classe,
                                                         graine=args.graine, resolutions=args.resolutions), indent=2),
                                         encoding="utf-8")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 4))
        for col, nom in (("exactitude", "exactitude"), ("rappel_saine", "rappel saine"),
                         ("rappel_cercosporiose_noire", "rappel cercosporiose"), ("rappel_fusariose", "rappel fusariose")):
            ax.plot(tab.petit_cote_px, tab[col], marker="o", label=nom)
        ax.axvline(113, color="grey", linestyle="--", label="miniatures éthiopiennes")
        ax.set_xlabel("petit côté de l'image (pixels)"); ax.set_ylabel("part bien classée"); ax.set_ylim(0, 1.02)
        ax.invert_xaxis(); ax.legend(fontsize=8); ax.set_title("Effet de la résolution (validation tanzanienne)")
        fig.tight_layout(); fig.savefig(out / "resolution_validation.png", dpi=120)
        print(f"Graphique : {out / 'resolution_validation.png'}")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
