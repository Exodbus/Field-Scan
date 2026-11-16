#!/usr/bin/env python3
"""A2 « plantain du Ghana » : téléchargement des 199 photos d'origine (lecture seule).

Avenant `docs/journee_2026-11-15/avenant_jeux_neufs.md`, section A2 : réglage « agroforesterie » du
comptage, jamais en apprentissage, en juge ni en test.

Méthode :
- liste des 199 identifiants : `out/prospection_jour_1511/universe/images/m2-eewev__plantain-detection.csv` ;
- pour chaque identifiant, l'API image publique de Roboflow (GET, lecture seule) donne l'adresse
  `source.roboflow.com/.../original.jpg` et les boîtes en pixels d'origine. Rien n'est modifié dans
  aucun espace Roboflow, aucun projet n'est copié ;
- les métadonnées (sans le vecteur « embedding ») vont dans `data/raw/plantain_ghana_m2/meta/<id>.json` ;
- l'original va dans `data/raw/plantain_ghana_m2/images/<nom d'origine>`, en passant par un `.part`,
  avec contrôle de la taille annoncée, décodage complet et dimensions 7 952 × 5 304 ; 4 essais au plus ;
- 3 téléchargements en parallèle.

La clé est lue dans ~/.roboflow/cle_api et n'apparaît dans aucune sortie ni aucun fichier.

Lancement (racine du dépôt) :
    export REQUESTS_CA_BUNDLE=C:/Users/coren/.certificats/bundle_windows.pem SSL_CERT_FILE=$REQUESTS_CA_BUNDLE
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/jeux_neufs_a2_telecharger.py
"""
import csv
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.stdout.reconfigure(encoding="utf-8")  # en mode -I, PYTHONIOENCODING est ignoré

LISTE = RACINE / "out/prospection_jour_1511/universe/images/m2-eewev__plantain-detection.csv"
DEST = RACINE / "data/raw/plantain_ghana_m2"
IMAGES = DEST / "images"
META = DEST / "meta"
PROJET = "m2-eewev/plantain-detection"
TAILLE = (7952, 5304)
PARALLELE = 3
ESSAIS = 4

Image.MAX_IMAGE_PIXELS = 60_000_000  # 42 Mpx attendus


def cle_api():
    return (Path.home() / ".roboflow" / "cle_api").read_text().strip()


def sans_cle(texte, cle):
    return texte.replace(cle, "<CLE>")


def lire_meta(iid, cle):
    f = META / f"{iid}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    for essai in range(ESSAIS):
        try:
            r = requests.get(f"https://api.roboflow.com/{PROJET}/images/{iid}", params={"api_key": cle}, timeout=90)
            if r.status_code == 200:
                j = json.loads(sans_cle(r.text, cle))["image"]
                j.pop("embedding", None)
                f.write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")
                return j
            print(f"  {iid} : API statut {r.status_code}", flush=True)
        except Exception as e:  # la clé ne sort jamais : seul le type d'erreur est affiché
            print(f"  {iid} : API erreur {type(e).__name__}", flush=True)
        time.sleep(3 * (essai + 1))
    raise RuntimeError(f"métadonnées introuvables pour {iid}")


def image_valide(chemin):
    try:
        with Image.open(chemin) as im:
            if im.format not in ("JPEG", "MPO") or im.size != TAILLE:  # MPO : JPEG avec aperçu intégré
                return False, f"format {im.format} taille {im.size}"
            im.load()  # décodage complet : détecte un fichier tronqué
        return True, "ok"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def telecharger(iid, nom, url):
    dest = IMAGES / nom
    if dest.exists():
        ok, msg = image_valide(dest)
        if ok:
            return nom, dest.stat().st_size, "déjà là"
        print(f"  {nom} présent mais invalide ({msg}) : nouvel essai", flush=True)
        dest.unlink()
    part = dest.with_suffix(dest.suffix + ".part")
    for essai in range(ESSAIS):
        try:
            with requests.get(url, stream=True, timeout=(30, 120)) as r:
                r.raise_for_status()
                attendu = int(r.headers.get("Content-Length", "0"))
                with open(part, "wb") as fh:
                    for bloc in r.iter_content(1 << 20):
                        fh.write(bloc)
            recu = part.stat().st_size
            if attendu and recu != attendu:
                raise IOError(f"tronqué : {recu} / {attendu} octets")
            ok, msg = image_valide(part)
            if not ok:
                raise IOError(f"image invalide : {msg}")
            part.replace(dest)
            return nom, recu, f"essai {essai + 1}"
        except Exception as e:
            print(f"  {nom} : essai {essai + 1} échoué ({type(e).__name__}: {str(e)[:120]})", flush=True)
            if part.exists():
                part.unlink()
            time.sleep(5 * (essai + 1))
    raise RuntimeError(f"échec définitif : {nom}")


def sha256(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as fh:
        for bloc in iter(lambda: fh.read(1 << 22), b""):
            h.update(bloc)
    return h.hexdigest()


def main():
    IMAGES.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)
    with open(LISTE, encoding="utf-8") as fh:
        lignes = list(csv.DictReader(fh))
    print(f"{len(lignes)} images à traiter", flush=True)
    cle = cle_api()
    taches = []
    for i, l in enumerate(lignes):
        j = lire_meta(l["id"], cle)
        url = j["urls"]["original"]
        assert url.startswith("https://source.roboflow.com/") and "api_key" not in url
        assert j["name"] == l["nom"], (j["name"], l["nom"])
        taches.append((l["id"], l["nom"], url))
        if (i + 1) % 50 == 0:
            print(f"  métadonnées : {i + 1}", flush=True)
            time.sleep(0.5)
    del cle

    t0 = time.time()
    total, faits = 0, 0
    with ThreadPoolExecutor(PARALLELE) as ex:
        for nom, octets, etat in ex.map(lambda t: telecharger(*t), taches):
            faits += 1
            total += octets
            if faits % 10 == 0 or faits == len(taches):
                print(f"  {faits}/{len(taches)} ({total / 1e9:.2f} Go, {time.time() - t0:.0f} s) dernier : {nom} {etat}",
                      flush=True)

    # empreintes, dans l'ordre des noms
    lignes_sha = []
    for nom in sorted(t[1] for t in taches):
        lignes_sha.append(f"{sha256(IMAGES / nom)}  images/{nom}")
    (DEST / "sha256.txt").write_text("\n".join(lignes_sha) + "\n", encoding="utf-8")
    print(f"terminé : {len(taches)} images, {total / 1e9:.3f} Go ; sha256.txt écrit", flush=True)


if __name__ == "__main__":
    main()
