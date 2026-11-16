"""Trailer Field Scan : plans ajoutés après les retours (ouverture réel -> 3D, réseau de neurones, visite 3D web).
Fonctions utilisées par video_trailer_montage.py (qui fournit les outils communs : police, texte_espace, charge_graded...).
"""
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw

VERT = (127, 208, 138)
BLANC = (255, 255, 255)
AMBRE = (255, 160, 70)
ROUGE = (255, 70, 60)


# ------------------------------------------------------------------------------------------------ ouverture réelle
def plan_reel(M, t):
    """Photo aérienne IGN réelle, vue zénithale qui descend, contours RPG qui se dessinent, texte « Impossible… » ;
    t = secondes depuis 3,0 s (0 à 4,4)."""
    W, H = M.W, M.H
    u = M.prog(t, 0, 5.0)
    cw = 2400 - 700 * u
    cx, cy = 2300 + 40 * u, 2500 - 160 * u
    th = math.radians(-6 + 5 * u)
    s = W / cw
    tx = W / 2 - s * (math.cos(th) * cx + math.sin(th) * cy)
    ty = H / 2 - s * (-math.sin(th) * cx + math.cos(th) * cy)
    A = np.array([[s * math.cos(th), s * math.sin(th), tx], [-s * math.sin(th), s * math.cos(th), ty]], np.float32)
    im = cv2.warpAffine(M.SOL, A, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    a_in = M.prog(t, 0.0, 0.5)
    im = im * (0.92 * a_in) * np.array([1.0, 1.02, 0.98], np.float32)
    im = M.vignette(im, 0.45)
    # contours des parcelles RPG qui se dessinent le long de leur périmètre
    cal = np.zeros((H, W, 3), np.float32)
    for k, p in enumerate(M.PARC):
        f = M.prog(t, 0.9 + 0.12 * k, 2.2 + 0.12 * k)
        if f <= 0:
            continue
        for poly in p["bord"]:
            ring = poly[0]
            pts = np.array([(A[0, 0] * px + A[0, 1] * py + A[0, 2], A[1, 0] * px + A[1, 1] * py + A[1, 2])
                            for px, py in (M.pix_sol(ring[i], ring[i + 1]) for i in range(0, len(ring), 2))], np.float32)
            seg = np.hypot(*np.diff(np.vstack([pts, pts[:1]]), axis=0).T)
            cum = np.concatenate([[0], np.cumsum(seg)])
            lim = f * cum[-1]
            for i in range(len(pts)):
                if cum[i] >= lim:
                    break
                a_ = pts[i]
                b_ = pts[(i + 1) % len(pts)]
                fr = min(1.0, (lim - cum[i]) / max(seg[i], 1e-6))
                e_ = a_ + (b_ - a_) * fr
                cv2.line(cal, (int(a_[0]), int(a_[1])), (int(e_[0]), int(e_[1])), (1.0, 1.0, 1.0), 3, cv2.LINE_AA)
    cal = cal + cv2.GaussianBlur(cal, (0, 0), 6) * 0.9
    col = np.array(VERT, np.float32) / 255.0
    im = im + cal.max(2, keepdims=True) * col * 255 * 0.8 + cal * 60
    im = M.degrade_bas(im, 330, 0.7)
    out = Image.fromarray(np.clip(im, 0, 255).astype(np.uint8))
    a_t = M.prog(t, 1.4, 2.4) * (1 - M.prog(t, 4.0, 4.4))
    M.texte_espace(out, "Impossible de tous les voir.", W / 2, 640, M.fin(80), 9, BLANC, a_t, 1.0)
    a_tag = M.prog(t, 0.3, 0.9)
    M.texte_espace(out, "RÉEL · PHOTO AÉRIENNE IGN BD ORTHO® · PARCELLES RPG", 64, 52, M.reg(22), 5, BLANC, a_tag * 0.9, 0.6, ancre="l")
    return np.asarray(out)


def tag_illustration(M, im_arr, a, texte="ILLUSTRATION · BANANIERS 3D DE SYNTHÈSE"):
    out = Image.fromarray(np.clip(im_arr, 0, 255).astype(np.uint8))
    M.texte_espace(out, texte, 64, 52, M.reg(22), 5, BLANC, a * 0.9, 0.7, ancre="l")
    return np.asarray(out)


# ------------------------------------------------------------------------------------------------ réseau de neurones
class Reseau:
    def __init__(self, M):
        self.M = M
        ga = np.array(M._g_img)
        mq = cv2.dilate((ga.max(2) < 12).astype(np.uint8), np.ones((11, 11), np.uint8))
        ga = cv2.inpaint(ga, mq, 9, cv2.INPAINT_TELEA)
        tile = ga.astype(np.float32) / 255.0                                         # 678 x 680, coin sans données comblé
        self.tile = tile
        g = cv2.cvtColor((tile * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        exg = np.clip(2 * tile[..., 1] - tile[..., 0] - tile[..., 2], 0, 1)
        rect = []
        # L0 : 16 patches de la vraie tuile
        h, w = tile.shape[:2]
        L0 = []
        for j in range(4):
            for i in range(4):
                p = tile[j * h // 4:(j + 1) * h // 4, i * w // 4:(i + 1) * w // 4]
                L0.append(cv2.resize(p, (96, 96), interpolation=cv2.INTER_AREA))
        # L1 : 8 cartes de contours orientés (filtres de Gabor sur la tuile)
        L1 = []
        for k in range(8):
            ker = cv2.getGaborKernel((21, 21), 4.0, k * math.pi / 8, 9.0, 0.6, 0)
            r = np.abs(cv2.filter2D(g, -1, ker))
            L1.append(self.teinte(cv2.resize(r / (r.max() + 1e-6), (96, 96), interpolation=cv2.INTER_AREA), 0.55))
        # L2 : 12 cartes plus grossières (réponses combinées, floutées)
        L2 = []
        for k in range(12):
            ker = cv2.getGaborKernel((31, 31), 7.0, k * math.pi / 12, 16.0, 0.5, 0)
            r = np.maximum(cv2.filter2D(exg - exg.mean(), -1, ker), 0) + 0.6 * np.abs(cv2.filter2D(g, -1, ker))
            r = cv2.GaussianBlur(r, (0, 0), 6)
            L2.append(self.teinte(cv2.resize(r / (r.max() + 1e-6), (64, 64), interpolation=cv2.INTER_AREA), 0.7))
        # L3 : 16 cartes très grossières (les taches de vert)
        L3 = []
        for k in range(16):
            r = cv2.GaussianBlur(exg * (0.6 + 0.4 * np.sin(k)) + 0.3 * g * (k % 3 == 0), (0, 0), 10 + 1.5 * (k % 4))
            L3.append(self.teinte(cv2.resize(r / (r.max() + 1e-6), (40, 40), interpolation=cv2.INTER_AREA), 0.85))
        # L4 : carte de chaleur des centres, d'après les détections réelles (cercles de extrait_P15)
        heat = np.zeros((h, w), np.float32)
        for (x, y) in M.CENT:
            if 0 <= int(y) < h and 0 <= int(x) < w:
                heat[int(y), int(x)] = 1.0
        heat = cv2.GaussianBlur(heat, (0, 0), 7)
        heat = heat / (heat.max() + 1e-9)
        self.heat = np.clip(heat * 1.6, 0, 1)
        self.L4 = self.colormap(self.heat)
        self.couches = []
        z = 0.0
        rng = np.random.default_rng(3)
        specs = [(L0, 4, 4, 100, 110, 0.0, 1.0), (L1, 4, 2, 112, 122, 800.0, 1.0), (L2, 4, 3, 84, 94, 1550.0, 1.0),
                 (L3, 4, 4, 58, 68, 2250.0, 1.0)]
        for (maps, cols, rows, taille, pas, Z, a) in specs:
            r_ = []
            for k, mp in enumerate(maps):
                cxk = ((k % cols) - (cols - 1) / 2) * pas
                cyk = ((k // cols) - (rows - 1) / 2) * pas
                r_.append(dict(x=cxk, y=cyk, z=Z, w=taille, tex=(mp * 255).astype(np.uint8)))
            self.couches.append(r_)
        self.Z4 = 3000.0
        self.W4 = 300.0
        # connexions entre couches successives (sous-ensemble tiré une fois)
        self.liens = []
        for l in range(len(self.couches) - 1):
            for _ in range(26):
                a_ = rng.integers(len(self.couches[l]))
                b_ = rng.integers(len(self.couches[l + 1]))
                self.liens.append((l, int(a_), int(b_), float(rng.random())))
        for k in range(10):
            self.liens.append((len(self.couches) - 1, int(rng.integers(16)), -1, float(rng.random())))

    @staticmethod
    def teinte(a, gamma=0.6):
        a = np.clip(a, 0, 1) ** gamma
        return np.stack([a * 0.25, a * 0.95, a * 0.45], -1)

    @staticmethod
    def colormap(x):
        x = np.clip(x, 0, 1)
        r = np.clip(2 * x - 0.5, 0, 1)
        g = np.clip(1.4 * x + 0.1, 0, 1) * (x > 0.02)
        b = np.clip(x * 0.6 - 0.1, 0, 1)
        return np.stack([r * 0.9 + 0.1 * g, g, b], -1) * np.clip(x * 3, 0, 1)[..., None]

    def proj(self, X, Y, Z, cam, f=1500.0):
        d = Z - cam[2]
        if d < 60:
            return None
        return 960 + f * (X - cam[0]) / d, 402 + f * (Y - cam[1]) / d, f / d

    def blit(self, canvas, tex, cx, cy, wpx, alpha):
        h, w = tex.shape[:2]
        wpx = int(max(wpx, 1))
        if wpx < 2 or wpx > 4000:
            return
        x0, y0 = int(cx - wpx / 2), int(cy - wpx / 2)
        x1, y1 = x0 + wpx, y0 + wpx
        if x1 <= 0 or y1 <= 0 or x0 >= canvas.shape[1] or y0 >= canvas.shape[0]:
            return
        # on ne redimensionne que la partie visible
        sx0, sy0 = max(x0, 0), max(y0, 0)
        sx1, sy1 = min(x1, canvas.shape[1]), min(y1, canvas.shape[0])
        t_ = cv2.resize(tex, (wpx, wpx), interpolation=cv2.INTER_LINEAR if wpx > w else cv2.INTER_AREA) if wpx < 1500 else \
            cv2.resize(tex, (wpx, wpx), interpolation=cv2.INTER_LINEAR)
        part = t_[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0].astype(np.float32)
        reg = canvas[sy0:sy1, sx0:sx1]
        reg[:] = reg * (1 - alpha * 0.9) + part * alpha
        # cadre lumineux
        cv2.rectangle(canvas, (x0, y0), (x1, y1), tuple(c / 255 * 255 * alpha for c in VERT[::-1]) if False else (110 * alpha, 230 * alpha, 130 * alpha), max(1, int(wpx / 60)), cv2.LINE_AA)

    def image(self, t):
        M = self.M
        W, H = M.W, M.H
        canvas = np.zeros((H, W, 3), np.float32)
        canvas[:] = np.array([10, 18, 14], np.float32)
        # grille de fond
        for gx in range(0, W, 96):
            canvas[:, gx:gx + 1] += 6
        for gy in range(0, H, 96):
            canvas[gy:gy + 1, :] += 6
        a_in = M.prog(t, 0.0, 0.5)
        # entrée : la tuile arrive par la gauche
        if t < 1.5:
            u = M.prog(t, 0.0, 1.4)
            taille = 640 - 200 * u
            xc = -taille / 2 + (700 * u) + 320 * 0
            xc = -340 + (960 - 6 * 0 - (-340)) * u * 0.62
            tile = cv2.resize((self.tile * 255).astype(np.float32), (int(taille), int(taille)), interpolation=cv2.INTER_AREA)
            x0, y0 = int(xc - taille / 2), int(402 - taille / 2)
            sx0, sx1 = max(x0, 0), min(x0 + int(taille), W)
            if sx1 > sx0:
                canvas[y0:y0 + int(taille), sx0:sx1] = tile[:, sx0 - x0:sx1 - x0]
            im = canvas
        else:
            # caméra : recul puis travelling à travers les couches
            u = M.prog(t, 1.8, 5.0)
            cz = -1500 + (self.Z4 - 560 + 1500) * u
            cxx = -82 * M.prog(t, 3.8, 5.0)
            cam = (cxx, 0.0, cz)
            # patches qui se séparent (t de 1,2 à 2,2)
            ecart = 1.0 + 0.10 * M.prog(t, 1.2, 2.0)
            # liste des rectangles à dessiner (profondeur décroissante)
            items = []
            for l, couche in enumerate(self.couches):
                for k, r in enumerate(couche):
                    items.append((r["z"], r, ecart if l == 0 else 1.0))
            items.append((self.Z4, dict(x=0.0, y=0.0, z=self.Z4, w=self.W4, tex=None), 1.0))
            items.sort(key=lambda a: -a[0])
            # liens et particules sous les cartes
            lum = np.zeros((H, W, 3), np.float32)
            appar_couches = [0.0, M.prog(t, 2.0, 2.8), M.prog(t, 2.2, 3.0), M.prog(t, 2.4, 3.2)]
            for (l, a_, b_, ph) in self.liens:
                ra = self.couches[l][a_]
                if b_ < 0:
                    qb = (0.0, 0.0, self.Z4)
                else:
                    rb = self.couches[l + 1][b_]
                    qb = (rb["x"], rb["y"], rb["z"])
                pa = self.proj(ra["x"] * (ecart if l == 0 else 1.0), ra["y"] * (ecart if l == 0 else 1.0), ra["z"], cam)
                pb = self.proj(qb[0], qb[1], qb[2], cam)
                if pa is None or pb is None:
                    continue
                al = appar_couches[min(l + 1, 3)] * 0.35
                if al <= 0:
                    continue
                cv2.line(lum, (int(pa[0]), int(pa[1])), (int(pb[0]), int(pb[1])), (0.30 * al, 0.9 * al, 0.45 * al), 1, cv2.LINE_AA)
                f = (t * 0.6 + ph) % 1.0
                px, py = pa[0] + (pb[0] - pa[0]) * f, pa[1] + (pb[1] - pa[1]) * f
                r_ = max(2, int(5 * (pa[2] + (pb[2] - pa[2]) * f) / 1.0 * 1.2))
                cv2.circle(lum, (int(px), int(py)), min(r_, 9), (0.8 * al * 2.2, 1.0 * al * 2.2, 0.9 * al * 2.2), -1, cv2.LINE_AA)
            canvas = canvas + (lum + cv2.GaussianBlur(lum, (0, 0), 5) * 1.5) * 255
            for z, r, e in items:
                l = int(round(z / 750.0)) if z > 0 else 0
                lid = 0 if z == 0 else (1 if z == 800 else (2 if z == 1550 else (3 if z == 2250 else 4)))
                al = 1.0 if lid == 0 else (appar_couches[lid] if lid < 4 else M.prog(t, 3.0, 3.8))
                if al <= 0.01:
                    continue
                p = self.proj(r["x"] * e, r["y"] * e, r["z"], cam)
                if p is None:
                    continue
                tex = (self.L4 * 255) if r["tex"] is None else r["tex"].astype(np.float32)
                self.blit(canvas, tex, p[0], p[1], r["w"] * p[2], al)
            im = canvas
        # fin : la tuile réelle se pose sous la carte de chaleur dans le carré du plan suivant
        if t > 4.6:
            fin = M.prog(t, 4.6, 5.6)
            taille = H
            ox = 1180 - taille // 2 + 10 * 0
            tile = cv2.resize(self.tile, (taille, taille), interpolation=cv2.INTER_AREA) * 255
            mk = cv2.resize(M.MASQUE_COIN, (taille, taille))[..., None]
            tile = tile * (1 - mk)
            heat = cv2.resize(self.L4, (taille, taille), interpolation=cv2.INTER_LINEAR) * 255
            reg = im[:, ox:ox + taille]
            reg[:] = reg * (1 - fin) + (tile * 0.88 + heat * 0.9 * (1 - 0.35 * fin)) * fin
        out = Image.fromarray(np.clip(im, 0, 255).astype(np.uint8))
        # textes
        arr = np.asarray(out).astype(np.float32)
        arr = M.vignette(arr, 0.45)
        out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        a1 = M.prog(t, 0.3, 1.0) * (1 - M.prog(t, 2.0, 2.5))
        M.texte_espace(out, "ENTRÉE · PHOTO DE DRONE · ÉQUATEUR", 64, 52, M.reg(22), 5, BLANC, a1, 0.8, ancre="l")
        a2 = M.prog(t, 2.2, 2.9) * (1 - M.prog(t, 4.4, 4.8))
        M.texte_espace(out, "COUCHES DU RÉSEAU DE NEURONES", 64, 52, M.reg(22), 5, VERT, a2, 0.8, ancre="l")
        a3 = M.prog(t, 4.6, 5.2)
        M.texte_espace(out, "SORTIE · CARTE DES CENTRES", 64, 52, M.reg(22), 5, VERT, a3, 0.8, ancre="l")
        at = M.prog(t, 0.5, 1.4) * (1 - M.prog(t, 3.6, 4.2))
        M.texte_espace(out, "L'image traverse un réseau de neurones…", 80, 690, M.fin(54), 5, BLANC, at, 1.0, ancre="l")
        at2 = M.prog(t, 5.0, 5.8) * (1 - M.prog(t, 6.6, 7.0))
        M.texte_espace(out, "…et chaque bananier s'allume.", 80, 400, M.fin(58), 5, BLANC, at2, 1.0, ancre="l")
        a4 = M.prog(t, 1.0, 1.8)
        M.texte_espace(out, "Schéma d'illustration · les centres affichés sont les détections réelles du modèle", 64, H - 40, M.reg(18), 3, BLANC, a4 * 0.75, 0.8, ancre="l")
        return np.asarray(out)


# ------------------------------------------------------------------------------------------------ visite 3D web
_STILLS = {}


def still(M, nom):
    if nom not in _STILLS:
        d = M.RACINE / "out/video_trailer/travail/visite"
        _STILLS[nom] = cv2.imread(str(d / f"{nom}.jpg"))[..., ::-1].astype(np.float32)
    return _STILLS[nom]


def fenetre(M, im, cx, cy, z):
    """Fenêtre de 1920 x 804 découpée dans une capture 1920 x 1080, centrée en (cx, cy), grossie de z.
    Renvoie (image, fonction de projection d'un point de la capture vers l'image)."""
    W, H = M.W, M.H
    A = np.array([[z, 0, W / 2 - z * cx], [0, z, H / 2 - z * cy]], np.float32)
    out = cv2.warpAffine(im, A, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return out, (lambda x, y: (z * x + A[0, 2], z * y + A[1, 2]))


def curseur(img, x, y, ech=1.0):
    pts = np.array([(0, 0), (0, 26), (6, 20), (11, 31), (15, 29), (10, 19), (18, 19)], np.float32) * ech + np.array([x, y], np.float32)
    cv2.fillPoly(img, [pts.astype(np.int32)], (255, 255, 255), cv2.LINE_AA)
    cv2.polylines(img, [pts.astype(np.int32)], True, (20, 20, 20), 2, cv2.LINE_AA)


def plan_visite(M, t):
    """t = secondes depuis le début du plan (0 à 11). Captures réelles de la visite 3D web, reliées par des mouvements
    de caméra simulés (le rendu logiciel de la page met 15 s par capture)."""
    W, H = M.W, M.H
    P = M.prog
    cal = np.zeros((H, W, 3), np.float32)
    couches = []                       # (alpha, image, projection)

    def ajouter(nom, a, cx, cy, z):
        if a > 0.002:
            im, pr = fenetre(M, still(M, nom), cx, cy, z)
            couches.append((a, im, pr))

    # chaque état apparaît en fondu par-dessus le précédent (les états plus anciens restent dessous, opaques)
    u1 = P(t, 0, 2.4)
    z1 = 1.0 + 0.05 * u1 + 0.75 * P(t, 2.4, 3.4) ** 1.5
    c1x = 960 + (1380 - 960) * P(t, 2.4, 3.4)
    c1y = 460 + (540 - 460) * P(t, 2.4, 3.4)
    ajouter("s1_ensemble_b", 1.0, c1x, c1y, z1)
    ajouter("s2_r054_a", P(t, 2.9, 3.4), 960, 402, 1.35 - 0.35 * P(t, 2.6, 4.0))
    ajouter("s2_r054_b", P(t, 4.0, 4.5), 960, 402 + 14 * P(t, 4.0, 7.0), 1.0)
    ajouter("s3_marche_a", P(t, 6.8, 7.3), 960, 402 + 14 * P(t, 6.8, 9.0), 1.0)
    ajouter("s4_sante_b", P(t, 8.6, 9.1), 960, 402 + 14 * P(t, 8.6, 10.5), 1.0)
    ajouter("s5_ensemble_sante", P(t, 10.0, 10.5), 960, 402 + 10 * P(t, 10.0, 11.0), 1.0)
    # composition : l'image du dessous est la plus opaque (empilement par fondu)
    base = couches[0][1].copy()
    for a, im, pr in couches[1:]:
        base = base * (1 - a) + im * a
    out = base
    # curseur : mouvements et clics (coordonnées dans la capture, projetées par la fenêtre active)
    def pos_dans(nom_pr, x, y):
        return nom_pr(x, y)
    cur = None
    if t < 3.0:
        c, pr = couches[0][1], couches[0][2]
        if t < 0.5:
            x, y = 1500, 820
        elif t < 2.0:
            f = P(t, 0.5, 2.0)
            x, y = 1500 + (160 - 1500) * f, 820 + (425 - 820) * f
        else:
            x, y = 160, 425
        cur = pr(x, y)
        if 2.1 < t < 2.8:                                   # clic : onde sur la ligne de R054
            r = 10 + 40 * P(t, 2.1, 2.8)
            cv2.circle(out, (int(cur[0]), int(cur[1])), int(r), (127, 208, 138), 3, cv2.LINE_AA)
    elif 5.0 <= t < 7.2:
        pr = couches[-1][2] if couches else None
        f = P(t, 5.0, 6.0)
        x, y = 1500 + (1730 - 1500) * f, 640 + (561 - 640) * f
        cur = fenetre(M, still(M, "s2_r054_b"), 960, 402 + 14 * P(t, 4.0, 7.0), 1.0)[1](x, y)
        if 6.1 < t < 6.8:
            r = 10 + 40 * P(t, 6.1, 6.8)
            cv2.circle(out, (int(cur[0]), int(cur[1])), int(r), (127, 208, 138), 3, cv2.LINE_AA)
    elif 7.6 <= t < 9.4:
        f = P(t, 7.6, 8.4)
        x, y = 1500 + (1645 - 1500) * f, 420 + (599 - 420) * f
        cur = fenetre(M, still(M, "s3_marche_a"), 960, 402 + 14 * P(t, 6.8, 9.0), 1.0)[1](x, y)
        if 8.5 < t < 9.2:
            r = 10 + 40 * P(t, 8.5, 9.2)
            cv2.circle(out, (int(cur[0]), int(cur[1])), int(r), (127, 208, 138), 3, cv2.LINE_AA)
    if cur is not None:
        curseur(out, cur[0], cur[1], 1.3)
    out = M.vignette(out, 0.25)
    im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    a_t = P(t, 0.4, 1.4) * (1 - P(t, 3.6, 4.2))
    M.texte_espace(im, "Se promener dans son exploitation.", W / 2, 700, M.fin(78), 7, BLANC, a_t, 1.0)
    a_g = P(t, 5.0, 5.8) * (1 - P(t, 10.4, 11.0))
    M.texte_espace(im, "VISITE 3D WEB · CAPTURES DE L'INTERFACE · BANANIERS 3D EN ILLUSTRATION", 64, H - 34, M.reg(18), 3, BLANC, a_g * 0.85, 0.9, ancre="l")
    return np.asarray(im)
