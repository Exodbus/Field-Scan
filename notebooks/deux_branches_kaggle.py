# Field Scan : calculs du protocole « deux branches » (docs/protocole_maladies_deux_branches.md). Aucun score affiché.
#  - caractéristiques DINOv2 ViT-B/14 figées des photos de loin (jeu photos-loin), vue d'origine, préparation de la v2 ;
#  - probabilités et réponses de la v2 (3 réseaux, 4 vues, ses seuils) et de DINOv2-FT (ses seuils : 1 réseau, 1 vue)
#    sur TDTU (autre_maladie, black_sigatoka).
# GPU, internet activé (poids DINOv2). Sorties dans /kaggle/working.
import json, sys, time
from pathlib import Path
import numpy as np, pandas as pd, torch
from torch.utils.data import DataLoader, Dataset

ENTREE, SORTIE = Path("/kaggle/input"), Path("/kaggle/working")
CLASSIF = sorted(ENTREE.rglob("classifieur.py"))[0]
sys.path.insert(0, str(CLASSIF.parent))
import classifieur  # noqa: E402

appareil = "cuda"
LISTE = sorted(ENTREE.rglob("liste_photos_loin.csv"))[0]
AJOUTS = sorted(ENTREE.rglob("images_ajouts.csv"))[0]
VERS_COMMUN = {"saine": "saine", "black_sigatoka": "cercosporiose_noire", "fusarium": "fusariose",
               "malade_non_identifiee": "malade_non_identifiee", "inconnu": "je_ne_sais_pas"}


class Images(Dataset):
    def __init__(self, c):
        self.c = c
    def __len__(self):
        return len(self.c)
    def __getitem__(self, i):
        return classifieur.PREPARATION(classifieur.preparer(self.c[i]))


def charge(chemins):
    return DataLoader(Images(chemins), batch_size=64, num_workers=4)


dino = torch.hub.load("facebookresearch/dinov2", "dinov2_vitb14", trust_repo=True).to(appareil).eval()


def f_dino(x):
    f = dino.forward_features(x)
    return torch.cat([f["x_norm_clstoken"], f["x_norm_patchtokens"].mean(1)], 1)


# 1. Caractéristiques DINOv2 figées des photos de loin
l = pd.read_csv(LISTE)
racine = LISTE.parent
chemins = [str(racine / f) for f in l.fichier]
assert Path(chemins[0]).exists(), chemins[0]
t0, car = time.time(), []
with torch.no_grad():
    for x in charge(chemins):
        with torch.autocast("cuda", dtype=torch.float16):
            car.append(f_dino(x.to(appareil)).float().cpu().numpy().astype(np.float16))
np.savez_compressed(SORTIE / "dinov2_photos_loin.npz", car=np.concatenate(car)[None], fichier=np.array(l.fichier),
                    source=np.array(l.source), role=np.array(l.role))
print(f"photos de loin : {len(l)} en {(time.time() - t0) / 60:.1f} min", flush=True)

# 2. TDTU : v2 et DINOv2-FT, chacun avec ses seuils
a = pd.read_csv(AJOUTS)
t = a[a.jeu.eq("tdtu") & a.classe.isin(["autre_maladie", "black_sigatoka"])]
rel = [i.removeprefix("ajouts_v3/") for i in t.image]
tdtu = pd.DataFrame(dict(chemin=["data/feuilles_v3_ajouts/" + r for r in rel], classe_vraie=t.classe.values))
fichiers = [str(AJOUTS.parent / r) for r in rel]

r2, s2 = classifieur.charger(sorted(ENTREE.rglob("maladies_v2_convnext_tiny_1.pt"))[0].parent)
r2 = [r.to(appareil).eval() for r in r2]
with torch.no_grad():
    P2 = torch.cat([torch.stack([sum(torch.softmax(r(v(x.to(appareil))), 1) for v in classifieur.VUES) / 4 for r in r2]).mean(0).cpu()
                    for x in charge(fichiers)]).numpy()
tdtu.assign(p_saine=P2[:, 0].round(6), p_black_sigatoka=P2[:, 1].round(6), p_fusarium=P2[:, 2].round(6),
            reponse=[VERS_COMMUN[x] for x in classifieur.decider(P2, s2)]).to_csv(SORTIE / "predictions_tdtu_v2.csv", index=False)


class Modele(torch.nn.Module):   # comme dans notebooks/entrainer_maladies_dinov2_kaggle.py
    def __init__(self):
        super().__init__()
        self.dino = torch.hub.load("facebookresearch/dinov2", "dinov2_vitb14", trust_repo=True)
        self.tete = torch.nn.Linear(1536, 3)
    def forward(self, x):
        f = self.dino.forward_features(x)
        return self.tete(torch.cat([f["x_norm_clstoken"], f["x_norm_patchtokens"].mean(1)], 1))


dossier_ft = sorted(ENTREE.rglob("maladies_dinov2_ft_1.pt"))[0].parent
sft = json.loads((dossier_ft / "seuils.json").read_text(encoding="utf-8"))
reseaux = []
for k in range(1, sft["nb_reseaux"] + 1):
    m = Modele()
    w = torch.load(dossier_ft / f"maladies_dinov2_ft_{k}.pt", map_location="cpu", weights_only=True)
    m.load_state_dict({n: v.float() if v.is_floating_point() else v for n, v in w.items()})
    reseaux.append(m.to(appareil).eval())
vues = classifieur.VUES if sft["quatre_vues"] else classifieur.VUES[:1]
with torch.no_grad():
    PF = torch.cat([torch.stack([sum(torch.softmax(r(v(x.to(appareil))).float(), 1) for v in vues) / len(vues) for r in reseaux]).mean(0).cpu()
                    for x in charge(fichiers)]).numpy()
tdtu.assign(p_saine=PF[:, 0].round(6), p_black_sigatoka=PF[:, 1].round(6), p_fusarium=PF[:, 2].round(6),
            reponse=[VERS_COMMUN[x] for x in classifieur.decider(PF, sft)]).to_csv(SORTIE / "predictions_tdtu_dinov2_ft.csv", index=False)
print("TDTU :", len(tdtu), "photos ; DINOv2-FT :", len(reseaux), "réseau(x),", len(vues), "vue(s)", flush=True)
print("->", sorted(p.name for p in SORTIE.iterdir()), flush=True)
