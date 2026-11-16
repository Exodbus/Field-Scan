#!/usr/bin/env python3
"""Survol animé de la parcelle (MP4, 1280 x 720, 24 i/s, 12,5 s) avec transition « photo réelle -> 3D ».

Déroulé (images numérotées de 1 à 300) :
  1-48    : photo réelle (mosaïque des 9 tuiles d'entraînement, 5 cm/px), léger zoom ; les centres détectés par le
            comptage v5 apparaissent (images 12 à 36) ;
  49-84   : fondu enchaîné (1,5 s) de la photo, légèrement floutée, vers le rendu 3D, étalonné d'abord sur les
            teintes de la photo (moyenne et écart type par canal) puis rendu à ses propres couleurs (jusqu'à 108) ; la caméra 3D part à la verticale, nord en haut, avec
            exactement la même emprise au sol que la photo (60 m de large) ;
  85-300  : rendu 3D seul : la caméra descend et s'incline, puis avance au-dessus des rangs.
Bandeaux de texte : ce qui est réel (photo, positions) et ce qui est illustratif (formes, décor).

Les images 3D sont rendues par EEVEE (carte graphique intégrée) : Cycles sur processeur demanderait ~7 h.
Étapes : (1) images 3D par Blender (scripts/blender_scene.py --vue survol ; reprise possible, les images déjà
rendues sont sautées) ; (2) composition des 300 images ; (3) encodage MP4 par Blender (scripts/blender_video.py).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/rendu_survol.py --donnees out/rendu_blender/v3
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

BLENDER = r"C:\Users\coren\outils\blender_5.2.4\blender-5.2.4-windows-x64\blender.exe"
N, DEBUT_3D, FIN_FONDU, FIN_ETALONNAGE = 300, 49, 84, 108
EMPRISE_M, RES = 60.0, 0.05
L, H = 1280, 720


def police(t, gras=False):
    try:
        return ImageFont.truetype(f"C:/Windows/Fonts/{'segoeuib' if gras else 'segoeui'}.ttf", t)
    except OSError:
        return ImageFont.load_default()


def bandeau(im, titre, sous_titre, alpha=1.0):
    if alpha <= 0:
        return im
    calque = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    d.rounded_rectangle((20, H - 92, 20 + 760, H - 20), radius=10, fill=(15, 20, 15, int(170 * alpha)))
    d.text((36, H - 86), titre, font=police(24, True), fill=(255, 255, 255, int(255 * alpha)))
    d.text((36, H - 52), sous_titre, font=police(17), fill=(225, 230, 220, int(255 * alpha)))
    return Image.alpha_composite(im.convert("RGBA"), calque).convert("RGB")


def etalonner(im3, ref, poids):
    """Rapproche les couleurs de l'image 3D de celles de la photo : moyenne et écart type par canal ramenés sur
    ceux de la photo, avec le poids donné (1 = teintes de la photo, 0 = image 3D inchangée)."""
    if poids <= 0:
        return im3
    a = np.asarray(im3).astype("float32")
    r = np.asarray(ref).astype("float32")
    mu_a, sd_a = a.reshape(-1, 3).mean(0), a.reshape(-1, 3).std(0) + 1e-3
    mu_r, sd_r = r.reshape(-1, 3).mean(0), r.reshape(-1, 3).std(0)
    b = (a - mu_a) / sd_a * sd_r + mu_r
    return Image.fromarray(np.clip(a + (b - a) * poids, 0, 255).astype(np.uint8))


def image_photo(photo, plants, largeur_m, alpha_cercles):
    """Recadrage centré de la mosaïque (largeur_m de large, 16:9), centres détectés en surimpression."""
    c = photo.width / 2
    lpx = largeur_m / RES
    hpx = lpx * H / L
    boite = (c - lpx / 2, c - hpx / 2, c + lpx / 2, c + hpx / 2)
    im = photo.crop(tuple(round(v) for v in boite)).resize((L, H), Image.LANCZOS)
    if alpha_cercles > 0:
        calque = Image.new("RGBA", (L, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(calque)
        k = L / lpx
        r = 0.4 / RES * k
        for x, y in plants:
            u, v = (x - boite[0]) * k, (y - boite[1]) * k
            if -10 < u < L + 10 and -10 < v < H + 10:
                d.ellipse((u - r, v - r, u + r, v + r), outline=(255, 50, 40, int(255 * alpha_cercles)), width=3)
        im = Image.alpha_composite(im.convert("RGBA"), calque).convert("RGB")
    return im


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--donnees", default="out/rendu_blender/v4")
    ap.add_argument("--fils", type=int, default=6)
    ap.add_argument("--echantillons", type=int, default=24)
    ap.add_argument("--moteur", choices=["eevee", "cycles"], default="eevee",
                    help="eevee (carte graphique, ~15 s par image) ; cycles : ~105 s par image sur 6 fils")
    ap.add_argument("--composer-seulement", action="store_true")
    a = ap.parse_args(argv)
    d = (RACINE / a.donnees).resolve()
    rendus, images = d / "survol_3d", d / "survol_images"
    rendus.mkdir(exist_ok=True)
    images.mkdir(exist_ok=True)
    if not a.composer_seulement:
        t = time.time()
        cmd = [BLENDER, "-b", "--factory-startup", "-t", str(a.fils), "-P", str(RACINE / "scripts/blender_scene.py"), "--",
               "--donnees", str(d), "--vue", "survol", "--simple", "--echantillons", str(a.echantillons), "--moteur", a.moteur,
               "--fils", str(a.fils), "--largeur", str(L), "--hauteur", str(H), "--sortie", str(rendus)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(f"images 3D : code {res.returncode}, {time.time() - t:.0f} s")
        if res.returncode != 0:
            print(res.stdout[-3000:], res.stderr[-3000:])
            return
    info = json.loads((d / "donnees_rendu.json").read_text(encoding="utf-8"))
    n_pieds = info["detecteur"]["n_detectes"]
    photo = Image.open(d / "tuile.png").convert("RGB")
    plants = pd.read_csv(d / "plants.csv")[["x_px", "y_px"]].to_numpy()
    t1 = ("Photo réelle du drone (Flora Pluas, Équateur)", f"5 cm/px ; cercles : {n_pieds} pieds détectés par le comptage v5")
    t2 = ("Rendu 3D : un bananier par pied détecté", "positions réelles ; formes, arbres et décor illustratifs")
    ref_photo = image_photo(photo, plants, EMPRISE_M, 0.0)
    for f in range(1, N + 1):
        if f < DEBUT_3D:
            u = (f - 1) / (DEBUT_3D - 1)
            larg = 66.5 + (EMPRISE_M - 66.5) * (u * u * (3 - 2 * u))
            ac = float(np.clip((f - 12) / 24, 0, 1))
            im = bandeau(image_photo(photo, plants, larg, ac), *t1)
        else:
            im3 = Image.open(rendus / f"image_{f:04d}.png").convert("RGB")
            # étalonnage : la 3D prend d'abord les teintes de la photo, puis retrouve les siennes (images 49 à 108)
            poids = float(np.clip(1 - (f - DEBUT_3D) / (FIN_ETALONNAGE - DEBUT_3D), 0, 1)) ** 1.5
            im3 = etalonner(im3, ref_photo, poids)
            if f <= FIN_FONDU:
                u = (f - DEBUT_3D) / (FIN_FONDU - DEBUT_3D)
                u = u * u * (3 - 2 * u)
                ph = image_photo(photo, plants, EMPRISE_M, 1 - u).filter(ImageFilter.GaussianBlur(2.5 * u))
                im = Image.blend(ph, im3, u)
                im = bandeau(bandeau(im, *t1, alpha=1 - u), *t2, alpha=u)
            else:
                im = bandeau(im3, *t2, alpha=float(np.clip(1 - (f - 250) / 30, 0.0, 1.0)) if f > 250 else 1.0)
        im.save(images / f"image_{f:04d}.png")
    print(f"{N} images composées dans {images}")
    cmd = [BLENDER, "-b", "--factory-startup", "-P", str(RACINE / "scripts/blender_video.py"), "--", str(images),
           str(d / "survol_parcelle.mp4"), str(L), str(H), "24"]
    (d / "survol_parcelle.mp4").unlink(missing_ok=True)
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("encodage :", res.returncode, [l_ for l_ in res.stdout.splitlines() if "VIDEO" in l_ or "Error" in l_])
    # Blender rend le code 0 même si le script Python échoue : on vérifie le fichier
    assert (d / "survol_parcelle.mp4").exists() and (d / "survol_parcelle.mp4").stat().st_size > 1e6, "MP4 absent"


if __name__ == "__main__":
    main()
