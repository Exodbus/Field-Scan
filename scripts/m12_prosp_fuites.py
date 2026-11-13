#!/usr/bin/env python3
"""Nuit du 12/11 (D-maladies) : contrôle de fuite des jeux de feuilles neufs. Aucun modèle.

Pour chaque jeu donné (nom=dossier), chaque image :
  - SHA-256 du fichier, comparé à : la liste d'apprentissage de la v10b (photos d'origine et copies en 448 px,
    y compris cm8zf62kzh, BLADE, godliver que nous n'avons pas), data/feuilles/index.csv, et les fichiers de
    références_extra (scripts/m12_prosp_references.py) ;
  - sous ses 8 symétries, dHash 64 bits (au plus 10 bits) puis vignette 16 x 16 (écart moyen au plus 5 sur 255)
    contre toutes nos références (caches existants + références_extra) : méthode de scripts/verifier_jeux_maladies.py ;
  - doublons internes (même méthode, entre images du même jeu) et copies entre jeux neufs.
Sorties dans data/raw/nuit_1112/_controle/ : fuites_<nom>.csv, paires_<nom>.jpg, bilan_fuites.json.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_prosp_fuites.py nom1=dossier1 nom2=dossier2 ...
"""
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageFile

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
from verifier_jeux_maladies import NV, comparer, par_image, planche_paires, variantes  # noqa: E402
from preparer_feuilles import dhash, vignette  # noqa: E402
from m12_prosp_references import reduire_vite, EXT  # noqa: E402

ImageFile.LOAD_TRUNCATED_IMAGES = True
CTRL = RACINE / "data/raw/nuit_1112/_controle"
SH, SV, LIMITE = 10, 5.0, 25.0


def references():
    cles, h, v, src = [], [], [], []
    d = np.load(RACINE / "out/maladies/equipe/evaluateur/test_de_loin/references_fuites.npz", allow_pickle=True)
    for c in d["cle"]:
        c = str(c); p = c.split("|", 1)[1]
        src.append(Path(p.split("::")[0]).stem if "::" in p else "/".join(Path(p).parts[-4:-1]))
    cles += [str(c) for c in d["cle"]]; h += [int(x) for x in d["h"]]; v.append(d["v"].astype(np.int16))
    d = np.load(RACINE / "out/maladies/roboflow_nouveaux/fuite_tanzanie_complete/references_tanzanie_2022_complete.npz",
                allow_pickle=True)
    cles += [f"t|{r}" for r in d["refs"]]; src += ["tanzanie_2022_complete"] * len(d["refs"])
    h += [int(x) for x in d["h"]]; v.append(d["v"].astype(np.int16))
    d = np.load(CTRL / "references_extra.npz", allow_pickle=True)
    ok = d["lisible"]
    cles += [str(c) for c in d["cle"][ok]]; src += [str(s) for s in d["source"][ok]]
    h += [int(x) for x in d["h"][ok]]; v.append(d["v"][ok].astype(np.int16))
    sha_extra = dict(zip(d["sha"], d["source"]))
    return cles, src, h, np.concatenate(v), sha_extra


def shas_connus(sha_extra):
    s = {}
    v10 = pd.read_csv(RACINE / "data/raw/partage_binome_v10b/partage_corentin_2026-11-11/liste_apprentissage_v10.csv")
    for col in ("sha256_origine", "sha256_copie_448"):
        s.update({x: f"v10b/{j}" for x, j in zip(v10[col], v10.jeu)})
    idx = pd.read_csv(RACINE / "data/feuilles/index.csv", usecols=["sha256", "source"])
    s.update({x: f"index/{j}" for x, j in zip(idx.sha256, idx.source) if isinstance(x, str)})
    s.update({k: f"extra/{j}" for k, j in sha_extra.items()})
    return s


def main():
    jeux = [a.split("=", 1) for a in sys.argv[1:]]
    cles, src, rh, rv, sha_extra = references()
    connus = shas_connus(sha_extra)
    print(f"références visuelles : {len(cles)} ; SHA-256 connus : {len(connus)}", flush=True)
    tout = []  # (jeu, chemin)
    for nom, dossier in jeux:
        tout += [(nom, c) for c in sorted(Path(dossier).rglob("*")) if c.is_file() and c.suffix.lower() in EXT]
    hs, vs, h0, v0, sha, tailles = [], [], [], [], [], []
    for i, (nom, c) in enumerate(tout):
        b = c.read_bytes()
        sha.append(hashlib.sha256(b).hexdigest())
        try:
            with Image.open(io.BytesIO(b)) as im0:
                tailles.append(im0.size)
            im = reduire_vite(b)
        except Exception:
            tailles.append((0, 0)); im = Image.new("RGB", (64, 64))
        h0.append(dhash(im)); v0.append(vignette(im))
        for t in variantes(im):
            hs.append(dhash(t)); vs.append(vignette(t))
        if i % 1000 == 0:
            print(f"  {i}/{len(tout)}", flush=True)
    VS, V0 = np.stack(vs).astype(np.int16), np.stack(v0).astype(np.int16)
    m, j = par_image(*comparer(hs, VS, rh, rv, SH, SV)[:2])
    jeu_de = np.array([n for n, _ in tout])
    mi, ji = par_image(*comparer(hs, VS, h0, V0, SH, SV, exclure=lambda i, jj: (i // NV) == jj)[:2])
    df = pd.DataFrame(dict(jeu=jeu_de, chemin=[c.as_posix() for _, c in tout], sha256=sha,
                           largeur=[t[0] for t in tailles], hauteur=[t[1] for t in tailles],
                           sha_connu=[connus.get(s, "") for s in sha],
                           ecart_ref=np.where(np.isfinite(m), np.round(m, 2), np.nan),
                           ref_proche=[cles[k] if k >= 0 else "" for k in j],
                           source_proche=[src[k] if k >= 0 else "" for k in j],
                           ecart_interne=np.where(np.isfinite(mi), np.round(mi, 2), np.nan),
                           double_de=[tout[k][1].as_posix() if k >= 0 else "" for k in ji],
                           jeu_double=[tout[k][0] if k >= 0 else "" for k in ji]))
    df["fuite_visuelle"] = df.ecart_ref <= SV
    df["fuite"] = df.fuite_visuelle | (df.sha_connu != "")
    bilan = {}
    for nom, _ in jeux:
        d = df[df.jeu == nom]
        d.to_csv(CTRL / f"fuites_{nom}.csv", index=False)
        dbl = d[d.ecart_interne <= SV]
        bilan[nom] = dict(images=len(d), sha_connus=int((d.sha_connu != "").sum()),
                          sha_connus_par_source=d[d.sha_connu != ""].sha_connu.value_counts().to_dict(),
                          fuites_visuelles=int(d.fuite_visuelle.sum()),
                          fuites_par_source=d[d.fuite_visuelle].source_proche.value_counts().to_dict(),
                          paires_sous_25=int((d.ecart_ref <= LIMITE).sum()),
                          doublons_internes=int((dbl.jeu_double == nom).sum()),
                          copies_autres_jeux_neufs=dbl[dbl.jeu_double != nom].jeu_double.value_counts().to_dict(),
                          sha_dupliques_internes=int(d.sha256.duplicated().sum()),
                          tailles={f"{a}x{b}": int(k) for (a, b), k in d.groupby(["largeur", "hauteur"]).size()
                                   .sort_values(ascending=False).head(5).items()})
        proches = d[d.ecart_ref <= LIMITE].sort_values("ecart_ref").head(24)
        cz = {}

        def ouvrir_ref(cle):
            k, p = cle.split("|", 1)
            if k == "f":
                return Image.open(p)
            if k == "z":
                z, n = p.split("::", 1)
                cz.setdefault(z, zipfile.ZipFile(z))
                return Image.open(io.BytesIO(cz[z].read(n)))
            return Image.new("RGB", (64, 64), "gray")
        try:
            planche_paires([(Image.open(r.chemin), ouvrir_ref(r.ref_proche), f"{r.ecart_ref:.1f} {r.source_proche}")
                            for r in proches.itertuples()], CTRL / f"paires_{nom}.jpg")
        except Exception as e:
            print("planche impossible", nom, e)
    (CTRL / "bilan_fuites.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(bilan, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
