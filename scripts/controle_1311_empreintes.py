#!/usr/bin/env python3
"""Contrôleur, nuit du 13/11 : SHA-256 des fichiers nécessaires pour relire la liste gelée (modèles, scripts, définitions,
probabilités et cartes de réglage utiles au Juge), écrits dans out/controle_nuit_1311/empreintes_liste_gelee.txt.
Liste des fichiers : arguments (chemins ou motifs glob relatifs à la racine du dépôt).
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_1311_empreintes.py <motif> [...]
"""
import datetime as dt
import hashlib
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sortie = RACINE / "out/controle_nuit_1311/empreintes_liste_gelee.txt"
vus, lignes = set(), []
for motif in sys.argv[1:]:
    if motif.startswith("#"):
        lignes.append(motif)
        continue
    fichiers = sorted(RACINE.glob(motif)) or [RACINE / motif]
    for f in fichiers:
        r = f.relative_to(RACINE).as_posix()
        if r in vus:
            continue
        vus.add(r)
        if not f.is_file():
            lignes.append(f"ABSENT  {r}")
            continue
        h = hashlib.sha256()
        with open(f, "rb") as fh:
            for bloc in iter(lambda: fh.read(1 << 20), b""):
                h.update(bloc)
        lignes.append(f"{h.hexdigest()}  {r}")
tete = f"# SHA-256 des fichiers de la liste gelée (Contrôleur, {dt.datetime.now():%d/%m/%Y %H:%M})"
sortie.write_text("\n".join([tete] + lignes) + "\n", encoding="utf-8")
print(f"{len(vus)} fichiers -> {sortie.relative_to(RACINE).as_posix()}")
