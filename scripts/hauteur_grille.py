#!/usr/bin/env python3
"""Essai « hauteur » : lecture de l'orthophoto et du MNS d'ODM dans le repère de la reconstruction.

Sans GPS, ODM écrit ses rasters avec une « pseudo-géoréférence » (origine 0, pas de 0,1) qui efface leur
position réelle. On la retrouve :
- orthophoto : `odm_orthophoto/odm_orthophoto_corners.txt` (xmin ymin xmax ymax, unités du repère) ;
- MNS : `odm_dem/dsm.original.tif` (avant découpe et pseudo-géoréférence), sinon rien (erreur explicite).

La grille commune est celle de l'orthophoto, ramenée à 5 cm au sol (facteur k, mètres par unité).
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
from hauteur_commun import PROJET  # noqa: E402

PAS_M = 0.05


def lire_mns_repere():
    """MNS (unités du repère, nan hors données) et (x0, px, y0, py) : x = x0 + col * px, y = y0 + lig * py."""
    import rasterio
    for nom in ("dsm.original.tif", "dsm.tif"):
        f = PROJET / "odm_dem" / nom
        if not f.exists():
            continue
        with rasterio.open(f) as r:
            t = r.transform
            z = r.read(1).astype("float32")
            nd = r.nodata
        if abs(t.a - 0.1) < 1e-9 and t.c == 0 and t.f == 0:
            continue     # pseudo-géoréférence : position perdue
        if nd is not None:
            z[z == nd] = np.nan
        z[~np.isfinite(z) | (z < -1e20)] = np.nan
        return z, (t.c, t.a, t.f, t.e)
    raise FileNotFoundError("aucun MNS avec sa position dans le repère (dsm.original.tif)")


def lire_ortho_repere():
    import rasterio
    f = PROJET / "odm_orthophoto/odm_orthophoto.tif"
    with rasterio.open(f) as r:
        a = r.read()
    xmin, ymin, xmax, ymax = map(float, (PROJET / "odm_orthophoto/odm_orthophoto_corners.txt").read_text().split()[:4])
    rgb = np.moveaxis(a[:3], 0, -1)
    alpha = a[3] > 0 if a.shape[0] >= 4 else np.ones(a.shape[1:], bool)
    return rgb, alpha, (xmin, ymin, xmax, ymax)


class Grille:
    def __init__(self, k):
        self.k = k
        self.pas_m = PAS_M
        self.pas_u = PAS_M / k
        rgb, alpha, (xmin, ymin, xmax, ymax) = lire_ortho_repere()
        self.x0, self.y0 = xmin, ymax
        L = int(np.floor((xmax - xmin) / self.pas_u))
        H = int(np.floor((ymax - ymin) / self.pas_u))
        self.rgb = cv2.resize(rgb, (L, H), interpolation=cv2.INTER_AREA)
        self.valide_ortho = cv2.resize(alpha.astype("uint8"), (L, H), interpolation=cv2.INTER_NEAREST).astype(bool)
        self.valide_ortho &= self.rgb.sum(2) > 0
        # MNS rééchantillonné sur la grille
        z, (mx0, mpx, my0, mpy) = lire_mns_repere()
        jj, ii = np.meshgrid(np.arange(L), np.arange(H))
        X = self.x0 + (jj + 0.5) * self.pas_u
        Y = self.y0 - (ii + 0.5) * self.pas_u
        cz = (X - mx0) / mpx - 0.5
        lz = (Y - my0) / mpy - 0.5
        val = np.isfinite(z)
        zf = np.where(val, z, 0).astype("float32")
        m = map_coordinates(val.astype("float32"), [lz, cz], order=1, cval=0.0)
        zz = map_coordinates(zf, [lz, cz], order=1, cval=0.0)
        self.mns_u = np.where(m > 0.999, zz, np.nan).astype("float32")
        self.valide = self.valide_ortho & np.isfinite(self.mns_u)

    def lisser(self, z, sigma_m):
        """Lissage gaussien normalisé (ignore les nan) ; nan hors données."""
        v = np.isfinite(z)
        s = sigma_m / self.pas_m
        num = gaussian_filter(np.where(v, z, 0).astype("float32"), s)
        den = gaussian_filter(v.astype("float32"), s)
        out = num / np.maximum(den, 1e-6)
        out[den < 0.2] = np.nan
        return out

    def _ij(self, X, Y):
        return (self.y0 - np.asarray(Y)) / self.pas_u - 0.5, (np.asarray(X) - self.x0) / self.pas_u - 0.5

    def echantillonner(self, z, X, Y):
        """Valeur bilinéaire de z (grille) aux points (X, Y) en unités ; hors données : médiane de z."""
        i, j = self._ij(X, Y)
        med = float(np.nanmedian(z))
        return map_coordinates(np.where(np.isfinite(z), z, med).astype("float32"), [i, j], order=1, cval=med)

    def valide_en(self, X, Y):
        i, j = self._ij(X, Y)
        i, j = np.round(i).astype(int), np.round(j).astype(int)
        dedans = (i >= 0) & (j >= 0) & (i < self.valide.shape[0]) & (j < self.valide.shape[1])
        out = np.zeros(len(i), bool)
        out[dedans] = self.valide[i[dedans], j[dedans]]
        return out


def construire_grille(rec, k):
    return Grille(k)
