# Field Scan : ConvNeXt-R, recette d'entraînement renforcée (Kaggle, GPU T4, internet activé pour les poids ImageNet).
# Protocole : docs/protocole_maladies_recette.md (écrit et commité avant l'entraînement).
# 4 variantes à un réseau (R0 témoin = recette de la v2 ; R1 = 10 époques + EMA ; R2 = R1 + CutMix ; R3 = R2 + AugMix),
# choix automatique sur TDTU (AUC de P(malade)) avec garde-fou de validation, puis modèle final à 3 réseaux, seuils
# par les règles de la v2 et probabilités sur la validation, BananaLSD et val_loin (aucun score affiché pour ces jeux).
# Sorties : /kaggle/working/recette/. ESSAI_LOCAL=1 : vérification du code sur processeur, sans poids ImageNet.
import io, json, os, random, sys, time
from pathlib import Path
import numpy as np, pandas as pd, torch
from PIL import Image, ImageOps
from scipy.stats import rankdata
from torch.optim.swa_utils import AveragedModel, get_ema_multi_avg_fn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import models, transforms as T

# 1. Réglages (figés par le protocole)
ESSAI_LOCAL = os.environ.get("ESSAI_LOCAL") == "1"
CLASSES = ["saine", "black_sigatoka", "fusarium"]
VARIANTES = {"R0": dict(epoques=6, ema=False, cutmix=False, augmix=False),
             "R1": dict(epoques=10, ema=True, cutmix=False, augmix=False),
             "R2": dict(epoques=10, ema=True, cutmix=True, augmix=False),
             "R3": dict(epoques=10, ema=True, cutmix=True, augmix=True)}
if ESSAI_LOCAL:
    VARIANTES = {k: dict(v, epoques=1) for k, v in VARIANTES.items()}
TAILLE_LOT = 8 if ESSAI_LOCAL else 32
LR, DECROISSANCE, LISSAGE, POIDS_PEROU = 1e-4, 1e-4, 0.1, 3
EMA, P_CUTMIX = 0.999, 0.5
GARDE_COUT, GAIN_MIN = 10, 0.01
COUT_RATEE, OBJECTIF_NOM_JUSTE, ACCEPTATION_VALIDATION = 2, 0.95, 0.95
TAILLE = 224
appareil = "cuda" if torch.cuda.is_available() else "cpu"
MIXTE = appareil == "cuda"
print("Calcul sur :", appareil, torch.cuda.get_device_name(0) if appareil == "cuda" else "", flush=True)
SORTIE = Path("out/maladies/recette_essai_local") if ESSAI_LOCAL else Path("/kaggle/working/recette")
SORTIE.mkdir(parents=True, exist_ok=True)

# 2. Données
if ESSAI_LOCAL:
    INDEX, FEUILLES, AJOUTS = Path("data/feuilles/index.csv"), Path("data/roamer_val_loin_feuilles/feuilles.csv"), Path("data/feuilles_v3_ajouts/images.csv")
else:
    ENTREE = Path("/kaggle/input")
    INDEX, FEUILLES = sorted(ENTREE.rglob("index.csv"))[0], sorted(ENTREE.rglob("feuilles.csv"))[0]
    AJOUTS = sorted(ENTREE.rglob("images_ajouts.csv"))[0]
VERS = {"saine": "saine", "cercosporiose_noire": "black_sigatoka", "fusariose": "fusarium"}
VERS_COMMUN = {"saine": "saine", "black_sigatoka": "cercosporiose_noire", "fusarium": "fusariose",
               "malade_non_identifiee": "malade_non_identifiee", "inconnu": "je_ne_sais_pas"}
idx = pd.read_csv(INDEX)
idx = idx[idx.retenue.astype(bool) & idx.chemin.notna()]


def tableau(s):
    return pd.DataFrame(dict(chemin="data/feuilles/" + s.chemin.values, fichier=[str(INDEX.parent / c) for c in s.chemin],
                             jeu=s.source.values, classe_vraie=s.classe.values))


entrainement = tableau(idx[idx.ensemble.eq("entrainement")])
validation = tableau(idx[idx.ensemble.eq("validation")])
bananalsd = tableau(idx[idx.ensemble.eq("test") & idx.source.eq("bananalsd")])
f = pd.read_csv(FEUILLES)
val_loin = pd.DataFrame(dict(chemin="data/roamer_val_loin_feuilles/" + f.image, fichier=[str(FEUILLES.parent / i) for i in f.image],
                             jeu=f.projet.values, classe_vraie=f.etat.values, photo=f.photo.values, groupe=f.groupe.values))
a = pd.read_csv(AJOUTS)
a = a[a.jeu.eq("tdtu")]
rel = [i.removeprefix("ajouts_v3/") for i in a.image]
tdtu = pd.DataFrame(dict(chemin=["data/feuilles_v3_ajouts/" + r for r in rel], fichier=[str(AJOUTS.parent / r) for r in rel],
                         jeu="tdtu", classe_vraie=a.classe.values))
if ESSAI_LOCAL:
    entrainement = entrainement.groupby(["jeu", "classe_vraie"]).head(2).reset_index(drop=True)
    validation = validation.groupby("classe_vraie").head(4).reset_index(drop=True)
    tdtu = tdtu.groupby("classe_vraie").head(4).reset_index(drop=True)
    bananalsd, val_loin = bananalsd.head(6), val_loin.head(6)
else:
    assert len(entrainement) == 16963 and len(validation) == 3001 and len(bananalsd) == 897 and len(val_loin) == 3014 and len(tdtu) == 1636
print("TDTU", tdtu.classe_vraie.value_counts().to_dict(), flush=True)

# 3. Préparation et augmentations de la v2 (+ AugMix pour R3)
NORMALISATION = T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])


def preparer(chemin):
    with Image.open(chemin) as im:
        im.draft("RGB", (TAILLE * 2, TAILLE * 2))
        im = ImageOps.exif_transpose(im).convert("RGB")
        petite = ImageOps.fit(im, (TAILLE, TAILLE), method=Image.BILINEAR)
    tampon = io.BytesIO()
    petite.save(tampon, format="JPEG", quality=95)
    return Image.open(tampon).convert("RGB")


class JPEGAleatoire:
    def __init__(self, p=0.5, qualites=(30, 95)):
        self.p, self.qualites = p, qualites
    def __call__(self, image):
        if random.random() >= self.p:
            return image
        tampon = io.BytesIO()
        image.save(tampon, format="JPEG", quality=random.randint(*self.qualites))
        return Image.open(tampon).convert("RGB")


def augmentations(augmix):
    etapes = [JPEGAleatoire(), T.RandomResizedCrop(224, scale=(0.4, 1.0), ratio=(0.8, 1.25)),
              T.RandomHorizontalFlip(), T.RandomVerticalFlip(), T.RandomRotation(30),
              T.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.04)]
    if augmix:
        etapes.append(T.AugMix(severity=3))
    etapes += [T.RandomApply([T.GaussianBlur(5, sigma=(0.1, 2.0))], p=0.3), T.ToTensor(), NORMALISATION,
               T.RandomErasing(p=0.5, scale=(0.02, 0.15))]
    return T.Compose(etapes)


aug_evaluation = T.Compose([T.ToTensor(), NORMALISATION])


class Feuilles(Dataset):
    def __init__(self, df, tr, etiquettes=True):
        self.c, self.tr = list(df.fichier), tr
        self.y = [CLASSES.index(VERS[c]) for c in df.classe_vraie] if etiquettes else [0] * len(df)
    def __len__(self):
        return len(self.c)
    def __getitem__(self, i):
        return self.tr(preparer(self.c[i])), self.y[i]


poids = np.where(entrainement.jeu.eq("perou_2026"), POIDS_PEROU, 1.0)
TRAVAILLEURS = 0 if ESSAI_LOCAL else 4
VUES = [lambda x: x, lambda x: x.flip(3), lambda x: x.flip(2), lambda x: x.rot90(1, (2, 3))]


@torch.no_grad()
def probas(reseaux, df, quatre_vues):
    vues = VUES if quatre_vues else VUES[:1]
    for m in reseaux:
        m.eval()
    s = []
    for x, _ in DataLoader(Feuilles(df, aug_evaluation, etiquettes=False), 8 if ESSAI_LOCAL else 64, num_workers=TRAVAILLEURS):
        x = x.to(appareil)
        with torch.autocast("cuda", dtype=torch.float16, enabled=MIXTE):
            p = torch.stack([sum(torch.softmax(m(v(x)).float(), 1) for v in vues) / len(vues) for m in reseaux]).mean(0)
        s.append(p.float().cpu())
    return torch.cat(s).numpy()


V_VAL = np.array([CLASSES.index(VERS[c]) for c in validation.classe_vraie])
SEUILS = np.round(np.arange(0.05, 0.96, 0.05), 2)


def tableau_seuils(p, v):
    malade, pm = v > 0, p[:, 1:].sum(1)
    return pd.DataFrame([dict(seuil=s, cout=COUT_RATEE * int((~(pm >= s) & malade).sum()) + int(((pm >= s) & ~malade).sum()))
                         for s in SEUILS])


def auc(score, positif):
    r = rankdata(score); n1 = int(positif.sum()); n0 = len(score) - n1
    return float((r[positif].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


# 4. Entraînement d'un réseau selon une variante
def entrainer(variante, graine):
    cfg = VARIANTES[variante]
    random.seed(graine); np.random.seed(graine); torch.manual_seed(graine)
    m = models.convnext_tiny(weights=None if ESSAI_LOCAL else models.ConvNeXt_Tiny_Weights.IMAGENET1K_V1)
    m.classifier[2] = torch.nn.Linear(m.classifier[2].in_features, len(CLASSES))
    m = m.to(appareil).to(memory_format=torch.channels_last)
    ema = AveragedModel(m, multi_avg_fn=get_ema_multi_avg_fn(EMA)) if cfg["ema"] else None
    tirage = WeightedRandomSampler(torch.tensor(poids, dtype=torch.double), len(entrainement), replacement=True,
                                   generator=torch.Generator().manual_seed(graine))
    charge = DataLoader(Feuilles(entrainement, augmentations(cfg["augmix"])), TAILLE_LOT, sampler=tirage,
                        num_workers=TRAVAILLEURS, persistent_workers=TRAVAILLEURS > 0, drop_last=True)
    opt = torch.optim.AdamW(m.parameters(), lr=LR, weight_decay=DECROISSANCE)
    plan = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=cfg["epoques"])
    perte = torch.nn.CrossEntropyLoss(label_smoothing=LISSAGE)
    echelle = torch.amp.GradScaler("cuda", enabled=MIXTE)
    for e in range(cfg["epoques"]):
        m.train(); t0, tot, n = time.time(), 0.0, 0
        for x, y in charge:
            x, y = x.to(appareil).contiguous(memory_format=torch.channels_last), y.to(appareil)
            lam, y2 = 1.0, y
            if cfg["cutmix"] and random.random() < P_CUTMIX:   # CutMix : un rectangle d'une autre photo du lot
                lam = np.random.beta(1.0, 1.0); perm = torch.randperm(len(x), device=x.device); y2 = y[perm]
                h, w = x.shape[2:]; rh, rw = int(h * np.sqrt(1 - lam)), int(w * np.sqrt(1 - lam))
                cy, cx = np.random.randint(h), np.random.randint(w)
                y0, y1, x0, x1 = max(cy - rh // 2, 0), min(cy + rh // 2, h), max(cx - rw // 2, 0), min(cx + rw // 2, w)
                x[:, :, y0:y1, x0:x1] = x[perm, :, y0:y1, x0:x1]
                lam = 1 - (y1 - y0) * (x1 - x0) / (h * w)
            opt.zero_grad()
            with torch.autocast("cuda", dtype=torch.float16, enabled=MIXTE):
                s = m(x).float()
                l = lam * perte(s, y) + (1 - lam) * perte(s, y2)
            echelle.scale(l).backward(); echelle.step(opt); echelle.update()
            if ema is not None:
                ema.update_parameters(m)
            tot += l.item() * len(y); n += len(y)
        plan.step()
        assert np.isfinite(tot), "perte non finie : une relance technique permise (protocole, section 5)"
        print(f"{variante} graine {graine} époque {e + 1}/{cfg['epoques']} perte {tot / n:.3f} ({time.time() - t0:.0f} s)", flush=True)
    final = ema.module if ema is not None else m
    return final.eval()


# 5. Les 4 variantes (graine 0) et le choix sur TDTU
malade_tdtu = tdtu.classe_vraie.ne("saine").to_numpy()
choix, reseaux0 = [], {}
for nom in VARIANTES:
    m = entrainer(nom, 0)
    reseaux0[nom] = m
    cout = int(tableau_seuils(probas([m], validation, False), V_VAL).cout.min())
    a_tdtu = auc(1 - probas([m], tdtu, False)[:, 0], malade_tdtu)
    choix.append(dict(variante=nom, auc_tdtu=round(a_tdtu, 4), cout_validation=cout))
    print(f"{nom} : AUC TDTU {a_tdtu:.4f}, coût validation {cout}", flush=True)
choix = pd.DataFrame(choix).set_index("variante")
ref = choix.loc["R0"]
eligibles = choix.drop("R0")
eligibles = eligibles[eligibles.cout_validation <= ref.cout_validation + GARDE_COUT]
retenue = None
if len(eligibles) and eligibles.auc_tdtu.max() >= ref.auc_tdtu + GAIN_MIN:
    retenue = eligibles.auc_tdtu.idxmax()
if ESSAI_LOCAL and retenue is None:
    retenue = "R3"   # essai local seulement : pour parcourir aussi la suite du carnet
choix.to_csv(SORTIE / "choix_variantes.csv")
print("variante retenue :", retenue, flush=True)
if retenue is None:
    (SORTIE / "bilan_choix.json").write_text(json.dumps(dict(retenue=None, raison="aucune variante ne dépasse R0 de 0,01 sur TDTU avec le garde-fou"),
                                                        ensure_ascii=False, indent=1), encoding="utf-8")
    sys.exit(0)

# 6. Modèle final : graines 1 et 2, puis règles de la v2 sur la validation
reseaux = [reseaux0[retenue]] + [entrainer(retenue, g) for g in (1, 2)]
for k, m in enumerate(reseaux, 1):
    torch.save({n: (t.half() if t.is_floating_point() else t) for n, t in m.state_dict().items()}, SORTIE / f"maladies_r_convnext_tiny_{k}.pt")
p_seul, p_moy = probas(reseaux[:1], validation, True), probas(reseaux, validation, True)
cout_seul, cout_moy = int(tableau_seuils(p_seul, V_VAL).cout.min()), int(tableau_seuils(p_moy, V_VAL).cout.min())
if cout_moy > cout_seul:
    reseaux = reseaux[:1]
    for k in (2, 3):
        (SORTIE / f"maladies_r_convnext_tiny_{k}.pt").unlink()
p1, p4 = probas(reseaux, validation, False), probas(reseaux, validation, True)
t1, t4 = tableau_seuils(p1, V_VAL), tableau_seuils(p4, V_VAL)
QUATRE_VUES = bool(t4.cout.min() < t1.cout.min())
pv, tv = (p4, t4) if QUATRE_VUES else (p1, t1)
SEUIL_ALERTE = float(tv.loc[tv.cout.idxmin(), "seuil"])
part = pv[:, 1:].max(1) / np.maximum(pv[:, 1:].sum(1), 1e-9)
maladie, alerte = 1 + pv[:, 1:].argmax(1), (pv[:, 1:].sum(1) >= SEUIL_ALERTE) & (V_VAL > 0)
SEUIL_NOM = 1.0
for s in np.round(np.arange(0.50, 1.0, 0.01), 2):
    nn = alerte & (part >= s)
    if nn.sum() and (maladie[nn] == V_VAL[nn]).mean() >= OBJECTIF_NOM_JUSTE:
        SEUIL_NOM = float(s); break
SEUIL_CONFIANCE = float(np.quantile(pv.max(1), 1 - ACCEPTATION_VALIDATION))
seuils = dict(modele=f"convnext_r_{retenue}_x{len(reseaux)}", classes=CLASSES, quatre_vues=QUATRE_VUES, nb_reseaux=len(reseaux),
              seuil_alerte=SEUIL_ALERTE, seuil_nom=SEUIL_NOM, seuil_confiance=SEUIL_CONFIANCE, variante=retenue,
              note="Seuils réglés sur la validation (3 001) par les règles de la v2 ; docs/protocole_maladies_recette.md")
(SORTIE / "seuils.json").write_text(json.dumps(seuils, ensure_ascii=False, indent=1), encoding="utf-8")


def decider(p):
    pm = p[:, 1:].sum(1); pt = p[:, 1:].max(1) / np.maximum(pm, 1e-9)
    nom = np.array(CLASSES)[1 + p[:, 1:].argmax(1)]
    r = np.where(pm < SEUIL_ALERTE, "saine", np.where(pt >= SEUIL_NOM, nom, "malade_non_identifiee")).astype(object)
    r[p.max(1) < SEUIL_CONFIANCE] = "inconnu"
    return [VERS_COMMUN[x] for x in r]


# 7. Probabilités et réponses, sans score affiché
for nom, df in (("validation", validation), ("bananalsd", bananalsd), ("val_loin_feuilles", val_loin)):
    p = pv if nom == "validation" else probas(reseaux, df, QUATRE_VUES)
    df.drop(columns="fichier").assign(**{f"p_{c}": p[:, i].round(6) for i, c in enumerate(CLASSES)}, reponse=decider(p)).to_csv(
        SORTIE / f"predictions_convnext_r_{nom}.csv", index=False)
(SORTIE / "bilan_choix.json").write_text(json.dumps(dict(retenue=retenue, choix=choix.reset_index().to_dict("records"),
                                                         cout_un_reseau=cout_seul, cout_moyenne=cout_moy,
                                                         versions=dict(torch=torch.__version__, gpu=torch.cuda.get_device_name(0) if MIXTE else "processeur")),
                                                    ensure_ascii=False, indent=1, default=float), encoding="utf-8")
print("->", SORTIE, sorted(p.name for p in SORTIE.iterdir()), flush=True)
