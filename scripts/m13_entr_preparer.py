#!/usr/bin/env python3
"""M-entraîneur (nuit du 13/11) : jeu Kaggle privé « m13-entr-outils » et contrôle de fuite avant l'envoi.

Contenu : poids de la soupe v2 + v8 (lecteur de F1), aiguilleur.npz, poids de la v9 « loin » (ME3), et AgroVisionBD
(jeu de RÉGLAGE, jamais appris) déjà préparé : photo décodée comme la chaîne (JPEG lu en 896 px, EXIF), recadrée en
384 x 384 (ImageOps.fit, BILINEAR), enregistrée en PNG sans perte. Le carnet refait JPEG 95 + normalisation : tenseur
identique à fieldscan.modules.maladies.preparer_convnext(taille=384, lecture=896) (contrôlé ici sur 20 photos).

Contrôle de fuite : aucun fichier envoyé (ni aucune photo d'origine d'AgroVisionBD) n'a le MD5 d'une image juge
(BanSpot : tout data/raw/banspot ; Cordana du Pérou : data/feuilles/images/test_perou) ; aucun nom ne contient
banspot, cordana, test_perou, SIG_PER, SYMPTOMATIC.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_entr_preparer.py [envoyer]
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageOps

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from fieldscan.modules import maladies  # noqa: E402

DOS = Path("C:/Users/coren/kaggle_tmp/m13_outils")
INTERDITS = ("banspot", "cordana_perou", "test_perou", "sig_per", "symptomatic")   # « cordana » seul est un nom de classe d'AgroVisionBD


def md5(f):
    return hashlib.md5(Path(f).read_bytes()).hexdigest()


def prep_png(chemin):
    with Image.open(chemin) as im:
        im.draft("RGB", (896, 896))
        im = ImageOps.exif_transpose(im).convert("RGB")
        return ImageOps.fit(im, (384, 384), method=Image.BILINEAR)


def depuis_png(f):
    """Ce que fait le carnet : ouverture, fit 384 (sans effet), JPEG 95, normalisation."""
    with Image.open(f) as im:
        im = im.convert("RGB")
        petite = ImageOps.fit(im, (384, 384), method=Image.BILINEAR)
    t = io.BytesIO(); petite.save(t, format="JPEG", quality=95)
    a = np.asarray(Image.open(t).convert("RGB"), dtype="float32") / 255.0
    a = (a - np.asarray(maladies.IMAGENET[0], "float32")) / np.asarray(maladies.IMAGENET[1], "float32")
    return a.transpose(2, 0, 1)


if __name__ == "__main__":
    reprise = DOS.exists() and len(list((DOS / "agrovision_384").glob("*.png"))) == 1082 and (DOS / "agrovision_384.csv").exists()
    if DOS.exists() and not reprise:
        shutil.rmtree(DOS)
    (DOS / "agrovision_384").mkdir(parents=True, exist_ok=True)
    (DOS / "soupe").mkdir(exist_ok=True); (DOS / "v9_loin").mkdir(exist_ok=True)
    for f in sorted((RACINE / "modeles/maladies_soupe_v2_v8/poids").iterdir()):
        shutil.copy(f, DOS / "soupe" / f.name)
    for f in sorted((RACINE / "modeles/maladies_v9_loin_kaggle/v9").glob("*.pt")) + [RACINE / "modeles/maladies_v9_loin_kaggle/v9/seuils.json"]:
        shutil.copy(f, DOS / "v9_loin" / f.name)
    shutil.copy(RACINE / "modeles/maladies_aiguilleur/aiguilleur.npz", DOS / "aiguilleur.npz")
    a = pd.read_csv(RACINE / "data/raw/nuit_1112/figshare_agrovisionbd_bangladesh/liste.csv")
    a = a[a.retenue].reset_index(drop=True)
    assert len(a) == 1082
    noms = []
    for k, c in enumerate(a.chemin):
        n = f"agro_{k:04d}.png"
        if not reprise:
            prep_png(RACINE / c).save(DOS / "agrovision_384" / n)
        noms.append("agrovision_384/" + n)
    a2 = pd.DataFrame(dict(chemin=a.chemin, png=noms, classe_vraie=a.classe, jeu="agrovision"))
    a2.to_csv(DOS / "agrovision_384.csv", index=False)
    # exactitude de la préparation (20 photos)
    ecart = max(float(np.abs(depuis_png(DOS / a2.png[k]) - maladies.preparer_convnext(str(RACINE / a2.chemin[k]), taille=384, lecture=896)).max())
                for k in range(0, 1082, 54))
    print("écart maximal de préparation (20 photos) :", ecart)
    assert ecart == 0.0
    # contrôle de fuite
    juges = {md5(p) for p in (RACINE / "data/raw/banspot").rglob("*") if p.is_file()}
    juges |= {md5(p) for p in (RACINE / "data/feuilles/images/test_perou").rglob("*") if p.is_file()}
    envoyes = [p for p in DOS.rglob("*") if p.is_file()]
    origines = [RACINE / c for c in a.chemin]
    commun = [str(p) for p in envoyes + origines if md5(p) in juges]
    noms_suspects = [str(p) for p in envoyes + origines if any(s in str(p).lower() for s in INTERDITS)]
    print(f"juges : {len(juges)} MD5 ; envoyés : {len(envoyes)} fichiers ; photos d'origine AgroVisionBD : {len(origines)}")
    print("MD5 communs avec un juge :", commun, "| noms suspects :", noms_suspects)
    assert not commun and not noms_suspects
    (DOS / "dataset-metadata.json").write_text(json.dumps({"title": "m13-entr-outils", "id": "affilecorentin/m13-entr-outils",
                                                          "licenses": [{"name": "other"}]}, indent=1), encoding="utf-8")
    (RACINE / "out/maladies/nuit_1311/kaggle/controle_fuite_outils.json").write_text(json.dumps(dict(
        md5_juges=len(juges), fichiers_envoyes=len(envoyes), origines_agrovision=len(origines), communs=commun,
        noms_suspects=noms_suspects, ecart_preparation=ecart), ensure_ascii=False, indent=1), encoding="utf-8")
    if len(sys.argv) > 1 and sys.argv[1] == "envoyer":
        env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
                   SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
        r = subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "datasets", "create", "-p", str(DOS), "-r", "zip"], env=env)
        sys.exit(r.returncode)
