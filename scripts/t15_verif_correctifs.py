"""Vérifie que les correctifs proposés (out/teledetection/jour_1511/correctifs/*_propose.py), chargés depuis leur fichier,
redonnent sur le RÉGLAGE les alertes des variantes du banc (TS2, TS1, DS1). Ne touche pas à fieldscan/."""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np

import t15_commun as tc
import t15_banc_s2 as bs
import t15_banc_drone as bd
from fieldscan import drone

COR = tc.SORTIE / "correctifs"


def charger(nom):
    spec = importlib.util.spec_from_file_location(f"propose_{nom}", COR / f"{nom}_propose.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def verif_temporel():
    tp = charger("temporel")
    P = tc.PaysS2(tc.PAYS_REGLAGE)
    dates = tuple(P.d.dates[:2])
    for mode, var in (("parcelle", "TT1"), ("site", "TT2")):
        for t in (None, 0, 1):
            if t is None:
                donnees, nom = P.sous_donnees(dates), "intact"
            else:
                zones, _ = P.tirer_zones(1000 * 3 + t, dates)
                donnees, nom = P.sous_donnees(dates, P.indices_injectes(dates[1], zones, "temporel")), f"tirage {t}"
            ctx = P.contexte(donnees)
            ctx.reglages.setdefault("temporel", {})["zones_temporel"] = mode
            al = tp.executer(ctx).alertes
            # surface d'alerte COMPLÈTE émise par le correctif (zones + parcelles éventuelles)
            r = P.rasteriser_wgs84([a["geometry"] for a in al if a["type"] == "zone_degradation"])
            r |= P.masque_parcelles({a["parcelle_id"] for a in al if a["type"] == "degradation"})
            b, _ = bs.temporel_variante(donnees, dates[0], dates[1], bs.VARIANTES["temporel"][var])
            print(f"temporel {var} ({mode}) {nom} : correctif {r.sum()} px, banc {b.sum()} px, différence {(r ^ b).sum()} px")


def verif_drone():
    vp = charger("vigueur")
    B = bd.Banc("reglage")
    var = dict(bd.VARIANTES["DS1"], em=0.0356)
    for t in (None, 0):
        B.zones = {} if t is None else B.tirer(bd.GRAINE_DRONE + t)
        ctx = bd.Contexte(inventaire=type("I", (), {"orthos": B.orthos, "scenes": []})(), parcelles=B.parc,
                          reglages=tc.reglages(), sortie=B.tmp, journal=tc.JournalMuet())
        ctx.reglages["vigueur"].update(indice_drone="vari", ecart_min_vari=0.0356)
        drone.lire_fenetre = B.lire_injecte
        try:
            _, alertes, _ = vp._vigueur_drone(ctx)
        finally:
            drone.lire_fenetre = bd.LIRE_ORIGINAL
        ban, _ = B.variante(var)
        import geopandas as gpd
        from rasterio import features
        for site in B.sites:
            rgb, valide, tt = B.lire(*B._args(site))
            g = [a["geometry"] for a in alertes if a["type"] == "zone_faible" and a["parcelle_id"] == site]
            r = (features.rasterize([(x, 1) for x in gpd.GeoSeries(g, crs="EPSG:4326").to_crs(B.utm)], out_shape=valide.shape,
                                    transform=tt, fill=0, dtype="uint8").astype(bool) if g else np.zeros(valide.shape, bool))
            print(f"drone DS1 {site} {'intact' if t is None else 'tirage 0'} : correctif {r.sum()} px, banc {ban[site].sum()} px, "
                  f"différence {(r ^ ban[site]).sum()} px")


if __name__ == "__main__":
    verif_temporel()
    verif_drone()
