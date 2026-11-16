#!/usr/bin/env python3
"""Visite 3D d'une petite partie de l'exploitation de Basse-Pointe : 13 parcelles déclarées (RPG), environ 43 ha.

Sortie : out/visite_basse_pointe_zone/ (page index.html écrite à la main, à côté).

Réel :
  - le sol : orthophoto IGN (BD ORTHO®, 20 cm, EPSG:5490), découpée sur l'emprise de la zone (parcelles + 30 m) ;
  - les parcelles : RPG de l'IGN (out/demo_martinique_rpg/parcelles_rpg_utm.geojson), culture déclarée ;
  - les chiffres : bulletin et alertes de la chaîne (out/demo_martinique_rpg/chaine/), sans aucun recalcul.
Illustration :
  - les bananiers 3D : placement de scripts/visite_martinique_rpg.py (rangs alignés sur la photo, fenêtres complétées
    dans les couverts fermés), sur les parcelles déclarées en banane qui ne sont pas en sol nu sur la photo ;
  - la canne 3D : touffes posées en rangs de 1,5 m [H], dans la direction des rangs vus sur la photo s'il y en a,
    sinon le long du grand côté de la parcelle.

Fichiers produits :
  tuiles/fin/{c}_{l}.jpg     photo à 0,2 m (natif), tuiles de 512 px (102,4 m), chargées autour de la caméra ;
  tuiles/fond/{c}_{l}.jpg    photo à 0,4 m, tuiles de 512 px, toute l'emprise, chargées au départ ;
  tuiles/contexte/{c}_{l}.jpg photo à 1,6 m autour de l'emprise (400 m), affichée grisée ;
  minicarte.jpg              mini-carte de l'emprise ;
  masque.bin.gz              numéro de parcelle (0 = hors zone, 1 à 13) par pixel de 0,5 m ;
  bananiers.bin, canne.bin   positions des plantes 3D d'illustration (8 octets par plante, rangées par tuile fine) ;
  bananiers.glb              formes des bananiers (copiées de out/visite_martinique/) ;
  donnees.json(.gz)          repère, parcelles, chiffres du bulletin, zones moins vertes ;
  controle/zone.jpg          contrôle : parcelles, numéros, plantes d'illustration sur la photo.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/visite_zone_preparer.py
"""
import gzip
import json
import math
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")      # en mode -I, PYTHONIOENCODING est ignoré

import geopandas as gpd  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import rasterio  # noqa: E402
import shapely  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from rasterio import features  # noqa: E402
from scipy.ndimage import gaussian_filter  # noqa: E402
from shapely.ops import polylabel  # noqa: E402

import visite_martinique_preparer as vm  # noqa: E402  (importés, non modifiés)
import visite_martinique_rpg as rpg  # noqa: E402

DOSSIER_RPG = RACINE / "out/demo_martinique_rpg"
PARCELLES = DOSSIER_RPG / "parcelles_rpg_utm.geojson"
BULLETIN = DOSSIER_RPG / "chaine/bulletin.csv"
ALERTES = DOSSIER_RPG / "chaine/alertes.geojson"
GLB = RACINE / "out/visite_martinique/bananiers.glb"
SORTIE = RACINE / "out/visite_basse_pointe_zone"
FILS = 6

ZONE = ["R014", "R016", "R033", "R034", "R035", "R036", "R037", "R050", "R051", "R052", "R053", "R054", "R055"]
MARGE_M = 30.0
RES = vm.RES                 # 0,2 m, natif
TUILE_PX = 512               # tuiles fines (102,4 m)
# fichiers de moins de 100 ko : sur la machine de développement, l'antivirus coupe souvent les réponses plus longues
RES_FOND, TUILE_FOND_PX = 0.4, 512
RES_CTX, MARGE_CTX_M, TUILE_CTX_PX = 1.6, 400.0, 384
RES_MASQUE = 0.5
RETRAIT_BORD_M = 0.8         # bordure 3D posée 0,8 m à l'intérieur : deux parcelles voisines ne se chevauchent pas
UNITE_POS = 0.02             # m : positions des plantes en unités de 2 cm depuis le coin sud-ouest de l'emprise
CODE_CANNE = "CSA"
CANNE_RANG_M = 1.5           # [H] écart entre rangs de canne
CANNE_PAS_M = 0.9            # [H] une touffe tous les 0,9 m le long du rang
CANNE_RETRAIT_M = 1.5
REMBOURRAGE = 65536          # octets nuls ajoutés à la fin des fichiers servis (voir rembourrer)


def json_np(o):
    return o.item() if hasattr(o, "item") else str(o)


# ============================================================================================================ emprise
def emprise_zone(geoms, tr):
    x0, y0, x1, y1 = shapely.union_all(geoms).bounds
    # calée sur la grille des pixels de l'ortho
    c0 = math.floor((x0 - MARGE_M - tr.c) / RES)
    c1 = math.ceil((x1 + MARGE_M - tr.c) / RES)
    l0 = math.floor((tr.f - (y1 + MARGE_M)) / RES)
    l1 = math.ceil((tr.f - (y0 - MARGE_M)) / RES)
    return dict(c0=c0, c1=c1, l0=l0, l1=l1,
                xmin=tr.c + c0 * RES, xmax=tr.c + c1 * RES, ymax=tr.f - l0 * RES, ymin=tr.f - l1 * RES)


def blocs_moyens(a, k):
    H, W = a.shape[:2]
    H2, W2 = H // k, W // k
    return a[:H2 * k, :W2 * k].reshape(H2, k, W2, k, 3).mean((1, 3)).astype(np.uint8)


def etape_tuiles(img, tr, emp, d):
    rgb = np.ascontiguousarray(img[:, emp["l0"]:emp["l1"], emp["c0"]:emp["c1"]].transpose(1, 2, 0))
    H, W = rgb.shape[:2]
    for sous in ("tuiles/fin", "tuiles/fond"):
        (d / sous).mkdir(parents=True, exist_ok=True)
    nc, nl = math.ceil(W / TUILE_PX), math.ceil(H / TUILE_PX)
    octets = 0
    for l in range(nl):
        for c in range(nc):
            a = rgb[l * TUILE_PX:(l + 1) * TUILE_PX, c * TUILE_PX:(c + 1) * TUILE_PX]
            f = d / f"tuiles/fin/{c}_{l}.jpg"
            Image.fromarray(a).save(f, quality=82, optimize=True)
            octets += f.stat().st_size
    k = int(round(RES_FOND / RES))
    fond = blocs_moyens(rgb, k)
    Hf, Wf = fond.shape[:2]
    ncf, nlf = math.ceil(Wf / TUILE_FOND_PX), math.ceil(Hf / TUILE_FOND_PX)
    octets_fond = 0
    for l in range(nlf):
        for c in range(ncf):
            a = fond[l * TUILE_FOND_PX:(l + 1) * TUILE_FOND_PX, c * TUILE_FOND_PX:(c + 1) * TUILE_FOND_PX]
            f = d / f"tuiles/fond/{c}_{l}.jpg"
            Image.fromarray(a).save(f, quality=84, optimize=True)
            octets_fond += f.stat().st_size
    # mini-carte : 440 px de large
    lm = 440
    hm = int(round(lm * Hf / Wf))
    Image.fromarray(fond).resize((lm, hm), Image.LANCZOS).save(d / "minicarte.jpg", quality=80)
    # contexte autour de l'emprise, à 1,6 m, borné à l'ortho
    kc = int(round(RES_CTX / RES))
    m = int(MARGE_CTX_M / RES)
    cc0, ll0 = max(emp["c0"] - m, 0), max(emp["l0"] - m, 0)
    cc1, ll1 = min(emp["c1"] + m, img.shape[2]), min(emp["l1"] + m, img.shape[1])
    cc1 = cc0 + (cc1 - cc0) // kc * kc
    ll1 = ll0 + (ll1 - ll0) // kc * kc
    ctx = blocs_moyens(np.ascontiguousarray(img[:, ll0:ll1, cc0:cc1].transpose(1, 2, 0)), kc)
    (d / "tuiles/contexte").mkdir(parents=True, exist_ok=True)
    ncc, nlc = math.ceil(ctx.shape[1] / TUILE_CTX_PX), math.ceil(ctx.shape[0] / TUILE_CTX_PX)
    for l in range(nlc):
        for c in range(ncc):
            a = ctx[l * TUILE_CTX_PX:(l + 1) * TUILE_CTX_PX, c * TUILE_CTX_PX:(c + 1) * TUILE_CTX_PX]
            Image.fromarray(a).save(d / f"tuiles/contexte/{c}_{l}.jpg", quality=78, optimize=True)
    info = dict(
        fin=dict(res=RES, px=TUILE_PX, n=[nc, nl], taille_px=[W, H], dossier="tuiles/fin", octets=octets),
        fond=dict(res=RES_FOND, px=TUILE_FOND_PX, n=[ncf, nlf], taille_px=[Wf, Hf], dossier="tuiles/fond", octets=octets_fond),
        minicarte=dict(image="minicarte.jpg", px=[lm, hm]),
        contexte=dict(dossier="tuiles/contexte", res=RES_CTX, px=TUILE_CTX_PX, n=[ncc, nlc],
                      taille_px=[int(ctx.shape[1]), int(ctx.shape[0])],
                      xmin=tr.c + cc0 * RES, xmax=tr.c + cc1 * RES, ymax=tr.f - ll0 * RES, ymin=tr.f - ll1 * RES))
    print(f"tuiles fines : {nc} × {nl}, {octets / 1e6:.1f} Mo ; fond : {ncf} × {nlf}, {octets_fond / 1e6:.1f} Mo ; "
          f"contexte {ctx.shape[1]} × {ctx.shape[0]} px", flush=True)
    return info


def etape_masque(parcelles, emp, d):
    W = int(round((emp["xmax"] - emp["xmin"]) / RES_MASQUE))
    H = int(round((emp["ymax"] - emp["ymin"]) / RES_MASQUE))
    tr = rasterio.Affine(RES_MASQUE, 0, emp["xmin"], 0, -RES_MASQUE, emp["ymax"])
    m = features.rasterize([(g, i + 1) for i, g in enumerate(parcelles.geometry)], out_shape=(H, W), transform=tr,
                           fill=0, dtype="uint8")
    # ligne 0 = sud (comme les coordonnées de texture) : on retourne l'image
    (d / "masque.bin.gz").write_bytes(gzip.compress(np.ascontiguousarray(m[::-1]).tobytes(), 9, mtime=0))
    print(f"masque : {W} × {H} px à {RES_MASQUE} m", flush=True)
    return dict(fichier="masque.bin.gz", px=[W, H], res=RES_MASQUE, note="uint8, 0 = hors zone, i = parcelles[i - 1], ligne 0 au sud")


# ============================================================================================================ plantes
def etape_fourier_zone(img, tr, parcelles, bulletin):
    F = vm.preparer_frequences()
    taches = [(r.parcelle_id, r.geometry, img, tr, F) for r in parcelles.itertuples()]
    with ThreadPoolExecutor(FILS) as ex:
        res = list(ex.map(vm.analyser_parcelle, taches))
    exg = bulletin.set_index("parcelle_id")["vigueur_drone_exg_med"].to_dict()
    for r in res:
        r["verdict"] = vm.verdict(r, exg.get(r["parcelle_id"]))
    return res


def regle_rpg(fourier, parcelles):
    """Même logique que scripts/visite_martinique_rpg.py (main) : bananiers 3D sur les parcelles déclarées en banane,
    sauf sol nu ; fenêtres sans rangs nets complétées."""
    geoms = dict(zip(parcelles.parcelle_id, parcelles.geometry))
    culture = dict(zip(parcelles.parcelle_id, parcelles.culture_code))
    rng = np.random.default_rng(2026)
    for r in fourier:
        pid, v = r["parcelle_id"], r["verdict"]
        sol_nu = r.get("g_moins_r_med") is None or r["g_moins_r_med"] <= vm.G_MOINS_R_MIN
        v["sol_nu"] = bool(sol_nu)
        if culture[pid] == rpg.CODE_BANANE and not sol_nu:
            info = rpg.completer_fenetres(r, geoms[pid], rng)
            v.update(bananeraie=True, rangs=info)
        else:
            v["bananeraie"] = False


def direction_canne(r, geom):
    nettes = [f for f in r["fenetres"] if f.get("rangs")]
    if nettes:
        moy, _ = vm.direction_axiale(nettes)
        return (moy + 90) % 180, "rangs vus sur la photo"
    rect = geom.minimum_rotated_rectangle
    xy = np.array(rect.exterior.coords)[:4]
    long_ = max((xy[(i + 1) % 4] - xy[i] for i in range(4)), key=np.linalg.norm)
    return math.degrees(math.atan2(long_[1], long_[0])) % 180, "grand côté de la parcelle"


def generer_canne(geom, dir_deg, zones, pid, img, tr):
    plantable = geom.buffer(-CANNE_RETRAIT_M)
    if plantable.is_empty:
        return np.zeros((0, 3))
    a = math.radians(dir_deg)
    v = np.array([math.cos(a), math.sin(a)])        # le long des rangs
    u = np.array([-v[1], v[0]])                     # en travers
    c = np.array(geom.centroid.coords[0])
    demi = math.hypot(geom.bounds[2] - geom.bounds[0], geom.bounds[3] - geom.bounds[1]) / 2 + 5
    rng = np.random.default_rng(vm.hachage("canne", pid) % 2 ** 32)
    s = np.arange(-demi, demi, CANNE_RANG_M)
    t = np.arange(-demi, demi, CANNE_PAS_M)
    S, Tt = np.meshgrid(s, t)
    Tt = Tt + rng.uniform(0, CANNE_PAS_M, S.shape[1])[None, :]
    P = c + np.outer(S.ravel(), u) + np.outer(Tt.ravel(), v)
    P += rng.normal(0, [0.08, 0.2], (len(P), 2)) @ np.array([u, v])
    P = P[shapely.contains_xy(plantable, P[:, 0], P[:, 1])]
    # pas de canne où le rouge l'emporte (pistes, sol nu)
    x0, y0, x1, y1 = geom.bounds
    c0, c1 = int((x0 - tr.c) / RES), int((x1 - tr.c) / RES) + 1
    l0, l1 = int((tr.f - y1) / RES), int((tr.f - y0) / RES) + 1
    bloc = img[:, l0:l1, c0:c1].astype(np.float32)
    GR = gaussian_filter(bloc[1] - bloc[0], 1.0 / RES)
    cc = np.clip(((P[:, 0] - tr.c) / RES).astype(int) - c0, 0, c1 - c0 - 1)
    ll = np.clip(((tr.f - P[:, 1]) / RES).astype(int) - l0, 0, l1 - l0 - 1)
    P = P[GR[ll, cc] >= -2.0]
    dans_zone = shapely.contains_xy(zones, P[:, 0], P[:, 1]) if zones is not None else np.zeros(len(P), bool)
    return np.c_[P, dans_zone]


def ranger(A, emp, info_fin, graine):
    """Enregistrements de 8 octets rangés par tuile fine : x, y (uint16, unités de 2 cm depuis le coin sud-ouest de
    l'emprise), forme (uint8), drapeaux (1 = zone moins verte), rotation (/256 tour), échelle (0,90 + 0,25 × v/255)."""
    n = len(A)
    rng = np.random.default_rng(graine)
    forme = rng.integers(0, vm.N_FORMES, n)
    rot = rng.integers(0, 256, n)
    ech = rng.integers(0, 256, n)
    nc, nl = info_fin["n"]
    T = TUILE_PX * RES
    col = np.clip(((A[:, 0] - emp["xmin"]) // T).astype(int), 0, nc - 1)
    lig = np.clip(((emp["ymax"] - A[:, 1]) // T).astype(int), 0, nl - 1)
    idx = lig * nc + col
    o = np.argsort(idx, kind="stable")
    A, forme, rot, ech, idx = A[o], forme[o], rot[o], ech[o], idx[o]
    rec = np.zeros(n, dtype=[("x", "<u2"), ("y", "<u2"), ("forme", "u1"), ("drap", "u1"), ("rot", "u1"), ("ech", "u1")])
    rec["x"] = np.clip(np.round((A[:, 0] - emp["xmin"]) / UNITE_POS), 0, 65535)
    rec["y"] = np.clip(np.round((A[:, 1] - emp["ymin"]) / UNITE_POS), 0, 65535)
    rec["forme"], rec["drap"], rec["rot"], rec["ech"] = forme, A[:, 2].astype(np.uint8), rot, ech
    debut = np.searchsorted(idx, np.arange(nc * nl))
    fin = np.searchsorted(idx, np.arange(nc * nl), side="right")
    return rec.tobytes(), [[int(a), int(z - a)] for a, z in zip(debut, fin)], A


# ============================================================================================================ données
def anneaux(geom, x0, y0, tol=0.3):
    return vm.anneaux(geom, x0, y0, tol)


def regle_score():
    """Règle de score telle que la chaîne l'a appliquée (journal.json du bulletin), pour les phrases de la fiche."""
    j = json.loads((DOSSIER_RPG / "chaine/journal.json").read_text(encoding="utf-8"))
    r = j["reglages"]
    return dict(date_bulletin=j.get("date"), surface_min_penalite_ha=r.get("vigueur", {}).get("surface_min_penalite_ha"),
                penalite_vigueur=r["score"]["penalites"].get("vigueur"), facteur_moyenne=r["score"].get("facteur_moyenne"),
                seuil_vert=r["score"].get("seuil_vert"), seuil_orange=r["score"].get("seuil_orange"))


def rembourrer(d):
    """Ajoute REMBOURRAGE octets nuls à la fin de chaque fichier lu par la page et rend leur taille utile.

    Sur la machine de développement, l'antivirus retient souvent la fin d'une réponse du serveur local (mesuré le
    16/11 : une tuile de 91 755 octets s'arrête à 65 280 octets une fois sur deux, et la fin n'arrive jamais ; avec
    70 000 octets nuls ajoutés, les 91 755 octets utiles sont arrivés 6 fois sur 6). La page lit les octets utiles
    puis coupe la connexion. donnees.json.gz (25 ko, lu en premier) n'est pas rembourré : il porte la table des tailles."""
    tailles = {}
    for f in sorted(d.rglob("*")):
        rel = f.relative_to(d).as_posix()
        if not f.is_file() or rel.split("/")[0] in ("controle", "captures", "travail") or \
                rel in ("index.html", "visite.js", "LISEZMOI.md", "donnees.json", "donnees.json.gz"):
            continue
        utile = f.stat().st_size
        tailles[rel] = utile
        with open(f, "ab") as h:
            h.write(bytes(REMBOURRAGE))
    print(f"{len(tailles)} fichiers rembourrés de {REMBOURRAGE} octets", flush=True)
    return tailles


def etape_donnees(parcelles, bulletin, alertes_z, zones, fourier, plantes, emp, tuiles, masque, d, tailles):
    x0 = round((emp["xmin"] + emp["xmax"]) / 2, 1)
    y0 = round((emp["ymin"] + emp["ymax"]) / 2, 1)
    bul = bulletin.set_index("parcelle_id")
    fr = {r["parcelle_id"]: r for r in fourier}
    ps = []
    for i, r in enumerate(parcelles.itertuples(), start=1):
        pid = r.parcelle_id
        q = bul.loc[pid]
        al = alertes_z[alertes_z.parcelle_id == pid]
        zf = al[al["type"] == "zone_faible"]
        g = r.geometry
        ancre = polylabel(g if g.geom_type == "Polygon" else max(g.geoms, key=lambda p: p.area), tolerance=0.5)
        bord = g.buffer(-RETRAIT_BORD_M, join_style="mitre")
        v = fr[pid]["verdict"]
        pl = plantes[pid]
        ps.append(dict(
            id=pid, i=i, culture=r.culture, culture_code=r.culture_code,
            surface_ha=round(float(q.surface_ha), 2), score=float(q.score), niveau=q.niveau,
            detail_score=None if pd.isna(q.detail_score) else q.detail_score,
            n_zones=int(len(zf)), n_zones_fortes=int((zf.gravite == "forte").sum()),
            zones_ha=None if pd.isna(q.vigueur_drone_zones_faibles_exg_ha) else round(float(q.vigueur_drone_zones_faibles_exg_ha), 3),
            plus_petite_zone_ha=None if zf.empty else round(float(zf.surface_ha.min()), 3),
            plus_grande_zone_ha=None if zf.empty else round(float(zf.surface_ha.max()), 3),
            sol_nu=bool(v.get("sol_nu")) and r.culture_code == rpg.CODE_BANANE,
            plantes=pl,
            ancre=[round(ancre.x - x0, 1), round(ancre.y - y0, 1)],
            anneaux=anneaux(g, x0, y0), bord=anneaux(bord, x0, y0, tol=0.2)))
    zs = [dict(id=z.id, parcelle=z.parcelle_id, surface_ha=round(float(z.surface_ha), 4), gravite=z.gravite,
               anneaux=anneaux(z.geometry, x0, y0, tol=0.15)) for z in zones.itertuples()]
    tot_ha = round(float(sum(p["surface_ha"] for p in ps)), 1)
    doc = dict(
        version=1,
        description="Visite 3D de 13 parcelles déclarées (RPG) de Basse-Pointe, Martinique : sol, parcelles et chiffres "
                    "réels ; bananiers et canne 3D d'illustration.",
        repere=dict(epsg=5490, nom="RGAF09 / UTM zone 20N", origine=[x0, y0],
                    note="x vers l'est, y vers le nord, en m depuis le centre de l'emprise"),
        emprise=dict(xmin=round(emp["xmin"] - x0, 2), xmax=round(emp["xmax"] - x0, 2),
                     ymin=round(emp["ymin"] - y0, 2), ymax=round(emp["ymax"] - y0, 2), marge_m=MARGE_M),
        tuiles=dict(tuiles, contexte=dict(tuiles["contexte"], xmin=round(tuiles["contexte"]["xmin"] - x0, 2),
                                          xmax=round(tuiles["contexte"]["xmax"] - x0, 2),
                                          ymin=round(tuiles["contexte"]["ymin"] - y0, 2),
                                          ymax=round(tuiles["contexte"]["ymax"] - y0, 2))),
        masque=masque,
        plantes=dict(unite_m=UNITE_POS, octets_par_plante=8,
                     format="uint16 x, uint16 y (unités de 2 cm depuis le coin sud-ouest de l'emprise), uint8 forme, "
                            "uint8 drapeaux (1 = zone moins verte), uint8 rotation (/256 tour), uint8 échelle (0,90 + 0,25 × v/255)",
                     bananiers=plantes["_bananiers"], canne=plantes["_canne"]),
        surface_ha=tot_ha, parcelles=ps, zones_faibles=zs,
        regle_score=regle_score(),
        tailles_utiles=tailles, rembourrage=REMBOURRAGE,
        source=dict(ortho="IGN, BD ORTHO® (Licence Ouverte Etalab 2.0), 20 cm",
                    parcelles="IGN, RPG (Licence Ouverte Etalab 2.0) : out/demo_martinique_rpg/parcelles_rpg_utm.geojson",
                    bulletin="out/demo_martinique_rpg/chaine/bulletin.csv",
                    alertes="out/demo_martinique_rpg/chaine/alertes.geojson"),
    )
    texte = json.dumps(doc, ensure_ascii=False, separators=(",", ":"), default=json_np)
    (d / "donnees.json").write_text(texte, encoding="utf-8")
    (d / "donnees.json.gz").write_bytes(gzip.compress(texte.encode("utf-8"), 9, mtime=0))
    print(f"donnees.json : {len(texte) / 1e3:.0f} ko ; {len(ps)} parcelles, {tot_ha} ha ; {len(zs)} zones moins vertes", flush=True)
    return doc


def etape_controle(img, emp, parcelles, plantes_xy, d):
    (d / "controle").mkdir(exist_ok=True)
    k = 5                                                         # 1 m par pixel
    a = np.ascontiguousarray(img[:, emp["l0"]:emp["l1"]:k, emp["c0"]:emp["c1"]:k].transpose(1, 2, 0))
    im = Image.fromarray(a).convert("RGB")
    dr = ImageDraw.Draw(im)
    r = RES * k
    px = lambda x, y: ((x - emp["xmin"]) / r, (emp["ymax"] - y) / r)  # noqa: E731
    for (B, C) in plantes_xy:
        for x, y in B[::3]:
            dr.point(px(x, y), fill=C)
    for p in parcelles.itertuples():
        g = p.geometry
        for poly in (g.geoms if g.geom_type == "MultiPolygon" else [g]):
            dr.line([px(*xy) for xy in poly.exterior.coords], fill=(255, 255, 255), width=2)
        c = g.representative_point()
        u, w = px(c.x, c.y)
        dr.text((u - 30, w - 8), f"{p.parcelle_id} {p.culture_code}", fill=(255, 255, 255), font=vm.police(16),
                stroke_width=3, stroke_fill=(0, 0, 0))
    im.save(d / "controle/zone.jpg", quality=86)


# ============================================================================================================ principal
def main():
    t = time.time()
    d = SORTIE
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(GLB, d / "bananiers.glb")
    img, tr, _ = vm.lire_ortho()
    print(f"ortho lue en {time.time() - t:.0f} s", flush=True)
    toutes = gpd.read_file(PARCELLES)
    assert toutes.crs.to_epsg() == 5490
    parcelles = toutes[toutes.parcelle_id.isin(ZONE)].sort_values("parcelle_id").reset_index(drop=True)
    assert len(parcelles) == len(ZONE), "parcelle manquante"
    bulletin = pd.read_csv(BULLETIN, encoding="utf-8")
    alertes = gpd.read_file(ALERTES).to_crs(5490)
    alertes_z = alertes[alertes.parcelle_id.isin(ZONE)].copy()
    zones = alertes_z[alertes_z["type"] == "zone_faible"].copy()
    zones["geometry"] = zones.geometry.make_valid()
    zones_par_p = {pid: shapely.union_all(g.geometry.values) for pid, g in zones.groupby("parcelle_id")}

    emp = emprise_zone(parcelles.geometry.values, tr)
    print(f"emprise : {emp['xmax'] - emp['xmin']:.1f} × {emp['ymax'] - emp['ymin']:.1f} m", flush=True)
    tuiles = etape_tuiles(img, tr, emp, d)
    masque = etape_masque(parcelles, emp, d)

    fourier = etape_fourier_zone(img, tr, parcelles, bulletin)
    regle_rpg(fourier, parcelles)
    geoms = dict(zip(parcelles.parcelle_id, parcelles.geometry))
    culture = dict(zip(parcelles.parcelle_id, parcelles.culture_code))
    plantes, ban, can = {}, [], []

    def planter(r):
        pid = r["parcelle_id"]
        if r["verdict"]["bananeraie"]:
            P = vm.generer_bananiers(geoms[pid], [f for f in r["fenetres"] if f.get("rangs")], zones_par_p.get(pid),
                                     pid, img, tr, r["fenetres"])
            return pid, "banane", P[:, :3], r["verdict"]["rangs"]
        if culture[pid] == CODE_CANNE:
            dir_deg, origine = direction_canne(r, geoms[pid])
            P = generer_canne(geoms[pid], dir_deg, zones_par_p.get(pid), pid, img, tr)
            return pid, "canne", P, dict(dir_rang_deg=round(dir_deg, 1), origine=origine, ecart_rangs_m=CANNE_RANG_M)
        return pid, None, np.zeros((0, 3)), None

    with ThreadPoolExecutor(FILS) as ex:
        res = list(ex.map(planter, fourier))
    for pid, sorte, P, info in res:
        plantes[pid] = dict(sorte=sorte, n=int(len(P)), n_zone=int(P[:, 2].sum()) if len(P) else 0, rangs=info)
        (ban if sorte == "banane" else can if sorte == "canne" else []).append(P)
    Ab, Ac = np.concatenate(ban), np.concatenate(can)
    bb, idx_b, Ab = ranger(Ab, emp, tuiles["fin"], 2026)
    bc, idx_c, Ac = ranger(Ac, emp, tuiles["fin"], 2027)
    (d / "bananiers.bin").write_bytes(bb)
    (d / "canne.bin").write_bytes(bc)
    plantes["_bananiers"] = dict(fichier="bananiers.bin", n=int(len(Ab)), n_zone=int(Ab[:, 2].sum()), index_par_tuile=idx_b,
                                 densite_ha=vm.DENSITE_HA)
    plantes["_canne"] = dict(fichier="canne.bin", n=int(len(Ac)), n_zone=int(Ac[:, 2].sum()), index_par_tuile=idx_c,
                             ecart_rangs_m=CANNE_RANG_M, pas_m=CANNE_PAS_M)
    print(f"bananiers d'illustration : {len(Ab)} ({int(Ab[:, 2].sum())} en zone moins verte) ; touffes de canne : {len(Ac)}",
          flush=True)
    for pid in ZONE:
        p = plantes[pid]
        print(f"  {pid} {culture[pid]} : {p['sorte']} {p['n']}", flush=True)
    etape_controle(img, emp, parcelles, [(Ab[:, :2], (255, 235, 59)), (Ac[:, :2], (0, 229, 255))], d)
    tailles = rembourrer(d)
    etape_donnees(parcelles, bulletin, alertes_z, zones, fourier, plantes, emp, tuiles, masque, d, tailles)
    print(f"terminé en {time.time() - t:.0f} s", flush=True)


if __name__ == "__main__":
    main()
