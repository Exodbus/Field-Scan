"""Banc d'anomalies injectées, vigueur drone (ExG) sur ReforesTree (15/11/2026).

Usage : python scripts/t15_banc_drone.py [--moitie reglage] [--tirages N] [--variantes DS1,DS2]
Moitié « réglage » : Carlos Vera Arteaga, Flora Pluas, Manuel Macias (ordre alphabétique, un sur deux, journal 14 h 01).
Moitié « mesure » : réservée au juge (scripts/t15_juge_drone.py).
Référence = fieldscan.modules.vigueur._vigueur_drone appelé tel quel ; seule fieldscan.drone.lire_fenetre est remplacée,
pendant l'exécution du banc, par une lecture mise en cache (fenêtre de la parcelle, comme le service) suivie de l'injection.
"""
import argparse
import hashlib
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import geopandas as gpd
from rasterio import features
from shapely.geometry import Point

import t15_commun as tc
from fieldscan import anomalies as an
from fieldscan import drone
from fieldscan.journal import Journal
from fieldscan.modules import Contexte
from fieldscan.modules import vigueur as m_vigueur

ORTHOS = tc.RACINE / "data" / "drone" / "reforestree" / "wwf_ecuador" / "RGB Orthomosaics"
SITES = ["Carlos Vera Arteaga", "Carlos Vera Guevara", "Flora Pluas", "Leonor Aspiazu", "Manuel Macias", "Nestor Macias"]
MOITIES = {"reglage": SITES[0::2], "mesure": SITES[1::2]}
SURF_DRONE = (0.1, 0.4)
MARGE_DRONE_M = 6.0
ECART_ENTRE_ZONES_M = 5.0
GRAINE_DRONE = 4000
LIRE_ORIGINAL = drone.lire_fenetre

VARIANTES = {
    "DS0r": dict(indice="exg", lissage_m=3.0, em=0.03),        # contrôle, pas un essai
    "DS1": dict(indice="vari", lissage_m=3.0, em=None),
    "DS2": dict(indice="gli", lissage_m=3.0, em=None),
    "DS3": dict(indice="exg", lissage_m=5.0, em=0.03),
    "DS4": dict(indice="exg", lissage_m=3.0, em=0.02),
    "DS5": dict(indice="exg", lissage_m=2.0, em=0.03),
    # tour 2 (journal 14 h 14)
    "DS6": dict(indice="vari", lissage_m=5.0, em=None),
    "DS7": dict(indice="exg", lissage_m=3.0, em=0.03, z=-1.5),
}
RES, Z, SIGMA_MIN, MIN_M2 = 0.5, -2.0, 0.01, 25.0


@dataclass
class OrthoBanc:
    chemin: str


def indice(nom, rgb, valide):
    if nom == "exg":
        return drone.exg(rgb, valide)
    r, g, b = rgb[0].astype("float64"), rgb[1].astype("float64"), rgb[2].astype("float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        if nom == "vari":
            den = g + r - b
            v = np.where(np.abs(den) > 1.0, (g - r) / den, np.nan)
            v = np.clip(v, -2, 2)
        elif nom == "gli":
            den = 2 * g + r + b
            v = np.where(den > 0, (2 * g - r - b) / den, np.nan)
    return np.where(valide, v, np.nan).astype("float32")


class Banc:
    def __init__(self, moitie):
        if moitie == "mesure" and os.environ.get("T15_MESURE_AUTORISEE") != "oui":
            raise SystemExit("Moitié « mesure » réservée au juge (T15_MESURE_AUTORISEE=oui).")
        self.sites = MOITIES[moitie]
        g = gpd.read_file(tc.RACINE / "data" / "drone" / "reforestree" / "prepare" / "sites.geojson")
        g = g[g.site.isin(self.sites)].rename(columns={"site": "parcelle_id"})[["parcelle_id", "geometry"]].reset_index(drop=True)
        self.parc = g
        self.utm = g.estimate_utm_crs()
        self.parc_m = g.to_crs(self.utm).set_index("parcelle_id")
        self.orthos = [OrthoBanc(str(ORTHOS / f"{s} RGB.tif")) for s in self.sites]
        self.cache_dir = tc.SORTIE / "cache_drone"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memo = {}
        self.zones = {}           # site -> zones (injection en cours)
        self.reg = tc.reglages()
        self.tmp = tc.SORTIE / "tmp" / f"drone_{moitie}"
        (self.tmp / "cartes").mkdir(parents=True, exist_ok=True)

    # ----- lecture par fenêtre, en cache -----
    def lire(self, chemin, crs, bounds, res):
        cle = (Path(chemin).name, tuple(round(v, 2) for v in bounds), res)
        if cle not in self.memo:
            f = self.cache_dir / (Path(chemin).stem.replace(" ", "_") + f"_{hashlib.md5(repr(cle).encode()).hexdigest()[:8]}.npz")
            if f.exists():
                z = np.load(f, allow_pickle=True)
                rgb, valide, t = z["rgb"], z["valide"], tuple(z["t"])
            else:
                t0 = time.time()
                rgb, valide, tt = LIRE_ORIGINAL(chemin, crs, bounds, res)
                t = tuple(tt)[:6]
                np.savez_compressed(f, rgb=rgb, valide=valide, t=np.array(t))
                print(f"  lecture {Path(chemin).name} : {time.time() - t0:.0f} s, {valide.shape}")
            from affine import Affine
            self.memo[cle] = (rgb, valide, Affine(*t))
        return self.memo[cle]

    def site_de(self, chemin):
        return Path(chemin).name.replace(" RGB.tif", "")

    def lire_injecte(self, chemin, crs, bounds, res):
        rgb, valide, t = self.lire(chemin, crs, bounds, res)
        zones = self.zones.get(self.site_de(chemin), [])
        if not zones:
            return rgb, valide, t
        rgb = rgb.copy()
        for z in zones:
            f = self.part(t, valide.shape, z)
            rgb[1] = rgb[1] * (1 - tc.GRAVITES["drone"][z["gravite"]] * f)
        return rgb, valide, t

    @staticmethod
    def part(t, forme, z, sur=3):
        h, w = forme
        x, y, r = z["x"], z["y"], z["r"]
        f = np.zeros(forme, "float32")
        c0, c1 = max(int((x - r - t.c) / t.a) - 1, 0), min(int((x + r - t.c) / t.a) + 2, w)
        l0, l1 = max(int((y + r - t.f) / t.e) - 1, 0), min(int((y - r - t.f) / t.e) + 2, h)
        off = (np.arange(sur) + 0.5) / sur
        X = t.c + ((np.arange(c0, c1)[:, None] + off[None]).ravel()) * t.a
        Y = t.f + ((np.arange(l0, l1)[:, None] + off[None]).ravel()) * t.e
        d = ((X[None, :] - x) ** 2 + (Y[:, None] - y) ** 2) <= r * r
        f[l0:l1, c0:c1] = d.reshape(l1 - l0, sur, c1 - c0, sur).mean(axis=(1, 3))
        return f

    def fenetre_site(self, site):
        x0, y0, x1, y1 = self.parc_m.geometry[site].bounds
        o = next(o for o in self.orthos if self.site_de(o.chemin) == site)
        return self.lire(o.chemin, self.utm, (x0 - 2, y0 - 2, x1 + 2, y1 + 2), RES)

    # ----- tirage des zones -----
    def tirer(self, graine):
        rng = np.random.default_rng(graine)
        t_ = graine % 1000
        out = {}
        for s_i, site in enumerate(self.sites):
            geom = self.parc_m.geometry[site]
            zs = []
            for j in range(2):
                for _ in range(300):
                    s_ha = float(np.exp(rng.uniform(np.log(SURF_DRONE[0]), np.log(SURF_DRONE[1]))))
                    r = np.sqrt(s_ha * 1e4 / np.pi)
                    inter = geom.buffer(-(r + MARGE_DRONE_M))
                    if inter.is_empty:
                        continue
                    x0, y0, x1, y1 = inter.bounds
                    p = Point(rng.uniform(x0, x1), rng.uniform(y0, y1))
                    if not inter.contains(p):
                        continue
                    if any(np.hypot(p.x - q["x"], p.y - q["y"]) < r + q["r"] + ECART_ENTRE_ZONES_M for q in zs):
                        continue
                    zs.append(dict(parcelle_id=site, x=p.x, y=p.y, r=r, surface_ha=s_ha, gravite=(t_ + s_i + j) % 3))
                    break
            out[site] = zs
        return out

    # ----- référence : le module en service -----
    def reference(self):
        ctx = Contexte(inventaire=type("I", (), {"orthos": self.orthos, "scenes": []})(), parcelles=self.parc,
                       reglages=tc.reglages(), sortie=self.tmp, journal=tc.JournalMuet())
        drone.lire_fenetre = self.lire_injecte
        try:
            _, alertes, _ = m_vigueur._vigueur_drone(ctx)
        finally:
            drone.lire_fenetre = LIRE_ORIGINAL
        out = {}
        parc = {a["parcelle_id"] for a in alertes if a["type"] == "parcelle_faible"}
        for site in self.sites:
            rgb, valide, t = self.lire_injecte(*self._args(site))
            geoms = [a["geometry"] for a in alertes if a["type"] == "zone_faible" and a["parcelle_id"] == site]
            if geoms:
                gs = gpd.GeoSeries(geoms, crs="EPSG:4326").to_crs(self.utm)
                al = features.rasterize([(g, 1) for g in gs], out_shape=valide.shape, transform=t, fill=0, dtype="uint8").astype(bool)
            else:
                al = np.zeros(valide.shape, bool)
            out[site] = al
        return out, parc

    def _args(self, site):
        x0, y0, x1, y1 = self.parc_m.geometry[site].bounds
        o = next(o for o in self.orthos if self.site_de(o.chemin) == site)
        return o.chemin, self.utm, (x0 - 2, y0 - 2, x1 + 2, y1 + 2), RES

    # ----- variantes -----
    def carte_indice(self, site, p, injecte=True):
        rgb, valide, t = (self.lire_injecte if injecte else self.lire)(*self._args(site))
        geom = self.parc_m.geometry[site]
        entiere = features.geometry_mask([geom], out_shape=valide.shape, transform=t, invert=True)
        couverture = float((valide & entiere).sum()) / max(int(entiere.sum()), 1)
        lis = p["lissage_m"]
        lisse, complet = drone.lisser(np.where(entiere, indice(p["indice"], rgb, valide), np.nan).astype("float32"), int(round(lis / RES)))
        reduite = geom.buffer(-max(RES, lis))
        m = features.geometry_mask([reduite], out_shape=valide.shape, transform=t, invert=True) & complet
        e = np.where(m, lisse, np.nan).astype("float32")
        return e, m, couverture

    def variante(self, p):
        out, meds, ok = {}, {}, []
        for site in self.sites:
            e, m, couv = self.carte_indice(site, p)
            idmap = m.astype("int32")
            z, ecart = an.z_dans_parcelles(e, idmap, [site], SIGMA_MIN)
            with np.errstate(invalid="ignore"):
                al = (z < p.get("z", Z)) & (ecart < -p["em"])
            out[site] = tc.filtrer_min_px(al, idmap, 1, max(1, int(MIN_M2 / (RES * RES))))
            meds[site] = float(np.nanmedian(e))
            if couv >= 0.5:
                ok.append(site)
        parc = {q for q, (e_, zz, a) in an.comparer_au_site(meds, ok, p["em"], p.get("z", Z), SIGMA_MIN).items() if a}
        return out, parc

    def calibrer_em(self, variantes):
        """Écart minimal de VARI et GLI : 0,03 x rapport des sigma robustes intra-site (images intactes), règle du journal."""
        sig = {}
        for nom in ("exg", "vari", "gli"):
            s = []
            for site in self.sites:
                e, m, _ = self.carte_indice(site, dict(indice=nom, lissage_m=3.0), injecte=False)
                s.append(an.sigma_robuste(e[m], 0.0))
            sig[nom] = float(np.median(s))
        for n, p in variantes.items():
            if p["em"] is None:
                p["em"] = round(0.03 * sig[p["indice"]] / sig["exg"], 4)
        return sig


def lancer(moitie, noms, n_tirages, decalage=0, sortie=None, variantes=None, fichier=None):
    t0 = time.time()
    variantes = {k: dict(v) for k, v in (variantes or VARIANTES).items()}
    B = Banc(moitie)
    for site in B.sites:
        B.fenetre_site(site)
    sig = B.calibrer_em(variantes)
    print("sigma robustes intra-site (images intactes) :", {k: round(v, 5) for k, v in sig.items()},
          "; écarts minimaux :", {k: v["em"] for k, v in variantes.items()})
    noms = ["REF"] + (noms or list(variantes))
    px_ha = RES * RES / 1e4
    lignes, fa_t, fa_i = [], {n: [] for n in noms}, {n: 0.0 for n in noms}
    B.zones = {}
    for n in noms:
        al, _ = B.reference() if n == "REF" else B.variante(variantes[n])
        fa_i[n] = sum(float(a.sum()) for a in al.values()) * px_ha
    for t in range(n_tirages):
        graine = decalage + GRAINE_DRONE + t
        B.zones = B.tirer(graine)
        f_cache = {}
        for n in noms:
            al, parc = B.reference() if n == "REF" else B.variante(variantes[n])
            fa = 0.0
            for site in B.sites:
                rgb, valide, tt = B.lire(*B._args(site))
                zs = B.zones[site]
                for z in zs:
                    if id(z) not in f_cache:
                        f_cache[id(z)] = B.part(tt, valide.shape, z)
                    z["f"] = f_cache[id(z)]
                lz, fa_s = tc.mesurer(al[site], zs, px_ha, parc, elargir_px=int(round(3.0 / RES)))
                fa += fa_s
                for l in lz:
                    lignes.append(dict(l, variante=n, scene=site, tirage=t, graine=graine))
            fa_t[n].append(fa)
    df = pd.DataFrame(lignes)
    res = pd.DataFrame([dict(variante=n, em=(variantes[n]["em"] if n != "REF" else 0.03),
                             **tc.resumer(df[df.variante == n].to_dict("records"), fa_t[n], fa_i[n], None)) for n in noms])
    sortie = Path(sortie or tc.SORTIE / moitie)
    sortie.mkdir(parents=True, exist_ok=True)
    suf = f"_{fichier}" if fichier else ""
    df.to_csv(sortie / f"zones_drone{suf}.csv", index=False)
    res.to_csv(sortie / f"resume_drone{suf}.csv", index=False)
    print(res.to_string(index=False))
    print(f"durée {time.time() - t0:.0f} s")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--moitie", default="reglage", choices=["reglage"])
    ap.add_argument("--variantes", default=None)
    ap.add_argument("--tirages", type=int, default=tc.N_TIRAGES)
    ap.add_argument("--lecture-seule", action="store_true")
    ap.add_argument("--tour", type=int, default=1)
    a = ap.parse_args()
    if a.tour > 1:
        lancer(a.moitie, a.variantes.split(","), a.tirages, sortie=tc.SORTIE / "reglage", fichier=f"tour{a.tour}")
        sys.exit(0)
    if a.lecture_seule:
        B = Banc(a.moitie)
        for s in B.sites:
            B.fenetre_site(s)
        sys.exit(0)
    lancer(a.moitie, a.variantes.split(",") if a.variantes else None, a.tirages,
           sortie=tc.SORTIE / ("reglage" if a.tirages == tc.N_TIRAGES and not a.variantes else "essai_rapide"))
