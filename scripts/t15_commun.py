"""Banc d'anomalies injectées (15/11/2026) : outils communs.

Protocole : docs/journee_2026-11-15/journal_teledetection.md (écrit avant tout calcul) et
docs/plan_journee_2026-11-15.md, section 3. Ce module n'écrit que dans out/teledetection/jour_1511/.
Il réutilise fieldscan par import, sans le modifier. La référence est la méthode en service, appelée telle quelle.
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "GDAL_NUM_THREADS"):
    os.environ[_v] = "2"                      # processeur : 2 fils au plus

import copy
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import numpy as np
import geopandas as gpd
from rasterio import features
from scipy import ndimage
from shapely.geometry import Point

from fieldscan import anomalies as an
from fieldscan import config as fs_config
from fieldscan import entrees, sentinel2
from fieldscan import parcelles as fs_parcelles
from fieldscan.journal import Journal
from fieldscan.modules import Contexte

SORTIE = RACINE / "out" / "teledetection" / "jour_1511"
SORTIE.mkdir(parents=True, exist_ok=True)

# ---------------- Protocole (journal, 14 h 01) ----------------
GRAVITES = {
    "vigueur": (0.10, 0.20, 0.35),     # PIR x (1 - g)
    "stress": (0.05, 0.10, 0.20),      # B11 x (1 + g)
    "temporel": (0.10, 0.20, 0.35),    # PIR x (1 - g), date 2 seulement
    "drone": (0.03, 0.06, 0.12),       # vert x (1 - g)
}
NOMS_GRAVITE = ("faible", "moyenne", "forte")
K_MODULE = {"vigueur": 1, "stress": 2, "temporel": 3}
N_TIRAGES = 20
N_ZONES_S2 = 6
SURF_S2 = (0.1, 1.0)
MARGE_S2_M = 10.0
DECALAGE_MESURE = 50_000
PAYS_REGLAGE = "equateur"
PAYS_MESURE = "cotedivoire"


def reglages():
    return fs_config.charger(RACINE / "config.yaml")


class JournalMuet(Journal):
    def note(self, niveau, message, **details):
        pass


# ---------------- Sentinel-2 ----------------
class PaysS2:
    """Données Sentinel-2 d'un pays, préparées par fieldscan.sentinel2.preparer, et bandes brutes sur la même grille."""

    def __init__(self, pays):
        if pays == PAYS_MESURE and os.environ.get("T15_MESURE_AUTORISEE") != "oui":
            raise SystemExit("Côte d'Ivoire = mesure : lecture réservée au juge (T15_MESURE_AUTORISEE=oui).")
        self.pays = pays
        self.reg = reglages()
        self.journal = JournalMuet()
        self.inv = entrees.reconnaitre(RACINE / "data" / "sentinel2" / pays, self.reg)
        self.parc = fs_parcelles.lire(RACINE / "data" / "parcelles" / f"parcelles_{pays}.geojson", self.reg, self.journal)
        self.tmp = SORTIE / "tmp" / pays
        (self.tmp / "cartes").mkdir(parents=True, exist_ok=True)
        ctx = Contexte(inventaire=self.inv, parcelles=self.parc, reglages=self.reg, sortie=self.tmp, journal=self.journal)
        self.d = sentinel2.preparer(ctx)
        # mêmes scènes que preparer : tri (date, Copernicus d'abord), première par date
        retenues, vues = {}, set()
        for s in sorted([s for s in self.inv.scenes if s.complete], key=lambda s: (s.date, s.format != "copernicus")):
            if s.date in vues or s.date not in self.d.dates:
                continue
            vues.add(s.date)
            retenues[s.date] = s
        g = dict(transform=self.d.transform, crs=self.d.crs, forme=self.d.forme)
        self.bandes = {dt: sentinel2._lire_scene(retenues[dt], g)[0] for dt in self.d.dates}
        self.parc_m = self.parc.to_crs(self.d.crs).set_index("parcelle_id")
        self.px_ha = abs(self.d.transform.a * self.d.transform.e) / 1e4
        # centres des pixels (coordonnées) pour la part de disque
        h, w = self.d.forme
        t = self.d.transform
        self.res = abs(t.a)

    def ok_ids(self, dates):
        return [p for p in self.d.ids if all(self.d.statut[(p, dt)] == "ok" for dt in dates)]

    def sous_donnees(self, dates, indices_remplaces=None):
        """DonneesS2 limité à `dates`, avec éventuellement des indices remplacés {(ind, date): carte}."""
        d = self.d
        n = sentinel2.DonneesS2(dates=list(dates), sources={dt: d.sources[dt] for dt in dates}, profil=d.profil,
                                transform=d.transform, crs=d.crs, forme=d.forme, idmap=d.idmap, ids=d.ids,
                                masque={dt: d.masque[dt] for dt in dates},
                                statut={k: v for k, v in d.statut.items() if k[1] in dates},
                                pct_masque={k: v for k, v in d.pct_masque.items() if k[1] in dates}, ecartees=[])
        n.indices = {k: v for k, v in d.indices.items() if k[1] in dates}
        if indices_remplaces:
            n.indices.update(indices_remplaces)
        return n

    def contexte(self, donnees):
        return Contexte(inventaire=self.inv, parcelles=self.parc, reglages=copy.deepcopy(self.reg), sortie=self.tmp,
                        journal=self.journal, cache={"s2": donnees})

    # ----- injection -----
    def part_disque(self, x, y, r, sur=5):
        """Part de chaque pixel de la grille dans le disque (x, y, r), par sur-échantillonnage sur x sur."""
        t, (h, w) = self.d.transform, self.d.forme
        f = np.zeros((h, w), "float32")
        c0 = max(int(np.floor((x - r - t.c) / t.a)) - 1, 0)
        c1 = min(int(np.ceil((x + r - t.c) / t.a)) + 1, w)
        l0 = max(int(np.floor((y + r - t.f) / t.e)) - 1, 0)
        l1 = min(int(np.ceil((y - r - t.f) / t.e)) + 1, h)
        if c1 <= c0 or l1 <= l0:
            return f
        off = (np.arange(sur) + 0.5) / sur
        cols = (np.arange(c0, c1)[:, None] + off[None]).ravel()
        lins = (np.arange(l0, l1)[:, None] + off[None]).ravel()
        X = t.c + cols * t.a
        Y = t.f + lins * t.e
        dedans = ((X[None, :] - x) ** 2 + (Y[:, None] - y) ** 2) <= r * r
        f[l0:l1, c0:c1] = dedans.reshape(l1 - l0, sur, c1 - c0, sur).mean(axis=(1, 3))
        return f

    def tirer_zones(self, graine, dates_ok, n_zones=N_ZONES_S2):
        """6 zones (une par parcelle), tailles log-uniformes 0,1-1 ha, 2 par gravité dans l'ordre tiré."""
        rng = np.random.default_rng(graine)
        ok = self.ok_ids(dates_ok)
        ordre = list(rng.permutation(ok))
        zones, abandons = [], 0
        grav = [0, 0, 1, 1, 2, 2][:n_zones]
        grav = list(rng.permutation(grav))
        for gk in grav:
            place = None
            for _ in range(100):
                if not ordre:
                    break
                pid = ordre[0]
                s_ha = float(np.exp(rng.uniform(np.log(SURF_S2[0]), np.log(SURF_S2[1]))))
                r = np.sqrt(s_ha * 1e4 / np.pi)
                interieur = self.parc_m.geometry[pid].buffer(-(r + MARGE_S2_M))
                if interieur.is_empty or interieur.area < 1:
                    if rng.uniform() < 0.2:             # parcelle trop petite pour cette taille : on change parfois de parcelle
                        ordre.append(ordre.pop(0))
                    continue
                x0, y0, x1, y1 = interieur.bounds
                for _ in range(200):
                    p = Point(rng.uniform(x0, x1), rng.uniform(y0, y1))
                    if interieur.contains(p):
                        place = dict(parcelle_id=pid, x=p.x, y=p.y, r=r, surface_ha=s_ha, gravite=int(gk))
                        break
                if place:
                    ordre.pop(0)
                    break
            if place:
                zones.append(place)
            else:
                abandons += 1
        for z in zones:
            z["f"] = self.part_disque(z["x"], z["y"], z["r"])
        return zones, abandons

    def indices_injectes(self, date, zones, module):
        """Indices NDVI, NDRE, NDMI recalculés après injection dans les bandes de `date`."""
        b = {k: v.copy() for k, v in self.bandes[date].items()}
        gv = GRAVITES[module]
        for z in zones:
            f = z["f"]
            f20 = ndimage.uniform_filter(f, size=2, mode="constant")
            g = gv[z["gravite"]]
            if module in ("vigueur", "temporel"):
                b["B08"] = b["B08"] * (1 - g * f)
                b["B8A"] = b["B8A"] * (1 - g * f20)
            elif module == "stress":
                b["B11"] = b["B11"] * (1 + g * f20)
        out = {}
        for nom, (a, c) in sentinel2.INDICES.items():
            orig = self.d.indices[(nom, date)]
            out[(nom, date)] = np.where(np.isnan(orig), np.nan, sentinel2.indice_normalise(b[a], b[c])).astype("float32")
        return out

    def rasteriser_wgs84(self, geoms):
        if not geoms:
            return np.zeros(self.d.forme, bool)
        gs = gpd.GeoSeries(geoms, crs="EPSG:4326").to_crs(self.d.crs)
        return features.rasterize([(g, 1) for g in gs if g is not None and not g.is_empty], out_shape=self.d.forme,
                                  transform=self.d.transform, fill=0, dtype="uint8").astype(bool)

    def masque_parcelles(self, pids):
        m = np.zeros(self.d.forme, bool)
        for p in pids:
            m |= self.d.idmap == self.d.ids.index(p) + 1
        return m


# ---------------- outils de mesure ----------------
def mesurer(alerte, zones, px_ha, parcelles_alerte, elargir_px):
    """Lignes par zone (touchée ou non), fausses alertes en ha hors des zones élargies."""
    lignes = []
    hors = np.ones(alerte.shape, bool)
    for z in zones:
        dedans = z["f"] >= 0.5
        part = float(alerte[dedans].mean()) if dedans.any() else np.nan
        lignes.append(dict(parcelle_id=z["parcelle_id"], gravite=NOMS_GRAVITE[z["gravite"]], surface_ha=round(z["surface_ha"], 3),
                           n_px=int(dedans.sum()), part_en_alerte=round(part, 3) if part == part else np.nan,
                           touchee=bool(part >= 0.5) if part == part else False,
                           parcelle_en_alerte=bool(z["parcelle_id"] in parcelles_alerte)))
        hors &= ~ndimage.binary_dilation(z["f"] > 0, iterations=max(elargir_px, 0)) if elargir_px > 0 else ~(z["f"] > 0)
    fa_ha = float((alerte & hors).sum()) * px_ha
    return lignes, fa_ha


def filtrer_min_px(alerte, idmap, n_ids, min_px):
    """Comme fieldscan.anomalies.extraire_zones, en raster : composantes 8-connexes d'au moins min_px pixels, par parcelle."""
    out = np.zeros(alerte.shape, bool)
    for k in range(1, n_ids + 1):
        dans = alerte & (idmap == k)
        if dans.sum() < min_px:
            continue
        lab, n = ndimage.label(dans, structure=np.ones((3, 3), bool))
        if n == 0:
            continue
        tailles = np.bincount(lab.ravel())
        garde = np.nonzero(tailles >= min_px)[0]
        garde = garde[garde > 0]
        out |= np.isin(lab, garde)
    return out


def lisser_dans_parcelles(a, idmap, n_ids, taille=3, noyau=None):
    """Moyenne glissante (fenêtre taille x taille, ou noyau donné) sans mélanger les parcelles ni les NaN."""
    out = np.full(a.shape, np.nan, "float32")
    for k in range(1, n_ids + 1):
        m = (idmap == k) & ~np.isnan(a)
        if not m.any():
            continue
        v = np.where(m, a, 0).astype("float64")
        if noyau is None:
            s = ndimage.uniform_filter(v, taille, mode="constant")
            w = ndimage.uniform_filter(m.astype("float64"), taille, mode="constant")
        else:
            s = ndimage.convolve(v, noyau, mode="constant")
            w = ndimage.convolve(m.astype("float64"), noyau, mode="constant")
        with np.errstate(invalid="ignore", divide="ignore"):
            out[m] = (s / w)[m]
    return out


TENTE = np.outer([0.25, 0.5, 0.25], [0.25, 0.5, 0.25])   # empreinte d'un pixel de 20 m centrée sur la grille de 10 m


def resumer(lignes_zones, fa_tirages, fa_intact, parc_forte):
    """Résumé d'une variante : rappel par gravité, rappel moyen, fausses alertes, alertes de parcelle."""
    import pandas as pd
    z = pd.DataFrame(lignes_zones)
    r = {g: round(float(z[z.gravite == g].touchee.mean()), 4) for g in NOMS_GRAVITE}
    forte = z[z.gravite == "forte"]
    return dict(rappel_faible=r["faible"], rappel_moyenne=r["moyenne"], rappel_forte=r["forte"],
                rappel_moyen=round(float(np.mean(list(r.values()))), 4), n_zones=len(z),
                fa_ha_par_tirage=round(float(np.mean(fa_tirages)), 3), fa_ha_sans_injection=round(float(fa_intact), 3),
                alerte_parcelle_forte=round(float(forte.parcelle_en_alerte.mean()), 4) if len(forte) else np.nan)
