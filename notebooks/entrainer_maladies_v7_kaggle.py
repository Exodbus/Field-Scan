# %% [markdown]
# # Field Scan : classifieur de maladies v7 (Kaggle, GPU T4)
#
# Protocole : `docs/protocole_maladies_v7.md` (écrit avant l'entraînement). Carnet repris du brouillon de l'agent
# `amelioration-modele` (justifications : `docs/maladies_equipe/amelioration-modele.md`, section 4), entrées finales ci-dessous.
#
# Base : carnet de la v5 (`notebooks/entrainer_maladies_v5_kaggle.py`), même structure, mêmes 4 classes, mêmes règles de
# seuils. Changements, et seulement ceux-ci :
#   1. **feuilles vues de loin ajoutées** : recadrages des feuilles segmentées ROAMER de Mindanao (polygones « positive »
#      = feuille malade, « negative » = feuille saine), **jamais le test « de loin » ni Laguna**, images communes avec le test
#      exclues ; tirés pour 10 % des images
#      de chaque époque ;
#   2. **augmentations « de loin »** : perte de résolution (réduction puis agrandissement), flou plus fort, et mosaïque
#      2 × 2 (l'image dans une case, trois feuilles saines autour, étiquette inchangée) ;
#   3. **précision mixte** (16 bits) sur le GPU, pour la vitesse ; résultat numérique équivalent à [H] près ;
#   4. probabilités de la validation enregistrées (`probas_validation.csv`) pour la fusion et la calibration.
# Résolution **inchangée (224 px)** : l'archive d'entraînement est déjà ramenée à 256 px de petit côté.
#
# **Avant de lancer** : Accelerator **GPU T4**, Internet **On** (poids ImageNet), trois jeux dans Input :
# `feuilles_pret_perou`, `feuilles_v3_ajouts` et `roamer_recadrages_v7` (dossier `data/roamer_recadrages_v7` préparé par
# `scripts/preparer_recadrages_v7.py` : 1 090 feuilles des images de `dev_loin` seulement, `recadrages.csv` avec les
# colonnes image, classe, jeu, photo, et la liste d'exclusion `exclusions_roamer_val_loin.csv`, obligatoire, qui retire
# toute image de `val_loin`). Aucun zip ROAMER en entrée : le carnet s'arrête s'il trouve un zip interdit.
#
# **Un seul entraînement** (3 réseaux). Aucun test lu : ni banana-buddy, ni le test « de loin » ROAMER, ni Laguna, ni la Cordana du Pérou.
# Sorties dans `/kaggle/working/v7/`.

# %%
# 1. Réglages (figés par docs/protocole_maladies_v7.md)
import io, json, os, random, sys, time, zipfile
from pathlib import Path
import numpy as np, pandas as pd, torch
from PIL import Image, ImageDraw, ImageFilter, ImageOps

ESSAI_LOCAL = os.environ.get("ESSAI_LOCAL") == "1"   # vérification du code sur processeur, sans poids ImageNet
CLASSES = ["saine", "black_sigatoka", "fusarium", "autre_maladie"]
EPOQUES = 1 if ESSAI_LOCAL else 6
NB_MODELES = 2 if ESSAI_LOCAL else 3
TAILLE_LOT = 8 if ESSAI_LOCAL else 32
TAUX_APPRENTISSAGE = 1e-4
LISSAGE_ETIQUETTES = 0.1
POIDS_PEROU = 3
PART_AUTRE = 0.10          # autre_maladie parmi les images hors ROAMER (comme la v5)
PART_ROAMER = 0.10         # nouveau : feuilles vues de loin, part des tirages de chaque époque
P_MOSAIQUE = 0.15          # nouveau : mosaïque 2 x 2 avec trois feuilles saines
P_BASSE_RESOLUTION = 0.30  # nouveau : réduction d'un facteur 0,25 à 0,7 puis retour à 224 px
FACTEURS_RESOLUTION = (0.25, 0.70)
MARGE_RECADRAGE = 0.10     # ROAMER : boîte du polygone élargie de 10 % de chaque côté
COUT_RATEE = 2
OBJECTIF_NOM_JUSTE = 0.95
ACCEPTATION_VALIDATION = 0.95
GRAINE = 0
TAILLE = 224
appareil = "cuda" if torch.cuda.is_available() else "cpu"
MIXTE = appareil == "cuda"
if ESSAI_LOCAL:
    torch.set_num_threads(2)   # processeur partagé avec l'équipe
print("Calcul sur :", appareil, torch.cuda.get_device_name(0) if appareil == "cuda" else "")
SORTIE = Path("out/maladies/v7_essai_local") if ESSAI_LOCAL else Path("/kaggle/working/v7")
SORTIE.mkdir(parents=True, exist_ok=True)

# %%
# 2. Données : archive de Corentin, ajouts khadavy / TDTU, recadrages ROAMER de Mindanao
if ESSAI_LOCAL:
    INDEX, AJOUTS = Path("data/feuilles/index.csv"), Path("data/feuilles_v3_ajouts/images.csv")
    ENTREE = Path(".")
else:
    ENTREE = Path("/kaggle/input")
    INDEX = sorted(ENTREE.rglob("index.csv"))[0]
    AJOUTS = sorted(ENTREE.rglob("images_ajouts.csv"))[0]
VERS_V7 = {"saine": "saine", "cercosporiose_noire": "black_sigatoka", "fusariose": "fusarium"}

idx = pd.read_csv(INDEX)
idx = idx[idx.retenue & idx.chemin.notna() & idx.ensemble.isin(["entrainement", "validation"])]   # jamais test ni test_perou
base = pd.DataFrame(dict(chemin=[str(INDEX.parent / c) for c in idx.chemin], classe=idx.classe.map(VERS_V7).values,
                         jeu=idx.source.values, ensemble=idx.ensemble.values))
aj = pd.read_csv(AJOUTS)
ajouts = pd.DataFrame(dict(chemin=[str(AJOUTS.parent / i.removeprefix("ajouts_v3/")) for i in aj.image],
                           classe=aj.classe.values, jeu=aj.jeu.values, ensemble="entrainement"))

# ROAMER : classe d'une feuille « positive » selon le jeu d'origine (hypothèse : la feuille malade d'un champ fusariose est
# une fusariose ; d'un champ Moko, un flétrissement bactérien, donc autre_maladie) ; « negative » = saine
CLASSE_POSITIVE = {"fusarium": "fusarium", "moko": "autre_maladie"}
# liste blanche : seuls ces zips de Mindanao sont ouverts ; tout autre zip ROAMER est ignoré
# bunchy top écarté : ses 2 247 polygones sont tous « positive » (aucune feuille « negative »), donc l'étiquette désigne
# sans doute la plante et non la feuille ; il dominerait aussi la part ROAMER (51 % des recadrages)
ZIPS_AUTORISES = {"roamer_feuilles_fusarium_leaf.zip": "fusarium", "roamer_feuilles_moko_leaf.zip": "moko"}
# liste interdite : test « de loin » (figé par l'évaluateur) et Laguna (écarté) ; jamais ouverts, jamais en entrée Kaggle
ZIPS_INTERDITS = {"roamer_feuilles_leaf_segmentation.zip", "roamer_feuilles_laguna_leaf_segmentation.zip"}
assert not ZIPS_INTERDITS & set(ZIPS_AUTORISES)
# exclusion des images communes ou quasi identiques au test « de loin » (même robot de Mindanao) : liste publiée par
# l'évaluateur, un CSV dont une colonne nomme l'image (photo, fichier, file_name, image ou nom) ; toutes les feuilles
# d'une image exclue sont retirées. Obligatoire sur Kaggle.
MOTIF_EXCLUSION = "exclusions_roamer*.csv"
EXCLUSION_OBLIGATOIRE = not ESSAI_LOCAL
DOSSIER_RECADRAGES = SORTIE / "roamer_recadrages"


def cle_photo(nom):
    """Clé d'image ROAMER : « color_frame_727ac07d » pour « .../color_frame_727ac07d_png.rf.<hash>.jpg » ou
    « color_frame_727ac07d.png » (nom Roboflow ou nom d'origine)."""
    n = Path(str(nom).replace("\\", "/")).name
    for coupe in ("_png.rf.", "_jpg.rf.", "_jpeg.rf.", ".rf."):
        if coupe in n:
            n = n.split(coupe)[0]
            break
    return n.rsplit(".", 1)[0] if n.lower().endswith((".png", ".jpg", ".jpeg")) else n


def lire_exclusions():
    racine = Path(os.environ.get("EXCLUSIONS_DOSSIER", "data/roamer_recadrages_v7")) if ESSAI_LOCAL else ENTREE
    fichiers = sorted(racine.rglob(MOTIF_EXCLUSION))
    if not fichiers:
        assert not EXCLUSION_OBLIGATOIRE, f"liste d'exclusion ({MOTIF_EXCLUSION}) absente : l'ajouter en entrée"
        print("aucune liste d'exclusion (essai local)")
        return set()
    cles = set()
    for f in fichiers:
        e = pd.read_csv(f)
        col = next((c for c in ("photo", "fichier", "file_name", "image", "nom") if c in e.columns), None)
        assert col is not None, f"{f.name} : aucune colonne de nom d'image"
        cles |= {cle_photo(v) for v in e[col].dropna()}
    print(f"exclusions test « de loin » : {len(cles)} images ({', '.join(f.name for f in fichiers)})")
    return cles


def zips_roamer():
    racine = Path("data/roboflow_maladies/nouveaux") if ESSAI_LOCAL else ENTREE
    trouves = [p for nom in sorted(ZIPS_AUTORISES) for p in sorted(racine.rglob(nom))]
    if not ESSAI_LOCAL:   # sur Kaggle, les zips interdits ne doivent même pas être en entrée
        assert not any(p.name in ZIPS_INTERDITS or "laguna" in p.name.lower() for p in racine.rglob("*.zip")), \
            "zip de test « de loin » présent en entrée : le retirer"
    assert not any(p.name in ZIPS_INTERDITS for p in trouves)
    return trouves


def recadrer_roamer(max_par_zip=None):
    """Recadre chaque polygone annoté (boîte élargie) et l'enregistre en JPEG ; renvoie le tableau des recadrages."""
    DOSSIER_RECADRAGES.mkdir(parents=True, exist_ok=True)
    lignes = []
    for chemin_zip in zips_roamer():
        maladie = ZIPS_AUTORISES[chemin_zip.name]
        with zipfile.ZipFile(chemin_zip) as z:
            for nom_json in sorted(n for n in z.namelist() if n.endswith("_annotations.coco.json")):
                coco = json.loads(z.read(nom_json))
                categories = {c["id"]: c["name"] for c in coco["categories"]}
                fichiers = {im["id"]: im for im in coco["images"]}
                partie = nom_json.split("/")[0]
                annotations = coco["annotations"][:max_par_zip] if max_par_zip else coco["annotations"]
                for a in annotations:
                    etat = categories[a["category_id"]]
                    if etat not in ("positive", "negative"):
                        continue
                    info = fichiers[a["image_id"]]
                    with Image.open(io.BytesIO(z.read(f"{partie}/{info['file_name']}"))) as im:
                        im = im.convert("RGB")
                        x, y, w, h = a["bbox"]
                        mx, my = MARGE_RECADRAGE * w, MARGE_RECADRAGE * h
                        boite = (max(0, x - mx), max(0, y - my), min(im.width, x + w + mx), min(im.height, y + h + my))
                        if boite[2] - boite[0] < 32 or boite[3] - boite[1] < 32:
                            continue
                        sortie = DOSSIER_RECADRAGES / f"{chemin_zip.stem}_{partie}_{a['id']:05d}.jpg"
                        im.crop(boite).save(sortie, quality=95)
                    lignes.append(dict(chemin=str(sortie), classe=CLASSE_POSITIVE[maladie] if etat == "positive" else "saine",
                                       jeu=f"roamer_{maladie}", ensemble="entrainement",
                                       photo=info.get("extra", {}).get("name", info["file_name"])))
    return pd.DataFrame(lignes, columns=["chemin", "classe", "jeu", "ensemble", "photo"])


EXCLUES = lire_exclusions()
preparees = sorted(ENTREE.rglob("recadrages.csv")) if not ESSAI_LOCAL else \
    sorted(Path("data/roamer_recadrages_v7").glob("recadrages.csv"))
if preparees:   # recadrages préparés par vue-de-loin (colonnes image, classe, jeu, photo ; chemins relatifs au csv)
    r = pd.read_csv(preparees[0])
    assert not r.jeu.astype(str).str.contains("laguna|leaf_segmentation", case=False).any(), "test « de loin » dans les recadrages"
    assert "photo" in r.columns or not EXCLUSION_OBLIGATOIRE, "recadrages.csv sans colonne photo : exclusion impossible"
    roamer = pd.DataFrame(dict(chemin=[str(preparees[0].parent / i) for i in r.image], classe=r.classe.values,
                               jeu=r.jeu.values, ensemble="entrainement",
                               photo=r.photo.values if "photo" in r.columns else r.image.values))
    print("recadrages ROAMER lus dans", preparees[0])
else:
    roamer = recadrer_roamer(max_par_zip=6 if ESSAI_LOCAL else None)
    print(f"recadrages ROAMER faits ici : {len(roamer)}")
retirees = roamer.photo.map(cle_photo).isin(EXCLUES)
print(f"recadrages retirés (images communes avec le test « de loin ») : {int(retirees.sum())} sur {len(roamer)}")
roamer = roamer[~retirees].drop(columns="photo").reset_index(drop=True)

images = pd.concat([base, ajouts, roamer], ignore_index=True)
assert images.classe.isin(CLASSES).all(), images[~images.classe.isin(CLASSES)].head()
entrainement = images[images.ensemble.eq("entrainement")].reset_index(drop=True)
validation = images[images.ensemble.eq("validation")].reset_index(drop=True)
if ESSAI_LOCAL:   # quelques images par classe et par jeu
    entrainement = entrainement.groupby(["jeu", "classe"]).head(2).reset_index(drop=True)
    validation = validation.groupby("classe").head(4).reset_index(drop=True)
else:
    assert len(entrainement) - len(roamer) == 16963 + 2067, len(entrainement)
    assert len(validation) == 3001, len(validation)
    assert len(roamer) > 0, "aucun recadrage ROAMER : vérifier les jeux en entrée"
for nom, df in (("entraînement", entrainement), ("validation", validation)):
    print(f"{nom:13s} {len(df):6d} images ", df.groupby(["jeu", "classe"]).size().to_dict())

# %%
# 3. Préparation identique à la v2 (classifieur.preparer), augmentations de la v2 et augmentations « de loin »
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


class BasseResolution:
    """Vue de loin : moins de pixels par lésion. Réduction d'un facteur tiré au hasard, puis retour à la taille."""
    def __init__(self, p, facteurs):
        self.p, self.facteurs = p, facteurs

    def __call__(self, image):
        if random.random() >= self.p:
            return image
        f = random.uniform(*self.facteurs)
        petite = image.resize((max(8, int(image.width * f)), max(8, int(image.height * f))), Image.BILINEAR)
        return petite.resize(image.size, random.choice([Image.BILINEAR, Image.BICUBIC]))


aug_entrainement = T.Compose([
    JPEGAleatoire(),
    T.RandomResizedCrop(224, scale=(0.4, 1.0), ratio=(0.8, 1.25)),
    T.RandomHorizontalFlip(), T.RandomVerticalFlip(), T.RandomRotation(30),
    T.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.04),
    BasseResolution(P_BASSE_RESOLUTION, FACTEURS_RESOLUTION),
    T.RandomApply([T.GaussianBlur(7, sigma=(0.1, 3.0))], p=0.3),   # v2 : noyau 5, sigma 2 au plus
    T.ToTensor(), NORMALISATION, T.RandomErasing(p=0.5, scale=(0.02, 0.15)),
])
aug_evaluation = T.Compose([T.ToTensor(), NORMALISATION])


class Feuilles(Dataset):
    def __init__(self, df, transformation, saines=None, p_mosaique=0.0):
        self.chemins, self.etiquettes = list(df.chemin), [CLASSES.index(c) for c in df.classe]
        self.transformation, self.saines, self.p_mosaique = transformation, saines or [], p_mosaique

    def __len__(self):
        return len(self.chemins)

    def mosaique(self, image):
        """L'image dans une case d'une grille 2 x 2, trois feuilles saines dans les autres ; étiquette inchangée."""
        demi = TAILLE // 2
        toile = Image.new("RGB", (TAILLE, TAILLE))
        case = random.randrange(4)
        for k in range(4):
            source = image if k == case else preparer(random.choice(self.saines))
            toile.paste(source.resize((demi, demi), Image.BILINEAR), ((k % 2) * demi, (k // 2) * demi))
        return toile

    def __getitem__(self, i):
        image = preparer(self.chemins[i])
        if self.saines and random.random() < self.p_mosaique:
            image = self.mosaique(image)
        return self.transformation(image), self.etiquettes[i]


# tirage : ROAMER = PART_ROAMER des tirages ; hors ROAMER, Pérou 3 fois plus souvent et autre_maladie = PART_AUTRE ;
# le reste à sa proportion naturelle
est_roamer = entrainement.jeu.str.startswith("roamer").to_numpy()
poids = np.where(entrainement.jeu.eq("perou_2026"), POIDS_PEROU, 1.0)
autre = entrainement.classe.eq("autre_maladie").to_numpy() & ~est_roamer
reste = ~autre & ~est_roamer
poids[autre] = PART_AUTRE / (1 - PART_AUTRE) * poids[reste].sum() / autre.sum()
if est_roamer.any():
    poids[est_roamer] = PART_ROAMER / (1 - PART_ROAMER) * poids[~est_roamer].sum() / est_roamer.sum()
print(f"Part du Pérou : {poids[entrainement.jeu.eq('perou_2026').to_numpy()].sum() / poids.sum():.1%}   "
      f"autre_maladie (hors ROAMER) : {poids[autre].sum() / poids.sum():.1%}   ROAMER : {poids[est_roamer].sum() / poids.sum():.1%}")
SAINES_MOSAIQUE = list(entrainement.chemin[entrainement.classe.eq("saine") & ~est_roamer])
TRAVAILLEURS = 0 if ESSAI_LOCAL else 4
charge_validation = DataLoader(Feuilles(validation, aug_evaluation), TAILLE_LOT, num_workers=TRAVAILLEURS)

# %%
# 4. Réseau : ConvNeXt-Tiny ImageNet, dernière couche à 4 classes (comme la v5)
from torchvision import models


def construire():
    m = models.convnext_tiny(weights=None if ESSAI_LOCAL else models.ConvNeXt_Tiny_Weights.IMAGENET1K_V1)
    m.classifier[2] = torch.nn.Linear(m.classifier[2].in_features, len(CLASSES))
    return m.to(appareil).to(memory_format=torch.channels_last)


VUES = [lambda x: x, lambda x: x.flip(3), lambda x: x.flip(2), lambda x: x.rot90(1, (2, 3))]


@torch.no_grad()
def predire(reseaux_, quatre_vues):
    vues = VUES if quatre_vues else VUES[:1]
    sorties, vraies = [], []
    for m in reseaux_:
        m.eval()
    for x, y in charge_validation:
        x = x.to(appareil).contiguous(memory_format=torch.channels_last)
        with torch.autocast("cuda", dtype=torch.float16, enabled=MIXTE):
            p = torch.stack([sum(torch.softmax(m(v(x)).float(), 1) for v in vues) / len(vues) for m in reseaux_]).mean(0)
        sorties.append(p.float().cpu()); vraies.append(y)
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
    charge = DataLoader(Feuilles(entrainement, aug_entrainement, SAINES_MOSAIQUE, P_MOSAIQUE), TAILLE_LOT, sampler=tirage,
                        num_workers=TRAVAILLEURS, persistent_workers=TRAVAILLEURS > 0)
    opt = torch.optim.AdamW(m.parameters(), lr=TAUX_APPRENTISSAGE, weight_decay=1e-4)
    plan = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOQUES)
    perte = torch.nn.CrossEntropyLoss(label_smoothing=LISSAGE_ETIQUETTES)
    echelle = torch.amp.GradScaler("cuda", enabled=MIXTE)
    print(f"--- réseau {k + 1}/{NB_MODELES} (graine {graine})")
    for epoque in range(1, EPOQUES + 1):
        m.train(); debut, total, n = time.time(), 0.0, 0
        for x, y in charge:
            x, y = x.to(appareil).contiguous(memory_format=torch.channels_last), y.to(appareil)
            opt.zero_grad()
            with torch.autocast("cuda", dtype=torch.float16, enabled=MIXTE):
                l = perte(m(x).float(), y)
            echelle.scale(l).backward(); echelle.step(opt); echelle.update()
            total += l.item() * len(y); n += len(y)
        plan.step()
        assert np.isfinite(total), "perte NaN : relance technique autorisée une fois"
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
# 8. Sauvegarde : poids en 16 bits (comme la v2), seuils, probabilités de validation, journal
for k, m in enumerate(reseaux, 1):
    torch.save({n: (t.half() if t.is_floating_point() else t) for n, t in m.state_dict().items()},
               SORTIE / f"maladies_v7_convnext_tiny_{k}.pt")
pd.DataFrame(probas_val, columns=[f"p_{c}" for c in CLASSES]).assign(
    chemin=[Path(c).name for c in validation.chemin], classe_vraie=validation.classe.values
).to_csv(SORTIE / "probas_validation.csv", index=False)
seuils = dict(modele="v7_convnext_tiny_v5_plus_roamer10_aug_loin_x3", classes=CLASSES, quatre_vues=QUATRE_VUES,
              nb_reseaux=len(reseaux), seuil_alerte=SEUIL_ALERTE, seuil_nom=SEUIL_NOM, seuil_confiance=SEUIL_CONFIANCE,
              decision="malade si P(black_sigatoka)+P(fusarium)+P(autre_maladie) >= seuil_alerte ; maladie nommée si "
                       "elle n'est pas autre_maladie et fait au moins seuil_nom de P(malade), sinon malade_non_identifiee ; "
                       "inconnu si la plus forte probabilité est sous seuil_confiance",
              note="Seuils réglés sur la validation Tanzanie 2022-2023 (3 001 images) ; brouillon amelioration-modele")
(SORTIE / "seuils.json").write_text(json.dumps(seuils, ensure_ascii=False, indent=1), encoding="utf-8")
journal = dict(versions=dict(torch=torch.__version__, python=sys.version.split()[0],
                             gpu=torch.cuda.get_device_name(0) if appareil == "cuda" else "processeur"),
               effectifs=dict(entrainement={f"{j}/{c}": int(n) for (j, c), n in entrainement.groupby(["jeu", "classe"]).size().items()},
                              validation=len(validation)),
               reglages=dict(PART_AUTRE=PART_AUTRE, PART_ROAMER=PART_ROAMER, P_MOSAIQUE=P_MOSAIQUE,
                             P_BASSE_RESOLUTION=P_BASSE_RESOLUTION, FACTEURS_RESOLUTION=FACTEURS_RESOLUTION, MIXTE=MIXTE),
               cout_un_reseau=cout_seul, cout_moyenne=cout_moy, essai_local=ESSAI_LOCAL)
(SORTIE / "journal.json").write_text(json.dumps(journal, ensure_ascii=False, indent=1, default=int), encoding="utf-8")
print("->", SORTIE, sorted(p.name for p in SORTIE.iterdir()))
