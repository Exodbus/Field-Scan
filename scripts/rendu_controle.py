#!/usr/bin/env python3
"""Contrôle objectif de l'alignement entre la photo réelle, les centres détectés (plants.csv) et les rendus 3D.

Entrées :
  - <donnees>/plants.csv, tuile.png (mosaïque réelle), vue_dessus_naturel.png, vue_drone_naturel.png ;
  - projections JSON écrites par Blender (scripts/blender_scene.py --projection) : position en pixels de chaque
    pied calculée avec la caméra de la vue (formule world_to_camera_view de Blender), sans relire l'image.

Mesures (vue de dessus) :
  1. part des centres projetés qui tombent sur un pixel « feuille » du rendu (vert, fenêtre de 5 x 5 px) ;
  2. corrélation, par blocs de ~5 m, entre la part de vert de la photo et celle du rendu ; on la calcule aussi
     pour le rendu retourné (miroir horizontal, vertical, rotation de 180° et de 90°) : si l'orientation était
     fausse, une de ces versions corrélerait mieux que l'image telle quelle.
Images : planche de superposition (photo + centres | rendu + centres projetés) et vue drone + pieds projetés.

Exemple :
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/rendu_controle.py --donnees out/rendu_blender/v2 \
        --proj-dessus proj_dessus.json --proj-drone proj_drone.json --sortie out/rendu_blender/v3
"""
import argparse
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402


def police(t, gras=False):
    for nom in (("segoeuib.ttf",) if gras else ("segoeui.ttf",)):
        try:
            return ImageFont.truetype(f"C:/Windows/Fonts/{nom}", t)
        except OSError:
            pass
    return ImageFont.load_default()


def vert(rgb, seuil=0.06):
    """Masque « végétation verte » : ExG normalisé = (2g - r - b) / (r + g + b) au-dessus du seuil."""
    a = rgb.astype("float32")
    s = a.sum(-1) + 1e-6
    exg = (2 * a[..., 1] - a[..., 0] - a[..., 2]) / s
    return (exg > seuil) & (s > 40)


def blocs(masque, n):
    h, l = masque.shape
    return np.array([[masque[i * h // n:(i + 1) * h // n, j * l // n:(j + 1) * l // n].mean() for j in range(n)]
                     for i in range(n)])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--donnees", default="out/rendu_blender/v2")
    ap.add_argument("--proj-dessus", required=True)
    ap.add_argument("--proj-drone")
    ap.add_argument("--rendu-dessus", help="défaut : <donnees>/vue_dessus_naturel.png")
    ap.add_argument("--rendu-drone", help="défaut : <donnees>/vue_drone_naturel.png")
    ap.add_argument("--sortie", default="out/rendu_blender/v3")
    ap.add_argument("--prefixe", default="controle_alignement")
    a = ap.parse_args(argv)
    d, out = RACINE / a.donnees, RACINE / a.sortie
    out.mkdir(parents=True, exist_ok=True)
    plants = pd.read_csv(d / "plants.csv")
    photo = np.asarray(Image.open(d / "tuile.png").convert("RGB"))
    rendu = np.asarray(Image.open(a.rendu_dessus or d / "vue_dessus_naturel.png").convert("RGB"))
    pj = json.loads(Path(a.proj_dessus).read_text(encoding="utf-8"))
    P = np.array([p["sol"][:2] for p in pj["pieds"]])
    ids = [p["id"] for p in pj["pieds"]]
    assert ids == plants.id.tolist()
    # cohérence : projection par la caméra et formule de plants.csv (x_px, y_px) à l'échelle du rendu
    k = rendu.shape[1] / photo.shape[1]
    ecart_formule = np.abs(P - plants[["x_px", "y_px"]].to_numpy() * k).max()

    # 1. centres projetés sur un pixel feuille
    mv = vert(rendu)
    h, l = mv.shape

    def part_sur_feuille(pts):
        ok = 0
        for x, y in pts:
            i, j = int(round(y)), int(round(x))
            fen = mv[max(i - 2, 0):i + 3, max(j - 2, 0):j + 3]
            ok += bool(fen.size and fen.any())
        return ok / len(pts)

    m_tel = part_sur_feuille(P)
    variantes_pts = {"miroir gauche-droite": np.c_[l - P[:, 0], P[:, 1]], "miroir haut-bas": np.c_[P[:, 0], h - P[:, 1]],
                     "rotation 180°": np.c_[l - P[:, 0], h - P[:, 1]], "rotation 90°": np.c_[h - P[:, 1], P[:, 0]]}
    m_var = {k_: part_sur_feuille(v) for k_, v in variantes_pts.items()}

    # 2. corrélation des densités de vert par blocs (13 x 13 blocs de ~5 m)
    n = 13
    bp = blocs(vert(photo), n)
    br = blocs(mv, n)
    corr = {"telle quelle": float(np.corrcoef(bp.ravel(), br.ravel())[0, 1])}
    for nom, f in (("miroir gauche-droite", np.fliplr), ("miroir haut-bas", np.flipud), ("rotation 180°", np.rot90),
                   ("rotation 90°", None)):
        b2 = np.rot90(br, 2) if nom == "rotation 180°" else (np.rot90(br, 1) if nom == "rotation 90°" else f(br))
        corr[nom] = float(np.corrcoef(bp.ravel(), b2.ravel())[0, 1])
    # densité des centres détectés par blocs (ce que le rendu doit reproduire)
    bc = np.zeros((n, n))
    for x, y in plants[["x_px", "y_px"]].to_numpy():
        bc[min(int(y / photo.shape[0] * n), n - 1), min(int(x / photo.shape[1] * n), n - 1)] += 1
    corr_centres_rendu = float(np.corrcoef(bc.ravel(), br.ravel())[0, 1])
    corr_centres_photo = float(np.corrcoef(bc.ravel(), bp.ravel())[0, 1])
    res = dict(
        ecart_max_projection_vs_formule_px=round(float(ecart_formule), 3),
        part_centres_sur_feuille=dict(telle_quelle=round(m_tel, 3), **{k_: round(v, 3) for k_, v in m_var.items()}),
        correlation_vert_photo_rendu_blocs_5m={k_: round(v, 3) for k_, v in corr.items()},
        correlation_densite_centres_vs_vert_rendu=round(corr_centres_rendu, 3),
        correlation_densite_centres_vs_vert_photo=round(corr_centres_photo, 3),
        part_vert_photo=round(float(vert(photo).mean()), 3), part_vert_rendu=round(float(mv.mean()), 3),
    )
    print(json.dumps(res, ensure_ascii=False, indent=1))
    (out / f"{a.prefixe}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    # planche : photo + centres | rendu + centres projetés par la caméra Blender, grille de 10 m
    c = 900
    g = Image.fromarray(photo).resize((c, c), Image.LANCZOS)
    dr = Image.fromarray(rendu).resize((c, c), Image.LANCZOS)
    for im, pts, sc in ((g, plants[["x_px", "y_px"]].to_numpy(), c / photo.shape[1]), (dr, P, c / l)):
        dd = ImageDraw.Draw(im)
        cote = photo.shape[1] * 0.05
        for v in range(-30, 31, 10):                                # grille en mètres (repère du rendu)
            px = (v / cote + 0.5) * c
            dd.line([(px, 0), (px, c)], fill=(255, 255, 255), width=1)
            dd.line([(0, px), (c, px)], fill=(255, 255, 255), width=1)
        for x, y in pts * sc:
            dd.ellipse((x - 5, y - 5, x + 5, y + 5), outline=(255, 30, 30), width=2)
    pl = Image.new("RGB", (2 * c + 20, c + 190), (250, 250, 247))
    pl.paste(g, (0, 70))
    pl.paste(dr, (c + 20, 70))
    D = ImageDraw.Draw(pl)
    D.text((10, 8), "Photo réelle (mosaïque) et centres de plants.csv", font=police(22, True), fill=(20, 20, 20))
    D.text((10, 40), "cercles : pixels (x_px, y_px) du détecteur ; grille : 10 m", font=police(16), fill=(60, 60, 60))
    D.text((c + 30, 8), "Rendu 3D de dessus et centres projetés par la caméra Blender", font=police(22, True), fill=(20, 20, 20))
    D.text((c + 30, 40), "cercles : world_to_camera_view(x_m, y_m, 0), sans relire l'image", font=police(16), fill=(60, 60, 60))
    t = (f"Centres projetés sur une feuille du rendu : {m_tel:.0%} (miroirs et rotations : "
         + ", ".join(f"{v:.0%}" for v in m_var.values()) + ").   "
         f"Corrélation du vert photo / rendu par blocs de 5 m : {corr['telle quelle']:.2f} "
         f"(retourné : {max(v for k_, v in corr.items() if k_ != 'telle quelle'):.2f} au mieux).")
    t2 = (f"Part de vert : photo {res['part_vert_photo']:.0%}, rendu {res['part_vert_rendu']:.0%}. Les zones vertes sans "
          "cercle de la photo sont surtout des arbres non-bananiers, que le détecteur ne compte pas.")
    D.text((10, c + 85), t.replace(".", ",", 0), font=police(17), fill=(20, 20, 20))
    D.text((10, c + 115), t2, font=police(17), fill=(20, 20, 20))
    D.text((10, c + 145), f"Écart maximal entre la projection de la caméra et la formule de plants.csv : "
           f"{ecart_formule:.2f} px.", font=police(17), fill=(20, 20, 20))
    pl.save(out / f"{a.prefixe}_dessus.png")
    print("planche :", out / f"{a.prefixe}_dessus.png")
    # zoom : le même quart (haut droit, x 0 à 33 m, y 0 à 33 m) dans les deux panneaux, agrandi deux fois
    z = Image.new("RGB", (2 * c + 20, c + 60), (250, 250, 247))
    z.paste(g.crop((c // 2, 0, c, c // 2)).resize((c, c), Image.LANCZOS), (0, 60))
    z.paste(dr.crop((c // 2, 0, c, c // 2)).resize((c, c), Image.LANCZOS), (c + 20, 60))
    Dz = ImageDraw.Draw(z)
    Dz.text((10, 15), "Zoom, quart nord-est (x 0 à 33 m, y 0 à 33 m) : photo + centres | rendu + centres projetés ; "
            "mêmes cercles aux mêmes pixels", font=police(20, True), fill=(20, 20, 20))
    z.save(out / f"{a.prefixe}_zoom.png")

    if a.proj_drone:
        pjd = json.loads(Path(a.proj_drone).read_text(encoding="utf-8"))
        im = Image.open(a.rendu_drone or d / "vue_drone_naturel.png").convert("RGB")
        dd = ImageDraw.Draw(im)
        for p in pjd["pieds"]:
            (x0, y0, _), (x1, y1, _) = p["sol"], p["sommet"]
            dd.line([(x0, y0), (x1, y1)], fill=(255, 40, 40), width=2)
            dd.ellipse((x0 - 4, y0 - 4, x0 + 4, y0 + 4), outline=(255, 40, 40), width=2)
        im.save(out / f"{a.prefixe}_drone.png")
        print("image :", out / f"{a.prefixe}_drone.png")


if __name__ == "__main__":
    main()
