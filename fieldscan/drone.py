"""Outils pour les orthomosaïques de drone : lecture par fenêtre, détecteur de pieds, vigueur RGB.

Une orthomosaïque n'est jamais chargée en entier : on lit la fenêtre de chaque parcelle, reprojetée
dans un système métrique (UTM des parcelles) et rééchantillonnée à la résolution voulue (moyenne des
pixels). Les orthomosaïques en degrés (EPSG:4326, comme ReforesTree) sont donc traitées comme les autres.
"""
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.windows import from_bounds


def lire_fenetre(chemin, crs_metrique, bounds, resolution_m):
    """RGB (3, H, W) en 0-255 (float32), masque des pixels valides, transform, pour `bounds` (x0, y0, x1, y1) en mètres."""
    x0, y0, x1, y1 = bounds
    largeur, hauteur = max(1, int(np.ceil((x1 - x0) / resolution_m))), max(1, int(np.ceil((y1 - y0) / resolution_m)))
    transform = from_origin(x0, y1, resolution_m, resolution_m)
    with rasterio.open(chemin) as src:
        with WarpedVRT(src, crs=crs_metrique, resampling=Resampling.average, transform=transform,
                       width=largeur, height=hauteur, src_nodata=src.nodata, nodata=0) as vrt:
            a = vrt.read(indexes=list(range(1, min(src.count, 4) + 1)), out_dtype="float32")
    rgb = a[:3]
    if a.shape[0] == 4:                      # 4e bande : transparence (orthomosaïques ODM, ReforesTree)
        valide = a[3] > 127
    else:
        valide = rgb.sum(0) > 0
    if rgb.max() <= 1.0 + 1e-6 and rgb.max() > 0:   # réflectance 0-1 : ramenée à 0-255
        rgb = rgb * 255.0
    return rgb, valide, transform


def recouvrement(chemin, parcelles_metriques):
    """Identifiants des parcelles qui chevauchent l'emprise de l'orthomosaïque."""
    from rasterio.warp import transform_bounds
    from shapely.geometry import box
    with rasterio.open(chemin) as src:
        emprise = box(*transform_bounds(src.crs, parcelles_metriques.crs, *src.bounds))
    return list(parcelles_metriques.parcelle_id[parcelles_metriques.intersects(emprise)])


# ---------- Détecteur de pieds (DeepForest affiné) ----------

def positions(n, taille, pas):
    if n <= taille:
        return [0]
    p = list(range(0, n - taille + 1, pas))
    if p[-1] != n - taille:
        p.append(n - taille)
    return p


class Detecteur:
    """DeepForest affiné : modèle vierge (configuration par défaut) + poids du fichier .ckpt, sur processeur."""

    def __init__(self, chemin):
        import torch
        from deepforest import main as df_main
        m = df_main.deepforest()
        point = torch.load(chemin, map_location="cpu", weights_only=False)
        etat = point.get("state_dict", point)
        manquants, inattendus = m.load_state_dict(etat, strict=False)
        mq = [k for k in manquants if k.startswith("model.")] + [k for k in inattendus if k.startswith("model.")]
        if mq:
            raise RuntimeError(f"poids incompatibles avec DeepForest ({len(mq)} tenseurs, ex. {mq[:2]})")
        m.model.eval()
        self.m, self.torch = m, torch

    def predire(self, rgb, valide, taille=400, recouvrement=0.25, iou_nms=0.3):
        """Boîtes (x0, y0, x1, y1) en pixels et scores, sans seuil."""
        from torchvision.ops import nms
        torch = self.torch
        img = np.moveaxis(rgb, 0, -1) / 255.0
        img[~valide] = 0.0
        h, l = valide.shape
        pas = max(1, int(taille * (1 - recouvrement)))
        boites, notes = [], []
        ancien = getattr(self.m.model, "score_thresh", None)
        self.m.model.score_thresh = 0.0
        with torch.no_grad():
            for y0 in positions(h, taille, pas):
                for x0 in positions(l, taille, pas):
                    morceau = np.ascontiguousarray(img[y0:y0 + taille, x0:x0 + taille])
                    o = self.m.model([torch.tensor(morceau, dtype=torch.float32).permute(2, 0, 1)])[0]
                    if len(o["boxes"]):
                        boites.append(o["boxes"].numpy() + np.array([x0, y0, x0, y0]))
                        notes.append(o["scores"].numpy())
        self.m.model.score_thresh = ancien
        if not boites:
            return np.empty((0, 4)), np.empty(0)
        b, s = np.concatenate(boites), np.concatenate(notes)
        garde = nms(torch.tensor(b, dtype=torch.float32), torch.tensor(s, dtype=torch.float32), iou_nms).numpy()
        return b[garde], s[garde]


# ---------- Vigueur RGB ----------

def exg(rgb, valide):
    """Excès de vert (2g - r - b, coordonnées chromatiques) : peu sensible à l'éclairage global."""
    total = rgb.sum(0)
    with np.errstate(divide="ignore", invalid="ignore"):
        r, g, b = rgb[0] / total, rgb[1] / total, rgb[2] / total
        e = 2 * g - r - b
    return np.where(valide & (total > 0), e, np.nan).astype("float32")


def lisser(a, taille_px):
    """Moyenne glissante sur une fenêtre carrée, et masque des pixels dont la fenêtre est COMPLÈTE.

    La moyenne efface la texture des rangs (alternance feuillage / sol). Près d'un bord (limite de parcelle,
    limite de l'image), la fenêtre est incomplète et sa moyenne biaisée ; les bords d'image sont en outre souvent
    flous ou coupent des plants en deux : sont exclus les pixels à moins d'une largeur de fenêtre d'une donnée manquante.
    """
    from scipy import ndimage
    valide = ~np.isnan(a)
    if taille_px <= 1:
        return a, valide
    somme = ndimage.uniform_filter(np.where(valide, a, 0).astype("float64"), taille_px, mode="constant")
    poids = ndimage.uniform_filter(valide.astype("float64"), taille_px, mode="constant")
    with np.errstate(divide="ignore", invalid="ignore"):
        lisse = np.where(poids > 0, somme / poids, np.nan).astype("float32")
    loin_des_bords = ndimage.uniform_filter(valide.astype("float64"), 2 * taille_px + 1, mode="constant") >= 0.999
    return lisse, valide & loin_des_bords
