"""Vidéo « pitch » de 60 s : compose toutes les images (1920 x 1080, 30 i/s) dans out/video_demo/travail/seg_pitch/.

Plans réels uniquement : photo IGN de Basse-Pointe et contours des 13 parcelles, comptage d'El Oro, photos de feuilles
de BanSpot, vol 3D Blender (images de scripts/video_demo_vol3d.py), puis cartons de titre. L'encodage MP4 est fait par
scripts/video_demo_montage.py (Blender, montage vidéo). Les chiffres viennent de out/demo_finale/chiffres.json
(1 026 pieds ; 4 malades sans alerte sur 646 feuilles tachées, donc 642 repérés) et de la visite (13 parcelles, 43 ha).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/video_demo_pitch.py [--debut N --fin M]
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import video_demo_plans2d as P  # noqa: E402
from video_demo_plans2d import (BLANC, FOND, FPS, GRIS, H, ORANGE, VERT, VIOLET, W, T, calque, coche, coins_ronds, gras,  # noqa: E402
                                norm, poser, prog, semi, texte)

OUT = T / "seg_pitch"
V = RACINE / "out/visite_basse_pointe_zone"
D = json.loads((V / "donnees.json").read_text(encoding="utf-8"))
SOL = Image.open(T / "sol_naturel.jpg").convert("RGB")
EMP = D["emprise"]
GRAD = None


def bande_bas(im, h=330, force=185):
    global GRAD
    if GRAD is None:
        a = np.zeros((H, W, 4), np.uint8)
        for y in range(H - h, H):
            a[y, :, 3] = int(force * ((y - (H - h)) / h) ** 1.4)
        GRAD = Image.fromarray(a, "RGBA")
    return Image.alpha_composite(im.convert("RGBA"), GRAD).convert("RGB")


def phrase(im, s, t, a0, a1, y=900, taille=78, couleur=BLANC, sortie=None):
    a = prog(t, a0, a0 + 0.6)
    if sortie:
        a *= 1 - prog(t, sortie, sortie + 0.4)

    def d(g):
        texte(g, (W // 2, y), s, gras(taille), couleur, "mm")
    return poser(im, d, a, int(24 * (1 - prog(t, a0, a0 + 0.6))))


def vue_sol(cx, cy, cw, taille=(W, H)):
    ch = cw * 9 / 16
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return SOL.resize(taille, Image.BICUBIC, box=box), box


def pix(x, y):
    return (x - EMP["xmin"]) / 0.2, (EMP["ymax"] - y) / 0.2


# ------------------------------------------------------------------------------------------------ plans
def s1(t):  # photo aérienne réelle, zoom lent
    z = 1.0 + 0.10 * t / 5
    im, _ = vue_sol(2240 + 40 * t, 2200, 3300 / z)
    im = bande_bas(im)
    im = phrase(im, "43 hectares.", t, 0.5, 5, y=880, taille=110)

    def d(g):
        texte(g, (60, 60), "Basse-Pointe, Martinique", semi(34), BLANC)
    return poser(im, d, prog(t, 1.2, 2.0))


def s2(t):
    im, _ = vue_sol(1500 + 70 * t, 3000, 2600 - 40 * t)
    im = Image.blend(im, Image.new("RGB", (W, H), FOND), 0.55)
    return phrase(im, "Impossible de tout surveiller à pied.", t, 0.3, 4, y=540, taille=88)


PARC = sorted(D["parcelles"], key=lambda p: -p["ancre"][1])


def s3(t):
    u = prog(t, 0, 8.3)
    cw = 4400 - 1100 * u
    im, box = vue_sol(2240, 1400 + 1700 * u, cw)
    sc = W / (box[2] - box[0])
    c = calque()
    g = ImageDraw.Draw(c, "RGBA")
    nvis = 0
    for k, p in enumerate(PARC):
        a = prog(t, 0.8 + k * 0.45, 1.4 + k * 0.45)
        if a <= 0:
            continue
        nvis += a > 0.9
        cult = p["culture"].startswith("Banane")
        col = (90, 230, 120) if cult else (235, 215, 70)
        for poly in p["bord"]:
            ring = poly[0]
            pts = [((px - box[0]) * sc, (py - box[1]) * sc) for px, py in (pix(ring[i], ring[i + 1]) for i in range(0, len(ring), 2))]
            g.polygon(pts, fill=col + (int(60 * a),), outline=col + (int(255 * a),), width=5)
        ax, ay = pix(*p["ancre"])
        sx, sy = (ax - box[0]) * sc, (ay - box[1]) * sc
        if 0 < sx < W and 0 < sy < H - 320 and a > 0.5:
            texte(g, (sx, sy), p["id"], gras(40), (255, 255, 255, int(255 * a)), "mm")
    im = Image.alpha_composite(im.convert("RGBA"), c).convert("RGB")
    im = bande_bas(im, 300, 170)
    im = phrase(im, "Field Scan découpe l'exploitation…", t, 0.4, 8, y=930, taille=70)

    def d(g):
        puce_txt = f"{min(13, int(round(prog(t, 1.0, 6.8) * 13)))} parcelles"
        g.rounded_rectangle((W - 420, 40, W - 40, 130), 24, fill=(10, 22, 14, 215))
        texte(g, (W - 230, 85), puce_txt, gras(48), VERT, "mm", False)
    return poser(im, d, prog(t, 1.0, 1.6))


# --- comptage
_src = Image.open(RACINE / "out/demo_eloro/controle_pieds/extrait_P15.png").convert("RGB")
_g_img, _d_img = _src.crop((14, 22, 694, 700)), _src.crop((708, 22, 1388, 700))
_a_g, _a_d = np.array(_g_img), np.array(_d_img)
_rouge = cv2.dilate(((_a_d[..., 0] > 170) & (_a_d[..., 1] < 90) & (_a_d[..., 2] < 90)).astype(np.uint8), np.ones((5, 5), np.uint8))
_nb, _lab = cv2.connectedComponents(_rouge)
_cent = []
for _k in range(1, _nb):
    _ys, _xs = np.nonzero(_lab == _k)
    if len(_xs) > 12:
        _cent.append((_k, _xs.mean(), _ys.mean()))
_cent.sort(key=lambda c: c[1] * 0.8 + c[2] * 0.6 + np.sin(c[2] * 0.37 + c[1] * 0.11) * 25)
_rang = np.zeros(_nb, np.int32) + 10**6
_rang[[c[0] for c in _cent]] = np.arange(len(_cent))
_carte = _rang[_lab]
_jaune = ((_a_d[..., 0] > 200) & (_a_d[..., 1] > 200) & (_a_d[..., 2] < 90))[..., None]


def s4(t):
    im = Image.new("RGB", (W, H), FOND)
    pr = prog(t, 0.8, 6.0)
    k = int(round(pr * len(_cent)))
    mix = np.where((_carte < k)[..., None], _a_d, _a_g)
    mix = np.where(_jaune, _a_d, mix)
    big = Image.fromarray(mix.astype(np.uint8)).resize((900, 900), Image.LANCZOS)
    a = prog(t, 0, 0.6)
    c = calque()
    c.paste(coins_ronds(big, 26), (110, 90))
    c.putalpha(c.getchannel("A").point(lambda v: int(v * a)))
    im = Image.alpha_composite(im.convert("RGBA"), c).convert("RGB")

    def d(g):
        texte(g, (1040, 330), "…compte chaque", gras(78), BLANC, "lm")
        texte(g, (1040, 420), "bananier…", gras(78), BLANC, "lm")
        texte(g, (1040, 620), f"{int(round(prog(t, 0.8, 6.2) * 1026)):,}".replace(",", " "), gras(150), VERT, "lm")
        texte(g, (1040, 740), "bananiers comptés", norm(48), GRIS, "lm")
        texte(g, (1040, 800), "par drone, sur 3 parcelles", norm(36), GRIS, "lm")
        texte(g, (1040, 1000), "El Oro, Équateur · un cercle rouge par pied", norm(30), (170, 185, 170), "lm", False)
    return poser(im, d, prog(t, 0.3, 1.0))


_ch = json.loads((RACINE / "out/demo_finale/chiffres.json").read_text(encoding="utf-8"))["maladies_photos"]
_sains = [m for m in _ch if m["classe_vraie"] == "sans_taches"]
_mal = [m for m in _ch if m["classe_vraie"] == "taches"]
_ordre = [_sains[0], _mal[0], _sains[1], _mal[1]]
_thumbs = [coins_ronds(Image.open(RACINE / "out/demo_finale" / m["vignette"]).convert("RGB").resize((410, 308), Image.LANCZOS), 20)
           for m in _ordre]


def s5(t):
    im = Image.new("RGB", (W, H), FOND)

    def d0(g):
        texte(g, (W // 2, 105), "…et repère la maladie sur une simple photo.", gras(62), BLANC, "mm")
    im = poser(im, d0, prog(t, 0, 0.6))
    for k, m in enumerate(_ordre):
        x, y = 80 + k * 450, 210
        a = prog(t, 0.5 + k * 0.7, 1.1 + k * 0.7)
        ar = prog(t, 1.1 + k * 0.7, 1.6 + k * 0.7)
        c = calque()
        c.paste(_thumbs[k], (x, y))
        c.putalpha(c.getchannel("A").point(lambda v, a=a: int(v * a)))
        im = Image.alpha_composite(im.convert("RGBA"), c).convert("RGB")
        saine = m["reponse"] == "saine"
        col = VERT if saine else ORANGE

        def dr(g, x=x, y=y, saine=saine, col=col):
            g.rounded_rectangle((x, y + 322, x + 410, y + 384), 18, fill=(22, 40, 28, 255), outline=col + (255,), width=3)
            coche(g, x + 34, y + 353, 22)
            texte(g, (x + 72, y + 353), "feuille saine" if saine else "feuille malade", semi(34), col, "lm", False)
        im = poser(im, dr, ar)

    def d1(g):
        texte(g, (W // 2, 760), "642 malades sur 646 repérés", gras(88), VERT, "mm")
        texte(g, (W // 2, 850), "sur des photos que le programme n'avait jamais vues", norm(36), GRIS, "mm")
        texte(g, (W // 2, 905), "BanSpot · 4 malades ratés, 56 fausses alertes", norm(30), (170, 185, 170), "mm", False)
    return poser(im, d1, prog(t, 4.2, 5.2), int(20 * (1 - prog(t, 4.2, 5.2))))


# --- vol 3D
SER = {k: {int(f.stem): f for f in (T / f"vol_{k}").glob("*.jpg")} for k in "ABC"}
_cache = {}


def img15(k, j):
    j = max(min(SER[k]) - 1, min(max(SER[k]) - 1, j))
    key = (k, j)
    if key not in _cache:
        if len(_cache) > 12:
            _cache.pop(next(iter(_cache)))
        _cache[key] = cv2.imread(str(SER[k][j + 1]))
    return _cache[key]


def img30(k, t):
    """Image du vol k à l'instant t (s), 30 i/s par flux optique."""
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


def etiq(im, a):
    return poser(im, P.etiquette_illustration, a)


def s6a(t):
    im = img30("A", t)
    im = bande_bas(im, 300, 175)
    im = phrase(im, "Puis le planteur se promène dans sa plantation.", t, 0.3, 4.5, y=930, taille=62, sortie=4.1)
    return etiq(im, prog(t, 0.2, 0.8))


def img_b30(t):
    """Plan B rendu directement à 30 i/s (alley : le flux optique y laissait des images fantômes)."""
    n = int(round(t * 30)) + 1
    return Image.open(T / "vol_B30" / f"{n:04d}.jpg").convert("RGB")


def s6b(t):
    im = img_b30(4.0 + t)
    im = bande_bas(im, 240, 150)
    im = phrase(im, "Entre les rangs de bananiers", t, 1.8, 7, y=960, taille=60, sortie=6.8)
    return etiq(im, 1.0)


def s6c(t):
    im = img30("C", t)
    im = bande_bas(im, 300, 175)
    im = phrase(im, "Les zones à surveiller passent en orange.", t, 0.4, 5, y=930, taille=62, sortie=4.7)
    return etiq(im, 1.0)


def s7(t):
    im, _ = vue_sol(2240 - 25 * t, 2200, 3000)
    im = Image.blend(im, Image.new("RGB", (W, H), FOND), 0.68)

    def d(g):
        texte(g, (W // 2, 440), "Field Scan", gras(190), BLANC, "mm")
        g.rounded_rectangle((W // 2 - 120, 560, W // 2 + 120, 566), 3, fill=VERT + (255,))
        texte(g, (W // 2, 650), "Votre plantation, vue d'en haut.", norm(66), VERT, "mm")
    return poser(im, d, prog(t, 0.2, 1.1), int(30 * (1 - prog(t, 0.2, 1.1))))


def s8(t):
    im, _ = vue_sol(2240, 2200, 3000)
    im = Image.blend(im, Image.new("RGB", (W, H), FOND), 0.8)

    def d(g):
        texte(g, (W // 2, 420), "Field Scan", gras(110), BLANC, "mm")
        texte(g, (W // 2, 540), "Projet Intelligence Lab · ING4", semi(52), GRIS, "mm")
        texte(g, (W // 2, 930), "Sources : IGN BD ORTHO® et RPG (Licence Ouverte Etalab 2.0) · UTMACH / OpenAerialMap (CC BY 4.0)", norm(25), (170, 185, 170), "mm", False)
        texte(g, (W // 2, 970), "ReforesTree (CC BY 4.0) · BanSpot · bananiers 3D : illustration", norm(25), (170, 185, 170), "mm", False)
    return poser(im, d, prog(t, 0.0, 0.5))


# (début, durée, fonction) ; chaque plan est évalué 0,3 s au-delà de sa fin pour le fondu enchaîné
PLANS = [(0, 5, s1), (5, 4, s2), (9, 8, s3), (17, 8, s4), (25, 8, s5), (33, 4.5, s6a), (37.5, 9.5, s6b), (47, 5, s6c),
         (52, 6, s7), (58, 2, s8)]
FONDU = 0.3


def image(i):
    t = i / FPS
    cur = max(k for k, (d, _, _) in enumerate(PLANS) if d <= t + 1e-9)
    d, dur, f = PLANS[cur]
    im = f(t - d)
    if cur > 0 and t - d < FONDU:
        d0, dur0, f0 = PLANS[cur - 1]
        im = Image.blend(f0(t - d0), im, (t - d) / FONDU)
    if t > 59.6:
        im = Image.blend(im, Image.new("RGB", (W, H), (0, 0, 0)), (t - 59.6) / 0.4)
    return im


if __name__ == "__main__":
    a = sys.argv[1:]
    deb = int(a[a.index("--debut") + 1]) if "--debut" in a else 0
    fin = int(a[a.index("--fin") + 1]) if "--fin" in a else 60 * FPS - 1
    pas = int(a[a.index("--pas") + 1]) if "--pas" in a else 1
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(deb, fin + 1, pas):
        image(i).save(OUT / f"{i + 1:04d}.jpg", quality=93, subsampling=0)
        if i % 60 == 0:
            print("image", i, flush=True)
