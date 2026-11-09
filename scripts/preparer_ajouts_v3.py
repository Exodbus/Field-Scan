#!/usr/bin/env python3
"""Ajouts d'entraînement de la v3 (docs/protocole_maladies_v3_convnext.md, sections 2 et 3), sans modèle.

  - khadavy : les 431 photos distinctes figées (data/test_khadavy/liste.csv) ; Sehat -> saine,
    Bercak-Hitam -> black_sigatoka, Bercak-Kuning -> autre_maladie ;
  - TDTU : étiquette d'image = ensemble des classes de ses boîtes ; photos distinctes = groupes de quasi-doublons
    (même méthode que les autres contrôles) ; un groupe aux étiquettes différentes est exclu ; une image par
    groupe, la première par nom ; Healthy seul -> saine ; Black Segatoka (avec ou sans Healthy) ->
    black_sigatoka ; Xanthomonas wilt et/ou Bacterial wilt (avec ou sans Healthy) -> autre_maladie ;
    tout le reste exclu ;
  - fuites : toute image d'ajout proche (écart <= 5, 8 symétries) de la validation tanzanienne 2022-2023
    locale, de BananaLSD ou du test banana-buddy figé est retirée de l'entraînement.

Sorties dans --out : images/<jeu>/<fichier>, images.csv (image, jeu, classe, source, sha256), exclusions.csv,
et l'archive Kaggle --zip (chemins posix). Refuse de réécrire une préparation existante.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/preparer_ajouts_v3.py
"""
import argparse
import hashlib
import io
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
from preparer_feuilles import dhash, vignette  # noqa: E402
from selectionner_test_khadavy import groupes_quasi_doublons, lire_coco  # noqa: E402
from verifier_jeux_maladies import comparer, par_image, reduire, variantes  # noqa: E402

KHADAVY = {"Sehat": "saine", "Bercak-Hitam": "black_sigatoka", "Bercak-Kuning": "autre_maladie"}
FLETRISSEMENTS = {"Xanthomonas wilt", "Bacterial wilt"}


def classe_tdtu(etiquette):
    s = set(etiquette.split("+")) - {"Healthy"}
    if etiquette == "Healthy":
        return "saine"
    if s == {"Black Segatoka"}:
        return "black_sigatoka"
    if s and s <= FLETRISSEMENTS:
        return "autre_maladie"
    return None


def sha(octets):
    return hashlib.sha256(octets).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/feuilles_v3_ajouts")
    ap.add_argument("--zip", default="data/feuilles_v3_ajouts.zip")
    args = ap.parse_args(argv)
    out = RACINE / args.out
    if (out / "images.csv").exists():
        sys.exit(f"{out / 'images.csv'} existe déjà : rien n'est réécrit.")
    exclusions = []

    # khadavy
    k = pd.read_csv(RACINE / "data/test_khadavy/liste.csv")
    k = k[k.jeu.eq("khadavy")]
    lignes = [dict(jeu="khadavy", classe=KHADAVY[r.classe], source=r.image,
                   octets=(RACINE / "data/test_khadavy" / r.fichier).read_bytes(), nom=Path(r.fichier).name)
              for r in k.itertuples()]

    # TDTU
    t, z = lire_coco(RACINE / "data/roboflow_maladies/tdtu_vietnam.zip")
    t["groupe"] = groupes_quasi_doublons(t, z, 10, 5.0)
    n_groupes = t.groupe.nunique()
    contradictoires = t.groupby("groupe").classe.nunique()
    contradictoires = set(contradictoires[contradictoires > 1].index)
    for g in contradictoires:
        exclusions.append(dict(jeu="tdtu", groupe=g, motif="etiquettes_contradictoires"))
    t = t[~t.groupe.isin(contradictoires)].sort_values("image").drop_duplicates("groupe")
    t["classe_v3"] = t.classe.map(classe_tdtu)
    for r in t[t.classe_v3.isna()].itertuples():
        exclusions.append(dict(jeu="tdtu", groupe=r.groupe, motif=f"etiquette_{r.classe}"))
    t = t[t.classe_v3.notna()]
    lignes += [dict(jeu="tdtu", classe=r.classe_v3, source=r.image, octets=z.read(r.image), nom=Path(r.image).name)
               for r in t.itertuples()]
    print(f"TDTU : {n_groupes} photos distinctes, {len(contradictoires)} groupes contradictoires, "
          f"{len(t)} retenues {t.classe_v3.value_counts().to_dict()}", flush=True)

    # fuites vers la validation tanzanienne locale, BananaLSD et le test banana-buddy
    idx = pd.read_csv(RACINE / "data/feuilles/index.csv")
    ref = idx[(idx.source.eq("tanzanie_2022") & idx.retenue) | idx.source.eq("bananalsd")]
    ref = ref[ref.chemin.notna()]
    chemins = [RACINE / "data/feuilles" / c for c in ref.chemin] + \
              [RACINE / "data/test_banana_buddy" / f for f in pd.read_csv(RACINE / "data/test_banana_buddy/liste.csv").fichier]
    src = [f"{s}" for s in ref.source] + ["test_banana_buddy"] * (len(chemins) - len(ref))
    rh, rv = [], []
    for c in chemins:
        im = reduire(Image.open(c)); rh.append(dhash(im)); rv.append(vignette(im))
    hs, vs = [], []
    for L in lignes:
        for v in variantes(reduire(Image.open(io.BytesIO(L["octets"])))):
            hs.append(dhash(v)); vs.append(vignette(v))
    m, j = par_image(*comparer(hs, np.stack(vs).astype(np.int16), rh, np.stack(rv).astype(np.int16), 10, 5.0)[:2])
    garde = []
    for L, e, jj in zip(lignes, m, j):
        if e <= 5.0:
            exclusions.append(dict(jeu=L["jeu"], groupe=L["source"], motif=f"proche_{src[jj]}", ecart=round(float(e), 2)))
        else:
            garde.append(L)
    print(f"références de fuite : {len(rh)} images ; ajouts retirés pour proximité : {len(lignes) - len(garde)}", flush=True)

    # écriture
    rows = []
    for k_, L in enumerate(garde):
        rel = f"images/{L['jeu']}/{k_:05d}_{L['nom']}"
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_bytes(L["octets"])
        rows.append(dict(image=f"ajouts_v3/{rel}", jeu=L["jeu"], classe=L["classe"], source=L["source"], sha256=sha(L["octets"])))
    liste = pd.DataFrame(rows)
    liste.to_csv(out / "images.csv", index=False, encoding="utf-8", lineterminator="\n")
    pd.DataFrame(exclusions).to_csv(out / "exclusions.csv", index=False, encoding="utf-8", lineterminator="\n")
    with zipfile.ZipFile(RACINE / args.zip, "w", zipfile.ZIP_STORED) as zo:
        # nom distinct : le carnet du binôme prend le premier « images.csv » trouvé dans ses données
        zo.write(out / "images.csv", "ajouts_v3/images_ajouts.csv")
        for r in liste.itertuples():
            zo.write(out / r.image.removeprefix("ajouts_v3/"), r.image)
    print(pd.crosstab(liste.jeu, liste.classe, margins=True).to_string())
    print("SHA-256 de images.csv :", sha((out / "images.csv").read_bytes()))
    print("archive :", RACINE / args.zip, f"{(RACINE / args.zip).stat().st_size / 1e6:.1f} Mo")


if __name__ == "__main__":
    main()
