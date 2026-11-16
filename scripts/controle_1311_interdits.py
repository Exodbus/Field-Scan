#!/usr/bin/env python3
"""Contrôleur, nuit du 13/11 : passage de contrôle des interdits (aucune lecture de contenu de juge).

Ce que fait un passage :
  1. empreinte SHA-256 du plan de nuit, comparée à docs/nuit_2026-11-13/empreinte_plan.txt ;
  2. `git status` : tout fichier suivi modifié ou supprimé est une infraction ; nouveaux non suivis listés ;
     les commits après 6fb6b42 sont une infraction ;
  3. dates d'accès et de modification (os.stat seulement, le contenu n'est jamais lu) des fichiers des juges relus
     et du test vierge : tout accès postérieur au début de la nuit (13/11 23 h 40) est signalé ;
  4. recherche, dans les scripts et carnets des agents (m13_*, c13_*) et tout fichier de code neuf, des noms
     de juges ;
  5. fichiers neufs ou modifiés depuis 23 h 40 hors des zones d'écriture du plan (section 7) ;
  6. fichiers neufs destinés à Kaggle (images, zip, métadonnées) : nom et taille comparés aux fichiers des juges
     (sans lire les juges) ; tout nouveau fichier de données sous data/ signalé (téléchargement).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_1311_interdits.py
"""
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
OUT = RACINE / "out/controle_nuit_1311"
OUT.mkdir(parents=True, exist_ok=True)
T0 = dt.datetime(2026, 11, 13, 23, 40).timestamp()
# accès aux juges comptés depuis T_ACCES (option --depuis JJ/MM-HH:MM ; défaut : début de la nuit)
T_ACCES = T0
for _a in sys.argv[1:]:
    if _a.startswith("--depuis="):
        _j, _h = _a.split("=", 1)[1].split("-")
        T_ACCES = dt.datetime(2026, 11, int(_j.split("/")[0]), int(_h.split(":")[0]), int(_h.split(":")[1])).timestamp()
COMMIT_DEPART = "6fb6b42"
SHA_PLAN = "c274ce6467a65210fc9e9df7d8228da686e8590ad6f6b440b1c472cf9c94041e"

# Zones d'écriture permises par le plan (section 7), en préfixes posix relatifs à la racine.
ZONES = (
    "out/maladies/nuit_1311/", "modeles/maladies_nuit_1311/", "out/comptage/nuit_1311/",
    "modeles/comptage_nuit_1311/", "out/prospection_nuit_1311/", "out/controle_nuit_1311/",
    "scripts/m13_", "scripts/c13_", "notebooks/m13_", "notebooks/c13_", "scripts/controle_1311_",
    "docs/nuit_2026-11-13/",
    # avenant_pistes_2.md (14/11, 18 h 30) : Veille, M-piste2, C-piste2
    "docs/veille_2026-11-14/", "out/maladies/nuit_1311/piste2/", "scripts/m14_", "notebooks/m14_",
    "modeles/maladies_nuit_1411/", "out/comptage/nuit_1311/piste2/", "scripts/c14_", "notebooks/c14_",
    "modeles/comptage_nuit_1411/",
)
# Fichiers non suivis présents avant la nuit (git status de 23 h 35), donc pas des créations de la nuit.
AVANT = ("CONTEXTE_FIELD_SCAN.md", "dataverse_fichiers.json", "docs/plan_nuit_2026-11-13.md",
         "modeles/comptage_v6_essais/", "modeles/maladies/meilleur_v", "modeles/maladies_binome/",
         "modeles/maladies_soupe_v2_v8/", "modeles/maladies_v12_essais/", "modeles/maladies_v5_kaggle/",
         "modeles/maladies_v7_kaggle/", "modeles/maladies_v8_kaggle/", "modeles/maladies_v9_loin_kaggle/")

MOTS_JUGES = re.compile(r"banspot|cordana_perou|test_perou|juge_m|juge_c\b|juge_c/|segmento|banano_dense|"
                        r"test_negatifs|test_dense|test_banano|test_espace|banana_trees_kp|[/\\\"']cg[/\\\"']",
                        re.I)


def rel(p):
    return Path(p).resolve().relative_to(RACINE).as_posix()


def fichiers_juges():
    """Listes (sans ouvrir les images) des fichiers des juges relus et du test vierge, par groupe."""
    g = {}

    def tous(d):
        d = RACINE / d
        return [Path(r) / f for r, _, fs in os.walk(d) for f in fs] if d.exists() else []

    g["M BanSpot (data/raw/banspot)"] = tous("data/raw/banspot")
    g["M BanSpot (out/maladies/banspot)"] = tous("out/maladies/banspot")
    g["M Cordana du Pérou (data/feuilles/images/test_perou)"] = tous("data/feuilles/images/test_perou")
    g["M fichiers *cordana_perou*"] = [p for d in ("out/maladies", "out/controle_nuit_1112", "data")
                                       for p in (RACINE / d).rglob("*cordana_perou*") if p.is_file()]
    g["M juge_m hors vierge"] = [p for p in tous("out/controle_nuit_1112/juge_m") if "vierge" not in p.parts]
    g["C juge_c"] = tous("out/controle_nuit_1112/juge_c")
    g["C banana_trees_kp (test vierge)"] = tous("data/roboflow_nuit_1112/comptage/banana_trees_kp")
    cg, tests = [], []
    import pandas as pd
    for v in ("v3", "v4", "v5", "v6"):
        D = RACINE / f"data/drone/comptage_{v}_5cm"
        cg += tous(D / "cg")
        t = D / "tuiles.csv"
        if t.exists():
            T = pd.read_csv(t, usecols=["image_path", "ensemble"])
            for n in T[T.ensemble.str.startswith("test")].image_path:
                p = D / "images" / n
                if p.exists():
                    tests.append(p)
    g["C dossiers cg/ du comptage"] = cg
    g["C tuiles test_* du comptage"] = tests
    return g


def passage():
    maintenant = dt.datetime.now()
    lignes = [f"Passage du {maintenant:%d/%m %H:%M:%S}", ""]
    alertes = []

    # 1. plan
    sha = hashlib.sha256((RACINE / "docs/plan_nuit_2026-11-13.md").read_bytes()).hexdigest()
    ok = sha == SHA_PLAN
    lignes.append(f"1. SHA-256 du plan : {sha} ({'= attendu' if ok else 'DIFFÉRENT'})")
    if not ok:
        alertes.append("plan de nuit modifié")

    # 2. git
    st = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=RACINE, capture_output=True,
                        text=True, encoding="utf-8").stdout.splitlines()
    modifies = [l for l in st if not l.startswith("??")]
    neufs = [l[3:].strip('"') for l in st if l.startswith("??")]
    neufs_nuit = [n for n in neufs if not n.startswith(AVANT)]
    tete = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RACINE, capture_output=True, text=True).stdout.strip()
    lignes.append(f"2. git : HEAD {tete} ({'= ' + COMMIT_DEPART if tete == COMMIT_DEPART else 'NOUVEAU COMMIT'}) ; "
                  f"suivis modifiés ou supprimés : {len(modifies)} ; non suivis neufs de la nuit : {len(neufs_nuit)}")
    for l in modifies:
        lignes.append(f"   MODIFIÉ : {l}")
    if modifies:
        alertes.append(f"{len(modifies)} fichier(s) suivi(s) modifié(s) : " + ", ".join(modifies[:5]))
    if tete != COMMIT_DEPART:
        alertes.append(f"commit pendant la nuit (HEAD {tete})")

    # 3. accès aux juges
    lignes.append("3. Accès aux juges relus et au test vierge (os.stat, contenu jamais lu) :")
    for nom, fs in fichiers_juges().items():
        acc, mod = [], []
        for p in fs:
            try:
                s = os.stat(p)
            except OSError:
                continue
            if s.st_mtime >= T0:
                mod.append((s.st_mtime, p))
            if s.st_atime >= T_ACCES:
                acc.append((s.st_atime, p))
        lignes.append(f"   {nom} : {len(fs)} fichiers ; accédés depuis {dt.datetime.fromtimestamp(T_ACCES):%d/%m %H:%M} : {len(acc)} ; modifiés : {len(mod)}")
        for t, p in sorted(acc)[-5:]:
            lignes.append(f"      accès {dt.datetime.fromtimestamp(t):%d/%m %H:%M:%S} {rel(p)}")
        for t, p in sorted(mod)[-5:]:
            lignes.append(f"      modif {dt.datetime.fromtimestamp(t):%d/%m %H:%M:%S} {rel(p)}")
        if acc or mod:
            alertes.append(f"accès ou modification de juge : {nom} ({len(acc)} accès, {len(mod)} modif.)")
    # témoins (dossiers sans juge) : un accès simultané ici signale un simple listage (ls -l), pas une lecture
    for d in ("out/analyse_banavista", "out/equateur", "out/cotedivoire", "data/drone/comptage_v5_5cm/mm"):
        fs = [Path(r) / f for r, _, f2 in os.walk(RACINE / d) for f in f2]
        a = [os.stat(p).st_atime for p in fs]
        if a:
            lignes.append(f"   témoin {d} : dernier accès {dt.datetime.fromtimestamp(max(a)):%d/%m %H:%M:%S}")

    # 4 et 5. fichiers neufs ou modifiés depuis T0
    recents = []
    for r, ds, fs in os.walk(RACINE):
        ds[:] = [d for d in ds if d not in (".git", ".venv", "__pycache__")]
        for f in fs:
            p = Path(r) / f
            try:
                s = p.stat()
            except OSError:
                continue
            if s.st_mtime >= T0 or s.st_ctime >= T0:
                recents.append((p, s))
    hors = [rel(p) for p, _ in recents if not rel(p).startswith(ZONES)]
    lignes.append(f"4. Fichiers écrits depuis 23 h 40 : {len(recents)} ; hors des zones du plan : {len(hors)}")
    for h in hors[:40]:
        lignes.append(f"   HORS ZONE : {h}")
    donnees = [h for h in hors if h.startswith("data/")]
    if donnees:
        alertes.append(f"{len(donnees)} fichier(s) neuf(s) sous data/ (téléchargement ?) : " + ", ".join(donnees[:5]))

    code = [p for p, _ in recents if p.suffix in (".py", ".ipynb", ".json", ".yaml", ".yml", ".txt", ".csv", ".md", ".sh")
            and rel(p).startswith(("scripts/m13_", "scripts/c13_", "notebooks/m13_", "notebooks/c13_", "scripts/m14_", "scripts/c14_",
                                   "notebooks/m14_", "notebooks/c14_", "out/maladies/nuit_1311/piste2/", "out/comptage/nuit_1311/piste2/",
                                   "out/maladies/nuit_1311/", "out/comptage/nuit_1311/", "modeles/"))
            and p.stat().st_size < 5_000_000]
    lignes.append(f"5. Recherche de noms de juges dans {len(code)} fichiers de code ou de listes neufs :")
    for p in code:
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        occ = sorted({m.group(0).lower() for m in MOTS_JUGES.finditer(txt)})
        if occ:
            lignes.append(f"   {rel(p)} : {', '.join(occ)}")

    # 6. Kaggle : fichiers neufs à envoyer, comparés en nom et taille aux juges (sans lire les juges)
    juges = {}
    for nom, fs in fichiers_juges().items():
        for p in fs:
            try:
                juges.setdefault((p.name.lower(), p.stat().st_size), nom)
            except OSError:
                pass
    tailles = {}
    for (n, t), g in juges.items():
        tailles.setdefault(t, g)
    images = [(p, s) for p, s in recents if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp")
              and not rel(p).startswith("out/controle_nuit_1311/")]
    zips = [p for p, _ in recents if p.suffix.lower() == ".zip"]
    meta = [rel(p) for p, _ in recents if p.name in ("kernel-metadata.json", "dataset-metadata.json")]
    suspects = []
    for p, s in images:
        if (p.name.lower(), s.st_size) in juges:
            suspects.append(f"{rel(p)} = nom et taille d'un fichier de juge ({juges[(p.name.lower(), s.st_size)]})")
    for z in zips:
        try:
            with zipfile.ZipFile(z) as Z:
                for i in Z.infolist():
                    b = Path(i.filename).name.lower()
                    if (b, i.file_size) in juges:
                        suspects.append(f"{rel(z)}:{i.filename} = nom et taille de juge ({juges[(b, i.file_size)]})")
                    elif MOTS_JUGES.search(i.filename):
                        suspects.append(f"{rel(z)}:{i.filename} porte un nom de juge")
        except (zipfile.BadZipFile, OSError):
            pass
    # dossiers d'envoi Kaggle hors dépôt (C:/Users/coren/kaggle_tmp/m13_*, c13_*)
    kt = Path("C:/Users/coren/kaggle_tmp")
    envoi = [p for d in sorted(list(kt.glob("*13_*")) + list(kt.glob("*14_*"))) for p in d.rglob("*") if p.is_file()] if kt.exists() else []
    for p in envoi:
        try:
            t = p.stat().st_size
        except OSError:
            continue
        if (p.name.lower(), t) in juges:
            suspects.append(f"{p} = nom et taille d'un fichier de juge ({juges[(p.name.lower(), t)]})")
        elif MOTS_JUGES.search(p.as_posix().replace("kaggle_tmp", "")) and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".zip", ".tif"):
            suspects.append(f"{p} porte un nom de juge")
    par_dossier = {}
    for p in envoi:
        k = "/".join(p.relative_to(kt).parts[:2])
        par_dossier[k] = par_dossier.get(k, 0) + 1
    lignes.append(f"6a. Dossiers d'envoi Kaggle (kaggle_tmp/*13_*) : {par_dossier}")
    lignes.append(f"6. Kaggle : métadonnées neuves {meta} ; images neuves {len(images)} ; zip neufs "
                  f"{[rel(z) for z in zips]} ; suspects : {len(suspects)}")
    for s in suspects[:20]:
        lignes.append(f"   SUSPECT : {s}")
    if suspects:
        alertes.append(f"{len(suspects)} fichier(s) préparé(s) identiques en nom et taille à des juges")

    lignes += ["", "ALERTES : " + ("aucune" if not alertes else "")]
    lignes += [f" - {a}" for a in alertes]
    texte = "\n".join(lignes)
    (OUT / f"interdits_{maintenant:%H%M}.txt").write_text(texte, encoding="utf-8")
    print(texte)


if __name__ == "__main__":
    passage()
