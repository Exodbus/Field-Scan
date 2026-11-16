#!/usr/bin/env python3
"""Rapatrie les sorties du carnet Kaggle m15b-traits (M-kaggle2, 15/11) dans out/maladies/jour_1511/kaggle2/lot_traits/
et contrôle leur forme (traits normalisés, tailles attendues, aucun nom de juge).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/m15b_recuperer.py [nom_du_carnet]
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
RACINE = Path(__file__).resolve().parents[1]
NOM = (sys.argv[1:] or ["m15b-traits"])[0]
dos = RACINE / "out/maladies/jour_1511/kaggle2/lot_traits"
dos.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
           SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
r = subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "output", f"affilecorentin/{NOM}", "-p", str(dos), "-o"],
                   env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.stdout[-600:], r.stderr[-600:])
ctrl = {"carnet": NOM, "fichiers": sorted(p.name for p in dos.iterdir())}
meta = pd.read_csv(dos / "appr_meta.csv")
for x in ("tdtu", "ethiopie"):
    z = np.load(dos / f"traits_s4_sans_{x}.npz")
    ctrl[x] = {n: list(z[n].shape) for n in z.files}
    assert z["appr"].shape[0] == len(meta)
    nrm = np.linalg.norm(z["appr"].astype("float32"), axis=1)
    ctrl[x]["norme_min_max"] = [float(nrm.min()), float(nrm.max())]
    assert np.isfinite(z["appr"].astype("float32")).all()
for f in dos.glob("chemins_*.csv"):
    ch = pd.read_csv(f).chemin.astype(str).str.lower()
    assert not ch.str.contains("banspot|cordana_perou|test_perou|sig_per|symptomatic").any(), f
assert not meta.pays.astype(str).str.lower().str.contains("banspot|perou_test|test_perou").any()
print(json.dumps(ctrl, indent=1))
(RACINE / "out/maladies/jour_1511/kaggle2/controle_traits.json").write_text(json.dumps(ctrl, indent=1), encoding="utf-8")
