#!/usr/bin/env python3
"""M-banc, nuit du 13/11 : temps par photo de chaque lecteur de F1, sur la même machine, mêmes photos, même nombre de
fils (2 : un autre calcul de M-banc tourne à 3 fils à côté ; machine partagée avec les autres agents).

Échantillon fixé avant la mesure : 6 photos par jeu de réglage (graine 2026), soit 30 photos. Pour chaque photo, dans
cet ordre : aiguilleur, v2, soupe, v10b (entière, 384 px, 4 vues), morceaux 2 x 2 (4 morceaux, v10b) ; chaque lecteur
lu photo par photo (lot de 1) pour que les conditions soient les mêmes. Les modèles sont chargés avant (chargement non
compté, comme dans une chaîne déjà lancée). Sortie : out/maladies/nuit_1311/banc/temps.json (+ temps.log).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_banc_temps.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import torch  # noqa: E402

torch.set_num_threads(2)
from fieldscan.modules import maladies  # noqa: E402
import m13_banc_commun as C  # noqa: E402


def chemin_absolu(c):
    c = str(c)
    return c if Path(c).is_absolute() else C.B.fichier(c)


def main():
    jeux = C.charger(roamer=False)
    rng = np.random.default_rng(2026)
    ech = []
    for j in C.JEUX5:
        for i in rng.choice(len(jeux[j]["chemin"]), 6, replace=False):
            ech.append((j, int(i), chemin_absolu(jeux[j]["chemin"][i])))
    agu = maladies.charger_aiguilleur(RACINE / "modeles/maladies_aiguilleur/aiguilleur.npz")
    m = {"v2": maladies.charger_convnext(RACINE / "modeles/maladies_binome/maladies_v2/poids"),
         "soupe": maladies.charger_convnext(RACINE / "modeles/maladies_soupe_v2_v8/poids"),
         "v10b": maladies.charger_convnext(RACINE / "modeles/maladies_binome/v10b")}
    T = {k: [] for k in ("aiguilleur", "v2", "soupe", "v10b", "morceaux_2x2")}
    ecart = []
    for k, (j, i, c) in enumerate(ech):
        t = time.perf_counter(); maladies.p_loin([c], agu); T["aiguilleur"].append(time.perf_counter() - t)
        for nom in ("v2", "soupe", "v10b"):
            t = time.perf_counter(); p = maladies.predire_convnext([c], m[nom]); T[nom].append(time.perf_counter() - t)
        ecart.append(float(np.abs(p[0] - jeux[j]["P10"][i]).max()))   # contrôle : même v10b que le cache
        t = time.perf_counter(); maladies.predire_convnext(maladies.morceaux_2x2(c), m["v10b"]); T["morceaux_2x2"].append(time.perf_counter() - t)
        print(time.strftime("%H:%M:%S"), k + 1, j, " ".join(f"{a} {v[-1]:.2f}" for a, v in T.items()), flush=True)
    res = {a: dict(moyenne=float(np.mean(v)), mediane=float(np.median(v)), n=len(v)) for a, v in T.items()}
    res["ecart_max_v10b_cache"] = max(ecart)
    res["echantillon"] = [(j, i) for j, i, _ in ech]
    res["fils"] = 2
    (C.SORTIE / "temps.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({a: res[a] for a in T}, ensure_ascii=False))
    print("écart max v10b / cache :", max(ecart))


if __name__ == "__main__":
    main()
