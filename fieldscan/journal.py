"""Journal d'exécution : événements, durées, versions et empreintes des entrées (journal.json)."""
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

PAQUETS = ["numpy", "pandas", "rasterio", "geopandas", "shapely", "pyproj", "Pillow", "PyYAML",
           "onnxruntime", "torch", "torchvision", "deepforest"]


def empreinte(chemin, taille_bloc=1 << 20):
    """Empreinte rapide : SHA-256 du premier et du dernier mégaoctet, plus la taille (fichiers volumineux)."""
    p = Path(chemin)
    h = hashlib.sha256(str(p.stat().st_size).encode())
    with open(p, "rb") as f:
        h.update(f.read(taille_bloc))
        if p.stat().st_size > taille_bloc:
            f.seek(-taille_bloc, 2)
            h.update(f.read(taille_bloc))
    return h.hexdigest()[:16]


class Journal:
    def __init__(self):
        self.debut = time.time()
        self.evenements, self.durees, self.infos = [], {}, {}

    def note(self, niveau, message, **details):
        self.evenements.append(dict(t=round(time.time() - self.debut, 1), niveau=niveau, message=message, **details))
        prefixe = {"info": "", "avertissement": "Attention : ", "erreur": "ERREUR : "}.get(niveau, "")
        print(f"{prefixe}{message}")

    def info(self, m, **d): self.note("info", m, **d)
    def avertir(self, m, **d): self.note("avertissement", m, **d)
    def erreur(self, m, **d): self.note("erreur", m, **d)

    def chrono(self, nom, secondes):
        self.durees[nom] = round(secondes, 1)

    def ecrire(self, chemin):
        versions = {"python": platform.python_version()}
        for p in PAQUETS:
            try:
                versions[p] = metadata.version(p)
            except metadata.PackageNotFoundError:
                pass
        contenu = dict(date=datetime.now(timezone.utc).isoformat(timespec="seconds"), duree_totale_s=round(time.time() - self.debut, 1),
                       durees_s=self.durees, versions=versions, **self.infos, evenements=self.evenements)
        Path(chemin).write_text(json.dumps(contenu, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
