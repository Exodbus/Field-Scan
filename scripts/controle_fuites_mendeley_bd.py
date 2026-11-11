"""Contrôle des fuites du jeu Mendeley wfzpdmc5vx (Bangladesh : Cordana, Pestalotiopsis, Sigatoka, saines). Aucun modèle.

Chaque image, sous ses 8 symétries, est comparée aux références du contrôle de l'évaluateur
(out/maladies/equipe/evaluateur/test_de_loin/controle_fuites.py : index des feuilles avec tout BananaLSD et le Pérou,
Banana Disease Recognition, ajouts v3 (khadavy, TDTU), test khadavy, zips Roboflow sauf banana_buddy), plus le jeu
banana_buddy lui-même (réservé : une copie y serait aussi à retirer). Même méthode : dHash ≤ 10 bits puis vignette ≤ 5.
Doublons internes cherchés de la même façon. Sorties dans out/maladies/mendeley_bd/.
"""
import importlib.util, json, sys, zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
from verifier_jeux_maladies import comparer, par_image, planche_paires, reduire, variantes, NV  # noqa: E402
from preparer_feuilles import dhash, vignette  # noqa: E402

spec = importlib.util.spec_from_file_location("cf", RACINE / "out/maladies/equipe/evaluateur/test_de_loin/controle_fuites.py")
cf = importlib.util.module_from_spec(spec); spec.loader.exec_module(cf)
SORTIE = RACINE / "out/maladies/mendeley_bd"
SORTIE.mkdir(parents=True, exist_ok=True)
SH, SV, LIMITE = 10, 5.0, 25.0

fichiers = sorted((RACINE / "data/raw/mendeley_wfzpdmc5vx/fichiers").iterdir())
classe = [f.stem.rstrip("0123456789").strip("_- ").lower() for f in fichiers]
items, rh, rv = cf.references()
bb = zipfile.ZipFile(RACINE / "data/roboflow_maladies/nouveaux/banana_buddy.zip")
noms_bb = [n for n in bb.namelist() if n.lower().endswith((".jpg", ".jpeg", ".png"))]
hb, vb = [], []
for n in noms_bb:
    im = reduire(Image.open(bb.open(n)))
    hb.append(dhash(im)); vb.append(vignette(im))
items = items + [("z", f"{bb.filename}::{n}", "banana_buddy (réservé)") for n in noms_bb]
rh, rv = list(rh) + hb, np.concatenate([rv, np.stack(vb).astype(np.int16)])
print("références :", pd.Series([s for *_, s in items]).value_counts().to_dict(), flush=True)

hs, vs, h0, v0 = [], [], [], []
for f in fichiers:
    im = reduire(Image.open(f))
    h0.append(dhash(im)); v0.append(vignette(im))
    for t in variantes(im):
        hs.append(dhash(t)); vs.append(vignette(t))
m, j = par_image(*comparer(hs, np.stack(vs).astype(np.int16), rh, rv, SH, SV)[:2])
# doublons internes : image i (8 symétries) contre les originaux des autres images
mi, ji = par_image(*comparer(hs, np.stack(vs).astype(np.int16), h0, np.stack(v0).astype(np.int16), SH, SV,
                             exclure=lambda i, jj: (i // NV) == jj)[:2])
df = pd.DataFrame(dict(fichier=[f.name for f in fichiers], classe=classe,
                       ecart_min=np.where(np.isfinite(m), np.round(m, 2), np.nan), fuite=m <= SV,
                       reference_proche=[items[k][1] if k >= 0 else "" for k in j],
                       source_proche=[items[k][2] if k >= 0 else "" for k in j],
                       ecart_interne=np.where(np.isfinite(mi), np.round(mi, 2), np.nan),
                       double_de=[fichiers[k].name if k >= 0 else "" for k in ji]))
df.to_csv(SORTIE / "fuites.csv", index=False)
proches = df[df.ecart_min <= LIMITE].sort_values("ecart_min").head(24)
cz = {}
planche_paires([(Image.open(RACINE / "data/raw/mendeley_wfzpdmc5vx/fichiers" / r.fichier),
                 cf.ouvrir_item(*[(k, c) for k, c, _ in items if c == r.reference_proche][0], cz),
                 f"{r.ecart_min:.1f} {r.source_proche}") for r in proches.itertuples()], SORTIE / "paires_proches.jpg")
bilan = dict(images=len(df), classes=df.classe.value_counts().to_dict(), references=len(items),
             fuites=int(df.fuite.sum()), fuites_par_source=df[df.fuite].source_proche.value_counts().to_dict(),
             paires_sous_25=int((df.ecart_min <= LIMITE).sum()),
             doublons_internes=int((df.ecart_interne <= SV).sum()),
             doublons_internes_entre_classes=int(sum(1 for r in df[df.ecart_interne <= SV].itertuples()
                                                    if df.loc[df.fichier == r.double_de, "classe"].iloc[0] != r.classe)))
(SORTIE / "bilan_fuites.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(bilan, ensure_ascii=False, indent=1))
