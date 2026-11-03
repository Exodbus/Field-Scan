"""Module vigueur : Sentinel-2 (NDVI, NDRE) et/ou drone (ExG), zones faibles et parcelles faibles.

1. Zones faibles : chaque pixel est comparé à la médiane de SA parcelle.
2. Parcelles faibles : la médiane de chaque parcelle est comparée à celle des autres parcelles du site.
Le bulletin retient, pour chaque parcelle, la dernière date où elle est exploitable (pas trop nuageuse).
Drone : excès de vert ExG = 2g - r - b (coordonnées chromatiques, peu sensibles à l'éclairage global),
sur une grille de 50 cm, lissé sur 3 m (l'échelle d'un pied), bordure de 3 m exclue (pistes, rangs de rive),
avec les mêmes règles de zones et de parcelles faibles.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from rasterio import features

from fieldscan import anomalies as an
from fieldscan import drone
from fieldscan.modules import Resultat
from fieldscan.modules._commun import confiance, date_reference, geometrie_parcelle, vers_wgs84
from fieldscan.sentinel2 import ecrire_carte, preparer

INDICES_VIGUEUR = ("ndvi", "ndre")


def executer(ctx):
    morceaux, alertes, couches, resume = [], [], [], {}
    if any(s.complete for s in ctx.inventaire.scenes):
        try:
            pp, al, co, rs = _vigueur_s2(ctx)
            morceaux.append(pp); alertes += al; couches += co; resume.update(rs)
        except RuntimeError as e:
            ctx.journal.avertir(f"  Vigueur Sentinel-2 non évaluée : {e}")
    if ctx.inventaire.orthos:
        pp, al, co = _vigueur_drone(ctx)
        morceaux.append(pp); alertes += al; couches += co
    if not morceaux:
        raise RuntimeError("aucune donnée de vigueur exploitable sur les parcelles")
    par = pd.concat(morceaux, axis=1) if len(morceaux) > 1 else morceaux[0]
    return Resultat(par_parcelle=par, alertes=alertes, couches=couches, resume=resume)


def _vigueur_drone(ctx):
    reg = ctx.reglages["vigueur"]
    res = reg.get("resolution_drone_m", 0.5)
    z_seuil, sigma_min, ecart_min = reg["seuil_z"], reg.get("sigma_min", 0.01), reg.get("ecart_min_exg", 0.03)
    min_px = max(1, int(reg.get("min_m2_zone_drone", 25) / (res * res)))
    utm = ctx.parcelles.estimate_utm_crs()
    parc_m = ctx.parcelles.to_crs(utm).set_index("parcelle_id")
    cartes = ctx.sortie / "cartes"
    cartes.mkdir(exist_ok=True)
    faits, zones, couches = {}, [], []
    for o in ctx.inventaire.orthos:
        for pid in drone.recouvrement(o.chemin, parc_m.reset_index()):
            geom = parc_m.geometry[pid]
            x0, y0, x1, y1 = geom.bounds
            rgb, valide, t = drone.lire_fenetre(o.chemin, utm, (x0 - 2, y0 - 2, x1 + 2, y1 + 2), res)
            entiere = features.geometry_mask([geom], out_shape=valide.shape, transform=t, invert=True)
            couverture = float((valide & entiere).sum()) / max(int(entiere.sum()), 1)
            if couverture < 0.05 or (pid in faits and faits[pid]["couverture"] >= couverture):
                continue
            # ExG lissé à l'échelle d'un pied (« lissage_drone_m ») sur la parcelle entière ; on ne garde que les pixels
            # à fenêtre complète, hors d'une bordure de même largeur (pistes, rangs de rive)
            lisse, complet = drone.lisser(np.where(entiere, drone.exg(rgb, valide), np.nan).astype("float32"),
                                          int(round(reg.get("lissage_drone_m", 3.0) / res)))
            reduite = geom.buffer(-max(res, reg.get("lissage_drone_m", 3.0)))
            if reduite.is_empty:
                continue
            m = features.geometry_mask([reduite], out_shape=valide.shape, transform=t, invert=True) & complet
            e = np.where(m, lisse, np.nan).astype("float32")
            idmap = m.astype("int32")
            z, ecart = an.z_dans_parcelles(e, idmap, [pid], sigma_min)
            chemin = cartes / f"drone_exg_{pid}.tif"
            profil = dict(driver="GTiff", crs=utm, transform=t, width=e.shape[1], height=e.shape[0], count=1, dtype="float32")
            ecrire_carte(chemin, e, profil)
            couches.append(str(chemin))
            alerte = (z < z_seuil) & (ecart < -ecart_min)
            for zn in an.extraire_zones(alerte, idmap, [pid], ecart, z, t, min_px):
                zones.append(dict(zn, carte=str(chemin.relative_to(ctx.sortie)), ortho=Path(o.chemin).name))
            faits[pid] = dict(couverture=round(couverture, 3), exg_med=round(float(np.nanmedian(e)), 4), ortho=Path(o.chemin).name)
    ok_ids = [p for p, f in faits.items() if f["couverture"] >= 0.5]
    comp = an.comparer_au_site({p: f["exg_med"] for p, f in faits.items()}, ok_ids, ecart_min, z_seuil, sigma_min)
    alertes = []
    for p, f in faits.items():
        e_site, zz, al = comp.get(p, (np.nan, np.nan, False))
        f.update(exg_ecart_site=e_site, exg_z_site=zz)
        zp = [zn for zn in zones if zn["parcelle_id"] == p]
        f["zones_faibles_exg_ha"] = round(sum(zn["surface_ha"] for zn in zp), 3)
        if al:
            alertes.append(dict(parcelle_id=p, module="vigueur", type="parcelle_faible", indice="exg", date="", gravite=an.gravite(zz),
                                valeur=e_site, z=zz, confiance="normale", message=f"Excès de vert (ExG, drone) inférieur de {abs(e_site):.3f} "
                                f"au reste du site (z = {zz})", source=f["ortho"], carte=f"cartes/drone_exg_{p}.tif",
                                geometry=geometrie_parcelle(ctx, p)))
        for zn, g in zip(zp, vers_wgs84([zn["geometry"] for zn in zp], utm)):
            alertes.append(dict(parcelle_id=p, module="vigueur", type="zone_faible", indice="exg", date="", gravite=an.gravite(zn["z_moyen"]),
                                valeur=zn["ecart_moyen"], z=zn["z_moyen"], surface_ha=zn["surface_ha"], confiance="normale",
                                message=f"Zone de {zn['surface_ha']:.2f} ha moins verte que le reste de la parcelle (ExG {zn['ecart_moyen']:+.3f}, drone)",
                                source=zn["ortho"], carte=zn["carte"], geometry=g))
    pp = pd.DataFrame.from_dict(faits, orient="index")
    pp.index.name = "parcelle_id"
    return pp.reindex(columns=["exg_med", "exg_z_site", "zones_faibles_exg_ha", "couverture", "ortho"]).add_prefix("drone_"), alertes, couches


def _vigueur_s2(ctx):
    d = preparer(ctx)
    reg = ctx.reglages["vigueur"]
    z_seuil, sigma_min, min_px = reg["seuil_z"], reg.get("sigma_min", 0.01), reg.get("min_px_zone", 5)
    seuil_faible = ctx.reglages["nuages"].get("confiance_faible_pct", 30.0)
    cartes = ctx.sortie / "cartes"
    cartes.mkdir(exist_ok=True)
    lignes, zones_toutes, couches = [], [], []
    for date in d.dates:
        ok_ids = [p for p in d.ids if d.statut[(p, date)] == "ok"]
        dans_ok = np.isin(d.idmap, [d.ids.index(p) + 1 for p in ok_ids])
        par = {p: dict(parcelle_id=p, date=date, statut=d.statut[(p, date)], pct_masque=d.pct_masque[(p, date)],
                       confiance=confiance(d, p, date, seuil_faible)) for p in d.ids}
        ecrire_carte(cartes / f"{date}_masque_nuages.tif", d.masque[date].astype("uint8"), d.profil)
        for ind in INDICES_VIGUEUR:
            a = d.indices[(ind, date)]
            chemin = cartes / f"{date}_{ind}.tif"
            ecrire_carte(chemin, a, d.profil)
            couches.append(str(chemin))
            ecart_min = reg[f"ecart_min_{ind}"]
            z, ecart = an.z_dans_parcelles(a, d.idmap, d.ids, sigma_min)
            alerte = dans_ok & (z < z_seuil) & (ecart < -ecart_min)
            for zn in an.extraire_zones(alerte, d.idmap, d.ids, ecart, z, d.transform, min_px):
                zones_toutes.append(dict(zn, date=date, indice=ind, carte=str(chemin.relative_to(ctx.sortie))))
            meds = an.medianes_parcelles(a, d.idmap, d.ids)
            for p, (e, zz, al) in an.comparer_au_site(meds, ok_ids, ecart_min, z_seuil, sigma_min).items():
                par[p].update({f"{ind}_med": round(meds[p], 4), f"{ind}_ecart_site": e, f"{ind}_z_site": zz,
                               f"alerte_{ind}_parcelle": al})
        lignes += par.values()
    tab = pd.DataFrame(lignes)
    tab.to_csv(ctx.sortie / "vigueur_par_date.csv", index=False)

    # Bulletin : état à la date de référence de chaque parcelle
    alertes, par_parcelle = [], []
    zdf = pd.DataFrame(zones_toutes)
    for p in d.ids:
        dref, exploitable = date_reference(d, p)
        ligne = tab[(tab.parcelle_id == p) & (tab.date == dref)].iloc[0].to_dict()
        zp = zdf[(zdf.parcelle_id == p) & (zdf.date == dref)] if len(zdf) else zdf
        ligne["zones_faibles_ha"] = round(float(zp.surface_ha.sum()), 3) if len(zp) else 0.0
        par_parcelle.append(ligne)
        if not exploitable:
            continue
        for ind in INDICES_VIGUEUR:
            if ligne.get(f"alerte_{ind}_parcelle"):
                z = ligne[f"{ind}_z_site"]
                alertes.append(dict(parcelle_id=p, module="vigueur", type="parcelle_faible", indice=ind, date=dref,
                                    gravite=an.gravite(z), valeur=ligne[f"{ind}_ecart_site"], z=z, confiance=ligne["confiance"],
                                    message=f"{ind.upper()} médian inférieur de {abs(ligne[f'{ind}_ecart_site']):.3f} au reste du site (z = {z})",
                                    source=d.sources[dref], carte=f"cartes/{dref}_{ind}.tif", geometry=geometrie_parcelle(ctx, p)))
        for zn, g in zip(zp.to_dict("records"), vers_wgs84(list(zp.geometry), d.crs) if len(zp) else []):
            alertes.append(dict(parcelle_id=p, module="vigueur", type="zone_faible", indice=zn["indice"], date=dref,
                                gravite=an.gravite(zn["z_moyen"]), valeur=zn["ecart_moyen"], z=zn["z_moyen"],
                                surface_ha=zn["surface_ha"], confiance=ligne["confiance"],
                                message=f"Zone de {zn['surface_ha']:.2f} ha où le {zn['indice'].upper()} est inférieur de "
                                        f"{abs(zn['ecart_moyen']):.3f} au reste de la parcelle",
                                source=d.sources[dref], carte=zn["carte"], geometry=g))
    colonnes = ["date", "statut", "confiance", "pct_masque", "ndvi_med", "ndvi_z_site", "ndre_med", "ndre_z_site", "zones_faibles_ha"]
    pp = pd.DataFrame(par_parcelle).set_index("parcelle_id")
    return pp.reindex(columns=colonnes), alertes, couches, dict(dates=d.dates, ecartees=d.ecartees)
