#!/usr/bin/env python3
"""Field Scan : du dossier d'images au bulletin de santé, parcelle par parcelle.

    python run.py --images DOSSIER --parcelles parcelles.geojson --out resultats/

Le dossier peut contenir des scènes Sentinel-2 (export du Copernicus Browser ou produit .SAFE),
des orthomosaïques de drone (GeoTIFF RGB) et des photos de feuilles (JPG, PNG). Les modules
sont activés selon les données présentes (option --modules pour les choisir). Tous les réglages
sont dans config.yaml (option --config).
"""
import argparse
import json
import sys
import time
import traceback
from pathlib import Path

from fieldscan import __version__, bulletin, config, entrees, parcelles
from fieldscan import modules as mods
from fieldscan.journal import Journal, empreinte


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", required=True, help="dossier des données (Sentinel-2, drone, photos de feuilles)")
    ap.add_argument("--parcelles", required=True, help="GeoJSON des parcelles")
    ap.add_argument("--out", required=True, help="dossier de sortie")
    ap.add_argument("--modules", nargs="+", choices=mods.ORDRE, help="modules à lancer (défaut : tous ceux que les données permettent)")
    ap.add_argument("--config", help="fichier YAML de réglages (défaut : config.yaml à côté de run.py, sinon valeurs intégrées)")
    args = ap.parse_args(argv)

    sortie = Path(args.out)
    sortie.mkdir(parents=True, exist_ok=True)
    journal = Journal()
    if args.config is None and (Path(__file__).resolve().parent / "config.yaml").exists():
        args.config = str(Path(__file__).resolve().parent / "config.yaml")   # config.yaml livré à côté de run.py
    reglages = config.charger(args.config)
    journal.infos.update(fieldscan=__version__, commande=" ".join(sys.argv), arguments=vars(args), reglages=reglages)
    journal.info(f"Field Scan {__version__} | réglages : {args.config or 'valeurs par défaut'}")

    t = time.time()
    inv = entrees.reconnaitre(args.images, reglages)
    journal.chrono("reconnaissance", time.time() - t)
    resume = inv.resume()
    journal.infos["inventaire"] = resume
    journal.info(f"Données reconnues : {resume['scenes_sentinel2']} scène(s) Sentinel-2 ({', '.join(resume['dates']) or 'aucune date'}), "
                 f"{resume['orthomosaiques']} orthomosaïque(s), {resume['photos_feuilles']} photo(s) de feuilles "
                 f"(dont {resume['photos_localisees']} localisée(s)), {resume['fichiers_ignores']} fichier(s) ignoré(s)")
    for s in inv.scenes:
        if not s.complete:
            journal.avertir(f"Scène {s.date} ({s.source}) incomplète : bandes présentes {sorted(s.bandes)}")
    (sortie / "inventaire.json").write_text(json.dumps(inv.en_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    gdf = parcelles.lire(args.parcelles, reglages, journal)
    journal.infos["parcelles"] = dict(fichier=args.parcelles, empreinte=empreinte(args.parcelles), nombre=len(gdf),
                                      surface_ha=round(float(gdf.surface_ha.sum()), 2))
    ctx = mods.Contexte(inventaire=inv, parcelles=gdf, reglages=reglages, sortie=sortie, journal=journal)

    statuts = {}
    for nom in args.modules or mods.ORDRE:
        possible, raison = mods.disponibilite(nom, inv)
        if not possible:
            statuts[nom] = dict(statut="non évalué", raison=raison)
            journal.info(f"Module {nom} : non évalué ({raison})")
            continue
        t = time.time()
        try:
            ctx.resultats[nom] = mods.executer(nom, ctx)
            statuts[nom] = dict(statut="évalué", alertes=len(ctx.resultats[nom].alertes))
            journal.info(f"Module {nom} : terminé en {time.time() - t:.1f} s, {len(ctx.resultats[nom].alertes)} alerte(s)")
        except NotImplementedError as e:
            statuts[nom] = dict(statut="à venir", raison=str(e))
            journal.avertir(f"Module {nom} : {e}")
        except RuntimeError as e:                 # données présentes mais inutilisables (hors parcelles, modèle absent…)
            statuts[nom] = dict(statut="non évalué", raison=str(e))
            journal.avertir(f"Module {nom} : non évalué ({e})")
        except Exception as e:                    # un module en échec n'arrête pas la chaîne
            statuts[nom] = dict(statut="erreur", raison=str(e))
            journal.erreur(f"Module {nom} : {e}", trace=traceback.format_exc())
        journal.chrono(f"module_{nom}", time.time() - t)
    journal.infos["modules"] = statuts

    t = time.time()
    table, alertes = bulletin.produire(ctx, statuts)
    journal.chrono("bulletin", time.time() - t)
    journal.infos["bulletin"] = dict(alertes=len(alertes), niveaux=table.niveau.value_counts().to_dict())
    journal.info(f"Bulletin : {len(alertes)} alerte(s) ; niveaux {table.niveau.value_counts().to_dict()}")
    prio = table.dropna(subset=["priorite"]).sort_values("priorite").head(5)
    for _, r in prio.iterrows():
        journal.info(f"  priorité {int(r.priorite)} : {r.parcelle_id} (score {int(r.score) if r.score == r.score else '—'}, {r.n_alertes} alerte(s))")
    journal.ecrire(sortie / "journal.json")
    print(f"\nRésultats dans {sortie}/ : bulletin.html, bulletin.csv, alertes.geojson, carte_bulletin.png, preuves/, cartes/, journal.json")


if __name__ == "__main__":
    main()
