#!/usr/bin/env python3
"""A1 PlantVillage / Penn State (`bxw-leaf`, 407 photos) : contrôle de fuite. Aucun modèle.

Règles : `docs/journee_2026-11-15/avenant_jeux_neufs.md` (règles communes et section A1) ; règle de retrait écrite
avant le contrôle dans `docs/journee_2026-11-16/journal_a1.md` (0 h 45).

Références (lecture seule) :
  R1  out/jeux_neufs_1511/a2_fuites/references_dhash.npz (15/11) : data/raw/* (sauf plantain_ghana_m2),
      data/roboflow*, data/drone/*, data/test_* ; clés, tailles, dHash, vignettes ;
  R2  data/raw/nuit_1112/_controle/references_extra.npz (12/11) : jeux de feuilles, dont roamer et demo_feuilles,
      avec SHA-256 ;
  R3  calculé ici : data/feuilles*, data/roamer_*, data/demo_feuilles et les dossiers de data/raw absents de R1
      (hors plantvillage_psu) ; dHash, vignette, SHA-256 ;
  L   data/raw/partage_binome_v10b/partage_corentin_2026-11-11/liste_apprentissage_v10.csv : SHA-256 des originaux
      et des copies 448 px, noms d'origine (dont godliver, cm8zf62kzh, BLADE, absents de ce PC) ;
  I   out/prospection_nuit_1311/index_noms_locaux.json : noms normalisés.

Critères : SHA-256 ; nom normalisé (nom publié et nom d'origine du XML) ; dHash 64 bits ≤ 6 sous les 8 symétries
d'A1 (vignette 16 x 16 rapportée pour information, seuil de confirmation 5 sur 255). Plus : doublons internes
A1-test / A1-appr (dHash ≤ 6).

    ... -I -u scripts/a1_fuites.py references   # R3 (2 processus)
    ... -I -u scripts/a1_fuites.py comparer
"""
import collections
import csv
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
sys.stdout.reconfigure(encoding="utf-8")

A1 = RACINE / "data/raw/plantvillage_psu/extrait"
OUT = RACINE / "out/jeux_neufs_1611/a1_fuites"
R1 = RACINE / "out/jeux_neufs_1511/a2_fuites/references_dhash.npz"
R2 = RACINE / "data/raw/nuit_1112/_controle/references_extra.npz"
R3 = OUT / "references_complement.npz"
LISTE = RACINE / "data/raw/partage_binome_v10b/partage_corentin_2026-11-11/liste_apprentissage_v10.csv"
INDEX = RACINE / "out/prospection_nuit_1311/index_noms_locaux.json"
DECOUPAGE = RACINE / "out/jeux_neufs_1611/a1_decoupage.csv"
EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
SEUIL_DH, SEUIL_VIG = 6, 5.0
PROCESSUS = 2
MAX_PX = 150_000_000
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


def norm(n):
    """Normalisation de l'index des noms (même code que scripts/jeux_neufs_a2_fuites.py)."""
    b = os.path.basename(n.replace("\\", "/")).lower()
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


def empreintes(donnees):
    try:
        im = Image.open(io.BytesIO(donnees))
        if im.width * im.height > MAX_PX:
            return "grande"
        if im.format in ("JPEG", "MPO"):
            im.draft("RGB", (128, 128))
        im = im.convert("RGB")
        return dhash(im), vignette(im)
    except Exception:
        return None


# ---------------------------------------------------------------- références R3
def racines_r3():
    d = np.load(R1, allow_pickle=False)
    deja = {"/".join(str(c).split("::")[0].split("/")[:3]) for c in d["cle"]}
    rs = sorted(RACINE.glob("data/feuilles*")) + sorted(RACINE.glob("data/roamer_*")) + [RACINE / "data/demo_feuilles"]
    for p in sorted((RACINE / "data/raw").iterdir()):
        rel = p.relative_to(RACINE).as_posix()
        if p.is_dir() and p.name != "plantvillage_psu" and rel not in deja:
            rs.append(p)
    return [p for p in rs if p.exists()]


def traiter(racine):
    rel = lambda p: p.relative_to(RACINE).as_posix()
    C, S, H, V, G, I = [], [], [], [], [], []

    def ajouter(cle, donnees):
        e = empreintes(donnees)
        if e == "grande":
            G.append(cle); e = None
        elif e is None:
            I.append(cle)
        C.append(cle); S.append(hashlib.sha256(donnees).hexdigest())
        H.append(e[0] if e else -1); V.append(e[1] if e else np.zeros((16, 16, 3), np.int16))

    fichiers = [racine] if racine.is_file() else [Path(dp) / f for dp, _, fs in os.walk(racine) for f in fs]
    for p in fichiers:
        ext = p.suffix.lower()
        if ext in EXT:
            ajouter(rel(p), p.read_bytes())
        elif ext == ".zip":
            try:
                z = zipfile.ZipFile(p)
            except Exception:
                I.append(rel(p)); continue
            with z:
                for m in z.infolist():
                    if not m.is_dir() and Path(m.filename).suffix.lower() in EXT:
                        try:
                            ajouter(f"{rel(p)}::{m.filename}", z.read(m))
                        except Exception:
                            I.append(f"{rel(p)}::{m.filename}")
    return rel(racine), C, S, H, V, G, I


def references():
    OUT.mkdir(parents=True, exist_ok=True)
    rs = racines_r3()
    print("R3 :", [r.relative_to(RACINE).as_posix() for r in rs], flush=True)
    t0 = time.time()
    C, S, H, V, G, I = [], [], [], [], [], []
    with ProcessPoolExecutor(PROCESSUS) as ex:
        for nom, c, s, h, v, g, i in ex.map(traiter, rs):
            C += c; S += s; H += h; V += v; G += g; I += i
            print(f"  {nom} : {len(c)} images ({time.time() - t0:.0f} s)", flush=True)
    np.savez_compressed(R3, cle=np.array(C), sha=np.array(S),
                        h=np.array([x if x >= 0 else 0 for x in H], np.uint64), ok=np.array([x >= 0 for x in H]),
                        v=np.array(V, np.int16), grandes=np.array(G), illisibles=np.array(I))
    print(f"R3 : {len(C)} images, {len(G)} trop grandes, {len(I)} illisibles", flush=True)


# ---------------------------------------------------------------- comparaison
def symetries(im):
    out = []
    for miroir in (False, True):
        b = im.transpose(Image.FLIP_LEFT_RIGHT) if miroir else im
        for k in range(4):
            out.append(b.rotate(90 * k, expand=True) if k else b)
    return out


def a1_empreintes(chemin):
    im = Image.open(chemin)
    im.draft("RGB", (256, 256))
    im = im.convert("RGB")
    return [(dhash(s), vignette(s)) for s in symetries(im)]


def sha_fichier(source):
    if isinstance(source, bytes):
        return hashlib.sha256(source).hexdigest()
    h = hashlib.sha256()
    with open(source, "rb") as fh:
        for bloc in iter(lambda: fh.read(1 << 22), b""):
            h.update(bloc)
    return h.hexdigest()


def comparer():
    dec = {l["nom"]: l for l in csv.DictReader(open(DECOUPAGE, encoding="utf-8"))}
    man = {l["nom"]: l for l in csv.DictReader(open(A1 / "manifeste.csv", encoding="utf-8"))}
    noms = sorted(dec)
    sha_a1 = {n: man[n]["sha256"] for n in noms}
    tailles_a1 = {int(man[n]["taille"]) for n in noms}

    # références (dHash + clés)
    d1 = np.load(R1, allow_pickle=False)
    d2 = np.load(R2, allow_pickle=True)   # cache produit par scripts/m12_prosp_references.py (le nôtre)
    d3 = np.load(R3, allow_pickle=False)
    k2 = np.array([str(c).split("Field-Scan\\", 1)[-1].replace("\\", "/") for c in d2["cle"]])
    cles = np.concatenate([d1["cle"].astype(str), np.char.add("R2|", k2), d3["cle"].astype(str)])
    H = np.concatenate([d1["h"], np.array([int(x) for x in d2["h"]], np.uint64), d3["h"]])
    ok = np.concatenate([d1["ok"], d2["lisible"], d3["ok"]])
    V = np.concatenate([d1["v"], d2["v"], d3["v"]]).astype(np.float32)
    print(f"références : R1 {len(d1['cle'])}, R2 {len(k2)}, R3 {len(d3['cle'])} ; sans dHash {(~ok).sum()}", flush=True)

    # 1. SHA-256
    lst = list(csv.DictReader(open(LISTE, encoding="utf-8")))
    sha_ref = collections.defaultdict(set)
    for l in lst:
        sha_ref[l["sha256_origine"]].add(f"v10:{l['jeu']}:{l['fichier_origine']}")
        sha_ref[l["sha256_copie_448"]].add(f"v10_448:{l['jeu']}:{l['fichier_origine']}")
    for c, s in zip(k2, d2["sha"]):
        sha_ref[str(s)].add("R2|" + c)
    for c, s in zip(d3["cle"], d3["sha"]):
        sha_ref[str(s)].add(str(c))
    meme_taille = [i for i, t in enumerate(d1["taille"]) if int(t) in tailles_a1]
    for i in meme_taille:
        c = str(d1["cle"][i])
        if "::" in c:
            z, m = c.split("::", 1)
            with zipfile.ZipFile(RACINE / z) as zf:
                s = sha_fichier(zf.read(m))
        else:
            s = sha_fichier(RACINE / c)
        sha_ref[s].add(c)
    sha_hits = [(n, sorted(sha_ref[s])) for n, s in sha_a1.items() if s in sha_ref]
    sha_internes = [g for g in collections.Counter(sha_a1.values()).items() if g[1] > 1]
    print(f"SHA-256 : {len(sha_ref)} empreintes de référence ({len(meme_taille)} de R1 hachées), "
          f"{len(sha_hits)} égalités ; doublons exacts internes {len(sha_internes)}", flush=True)

    # 2. noms (publié et d'origine du XML)
    cand = {}
    for n in noms:
        cand.setdefault(norm(n), set()).add(n)
        if dec[n]["nom_xml"]:
            cand.setdefault(norm(dec[n]["nom_xml"]), set()).add(n)
    nom_hits = collections.defaultdict(set)
    for c in cles:
        k = norm(str(c).split("::")[-1])
        if k in cand:
            for n in cand[k]:
                nom_hits[n].add(str(c))
    for l in lst:
        for champ in ("nom_origine", "fichier_origine"):
            k = norm(l[champ])
            if k in cand:
                for n in cand[k]:
                    nom_hits[n].add(f"v10:{l['jeu']}:{l['fichier_origine']}")
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    for k, srcs in idx.items():
        if k in cand:
            for n in cand[k]:
                nom_hits[n].update(f"index:{s}" for s in srcs)
    mots = collections.Counter("/".join(str(c).split("::")[0].split("/")[:3]) for c in cles
                               if re.search(r"bxw|xanthomonas|wilt_bact|bacterial", str(c), re.I))
    mots_v10 = collections.Counter(l["jeu"] for l in lst if re.search(r"bxw|bbw|xanth|bacterial", l["fichier_origine"], re.I))
    print(f"noms : {len(nom_hits)} photos A1 avec un nom commun ; « bxw » etc. dans les chemins : {dict(mots)} ; "
          f"v10 : {dict(mots_v10)}", flush=True)

    # 3. dHash sous 8 symétries
    Hr, Vr, Cr = H[ok], V[ok], cles[ok]
    emp = {n: a1_empreintes(A1 / "bxw-leaf" / n) for n in noms}
    paires, proches = {}, []
    for n in noms:
        best = (99, None, None)
        for h, v in emp[n]:
            dist = np.bitwise_count(Hr ^ np.uint64(h))
            for j in np.nonzero(dist <= SEUIL_DH)[0]:
                ecart = float(np.abs(Vr[j] - v).mean())
                k = (n, str(Cr[j]))
                x = dict(a1=n, ref=str(Cr[j]), dhash=int(dist[j]), vignette=round(ecart, 2), confirme=ecart <= SEUIL_VIG)
                if k not in paires or (x["dhash"], x["vignette"]) < (paires[k]["dhash"], paires[k]["vignette"]):
                    paires[k] = x
            j = int(dist.argmin())
            if dist[j] < best[0]:
                best = (int(dist[j]), str(Cr[j]), float(np.abs(Vr[j] - v).mean()))
        proches.append(dict(a1=n, role=dec[n]["role"], dist_min=best[0], ref=best[1], vignette=round(best[2], 2)))
    paires = sorted(paires.values(), key=lambda x: (x["a1"], x["dhash"]))
    print(f"dHash ≤ {SEUIL_DH} : {len(paires)} paires, {sum(x['confirme'] for x in paires)} confirmées", flush=True)

    # 4. doublons internes (A1 contre A1, sous symétries)
    h0 = np.array([emp[n][0][0] for n in noms], np.uint64)
    v0 = np.array([emp[n][0][1] for n in noms], np.float32)
    internes = {}
    for i, n in enumerate(noms):
        for h, v in emp[n]:
            dist = np.bitwise_count(h0 ^ np.uint64(h))
            for j in np.nonzero(dist <= SEUIL_DH)[0]:
                if j == i:
                    continue
                a, b = sorted((n, noms[j]))
                x = dict(a=a, b=b, role_a=dec[a]["role"], role_b=dec[b]["role"], dhash=int(dist[j]),
                         vignette=round(float(np.abs(v0[j] - v).mean()), 2))
                if (a, b) not in internes or x["dhash"] < internes[(a, b)]["dhash"]:
                    internes[(a, b)] = x
    internes = sorted(internes.values(), key=lambda x: (x["a"], x["b"]))
    croisees = [x for x in internes if x["role_a"] != x["role_b"]]
    print(f"internes : {len(internes)} paires, dont {len(croisees)} entre A1-test et A1-appr", flush=True)

    # 5. retraits d'A1-test
    motifs = collections.defaultdict(list)
    for n, refs in sha_hits:
        motifs[n].append("sha256")
    for n in nom_hits:
        motifs[n].append("nom")
    for x in paires:
        if "dhash" not in motifs[x["a1"]]:
            motifs[x["a1"]].append("dhash")
    for x in croisees:
        t = x["a"] if x["role_a"] == "A1-test" else x["b"]
        if "interne_appr" not in motifs[t]:
            motifs[t].append("interne_appr")
    for (s, k) in sha_internes:   # copies exactes internes : comme les croisées si entre moitiés
        grp = [n for n in noms if sha_a1[n] == s]
        if len({dec[n]["role"] for n in grp}) > 1:
            for n in grp:
                if dec[n]["role"] == "A1-test" and "interne_appr" not in motifs[n]:
                    motifs[n].append("interne_appr")
    roles = []
    for n in noms:
        r = dec[n]["role"]
        m = motifs.get(n, [])
        final = "retiree_fuite" if (r == "A1-test" and m) else r
        roles.append(dict(nom=n, lot=dec[n]["lot"], pays=dec[n]["pays"], role_avenant=r, role_final=final,
                          motifs=";".join(m)))
    OUT.mkdir(parents=True, exist_ok=True)
    with open(RACINE / "out/jeux_neufs_1611/a1_roles_finaux.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, list(roles[0])); w.writeheader(); w.writerows(roles)
    with open(OUT / "paires_dhash.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["a1", "ref", "dhash", "vignette", "confirme"]); w.writeheader(); w.writerows(paires)
    with open(OUT / "plus_proches.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["a1", "role", "dist_min", "ref", "vignette"]); w.writeheader(); w.writerows(proches)
    with open(OUT / "internes.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["a", "b", "role_a", "role_b", "dhash", "vignette"]); w.writeheader(); w.writerows(internes)
    with open(OUT / "noms_communs.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["a1", "ref"])
        for n, rs in sorted(nom_hits.items()):
            for r in sorted(rs):
                w.writerow([n, r])
    with open(OUT / "sha_egalites.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["a1", "ref"])
        for n, rs in sha_hits:
            for r in rs:
                w.writerow([n, r])

    def dossier(c):
        return "/".join(c.split("::")[0].split("/")[:3])

    dist_min = collections.Counter(min(p["dist_min"], 20) for p in proches)
    bilan = dict(
        a1=len(noms), references=dict(R1=int(len(d1["cle"])), R2=int(len(k2)), R3=int(len(d3["cle"])),
                                      sans_dhash=int((~ok).sum()), sha_connus=len(sha_ref),
                                      liste_v10=len(lst), index_noms=len(idx)),
        R3_dossiers=sorted({dossier(str(c)) for c in d3["cle"]}),
        sha_egalites=len(sha_hits), sha_doublons_internes=len(sha_internes),
        noms_communs=len(nom_hits), chemins_bxw=dict(mots), v10_bxw=dict(mots_v10),
        dhash_paires=len(paires), dhash_confirmees=sum(x["confirme"] for x in paires),
        dhash_paires_par_dossier=dict(collections.Counter(dossier(x["ref"]) for x in paires)),
        dhash_confirmees_par_dossier=dict(collections.Counter(dossier(x["ref"]) for x in paires if x["confirme"])),
        a1_avec_paire=len({x["a1"] for x in paires}),
        a1_avec_paire_par_role=dict(collections.Counter(dec[a]["role"] for a in {x["a1"] for x in paires})),
        distance_min_histogramme={str(k): v for k, v in sorted(dist_min.items())},
        internes=len(internes), internes_croisees=len(croisees),
        internes_meme_role=dict(collections.Counter(x["role_a"] for x in internes if x["role_a"] == x["role_b"])),
        retraits=dict(collections.Counter(r["motifs"] for r in roles if r["role_final"] == "retiree_fuite")),
        roles_finaux=dict(collections.Counter(r["role_final"] for r in roles)),
        roles_finaux_pays={f"{a}|{b}": n for (a, b), n in
                           sorted(collections.Counter((r["role_final"], r["pays"]) for r in roles).items())},
        appr_avec_motif=dict(collections.Counter(r["motifs"] for r in roles if r["role_final"] == "A1-appr" and r["motifs"])),
    )
    (OUT / "bilan.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(bilan, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    {"references": references, "comparer": comparer}[sys.argv[1]]()
