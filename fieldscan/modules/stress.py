"""Module stress hydrique (Sentinel-2) : NDMI comparé à ce qu'on attend pour le NDVI du pixel.

Le NDMI dépend de l'eau des feuilles, mais aussi de la densité du feuillage (corrélation de 0,96 avec
le NDVI sur nos sites). On ajuste donc une droite NDMI ~ NDVI sur les parcelles exploitables du site,
et l'on regarde le résidu : un NDMI plus bas que prévu suggère un manque d'eau plutôt qu'un feuillage moins dense.
"""
import numpy as np
import pandas as pd

from fieldscan import anomalies as an
from fieldscan.modules import Resultat
from fieldscan.modules._commun import confiance, date_reference, geometrie_parcelle, vers_wgs84
from fieldscan.sentinel2 import ecrire_carte, preparer


def executer(ctx):
    d = preparer(ctx)
    reg = ctx.reglages["stress"]
    z_seuil, ecart_min = reg["seuil_z"], reg["ecart_min_residu_ndmi"]
    seuil_faible = ctx.reglages["nuages"].get("confiance_faible_pct", 30.0)
    sigma_min, min_px = reg.get("sigma_min", 0.01), reg.get("min_px_zone", 5)
    cartes = ctx.sortie / "cartes"
    cartes.mkdir(exist_ok=True)
    lignes, zones_toutes, ajustements, couches = [], [], {}, []
    dans_parcelle = d.idmap > 0
    for date in d.dates:
        ok_ids = [p for p in d.ids if d.statut[(p, date)] == "ok"]
        dans_ok = np.isin(d.idmap, [d.ids.index(p) + 1 for p in ok_ids])
        x, y = d.indices[("ndvi", date)], d.indices[("ndmi", date)]
        ecrire_carte(cartes / f"{date}_ndmi.tif", y, d.profil)
        valides = dans_ok & ~np.isnan(x) & ~np.isnan(y)
        if valides.sum() < 30:
            ctx.journal.avertir(f"  Stress {date} : trop peu de pixels exploitables pour ajuster NDMI ~ NDVI")
            continue
        pente, ordonnee = np.polyfit(x[valides], y[valides], 1)
        ajustements[date] = dict(pente=round(float(pente), 4), ordonnee=round(float(ordonnee), 4),
                                 correlation=round(float(np.corrcoef(x[valides], y[valides])[0, 1]), 3))
        residu = np.full(d.forme, np.nan, "float32")
        tous = dans_parcelle & ~np.isnan(x) & ~np.isnan(y)
        residu[tous] = y[tous] - (ordonnee + pente * x[tous])
        chemin = cartes / f"{date}_ndmi_residu.tif"
        ecrire_carte(chemin, residu, d.profil)
        couches.append(str(chemin))
        zr = residu / an.sigma_robuste(residu[valides], sigma_min)
        alerte = dans_ok & (zr < z_seuil) & (residu < -ecart_min)
        for zn in an.extraire_zones(alerte, d.idmap, d.ids, residu, zr, d.transform, min_px):
            zones_toutes.append(dict(zn, date=date, carte=str(chemin.relative_to(ctx.sortie))))
        meds = an.medianes_parcelles(residu, d.idmap, d.ids)
        comp = an.comparer_au_site(meds, ok_ids, ecart_min, z_seuil, sigma_min)
        for p in d.ids:
            e, zz, al = comp.get(p, (np.nan, np.nan, False))
            lignes.append(dict(parcelle_id=p, date=date, ndmi_med=round(float(np.nanmedian(y[d.idmap == d.ids.index(p) + 1])), 4)
                               if np.any(~np.isnan(y[d.idmap == d.ids.index(p) + 1])) else np.nan,
                               residu_ndmi_med=round(meds[p], 4) if p in meds else np.nan, residu_z_site=zz, alerte_parcelle=al))
    tab = pd.DataFrame(lignes)
    tab.to_csv(ctx.sortie / "stress_par_date.csv", index=False)
    zdf = pd.DataFrame(zones_toutes)
    alertes, par_parcelle = [], []
    for p in d.ids:
        dref, exploitable = date_reference(d, p)
        sel = tab[(tab.parcelle_id == p) & (tab.date == dref)] if len(tab) else tab
        ligne = sel.iloc[0].to_dict() if len(sel) else dict(parcelle_id=p, date=dref)
        zp = zdf[(zdf.parcelle_id == p) & (zdf.date == dref)] if len(zdf) else zdf
        ligne["zones_stress_ha"] = round(float(zp.surface_ha.sum()), 3) if len(zp) else 0.0
        par_parcelle.append(ligne)
        if not exploitable:
            continue
        conf = confiance(d, p, dref, seuil_faible)
        if ligne.get("alerte_parcelle"):
            alertes.append(dict(parcelle_id=p, module="stress", type="parcelle_stress", indice="ndmi_residu", date=dref,
                                gravite=an.gravite(ligne["residu_z_site"]), valeur=ligne["residu_ndmi_med"], z=ligne["residu_z_site"], confiance=conf,
                                message=f"NDMI plus bas que prévu pour sa vigueur (résidu {ligne['residu_ndmi_med']:+.3f}, "
                                        f"z = {ligne['residu_z_site']}) : manque d'eau probable",
                                source=d.sources[dref], carte=f"cartes/{dref}_ndmi_residu.tif", geometry=geometrie_parcelle(ctx, p)))
        for zn, g in zip(zp.to_dict("records"), vers_wgs84(list(zp.geometry), d.crs) if len(zp) else []):
            alertes.append(dict(parcelle_id=p, module="stress", type="zone_stress", indice="ndmi_residu", date=dref,
                                gravite=an.gravite(zn["z_moyen"]), valeur=zn["ecart_moyen"], z=zn["z_moyen"], surface_ha=zn["surface_ha"], confiance=conf,
                                message=f"Zone de {zn['surface_ha']:.2f} ha au NDMI plus bas que prévu ({zn['ecart_moyen']:+.3f})",
                                source=d.sources[dref], carte=zn["carte"], geometry=g))
    pp = pd.DataFrame(par_parcelle).set_index("parcelle_id")
    return Resultat(par_parcelle=pp.reindex(columns=["date", "ndmi_med", "residu_ndmi_med", "residu_z_site", "zones_stress_ha"]),
                    alertes=alertes, couches=couches, resume=dict(ajustement_ndmi_ndvi=ajustements))
