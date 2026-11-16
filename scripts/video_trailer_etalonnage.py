"""Trailer Field Scan : étalonnage cinéma des plans 3D (brume de distance, lueur, traînée anamorphique, courbes,
ombres bleu-vert, hautes lumières chaudes, vignettage, grain) et interpolation 12 -> 24 i/s par flux optique.

Entrée : out/video_trailer/travail/<plan>_<fps>/NNNN_image.png (16 bits) et NNNN_brume.png (distance / 8000 m).
Sortie : out/video_trailer/travail/graded/<plan>/NNNN.png (1920 x 804, 24 i/s, après interpolation).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/video_trailer_etalonnage.py --plan grue --fps 12
    ... --test <fichier_image.png> <sortie.png>     (une seule image, pour régler)
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

RACINE = Path(__file__).resolve().parents[1]
TRAVAIL = RACINE / "out/video_trailer/travail"
PROFONDEUR = 8000.0

# réglages par plan : (distance de brume en m, force de la brume, lueur, traînée)
REGLAGES = dict(
    aube=dict(fog=900, a=0.0, glow=0.35, streak=0.10),
    rangs=dict(fog=520, a=0.0, glow=0.30, streak=0.08),
    orbite=dict(fog=900, a=0.55, glow=0.20, streak=0.0),
    fpv=dict(fog=500, a=0.0, glow=0.28, streak=0.08),
    grue=dict(fog=520, a=0.93, glow=0.30, streak=0.12),
    final=dict(fog=520, a=0.93, glow=0.38, streak=0.22),
)
COULEUR_BRUME = np.array([0.98, 0.80, 0.64], np.float32)     # RVB, orangé de l'heure dorée


def lire(chemin_image):
    im = cv2.imread(str(chemin_image), cv2.IMREAD_UNCHANGED)
    im = im[..., :3][..., ::-1].astype(np.float32) / (65535.0 if im.dtype == np.uint16 else 255.0)
    br = cv2.imread(str(chemin_image).replace("_image.png", "_brume.png"), cv2.IMREAD_UNCHANGED)
    if br is not None:
        if br.ndim == 3:
            br = br[..., 0]
        br = br.astype(np.float32) / (65535.0 if br.dtype == np.uint16 else 255.0)
    return im, br


def etalonner(im, br, r, graine=0, rampe=1.0):
    h, w = im.shape[:2]
    if br is not None:
        ciel = br > 0.995
        br = cv2.GaussianBlur(cv2.erode(br, np.ones((13, 13), np.uint8)), (0, 0), 4)   # la brume suit les bords flous
        d = br * PROFONDEUR
        fog = 1.0 - np.exp(-(d / r["fog"]) ** 1.15)
        fog = np.where(ciel, 0.0, fog) * r["a"] * rampe
        # la brume est plus dense près de l'horizon : légère modulation en hauteur d'image
        mod = 0.85 + 0.30 * np.linspace(0.6, 1.0, h)[:, None]
        fog = np.clip(fog * mod, 0, 0.93)[..., None]
        coul = COULEUR_BRUME
        lignes = np.where(ciel.mean(1) > 0.5)[0]
        if len(lignes) > 20:                         # couleur de brume = ciel juste au-dessus de l'horizon
            l1 = lignes.max()
            coul = im[max(l1 - 14, 0):l1 - 2][ciel[max(l1 - 14, 0):l1 - 2]].mean(0)
            coul = np.clip(coul * 0.9, 0, 1)
        im = im * (1 - fog) + coul * fog
    # lueur : hautes lumières floutées, ajoutées
    lum = im.max(2, keepdims=True)
    hl = np.clip((lum - 0.72) / 0.28, 0, 1) * im
    g = cv2.GaussianBlur(hl, (0, 0), 14) * 0.7 + cv2.GaussianBlur(hl, (0, 0), 40) * 0.6
    im = im + g * r["glow"] * np.array([1.0, 0.86, 0.68], np.float32)
    if r["streak"] > 0:                               # traînée anamorphique horizontale, bleutée
        hs = np.clip((lum - 0.88) / 0.12, 0, 1) * im
        st = cv2.blur(cv2.GaussianBlur(hs, (0, 0), 3), (int(w * 0.35) | 1, 1))
        im = im + st * r["streak"] * np.array([0.55, 0.75, 1.0], np.float32)
    # courbe en S (noirs denses) et saturation
    im = np.clip(im, 0, 1.2)
    x = np.clip(im, 0, 1)
    s = x * x * (3 - 2 * x)
    im = 0.55 * s + 0.45 * x
    im = np.where(im < 0.5, im * 0.92, im)
    gris = im.mean(2, keepdims=True)
    im = gris + (im - gris) * 1.10
    # ombres bleu-vert, hautes lumières chaudes
    L = im.mean(2, keepdims=True)
    ombre = np.clip(1 - L / 0.45, 0, 1) ** 1.6
    clair = np.clip((L - 0.5) / 0.5, 0, 1)
    im = im + ombre * np.array([-0.010, 0.012, 0.022], np.float32) + clair * np.array([0.045, 0.010, -0.040], np.float32)
    # vignettage
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rr = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))
    im = im * (1 - 0.40 * np.clip(rr - 0.45, 0, 1) ** 1.8)[..., None]
    # grain léger, plus visible dans les ombres
    rng = np.random.default_rng(graine)
    gr = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 0.7)[..., None]
    im = im + gr * 0.026 * (1.0 - 0.4 * np.clip(L, 0, 1))
    return np.clip(im, 0, 1)


def milieu_flux(a, b, t=0.5):
    """Image intermédiaire entre a et b (float RVB) par flux optique de Farneback (a -> b et b -> a)."""
    ga = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    gb = cv2.cvtColor((b * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    s = 0.5
    ga2, gb2 = cv2.resize(ga, None, fx=s, fy=s), cv2.resize(gb, None, fx=s, fy=s)
    fab = cv2.calcOpticalFlowFarneback(ga2, gb2, None, 0.5, 4, 21, 3, 7, 1.5, 0) / s
    fba = cv2.calcOpticalFlowFarneback(gb2, ga2, None, 0.5, 4, 21, 3, 7, 1.5, 0) / s
    h, w = a.shape[:2]
    fab = cv2.resize(fab, (w, h))
    fba = cv2.resize(fba, (w, h))
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    wa = cv2.remap(a, gx - fab[..., 0] * t, gy - fab[..., 1] * t, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    wb = cv2.remap(b, gx - fba[..., 0] * (1 - t), gy - fba[..., 1] * (1 - t), cv2.INTER_LINEAR,
                   borderMode=cv2.BORDER_REPLICATE)
    return wa * (1 - t) + wb * t


def ecrire(chemin, im):
    cv2.imwrite(str(chemin), (np.clip(im, 0, 1)[..., ::-1] * 255 + 0.5).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan")
    ap.add_argument("--fps", type=int, default=12)
    ap.add_argument("--test", nargs=2)
    ap.add_argument("--reglage", default=None, help="plan dont on prend les réglages (pour --test)")
    a = ap.parse_args()
    if a.test:
        im, br = lire(a.test[0])
        ecrire(a.test[1], etalonner(im, br, REGLAGES[a.reglage or a.plan or "grue"]))
        return
    r = REGLAGES[a.plan]
    src = TRAVAIL / f"{a.plan}_{a.fps}"
    dst = TRAVAIL / "graded" / a.plan
    dst.mkdir(parents=True, exist_ok=True)
    fichiers = sorted(src.glob("*_image.png"))
    print(len(fichiers), "images", flush=True)
    prec = None
    k = 0
    for i, f in enumerate(fichiers):
        im, br = lire(f)
        # interpolation avant étalonnage (la brume ajoutée ensuite est la même pour les deux)
        rampe = 1.0
        if a.plan == "grue":      # pas de brume de distance dans la partie basse (flou de bougé et bords)
            rampe = float(np.clip((i / 12.0 - 3.0) / 2.5, 0, 1))
        if a.fps == 12:
            if prec is not None:
                im_m, br_m = milieu_flux(prec[0], im), (prec[1] + br) / 2 if br is not None else None
                k += 1
                ecrire(dst / f"{k:04d}.png", etalonner(im_m, br_m, r, graine=k, rampe=rampe))
            k += 1
            ecrire(dst / f"{k:04d}.png", etalonner(im, br, r, graine=k, rampe=rampe))
            prec = (im, br)
        else:
            k += 1
            ecrire(dst / f"{k:04d}.png", etalonner(im, br, r, graine=k))
    print(k, "images étalonnées dans", dst, flush=True)


if __name__ == "__main__":
    main()
