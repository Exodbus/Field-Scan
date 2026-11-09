# Field Scan : caractéristiques figées DINOv2 ViT-B/14 et ConvNeXt-Tiny ImageNet (docs/protocole_maladies_dinov2.md).
# Aucun score. GPU, internet activé (poids téléchargés par torch.hub et torchvision).
# Jeux : entrainement (16 963, 1 vue), tdtu (autre_maladie, black_sigatoka ; 1 vue), validation (3 001) et bananalsd (897)
# avec les 4 vues de la v2. Préparation de la v2 (classifieur.preparer, normalisation ImageNet).
# Sorties : /kaggle/working/<reseau>_<jeu>.npz (car : (vues, n, d) en float16, chemin, classe, source).
import sys, time
from pathlib import Path
import numpy as np, pandas as pd, torch
from torch.utils.data import DataLoader, Dataset
from torchvision import models

ENTREE, SORTIE = Path("/kaggle/input"), Path("/kaggle/working")
CLASSIF = sorted(ENTREE.rglob("classifieur.py"))[0]
sys.path.insert(0, str(CLASSIF.parent))
import classifieur  # noqa: E402

INDEX = sorted(ENTREE.rglob("index.csv"))[0]
AJOUTS = sorted(ENTREE.rglob("images_ajouts.csv"))[0]
appareil = "cuda"


def jeux():
    idx = pd.read_csv(INDEX)
    idx = idx[idx.retenue.astype(bool)]
    out = {}
    for nom, s in (("entrainement", idx[idx.ensemble.eq("entrainement") & idx.chemin.notna()]),
                   ("validation", idx[idx.ensemble.eq("validation")]),
                   ("bananalsd", idx[idx.ensemble.eq("test") & idx.source.eq("bananalsd")])):
        out[nom] = pd.DataFrame(dict(chemin="data/feuilles/" + s.chemin.values, kaggle=[str(INDEX.parent / c) for c in s.chemin],
                                     classe=s.classe.values, source=s.source.values))
    a = pd.read_csv(AJOUTS)
    t = a[a.jeu.eq("tdtu") & a.classe.isin(["autre_maladie", "black_sigatoka"])]
    rel = [i.removeprefix("ajouts_v3/") for i in t.image]
    out["tdtu"] = pd.DataFrame(dict(chemin=["data/feuilles_v3_ajouts/" + r for r in rel], kaggle=[str(AJOUTS.parent / r) for r in rel],
                                    classe=t.classe.values, source="tdtu"))
    return out


class Images(Dataset):
    def __init__(self, c):
        self.c = c
    def __len__(self):
        return len(self.c)
    def __getitem__(self, i):
        return classifieur.PREPARATION(classifieur.preparer(self.c[i]))


dino = torch.hub.load("facebookresearch/dinov2", "dinov2_vitb14", trust_repo=True).to(appareil).eval()
cnx = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.IMAGENET1K_V1).to(appareil).eval()


def f_dino(x):
    f = dino.forward_features(x)
    return torch.cat([f["x_norm_clstoken"], f["x_norm_patchtokens"].mean(1)], 1)


def f_cnx(x):
    return cnx.classifier[1](cnx.classifier[0](cnx.avgpool(cnx.features(x))))


RESEAUX = {"dinov2": f_dino, "convnext_in": f_cnx}


@torch.no_grad()
def extraire(chemins, nb_vues):
    vues = classifieur.VUES[:nb_vues]
    sortie = {r: [[] for _ in vues] for r in RESEAUX}
    for x in DataLoader(Images(chemins), batch_size=64, num_workers=4):
        x = x.to(appareil)
        with torch.autocast("cuda", dtype=torch.float16):
            for r, f in RESEAUX.items():
                for k, v in enumerate(vues):
                    sortie[r][k].append(f(v(x).contiguous()).float().cpu().numpy().astype(np.float16))
    return {r: np.stack([np.concatenate(s) for s in sv]) for r, sv in sortie.items()}


for nom, d in jeux().items():
    t0 = time.time()
    car = extraire(list(d.kaggle), 4 if nom in ("validation", "bananalsd") else 1)
    for r, c in car.items():
        np.savez_compressed(SORTIE / f"{r}_{nom}.npz", car=c, chemin=np.array(d.chemin), classe=np.array(d.classe), source=np.array(d.source))
    print(f"{nom} : {len(d)} photos, {', '.join(f'{r} {c.shape}' for r, c in car.items())}, {(time.time() - t0) / 60:.1f} min", flush=True)
print("->", sorted(p.name for p in SORTIE.iterdir()), flush=True)
