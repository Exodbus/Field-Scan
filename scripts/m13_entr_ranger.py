#!/usr/bin/env python3
"""Range un candidat « ensemble des 2 plis » (M-entraîneur, 14/11) dans modeles/maladies_nuit_1311/<candidat>/ : les 2 poids
(sans TDTU, sans Éthiopie) + seuils.json au format de la v10b (chargeable par fieldscan.modules.maladies.charger_convnext),
avec la confiance des photos « proche » (s_p) et, en clé à part, celle de l'élève dans la branche « loin » (s_l).
Rien n'est installé dans la chaîne.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_entr_ranger.py <lot> <candidat> <recette_des_seuils>
"""
import json
import shutil
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
lot, nom, rec = sys.argv[1:4]
couple = json.loads((RACINE / "out/maladies/nuit_1311/kaggle/lot1" / f"seuils2_{rec}.json").read_text(encoding="utf-8"))["couple"]
src = RACINE / "modeles/maladies_nuit_1311" / lot
dst = RACINE / "modeles/maladies_nuit_1311" / nom
dst.mkdir(parents=True, exist_ok=True)
pts = sorted(src.glob(f"maladies_m13{nom}_sans_*.pt"))
assert len(pts) == 2, pts
for p in pts:
    shutil.copy(p, dst / p.name)
s = json.loads((RACINE / "modeles/maladies_binome/v10b/seuils.json").read_text(encoding="utf-8"))
s["modele"] = f"m13_{nom}_eleve_F1_2_plis"
s["membres"][0]["motif"] = f"maladies_m13{nom}_sans_*.pt"
s["seuil_confiance"] = couple[0]
s["seuil_confiance_loin_eleve"] = couple[1]
s["note"] = (f"Élève distillé de F1 (M-entraîneur, nuit du 13/11, recette {rec}) : 2 ConvNeXt-Tiny DINOv3 (plis sans TDTU, "
             f"sans Éthiopie), lus en 384 px, 4 vues. Photo proche : confiance {couple[0]} ; photo « loin » : réponse de la v2 si "
             f"elle alerte, sinon l'élève décidé avec la confiance {couple[1]}. Autres seuils : ceux de la v10b. Non installé.")
(dst / "seuils.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
print("rangé :", dst, [p.name for p in dst.iterdir()])
