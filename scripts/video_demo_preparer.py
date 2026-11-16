"""Vidéo de démonstration : prépare les textures et les panneaux du vol 3D (plan 6) depuis out/visite_basse_pointe_zone/.

Écrit seulement dans out/video_demo/travail/ :
  sol_naturel.jpg   photo IGN à 20 cm assemblée (toute l'emprise, 4481 x 4408 px) ;
  sol_sante.jpg     la même photo avec les zones moins vertes en orange (alertes.geojson, via donnees.json) ;
  contexte.jpg      contexte à 1,6 m autour de la zone ;
  panneau_<id>.png  panneau flottant de chaque parcelle (numéro, culture, surface, score) ;
  panneau_etiquette.png  non utilisé (les textes d'écran sont posés au montage).

Les fichiers de la visite sont suivis de 65 536 octets nuls : on ne lit que les octets utiles (tailles_utiles).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/video_demo_preparer.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RACINE = Path(__file__).resolve().parents[1]
V = RACINE / "out/visite_basse_pointe_zone"
OUT = RACINE / "out/video_demo/travail"
FONTS = Path("C:/Windows/Fonts")


def police(nom, t):
    return ImageFont.truetype(str(FONTS / nom), t)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = json.loads((V / "donnees.json").read_text(encoding="utf-8"))
    E = d["emprise"]
    W, H = d["tuiles"]["fin"]["taille_px"]
    px, (nc, nl) = d["tuiles"]["fin"]["px"], d["tuiles"]["fin"]["n"]
    sol = Image.new("RGB", (W, H))
    for l in range(nl):
        for c in range(nc):
            sol.paste(Image.open(V / f"tuiles/fin/{c}_{l}.jpg").convert("RGB"), (c * px, l * px))
    sol.save(OUT / "sol_naturel.jpg", quality=93)
    # zones moins vertes en orange
    sante = sol.convert("RGBA")
    calque = Image.new("RGBA", sante.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(calque)
    res = d["tuiles"]["fin"]["res"]

    def pix(r):
        return [((r[i] - E["xmin"]) / res, (E["ymax"] - r[i + 1]) / res) for i in range(0, len(r), 2)]
    n = 0
    for z in d["zones_faibles"]:
        for poly in z["anneaux"]:
            dr.polygon(pix(poly[0]), fill=(255, 128, 0, 215))
            for trou in poly[1:]:
                dr.polygon(pix(trou), fill=(0, 0, 0, 0))
            n += 1
    sante = Image.alpha_composite(sante, calque).convert("RGB")
    sante.save(OUT / "sol_sante.jpg", quality=93)
    print("zones dessinées :", n, flush=True)
    # contexte
    C = d["tuiles"]["contexte"]
    ctx = Image.new("RGB", tuple(C["taille_px"]))
    for l in range(C["n"][1]):
        for c in range(C["n"][0]):
            ctx.paste(Image.open(V / f"tuiles/contexte/{c}_{l}.jpg").convert("RGB"), (c * C["px"], l * C["px"]))
    ctx.save(OUT / "contexte.jpg", quality=90)
    # panneaux
    fb, fn = police("segoeuib.ttf", 64), police("segoeui.ttf", 40)
    for p in d["parcelles"]:
        im = Image.new("RGBA", (720, 220), (0, 0, 0, 0))
        g = ImageDraw.Draw(im)
        g.rounded_rectangle((4, 4, 716, 216), 26, fill=(14, 28, 18, 235), outline=(110, 215, 130, 255), width=5)
        g.text((30, 14), p["id"], font=fb, fill=(255, 255, 255, 255))
        cult = p["culture"].replace("\ufffd", "e")
        cult = "Banane" if cult.startswith("Banane") else "Canne à sucre"
        g.text((30, 14), f"{p['id']} · {cult}", font=fb, fill=(255, 255, 255, 255))
        g.text((30, 106), f"{str(p['surface_ha']).replace('.', ',')} ha", font=fn, fill=(235, 235, 235, 255))
        g.text((30, 154), "rien à signaler", font=police("segoeuib.ttf", 44), fill=(127, 208, 138, 255))
        im.save(OUT / f"panneau_{p['id']}.png")
    print("panneaux :", len(d["parcelles"]), flush=True)


if __name__ == "__main__":
    sys.exit(main())
