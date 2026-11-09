# Field Scan : classifieur « de loin » v9 (saine / malade, feuilles ROAMER vues de loin), Kaggle GPU.
# Protocole : docs/protocole_maladies_v9_loin.md (écrit avant). Apprentissage : feuilles de dev_loin ; mesure unique : val_loin.
# Préparation de la v2 (recadrage carré 224 + JPEG 95), augmentations de la v7 sans mosaïque, tirage équilibré,
# 3 réseaux, 8 époques, dernière gardée. Sorties /kaggle/working/v9/ : poids, seuils.json, predictions_v9_val_loin_feuilles.csv.
import io, json, os, random, time
from pathlib import Path
import numpy as np, pandas as pd, torch
from PIL import Image, ImageOps
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import models, transforms as T

ESSAI_LOCAL = os.environ.get("ESSAI_LOCAL") == "1"
EPOQUES, NB, LOT, GRAINE, TAILLE = (1, 1, 8, 0, 224) if ESSAI_LOCAL else (8, 3, 32, 0, 224)
appareil = "cuda" if torch.cuda.is_available() else "cpu"
SORTIE = Path("out/maladies/v9_essai_local") if ESSAI_LOCAL else Path("/kaggle/working/v9")
SORTIE.mkdir(parents=True, exist_ok=True)
racine = Path("data") if ESSAI_LOCAL else Path("/kaggle/input")
DEV = [p for p in racine.rglob("feuilles.csv") if "dev_loin" in str(p) or "dev-loin" in str(p)][0]
VAL = [p for p in racine.rglob("feuilles.csv") if "val_loin" in str(p) or "val-loin" in str(p)][0]
dev, val = pd.read_csv(DEV), pd.read_csv(VAL)
dev["chemin"] = [str(DEV.parent / i) for i in dev.image]
val["chemin"] = [str(VAL.parent / i) for i in val.image]
assert not set(dev.photo) & set(val.photo), "photo commune dev / val"
if ESSAI_LOCAL:
    dev, val = dev.groupby("etat").head(8), val.groupby("etat").head(6)
print(appareil, "dev", dev.etat.value_counts().to_dict(), "val", len(val), flush=True)
NORM = T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])


def preparer(chemin):
    with Image.open(chemin) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        petite = ImageOps.fit(im, (TAILLE, TAILLE), method=Image.BILINEAR)
    t = io.BytesIO(); petite.save(t, format="JPEG", quality=95)
    return Image.open(t).convert("RGB")


class BasseResolution:
    def __call__(self, im):
        if random.random() >= 0.3:
            return im
        f = random.uniform(0.25, 0.70)
        return im.resize((max(8, int(im.width * f)), max(8, int(im.height * f))), Image.BILINEAR).resize(im.size, Image.BILINEAR)


AUG = T.Compose([T.RandomResizedCrop(224, scale=(0.4, 1.0), ratio=(0.8, 1.25)), T.RandomHorizontalFlip(), T.RandomVerticalFlip(),
                 T.RandomRotation(30), T.ColorJitter(0.4, 0.4, 0.4, 0.04), BasseResolution(),
                 T.RandomApply([T.GaussianBlur(7, sigma=(0.1, 3.0))], p=0.3), T.ToTensor(), NORM,
                 T.RandomErasing(p=0.5, scale=(0.02, 0.15))])
EVAL = T.Compose([T.ToTensor(), NORM])


class D(Dataset):
    def __init__(self, df, tr):
        self.c, self.y, self.tr = list(df.chemin), [int(e == "malade") for e in df.etat], tr
    def __len__(self):
        return len(self.c)
    def __getitem__(self, i):
        return self.tr(preparer(self.c[i])), self.y[i]


VUES = [lambda x: x, lambda x: x.flip(3), lambda x: x.flip(2), lambda x: x.rot90(1, (2, 3))]


@torch.no_grad()
def p_malade(reseaux, df):
    s = []
    for x, _ in DataLoader(D(df, EVAL), LOT, num_workers=0 if ESSAI_LOCAL else 4):
        x = x.to(appareil)
        s.append(torch.stack([sum(torch.softmax(m(v(x)), 1) for v in VUES) / 4 for m in reseaux]).mean(0)[:, 1].cpu())
    return torch.cat(s).numpy()


y = (dev.etat == "malade").to_numpy()
w = np.where(y, 0.5 / y.sum(), 0.5 / (~y).sum())
reseaux = []
for k in range(NB):
    random.seed(GRAINE + k); np.random.seed(GRAINE + k); torch.manual_seed(GRAINE + k)
    m = models.convnext_tiny(weights=None if ESSAI_LOCAL else models.ConvNeXt_Tiny_Weights.IMAGENET1K_V1)
    m.classifier[2] = torch.nn.Linear(m.classifier[2].in_features, 2)
    m = m.to(appareil)
    tir = WeightedRandomSampler(torch.tensor(w), len(dev), replacement=True, generator=torch.Generator().manual_seed(GRAINE + k))
    charge = DataLoader(D(dev, AUG), LOT, sampler=tir, num_workers=0 if ESSAI_LOCAL else 4)
    opt = torch.optim.AdamW(m.parameters(), lr=1e-4, weight_decay=1e-4)
    plan = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOQUES)
    perte = torch.nn.CrossEntropyLoss(label_smoothing=0.1)
    echelle = torch.amp.GradScaler(enabled=appareil == "cuda")
    for e in range(EPOQUES):
        m.train(); t0, tot, n = time.time(), 0.0, 0
        for x, yy in charge:
            x, yy = x.to(appareil), yy.to(appareil)
            opt.zero_grad()
            with torch.autocast(appareil, enabled=appareil == "cuda"):
                l = perte(m(x), yy)
            echelle.scale(l).backward(); echelle.step(opt); echelle.update()
            tot += l.item() * len(yy); n += len(yy)
        plan.step()
        print(f"réseau {k + 1} époque {e + 1} perte {tot / n:.3f} ({time.time() - t0:.0f} s)", flush=True)
    m.eval(); reseaux.append(m)
    torch.save({a: (t.half() if t.is_floating_point() else t) for a, t in m.state_dict().items()}, SORTIE / f"maladies_v9_loin_{k + 1}.pt")

# seuil fixé avant la mesure : 10 % de fausses alertes sur les feuilles saines de dev_loin
pd_dev = p_malade(reseaux, dev)
seuil = float(np.quantile(pd_dev[~y], 0.90))
(SORTIE / "seuils.json").write_text(json.dumps(dict(modele="v9_loin_convnext_tiny_binaire_x3", classes=["saine", "malade"],
                                                    quatre_vues=True, nb_reseaux=NB, seuil_malade=seuil), indent=1), encoding="utf-8")
print("seuil (10 % FA sur dev) :", round(seuil, 4), flush=True)
# mesure unique sur val_loin : probabilités écrites, aucune lecture de score ici
pv = p_malade(reseaux, val)
val.drop(columns="chemin").assign(p_malade=pv.round(6), reponse=np.where(pv >= seuil, "malade", "saine")).to_csv(
    SORTIE / "predictions_v9_val_loin_feuilles.csv", index=False)
print("->", sorted(p.name for p in SORTIE.iterdir()), flush=True)
