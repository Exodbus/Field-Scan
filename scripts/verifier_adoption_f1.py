"""Adoption de F1 (13/11/2026) : vérifie que le code F1 installé dans fieldscan/modules/maladies.py redonne exactement les réponses de la référence
(scripts/m12_banc_finalistes.py) sur les probabilités déjà calculées (test vierge, juges)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd, yaml
R = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(R), str(R / "scripts")]
from fieldscan.modules import maladies as M
import m12_banc_finalistes as MF, juge_nuit_m_juges as JJ
reg = yaml.safe_load((R / "config.yaml").read_text(encoding="utf-8"))["maladies"]
m = M.charger_convnext(R / reg["modele"])
mv2 = M.charger_convnext(R / reg["melange_proche"][1])
mp = {**m, "seuil": float(reg["seuil_confiance_melange"]), "jnsp_alerte": reg["jnsp_alerte"]}
ml = {**mv2, "jnsp_alerte": reg["jnsp_alerte_loin"]}
F1 = MF.CANDIDATS["F1_trois_morceaux2x2"]
def comparer(nom, P10, Pso, Pv2, pl, G2):
    a = MF.repondre(P10, Pso, Pv2, pl, F1, G2=G2)
    b = M.decider_melange(P10, Pso, Pv2, pl, G2, mp, ml, reg["loin_ou_proche"])[0]
    print(f"{nom:34s} {len(a)} photos, réponses différentes : {int((a != b).sum())}")
    assert (a == b).all()
V = R / "out/controle_nuit_1112/juge_m/vierge"
P10, Pso, Pv2, pl = (np.load(V / f"p_{k}.npy") for k in ("v10b", "soupe", "v2", "loin"))
G = np.load(V / "p_g2.npy"); inc = np.isnan(G).any((1, 2))
for cote, rem in (("morceaux non lus = saine", JJ.SAINE), ("morceaux non lus = malade", JJ.MALADE)):
    Gc = G.copy(); Gc[inc] = rem
    comparer("vierge, " + cote, P10, Pso, Pv2, pl, Gc)
rng = np.random.default_rng(0)
comparer("vierge, morceaux au hasard", P10, Pso, Pv2, pl, rng.dirichlet(np.ones(4), (len(P10), 4)))
z = JJ.charger()
for j in JJ.JEUX:
    d = JJ.jeu(z, j)
    comparer(f"juge {j}, morceaux au hasard", d["P10"], d["Pso"], d["Pv2"], d["p_loin"], rng.dirichlet(np.ones(4), (len(d["P10"]), 4)))
# morceaux : mêmes octets que la référence
photo = pd.read_csv(V / "reponses_installee.csv").chemin[0]
a, b = M.morceaux_2x2(R / photo), JJ.morceaux(R / photo)
print("morceaux identiques à la référence :", all(x.getvalue() == y.getvalue() for x, y in zip(a, b)))
