"""Banc d'anomalies injectées, Sentinel-2 : vigueur, stress hydrique, suivi temporel (15/11/2026).

Usage : python scripts/t15_banc_s2.py --module vigueur|stress|temporel [--pays equateur] [--variantes A,B]
Réglage : Équateur. La Côte d'Ivoire (mesure) n'est lue que par le juge (scripts/t15_juge_s2.py).
Référence = la méthode en service, appelée telle quelle (fieldscan.modules.*), sur des indices injectés.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

import t15_commun as tc
from fieldscan import anomalies as an
from fieldscan.modules import stress as m_stress
from fieldscan.modules import temporel as m_temporel
from fieldscan.modules import vigueur as m_vigueur

# ---------------- méthodes ----------------
# Réglages du service (config.yaml + valeurs par défaut) : z < -2, écarts 0,05 (NDVI, NDRE), 0,03 (résidu NDMI),
# sigma plancher 0,01, 5 pixels au moins.
VARIANTES = {
    "vigueur": {
        "VS0r": dict(indices=("ndvi", "ndre"), lissage=0, z=-2.0, em=dict(ndvi=0.05, ndre=0.05)),   # contrôle, pas un essai
        "VS1": dict(indices=("ndre",), lissage=0, z=-2.0, em=dict(ndvi=0.05, ndre=0.05)),
        "VS2": dict(indices=("ndvi", "ndre"), lissage=3, z=-2.0, em=dict(ndvi=0.05, ndre=0.05)),
        "VS3": dict(indices=("ndvi", "ndre"), lissage=0, z=-2.0, em=dict(ndvi=0.05, ndre=0.03)),
        "VS4": dict(indices=("ndvi", "ndre"), lissage=3, z=-2.0, em=dict(ndvi=0.05, ndre=0.03)),
        "VS5": dict(indices=("ndvi", "ndre"), lissage=0, z=-1.5, em=dict(ndvi=0.05, ndre=0.05)),
        "VS6": dict(indices=("ndre",), lissage=3, z=-2.0, em=dict(ndvi=0.05, ndre=0.03)),
        # tour 2 (journal 14 h 14)
        "VS7": dict(indices=("ndvi", "ndre"), lissage="tente", z=-2.0, em=dict(ndvi=0.05, ndre=0.03)),
        "VS8": dict(indices=("ndvi", "ndre"), lissage=3, z=-2.0, em=dict(ndvi=0.05, ndre=0.04)),
    },
    "stress": {
        "SS0r": dict(droite="site", ndvi_20m=False, lissage=0, z=-2.0, em=0.03),
        "SS1": dict(droite="parcelle", ndvi_20m=False, lissage=0, z=-2.0, em=0.03),
        "SS2": dict(droite="site", ndvi_20m=True, lissage=0, z=-2.0, em=0.03),
        "SS3": dict(droite="site", ndvi_20m=False, lissage=3, z=-2.0, em=0.03),
        "SS4": dict(droite="site", ndvi_20m=True, lissage=3, z=-2.0, em=0.03),
        "SS5": dict(droite="site", ndvi_20m=False, lissage=0, z=-2.0, em=0.02),
        "SS6": dict(droite="parcelle", ndvi_20m=False, lissage=3, z=-2.0, em=0.03),
        # tour 2 (journal 14 h 14)
        "SS7": dict(droite="site", ndvi_20m=True, lissage=0, z=-2.0, em=0.02),
        "SS8": dict(droite="parcelle", ndvi_20m=False, lissage=0, z=-2.0, em=0.02),
        "SS9": dict(droite="parcelle", ndvi_20m=True, lissage=0, z=-2.0, em=0.02),
    },
    "temporel": {
        "TS0r": dict(zones=None),
        "TS1": dict(zones="site", lissage=0, indices=("ndvi", "ndmi")),
        "TS2": dict(zones="parcelle", lissage=0, indices=("ndvi", "ndmi")),
        "TS3": dict(zones="site", lissage=3, indices=("ndvi", "ndmi")),
        "TS4": dict(zones="parcelle", lissage=3, indices=("ndvi", "ndmi")),
        # information (pas des essais) : zones réunies aux parcelles en alerte
        "TS1u": dict(zones="site", lissage=0, indices=("ndvi", "ndmi"), union=True),
        "TS2u": dict(zones="parcelle", lissage=0, indices=("ndvi", "ndmi"), union=True),
        # tour 3 (journal 14 h 18) : surface = tout ce qu'émettrait le correctif (zones + parcelles en alerte)
        "TT1": dict(zones="parcelle", lissage=0, indices=("ndvi", "ndmi"), parcelles="aucune"),
        "TT2": dict(zones="site", lissage=0, indices=("ndvi", "ndmi"), parcelles="aucune"),
        "TT3": dict(zones="site", lissage=0, indices=("ndvi", "ndmi"), parcelles=("couverture", 0.25)),
        "TT4": dict(zones="site", lissage=0, indices=("ndvi", "ndmi"), parcelles=("couverture", 0.50)),
    },
}
EM_TEMPOREL = dict(ndvi=0.05, ndmi=0.03, ndre=0.05)
SIGMA_MIN, MIN_PX = 0.01, 5


def _dans_ok(d, ok_ids):
    return np.isin(d.idmap, [d.ids.index(p) + 1 for p in ok_ids])


def vigueur_variante(d, date, p):
    ok_ids = [q for q in d.ids if d.statut[(q, date)] == "ok"]
    dans_ok = _dans_ok(d, ok_ids)
    alerte, parc = np.zeros(d.forme, bool), set()
    for ind in p["indices"]:
        a0 = d.indices[(ind, date)]
        if p["lissage"] == "tente":
            a = tc.lisser_dans_parcelles(a0, d.idmap, len(d.ids), noyau=tc.TENTE)
        else:
            a = tc.lisser_dans_parcelles(a0, d.idmap, len(d.ids), p["lissage"]) if p["lissage"] else a0
        z, ecart = an.z_dans_parcelles(a, d.idmap, d.ids, SIGMA_MIN)
        with np.errstate(invalid="ignore"):
            al = dans_ok & (z < p["z"]) & (ecart < -p["em"][ind])
        alerte |= tc.filtrer_min_px(al, d.idmap, len(d.ids), MIN_PX)
        meds = an.medianes_parcelles(a0, d.idmap, d.ids)
        parc |= {q for q, (e, zz, x) in an.comparer_au_site(meds, ok_ids, p["em"][ind], p["z"], SIGMA_MIN).items() if x}
    return alerte, parc


def _residu(d, date, x, y, valides, droite):
    residu = np.full(d.forme, np.nan, "float32")
    tous = (d.idmap > 0) & ~np.isnan(x) & ~np.isnan(y)
    pente, ordonnee = np.polyfit(x[valides], y[valides], 1)
    residu[tous] = y[tous] - (ordonnee + pente * x[tous])
    if droite == "parcelle":
        for k in range(1, len(d.ids) + 1):
            mk = valides & (d.idmap == k)
            if mk.sum() >= 30:
                pk, ok_ = np.polyfit(x[mk], y[mk], 1)
                tk = tous & (d.idmap == k)
                residu[tk] = y[tk] - (ok_ + pk * x[tk])
    return residu


def stress_variante(d, date, p):
    ok_ids = [q for q in d.ids if d.statut[(q, date)] == "ok"]
    dans_ok = _dans_ok(d, ok_ids)
    x, y = d.indices[("ndvi", date)], d.indices[("ndmi", date)]
    if p["ndvi_20m"]:
        x = tc.lisser_dans_parcelles(x, d.idmap, len(d.ids), noyau=tc.TENTE)
    valides = dans_ok & ~np.isnan(x) & ~np.isnan(y)
    if valides.sum() < 30:
        return np.zeros(d.forme, bool), set()
    residu = _residu(d, date, x, y, valides, p["droite"])
    if p["lissage"]:
        residu = tc.lisser_dans_parcelles(residu, d.idmap, len(d.ids), p["lissage"])
    zr = residu / an.sigma_robuste(residu[valides], SIGMA_MIN)
    with np.errstate(invalid="ignore"):
        al = dans_ok & (zr < p["z"]) & (residu < -p["em"])
    alerte = tc.filtrer_min_px(al, d.idmap, len(d.ids), MIN_PX)
    # alerte de parcelle : comme le service (droite du site, résidu non lissé), avec le NDVI de la variante
    r_site = _residu(d, date, x, y, valides, "site")
    meds = an.medianes_parcelles(r_site, d.idmap, d.ids)
    parc = {q for q, (e, zz, a) in an.comparer_au_site(meds, ok_ids, p["em"], p["z"], SIGMA_MIN).items() if a}
    return alerte, parc


def temporel_parcelles(d, d1, d2, indices=("ndvi", "ndmi")):
    """Alertes de parcelle comme fieldscan.modules.temporel (réécrit pour le contrôle)."""
    communs = [q for q in d.ids if d.statut[(q, d1)] == "ok" and d.statut[(q, d2)] == "ok"]
    parc, communs_delta = set(), {}
    for ind in indices:
        m1 = an.medianes_parcelles(d.indices[(ind, d1)], d.idmap, d.ids)
        m2 = an.medianes_parcelles(d.indices[(ind, d2)], d.idmap, d.ids)
        delta = {q: m2[q] - m1[q] for q in communs if q in m1 and q in m2}
        if len(delta) < 3:
            continue
        commun = float(np.median(list(delta.values())))
        communs_delta[ind] = commun
        corr = {q: v - commun for q, v in delta.items()}
        s = an.sigma_robuste(list(corr.values()), SIGMA_MIN)
        parc |= {q for q, v in corr.items() if v / s < -2.0 and v < -EM_TEMPOREL[ind]}
    return parc, communs_delta, communs


def temporel_variante(d, d1, d2, p):
    parc, commun, communs = temporel_parcelles(d, d1, d2)
    if p["zones"] is None:
        return d_masque(d, parc), parc
    dans_ok = _dans_ok(d, communs)
    alerte = np.zeros(d.forme, bool)
    for ind in p["indices"]:
        if ind not in commun:
            m1 = an.medianes_parcelles(d.indices[(ind, d1)], d.idmap, d.ids)
            m2 = an.medianes_parcelles(d.indices[(ind, d2)], d.idmap, d.ids)
            commun[ind] = float(np.median([m2[q] - m1[q] for q in communs if q in m1 and q in m2]))
        delta = d.indices[(ind, d2)] - d.indices[(ind, d1)]
        if p["lissage"]:
            delta = tc.lisser_dans_parcelles(delta, d.idmap, len(d.ids), p["lissage"])
        corr = (delta - commun[ind]).astype("float32")
        if p["zones"] == "site":
            ecart = corr
            z = corr / an.sigma_robuste(corr[dans_ok], SIGMA_MIN)
        else:
            z, ecart = an.z_dans_parcelles(corr, d.idmap, d.ids, SIGMA_MIN)
        with np.errstate(invalid="ignore"):
            al = dans_ok & (z < -2.0) & (ecart < -EM_TEMPOREL[ind])
        alerte |= tc.filtrer_min_px(al, d.idmap, len(d.ids), MIN_PX)
    if p.get("union"):
        alerte |= d_masque(d, parc)
    pol = p.get("parcelles")
    if pol == "aucune":
        return alerte, set()
    if isinstance(pol, tuple) and pol[0] == "couverture":
        gardees = set()
        for q in parc:
            mq = d.idmap == d.ids.index(q) + 1
            if mq.any() and float(alerte[mq].mean()) >= pol[1]:
                gardees.add(q)
        return alerte | d_masque(d, gardees), gardees
    return alerte, parc


def d_masque(d, pids):
    m = np.zeros(d.forme, bool)
    for q in pids:
        m |= d.idmap == d.ids.index(q) + 1
    return m


# ---------------- référence : le module en service ----------------
def reference(P, module, donnees):
    ctx = P.contexte(donnees)
    if module == "vigueur":
        _, alertes, _, _ = m_vigueur._vigueur_s2(ctx)
        zones = [a["geometry"] for a in alertes if a["type"] == "zone_faible"]
        parc = {a["parcelle_id"] for a in alertes if a["type"] == "parcelle_faible"}
        return P.rasteriser_wgs84(zones), parc
    if module == "stress":
        alertes = m_stress.executer(ctx).alertes
        zones = [a["geometry"] for a in alertes if a["type"] == "zone_stress"]
        parc = {a["parcelle_id"] for a in alertes if a["type"] == "parcelle_stress"}
        return P.rasteriser_wgs84(zones), parc
    if module == "temporel":
        alertes = m_temporel.executer(ctx).alertes
        parc = {a["parcelle_id"] for a in alertes if a["type"] == "degradation"}
        return P.masque_parcelles(parc), parc
    raise ValueError(module)


def variante(P, module, donnees, dates, p):
    if module == "vigueur":
        return vigueur_variante(donnees, dates[0], p)
    if module == "stress":
        return stress_variante(donnees, dates[0], p)
    return temporel_variante(donnees, dates[0], dates[1], p)


def scenes(P, module):
    if module == "temporel":
        return [tuple(P.d.dates[i:i + 2]) for i in range(len(P.d.dates) - 1)]
    return [(dt,) for dt in P.d.dates]


def lancer(module, pays, noms, decalage=0, sortie=None, variantes=None, fichier=None):
    t0 = time.time()
    variantes = variantes or VARIANTES[module]
    P = tc.PaysS2(pays)
    noms = ["REF"] + [n for n in (noms or list(variantes))]
    lignes, fa_tirages, fa_intact, abandons = [], {n: [] for n in noms}, {n: 0.0 for n in noms}, 0
    for ks, dates in enumerate(scenes(P, module)):
        intact = P.sous_donnees(dates)
        for n in noms:
            al, _ = reference(P, module, intact) if n == "REF" else variante(P, module, intact, dates, variantes[n])
            fa_intact[n] += float(al.sum()) * P.px_ha
        for t in range(tc.N_TIRAGES):
            graine = decalage + 1000 * tc.K_MODULE[module] + 100 * ks + t
            zones, ab = P.tirer_zones(graine, dates)
            abandons += ab
            cible = dates[-1]                       # temporel : date 2 seulement
            inj = P.sous_donnees(dates, P.indices_injectes(cible, zones, module))
            for n in noms:
                al, parc = reference(P, module, inj) if n == "REF" else variante(P, module, inj, dates, variantes[n])
                lz, fa = tc.mesurer(al, zones, P.px_ha, parc, elargir_px=1)
                fa_tirages[n].append(fa)
                for l in lz:
                    lignes.append(dict(l, variante=n, scene="+".join(dates), tirage=t, graine=graine))
    df = pd.DataFrame(lignes)
    res = []
    for n in noms:
        r = tc.resumer(df[df.variante == n].to_dict("records"), fa_tirages[n], fa_intact[n], None)
        res.append(dict(variante=n, **r))
    res = pd.DataFrame(res)
    sortie = Path(sortie or tc.SORTIE / pays)
    sortie.mkdir(parents=True, exist_ok=True)
    suffixe = f"_{fichier}" if fichier else ("" if set(noms) == {"REF", *variantes} else "_" + "_".join(noms[1:]))
    df.to_csv(sortie / f"zones_{module}{suffixe}.csv", index=False)
    res.to_csv(sortie / f"resume_{module}{suffixe}.csv", index=False)
    print(res.to_string(index=False))
    print(f"zones abandonnées : {abandons} ; durée {time.time() - t0:.0f} s")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--module", required=True, choices=list(VARIANTES))
    ap.add_argument("--pays", default=tc.PAYS_REGLAGE, choices=[tc.PAYS_REGLAGE])
    ap.add_argument("--variantes", default=None)
    ap.add_argument("--tirages", type=int, default=None)
    ap.add_argument("--tour", type=int, default=1)
    a = ap.parse_args()
    if a.tirages:
        tc.N_TIRAGES = a.tirages
    if a.tour > 1:
        lancer(a.module, a.pays, a.variantes.split(","), sortie=tc.SORTIE / "reglage", fichier=f"tour{a.tour}")
    else:
        lancer(a.module, a.pays, a.variantes.split(",") if a.variantes else None,
               sortie=tc.SORTIE / "reglage" if a.tirages is None else tc.SORTIE / "essai_rapide")
