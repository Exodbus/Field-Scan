"""Télécharge un jeu public de Mendeley Data, fichier par fichier, en vérifiant le SHA-256 annoncé par l'API.

Usage : python scripts/telecharger_mendeley.py wfzpdmc5vx data/raw/mendeley_wfzpdmc5vx
Le jeu va dans son propre dossier ; rien n'y est exécuté. Une liste `fichiers.csv` (nom, dossier, taille, sha256) est écrite.
Certificat : variable SSL_CERT_FILE (contournement Norton, voir la mémoire du projet).
"""
import csv, hashlib, json, os, ssl, sys, time, urllib.request
from pathlib import Path

jeu, dest = sys.argv[1], Path(sys.argv[2])
dest.mkdir(parents=True, exist_ok=True)
ctx = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE"))
ENTETES = {"User-Agent": "Mozilla/5.0 (field-scan, projet etudiant)"}


def lire(url):
    for essai in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=ENTETES), context=ctx, timeout=120) as r:
                return r.read()
        except Exception as e:  # nouvel essai après une pause
            if essai == 3:
                raise
            time.sleep(3 * (essai + 1))


meta = json.loads(lire(f"https://data.mendeley.com/public-api/datasets/{jeu}"))
(dest / "metadonnees.json").write_text(json.dumps({k: v for k, v in meta.items() if k != "files"}, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
lignes = []
for f in meta["files"]:
    c = f["content_details"]
    nom, dossier = f["filename"], (f.get("folder") or {}).get("name", "") if isinstance(f.get("folder"), dict) else ""
    cible = dest / "fichiers" / nom
    cible.parent.mkdir(parents=True, exist_ok=True)
    if not (cible.exists() and hashlib.sha256(cible.read_bytes()).hexdigest() == c["sha256_hash"]):
        donnees = lire(c["download_url"])
        if hashlib.sha256(donnees).hexdigest() != c["sha256_hash"]:
            raise RuntimeError(f"SHA-256 différent pour {nom}")
        cible.write_bytes(donnees)
    lignes.append(dict(fichier=nom, dossier=dossier, taille=c.get("size", f.get("size")), sha256=c["sha256_hash"]))
with open(dest / "fichiers.csv", "w", encoding="utf-8", newline="") as o:
    w = csv.DictWriter(o, fieldnames=list(lignes[0]))
    w.writeheader(); w.writerows(lignes)
print(f"{jeu} : {len(lignes)} fichiers, SHA-256 vérifiés -> {dest}")
