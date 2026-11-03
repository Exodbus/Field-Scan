"""Outils communs de détection d'anomalies (repris de scripts/anomalies_parcelles.py).

Une alerte exige DEUX conditions : un écart inhabituel (z-score robuste sous le seuil) ET un écart
assez grand en valeur absolue. Le z-score utilise la MAD (écart absolu médian), peu sensible aux
valeurs extrêmes, avec un plancher pour ne pas alerter sur des écarts minuscules dans un site homogène.
"""
import numpy as np
from rasterio import features
from scipy import ndimage
from shapely.geometry import shape
from shapely.ops import unary_union

K_MAD = 1.4826


def sigma_robuste(v, plancher):
    v = np.asarray(v, dtype="float64")
    v = v[~np.isnan(v)]
    if v.size < 2:
        return plancher
    return max(K_MAD * float(np.median(np.abs(v - np.median(v)))), plancher)


def medianes_parcelles(a, idmap, ids):
    out = {}
    for k, pid in enumerate(ids, start=1):
        v = a[idmap == k]
        v = v[~np.isnan(v)]
        if v.size:
            out[pid] = float(np.median(v))
    return out


def comparer_au_site(meds, ok_ids, ecart_min, z_seuil, sigma_min):
    """Compare la médiane de chaque parcelle à celles des parcelles « ok » du site : {pid: (écart, z, alerte)}."""
    ref = np.array([meds[p] for p in ok_ids if p in meds])
    if ref.size < 3:
        return {}
    centre, s = float(np.median(ref)), sigma_robuste(ref, sigma_min)
    return {pid: (round(m - centre, 4), round((m - centre) / s, 2),
                  bool(pid in ok_ids and (m - centre) / s < z_seuil and (m - centre) < -ecart_min))
            for pid, m in meds.items()}


def z_dans_parcelles(a, idmap, ids, sigma_min):
    """Écart de chaque pixel à la médiane de SA parcelle, et z-score correspondant."""
    z = np.full(a.shape, np.nan, "float32")
    ecart = np.full(a.shape, np.nan, "float32")
    for k in range(1, len(ids) + 1):
        sel = (idmap == k) & ~np.isnan(a)
        if sel.any():
            ecart[sel] = a[sel] - float(np.median(a[sel]))
            z[sel] = ecart[sel] / sigma_robuste(a[sel], sigma_min)
    return z, ecart


def extraire_zones(alerte, idmap, ids, ecart, z, transform, min_px):
    """Pixels en alerte regroupés en zones connexes, parcelle par parcelle."""
    zones = []
    surface_px_ha = abs(transform.a * transform.e) / 1e4
    for k, pid in enumerate(ids, start=1):
        dans = alerte & (idmap == k)
        if dans.sum() < min_px:
            continue
        lab, n = ndimage.label(dans, structure=np.ones((3, 3), bool))
        for j in range(1, n + 1):
            cm = lab == j
            if cm.sum() < min_px:
                continue
            geoms = [shape(g) for g, v in features.shapes(cm.astype("uint8"), mask=cm, transform=transform) if v == 1]
            zones.append(dict(parcelle_id=pid, n_px=int(cm.sum()), surface_ha=round(float(cm.sum()) * surface_px_ha, 3),
                              ecart_moyen=round(float(np.nanmean(ecart[cm])), 4), z_moyen=round(float(np.nanmean(z[cm])), 2),
                              geometry=unary_union(geoms)))
    return zones


def gravite(z):
    return "forte" if z is not None and z < -3 else "moyenne"
