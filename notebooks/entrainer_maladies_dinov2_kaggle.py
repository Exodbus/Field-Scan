# Field Scan : DINOv2-FT, fine-tuning de DINOv2 ViT-B/14 avec la recette de la v2 (Kaggle, GPU T4, internet activé).
# Protocole : docs/protocole_maladies_dinov2_ft.md (écrit et commité avant l'entraînement).
# Données de la v2 (Tanzanie 2021 + Pérou x 3, 3 classes) ; augmentations de la v2 ; LP-FT (1 époque tête seule, puis
# 6 époques tout le réseau) ; 3 réseaux ; dernière époque gardée ; seuils par les règles de la v2 sur la validation.
# Écrit les probabilités et réponses sur la validation, BananaLSD et les feuilles de val_loin, sans afficher de score.
# Sorties dans /kaggle/working/dinov2_ft/. ESSAI_LOCAL=1 : vérification du code sur processeur avec un faux réseau.
import io, json, os, random, sys, time
from pathlib import Path
import numpy as np, pandas as pd, torch
from PIL import Image, ImageOps
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms as T

# 1. Réglages (figés par le protocole)
ESSAI_LOCAL = os.environ.get("ESSAI_LOCAL") == "1"
CLASSES = ["saine", "black_sigatoka", "fusarium"]
EPOQUES_TETE, EPOQUES = (1, 1) if ESSAI_LOCAL else (1, 6)
NB_MODELES = 2 if ESSAI_LOCAL else 3
TAILLE_LOT = 8 if ESSAI_LOCAL else 32
LR_TETE_SEULE, LR_RESEAU, LR_TETE = 1e-3, 1e-5, 1e-4
DECROISSANCE = 0.05
LISSAGE_ETIQUETTES = 0.1
POIDS_PEROU = 3
COUT_RATEE, OBJECTIF_NOM_JUSTE, ACCEPTATION_VALIDATION = 2, 0.95, 0.95
GRAINE, TAILLE = 0, 224
appareil = "cuda" if torch.cuda.is_available() else "cpu"
MIXTE = appareil == "cuda"
print("Calcul sur :", appareil, torch.cuda.get_device_name(0) if appareil == "cuda" else "", flush=True)
SORTIE = Path("out/maladies/dinov2_ft_essai_local") if ESSAI_LOCAL else Path("/kaggle/working/dinov2_ft")
SORTIE.mkdir(parents=True, exist_ok=True)

# 2. Données
if ESSAI_LOCAL:
    INDEX, FEUILLES = Path("data/feuilles/index.csv"), Path("data/roamer_val_loin_feuilles/feuilles.csv")
else:
    ENTREE = Path("/kaggle/input")
    INDEX = sorted(ENTREE.rglob("index.csv"))[0]
    FEUILLES = sorted(ENTREE.rglob("feuilles.csv"))[0]
VERS = {"saine": "saine", "cercosporiose_noire": "black_sigatoka", "fusariose": "fusarium"}
VERS_COMMUN = {"saine": "saine", "black_sigatoka": "cercosporiose_noire", "fusarium": "fusariose",
               "malade_non_identifiee": "malade_non_identifiee", "inconnu": "je_ne_sais_pas"}
idx = pd.read_csv(INDEX)
idx = idx[idx.retenue.astype(bool) & idx.chemin.notna()]


def tableau(s, avec_classe=True):
    return pd.DataFrame(dict(chemin="data/feuilles/" + s.chemin.values, fichier=[str(INDEX.parent / c) for c in s.chemin],
                             jeu=s.source.values, classe_vraie=s.classe.values))


entrainement = tableau(idx[idx.ensemble.eq("entrainement")])
validation = tableau(idx[idx.ensemble.eq("validation")])
bananalsd = tableau(idx[idx.ensemble.eq("test") & idx.source.eq("bananalsd")])
f = pd.read_csv(FEUILLES)
val_loin = pd.DataFrame(dict(chemin="data/roamer_val_loin_feuilles/" + f.image, fichier=[str(FEUILLES.parent / i) for i in f.image],
                             jeu=f.projet.values, classe_vraie=f.etat.values, photo=f.photo.values, groupe=f.groupe.values))
if ESSAI_LOCAL:
    entrainement = entrainement.groupby(["jeu", "classe_vraie"]).head(2).reset_index(drop=True)
    validation = validation.groupby("classe_vraie").head(4).reset_index(drop=True)
    bananalsd, val_loin = bananalsd.head(6), val_loin.head(6)
else:
    assert len(entrainement) == 16963 and len(validation) == 3001 and len(bananalsd) == 897 and len(val_loin) == 3014
print("entraînement", entrainement.groupby(["jeu", "classe_vraie"]).size().to_dict(), "validation", len(validation), flush=True)

# 3. Préparation et augmentations de la v2
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
    JPEGAleatoire(), T.RandomResizedCrop(224, scale=(0.4, 1.0), ratio=(0.8, 1.25)),
    T.RandomHorizontalFlip(), T.RandomVerticalFlip(), T.RandomRotation(30),
    T.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.04),
    T.RandomApply([T.GaussianBlur(5, sigma=(0.1, 2.0))], p=0.3),
    T.ToTensor(), NORMALISATION, T.RandomErasing(p=0.5, scale=(0.02, 0.15))])
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


# 4. Réseau : DINOv2 ViT-B/14 + tête linéaire sur [jeton de classe, moyenne des jetons d'image]
class FauxDino(torch.nn.Module):   # essai local seulement : même interface, aucun poids téléchargé
    def __init__(self):
        super().__init__()
        self.c = torch.nn.Conv2d(3, 768, 14, 14)
    def forward_features(self, x):
        t = self.c(x).flatten(2).transpose(1, 2)
        return {"x_norm_clstoken": t.mean(1), "x_norm_patchtokens": t}


class Modele(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.dino = FauxDino() if ESSAI_LOCAL else torch.hub.load("facebookresearch/dinov2", "dinov2_vitb14", trust_repo=True)
        self.tete = torch.nn.Linear(1536, len(CLASSES))
    def forward(self, x):
        f = self.dino.forward_features(x)
        return self.tete(torch.cat([f["x_norm_clstoken"], f["x_norm_patchtokens"].mean(1)], 1))


VUES = [lambda x: x, lambda x: x.flip(3), lambda x: x.flip(2), lambda x: x.rot90(1, (2, 3))]


@torch.no_grad()
def probas(reseaux, df, quatre_vues):
    vues = VUES if quatre_vues else VUES[:1]
    for m in reseaux:
        m.eval()
    s = []
    for x, _ in DataLoader(Feuilles(df, aug_evaluation, etiquettes=False), 64 if not ESSAI_LOCAL else 8, num_workers=TRAVAILLEURS):
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


def epoque(m, opt, plan, echelle, perte, charge):
    m.train(); t0, tot, n = time.time(), 0.0, 0
    for x, y in charge:
        x, y = x.to(appareil), y.to(appareil)
        opt.zero_grad()
        with torch.autocast("cuda", dtype=torch.float16, enabled=MIXTE):
            l = perte(m(x).float(), y)
        echelle.scale(l).backward()
        echelle.unscale_(opt); torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        echelle.step(opt); echelle.update()
        tot += l.item() * len(y); n += len(y)
    if plan is not None:
        plan.step()
    assert np.isfinite(tot), "perte non finie : une relance technique permise (protocole, section 2)"
    return tot / n, time.time() - t0


# 5. Entraînement : 3 réseaux, LP puis FT, dernière époque gardée
historique, reseaux = [], []
for k in range(NB_MODELES):
    g = GRAINE + k
    random.seed(g); np.random.seed(g); torch.manual_seed(g)
    m = Modele().to(appareil)
    tirage = WeightedRandomSampler(torch.tensor(poids, dtype=torch.double), len(entrainement), replacement=True,
                                   generator=torch.Generator().manual_seed(g))
    charge = DataLoader(Feuilles(entrainement, aug_entrainement), TAILLE_LOT, sampler=tirage, num_workers=TRAVAILLEURS,
                        persistent_workers=TRAVAILLEURS > 0, drop_last=True)
    perte = torch.nn.CrossEntropyLoss(label_smoothing=LISSAGE_ETIQUETTES)
    echelle = torch.amp.GradScaler("cuda", enabled=MIXTE)
    for p in m.dino.parameters():   # LP : réseau figé, tête seule
        p.requires_grad_(False)
    opt = torch.optim.AdamW(m.tete.parameters(), lr=LR_TETE_SEULE, weight_decay=DECROISSANCE)
    for e in range(EPOQUES_TETE):
        l, d = epoque(m, opt, None, echelle, perte, charge)
        c = int(tableau_seuils(probas([m], validation, False), V_VAL).cout.min())
        historique.append(dict(reseau=k + 1, phase="tete", epoque=e + 1, perte=l, cout_validation=c))
        print(f"réseau {k + 1} tête seule époque {e + 1} perte {l:.3f} ({d:.0f} s)", flush=True)
    for p in m.dino.parameters():   # FT : tout le réseau
        p.requires_grad_(True)
    opt = torch.optim.AdamW([dict(params=m.dino.parameters(), lr=LR_RESEAU), dict(params=m.tete.parameters(), lr=LR_TETE)],
                            weight_decay=DECROISSANCE)
    plan = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOQUES)
    for e in range(EPOQUES):
        l, d = epoque(m, opt, plan, echelle, perte, charge)
        c = int(tableau_seuils(probas([m], validation, False), V_VAL).cout.min())
        historique.append(dict(reseau=k + 1, phase="reseau", epoque=e + 1, perte=l, cout_validation=c))
        print(f"réseau {k + 1} tout le réseau époque {e + 1} perte {l:.3f} ({d:.0f} s)", flush=True)
    m.eval(); reseaux.append(m)
    torch.save({n: (t.half() if t.is_floating_point() else t) for n, t in m.state_dict().items()}, SORTIE / f"maladies_dinov2_ft_{k + 1}.pt")
pd.DataFrame(historique).to_csv(SORTIE / "historique.csv", index=False)

# 6. Règles de la v2 sur la validation : moyenne des réseaux ou un seul, 1 ou 4 vues, puis seuils
p_seul, p_moy = probas(reseaux[:1], validation, True), probas(reseaux, validation, True)
cout_seul, cout_moy = int(tableau_seuils(p_seul, V_VAL).cout.min()), int(tableau_seuils(p_moy, V_VAL).cout.min())
if cout_moy > cout_seul:
    reseaux = reseaux[:1]
p1, p4 = probas(reseaux, validation, False), probas(reseaux, validation, True)
t1, t4 = tableau_seuils(p1, V_VAL), tableau_seuils(p4, V_VAL)
QUATRE_VUES = bool(t4.cout.min() < t1.cout.min())
pv, tv = (p4, t4) if QUATRE_VUES else (p1, t1)
SEUIL_ALERTE = float(tv.loc[tv.cout.idxmin(), "seuil"])
pm, part = pv[:, 1:].sum(1), pv[:, 1:].max(1) / np.maximum(pv[:, 1:].sum(1), 1e-9)
maladie, alerte = 1 + pv[:, 1:].argmax(1), (pv[:, 1:].sum(1) >= SEUIL_ALERTE) & (V_VAL > 0)
SEUIL_NOM = 1.0
for s in np.round(np.arange(0.50, 1.0, 0.01), 2):
    nn = alerte & (part >= s)
    if nn.sum() and (maladie[nn] == V_VAL[nn]).mean() >= OBJECTIF_NOM_JUSTE:
        SEUIL_NOM = float(s); break
SEUIL_CONFIANCE = float(np.quantile(pv.max(1), 1 - ACCEPTATION_VALIDATION))
seuils = dict(modele="dinov2_ft_vitb14_recette_v2", classes=CLASSES, quatre_vues=QUATRE_VUES, nb_reseaux=len(reseaux),
              seuil_alerte=SEUIL_ALERTE, seuil_nom=SEUIL_NOM, seuil_confiance=SEUIL_CONFIANCE,
              note="Seuils réglés sur la validation (3 001) par les règles de la v2 ; docs/protocole_maladies_dinov2_ft.md")
(SORTIE / "seuils.json").write_text(json.dumps(seuils, ensure_ascii=False, indent=1), encoding="utf-8")


def decider(p):
    pm = p[:, 1:].sum(1); part = p[:, 1:].max(1) / np.maximum(pm, 1e-9)
    nom = np.array(CLASSES)[1 + p[:, 1:].argmax(1)]
    r = np.where(pm < SEUIL_ALERTE, "saine", np.where(part >= SEUIL_NOM, nom, "malade_non_identifiee")).astype(object)
    r[p.max(1) < SEUIL_CONFIANCE] = "inconnu"
    return [VERS_COMMUN[x] for x in r]


# 7. Probabilités et réponses, sans score affiché
for nom, df in (("validation", validation), ("bananalsd", bananalsd), ("val_loin_feuilles", val_loin)):
    p = pv if nom == "validation" else probas(reseaux, df, QUATRE_VUES)
    df.drop(columns="fichier").assign(**{f"p_{c}": p[:, i].round(6) for i, c in enumerate(CLASSES)}, reponse=decider(p)).to_csv(
        SORTIE / f"predictions_dinov2_ft_{nom}.csv", index=False)
journal = dict(versions=dict(torch=torch.__version__, python=sys.version.split()[0],
                             gpu=torch.cuda.get_device_name(0) if appareil == "cuda" else "processeur"),
               effectifs=dict(entrainement=len(entrainement), validation=len(validation)),
               cout_un_reseau=cout_seul, cout_moyenne=cout_moy, essai_local=ESSAI_LOCAL)
(SORTIE / "journal.json").write_text(json.dumps(journal, ensure_ascii=False, indent=1, default=int), encoding="utf-8")
print("->", SORTIE, sorted(p.name for p in SORTIE.iterdir()), flush=True)
