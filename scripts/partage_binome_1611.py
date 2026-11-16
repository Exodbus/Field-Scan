#!/usr/bin/env python3
"""Archives demandées par le binôme le 16/11/2026 (sa chaîne, sur des zones qu'elle n'a jamais vues) :
  zone_equateur.zip, zone_cotedivoire.zip : parcelles QGIS (GeoJSON) + bandes Sentinel-2 L2A (B02, B03, B04, B05, B08,
    B8A, B11, B12, carte de classification de scène) aux deux dates disponibles, et un LISEZMOI ;
  comptage_annotes.zip : segmento est, CG (points annotés à la main dans les carrés CG1-CG9) et banana_trees_kp
    (export Roboflow d'origine), et un LISEZMOI.
Sortie : out/partage_binome_1611/. Rien n'est envoyé : c'est Corentin qui transmet.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/partage_binome_1611.py
"""
import csv
import io
import json
import sys
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

OUT = RACINE / "out/partage_binome_1611"
BANDES = ["B02", "B03", "B04", "B05", "B08", "B8A", "B11", "B12", "Scene_classification_map"]

ZONES = {
    "equateur": dict(
        parcelles="parcelles_equateur.geojson", nom="Équateur (près de Machala, El Oro)", crs="EPSG:32717",
        dates={"2023-02-10": "saison des pluies probable", "2023-08-29": "saison sèche probable"},
        note="13 parcelles tracées à la main dans QGIS sur l'image couleur du 10/02/2023 (bananeraies en blocs réguliers)."),
    "cotedivoire": dict(
        parcelles="parcelles_cotedivoire.geojson", nom="Côte d'Ivoire (bords du Bandama, près d'Aoua)", crs="EPSG:32630",
        dates={"2023-06-13": "saison des pluies probable", "2024-01-04": "saison sèche probable"},
        note="33 parcelles tracées à la main dans QGIS sur l'image couleur du 04/01/2024. Attention : culture non "
             "confirmée (bananier probable, palmier à huile ou hévéa possibles). Janvier 2024 est voilé par des "
             "cirrus fins ; juin 2023 est propre sur les parcelles."),
}


def lisez_zone(z, cle, fichiers):
    lignes = [
        f"# Zone {z['nom']}",
        "",
        "Préparé par Corentin (projet Field Scan) le 16/11/2026, pour tester ta chaîne sur une zone qu'elle n'a jamais vue.",
        "",
        "## Contenu",
        f"- `{z['parcelles']}` : parcelles QGIS, {z['crs']}, un identifiant par parcelle (`parcelle_id`).",
        f"- `sentinel2/<date>/` : bandes Sentinel-2 L2A exportées du Copernicus Browser (TIFF 32 bits, réflectance de "
        f"surface, environ 10 m ; les bandes à 20 m ont été rééchantillonnées par l'export).",
    ]
    for d, s in z["dates"].items():
        lignes.append(f"  - {d} : {s} (à vérifier avec des données climatiques).")
    lignes += [
        "- Bandes : " + ", ".join(BANDES) + ".",
        "- **Carte de classification de scène** : c'est l'image **colorée** du Copernicus Browser, pas les codes SCL bruts. "
        "Ses couleurs suivent la palette standard Sentinel-2 ; chez nous, elles sont reconverties en classes "
        "(`fieldscan/` : nuages forte et moyenne probabilité, cirrus, ombres, pixels sombres écartés).",
        "- **Ortho de drone** : aucune sur cette zone.",
        "- **Photos de feuilles géolocalisées** : aucune prise dans ces parcelles.",
        "",
        "## À savoir",
        f"- {z['note']}",
        "- Licence des images : données Copernicus Sentinel, accès libre et ouvert (mention « Contains modified Copernicus "
        "Sentinel data 2023-2024 »).",
        "",
        "## Fichiers",
    ] + [f"- {f}" for f in fichiers]
    return "\n".join(lignes) + "\n"


def zone(cle):
    z = ZONES[cle]
    dest = OUT / f"zone_{cle}.zip"
    fichiers = []
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zo:
        p = RACINE / "data/parcelles" / z["parcelles"]
        zo.write(p, z["parcelles"]); fichiers.append(z["parcelles"])
        for src in sorted((RACINE / "data/sentinel2" / cle).glob("*.zip")):
            date = src.name[:10]
            with zipfile.ZipFile(src) as zi:
                for n in zi.namelist():
                    b = next((b for b in BANDES if f"_L2A_{b}_" in n or n.endswith(f"_L2A_{b}_.tiff")), None)
                    if b is None:
                        continue
                    nom = f"sentinel2/{date}/{b}.tiff"
                    zo.writestr(nom, zi.read(n)); fichiers.append(nom)
        zo.writestr("LISEZMOI.md", lisez_zone(z, cle, fichiers))
    manquantes = [f"{d}/{b}" for d in z["dates"] for b in BANDES if f"sentinel2/{d}/{b}.tiff" not in fichiers]
    print(dest.name, f"{dest.stat().st_size / 1e6:.1f} Mo", len(fichiers), "fichiers ; bandes manquantes :", manquantes or "aucune")


LISEZ_COMPTAGE = """# Jeux de comptage annotés (segmento est, CG, banana_trees_kp)

Préparé par Corentin (projet Field Scan) le 16/11/2026.

**Important** : pour nous, ce sont des **juges et un test**. Merci de ne rien apprendre ni régler dessus, et de ne
noter ton palm3 qu'une fois, comme prévu. Notre v5 a déjà été mesuré dessus ; ses chiffres sont dans
`docs/protocole_comptage_v5.md` (test, lu une fois) : segmento est F1 0,673, CG (mères) F1 0,315.

## segmento est (`segmento_est/`)
- 39 tuiles de plantation dense, ramenées à **5 cm/pixel** (colonne `facteur` de `tuiles.csv` : facteur de réduction
  appliqué à l'image d'origine).
- `objets.csv` : un objet par bananier, centre `cx`, `cy` en pixels de la tuile, `taille`, `type`.
- Source : Roboflow, projet « Plants-bana » (segmento), boîtes d'origine converties en centres. Licence : celle de la page
  Roboflow d'origine, à citer.

## CG (`cg/`)
- 9 carrés de 40 m (CG1 à CG9) tirés au hasard (graine 2026) sur l'orthomosaïque Carlos Vera Guevara de ReforesTree
  (agroforesterie, Équateur), à 5 cm/pixel.
- `points.csv` : un point par bananier **annoté à la main par Corentin** (`type` = `mere` pour les pieds mères).
  `zones.csv` : la zone utile de chaque image (marge de 60 px exclue).
- Notre mesure ne compte que les **mères** ; un point détecté dans la marge n'est pas compté.
- Source des images : ReforesTree (Reiersen et al., 2022), CC BY 4.0. Points : les nôtres.

## banana_trees_kp (`banana_trees_kp/`)
- `banana_trees_kp.zip` : export **COCO d'origine** de Roboflow, sans modification
  (https://universe.roboflow.com/test-purpose/banana-trees-cpzur, version 1 ; `source.json` : date et MD5).
- Échelle variable d'une photo à l'autre (environ 8,6 à 14,3 cm/pixel). Lors de notre lecture unique, les points
  annotés tombaient souvent loin des centres détectés (médiane 45 px) : à vérifier avant de conclure.
- Licence : celle de la page Roboflow, à citer.

## Appariement que nous utilisons (pour comparer)
Pics de la carte de chaleur (fenêtre 7), appariement un à un dans 20 px à 5 cm/pixel (1 m), précision, rappel, F1 ;
erreur de compte = |détectés − annotés| / annotés.
"""


def comptage():
    D = RACINE / "data/drone/comptage_v5_5cm"
    dest = OUT / "comptage_annotes.zip"
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zo:
        T = list(csv.DictReader(open(D / "tuiles.csv", encoding="utf-8")))
        seg = [t for t in T if t["ensemble"] == "test_dense"]
        noms = {t["image_path"] for t in seg}
        for t in seg:
            zo.write(D / "images" / t["image_path"], f"segmento_est/images/{t['image_path']}")
        for nom, lignes in (("tuiles.csv", seg), ("objets.csv", [o for o in csv.DictReader(open(D / "objets.csv", encoding="utf-8")) if o["image_path"] in noms])):
            s = io.StringIO()
            w = csv.DictWriter(s, fieldnames=list(lignes[0].keys()))
            w.writeheader(); w.writerows(lignes)
            zo.writestr(f"segmento_est/{nom}", s.getvalue())
        for f in sorted((D / "cg").rglob("*")):
            if f.is_file():
                zo.write(f, "cg/" + f.relative_to(D / "cg").as_posix())
        K = RACINE / "data/roboflow_nuit_1112/comptage/banana_trees_kp"
        for f in ("banana_trees_kp.zip", "source.json"):
            zo.write(K / f, f"banana_trees_kp/{f}")
        zo.writestr("LISEZMOI.md", LISEZ_COMPTAGE)
    print(dest.name, f"{dest.stat().st_size / 1e6:.1f} Mo ; segmento : {len(seg)} tuiles")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for cle in ZONES:
        zone(cle)
    comptage()
