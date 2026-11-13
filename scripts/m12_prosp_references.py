#!/usr/bin/env python3
"""Nuit du 12/11 (D-maladies) : empreintes de référence de TOUS nos jeux de feuilles, pour le contrôle de fuite
des jeux neufs. Aucun modèle.

Réutilise, en lecture seule, deux caches déjà calculés (même méthode : image réduite à 256 px de petit côté,
dHash 64 bits et vignette 16 x 16 couleur) :
  - out/maladies/equipe/evaluateur/test_de_loin/references_fuites.npz (index des feuilles : Tanzanie 2021,
    Tanzanie 2022-2023 sur place, Pérou, BananaLSD ; Banana Disease Recognition ; khadavy, TDTU ; test khadavy ;
    zips Roboflow sauf banana_buddy et roamer_feuilles_leaf_segmentation) ;
  - out/maladies/roboflow_nouveaux/fuite_tanzanie_complete/references_tanzanie_2022_complete.npz (Tanzanie 2022-2023
    complète).
Et calcule les jeux absents de ces caches : banana_buddy, roamer_feuilles_leaf_segmentation, test banana_buddy,
photos de loin du robot, Mendeley wfzpdmc5vx, Éthiopie, PSFD-Musa, BanSpot, BananaLSD brut, Tanzanie brute
(healthy_1), Pérou et zips tanzaniens bruts non lus (data/raw/zips, hors Pérou déjà dans l'index).
Le SHA-256 de chaque fichier calculé est gardé.

Sortie : data/raw/nuit_1112/_controle/references_extra.npz (cle, h, v, sha, source).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_prosp_references.py
"""
import hashlib
import io
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageFile, ImageOps

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
from preparer_feuilles import dhash, vignette  # noqa: E402

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None
EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff")
SORTIE = RACINE / "data/raw/nuit_1112/_controle"


def reduire_vite(donnees, cote=256):
    im = Image.open(io.BytesIO(donnees))
    if im.format == "JPEG":
        im.draft("RGB", (cote * 2, cote * 2))
    im = ImageOps.exif_transpose(im).convert("RGB")
    r = cote / min(im.size)
    return im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS) if r < 1 else im


def empreinte(donnees):
    try:
        im = reduire_vite(donnees)
        return hashlib.sha256(donnees).hexdigest(), dhash(im), vignette(im)
    except Exception:
        return hashlib.sha256(donnees).hexdigest(), None, None


def taches():
    """(clé, source, lecteur) pour chaque image à calculer."""
    out = []
    zips = {
        "banana_buddy": RACINE / "data/roboflow_maladies/nouveaux/banana_buddy.zip",
        "roamer_feuilles_leaf_segmentation": RACINE / "data/roboflow_maladies/nouveaux/roamer_feuilles_leaf_segmentation.zip",
    }
    for src, z in zips.items():
        with zipfile.ZipFile(z) as zz:
            out += [(f"z|{z}::{n}", src) for n in zz.namelist() if n.lower().endswith(EXT)]
    for z in sorted((RACINE / "data/raw/zips").glob("*.zip")):
        if z.name == "perou_2026.zip" or z.name == "ethiopie_2021.zip":
            continue  # Pérou : dans l'index ; Éthiopie : lue extraite
        with zipfile.ZipFile(z) as zz:
            out += [(f"z|{z}::{n}", f"tanzanie_zip/{z.stem}") for n in zz.namelist() if n.lower().endswith(EXT)]
    dossiers = {
        "test_banana_buddy": RACINE / "data/test_banana_buddy/images",
        "roamer_dev_loin": RACINE / "data/roamer_dev_loin_feuilles",
        "roamer_val_loin": RACINE / "data/roamer_val_loin_feuilles",
        "roamer_recadrages_v7": RACINE / "data/roamer_recadrages_v7",
        "demo_feuilles": RACINE / "data/demo_feuilles",
        "mendeley_wfzpdmc5vx": RACINE / "data/raw/mendeley_wfzpdmc5vx/fichiers",
        "ethiopie_2021": RACINE / "data/raw/ethiopie_2021/resized",
        "psfd_musa": RACINE / "data/raw/psfd_musa/extrait",
        "banspot": RACINE / "data/raw/banspot",
        "bananalsd_brut": RACINE / "data/raw/bananalsd",
        "tanzanie_brut_2021": RACINE / "data/raw/tanzania_2021",
        "tanzanie_brut_2022": RACINE / "data/raw/tanzania_2022",
        "bdr_brut": RACINE / "data/raw/banana_disease_recognition/extrait",
    }
    for src, d in dossiers.items():
        out += [(f"f|{c}", src) for c in sorted(d.rglob("*")) if c.is_file() and c.suffix.lower() in EXT]
    return out


def lire(cle):
    k, chemin = cle.split("|", 1)
    if k == "f":
        return Path(chemin).read_bytes()
    z, n = chemin.split("::", 1)
    with zipfile.ZipFile(z) as zz:
        return zz.read(n)


def travail(lot):
    res = []
    zcache = {}
    for cle in lot:
        k, chemin = cle.split("|", 1)
        if k == "z":
            z, n = chemin.split("::", 1)
            if z not in zcache:
                zcache[z] = zipfile.ZipFile(z)
            d = zcache[z].read(n)
        else:
            d = Path(chemin).read_bytes()
        res.append(empreinte(d))
    return res


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    t = taches()
    print(f"{len(t)} images à calculer", flush=True)
    cles = [c for c, _ in t]
    lots = [cles[i:i + 200] for i in range(0, len(cles), 200)]
    sha, h, v = [], [], []
    with ProcessPoolExecutor(8) as ex:
        for i, r in enumerate(ex.map(travail, lots)):
            for s, hh, vv in r:
                sha.append(s); h.append(hh); v.append(vv if vv is not None else np.zeros((16, 16, 3), np.int16))
            if i % 10 == 0:
                print(f"  {len(sha)}/{len(cles)}", flush=True)
    ok = np.array([x is not None for x in h])
    np.savez_compressed(SORTIE / "references_extra.npz", cle=np.array(cles), source=np.array([s for _, s in t]),
                        sha=np.array(sha), h=np.array([x if x is not None else 0 for x in h], dtype=object),
                        v=np.stack(v).astype(np.int16), lisible=ok)
    print(f"fini : {len(cles)} images, {int((~ok).sum())} illisibles")


if __name__ == "__main__":
    main()
