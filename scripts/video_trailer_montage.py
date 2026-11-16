"""Trailer Field Scan : composition des 1728 images (1920 x 1080, bandes noires 2,39:1, 24 i/s) dans
out/video_trailer/travail/seg_trailer/NNNN.jpg.

Assemble les plans 3D étalonnés (travail/graded/<plan>/), fabrique les plans de données (couche holographique sur la
photo IGN, détections d'El Oro, feuilles saines et malades), les titres, les flashs et le carton de fin.
Le découpage minuté est dans video_trailer_decoupage.py.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/video_trailer_montage.py [--debut N --fin M]
    ... --controle      : n'écrit qu'une image toutes les 2 s dans out/video_trailer/controle/
"""
import argparse
import json
import math
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

import video_trailer_decoupage as DEC  # noqa: E402

W, H = 1920, 804
CW, CH = 1920, 1080
BARRE = (CH - H) // 2
FPS = DEC.FPS
TRAV = RACINE / "out/video_trailer/travail"
SEG = TRAV / "seg_trailer"
VERT = (127, 208, 138)          # #7FD08A
AMBRE = (255, 160, 70)
ROUGE = (255, 70, 60)
BLANC = (255, 255, 255)
FONTS = "C:/Windows/Fonts/"

V = RACINE / "out/visite_basse_pointe_zone"
DONNEES = json.loads((V / "donnees.json").read_text(encoding="utf-8"))
EMP = DONNEES["emprise"]
PARC = DONNEES["parcelles"]


# ------------------------------------------------------------------------------------------------------ outils
_cache_pol = {}


def police(nom, taille):
    k = (nom, taille)
    if k not in _cache_pol:
        _cache_pol[k] = ImageFont.truetype(FONTS + nom, taille)
    return _cache_pol[k]


def fin(t):
    return police("segoeuil.ttf", t)


def reg(t):
    return police("segoeui.ttf", t)


def semi(t):
    return police("seguisb.ttf", t)


def lisse(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def prog(t, a, b):
    return lisse((t - a) / (b - a)) if b > a else float(t >= a)


def largeur_espacee(txt, f, esp):
    return sum(f.getlength(c) for c in txt) + esp * (len(txt) - 1)


def texte_espace(im, txt, cx, cy, f, esp=8, couleur=BLANC, a=1.0, ombre=0.0, ancre="m"):
    """Texte en lettres espacées, blanc, centré (ancre « m ») ou aligné à gauche (« l ») ; ombre douce pour la lisibilité.
    im : PIL RGB, modifié sur place."""
    if a <= 0.004:
        return im
    L = int(largeur_espacee(txt, f, esp)) + 120
    Hh = int(f.size * 1.9)
    x0 = int(cx - L / 2) if ancre == "m" else int(cx) - 40
    y0 = int(cy - Hh / 2)
    box = (max(x0, 0), max(y0, 0), min(x0 + L, W), min(y0 + Hh, H))
    if box[2] <= box[0] or box[3] <= box[1]:
        return im
    cal = Image.new("L", (L, Hh), 0)
    d = ImageDraw.Draw(cal)
    x = 60 if ancre == "m" else 40
    if ancre == "m":
        x = (L - largeur_espacee(txt, f, esp)) / 2
    for c in txt:
        d.text((x, Hh / 2), c, font=f, fill=255, anchor="lm")
        x += f.getlength(c) + esp
    arr = np.asarray(im).astype(np.float32)
    sub = (slice(box[1], box[3]), slice(box[0], box[2]))
    m = np.asarray(cal).astype(np.float32) / 255.0
    m = m[box[1] - y0:box[3] - y0, box[0] - x0:box[2] - x0]
    if ombre > 0:
        sh = cv2.GaussianBlur(np.asarray(cal).astype(np.float32) / 255.0, (0, 0), 9)[box[1] - y0:box[3] - y0, box[0] - x0:box[2] - x0]
        arr[sub] *= (1 - np.clip(sh * ombre * 1.4, 0, 0.85) * a)[..., None]
    arr[sub] = arr[sub] * (1 - m[..., None] * a) + np.array(couleur, np.float32) * m[..., None] * a
    im.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)))
    return im


def charge_graded(plan, t_plan):
    d = TRAV / "graded" / plan
    n = len(list(d.glob("*.png"))) if d.exists() else 0
    if n == 0:
        return np.zeros((H, W, 3), np.uint8)
    i = min(max(int(round(t_plan * FPS)) + 1, 1), n)
    im = cv2.imread(str(d / f"{i:04d}.png"))
    return im[..., ::-1].copy()


def glow(arr, rayon=10, force=1.0):
    return arr + cv2.GaussianBlur(arr, (0, 0), rayon) * force


def vignette(arr, force=0.35):
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rr = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))
    return arr * (1 - force * np.clip(rr - 0.5, 0, 1) ** 1.6)[..., None]


def etiquette_lieu(im, txt, a=1.0):
    return texte_espace(im, txt, 64, 52, reg(22), 5, BLANC, a * 0.9, 0.6, ancre="l")


def degrade_bas(arr, hauteur=300, force=0.75):
    g = (force * np.linspace(0, 1, hauteur) ** 1.4)[:, None, None]
    arr[-hauteur:] *= (1 - g)
    return arr


# ------------------------------------------------------------------------------------------------------ plan parcelles
SOL = cv2.imread(str(RACINE / "out/video_demo/travail/sol_naturel.jpg"))[..., ::-1].copy()


def pix_sol(x, y):
    return (x - EMP["xmin"]) / 0.2, (EMP["ymax"] - y) / 0.2


def vue_parcelles(t):
    """Photo IGN vue du ciel : lent travelling descendant, zoom, légère rotation ; renvoie (image, fonction de projection)."""
    u = prog(t, 0, 8.0)
    cw = 4300 - 1300 * u
    cx, cy = 2240, 1500 + 1600 * u
    th = math.radians(-4 + 7 * u)
    s = W / cw
    tx = W / 2 - s * (math.cos(th) * cx + math.sin(th) * cy)
    ty = H / 2 - s * (-math.sin(th) * cx + math.cos(th) * cy)
    M = np.array([[s * math.cos(th), s * math.sin(th), tx], [-s * math.sin(th), s * math.cos(th), ty]], np.float32)
    im = cv2.warpAffine(SOL, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    def proj(x, y):
        return M[0, 0] * x + M[0, 1] * y + M[0, 2], M[1, 0] * x + M[1, 1] * y + M[1, 2]
    return im, proj


def plan_parcelles(t):
    im, proj = vue_parcelles(t)
    base = im.astype(np.float32)
    # grade « données » : image plus sombre et froide pour que la couche verte ressorte
    base = base * np.array([0.62, 0.72, 0.70], np.float32)
    base = vignette(base, 0.5)
    # barre de balayage
    xb = -80 + (W + 160) * prog(t, 1.2, 5.6)
    cal = np.zeros((H, W, 3), np.float32)
    lum = np.zeros((H, W), np.float32)
    nb = 0
    parc_proj = []
    for p in PARC:
        anneaux = p["bord"]
        polys = []
        for poly in anneaux:
            ring = poly[0]
            pts = np.array([proj(*pix_sol(ring[i], ring[i + 1])) for i in range(0, len(ring), 2)], np.float32)
            polys.append(pts)
        ax, ay = proj(*pix_sol(*p["ancre"]))
        parc_proj.append((p, polys, ax, ay))
    # moment d'allumage = passage de la barre sur l'ancre de la parcelle (position à t = 3 s pour fixer l'ordre)
    im3, proj3 = vue_parcelles(3.0)
    t_on = {}
    for p, polys, ax, ay in parc_proj:
        x3 = proj3(*pix_sol(*p["ancre"]))[0]
        u3 = (x3 + 80) / (W + 160)
        t_on[p["id"]] = 1.2 + 4.4 * min(max(u3, 0), 1) * 1.0
    # on inverse la loi lisse de la barre (approx. linéaire par morceaux)
    labels = []
    for p, polys, ax, ay in parc_proj:
        to = t_on[p["id"]]
        a = prog(t, to, to + 0.45)
        if a <= 0:
            continue
        nb += 1
        for pts in polys:
            pi = pts.astype(np.int32).reshape(-1, 1, 2)
            cv2.fillPoly(cal, [pi], tuple(c / 255.0 * 0.22 * a for c in VERT))
            cv2.polylines(cal, [pi], True, tuple(c / 255.0 * a for c in VERT), 4, cv2.LINE_AA)
        labels.append((p, ax, ay, a, to))
    # lueur des contours
    cal = cal + cv2.GaussianBlur(cal, (0, 0), 9) * 1.3
    base = base + cal * 255
    # ligne de balayage
    xs = np.arange(W, dtype=np.float32)
    prof = np.exp(-((xs - xb) / 5.0) ** 2) * 1.0 + np.exp(-((xs - xb) / 60.0) ** 2) * 0.22
    actif = 0.0 if (t < 1.1 or t > 5.9) else 1.0
    base += (prof[None, :, None] * np.array([0.5, 1.0, 0.65], np.float32) * 255 * actif)
    # légère trame
    base[::4] *= 0.95
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im, "RGBA")
    for p, ax, ay, a, to in labels:
        pop = 0.6 + 0.4 * prog(t, to + 0.1, to + 0.5)
        f1, f2 = semi(int(30 * pop)), reg(int(22 * pop))
        s1 = p["id"]
        s2 = f"{p['surface_ha']:.2f} ha".replace(".", ",")
        w = max(f1.getlength(s1), f2.getlength(s2)) + 26
        x0, y0 = ax - w / 2, ay - 38
        d.rounded_rectangle((x0, y0, x0 + w, y0 + 76), 10, fill=(6, 18, 12, int(190 * a)), outline=VERT + (int(255 * a),), width=2)
        d.text((ax, y0 + 22), s1, font=f1, fill=BLANC + (int(255 * a),), anchor="mm")
        d.text((ax, y0 + 54), s2, font=f2, fill=VERT + (int(255 * a),), anchor="mm")
    # compteur
    a_c = prog(t, 1.0, 1.6) * (1 - prog(t, 7.5, 8.0))
    texte_espace(im, f"{nb:02d}  PARCELLES", 1500, 740, semi(34), 8, VERT, a_c, 0.5, ancre="l")
    if nb >= 13:
        texte_espace(im, "43 HECTARES", 1500, 700, reg(26), 6, BLANC, prog(t, 5.8, 6.4), 0.5, ancre="l")
    arr = np.asarray(im).astype(np.float32)
    arr = degrade_bas(arr, 330, 0.7)
    im = Image.fromarray(arr.astype(np.uint8))
    a_t = prog(t, 0.5, 1.6) * (1 - prog(t, 7.3, 8.0))
    texte_espace(im, "Voir chaque parcelle.", W / 2, 640, fin(88), 9, BLANC, a_t, 0.9)
    etiquette_lieu(im, "MARTINIQUE · PHOTO AÉRIENNE IGN", a_t)
    return np.asarray(im)


# ------------------------------------------------------------------------------------------------------ plan comptage
_src = Image.open(RACINE / "out/demo_eloro/controle_pieds/extrait_P15.png").convert("RGB")
_g_img = _src.crop((14, 22, 694, 700))
_d_img = _src.crop((708, 22, 1388, 700))
# coin sans données (noir) de l'image source : fondu dans l'arrière-plan sombre au lieu d'un triangle noir net
_ga = np.array(_g_img)
_mq = cv2.dilate((_ga.max(2) < 12).astype(np.uint8), np.ones((15, 15), np.uint8)).astype(np.float32)
MASQUE_COIN = np.clip(cv2.GaussianBlur(_mq, (0, 0), 22) * 1.6, 0, 1)
_a_d = np.array(_d_img)
_rouge = cv2.dilate(((_a_d[..., 0] > 170) & (_a_d[..., 1] < 90) & (_a_d[..., 2] < 90)).astype(np.uint8), np.ones((5, 5), np.uint8))
_nb, _lab = cv2.connectedComponents(_rouge)
CENT = []
for _k in range(1, _nb):
    _ys, _xs = np.nonzero(_lab == _k)
    if len(_xs) > 12:
        CENT.append((_xs.mean(), _ys.mean()))
CENT.sort(key=lambda c: c[0] * 0.8 + c[1] * 0.6 + np.sin(c[1] * 0.37 + c[0] * 0.11) * 25)
NCERC = len(CENT)


def plan_comptage(t):
    # fond : l'image floutée et assombrie, plein cadre
    r = W / _g_img.size[0]
    fond = np.asarray(_g_img.resize((W, int(_g_img.size[1] * r)), Image.BICUBIC))
    y0 = (fond.shape[0] - H) // 2
    fond = cv2.GaussianBlur(fond[y0:y0 + H], (0, 0), 22).astype(np.float32) * 0.28
    # carré net : zoom lent
    z = 1.0 + 0.10 * prog(t, 0, 8.0)
    taille = int(H * 1.0 * z)
    sq = np.asarray(_g_img.resize((taille, taille), Image.LANCZOS)).astype(np.float32)
    ox = int(1180 - taille / 2 + 10 * t)
    oy = int(H / 2 - taille / 2)
    a_in = prog(t, 0.0, 0.7)
    canvas = fond.copy()
    xs0, ys0 = max(ox, 0), max(oy, 0)
    xs1, ys1 = min(ox + taille, W), min(oy + taille, H)
    mk = cv2.resize(MASQUE_COIN, (taille, taille))[..., None]
    sq = sq * (1 - mk) + fond[oy:oy + taille, ox:ox + taille] * mk if (oy >= 0 and ox >= 0 and oy + taille <= H and ox + taille <= W) else sq * (1 - mk)
    canvas[ys0:ys1, xs0:xs1] = sq[ys0 - oy:ys1 - oy, xs0 - ox:xs1 - ox] * (0.88 + 0.12 * a_in)
    # détections
    cal = np.zeros((H, W, 3), np.float32)
    k = taille / 680.0
    nrev = 0
    for i, (cx, cy) in enumerate(CENT):
        tk = 1.0 + 5.4 * i / NCERC
        a = prog(t, tk, tk + 0.18)
        if a <= 0:
            continue
        nrev += 1
        x, y = ox + cx * k, oy + cy * k
        r0 = 13 * k * (0.5 + 0.5 * a)
        cv2.circle(cal, (int(x), int(y)), int(r0), tuple(c / 255.0 for c in ROUGE), 3, cv2.LINE_AA)
        ond = prog(t, tk, tk + 0.55)
        if 0 < ond < 1:                                           # onde qui s'étend à l'apparition
            cv2.circle(cal, (int(x), int(y)), int(r0 + 30 * ond), tuple(c / 255.0 * (1 - ond) for c in ROUGE), 2, cv2.LINE_AA)
    cal = cal + cv2.GaussianBlur(cal, (0, 0), 6) * 1.2
    canvas = canvas + cal * 255
    canvas = vignette(canvas, 0.45)
    im = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))
    a_t = prog(t, 0.4, 1.4) * (1 - prog(t, 7.3, 8.0))
    texte_espace(im, "Compter", 100, 200, fin(96), 8, BLANC, a_t, 0.9, ancre="l")
    texte_espace(im, "les bananiers.", 100, 300, fin(96), 8, BLANC, prog(t, 0.6, 1.6) * (1 - prog(t, 7.3, 8.0)), 0.9, ancre="l")
    ac = prog(t, 0.9, 1.8) * (1 - prog(t, 7.3, 8.0))
    # compteur lumineux
    cal2 = Image.new("L", (800, 260), 0)
    ImageDraw.Draw(cal2).text((0, 0), str(nrev), font=police("segoeuisl.ttf", 230), fill=255)
    m = np.asarray(cal2).astype(np.float32) / 255.0
    arr = np.asarray(im).astype(np.float32)
    ys, xs = 400, 96
    sub = arr[ys:ys + 260, xs:xs + 800]
    gl = cv2.GaussianBlur(m, (0, 0), 14)
    sub[:] = sub + (gl[..., None] * np.array(VERT, np.float32) * 0.9 * ac)
    sub[:] = sub * (1 - m[..., None] * ac) + np.array(VERT, np.float32) * m[..., None] * ac
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    texte_espace(im, "BANANIERS REPÉRÉS SUR CE CARRÉ DE 40 M", 100, 690, reg(23), 5, BLANC, ac, 0.9, ancre="l")
    etiquette_lieu(im, "ÉQUATEUR · IMAGE DE DRONE", ac)
    return np.asarray(im)


# ------------------------------------------------------------------------------------------------------ plan maladie
_FEUILLES = {}


def feuille(nom, cote_x=0.5):
    if nom not in _FEUILLES:
        im = cv2.imread(str(RACINE / "out/demo_finale/photos_banspot" / nom))[..., ::-1]
        s = (W * 1.16) / im.shape[1]
        _FEUILLES[nom] = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return _FEUILLES[nom]


def vue_feuille(nom, t, dur, flou0=34.0, y_deb=0.15, y_fin=0.55):
    im = feuille(nom)
    h, w = im.shape[:2]
    z = 1.0 + 0.07 * (t / dur)
    cw, chh = int(W / z), int(H / z)
    cy0 = int((h - chh) * (y_deb + (y_fin - y_deb) * (t / dur)))
    cx0 = int((w - cw) * 0.5)
    crop = im[cy0:cy0 + chh, cx0:cx0 + cw]
    crop = cv2.resize(crop, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    sigma = flou0 * (1 - prog(t, 0.15, 1.5)) ** 1.5
    if sigma > 0.5:
        crop = cv2.GaussianBlur(crop, (0, 0), sigma)
    return crop


def cadre_vise(arr, couleur, a, marge=120):
    cal = np.zeros_like(arr)
    x0, y0, x1, y1 = marge + 120, marge - 20, W - marge - 120, H - marge + 20
    L = 70
    c = tuple(float(v) for v in couleur)
    for (x, y, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        cv2.line(cal, (x, y), (x + dx * L, y), c, 4, cv2.LINE_AA)
        cv2.line(cal, (x, y), (x, y + dy * L), c, 4, cv2.LINE_AA)
    cal = cal + cv2.GaussianBlur(cal, (0, 0), 7)
    return arr + cal * a


def puce(im, txt, couleur, a, x, y, coche=True):
    f = semi(40)
    w = int(largeur_espacee(txt, f, 5)) + 130
    cal = Image.new("RGBA", (w, 84), (0, 0, 0, 0))
    d = ImageDraw.Draw(cal)
    d.rounded_rectangle((0, 0, w - 1, 83), 42, fill=(8, 16, 12, 215), outline=couleur + (255,), width=3)
    if coche:
        d.line((30, 44, 42, 56, 62, 28), fill=couleur + (255,), width=6, joint="curve")
    else:
        d.ellipse((28, 30, 52, 54), fill=couleur + (255,))
        d.polygon([(40, 28), (36, 46), (44, 46)], fill=(8, 16, 12, 255))
    x_t = 82
    for c in txt:
        d.text((x_t, 42), c, font=f, fill=BLANC + (255,), anchor="lm")
        x_t += f.getlength(c) + 5
    cal.putalpha(cal.getchannel("A").point(lambda v: int(v * a)))
    b = im.convert("RGBA")
    b.alpha_composite(cal, (int(x - w / 2), int(y)))
    return b.convert("RGB")


def plan_maladie(t):
    saine = t < 3.7
    if saine:
        tt = t
        arr = vue_feuille("banspot_NOSIG_PER_RDMI_116.jpg", tt, 3.7, 34.0, 0.2, 0.5)
        col = VERT
        txt, coche = "FEUILLE SAINE", True
    else:
        tt = t - 3.7
        arr = vue_feuille("banspot_SIG_PER_RDMI_90.jpg", tt, 4.3, 38.0, 0.05, 0.4)
        col = AMBRE
        txt, coche = "FEUILLE MALADE", False
    arr = arr * 0.92
    arr = vignette(arr, 0.5)
    # ligne de balayage horizontale (analyse)
    dur = 3.7 if saine else 4.3
    yb = H * prog(tt, 1.4, 2.8)
    if 1.4 < tt < 2.9:
        ys = np.arange(H, dtype=np.float32)
        prof = np.exp(-((ys - yb) / 4.0) ** 2) + 0.25 * np.exp(-((ys - yb) / 50.0) ** 2)
        arr = arr + prof[:, None, None] * np.array(col, np.float32) * 0.9
    a_cad = prog(tt, 1.4, 2.0)
    arr = cadre_vise(arr, np.array(col, np.float32), a_cad)
    if not saine:   # impact : un battement lumineux quand l'étiquette s'allume
        pulse = max(0.0, 1 - abs(tt - 2.9) / 0.5)
        arr = arr + pulse * 0.0
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    arr2 = degrade_bas(np.asarray(im).astype(np.float32), 330, 0.78)
    im = Image.fromarray(arr2.astype(np.uint8))
    a_lab = prog(tt, 2.8, 3.2)
    im = puce(im, txt, col, a_lab, W / 2, 420, coche)
    a_t = prog(t, 0.4, 1.4) * (1 - prog(t, 7.3, 8.0))
    texte_espace(im, "Repérer la maladie.", W / 2, 640, fin(88), 9, BLANC, a_t, 0.9)
    if not saine:
        texte_espace(im, "SUR UNE SIMPLE PHOTO DE FEUILLE", W / 2, 722, reg(24), 7, BLANC, prog(t, 5.5, 6.3) * (1 - prog(t, 7.3, 8.0)), 0.9)
    etiquette_lieu(im, "PHOTO DE FEUILLE · BANSPOT", a_t)
    return np.asarray(im)


# ------------------------------------------------------------------------------------------------------ titre, fin
def reflet(arr, t_rel, force=1.0):
    """Reflet d'objectif : traînée anamorphique bleutée et quelques fantômes, balayés lentement."""
    cx = W * (0.20 + 0.60 * lisse(t_rel / 5.5))
    cy = 395.0
    cal = np.zeros((H, W, 3), np.float32)
    xs = np.arange(W, dtype=np.float32)
    ys = np.arange(H, dtype=np.float32)
    trainee = np.exp(-((ys - cy) / 3.0) ** 2)[:, None] * np.exp(-np.abs(xs - cx) / 420.0)[None, :]
    cal += trainee[..., None] * np.array([0.35, 0.55, 1.0], np.float32) * 0.9
    disque = np.exp(-(((xs[None, :] - cx) ** 2 + (ys[:, None] - cy) ** 2) / (2 * 38.0 ** 2)))
    cal += disque[..., None] * np.array([1.0, 0.85, 0.65], np.float32) * 0.8
    for k, (f, r, c) in enumerate(((-0.55, 40, (0.4, 0.9, 0.6)), (-1.1, 70, (0.9, 0.5, 0.3)), (0.7, 28, (0.4, 0.5, 1.0)), (1.5, 55, (1.0, 0.7, 0.3)))):
        gx = W / 2 + (cx - W / 2) * (-f)
        gy = H / 2 + (cy - H / 2) * (-f)
        g = np.exp(-(((xs[None, :] - gx) ** 2 + (ys[:, None] - gy) ** 2) / (2 * r ** 2)))
        ring = np.exp(-((np.hypot(xs[None, :] - gx, ys[:, None] - gy) - r * 1.4) / 6.0) ** 2)
        cal += (g * 0.10 + ring * 0.12)[..., None] * np.array(c, np.float32)
    return arr + cal * 255 * force


def plan_titre(t):
    """t = secondes depuis l'impact du titre (58,6 s)."""
    base = charge_graded("final", t).astype(np.float32)
    base = degrade_bas(base, 400, 0.55)
    # flash à l'impact
    fl = max(0.0, 1 - t / 0.35) ** 2
    base = base + fl * 190
    # reflet : s'allume à l'impact, s'atténue
    base = reflet(base, t, force=0.55 * min(1, t / 0.4) * (0.4 + 0.6 * np.exp(-t / 3.0)))
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    a = prog(t, 0.4, 2.8)
    esp = 46 - 18 * prog(t, 0.4, 5.0)
    texte_espace(im, "FIELD SCAN", W / 2, 360, fin(172), esp, BLANC, a, 1.0)
    a2 = prog(t, DEC.SLOGAN - DEC.TITRE_IMPACT, DEC.SLOGAN - DEC.TITRE_IMPACT + 1.4) * (1 - prog(t, 6.6, 7.0))
    texte_espace(im, "Voir sa plantation comme jamais.", W / 2, 520, fin(48), 9, BLANC, a2, 1.0)
    return np.asarray(im)


def plan_fin(t):
    """t = secondes depuis 65,6 s."""
    im = Image.fromarray(np.zeros((H, W, 3), np.uint8))
    a1 = prog(t, 0.6, 1.8)
    texte_espace(im, "PROJET INTELLIGENCE LAB · ING4", W / 2, 250, fin(58), 12, BLANC, a1)
    a2 = prog(t, 1.8, 2.8)
    texte_espace(im, "3 sites, 3 jeux de données publics", W / 2, 400, fin(42), 5, BLANC, a2)
    a3 = prog(t, 3.0, 4.0)
    texte_espace(im, "Images 3D de synthèse · données réelles :", W / 2, 560, reg(27), 2, BLANC, a3)
    texte_espace(im, "IGN BD ORTHO® et RPG (Etalab 2.0), UTMACH / OpenAerialMap, BanSpot", W / 2, 606, reg(27), 2, BLANC, a3)
    arr = np.asarray(im).astype(np.float32)
    arr *= (1 - prog(t, 5.8, 6.4))
    return arr.astype(np.uint8)


def plan_texte_noir(t, lignes, tailles, y0, esp, a):
    im = Image.fromarray(np.zeros((H, W, 3), np.uint8))
    for k, (s, tz) in enumerate(zip(lignes, tailles)):
        texte_espace(im, s, W / 2, y0 + k * 120, fin(tz), esp, BLANC, a)
    return np.asarray(im)


# ------------------------------------------------------------------------------------------------------ chronologie
def image_cadre(t):
    T = DEC.T
    f = np.zeros((H, W, 3), np.uint8)
    if t < T["aube"][0]:
        a = prog(t, 0.5, 1.6) * (1 - prog(t, 2.6, 3.2))
        im = Image.fromarray(f)
        texte_espace(im, "Chaque matin,", W / 2, 330, fin(84), 11, BLANC, a)
        texte_espace(im, "des milliers de bananiers.", W / 2, 440, fin(84), 11, BLANC, prog(t, 0.9, 2.0) * (1 - prog(t, 2.6, 3.2)))
        return np.asarray(im)
    if t < T["texte3"][0]:                                           # aube
        tt = t - T["aube"][0]
        arr = charge_graded("aube", tt).astype(np.float32)
        arr *= min(1.0, tt / 0.5)
        arr = degrade_bas(arr, 360, 0.6)
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        a = prog(t, T["texte2"][0], T["texte2"][0] + 1.1) * (1 - prog(t, 7.7, 8.4))
        texte_espace(im, "Impossible de tous les voir.", W / 2, 640, fin(80), 9, BLANC, a, 1.0)
        arr = np.asarray(im).astype(np.float32) * (1 - prog(t, 8.3, 8.7))
        return arr.astype(np.uint8)
    if t < T["montee"][0]:                                           # « Jusqu'à aujourd'hui. »
        tt = t - T["texte3"][0]
        a = prog(tt, 0.3, 1.2) * (1 - prog(tt, 2.1, 2.5))
        im = Image.fromarray(f)
        texte_espace(im, "Jusqu'à aujourd'hui.", W / 2, H / 2, fin(100), 12, BLANC, a)
        return np.asarray(im)
    if t < T["parcelles"][0]:                                        # montée : coupes de plus en plus courtes
        for (d0, plan, p0, dur) in DEC.MONTEE:
            if d0 <= t < d0 + dur or (plan == DEC.MONTEE[-1][1] and t >= d0):
                tt = t - d0
                arr = charge_graded(plan, p0 + tt).astype(np.float32)
                z = 1.0 + 0.045 * math.exp(-tt * 9)                  # petit « coup de zoom » à chaque coupe
                if z > 1.001:
                    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
                    arr = cv2.warpAffine(arr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
                if d0 == T["montee"][0]:
                    arr = arr * min(1.0, tt / 0.12)
                return arr.astype(np.uint8)
    if t < T["comptage"][0]:
        return plan_parcelles(t - T["parcelles"][0])
    if t < T["maladie"][0]:
        return plan_comptage(t - T["comptage"][0])
    if t < T["grue"][0]:
        return plan_maladie(t - T["maladie"][0])
    if t < T["silence"][0]:                                          # grande révélation
        tt = t - T["grue"][0]
        arr = charge_graded("grue", tt).astype(np.float32)
        return vignette(arr, 0.1).clip(0, 255).astype(np.uint8)
    if t < T["titre"][0]:
        return f
    if t < T["fin"][0]:
        return plan_titre(t - T["titre"][0])
    return plan_fin(t - T["fin"][0])


def image_finale(i):
    t = i / FPS
    c = image_cadre(t).astype(np.float32)
    # flashs blancs (3 images) sur les coupes fortes
    for tf in DEC.COUPES_FORTES[1:]:
        d = t - tf
        if 0 <= d < 0.14:
            c = c + (1 - d / 0.14) * 170
    # fondu au noir à la toute fin
    if t > DEC.DUREE - 0.35:
        c *= max(0.0, (DEC.DUREE - t) / 0.35)
    out = np.zeros((CH, CW, 3), np.uint8)
    out[BARRE:BARRE + H] = np.clip(c, 0, 255).astype(np.uint8)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debut", type=int, default=0)
    ap.add_argument("--fin", type=int, default=0)
    ap.add_argument("--controle", action="store_true")
    ap.add_argument("--pas", type=int, default=1)
    ap.add_argument("--sortie", default=None)
    a = ap.parse_args()
    n = int(DEC.DUREE * FPS)
    SEG.mkdir(parents=True, exist_ok=True)
    print("cercles reconnus :", NCERC, flush=True)
    sortie = Path(a.sortie) if a.sortie else SEG
    sortie.mkdir(parents=True, exist_ok=True)
    fin_ = a.fin or n
    for i in range(a.debut, fin_, a.pas):
        im = image_finale(i)
        cv2.imwrite(str(sortie / f"{i + 1:04d}.jpg"), im[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 95])
        if i % 100 == 0:
            print("image", i, flush=True)


if __name__ == "__main__":
    main()
