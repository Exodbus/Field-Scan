"""Module suivi temporel (Sentinel-2) : évolution de chaque parcelle entre deux dates successives.

La variation commune à tout le site (saison, atmosphère) est retirée : on ne signale que les parcelles
qui se dégradent PLUS que les autres. Le bulletin retient la dernière paire de dates utile à la parcelle.

TT1, adopté par Corentin le 15/11/2026 (banc d'anomalies injectées : docs/journee_2026-11-15/recap.md, section 3 ;
out/controle_jour_1511/juge_teledetection.md) : des ZONES de dégradation REMPLACENT les alertes de parcelle (le tableau
par parcelle garde delta et z, sans alerte). Le bulletin ne pénalise une parcelle que si ses zones totalisent au moins
temporel.surface_min_penalite_ha (0,5 ha). Le delta par pixel, moins la variation commune au site, est comparé :
  - à la médiane du delta de SA parcelle (« zones_temporel: parcelle », TT1) ;
  - ou à l'ensemble des pixels du site (« zones_temporel: site », TT2).
Alerte de zone : z robuste < seuil_z ET écart < -écart minimal (0,05 NDVI, 0,03 NDMI), 5 pixels au moins,
parcelles « ok » aux deux dates. Réglage absent ou null : module d'avant (alertes de parcelle seules).
"""
import numpy as np
import pandas as pd

from fieldscan import anomalies as an
from fieldscan.modules import Resultat
from fieldscan.modules._commun import geometrie_parcelle, vers_wgs84
from fieldscan.sentinel2 import ecrire_carte, preparer


def executer(ctx):
    d = preparer(ctx)
    if len(d.dates) < 2:
        raise RuntimeError(f"une seule date Sentinel-2 recouvre les parcelles ({d.dates[0]})")
    reg = ctx.reglages
    z_seuil, sigma_min = reg["vigueur"]["seuil_z"], reg["vigueur"].get("sigma_min", 0.01)
    seuils = {"ndvi": reg["vigueur"]["ecart_min_ndvi"], "ndmi": reg["stress"]["ecart_min_residu_ndmi"]}
    cartes = ctx.sortie / "cartes"
    cartes.mkdir(exist_ok=True)
    mode_zones = reg.get("temporel", {}).get("zones_temporel")   # absent = module d'avant
    min_px = reg["vigueur"].get("min_px_zone", 5)
    lignes, couches, zones_toutes = [], [], []
    for d1, d2 in zip(d.dates[:-1], d.dates[1:]):
        communs = [p for p in d.ids if d.statut[(p, d1)] == "ok" and d.statut[(p, d2)] == "ok"]
        dans_ok = np.isin(d.idmap, [d.ids.index(p) + 1 for p in communs])
        for ind in ("ndvi", "ndmi"):
            m1 = an.medianes_parcelles(d.indices[(ind, d1)], d.idmap, d.ids)
            m2 = an.medianes_parcelles(d.indices[(ind, d2)], d.idmap, d.ids)
            delta = {p: m2[p] - m1[p] for p in communs if p in m1 and p in m2}
            if len(delta) < 3:
                continue
            commun = float(np.median(list(delta.values())))
            corr = {p: v - commun for p, v in delta.items()}
            s = an.sigma_robuste(list(corr.values()), sigma_min)
            for p in d.ids:
                if p in corr:
                    z = corr[p] / s
                    lignes.append(dict(parcelle_id=p, date1=d1, date2=d2, indice=ind, evaluee=True, delta=round(delta[p], 4),
                                       delta_site=round(commun, 4), delta_corrige=round(corr[p], 4), z=round(z, 2),
                                       alerte=bool(z < z_seuil and corr[p] < -seuils[ind])))
                else:
                    lignes.append(dict(parcelle_id=p, date1=d1, date2=d2, indice=ind, evaluee=False))
            chemin = cartes / f"{d1}_{d2}_delta_{ind}_corrige.tif"
            corrige = np.where(d.idmap > 0, d.indices[(ind, d2)] - d.indices[(ind, d1)] - commun, np.nan).astype("float32")
            ecrire_carte(chemin, corrige, d.profil)
            couches.append(str(chemin))
            if mode_zones:
                if mode_zones == "site":
                    ecart = corrige
                    zpx = corrige / an.sigma_robuste(corrige[dans_ok], sigma_min)
                else:
                    zpx, ecart = an.z_dans_parcelles(corrige, d.idmap, d.ids, sigma_min)
                with np.errstate(invalid="ignore"):
                    alerte_px = dans_ok & (zpx < z_seuil) & (ecart < -seuils[ind])
                for zn in an.extraire_zones(alerte_px, d.idmap, d.ids, ecart, zpx, d.transform, min_px):
                    zones_toutes.append(dict(zn, date1=d1, date2=d2, indice=ind, carte=str(chemin.relative_to(ctx.sortie))))
    tab = pd.DataFrame(lignes)
    tab.to_csv(ctx.sortie / "evolution_par_paire.csv", index=False)
    if tab.empty or not tab.evaluee.any():
        raise RuntimeError("aucune paire de dates avec au moins trois parcelles exploitables aux deux dates")
    alertes, par_parcelle = [], []
    for p in d.ids:
        ev = tab[(tab.parcelle_id == p) & tab.evaluee]
        if ev.empty:
            par_parcelle.append(dict(parcelle_id=p))
            continue
        derniere = ev[ev.date2 == ev.date2.max()]
        ligne = dict(parcelle_id=p, date1=derniere.date1.iloc[0], date2=derniere.date2.iloc[0])
        for r in derniere.to_dict("records"):
            ligne.update({f"{r['indice']}_delta_corrige": r["delta_corrige"], f"{r['indice']}_z": r["z"]})
            if r["alerte"] and not mode_zones:      # avec les zones : plus d'alerte de parcelle séparée (TT1 / TT2)
                alertes.append(dict(parcelle_id=p, module="temporel", type="degradation", indice=r["indice"], date=r["date2"],
                                    gravite=an.gravite(r["z"]), valeur=r["delta_corrige"], z=r["z"],
                                    message=f"{r['indice'].upper()} en baisse de {abs(r['delta_corrige']):.3f} de plus que le reste du site "
                                            f"entre le {r['date1']} et le {r['date2']} (z = {r['z']})",
                                    source=f"{d.sources[r['date1']]} → {d.sources[r['date2']]}",
                                    carte=f"cartes/{r['date1']}_{r['date2']}_delta_{r['indice']}_corrige.tif",
                                    geometry=geometrie_parcelle(ctx, p)))
        zp = [zn for zn in zones_toutes if zn["parcelle_id"] == p and zn["date2"] == ligne["date2"]]
        ligne["zones_degradation_ha"] = round(sum(zn["surface_ha"] for zn in zp), 3)
        for zn, g in zip(zp, vers_wgs84([zn["geometry"] for zn in zp], d.crs)):
            alertes.append(dict(parcelle_id=p, module="temporel", type="zone_degradation", indice=zn["indice"], date=zn["date2"],
                                gravite=an.gravite(zn["z_moyen"]), valeur=zn["ecart_moyen"], z=zn["z_moyen"],
                                surface_ha=zn["surface_ha"],
                                message=f"Zone de {zn['surface_ha']:.2f} ha où le {zn['indice'].upper()} a baissé de "
                                        f"{abs(zn['ecart_moyen']):.3f} de plus que le reste "
                                        f"{'de la parcelle' if mode_zones != 'site' else 'du site'} entre le {zn['date1']} et le {zn['date2']}",
                                source=f"{d.sources[zn['date1']]} → {d.sources[zn['date2']]}", carte=zn["carte"], geometry=g))
        par_parcelle.append(ligne)
    pp = pd.DataFrame(par_parcelle).set_index("parcelle_id")
    return Resultat(par_parcelle=pp.reindex(columns=["date1", "date2", "ndvi_delta_corrige", "ndvi_z", "ndmi_delta_corrige", "ndmi_z",
                                                     "zones_degradation_ha"]),
                    alertes=alertes, couches=couches)
