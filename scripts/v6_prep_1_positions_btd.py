#!/usr/bin/env python3
"""Retrouve la position des tuiles de banana_tree_detection dans leur orthomosaïque (découpage v6, plan de nuit 3.2).

Constat : 396 tuiles de 1280 px (numéros 0 à 435) et 20 tuiles de 1024 px (numéros 0 à 19, second pavage). Le numéro
ne donne pas la position (lignes de longueur variable). Méthode (aucun modèle) :
1. décalage entre tuiles de numéros proches (écarts 1 et 7 à 22) par corrélation de phase sur les images réduites au
   quart, vérifiée par la corrélation sur la zone commune (appariements_btd.csv, réutilisé s'il existe) ;
2. segments de lignes : suites de numéros consécutifs dont chaque tuile est la voisine de droite de la précédente
   (décalage (896, 0) px, corrélation >= 0,6) ;
3. placement relatif des segments : chaque lien fiable entre deux segments (sur la grille au pas de 896 px avec
   corrélation >= 0,6, ou hors grille avec corrélation >= 0,9) donne un vote pour le décalage (en px) entre leurs
   origines ; un décalage est retenu s'il réunit au moins 2 votes à 16 px près et plus de la moitié des votes ;
4. blocs : segments reliés de proche en proche ; coordonnées en pixels dans le repère du bloc (x_px, y_px).
   Deux blocs non reliés n'ont pas de position relative connue.

Sortie : data/drone/decoupage_comptage_v6/positions_btd.csv (une ligne par image du zip), appariements_btd.csv,
liens_segments_btd.csv.

Exemple :
    python scripts/v6_prep_1_positions_btd.py
"""
import collections
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
ZIP = RACINE / "data/roboflow/banana_tree_detection.zip"
OUT = RACINE / "data/drone/decoupage_comptage_v6"
PAS = 896                 # pas du pavage de 1280 px, mesuré (recouvrement de 384 px)
REDUC = 4                 # corrélation sur les images réduites au quart
CORR_MIN = 0.6            # corrélation minimale (décalage sur la grille)
CORR_HORS_GRILLE = 0.9    # corrélation minimale (décalage hors grille)
TOL = 48                  # écart toléré (px) entre le décalage mesuré et un multiple du pas
ECARTS = [1] + list(range(7, 23))   # écarts de numéro essayés (voisine de droite, voisines de la ligne du dessous)


def decalage(a, b):
    """(corr, dx, dy) tel que b(x, y) ~ a(x + dx, y + dy) : corrélation de phase, vérifiée sur la zone commune."""
    T = a.shape[0]
    fa, fb = np.fft.fft2(a - a.mean()), np.fft.fft2(b - b.mean())
    r = fa * np.conj(fb)
    r /= np.abs(r) + 1e-6
    c = np.real(np.fft.ifft2(r))
    best = (-1.0, 0, 0)
    for idx in np.argsort(c.ravel())[-5:]:
        y, x = divmod(int(idx), T)
        for dx in (x, x - T):
            for dy in (y, y - T):
                x0, x1, y0, y1 = max(dx, 0), min(T + dx, T), max(dy, 0), min(T + dy, T)
                if x1 - x0 < 16 or y1 - y0 < 16:
                    continue
                u, v = a[y0:y1, x0:x1], b[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
                if u.std() < 2 or v.std() < 2:
                    continue
                cc = float(np.corrcoef(u.ravel(), v.ravel())[0, 1])
                if cc > best[0]:
                    best = (cc, dx, dy)
    return best


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    z = zipfile.ZipFile(ZIP)
    lignes, G = [], {}
    fichier_app = OUT / "appariements_btd.csv"
    for part in ["train", "valid", "test"]:
        d = json.loads(z.read(f"{part}/_annotations.coco.json"))
        nb = collections.Counter(a["image_id"] for a in d["annotations"])
        for im in d["images"]:
            nom = f"{part}/{im['file_name']}"
            k = int(re.search(r"_3857_(\d+)_png", nom).group(1))
            img = Image.open(io.BytesIO(z.read(nom))).convert("L")
            lignes.append(dict(image=nom, numero=k, largeur=img.width, hauteur=img.height, largeur_coco=im["width"],
                               boites=nb[im["id"]]))
            if img.width == 1280 and not fichier_app.exists():
                G[k] = np.asarray(img.resize((1280 // REDUC, 1280 // REDUC), Image.BILINEAR), dtype=np.float32)
    t = pd.DataFrame(lignes)
    print(f"{len(t)} images ; {int((t.largeur == 1280).sum())} de 1280 px, {int((t.largeur == 1024).sum())} de 1024 px", flush=True)
    t1280 = t[t.largeur == 1280]
    assert t1280.numero.is_unique
    ks = sorted(t1280.numero)

    # 1. appariements entre tuiles de numéros proches
    if fichier_app.exists():
        A = pd.read_csv(fichier_app)
        print(f"appariements relus : {fichier_app.name}")
    else:
        app = []
        for k in ks:
            for e in ECARTS:
                if k + e in G:
                    cc, dx, dy = decalage(G[k], G[k + e])
                    dx, dy = dx * REDUC, dy * REDUC
                    i, j = round(dx / PAS), round(dy / PAS)
                    ok = cc >= CORR_MIN and abs(dx - i * PAS) <= TOL and abs(dy - j * PAS) <= TOL and (i, j) != (0, 0) \
                        and abs(i) <= 1 and abs(j) <= 1
                    app.append(dict(a=k, b=k + e, corr=round(cc, 3), dx=dx, dy=dy, di=i, dj=j, garde=ok))
        A = pd.DataFrame(app)
        A.to_csv(fichier_app, index=False)
    print(f"{len(A)} paires essayées ; sur la grille et corr >= {CORR_MIN} : {int(A.garde.sum())} ; "
          f"hors grille et corr >= {CORR_HORS_GRILLE} : {int(((~A.garde) & (A['corr'] >= CORR_HORS_GRILLE)).sum())}")

    # 2. segments de lignes
    droite = set(map(tuple, A[A.garde & (A.b == A.a + 1) & (A.di == 1) & (A.dj == 0)][["a", "b"]].to_numpy()))
    segs, cur = [], [ks[0]]
    for k in ks[1:]:
        if (cur[-1], k) in droite:
            cur.append(k)
        else:
            segs.append(cur)
            cur = [k]
    segs.append(cur)
    seg_de = {k: i for i, s in enumerate(segs) for k in s}
    rang = {k: s.index(k) for s in segs for k in s}
    print(f"{len(segs)} segments de lignes : " + ", ".join(f"{s[0]}-{s[-1]}" for s in segs))

    # 3. votes entre segments
    fiables = A[(A.garde) | (A["corr"] >= CORR_HORS_GRILLE)]
    votes = collections.defaultdict(list)
    for r in fiables.itertuples():
        sa, sb = seg_de.get(r.a), seg_de.get(r.b)
        if sa is None or sb is None or sa == sb:
            continue
        votes[(sa, sb)].append((rang[r.a] * PAS + r.dx - rang[r.b] * PAS, r.dy))
    liens, lignes_l = {}, []
    for (sa, sb), v in sorted(votes.items()):
        v = np.array(v, dtype=float)
        mediane = np.median(v, axis=0)
        accord = (np.abs(v - mediane) <= 16).all(axis=1)
        ok = accord.sum() >= 2 and accord.sum() > len(v) / 2
        off = v[accord].mean(axis=0) if ok else mediane
        lignes_l.append(dict(segment_a=f"{segs[sa][0]}-{segs[sa][-1]}", segment_b=f"{segs[sb][0]}-{segs[sb][-1]}",
                             votes=len(v), concordants=int(accord.sum()), dx=round(off[0], 1), dy=round(off[1], 1),
                             retenu=bool(ok)))
        if ok:
            liens[(sa, sb)] = off
    pd.DataFrame(lignes_l).to_csv(OUT / "liens_segments_btd.csv", index=False)

    # 4. blocs et coordonnées
    vois = collections.defaultdict(list)
    for (sa, sb), off in liens.items():
        vois[sa].append((sb, off))
        vois[sb].append((sa, -off))
    origine, bloc, ecarts = {}, {}, []
    for depart in range(len(segs)):
        if depart in origine:
            continue
        nb_ = len(set(bloc.values()))
        origine[depart], bloc[depart] = np.zeros(2), nb_
        file = collections.deque([depart])
        while file:
            u = file.popleft()
            for v, off in vois[u]:
                p = origine[u] + off
                if v not in origine:
                    origine[v], bloc[v] = p, nb_
                    file.append(v)
                else:
                    ecarts.append(float(np.abs(origine[v] - p).max()))
    print(f"liens retenus : {len(liens)} ; écart maximal sur les cycles : {max(ecarts, default=0):.0f} px")
    blocs = collections.defaultdict(list)
    for s, b in bloc.items():
        blocs[b].append(s)
    for b, ss in blocs.items():
        o = np.array([origine[s] for s in ss])
        x0, y0 = o[:, 0].min(), o[:, 1].min()
        for s in ss:
            origine[s] = origine[s] - (x0, y0)
        print(f"bloc {b} : segments {segs[min(ss)][0]} à {segs[max(ss)][-1]}, {sum(len(segs[s]) for s in ss)} tuiles")

    def info(k, w):
        if w != 1280:
            return (np.nan,) * 5
        s = seg_de[k]
        return (s, bloc[s], origine[s][0] + rang[k] * PAS, origine[s][1], rang[k])
    cols = [info(k, w) for k, w in zip(t.numero, t.largeur)]
    t["segment"], t["bloc"], t["x_px"], t["y_px"], t["rang_dans_segment"] = zip(*cols)
    t.sort_values(["largeur", "numero"]).to_csv(OUT / "positions_btd.csv", index=False)
    # contrôle : deux tuiles d'un même bloc ne doivent pas occuper la même place
    p = t[t.largeur == 1280]
    doubles = p.groupby(["bloc", (p.x_px / 64).round(), (p.y_px / 64).round()]).size()
    print(f"places occupées par plusieurs tuiles d'un même bloc : {int((doubles > 1).sum())}")


if __name__ == "__main__":
    main()
