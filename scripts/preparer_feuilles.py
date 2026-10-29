#!/usr/bin/env python3
"""Préparation du jeu de feuilles du module maladies.

Découpage (carnet de données) :
  - entraînement : Tanzanie, campagne 2021 (Harvard Dataverse), et Pérou (Mendeley Data, 2026),
    feuilles saines et Sigatoka seulement ;
  - validation   : Tanzanie, campagne 2022-2023 (Zenodo), un zip par classe ;
  - test         : BananaLSD (Bangladesh), dossier OriginalSet uniquement ;
  - test_perou   : Cordana du jeu péruvien, mise à part : jamais apprise ni utilisée pour un réglage
    (Cordana est une maladie « inconnue » du test) ; sert seulement de test supplémentaire du rejet.

Classes :
  - saine, cercosporiose_noire, fusariose (Tanzanie) ;
  - BananaLSD : healthy -> saine ; sigatoka -> cercosporiose_noire (la classe des auteurs
    regroupe cercosporiose noire et jaune) ; cordana et pestalotiopsis -> inconnue_cordana,
    inconnue_pestalotiopsis : maladies absentes de l'entraînement, que le modèle doit rejeter.
  - Pérou : sanas -> saine ; sigatoka -> cercosporiose_noire (forme non précisée) ;
    cordana -> inconnue_cordana (ensemble test_perou).

Exclusions (rien n'est supprimé : tout est noté dans l'index, colonne `motif`) :
  - tige : photos de pseudo-tronc (docs/exclusions/tiges_fusariose_2021.csv) ;
  - copie_exacte : même fichier (SHA-256) déjà présent dans la même classe et le même ensemble ;
  - etiquette_contradictoire : même fichier dans deux classes différentes (toutes les copies) ;
  - perou_copie_evaluation : image péruvienne d'entraînement identique, ou presque, à une image de
    validation ou de test ; retirée de l'entraînement (source ajoutée après coup : les ensembles
    d'évaluation restent inchangés) ;
  - fuite_exacte, fuite_visuelle : image de validation ou de test identique, ou presque identique, à une
    image d'un ensemble antérieur (entraînement pour la validation ; entraînement et validation pour le
    test). Fuite visuelle en deux temps : l'empreinte dHash (64 bits) propose des candidats (au plus
    --seuil-candidat bits de différence), puis on confirme en comparant les deux images réduites à
    16 x 16 pixels en couleur (écart moyen au plus --seuil-vignette, sur 255). L'empreinte seule ne
    suffit pas : les nervures parallèles des feuilles donnent des empreintes voisines à des photos
    différentes (vérifié à l'œil sur les 110 premières alertes, toutes fausses). Seuil de vignette :
    une vraie copie redimensionnée et recompressée donne environ 0,5 à 1 ; la fausse alerte la plus
    proche observée (deux feuilles vertes différentes) donnait 9,9 ; d'où 5, à mi-chemin.

Uniformisation : rotation EXIF appliquée, petit côté ramené à --cote pixels, JPEG qualité 92.

Sortie : data/feuilles/images/<ensemble>/<classe>/<id>.jpg et data/feuilles/index.csv.

Exemple :
    python scripts/preparer_feuilles.py
"""
import argparse
import hashlib
import io
import json
import re
import time
import zipfile
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd
from PIL import Image, ImageOps

EXT_IMAGES = {".jpg", ".jpeg", ".png"}
ORDRE_ENSEMBLES = ["entrainement", "validation", "test", "test_perou"]
CLASSES_ZIP = {"HEALTHY": "saine", "BLACK SIGATOKA": "cercosporiose_noire", "FUSARIUM WILT": "fusariose"}
CLASSES_BANANALSD = {"healthy": "saine", "sigatoka": "cercosporiose_noire",
                     "cordana": "inconnue_cordana", "pestalotiopsis": "inconnue_pestalotiopsis"}
CLASSES_PEROU = {"sanas": ("entrainement", "saine"), "sigatoka": ("entrainement", "cercosporiose_noire"),
                 "cordana": ("test_perou", "inconnue_cordana")}


def est_image(nom):
    p = PurePosixPath(nom.replace("\\", "/"))
    return p.suffix.lower() in EXT_IMAGES and "__MACOSX" not in p.parts and not p.name.startswith("._")


def inventaire(args):
    """Une entrée par image source : ensemble, classe, source, clé d'origine et fonction de lecture."""
    entrees = []
    for z in sorted(Path(args.zips).glob("*.zip")):
        m = re.match(r"^(HEALTHY|BLACK SIGATOKA|FUSARIUM WILT)([_-])(\d+)\.zip$", z.name)
        if not m:
            continue
        ensemble = "entrainement" if m.group(2) == "_" else "validation"
        source = "tanzanie_2021" if ensemble == "entrainement" else "tanzanie_2022"
        with zipfile.ZipFile(z) as a:
            for n in a.namelist():
                if not n.endswith("/") and est_image(n):
                    entrees.append(dict(ensemble=ensemble, classe=CLASSES_ZIP[m.group(1)], classe_origine=m.group(1),
                                        source=source, cle=f"{z.name}::{n}", conteneur=str(z), membre=n))
    for dossier, ensemble, source in ((args.sain_2021, "entrainement", "tanzanie_2021"),
                                      (args.sain_2022, "validation", "tanzanie_2022")):
        p = Path(dossier)
        if not p.exists():
            raise SystemExit(f"Dossier introuvable : {p}")
        for f in sorted(p.rglob("*")):
            if f.is_file() and est_image(str(f)):
                entrees.append(dict(ensemble=ensemble, classe="saine", classe_origine="HEALTHY", source=source,
                                    cle=f"{p.name}::{f.relative_to(p).as_posix()}", conteneur="", membre=str(f)))
    if not args.sans_perou:
        z = Path(args.perou)
        if not z.exists():
            raise SystemExit(f"Jeu péruvien introuvable : {z} (ou option --sans-perou)")
        with zipfile.ZipFile(z) as a:
            for n in a.namelist():
                if n.endswith("/") or not est_image(n):
                    continue
                dossier = PurePosixPath(n).parent.name.lower()
                if dossier not in CLASSES_PEROU:
                    raise SystemExit(f"Dossier de classe inattendu dans le jeu péruvien : {dossier}")
                ensemble, classe = CLASSES_PEROU[dossier]
                entrees.append(dict(ensemble=ensemble, classe=classe, classe_origine=dossier, source="perou_2026",
                                    cle=f"{z.name}::{n}", conteneur=str(z), membre=n))
    racine = Path(args.bananalsd)
    for f in sorted(racine.rglob("*")):
        parties = [x.lower() for x in f.parts]
        if f.is_file() and est_image(str(f)) and "originalset" in parties:
            cls = f.parent.name.lower()
            cible = next((v for k, v in CLASSES_BANANALSD.items() if k in cls), None)
            if cible is None:
                raise SystemExit(f"Classe BananaLSD inconnue : {f.parent.name}")
            entrees.append(dict(ensemble="test", classe=cible, classe_origine=f.parent.name, source="bananalsd",
                                cle=f"OriginalSet::{f.parent.name}/{f.name}", conteneur="", membre=str(f)))
    return pd.DataFrame(entrees)


def lire_octets(ligne, archives):
    if ligne.conteneur:
        a = archives.setdefault(ligne.conteneur, zipfile.ZipFile(ligne.conteneur))
        return a.read(ligne.membre)
    return Path(ligne.membre).read_bytes()


def ouvrir_uniformisee(octets, cote):
    """Image avec rotation EXIF appliquée, petit côté ramené à `cote` pixels (jamais agrandie)."""
    im = Image.open(io.BytesIO(octets))
    taille_origine = im.size  # avant le décodage accéléré, qui réduit déjà l'image
    im.draft("RGB", (cote * 2, cote * 2))  # décodage JPEG accéléré, à résolution réduite
    im = ImageOps.exif_transpose(im).convert("RGB")
    r = cote / min(im.size)
    if r < 1:
        im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    return im, taille_origine


def dhash(im, taille=8):
    """Empreinte visuelle de 64 bits : sens du gradient horizontal d'une miniature en niveaux de gris."""
    g = np.asarray(im.convert("L").resize((taille + 1, taille), Image.BILINEAR), dtype=np.int16)
    bits = (g[:, 1:] > g[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def vignette(im, cote=16):
    """Image réduite en couleur, pour confirmer une ressemblance pixel par pixel."""
    return np.asarray(im.resize((cote, cote), Image.BILINEAR), dtype=np.int16)


def fuites_visuelles(h_cour, h_ant, v_cour, v_ant, seuil_candidat, seuil_vignette, morceau=500):
    """Pour chaque image courante : distance d'empreinte minimale, plus petit écart de vignette parmi les
    candidats (empreinte à au plus seuil_candidat bits), et fuite confirmée ou non."""
    n = len(h_cour)
    dist = np.full(n, 64)
    ecart = np.full(n, np.nan)
    if len(h_ant) == 0:
        return dist, ecart, np.zeros(n, bool)
    a, b = np.asarray(h_cour, dtype=np.uint64), np.asarray(h_ant, dtype=np.uint64)
    for i in range(0, n, morceau):
        d = np.bitwise_count(a[i:i + morceau, None] ^ b[None, :])
        dist[i:i + morceau] = d.min(axis=1)
        for li, lj in zip(*np.nonzero(d <= seuil_candidat)):
            e = float(np.abs(v_cour[i + li] - v_ant[lj]).mean())
            if np.isnan(ecart[i + li]) or e < ecart[i + li]:
                ecart[i + li] = e
    return dist, ecart, ecart <= seuil_vignette


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zips", default="data/raw/zips")
    ap.add_argument("--sain-2021", default="data/raw/tanzania_2021/healthy_1")
    ap.add_argument("--sain-2022", default="data/raw/tanzania_2022/healthy_1")
    ap.add_argument("--bananalsd", default="data/raw/bananalsd")
    ap.add_argument("--perou", default="data/raw/zips/perou_2026.zip")
    ap.add_argument("--sans-perou", action="store_true", help="version sans le jeu péruvien (ablation)")
    ap.add_argument("--tiges", default="docs/exclusions/tiges_fusariose_2021.csv")
    ap.add_argument("--out", default="data/feuilles")
    ap.add_argument("--cote", type=int, default=256, help="petit côté des images préparées, en pixels (défaut 256)")
    ap.add_argument("--seuil-candidat", type=int, default=6,
                    help="bits de différence d'empreinte pour proposer une fuite visuelle (défaut 6)")
    ap.add_argument("--seuil-vignette", type=float, default=5.0,
                    help="écart moyen maximal (sur 255) des vignettes 16 x 16 pour confirmer une fuite (défaut 5)")
    args = ap.parse_args(argv)
    debut = time.time()
    out = Path(args.out)

    idx = inventaire(args)
    print(f"{len(idx)} images trouvées :")
    print(idx.groupby(["ensemble", "classe"]).size().to_string())

    tiges = pd.read_csv(args.tiges)
    cles_tiges = set(tiges.zip + "::" + tiges.membre)
    idx["motif"] = np.where(idx.cle.isin(cles_tiges), "tige", "")
    print(f"\nTiges exclues : {(idx.motif == 'tige').sum()} (liste : {len(cles_tiges)})")

    # Premier passage : empreintes seulement (aucune image gardée en mémoire)
    archives, sha, dh, larg, haut, vign, illisibles = {}, [], [], [], [], [], 0
    for i, ligne in enumerate(idx.itertuples()):
        try:
            octets = lire_octets(ligne, archives)
            im, (l, h) = ouvrir_uniformisee(octets, args.cote)
            sha.append(hashlib.sha256(octets).hexdigest()); dh.append(dhash(im)); larg.append(l); haut.append(h)
            vign.append(vignette(im))
        except Exception:
            illisibles += 1
            sha.append(""); dh.append(0); larg.append(0); haut.append(0); vign.append(np.zeros((16, 16, 3), np.int16))
        if (i + 1) % 500 == 0 or i + 1 == len(idx):
            print(f"\r  empreintes : {i + 1}/{len(idx)}", end="", flush=True)
    print()
    idx["sha256"], idx["dhash"], idx["largeur_origine"], idx["hauteur_origine"] = sha, dh, larg, haut
    vign = np.stack(vign)
    idx.loc[idx.sha256 == "", "motif"] = "illisible"
    idx["id"] = idx.source + "_" + idx.sha256.str[:12]

    # Copies exactes et étiquettes contradictoires (dans chaque ensemble)
    ok = idx.motif == ""
    classes_par_sha = idx[ok].groupby(["ensemble", "sha256"]).classe.nunique()
    contradictoires = {k for k, v in classes_par_sha.items() if v > 1}
    contra = ok & pd.Series([(e, s) in contradictoires for e, s in zip(idx.ensemble, idx.sha256)], index=idx.index)
    idx.loc[contra, "motif"] = "etiquette_contradictoire"
    ok = idx.motif == ""
    copies = ok & idx[ok].duplicated(["ensemble", "classe", "sha256"], keep="first").reindex(idx.index, fill_value=False)
    idx.loc[copies, "motif"] = "copie_exacte"

    # Source ajoutée après coup (Pérou) : ses copies d'images d'évaluation sont retirées de l'entraînement,
    # pour que la validation et le test restent identiques à la version sans Pérou (résultats comparables)
    evaluation = idx[idx.ensemble.isin(["validation", "test", "test_perou"]) & (idx.motif == "")]
    perou = (idx.source == "perou_2026") & (idx.ensemble == "entrainement") & (idx.motif == "")
    idx.loc[perou & idx.sha256.isin(set(evaluation.sha256)), "motif"] = "perou_copie_evaluation"
    perou = (idx.source == "perou_2026") & (idx.ensemble == "entrainement") & (idx.motif == "")
    if perou.any():
        pos_p, pos_e = np.flatnonzero(perou.to_numpy()), idx.index.get_indexer(evaluation.index)
        _, _, copie = fuites_visuelles(idx.dhash.to_numpy()[pos_p], idx.dhash.to_numpy()[pos_e],
                                       vign[pos_p], vign[pos_e], args.seuil_candidat, args.seuil_vignette)
        idx.loc[perou[perou].index[copie], "motif"] = "perou_copie_evaluation"

    # Fuites entre ensembles : exactes (SHA-256), puis visuelles (dHash)
    for k, ens in enumerate(ORDRE_ENSEMBLES[1:], start=1):
        anterieurs = idx[(idx.ensemble.isin(ORDRE_ENSEMBLES[:k])) & (idx.motif == "")]
        courant = (idx.ensemble == ens) & (idx.motif == "")
        exacte = courant & idx.sha256.isin(set(anterieurs.sha256))
        idx.loc[exacte, "motif"] = "fuite_exacte"
        courant = (idx.ensemble == ens) & (idx.motif == "")
        pos_c, pos_a = np.flatnonzero(courant.to_numpy()), idx.index.get_indexer(anterieurs.index)
        d, e, fuite = fuites_visuelles(idx.dhash.to_numpy()[pos_c], idx.dhash.to_numpy()[pos_a],
                                       vign[pos_c], vign[pos_a], args.seuil_candidat, args.seuil_vignette)
        idx.loc[courant, "distance_min_anterieur"] = d
        idx.loc[courant, "ecart_vignette_min"] = np.round(e, 2)
        idx.loc[courant[courant].index[fuite], "motif"] = "fuite_visuelle"

    # Second passage : écriture des seules images retenues
    retenues = idx[idx.motif == ""]
    for k, (i, ligne) in enumerate(retenues.iterrows(), start=1):
        im, _ = ouvrir_uniformisee(lire_octets(ligne, archives), args.cote)
        dest = out / "images" / ligne.ensemble / ligne.classe / f"{ligne.id}.jpg"
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, quality=92)
        idx.at[i, "chemin"] = dest.relative_to(out).as_posix()
        if k % 500 == 0 or k == len(retenues):
            print(f"\r  écriture : {k}/{len(retenues)}", end="", flush=True)
    print()
    idx["retenue"] = idx.motif == ""
    colonnes = ["id", "ensemble", "classe", "classe_origine", "source", "retenue", "motif", "chemin", "cle",
                "largeur_origine", "hauteur_origine", "sha256", "dhash", "distance_min_anterieur", "ecart_vignette_min"]
    idx["dhash"] = idx.dhash.map(lambda x: f"{int(x):016x}")
    idx.reindex(columns=colonnes).to_csv(out / "index.csv", index=False)

    tab = idx[idx.retenue].groupby(["ensemble", "classe"]).size().unstack(fill_value=0)
    motifs = idx[~idx.retenue].groupby(["ensemble", "motif"]).size().unstack(fill_value=0)
    (out / "parametres.json").write_text(json.dumps(dict(
        cote_px=args.cote, seuil_candidat_bits=args.seuil_candidat, seuil_vignette=args.seuil_vignette,
        perou=not args.sans_perou, liste_tiges=args.tiges, images_trouvees=len(idx),
        images_retenues=int(idx.retenue.sum()), illisibles=illisibles, duree_s=round(time.time() - debut)),
        indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nImages retenues par ensemble et par classe :")
    print(tab.to_string())
    cand = idx.ecart_vignette_min.notna()
    print(f"\nCandidats de fuite visuelle (empreinte à {args.seuil_candidat} bits au plus) : {int(cand.sum())} ; "
          f"confirmés (vignettes à {args.seuil_vignette:g} au plus) : {int((idx.motif == 'fuite_visuelle').sum())}")
    if cand.any():
        print("Écart de vignette des candidats (min, 10e centile, médiane) :",
              [round(float(x), 1) for x in idx.loc[cand, "ecart_vignette_min"].quantile([0, 0.1, 0.5])])
    print("\nImages exclues par motif :")
    print(motifs.to_string())
    print(f"\nTerminé en {time.time() - debut:.0f} s. Index : {out / 'index.csv'} | images : {out / 'images'}")


if __name__ == "__main__":
    main()
