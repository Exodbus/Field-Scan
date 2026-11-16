"""Vidéo « pitch » v2 (environ 58 s) : images 1920 x 1080 à 30 i/s dans out/video_demo/travail/seg_pitch_v2/.

Reprend les plans réels de la v1 en suivant la synthèse des relecteurs : chiffres alignés sur ce qui est montré
(142 bananiers sur le carré, fourchette 800 à 950 sur les 3 parcelles), parcelles « déclarées », bandeau de site fixe,
texte blanc Segoe UI Semibold, coupes avec fondu au noir, aucun texte fantôme. Les images du vol 3D viennent de
scripts/video_demo_vol3d.py (travail/v2_A, v2_B, v2_C).

Sources des chiffres : out/demo_finale/chiffres.json (eloro P14 à P16 : somme des colonnes « bas » 155+259+386 = 800 et
« haut » 185+309+460 = 954 ; maladies_photos) ; out/demo_eloro/controle_pieds/extrait_P15.png (142 cercles) ;
out/demo_finale/index.html (BanSpot : 4 malades sans alerte sur 646 tachées, 56 saines en alerte sur 646) ; visite
(13 parcelles, 43 ha). « Près de 8 sur 10 » : rappel 0,776 du protocole v5 (test banano), repris de la demande de relecture.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/video_demo_pitch_v2.py [--debut N --fin M]
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

import video_demo_plans2d as P  # noqa: E402

W, H, FPS = 1920, 1080, 30
T = RACINE / "out/video_demo/travail"
OUT = T / "seg_pitch_v2"
V = RACINE / "out/visite_basse_pointe_zone"
D = json.loads((V / "donnees.json").read_text(encoding="utf-8"))
SOL = Image.open(T / "sol_naturel.jpg").convert("RGB")
EMP = D["emprise"]
BLANC, ACC, FOND = (255, 255, 255), (127, 208, 138), (12, 24, 16)
GRIS = (205, 214, 207)
PILULE = (43, 58, 51)
lisse, prog = P.lisse, P.prog


def sb(t):
    return P.police("seguisb.ttf", t)


# ------------------------------------------------------------------------------------------------ outils de texte
def texte_doux(im, lignes, x, y, taille, couleur=BLANC, a=1.0, dy=0, ancre="m", interligne=1.24, police=None):
    """Texte blanc avec ombre douce. ancre « m » : centré en x ; « l » : aligné à gauche. y = haut de la première ligne."""
    if a <= 0.003:
        return im
    f = police or sb(taille)
    h = int(taille * interligne)
    larg = max(int(f.getlength(s)) for s in lignes) + 80
    x0 = int(x - larg / 2) if ancre == "m" else int(x - 20)
    y0 = int(y - dy - 20)
    box = (max(0, x0), max(0, y0), min(W, x0 + larg + 40), min(H, y0 + h * len(lignes) + 60))
    if box[2] <= box[0] or box[3] <= box[1]:
        return im
    c = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
    g = ImageDraw.Draw(c)
    for k, s in enumerate(lignes):
        px = (x - box[0]) if ancre == "m" else (x - box[0])
        g.text((px, y - dy - box[1] + k * h), s, font=f, fill=(0, 0, 0, 255), anchor="ma" if ancre == "m" else "la")
    ombre = c.filter(ImageFilter.GaussianBlur(6))
    ombre.putalpha(ombre.getchannel("A").point(lambda v: int(min(255, v * 1.5) * 0.75 * a)))
    c2 = Image.new("RGBA", c.size, (0, 0, 0, 0))
    g2 = ImageDraw.Draw(c2)
    for k, s in enumerate(lignes):
        g2.text((x - box[0], y - dy - box[1] + k * h), s, font=f, fill=couleur + (int(255 * a),),
                anchor="ma" if ancre == "m" else "la")
    c2 = Image.alpha_composite(ombre, c2)
    base = im.convert("RGBA")
    base.alpha_composite(c2, (box[0], box[1]))
    return base.convert("RGB")


def appar(t, t0, d=0.4):
    a = lisse((t - t0) / d)
    return a, 24 * (1 - a)


def degrade_bas(im, hauteur=380, force=200):
    a = np.zeros((hauteur, W, 4), np.uint8)
    a[..., 3] = (force * (np.linspace(0, 1, hauteur) ** 1.5))[:, None].astype(np.uint8)
    b = im.convert("RGBA")
    b.alpha_composite(Image.fromarray(a, "RGBA"), (0, H - hauteur))
    return b.convert("RGB")


def degrade_haut(im, hauteur=150, force=170):
    a = np.zeros((hauteur, W, 4), np.uint8)
    a[..., 3] = (force * (np.linspace(1, 0, hauteur) ** 1.5))[:, None].astype(np.uint8)
    b = im.convert("RGBA")
    b.alpha_composite(Image.fromarray(a, "RGBA"), (0, 0))
    return b.convert("RGB")


def bandeau(im, texte):
    """Bandeau fixe en haut à gauche : où a été prise l'image."""
    f = sb(28)
    w = int(f.getlength(texte)) + 48
    c = Image.new("RGBA", (w, 56), (0, 0, 0, 0))
    g = ImageDraw.Draw(c)
    g.rounded_rectangle((0, 0, w - 1, 55), 16, fill=(10, 22, 14, 215), outline=ACC + (255,), width=2)
    g.text((24, 28), texte, font=f, fill=BLANC + (255,), anchor="lm")
    b = im.convert("RGBA")
    b.alpha_composite(c, (40, 34))
    return b.convert("RGB")


def pilule(im):
    f = sb(30)
    s = "Bananiers 3D : illustration"
    w = int(f.getlength(s)) + 56
    c = Image.new("RGBA", (w, 58), (0, 0, 0, 0))
    g = ImageDraw.Draw(c)
    g.rounded_rectangle((0, 0, w - 1, 57), 29, fill=PILULE + (240,), outline=ACC + (255,), width=3)
    g.text((w / 2, 29), s, font=f, fill=BLANC + (255,), anchor="mm")
    b = im.convert("RGBA")
    b.alpha_composite(c, (W - 40 - w, H - 40 - 58))
    return b.convert("RGB")


def vue_sol(cx, cy, cw):
    ch = cw * 9 / 16
    return SOL.resize((W, H), Image.BICUBIC, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)), (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)


def pix(x, y):
    return (x - EMP["xmin"]) / 0.2, (EMP["ymax"] - y) / 0.2


# ------------------------------------------------------------------------------------------------ plans
def s1(t):  # accroche : photo réelle, zoom +8 %, pas assombrie
    z = 1.0 + 0.08 * t / 4
    im, _ = vue_sol(2240 + 30 * t, 2200, 3300 / z)
    im = degrade_bas(im, 360, 190)
    a, dy = appar(t, 0.5)
    im = texte_doux(im, ["Quelles parcelles vont bien ?", "Lesquelles souffrent ?"], W // 2, 800, 80, a=a, dy=dy)
    return bandeau(im, "MARTINIQUE · photo aérienne IGN")


PARC = sorted(D["parcelles"], key=lambda p: -p["ancre"][1])


def s2(t):  # parcelles déclarées suivies depuis le ciel
    u = prog(t, 0, 10.0)
    cw = 4400 - 1100 * u
    im, box = vue_sol(2240, 1400 + 1700 * u, cw)
    sc = W / (box[2] - box[0])
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(c)
    for k, p in enumerate(PARC):
        a = prog(t, 1.0 + k * 0.4, 1.6 + k * 0.4)
        if a <= 0:
            continue
        for poly in p["bord"]:
            ring = poly[0]
            pts = [((px - box[0]) * sc, (py - box[1]) * sc) for px, py in (pix(ring[i], ring[i + 1]) for i in range(0, len(ring), 2))]
            g.polygon(pts, fill=ACC + (int(55 * a),), outline=ACC + (int(255 * a),), width=5)
    b = im.convert("RGBA")
    b.alpha_composite(c)
    im = degrade_bas(b.convert("RGB"), 420, 205)
    a, dy = appar(t, 0.6)
    im = texte_doux(im, ["À partir du plan des parcelles,", "Field Scan suit chacune depuis le ciel."], W // 2, 800, 72, a=a, dy=dy)
    nb = min(13, int(round(prog(t, 1.0, 6.2) * 13)))
    a2 = prog(t, 1.0, 1.5)
    f = sb(60)
    s = f"{nb} parcelles · 43 hectares"
    w = int(f.getlength("13 parcelles · 43 hectares")) + 70
    c = Image.new("RGBA", (w, 104), (0, 0, 0, 0))
    ImageDraw.Draw(c).rounded_rectangle((0, 0, w - 1, 103), 26, fill=(10, 22, 14, int(220 * a2)), outline=ACC + (int(255 * a2),), width=3)
    ImageDraw.Draw(c).text((w // 2, 52), s, font=f, fill=ACC + (int(255 * a2),), anchor="mm")
    b = im.convert("RGBA")
    b.alpha_composite(c, (W - 40 - w, 34))
    return bandeau(b.convert("RGB"), "MARTINIQUE · photo aérienne IGN")


# --- drone
_src = Image.open(RACINE / "out/demo_eloro/controle_pieds/extrait_P15.png").convert("RGB")
_g_img, _d_img = _src.crop((14, 22, 694, 700)), _src.crop((708, 22, 1388, 700))
_a_d = np.array(_d_img)
_rouge = cv2.dilate(((_a_d[..., 0] > 170) & (_a_d[..., 1] < 90) & (_a_d[..., 2] < 90)).astype(np.uint8), np.ones((5, 5), np.uint8))
_nb, _lab = cv2.connectedComponents(_rouge)
_cent = []
for _k in range(1, _nb):
    _ys, _xs = np.nonzero(_lab == _k)
    if len(_xs) > 12:
        _cent.append((_xs.mean(), _ys.mean()))
_cent.sort(key=lambda c: c[0] * 0.8 + c[1] * 0.6 + np.sin(c[1] * 0.37 + c[0] * 0.11) * 25)
NCERC = len(_cent)
print("cercles reconnus :", NCERC, flush=True)
_FOND_FLOU = None
TAILLE = 1000
_CLEAN = _g_img.resize((TAILLE, TAILLE), Image.LANCZOS)


def fond_flou():
    global _FOND_FLOU
    if _FOND_FLOU is None:
        r = max(W / _g_img.size[0], H / _g_img.size[1])
        im = _g_img.resize((int(_g_img.size[0] * r) + 1, int(_g_img.size[1] * r) + 1), Image.LANCZOS)
        im = im.crop(((im.size[0] - W) // 2, 0, (im.size[0] - W) // 2 + W, H)).filter(ImageFilter.GaussianBlur(24))
        _FOND_FLOU = Image.blend(im, Image.new("RGB", (W, H), FOND), 0.62)
    return _FOND_FLOU


def s3(t):
    im = fond_flou().copy()
    X0, Y0 = 60, 40
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    c.paste(P.coins_ronds(_CLEAN, 28), (X0, Y0))
    b = im.convert("RGBA")
    b.alpha_composite(c)
    g = ImageDraw.Draw(b, "RGBA")
    k = 1000 / 680
    nrev = 0
    for i, (cx, cy) in enumerate(_cent):
        tk = 0.9 + 5.6 * i / NCERC
        a = lisse((t - tk) / 0.15)
        if a <= 0:
            continue
        nrev += 1
        r = 12 * (0.4 + 0.6 * a)
        x, y = X0 + cx * k, Y0 + cy * k
        g.ellipse((x - r, y - r, x + r, y + r), outline=(255, 60, 50, int(255 * a)), width=4)
    im = b.convert("RGB")
    # pastille du compteur : sur le coin noir de l'image
    ac, dyc = appar(t, 0.8)
    cb = Image.new("RGBA", (560, 250), (0, 0, 0, 0))
    gd = ImageDraw.Draw(cb)
    gd.rounded_rectangle((0, 0, 559, 249), 28, fill=(10, 22, 14, int(235 * ac)), outline=ACC + (int(255 * ac),), width=3)
    gd.text((34, 14), str(nrev), font=P.gras(130), fill=ACC + (int(255 * ac),))
    gd.text((34, 160), "bananiers repérés sur", font=sb(36), fill=BLANC + (int(255 * ac),))
    gd.text((34, 202), "ce carré de 40 m", font=sb(36), fill=BLANC + (int(255 * ac),))
    b = im.convert("RGBA")
    b.alpha_composite(cb, (X0 + TAILLE - 560 - 16, Y0 + TAILLE - 250 - 16))
    im = b.convert("RGB")
    a, dy = appar(t, 0.4)
    im = texte_doux(im, ["Un drone passe :", "les bananiers sont", "repérés un par un."], 1100, 90, 72, a=a, dy=dy, ancre="l")
    a2, dy2 = appar(t, 3.0)
    im = texte_doux(im, ["Sur les 3 parcelles :", "environ 800 à 950 bananiers"], 1100, 470, 44, ACC, a=a2, dy=dy2, ancre="l")
    a3, dy3 = appar(t, 4.6)
    im = texte_doux(im, ["Testé sur une plantation jamais vue :", "près de 8 bananiers sur 10 retrouvés."], 1100, 650, 40, BLANC, a=a3, dy=dy3, ancre="l")
    return bandeau(im, "ÉQUATEUR · drone")


# --- feuilles
_ch = json.loads((RACINE / "out/demo_finale/chiffres.json").read_text(encoding="utf-8"))["maladies_photos"]
_sa = [m for m in _ch if m["classe_vraie"] == "sans_taches"]
_ma = [m for m in _ch if m["classe_vraie"] == "taches"]
_ordre = [_sa[0], _ma[0], _ma[1], _sa[1]]
_thumbs = [P.coins_ronds(Image.open(RACINE / "out/demo_finale" / m["vignette"]).convert("RGB").resize((533, 400), Image.LANCZOS), 22) for m in _ordre]


def s4(t):
    im = Image.new("RGB", (W, H), FOND)
    b = im.convert("RGBA")
    g = ImageDraw.Draw(b, "RGBA")
    for k, m in enumerate(_ordre):
        x, y = 50 + (k % 2) * 557, 100 + (k // 2) * 480
        a = lisse((t - (0.5 + 0.25 * k)) / 0.4)
        if a <= 0:
            continue
        c = Image.new("RGBA", (533, 464), (0, 0, 0, 0))
        c.paste(_thumbs[k], (0, 0))
        saine = m["reponse"] == "saine"
        col = ACC if saine else (255, 160, 70)
        gd = ImageDraw.Draw(c)
        gd.rounded_rectangle((0, 408, 532, 463), 18, fill=(22, 40, 28, 255), outline=col + (255,), width=3)
        P.coche(gd, 36, 436, 20)
        gd.text((72, 436), "feuille saine" if saine else "feuille malade", font=sb(34), fill=col + (255,), anchor="lm")
        c.putalpha(c.getchannel("A").point(lambda v, a=a: int(v * a)))
        b.alpha_composite(c, (x, int(y + 20 * (1 - a))))
    im = b.convert("RGB")
    a, dy = appar(t, 0.4)
    im = texte_doux(im, ["Une simple photo", "de feuille suffit", "pour repérer", "la maladie."], 1260, 110, 72, a=a, dy=dy, ancre="l")
    a2, dy2 = appar(t, 3.6)
    im = texte_doux(im, ["642 feuilles malades", "sur 646 repérées"], 1260, 560, 44, ACC, a=a2, dy=dy2, ancre="l")
    a3, dy3 = appar(t, 4.4)
    im = texte_doux(im, ["56 feuilles saines", "sur 646 signalées à tort"], 1260, 700, 44, ACC, a=a3, dy=dy3, ancre="l")
    a4, dy4 = appar(t, 5.0)
    im = texte_doux(im, ["sur des photos que le système", "n'avait jamais vues"], 1260, 850, 34, GRIS, a=a4, dy=dy4, ancre="l")
    return bandeau(im, "PHOTOS DE FEUILLES")


# --- vol 3D
SERIE = {k: {int(f.stem): f for f in (T / f"v2_{k}").glob("*.jpg")} for k in "ABC"}
_cache = {}


def img15(k, j):
    j = max(min(SERIE[k]) - 1, min(max(SERIE[k]) - 1, j))
    if (k, j) not in _cache:
        if len(_cache) > 10:
            _cache.pop(next(iter(_cache)))
        _cache[(k, j)] = cv2.imread(str(SERIE[k][j + 1]))
    return _cache[(k, j)]


def vol15(k, t):
    j = t * 15
    j0 = int(np.floor(j))
    a = j - j0
    if a < 0.25:
        fr = img15(k, j0)
    elif a < 0.75:
        fr = P.interpoler(img15(k, j0), img15(k, j0 + 1), 0.5)
    else:
        fr = img15(k, j0 + 1)
    return Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))


def vol3d(im, lignes, t, t0=0.4, size=72):
    im = degrade_haut(degrade_bas(im, 330, 185))
    a, dy = appar(t, t0)
    im = texte_doux(im, lignes, W // 2, H - 60 - int(size * 1.24) * len(lignes) - 90, size, a=a, dy=dy)
    return pilule(bandeau(im, "MARTINIQUE · visite 3D, bananiers simulés"))


def s5a(t):
    return vol3d(vol15("A", t), ["Puis le planteur se promène", "dans sa plantation."], t)


def s5b(t):
    n = int(round((4.0 + t) * 30)) + 1
    im = Image.open(T / "v2_B" / f"{n:04d}.jpg").convert("RGB")
    return vol3d(im, ["Entre les rangs de bananiers."], t, 1.2)


def s5c(t):
    return vol3d(vol15("C", t), ["Zones moins vertes sur la photo", "(pas un diagnostic)"], t, 0.3)


def s6(t):  # titre
    im, _ = vue_sol(2240 - 25 * t, 2200, 3000)
    im = Image.blend(im, Image.new("RGB", (W, H), FOND), 0.6)
    a, dy = appar(t, 0.3)
    im = texte_doux(im, ["Field Scan"], W // 2, 300, 200, a=a, dy=dy, police=P.gras(200))
    b = im.convert("RGBA")
    ImageDraw.Draw(b).rounded_rectangle((W // 2 - 120, 560, W // 2 + 120, 566), 3, fill=ACC + (int(255 * a),))
    im = b.convert("RGB")
    a2, dy2 = appar(t, 1.3)
    return texte_doux(im, ["Repérer plus tôt ce qui ne va pas,", "parcelle par parcelle."], W // 2, 620, 72, ACC, a=a2, dy=dy2)


def s7(t):  # fin
    im, _ = vue_sol(2240, 2200, 3000)
    im = Image.blend(im, Image.new("RGB", (W, H), FOND), 0.78)
    a, dy = appar(t, 0.2)
    im = texte_doux(im, ["Projet Intelligence Lab · ING4"], W // 2, 170, 72, a=a, dy=dy)
    a2, dy2 = appar(t, 0.6)
    im = texte_doux(im, ["3 sites, 3 jeux de données publics : aucune donnée", "ouverte ne couvre une même ferme aux trois échelles."], W // 2, 330, 44, ACC, a=a2, dy=dy2)
    b = im.convert("RGBA")
    bd = Image.new("RGBA", (W, 250), (10, 22, 14, int(225 * lisse((t - 0.8) / 0.4))))
    b.alpha_composite(bd, (0, 700))
    im = b.convert("RGB")
    a3, dy3 = appar(t, 1.0)
    return texte_doux(im, ["Sources : IGN BD ORTHO® et RPG (Licence Ouverte Etalab 2.0)", "UTMACH / OpenAerialMap (CC BY 4.0) · ReforesTree (CC BY 4.0) · BanSpot",
                           "Bananiers 3D : illustration"], W // 2, 730, 30, GRIS, a=a3, dy=dy3, interligne=1.5)


# (début, durée, fonction)
PLANS = [(0, 4, s1), (4, 10, s2), (14, 8, s3), (22, 8, s4), (30, 6.5, s5a), (36.5, 8.4, s5b), (44.9, 4.5, s5c),
         (49.4, 5, s6), (54.4, 4, s7)]
TOTAL = 58.4
DIP = 0.2


def image(i):
    t = i / FPS
    k = max(j for j, (d, _, _) in enumerate(PLANS) if d <= t + 1e-9)
    d, dur, f = PLANS[k]
    tl = min(t - d, dur - 1e-3)
    im = f(tl)
    noir = 0.0
    if tl < DIP:
        noir = 1 - tl / DIP if k > 0 else 0.0
    if dur - tl < DIP:
        noir = max(noir, 1 - (dur - tl) / DIP)
    if k == len(PLANS) - 1 and dur - tl < 0.4:
        noir = max(noir, 1 - (dur - tl) / 0.4)
    if noir > 0.01:
        im = Image.blend(im, Image.new("RGB", (W, H), (0, 0, 0)), min(1.0, noir))
    return im


if __name__ == "__main__":
    a = sys.argv[1:]
    n = int(TOTAL * FPS)
    deb = int(a[a.index("--debut") + 1]) if "--debut" in a else 0
    fin = int(a[a.index("--fin") + 1]) if "--fin" in a else n - 1
    pas = int(a[a.index("--pas") + 1]) if "--pas" in a else 1
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(deb, fin + 1, pas):
        image(i).save(OUT / f"{i + 1:04d}.jpg", quality=93, subsampling=0)
        if i % 60 == 0:
            print("image", i, flush=True)
