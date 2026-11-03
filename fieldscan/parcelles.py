"""Lecture des parcelles : identifiant, géométries valides, surface, reprojection."""
import geopandas as gpd


def lire(chemin, reglages, journal):
    """GeoDataFrame avec une colonne `parcelle_id` unique et une colonne `surface_ha`."""
    try:
        gdf = gpd.read_file(chemin)
    except Exception as e:
        raise SystemExit(f"Impossible de lire les parcelles {chemin} : {e}")
    if gdf.empty:
        raise SystemExit(f"Aucune parcelle dans {chemin}")
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    autres = gdf.geom_type[~gdf.geom_type.isin(["Polygon", "MultiPolygon"])]
    if len(autres):
        journal.avertir(f"{len(autres)} géométrie(s) autre(s) que des polygones ignorée(s)")
        gdf = gdf[gdf.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    if gdf.crs is None:
        journal.avertir("Les parcelles n'ont pas de système de coordonnées : EPSG:4326 supposé")
        gdf = gdf.set_crs("EPSG:4326")
    invalides = ~gdf.geometry.is_valid
    if invalides.any():
        journal.avertir(f"{int(invalides.sum())} géométrie(s) invalide(s) réparée(s)")
        gdf.loc[invalides, "geometry"] = gdf.loc[invalides, "geometry"].buffer(0)

    champ = next((c for c in reglages["parcelles"]["champs_identifiant"] if c in gdf.columns), None)
    if champ is None:
        gdf["parcelle_id"] = [f"P{k:03d}" for k in range(1, len(gdf) + 1)]
        journal.avertir("Aucun champ d'identifiant reconnu : parcelles numérotées P001, P002…")
    else:
        gdf["parcelle_id"] = gdf[champ].astype(str)
        if gdf.parcelle_id.duplicated().any():
            journal.avertir(f"Identifiants en double dans le champ « {champ} » : suffixes ajoutés")
            gdf["parcelle_id"] = gdf.parcelle_id + gdf.groupby("parcelle_id").cumcount().map(lambda k: "" if k == 0 else f"_{k}")
    metrique = gdf.estimate_utm_crs()
    gdf["surface_ha"] = gdf.to_crs(metrique).area.round(1) / 1e4
    gdf["surface_ha"] = gdf.surface_ha.round(2)
    journal.info(f"{len(gdf)} parcelles lues (identifiant : {champ or 'numérotation'}, {gdf.surface_ha.sum():.1f} ha, CRS {gdf.crs.to_string()})")
    return gdf.reset_index(drop=True)
