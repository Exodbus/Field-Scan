"""Module comptage des pieds (orthomosaïque de drone, DeepForest affiné, processeur).

Pieds estimés : une fourchette, pieds détectés x [coefficient_bas, coefficient_haut]. Le détecteur sous-compte,
et d'autant plus que les couronnes se touchent : 1,43 en agroforesterie (référence manuelle MM1-MM2), 2,19 en
plantation dense (validation de Count banana plants). Sans connaître le milieu de chaque parcelle, on affiche
les deux bornes. Les jeunes plantations (feuilles fines) sont très sous-comptées, au-delà de la fourchette.
Les alertes de densité comparent les parcelles entre elles : le coefficient s'y annule.

Pour chaque parcelle survolée : lecture de sa fenêtre à la résolution d'entraînement (10 cm), fenêtres
glissantes de 400 pixels, fusion des doublons, seuil de score (0,5, choisi sur la validation), centres des
boîtes -> pieds géolocalisés. Densité = pieds / surface réellement couverte par l'image (une parcelle à
moitié survolée n'est pas déclarée à moitié vide). Alerte « densité faible » : nettement moins dense que les
autres parcelles du site (z-score robuste ET écart relatif minimal), en confiance faible : le comptage est
indicatif (modèle dense_v2, seuil 0,5 : F1 0,68 sur la référence manuelle MM1-MM2, 0,56 en plantation dense,
0,12 sur un site de jeune plantation jamais vu ; voir le carnet de données).
"""
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from rasterio import features
from shapely.geometry import Point

from fieldscan import anomalies as an
from fieldscan import drone
from fieldscan.modules import Resultat
from fieldscan.modules._commun import geometrie_parcelle


def _vignette(rgb, valide, transform, geom, points, chemin, titre):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pas = max(1, int(max(rgb.shape[1:]) / 900))            # affichage allégé pour les grandes parcelles
    img = np.moveaxis(rgb[:, ::pas, ::pas], 0, -1) / 255.0
    img[~valide[::pas, ::pas]] = 1.0
    h, l = valide.shape
    x0, y1, r = transform.c, transform.f, transform.a
    fig, ax = plt.subplots(figsize=(5, 5), dpi=110)
    ax.imshow(np.clip(img, 0, 1), extent=(x0, x0 + l * r, y1 - h * r, y1))
    gpd.GeoSeries([geom]).boundary.plot(ax=ax, color="yellow", linewidth=1.2)
    if len(points):
        ax.scatter([p.x for p in points], [p.y for p in points], s=6, c="red", edgecolors="none")
    ax.set_axis_off(); ax.set_title(titre, fontsize=9)
    fig.tight_layout(); fig.savefig(chemin); plt.close(fig)


def executer(ctx):
    reg = ctx.reglages["comptage"]
    chemin_modele = Path(reg["modele"])
    if not chemin_modele.exists():
        raise RuntimeError(f"modèle de comptage introuvable : {chemin_modele}")
    try:
        det = drone.Detecteur(chemin_modele)
    except ModuleNotFoundError as e:
        raise RuntimeError(f"bibliothèque manquante pour le comptage ({e.name}) : pip install deepforest")
    res = reg["resolution_cm"] / 100
    utm = ctx.parcelles.estimate_utm_crs()
    parc_m = ctx.parcelles.to_crs(utm)
    (ctx.sortie / "preuves").mkdir(exist_ok=True)
    meilleurs, pieds = {}, []
    t_total, ha_total = 0.0, 0.0
    for o in ctx.inventaire.orthos:
        for pid in drone.recouvrement(o.chemin, parc_m):
            geom = parc_m.set_index("parcelle_id").geometry[pid]
            x0, y0, x1, y1 = geom.bounds
            rgb, valide, t = drone.lire_fenetre(o.chemin, utm, (x0 - 2, y0 - 2, x1 + 2, y1 + 2), res)
            masque = features.geometry_mask([geom], out_shape=valide.shape, transform=t, invert=True)
            couverture = float((valide & masque).sum()) / max(int(masque.sum()), 1)
            if couverture < 0.05 or (pid in meilleurs and meilleurs[pid]["couverture"] >= couverture):
                continue
            debut = time.time()
            boites, scores = det.predire(rgb, valide, reg.get("taille_fenetre", 400), reg.get("recouvrement", 0.25), reg.get("nms", 0.3))
            duree = time.time() - debut
            surface_lue = valide.sum() * res * res / 1e4
            t_total, ha_total = t_total + duree, ha_total + surface_lue
            garde = scores >= reg["seuil_score"]
            cx, cy = (boites[garde, 0] + boites[garde, 2]) / 2 + 0.5, (boites[garde, 1] + boites[garde, 3]) / 2 + 0.5
            pts = [Point(t.c + x * res, t.f - y * res) for x, y in zip(cx, cy)]
            dedans = [(p, s) for p, s in zip(pts, scores[garde]) if geom.contains(p)]
            surface_couverte = couverture * geom.area / 1e4
            chemin_v = ctx.sortie / "preuves" / f"comptage_{pid}.png"
            _vignette(rgb, valide, t, geom, [p for p, _ in dedans], chemin_v,
                      f"{pid} : {len(dedans)} pieds détectés (couverture {couverture:.0%})")
            meilleurs[pid] = dict(parcelle_id=pid, n_pieds=len(dedans), couverture=round(couverture, 3),
                                  surface_couverte_ha=round(surface_couverte, 3),
                                  densite_ha=round(len(dedans) / surface_couverte, 1) if surface_couverte > 0 else np.nan,
                                  ortho=Path(o.chemin).name, preuve=f"preuves/{chemin_v.name}",
                                  points=[(p, float(s)) for p, s in dedans])
    if not meilleurs:
        raise RuntimeError("aucune orthomosaïque ne recouvre les parcelles")
    for m in meilleurs.values():
        pieds += [dict(parcelle_id=m["parcelle_id"], score=round(s, 3), ortho=m["ortho"], geometry=p) for p, s in m["points"]]
    if pieds:
        gpd.GeoDataFrame(pieds, geometry="geometry", crs=utm).to_crs("EPSG:4326").to_file(ctx.sortie / "pieds.geojson", driver="GeoJSON")
    tab = pd.DataFrame([{k: v for k, v in m.items() if k != "points"} for m in meilleurs.values()]).set_index("parcelle_id")
    # ancienne configuration (un seul « coefficient ») : les deux bornes valent ce coefficient
    bas = float(reg.get("coefficient_bas", reg.get("coefficient", 1.0)))
    haut = float(reg.get("coefficient_haut", reg.get("coefficient", bas)))
    tab["n_pieds_estimes_bas"] = (tab.n_pieds * bas).round().astype(int)
    tab["n_pieds_estimes_haut"] = (tab.n_pieds * haut).round().astype(int)
    tab["densite_estimee_bas_ha"] = (tab.densite_ha * bas).round(1)
    tab["densite_estimee_haut_ha"] = (tab.densite_ha * haut).round(1)
    tab.to_csv(ctx.sortie / "comptage_parcelles.csv")

    # Densité faible : comparaison aux autres parcelles bien couvertes du site
    alertes = []
    couv_min, z_seuil, ecart_rel = reg.get("couverture_min", 0.5), reg.get("seuil_z", -2.0), reg.get("ecart_relatif_min", 0.2)
    bien = tab[(tab.couverture >= couv_min) & tab.densite_ha.notna()]
    if len(bien) >= 3:
        med = float(bien.densite_ha.median())
        s = an.sigma_robuste(bien.densite_ha.values, max(0.05 * med, 1.0))
        for pid, r in bien.iterrows():
            z = (r.densite_ha - med) / s
            if z < z_seuil and r.densite_ha < (1 - ecart_rel) * med:
                alertes.append(dict(parcelle_id=pid, module="comptage", type="densite_faible", indice="pieds_par_ha", date="",
                                    gravite=an.gravite(z), valeur=r.densite_ha, z=round(z, 2), confiance="faible",
                                    message=f"{r.densite_ha:.0f} pieds détectés par ha contre {med:.0f} en médiane sur le site "
                                            f"({(1 - r.densite_ha / med):.0%} de moins, z = {z:.1f}) ; comptage indicatif",
                                    source=r.ortho, carte=None, preuve=r.preuve, geometry=geometrie_parcelle(ctx, pid)))
    sec_ha = round(t_total / ha_total, 1) if ha_total else None
    ctx.journal.info(f"  Comptage : {len(pieds)} pieds détectés, soit {int(tab.n_pieds_estimes_bas.sum())} à "
                     f"{int(tab.n_pieds_estimes_haut.sum())} estimés (coefficients {bas} à {haut}) "
                     f"sur {len(tab)} parcelle(s) ; {sec_ha} s par hectare sur processeur")
    ctx.journal.infos["comptage_secondes_par_ha"] = sec_ha
    return Resultat(par_parcelle=tab[["n_pieds", "n_pieds_estimes_bas", "n_pieds_estimes_haut", "densite_ha",
                                      "densite_estimee_bas_ha", "densite_estimee_haut_ha", "couverture",
                                      "surface_couverte_ha", "ortho"]], alertes=alertes,
                    couches=[str(ctx.sortie / "pieds.geojson")],
                    resume=dict(secondes_par_ha=sec_ha, pieds=len(pieds), coefficient_bas=bas, coefficient_haut=haut,
                                pieds_estimes_bas=int(tab.n_pieds_estimes_bas.sum()),
                                pieds_estimes_haut=int(tab.n_pieds_estimes_haut.sum())))
