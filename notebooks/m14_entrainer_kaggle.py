# Field Scan, nuit du 13 au 14 novembre 2026, agent M-entraîneur (plan docs/plan_nuit_2026-11-13.md, section 4.2).
# Reprend notebooks/m12_entrainer_v12_kaggle.py (nuit du 12/11) avec :
#   ME1 : distillation de F1 (mélange géométrique v10b lue entière + morceaux 2 x 2, soupe, v2) dans un seul ConvNeXt-Tiny ;
#   ME2 : v12 avec les leçons (sans PSFD, 50/50 par source, jeux neufs, morceaux de feuilles en augmentation).
# Phase « maître » (si aucune sortie d'un carnet précédent n'est fournie) : probabilités de v10b (entière et 2 x 2), soupe
#   et v2 sur les images d'APPRENTISSAGE et sur roamer_dev_loin_feuilles (jeu de réglage, pour la mesure de F1).
# Phase « élèves » : MODE "plis" = un réseau par pli (sans TDTU, sans Éthiopie), lu sur le pays tenu à l'écart et sur les
#   jeux jamais appris (validation Tanzanie, PSFD, AgroVisionBD, roamer_dev_loin) ; MODE "final" = un réseau sur tout.
# Le carnet n'écrit que des probabilités : aucune décision, aucun score. Aucun juge n'est lu (contrôle par chemin et SHA-256).
import copy, io, json, os, random, subprocess, sys, threading, time, traceback
from pathlib import Path
import numpy as np, pandas as pd, torch
from PIL import Image, ImageOps
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms as T
from torchvision import models as tvm
from concurrent.futures import ThreadPoolExecutor

MODE = "plis"            # remplacé en dur dans la copie envoyée à Kaggle
RECETTES = [dict(nom="d1")]   # remplacé en dur dans la copie envoyée à Kaggle
T0 = time.time()
DEFAUT = dict(epoques=3, n_epoque=16000, lr_reseau=1e-5, lr_tete=1e-4, poids_ratee=2.0, lissage=0.0, parts="tanz40", ema=0.998,
              depart=0, lot=32, pays_hors=["psfd"], taille=224, morceaux=0.0, morceaux_taille=(0.45, 0.6), basse_res=0.3,
              jeux_en_plus=["mendeley_5nfjzntwd8_bangladesh", "mendeley_6yy9522rdy_bangladesh"], sain_source=True, graine=0,
              alpha=0.0, temperature=1.0, depart_poids=None)
# alpha = part de la perte de distillation (entropie croisée douce contre F1) ; 1 - alpha = perte pondérée sur les étiquettes
CLASSES = ["saine", "black_sigatoka", "fusarium", "autre"]
SANS_NOM = 4
PLIS = ["tdtu", "ethiopie"]
GPU = torch.cuda.is_available()
NB_GPU = torch.cuda.device_count() if GPU else 1
print("mode", MODE, "| recettes", [r["nom"] for r in RECETTES], "| GPU", [torch.cuda.get_device_name(i) for i in range(NB_GPU)] if GPU else "processeur", flush=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "timm>=1.0.20"], check=True)
import timm

# 1. Données
E = Path("/kaggle/input")
def un(nom, filtre=None):
    t = sorted(p for p in E.rglob(nom) if filtre is None or filtre in str(p))
    assert t, nom
    return t[0]
INDEX, AJOUTS, NUIT, LISTES = un("index.csv"), un("images_ajouts.csv"), un("nuit.csv"), un("listes_v10b.csv")
P_V10B = sorted(E.rglob("maladies_v10b_*.pt")); P_SOUPE = sorted(E.rglob("maladies_soupe_convnext_tiny_*.pt"))
P_V2 = sorted(E.rglob("maladies_v2_convnext_tiny_*.pt"))
assert len(P_V10B) == 3 and len(P_SOUPE) == 3 and len(P_V2) == 3, (P_V10B, P_SOUPE, P_V2)
AGRO, ROAMER, NEUFS = un("agrovision_384.csv"), un("feuilles.csv", "roamer"), un("liste_entrainement.csv")
SORTIE = Path("/kaggle/working")
nuit = pd.read_csv(NUIT)
BASE_NUIT = NUIT.parent
if not (BASE_NUIT / nuit.image.iloc[0]).exists():
    trouve = next(E.rglob(Path(nuit.image.iloc[0]).name)); BASE_NUIT = trouve.parents[len(Path(nuit.image.iloc[0]).parts) - 1]


def fichier(c):
    if c.startswith("data/feuilles/"):
        return str(INDEX.parent / c.removeprefix("data/feuilles/"))
    if c.startswith("data/feuilles_v3_ajouts/"):
        return str(AJOUTS.parent / c.removeprefix("data/feuilles_v3_ajouts/"))
    return str(BASE_NUIT / c)


VERS = {"saine": 0, "cercosporiose_noire": 1, "black_sigatoka": 1, "fusariose": 2, "cordana": 3, "pestalotiopsis": 3,
        "sigatoka_jaune": 3, "xanthomonas": 3, "autre_maladie": SANS_NOM, "sigatoka": SANS_NOM}
idx_tout = pd.read_csv(INDEX)
idx = idx_tout[idx_tout.retenue.astype(bool) & idx_tout.chemin.notna() & idx_tout.ensemble.eq("entrainement")]
SHA_JUGES = set(idx_tout[idx_tout.ensemble.eq("test_perou")].sha256.dropna())   # Cordana du Pérou : jamais lue
assert not SHA_JUGES & set(idx.sha256.dropna())
base = pd.DataFrame(dict(chemin="data/feuilles/" + idx.chemin.values, pays=idx.source.values, classe_vraie=idx.classe.values))
bd = nuit[nuit.role.eq("apprentissage")]
bd = pd.DataFrame(dict(chemin=bd.image.values, pays=bd.jeu.values, classe_vraie=bd.classe.values))
L = pd.read_csv(LISTES)
mesures = {j: L[L.jeu.eq(j)].reset_index(drop=True) for j in ["validation", "tdtu", "psfd", "ethiopie"]}
pays = pd.concat([mesures[j].rename(columns={"jeu": "pays"}) for j in ["tdtu", "ethiopie"]], ignore_index=True)
ln = pd.read_csv(NEUFS)
racine_n = NEUFS.parent
if not (racine_n / ln.fichier.iloc[0]).exists():
    trouve = next(E.rglob(Path(ln.fichier.iloc[0]).name)); racine_n = trouve.parents[len(Path(ln.fichier.iloc[0]).parts) - 1]
neufs = pd.DataFrame(dict(chemin="nuit_1112/" + ln.fichier.values, pays=ln.jeu.values,
                          classe_vraie=ln.classe.map({"saine": "saine", "black_sigatoka": "black_sigatoka", "fusarium": "fusariose",
                                                      "autre": "cordana", "inconnue": "sigatoka"}).values,
                          fichier=[str(racine_n / f) for f in ln.fichier]))
appr = pd.concat([base, bd, pays], ignore_index=True)
appr["fichier"] = [fichier(c) for c in appr.chemin]
appr = pd.concat([appr, neufs], ignore_index=True).reset_index(drop=True)
appr["y"] = [VERS[c] for c in appr.classe_vraie]
for j in mesures:
    mesures[j]["fichier"] = [fichier(c) for c in mesures[j].chemin]
ag = pd.read_csv(AGRO)
racine_a = AGRO.parent
if not (racine_a / ag.png.iloc[0]).exists():   # dossier envoyé en zip : retrouver où Kaggle l'a décompressé
    trouve = next(E.rglob(Path(ag.png.iloc[0]).name)); racine_a = trouve.parents[len(Path(ag.png.iloc[0]).parts) - 1]
mesures["agrovision"] = pd.DataFrame(dict(chemin=ag.chemin, jeu="agrovision", classe_vraie=ag.classe_vraie, fichier=[str(racine_a / p) for p in ag.png]))
ro = pd.read_csv(ROAMER)
racine_r = ROAMER.parent
if not (racine_r / ro.image.iloc[0]).exists():
    trouve = next(E.rglob(Path(ro.image.iloc[0]).name)); racine_r = trouve.parents[len(Path(ro.image.iloc[0]).parts) - 1]
mesures["roamer_dev_loin"] = pd.DataFrame(dict(chemin=ro.image, jeu="roamer_dev_loin", classe_vraie=ro.etat, fichier=[str(racine_r / p) for p in ro.image]))
# contrôles : aucun juge, la validation n'est jamais apprise, tailles attendues
INTERDITS = ("banspot", "cordana_perou", "test_perou", "sig_per", "symptomatic")
for f in list(appr.fichier) + [f for g in mesures.values() for f in g.fichier]:
    assert not any(s in f.lower() for s in INTERDITS), f
assert not set(appr.chemin) & set(mesures["validation"].chemin)
assert len(base) == 16963 and len(bd) == 422 and len(mesures["validation"]) == 3001 and len(mesures["tdtu"]) == 1636
assert len(mesures["ethiopie"]) == 1289 and len(mesures["psfd"]) == 738 and len(mesures["agrovision"]) == 1082 and len(neufs) == 1405
assert all(Path(f).exists() for f in list(appr.fichier[::50]) + list(mesures["agrovision"].fichier[::50]) + list(mesures["roamer_dev_loin"].fichier[::50]))
print("apprentissage", appr.groupby(["pays", "y"]).size().to_dict(), flush=True)

# 2. Préparation (fieldscan/modules/maladies.py, preparer_convnext) ; tout en uint8, normalisation sur le GPU
MOY, ECT = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


def fit_jpeg(im, taille):
    petite = ImageOps.fit(im, (taille, taille), method=Image.BILINEAR)
    t = io.BytesIO(); petite.save(t, format="JPEG", quality=95)
    return np.asarray(Image.open(t).convert("RGB"), dtype="uint8")


def ouvrir(chemin, lecture):
    with Image.open(chemin) as im:
        im.draft("RGB", (lecture, lecture))
        return ImageOps.exif_transpose(im).convert("RGB")


def preparer(chemin, taille, lecture):
    return fit_jpeg(ouvrir(chemin, lecture), taille)


def morceaux(im):
    w, h = im.size
    mw, mh = max(1, round(0.6 * w)), max(1, round(0.6 * h))
    return [im.crop((round(ix * (w - mw)), round(iy * (h - mh)), round(ix * (w - mw)) + mw, round(iy * (h - mh)) + mh))
            for iy in range(2) for ix in range(2)]


def en_memoire(fichiers, taille, lecture):
    with ThreadPoolExecutor(4) as ex:
        return np.stack(list(ex.map(lambda f: preparer(f, taille, lecture), fichiers)))


X_APPR = en_memoire(appr.fichier, 224, 448)          # apprentissage en 224 px ; aussi l'entrée de la soupe et de la v2
X_MES = {j: en_memoire(g.fichier, 384, 896) for j, g in mesures.items()}
print(f"photos en mémoire : {len(X_APPR)} + {sum(len(x) for x in X_MES.values())} en {(time.time() - T0) / 60:.1f} min", flush=True)
VERROU = threading.Lock()
VUES = [lambda x: x, lambda x: x.flip(3), lambda x: x.flip(2), lambda x: x.rot90(1, (2, 3))]


def normaliser(x, appareil):
    moy, ect = torch.tensor(MOY, device=appareil).view(1, 3, 1, 1), torch.tensor(ECT, device=appareil).view(1, 3, 1, 1)
    x = x.to(appareil, non_blocking=True).permute(0, 3, 1, 2).float().div(255.0)
    return ((x - moy) / ect).contiguous(memory_format=torch.channels_last)


@torch.no_grad()
def proba(reseaux, x):
    with torch.autocast("cuda", dtype=torch.float16, enabled=GPU):
        return torch.stack([sum(torch.softmax(r(v(x)).float(), 1) for v in VUES) / len(VUES) for r in reseaux]).mean(0)


def charger(chemins, genre, appareil):
    out = []
    for p in chemins:
        if genre == "timm":
            r = timm.create_model("convnext_tiny.dinov3_lvd1689m", pretrained=False, num_classes=4)
        else:
            r = tvm.convnext_tiny(weights=None); r.classifier[2] = torch.nn.Linear(r.classifier[2].in_features, 3)
        w = torch.load(p, map_location="cpu", weights_only=True)
        r.load_state_dict({k: v.float() if v.is_floating_point() else v for k, v in w.items()})
        out.append(r.to(appareil).eval().to(memory_format=torch.channels_last))
    return out


# 3. Phase « maître » : P10 (384 px), G2 (4 morceaux, 384 px), Pso et Pv2 (224 px) ; 4 vues, moyenne des 3 réseaux
class LotMaitre(Dataset):
    def __init__(self, fichiers): self.f = list(fichiers)
    def __len__(self): return len(self.f)
    def __getitem__(self, i):
        im = ouvrir(self.f[i], 896)
        return torch.from_numpy(np.stack([fit_jpeg(im, 384)] + [fit_jpeg(m, 384) for m in morceaux(im)]))


def maitre_sur(fichiers, x224, appareil, etiquette):
    with VERROU:
        r10, rso, rv2 = charger(P_V10B, "timm", appareil), charger(P_SOUPE, "tv", appareil), charger(P_V2, "tv", appareil)
        charge = DataLoader(LotMaitre(fichiers), batch_size=8, num_workers=2)
        it = iter(charge)
    P10, G2, t0, n = [], [], time.time(), 0
    for x in it:
        b = x.shape[0]
        p = proba(r10, normaliser(x.flatten(0, 1), appareil)).reshape(b, 5, 4).cpu().numpy()
        P10.append(p[:, 0]); G2.append(p[:, 1:]); n += b
        if n % 2000 < b:
            print(f"[maître {etiquette}] {n}/{len(fichiers)} ({(time.time() - t0) / n:.3f} s par photo)", flush=True)
    Pso, Pv2 = [], []
    for i in range(0, len(x224), 64):
        x = normaliser(torch.from_numpy(x224[i:i + 64]), appareil)
        Pso.append(proba(rso, x).cpu().numpy()); Pv2.append(proba(rv2, x).cpu().numpy())
    del r10, rso, rv2
    return np.concatenate(P10), np.concatenate(G2), np.concatenate(Pso), np.concatenate(Pv2)


def lecture_morceaux(P10, G2):
    pm = ((1 - P10[:, 0]) + np.sort(1 - G2[:, :, 0], 1)[:, -2:].mean(1)) / 2
    reste = np.clip(1 - P10[:, 0], 1e-9, None)
    Q = P10 * (pm / reste)[:, None]; Q[:, 0] = 1 - pm
    return Q


def melange_geometrique(P10, Pso, Pv2):
    w = 1 / 3
    lg = w * (np.log(np.clip(P10[:, :3], 1e-9, 1)) + np.log(np.clip(Pso, 1e-9, 1)) + np.log(np.clip(Pv2, 1e-9, 1)))
    q = np.hstack([np.exp(lg), w * P10[:, 3:]])
    return q / q.sum(1, keepdims=True)


MAITRE_PRET = sorted(E.rglob("maitre_appr.npz"))
if MAITRE_PRET:
    m_ = np.load(MAITRE_PRET[0], allow_pickle=True)
    assert list(m_["chemin"]) == list(appr.chemin)
    Q_APPR = m_["Q"]
    print("maître repris de", MAITRE_PRET[0], flush=True)
else:
    roamer224 = en_memoire(mesures["roamer_dev_loin"].fichier, 224, 448)
    taches = [("appr", list(appr.fichier), X_APPR), ("roamer_dev_loin", list(mesures["roamer_dev_loin"].fichier), roamer224),
              ("validation_controle", list(mesures["validation"].fichier[:300]), en_memoire(mesures["validation"].fichier[:300], 224, 448))]
    res = {}
    def file_maitre(k):
        app = f"cuda:{k}" if GPU else "cpu"
        for nom, f, x224 in taches:
            moitie = np.array_split(np.arange(len(f)), NB_GPU)[k]
            res[(nom, k)] = maitre_sur([f[i] for i in moitie], x224[moitie], app, f"{nom} {k}")
    fils = [threading.Thread(target=file_maitre, args=(k,)) for k in range(NB_GPU)]
    [f.start() for f in fils]; [f.join() for f in fils]
    for nom, f, _ in taches:
        P10, G2, Pso, Pv2 = (np.concatenate([res[(nom, k)][i] for k in range(NB_GPU)]) for i in range(4))
        Q = melange_geometrique(lecture_morceaux(P10, G2), Pso, Pv2)
        chem = list(appr.chemin) if nom == "appr" else list(mesures["roamer_dev_loin" if nom == "roamer_dev_loin" else "validation"].chemin[:len(f)])
        np.savez_compressed(SORTIE / f"maitre_{nom}.npz", chemin=np.array(chem, dtype=object), P10=P10, G2=G2, Pso=Pso, Pv2=Pv2, Q=Q)
    Q_APPR = np.load(SORTIE / "maitre_appr.npz", allow_pickle=True)["Q"]
    print(f"phase maître finie à {(time.time() - T0) / 60:.1f} min", flush=True)
assert Q_APPR.shape == (len(appr), 4) and np.isfinite(Q_APPR).all()


# 4. Augmentations (carnet du 12/11)
class JPEGAleatoire:
    def __init__(self, p=0.5, qualites=(30, 95)): self.p, self.qualites = p, qualites
    def __call__(self, image):
        if random.random() >= self.p: return image
        t = io.BytesIO(); image.save(t, format="JPEG", quality=random.randint(*self.qualites))
        return Image.open(t).convert("RGB")


class Morceau:
    """Avec la probabilité p, la photo est remplacée par un de ses morceaux (côté tiré dans `taille`), même cible."""
    def __init__(self, p, taille): self.p, self.taille = p, taille
    def __call__(self, image):
        if random.random() >= self.p: return image
        w, h = image.size; f = random.uniform(*self.taille)
        cw, ch = int(w * f), int(h * f)
        x0, y0 = random.randint(0, w - cw), random.randint(0, h - ch)
        return image.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.BILINEAR)


class BasseRes:
    def __init__(self, p): self.p = p
    def __call__(self, image):
        if random.random() >= self.p: return image
        w, h = image.size; c = random.randint(100, 160)
        return image.resize((c, max(1, int(c * h / w))), Image.BILINEAR).resize((w, h), Image.BILINEAR)


def augmentations(R):
    tr = [JPEGAleatoire(), T.RandomResizedCrop(R["taille"], scale=(0.4, 1.0), ratio=(0.8, 1.25)),
          T.RandomHorizontalFlip(), T.RandomVerticalFlip(), T.RandomRotation(30),
          T.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.04),
          T.RandomApply([T.GaussianBlur(5, sigma=(0.1, 2.0))], p=0.3),
          T.ToTensor(), T.Normalize(MOY, ECT), T.RandomErasing(p=0.5, scale=(0.02, 0.15))]
    if R["morceaux"] > 0: tr.insert(0, Morceau(R["morceaux"], tuple(R["morceaux_taille"])))
    if R["basse_res"] > 0: tr.insert(0, BasseRes(R["basse_res"]))
    return T.Compose(tr)


class Feuilles(Dataset):
    def __init__(self, lignes, y, q, tr): self.l, self.y, self.q, self.tr = np.asarray(lignes), np.asarray(y), np.asarray(q, "float32"), tr
    def __len__(self): return len(self.l)
    def __getitem__(self, i):
        k = self.l[i]
        return self.tr(Image.fromarray(X_APPR[k])), int(self.y[k]), torch.from_numpy(self.q[k])


def poids_tirage(df, R):
    sources = list(df.pays.unique())
    fixe = {"tanzanie_2021": 0.40, "perou_2026": 0.10, "mendeley_bd": 0.05}
    autres = [s for s in sources if s not in fixe]
    reste = 1 - sum(v for s, v in fixe.items() if s in sources)
    part = {s: fixe[s] for s in sources if s in fixe}
    part.update({s: reste / len(autres) for s in autres})
    n_classes = df.groupby("pays").y.nunique(); n = df.groupby(["pays", "y"]).y.transform("size")
    w = (df.pays.map(part) / df.pays.map(n_classes) / n).to_numpy(dtype="float64").copy()
    if R["sain_source"]:
        s_ = df.y.to_numpy() == 0
        for src in df.pays.unique():
            k_ = (df.pays == src).to_numpy()
            if s_[k_].any() and (~s_[k_]).any():
                tot_ = w[k_].sum(); w[k_ & s_] *= 0.5 * tot_ / w[k_ & s_].sum(); w[k_ & ~s_] *= 0.5 * tot_ / w[k_ & ~s_].sum()
    return w


def perte(z, y, q, R):
    lp = torch.log_softmax(z.float() / R["temperature"], 1)
    l_dist = -(q * lp).sum(1) * R["temperature"] ** 2
    lp1 = torch.log_softmax(z.float(), 1)
    l_malade = -torch.logsumexp(lp1[:, 1:], 1)
    nomme = y < SANS_NOM
    yc = torch.where(nomme, y, torch.zeros_like(y))
    ce = -(1 - R["lissage"]) * lp1.gather(1, yc[:, None])[:, 0] - R["lissage"] * lp1.mean(1)
    l_etiq = torch.where(nomme, ce + (R["poids_ratee"] - 1) * l_malade * (nomme & (y > 0)), R["poids_ratee"] * l_malade)
    return (R["alpha"] * l_dist + (1 - R["alpha"]) * l_etiq).mean()


def nouveau(R, appareil):
    r = timm.create_model("convnext_tiny.dinov3_lvd1689m", pretrained=False, num_classes=4)
    w = torch.load(P_V10B[R["depart"]], map_location="cpu", weights_only=True)
    r.load_state_dict({n: v.float() if v.is_floating_point() else v for n, v in w.items()})
    return r.to(appareil)


def entrainer(R, df, appareil, etiquette):
    torch.manual_seed(R["graine"]); g = torch.Generator().manual_seed(R["graine"])
    with VERROU:
        m = nouveau(R, appareil).to(memory_format=torch.channels_last)
    ema = copy.deepcopy(m).eval()
    for p in ema.parameters(): p.requires_grad_(False)
    tete = [p for n, p in m.named_parameters() if n.startswith("head.fc")]
    corps = [p for n, p in m.named_parameters() if not n.startswith("head.fc")]
    opt = torch.optim.AdamW([dict(params=corps, lr=R["lr_reseau"]), dict(params=tete, lr=R["lr_tete"])], weight_decay=0.05)
    pas_total = R["epoques"] * (R["n_epoque"] // R["lot"])
    plan = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=pas_total)
    echelle = torch.amp.GradScaler("cuda", enabled=GPU)
    tirage = WeightedRandomSampler(torch.tensor(poids_tirage(df, R)), R["n_epoque"], replacement=True, generator=g)
    charge = DataLoader(Feuilles(df.index.to_numpy(), appr.y.to_numpy(), Q_APPR, augmentations(R)), R["lot"], sampler=tirage,
                        num_workers=2, persistent_workers=True, drop_last=True)
    with VERROU:
        iter(charge)
    pas = 0
    for e in range(R["epoques"]):
        m.train(); t0, tot, n = time.time(), 0.0, 0
        for x, yb, qb in charge:
            x, yb, qb = x.to(appareil).contiguous(memory_format=torch.channels_last), yb.to(appareil), qb.to(appareil)
            opt.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.float16, enabled=GPU):
                l = perte(m(x), yb, qb, R)
            echelle.scale(l).backward(); echelle.unscale_(opt); torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
            echelle.step(opt); echelle.update(); plan.step(); pas += 1
            d = min(R["ema"], (1 + pas) / (10 + pas))
            with torch.no_grad():
                for pe, pm in zip(ema.parameters(), m.parameters()): pe.mul_(d).add_(pm.detach(), alpha=1 - d)
            tot += l.item() * len(yb); n += len(yb)
        assert np.isfinite(tot)
        print(f"[{etiquette}] époque {e + 1}/{R['epoques']} perte {tot / n:.4f} ({time.time() - t0:.0f} s)", flush=True)
    del charge, opt
    return ema.eval()


def lire(r, X, appareil, lot=48):
    return np.concatenate([proba([r], normaliser(torch.from_numpy(X[i:i + lot]), appareil)).cpu().numpy() for i in range(0, len(X), lot)])


def ecrire(P, df, chemin):
    out = df[["chemin", "jeu", "classe_vraie"]].copy()
    for k, c in enumerate(["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]): out[c] = P[:, k].round(6)
    out.to_csv(chemin, index=False)


COMMUNS = ["validation", "psfd", "agrovision", "roamer_dev_loin"]   # jamais appris : lus par chaque pli


def une_recette(R, appareil):
    R = {**DEFAUT, **R}; nom = R["nom"]
    (SORTIE / f"recette_{nom}.json").write_text(json.dumps(dict(mode=MODE, **R), ensure_ascii=False), encoding="utf-8")
    retires = list(R["pays_hors"]) + [j for j in DEFAUT["jeux_en_plus"] if j not in R["jeux_en_plus"]]
    if MODE == "plis":
        for x in PLIS:
            df = appr[~appr.pays.isin([x] + retires)]
            r = entrainer(R, df, appareil, f"{nom} sans {x}")
            ecrire(lire(r, X_MES[x], appareil), mesures[x], SORTIE / f"predictions_{nom}_{x}.csv")
            for j in COMMUNS:
                ecrire(lire(r, X_MES[j], appareil), mesures[j], SORTIE / f"predictions_{nom}_{j}_pli_{x}.csv")
            if R.get("garder"):   # 14/11 : le modèle livrable est l'ensemble des 2 réseaux des plis
                torch.save({n: (t.half() if t.is_floating_point() else t) for n, t in r.state_dict().items()},
                           SORTIE / f"maladies_m13{nom}_sans_{x}.pt")
            del r
            print(f"[{nom}] pli sans {x} écrit à {(time.time() - T0) / 60:.1f} min", flush=True)
    else:
        df = appr[~appr.pays.isin(retires)]
        r = entrainer(R, df, appareil, f"{nom} final")
        torch.save({n: (t.half() if t.is_floating_point() else t) for n, t in r.state_dict().items()}, SORTIE / f"maladies_m13{nom}_0.pt")
        for j in COMMUNS:
            ecrire(lire(r, X_MES[j], appareil), mesures[j], SORTIE / f"predictions_{nom}_final_{j}.csv")


echecs = []
def file(k):
    appareil = f"cuda:{k}" if GPU else "cpu"
    for R in RECETTES[k::NB_GPU]:
        t0 = time.time()
        try:
            une_recette(R, appareil); print(f"recette {R['nom']} finie en {(time.time() - t0) / 60:.1f} min sur {appareil}", flush=True)
        except Exception:
            echecs.append(R["nom"]); traceback.print_exc()
        if GPU: torch.cuda.empty_cache()


fils = [threading.Thread(target=file, args=(k,)) for k in range(NB_GPU)]
[f.start() for f in fils]; [f.join() for f in fils]
print(f"fini en {(time.time() - T0) / 60:.1f} min ; échecs :", echecs, flush=True)
assert not echecs, echecs
