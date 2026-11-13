#!/usr/bin/env python3
"""Range le modèle final d'un finaliste v12 (3 réseaux appris sur tout) dans modeles/maladies_v12_essais/v12<candidat>/,
au format lu par fieldscan/modules/maladies.py (même seuils.json que la v10b, motif des poids changé). N'installe rien
dans la chaîne. Contrôle : chaîne complète sur la validation Tanzanie lue par le modèle final (ce n'est PAS une mesure
de réglage : la validation reste hors de l'apprentissage, mais c'est le seul jeu non appris par le modèle final).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/m12_entr_installer.py <candidat> [seuil_regle_b]
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m12_entr_mesurer as M  # noqa: E402

nom = sys.argv[1]
regle_b = float(sys.argv[2]) if len(sys.argv) > 2 else None
src = M.RACINE / "out/maladies/nuit_1112/kaggle" / (__import__("os").environ.get("SOURCE") or f"final_{nom}")
dst = M.RACINE / "modeles/maladies_v12_essais" / (f"v12{nom}" + (f"_b{regle_b:g}" if regle_b else ""))
dst.mkdir(parents=True, exist_ok=True)
poids = sorted(src.glob(f"maladies_v12{nom}_*.pt"))
assert len(poids) == 3, poids
for p in poids:
    shutil.copy2(p, dst / p.name)
s = json.loads((M.RACINE / "modeles/maladies_binome/v10b/seuils.json").read_text(encoding="utf-8"))
s["modele"] = f"v12{nom}" + (f"_regle_b_{regle_b:g}" if regle_b else "")
s["membres"][0]["motif"] = f"maladies_v12{nom}_*.pt"
if regle_b:
    s["seuil_confiance"] = regle_b
recette = json.loads((src / f"recette_{nom}.json").read_text(encoding="utf-8"))
s["note"] = (f"Candidat v12{nom} de la nuit du 12/11 (agent M-entraînement) : 3 ConvNeXt-Tiny DINOv3 repartis des 3 réseaux de la "
             f"v10b, réentraînés sur tout (recette {json.dumps(recette, ensure_ascii=False)}). Seuils de la v10b"
             + (f", règle B réglée à {regle_b:g} sur le réglage" if regle_b else " inchangés") + ". Built with DINOv3.")
(dst / "seuils.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
P = M.lire_csv(src / f"predictions_{nom}_final_validation.csv", "validation")
m = dict(M.M_V10B, seuil=regle_b) if regle_b else M.M_V10B
c = M.compter("validation", P, m)
print(f"{dst} : validation (modèle final, chaîne) {c[0]}/{c[1]} malades sans alerte, {c[2]}/{c[3]} saines en alerte")
