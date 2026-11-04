#!/usr/bin/env python3
"""Écrit notebooks/entrainer_centres_v3_kaggle.ipynb (détecteur de centres v3, protocole docs/protocole_comptage_v3.md).

Le carnet reprend la recette du v2 (réseau, perte, augmentations, 30 époques) ; seuls changent les données, la zone
ignorée, le tirage des échantillons et la règle de choix. Variable d'environnement FS_ESSAI_LOCAL=<dossier> : essai
sur processeur avec quelques tuiles (vérification du code avant Kaggle), sans rien changer à la recette.

Exemple :
    python scripts/ecrire_carnet_v3.py
"""
import json
from pathlib import Path

CELLULES = []


def md(texte):
    CELLULES.append(dict(cell_type="markdown", metadata={}, source=texte.strip("\n")))


def code(texte):
    CELLULES.append(dict(cell_type="code", metadata={}, execution_count=None, outputs=[], source=texte.strip("\n")))


md("""
# Field Scan : détecteur de centres v3, réentraîné de zéro

Protocole complet, fixé et validé **avant** cet entraînement : `docs/protocole_comptage_v3.md` (commit 2ea3b4c et suivants).

**Données** (`comptage_v3_5cm.zip`, préparé par `scripts/preparer_comptage_v3.py` d'après `scripts/decouper_comptage.py`) : découpage par site, orthomosaïque ou vol, sans fuite vérifiée ; jeunes bananiers DJI réannotés en points ; palmiers et cocotiers comme exemples sans bananier, à leur taille réelle.

**Règle de choix** : couple (époque, seuil) qui maximise la moyenne des F1 de validation (segmento est, jeunes bananiers dji_0544, MM1-MM2 mères seules), parmi les couples dont les fausses détections sur les images de validation sans bananier restent sous 5 % des arbres annotés. **Adoption** : le v3 remplace le v2 par principe de protocole. **Test** (CG1-CG9, images de test sans bananier) : regardé une seule fois, à la fin.

**Avant de lancer** : Input = `field-scan-comptage` (version avec `comptage_v3_5cm.zip`) ; GPU ; Save & Run All. Vérifier les premières lignes du journal (nombre de tuiles par ensemble).
""")

md("## 1. Données")
code(r"""
import os, glob, zipfile, shutil, json, time
ESSAI = os.environ.get('FS_ESSAI_LOCAL')          # essai local sur processeur (vérification du code), sinon Kaggle
if ESSAI:
    SRC, D, SORTIE = ESSAI, ESSAI, os.path.join(ESSAI, '_sortie_essai')
    os.makedirs(SORTIE, exist_ok=True)
else:
    z = [p for p in glob.glob('/kaggle/input/**/comptage_v3_5cm*.zip', recursive=True) if os.path.isfile(p)]
    d = [os.path.dirname(p) for p in glob.glob('/kaggle/input/**/tuiles.csv', recursive=True)]
    assert z or d, 'Introuvable : comptage_v3_5cm.zip (ou un dossier contenant tuiles.csv)'
    D, SORTIE = '/tmp/v3', '/kaggle/working/modele_centres_v3'
    shutil.rmtree(D, ignore_errors=True); os.makedirs(SORTIE, exist_ok=True)
    if z:
        with zipfile.ZipFile(z[0]) as zz:
            zz.extractall(D)
        SRC = z[0]
    else:
        shutil.copytree(d[0], D); SRC = d[0]
print('Source :', SRC)
for f in ('tuiles.csv', 'objets.csv', 'mm/points.csv', 'mm/zones.csv', 'cg/points.csv', 'cg/zones.csv'):
    assert os.path.exists(f'{D}/{f}'), f'manque {f}'
def chemin_image(nom):
    for sous in ('images', 'mm/images', 'cg/images'):
        p = f'{D}/{sous}/{nom}'
        if os.path.exists(p):
            return p
    raise FileNotFoundError(nom)
print(len(os.listdir(f'{D}/images')), 'tuiles')
""")

md("## 2. Versions")
code(r"""
import torch, torchvision, platform, numpy as np, pandas as pd
VERSIONS = {'torch': torch.__version__, 'torchvision': torchvision.__version__, 'python': platform.python_version(),
            'gpu': torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'aucun'}
print(VERSIONS)
if not ESSAI:
    assert torch.cuda.is_available(), 'Pas de GPU : Settings > Accelerator > GPU'
DEV = 'cuda' if torch.cuda.is_available() else 'cpu'
""")

md("## 3. Échantillons et équilibre (protocole, section 3 bis)")
code(r"""
TUILES = pd.read_csv(f'{D}/tuiles.csv'); OBJETS = pd.read_csv(f'{D}/objets.csv')
if ESSAI:                                          # essai : quelques tuiles par ensemble et par groupe
    TUILES = TUILES.groupby(['ensemble', 'groupe']).head(3)
RAYON_IGNORE = 20.0                                # rejets : ni cible ni fond dans un rayon de 1 m (20 px)

def echantillon(r):
    o = OBJETS[OBJETS.image_path == r.image_path]
    meres = o[o.type == 'mere'][['cx', 'cy', 'taille']].to_numpy('float32').reshape(-1, 3)
    ign = o[o.type != 'mere'][['cx', 'cy']].to_numpy('float32').reshape(-1, 2)
    ign = np.c_[ign, np.full(len(ign), RAYON_IGNORE, 'float32')] if len(ign) else np.zeros((0, 3), 'float32')
    masque = None if np.isnan(r.masque_r) else np.array([[r.masque_cx, r.masque_cy, r.masque_r]], 'float32')
    return dict(nom=r.image_path, groupe=r.groupe, pts=meres, ign=ign, masque=masque, n_autres=int(r.n_autres_arbres))

ECH = {e: [echantillon(r) for r in g.itertuples()] for e, g in TUILES.groupby('ensemble')}
NEGATIF = lambda e: e['groupe'].startswith(('palmier', 'cocotier'))
TRAIN = ECH['train']
T_RT = [e for e in TRAIN if e['groupe'].startswith('rt_')]
T_JEUNES = [e for e in TRAIN if e['groupe'].startswith('jeunes_dji')]
T_NEG = [e for e in TRAIN if NEGATIF(e)]
T_AUTRES = [e for e in TRAIN if not (e['groupe'].startswith(('rt_', 'jeunes_dji')) or NEGATIF(e))]
# Parts fixées à l'avance : ReforesTree 25 % (règle du v2), jeunes bananiers 10 %, sans bananier au plus 25 %
# (tirage renouvelé à chaque époque), le reste (segmento ouest, Count) 40 % sans répétition.
N_EPOQUE = int(round(len(T_AUTRES) / 0.40))
REP_RT = max(1, int(round(0.25 * N_EPOQUE / max(len(T_RT), 1))))
REP_JEUNES = max(1, int(round(0.10 * N_EPOQUE / max(len(T_JEUNES), 1))))
N_NEG = min(len(T_NEG), int(round(0.25 * N_EPOQUE)))
def echantillons_epoque(rng):
    return T_AUTRES + T_RT * REP_RT + T_JEUNES * REP_JEUNES + rng.sample(T_NEG, N_NEG)
print(f'Entraînement : autres {len(T_AUTRES)} tuiles ; ReforesTree {len(T_RT)} x {REP_RT} ; jeunes bananiers '
      f'{len(T_JEUNES)} x {REP_JEUNES} ; sans bananier {N_NEG} tirées parmi {len(T_NEG)} ; '
      f'{len(T_AUTRES) + len(T_RT) * REP_RT + len(T_JEUNES) * REP_JEUNES + N_NEG} échantillons par époque')
for e, l in ECH.items():
    print(f'  {e:14s} : {len(l):5d} tuiles, {sum(len(x["pts"]) for x in l):6d} bananiers, '
          f'{sum(x["n_autres"] for x in l):5d} autres arbres')
PTS_MM, ZONES_MM = pd.read_csv(f'{D}/mm/points.csv'), pd.read_csv(f'{D}/mm/zones.csv')
print('MM :', PTS_MM.groupby(['zone_id', 'type']).size().to_dict())
""")

md("## 4. Jeu de données, augmentations, cartes cibles et zone ignorée")
code(r"""
import random, math
from PIL import Image, ImageEnhance
from torch.utils.data import Dataset, DataLoader

CROP, STRIDE = 448, 4
MOY = np.array([0.485, 0.456, 0.406], 'float32'); ECT = np.array([0.229, 0.224, 0.225], 'float32')

def carte_cible(pts, h, w):
    # Une gaussienne par pied, centrée sur la cellule du centre (valeur 1 au pic) ; écart-type = taille / 24 (comme le v2)
    H, W = (h + STRIDE - 1) // STRIDE, (w + STRIDE - 1) // STRIDE
    hm = np.zeros((H, W), 'float32')
    for cx, cy, t in pts:
        i, j = int(cx // STRIDE), int(cy // STRIDE)
        if not (0 <= i < W and 0 <= j < H):
            continue
        s = max(0.8, t / STRIDE / 6)
        r = int(3 * s) + 1
        x0, x1, y0, y1 = max(0, i - r), min(W, i + r + 1), max(0, j - r), min(H, j + r + 1)
        xx, yy = np.arange(x0, x1)[None, :], np.arange(y0, y1)[:, None]
        hm[y0:y1, x0:x1] = np.maximum(hm[y0:y1, x0:x1], np.exp(-((xx - i) ** 2 + (yy - j) ** 2) / (2 * s * s)))
    return hm

def carte_poids(masque, ign, h, w):
    # 1 = compté dans la perte ; 0 = ignoré (hors du disque des photos DJI, autour des rejets)
    H, W = (h + STRIDE - 1) // STRIDE, (w + STRIDE - 1) // STRIDE
    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy = (xx + 0.5) * STRIDE, (yy + 0.5) * STRIDE
    p = np.ones((H, W), 'float32')
    if masque is not None and len(masque):
        mx, my, mr = masque[0]
        p[(cx - mx) ** 2 + (cy - my) ** 2 > mr ** 2] = 0
    for x, y, r in ign:
        p[(cx - x) ** 2 + (cy - y) ** 2 <= r ** 2] = 0
    return p

def tourner(arr, pts, k):
    # Rotation de k quarts de tour (sens direct, comme np.rot90) de l'image et des points (colonnes x, y, valeur)
    for _ in range(k):
        n = arr.shape[1]
        arr = np.rot90(arr)
        pts = [np.c_[p[:, 1], n - p[:, 0], p[:, 2]] if p is not None and len(p) else p for p in pts]
    return np.ascontiguousarray(arr), pts

class Tuiles(Dataset):
    def __init__(self, echantillons):
        self.e = echantillons
    def __len__(self):
        return len(self.e)
    def __getitem__(self, i):
        ech = self.e[i]
        im = Image.open(chemin_image(ech['nom'])).convert('RGB')
        pts, ign = ech['pts'].copy(), ech['ign'].copy()
        masque = None if ech['masque'] is None else ech['masque'].copy()
        e = random.uniform(0.8, 1.25)                                   # variation d'échelle (comme le v2)
        im = im.resize((max(1, round(im.width * e)), max(1, round(im.height * e))), Image.BILINEAR)
        pts[:, :3] *= e; ign[:, :3] *= e
        if masque is not None:
            masque *= e
        for f in (ImageEnhance.Brightness, ImageEnhance.Contrast, ImageEnhance.Color):
            im = f(im).enhance(random.uniform(0.8, 1.2))
        a = np.asarray(im)
        x0, y0 = random.randint(0, max(0, a.shape[1] - CROP)), random.randint(0, max(0, a.shape[0] - CROP))
        cadre = np.zeros((CROP, CROP, 3), 'uint8')
        morceau = a[y0:y0 + CROP, x0:x0 + CROP]
        cadre[:morceau.shape[0], :morceau.shape[1]] = morceau
        for p in [pts, ign] + ([masque] if masque is not None else []):
            p[:, 0] -= x0; p[:, 1] -= y0
        pts = pts[(pts[:, 0] >= 0) & (pts[:, 0] < CROP) & (pts[:, 1] >= 0) & (pts[:, 1] < CROP)]
        if random.random() < 0.5:
            cadre = np.ascontiguousarray(cadre[:, ::-1])
            for p in [pts, ign] + ([masque] if masque is not None else []):
                p[:, 0] = CROP - p[:, 0]
        cadre, (pts, ign, masque) = tourner(cadre, [pts, ign, masque], random.randint(0, 3))
        x = ((cadre.astype('float32') / 255 - MOY) / ECT).transpose(2, 0, 1)
        return (torch.from_numpy(x), torch.from_numpy(carte_cible(pts, CROP, CROP)[None]),
                torch.from_numpy(carte_poids(masque, ign, CROP, CROP)[None]))
""")

md("## 5. Réseau, perte, pics et mesures")
code(r"""
import torch.nn as nn, torch.nn.functional as F
from torchvision.models import resnet18, ResNet18_Weights
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

class DetecteurCentres(nn.Module):
    # ResNet-18 (ImageNet) + décodeur à fusion d'étages (type FPN) -> carte des centres au quart de la résolution (comme le v2)
    def __init__(self, c=64):
        super().__init__()
        r = resnet18(weights=ResNet18_Weights.DEFAULT)
        self.souche = nn.Sequential(r.conv1, r.bn1, r.relu, r.maxpool)
        self.etages = nn.ModuleList([r.layer1, r.layer2, r.layer3, r.layer4])
        self.lat = nn.ModuleList([nn.Conv2d(k, c, 1) for k in (64, 128, 256, 512)])
        self.lisse = nn.Sequential(nn.Conv2d(c, c, 3, padding=1), nn.BatchNorm2d(c), nn.ReLU(inplace=True),
                                   nn.Conv2d(c, c, 3, padding=1), nn.BatchNorm2d(c), nn.ReLU(inplace=True))
        self.tete = nn.Conv2d(c, 1, 1)
        nn.init.constant_(self.tete.bias, -2.19)
    def forward(self, x):
        x = self.souche(x)
        feats = []
        for et in self.etages:
            x = et(x); feats.append(x)
        p = self.lat[3](feats[3])
        for k in (2, 1, 0):
            p = F.interpolate(p, size=feats[k].shape[-2:], mode='nearest') + self.lat[k](feats[k])
        return self.tete(self.lisse(p))

def perte_focale(logits, cible, poids):
    # Perte focale de CenterNet (comme le v2), pondérée : les cellules de poids 0 (zone ignorée) ne comptent pas
    p = torch.sigmoid(logits.float()).clamp(1e-4, 1 - 1e-4)
    pos = cible.eq(1).float() * poids
    l_pos = torch.log(p) * (1 - p) ** 2 * pos
    l_neg = torch.log(1 - p) * p ** 2 * (1 - cible) ** 4 * (1 - cible.eq(1).float()) * poids
    return -(l_pos.sum() + l_neg.sum()) / pos.sum().clamp(min=1)

K_PICS = 7

def pics(carte, seuil):
    m = F.max_pool2d(carte[None, None], K_PICS, 1, K_PICS // 2)[0, 0]
    ys, xs = torch.nonzero((carte == m) & (carte >= seuil), as_tuple=True)
    return (np.c_[(xs.cpu().numpy() + 0.5) * STRIDE, (ys.cpu().numpy() + 0.5) * STRIDE],
            carte[ys, xs].float().cpu().numpy())

@torch.no_grad()
def predire_carte(modele, img):
    x = torch.from_numpy(((img.astype('float32') / 255 - MOY) / ECT).transpose(2, 0, 1))[None].to(DEV)
    with torch.autocast(DEV, dtype=torch.float16, enabled=DEV == 'cuda'):
        logits = modele(x)
    return torch.sigmoid(logits.float())[0, 0]

def compter(det, certains, ignores, rayon):
    # Comme evaluer_comptage.evaluer_zone : appariement optimal à rayon ; détections proches d'un point ignoré écartées
    n, pris = 0, set()
    if len(det) and len(certains):
        d = cdist(det, certains)
        li, co = linear_sum_assignment(np.where(d <= rayon, d, 1e6))
        ok = d[li, co] <= rayon
        n, pris = int(ok.sum()), set(li[ok].tolist())
    reste = [i for i in range(len(det)) if i not in pris]
    ign = int((cdist(det[reste], ignores).min(1) <= rayon).sum()) if len(ignores) and reste else 0
    return n, len(det) - n - ign, len(certains) - n

def f1(vp, fp, fn):
    p = vp / (vp + fp) if vp + fp else 0.0; r = vp / (vp + fn) if vp + fn else 0.0
    return round(2 * p * r / (p + r), 4) if p + r else 0.0

SEUILS = [round(0.10 + 0.05 * k, 2) for k in range(11)]          # 0,10 à 0,60 par pas de 0,05 (protocole)
RAYON_PX = 20                                                     # 1 m à 5 cm par pixel

def dans_masque(xy, masque):
    if masque is None or not len(xy):
        return np.ones(len(xy), bool)
    mx, my, mr = masque[0]
    return (xy[:, 0] - mx) ** 2 + (xy[:, 1] - my) ** 2 <= mr ** 2

def mesurer_tuiles(modele, echantillons):
    # F1 par seuil sur des tuiles (centres annotés ; rejets ignorés ; disque appliqué aux détections et aux points)
    acc = {s: [0, 0, 0] for s in SEUILS}
    for e in echantillons:
        det, sc = pics(predire_carte(modele, np.asarray(Image.open(chemin_image(e['nom'])).convert('RGB'))), min(SEUILS))
        garde = dans_masque(det, e['masque']); det, sc = det[garde], sc[garde]
        certains = e['pts'][dans_masque(e['pts'], e['masque'])][:, :2]
        for s in SEUILS:
            for k, v in enumerate(compter(det[sc >= s], certains, e['ign'][:, :2], RAYON_PX)):
                acc[s][k] += v
    return {s: dict(vp=a[0], fp=a[1], fn=a[2], f1=f1(*a)) for s, a in acc.items()}

def mesurer_reference(modele, pts_ref, zones, meres_seules=True):
    # Références manuelles (MM, CG) : détections dans le carré ; rejets et incertains ignorés (ou rejets comptés)
    acc = {s: [0, 0, 0] for s in SEUILS}; parzone = {}
    for _, z in zones.iterrows():
        det, sc = pics(predire_carte(modele, np.asarray(Image.open(chemin_image(z.image_path)).convert('RGB'))), min(SEUILS))
        dedans = (det[:, 0] >= z.x0) & (det[:, 0] <= z.x1) & (det[:, 1] >= z.y0) & (det[:, 1] <= z.y1)
        det, sc = det[dedans], sc[dedans]
        p = pts_ref[pts_ref.zone_id == z.zone_id]
        certain = (p.type == 'mere') if meres_seules else p.type.isin(['mere', 'rejet'])
        certains, ignores = p[certain][['x', 'y']].to_numpy(), p[~certain][['x', 'y']].to_numpy()
        parzone[z.zone_id] = (det, sc, len(certains))
        for s in SEUILS:
            for k, v in enumerate(compter(det[sc >= s], certains, ignores, RAYON_PX)):
                acc[s][k] += v
    return {s: dict(vp=a[0], fp=a[1], fn=a[2], f1=f1(*a)) for s, a in acc.items()}, parzone

def mesurer_negatifs(modele, echantillons):
    # Fausses détections sur des tuiles sans bananier, rapportées au nombre d'arbres annotés
    fp = {s: 0 for s in SEUILS}; arbres = sum(e['n_autres'] for e in echantillons)
    for e in echantillons:
        _, sc = pics(predire_carte(modele, np.asarray(Image.open(chemin_image(e['nom'])).convert('RGB'))), min(SEUILS))
        for s in SEUILS:
            fp[s] += int((sc >= s).sum())
    return {s: dict(fp=fp[s], arbres=arbres, taux=round(fp[s] / max(arbres, 1), 4)) for s in SEUILS}

def mesurer_validation(modele):
    modele.eval()
    return dict(dense=mesurer_tuiles(modele, ECH['val_dense']), jeunes=mesurer_tuiles(modele, ECH['val_jeunes']),
                mm=mesurer_reference(modele, PTS_MM, ZONES_MM)[0], neg=mesurer_negatifs(modele, ECH['val_negatifs']))
""")

md("## 6. Essai rapide (s'arrête en une minute si quelque chose ne va pas)")
code(r"""
rng0 = random.Random(0)
jeu = Tuiles(echantillons_epoque(rng0))
x, y, w = jeu[0]
print('tuile', tuple(x.shape), '| carte', tuple(y.shape), '| pics à 1 :', int((y == 1).sum()), '| poids nuls :', int((w == 0).sum()))
jj = Tuiles(T_JEUNES); xj, yj, wj = jj[0]
print('tuile de jeunes bananiers : pics', int((yj == 1).sum()), '| part ignorée', round(float((wj == 0).float().mean()), 2))
modele = DetecteurCentres().to(DEV)
lot = torch.stack([jeu[i][0] for i in range(4)]).to(DEV)
cib = torch.stack([jeu[i][1] for i in range(4)]).to(DEV); poi = torch.stack([jeu[i][2] for i in range(4)]).to(DEV)
with torch.autocast(DEV, dtype=torch.float16, enabled=DEV == 'cuda'):
    sortie = modele(lot)
perte = perte_focale(sortie, cib, poi); perte.backward()
print('sortie', tuple(sortie.shape), '| perte', round(float(perte), 3), '| gradients finis :',
      all(torch.isfinite(p.grad).all() for p in modele.parameters() if p.grad is not None))
e = ECH['val_dense'][0]
img = np.asarray(Image.open(chemin_image(e['nom'])).convert('RGB'))
parfaite = torch.from_numpy(carte_cible(e['pts'], img.shape[0], img.shape[1])).to(DEV)
det, _ = pics(parfaite, 0.5)
print('carte parfaite :', compter(det, e['pts'][:, :2], np.zeros((0, 2)), RAYON_PX), 'pour', len(e['pts']),
      'bananiers (attendu : presque tous trouvés, 0 faux)')
del modele, lot, cib, poi, sortie
if DEV == 'cuda':
    torch.cuda.empty_cache()
""")

md("## 7. Entraînement et choix (règle fixée à l'avance)")
code(r"""
REGLAGES = dict(reseau='resnet18 ImageNet + décodeur FPN, sortie au quart', resolution_cm=5, decoupe_px=CROP, stride=STRIDE,
                epoques=2 if ESSAI else 30, lot=4 if ESSAI else 16, lr_squelette=3e-4, lr_decodeur=1e-3, decroissance_poids=1e-4,
                programme='OneCycle, 5 % de montée', ecretage=5.0,
                augmentations='échelle 0,8-1,25, luminosité/contraste/saturation 0,8-1,2, miroir, quarts de tour',
                k_pics=K_PICS, rayon_px=RAYON_PX, rayon_ignore_px=RAYON_IGNORE, duree_max_h=4.0, graine=2026,
                parts='ReforesTree 25 % (répétée), jeunes bananiers 10 % (répétés), sans bananier au plus 25 % (tirage par époque), autres 40 %',
                rep_reforestree=REP_RT, rep_jeunes=REP_JEUNES, n_negatifs_par_epoque=N_NEG)
random.seed(2026); np.random.seed(2026); torch.manual_seed(2026)
rng = random.Random(2026)
modele = DetecteurCentres().to(DEV)
squelette = list(modele.souche.parameters()) + list(modele.etages.parameters())
ids = {id(p) for p in squelette}
decodeur = [p for p in modele.parameters() if id(p) not in ids]
opt = torch.optim.AdamW([{'params': squelette, 'lr': REGLAGES['lr_squelette']}, {'params': decodeur, 'lr': REGLAGES['lr_decodeur']}],
                        weight_decay=REGLAGES['decroissance_poids'])
n_lots = len(echantillons_epoque(random.Random(0))) // REGLAGES['lot']
prog = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=[REGLAGES['lr_squelette'], REGLAGES['lr_decodeur']],
                                           total_steps=REGLAGES['epoques'] * n_lots, pct_start=0.05)
echelle = torch.amp.GradScaler(enabled=DEV == 'cuda')

def lignes_choix(m, ep):
    # Règle fixée à l'avance (protocole, section 4)
    return [dict(epoque=ep, seuil=s, f1_dense=m['dense'][s]['f1'], f1_jeunes=m['jeunes'][s]['f1'], f1_mm=m['mm'][s]['f1'],
                 fp_neg=m['neg'][s]['fp'], taux_fp_neg=m['neg'][s]['taux'],
                 moyenne=round((m['dense'][s]['f1'] + m['jeunes'][s]['f1'] + m['mm'][s]['f1']) / 3, 4),
                 eligible=m['neg'][s]['taux'] <= 0.05) for s in SEUILS]

HISTO, MEILLEUR, REPLI, debut = [], None, None, time.time()
print(f'{n_lots} lots par époque', flush=True)
for ep in range(1, REGLAGES['epoques'] + 1):
    modele.train(); t0, somme, n = time.time(), 0.0, 0
    charge = DataLoader(Tuiles(echantillons_epoque(rng)), batch_size=REGLAGES['lot'], shuffle=True,
                        num_workers=0 if ESSAI else 4, drop_last=True, pin_memory=DEV == 'cuda')
    for k, (x, y, w) in enumerate(charge):
        if k >= n_lots or (ESSAI and k >= 3):
            break
        x, y, w = x.to(DEV, non_blocking=True), y.to(DEV, non_blocking=True), w.to(DEV, non_blocking=True)
        with torch.autocast(DEV, dtype=torch.float16, enabled=DEV == 'cuda'):
            logits = modele(x)
        perte = perte_focale(logits, y, w)
        if not torch.isfinite(perte):
            raise RuntimeError(f"perte non finie à l'époque {ep}")
        opt.zero_grad(set_to_none=True)
        echelle.scale(perte).backward(); echelle.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(modele.parameters(), REGLAGES['ecretage'])
        echelle.step(opt); echelle.update(); prog.step()
        somme += float(perte); n += 1
    lignes = lignes_choix(mesurer_validation(modele), ep)
    HISTO += lignes
    eligibles = [r for r in lignes if r['eligible']]
    be = max(eligibles, key=lambda r: r['moyenne']) if eligibles else None
    if be and (MEILLEUR is None or be['moyenne'] > MEILLEUR['moyenne']):
        MEILLEUR = be; torch.save(modele.state_dict(), f'{SORTIE}/meilleur.pt')
    if MEILLEUR is None:                       # repli prévu par le protocole : aucun couple sous 5 % jusqu'ici
        bf = min(lignes, key=lambda r: (r['taux_fp_neg'], -r['moyenne']))
        if REPLI is None or (bf['taux_fp_neg'], -bf['moyenne']) < (REPLI['taux_fp_neg'], -REPLI['moyenne']):
            REPLI = bf; torch.save(modele.state_dict(), f'{SORTIE}/repli.pt')
    b = max(lignes, key=lambda r: r['moyenne'])
    print(f"époque {ep:2d} : perte {somme / max(n, 1):.3f} | {(time.time() - t0) / 60:.1f} min | meilleur seuil {b['seuil']} : "
          f"dense {b['f1_dense']:.3f}, jeunes {b['f1_jeunes']:.3f}, MM {b['f1_mm']:.3f}, moyenne {b['moyenne']:.3f}, "
          f"sans bananier {b['taux_fp_neg']:.1%} | retenu : "
          f"{'époque ' + str(MEILLEUR['epoque']) + ' seuil ' + str(MEILLEUR['seuil']) + ' (' + str(MEILLEUR['moyenne']) + ')' if MEILLEUR else 'aucun couple éligible'}",
          flush=True)
    if (time.time() - debut) / 3600 > REGLAGES['duree_max_h']:
        print('Durée maximale atteinte : arrêt propre', flush=True); break
pd.DataFrame(HISTO).to_csv(f'{SORTIE}/choix.csv', index=False)
if MEILLEUR is None:
    print('Aucun couple sous 5 % de fausses détections : repli du protocole (le moins de fausses détections)')
    MEILLEUR = REPLI; shutil.copy(f'{SORTIE}/repli.pt', f'{SORTIE}/meilleur.pt')
print('Retenu :', MEILLEUR)
""")

md("## 8. Test (une seule fois), export ONNX et vérification")
code(r"""
modele.load_state_dict(torch.load(f'{SORTIE}/meilleur.pt', map_location=DEV)); modele.eval()
s = MEILLEUR['seuil']
PTS_CG, ZONES_CG = pd.read_csv(f'{D}/cg/points.csv'), pd.read_csv(f'{D}/cg/zones.csv')
cg_meres, parzone = mesurer_reference(modele, PTS_CG, ZONES_CG, meres_seules=True)
cg_tous, _ = mesurer_reference(modele, PTS_CG, ZONES_CG, meres_seules=False)
neg_test = mesurer_negatifs(modele, ECH['test_negatifs'])
for lib, t_ in (('CG1-CG9, mères seules', cg_meres[s]), ('CG1-CG9, tous pieds', cg_tous[s])):
    p_ = t_['vp'] / max(t_['vp'] + t_['fp'], 1); r_ = t_['vp'] / max(t_['vp'] + t_['fn'], 1)
    print(f"{lib}, seuil {s} : précision {p_:.3f}, rappel {r_:.3f}, F1 {t_['f1']:.3f}")
print(f"Images de test sans bananier : {neg_test[s]['fp']} fausses détections pour {neg_test[s]['arbres']} arbres ({neg_test[s]['taux']:.1%})")
comptes = {z: dict(detectes=int((sc >= s).sum()), meres=n_) for z, (det, sc, n_) in parzone.items()}
print('Comptage par carré (détectés / mères annotées) :', comptes)
print('Pour mémoire (v2, mesuré sur ton ordinateur) : CG mères seules F1 0,196 ; tous pieds 0,189')

if not ESSAI:
    !pip -q install onnxruntime
import onnxruntime as ort
cpu = DetecteurCentres(); cpu.load_state_dict(torch.load(f'{SORTIE}/meilleur.pt', map_location='cpu')); cpu.eval()
chemin_onnx = f'{SORTIE}/centres_5cm_v3.onnx'
torch.onnx.export(cpu, torch.randn(1, 3, 512, 512), chemin_onnx, input_names=['image'], output_names=['logits'], opset_version=17,
                  dynamic_axes={'image': {2: 'h', 3: 'l'}, 'logits': {2: 'h4', 3: 'l4'}}, dynamo=False)
img = np.asarray(Image.open(chemin_image(ZONES_MM.image_path.iloc[0])).convert('RGB'))
xin = ((img.astype('float32') / 255 - MOY) / ECT).transpose(2, 0, 1)[None]
ref = cpu(torch.from_numpy(xin)).detach().numpy()
sess = ort.InferenceSession(chemin_onnx, providers=['CPUExecutionProvider'])
t0 = time.time(); out = sess.run(None, {'image': xin})[0]; duree = time.time() - t0
ha = img.shape[0] * img.shape[1] * 0.05 ** 2 / 1e4
print(f"ONNX : écart maximal {np.abs(out - ref).max():.2e} ; {os.path.getsize(chemin_onnx) / 1e6:.0f} Mo ; "
      f"{duree:.2f} s pour {ha:.2f} ha, soit {duree / ha:.0f} s par hectare")
json.dump(dict(versions=VERSIONS, reglages=REGLAGES, retenu=MEILLEUR, seuil=s,
               tests=dict(cg_meres=cg_meres, cg_tous=cg_tous, sans_bananier=neg_test, comptes_cg=comptes),
               normalisation=dict(moyenne=MOY.tolist(), ecart_type=ECT.tolist()), entree='RGB 0-255 / 255, normalisé, NCHW',
               sortie='logits au quart de la résolution ; sigmoïde puis maxima locaux (fenêtre k_pics) au-dessus du seuil',
               regle='protocole docs/protocole_comptage_v3.md : couple (époque, seuil) maximisant la moyenne des F1 segmento est, '
                     'jeunes bananiers dji_0544 et MM1-MM2 (mères seules), fausses détections sans bananier <= 5 % des arbres ; '
                     'v3 adopté par principe ; test CG1-CG9 regardé une fois'),
          open(f'{SORTIE}/centres_5cm_v3.json', 'w'), indent=2, ensure_ascii=False, default=float)
print(sorted(os.listdir(SORTIE)))
""")

md("""
## 9. Ensuite, sur ton ordinateur

Télécharge `centres_5cm_v3.onnx` et `centres_5cm_v3.json` (même nom obligatoire), range-les dans `Field-Scan/modeles/`, puis mets `modele: modeles/centres_5cm_v3.onnx` dans `config.yaml`. Les chiffres du test sont ceux de la section 8 ; aucun réglage ne doit être changé après les avoir vus.
""")


def main():
    nb = dict(cells=CELLULES, metadata=dict(kernelspec=dict(display_name="Python 3", language="python", name="python3"),
                                            language_info=dict(name="python")), nbformat=4, nbformat_minor=5)
    for c in nb["cells"]:
        texte = c["source"]
        c["source"] = [l + "\n" for l in texte.split("\n")[:-1]] + [texte.split("\n")[-1]]
    out = Path(__file__).resolve().parents[1] / "notebooks" / "entrainer_centres_v3_kaggle.ipynb"
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Carnet écrit : {out}")


if __name__ == "__main__":
    main()
