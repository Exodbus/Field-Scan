# Field Scan, nuit du 12 au 13 novembre 2026 : M6 (v12c), caractéristiques figées DINOv3 ViT-B lues sur la photo entière
# et sur 4 morceaux (plan, section 4.3). Aucun entraînement ici, aucun score : le carnet écrit des caractéristiques par photo.
# Préparation : photo remise droite, JPEG lu en 896 px, petit côté à 448 px + recadrage carré au centre (BILINEAR), JPEG 95
# (même chaîne que preparer_convnext, taille 448). Vues : photo entière ramenée à 224 px, puis ses 4 quarts de 224 px.
# Par vue : jeton de classe + moyenne des jetons d'image (2 × 768). Sortie : tableau (n, 5, 1536) en 16 bits + index CSV.
import io, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd, torch
from PIL import Image, ImageOps

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "timm>=1.0.20"], check=True)
import timm

E = Path("/kaggle/input")
INDEX, AJOUTS, NUIT = sorted(E.rglob("index.csv"))[0], sorted(E.rglob("images_ajouts.csv"))[0], sorted(E.rglob("nuit.csv"))[0]
LISTES = next(E.rglob("listes_v10b.csv"))
SORTIE = Path("/kaggle/working")
nuit = pd.read_csv(NUIT)
BASE_NUIT = NUIT.parent
if not (BASE_NUIT / nuit.image.iloc[0]).exists():
    trouve = next(E.rglob(Path(nuit.image.iloc[0]).name))
    BASE_NUIT = trouve.parents[len(Path(nuit.image.iloc[0]).parts) - 1]


def fichier(c):
    if c.startswith("data/feuilles/"):
        return str(INDEX.parent / c.removeprefix("data/feuilles/"))
    if c.startswith("data/feuilles_v3_ajouts/"):
        return str(AJOUTS.parent / c.removeprefix("data/feuilles_v3_ajouts/"))
    return str(BASE_NUIT / c)


idx = pd.read_csv(INDEX)
idx = idx[idx.retenue.astype(bool) & idx.chemin.notna() & idx.ensemble.eq("entrainement")]
base = pd.DataFrame(dict(chemin="data/feuilles/" + idx.chemin.values, jeu=idx.source.values, classe_vraie=idx.classe.values))
bd = nuit[nuit.role.eq("apprentissage")]
bd = pd.DataFrame(dict(chemin=bd.image.values, jeu=bd.jeu.values, classe_vraie=bd.classe.values))
L = pd.read_csv(LISTES)
# réglage et apprentissage seulement : aucun juge (BanSpot, Cordana du Pérou) n'est lu par ce carnet
lots = {"reglage": pd.concat([base, bd, L[L.jeu.isin(["validation", "tdtu", "psfd", "ethiopie"])]], ignore_index=True)}
assert not lots["reglage"].jeu.isin(["cordana_perou", "bananalsd"]).any()
assert len(lots["reglage"]) == 16963 + 422 + 3001 + 1636 + 738 + 1289

m = timm.create_model("vit_base_patch16_dinov3.lvd1689m", pretrained=True, num_classes=0, dynamic_img_size=True).cuda().eval()
cfg = m.pretrained_cfg
MOY, ECT = torch.tensor(cfg["mean"]).view(1, 3, 1, 1).cuda(), torch.tensor(cfg["std"]).view(1, 3, 1, 1).cuda()
print("DINOv3 :", cfg.get("hf_hub_id"), "préfixes", m.num_prefix_tokens, "normalisation", cfg["mean"], cfg["std"], flush=True)
torch.save({k: v.half() for k, v in m.state_dict().items()}, SORTIE / "dinov3_vitb16_lvd1689m_16bits.pt")   # pour la lecture locale


def preparer(chemin, taille=448, lecture=896):
    with Image.open(chemin) as im:
        im.draft("RGB", (lecture, lecture))
        im = ImageOps.exif_transpose(im).convert("RGB")
        petite = ImageOps.fit(im, (taille, taille), method=Image.BILINEAR)
    t = io.BytesIO(); petite.save(t, format="JPEG", quality=95)
    return np.asarray(Image.open(t).convert("RGB"), dtype="uint8")


@torch.no_grad()
def caracteristiques(x):
    """x : (b, 3, 448, 448) normalisé -> (b, 5, 1536) : photo entière en 224 px puis 4 quarts."""
    vues = [torch.nn.functional.interpolate(x, size=224, mode="bilinear", antialias=True, align_corners=False),
            x[:, :, :224, :224], x[:, :, :224, 224:], x[:, :, 224:, :224], x[:, :, 224:, 224:]]
    out = []
    for v in vues:
        with torch.autocast("cuda", dtype=torch.float16):
            f = m.forward_features(v.contiguous())
        f = f.float()
        out.append(torch.cat([f[:, 0], f[:, m.num_prefix_tokens:].mean(1)], 1))
    return torch.stack(out, 1)


t0 = time.time()
for nom, df in lots.items():
    fichiers = [fichier(c) for c in df.chemin]
    sorties = []
    with ThreadPoolExecutor(8) as ex:
        for i in range(0, len(fichiers), 64):
            a = np.stack(list(ex.map(preparer, fichiers[i:i + 64])))
            x = torch.from_numpy(a).cuda().permute(0, 3, 1, 2).float().div(255.0)
            sorties.append(caracteristiques((x - MOY) / ECT).cpu().numpy().astype("float16"))
            if i % 3200 == 0:
                print(f"{nom} : {i}/{len(fichiers)} ({(time.time() - t0) / 60:.1f} min)", flush=True)
    np.save(SORTIE / f"caracteristiques_{nom}.npy", np.concatenate(sorties))
    df.to_csv(SORTIE / f"index_{nom}.csv", index=False)
print("fini", sorted(p.name for p in SORTIE.iterdir()), flush=True)
