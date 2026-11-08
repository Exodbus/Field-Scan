# %% [markdown]
# # Field Scan : classifieur de maladies v5 (Kaggle, GPU T4)
#
# Protocole : `docs/protocole_maladies_v3_convnext.md` (amendement 1 : ce modèle s'appelle **v5**). Recette de la
# v2 ConvNeXt du binôme, inchangée sauf : **4 classes** (saine, black_sigatoka, fusarium, autre_maladie),
# **ajouts d'entraînement** khadavy et TDTU, autre_maladie tirée pour **10 %** des images de chaque époque.
#
# **Avant de lancer** : Settings → Accelerator → **GPU T4**, Internet **On** (poids ImageNet), et deux jeux dans Input :
# `feuilles_pret_perou` (archive `data/feuilles_pret_perou.zip`) et `feuilles_v3_ajouts` (`data/feuilles_v3_ajouts.zip`).
#
# **Un seul entraînement** (3 réseaux). Aucun test n'est lu ici : ni banana-buddy, ni khadavy comme mesure, ni la
# Cordana du Pérou. Sorties dans `/kaggle/working/v5/` : 3 poids (16 bits), `seuils.json`, `historique.csv`, `journal.json`.

# %%
# 1. Réglages (fixés par le protocole ; rien n'est à changer)
import io, json, os, random, sys, time
from pathlib import Path
import numpy as np, pandas as pd, torch
from PIL import Image, ImageOps

ESSAI_LOCAL = os.environ.get("ESSAI_LOCAL") == "1"   # vérification du code sur processeur, sans poids ImageNet
CLASSES = ["saine", "black_sigatoka", "fusarium", "autre_maladie"]
EPOQUES = 1 if ESSAI_LOCAL else 6
NB_MODELES = 2 if ESSAI_LOCAL else 3
TAILLE_LOT = 8 if ESSAI_LOCAL else 32
TAUX_APPRENTISSAGE = 1e-4
LISSAGE_ETIQUETTES = 0.1
POIDS_PEROU = 3
PART_AUTRE = 0.10
COUT_RATEE = 2
OBJECTIF_NOM_JUSTE = 0.95
ACCEPTATION_VALIDATION = 0.95
GRAINE = 0
TAILLE = 224
appareil = "cuda" if torch.cuda.is_available() else "cpu"
print("Calcul sur :", appareil, torch.cuda.get_device_name(0) if appareil == "cuda" else "")
SORTIE = Path("out/maladies/v5_essai_local") if ESSAI_LOCAL else Path("/kaggle/working/v5")
SORTIE.mkdir(parents=True, exist_ok=True)

# %%
# 2. Données : archive de Corentin (Tanzanie 2021, Pérou, validation Tanzanie 2022-2023, BananaLSD) et ajouts
if ESSAI_LOCAL:
    INDEX, AJOUTS = Path("data/feuilles/index.csv"), Path("data/feuilles_v3_ajouts/images.csv")
else:
    INDEX = sorted(Path("/kaggle/input").rglob("index.csv"))[0]
    AJOUTS = sorted(Path("/kaggle/input").rglob("images_ajouts.csv"))[0]
VERS_V5 = {"saine": "saine", "cercosporiose_noire": "black_sigatoka", "fusariose": "fusarium"}

idx = pd.read_csv(INDEX)
idx = idx[idx.retenue & idx.chemin.notna() & idx.ensemble.isin(["entrainement", "validation"])]   # jamais test ni test_perou
base = pd.DataFrame(dict(chemin=[str(INDEX.parent / c) for c in idx.chemin], classe=idx.classe.map(VERS_V5).values,
                         jeu=idx.source.values, ensemble=idx.ensemble.values))
aj = pd.read_csv(AJOUTS)
ajouts = pd.DataFrame(dict(chemin=[str(AJOUTS.parent / i.removeprefix("ajouts_v3/")) for i in aj.image],
                           classe=aj.classe.values, jeu=aj.jeu.values, ensemble="entrainement"))
images = pd.concat([base, ajouts], ignore_index=True)
assert images.classe.isin(CLASSES).all(), images[~images.classe.isin(CLASSES)].head()
entrainement = images[images.ensemble.eq("entrainement")].reset_index(drop=True)
validation = images[images.ensemble.eq("validation")].reset_index(drop=True)
if ESSAI_LOCAL:   # quelques images par classe et par jeu
    entrainement = entrainement.groupby(["jeu", "classe"]).head(4).reset_index(drop=True)
    validation = validation.groupby("classe").head(6).reset_index(drop=True)
else:
    assert len(entrainement) == 16963 + 2067, len(entrainement)
    assert len(validation) == 3001, len(validation)
for nom, df in (("entraînement", entrainement), ("validation", validation)):
    print(f"{nom:13s} {len(df):6d} images ", df.groupby(["jeu", "classe"]).size().to_dict())

# %%
# 3. Préparation identique à la v2 (classifieur.preparer) puis augmentations de la v2
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms as T

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


aug_entrainement = T.Compose([
    JPEGAleatoire(),
    T.RandomResizedCrop(224, scale=(0.4, 1.0), ratio=(0.8, 1.25)),
    T.RandomHorizontalFlip(), T.RandomVerticalFlip(), T.RandomRotation(30),
    T.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.04),
    T.RandomApply([T.GaussianBlur(5, sigma=(0.1, 2.0))], p=0.3),
    T.ToTensor(), NORMALISATION, T.RandomErasing(p=0.5, scale=(0.02, 0.15)),
])
aug_evaluation = T.Compose([T.ToTensor(), NORMALISATION])


class Feuilles(Dataset):
    def __init__(self, df, transformation):
        self.chemins, self.etiquettes = list(df.chemin), [CLASSES.index(c) for c in df.classe]
        self.transformation = transformation

    def __len__(self):
        return len(self.chemins)

    def __getitem__(self, i):
        return self.transformation(preparer(self.chemins[i])), self.etiquettes[i]


# tirage : Pérou 3 fois plus souvent ; autre_maladie ramenée à PART_AUTRE des tirages ; le reste à sa proportion naturelle
poids = np.where(entrainement.jeu.eq("perou_2026"), POIDS_PEROU, 1.0)
autre = entrainement.classe.eq("autre_maladie").to_numpy()
poids[autre] = PART_AUTRE / (1 - PART_AUTRE) * poids[~autre].sum() / autre.sum()
print(f"Part du Pérou : {poids[entrainement.jeu.eq('perou_2026').to_numpy()].sum() / poids.sum():.1%}   "
      f"part de autre_maladie : {poids[autre].sum() / poids.sum():.1%}")
TRAVAILLEURS = 0 if ESSAI_LOCAL else 4
charge_validation = DataLoader(Feuilles(validation, aug_evaluation), TAILLE_LOT, num_workers=TRAVAILLEURS)

# %%
# 4. Réseau : ConvNeXt-Tiny ImageNet, dernière couche à 4 classes (comme classifieur.charger)
from torchvision import models


def construire():
    m = models.convnext_tiny(weights=None if ESSAI_LOCAL else models.ConvNeXt_Tiny_Weights.IMAGENET1K_V1)
    m.classifier[2] = torch.nn.Linear(m.classifier[2].in_features, len(CLASSES))
    return m.to(appareil)


VUES = [lambda x: x, lambda x: x.flip(3), lambda x: x.flip(2), lambda x: x.rot90(1, (2, 3))]


@torch.no_grad()
def predire(reseaux_, quatre_vues):
    vues = VUES if quatre_vues else VUES[:1]
    sorties, vraies = [], []
    for m in reseaux_:
        m.eval()
    for x, y in charge_validation:
        x = x.to(appareil)
        p = torch.stack([sum(torch.softmax(m(v(x)), 1) for v in vues) / len(vues) for m in reseaux_]).mean(0)
        sorties.append(p.cpu()); vraies.append(y)
    return torch.cat(sorties).numpy(), torch.cat(vraies).numpy()


SEUILS = np.round(np.arange(0.05, 0.96, 0.05), 2)


def tableau_seuils(probas, vraies):
    malade, p_malade = vraies > 0, probas[:, 1:].sum(1)
    lignes = []
    for s in SEUILS:
        dit = p_malade >= s
        ratees, fausses = int((~dit & malade).sum()), int((dit & ~malade).sum())
        lignes.append(dict(seuil=s, malades_ratees=ratees, fausses_alertes=fausses, cout=COUT_RATEE * ratees + fausses))
    return pd.DataFrame(lignes)

# %%
# 5. Entraînement : 3 réseaux (graines 0, 1, 2), dernière époque gardée (règle de la v2)
historique, reseaux = [], []
for k in range(NB_MODELES):
    graine = GRAINE + k
    random.seed(graine); np.random.seed(graine); torch.manual_seed(graine)
    m = construire()
    tirage = WeightedRandomSampler(torch.tensor(poids, dtype=torch.double), num_samples=len(entrainement), replacement=True,
                                   generator=torch.Generator().manual_seed(graine))
    charge = DataLoader(Feuilles(entrainement, aug_entrainement), TAILLE_LOT, sampler=tirage, num_workers=TRAVAILLEURS)
    opt = torch.optim.AdamW(m.parameters(), lr=TAUX_APPRENTISSAGE, weight_decay=1e-4)
    plan = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOQUES)
    perte = torch.nn.CrossEntropyLoss(label_smoothing=LISSAGE_ETIQUETTES)
    print(f"--- réseau {k + 1}/{NB_MODELES} (graine {graine})")
    for epoque in range(1, EPOQUES + 1):
        m.train(); debut, total, n = time.time(), 0.0, 0
        for x, y in charge:
            x, y = x.to(appareil), y.to(appareil)
            opt.zero_grad(); l = perte(m(x), y); l.backward(); opt.step()
            total += l.item() * len(y); n += len(y)
        plan.step()
        assert np.isfinite(total), "perte NaN : relance technique autorisée une fois (protocole, section 6)"
        p, v = predire([m], False)
        cout = int(tableau_seuils(p, v).cout.min())
        historique.append(dict(reseau=k + 1, epoque=epoque, perte=total / n, cout_validation=cout))
        print(f"époque {epoque}  perte {total / n:.3f}  coût validation {cout}  ({time.time() - debut:.0f} s)")
    reseaux.append(m)
pd.DataFrame(historique).to_csv(SORTIE / "historique.csv", index=False)

# %%
# 6. Règles de la v2 sur la validation : moyenne des réseaux ou un seul, 1 ou 4 vues, puis seuil d'alerte
p_seul, v_val = predire(reseaux[:1], True)
p_moy, _ = predire(reseaux, True)
cout_seul, cout_moy = int(tableau_seuils(p_seul, v_val).cout.min()), int(tableau_seuils(p_moy, v_val).cout.min())
if cout_moy > cout_seul:
    reseaux = reseaux[:1]
print(f"coût 4 vues : un réseau {cout_seul}, moyenne {cout_moy} -> {len(reseaux)} réseau(x)")
p1, _ = predire(reseaux, False)
p4, _ = predire(reseaux, True)
t1, t4 = tableau_seuils(p1, v_val), tableau_seuils(p4, v_val)
QUATRE_VUES = bool(t4.cout.min() < t1.cout.min())
probas_val, tableau_val = (p4, t4) if QUATRE_VUES else (p1, t1)
SEUIL_ALERTE = float(tableau_val.loc[tableau_val.cout.idxmin(), "seuil"])
print("4 vues" if QUATRE_VUES else "1 vue", f"; seuil d'alerte {SEUIL_ALERTE:.2f}")
print(tableau_val.to_string(index=False))

# %%
# 7. Seuil de nom (maladie nommée juste au moins 95 % du temps) et seuil de confiance (95 % des photos gardées)
#    autre_maladie, absente de la validation, compte comme un nom faux si elle est la plus probable.
p_malade = probas_val[:, 1:].sum(1)
part = probas_val[:, 1:].max(1) / np.maximum(p_malade, 1e-9)
maladie = 1 + probas_val[:, 1:].argmax(1)
alerte = (p_malade >= SEUIL_ALERTE) & (v_val > 0)
SEUIL_NOM = 1.0
for s in np.round(np.arange(0.50, 1.0, 0.01), 2):
    nommees = alerte & (part >= s)
    if nommees.sum() and (maladie[nommees] == v_val[nommees]).mean() >= OBJECTIF_NOM_JUSTE:
        SEUIL_NOM = float(s); break
SEUIL_CONFIANCE = float(np.quantile(probas_val.max(1), 1 - ACCEPTATION_VALIDATION))
print(f"seuil de nom {SEUIL_NOM:.2f} ; seuil de confiance {SEUIL_CONFIANCE:.4f}")

# %%
# 8. Sauvegarde : poids en 16 bits (comme la v2), seuils, journal
for k, m in enumerate(reseaux, 1):
    torch.save({n: (t.half() if t.is_floating_point() else t) for n, t in m.state_dict().items()},
               SORTIE / f"maladies_v5_convnext_tiny_{k}.pt")
seuils = dict(modele="v5_convnext_tiny_ajouts_khadavy_tdtu_autre10_x3", classes=CLASSES, quatre_vues=QUATRE_VUES,
              nb_reseaux=len(reseaux), seuil_alerte=SEUIL_ALERTE, seuil_nom=SEUIL_NOM, seuil_confiance=SEUIL_CONFIANCE,
              decision="malade si P(black_sigatoka)+P(fusarium)+P(autre_maladie) >= seuil_alerte ; maladie nommée si "
                       "elle n'est pas autre_maladie et fait au moins seuil_nom de P(malade), sinon malade_non_identifiee ; "
                       "inconnu si la plus forte probabilité est sous seuil_confiance",
              note="Seuils réglés sur la validation Tanzanie 2022-2023 (3 001 images), docs/protocole_maladies_v3_convnext.md")
(SORTIE / "seuils.json").write_text(json.dumps(seuils, ensure_ascii=False, indent=1), encoding="utf-8")
journal = dict(versions=dict(torch=torch.__version__, python=sys.version.split()[0],
                             gpu=torch.cuda.get_device_name(0) if appareil == "cuda" else "processeur"),
               effectifs=dict(entrainement={f"{j}/{c}": int(n) for (j, c), n in entrainement.groupby(["jeu", "classe"]).size().items()},
                              validation=len(validation)),
               cout_un_reseau=cout_seul, cout_moyenne=cout_moy, essai_local=ESSAI_LOCAL)
(SORTIE / "journal.json").write_text(json.dumps(journal, ensure_ascii=False, indent=1, default=int), encoding="utf-8")
print("->", SORTIE, sorted(p.name for p in SORTIE.iterdir()))
