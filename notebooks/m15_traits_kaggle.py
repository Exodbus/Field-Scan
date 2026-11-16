# Field Scan, journée du 15 novembre 2026, agent M-kaggle (journal docs/journee_2026-11-15/journal_m_kaggle.md, 14 h 15,
# règles écrites avant calcul). Traits pour le lecteur kNN (idée M1 de la veille) : sortie avant la tête des soupes s4
# (sorties du carnet m15-soupe), 768 nombres normalisés L2, une vue, 224 px, pour TOUTES les images d'apprentissage (mémoire,
# filtrée par pli en local) et pour les 6 jeux de mesure. Un jeu de traits par pli (sans TDTU, sans Éthiopie).
# Données et contrôles anti-juges repris de notebooks/m14_entrainer_kaggle.py. Aucun entraînement, aucune décision, aucun score.
import copy, io, json, os, random, subprocess, sys, threading, time, traceback
from pathlib import Path
import numpy as np, pandas as pd, torch
from PIL import Image, ImageOps
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms as T
from torchvision import models as tvm
from concurrent.futures import ThreadPoolExecutor

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
print("m15 traits | GPU", [torch.cuda.get_device_name(i) for i in range(NB_GPU)] if GPU else "processeur", flush=True)
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


X_APPR = en_memoire(appr.fichier, 224, 448)          # mémoire du kNN, 224 px comme l'apprentissage
X_MES = {j: en_memoire(g.fichier, 224, 448) for j, g in mesures.items()}   # requêtes, 224 px aussi
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




# 3. Traits (m15)
def trouver_soupe(x):
    t = sorted(E.rglob(f"maladies_m15s4_sans_{x}.pt"))
    assert len(t) == 1, (x, t)
    return t[0]


def reseau(sd, appareil):
    r = timm.create_model("convnext_tiny.dinov3_lvd1689m", pretrained=False, num_classes=4)
    r.load_state_dict(sd)
    return r.to(appareil).eval().to(memory_format=torch.channels_last)


@torch.no_grad()
def traits(r, X, appareil, lot=128):
    out = []
    for i in range(0, len(X), lot):
        x = normaliser(torch.from_numpy(X[i:i + lot]), appareil)
        with torch.autocast("cuda", dtype=torch.float16, enabled=GPU):
            f = r.forward_head(r.forward_features(x), pre_logits=True).float()
        out.append(torch.nn.functional.normalize(f, dim=1).cpu().numpy().astype("float16"))
    return np.concatenate(out)


echecs = []


def un_pli(k, x):
    appareil = f"cuda:{k}" if GPU else "cpu"
    try:
        w = torch.load(trouver_soupe(x), map_location="cpu", weights_only=True)
        with VERROU:
            r = reseau({n: (v.float() if v.is_floating_point() else v) for n, v in w.items()}, appareil)
        F = {"appr": traits(r, X_APPR, appareil)}
        for j in X_MES:
            F[f"mes_{j}"] = traits(r, X_MES[j], appareil)
        np.savez(SORTIE / f"traits_s4_sans_{x}.npz", **F)
        print(f"[traits] pli sans {x} écrit à {(time.time() - T0) / 60:.1f} min", {n: v.shape for n, v in F.items()}, flush=True)
    except Exception:
        echecs.append(x); traceback.print_exc()


appr[["chemin", "pays", "y"]].to_csv(SORTIE / "appr_meta.csv", index=False)
for j, g in mesures.items():
    g[["chemin", "classe_vraie"]].to_csv(SORTIE / f"chemins_{j}.csv", index=False)
fils = [threading.Thread(target=un_pli, args=(k % NB_GPU, x)) for k, x in enumerate(PLIS)]
[f.start() for f in fils]; [f.join() for f in fils]
print(f"fini en {(time.time() - T0) / 60:.1f} min ; échecs :", echecs, flush=True)
assert not echecs, echecs
