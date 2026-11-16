"""Vidéo de démonstration : images (1920 x 1080, 30 i/s) de tous les plans, sauf le montage final.

Chaque plan est écrit dans out/video_demo/travail/seg_<plan>/0001.jpg, 0002.jpg, ... Les chiffres viennent de
out/demo_finale/chiffres.json et index.html, out/demo_martinique_rpg/comparaison_resume.json et du LISEZMOI de la visite.
Le plan « vol3d » lit les images rendues par scripts/video_demo_vol3d.py (15 i/s), les passe à 30 i/s (flux optique OpenCV)
et y pose les textes. Plans : titre echelles parcelles comptage maladies vol3d realiste reel fin.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/video_demo_plans2d.py [plan ...]
"""
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RACINE = Path(__file__).resolve().parents[1]
T = RACINE / "out/video_demo/travail"
W, H, FPS = 1920, 1080, 30
FONTS = Path("C:/Windows/Fonts")
FOND = (12, 24, 16)
VERT = (120, 230, 140)
ORANGE = (255, 150, 40)
VIOLET = (190, 150, 255)
BLANC = (245, 245, 245)
GRIS = (200, 210, 200)

_f = {}


def police(nom, t):
    k = (nom, t)
    if k not in _f:
        _f[k] = ImageFont.truetype(str(FONTS / nom), t)
    return _f[k]


def gras(t):
    return police("segoeuib.ttf", t)


def semi(t):
    return police("seguisb.ttf", t)


def norm(t):
    return police("segoeui.ttf", t)


def lisse(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def prog(t, a, b):
    return lisse((t - a) / (b - a)) if b > a else float(t >= a)


def calque():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def texte(g, xy, s, font, fill=BLANC, anchor="la", ombre=True):
    if ombre:
        g.text((xy[0] + 2, xy[1] + 3), s, font=font, fill=(0, 0, 0, 170), anchor=anchor)
    g.text(xy, s, font=font, fill=fill + (255,) if len(fill) == 3 else fill, anchor=anchor)


def poser(base, dessiner, a=1.0, dy=0):
    """Dessine sur un calque transparent, le rend a-transparent, le décale de dy px et le pose sur base (RGB)."""
    if a <= 0.003:
        return base
    c = calque()
    dessiner(ImageDraw.Draw(c, "RGBA"))
    if a < 1.0:
        al = c.getchannel("A").point(lambda v: int(v * a))
        c.putalpha(al)
    if dy:
        c = c.transform(c.size, Image.AFFINE, (1, 0, 0, 0, 1, -dy))
    return Image.alpha_composite(base.convert("RGBA"), c).convert("RGB")


def puce(g, box, fill=(10, 22, 14, 205), contour=None, r=22):
    g.rounded_rectangle(box, r, fill=fill, outline=contour, width=3 if contour else 0)


def coche(g, cx, cy, r=24, col=(46, 170, 80)):
    g.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (255,))
    k = r / 24
    g.line([(cx - 11 * k, cy + 1 * k), (cx - 3 * k, cy + 10 * k), (cx + 13 * k, cy - 9 * k)], fill=(255, 255, 255, 255),
           width=max(3, int(5 * k)), joint="curve")


def etiquette_illustration(g, y=H - 78):
    """Étiquette « bananiers 3D : illustration » (reste affichée pendant la visite 3D)."""
    s = "Bananiers 3D : illustration"
    w = g.textlength(s, font=semi(30)) + 56
    puce(g, (W - 40 - w, y, W - 40, y + 54), (40, 22, 70, 225), VIOLET + (255,), 27)
    texte(g, (W - 40 - w / 2, y + 27), s, semi(30), VIOLET, "mm", False)


def sauver(im, dossier, i):
    dossier.mkdir(parents=True, exist_ok=True)
    im.save(dossier / f"{i:04d}.jpg", quality=93, subsampling=0)


def charger(p, taille=None):
    im = Image.open(p).convert("RGB")
    return im.resize(taille, Image.LANCZOS) if taille else im


def fond_flou(img, sombre=0.35, flou=0):
    im = img.convert("RGB").resize((W, H), Image.LANCZOS)
    if flou:
        im = im.filter(ImageFilter.GaussianBlur(flou))
    return Image.blend(im, Image.new("RGB", (W, H), FOND), 1 - sombre)


def coins_ronds(im, r):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, im.size[0] - 1, im.size[1] - 1), r, fill=255)
    im = im.convert("RGBA")
    im.putalpha(m)
    return im


def sous(a, p="Image"):
    return a


# ------------------------------------------------------------------------------------------------ plans
def plan_titre():
    n = 4 * FPS
    sol = Image.open(T / "sol_naturel.jpg").convert("RGB")
    for i in range(n):
        t = i / FPS
        z = 1.0 + 0.05 * t / 4
        cw, ch = int(1500 / z), int(844 / z)
        x0, y0 = 2200 - cw // 2 + int(30 * t), 2000 - ch // 2
        im = sol.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.LANCZOS)
        im = Image.blend(im, Image.new("RGB", (W, H), FOND), 0.62)
        a1, a2 = prog(t, 0.2, 1.1), prog(t, 1.4, 2.2)

        def d1(g):
            texte(g, (W // 2, 470), "Field Scan", gras(190), BLANC, "mm")
        im = poser(im, d1, a1, int(30 * (1 - a1)))

        def d2(g):
            g.rounded_rectangle((W // 2 - 120, 580, W // 2 + 120, 586), 3, fill=VERT + (255,))
            texte(g, (W // 2, 660), "De l'image au bulletin de santé d'une bananeraie", norm(58), GRIS, "mm")
        im = poser(im, d2, a2, int(20 * (1 - a2)))
        sauver(im, T / "seg_titre", i + 1)


def plan_echelles():
    n = 6 * FPS
    cartes = [
        ("Satellite et avion", "Les parcelles", T.parent.parent / "demo_finale/medias/martinique_parcelles_zoom.jpg", (0, 0, 1600, 1035), VERT),
        ("Drone", "Le comptage des pieds", T.parent.parent / "demo_finale/medias/eloro_comptage_P15.jpg", (0, 0, 675, 691), ORANGE),
        ("Smartphone", "La maladie de la feuille", T.parent.parent / "demo_finale/medias/feuille_banspot_SIG_PER_NKA_69.jpg", (0, 0, 640, 480), (255, 110, 90)),
    ]
    ims = []
    for _, _, p, box, _c in cartes:
        im = Image.open(p).convert("RGB").crop(box)
        r = max(560 / im.size[0], 380 / im.size[1])
        im = im.resize((int(im.size[0] * r) + 1, int(im.size[1] * r) + 1), Image.LANCZOS)
        ox, oy = (im.size[0] - 560) // 2, (im.size[1] - 380) // 2
        ims.append(coins_ronds(im.crop((ox, oy, ox + 560, oy + 380)), 24))
    for i in range(n):
        t = i / FPS
        im = Image.new("RGB", (W, H), FOND)
        a0 = prog(t, 0.0, 0.7)

        def dt(g):
            texte(g, (W // 2, 150), "Trois échelles, une même chaîne", gras(70), BLANC, "mm")
        im = poser(im, dt, a0)
        for k, (nom, sub, _p, _b, col) in enumerate(cartes):
            a = prog(t, 0.5 + k * 0.9, 1.3 + k * 0.9)
            x = 90 + k * 620

            def dc(g, k=k, nom=nom, sub=sub, col=col, x=x):
                puce(g, (x - 10, 270, x + 570, 800), (22, 40, 28, 255), col + (255,), 30)
                texte(g, (x + 30, 690), nom, gras(52), BLANC, "lm")
                texte(g, (x + 30, 750), sub, norm(38), GRIS, "lm")
                g.ellipse((x + 482, 650, x + 546, 714), fill=col + (255,))
                texte(g, (x + 514, 682), str(k + 1), gras(40), (10, 20, 12), "mm", False)
            im = poser(im, dc, a, int(40 * (1 - a)))
            tmp = ims[k]
            c = calque()
            c.paste(tmp, (x + 0, 290))
            al = c.getchannel("A").point(lambda v, a=a: int(v * a))
            c.putalpha(al)
            c = c.transform(c.size, Image.AFFINE, (1, 0, 0, 0, 1, -int(40 * (1 - a))))
            im = Image.alpha_composite(im.convert("RGBA"), c).convert("RGB")
        a3 = prog(t, 3.9, 4.7)

        def db(g):
            texte(g, (W // 2, 930), "Du plan large de l'exploitation jusqu'à une seule feuille", norm(46), VERT, "mm")
        im = poser(im, db, a3)
        sauver(im, T / "seg_echelles", i + 1)


def plan_parcelles():
    n = 12 * FPS
    src = Image.open(T.parent.parent / "demo_martinique_rpg/comparaison_auto_rpg.jpg").convert("RGB")
    sw, sh = src.size
    for i in range(n):
        t = i / FPS
        u = lisse(t / 12.0)
        z = 1.0 + 0.55 * u
        cw = sw / z * 0.985
        ch = cw * 9 / 16
        cx = sw * (0.50 - 0.16 * u)
        cy = sh * (0.50 - 0.04 * u)
        box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
        im = src.resize((W, H), Image.LANCZOS, box=box)
        a1 = prog(t, 0.3, 1.0)

        def dt(g):
            puce(g, (40, 36, 1120, 160), (10, 22, 14, 215))
            texte(g, (74, 70), "Parcelles : la photo aérienne devient un parcellaire", gras(44), BLANC)
            texte(g, (74, 118), "Basse-Pointe, Martinique · IGN BD ORTHO® et RPG", norm(30), GRIS)
        im = poser(im, dt, a1)

        def dl(g):
            puce(g, (40, H - 215, 1010, H - 40), (10, 22, 14, 215))
            for j, (c, s) in enumerate([((0, 220, 235), "parcelles déclarées, bananes (RPG)"),
                                        ((235, 60, 190), "parcelles déclarées, canne (RPG)"),
                                        ((250, 220, 40), "parcelles trouvées automatiquement")]):
                y = H - 180 + j * 46
                g.line([(70, y + 14), (140, y + 14)], fill=c + (255,), width=7)
                texte(g, (165, y), s, norm(34), BLANC)
        im = poser(im, dl, prog(t, 1.0, 1.8))
        a2 = prog(t, 6.4, 7.4)

        def dk(g):
            puce(g, (1000, 190, 1880, 760), (10, 22, 14, 232), VERT + (255,), 30)
            texte(g, (1040, 262), "112", gras(100), VERT, "lm")
            texte(g, (1220, 262), "parcelles déclarées (RPG)", norm(40), BLANC, "lm")
            texte(g, (1040, 390), "196", gras(100), VERT, "lm")
            texte(g, (1220, 372), "parcelles automatiques", norm(40), BLANC, "lm")
            texte(g, (1220, 416), "sur 390 ha", norm(34), GRIS, "lm")
            texte(g, (1040, 530), "Recouvrement médian 0,44 : le RPG est déclaratif,", norm(32), GRIS, "lm")
            texte(g, (1040, 570), "pas une vérité terrain du découpage.", norm(32), GRIS, "lm")
            g.line([(1040, 618), (1840, 618)], fill=(90, 130, 100, 255), width=2)
            texte(g, (1040, 680), "Zoom : 13 parcelles · 43 ha", gras(44), BLANC, "lm")
            texte(g, (1040, 728), "vigueur mesurée par zone", norm(34), VERT, "lm")
        im = poser(im, dk, a2, int(30 * (1 - a2)))
        sauver(im, T / "seg_parcelles", i + 1)


def plan_comptage():
    n = 12 * FPS
    src = Image.open(T.parent.parent / "demo_eloro/controle_pieds/extrait_P15.png").convert("RGB")
    g_img = src.crop((14, 22, 694, 700))
    d_img = src.crop((708, 22, 1388, 700))
    a_g, a_d = np.array(g_img), np.array(d_img)
    rouge = ((a_d[..., 0] > 170) & (a_d[..., 1] < 90) & (a_d[..., 2] < 90)).astype(np.uint8)
    rouge_d = cv2.dilate(rouge, np.ones((5, 5), np.uint8))
    nb, lab = cv2.connectedComponents(rouge_d)
    cent = []
    for k in range(1, nb):
        ys, xs = np.nonzero(lab == k)
        cent.append((k, xs.mean(), ys.mean(), len(xs)))
    cent = [c for c in cent if c[3] > 12]
    cent.sort(key=lambda c: c[1] * 0.8 + c[2] * 0.6 + np.sin(c[2] * 0.37 + c[1] * 0.11) * 25)  # balayage
    ordre = np.array([c[0] for c in cent])
    ncercles = len(cent)
    print("cercles reconnus :", ncercles, "(142 annoncés)", flush=True)
    rang = np.zeros(nb, dtype=np.int32) + 10**6
    rang[ordre] = np.arange(len(ordre))
    carte_rang = rang[lab]
    taille = 720
    g_big = g_img.resize((taille, taille), Image.LANCZOS)
    for i in range(n):
        t = i / FPS
        im = Image.new("RGB", (W, H), FOND)
        a0 = prog(t, 0.0, 0.7)
        pr = prog(t, 1.2, 7.4)
        k = int(round(pr * ncercles))
        masque = (carte_rang < k)[..., None]
        mix = np.where(masque, a_d, a_g)
        # les contours jaunes du panneau de droite restent visibles : on les reprend de d_img
        jaune = ((a_d[..., 0] > 200) & (a_d[..., 1] > 200) & (a_d[..., 2] < 90))[..., None]
        mix = np.where(jaune, a_d, mix)
        d_big = Image.fromarray(mix.astype(np.uint8)).resize((taille, taille), Image.LANCZOS)

        def dt(g):
            texte(g, (60, 56), "Drone : comptage des pieds", gras(54), BLANC)
            texte(g, (60, 120), "El Oro, Équateur · carré de 40 m dans la parcelle P15 · 6,4 cm par pixel", norm(32), GRIS)
        im = poser(im, dt, a0)
        c = calque()
        c.paste(coins_ronds(g_big, 20), (110, 190))
        c.paste(coins_ronds(d_big, 20), (1090, 190))
        al = c.getchannel("A").point(lambda v, a=a0: int(v * a))
        c.putalpha(al)
        im = Image.alpha_composite(im.convert("RGBA"), c).convert("RGB")

        def dl(g):
            texte(g, (470, 925), "image du drone", norm(32), GRIS, "mm")
            texte(g, (1450, 925), "un cercle rouge par pied détecté", norm(32), GRIS, "mm")
            g.polygon([(870, 540), (870, 580), (905, 560)], fill=VERT + (255,))
            g.polygon([(905, 540), (905, 580), (940, 560)], fill=VERT + (255,))
            g.polygon([(940, 540), (940, 580), (975, 560)], fill=VERT + (255,))
        im = poser(im, dl, a0)
        ac = 1 - prog(t, 8.0, 8.6)

        def dc(g):
            g.rounded_rectangle((1090, 150, 1810, 188), 0, fill=(0, 0, 0, 0))
            texte(g, (1090 + 360, 972), f"{int(round(pr * 142))} pieds détectés dans ce carré", gras(48), VERT, "mm")
        im = poser(im, dc, ac * a0)
        ab = prog(t, 8.2, 9.2)

        def db(g):
            puce(g, (60, 950, 960, 1050), (22, 40, 28, 255), VERT + (255,), 26)
            texte(g, (100, 1000), "1 026", gras(66), VERT, "lm")
            texte(g, (320, 1000), "pieds détectés dans les 3 blocs de bananiers", norm(30), BLANC, "lm")
            puce(g, (990, 950, 1860, 1050), (22, 40, 28, 255), ORANGE + (255,), 26)
            texte(g, (1030, 1000), "F1 0,81", gras(66), ORANGE, "lm")
            texte(g, (1290, 988), "plantation dense jamais vue", norm(30), BLANC, "lm")
            texte(g, (1290, 1024), "4 641 pieds trouvés pour 5 029", norm(26), GRIS, "lm")
        im = poser(im, db, ab, int(30 * (1 - ab)))
        sauver(im, T / "seg_comptage", i + 1)


def plan_maladies():
    n = 12 * FPS
    d = json.loads((T.parent.parent / "demo_finale/chiffres.json").read_text(encoding="utf-8"))
    ph = d["maladies_photos"]
    sains = [m for m in ph if m["classe_vraie"] == "sans_taches"]
    mal = [m for m in ph if m["classe_vraie"] == "taches"]
    ordre = [sains[0], mal[0], sains[1], mal[1], mal[2], sains[2], mal[3], sains[3]]
    tw, th = 420, 315
    ims = []
    for m in ordre:
        im = Image.open(T.parent.parent / "demo_finale" / m["vignette"]).convert("RGB").resize((tw, th), Image.LANCZOS)
        ims.append(coins_ronds(im, 18))
    for i in range(n):
        t = i / FPS
        im = Image.new("RGB", (W, H), FOND)

        def dt(g):
            texte(g, (60, 52), "Smartphone : la feuille est-elle malade ?", gras(54), BLANC)
            texte(g, (60, 116), "8 photos de feuilles de BanSpot tirées au hasard, jamais vues à l'apprentissage", norm(30), GRIS)
        im = poser(im, dt, prog(t, 0, 0.7))
        for k, m in enumerate(ordre):
            col, lig = k % 4, k // 4
            x, y = 75 + col * 450, 175 + lig * 395
            a = prog(t, 0.6 + k * 0.8, 1.2 + k * 0.8)
            ar = prog(t, 1.2 + k * 0.8, 1.8 + k * 0.8)
            c = calque()
            c.paste(ims[k], (x, y))
            c.putalpha(c.getchannel("A").point(lambda v, a=a: int(v * a)))
            im = Image.alpha_composite(im.convert("RGBA"), c).convert("RGB")
            saine = m["reponse"] == "saine"
            couleur = VERT if saine else ORANGE
            lib = "feuille saine" if saine else "cercosporiose noire"

            def dr(g, x=x, y=y, lib=lib, couleur=couleur, m=m):
                puce(g, (x, y + th + 8, x + tw, y + th + 66), (22, 40, 28, 255), couleur + (255,), 16)
                coche(g, x + 34, y + th + 37, 21)
                texte(g, (x + 68, y + th + 37), lib, semi(32), couleur, "lm", False)
                texte(g, (x + tw - 14, y + th + 37), f"{float(m['p_malade']):.2f}".replace(".", ","), norm(26), GRIS, "rm", False)
            im = poser(im, dr, ar)
        ab = prog(t, 8.3, 9.2)

        def db(g):
            texte(g, (W // 2, 985), "8 justes sur 8 sur cet échantillon. Mesure complète sur BanSpot (646 feuilles tachées, 646 saines) :", norm(30), GRIS, "mm")
            puce(g, (150, 1012, 1770, 1070), (22, 40, 28, 255), ORANGE + (255,), 26)
            texte(g, (W // 2, 1041), "4 malades ratés sur 646  ·  56 fausses alertes sur 646", gras(38), ORANGE, "mm", False)
        im = poser(im, db, ab, int(20 * (1 - ab)))
        sauver(im, T / "seg_maladies", i + 1)


def plan_realiste():
    n = 8 * FPS
    dossier = T.parent.parent / "rendu_blender/v4/survol_3d"
    for i in range(n):
        t = i / FPS
        j = 109 + (i / n) * (300 - 109)
        i0 = int(math.floor(j))
        a = j - i0
        f0 = Image.open(dossier / f"image_{i0:04d}.png").convert("RGB")
        f1 = Image.open(dossier / f"image_{min(i0 + 1, 300):04d}.png").convert("RGB")
        im = Image.blend(f0, f1, a)
        z = 1.0 + 0.06 * t / 8
        cw, ch = im.size[0] / z, im.size[1] / z
        x0, y0 = (im.size[0] - cw) / 2, (im.size[1] - ch) / 2
        im = im.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))

        def dt(g):
            puce(g, (40, H - 190, 1560, H - 40), (10, 22, 14, 220))
            texte(g, (76, H - 150), "Rendu réaliste Blender d'une parcelle de drone (Flora Pluas, Équateur)", gras(42), BLANC)
            texte(g, (76, H - 96), "un bananier 3D par pied détecté, à sa position réelle · formes, arbres et décor : illustration", norm(30), GRIS)
        im = poser(im, dt, prog(t, 0.3, 1.0))
        im = poser(im, etiquette_illustration, prog(t, 0.3, 1.0))
        sauver(im, T / "seg_realiste", i + 1)


def plan_reel():
    n = 6 * FPS
    for i in range(n):
        t = i / FPS
        im = Image.new("RGB", (W, H), FOND)

        def dt(g):
            texte(g, (W // 2, 110), "Ce qui est réel, ce qui ne l'est pas", gras(64), BLANC, "mm")
        im = poser(im, dt, prog(t, 0, 0.6))
        reel = ["la photo aérienne (IGN)", "les parcelles du RPG et leurs scores", "le comptage des pieds à El Oro", "les réponses sur les feuilles (BanSpot)"]
        ill = ["les bananiers et la canne en 3D", "posés sur les rangs de la photo"]
        a1 = prog(t, 0.5, 1.2)

        def dr(g):
            puce(g, (90, 210, 930, 800), (22, 40, 28, 255), VERT + (255,), 30)
            texte(g, (130, 275), "RÉEL", gras(56), VERT, "lm")
            for j, s in enumerate(reel):
                a = prog(t, 1.0 + j * 0.35, 1.5 + j * 0.35)
                if a > 0:
                    coche(g, 150, 380 + j * 90, 20)
                    texte(g, (190, 380 + j * 90), s, norm(38), (BLANC[0], BLANC[1], BLANC[2], int(255 * a)), "lm", False)
        im = poser(im, dr, a1)

        def di(g):
            puce(g, (990, 210, 1830, 800), (40, 22, 70, 255), VIOLET + (255,), 30)
            texte(g, (1030, 275), "ILLUSTRATION", gras(56), VIOLET, "lm")
            for j, s in enumerate(ill):
                a = prog(t, 2.6 + j * 0.4, 3.1 + j * 0.4)
                if a > 0:
                    texte(g, (1030, 380 + j * 80), s, norm(38), (BLANC[0], BLANC[1], BLANC[2], int(255 * a)), "lm", False)
            texte(g, (1030, 600), "aucun comptage n'est affiché", norm(34), (GRIS[0], GRIS[1], GRIS[2], 230), "lm", False)
            texte(g, (1030, 650), "sur la photo d'avion de Martinique", norm(34), (GRIS[0], GRIS[1], GRIS[2], 230), "lm", False)
        im = poser(im, di, prog(t, 2.2, 2.9))

        def df(g):
            texte(g, (W // 2, 900), "Trois sites, car aucune donnée publique ne couvre", norm(40), VERT, "mm")
            texte(g, (W // 2, 955), "une même ferme aux trois échelles.", norm(40), VERT, "mm")
        im = poser(im, df, prog(t, 3.8, 4.6))
        sauver(im, T / "seg_reel", i + 1)


def plan_fin():
    n = 4 * FPS
    sol = Image.open(T / "sol_naturel.jpg").convert("RGB")
    for i in range(n):
        t = i / FPS
        z = 1.0 + 0.03 * t / 4
        cw, ch = int(1500 / z), int(844 / z)
        x0, y0 = 1500, 2600
        im = sol.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.LANCZOS)
        im = Image.blend(im, Image.new("RGB", (W, H), FOND), 0.7)

        def d1(g):
            texte(g, (W // 2, 330), "Field Scan · Intelligence Lab ING4", gras(84), BLANC, "mm")
            g.rounded_rectangle((W // 2 - 120, 400, W // 2 + 120, 406), 3, fill=VERT + (255,))
            texte(g, (W // 2, 500), "Sources", semi(36), VERT, "mm")
            for j, s in enumerate(["IGN, BD ORTHO® et RPG (Licence Ouverte Etalab 2.0)",
                                   "UTMACH / OpenAerialMap (CC BY 4.0)",
                                   "ReforesTree (CC BY 4.0)",
                                   "BanSpot"]):
                texte(g, (W // 2, 565 + j * 52), s, norm(34), GRIS, "mm")
        im = poser(im, d1, prog(t, 0.2, 1.0))
        sauver(im, T / "seg_fin", i + 1)


# ------------------------------------------------------------------------------------------------ vol 3D
def lire_serie(nom):
    fs = sorted((T / f"vol_{nom}").glob("*.jpg"))
    return fs


def interpoler(f0, f1, a=0.5):
    """Image intermédiaire par flux optique (Farneback) entre deux images BGR."""
    g0 = cv2.cvtColor(cv2.resize(f0, (960, 540)), cv2.COLOR_BGR2GRAY)
    g1 = cv2.cvtColor(cv2.resize(f1, (960, 540)), cv2.COLOR_BGR2GRAY)
    fl01 = cv2.calcOpticalFlowFarneback(g0, g1, None, 0.5, 4, 25, 3, 7, 1.5, 0)
    fl10 = cv2.calcOpticalFlowFarneback(g1, g0, None, 0.5, 4, 25, 3, 7, 1.5, 0)
    fl01 = cv2.resize(fl01, (W, H)) * 2
    fl10 = cv2.resize(fl10, (W, H)) * 2
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    w0 = cv2.remap(f0, gx - a * fl10[..., 0] * -1 * -1 + 0 * gx - 0, gy - a * fl10[..., 1] * -1 * -1 + 0 * gy - 0, cv2.INTER_LINEAR,
                   borderMode=cv2.BORDER_REPLICATE) if False else None
    # image à t=a : on cherche pour chaque pixel sa position dans f0 (x - a*F01) et dans f1 (x - (1-a)*F10)
    w0 = cv2.remap(f0, gx - a * fl01[..., 0], gy - a * fl01[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    w1 = cv2.remap(f1, gx - (1 - a) * fl10[..., 0], gy - (1 - a) * fl10[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return cv2.addWeighted(w0, 1 - a, w1, a, 0)


def plan_vol3d():
    series = [lire_serie(k) for k in "ABC"]
    if not all(series):
        raise SystemExit("images du vol 3D absentes")
    fps_src = 15
    # liste des images à 15 i/s : A puis B (raccord direct), C en fondu de 0,5 s sur la fin de B
    seq = series[0] + series[1]
    fondu = 15 // 2
    total15 = len(seq) + len(series[2]) - fondu
    n = total15 * 2
    print("images sources :", len(seq), "+", len(series[2]), "-> sorties 30 i/s :", n, flush=True)

    def src(j):  # image 15 i/s numéro j
        if j < len(seq) - fondu:
            return cv2.imread(str(seq[j]))
        if j < len(seq):
            k = j - (len(seq) - fondu)
            a = (k + 1) / (fondu + 1)
            return cv2.addWeighted(cv2.imread(str(seq[j])), 1 - a, cv2.imread(str(series[2][k])), a, 0)
        return cv2.imread(str(series[2][j - len(seq) + fondu]))
    cache = {}

    def get(j):
        if j not in cache:
            cache[j] = src(j)
            for old in [c for c in cache if c < j - 2]:
                del cache[old]
        return cache[j]
    tA, tB = len(series[0]) / fps_src, len(series[1]) / fps_src
    for i in range(n):
        j = i // 2
        if i % 2 == 0:
            fr = get(j)
        elif j + 1 < total15:
            fr = interpoler(get(j), get(j + 1))
        else:
            fr = get(j)
        im = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
        t = i / FPS
        a_ill = prog(t, 0.2, 0.9)
        legendes = [
            (0.0, tA, "Visite 3D : 13 parcelles de Basse-Pointe (43 ha)", "photo IGN, parcelles du RPG et scores de la chaîne, au-dessus des parcelles"),
            (tA, tA + tB - 0.5, "Au ras des rangs", "bananiers d'illustration posés sur les rangs de la photo"),
            (tA + tB - 0.5, n / FPS, "Mode Santé : les zones moins vertes en orange", "0,01 à 0,20 ha par parcelle, sous le seuil de 0,5 ha : toutes les parcelles restent à 100 (RAS)"),
        ]
        for (d0, d1, tit, sub) in legendes:
            a = prog(t, d0 + 0.3, d0 + 0.9) * (1 - prog(t, d1 - 0.5, d1 - 0.1))
            if a > 0.01:
                def dl(g, tit=tit, sub=sub):
                    puce(g, (40, 36, 1560 if len(sub) > 80 else 1280, 160), (10, 22, 14, 215))
                    texte(g, (76, 70), tit, gras(42), BLANC)
                    texte(g, (76, 118), sub, norm(28), GRIS)
                im = poser(im, dl, a)
        im = poser(im, etiquette_illustration, a_ill)
        sauver(im, T / "seg_vol3d", i + 1)


PLANS = dict(titre=plan_titre, echelles=plan_echelles, parcelles=plan_parcelles, comptage=plan_comptage,
             maladies=plan_maladies, vol3d=plan_vol3d, realiste=plan_realiste, reel=plan_reel, fin=plan_fin)

if __name__ == "__main__":
    choix = sys.argv[1:] or [k for k in PLANS if k != "vol3d"]
    for k in choix:
        print("plan", k, flush=True)
        PLANS[k]()
    print("terminé", flush=True)
