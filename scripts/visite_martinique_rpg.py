#!/usr/bin/env python3
"""Visite 3D de Basse-Pointe avec les parcelles déclarées (RPG) à la place des parcelles automatiques.

Reprend scripts/visite_martinique_preparer.py (importé, non modifié) avec trois changements :
  1. parcelles : out/demo_martinique_rpg/parcelles_rpg_utm.geojson (RPG découpé sur l'orthophoto,
     scripts/demo_martinique_rpg.py) ; bulletin et alertes de la chaîne relancée sur ces parcelles
     (out/demo_martinique_rpg/chaine/, run.py --modules vigueur) ;
  2. où poser des bananiers 3D : sur les parcelles déclarées « Banane (export) » (code BEF), et seulement là. La règle
     « bananeraie » par Fourier ne décide plus ; l'analyse de Fourier sert seulement à aligner les rangs 3D sur les rangs
     de la photo ;
  3. dans une parcelle déclarée en banane, une fenêtre sans rangs nets sur la photo (couvert fermé) reçoit la direction
     et la période médianes des fenêtres à rangs nets de la même parcelle (phase tirée au hasard) ; une parcelle sans
     aucune fenêtre à rangs nets prend la direction du grand côté de son rectangle englobant minimal et une période de
     2,8 m [H]. Les filtres de la photo restent : pas de bananier sur les allées sombres, le sol nu, les pistes.

Les tuiles de l'orthophoto, la mini-carte, bananiers.glb et la page viennent de out/visite_martinique/ (copiés).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/visite_martinique_rpg.py
"""
import gzip
import json
import math
import shutil
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))

import geopandas as gpd  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import visite_martinique_preparer as vm  # noqa: E402

DOSSIER_RPG = RACINE / "out/demo_martinique_rpg"
SOURCE_VISITE = RACINE / "out/visite_martinique"
vm.PARCELLES = DOSSIER_RPG / "parcelles_rpg_utm.geojson"
vm.BULLETIN = DOSSIER_RPG / "chaine/bulletin.csv"
vm.ALERTES = DOSSIER_RPG / "chaine/alertes.geojson"
vm.SORTIE = RACINE / "out/visite_martinique_rpg"
CODE_BANANE = "BEF"
PERIODE_DEFAUT_M = 2.8        # [H] rang simple, si la photo ne montre aucun rang net dans la parcelle
PAS_SYNTH_M = 25.0            # grille des fenêtres créées dans une parcelle trop étroite pour une fenêtre de 51 m


def copier_commun(d):
    d.mkdir(parents=True, exist_ok=True)
    (d / "travail").mkdir(exist_ok=True)
    for nom in ("tuiles", "minicarte.jpg", "bananiers.glb"):
        s, c = SOURCE_VISITE / nom, d / nom
        if s.is_dir():
            if not c.exists():
                shutil.copytree(s, c)
        else:
            shutil.copy2(s, c)


REMPLACEMENTS_PAGE = [
    # bandeau, aide, licence
    ("photo IGN, parcelles automatiques, scores et alertes de la chaîne",
     "photo IGN, parcelles déclarées (RPG), scores et alertes de la chaîne"),
    ("bananiers 3D posés sur les rangs de la photo —",
     "bananiers 3D sur les parcelles déclarées en banane —"),
    ("les 196 parcelles découpées automatiquement, leurs scores",
     "les parcelles déclarées par les exploitants (RPG de l'IGN) et leur culture, leurs scores"),
    ("seulement sur les parcelles où une règle écrite y voit des rangs de bananiers.",
     "seulement sur les parcelles déclarées en banane, alignés sur les rangs de la photo quand ils sont visibles."),
    ("Photo : IGN, BD ORTHO® · Licence Ouverte Etalab 2.0",
     "Photo : IGN, BD ORTHO® · Parcelles : IGN, RPG · Licence Ouverte Etalab 2.0"),
    # fiche : culture déclarée
    ("<dt>Surface</dt><dd id=\"f-surface\"></dd>",
     "<dt>Culture déclarée</dt><dd id=\"f-culture\"></dd>\n    <dt>Surface</dt><dd id=\"f-surface\"></dd>"),
    ("  $('f-surface').textContent = `${fmt(p.surface_ha, 2)} ha`;",
     "  $('f-culture').textContent = p.culture || '–';\n  $('f-surface').textContent = `${fmt(p.surface_ha, 2)} ha`;"),
    ("    ? `Rangs de bananiers vus sur la photo (direction ${fmt(r.dir_rang_deg, 0)}° depuis l'est, période ${fmt(r.periode_mediane_m, 1)} m). ` +",
     "    ? `Parcelle déclarée en banane. Rangs 3D : direction ${fmt(r.dir_rang_deg, 0)}° depuis l'est, période ${fmt(r.periode_mediane_m, 1)} m ` +\n"
     "      `(${r.rangs && r.rangs.fenetres_photo ? 'alignés sur les rangs vus sur la photo' : 'aucun rang net sur la photo : direction du grand côté'}). ` +"),
    ("? '' : ' · sans bananiers 3D'}`;", "? ' · banane' : ' · ' + (p.culture || 'autre')}`;"),
    ("$('aide-sous').textContent = `390 ha de bananeraies à Basse-Pointe (nord-est de la Martinique), ${parcelles.length} parcelles. ` +",
     "$('aide-sous').textContent = `${fmt(D.rpg.surface_totale_ha, 0)} ha à Basse-Pointe (nord-est de la Martinique), ${parcelles.length} parcelles déclarées, ` +\n"
     "  `dont ${D.rpg.n_banane} en banane (${fmt(D.rpg.surface_banane_ha, 0)} ha). ` +"),
]


def adapter_page(d):
    html = (SOURCE_VISITE / "index.html").read_text(encoding="utf-8")
    for avant, apres in REMPLACEMENTS_PAGE:
        assert html.count(avant) == 1, f"texte introuvable ou ambigu dans la page : {avant[:60]}"
        html = html.replace(avant, apres)
    (d / "index.html").write_text(html, encoding="utf-8")


def onde(dir_rang_deg, periode):
    """Vecteur d'onde (cycles/m) perpendiculaire aux rangs de direction dir_rang_deg (depuis l'est)."""
    a = math.radians(dir_rang_deg - 90)
    return math.cos(a) / periode, math.sin(a) / periode


def completer_fenetres(r, geom, rng):
    """Parcelle déclarée en banane : toutes ses fenêtres portent des rangs (voir l'en-tête, point 3)."""
    fen = r["fenetres"]
    nettes = [f for f in fen if f.get("rangs")]
    if nettes:
        moy, _ = vm.direction_axiale(nettes)
        dir_rang = (moy + 90) % 180
        per = float(np.median([f["periode"] for f in nettes]))
        claires = float(np.mean([f["plantes_claires"] for f in nettes])) >= 0.5
        origine = "médiane des rangs nets de la parcelle"
    else:
        rect = geom.minimum_rotated_rectangle
        xy = np.array(rect.exterior.coords)[:4]
        cotes = [xy[(i + 1) % 4] - xy[i] for i in range(4)]
        long_ = max(cotes, key=np.linalg.norm)
        dir_rang = math.degrees(math.atan2(long_[1], long_[0])) % 180
        per, claires = PERIODE_DEFAUT_M, True
        origine = "grand côté de la parcelle (aucun rang net sur la photo) [H]"
    kx, ky = onde(dir_rang, per)
    if not fen:                                     # parcelle trop étroite : fenêtres synthétiques sur une grille
        plantable = geom.buffer(-vm.RETRAIT_BANANIERS_M)
        x0, y0, x1, y1 = geom.bounds
        for x in np.arange(x0 + PAS_SYNTH_M / 2, x1, PAS_SYNTH_M):
            for y in np.arange(y0 + PAS_SYNTH_M / 2, y1, PAS_SYNTH_M):
                fen.append(dict(x=float(x), y=float(y), part=0.0, pic=0.0, periodique=False))
        if not fen or plantable.is_empty:
            c = geom.representative_point()
            fen.append(dict(x=c.x, y=c.y, part=0.0, pic=0.0, periodique=False))
    n_synth = 0
    for f in fen:
        if f.get("rangs"):
            continue
        f.update(kx=kx, ky=ky, periode=per, dir_rang_deg=round(dir_rang, 1), plantes_claires=claires,
                 phase=float(rng.uniform(0, 2 * math.pi)), coherence_exg=0.0, rangs=True, synthetique=True)
        n_synth += 1
    return dict(dir_rang_deg=round(dir_rang, 1), periode_m=round(per, 2), origine=origine,
                fenetres_photo=len(nettes), fenetres_completees=n_synth)


def main():
    t = time.time()
    d = vm.SORTIE
    copier_commun(d)
    adapter_page(d)
    img, tr, b = vm.lire_ortho()
    parcelles = gpd.read_file(vm.PARCELLES)
    assert parcelles.crs.to_epsg() == 5490
    culture = dict(zip(parcelles.parcelle_id, parcelles.culture_code))
    libelle = dict(zip(parcelles.parcelle_id, parcelles.culture))
    bulletin = pd.read_csv(vm.BULLETIN, encoding="utf-8")
    if "comptage_n_pieds" not in bulletin.columns:
        bulletin["comptage_n_pieds"] = 0            # chaîne relancée sans le comptage (muet sur cette photo)
    alertes = gpd.read_file(vm.ALERTES).to_crs(5490)
    zones = alertes[alertes["type"] == "zone_faible"].copy()
    zones["geometry"] = zones.geometry.make_valid()
    tuiles = json.loads((d / "tuiles/tuiles.json").read_text(encoding="utf-8"))

    fourier = vm.etape_fourier(img, tr, parcelles, bulletin, d)
    geoms = dict(zip(parcelles.parcelle_id, parcelles.geometry))
    rng = np.random.default_rng(2026)
    for r in fourier:
        pid = r["parcelle_id"]
        v = r["verdict"]
        v["regle_photo"] = dict(bananeraie=v["bananeraie"], motif=v.get("motif"))   # pour information
        v["culture_code"], v["culture"] = culture[pid], libelle[pid]
        sol_nu = r.get("g_moins_r_med") is None or r["g_moins_r_med"] <= vm.G_MOINS_R_MIN
        if culture[pid] == CODE_BANANE and sol_nu:
            # déclarée en banane (RPG, millésime antérieur) mais surtout du sol nu sur la photo de 2025 : replantation
            # ou jachère probable [H] ; pas de bananiers 3D
            v.update(bananeraie=False, motif="déclarée en banane (RPG), mais la photo de 2025 montre surtout du sol nu "
                                             "(replantation ou jachère probable)")
        elif culture[pid] == CODE_BANANE:
            info = completer_fenetres(r, geoms[pid], rng)
            v.update(bananeraie=True, dir_rang_deg=info["dir_rang_deg"], periode_mediane_m=info["periode_m"],
                     rangs=info, motif="parcelle déclarée en banane (RPG)")
            v["n_fenetres_rangs"] = sum(bool(f.get("rangs")) for f in r["fenetres"])
            v["n_fenetres"] = max(v.get("n_fenetres", 0), len(r["fenetres"]))
        else:
            v.update(bananeraie=False, motif=f"parcelle déclarée en « {libelle[pid]} » (RPG)")
    n_ban = sum(r["verdict"]["bananeraie"] for r in fourier)
    print(f"parcelles avec bananiers 3D : {n_ban} sur {len(fourier)} ; déclarées en banane mais sol nu : "
          f"{sum(1 for r in fourier if culture[r['parcelle_id']] == CODE_BANANE and not r['verdict']['bananeraie'])}", flush=True)

    info_b, A = vm.etape_bananiers(fourier, parcelles, zones, tuiles, b, d, img, tr)
    doc = vm.etape_donnees(fourier, parcelles, bulletin, alertes, zones, tuiles, info_b, b, d)
    # ajouts : culture déclarée, sources
    for p in doc["parcelles"]:
        p["culture_code"], p["culture"] = culture[p["id"]], libelle[p["id"]]
    surf = parcelles.assign(ha=parcelles.area / 1e4)
    doc["rpg"] = dict(surface_totale_ha=round(float(surf.ha.sum()), 1),
                      surface_banane_ha=round(float(surf[surf.culture_code == CODE_BANANE].ha.sum()), 1),
                      n_banane=int((surf.culture_code == CODE_BANANE).sum()))
    doc["description"] = ("Visite 3D de l'exploitation de Basse-Pointe (Martinique) : sol réel (orthophoto IGN), parcelles "
                          "déclarées (RPG, IGN) et métriques de la chaîne (réels) ; bananiers 3D d'illustration sur les "
                          "parcelles déclarées en banane.")
    doc["source"].update(parcelles="out/demo_martinique_rpg/parcelles_rpg_utm.geojson (RPG, IGN, Etalab 2.0)",
                         bulletin="out/demo_martinique_rpg/chaine/bulletin.csv",
                         alertes="out/demo_martinique_rpg/chaine/alertes.geojson")
    texte = json.dumps(doc, ensure_ascii=False, separators=(",", ":"), default=vm._json_np)
    (d / "donnees.json").write_text(texte, encoding="utf-8")
    (d / "donnees.json.gz").write_bytes(gzip.compress(texte.encode("utf-8"), 9, mtime=0))
    vm.etape_controle(img, tr, b, fourier, parcelles, d, A, [])
    print(f"terminé en {time.time() - t:.0f} s ; {doc['rpg']}", flush=True)


if __name__ == "__main__":
    main()
