#!/usr/bin/env python3
"""A2 « plantain du Ghana » : contrôle de fuite (avenant du 15/11, règles communes). Aucun modèle.

Compare les 199 photos d'origine de `data/raw/plantain_ghana_m2/images/` avec nos données :
`data/raw/*` (sauf plantain_ghana_m2), `data/roboflow*`, `data/drone/*`, `data/test_*`, fichiers isolés et membres
des zips, ainsi que l'index `out/prospection_nuit_1311/index_noms_locaux.json`.

Trois critères :
  1. SHA-256 : une égalité exige la même taille ; seuls les fichiers de même taille qu'un original sont hachés ;
  2. nom d'origine normalisé (même normalisation que l'index des noms) ;
  3. dHash 64 bits (définition de scripts/preparer_feuilles.py), A2 sous ses 8 symétries, distance ≤ 6.
     Un dHash proche sur des vues aériennes de végétation donne des coïncidences : chaque paire est confirmée par
     l'écart moyen des vignettes 16 × 16 en couleur (≤ 5 sur 255, méthode de scripts/verifier_jeux_maladies.py).

Étapes :
    ... -I -u scripts/jeux_neufs_a2_fuites.py references   # index des références (cache npz), 2 processus
    ... -I -u scripts/jeux_neufs_a2_fuites.py comparer     # après le téléchargement
"""
import hashlib
import io
import json
import os
import re
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageFile

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.stdout.reconfigure(encoding="utf-8")  # en mode -I, PYTHONIOENCODING est ignoré

A2 = RACINE / "data/raw/plantain_ghana_m2"
OUT = RACINE / "out/jeux_neufs_1511/a2_fuites"
CACHE = OUT / "references_dhash.npz"
INDEX = RACINE / "out/prospection_nuit_1311/index_noms_locaux.json"
EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
SEUIL_DH, SEUIL_VIG = 6, 5.0
PROCESSUS = 2
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None
MAX_PX = 150_000_000           # au-delà (orthomosaïques géantes), pas de dHash : noté à part


def norm(n):
    """Normalisation de l'index des noms (out/prospection_nuit_1311/index_noms_locaux.py)."""
    b = os.path.basename(n).lower()
    b = re.sub(r"_(jpg|jpeg|png)\.rf\.[0-9a-f]+", "", b)
    b = re.sub(r"\.rf\.[0-9a-f]+", "", b)
    b = os.path.splitext(b)[0]
    b = re.sub(r"_(jpg|jpeg|png)$", "", b)
    return re.sub(r"[^0-9a-z]", "", b)


def dhash(im, taille=8):
    g = np.asarray(im.convert("L").resize((taille + 1, taille), Image.BILINEAR), dtype=np.int16)
    bits = (g[:, 1:] > g[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def vignette(im, cote=16):
    return np.asarray(im.convert("RGB").resize((cote, cote), Image.BILINEAR), dtype=np.int16)


def empreintes(source):
    """dHash et vignette d'une image (chemin ou octets). None si illisible ou trop grande."""
    try:
        im = Image.open(source)
        if im.width * im.height > MAX_PX:
            return "grande"
        if im.format in ("JPEG", "MPO"):
            im.draft("RGB", (128, 128))
        im = im.convert("RGB")
        return dhash(im), vignette(im)
    except Exception:
        return None


def sources():
    racines = [p for p in (RACINE / "data/raw").iterdir() if p.is_dir() and p.name != "plantain_ghana_m2"]
    racines += sorted((RACINE / "data").glob("roboflow*")) + sorted((RACINE / "data/drone").iterdir())
    racines += sorted((RACINE / "data").glob("test_*"))
    return [p for p in racines if p.is_dir()]


def traiter_racine(racine):
    """Toutes les images (fichiers isolés et membres de zips) d'un dossier de référence."""
    rel = lambda p: p.relative_to(RACINE).as_posix()
    cles, tailles, hs, vs, grandes, illisibles = [], [], [], [], [], []
    for dp, _, fs in os.walk(racine):
        for f in fs:
            p = Path(dp) / f
            ext = p.suffix.lower()
            if ext in EXT:
                e = empreintes(p)
                cle = rel(p)
                if e == "grande":
                    grandes.append(cle); e = None
                elif e is None:
                    illisibles.append(cle)
                cles.append(cle); tailles.append(p.stat().st_size)
                hs.append(e[0] if e else -1); vs.append(e[1] if e else np.zeros((16, 16, 3), np.int16))
            elif ext == ".zip":
                try:
                    z = zipfile.ZipFile(p)
                except Exception:
                    illisibles.append(rel(p)); continue
                with z:
                    for m in z.infolist():
                        if m.is_dir() or Path(m.filename).suffix.lower() not in EXT:
                            continue
                        cle = f"{rel(p)}::{m.filename}"
                        try:
                            e = empreintes(io.BytesIO(z.read(m)))
                        except Exception:
                            e = None
                        if e == "grande":
                            grandes.append(cle); e = None
                        elif e is None:
                            illisibles.append(cle)
                        cles.append(cle); tailles.append(m.file_size)
                        hs.append(e[0] if e else -1); vs.append(e[1] if e else np.zeros((16, 16, 3), np.int16))
    return rel(racine), cles, tailles, hs, vs, grandes, illisibles


def references():
    OUT.mkdir(parents=True, exist_ok=True)
    rs = sources()
    print(f"{len(rs)} dossiers de référence", flush=True)
    t0 = time.time()
    C, T, H, V, G, I = [], [], [], [], [], []
    with ProcessPoolExecutor(PROCESSUS) as ex:
        for nom, c, t, h, v, g, i in ex.map(traiter_racine, rs):
            C += c; T += t; H += h; V += v; G += g; I += i
            print(f"  {nom} : {len(c)} images ({time.time() - t0:.0f} s)", flush=True)
    np.savez_compressed(CACHE, cle=np.array(C), taille=np.array(T, np.int64),
                        h=np.array([x if x >= 0 else 0 for x in H], np.uint64), ok=np.array([x >= 0 for x in H]),
                        v=np.array(V, np.int16), grandes=np.array(G), illisibles=np.array(I))
    print(f"références : {len(C)} images, {len(G)} trop grandes, {len(I)} illisibles ; {CACHE}", flush=True)


def symetries(im):
    out = []
    for miroir in (False, True):
        b = im.transpose(Image.FLIP_LEFT_RIGHT) if miroir else im
        for k in range(4):
            out.append(b.rotate(90 * k, expand=True) if k else b)
    return out


def a2_empreinte(chemin):
    im = Image.open(chemin)
    im.draft("RGB", (1000, 700))
    im = im.convert("RGB")
    return [(dhash(s), vignette(s)) for s in symetries(im)]


def sha256(source):
    h = hashlib.sha256()
    if isinstance(source, bytes):
        h.update(source)
        return h.hexdigest()
    with open(source, "rb") as fh:
        for bloc in iter(lambda: fh.read(1 << 22), b""):
            h.update(bloc)
    return h.hexdigest()


def comparer():
    d = np.load(CACHE, allow_pickle=False)
    cles, tailles, H, ok, V = d["cle"], d["taille"], d["h"], d["ok"], d["v"]
    imgs = sorted((A2 / "images").glob("*.JPG"))
    sha_a2 = {}
    for l in (A2 / "sha256.txt").read_text(encoding="utf-8").splitlines():
        s, n = l.split("  ", 1)
        sha_a2[Path(n).name] = s
    tailles_a2 = {p.stat().st_size for p in imgs}
    print(f"A2 : {len(imgs)} photos ; références : {len(cles)} images", flush=True)

    # 1. SHA-256 (seulement les références de même taille qu'un original)
    meme_taille = [i for i, t in enumerate(tailles) if int(t) in tailles_a2]
    sha_hits = []
    for i in meme_taille:
        c = str(cles[i])
        if "::" in c:
            z, m = c.split("::", 1)
            with zipfile.ZipFile(RACINE / z) as zf:
                s = sha256(zf.read(m))
        else:
            s = sha256(RACINE / c)
        if s in sha_a2.values():
            sha_hits.append((c, s))
    print(f"SHA-256 : {len(meme_taille)} références de même taille, {len(sha_hits)} égalités", flush=True)

    # 2. noms
    noms_a2 = {norm(p.name): p.name for p in imgs}
    nom_hits = [(str(c), noms_a2[norm(str(c).split("::")[-1])]) for c in cles if norm(str(c).split("::")[-1]) in noms_a2]
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    idx_hits = {k: v for k, v in idx.items() if k in noms_a2}
    mots = [str(c) for c in cles if re.search(r"adabokrom|plantain", str(c), re.I)]
    print(f"noms : {len(nom_hits)} fichiers de même nom ; index : {len(idx_hits)} noms ; "
          f"« adabokrom » ou « plantain » dans {len(mots)} chemins", flush=True)

    # 3. dHash sous 8 symétries + vignette
    Hr = H[ok]; Vr = V[ok].astype(np.float32); Cr = cles[ok]
    dh_hits, proches = [], []
    for p in imgs:
        best = (99, None, None)
        for h, v in a2_empreinte(p):
            dist = np.bitwise_count(Hr ^ np.uint64(h))
            for j in np.nonzero(dist <= SEUIL_DH)[0]:
                ecart = float(np.abs(Vr[j] - v).mean())
                dh_hits.append(dict(a2=p.name, ref=str(Cr[j]), dhash=int(dist[j]), vignette=round(ecart, 2),
                                    confirme=ecart <= SEUIL_VIG))
            j = int(dist.argmin())
            if dist[j] < best[0]:
                best = (int(dist[j]), str(Cr[j]), float(np.abs(Vr[j] - v).mean()))
        proches.append(dict(a2=p.name, dist_min=best[0], ref=best[1], vignette=round(best[2], 2)))
    # une paire par (a2, ref) : la meilleure symétrie
    uniq = {}
    for x in dh_hits:
        k = (x["a2"], x["ref"])
        if k not in uniq or (x["dhash"], x["vignette"]) < (uniq[k]["dhash"], uniq[k]["vignette"]):
            uniq[k] = x
    dh_hits = sorted(uniq.values(), key=lambda x: (x["a2"], x["dhash"]))
    conf = [x for x in dh_hits if x["confirme"]]
    print(f"dHash ≤ {SEUIL_DH} : {len(dh_hits)} paires, {len(conf)} confirmées par la vignette", flush=True)

    def dossier(c):
        return "/".join(c.split("::")[0].split("/")[:3])

    import collections
    bilan = dict(
        a2=len(imgs), references=int(len(cles)), references_sans_dhash=int((~ok).sum()),
        grandes=[str(x) for x in d["grandes"]], illisibles=int(len(d["illisibles"])),
        sha_egalites=sha_hits, sha_meme_taille=len(meme_taille),
        noms_communs=len(nom_hits), noms_communs_par_dossier=dict(collections.Counter(dossier(c) for c, _ in nom_hits)),
        index_noms=len(idx_hits), index_par_source=dict(collections.Counter(s for v in idx_hits.values() for s in v)),
        chemins_adabokrom_plantain=dict(collections.Counter(dossier(c) for c in mots)),
        dhash_paires=len(dh_hits), dhash_confirmees=len(conf),
        dhash_confirmees_par_dossier=dict(collections.Counter(dossier(x["ref"]) for x in conf)),
        dhash_non_confirmees_par_dossier=dict(collections.Counter(dossier(x["ref"]) for x in dh_hits if not x["confirme"])),
        a2_avec_paire_confirmee=len({x["a2"] for x in conf}),
        a2_avec_paire_confirmee_hors_export=len({x["a2"] for x in conf if "plantain_m2" not in x["ref"]}),
    )
    (OUT / "bilan.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
    import csv
    with open(OUT / "paires_dhash.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["a2", "ref", "dhash", "vignette", "confirme"]); w.writeheader(); w.writerows(dh_hits)
    with open(OUT / "plus_proches.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["a2", "dist_min", "ref", "vignette"]); w.writeheader(); w.writerows(proches)
    with open(OUT / "noms_communs.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["ref", "a2"]); w.writerows(nom_hits)
    print(json.dumps({k: v for k, v in bilan.items() if k not in ("grandes",)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    {"references": references, "comparer": comparer}[sys.argv[1]]()
