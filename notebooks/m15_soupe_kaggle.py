# Field Scan, journée du 15 novembre 2026, agent M-kaggle (plan docs/plan_journee_2026-11-15.md ; journal
# docs/journee_2026-11-15/journal_m_kaggle.md, règles écrites à 14 h 00 avant tout calcul).
# Soupe de poids des 4 tirages de la recette d3b (graines 0 à 3), un réseau par pli (sans TDTU, sans Éthiopie) : moyenne
# uniforme des poids des 4 réseaux du pli (tous partis du réseau 0 de la v10b). AUCUN entraînement, aucun réglage.
# Lecture : pays tenu à l'écart + jeux jamais appris (validation Tanzanie, PSFD, AgroVisionBD, roamer_dev_loin), 384 px, 4 vues.
# Chargement des données et contrôles anti-juges repris tels quels de notebooks/m14_entrainer_kaggle.py (copie de m13) ;
# les images d'apprentissage ne sont PAS chargées (seules les listes servent aux contrôles).
# Le carnet n'écrit que des probabilités et les 2 soupes : aucune décision, aucun score. Aucun juge n'est lu.
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
print("m15 soupe | GPU", [torch.cuda.get_device_name(i) for i in range(NB_GPU)] if GPU else "processeur", flush=True)
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


X_MES = {j: en_memoire(g.fichier, 384, 896) for j, g in mesures.items()}
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



# 3. Soupes (m15)
import hashlib
GRAINES = ["d3b", "d3g1", "d3g2", "d3g3"]


def trouver(n, x):
    t = sorted(p for p in E.rglob(f"maladies_m13{n}_sans_{x}.pt"))
    assert len(t) == 1, (n, x, t)
    return t[0]


def faire_soupe(x):
    somme = None
    for n in GRAINES:
        p = trouver(n, x)
        print(f"[soupe sans {x}] {n} : {p} sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}", flush=True)
        w = torch.load(p, map_location="cpu", weights_only=True)
        w = {k: (v.float() if v.is_floating_point() else v) for k, v in w.items()}
        if somme is None:
            somme = w
            continue
        assert somme.keys() == w.keys()
        for k in somme:
            if somme[k].is_floating_point():
                somme[k] = somme[k] + w[k]
            else:
                assert torch.equal(somme[k], w[k]), k
    return {k: (v / len(GRAINES) if v.is_floating_point() else v) for k, v in somme.items()}


def reseau(sd, appareil):
    r = timm.create_model("convnext_tiny.dinov3_lvd1689m", pretrained=False, num_classes=4)
    r.load_state_dict(sd)
    return r.to(appareil).eval().to(memory_format=torch.channels_last)


def lire(r, X, appareil, lot=48):
    return np.concatenate([proba([r], normaliser(torch.from_numpy(X[i:i + lot]), appareil)).cpu().numpy() for i in range(0, len(X), lot)])


def ecrire(P, df, chemin):
    out = df[["chemin", "jeu", "classe_vraie"]].copy()
    for k, c in enumerate(["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]): out[c] = P[:, k].round(6)
    out.to_csv(chemin, index=False)


COMMUNS = ["validation", "psfd", "agrovision", "roamer_dev_loin"]   # jamais appris : lus par chaque pli
echecs = []


def un_pli(k, x):
    appareil = f"cuda:{k}" if GPU else "cpu"
    try:
        sd = faire_soupe(x)
        torch.save({n: (t.half() if t.is_floating_point() else t) for n, t in sd.items()}, SORTIE / f"maladies_m15s4_sans_{x}.pt")
        with VERROU:
            r = reseau(sd, appareil)
        ecrire(lire(r, X_MES[x], appareil), mesures[x], SORTIE / f"predictions_s4_{x}.csv")
        for j in COMMUNS:
            ecrire(lire(r, X_MES[j], appareil), mesures[j], SORTIE / f"predictions_s4_{j}_pli_{x}.csv")
        print(f"[s4] pli sans {x} écrit à {(time.time() - T0) / 60:.1f} min", flush=True)
        if x == "tdtu":   # contrôle : d3b (graine 0) relu sur la validation, à comparer aux probabilités de lot2p
            w = torch.load(trouver("d3b", "tdtu"), map_location="cpu", weights_only=True)
            with VERROU:
                r0 = reseau({n: (v.float() if v.is_floating_point() else v) for n, v in w.items()}, appareil)
            ecrire(lire(r0, X_MES["validation"], appareil), mesures["validation"], SORTIE / "controle_d3b_validation_pli_tdtu.csv")
            print("[contrôle] d3b relu", flush=True)
    except Exception:
        echecs.append(x); traceback.print_exc()


fils = [threading.Thread(target=un_pli, args=(k % NB_GPU, x)) for k, x in enumerate(PLIS)]
[f.start() for f in fils]; [f.join() for f in fils]
print(f"fini en {(time.time() - T0) / 60:.1f} min ; échecs :", echecs, flush=True)
assert not echecs, echecs
