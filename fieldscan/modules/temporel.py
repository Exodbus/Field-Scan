"""Module suivi temporel (Sentinel-2) : évolution de chaque parcelle entre deux dates successives.

La variation commune à tout le site (saison, atmosphère) est retirée : on ne signale que les parcelles
qui se dégradent PLUS que les autres. Le bulletin retient la dernière paire de dates utile à la parcelle.
"""
import numpy as np
import pandas as pd

from fieldscan import anomalies as an
from fieldscan.modules import Resultat
from fieldscan.modules._commun import geometrie_parcelle
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
    lignes, couches = [], []
    for d1, d2 in zip(d.dates[:-1], d.dates[1:]):
        communs = [p for p in d.ids if d.statut[(p, d1)] == "ok" and d.statut[(p, d2)] == "ok"]
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
            ecrire_carte(chemin, np.where(d.idmap > 0, d.indices[(ind, d2)] - d.indices[(ind, d1)] - commun, np.nan).astype("float32"), d.profil)
            couches.append(str(chemin))
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
            if r["alerte"]:
                alertes.append(dict(parcelle_id=p, module="temporel", type="degradation", indice=r["indice"], date=r["date2"],
                                    gravite=an.gravite(r["z"]), valeur=r["delta_corrige"], z=r["z"],
                                    message=f"{r['indice'].upper()} en baisse de {abs(r['delta_corrige']):.3f} de plus que le reste du site "
                                            f"entre le {r['date1']} et le {r['date2']} (z = {r['z']})",
                                    source=f"{d.sources[r['date1']]} → {d.sources[r['date2']]}",
                                    carte=f"cartes/{r['date1']}_{r['date2']}_delta_{r['indice']}_corrige.tif",
                                    geometry=geometrie_parcelle(ctx, p)))
        par_parcelle.append(ligne)
    pp = pd.DataFrame(par_parcelle).set_index("parcelle_id")
    return Resultat(par_parcelle=pp.reindex(columns=["date1", "date2", "ndvi_delta_corrige", "ndvi_z", "ndmi_delta_corrige", "ndmi_z"]),
                    alertes=alertes, couches=couches)
