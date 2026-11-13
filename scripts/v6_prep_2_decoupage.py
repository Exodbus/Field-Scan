#!/usr/bin/env python3
"""Découpage v6 du détecteur de comptage (plan de nuit du 12/11/2026, section 3.2). Aucun modèle n'est exécuté.

Découpage v6 = découpage v5 inchangé (toutes les lignes hors banana_tree_detection recopiées telles quelles)
+ banana_tree_detection (btd) reclassé, d'après data/drone/decoupage_comptage_v6/positions_btd.csv
(scripts/v6_prep_1_positions_btd.py) :

1. exclusions automatiques :
   - btd_annot_fausses : tuiles de 1280 px dont le JSON COCO donne une largeur de 1024 px. Elles portent les boîtes
     de la tuile de 1024 px du même numéro (boîtes sur la route, constaté sur les numéros 0 et 12) ; 16 tuiles ;
   - btd_1024 : les 20 tuiles de 1024 px, second pavage du même champ ; leur position dans la mosaïque n'est pas
     donnée par les noms et elles recouvrent le sol des tuiles de 1280 px (risque de fuite) ;
   - btd_non_placee : tuile de 1280 px hors de la composante principale du graphe d'appariements (position non sûre).
2. positions (scripts/v6_prep_1_positions_btd.py) : la mosaïque se lit en segments de lignes (numéros consécutifs,
   voisines de droite), placés de proche en proche en blocs ; le bloc 0-284 contient 264 tuiles, les tuiles 286-435
   forment des blocs sans position mesurée par rapport à lui. Coupe géographique dans l'ordre des segments (ordre de
   lecture de haut en bas : numéros croissants) : la bande tampon est un segment entier, choisi pour rendre les deux
   côtés les plus égaux en nombre de tuiles valides (à égalité, le premier) ; le côté au plus grand nombre de tuiles
   va à l'entraînement (btd_train), l'autre en validation (btd_val). Dans un même bloc, deux segments séparés par la
   bande sont distants d'au moins 2 x 896 - 1280 = 512 px (environ 16 m) ; entre blocs sans position relative,
   l'absence de recouvrement est vérifiée sur les images (scripts/v6_prep_3_fuites.py, toutes les paires).
3. garde-fou (plan de nuit 10 h) : si les positions ne sont pas retrouvées (moins de la moitié des tuiles placées),
   toutes les tuiles btd valides vont en validation et rien en entraînement.

Sorties : data/drone/decoupage_comptage_v6/decoupage.csv, groupes.csv, rapport.txt, grille_btd.txt.

Exemple :
    python scripts/v6_prep_2_decoupage.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
V5 = RACINE / "data/drone/decoupage_comptage_v5/decoupage.csv"
OUT = RACINE / "data/drone/decoupage_comptage_v6"
COLS_N = ["n_Banana", "n_Cacao", "n_Banana-plant", "n_rejet", "n_Oil Palm Tree", "n_coconut_tree", "n_0",
          "n_platano", "n_banana-tree", "n_Bananas", "n_Others", "n_banana"]


def main():
    rapport = []
    dec5 = pd.read_csv(V5)
    btd5 = dec5[dec5.groupe == "btd"]
    reste = dec5[dec5.groupe != "btd"].copy()
    pos = pd.read_csv(OUT / "positions_btd.csv")
    rapport.append(f"Découpage v6 écrit par scripts/v6_prep_2_decoupage.py, avant toute mesure de modèle.")
    rapport.append(f"v5 : {len(dec5)} lignes, dont {len(btd5)} banana_tree_detection (groupe btd, partie test) ; "
                   f"{len(reste)} lignes recopiées sans changement.")
    rapport.append(f"banana_tree_detection.zip : {len(pos)} images ({int((pos.largeur == 1280).sum())} de 1280 px, "
                   f"{int((pos.largeur == 1024).sum())} de 1024 px), 416 MD5 distincts, numéros 0 à {pos.numero.max()}.")

    fausse = (pos.largeur == 1280) & (pos.largeur_coco != pos.largeur)
    p1024 = pos.largeur == 1024
    placee = pos.segment.notna()
    pos["groupe"] = np.where(fausse, "btd_annot_fausses", np.where(p1024, "btd_1024",
                             np.where(~placee, "btd_non_placee", "")))
    valides = pos[pos.groupe == ""]
    n1280 = int(((pos.largeur == 1280) & ~fausse).sum())
    trouve = len(valides) >= 0.5 * n1280
    if trouve:
        par_seg = valides.groupby("segment").size()
        segs = sorted(pos[placee].segment.unique())
        meilleur = None
        for b in segs:
            haut = int(par_seg[par_seg.index < b].sum())
            bas = int(par_seg[par_seg.index > b].sum())
            if meilleur is None or abs(haut - bas) < meilleur[0]:
                meilleur = (abs(haut - bas), b, haut, bas)
        _, b, haut, bas = meilleur
        train_haut = haut >= bas
        def role(s_):
            if s_ == b:
                return "btd_tampon"
            return "btd_train" if (s_ < b) == train_haut else "btd_val"
        pos.loc[valides.index, "groupe"] = [role(s_) for s_ in valides.segment]
        nums = pos[pos.segment == b].numero
        regle = (f"segments ordonnés par numéro ; bande tampon = segment {int(nums.min())}-{int(nums.max())} ; "
                 f"{haut} tuiles valides avant, {bas} après ; entraînement = "
                 f"{'numéros avant la bande' if train_haut else 'numéros après la bande'}, validation = l'autre côté")
    else:
        pos.loc[valides.index, "groupe"] = "btd_val"
        regle = "positions non retrouvées (garde-fou) : toutes les tuiles valides en validation, rien en entraînement"
    rapport.append("Règle appliquée : " + regle)

    partie = {"btd_train": "train", "btd_val": "val", "btd_tampon": "exclu", "btd_annot_fausses": "exclu",
              "btd_1024": "exclu", "btd_non_placee": "exclu"}
    lignes = []
    for r in pos.itertuples():
        stem = Path(r.image).name.split("_png.rf.")[0].lower()
        origine = stem if r.largeur == 1280 else stem + "_p1024"      # second pavage : image différente, même numéro
        d = {c: 0 for c in COLS_N}
        d["n_banana-tree"] = int(r.boites)
        lignes.append(dict(zip="banana_tree_detection.zip", partie_roboflow=r.image.split("/")[0], image=r.image,
                           origine=origine, photo=origine, largeur=float(r.largeur), hauteur=float(r.hauteur),
                           groupe=r.groupe, source="banana_tree_detection",
                           annotations="banana_tree_detection (Roboflow, boîtes)", partie=partie[r.groupe],
                           bloc_mosaique=r.bloc, segment_mosaique=r.segment, x_mosaique_px=r.x_px, y_mosaique_px=r.y_px, **d))
    btd6 = pd.DataFrame(lignes)
    dec6 = pd.concat([reste, btd6], ignore_index=True)[list(dec5.columns) + ["bloc_mosaique", "segment_mosaique", "x_mosaique_px", "y_mosaique_px"]]

    # contrôles de base
    assert dec6.image.is_unique
    for col in ("photo", "origine"):
        nb = dec6[dec6.partie.isin(["train", "val", "test"])].groupby(col).partie.nunique()
        assert (nb <= 1).all(), f"{col} dans plusieurs parties"
    dec6.to_csv(OUT / "decoupage.csv", index=False)
    grp = dec6.groupby(["partie", "groupe"]).agg(images=("image", "size"), photos=("photo", "nunique"),
                                                **{c: (c, "sum") for c in COLS_N}).reset_index()
    grp.to_csv(OUT / "groupes.csv", index=False)

    rapport.append("")
    rapport.append("banana_tree_detection en v6 (tuiles, boîtes banana-tree = plants annotés) :")
    for g in ["btd_train", "btd_tampon", "btd_val", "btd_annot_fausses", "btd_1024", "btd_non_placee"]:
        s = btd6[btd6.groupe == g]
        rapport.append(f"  {g:18s} partie {partie[g]:5s} : {len(s):4d} tuiles, {int(s['n_banana-tree'].sum()):6d} plants")
    rapport.append(f"  (v5, test : {len(btd5)} tuiles, {int(btd5['n_banana-tree'].sum())} plants, dont 4 tuiles aux "
                   f"boîtes fausses)")
    rapport.append("")
    rapport.append("Segments de lignes (numéros) et rôle : E entraînement, V validation, T tampon, x annotations fausses")
    for sg, g in pos[placee].groupby("segment"):
        code = "".join({"btd_train": "E", "btd_val": "V", "btd_tampon": "T", "btd_annot_fausses": "x"}.get(v, "?")
                       for v in g.sort_values("numero").groupe)
        rapport.append(f"  bloc {int(g.bloc.iloc[0])} segment {int(g.numero.min()):3d}-{int(g.numero.max()):3d} "
                       f"(y = {g.y_px.iloc[0]:6.0f} px) : {code}")
    rapport.append("")
    rapport.append("Toutes les parties (v6) :")
    rapport.append(grp[["partie", "groupe", "images", "photos", "n_banana-tree"]].to_string(index=False))
    rapport.append("")
    rapport.append("Contrôle de base : image, photo et origine chacune dans une seule partie (train/val/test) : OK.")
    rapport.append("Contrôle de fuite complet (MD5, recouvrement) : voir fuites.txt (scripts/v6_prep_3_fuites.py).")
    (OUT / "rapport.txt").write_text("\n".join(rapport) + "\n", encoding="utf-8")
    print("\n".join(rapport))


if __name__ == "__main__":
    main()
