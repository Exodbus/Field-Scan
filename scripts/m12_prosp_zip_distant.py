#!/usr/bin/env python3
"""Nuit du 12/11 (D-maladies) : lit un grand zip distant par morceaux (requêtes HTTP Range) et n'en extrait
que les fichiers voulus. Sert pour AgroVisionBD (Figshare, 17,7 Go, dont seules les feuilles de bananier nous
intéressent). Rien n'est exécuté ; les fichiers extraits vont dans leur propre dossier.

    python scripts/m12_prosp_zip_distant.py URL DOSSIER --liste            (liste du contenu dans DOSSIER/contenu_zip.csv)
    python scripts/m12_prosp_zip_distant.py URL DOSSIER --motif REGEX      (extrait les noms qui correspondent)
Certificat : variable SSL_CERT_FILE (contournement Norton).
"""
import argparse
import csv
import io
import os
import re
import ssl
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CTX = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE"))
ENTETES = {"User-Agent": "client-recherche/1.0"}


def lire_plage(url, debut, fin):
    for essai in range(6):
        try:
            req = urllib.request.Request(url, headers={**ENTETES, "Range": f"bytes={debut}-{fin}"})
            with urllib.request.urlopen(req, context=CTX, timeout=180) as r:
                d = r.read()
            if len(d) == fin - debut + 1:
                return d
        except Exception:
            pass
        time.sleep(2 * (essai + 1))
    raise RuntimeError(f"plage {debut}-{fin} illisible")


class FichierDistant(io.RawIOBase):
    def __init__(self, url):
        self.url = url
        req = urllib.request.Request(url, headers={**ENTETES, "Range": "bytes=0-0"})
        with urllib.request.urlopen(req, context=CTX, timeout=60) as r:
            self.taille = int(r.headers["Content-Range"].split("/")[1])
        self.pos = 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.taille + off
        return self.pos

    def tell(self):
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.taille - self.pos
        n = min(n, self.taille - self.pos)
        if n <= 0:
            return b""
        d = lire_plage(self.url, self.pos, self.pos + n - 1)
        self.pos += len(d)
        return d

    def readinto(self, b):
        d = self.read(len(b))
        b[:len(d)] = d
        return len(d)


def extraire(url, info, cible):
    """Lit l'en-tête local puis les données compressées d'une entrée, en deux requêtes."""
    en_tete = lire_plage(url, info.header_offset, info.header_offset + 29)
    n_nom, n_extra = int.from_bytes(en_tete[26:28], "little"), int.from_bytes(en_tete[28:30], "little")
    debut = info.header_offset + 30 + n_nom + n_extra
    brut = lire_plage(url, debut, debut + info.compress_size - 1) if info.compress_size else b""
    if info.compress_type == zipfile.ZIP_STORED:
        d = brut
    elif info.compress_type == zipfile.ZIP_DEFLATED:
        import zlib
        d = zlib.decompress(brut, -15)
    else:
        raise RuntimeError(f"compression {info.compress_type} non gérée")
    import zlib
    if zlib.crc32(d) & 0xFFFFFFFF != info.CRC:
        raise RuntimeError(f"CRC différent : {info.filename}")
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_bytes(d)
    return len(d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url"); ap.add_argument("dossier")
    ap.add_argument("--liste", action="store_true"); ap.add_argument("--motif")
    a = ap.parse_args()
    dest = Path(a.dossier); dest.mkdir(parents=True, exist_ok=True)
    f = FichierDistant(a.url)
    z = zipfile.ZipFile(io.BufferedReader(f, buffer_size=1 << 20))
    infos = z.infolist()
    with open(dest / "contenu_zip.csv", "w", encoding="utf-8", newline="") as o:
        w = csv.writer(o); w.writerow(["nom", "taille", "taille_compressee", "crc"])
        for i in infos:
            w.writerow([i.filename, i.file_size, i.compress_size, f"{i.CRC:08x}"])
    print(f"{len(infos)} entrées, zip de {f.taille / 1e9:.2f} Go", flush=True)
    if not a.motif:
        return
    rx = re.compile(a.motif)
    choisis = [i for i in infos if not i.is_dir() and rx.search(i.filename)]
    print(f"{len(choisis)} fichiers à extraire, {sum(i.compress_size for i in choisis) / 1e9:.2f} Go", flush=True)
    fait = [0]

    def un(i):
        c = dest / "fichiers" / i.filename
        if c.exists() and c.stat().st_size == i.file_size:
            return
        extraire(a.url, i, c)
        fait[0] += 1
        if fait[0] % 100 == 0:
            print(f"  {fait[0]}/{len(choisis)}", flush=True)
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(un, choisis))
    print("fini", flush=True)


if __name__ == "__main__":
    main()
