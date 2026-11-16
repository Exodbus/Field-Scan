#!/usr/bin/env python3
"""Démo finale : tableau de synthèse par parcelle (découpage automatique + comptage + vigueur + score).

Réunit `parcelles_auto.geojson` et les sorties de `run.py` (`chaine/bulletin.csv`, `chaine/alertes.geojson`)
en un seul CSV, `synthese_parcelles.csv`, une ligne par parcelle, et imprime un résumé par site.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/demo_synthese.py --site martinique
"""
import argparse
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import geopandas as gpd
import pandas as pd

DEMOS = {"martinique": RACINE / "out/demo_martinique", "silkwood": RACINE / "out/demo_silkwood"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", choices=list(DEMOS), required=True)
    demo = DEMOS[ap.parse_args().site]
    parc = gpd.read_file(demo / "parcelles_auto.geojson")
    bul = pd.read_csv(demo / "chaine/bulletin.csv")
    al = gpd.read_file(demo / "chaine/alertes.geojson")
    n_al = al.groupby(["parcelle_id", "type"]).size().unstack(fill_value=0)
    garde = ["parcelle_id", "score", "niveau", "n_alertes", "comptage_n_pieds", "comptage_n_pieds_estimes_bas",
             "comptage_n_pieds_estimes_haut", "comptage_densite_ha", "comptage_espacement_median_m",
             "vigueur_drone_exg_med", "vigueur_drone_exg_z_site", "vigueur_drone_zones_faibles_exg_ha"]
    t = (parc.drop(columns=["geometry", "methode"]).merge(bul[[c for c in garde if c in bul.columns]], on="parcelle_id", how="left")
         .merge(n_al.add_prefix("alertes_"), left_on="parcelle_id", right_index=True, how="left"))
    t = t.fillna({c: 0 for c in t.columns if c.startswith("alertes_")})
    t.to_csv(demo / "synthese_parcelles.csv", index=False, encoding="utf-8")
    resume = dict(parcelles=len(t), surface_ha=round(float(t.surface_ha.sum()), 1),
                  pieds=int(t.comptage_n_pieds.sum()), parcelles_avec_pieds=int((t.comptage_n_pieds > 0).sum()),
                  niveaux=t.niveau.value_counts().to_dict(), alertes=al.groupby("type").size().to_dict(),
                  surface_zones_faibles_ha=round(float(al.loc[al["type"] == "zone_faible", "surface_ha"].sum()), 2))
    (demo / "synthese_resume.json").write_text(json.dumps(resume, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resume, ensure_ascii=False))


if __name__ == "__main__":
    main()
