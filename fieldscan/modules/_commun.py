"""Fonctions partagées par les modules Sentinel-2 : date de référence, géométries des alertes."""
import geopandas as gpd


def date_reference(d, pid):
    """Dernière date où la parcelle est exploitable (statut ok) ; à défaut, la dernière date."""
    ok = [dt for dt in d.dates if d.statut.get((pid, dt)) == "ok"]
    return (ok[-1] if ok else d.dates[-1]), bool(ok)


def vers_wgs84(geometries, crs):
    """Géométries (liste shapely) reprojetées en EPSG:4326, pour la carte du bulletin."""
    if not geometries:
        return []
    return list(gpd.GeoSeries(geometries, crs=crs).to_crs("EPSG:4326"))


def geometrie_parcelle(ctx, pid):
    return ctx.parcelles.to_crs("EPSG:4326").set_index("parcelle_id").geometry[pid]


def confiance(d, pid, date, seuil_faible):
    if d.statut.get((pid, date)) != "ok":
        return "non_evaluee"
    pm = d.pct_masque.get((pid, date))
    return "faible" if pm is not None and pm == pm and pm > seuil_faible else "normale"
