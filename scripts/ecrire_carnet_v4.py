#!/usr/bin/env python3
"""Écrit notebooks/entrainer_centres_v4_kaggle.ipynb (détecteur de centres v4, protocole docs/protocole_comptage_v4.md).

Recette du v3 (réseau, perte pondérée, augmentations, 30 époques, graine 2026) ; changent : les données
(comptage_v4_5cm.zip), les parts des échantillons, la règle de choix (trois F1 de validation), la comparaison avec le
v3 (centres_5cm_v3.onnx, même validation, meilleur seuil pour lui) et le test en trois situations, regardé une fois.
Variable d'environnement FS_ESSAI_LOCAL=<dossier> : essai sur processeur avec quelques tuiles (vérification du code).

Exemple :
    python scripts/ecrire_carnet_v4.py
"""
import json
from pathlib import Path

CELLULES = []


def md(texte):
    CELLULES.append(dict(cell_type="markdown", metadata={}, source=texte.strip("\n")))


def code(texte):
    CELLULES.append(dict(cell_type="code", metadata={}, execution_count=None, outputs=[], source=texte.strip("\n")))


md("""
# Field Scan : détecteur de centres v4 (plantations ajoutées), réentraîné de zéro

Protocole fixé et validé **avant** cet entraînement : `docs/protocole_comptage_v4.md` (commits 8f8aeeb et bd4fdba).

**Données** : `comptage_v4_5cm.zip` (`scripts/decouper_comptage.py --version v4`, `scripts/preparer_comptage_v3.py --version v4`). Nouvelles plantations : `plantas_platano` (lote_2 en entraînement, 100_metros en validation), `platano_lasuiza` (entraînement), `banana_tree_detection` (test).

**Règle de choix** : couple (époque, seuil) qui maximise la moyenne des trois F1 de validation (plantain 100_metros, jeunes bananiers dji_0544, MM1-MM2 mères seules), fausses détections sur les images de validation sans bananier sous 5 % des arbres. **Adoption** : le v4 remplace le v3 si sa moyenne est strictement meilleure que celle du v3 mesuré sur la même validation (meilleur seuil pour lui). **Test** (segmento est, banana_tree_detection, CG1-CG9, images sans bananier) : une seule fois, v3 et v4.

**Avant de lancer** : Input = `field-scan-comptage` (version avec `comptage_v4_5cm.zip` et `centres_5cm_v3.onnx`) ; GPU ; Internet ; Save & Run All. Vérifier les premières lignes du journal.
""")

md("## 1. Données et modèle v3")
code(r"""
import os, glob, zipfile, shutil, json, time
ESSAI = os.environ.get('FS_ESSAI_LOCAL')          # essai local sur processeur (vérification du code), sinon Kaggle
if ESSAI:
    D, SORTIE = ESSAI, os.path.join(ESSAI, '_sortie_essai_v4')
    os.makedirs(SORTIE, exist_ok=True)
    ONNX_V3 = os.environ.get('FS_ONNX_V3', 'modeles/centres_5cm_v3.onnx')
else:
    print('Installation de onnxruntime (il faut Internet activé dans les réglages du carnet)…', flush=True)
    !pip install -q --timeout 20 --retries 1 onnxruntime
    try:
        import onnxruntime
    except ImportError:
        raise SystemExit("onnxruntime n'a pas pu être installé : activer Internet (Settings > Internet on) puis relancer")
    print('Recherche des données…', flush=True)
    z = [p for p in glob.glob('/kaggle/input/**/comptage_v4_5cm*.zip', recursive=True) if os.path.isfile(p)]
    d = [os.path.dirname(p) for p in glob.glob('/kaggle/input/**/tuiles.csv', recursive=True) if 'v4' in p]
    assert z or d, 'Introuvable : comptage_v4_5cm.zip (ou un dossier comptage_v4_5cm contenant tuiles.csv)'
    D, SORTIE = '/tmp/v4', '/kaggle/working/modele_centres_v4'
    shutil.rmtree(D, ignore_errors=True); os.makedirs(SORTIE, exist_ok=True)
    if z:
        with zipfile.ZipFile(z[0]) as zz:
            zz.extractall(D)
    else:
        D = d[0]                                   # dossier déjà décompressé par Kaggle : lu sur place (lecture seule), sans copie
    o = [p for p in glob.glob('/kaggle/input/**/centres_5cm_v3.onnx', recursive=True)]
    assert o, 'Introuvable : centres_5cm_v3.onnx (à ajouter au jeu field-scan-comptage)'
    ONNX_V3 = o[0]
print('Données :', D, '| modèle v3 :', ONNX_V3)
for f in ('tuiles.csv', 'objets.csv', 'mm/points.csv', 'mm/zones.csv', 'cg/points.csv', 'cg/zones.csv'):
    assert os.path.exists(f'{D}/{f}'), f'manque {f}'
def chemin_image(nom):
    for sous in ('images', 'mm/images', 'cg/images'):
        p = f'{D}/{sous}/{nom}'
        if os.path.exists(p):
            return p
    raise FileNotFoundError(nom)
print(len(os.listdir(f'{D}/images')), 'images')
""")

md("## 2. Versions")
code(r"""
import torch, torchvision, platform, numpy as np, pandas as pd, onnxruntime as ort
VERSIONS = {'torch': torch.__version__, 'torchvision': torchvision.__version__, 'python': platform.python_version(),
            'onnxruntime': ort.__version__, 'gpu': torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'aucun'}
print(VERSIONS)
if not ESSAI:
    assert torch.cuda.is_available(), 'Pas de GPU : Settings > Accelerator > GPU'
DEV = 'cuda' if torch.cuda.is_available() else 'cpu'
""")

md("## 3. Échantillons et parts (protocole v4, section 4)")
code(r"""
TUILES = pd.read_csv(f'{D}/tuiles.csv'); OBJETS = pd.read_csv(f'{D}/objets.csv')
if ESSAI:
    TUILES = TUILES.groupby(['ensemble', 'groupe']).head(3)
RAYON_IGNORE = 20.0

OBJ_PAR_IMAGE = {k: g for k, g in OBJETS.groupby('image_path')}   # une seule passe (au lieu d'un filtre par tuile)
VIDE = OBJETS.iloc[:0]

def echantillon(r):
    o = OBJ_PAR_IMAGE.get(r.image_path, VIDE)
    meres = o[o.type == 'mere'][['cx', 'cy', 'taille']].to_numpy('float32').reshape(-1, 3)
    ign = o[o.type != 'mere'][['cx', 'cy']].to_numpy('float32').reshape(-1, 2)
    ign = np.c_[ign, np.full(len(ign), RAYON_IGNORE, 'float32')] if len(ign) else np.zeros((0, 3), 'float32')
    masque = None if np.isnan(r.masque_r) else np.array([[r.masque_cx, r.masque_cy, r.masque_r]], 'float32')
    return dict(nom=r.image_path, groupe=r.groupe, pts=meres, ign=ign, masque=masque, n_autres=int(r.n_autres_arbres))

ECH = {e: [echantillon(r) for r in g.itertuples()] for e, g in TUILES.groupby('ensemble')}
NEGATIF = lambda e: e['groupe'].startswith(('palmier', 'cocotier'))
TRAIN = ECH['train']
T_PLANT = [e for e in TRAIN if e['groupe'].startswith(('pp_', 'lasuiza'))]
T_RT = [e for e in TRAIN if e['groupe'].startswith('rt_')]
T_JEUNES = [e for e in TRAIN if e['groupe'].startswith('jeunes_dji')]
T_NEG = [e for e in TRAIN if NEGATIF(e)]
T_AUTRES = [e for e in TRAIN if not (e['groupe'].startswith(('pp_', 'lasuiza', 'rt_', 'jeunes_dji')) or NEGATIF(e))]
# Parts fixées à l'avance : autres (segmento ouest, Count) 30 % sans répétition ; plantations 20 % ; ReforesTree 20 % ;
# jeunes bananiers 10 % ; sans bananier au plus 20 % (tirage renouvelé à chaque époque)
N_EPOQUE = int(round(len(T_AUTRES) / 0.30))
def parts(liste, part):
    return max(1, int(round(part * N_EPOQUE / max(len(liste), 1))))
REP_PLANT, REP_RT, REP_JEUNES = parts(T_PLANT, 0.20), parts(T_RT, 0.20), parts(T_JEUNES, 0.10)
N_NEG = min(len(T_NEG), int(round(0.20 * N_EPOQUE)))
def echantillons_epoque(rng):
    return T_AUTRES + T_PLANT * REP_PLANT + T_RT * REP_RT + T_JEUNES * REP_JEUNES + rng.sample(T_NEG, N_NEG)
n0 = len(echantillons_epoque(__import__('random').Random(0)))
print(f'Entraînement : autres {len(T_AUTRES)} ; plantations {len(T_PLANT)} x {REP_PLANT} ; ReforesTree {len(T_RT)} x {REP_RT} ; '
      f'jeunes {len(T_JEUNES)} x {REP_JEUNES} ; sans bananier {N_NEG} tirées parmi {len(T_NEG)} ; {n0} échantillons par époque')
for e, l in ECH.items():
    print(f'  {e:14s} : {len(l):5d} images, {sum(len(x["pts"]) for x in l):6d} bananiers, {sum(x["n_autres"] for x in l):5d} autres arbres')
PTS_MM, ZONES_MM = pd.read_csv(f'{D}/mm/points.csv'), pd.read_csv(f'{D}/mm/zones.csv')
PTS_CG, ZONES_CG = pd.read_csv(f'{D}/cg/points.csv'), pd.read_csv(f'{D}/cg/zones.csv')
print('MM :', PTS_MM.groupby(['zone_id', 'type']).size().to_dict())
""")

md("## 4. Jeu de données, augmentations, cartes cibles et zone ignorée (comme le v3)")
code(r"""
import random, math
from PIL import Image, ImageEnhance
from torch.utils.data import Dataset, DataLoader

CROP, STRIDE = 448, 4
MOY = np.array([0.485, 0.456, 0.406], 'float32'); ECT = np.array([0.229, 0.224, 0.225], 'float32')

def carte_cible(pts, h, w):
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
        e = random.uniform(0.8, 1.25)
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

md("## 5. Réseau, perte, prédicteurs (v4 PyTorch, v3 ONNX) et mesures")
code(r"""
import torch.nn as nn, torch.nn.functional as F
from torchvision.models import resnet18, ResNet18_Weights
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

class DetecteurCentres(nn.Module):
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
    p = torch.sigmoid(logits.float()).clamp(1e-4, 1 - 1e-4)
    pos = cible.eq(1).float() * poids
    l_pos = torch.log(p) * (1 - p) ** 2 * pos
    l_neg = torch.log(1 - p) * p ** 2 * (1 - cible) ** 4 * (1 - cible.eq(1).float()) * poids
    return -(l_pos.sum() + l_neg.sum()) / pos.sum().clamp(min=1)

K_PICS = 7
SEUILS = [round(0.10 + 0.05 * k, 2) for k in range(11)]
RAYON_PX = 20

def entree(img):
    # Image complétée en noir jusqu'à un multiple de 32 (comme la chaîne, qui complète en noir hors image)
    h, w = img.shape[:2]
    H, W = (h + 31) // 32 * 32, (w + 31) // 32 * 32
    x = np.zeros((H, W, 3), 'float32'); x[:h, :w] = img.astype('float32') / 255
    x[h:, :, :] = 0; x[:, w:, :] = 0
    return ((x - MOY) / ECT).transpose(2, 0, 1)[None].astype('float32'), h, w

class PredicteurTorch:
    def __init__(self, modele):
        self.m = modele
    @torch.no_grad()
    def carte(self, img):
        x, h, w = entree(img)
        with torch.autocast(DEV, dtype=torch.float16, enabled=DEV == 'cuda'):
            lg = self.m(torch.from_numpy(x).to(DEV))
        return torch.sigmoid(lg.float())[0, 0, :(h + 3) // 4, :(w + 3) // 4]

class PredicteurOnnx:
    def __init__(self, chemin):
        self.s = ort.InferenceSession(chemin, providers=['CPUExecutionProvider'])
        self.n = self.s.get_inputs()[0].name
    def carte(self, img):
        x, h, w = entree(img)
        lg = self.s.run(None, {self.n: x})[0]
        return torch.sigmoid(torch.from_numpy(lg))[0, 0, :(h + 3) // 4, :(w + 3) // 4]

def pics(carte, seuil):
    m = F.max_pool2d(carte[None, None], K_PICS, 1, K_PICS // 2)[0, 0]
    ys, xs = torch.nonzero((carte == m) & (carte >= seuil), as_tuple=True)
    return (np.c_[(xs.cpu().numpy() + 0.5) * STRIDE, (ys.cpu().numpy() + 0.5) * STRIDE],
            carte[ys, xs].float().cpu().numpy())

def compter(det, certains, ignores, rayon):
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

def dans_masque(xy, masque):
    if masque is None or not len(xy):
        return np.ones(len(xy), bool)
    mx, my, mr = masque[0]
    return (xy[:, 0] - mx) ** 2 + (xy[:, 1] - my) ** 2 <= mr ** 2

def lire(nom):
    return np.asarray(Image.open(chemin_image(nom)).convert('RGB'))

def mesurer_tuiles(pred, echantillons):
    acc = {s: [0, 0, 0] for s in SEUILS}; det_tot = {s: 0 for s in SEUILS}; vrais = 0
    for e in echantillons:
        det, sc = pics(pred.carte(lire(e['nom'])), min(SEUILS))
        garde = dans_masque(det, e['masque']); det, sc = det[garde], sc[garde]
        certains = e['pts'][dans_masque(e['pts'], e['masque'])][:, :2]; vrais += len(certains)
        for s in SEUILS:
            det_tot[s] += int((sc >= s).sum())
            for k, v in enumerate(compter(det[sc >= s], certains, e['ign'][:, :2], RAYON_PX)):
                acc[s][k] += v
    return {s: dict(vp=a[0], fp=a[1], fn=a[2], f1=f1(*a), detectes=det_tot[s], reels=vrais) for s, a in acc.items()}

def mesurer_reference(pred, pts_ref, zones, meres_seules=True):
    acc = {s: [0, 0, 0] for s in SEUILS}; parzone = {}
    for _, z in zones.iterrows():
        det, sc = pics(pred.carte(lire(z.image_path)), min(SEUILS))
        dedans = (det[:, 0] >= z.x0) & (det[:, 0] <= z.x1) & (det[:, 1] >= z.y0) & (det[:, 1] <= z.y1)
        det, sc = det[dedans], sc[dedans]
        p = pts_ref[pts_ref.zone_id == z.zone_id]
        certain = (p.type == 'mere') if meres_seules else p.type.isin(['mere', 'rejet'])
        certains, ignores = p[certain][['x', 'y']].to_numpy(), p[~certain][['x', 'y']].to_numpy()
        parzone[z.zone_id] = (sc, len(certains))
        for s in SEUILS:
            for k, v in enumerate(compter(det[sc >= s], certains, ignores, RAYON_PX)):
                acc[s][k] += v
    return {s: dict(vp=a[0], fp=a[1], fn=a[2], f1=f1(*a)) for s, a in acc.items()}, parzone

def mesurer_negatifs(pred, echantillons):
    fp = {s: 0 for s in SEUILS}; arbres = sum(e['n_autres'] for e in echantillons)
    for e in echantillons:
        _, sc = pics(pred.carte(lire(e['nom'])), min(SEUILS))
        for s in SEUILS:
            fp[s] += int((sc >= s).sum())
    return {s: dict(fp=fp[s], arbres=arbres, taux=round(fp[s] / max(arbres, 1), 4)) for s in SEUILS}

def mesurer_validation(pred):
    return dict(plantain=mesurer_tuiles(pred, ECH['val_plantain']), jeunes=mesurer_tuiles(pred, ECH['val_jeunes']),
                mm=mesurer_reference(pred, PTS_MM, ZONES_MM)[0], neg=mesurer_negatifs(pred, ECH['val_negatifs']))

def lignes_choix(m, ep):
    # Règle fixée à l'avance (protocole v4, section 5)
    return [dict(epoque=ep, seuil=s, f1_plantain=m['plantain'][s]['f1'], f1_jeunes=m['jeunes'][s]['f1'], f1_mm=m['mm'][s]['f1'],
                 fp_neg=m['neg'][s]['fp'], taux_fp_neg=m['neg'][s]['taux'],
                 moyenne=round((m['plantain'][s]['f1'] + m['jeunes'][s]['f1'] + m['mm'][s]['f1']) / 3, 4),
                 eligible=m['neg'][s]['taux'] <= 0.05) for s in SEUILS]

def meilleur(lignes):
    el = [r for r in lignes if r['eligible']]
    return max(el, key=lambda r: r['moyenne']) if el else min(lignes, key=lambda r: (r['taux_fp_neg'], -r['moyenne']))
""")

md("## 6. Essai rapide")
code(r"""
rng0 = random.Random(0)
jeu = Tuiles(echantillons_epoque(rng0))
x, y, w = jeu[0]
print('tuile', tuple(x.shape), '| carte', tuple(y.shape), '| pics à 1 :', int((y == 1).sum()))
for nom_l, l in (('plantations', T_PLANT), ('jeunes', T_JEUNES)):
    xj, yj, wj = Tuiles(l)[0]
    print(f'tuile {nom_l} : pics {int((yj == 1).sum())} | part ignorée {round(float((wj == 0).float().mean()), 2)}')
modele = DetecteurCentres().to(DEV)
lot = torch.stack([jeu[i][0] for i in range(4)]).to(DEV)
cib = torch.stack([jeu[i][1] for i in range(4)]).to(DEV); poi = torch.stack([jeu[i][2] for i in range(4)]).to(DEV)
with torch.autocast(DEV, dtype=torch.float16, enabled=DEV == 'cuda'):
    sortie = modele(lot)
perte = perte_focale(sortie, cib, poi); perte.backward()
print('sortie', tuple(sortie.shape), '| perte', round(float(perte.detach()), 3), '| gradients finis :',
      all(torch.isfinite(p.grad).all() for p in modele.parameters() if p.grad is not None))
e = ECH['val_plantain'][0]; img = lire(e['nom'])
parfaite = torch.from_numpy(carte_cible(e['pts'], img.shape[0], img.shape[1])).to(DEV)
det, _ = pics(parfaite, 0.5)
print('carte parfaite (plantain) :', compter(det, e['pts'][:, :2], np.zeros((0, 2)), RAYON_PX), 'pour', len(e['pts']), 'plants')
V3 = PredicteurOnnx(ONNX_V3)
c3 = V3.carte(img); print('v3 ONNX : carte', tuple(c3.shape), 'pour une image', img.shape[:2])
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
                parts='autres 30 %, plantations 20 %, ReforesTree 20 %, jeunes bananiers 10 %, sans bananier au plus 20 %',
                rep_plantations=REP_PLANT, rep_reforestree=REP_RT, rep_jeunes=REP_JEUNES, n_negatifs_par_epoque=N_NEG)
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
        somme += float(perte.detach()); n += 1
    modele.eval()
    lignes = lignes_choix(mesurer_validation(PredicteurTorch(modele)), ep)
    HISTO += lignes
    eligibles = [r for r in lignes if r['eligible']]
    be = max(eligibles, key=lambda r: r['moyenne']) if eligibles else None
    if be and (MEILLEUR is None or be['moyenne'] > MEILLEUR['moyenne']):
        MEILLEUR = be; torch.save(modele.state_dict(), f'{SORTIE}/meilleur.pt')
    if MEILLEUR is None:
        bf = min(lignes, key=lambda r: (r['taux_fp_neg'], -r['moyenne']))
        if REPLI is None or (bf['taux_fp_neg'], -bf['moyenne']) < (REPLI['taux_fp_neg'], -REPLI['moyenne']):
            REPLI = bf; torch.save(modele.state_dict(), f'{SORTIE}/repli.pt')
    b = max(lignes, key=lambda r: r['moyenne'])
    print(f"époque {ep:2d} : perte {somme / max(n, 1):.3f} | {(time.time() - t0) / 60:.1f} min | meilleur seuil {b['seuil']} : "
          f"plantain {b['f1_plantain']:.3f}, jeunes {b['f1_jeunes']:.3f}, MM {b['f1_mm']:.3f}, moyenne {b['moyenne']:.3f}, "
          f"sans bananier {b['taux_fp_neg']:.1%} | retenu : "
          f"{'époque ' + str(MEILLEUR['epoque']) + ' seuil ' + str(MEILLEUR['seuil']) + ' (' + str(MEILLEUR['moyenne']) + ')' if MEILLEUR else 'aucun couple éligible'}",
          flush=True)
    if (time.time() - debut) / 3600 > REGLAGES['duree_max_h']:
        print('Durée maximale atteinte : arrêt propre', flush=True); break
pd.DataFrame(HISTO).to_csv(f'{SORTIE}/choix.csv', index=False)
if MEILLEUR is None:
    print('Aucun couple sous 5 % de fausses détections : repli du protocole (le moins de fausses détections)')
    MEILLEUR = REPLI; shutil.copy(f'{SORTIE}/repli.pt', f'{SORTIE}/meilleur.pt')
print('Retenu (v4) :', MEILLEUR)
""")

md("## 8. Adoption : v3 mesuré sur la même validation (avant tout test)")
code(r"""
t0 = time.time()
V3_VAL = lignes_choix(mesurer_validation(V3), 'v3')
V3_RETENU = meilleur(V3_VAL)
pd.DataFrame(V3_VAL).to_csv(f'{SORTIE}/choix_v3.csv', index=False)
print(f"v3 sur la validation v4 ({(time.time() - t0) / 60:.1f} min) : meilleur seuil {V3_RETENU['seuil']} : plantain {V3_RETENU['f1_plantain']:.3f}, "
      f"jeunes {V3_RETENU['f1_jeunes']:.3f}, MM {V3_RETENU['f1_mm']:.3f}, moyenne {V3_RETENU['moyenne']:.3f}, sans bananier {V3_RETENU['taux_fp_neg']:.1%}")
print(f"v4 retenu : époque {MEILLEUR['epoque']}, seuil {MEILLEUR['seuil']}, moyenne {MEILLEUR['moyenne']:.3f}")
ADOPTE = MEILLEUR['moyenne'] > V3_RETENU['moyenne']
print('Règle d\'adoption (moyenne v4 strictement meilleure que v3) :', 'REMPLIE : le v4 remplace le v3' if ADOPTE else 'NON REMPLIE : le v3 reste en place (seuil 0,20)')
""")

md("## 9. Test (une seule fois, v3 et v4), export ONNX et vérification")
code(r"""
modele.load_state_dict(torch.load(f'{SORTIE}/meilleur.pt', map_location=DEV)); modele.eval()
V4 = PredicteurTorch(modele)
SEUIL = {'v4': MEILLEUR['seuil'], 'v3': 0.20}           # v3 : seuil de son protocole
TESTS = {}
for nom_m, pred in (('v4', V4), ('v3', V3)):
    s = SEUIL[nom_m]; t0 = time.time()
    dense = mesurer_tuiles(pred, ECH['test_dense'])[s]; espace = mesurer_tuiles(pred, ECH['test_espace'])[s]
    cg_m, parzone = mesurer_reference(pred, PTS_CG, ZONES_CG, True); cg_t, _ = mesurer_reference(pred, PTS_CG, ZONES_CG, False)
    neg = mesurer_negatifs(pred, ECH['test_negatifs'])[s]
    TESTS[nom_m] = dict(seuil=s, dense=dense, espace=espace, cg_meres=cg_m[s], cg_tous=cg_t[s], sans_bananier=neg,
                        comptes_cg={z: dict(detectes=int((sc >= s).sum()), meres=n_) for z, (sc, n_) in parzone.items()})
    def pr(t):
        return t['vp'] / max(t['vp'] + t['fp'], 1), t['vp'] / max(t['vp'] + t['fn'], 1)
    if ESSAI:                                   # essai local : le test tourne (vérification du code) mais n'est pas affiché
        print(f"--- {nom_m} : test calculé (résultats masqués en essai local)"); continue
    print(f"--- {nom_m} (seuil {s}, {(time.time() - t0) / 60:.1f} min)")
    for lib, t in (('dense (segmento est)', dense), ('espacée (banana_tree_detection)', espace)):
        p_, r_ = pr(t)
        print(f"  {lib} : précision {p_:.3f}, rappel {r_:.3f}, F1 {t['f1']:.3f} ; {t['detectes']} détectés pour {t['reels']} annotés")
    for lib, t in (('CG mères seules', cg_m[s]), ('CG tous pieds', cg_t[s])):
        p_, r_ = pr(t)
        print(f"  {lib} : précision {p_:.3f}, rappel {r_:.3f}, F1 {t['f1']:.3f}")
    print(f"  sans bananier : {neg['fp']} fausses détections pour {neg['arbres']} arbres ({neg['taux']:.1%})")

if not ESSAI:
    !pip install -q --timeout 20 --retries 1 onnx
cpu =DetecteurCentres(); cpu.load_state_dict(torch.load(f'{SORTIE}/meilleur.pt', map_location='cpu')); cpu.eval()
chemin_onnx = f'{SORTIE}/centres_5cm_v4.onnx'
try:
    torch.onnx.export(cpu, torch.randn(1, 3, 512, 512), chemin_onnx, input_names=['image'], output_names=['logits'], opset_version=17,
                      dynamic_axes={'image': {2: 'h', 3: 'l'}, 'logits': {2: 'h4', 3: 'l4'}}, dynamo=False)
    xin, _, _ = entree(lire(ZONES_MM.image_path.iloc[0]))
    ref = cpu(torch.from_numpy(xin)).detach().numpy()
    sess = ort.InferenceSession(chemin_onnx, providers=['CPUExecutionProvider'])
    t0 = time.time(); out = sess.run(None, {'image': xin})[0]; duree = time.time() - t0
    ha = xin.shape[2] * xin.shape[3] * 0.05 ** 2 / 1e4
    print(f"ONNX : écart maximal {np.abs(out - ref).max():.2e} ; {os.path.getsize(chemin_onnx) / 1e6:.0f} Mo ; {duree / ha:.0f} s par hectare")
except Exception as e:
    print('Export ONNX impossible ici :', e)
json.dump(dict(versions=VERSIONS, reglages=REGLAGES, retenu=MEILLEUR, seuil=MEILLEUR['seuil'],
               adoption=dict(v3_sur_validation_v4=V3_RETENU, v4=MEILLEUR, adopte=bool(ADOPTE)), tests=TESTS,
               normalisation=dict(moyenne=MOY.tolist(), ecart_type=ECT.tolist()), entree='RGB 0-255 / 255, normalisé, NCHW',
               sortie='logits au quart de la résolution ; sigmoïde puis maxima locaux (fenêtre k_pics) au-dessus du seuil',
               regle='protocole docs/protocole_comptage_v4.md : couple (époque, seuil) maximisant la moyenne des F1 plantain 100_metros, '
                     'jeunes bananiers dji_0544 et MM1-MM2 (mères seules), fausses détections sans bananier <= 5 % des arbres ; '
                     'adoption si moyenne strictement meilleure que le v3 sur la même validation ; test regardé une fois'),
          open(f'{SORTIE}/centres_5cm_v4.json', 'w'), indent=2, ensure_ascii=False, default=float)
print(sorted(os.listdir(SORTIE)))
""")

md("""
## 10. Ensuite, sur ton ordinateur

Télécharge `centres_5cm_v4.onnx`, `centres_5cm_v4.json` et `choix.csv`. Si la règle d'adoption est remplie, range les deux premiers dans `Field-Scan/modeles/` ; la configuration sera passée au v4 et la fourchette du bulletin remesurée sur la validation. Aucun réglage ne change après le test.
""")


def main():
    nb = dict(cells=CELLULES, metadata=dict(kernelspec=dict(display_name="Python 3", language="python", name="python3"),
                                            language_info=dict(name="python")), nbformat=4, nbformat_minor=5)
    for c in nb["cells"]:
        texte = c["source"]
        c["source"] = [l + "\n" for l in texte.split("\n")[:-1]] + [texte.split("\n")[-1]]
    out = Path(__file__).resolve().parents[1] / "notebooks" / "entrainer_centres_v4_kaggle.ipynb"
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Carnet écrit : {out}")


if __name__ == "__main__":
    main()
