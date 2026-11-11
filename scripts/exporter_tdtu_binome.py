#!/usr/bin/env python3
"""Test commun sur TDTU avec le binôme (10 novembre 2026) : photos, étiquettes et réponses du module maladies, photo par photo.

Écrit dans out/partage_binome/ :
- tdtu_1636.zip : les 1 636 photos TDTU de data/feuilles_v3_ajouts (photos distinctes après regroupement des quasi-doublons
  et retrait des étiquettes contradictoires, scripts/preparer_ajouts_v3.py) et etiquettes.csv ;
- reponses_module_tdtu.csv : réponse du module de la chaîne (aiguilleur ; soupe + politique b de près ; v2 + politique b de
  loin), calculée avec les mêmes probabilités que le module (contrôle d'intégration du 10 novembre : réussi).
Les empreintes SHA-256 des deux fichiers sont affichées, pour figer nos réponses avant toute note de la v10b.

Étiquettes TDTU : saine = « Healthy » ; black_sigatoka = « Black Segatoka » seul ; autre_maladie = « Xanthomonas wilt » ou
« Bacterial wilt » seuls (flétrissements).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/exporter_tdtu_binome.py
"""
import hashlib, io, json, zipfile
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
DOS = RACINE / "out/maladies/cinq_classes"
SORTIE = RACINE / "out/partage_binome"
ALERTE = {"cercosporiose_noire", "fusariose", "malade_non_identifiee", "cordana", "pestalotiopsis"}
SOUPE = json.loads((RACINE / "modeles/maladies_soupe_v2_v8/poids/seuils.json").read_text(encoding="utf-8"))
V2 = json.loads((RACINE / "modeles/maladies_binome/maladies_v2/poids/seuils.json").read_text(encoding="utf-8"))


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


v2, so = pd.read_csv(DOS / "predictions_v2_tdtu.csv"), pd.read_csv(DOS / "predictions_soupe_tdtu.csv")
pl = pd.read_csv(DOS / "p_loin_tdtu.csv")
assert list(v2.chemin) == list(so.chemin) == list(pl.chemin) and len(v2) == 1636
proche = so.reponse.values.astype(object)
proche[(proche == "je_ne_sais_pas") & (1 - so.p_saine.values >= SOUPE["seuil_alerte"])] = "malade_non_identifiee"
loin = v2.reponse.values.astype(object)
loin[(loin == "je_ne_sais_pas") & (1 - v2.p_saine.values >= V2["seuil_alerte"])] = "malade_non_identifiee"
est_loin = pl.p_loin.values >= 0.5

ref = pd.read_csv(RACINE / "data/feuilles_v3_ajouts/images.csv")
ref = ref[ref.jeu.eq("tdtu")]
ref = ref.set_index(ref.image.str.removeprefix("ajouts_v3/").rename(None))
cle = v2.chemin.str.removeprefix("data/feuilles_v3_ajouts/")
assert cle.isin(ref.index).all()
r = ref.loc[cle]

nom = [Path(c).name for c in v2.chemin]
etiquettes = pd.DataFrame(dict(photo=nom, classe=v2.classe_vraie.values, fichier_roboflow=r.source.values,
                               sha256=r.sha256.values))
reponses = etiquettes[["photo", "classe"]].copy()
reponses["branche"] = np.where(est_loin, "loin", "pres")
reponses["p_loin"] = pl.p_loin.round(4).values
reponses["p_malade"] = np.where(est_loin, 1 - v2.p_saine.values, 1 - so.p_saine.values).round(4)
reponses["reponse"] = np.where(est_loin, loin, proche)
reponses["alerte"] = reponses.reponse.isin(ALERTE)

SORTIE.mkdir(parents=True, exist_ok=True)
fz = SORTIE / "tdtu_1636.zip"
with zipfile.ZipFile(fz, "w", zipfile.ZIP_STORED) as z:
    for c, n in zip(v2.chemin, nom):
        z.write(RACINE / c, f"tdtu_1636/photos/{n}")
    z.writestr("tdtu_1636/etiquettes.csv", etiquettes.to_csv(index=False).encode("utf-8"))
fr = SORTIE / "reponses_module_tdtu.csv"
reponses.to_csv(fr, index=False, encoding="utf-8")

print("classes :", etiquettes.classe.value_counts().to_dict())
print("branches :", reponses.branche.value_counts().to_dict())
for f in (fz, fr):
    print(f"{f.name} : {f.stat().st_size / 1e6:.1f} Mo, SHA-256 {sha(f)}")
