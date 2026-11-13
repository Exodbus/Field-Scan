#!/usr/bin/env python3
"""Élève de E-017 (D-009) : entraînement, inférence et seuil non supervisé (performance-engineer).

Sous-commandes :
    entrainer --pseudo CSV --reserve CSV --epoques N --sortie DIR [--decoupe 384] [--lot 8] [--threads 8]
        Entraîne sur les pseudo-étiquettes (image_path,x,y,z) des images de la réserve (colonne image_path),
        graine 2026, dernière époque retenue : DIR/dernier.pt, DIR/historique.csv, DIR/entrainement.json.
    predire --modele PT --images CSV --sortie CSV [--plancher 0.05]
        Détections image_path,x,y,score (format de scripts/math_evaluer.py), NMS 1,0 m.
        --modele imagenet : réseau non entraîné (initialisation ImageNet, tête au biais −2,19), pour les essais.
    seuil --detections CSV --pseudo CSV --reserve CSV [--sortie JSON]
        Seuil tel que le nombre de détections de l'élève sur la réserve égale celui du professeur (z ≥ 2,238).
    accord --detections CSV --pseudo CSV --reserve CSV --seuil S [--sortie JSON]
        Part des positifs du professeur retrouvés à 1 m par l'élève (au seuil S), et inversement.
    essai-temps --images-groupe bv_b_train --n 30 --sortie DIR
        Mesure du temps par époque et par image, et de la mémoire, sur des étiquettes factices tirées au hasard.

Lancement : PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/math_eleve.py <sous-commande> …
"""
import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

from comptage_math import eleve as E  # noqa: E402


def memoire_pic_mo() -> float:
    """Pic de mémoire de travail du processus (Windows : peak_wset), en Mo."""
    try:
        import psutil
        mi = psutil.Process(os.getpid()).memory_info()
        return round(getattr(mi, "peak_wset", mi.rss) / 2 ** 20, 1)
    except Exception:
        return float("nan")


def machine() -> dict:
    return dict(processeur=platform.processor(), coeurs=os.cpu_count(), torch=torch.__version__,
                python=platform.python_version(), systeme=platform.platform())


def cmd_entrainer(a):
    images = E.lire_liste(a.reserve)
    pseudo = E.lire_pseudo(a.pseudo)
    disques, resolutions = E.lire_disques(a.reserve)
    sortie = Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    fic = open(sortie / "journal.txt", "a", encoding="utf-8")

    def journal(m):
        print(m, flush=True)
        fic.write(m + "\n")
        fic.flush()

    journal(f"réserve : {len(images)} images, {sum(len(v[0]) for v in pseudo.values())} positifs, "
            f"{sum(len(v[1]) for v in pseudo.values())} ignorés (toutes images du CSV)")
    journal(f"disques comptés : {len(disques)} / {len(images)} images ; résolutions de la réserve : {len(resolutions)}")
    r = E.entrainer(images, pseudo, a.epoques, sortie, decoupe=a.decoupe, lot=a.lot, threads=a.threads,
                    journal=journal, disques=disques, resolutions=resolutions)
    r.update(reglages=dict(pseudo=str(a.pseudo), reserve=str(a.reserve), epoques=a.epoques, decoupe=a.decoupe,
                           lot=a.lot, threads=a.threads, graine=E.GRAINE, sigma_m=E.SIGMA_M,
                           rayon_ignore_m=E.RAYON_IGNORE_M, z_positif=E.Z_POSITIF, z_ignore=E.Z_IGNORE,
                           retenu="dernière époque"),
             memoire_pic_mo=memoire_pic_mo(), machine=machine())
    (sortie / "entrainement.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    journal(f"fin : {r['total_s'] / 3600:.2f} h, mémoire de pointe {r['memoire_pic_mo']} Mo")


def cmd_predire(a):
    images = E.lire_liste(a.images)
    modele = E.DetecteurCentres(imagenet=True).eval() if a.modele == "imagenet" else E.charger(a.modele)
    t0 = time.perf_counter()
    d = E.predire(modele, images, plancher=a.plancher, lot=a.lot, threads=a.threads)
    dt = time.perf_counter() - t0
    Path(a.sortie).parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(a.sortie, index=False)
    print(f"{len(d)} détections sur {len(images)} images, {dt:.1f} s ({dt / max(len(images), 1):.3f} s par image) "
          f"-> {a.sortie}", flush=True)


def cmd_seuil(a):
    det = pd.read_csv(a.detections)
    disques, _ = E.lire_disques(a.reserve)
    n0 = len(det)
    det = E.dans_disques(det, disques)                    # D-010 : détections de l'élève dans le disque compté
    r = E.seuil_non_supervise(det, a.pseudo, E.lire_liste(a.reserve))
    p = pd.read_csv(a.pseudo)
    p = p[(p.z >= E.Z_POSITIF) & p.image_path.isin(set(E.lire_liste(a.reserve)))]
    r.update(detections_hors_disque_ecartees=int(n0 - len(det)),
             positifs_professeur_hors_disque=int(len(p) - len(E.dans_disques(p, disques))),
             detections=str(a.detections), pseudo=str(a.pseudo), reserve=str(a.reserve))
    print(json.dumps(r, ensure_ascii=False), flush=True)
    if a.sortie:
        Path(a.sortie).parent.mkdir(parents=True, exist_ok=True)
        Path(a.sortie).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_accord(a):
    """Désaccord élève-professeur sur une liste : appariement un à un (Hongrois) à moins de 1 m, dans le disque compté.

    Ce n'est pas une évaluation : le professeur n'est pas une référence (CLAUDE.md)."""
    from scipy.optimize import linear_sum_assignment
    from scipy.spatial.distance import cdist
    images = E.lire_liste(a.reserve)
    ens = set(images)
    disques, res = E.lire_disques(a.reserve)
    det = pd.read_csv(a.detections)
    det = E.dans_disques(det[det.image_path.isin(ens) & (det.score >= a.seuil)], disques)
    p = pd.read_csv(a.pseudo)
    p = E.dans_disques(p[p.image_path.isin(ens) & (p.z >= E.Z_POSITIF)], disques)
    gd, gp = dict(list(det.groupby("image_path"))), dict(list(p.groupby("image_path")))
    n_app = 0
    for n in images:
        if n not in gd or n not in gp:
            continue
        r_px = 100.0 / res.get(n, E.CM_DEFAUT)
        d = cdist(gd[n][["x", "y"]].to_numpy(float), gp[n][["x", "y"]].to_numpy(float))
        i, j = linear_sum_assignment(np.where(d < r_px, d, 1e6))
        n_app += int((d[i, j] < r_px).sum())
    r = dict(seuil=a.seuil, n_eleve=len(det), n_professeur=len(p), apparies_1m=n_app,
             part_professeur_retrouvee=round(n_app / max(len(p), 1), 4),
             part_eleve_confirmee=round(n_app / max(len(det), 1), 4), n_images=len(images))
    print(json.dumps(r, ensure_ascii=False), flush=True)
    if a.sortie:
        Path(a.sortie).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_essai_temps(a):
    """Étiquettes factices (points uniformes au hasard) : mesure de coût seulement, aucun résultat de qualité."""
    sortie = Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    liste = pd.read_csv(E.RESOLUTIONS_CSV[0])
    noms = sorted(liste.loc[liste.groupe == a.images_groupe, "image_path"])
    rng = np.random.default_rng(E.GRAINE)
    noms = sorted(rng.choice(noms, size=min(a.n, len(noms)), replace=False).tolist())
    lignes = []
    for n in noms:                               # ~60 points par image (ordre de grandeur des tuiles bv), z dans [1 ; 4]
        k = 60
        for x, y, z in zip(rng.uniform(0, 512, k), rng.uniform(0, 512, k), rng.uniform(1.0, 4.0, k)):
            lignes.append((n, round(x, 1), round(y, 1), round(z, 3)))
    pseudo_csv, reserve_csv = sortie / "pseudo_factice.csv", sortie / "reserve_factice.csv"
    pd.DataFrame(lignes, columns=["image_path", "x", "y", "z"]).to_csv(pseudo_csv, index=False)
    pd.DataFrame({"image_path": noms}).to_csv(reserve_csv, index=False)
    pseudo = E.lire_pseudo(pseudo_csv)
    res = []
    for decoupe, lot in [tuple(map(int, c.split("x"))) for c in a.configs]:
        t0 = time.perf_counter()
        r = E.entrainer(noms, pseudo, a.epoques, sortie / f"d{decoupe}_l{lot}", decoupe=decoupe, lot=lot,
                        threads=a.threads)
        h = r["historique"]
        # première époque exclue de la moyenne si possible (échauffement des noyaux)
        regime = h[1:] if len(h) > 1 else h
        s_img = float(np.mean([e["duree_s"] / e["images"] for e in regime]))
        res.append(dict(decoupe=decoupe, lot=lot, threads=a.threads, epoques=a.epoques, images_par_epoque=h[0]["images"],
                        s_par_image=round(s_img, 4), s_par_epoque=[e["duree_s"] for e in h],
                        donnees_s=[e["donnees_s"] for e in h], chargement_s=round(r["chargement_s"], 2),
                        total_s=round(time.perf_counter() - t0, 1), memoire_pic_mo=memoire_pic_mo()))
        print(json.dumps(res[-1], ensure_ascii=False), flush=True)
    # inférence : réseau du dernier essai, image entière 512 px
    modele = E.charger(sortie / f"d{decoupe}_l{lot}" / "dernier.pt")
    t0 = time.perf_counter()
    det = E.predire(modele, noms, threads=a.threads)
    t_inf = (time.perf_counter() - t0) / len(noms)
    bilan = dict(essais=res, inference_s_par_image=round(t_inf, 4), n_detections_inference=len(det),
                 memoire_pic_mo=memoire_pic_mo(), machine=machine())
    (sortie / "essai_temps.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(bilan, ensure_ascii=False), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    e = s.add_parser("entrainer")
    e.add_argument("--pseudo", required=True)
    e.add_argument("--reserve", required=True)
    e.add_argument("--epoques", type=int, required=True)
    e.add_argument("--sortie", required=True)
    e.add_argument("--decoupe", type=int, default=384)
    e.add_argument("--lot", type=int, default=8)
    e.add_argument("--threads", type=int, default=8)
    e.set_defaults(f=cmd_entrainer)
    q = s.add_parser("predire")
    q.add_argument("--modele", required=True)
    q.add_argument("--images", required=True)
    q.add_argument("--sortie", required=True)
    q.add_argument("--plancher", type=float, default=0.05)
    q.add_argument("--lot", type=int, default=8)
    q.add_argument("--threads", type=int, default=8)
    q.set_defaults(f=cmd_predire)
    t = s.add_parser("seuil")
    t.add_argument("--detections", required=True)
    t.add_argument("--pseudo", required=True)
    t.add_argument("--reserve", required=True)
    t.add_argument("--sortie")
    t.set_defaults(f=cmd_seuil)
    c = s.add_parser("accord")
    c.add_argument("--detections", required=True)
    c.add_argument("--pseudo", required=True)
    c.add_argument("--reserve", required=True)
    c.add_argument("--seuil", type=float, required=True)
    c.add_argument("--sortie")
    c.set_defaults(f=cmd_accord)
    m = s.add_parser("essai-temps")
    m.add_argument("--images-groupe", default="bv_b_train")
    m.add_argument("--n", type=int, default=30)
    m.add_argument("--epoques", type=int, default=3)
    m.add_argument("--configs", nargs="+", default=["512x8", "384x8"])
    m.add_argument("--threads", type=int, default=8)
    m.add_argument("--sortie", default=str(RACINE / "out/comptage_math/performance-engineer/E-017/essai_temps"))
    m.set_defaults(f=cmd_essai_temps)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
