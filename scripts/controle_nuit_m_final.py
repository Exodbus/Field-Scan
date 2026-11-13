#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : modèle final v12 (3 réseaux appris sur tout) : validation Tanzanie lue par le modèle
final (fichier du carnet Kaggle), chaîne réécrite (loin -> v2 ; proche alerte si P(saine) < t), et identité des poids
rangés dans modeles/ avec ceux sortis du carnet (SHA-256). Réglage seulement.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_m_final.py a4 0.5186470150947571
"""
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import controle_nuit_m_recalcul as R  # noqa: E402

if __name__ == "__main__":
    c, t = sys.argv[1], float(sys.argv[2])
    K = RACINE / f"out/maladies/nuit_1112/kaggle/{sys.argv[3] if len(sys.argv) > 3 else 'final_' + c}"
    d = R.charger()["validation"]
    p = pd.read_csv(K / f"predictions_{c}_final_validation.csv").set_index("chemin").loc[list(d["chemin"])]
    a = np.where(d["loin"], d["Pv2"][:, 0] <= 0.70, p.p_saine.to_numpy() < t)
    m = d["malade"]
    l = [f"{c} modèle final, validation au seuil {t:.4f} : malades sans alerte {int((m & ~a).sum())}/{int(m.sum())} ; "
         f"saines en alerte {int((~m & a).sum())}/{int((~m).sum())} (limites 14 et 77)"]
    for f in sorted(K.glob(f"maladies_v12{c}_*.pt")):
        g = RACINE / f"modeles/maladies_v12_essais/v12{c}/{f.name}"
        h1 = hashlib.sha256(f.read_bytes()).hexdigest()
        h2 = hashlib.sha256(g.read_bytes()).hexdigest() if g.exists() else "absent"
        l.append(f"  {f.name} : carnet {h1[:16]}… ; modeles/ {h2[:16]}… ; {'identiques' if h1 == h2 else 'DIFFÉRENTS'}")
    (R.OUT / f"m_final_{c}.txt").write_text("\n".join(l) + "\n", encoding="utf-8")
    print("\n".join(l))
