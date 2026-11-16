"""Données de la visite 3D de l'exploitation de Basse-Pointe (out/visite_martinique/).

Étapes (toutes par défaut, ou choisies par --etapes) :
  tuiles     orthophoto IGN découpée en tuiles JPEG : fond à 0,8 m (tout le site, chargé au départ) et tuiles fines à
             0,2 m (chargées autour du marcheur), plus la mini-carte ;
  fourier    analyse des rangs par fenêtres de Fourier (règle « bananeraie » v1, écrite dans le LISEZMOI avant le
             calcul) : direction, période et phase des rangs, fenêtre par fenêtre ;
  bananiers  bananiers d'illustration sur les parcelles retenues, alignés sur les rangs de la photo ;
             bananiers.bin (rangés par tuile fine) ;
  donnees    donnees.json : repère, tuiles, parcelles et métriques du bulletin, zones faibles, point de départ ;
  controle   images de contrôle (parcelles retenues ou non, bananiers d'illustration sur la photo).

Repère : l'orthophoto est en EPSG:5490 (RGAF09 / UTM zone 20N), donc déjà en UTM 20N métrique ; aucun
rééchantillonnage n'est nécessaire. Origine au centre de l'image ; x vers l'est, y vers le nord, en mètres.
RGAF09 et WGS 84 diffèrent de quelques centimètres : sans effet ici.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/visite_martinique_preparer.py [--etapes fourier,controle]
"""
import argparse
import gzip
import hashlib
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import geopandas as gpd  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import rasterio  # noqa: E402
import shapely  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from rasterio import features  # noqa: E402
from scipy.ndimage import gaussian_filter  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402
from shapely.geometry import mapping  # noqa: E402

ORTHO = RACINE / "data/raw/ortho_martinique_basse_pointe/ortho_martinique_basse_pointe_2025_20cm.tif"
PARCELLES = RACINE / "out/demo_martinique/parcelles_auto_utm.geojson"
BULLETIN = RACINE / "out/demo_martinique/chaine/bulletin.csv"
ALERTES = RACINE / "out/demo_martinique/chaine/alertes.geojson"
SORTIE = RACINE / "out/visite_martinique"
FILS = 6

RES = 0.2                    # m par pixel de l'ortho
TUILE_PX = 512               # côté d'une tuile fine (102,4 m)
RES_FOND = 0.8               # m par pixel du fond
TUILE_FOND_PX = 512          # côté d'une tuile du fond (409,6 m)

# ---- règle « bananeraie » (LISEZMOI) : v1 écrite avant tout calcul, v2 après le contrôle à l'œil de la v1
VERSION_REGLE = 2
SIGMA_PASSE_HAUT_M = 4.0
RETRAIT_M = 5.0
FEN_PX = 256
PAS_PX = 128
PART_MIN_FEN = 0.80
PERIODE_MIN_M, PERIODE_MAX_M = 2.2, 7.0
# v1 (abandonnée, gardée pour mémoire) : pic >= 12 sur la moitié des fenêtres, cohérence >= 0,9, ExG du bulletin >= 0,03
SEUIL_PIC = 9.0              # v2 : une fenêtre « porte des rangs » si son pic blanchi atteint 9
PIC_MEDIAN_MIN = 9.0         # v2 : pic blanchi médian de la parcelle
COHERENCE_MIN = 0.75         # v2 : cohérence des directions des fenêtres de pic >= 9
G_MOINS_R_MIN = 0.0          # v2 : médiane de G - R sur la parcelle rétrécie (> 0 : le vert domine)
VOISINAGE_M = 60.0           # fenêtres qui portent les rangs : accord avec leurs voisines à moins de 60 m
ECART_DIR_MAX = 15.0
ECART_PERIODE_MAX = 0.25

# ---- bananiers d'illustration [H]
DENSITE_HA = 1900            # pieds par hectare, valeur typique d'une bananeraie d'export antillaise [H]
ECART_RANG_MIN, ECART_RANG_MAX = 1.6, 3.0     # m entre deux pieds d'un même rang
PERIODE_DOUBLE_M = 4.6       # au-delà, le motif est un double rang : deux rangs par période [H]
RETRAIT_BANANIERS_M = 2.0    # pas de bananier à moins de 2 m du bord de la parcelle (pistes)
N_FORMES = 48


def lire_ortho():
    with rasterio.open(ORTHO) as r:
        img = r.read()                                              # (3, H, W) uint8
        tr = r.transform
        b = r.bounds
    return img, tr, b


# ======================================================================================================== tuiles
def etape_tuiles(img, b, dossier):
    H, W = img.shape[1:]
    d_fin = dossier / "tuiles/fin"
    d_fond = dossier / "tuiles/fond"
    d_fin.mkdir(parents=True, exist_ok=True)
    d_fond.mkdir(parents=True, exist_ok=True)
    rgb = np.ascontiguousarray(img.transpose(1, 2, 0))
    tuiles_fin = []
    nc, nl = math.ceil(W / TUILE_PX), math.ceil(H / TUILE_PX)
    octets = 0
    for l in range(nl):
        for c in range(nc):
            a = rgb[l * TUILE_PX:(l + 1) * TUILE_PX, c * TUILE_PX:(c + 1) * TUILE_PX]
            f = d_fin / f"{c}_{l}.jpg"
            Image.fromarray(a).save(f, quality=80, optimize=True)
            octets += f.stat().st_size
            tuiles_fin.append(dict(c=c, l=l, px=[int(a.shape[1]), int(a.shape[0])]))
    print(f"tuiles fines : {len(tuiles_fin)} ({nc} × {nl}), {octets / 1e6:.1f} Mo", flush=True)
    # fond à 0,8 m : moyenne de blocs 4 × 4
    k = int(round(RES_FOND / RES))
    Hf, Wf = H // k, W // k
    fond = rgb[:Hf * k, :Wf * k].reshape(Hf, k, Wf, k, 3).mean((1, 3)).astype(np.uint8)
    tuiles_fond = []
    ncf, nlf = math.ceil(Wf / TUILE_FOND_PX), math.ceil(Hf / TUILE_FOND_PX)
    for l in range(nlf):
        for c in range(ncf):
            a = fond[l * TUILE_FOND_PX:(l + 1) * TUILE_FOND_PX, c * TUILE_FOND_PX:(c + 1) * TUILE_FOND_PX]
            Image.fromarray(a).save(d_fond / f"{c}_{l}.jpg", quality=82, optimize=True)
            tuiles_fond.append(dict(c=c, l=l, px=[int(a.shape[1]), int(a.shape[0])]))
    # mini-carte : 1024 px de large
    lm = 1024
    hm = int(round(lm * Hf / Wf))
    Image.fromarray(fond).resize((lm, hm), Image.LANCZOS).save(dossier / "minicarte.jpg", quality=85)
    info = dict(fin=dict(res=RES, px=TUILE_PX, n=[nc, nl], dossier="tuiles/fin", octets=octets),
                fond=dict(res=RES_FOND, px=TUILE_FOND_PX, n=[ncf, nlf], dossier="tuiles/fond",
                          taille_px=[Wf, Hf]),
                minicarte=dict(image="minicarte.jpg", px=[lm, hm]))
    (dossier / "tuiles/tuiles.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    return info


# ======================================================================================================== Fourier
def preparer_frequences():
    f = np.fft.fftfreq(FEN_PX)                                       # cycles par pixel
    FU, FV = np.meshgrid(f, f)                                       # FU : colonnes (est), FV : lignes (sud)
    rayon = np.hypot(FU, FV) * FEN_PX
    anneau = np.round(rayon).astype(int)
    per_m = np.where(rayon > 0, FEN_PX / np.maximum(rayon, 1e-9) * RES, np.inf)
    bande = (per_m >= PERIODE_MIN_M) & (per_m <= PERIODE_MAX_M) & (FU >= 0)   # demi-plan (spectre symétrique)
    hann = np.outer(np.hanning(FEN_PX), np.hanning(FEN_PX)).astype(np.float32)
    return dict(FU=FU, FV=FV, anneau=anneau, bande=bande, hann=hann)


def analyser_parcelle(args):
    """Fenêtres de Fourier d'une parcelle (règle v1). Retourne la liste des fenêtres et le verdict."""
    pid, geom, img, tr, F = args
    retr = geom.buffer(-RETRAIT_M)
    res = dict(parcelle_id=pid, fenetres=[])
    if retr.is_empty:
        return res
    # fenêtres de la grille globale (pas de 128 px) qui touchent la parcelle rétrécie
    x0, y0, x1, y1 = retr.bounds
    c0 = int(math.floor((x0 - tr.c) / RES / PAS_PX)) - 1
    c1 = int(math.ceil((x1 - tr.c) / RES / PAS_PX))
    l0 = int(math.floor((tr.f - y1) / RES / PAS_PX)) - 1
    l1 = int(math.ceil((tr.f - y0) / RES / PAS_PX))
    H, W = img.shape[1:]
    # zone de lecture (avec marge pour le flou) en pixels
    m = int(3 * SIGMA_PASSE_HAUT_M / RES)
    cmin, cmax = max(c0 * PAS_PX - m, 0), min(c1 * PAS_PX + FEN_PX + m, W)
    lmin, lmax = max(l0 * PAS_PX - m, 0), min(l1 * PAS_PX + FEN_PX + m, H)
    if cmax <= cmin or lmax <= lmin:
        return res
    bloc = img[:, lmin:lmax, cmin:cmax].astype(np.float32)
    Y = bloc.mean(0)
    Yh = Y - gaussian_filter(Y, SIGMA_PASSE_HAUT_M / RES)
    s = bloc.sum(0) + 1e-3
    exg = (2 * bloc[1] - bloc[0] - bloc[2]) / s
    Eh = exg - gaussian_filter(exg, SIGMA_PASSE_HAUT_M / RES)
    # masque de la parcelle rétrécie sur le bloc
    cols = tr.c + (np.arange(cmin, cmax) + 0.5) * RES
    lignes = tr.f - (np.arange(lmin, lmax) + 0.5) * RES
    XX, YY = np.meshgrid(cols, lignes)
    masque = features.rasterize([(retr, 1)], out_shape=Y.shape, transform=rasterio.Affine(
        RES, 0, tr.c + cmin * RES, 0, -RES, tr.f - lmin * RES), fill=0, dtype="uint8").astype(bool)
    if masque.any():
        res["g_moins_r_med"] = float(np.median((bloc[1] - bloc[0])[masque]))
        res["luminance_med"] = float(np.median(Y[masque]))
    for l in range(l0, l1 + 1):
        for c in range(c0, c1 + 1):
            pc, pl = c * PAS_PX - cmin, l * PAS_PX - lmin
            if pc < 0 or pl < 0 or pc + FEN_PX > cmax - cmin or pl + FEN_PX > lmax - lmin:
                continue
            mk = masque[pl:pl + FEN_PX, pc:pc + FEN_PX]
            part = float(mk.mean())
            if part < PART_MIN_FEN:
                continue
            w = F["hann"] * mk
            sY = Yh[pl:pl + FEN_PX, pc:pc + FEN_PX] * mk
            sY = (sY - sY[mk].mean()) * w
            P = np.abs(np.fft.fft2(sY)) ** 2
            moy = np.bincount(F["anneau"].ravel(), P.ravel()) / np.maximum(np.bincount(F["anneau"].ravel()), 1)
            Pb = P / np.maximum(moy[F["anneau"]], 1e-12)
            Pb_bande = np.where(F["bande"], Pb, 0)
            i = int(np.argmax(Pb_bande))
            iv, iu = np.unravel_index(i, P.shape)
            pic = float(Pb_bande[iv, iu])
            # affinage du pic (parabole sur le log de la puissance), en cycles par pixel
            lp = np.log(P + 1e-12)

            def para(a, b_, c_):
                d = a - 2 * b_ + c_
                return 0.0 if d >= 0 else 0.5 * (a - c_) / d
            du = para(lp[iv, (iu - 1) % FEN_PX], lp[iv, iu], lp[iv, (iu + 1) % FEN_PX])
            dv = para(lp[(iv - 1) % FEN_PX, iu], lp[iv, iu], lp[(iv + 1) % FEN_PX, iu])
            fu = (F["FU"][iv, iu] * FEN_PX + du) / FEN_PX
            fv = (F["FV"][iv, iu] * FEN_PX + dv) / FEN_PX
            # vecteur d'onde dans le monde (cycles par m) : x = colonnes, y = -lignes
            kx, ky = fu / RES, -fv / RES
            # centre de la fenêtre (monde)
            xc = tr.c + (c * PAS_PX + FEN_PX / 2) * RES
            yc = tr.f - (l * PAS_PX + FEN_PX / 2) * RES
            dx = XX[pl:pl + FEN_PX, pc:pc + FEN_PX] - xc
            dy = YY[pl:pl + FEN_PX, pc:pc + FEN_PX] - yc
            onde = np.exp(-2j * np.pi * (kx * dx + ky * dy))
            cY = complex((sY * onde).sum())
            sE = Eh[pl:pl + FEN_PX, pc:pc + FEN_PX] * mk
            sE = (sE - sE[mk].mean()) * w
            cE = complex((sE * onde).sum())
            # les bananiers sont là où l'ExG est fort : phase de la luminance, retournée si l'ExG est en opposition
            plantes_claires = (cY * cE.conjugate()).real >= 0
            phase = math.atan2(cY.imag, cY.real) + (0.0 if plantes_claires else math.pi)
            per = 1.0 / math.hypot(kx, ky)
            res["fenetres"].append(dict(x=round(xc, 2), y=round(yc, 2), part=round(part, 3), pic=round(pic, 2),
                                        periodique=pic >= SEUIL_PIC, kx=kx, ky=ky, periode=round(per, 3),
                                        dir_rang_deg=round((math.degrees(math.atan2(ky, kx)) + 90) % 180, 1),
                                        phase=phase, plantes_claires=bool(plantes_claires),
                                        coherence_exg=round(abs(cE) / (np.sqrt((sE ** 2).sum() * (w ** 2).sum()) + 1e-12), 4)))
    return res


def direction_axiale(fen):
    """Direction moyenne (modulo 180°) du vecteur d'onde et longueur résultante (angles doublés)."""
    ang = np.radians([2 * (math.degrees(math.atan2(f["ky"], f["kx"])) % 180) for f in fen])
    R = float(np.hypot(np.cos(ang).mean(), np.sin(ang).mean()))
    moy = math.degrees(math.atan2(np.sin(ang).mean(), np.cos(ang).mean())) / 2 % 180
    return moy, R


def marquer_fenetres_rangs(fen):
    """Fenêtres qui portent les rangs : pic >= SEUIL_PIC et accord avec les voisines (direction, période)."""
    cand = [f for f in fen if f["pic"] >= SEUIL_PIC]
    for f in fen:
        f["periodique"] = f["pic"] >= SEUIL_PIC
        f["rangs"] = False
    for f in cand:
        vois = [g for g in cand if math.hypot(g["x"] - f["x"], g["y"] - f["y"]) <= VOISINAGE_M]
        moy, _ = direction_axiale(vois)
        d = abs((math.degrees(math.atan2(f["ky"], f["kx"])) % 180) - moy)
        d = min(d, 180 - d)
        # v2 (révisée) : accord de direction seulement ; l'accord de période écartait les fenêtres où le pic passe
        # du rang (2,8 m) au double rang (5,7 m), fréquentes dans les blocs les plus nets
        f["rangs"] = bool(d <= ECART_DIR_MAX)


def verdict(res, exg_med=None):
    """Règle « bananeraie » v2 (LISEZMOI)."""
    fen = res["fenetres"]
    marquer_fenetres_rangs(fen)
    per = [f for f in fen if f["periodique"]]
    v = dict(version=VERSION_REGLE, n_fenetres=len(fen), n_periodiques=len(per),
             n_fenetres_rangs=sum(f["rangs"] for f in fen),
             pic_median=round(float(np.median([f["pic"] for f in fen])), 2) if fen else 0.0,
             g_moins_r_med=res.get("g_moins_r_med"), exg_med_bulletin=exg_med)
    if per:
        moy, R = direction_axiale(per)
        rg = [f for f in fen if f["rangs"]] or per
        v.update(coherence=round(R, 3), dir_rang_deg=round((moy + 90) % 180, 1),
                 periode_mediane_m=round(float(np.median([f["periode"] for f in rg])), 2),
                 part_plantes_claires=round(float(np.mean([f["plantes_claires"] for f in rg])), 2))
    else:
        v.update(coherence=0.0)
    c1 = len(fen) >= 1
    c2 = c1 and v["pic_median"] >= PIC_MEDIAN_MIN
    c3 = c2 and v["coherence"] >= COHERENCE_MIN
    gr = res.get("g_moins_r_med")
    c4 = gr is not None and gr > G_MOINS_R_MIN
    v["conditions"] = dict(analysable=c1, periodique=bool(c2), direction_coherente=bool(c3), vegetation=bool(c4))
    v["bananeraie"] = bool(c1 and c2 and c3 and c4 and v["n_fenetres_rangs"] > 0)
    if not c1:
        v["motif"] = "pas assez de place pour l'analyse (aucune fenêtre de 51 m dans la parcelle rétrécie de 5 m)"
    elif not c2:
        v["motif"] = f"pas de rangs nets sur la photo (pic médian {v['pic_median']:.1f} < {PIC_MEDIAN_MIN:.0f})"
    elif not c3:
        v["motif"] = f"rangs de directions incohérentes (cohérence {v['coherence']:.2f} < {COHERENCE_MIN})"
    elif not c4:
        v["motif"] = "pas assez de vert (le rouge domine : sol nu, paillage, toiture)"
    else:
        v["motif"] = "rangs nets, direction cohérente, couvert vert"
    return v


def etape_fourier(img, tr, parcelles, bulletin, dossier):
    F = preparer_frequences()
    t = time.time()
    taches = [(r.parcelle_id, r.geometry, img, tr, F) for r in parcelles.itertuples()]
    with ThreadPoolExecutor(FILS) as ex:
        resultats = list(ex.map(analyser_parcelle, taches))
    exg = bulletin.set_index("parcelle_id")["vigueur_drone_exg_med"].to_dict()
    for r in resultats:
        r["verdict"] = verdict(r, exg.get(r["parcelle_id"]))
    n = sum(r["verdict"]["bananeraie"] for r in resultats)
    print(f"Fourier : {sum(len(r['fenetres']) for r in resultats)} fenêtres, {n} parcelles « bananeraie » "
          f"sur {len(resultats)} en {time.time() - t:.0f} s", flush=True)
    (dossier / "travail").mkdir(exist_ok=True)
    (dossier / "travail/fourier.json").write_text(json.dumps(resultats, ensure_ascii=False, default=_json_np), encoding="utf-8")
    return resultats


# ======================================================================================================== bananiers
def _json_np(o):
    """Types numpy -> types Python (json)."""
    return o.item() if hasattr(o, "item") else str(o)


def hachage(*v):
    return int.from_bytes(hashlib.blake2b(repr(v).encode(), digest_size=8).digest(), "little")


def generer_bananiers(geom, fen_per, zones, pid, img=None, tr=None, fen_toutes=None):
    """Bananiers d'illustration d'une parcelle : rangs de la fenêtre périodique la plus proche.

    Phase : les bananiers sont sur les crêtes de la luminance si la parcelle a ses plantes claires (vote des
    fenêtres, pondéré par la force du signal ExG), sinon dans les creux. Les allées sombres (luminance lissée sous
    le 8e centile de la parcelle : ombres des allées, fossés), les taches très claires (au-dessus du 96e centile :
    pistes, sol nu) et les pixels où le rouge l'emporte (G - R lissé sur 1 m < -2) ne reçoivent pas de bananier."""
    plantable = geom.buffer(-RETRAIT_BANANIERS_M)
    if plantable.is_empty or not fen_per:
        return np.zeros((0, 5))
    poids = np.array([f.get("coherence_exg", 0.0) for f in fen_per]) + 1e-6
    claires = float((poids * np.array([f["plantes_claires"] for f in fen_per])).sum() / poids.sum()) >= 0.5
    # luminance lissée (σ = 0,8 m) sur l'emprise de la parcelle
    sombre = None
    if img is not None:
        x0, y0, x1, y1 = geom.bounds
        c0, c1 = max(int((x0 - tr.c) / RES), 0), min(int((x1 - tr.c) / RES) + 1, img.shape[2])
        l0, l1 = max(int((tr.f - y1) / RES), 0), min(int((tr.f - y0) / RES) + 1, img.shape[1])
        bloc = img[:, l0:l1, c0:c1].astype(np.float32)
        L = gaussian_filter(bloc.mean(0), 0.8 / RES)
        GR = gaussian_filter(bloc[1] - bloc[0], 1.0 / RES)          # pistes, sol nu : le rouge l'emporte
        cols = tr.c + (np.arange(c0, c1) + 0.5) * RES
        lig = tr.f - (np.arange(l0, l1) + 0.5) * RES
        XX, YY = np.meshgrid(cols, lig)
        dedans = shapely.contains_xy(plantable, XX[::5, ::5], YY[::5, ::5])
        seuil = float(np.percentile(L[::5, ::5][dedans], 8)) if dedans.any() else -1
        seuil_clair = float(np.percentile(L[::5, ::5][dedans], 96)) if dedans.any() else 1e9

        def sombre(P):
            cc = np.clip(((P[:, 0] - tr.c) / RES).astype(int) - c0, 0, c1 - c0 - 1)
            ll = np.clip(((tr.f - P[:, 1]) / RES).astype(int) - l0, 0, l1 - l0 - 1)
            return (L[ll, cc] < seuil) | (L[ll, cc] > seuil_clair) | (GR[ll, cc] < -2.0)
    # toutes les fenêtres de la parcelle : un point dont la fenêtre la plus proche ne porte pas de rangs (pré,
    # bosquet, partie de parcelle sans motif) ne reçoit pas de bananier
    toutes = fen_toutes if fen_toutes else fen_per
    centres = np.array([[f["x"], f["y"]] for f in toutes])
    arbre = cKDTree(centres)
    indice = {id(f): i for i, f in enumerate(toutes)}
    rng = np.random.default_rng(hachage(pid) % 2 ** 32)
    sorties = []
    for j, f in enumerate(fen_per):
        k = np.array([f["kx"], f["ky"]])
        kn = np.linalg.norm(k)
        u = k / kn                                                 # perpendiculaire aux rangs
        v = np.array([-u[1], u[0]])                                # le long des rangs
        per = 1.0 / kn
        double = per >= PERIODE_DOUBLE_M
        rangs_par_periode = 2 if double else 1
        ecart = float(np.clip(rangs_par_periode * 1e4 / (DENSITE_HA * per), ECART_RANG_MIN, ECART_RANG_MAX))
        # crêtes : 2π k·(p - c) + phase = 0 [2π]  ->  s = (n - phase / 2π) * per le long de u
        phase_lum = f["phase"] - (0.0 if f["plantes_claires"] else math.pi)
        phase = phase_lum + (0.0 if claires else math.pi)
        s0 = -phase / (2 * math.pi) * per
        decal = [-0.17 * per, 0.17 * per] if double else [0.0]
        demi = 40.0
        n_rangs = int(demi / per) + 2
        n_long = int(demi / ecart) + 2
        c = np.array([f["x"], f["y"]])
        pts = []
        for n in range(-n_rangs, n_rangs + 1):
            for d in decal:
                s = s0 + n * per + d
                # décalage le long du rang propre à chaque rang (pas de damier artificiel)
                o = (hachage(pid, j, n, d) % 1000) / 1000 * ecart
                t = np.arange(-n_long, n_long + 1) * ecart + o
                P = c + np.outer(np.full_like(t, s), u) + np.outer(t, v)
                pts.append(P)
        P = np.concatenate(pts)
        P += rng.normal(0, [0.12, 0.2], (len(P), 2)) @ np.array([u, v])   # léger désordre (0,12 m en travers, 0,2 m le long)
        _, plus_proche = arbre.query(P)
        P = P[plus_proche == indice[id(f)]]
        if len(P) == 0:
            continue
        P = P[shapely.contains_xy(plantable, P[:, 0], P[:, 1])]
        if sombre is not None and len(P):
            P = P[~sombre(P)]
        if len(P) == 0:
            continue
        dans_zone = shapely.contains_xy(zones, P[:, 0], P[:, 1]) if zones is not None else np.zeros(len(P), bool)
        sorties.append(np.c_[P, dans_zone, np.full(len(P), j), np.full(len(P), per)])
    return np.concatenate(sorties) if sorties else np.zeros((0, 5))


def etape_bananiers(fourier, parcelles, zones_gdf, tuiles, b, dossier, img=None, tr=None):
    t = time.time()
    geoms = dict(zip(parcelles.parcelle_id, parcelles.geometry))
    zones_par_p = {pid: shapely.union_all(g.geometry.values) for pid, g in zones_gdf.groupby("parcelle_id")}
    tous, par_parcelle = [], {}
    taches = [(r, geoms[r["parcelle_id"]], [f for f in r["fenetres"] if f["rangs"]],
               zones_par_p.get(r["parcelle_id"])) for r in fourier if r["verdict"]["bananeraie"]]
    with ThreadPoolExecutor(FILS) as ex:
        res = list(ex.map(lambda a: generer_bananiers(a[1], a[2], a[3], a[0]["parcelle_id"], img, tr, a[0]["fenetres"]), taches))
    for (r, *_), P in zip(taches, res):
        pid = r["parcelle_id"]
        par_parcelle[pid] = dict(n=int(len(P)), n_zone=int(P[:, 2].sum()) if len(P) else 0)
        if len(P):
            tous.append(np.c_[P[:, :3], np.full(len(P), int(pid[1:]))])
    A = np.concatenate(tous)
    n = len(A)
    # forme, rotation, échelle : tirages fixes (illustratifs)
    rng = np.random.default_rng(2026)
    forme = rng.integers(0, N_FORMES, n)
    rot = rng.integers(0, 256, n)
    ech = rng.integers(0, 256, n)                                  # échelle 0,90 à 1,15 des formes de la v4 [H]
    # rangement par tuile fine
    nc, nl = tuiles["fin"]["n"]
    T = TUILE_PX * RES
    col = np.clip(((A[:, 0] - b.left) // T).astype(int), 0, nc - 1)
    lig = np.clip(((b.top - A[:, 1]) // T).astype(int), 0, nl - 1)
    idx = lig * nc + col
    ordre = np.argsort(idx, kind="stable")
    A, forme, rot, ech, idx, col, lig = (z[ordre] for z in (A, forme, rot, ech, idx, col, lig))
    x0 = b.left + col * T
    y0 = b.top - (lig + 1) * T
    xs = np.clip(np.round((A[:, 0] - x0) * 100), 0, 65535).astype(np.uint16)
    ys = np.clip(np.round((A[:, 1] - y0) * 100), 0, 65535).astype(np.uint16)
    rec = np.zeros(n, dtype=[("x", "<u2"), ("y", "<u2"), ("forme", "u1"), ("drap", "u1"), ("rot", "u1"), ("ech", "u1")])
    rec["x"], rec["y"], rec["forme"], rec["drap"], rec["rot"], rec["ech"] = xs, ys, forme, A[:, 2].astype(np.uint8), rot, ech
    (dossier / "bananiers.bin").write_bytes(rec.tobytes())
    debut = np.searchsorted(idx, np.arange(nc * nl))
    fin = np.searchsorted(idx, np.arange(nc * nl), side="right")
    index = [[int(a), int(z - a)] for a, z in zip(debut, fin)]
    print(f"bananiers d'illustration : {n} sur {len(par_parcelle)} parcelles, "
          f"{int(A[:, 2].sum())} dans une zone faible, {(dossier / 'bananiers.bin').stat().st_size / 1e6:.1f} Mo, "
          f"{time.time() - t:.0f} s", flush=True)
    info = dict(fichier="bananiers.bin", n=int(n), octets_par_pied=8, index_par_tuile=index,
                format="uint16 x, uint16 y (cm depuis le coin sud-ouest de la tuile fine), uint8 forme (0-47), "
                       "uint8 drapeaux (1 = dans une zone faible), uint8 rotation (/256 tour), uint8 échelle (0,90 + 0,25 × v/255, appliquée par la page)",
                par_parcelle=par_parcelle)
    (dossier / "travail/bananiers_info.json").write_text(json.dumps(info, ensure_ascii=False, default=_json_np), encoding="utf-8")
    return info, A


# ======================================================================================================== données
def anneaux(geom, x0, y0, tol=0.4):
    """Polygones (ou multipolygones) en anneaux de coordonnées locales arrondies à 0,1 m."""
    g = geom.simplify(tol, preserve_topology=True)
    polys = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
    out = []
    for p in polys:
        if p.is_empty:
            continue
        rings = [p.exterior] + list(p.interiors)
        out.append([[round(v, 1) for xy in r.coords[:-1] for v in (xy[0] - x0, xy[1] - y0)] for r in rings])
    return out


def point_de_depart(fourier, parcelles, x0, y0):
    """Bord d'une belle parcelle de bananiers : compacte, 1,5 à 4 ha, rangs nets ; dans une allée, regard le long des rangs."""
    geoms = dict(zip(parcelles.parcelle_id, parcelles.geometry))
    meilleurs = []
    for r in fourier:
        v = r["verdict"]
        if not v["bananeraie"]:
            continue
        g = geoms[r["parcelle_id"]]
        ha = g.area / 1e4
        compac = g.area / g.convex_hull.area
        if not (1.5 <= ha <= 4.0) or compac < 0.9:
            continue
        note = v["n_fenetres_rangs"] / max(v["n_fenetres"], 1) * v["coherence"] * min(v["pic_median"], 200) * compac
        meilleurs.append((note, r["parcelle_id"]))
    meilleurs.sort(reverse=True)
    pid = meilleurs[0][1]
    r = next(q for q in fourier if q["parcelle_id"] == pid)
    g = geoms[pid]
    per = [f for f in r["fenetres"] if f["rangs"]]
    # fenêtre la plus proche du bord sud de la parcelle ; on part de son centre et on recule le long des rangs
    c = np.array(g.centroid.coords[0])
    f = min(per, key=lambda q: math.hypot(q["x"] - c[0], q["y"] - c[1]))
    k = np.array([f["kx"], f["ky"]])
    u = k / np.linalg.norm(k)
    v = np.array([-u[1], u[0]])
    P = 1 / np.linalg.norm(k)
    # allée : à mi-chemin entre deux crêtes (ou au milieu de l'allée d'un double rang)
    s0 = -f["phase"] / (2 * math.pi) * P + 0.5 * P
    centre = np.array([f["x"], f["y"]]) + u * s0
    # du centre, on recule le long des rangs (dans le sens qui sort le plus vite de la parcelle) jusqu'au bord
    sens = None
    for sg in (1, -1):
        for d in np.arange(0, 400, 0.5):
            p = centre - sg * v * d
            if not g.contains(shapely.Point(p)):
                if sens is None or d < sens[1]:
                    sens = (sg, d)
                break
    sg, d = sens
    pos = centre - sg * v * max(d - 4.0, 0.0)                      # dans l'allée, à 4 m du bord de la parcelle
    regard = sg * v
    lacet = math.degrees(math.atan2(-regard[0], regard[1]))         # convention de la page : 0 = nord, + = vers l'ouest
    return dict(parcelle=pid, x=round(float(pos[0] - x0), 2), y=round(float(pos[1] - y0), 2), lacet_deg=round(lacet, 1),
                candidats=[p for _, p in meilleurs[:8]])


def etape_donnees(fourier, parcelles, bulletin, alertes, zones_gdf, tuiles, info_b, b, dossier):
    x0, y0 = (b.left + b.right) / 2, (b.bottom + b.top) / 2
    bul = bulletin.set_index("parcelle_id")
    fr = {r["parcelle_id"]: r for r in fourier}
    al = alertes.copy()
    ps = []
    for r in parcelles.itertuples():
        pid = r.parcelle_id
        q = bul.loc[pid]
        v = fr[pid]["verdict"]
        a = al[al.parcelle_id == pid]
        alist = [dict(id=x.id, type=x.type, surface_ha=None if pd.isna(x.surface_ha) else round(float(x.surface_ha), 4),
                      valeur=None if pd.isna(x.valeur) else round(float(x.valeur), 3), message=x.message)
                 for x in a.itertuples()]
        c = r.geometry.representative_point()
        ps.append(dict(
            id=pid, anneaux=anneaux(r.geometry, x0, y0), centre=[round(c.x - x0, 1), round(c.y - y0, 1)],
            surface_ha=round(float(q.surface_ha), 2), score=float(q.score), niveau=q.niveau, n_alertes=int(q.n_alertes),
            alertes=alist,
            exg_med=None if pd.isna(q.vigueur_drone_exg_med) else float(q.vigueur_drone_exg_med),
            zones_faibles_ha=None if pd.isna(q.vigueur_drone_zones_faibles_exg_ha) else float(q.vigueur_drone_zones_faibles_exg_ha),
            pieds_detectes_chaine=int(q.comptage_n_pieds),
            bananeraie=v["bananeraie"], regle=v,
            bananiers_illustration=info_b["par_parcelle"].get(pid, dict(n=0, n_zone=0))))
    zs = [dict(id=z.id, parcelle=z.parcelle_id, surface_ha=round(float(z.surface_ha), 4), valeur=round(float(z.valeur), 3),
               anneaux=anneaux(z.geometry, x0, y0, tol=0.15)) for z in zones_gdf.itertuples()]
    depart = point_de_depart(fourier, parcelles, x0, y0)
    doc = dict(
        version=1,
        description="Visite 3D de l'exploitation de Basse-Pointe (Martinique) : sol réel (orthophoto IGN), parcelles "
                    "automatiques et métriques de la chaîne (réels) ; bananiers 3D d'illustration.",
        repere=dict(epsg=5490, nom="RGAF09 / UTM zone 20N", origine=[x0, y0],
                    note="x vers l'est, y vers le nord, en m depuis le centre de l'orthophoto"),
        emprise=dict(xmin=b.left - x0, xmax=b.right - x0, ymin=b.bottom - y0, ymax=b.top - y0),
        tuiles=tuiles,
        bananiers=dict(fichier=info_b["fichier"], n=info_b["n"], index_par_tuile=info_b["index_par_tuile"],
                       format=info_b["format"], densite_ha=DENSITE_HA, periode_double_m=PERIODE_DOUBLE_M,
                       ecart_rang_m=[ECART_RANG_MIN, ECART_RANG_MAX], retrait_m=RETRAIT_BANANIERS_M),
        regle_bananeraie=dict(version=VERSION_REGLE, sigma_passe_haut_m=SIGMA_PASSE_HAUT_M, retrait_m=RETRAIT_M,
                              fenetre_m=FEN_PX * RES, pas_m=PAS_PX * RES, part_min=PART_MIN_FEN,
                              periodes_m=[PERIODE_MIN_M, PERIODE_MAX_M], seuil_pic=SEUIL_PIC,
                              pic_median_min=PIC_MEDIAN_MIN, coherence_min=COHERENCE_MIN, g_moins_r_min=G_MOINS_R_MIN),
        parcelles=ps, zones_faibles=zs, depart=depart,
        source=dict(ortho="IGN, BD ORTHO® (Licence Ouverte Etalab 2.0), 20 cm, édition 2025 très probable",
                    parcelles="out/demo_martinique/parcelles_auto_utm.geojson",
                    bulletin="out/demo_martinique/chaine/bulletin.csv",
                    alertes="out/demo_martinique/chaine/alertes.geojson"),
    )
    texte = json.dumps(doc, ensure_ascii=False, separators=(",", ":"), default=_json_np)
    (dossier / "donnees.json").write_text(texte, encoding="utf-8")
    # version compressée lue par la page (l'antivirus de la machine de développement bloquait le JSON brut)
    (dossier / "donnees.json.gz").write_bytes(gzip.compress(texte.encode("utf-8"), 9, mtime=0))
    print(f"donnees.json : {(dossier / 'donnees.json').stat().st_size / 1e6:.2f} Mo ; départ {depart}", flush=True)
    return doc


# ======================================================================================================== contrôle
def police(t):
    for nom in ("arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(nom, t)
        except OSError:
            pass
    return ImageFont.load_default()


def etape_controle(img, tr, b, fourier, parcelles, dossier, bananiers=None, extraits=()):
    d = dossier / "controle"
    d.mkdir(exist_ok=True)
    # 1. vue d'ensemble à 0,5 m : vert = bananeraie retenue, rouge = rejetée (avec le motif)
    k = 5
    rgb = img[:, ::1, ::1]
    H, W = rgb.shape[1:]
    small = np.asarray(Image.fromarray(np.ascontiguousarray(rgb.transpose(1, 2, 0))).resize((W * 2 // k, H * 2 // k), Image.BILINEAR))
    res = RES * k / 2
    im = Image.fromarray(small).convert("RGBA")
    calque = Image.new("RGBA", im.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(calque)
    fr = {r["parcelle_id"]: r for r in fourier}
    f = police(15)

    def px(x, y):
        return ((x - b.left) / res, (b.top - y) / res)
    for r in parcelles.itertuples():
        v = fr[r.parcelle_id]["verdict"]
        g = r.geometry
        polys = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
        for p in polys:
            pts = [px(*xy) for xy in p.exterior.coords]
            if v["bananeraie"]:
                dr.polygon(pts, fill=(60, 220, 90, 70), outline=(80, 255, 110, 255), width=3)
            else:
                dr.polygon(pts, fill=(230, 40, 40, 60), outline=(255, 70, 70, 255), width=3)
        c = g.representative_point()
        u, w = px(c.x, c.y)
        cond = v["conditions"]
        code = "B" if v["bananeraie"] else ("A" if not cond["analysable"] else "P" if not cond["periodique"]
                                            else "D" if not cond["direction_coherente"] else "V")
        txt = f"{r.parcelle_id} {code}"
        dr.text((u - 30, w - 8), txt, fill=(255, 255, 255, 255), font=f, stroke_width=3, stroke_fill=(0, 0, 0, 255))
    im = Image.alpha_composite(im, calque).convert("RGB")
    im.save(d / "regle_bananeraie.jpg", quality=85)
    # 2. extraits à 0,2 m : bananiers d'illustration (points) sur la photo
    if bananiers is not None:
        for pid in extraits:
            g = parcelles.set_index("parcelle_id").geometry[pid]
            c = g.representative_point()
            demi = 40
            c0 = int((c.x - demi - b.left) / RES)
            l0 = int((b.top - (c.y + demi)) / RES)
            n = int(2 * demi / RES)
            a = np.ascontiguousarray(img[:, l0:l0 + n, c0:c0 + n].transpose(1, 2, 0))
            gros = Image.fromarray(a).resize((n * 2, n * 2), Image.BILINEAR)
            dr = ImageDraw.Draw(gros)
            sel = (np.abs(bananiers[:, 0] - c.x) < demi) & (np.abs(bananiers[:, 1] - c.y) < demi)
            for x, y, z in bananiers[sel][:, :3]:
                u = ((x - b.left) / RES - c0) * 2
                w = ((b.top - y) / RES - l0) * 2
                col = (255, 140, 0) if z else (255, 235, 59)
                dr.ellipse([u - 3, w - 3, u + 3, w + 3], outline=col, width=2)
            # moitié gauche sans points pour comparer
            brut = Image.fromarray(a).resize((n * 2, n * 2), Image.BILINEAR)
            cote = Image.new("RGB", (n * 4 + 10, n * 2), (0, 0, 0))
            cote.paste(brut, (0, 0))
            cote.paste(gros, (n * 2 + 10, 0))
            cote.save(d / f"rangs_{pid}.jpg", quality=88)
    print(f"contrôle : {d}", flush=True)


# ======================================================================================================== principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etapes", default="tuiles,fourier,bananiers,donnees,controle")
    ap.add_argument("--extraits", default="", help="parcelles à montrer en extrait (contrôle des rangs), séparées par des virgules")
    a = ap.parse_args()
    etapes = set(a.etapes.split(","))
    d = SORTIE
    d.mkdir(parents=True, exist_ok=True)
    (d / "travail").mkdir(exist_ok=True)
    t = time.time()
    img, tr, b = lire_ortho()
    print(f"ortho lue : {img.shape} en {time.time() - t:.0f} s", flush=True)
    parcelles = gpd.read_file(PARCELLES)
    assert parcelles.crs.to_epsg() == 5490
    bulletin = pd.read_csv(BULLETIN, encoding="utf-8")
    alertes = gpd.read_file(ALERTES).to_crs(5490)
    zones = alertes[alertes["type"] == "zone_faible"].copy()
    zones["geometry"] = zones.geometry.make_valid()
    if "tuiles" in etapes:
        tuiles = etape_tuiles(img, b, d)
    else:
        tuiles = json.loads((d / "tuiles/tuiles.json").read_text(encoding="utf-8"))
    if "fourier" in etapes:
        fourier = etape_fourier(img, tr, parcelles, bulletin, d)
    else:
        fourier = json.loads((d / "travail/fourier.json").read_text(encoding="utf-8"))
        for r in fourier:                                            # verdict recalculé (même règle)
            r["verdict"] = verdict(r, bulletin.set_index("parcelle_id")["vigueur_drone_exg_med"].get(r["parcelle_id"]))
    A = None
    if "bananiers" in etapes or "donnees" in etapes or "controle" in etapes:
        info_b, A = etape_bananiers(fourier, parcelles, zones, tuiles, b, d, img, tr)
    if "donnees" in etapes:
        etape_donnees(fourier, parcelles, bulletin, alertes, zones, tuiles, info_b, b, d)
    if "controle" in etapes:
        ex = [p for p in a.extraits.split(",") if p]
        etape_controle(img, tr, b, fourier, parcelles, d, A, ex)
    print(f"terminé en {time.time() - t:.0f} s", flush=True)


if __name__ == "__main__":
    main()
