#!/usr/bin/env python3
"""Étape 1 : fuites entre membres. Une image de RÉGLAGE (ou de juge) a-t-elle été apprise par le v3, le v4 ou le v5 ?

Trois contrôles, par membre : (1) partie du groupe dans le découpage du membre (photo, image d'origine, groupe) ;
(2) nom de tuile présent dans l'entraînement de l'archive du membre ; (3) MD5 des tuiles de réglage et de juge
(archive v5) contre les tuiles d'entraînement de l'archive du membre. Aucun modèle n'est exécuté ici.
Les images de banana_tree_detection ne sont pas ouvertes ici (seuls les CSV de découpage sont lus pour elles).
"""
import hashlib
import sys
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
DR = RACINE / "data/drone"
DEC = {"v3": "decoupage_comptage", "v4": "decoupage_comptage_v4", "v5": "decoupage_comptage_v5"}
ARC = {"v3": "comptage_v3_5cm", "v4": "comptage_v4_5cm", "v5": "comptage_v5_5cm"}
REGLAGE = ["bv_b_val", "pp_100_metros", "jeunes_dji_0544", "rt_manuel_macias", "cocotier_0900_1299", "palmier_44000_16000", "btd"]
JUGES = ["segmento_est", "banano", "rt_carlos_vera_guevara", "cocotier_1300_plus", "palmier_44000_4000"]
sortie = RACINE / "out/comptage_v6/banc/fuites_membres.txt"
lignes = []


def dire(s=""):
    print(s)
    lignes.append(s)


d = {v: pd.read_csv(DR / p / "decoupage.csv", low_memory=False) for v, p in DEC.items()}
ref = d["v5"]
dire("1. Partie de chaque groupe de réglage et de juge dans le découpage de chaque membre (absent = jamais vu)")
for role, groupes in (("réglage", REGLAGE), ("juge", JUGES)):
    for g in groupes:
        r = ref[ref.groupe == g]
        mots = []
        for v, t in d.items():
            parties = set()
            for col in ("image", "origine", "photo"):
                parties |= set(t[t[col].isin(set(r[col]))].partie)
            parties |= set(t[t.groupe == g].partie)
            mots.append(f"{v} : {', '.join(sorted(parties)) or 'absent'}")
        dire(f"  {role:8s} {g:24s} ({len(r):3d} images) -> " + " ; ".join(mots))

dire("\n2 et 3. Tuiles de réglage et de juge (archive v5) contre les tuiles d'entraînement de chaque archive : nom, puis MD5")


def md5(p):
    return hashlib.md5(p.read_bytes()).hexdigest()


T5 = pd.read_csv(DR / ARC["v5"] / "tuiles.csv")
cibles = T5[(T5.ensemble != "train") & (T5.groupe != "btd")]          # btd : pas ouvert avant le découpage v6
empreintes = {n: md5(DR / ARC["v5"] / "images" / n) for n in cibles.image_path}
for sous in ("mm", "cg"):
    for p in (DR / ARC["v5"] / sous / "images").iterdir():
        empreintes[f"{sous}/{p.name}"] = md5(p)
inverse = {}
for n, h in empreintes.items():
    inverse.setdefault(h, []).append(n)
for v, a in ARC.items():
    T = pd.read_csv(DR / a / "tuiles.csv")
    train = T[T.ensemble == "train"]
    noms = set(train.image_path) & set(cibles.image_path)
    communs = []
    for n in train.image_path:
        h = md5(DR / a / "images" / n)
        if h in inverse:
            communs.append((n, inverse[h]))
    dire(f"  {v} : {len(train)} tuiles d'entraînement ; noms communs avec réglage/juges : {len(noms)} ; fichiers identiques (MD5) : {len(communs)}")
    for c in communs[:10]:
        dire(f"      {c}")
    # ensembles de validation du membre (choix de l'époque et du seuil) : pas un apprentissage, mais un choix
    val = sorted(set(T[T.ensemble.str.startswith("val")].groupe))
    dire(f"      groupes ayant servi au CHOIX de l'époque et du seuil du {v} : {', '.join(val)} + MM1-MM2")
sortie.parent.mkdir(parents=True, exist_ok=True)
sortie.write_text("\n".join(lignes), encoding="utf-8")
