#!/usr/bin/env python3
"""Anomalies de vigueur (NDVI, NDRE) et de stress hydrique (NDMI) par parcelle.

Lit le dossier produit par indices_parcelles.py (cartes, tableau, parcelles) et
cherche ce qui sort de l'ordinaire, au lieu de comparer des valeurs brutes :

1. Vigueur, zones faibles : chaque pixel est comparé à la médiane de SA parcelle.
2. Vigueur, parcelles faibles : la médiane de chaque parcelle est comparée à
   celle des autres parcelles du site, à la même date.
3. Stress hydrique : le NDMI est comparé à ce qu'on attend pour le NDVI du pixel
   (droite NDMI ~ NDVI ajustée sur le site). Un NDMI plus bas que prévu suggère
   un manque d'eau plutôt qu'un feuillage moins dense.
4. Évolution entre deux dates : la variation de chaque parcelle, après avoir
   retiré la variation commune à tout le site (saison, atmosphère).

Les pixels situés à moins de --marge-nuage pixels d'un pixel masqué (nuage, cirrus,
ombre) sont aussi écartés : la classification détecte mal les bords des nuages.

Une alerte exige DEUX conditions : un écart inhabituel (z-score robuste sous le
seuil) ET un écart assez grand en valeur absolue. Seules les parcelles au statut
'ok' sont évaluées ; les autres sont marquées 'non évaluée'.

Exemple :
    python anomalies_parcelles.py --resultats out/equateur
"""
import argparse
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio import features
from scipy import ndimage
from shapely.geometry import shape
from shapely.ops import unary_union

K_MAD = 1.4826  # rend la MAD comparable à un écart-type pour une loi normale


def sigma_robuste(v, plancher):
    """Écart-type robuste (MAD), jamais inférieur au plancher."""
    v = np.asarray(v, dtype="float64")
    v = v[~np.isnan(v)]
    if v.size < 2:
        return plancher
    return max(K_MAD * float(np.median(np.abs(v - np.median(v)))), plancher)


def lire(chemin):
    with rasterio.open(chemin) as src:
        return src.read(1).astype("float32"), src.profile, src.transform, src.crs, src.shape


def ecrire(chemin, tableau, profil):
    p = profil.copy()
    p.update(count=1, dtype="float32", nodata=np.nan, compress="deflate")
    with rasterio.open(chemin, "w", **p) as dst:
        dst.write(tableau.astype("float32"), 1)


def extraire_zones(alerte, idmap, ids, ecart, transform, min_px, attributs):
    """Regroupe les pixels en alerte en zones connexes, parcelle par parcelle."""
    zones = []
    surface_px_ha = abs(transform.a * transform.e) / 1e4
    for k, pid in enumerate(ids, start=1):
        dans = alerte & (idmap == k)
        if dans.sum() < min_px:
            continue
        lab, n = ndimage.label(dans, structure=np.ones((3, 3), bool))
        for j in range(1, n + 1):
            cm = lab == j
            n_px = int(cm.sum())
            if n_px < min_px:
                continue
            geoms = [shape(g) for g, v in features.shapes(cm.astype("uint8"), mask=cm, transform=transform) if v == 1]
            zones.append(dict(attributs, parcelle_id=pid, n_px=n_px,
                              surface_ha=round(n_px * surface_px_ha, 3),
                              ecart_moyen=round(float(np.nanmean(ecart[cm])), 4),
                              geometry=unary_union(geoms)))
    return zones


def medianes_parcelles(a, idmap, ids):
    out = {}
    for k, pid in enumerate(ids, start=1):
        v = a[idmap == k]
        v = v[~np.isnan(v)]
        if v.size:
            out[pid] = float(np.median(v))
    return out


def evaluer_parcelles(meds, ok_ids, ecart_min, args):
    """Compare chaque parcelle aux parcelles 'ok' du site. Retourne {pid: (écart, z, alerte)}."""
    ref = np.array([meds[p] for p in ok_ids if p in meds])
    if ref.size < 3:
        return {}
    centre, s = float(np.median(ref)), sigma_robuste(ref, args.sigma_min)
    res = {}
    for pid, m in meds.items():
        ecart = m - centre
        z = ecart / s
        alerte = (pid in ok_ids) and z < args.z_seuil and ecart < -ecart_min
        res[pid] = (round(ecart, 4), round(z, 2), bool(alerte))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--resultats", required=True, help="dossier produit par indices_parcelles.py")
    ap.add_argument("--out", help="dossier de sortie (défaut : <resultats>/anomalies)")
    ap.add_argument("--z-seuil", type=float, default=-2.0, help="z-score robuste en dessous duquel l'écart est inhabituel (défaut -2)")
    ap.add_argument("--ecart-vigueur", type=float, default=0.05, help="écart minimal de NDVI ou NDRE pour alerter (défaut 0,05)")
    ap.add_argument("--ecart-stress", type=float, default=0.03, help="écart minimal de NDMI, par rapport à l'attendu, pour alerter (défaut 0,03)")
    ap.add_argument("--min-px-zone", type=int, default=5, help="taille minimale d'une zone en pixels (défaut 5, soit 0,05 ha)")
    ap.add_argument("--sigma-min", type=float, default=0.01, help="plancher de l'écart-type robuste (défaut 0,01)")
    ap.add_argument("--confiance-masque", type=float, default=30.0,
                    help="au-dessus de ce %% de pixels masqués, une parcelle évaluée a une confiance 'faible' (défaut 30)")
    ap.add_argument("--marge-nuage", type=int, default=2, help="pixels écartés autour des pixels masqués (défaut 2, soit environ 20 m)")
    args = ap.parse_args(argv)

    res = Path(args.resultats)
    out = Path(args.out) if args.out else res / "anomalies"
    (out / "cartes").mkdir(parents=True, exist_ok=True)

    params = json.loads((res / "parametres.json").read_text(encoding="utf8"))
    df = pd.read_csv(res / "parcelles_indices.csv")
    parcelles = gpd.read_file(res / "parcelles_indices.geojson")[["parcelle_id", "geometry"]]
    ids = list(parcelles.parcelle_id)
    dates = sorted(df.date.unique())
    statut = df.set_index(["parcelle_id", "date"])["statut"].to_dict()
    pct_masque = df.set_index(["parcelle_id", "date"])["pct_masque"].to_dict()
    source = df.groupby("date")["scene_source"].first().to_dict()

    _, profil, transform, crs, forme = lire(res / "cartes" / f"{dates[0]}_ndvi.tif")
    erosion = params.get("erosion_px", 1) * abs(transform.a)
    parc_r = parcelles.to_crs(crs)
    formes = []
    for k, g in enumerate(parc_r.geometry, start=1):
        r = g.buffer(-erosion) if erosion > 0 else g
        if not r.is_empty:
            formes.append((r, k))
    idmap = features.rasterize(formes, out_shape=forme, transform=transform, fill=0, dtype="int32")
    dans_parcelle = idmap > 0

    lignes, zones, medianes, ajustements = {}, [], {}, {}
    vigueur = ["ndvi", "ndre"]

    for d in dates:
        cartes = {}
        for ind in ("ndvi", "ndre", "ndmi"):
            a, _, t, _, f = lire(res / "cartes" / f"{d}_{ind}.tif")
            if f != forme or t != transform:
                raise SystemExit(f"La carte {d}_{ind}.tif n'a pas la même grille que les autres dates.")
            cartes[ind] = a
        masque_path = res / "cartes" / f"{d}_masque_nuages.tif"
        if args.marge_nuage > 0 and masque_path.exists():
            with rasterio.open(masque_path) as src:
                masque = src.read(1).astype(bool)
            halo = ndimage.binary_dilation(masque, structure=np.ones((3, 3), bool), iterations=args.marge_nuage) & ~masque
            for ind in cartes:
                cartes[ind] = np.where(halo, np.nan, cartes[ind]).astype("float32")
        ok_ids = [p for p in ids if statut.get((p, d)) == "ok"]
        dans_ok = np.isin(idmap, [ids.index(p) + 1 for p in ok_ids])
        base = dict(date=d, scene_source=source.get(d, ""))
        for pid in ids:
            evaluee = statut.get((pid, d)) == "ok"
            pm = pct_masque.get((pid, d), np.nan)
            confiance = ("non_evaluee" if not evaluee else
                         "faible" if (not np.isnan(pm) and pm > args.confiance_masque) else "normale")
            lignes[(pid, d)] = dict(parcelle_id=pid, date=d, statut=statut.get((pid, d)), evaluee=evaluee,
                                    pct_masque=pm, confiance=confiance, scene_source=source.get(d, ""))

        # 1 et 2. Vigueur : zones faibles dans la parcelle, puis parcelle faible dans le site
        for ind in vigueur:
            a = cartes[ind]
            z = np.full(forme, np.nan, "float32")
            ecart = np.full(forme, np.nan, "float32")
            for k, pid in enumerate(ids, start=1):
                sel = (idmap == k) & ~np.isnan(a)
                if not sel.any():
                    continue
                med = float(np.median(a[sel]))
                ecart[sel] = a[sel] - med
                z[sel] = ecart[sel] / sigma_robuste(a[sel], args.sigma_min)
            ecrire(out / "cartes" / f"{d}_{ind}_z_dans_parcelle.tif", z, profil)
            alerte = dans_ok & (z < args.z_seuil) & (ecart < -args.ecart_vigueur)
            zones += extraire_zones(alerte, idmap, ids, ecart, transform, args.min_px_zone,
                                    dict(base, type="zone_faible", indice=ind, carte_source=f"cartes/{d}_{ind}.tif"))
            medianes[(ind, d)] = medianes_parcelles(a, idmap, ids)
            for pid, (e, zz, al) in evaluer_parcelles(medianes[(ind, d)], ok_ids, args.ecart_vigueur, args).items():
                lignes[(pid, d)].update({f"{ind}_med": round(medianes[(ind, d)][pid], 4), f"{ind}_ecart_site": e,
                                         f"{ind}_z_site": zz, f"alerte_{ind}_parcelle": al})
        medianes[("ndmi", d)] = medianes_parcelles(cartes["ndmi"], idmap, ids)

        # 3. Stress hydrique : NDMI plus bas que prévu pour le NDVI du pixel
        x, y = cartes["ndvi"], cartes["ndmi"]
        valides = dans_ok & ~np.isnan(x) & ~np.isnan(y)
        if valides.sum() >= 30:
            pente, ordonnee = np.polyfit(x[valides], y[valides], 1)
            ajustements[d] = dict(pente=round(float(pente), 4), ordonnee=round(float(ordonnee), 4),
                                  correlation=round(float(np.corrcoef(x[valides], y[valides])[0, 1]), 3),
                                  n_pixels=int(valides.sum()))
            residu = np.full(forme, np.nan, "float32")
            tous = dans_parcelle & ~np.isnan(x) & ~np.isnan(y)
            residu[tous] = y[tous] - (ordonnee + pente * x[tous])
            ecrire(out / "cartes" / f"{d}_ndmi_residu.tif", residu, profil)
            zr = residu / sigma_robuste(residu[valides], args.sigma_min)
            alerte = dans_ok & (zr < args.z_seuil) & (residu < -args.ecart_stress)
            zones += extraire_zones(alerte, idmap, ids, residu, transform, args.min_px_zone,
                                    dict(base, type="zone_stress", indice="ndmi_residu", carte_source=f"cartes/{d}_ndmi.tif"))
            meds_r = medianes_parcelles(residu, idmap, ids)
            for pid, (e, zz, al) in evaluer_parcelles(meds_r, ok_ids, args.ecart_stress, args).items():
                lignes[(pid, d)].update({"ndmi_residu_med": round(meds_r[pid], 4), "ndmi_residu_z_site": zz,
                                         "alerte_stress_parcelle": al})

    # Nombre et surface des zones par parcelle et par date
    zdf = pd.DataFrame([{k: v for k, v in z.items() if k != "geometry"} for z in zones])
    for (pid, d), ligne in lignes.items():
        for typ, ind in (("zone_faible", "ndvi"), ("zone_faible", "ndre"), ("zone_stress", "ndmi_residu")):
            sous = zdf[(zdf.parcelle_id == pid) & (zdf.date == d) & (zdf.indice == ind)] if len(zdf) else zdf
            ligne[f"zones_{ind}_n"] = int(len(sous))
            ligne[f"zones_{ind}_ha"] = round(float(sous.surface_ha.sum()), 3) if len(sous) else 0.0
    pd.DataFrame(lignes.values()).to_csv(out / "alertes_parcelles.csv", index=False)

    # 4. Évolution entre dates successives, corrigée de la variation commune au site
    evol = []
    for d1, d2 in zip(dates[:-1], dates[1:]):
        communs = [p for p in ids if statut.get((p, d1)) == "ok" and statut.get((p, d2)) == "ok"]
        for ind in ("ndvi", "ndmi"):
            m1, m2 = medianes[(ind, d1)], medianes[(ind, d2)]
            delta = {p: m2[p] - m1[p] for p in communs if p in m1 and p in m2}
            if len(delta) < 3:
                continue
            commun = float(np.median(list(delta.values())))
            corr = {p: v - commun for p, v in delta.items()}
            s = sigma_robuste(list(corr.values()), args.sigma_min)
            seuil = args.ecart_vigueur if ind == "ndvi" else args.ecart_stress
            for p in ids:
                if p in corr:
                    z = corr[p] / s
                    evol.append(dict(parcelle_id=p, date1=d1, date2=d2, indice=ind, evaluee=True,
                                     delta=round(delta[p], 4), delta_site=round(commun, 4),
                                     delta_corrige=round(corr[p], 4), z=round(z, 2),
                                     alerte_degradation=bool(z < args.z_seuil and corr[p] < -seuil)))
                else:
                    evol.append(dict(parcelle_id=p, date1=d1, date2=d2, indice=ind, evaluee=False))
            a1, *_ = lire(res / "cartes" / f"{d1}_{ind}.tif")
            a2, *_ = lire(res / "cartes" / f"{d2}_{ind}.tif")
            carte = np.where(dans_parcelle, a2 - a1 - commun, np.nan)
            ecrire(out / "cartes" / f"{d1}_{d2}_delta_{ind}_corrige.tif", carte, profil)
    pd.DataFrame(evol).to_csv(out / "evolution_parcelles.csv", index=False)

    # Zones en alerte : GeoJSON pour QGIS (chaque zone renvoie à sa date, sa scène et sa carte)
    chemin_zones = out / "alertes_zones.geojson"
    if zones:
        gpd.GeoDataFrame(zones, geometry="geometry", crs=crs).to_file(chemin_zones, driver="GeoJSON")
    else:
        chemin_zones.write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf8")

    (out / "parametres_anomalies.json").write_text(json.dumps(dict(
        resultats=str(res), z_seuil=args.z_seuil, ecart_vigueur=args.ecart_vigueur, ecart_stress=args.ecart_stress,
        min_px_zone=args.min_px_zone, sigma_min=args.sigma_min, marge_nuage_px=args.marge_nuage,
        confiance_masque_pct=args.confiance_masque,
        ajustement_ndmi_ndvi=ajustements),
        indent=2, ensure_ascii=False), encoding="utf8")

    tab = pd.DataFrame(lignes.values())
    print("Parcelles en alerte (parmi les parcelles évaluées) :")
    for d in dates:
        t = tab[(tab.date == d) & tab.evaluee]
        cols = [c for c in ("alerte_ndvi_parcelle", "alerte_ndre_parcelle", "alerte_stress_parcelle") if c in t]
        detail = ", ".join(f"{c.split('_')[1]} {int(t[c].fillna(False).astype(bool).sum())}" for c in cols)
        print(f"  {d} : {len(t)} évaluées | {detail}")
    if len(zdf):
        print("\nZones en alerte (nombre ; surface en ha) :")
        print(zdf.groupby(["date", "indice"]).agg(n=("n_px", "size"), ha=("surface_ha", "sum")).round(2).to_string())
    else:
        print("\nAucune zone en alerte.")
    if evol:
        e = pd.DataFrame(evol)
        e = e[e.evaluee]
        print("\nDégradations entre dates (après correction de l'effet commun) :")
        print(e.groupby(["date1", "date2", "indice"]).alerte_degradation.sum().astype(int).to_string())
    print(f"\nRésultats dans {out}/")


if __name__ == "__main__":
    main()
