# Field Scan, nuit du 13 au 14 novembre 2026, agent M-entraîneur : ME3, lecteur « loin » neuf (plan du 13/11, 4.2).
# ConvNeXt-Tiny (torchvision), 2 classes (saine, malade), départ = réseau 1 de la v9 « loin » ; préparation de la v2
# (224 px, JPEG lu en 448 px), 4 vues à la lecture.
# Apprentissage : photos entières du robot ROAMER de dev_loin (1 312, rôle apprentissage_loin de photos-loin) ; jeux
# neufs du Bangladesh (feuilles-nuit-1112) ; photos « loin » (p_loin >= 0,5, liste fournie) de TDTU et d'Éthiopie dans les
# plis qui ne les mesurent pas. Jamais : validation Tanzanie, PSFD, AgroVisionBD, roamer_dev_loin_feuilles, juges.
# Tirage : sources à parts égales, 50/50 saines / malades dans chaque source. Sorties : P(malade) par photo seulement.
import copy, io, json, random, subprocess, sys, threading, time, traceback
from pathlib import Path
import numpy as np, pandas as pd, torch
from PIL import Image, ImageOps
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms as T
from torchvision import models as tvm
from concurrent.futures import ThreadPoolExecutor

RECETTES = [dict(nom="l1")]   # remplacé en dur dans la copie envoyée à Kaggle
LOIN_PAYS = {}                # remplacé en dur : {"tdtu": [chemins], "ethiopie": [chemins]} (p_loin >= 0,5, caches locaux)
DEFAUT = dict(epoques=4, n_epoque=4000, lr=3e-5, lr_tete=3e-4, lot=32, ema=0.998, lissage=0.1, graine=0, depart=1,
              robot=True, depart_v2=False)
# robot=False et depart_v2=True (l1b, 14/11) : ni photos du robot dev_loin ni v9 (apprise sur roamer_dev_loin_feuilles),
# pour que roamer_dev_loin_feuilles reste un jeu de mesure sans fuite ; départ = réseau 1 de la v2 (tête neuve à 2 classes).
T0 = time.time()
GPU = torch.cuda.is_available(); NB_GPU = torch.cuda.device_count() if GPU else 1
E = Path("/kaggle/input"); SORTIE = Path("/kaggle/working")


def un(nom, filtre=None):
    t = sorted(p for p in E.rglob(nom) if filtre is None or filtre in str(p)); assert t, nom; return t[0]


def racine(liste_csv, rel):
    r = liste_csv.parent
    if not (r / rel).exists():
        trouve = next(E.rglob(Path(rel).name)); r = trouve.parents[len(Path(rel).parts) - 1]
    return r


INDEX, AJOUTS, NUIT, LISTES = un("index.csv"), un("images_ajouts.csv"), un("nuit.csv"), un("listes_v10b.csv")
PL, NEUFS, AGRO, ROAMER = un("liste_photos_loin.csv"), un("liste_entrainement.csv"), un("agrovision_384.csv"), un("feuilles.csv", "roamer")
P_V9 = sorted(E.rglob("maladies_v9_loin_*.pt")); assert len(P_V9) == 3
P_V2 = sorted(E.rglob("maladies_v2_convnext_tiny_*.pt")); assert len(P_V2) == 3
nuit = pd.read_csv(NUIT); BASE_NUIT = racine(NUIT, nuit.image.iloc[0])


def fichier(c):
    if c.startswith("data/feuilles/"): return str(INDEX.parent / c.removeprefix("data/feuilles/"))
    if c.startswith("data/feuilles_v3_ajouts/"): return str(AJOUTS.parent / c.removeprefix("data/feuilles_v3_ajouts/"))
    return str(BASE_NUIT / c)


pl = pd.read_csv(PL); pl = pl[pl.role.eq("apprentissage_loin")]; rp = racine(PL, pl.fichier.iloc[0])
robot = pd.DataFrame(dict(chemin=pl.fichier, pays="robot", y=(pl.source != "robot_roamer2_healthy_plantes").astype(int), fichier=[str(rp / f) for f in pl.fichier]))
ln = pd.read_csv(NEUFS); rn = racine(NEUFS, ln.fichier.iloc[0])
neufs = pd.DataFrame(dict(chemin=ln.fichier, pays=ln.jeu, y=(ln.classe != "saine").astype(int), fichier=[str(rn / f) for f in ln.fichier]))
L = pd.read_csv(LISTES)
mes = {j: L[L.jeu.eq(j)].reset_index(drop=True) for j in ["validation", "tdtu", "psfd", "ethiopie"]}
for j in mes: mes[j]["fichier"] = [fichier(c) for c in mes[j].chemin]
pays = []
for j in ["tdtu", "ethiopie"]:
    g = mes[j][mes[j].chemin.isin(LOIN_PAYS.get(j, []))]
    pays.append(pd.DataFrame(dict(chemin=g.chemin, pays=j, y=(g.classe_vraie != "saine").astype(int), fichier=g.fichier)))
appr = pd.concat([robot, neufs] + pays, ignore_index=True)
ag = pd.read_csv(AGRO); ra = racine(AGRO, ag.png.iloc[0])
mes["agrovision"] = pd.DataFrame(dict(chemin=ag.chemin, jeu="agrovision", classe_vraie=ag.classe_vraie, fichier=[str(ra / p) for p in ag.png]))
ro = pd.read_csv(ROAMER); rr = racine(ROAMER, ro.image.iloc[0])
mes["roamer_dev_loin"] = pd.DataFrame(dict(chemin=ro.image, jeu="roamer_dev_loin", classe_vraie=ro.etat, fichier=[str(rr / p) for p in ro.image]))
INTERDITS = ("banspot", "cordana_perou", "test_perou", "sig_per", "symptomatic")
for f in list(appr.fichier) + [f for g in mes.values() for f in g.fichier]:
    assert not any(s in f.lower() for s in INTERDITS), f
assert not set(appr.chemin) & (set(mes["validation"].chemin) | set(mes["psfd"].chemin) | set(mes["agrovision"].chemin) | set(mes["roamer_dev_loin"].chemin))
assert len(robot) == 1312 and len(neufs) == 1405
print("apprentissage", appr.groupby(["pays", "y"]).size().to_dict(), flush=True)

MOY, ECT = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


def preparer(chemin):
    with Image.open(chemin) as im:
        im.draft("RGB", (448, 448)); im = ImageOps.exif_transpose(im).convert("RGB")
        petite = ImageOps.fit(im, (224, 224), method=Image.BILINEAR)
    t = io.BytesIO(); petite.save(t, format="JPEG", quality=95)
    return np.asarray(Image.open(t).convert("RGB"), dtype="uint8")


def en_memoire(f):
    with ThreadPoolExecutor(4) as ex: return np.stack(list(ex.map(preparer, f)))


X_APPR = en_memoire(appr.fichier)
# AgroVisionBD n'est disponible qu'en 384 px (préparation de la v10b) : ramené en 224 px par le même ajustement (écart noté)
X_MES = {j: en_memoire(g.fichier) for j, g in mes.items()}
print(f"en mémoire en {(time.time() - T0) / 60:.1f} min", flush=True)
VERROU = threading.Lock()
VUES = [lambda x: x, lambda x: x.flip(3), lambda x: x.flip(2), lambda x: x.rot90(1, (2, 3))]


def nouveau(R, app):
    r = tvm.convnext_tiny(weights=None); r.classifier[2] = torch.nn.Linear(r.classifier[2].in_features, 3 if R["depart_v2"] else 2)
    w = torch.load((P_V2 if R["depart_v2"] else P_V9)[R["depart"]], map_location="cpu", weights_only=True)
    r.load_state_dict({k: v.float() if v.is_floating_point() else v for k, v in w.items()})
    if R["depart_v2"]:   # tête à 2 classes : saine = saine de la v2, malade = somme des maladies (log-somme des logits)
        W, b = r.classifier[2].weight.data, r.classifier[2].bias.data
        lin = torch.nn.Linear(W.shape[1], 2)
        lin.weight.data = torch.stack([W[0], W[1:].mean(0)]); lin.bias.data = torch.stack([b[0], b[1:].mean()])
        r.classifier[2] = lin
    return r.to(app)


class JeuL(Dataset):
    def __init__(self, lignes, tr): self.l, self.tr = np.asarray(lignes), tr
    def __len__(self): return len(self.l)
    def __getitem__(self, i):
        k = self.l[i]; return self.tr(Image.fromarray(X_APPR[k])), int(appr.y.iat[k])


AUG = T.Compose([T.RandomResizedCrop(224, scale=(0.5, 1.0), ratio=(0.8, 1.25)), T.RandomHorizontalFlip(),
                 T.ColorJitter(0.3, 0.3, 0.3, 0.03), T.RandomApply([T.GaussianBlur(5, sigma=(0.1, 2.0))], p=0.3),
                 T.ToTensor(), T.Normalize(MOY, ECT), T.RandomErasing(p=0.3, scale=(0.02, 0.1))])


def entrainer(R, df, app, etiq):
    torch.manual_seed(R["graine"]); g = torch.Generator().manual_seed(R["graine"])
    with VERROU: m = nouveau(R, app)
    ema = copy.deepcopy(m).eval()
    for p in ema.parameters(): p.requires_grad_(False)
    tete = [p for n, p in m.named_parameters() if n.startswith("classifier")]
    corps = [p for n, p in m.named_parameters() if not n.startswith("classifier")]
    opt = torch.optim.AdamW([dict(params=corps, lr=R["lr"]), dict(params=tete, lr=R["lr_tete"])], weight_decay=0.05)
    pas_total = R["epoques"] * (R["n_epoque"] // R["lot"])
    plan = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=pas_total)
    w = np.zeros(len(df)); src = df.pays.to_numpy(); y = df.y.to_numpy()
    for s in np.unique(src):
        for c in (0, 1):
            k = (src == s) & (y == c)
            if k.any(): w[k] = 1.0 / k.sum() / (2 if ((src == s) & (y == 1 - c)).any() else 1)
    charge = DataLoader(JeuL(df.index.to_numpy(), AUG), R["lot"], sampler=WeightedRandomSampler(torch.tensor(w), R["n_epoque"], True, generator=g),
                        num_workers=2, persistent_workers=True, drop_last=True)
    with VERROU: iter(charge)
    ech = torch.amp.GradScaler("cuda", enabled=GPU); pas = 0
    for e in range(R["epoques"]):
        m.train(); tot, n = 0.0, 0
        for x, yb in charge:
            x, yb = x.to(app), yb.to(app); opt.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.float16, enabled=GPU):
                l = torch.nn.functional.cross_entropy(m(x).float(), yb, label_smoothing=R["lissage"])
            ech.scale(l).backward(); ech.step(opt); ech.update(); plan.step(); pas += 1
            d = min(R["ema"], (1 + pas) / (10 + pas))
            with torch.no_grad():
                for pe, pm in zip(ema.parameters(), m.parameters()): pe.mul_(d).add_(pm.detach(), alpha=1 - d)
            tot += l.item() * len(yb); n += len(yb)
        print(f"[{etiq}] époque {e + 1} perte {tot / n:.4f}", flush=True)
    return ema.eval()


@torch.no_grad()
def lire(r, X, app):
    moy, ect = torch.tensor(MOY, device=app).view(1, 3, 1, 1), torch.tensor(ECT, device=app).view(1, 3, 1, 1)
    out = []
    for i in range(0, len(X), 64):
        x = ((torch.from_numpy(X[i:i + 64]).to(app).permute(0, 3, 1, 2).float() / 255 - moy) / ect)
        with torch.autocast("cuda", dtype=torch.float16, enabled=GPU):
            out.append((sum(torch.softmax(r(v(x)).float(), 1) for v in VUES) / 4)[:, 1].cpu().numpy())
    return np.concatenate(out)


def ecrire(p, df, f):
    o = df[["chemin", "jeu", "classe_vraie"]].copy(); o["p_malade"] = p.round(6); o.to_csv(f, index=False)


def une(R, app):
    R = {**DEFAUT, **R}; nom = R["nom"]
    for x in ["tdtu", "ethiopie"]:
        df = appr[(appr.pays != x) & ((appr.pays != "robot") | R["robot"])]
        r = entrainer(R, df, app, f"{nom} sans {x}")
        ecrire(lire(r, X_MES[x], app), mes[x], SORTIE / f"loin_{nom}_{x}.csv")
        for j in ["validation", "psfd", "agrovision", "roamer_dev_loin"]:
            ecrire(lire(r, X_MES[j], app), mes[j], SORTIE / f"loin_{nom}_{j}_pli_{x}.csv")
        if R.get("garder"):
            torch.save({k: v.half() for k, v in r.state_dict().items()}, SORTIE / f"loin_{nom}_sans_{x}.pt")
        print(f"[{nom}] pli sans {x} à {(time.time() - T0) / 60:.1f} min", flush=True)


echecs = []
def file(k):
    app = f"cuda:{k}" if GPU else "cpu"
    for R in RECETTES[k::NB_GPU]:
        try: une(R, app)
        except Exception: echecs.append(R["nom"]); traceback.print_exc()


fils = [threading.Thread(target=file, args=(k,)) for k in range(NB_GPU)]
[f.start() for f in fils]; [f.join() for f in fils]
print(f"fini en {(time.time() - T0) / 60:.1f} min ; échecs {echecs}", flush=True)
assert not echecs
