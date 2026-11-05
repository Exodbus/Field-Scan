#!/usr/bin/env python3
"""Découpage entraînement / validation / test du comptage, par GROUPE (site, orthomosaïque, vol), fixé avant tout entraînement.

Règles (écrites le 4 novembre 2026, avant le réentraînement de zéro) :
- Les découpages fournis par Roboflow sont ignorés : ils sont aléatoires et partagent des photos d'origine entre
  train, valid et test (Plants-bana : 54, 39 et 32 photos communes).
- Une seule version de chaque image : plants_bana_originaux pour les bananiers, sauf 100_022x et corte, pris dans
  Count banana plants (mêmes découpes et mêmes boîtes, mais images sans retouches d'augmentation) ; Plants-bana
  augmenté et les bananiers de Multiple tree servent seulement à vérifier qu'aucune de leurs photos ne tombe dans
  deux parties ; de Multiple tree, on ne garde que les palmiers à huile et les cocotiers.
- Jeunes bananiers : photos DJI dji_0544, 0546, 0548 (sans recouvrement entre elles), réannotées à la main en points ;
  les photos DJI qui les recouvrent, les cacaoyères DJI et dji_fly sont exclues (annotations inutilisables).
- Un groupe entier va dans une seule partie. Groupes liés (mêmes vols probables) ensemble.
- Le choix des groupes repose sur leur contenu et la qualité des annotations (contrôle visuel), jamais sur un
  résultat de modèle. Le modèle est réentraîné de zéro ; le test n'est regardé qu'une fois, à la fin.
- Test bananiers : Carlos Vera Guevara, mesuré sur la référence manuelle CG1-CG9 (déjà consultée pour les anciens
  modèles : à signaler). Carlos Vera Arteaga, à 200 m, est exclu partout. Les vues obliques (images de vidéo) sont
  exclues : la chaîne ne lit que des vues verticales.

Sorties dans --out : decoupage.csv (une ligne par image ou site), groupes.csv (bilan par groupe), rapport.txt
(vérifications). Le script s'arrête en erreur si une image n'a pas de groupe ou si une fuite est trouvée.

Exemple :
    python scripts/decouper_comptage.py --out data/drone/decoupage_comptage
"""
import argparse
import collections
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

import io

import geopandas as gpd
import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verifier_sources_communes import origine, photo  # noqa: E402

RACINE = Path("data/roboflow")

# ---- Affectation des groupes (seule partie à modifier, et seulement avant l'entraînement) ----
PARTIES = {
    # ReforesTree : par site (annotations ReforesTree en entraînement ; référence manuelle MM en validation)
    "rt_flora_pluas": "train", "rt_nestor_macias": "train", "rt_leonor_aspiazu": "train",
    "rt_manuel_macias": "val",                    # mesuré sur la référence manuelle MM1-MM2 (indicatif, petite)
    "rt_carlos_vera_guevara": "test",             # mesuré sur la référence manuelle CG1-CG9 ; le modèle repart de zéro
    "rt_carlos_vera_arteaga": "exclu",            # voisin de CG (200 m)
    # Lot de bananiers Roboflow (vues verticales)
    "vols_100_022x": "train",                     # vols 100_0221 à 100_0224, annotations de Count banana plants
    "corte": "train",                             # même projet, annotations de Count banana plants
    "segmento_ouest": "train",                    # orthomosaïque « segmento », colonnes x < 22400 px
    "segmento_est": "val",                        # même orthomosaïque, x >= 22400 px (bande vide de 640 px entre les deux)
    # Jeunes bananiers : photos DJI réannotées en points (docs/consigne_annotation_jeunes_bananiers.md)
    "jeunes_dji_0546": "train", "jeunes_dji_0548": "train", "jeunes_dji_0544": "val",
    "dji_recouvrement": "exclu",                  # dji_0545, 0547, 0549 : recouvrent les photos annotées
    "dji_cacao": "exclu",                         # dji_0537 à 0543 : cacaoyères avec bananiers non annotés en bord
    "dji_fly": "exclu",                           # boîtes larges et mal centrées sur les pieds
    # cacaoyères : des bananiers y sont visibles mais jamais annotés (contrôle visuel des tuiles préparées) ;
    # ni exemples négatifs (le modèle apprendrait qu'un bananier est du fond) ni mesure de fausses détections
    "cacau_1": "exclu", "cacau_2": "exclu", "cacao": "exclu",
    "video_oblique": "exclu", "whatsapp_oblique": "exclu",   # vues obliques
    # Multiple tree : palmiers à huile (trois zones d'une grande image) et cocotiers (vignettes numérotées)
    "palmier_52000_20000": "train", "palmier_44000_16000": "val", "palmier_44000_4000": "test",
    "cocotier_0000_0899": "train", "cocotier_0900_1299": "val", "cocotier_1300_plus": "test",
}
# v4 (docs/protocole_comptage_v4.md) : nouvelles sources et segmento est en test
PARTIES_V4 = {**PARTIES,
              "segmento_est": "test",                 # plantation dense (test, boîtes Roboflow)
              "pp_lote_2": "train", "pp_lote_2_parte_2": "train",   # plantas_platano : même lot, en deux parties
              "pp_100_metros": "val",                 # plantas_platano : autre orthomosaïque
              "lasuiza": "train",                     # platano_lasuiza : orthomosaïques non distinguables
              "btd": "test"}                          # banana_tree_detection : site indépendant, plantation espacée
SOURCES_V4 = {"plantas_platano.zip": "plantas_platano", "platano_lasuiza.zip": "platano_lasuiza",
              "banana_tree_detection.zip": "banana_tree_detection"}
SITES_RT = {"Flora Pluas": "rt_flora_pluas", "Nestor Macias": "rt_nestor_macias", "Leonor Aspiazu": "rt_leonor_aspiazu",
            "Manuel Macias": "rt_manuel_macias", "Carlos Vera Guevara": "rt_carlos_vera_guevara",
            "Carlos Vera Arteaga": "rt_carlos_vera_arteaga"}


def groupe_banane(p):
    """Groupe d'une photo d'origine du lot de bananiers Roboflow ; None si inconnue (erreur)."""
    if re.match(r"^100_022[1-4]_", p):
        return "vols_100_022x"
    if p.startswith("segmento"):
        m = re.match(r"^segmento_(\d+)_(\d+)", p)
        if not m:
            return None
        return "segmento_ouest" if int(m.group(1)) < 22400 else "segmento_est"
    m = re.match(r"^dji_(05\d\d)", p)
    if m:
        n = int(m.group(1))
        if n in (544, 546, 548):
            return f"jeunes_dji_0{n}"
        return "dji_recouvrement" if n in (545, 547, 549) else "dji_cacao"
    for prefixe, g in [("corte", "corte"), ("cacau_1", "cacau_1"), ("cacau_2", "cacau_2"), ("cacao", "cacao"),
                       ("dji_fly", "dji_fly"), ("vi-deo", "video_oblique"), ("whatsapp", "whatsapp_oblique")]:
        if p.startswith(prefixe):
            return g
    return None


def groupe_v4(source, o):
    """Groupe d'une image des sources ajoutées en v4 (o = nom d'origine, en minuscules)."""
    if source == "plantas_platano":
        m = re.match(r"^(100_metros|lote_2_parte_2|lote_2)_chunk", o)
        return f"pp_{m.group(1)}" if m else None
    if source == "platano_lasuiza":
        return "lasuiza" if o.startswith("tile_") else None
    if source == "banana_tree_detection":
        return "btd" if o.startswith("uav20221018") else None
    return None


def cadres_dessines(octets):
    """Vrai si l'image contient des cadres d'annotation dessinés dans les pixels (vert pur aligné en lignes)."""
    a = np.asarray(Image.open(io.BytesIO(octets)).convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    vert = (g > 180) & (r < 110) & (b < 110) & (g - r > 100)
    lignes = int((vert.sum(1) > 40).sum() + (vert.sum(0) > 40).sum())
    return bool(vert.mean() > 0.002 and lignes >= 2)


def groupe_palmier(o):
    m = re.match(r"^(44000_4000|44000_16000|52000_20000)_", o)
    if m:
        return f"palmier_{m.group(1)}"
    if re.match(r"^\d{6}$", o):
        n = int(o)
        return "cocotier_0000_0899" if n < 900 else "cocotier_0900_1299" if n < 1300 else "cocotier_1300_plus"
    return None


def lire_coco(chemin_zip):
    """Une ligne par image : partie Roboflow, nom, origine, photo, taille, nombre d'objets par classe, empreinte."""
    z = zipfile.ZipFile(chemin_zip)
    lignes = []
    for part in ["train", "valid", "test"]:
        d = json.loads(z.read(f"{part}/_annotations.coco.json"))
        cat = {c["id"]: c["name"] for c in d["categories"]}
        nb = collections.defaultdict(collections.Counter)
        for a in d["annotations"]:
            nb[a["image_id"]][cat[a["category_id"]]] += 1
        for im in d["images"]:
            nom = f"{part}/{im['file_name']}"
            lignes.append(dict(zip=Path(chemin_zip).name, partie_roboflow=part, image=nom, origine=origine(nom),
                               photo=photo(nom), largeur=im["width"], hauteur=im["height"],
                               empreinte=hashlib.md5(z.read(nom)).hexdigest(), **{f"n_{k}": v for k, v in nb[im["id"]].items()}))
    return pd.DataFrame(lignes).fillna(0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", choices=["v3", "v4"], default="v3", help="découpage du protocole v3 ou v4")
    ap.add_argument("--out", default=None, help="défaut : data/drone/decoupage_comptage (v3) ou ..._v4")
    ap.add_argument("--sites", default="data/drone/reforestree/prepare/resume_sites.csv",
                    help="liste des sites ReforesTree (colonne site)")
    ap.add_argument("--points-jeunes", default="data/drone/jeunes_bananiers/points_jeunes_bananiers.geojson",
                    help="points manuels des jeunes bananiers (GeoJSON versionné, repère local de cadres.json)")
    args = ap.parse_args(argv)
    out = Path(args.out or ("data/drone/decoupage_comptage" + ("_v4" if args.version == "v4" else "")))
    out.mkdir(parents=True, exist_ok=True)
    parties = PARTIES_V4 if args.version == "v4" else PARTIES
    rapport, erreurs = [], []

    # 1. Bananiers : plants_bana_originaux, une ligne par image d'origine (les copies augmentées sont retirées)
    pb = lire_coco(RACINE / "plants_bana_originaux.zip")
    avant = len(pb)
    # parmi les copies d'une même image d'origine, préférer une copie en couleur (Roboflow a passé quelques
    # copies d'entraînement en niveaux de gris)
    zpb = zipfile.ZipFile(RACINE / "plants_bana_originaux.zip")
    def en_gris(nom):
        a = np.asarray(Image.open(io.BytesIO(zpb.read(nom))).convert("RGB").resize((64, 64))).astype(float)
        return bool(np.abs(a[..., 0] - a[..., 1]).mean() + np.abs(a[..., 1] - a[..., 2]).mean() < 2)
    multi = pb.origine.duplicated(keep=False)
    pb["gris"] = False
    pb.loc[multi, "gris"] = pb.loc[multi, "image"].map(en_gris)
    pb = pb.sort_values(["origine", "gris", "image"]).drop_duplicates("origine")
    rapport.append(f"copies en niveaux de gris évitées ; images gardées encore en gris : {int(pb.gris.sum())}")
    pb = pb.drop(columns="gris")
    rapport.append(f"plants_bana_originaux : {avant} images, {len(pb)} images d'origine gardées (copies retirées)")
    # segmento : tuiles d'une même orthomosaïque nommées par leur position (segmento_x_y) ; photo() retirerait la
    # position, on garde donc l'origine comme « photo » et le découpage se fait par position (groupe ouest / est)
    seg = pb.origine.str.startswith("segmento")
    pb.loc[seg, "photo"] = pb.loc[seg, "origine"]
    pb["groupe"] = pb.photo.map(groupe_banane)
    pb["source"] = "plants_bana"
    pb["annotations"] = "plants_bana_originaux (boîtes)"

    # 1 bis. 100_022x et corte : mêmes découpes et mêmes boîtes dans Count banana plants, mais images sans les
    # retouches d'augmentation de Plants-bana (comparer_annotations_roboflow.py) : on prend Count.
    ct = lire_coco(RACINE / "count_banana_plants.zip").drop_duplicates("origine")
    ct["groupe"] = ct.photo.map(groupe_banane)
    ct["source"] = "count_banana_plants"
    ct["annotations"] = "count_banana_plants (boîtes)"
    remplaces = pb.groupe.isin(["vols_100_022x", "corte"])
    rapport.append(f"100_022x et corte : {int(remplaces.sum())} images Plants-bana remplacées par {len(ct)} images "
                   f"d'origine de Count banana plants (mêmes découpes, images non retouchées)")
    if set(ct.groupe.dropna()) - {"vols_100_022x", "corte"}:
        erreurs.append(f"Count contient d'autres groupes : {set(ct.groupe.dropna())}")
    pb = pd.concat([pb[~remplaces], ct], ignore_index=True)

    # 1 ter. Jeunes bananiers DJI : les boîtes Roboflow sont remplacées par les points annotés à la main
    pts = gpd.read_file(args.points_jeunes, **({"layer": "points"} if str(args.points_jeunes).endswith(".gpkg") else {}))
    pts = pts[~(pts.geometry.isna() | pts.geometry.is_empty)]
    cadres = json.loads(Path(args.points_jeunes).with_name("cadres.json").read_text(encoding="utf-8"))["images"]
    def image_du_point(pt):
        for c in cadres:
            if c["decalage_x"] <= pt.x < c["decalage_x"] + c["largeur"] and -c["hauteur"] <= pt.y <= 0:
                return c["image"]
        return None
    pts["photo"] = pts.geometry.apply(image_du_point)
    pts["type"] = pts["type"].fillna("mere")
    jeunes = pb.groupe.str.startswith("jeunes_dji", na=False)
    for i in pb.index[jeunes]:
        s = pts[pts.photo == pb.at[i, "photo"]]
        for c in [c for c in pb.columns if c.startswith("n_")]:
            pb.at[i, c] = 0
        pb.at[i, "n_Banana"] = int((s["type"] == "mere").sum())     # s["type"] : la colonne (s.type = type de géométrie)
        pb.at[i, "n_rejet"] = int((s["type"] == "rejet").sum())
        pb.at[i, "annotations"] = f"{Path(args.points_jeunes).name} (points manuels)"
    rapport.append(f"jeunes bananiers DJI : {len(pts)} points manuels ({dict(pts.groupby(['photo', 'type']).size())})")

    # 2. Multiple tree : palmiers à huile et cocotiers seulement (images sans bananier)
    mt = lire_coco(RACINE / "multiple_tree.zip")
    mt["groupe"] = mt.origine.map(groupe_palmier)
    sans_banane = mt.get("n_Banana-plant", 0) == 0
    mt_pal = mt[mt.groupe.notna() & sans_banane].drop_duplicates("origine").copy()
    rapport.append(f"multiple_tree : {len(mt)} images, {len(mt_pal)} images d'origine de palmiers ou cocotiers gardées "
                   f"(le reste : bananiers et découpes des photos de Plants-bana, déjà couverts)")
    mt_pal["source"] = "multiple_tree"
    mt_pal["annotations"] = "multiple_tree (boîtes de palmiers et cocotiers)"
    a_verifier = mt[mt.groupe.notna() & ~sans_banane]
    if len(a_verifier):
        erreurs.append(f"{len(a_verifier)} images de palmiers contiennent aussi des bananiers")

    # 3. ReforesTree : une ligne par site
    sites = pd.read_csv(args.sites)
    col = "site" if "site" in sites.columns else sites.columns[0]
    ref = {"rt_manuel_macias": "référence manuelle MM1-MM2 (points)", "rt_carlos_vera_guevara": "référence manuelle CG1-CG9 (points)"}
    rt = pd.DataFrame([dict(source="reforestree", image=r[col], origine=r[col], photo=r[col], groupe=SITES_RT.get(r[col]),
                            n_Banana=r.get("bananiers", 0),
                            annotations=ref.get(SITES_RT.get(r[col]), "boîtes ReforesTree (incomplètes)")) for _, r in sites.iterrows()])

    # 3 bis (v4). Plantations ajoutées : une copie par image (MD5 et nom d'origine) ; images à cadres dessinés retirées
    nouveaux = []
    if args.version == "v4":
        for nom_zip, source in SOURCES_V4.items():
            t = lire_coco(RACINE / nom_zip)
            avant = len(t)
            zz = zipfile.ZipFile(RACINE / nom_zip)
            t["cadres_dessines"] = t.image.map(lambda n: cadres_dessines(zz.read(n)))
            n_cadres = int(t.cadres_dessines.sum())
            t = t[~t.cadres_dessines].drop(columns="cadres_dessines")
            t = t.sort_values("image").drop_duplicates("empreinte")
            if source != "platano_lasuiza":          # lasuiza : même nom pour des images différentes (plusieurs orthomosaïques)
                t = t.drop_duplicates("origine")
            t["groupe"] = [groupe_v4(source, o) for o in t.origine]
            t["source"] = source
            t["annotations"] = f"{source} (Roboflow, " + ("points" if source == "plantas_platano" else "boîtes") + ")"
            # photo d'origine = nom d'origine (tuiles d'orthomosaïque nommées par leur position)
            t["photo"] = t.origine if source != "platano_lasuiza" else "lasuiza_" + t.origine
            rapport.append(f"{source} : {avant} images, {n_cadres} à cadres dessinés retirées, {len(t)} gardées "
                           f"(copies retirées) ; groupes {dict(t.groupe.value_counts())}")
            nouveaux.append(t)

    tab = pd.concat([pb, mt_pal, rt] + nouveaux, ignore_index=True)
    sans_groupe = tab[tab.groupe.isna()]
    if len(sans_groupe):
        erreurs.append(f"{len(sans_groupe)} images sans groupe, ex. {sans_groupe.photo.head(5).tolist()}")
    inconnus = set(tab.groupe.dropna()) - set(parties)
    if inconnus:
        erreurs.append(f"groupes sans partie : {sorted(inconnus)}")
    tab["partie"] = tab.groupe.map(parties)
    for c in [c for c in tab.columns if c.startswith("n_")]:
        tab[c] = tab[c].fillna(0).astype(int)

    # 4. Vérifications de fuite entre parties (train, val, test, bonus)
    gardees = tab[tab.partie.isin(["train", "val", "test", "bonus"])]
    for cle, libelle in [("photo", "photo d'origine"), ("origine", "image d'origine"), ("groupe", "groupe")]:
        multi = gardees.groupby(cle).partie.nunique()
        multi = multi[multi > 1]
        rapport.append(f"{libelle} dans plusieurs parties : {len(multi)}")
        if len(multi):
            erreurs.append(f"{libelle} dans plusieurs parties : {multi.index[:5].tolist()}")
    emp = gardees[gardees.empreinte.notna() & (gardees.empreinte != 0)]
    multi = emp.groupby("empreinte").partie.nunique()
    rapport.append(f"fichiers identiques (MD5) dans plusieurs parties : {int((multi > 1).sum())} ; "
                   f"en double dans une même partie : {int(emp.empreinte.duplicated().sum())}")
    if (multi > 1).any():
        erreurs.append("fichiers identiques dans plusieurs parties")

    # 5. Les autres versions des mêmes photos (Count banana plants, Plants-bana augmenté, bananiers de Multiple tree)
    #    ne doivent pas relier deux parties : chacune de leurs photos doit appartenir à un seul groupe connu.
    partie_photo = gardees.drop_duplicates("photo").set_index("photo").partie
    for nom in ["count_banana_plants.zip", "plants_bana.zip"]:
        autres = {photo(n) for n in zipfile.ZipFile(RACINE / nom).namelist() if n.lower().endswith((".jpg", ".jpeg", ".png"))}
        connues = autres & set(partie_photo.index)
        rapport.append(f"{nom} : {len(autres)} photos d'origine, dont {len(connues)} déjà dans le découpage "
                       f"(parties : {dict(partie_photo[list(connues)].value_counts())}) ; non utilisé")
    ban_mt = {p for p in mt[~sans_banane].photo}
    connues = ban_mt & set(partie_photo.index)
    rapport.append(f"multiple_tree, images avec bananiers : {len(ban_mt)} photos d'origine, dont {len(connues)} déjà "
                   f"dans le découpage (parties : {dict(partie_photo[list(connues)].value_counts())}) ; non utilisé")

    # 6. Bilan
    comptes = [c for c in tab.columns if c.startswith("n_")]
    bilan = (tab.groupby(["partie", "groupe"]).agg(images=("image", "size"), photos=("photo", "nunique"), **{c: (c, "sum") for c in comptes})
             .reset_index().sort_values(["partie", "groupe"]))
    bilan.to_csv(out / "groupes.csv", index=False)
    tab.drop(columns=["empreinte"]).to_csv(out / "decoupage.csv", index=False)
    texte = "\n".join(rapport + ["", bilan.to_string(index=False), "",
                                 "ERREURS :" if erreurs else "Aucune erreur : pas de fuite entre les parties."] + erreurs)
    (out / "rapport.txt").write_text(texte, encoding="utf-8")
    print(texte)
    if erreurs:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
