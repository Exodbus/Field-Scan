#!/usr/bin/env python3
"""Nuit du 12/11 (D-maladies) : listes par jeu neuf, choix du test vierge (règle 4.5) et archive d'entraînement.
Aucun modèle.

1. Pour chaque jeu : CSV data/raw/nuit_1112/<jeu>/liste.csv (chemin, classe_origine, classe, pays, source, sha256,
   largeur, hauteur, retenue, motif). Classe ramenée à saine / black_sigatoka / fusarium / autre / inconnue.
   Exclus : fuite (SHA-256 connu ou dHash + vignette sous les 8 symétries, scripts/m12_prosp_fuites.py), copie
   d'un autre jeu neuf (gardée dans le premier jeu de la liste JEUX), doublon interne (on garde la première photo
   du groupe), photo hors feuille de bananier (classes de fruit), photo illisible.
2. Règle 4.5 du plan (écrite avant) : parmi les jeux neufs valides dont le pays ou la source est absent de tous nos
   jeux, le test vierge est celui qui a le plus de photos retenues, à condition d'avoir des saines ET des malades.
   Choix sur les effectifs seuls. Écrit dans data/raw/nuit_1112/_controle/choix_test_vierge.json.
3. Jeux d'entraînement (tous les autres jeux valides) : photos retenues réduites à 896 px de petit côté (JPEG 92,
   remise droite EXIF) dans data/raw/nuit_1112/_kaggle/feuilles-nuit-1112/feuilles_nuit_1112.zip, avec
   liste_entrainement.csv. Le test vierge n'y est jamais mis.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_prosp_preparer.py
"""
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd
from PIL import Image, ImageFile, ImageOps

RACINE = Path(__file__).resolve().parents[1]
NUIT = RACINE / "data/raw/nuit_1112"
CTRL = NUIT / "_controle"
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


def classe_indonesie(chemin):
    n = Path(chemin).name.lower()
    o = re.sub(r"[\s_]*\d+\.\w+$", "", n)
    return o, {"healthy": "saine", "sigatoka": "black_sigatoka", "layu fusarium": "fusarium",
               "cordana": "autre"}.get(o, "inconnue")


def classe_agrovision(chemin):
    o = Path(chemin).parent.name
    return o, {"banana_healthy_leaf": "saine", "banana_black_sigatoka_leaf": "black_sigatoka",
               "banana_panama_leaf": "fusarium", "banana_cordana_spot_leaf": "autre"}.get(o, "inconnue")


def classe_dossier(table):
    def f(chemin):
        o = Path(chemin).parent.name
        for motif, c in table:
            if re.search(motif, o, re.I):
                return o, c
        return o, "hors_feuille"
    return f


# (nom, dossier relatif, fonction de classe, pays, source, pays ou source absent de nos jeux)
JEUX = [
    ("figshare_agrovisionbd_bangladesh", "figshare_agrovisionbd_bangladesh/fichiers", classe_agrovision,
     "Bangladesh (Patuakhali)", "Figshare 10.6084/m9.figshare.34005402", True),
    ("mendeley_ffbb33cj4y_indonesie", "mendeley_ffbb33cj4y_indonesie/fichiers", classe_indonesie,
     "Indonésie (annoncé)", "Mendeley 10.17632/ffbb33cj4y.1 (compilation de jeux connus)", False),
]
EXTRA = json.loads((CTRL / "jeux_extra.json").read_text(encoding="utf-8")) if (CTRL / "jeux_extra.json").exists() else []
for e in EXTRA:  # jeux ajoutés après inspection : {nom, dossier, table: [[motif, classe]...], pays, source, neuf}
    JEUX.append((e["nom"], e["dossier"], classe_dossier(e["table"]), e["pays"], e["source"], e["neuf"]))
# photos de taille « web » (plus grand côté < 2 000 px) dans un jeu annoncé comme pris au téléphone en pleine
# résolution : vraisemblablement reprises d'internet (5 sont des copies de nos jeux) ; écartées
TAILLE_MIN = {"figshare_agrovisionbd_bangladesh": 2000}
# jeux jugés non valides comme test sur les planches (avant tout décompte des photos retenues)
EXCLUS_DU_TEST = {e["nom"]: e["exclu_du_test"] for e in EXTRA if e.get("exclu_du_test")}
MALADES = {"black_sigatoka", "fusarium", "autre", "inconnue"}


def listes():
    out = {}
    vus_sha = set()
    for nom, dossier, fclasse, pays, source, neuf in JEUX:
        f = CTRL / f"fuites_{nom}.csv"
        if not f.exists():
            print("pas de contrôle de fuite pour", nom); continue
        d = pd.read_csv(f, keep_default_na=False)
        d["chemin"] = d.chemin.astype(str)
        co = [fclasse(c) for c in d.chemin]
        d["classe_origine"] = [a for a, _ in co]
        d["classe"] = [b for _, b in co]
        d["pays"], d["source"] = pays, source
        ei = pd.to_numeric(d.ecart_interne, errors="coerce").fillna(float("inf"))
        # 1er passage : motifs propres à chaque photo
        m1 = {}
        for r, e in zip(d.itertuples(), ei):
            if r.classe == "hors_feuille":
                m1[r.chemin] = "hors_feuille"
            elif int(r.largeur) == 0:
                m1[r.chemin] = "illisible"
            elif r.sha_connu:
                m1[r.chemin] = f"sha_connu:{r.sha_connu}"
            elif str(r.fuite_visuelle) == "True":
                m1[r.chemin] = f"fuite_visuelle:{r.source_proche}"
            elif nom in TAILLE_MIN and max(int(r.largeur), int(r.hauteur)) < TAILLE_MIN[nom]:
                m1[r.chemin] = "taille_web"
            elif r.sha256 in vus_sha:
                m1[r.chemin] = "copie_exacte_jeu_neuf"
            elif e <= 5 and r.jeu_double != nom and r.jeu_double in out:
                m1[r.chemin] = f"copie_jeu_neuf:{r.jeu_double}"
            else:
                m1[r.chemin] = ""
        # 2e passage : quasi-copie (même jeu) d'une photo écartée pour fuite, puis doublons internes
        motif, gardes = [], set()
        for r, e in zip(d.itertuples(), ei):
            m = m1[r.chemin]
            if m == "" and e <= 5 and r.jeu_double == nom:
                md = m1.get(r.double_de, "")
                if md.startswith(("sha_connu", "fuite_visuelle", "taille_web")):
                    m = "proche_d_une_photo_ecartee"
                elif r.double_de in gardes:
                    m = "doublon_interne"
            motif.append(m)
            if m == "":
                gardes.add(r.chemin); vus_sha.add(r.sha256)
        d["motif"] = motif
        d["retenue"] = d.motif == ""
        # doublon interne dont la classe diffère : étiquette douteuse, les deux photos retirées
        cls = dict(zip(d.chemin, d.classe))
        conflit = set()
        for r, e in zip(d.itertuples(), ei):
            if e <= 5 and r.jeu_double == nom and cls.get(r.double_de) != r.classe:
                conflit |= {r.chemin, r.double_de}
        d.loc[d.chemin.isin(conflit) & d.retenue, "motif"] = "doublon_classes_differentes"
        d.loc[d.chemin.isin(conflit), "retenue"] = False
        cols = ["chemin", "classe_origine", "classe", "pays", "source", "sha256", "largeur", "hauteur", "retenue",
                "motif", "ecart_ref", "source_proche"]
        d[cols].to_csv(NUIT / nom / "liste.csv", index=False)
        out[nom] = (d, pays, source, neuf)
    return out


def main():
    L = listes()
    bilan, candidats = {}, []
    for nom, (d, pays, source, neuf) in L.items():
        r = d[d.retenue]
        b = dict(pays=pays, source=source, pays_ou_source_neuf=neuf, photos=len(d), retenues=len(r),
                 par_classe=r.classe.value_counts().to_dict(), par_classe_origine=r.classe_origine.value_counts().to_dict(),
                 exclusions=d[~d.retenue].motif.str.split(":").str[0].value_counts().to_dict())
        b["saines"] = int((r.classe == "saine").sum()); b["malades"] = int(r.classe.isin(MALADES).sum())
        bilan[nom] = b
        b["exclu_du_test"] = EXCLUS_DU_TEST.get(nom, "")
        if neuf and not b["exclu_du_test"] and b["saines"] > 0 and b["malades"] > 0:
            candidats.append((len(r), nom))
    candidats.sort(reverse=True)
    test = candidats[0][1] if candidats else None
    choix = dict(regle="plan_nuit_2026-11-12 section 4.5 : le plus de photos retenues, avec saines et malades, "
                       "pays ou source absent de nos jeux ; effectifs seuls",
                 candidats=[dict(jeu=n, retenues=k) for k, n in candidats], test_vierge=test)
    (CTRL / "choix_test_vierge.json").write_text(json.dumps(choix, ensure_ascii=False, indent=1), encoding="utf-8")
    (CTRL / "bilan_jeux.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(choix, ensure_ascii=False, indent=1)); print(json.dumps(bilan, ensure_ascii=False, indent=1))
    if "--sans-zip" in sys.argv:
        return
    sortie = NUIT / "_kaggle/feuilles-nuit-1112"
    sortie.mkdir(parents=True, exist_ok=True)
    lignes = []
    with zipfile.ZipFile(sortie / "feuilles_nuit_1112.zip", "w", zipfile.ZIP_STORED) as z:
        for nom, (d, pays, source, neuf) in L.items():
            if nom == test:
                continue
            for r in d[d.retenue].itertuples():
                im = ImageOps.exif_transpose(Image.open(r.chemin)).convert("RGB")
                f = 896 / min(im.size)
                if f < 1:
                    im = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
                buf = io.BytesIO(); im.save(buf, "JPEG", quality=92)
                arc = f"{nom}/{r.classe}/{r.sha256[:16]}.jpg"
                z.writestr(arc, buf.getvalue())
                lignes.append(dict(fichier=arc, jeu=nom, classe=r.classe, classe_origine=r.classe_origine,
                                   pays=pays, source=source, sha256_origine=r.sha256, chemin_origine=r.chemin))
        pd.DataFrame(lignes).to_csv(sortie / "liste_entrainement.csv", index=False)
        z.write(sortie / "liste_entrainement.csv", "liste_entrainement.csv")
    print(f"archive : {len(lignes)} photos -> {sortie}")


if __name__ == "__main__":
    main()
