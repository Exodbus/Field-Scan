# Field Scan, nuit du 12 au 13 novembre 2026 : candidats « v12 » du module maladies (plan, section 4.3, M4 et M5).
# Départ : poids de la v10b (timm convnext_tiny.dinov3_lvd1689m, 4 classes : saine, black_sigatoka, fusarium, autre).
# MODE = "plis"  : validation croisée par pays (TDTU, PSFD, Éthiopie) ; un réseau par pli, entraîné SANS le pays mesuré ;
#                  la validation Tanzanie 2022-2023 (jamais apprise) est lue par chaque pli.
# MODE = "final" : 3 réseaux (départs 0, 1, 2 de la v10b) entraînés sur tout, pays compris ; poids enregistrés en 16 bits.
# Le carnet n'écrit que des probabilités par photo : aucun score, aucun seuil. La décision se fait en local.
# Choix (journal docs/nuit_2026-11-12/journal_m_entrainement.md) : étiquettes sans nom de maladie -> −log(1 − P(saine)) ;
# Sigatoka jaune, Xanthomonas, Cordana, Pestalotiopsis -> classe « autre » ; perte pondérée ; tirage par pays et par classe ; EMA.
# ESSAI_LOCAL=1 : vérification du code sur processeur avec quelques photos.
import copy, io, json, os, random, subprocess, sys, threading, time, traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd, torch
from PIL import Image, ImageOps
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms as T

MODE = "plis"            # remplacé en dur dans la copie envoyée à Kaggle
RECETTES = [dict(nom="a1")]   # remplacé en dur dans la copie envoyée à Kaggle
ESSAI_LOCAL = os.environ.get("ESSAI_LOCAL") == "1"
DEFAUT = dict(epoques=3, n_epoque=16000, lr_reseau=1e-5, lr_tete=1e-4, poids_ratee=3.0, lissage=0.0, aug="base",
              cutmix=0.0, parts="tanz40", ema=0.998, depart=0, reseaux=[0], lot=32, sans_nom="malade", pays_hors=[],
              taille=224, dro=0.0, morceaux=0.0, deux_temps=False, jeux_en_plus=[], sain50=False, sain_source=False, basse_res=0.0, graine=0)
CLASSES = ["saine", "black_sigatoka", "fusarium", "autre"]
SANS_NOM = 4             # étiquette « malade, maladie non nommée » : perte −log(1 − P(saine))
PAYS = ["tdtu", "psfd", "ethiopie"]
GPU = torch.cuda.is_available()
NB_GPU = torch.cuda.device_count() if GPU else 1
print("mode", MODE, "| recettes", [r["nom"] for r in RECETTES], "| GPU", [torch.cuda.get_device_name(i) for i in range(NB_GPU)] if GPU else "processeur", flush=True)
if not ESSAI_LOCAL:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "timm>=1.0.20"], check=True)
import timm

# 1. Données
if ESSAI_LOCAL:
    INDEX, AJOUTS, NUIT = Path("data/feuilles/index.csv"), Path("data/feuilles_v3_ajouts/images.csv"), Path("out/maladies/maladies_nuit/nuit.csv")
    LISTES, POIDS = Path("C:/Users/coren/kaggle_tmp/v10b_poids/listes_v10b.csv"), sorted(Path("modeles/maladies_binome/v10b").glob("maladies_v10b_*.pt"))
    SORTIE = Path(os.environ.get("SORTIE_ESSAI", "out/maladies/nuit_1112/kaggle/essai_local"))
else:
    E = Path("/kaggle/input")
    INDEX, AJOUTS, NUIT = sorted(E.rglob("index.csv"))[0], sorted(E.rglob("images_ajouts.csv"))[0], sorted(E.rglob("nuit.csv"))[0]
    LISTES, POIDS = next(E.rglob("listes_v10b.csv")), sorted(E.rglob("maladies_v10b_*.pt"))
    SORTIE = Path("/kaggle/working")
SORTIE.mkdir(parents=True, exist_ok=True)
assert len(POIDS) == 3, POIDS
nuit = pd.read_csv(NUIT)
BASE_NUIT = NUIT.parent
if not (BASE_NUIT / nuit.image.iloc[0]).exists():   # dossiers envoyés en zip : retrouver où Kaggle les a décompressés
    trouve = next(Path("/kaggle/input").rglob(Path(nuit.image.iloc[0]).name))
    BASE_NUIT = trouve.parents[len(Path(nuit.image.iloc[0]).parts) - 1]


def fichier(c):
    if c.startswith("data/feuilles/"):
        return str(INDEX.parent / c.removeprefix("data/feuilles/"))
    if c.startswith("data/feuilles_v3_ajouts/"):
        return str(AJOUTS.parent / c.removeprefix("data/feuilles_v3_ajouts/"))
    return str(BASE_NUIT / c)


# étiquette d'apprentissage par classe d'origine
VERS = {"saine": 0, "cercosporiose_noire": 1, "black_sigatoka": 1, "fusariose": 2, "cordana": 3, "pestalotiopsis": 3,
        "sigatoka_jaune": 3, "xanthomonas": 3, "autre_maladie": SANS_NOM, "sigatoka": SANS_NOM}
idx = pd.read_csv(INDEX)
idx = idx[idx.retenue.astype(bool) & idx.chemin.notna() & idx.ensemble.eq("entrainement")]
base = pd.DataFrame(dict(chemin="data/feuilles/" + idx.chemin.values, pays=idx.source.values, classe_vraie=idx.classe.values))
bd = nuit[nuit.role.eq("apprentissage")]
bd = pd.DataFrame(dict(chemin=bd.image.values, pays=bd.jeu.values, classe_vraie=bd.classe.values))
L = pd.read_csv(LISTES)                                # liste exacte des photos mesurées le 11/11 (v10b)
mesures = {j: L[L.jeu.eq(j)].reset_index(drop=True) for j in ["validation"] + PAYS}
pays = pd.concat([mesures[j].rename(columns={"jeu": "pays"}) for j in PAYS], ignore_index=True)
# essai 16 : jeux d'entraînement neufs de D-maladies (feuilles-nuit-1112), seulement si une recette les demande
JEUX_NEUFS = sorted({j for R in RECETTES for j in R.get("jeux_en_plus", [])})
neufs = pd.DataFrame(columns=["chemin", "pays", "classe_vraie", "fichier"])
if JEUX_NEUFS:
    LN = sorted(Path("data/raw/nuit_1112/_kaggle/feuilles-nuit-1112" if ESSAI_LOCAL else "/kaggle/input").rglob("liste_entrainement.csv"))[0]
    ln = pd.read_csv(LN)
    ln = ln[ln.jeu.isin(JEUX_NEUFS)]
    racine_n = LN.parent
    if not (racine_n / ln.fichier.iloc[0]).exists():
        trouve = next((Path("/kaggle/input") if not ESSAI_LOCAL else racine_n).rglob(Path(ln.fichier.iloc[0]).name))
        racine_n = trouve.parents[len(Path(ln.fichier.iloc[0]).parts) - 1]
    neufs = pd.DataFrame(dict(chemin="nuit_1112/" + ln.fichier.values, pays=ln.jeu.values,
                              classe_vraie=ln.classe.map({"saine": "saine", "black_sigatoka": "black_sigatoka", "fusarium": "fusariose",
                                                          "autre": "cordana", "inconnue": "sigatoka"}).values,
                              fichier=[str(racine_n / f) for f in ln.fichier]))
    assert all(Path(f).exists() for f in neufs.fichier.iloc[::40]), "photos de feuilles-nuit-1112 introuvables"
    print("jeux neufs", neufs.groupby(["pays", "classe_vraie"]).size().to_dict(), flush=True)
appr = pd.concat([base, bd, pays], ignore_index=True)
appr["fichier"] = [fichier(c) for c in appr.chemin]
appr = pd.concat([appr, neufs], ignore_index=True)
appr["y"] = [VERS[c] for c in appr.classe_vraie]
for j in mesures:
    mesures[j]["fichier"] = [fichier(c) for c in mesures[j].chemin]
if ESSAI_LOCAL:
    appr = appr.groupby(["pays", "classe_vraie"]).head(3).reset_index(drop=True)
    mesures = {j: g.groupby("classe_vraie").head(3).reset_index(drop=True) for j, g in mesures.items()}
else:
    assert len(base) == 16963 and len(mesures["validation"]) == 3001 and len(mesures["tdtu"]) == 1636
    assert len(mesures["psfd"]) == 738 and len(mesures["ethiopie"]) == 1289 and len(bd) == 422
assert not set(appr.chemin) & set(mesures["validation"].chemin), "la validation ne doit jamais être apprise"
print("apprentissage", appr.groupby(["pays", "y"]).size().to_dict(), flush=True)

# 2. Préparation (identique à fieldscan/modules/maladies.py, preparer_convnext) et mise en mémoire
MOY, ECT = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


def preparer(chemin, taille, lecture):
    with Image.open(chemin) as im:
        im.draft("RGB", (lecture, lecture))
        im = ImageOps.exif_transpose(im).convert("RGB")
        petite = ImageOps.fit(im, (taille, taille), method=Image.BILINEAR)
    t = io.BytesIO(); petite.save(t, format="JPEG", quality=95)
    return np.asarray(Image.open(t).convert("RGB"), dtype="uint8")


def en_memoire(fichiers, taille, lecture):
    with ThreadPoolExecutor(8) as ex:   # Pillow relâche le verrou pendant le décodage
        return np.stack(list(ex.map(lambda f: preparer(f, taille, lecture), fichiers)))


t0 = time.time()
TAILLES = sorted({R.get("taille", 224) for R in RECETTES} | {224})
X_APPR_T = {t: en_memoire(appr.fichier, t, max(448, 2 * t)) for t in TAILLES}   # apprentissage en 224 px (comme la v10)
X_APPR = X_APPR_T[224]
X_MES = {j: en_memoire(g.fichier, 384, 896) for j, g in mesures.items()}  # lecture en 384 px, JPEG lu en 896 px (chaîne)
print(f"photos en mémoire : {len(X_APPR)} + {sum(len(x) for x in X_MES.values())} en {time.time() - t0:.0f} s", flush=True)


# 3. Augmentations
class JPEGAleatoire:
    def __init__(self, p=0.5, qualites=(30, 95)):
        self.p, self.qualites = p, qualites
    def __call__(self, image):
        if random.random() >= self.p:
            return image
        t = io.BytesIO(); image.save(t, format="JPEG", quality=random.randint(*self.qualites))
        return Image.open(t).convert("RGB")


class Eclairage:
    """Gamma au hasard et dégradé de lumière d'un bord à l'autre (ombre portée, contre-jour)."""
    def __init__(self, p=0.5):
        self.p = p
    def __call__(self, image):
        if random.random() >= self.p:
            return image
        a = np.asarray(image, dtype="float32") / 255.0
        a = a ** random.uniform(0.6, 1.6)
        h, w = a.shape[:2]
        angle, force = random.uniform(0, 2 * np.pi), random.uniform(0.0, 0.5)
        yy, xx = np.mgrid[0:h, 0:w].astype("float32")
        rampe = ((xx / w - 0.5) * np.cos(angle) + (yy / h - 0.5) * np.sin(angle))
        a = np.clip(a * (1 + force * 2 * rampe)[..., None], 0, 1)
        return Image.fromarray((a * 255).astype("uint8"))


NORMALISATION = T.Normalize(MOY, ECT)
AUG = {
    "base": T.Compose([   # carnet « cinq classes » (recette de la v2), reprise par le protocole v10c
        JPEGAleatoire(), T.RandomResizedCrop(224, scale=(0.4, 1.0), ratio=(0.8, 1.25)),
        T.RandomHorizontalFlip(), T.RandomVerticalFlip(), T.RandomRotation(30),
        T.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.04),
        T.RandomApply([T.GaussianBlur(5, sigma=(0.1, 2.0))], p=0.3),
        T.ToTensor(), NORMALISATION, T.RandomErasing(p=0.5, scale=(0.02, 0.15))]),
    "forte": T.Compose([  # M5 : couleur, éclairage, flou, JPEG, effacement plus forts
        JPEGAleatoire(0.7, (20, 95)), T.RandomResizedCrop(224, scale=(0.25, 1.0), ratio=(0.67, 1.5)),
        T.RandomHorizontalFlip(), T.RandomVerticalFlip(), T.RandomRotation(45),
        T.ColorJitter(brightness=0.5, contrast=0.5, saturation=0.5, hue=0.08), Eclairage(0.5),
        T.RandomApply([T.GaussianBlur(7, sigma=(0.1, 3.0))], p=0.4),
        T.ToTensor(), NORMALISATION, T.RandomErasing(p=0.6, scale=(0.02, 0.25))]),
}


def aug_taille(nom, t):
    """Mêmes augmentations, recadrage à t px."""
    tr = copy.deepcopy(AUG[nom])
    for k, a in enumerate(tr.transforms):
        if isinstance(a, T.RandomResizedCrop):
            tr.transforms[k] = T.RandomResizedCrop(t, scale=a.scale, ratio=a.ratio)
    return tr


class Morceau:
    """Essai 17 : avec la probabilité p, la photo est remplacée par un de ses morceaux (20 à 35 % de la surface), même étiquette."""
    def __init__(self, p):
        self.p = p
    def __call__(self, image):
        if random.random() >= self.p:
            return image
        w, h = image.size
        f = random.uniform(0.45, 0.6)
        cw, ch = int(w * f), int(h * f)
        x0, y0 = random.randint(0, w - cw), random.randint(0, h - ch)
        return image.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.BILINEAR)


class BasseRes:
    """Photo réduite à 100-160 px puis ré-agrandie (photos peu nettes, comme les miniatures éthiopiennes)."""
    def __init__(self, p):
        self.p = p
    def __call__(self, image):
        if random.random() >= self.p:
            return image
        w, h = image.size
        c = random.randint(100, 160)
        return image.resize((c, max(1, int(c * h / w))), Image.BILINEAR).resize((w, h), Image.BILINEAR)


class Feuilles(Dataset):
    def __init__(self, lignes, y, tr, x_appr=None, pays=None):
        self.lignes, self.y, self.tr = np.asarray(lignes), np.asarray(y), tr
        self.x = X_APPR if x_appr is None else x_appr
        self.pays = np.zeros(len(self.lignes), int) if pays is None else np.asarray(pays)
    def __len__(self):
        return len(self.lignes)
    def __getitem__(self, i):
        return self.tr(Image.fromarray(self.x[self.lignes[i]])), int(self.y[i]), int(self.pays[i])


def poids_tirage(df, parts):
    """Poids par photo : part du pays, partagée à égalité entre ses classes, puis entre les photos de la classe."""
    sources = list(df.pays.unique())
    if parts == "egal":
        part = {s: 1 / len(sources) for s in sources}
    else:   # « tanz40 » : Tanzanie 40 %, Pérou 10 %, Mendeley 5 %, le reste à égalité entre les pays reclassés présents
        fixe = {"tanzanie_2021": 0.40, "perou_2026": 0.10, "mendeley_bd": 0.05}
        if parts == "tanz60":
            fixe = {"tanzanie_2021": 0.60, "perou_2026": 0.10, "mendeley_bd": 0.05}
        autres = [s for s in sources if s not in fixe]
        reste = 1 - sum(v for s, v in fixe.items() if s in sources)
        part = {s: fixe[s] for s in sources if s in fixe}
        if autres:
            part.update({s: reste / len(autres) for s in autres})
        else:
            part = {s: v / sum(part.values()) for s, v in part.items()}
    n_classes = df.groupby("pays").y.nunique()
    n = df.groupby(["pays", "y"]).y.transform("size")
    return (df.pays.map(part) / df.pays.map(n_classes) / n).to_numpy(dtype="float64")


# 4. Réseau, perte, EMA
VERROU = threading.Lock()   # lot 1 : fork des DataLoader refusé pendant qu'un autre fil tenait un verrou de fichier


def nouveau(k, appareil):
    with VERROU:
        return _nouveau(k, appareil)


def _nouveau(k, appareil):
    r = timm.create_model("convnext_tiny.dinov3_lvd1689m", pretrained=False, num_classes=4)
    w = torch.load(POIDS[k], map_location="cpu", weights_only=True)
    r.load_state_dict({n: v.float() if v.is_floating_point() else v for n, v in w.items()})
    return r.to(appareil)


def perte(z, y, poids_ratee, lissage, par_photo=False):
    lp = torch.log_softmax(z.float(), 1)
    l_malade = -torch.logsumexp(lp[:, 1:], 1)                     # −log(1 − P(saine))
    nomme = y < SANS_NOM
    yc = torch.where(nomme, y, torch.zeros_like(y))
    ce = -(1 - lissage) * lp.gather(1, yc[:, None])[:, 0] - lissage * lp.mean(1)
    malade_nommee = nomme & (y > 0)
    l = torch.where(nomme, ce + (poids_ratee - 1) * l_malade * malade_nommee, poids_ratee * l_malade)
    return l if par_photo else l.mean()


def cutmix_fonds(x, y, p, g):
    """Colle sur une part p des photos un rectangle (10 à 30 % de la surface) pris dans une photo saine du lot."""
    saines = torch.nonzero(y == 0)[:, 0]
    if p <= 0 or len(saines) == 0:
        return x
    x = x.clone(); n, _, h, w = x.shape
    for i in range(n):
        if torch.rand(1, generator=g).item() >= p:
            continue
        s = saines[torch.randint(len(saines), (1,), generator=g).item()].item()
        if s == i:
            continue
        aire = 0.1 + 0.2 * torch.rand(1, generator=g).item(); ratio = 0.5 + 1.5 * torch.rand(1, generator=g).item()
        hh, ww = min(h, int((aire * h * w * ratio) ** 0.5)), min(w, int((aire * h * w / ratio) ** 0.5))
        y0, x0 = torch.randint(h - hh + 1, (1,), generator=g).item(), torch.randint(w - ww + 1, (1,), generator=g).item()
        y1, x1 = torch.randint(h - hh + 1, (1,), generator=g).item(), torch.randint(w - ww + 1, (1,), generator=g).item()
        x[i, :, y0:y0 + hh, x0:x0 + ww] = x[s, :, y1:y1 + hh, x1:x1 + ww]
    return x


VUES = [lambda x: x, lambda x: x.flip(3), lambda x: x.flip(2), lambda x: x.rot90(1, (2, 3))]


@torch.no_grad()
def lire(reseaux, X, appareil, lot=48):
    """Probabilités (n, 4) : moyenne des 4 vues puis des réseaux, photo déjà préparée en 384 px."""
    moy, ect = torch.tensor(MOY, device=appareil).view(1, 3, 1, 1), torch.tensor(ECT, device=appareil).view(1, 3, 1, 1)
    sorties = []
    for i in range(0, len(X), lot):
        x = torch.from_numpy(X[i:i + lot]).to(appareil).permute(0, 3, 1, 2).float().div(255.0)
        x = ((x - moy) / ect).contiguous()
        with torch.autocast("cuda", dtype=torch.float16, enabled=appareil != "cpu"):
            p = torch.stack([sum(torch.softmax(r(v(x)).float(), 1) for v in VUES) / len(VUES) for r in reseaux]).mean(0)
        sorties.append(p.float().cpu().numpy())
    return np.concatenate(sorties)


def ecrire(P, df, chemin):
    out = df[["chemin", "jeu", "classe_vraie"]].copy()
    for k, c in enumerate(["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]):
        out[c] = P[:, k].round(6)
    out.to_csv(chemin, index=False)


def entrainer(R, df, depart, graine, appareil, etiquette):
    """Un réseau : départ v10b, tirage équilibré, perte pondérée, EMA ; renvoie le réseau EMA de la dernière époque."""
    torch.manual_seed(graine)
    g = torch.Generator().manual_seed(graine)
    m = nouveau(depart, appareil).to(memory_format=torch.channels_last)
    ema = copy.deepcopy(m).eval()
    for p in ema.parameters():
        p.requires_grad_(False)
    tete = [p for n, p in m.named_parameters() if n.startswith("head.fc")]
    corps = [p for n, p in m.named_parameters() if not n.startswith("head.fc")]
    assert len(tete) == 2
    opt = torch.optim.AdamW([dict(params=corps, lr=R["lr_reseau"]), dict(params=tete, lr=R["lr_tete"])], weight_decay=0.05)
    n_epoque = 64 if ESSAI_LOCAL else R["n_epoque"]
    pas_total = R["epoques"] * (n_epoque // R["lot"])
    plan = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(pas_total, 1))
    echelle = torch.amp.GradScaler("cuda", enabled=appareil != "cpu")
    w = poids_tirage(df, R["parts"]).copy()
    if R["sain_source"]:   # moitié saines, moitié malades DANS chaque source : la source ne prédit plus l'étiquette
        s_ = df.y.to_numpy() == 0
        for src in df.pays.unique():
            k_ = (df.pays == src).to_numpy()
            if s_[k_].any() and (~s_[k_]).any():
                tot_ = w[k_].sum()
                w[k_ & s_] *= 0.5 * tot_ / w[k_ & s_].sum()
                w[k_ & ~s_] *= 0.5 * tot_ / w[k_ & ~s_].sum()
    if R["sain50"]:   # la moitié du tirage en feuilles saines (toutes sources confondues), l'autre en malades
        s_ = df.y.to_numpy() == 0
        w = np.where(s_, w * 0.5 / w[s_].sum(), w * 0.5 / w[~s_].sum())
    tirage = WeightedRandomSampler(torch.tensor(w), n_epoque, replacement=True, generator=g)
    y = df.y.to_numpy().copy()
    if R["sans_nom"] == "autre":            # variante : les malades sans nom vont dans la classe « autre »
        y[y == SANS_NOM] = 3
    tr = aug_taille(R["aug"], R["taille"])
    if R["morceaux"] > 0:
        tr.transforms.insert(0, Morceau(R["morceaux"]))
    if R["basse_res"] > 0:
        tr.transforms.insert(0, BasseRes(R["basse_res"]))
    groupes = sorted(df.pays.unique())
    gid = df.pays.map({gname: k for k, gname in enumerate(groupes)}).to_numpy()
    q = torch.ones(len(groupes), device=appareil) / len(groupes)    # essai 15 : poids des groupes (Group-DRO)
    charge = DataLoader(Feuilles(df.index.to_numpy(), y, tr, X_APPR_T[R["taille"]], gid), R["lot"], sampler=tirage,
                        num_workers=0 if ESSAI_LOCAL else 2, persistent_workers=not ESSAI_LOCAL, drop_last=True)
    with VERROU:   # les processus de chargement sont créés ici (fork), un fil à la fois
        iter(charge)
    pas = 0
    for e in range(R["epoques"]):
        if R["deux_temps"]:   # essai 18 : première époque, tête et dernier étage seuls ; ensuite tout le réseau
            for n_, p_ in m.named_parameters():
                p_.requires_grad_(e > 0 or n_.startswith("head") or n_.startswith("stages.3"))
        m.train(); t0, tot, n = time.time(), 0.0, 0
        for x, yb, gb in charge:
            x, yb, gb = x.to(appareil), yb.to(appareil), gb.to(appareil)
            x = cutmix_fonds(x, yb, R["cutmix"], g).contiguous(memory_format=torch.channels_last)
            opt.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.float16, enabled=appareil != "cpu"):
                lp_ = perte(m(x), yb, R["poids_ratee"], R["lissage"], par_photo=True)
            if R["dro"] > 0:
                with torch.no_grad():
                    for k_ in gb.unique():
                        q[k_] *= torch.exp(R["dro"] * lp_[gb == k_].mean())
                    q /= q.sum()
                l = (lp_ * q[gb] * len(groupes)).mean()
            else:
                l = lp_.mean()
            echelle.scale(l).backward()
            echelle.unscale_(opt); torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
            echelle.step(opt); echelle.update(); plan.step(); pas += 1
            d = min(R["ema"], (1 + pas) / (10 + pas))
            with torch.no_grad():
                for pe, pm in zip(ema.parameters(), m.parameters()):
                    pe.mul_(d).add_(pm.detach(), alpha=1 - d)
            tot += l.item() * len(yb); n += len(yb)
        assert np.isfinite(tot), "perte non finie"
        print(f"[{etiquette}] époque {e + 1}/{R['epoques']} perte {tot / max(n, 1):.4f} ({time.time() - t0:.0f} s)", flush=True)
    del charge, opt
    return ema.eval()


def une_recette(R, appareil):
    R = {**DEFAUT, **R}
    nom = R["nom"]
    (SORTIE / f"recette_{nom}.json").write_text(json.dumps(dict(mode=MODE, **R), ensure_ascii=False), encoding="utf-8")
    if R["epoques"] == 0:        # témoin : la v10b telle quelle (réseaux R["reseaux"]), lue par ce carnet
        reseaux = [nouveau(k, appareil).eval() for k in R["reseaux"]]
        for j, g in mesures.items():
            ecrire(lire(reseaux, X_MES[j], appareil), g, SORTIE / f"predictions_{nom}_{j}.csv")
        return
    retires = list(R["pays_hors"]) + [j for j in JEUX_NEUFS if j not in R["jeux_en_plus"]]
    if MODE == "plis":
        premier = None
        for x in PAYS:
            if x in R["pays_hors"]:   # pays jamais appris : lu par le réseau du premier pli
                continue
            df = appr[~appr.pays.isin([x] + retires)]
            assert x not in set(df.pays)
            r = entrainer(R, df, R["depart"], R["graine"], appareil, f"{nom} sans {x}")
            ecrire(lire([r], X_MES[x], appareil), mesures[x], SORTIE / f"predictions_{nom}_{x}.csv")
            if premier is None:
                premier = True
                for h in R["pays_hors"]:
                    ecrire(lire([r], X_MES[h], appareil), mesures[h], SORTIE / f"predictions_{nom}_{h}.csv")
            ecrire(lire([r], X_MES["validation"], appareil), mesures["validation"], SORTIE / f"predictions_{nom}_validation_pli_{x}.csv")
            del r
            print(f"[{nom}] pli sans {x} écrit", flush=True)
    else:                        # final : 3 réseaux sur tout
        df = appr[~appr.pays.isin(retires)]
        reseaux = []
        for k in range(3):
            r = entrainer(R, df, k, k, appareil, f"{nom} final {k}")
            torch.save({n: (t.half() if t.is_floating_point() else t) for n, t in r.state_dict().items()},
                       SORTIE / f"maladies_v12{nom}_{k}.pt")
            reseaux.append(r)
        ecrire(lire(reseaux, X_MES["validation"], appareil), mesures["validation"], SORTIE / f"predictions_{nom}_final_validation.csv")


# 5. Une file de recettes par GPU (un fil d'exécution par GPU)
echecs = []


def file(k):
    appareil = f"cuda:{k}" if GPU else "cpu"
    for R in RECETTES[k::NB_GPU]:
        t0 = time.time()
        try:
            une_recette(R, appareil)
            print(f"recette {R['nom']} finie en {(time.time() - t0) / 60:.1f} min sur {appareil}", flush=True)
        except Exception:
            echecs.append(R["nom"]); traceback.print_exc()
        if GPU:
            torch.cuda.empty_cache()


fils = [threading.Thread(target=file, args=(k,)) for k in range(NB_GPU)]
[f.start() for f in fils]; [f.join() for f in fils]
print("fini ; échecs :", echecs, "| fichiers :", sorted(p.name for p in SORTIE.iterdir()), flush=True)
assert not echecs, echecs
