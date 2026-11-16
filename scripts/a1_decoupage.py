#!/usr/bin/env python3
"""A1 PlantVillage / Penn State : inventaire des annotations XML et découpage A1-test / A1-appr. Aucun modèle.

Règle (avenant du 15/11, section A1, appliquée à la lettre) :
  - le lot est le champ « ferme », « lieu » ou « date » des annotations s'il existe (le premier des trois qui
    existe) ; lots triés par nom, un sur deux : impairs -> A1-test, pairs -> A1-appr ;
  - sans aucun de ces champs : blocs de 50 noms de fichiers consécutifs (tri alphabétique), un bloc sur deux,
    en commençant par A1-test.
Les champs cherchés : toute balise XML dont le nom (sans casse) est l'un de
  ferme, farm, lieu, location, place, site, date, datetime, date_taken (synonymes anglais compris).

Sorties : out/jeux_neufs_1611/a1_decoupage.csv, a1_inventaire_xml.json.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/a1_decoupage.py
"""
import collections
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.stdout.reconfigure(encoding="utf-8")

EXTRAIT = RACINE / "data/raw/plantvillage_psu/extrait"
OUT = RACINE / "out/jeux_neufs_1611"
CHAMPS = {"ferme": ("ferme", "farm"), "lieu": ("lieu", "location", "place", "site"),
          "date": ("date", "datetime", "date_taken")}
BLOC = 50


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    photos = sorted(p.name for p in (EXTRAIT / "bxw-leaf").glob("*.jpg"))
    balises = collections.Counter()
    trouves = {k: 0 for k in CHAMPS}
    infos = {}
    for nom in photos:
        x = EXTRAIT / "annotations_bxw_leaf" / (Path(nom).stem + ".xml")
        r = ET.parse(x).getroot()
        tags = [e.tag for e in r.iter()]
        balises.update(set(tags))
        for k, syn in CHAMPS.items():
            if any(t.lower() in syn for t in tags):
                trouves[k] += 1
        objets = [o.findtext("name") for o in r.findall("object")]
        infos[nom] = dict(pays=nom.split("_")[3], nom_xml=r.findtext("filename"), dossier_xml=r.findtext("folder"),
                          n_bxw=sum(o == "banana_BXW_leaf" for o in objets), objets=";".join(objets))
    champ = next((k for k in CHAMPS if trouves[k] == len(photos)), None)
    partiel = {k: v for k, v in trouves.items() if 0 < v < len(photos)}

    lignes = []
    if champ is None:
        regle = f"blocs de {BLOC} noms consécutifs (aucun champ ferme, lieu ou date dans les annotations)"
        for i, nom in enumerate(photos):
            b = i // BLOC
            lignes.append(dict(nom=nom, lot=f"bloc_{b + 1:02d}", role="A1-test" if b % 2 == 0 else "A1-appr",
                               **infos[nom]))
    else:  # non utilisé ici, écrit pour que la règle soit complète
        raise SystemExit(f"champ {champ} trouvé : appliquer la règle par lot (non prévu par ce script)")

    with open(OUT / "a1_decoupage.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["nom", "lot", "role", "pays", "nom_xml", "dossier_xml", "n_bxw", "objets"])
        w.writeheader()
        w.writerows(lignes)
    resume = collections.Counter((l["lot"], l["role"], l["pays"]) for l in lignes)
    inv = dict(photos=len(photos), balises=dict(balises), champs_ferme_lieu_date=trouves, partiels=partiel,
               regle=regle,
               sans_boite_bxw=[n for n, i in infos.items() if i["n_bxw"] == 0],
               lots=[dict(lot=a, role=b, pays=c, n=n) for (a, b, c), n in sorted(resume.items())],
               roles=dict(collections.Counter(l["role"] for l in lignes)),
               roles_pays={f"{r}|{p}": n for (r, p), n in
                           sorted(collections.Counter((l["role"], l["pays"]) for l in lignes).items())},
               nom_xml_motifs=dict(collections.Counter(
                   (l["pays"], re.sub(r"\d+", "N", l["nom_xml"] or "")) for l in lignes).most_common()) and
               {f"{p}|{m}": n for (p, m), n in collections.Counter(
                   (l["pays"], re.sub(r"\d+", "N", l["nom_xml"] or "")) for l in lignes).most_common()})
    (OUT / "a1_inventaire_xml.json").write_text(json.dumps(inv, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(inv, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
