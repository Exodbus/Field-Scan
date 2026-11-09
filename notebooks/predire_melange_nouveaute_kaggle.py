# Field Scan : calculs du protocole « mélange + nouveauté » (docs/protocole_maladies_melange_nouveaute.md, amendement 1),
# sur GPU Kaggle. N'affiche aucun score.
#  - contrôle : probabilités de la v2 sur les 8 premières photos de chaque jeu (comparées en local aux fichiers GPU de la nuit) ;
#  - A2, soupe v2 + v8 : réseau k = moyenne paramètre par paramètre des réseaux k de la v2 et de la v8 ; 3 réseaux, 4 vues ;
#    jeux validation (3 001), bananalsd (897), val_loin_feuilles (3 014) ;
#  - B, caractéristiques de la v2 : entrée de la dernière couche (768) et logits, vue d'origine, pour chaque réseau ;
#    jeux ajustement (500 par source et classe de l'apprentissage, graine 2026), tdtu (autre_maladie, black_sigatoka),
#    validation, bananalsd.
# Préparation de la v2 (classifieur.preparer). Sorties dans /kaggle/working.
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
FEUILLES = sorted(ENTREE.rglob("feuilles.csv"))[0]
AJOUTS = sorted(ENTREE.rglob("images_ajouts.csv"))[0]
appareil = "cuda"
P = ["p_saine", "p_black_sigatoka", "p_fusarium"]


def jeux():
    """Mêmes listes, dans le même ordre, que le carnet predictions-adoption-v5-v7."""
    idx = pd.read_csv(INDEX)
    idx = idx[idx.retenue.astype(bool)]
    out = {}
    for nom, s in (("validation", idx[idx.ensemble.eq("validation")]),
                   ("bananalsd", idx[idx.ensemble.eq("test") & idx.source.eq("bananalsd")])):
        out[nom] = pd.DataFrame(dict(chemin="data/feuilles/" + s.chemin.values, kaggle=[str(INDEX.parent / c) for c in s.chemin],
                                     jeu=s.source.values, classe_vraie=s.classe.values))
    f = pd.read_csv(FEUILLES)
    out["val_loin_feuilles"] = pd.DataFrame(dict(chemin="data/roamer_val_loin_feuilles/" + f.image, kaggle=[str(FEUILLES.parent / i) for i in f.image],
                                                 jeu=f.projet.values, classe_vraie=f.etat.values, photo=f.photo.values, groupe=f.groupe.values))
    return out


def jeux_caracteristiques(base):
    idx = pd.read_csv(INDEX)
    idx = idx[idx.retenue.astype(bool) & idx.chemin.notna()]
    ent = idx[idx.ensemble.eq("entrainement")]
    aj = ent.groupby(["source", "classe"], group_keys=False).apply(lambda g: g.sample(min(500, len(g)), random_state=2026))
    a = pd.read_csv(AJOUTS)
    t = a[a.jeu.eq("tdtu") & a.classe.isin(["autre_maladie", "black_sigatoka"])]
    rel = [i.removeprefix("ajouts_v3/") for i in t.image]
    return {"ajustement": pd.DataFrame(dict(chemin="data/feuilles/" + aj.chemin.values, kaggle=[str(INDEX.parent / c) for c in aj.chemin],
                                            classe=aj.classe.values, source=aj.source.values)),
            "tdtu": pd.DataFrame(dict(chemin=["data/feuilles_v3_ajouts/" + r for r in rel], kaggle=[str(AJOUTS.parent / r) for r in rel],
                                      classe=t.classe.values, source="tdtu")),
            "validation": base["validation"].rename(columns={"classe_vraie": "classe"}).assign(source="tanzanie_2022"),
            "bananalsd": base["bananalsd"].rename(columns={"classe_vraie": "classe"}).assign(source="bananalsd")}


class Images(Dataset):
    def __init__(self, c):
        self.c = c
    def __len__(self):
        return len(self.c)
    def __getitem__(self, i):
        return classifieur.PREPARATION(classifieur.preparer(self.c[i]))


def charge(chemins):
    return DataLoader(Images(chemins), batch_size=64, num_workers=4)


@torch.no_grad()
def probas(reseaux, chemins):
    s = []
    for x in charge(chemins):
        x = x.to(appareil)
        s.append(torch.stack([sum(torch.softmax(r(v(x)), 1) for v in classifieur.VUES) / 4 for r in reseaux]).mean(0).cpu())
    return torch.cat(s).numpy()


@torch.no_grad()
def caracteristiques(reseaux, chemins):
    car, log = [[] for _ in reseaux], [[] for _ in reseaux]
    for x in charge(chemins):
        x = x.to(appareil)
        for k, r in enumerate(reseaux):
            z = r.classifier[1](r.classifier[0](r.avgpool(r.features(x))))
            car[k].append(z.cpu().numpy()); log[k].append(r.classifier[2](z).cpu().numpy())
    return np.stack([np.concatenate(c) for c in car]).astype(np.float32), np.stack([np.concatenate(l) for l in log]).astype(np.float32)


def lire(p):
    return {k: v.float() if v.is_floating_point() else v for k, v in torch.load(p, map_location="cpu", weights_only=True).items()}


dossier_v2 = sorted(ENTREE.rglob("maladies_v2_convnext_tiny_1.pt"))[0].parent
dossier_v8 = sorted(ENTREE.rglob("maladies_v8_convnext_tiny_1.pt"))[0].parent
v2, _ = classifieur.charger(dossier_v2)
v2 = [r.to(appareil).eval() for r in v2]
base = jeux()

# contrôle de la préparation
for j, d in base.items():
    d.head(8).drop(columns="kaggle").assign(**dict(zip(P, probas(v2, list(d.kaggle.head(8))).T.round(6)))).to_csv(SORTIE / f"controle_v2_{j}.csv", index=False)
print("contrôle écrit", flush=True)

# B : caractéristiques de la v2
for nom, d in jeux_caracteristiques(base).items():
    t0 = time.time()
    car, log = caracteristiques(v2, list(d.kaggle))
    np.savez_compressed(SORTIE / f"caracteristiques_{nom}.npz", car=car, logits=log, chemin=np.array(d.chemin), classe=np.array(d.classe),
                        source=np.array(d.source))
    print(f"caractéristiques {nom} : {len(d)} photos en {(time.time() - t0) / 60:.1f} min", flush=True)

# A2 : soupe v2 + v8
a, b = sorted(dossier_v2.glob("maladies_v2_convnext_tiny_*.pt")), sorted(dossier_v8.glob("maladies_v8_convnext_tiny_*.pt"))
assert len(a) == len(b) == 3
soupe = []
for fa, fb in zip(a, b):
    wa, wb = lire(fa), lire(fb)
    assert wa.keys() == wb.keys()
    m = models.convnext_tiny(weights=None)
    m.classifier[2] = torch.nn.Linear(m.classifier[2].in_features, 3)
    m.load_state_dict({k: (wa[k] + wb[k]) / 2 if wa[k].is_floating_point() else wa[k] for k in wa})
    soupe.append(m.to(appareil).eval())
for j, d in base.items():
    t0 = time.time()
    d.drop(columns="kaggle").assign(**dict(zip(P, probas(soupe, list(d.kaggle)).T.round(6)))).to_csv(SORTIE / f"predictions_soupe_{j}.csv", index=False)
    print(f"soupe {j} : {len(d)} photos en {(time.time() - t0) / 60:.1f} min", flush=True)
print("->", sorted(p.name for p in SORTIE.iterdir()), flush=True)
