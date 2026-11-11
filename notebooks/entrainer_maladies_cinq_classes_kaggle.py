# Field Scan : modèles à 5 classes (saine, Sigatoka noire, fusariose, Cordana, Pestalotiopsis), Kaggle GPU, internet activé.
# Protocole : docs/protocole_maladies_cinq_classes.md (écrit avant l'entraînement ; empreinte dans le journal de la nuit).
# RESEAU = "convnext" (C5, recette de la v2), "dinov2" (D5, recette de DINOv2-FT) ou "dinov3" (E5, recette de DINOv2-FT).
# Données de la v2 + jeu Mendeley wfzpdmc5vx filtré (x 5) ; 3 réseaux ; dernière époque ; seuils par les règles de la v2.
# Écrit les probabilités sur la validation, BananaLSD, TDTU, PSFD et l'Éthiopie, sans afficher de score.
# ESSAI_LOCAL=1 : vérification du code sur processeur, faux réseaux, quelques images.
import copy, io, json, os, random, subprocess, sys, time
from pathlib import Path
import numpy as np, pandas as pd, torch
from PIL import Image, ImageOps
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import models, transforms as T

RESEAU = os.environ.get("RESEAU", "dinov2")   # remplacé en dur dans la copie envoyée à Kaggle
ESSAI_LOCAL = os.environ.get("ESSAI_LOCAL") == "1"
NOM = {"convnext": "c5", "dinov2": "d5", "dinov3": "e5", "dinov2l": "l5"}[RESEAU]
CLASSES = ["saine", "black_sigatoka", "fusarium", "cordana", "pestalotiopsis"]
VIT = RESEAU in ("dinov2", "dinov3", "dinov2l")
EPOQUES_TETE, EPOQUES = ((1, 1) if ESSAI_LOCAL else (1, 6)) if VIT else ((0, 1) if ESSAI_LOCAL else (0, 6))
NB_MODELES = 2 if (ESSAI_LOCAL or RESEAU == "dinov2l") else 3   # L5 : 2 réseaux (amendement 1)
TAILLE_LOT = 8 if ESSAI_LOCAL else 32
LISSAGE, POIDS_PEROU, POIDS_BD = 0.1, 3, 5
COUT_RATEE, OBJECTIF_NOM_JUSTE, ACCEPTATION_VALIDATION = 2, 0.95, 0.95
TAILLE = 224
appareil = "cuda" if torch.cuda.is_available() else "cpu"
MIXTE = appareil == "cuda"
print("Réseau :", RESEAU, "| calcul sur :", appareil, torch.cuda.get_device_name(0) if MIXTE else "", flush=True)
SORTIE = Path(f"out/maladies/cinq_classes_essai_local/{NOM}") if ESSAI_LOCAL else Path(f"/kaggle/working/{NOM}")
SORTIE.mkdir(parents=True, exist_ok=True)
if RESEAU == "dinov3" and not ESSAI_LOCAL:   # DINOv3 demande un timm récent
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "timm>=1.0.20"], check=True)

# 1. Données
if ESSAI_LOCAL:
    INDEX, AJOUTS, NUIT = Path("data/feuilles/index.csv"), Path("data/feuilles_v3_ajouts/images.csv"), Path("out/maladies/maladies_nuit/nuit.csv")
else:
    ENTREE = Path("/kaggle/input")
    INDEX = sorted(ENTREE.rglob("index.csv"))[0]
    AJOUTS = sorted(ENTREE.rglob("images_ajouts.csv"))[0]   # nom de images.csv dans le jeu Kaggle feuilles-v3-ajouts
    NUIT = sorted(ENTREE.rglob("nuit.csv"))[0]
VERS = {"saine": "saine", "cercosporiose_noire": "black_sigatoka", "fusariose": "fusarium", "black_sigatoka": "black_sigatoka",
        "cordana": "cordana", "pestalotiopsis": "pestalotiopsis"}
VERS_COMMUN = {"saine": "saine", "black_sigatoka": "cercosporiose_noire", "fusarium": "fusariose", "cordana": "cordana",
               "pestalotiopsis": "pestalotiopsis", "malade_non_identifiee": "malade_non_identifiee", "inconnu": "je_ne_sais_pas"}
idx = pd.read_csv(INDEX)
idx = idx[idx.retenue.astype(bool) & idx.chemin.notna()]


def tableau(s):
    return pd.DataFrame(dict(chemin="data/feuilles/" + s.chemin.values, fichier=[str(INDEX.parent / c) for c in s.chemin],
                             jeu=s.source.values, classe_vraie=s.classe.values))


nuit = pd.read_csv(NUIT)
BASE_NUIT = NUIT.parent
if not (BASE_NUIT / nuit.image.iloc[0]).exists():   # dossiers envoyés en zip : retrouver où Kaggle les a décompressés
    trouve = next(Path("/kaggle/input").rglob(Path(nuit.image.iloc[0]).name))
    BASE_NUIT = trouve.parents[len(Path(nuit.image.iloc[0]).parts) - 1]
assert all((BASE_NUIT / i).exists() for i in nuit.image.iloc[::50]), "images de maladies-nuit introuvables"
nuit = pd.DataFrame(dict(chemin=nuit.image.values, fichier=[str(BASE_NUIT / i) for i in nuit.image], jeu=nuit.jeu.values,
                         classe_vraie=nuit.classe.values, role=nuit.role.values))
bd = nuit[nuit.role.eq("apprentissage")].drop(columns="role")
entrainement = pd.concat([tableau(idx[idx.ensemble.eq("entrainement")]), bd], ignore_index=True)
validation = tableau(idx[idx.ensemble.eq("validation")])
bananalsd = tableau(idx[idx.ensemble.eq("test") & idx.source.eq("bananalsd")])
aj = pd.read_csv(AJOUTS)
aj = aj[aj.jeu.eq("tdtu")]
tdtu = pd.DataFrame(dict(chemin="data/feuilles_v3_ajouts/" + aj.image.str.removeprefix("ajouts_v3/"),
                         fichier=[str(AJOUTS.parent / i.removeprefix("ajouts_v3/")) for i in aj.image], jeu="tdtu",
                         classe_vraie=aj.classe.values))
mesures = {j: g.drop(columns="role").reset_index(drop=True) for j, g in nuit[nuit.role.eq("mesure")].groupby("jeu")}
if ESSAI_LOCAL:
    entrainement = entrainement.groupby(["jeu", "classe_vraie"]).head(2).reset_index(drop=True)
    validation = validation.groupby("classe_vraie").head(4).reset_index(drop=True)
    bananalsd, tdtu = bananalsd.head(6), tdtu.head(6)
    mesures = {j: g.head(4) for j, g in mesures.items()}
else:
    assert len(validation) == 3001 and len(bananalsd) == 897 and len(tdtu) == 1636
    assert (entrainement.jeu != "mendeley_bd").sum() == 16963
print("entraînement", entrainement.groupby(["jeu", "classe_vraie"]).size().to_dict(), "| mesures",
      {j: len(g) for j, g in mesures.items()}, flush=True)

# 2. Préparation et augmentations de la v2
MOYENNE, ECART = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


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


# 3. Réseaux
class FauxVit(torch.nn.Module):   # essai local seulement : même interface que DINOv2 / timm, aucun poids téléchargé
    def __init__(self, patch, prefixes):
        super().__init__()
        self.c, self.num_prefix_tokens = torch.nn.Conv2d(3, 768, patch, patch), prefixes
    def forward_features(self, x):
        t = self.c(x).flatten(2).transpose(1, 2)
        if self.num_prefix_tokens is None:
            return {"x_norm_clstoken": t.mean(1), "x_norm_patchtokens": t}
        return torch.cat([t[:, :1].repeat(1, self.num_prefix_tokens, 1), t], 1)


class Vit(torch.nn.Module):
    def __init__(self, dos):
        super().__init__()
        self.dino, self.tete = dos, torch.nn.Linear(2 * getattr(dos, "embed_dim", 768), len(CLASSES))
    def forward(self, x):
        f = self.dino.forward_features(x)
        if isinstance(f, dict):   # DINOv2 (torch.hub)
            c, p = f["x_norm_clstoken"], f["x_norm_patchtokens"]
        else:                     # timm (DINOv3) : jetons normalisés, jeton de classe puis registres puis image
            c, p = f[:, 0], f[:, self.dino.num_prefix_tokens:]
        return self.tete(torch.cat([c, p.mean(1)], 1))


def dos_de_base():
    global MOYENNE, ECART
    if RESEAU == "convnext":
        return models.convnext_tiny(weights=None if ESSAI_LOCAL else models.ConvNeXt_Tiny_Weights.IMAGENET1K_V1)
    if RESEAU in ("dinov2", "dinov2l"):
        nom = "dinov2_vitb14" if RESEAU == "dinov2" else "dinov2_vitl14"
        return FauxVit(14, None) if ESSAI_LOCAL else torch.hub.load("facebookresearch/dinov2", nom, trust_repo=True)
    if ESSAI_LOCAL:
        return FauxVit(16, 5)
    import timm
    m = timm.create_model("vit_base_patch16_dinov3.lvd1689m", pretrained=True, num_classes=0, dynamic_img_size=True)
    cfg = m.pretrained_cfg
    MOYENNE, ECART = list(cfg.get("mean", MOYENNE)), list(cfg.get("std", ECART))
    print("DINOv3 :", cfg.get("hf_hub_id"), "préfixes", m.num_prefix_tokens, "normalisation", MOYENNE, ECART, flush=True)
    return m


BASE = dos_de_base()   # téléchargé une fois, copié pour chaque réseau
NORMALISATION = T.Normalize(MOYENNE, ECART)
aug_entrainement = T.Compose([
    JPEGAleatoire(), T.RandomResizedCrop(224, scale=(0.4, 1.0), ratio=(0.8, 1.25)),
    T.RandomHorizontalFlip(), T.RandomVerticalFlip(), T.RandomRotation(30),
    T.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.04),
    T.RandomApply([T.GaussianBlur(5, sigma=(0.1, 2.0))], p=0.3),
    T.ToTensor(), NORMALISATION, T.RandomErasing(p=0.5, scale=(0.02, 0.15))])
aug_evaluation = T.Compose([T.ToTensor(), NORMALISATION])


def nouveau_modele():
    if RESEAU == "convnext":
        m = copy.deepcopy(BASE)
        m.classifier[2] = torch.nn.Linear(m.classifier[2].in_features, len(CLASSES))
        return m.to(appareil).to(memory_format=torch.channels_last)
    return Vit(copy.deepcopy(BASE)).to(appareil)


class Feuilles(Dataset):
    def __init__(self, df, tr, etiquettes=True):
        self.c, self.tr = list(df.fichier), tr
        self.y = [CLASSES.index(VERS[c]) for c in df.classe_vraie] if etiquettes else [0] * len(df)
    def __len__(self):
        return len(self.c)
    def __getitem__(self, i):
        return self.tr(preparer(self.c[i])), self.y[i]


poids = np.select([entrainement.jeu.eq("perou_2026"), entrainement.jeu.eq("mendeley_bd")], [POIDS_PEROU, POIDS_BD], 1.0)
TRAVAILLEURS = 0 if ESSAI_LOCAL else 4
VUES = [lambda x: x, lambda x: x.flip(3), lambda x: x.flip(2), lambda x: x.rot90(1, (2, 3))]


@torch.no_grad()
def probas(reseaux, df, quatre_vues):
    """Moyenne des réseaux de la moyenne des vues ; un réseau à la fois sur le GPU (mémoire), puis remis où il était."""
    vues = VUES if quatre_vues else VUES[:1]
    total = None
    for m in reseaux:
        ou = next(m.parameters()).device
        m.to(appareil).eval()
        s = []
        for x, _ in DataLoader(Feuilles(df, aug_evaluation, etiquettes=False), 8 if ESSAI_LOCAL else 64, num_workers=TRAVAILLEURS):
            x = x.to(appareil)
            with torch.autocast("cuda", dtype=torch.float16, enabled=MIXTE):
                p = sum(torch.softmax(m(v(x)).float(), 1) for v in vues) / len(vues)
            s.append(p.float().cpu())
        m.to(ou)
        p = torch.cat(s).numpy()
        total = p if total is None else total + p
    return total / len(reseaux)


V_VAL = np.array([CLASSES.index(VERS[c]) for c in validation.classe_vraie])
SEUILS = np.round(np.arange(0.05, 0.96, 0.05), 2)


def tableau_seuils(p, v):
    malade, pm = v > 0, 1 - p[:, 0]
    return pd.DataFrame([dict(seuil=s, cout=COUT_RATEE * int((~(pm >= s) & malade).sum()) + int(((pm >= s) & ~malade).sum()))
                         for s in SEUILS])


def epoque(m, opt, plan, echelle, perte, charge, borne):
    m.train(); t0, tot, n = time.time(), 0.0, 0
    for x, y in charge:
        x, y = x.to(appareil), y.to(appareil)
        if RESEAU == "convnext":
            x = x.contiguous(memory_format=torch.channels_last)
        opt.zero_grad()
        with torch.autocast("cuda", dtype=torch.float16, enabled=MIXTE):
            l = perte(m(x).float(), y)
        echelle.scale(l).backward()
        if borne:
            echelle.unscale_(opt); torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        echelle.step(opt); echelle.update()
        tot += l.item() * len(y); n += len(y)
    if plan is not None:
        plan.step()
    assert np.isfinite(tot), "perte non finie : une relance technique permise (protocole, section 5)"
    return tot / n, time.time() - t0


# 4. Entraînement : 3 réseaux, dernière époque gardée
historique, reseaux = [], []
REPRISE = {}   # relance technique de L5 (protocole, section 6) : réseau 1 repris tel quel de la version 1 du carnet
if not ESSAI_LOCAL and RESEAU == "dinov2l":
    REPRISE = {0: f for f in sorted(Path("/kaggle/input").rglob("maladies_l5_1.pt"))[:1]}
for k in range(NB_MODELES):
    random.seed(k); np.random.seed(k); torch.manual_seed(k)
    m = nouveau_modele()
    if k in REPRISE:
        w = torch.load(REPRISE[k], map_location="cpu", weights_only=True)
        m.load_state_dict({n: v.float() if v.is_floating_point() else v for n, v in w.items()})
        print(f"réseau {k + 1} repris de {REPRISE[k]} (version 1, entraînement complet)", flush=True)
        m.eval().cpu(); reseaux.append(m)
        torch.save({n: (t.half() if t.is_floating_point() else t) for n, t in m.state_dict().items()}, SORTIE / f"maladies_{NOM}_{k + 1}.pt")
        continue
    tirage = WeightedRandomSampler(torch.tensor(poids, dtype=torch.double), len(entrainement), replacement=True,
                                   generator=torch.Generator().manual_seed(k))
    charge = DataLoader(Feuilles(entrainement, aug_entrainement), TAILLE_LOT, sampler=tirage, num_workers=TRAVAILLEURS,
                        persistent_workers=TRAVAILLEURS > 0, drop_last=True)
    perte = torch.nn.CrossEntropyLoss(label_smoothing=LISSAGE)
    echelle = torch.amp.GradScaler("cuda", enabled=MIXTE)
    if VIT:   # LP : réseau figé, tête seule ; puis FT (recette de DINOv2-FT)
        for p in m.dino.parameters():
            p.requires_grad_(False)
        opt = torch.optim.AdamW(m.tete.parameters(), lr=1e-3, weight_decay=0.05)
        for e in range(EPOQUES_TETE):
            l, d = epoque(m, opt, None, echelle, perte, charge, True)
            historique.append(dict(reseau=k + 1, phase="tete", epoque=e + 1, perte=l,
                                   cout_validation=int(tableau_seuils(probas([m], validation, False), V_VAL).cout.min())))
            print(f"réseau {k + 1} tête seule époque {e + 1} perte {l:.3f} ({d:.0f} s)", flush=True)
        for p in m.dino.parameters():
            p.requires_grad_(True)
        opt = torch.optim.AdamW([dict(params=m.dino.parameters(), lr=1e-5), dict(params=m.tete.parameters(), lr=1e-4)],
                                weight_decay=0.05)
    else:     # recette de la v2
        opt = torch.optim.AdamW(m.parameters(), lr=1e-4, weight_decay=1e-4)
    plan = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOQUES)
    for e in range(EPOQUES):
        l, d = epoque(m, opt, plan, echelle, perte, charge, VIT)
        historique.append(dict(reseau=k + 1, phase="reseau", epoque=e + 1, perte=l,
                               cout_validation=int(tableau_seuils(probas([m], validation, False), V_VAL).cout.min())))
        print(f"réseau {k + 1} époque {e + 1} perte {l:.3f} ({d:.0f} s)", flush=True)
    m.eval()
    torch.save({n: (t.half() if t.is_floating_point() else t) for n, t in m.state_dict().items()}, SORTIE / f"maladies_{NOM}_{k + 1}.pt")
    del opt, echelle, charge
    m.cpu(); reseaux.append(m)
    if MIXTE:
        torch.cuda.empty_cache()
pd.DataFrame(historique).to_csv(SORTIE / "historique.csv", index=False)

# 5. Règles de la v2 sur la validation : moyenne des réseaux ou un seul, 1 ou 4 vues, puis seuils
p_seul, p_moy = probas(reseaux[:1], validation, True), probas(reseaux, validation, True)
cout_seul, cout_moy = int(tableau_seuils(p_seul, V_VAL).cout.min()), int(tableau_seuils(p_moy, V_VAL).cout.min())
if cout_moy > cout_seul:
    reseaux = reseaux[:1]
p1, p4 = probas(reseaux, validation, False), probas(reseaux, validation, True)
t1, t4 = tableau_seuils(p1, V_VAL), tableau_seuils(p4, V_VAL)
QUATRE_VUES = bool(t4.cout.min() < t1.cout.min())
pv, tv = (p4, t4) if QUATRE_VUES else (p1, t1)
SEUIL_ALERTE = float(tv.loc[tv.cout.idxmin(), "seuil"])
pm = 1 - pv[:, 0]
part = pv[:, 1:].max(1) / np.maximum(pm, 1e-9)
maladie, alerte = 1 + pv[:, 1:].argmax(1), (pm >= SEUIL_ALERTE) & (V_VAL > 0)
SEUIL_NOM = 1.0
for s in np.round(np.arange(0.50, 1.0, 0.01), 2):
    nn = alerte & (part >= s)
    if nn.sum() and (maladie[nn] == V_VAL[nn]).mean() >= OBJECTIF_NOM_JUSTE:
        SEUIL_NOM = float(s); break
SEUIL_CONFIANCE = float(np.quantile(pv.max(1), 1 - ACCEPTATION_VALIDATION))
seuils = dict(modele=f"{NOM}_{RESEAU}_cinq_classes", reseau=RESEAU, classes=CLASSES, quatre_vues=QUATRE_VUES,
              nb_reseaux=len(reseaux), seuil_alerte=SEUIL_ALERTE, seuil_nom=SEUIL_NOM, seuil_confiance=SEUIL_CONFIANCE,
              normalisation=dict(moyenne=MOYENNE, ecart_type=ECART),
              note="Seuils réglés sur la validation (3 001) par les règles de la v2 ; docs/protocole_maladies_cinq_classes.md")
(SORTIE / "seuils.json").write_text(json.dumps(seuils, ensure_ascii=False, indent=1), encoding="utf-8")


def decider(p):
    pm = 1 - p[:, 0]; part = p[:, 1:].max(1) / np.maximum(pm, 1e-9)
    nom = np.array(CLASSES)[1 + p[:, 1:].argmax(1)]
    r = np.where(pm < SEUIL_ALERTE, "saine", np.where(part >= SEUIL_NOM, nom, "malade_non_identifiee")).astype(object)
    r[p.max(1) < SEUIL_CONFIANCE] = "inconnu"
    return [VERS_COMMUN[x] for x in r]


# 6. Probabilités et réponses, sans score affiché
jeux = {"validation": validation, "bananalsd": bananalsd, "tdtu": tdtu, **mesures}
for nom, df in jeux.items():
    p = pv if nom == "validation" else probas(reseaux, df, QUATRE_VUES)
    df.drop(columns="fichier").assign(**{f"p_{c}": p[:, i].round(6) for i, c in enumerate(CLASSES)}, reponse=decider(p)).to_csv(
        SORTIE / f"predictions_{NOM}_{nom}.csv", index=False)
journal = dict(reseau=RESEAU, versions=dict(torch=torch.__version__, python=sys.version.split()[0],
                                            gpu=torch.cuda.get_device_name(0) if MIXTE else "processeur"),
               effectifs=dict(entrainement=len(entrainement), **{j: len(d) for j, d in jeux.items()}),
               cout_un_reseau=cout_seul, cout_moyenne=cout_moy, essai_local=ESSAI_LOCAL)
(SORTIE / "journal.json").write_text(json.dumps(journal, ensure_ascii=False, indent=1, default=int), encoding="utf-8")
print("->", SORTIE, sorted(p.name for p in SORTIE.iterdir()), flush=True)
