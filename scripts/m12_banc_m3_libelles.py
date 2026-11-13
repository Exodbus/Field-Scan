#!/usr/bin/env python3
"""M3, suite : seuil_alerte et seuil v11 (seuil_inconnu_malade) de la v10b, seuil de confiance installé (réglage seul).

Ces deux seuils ne changent pas le nombre d'alertes tant que seuil_alerte >= 1 - seuil_confiance : ils changent le
libellé (maladie nommée, malade non identifiée, à vérifier). Rapporté : coût, saines « à vérifier », Sigatoka nommée.
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402

jeux = B.charger_reglage()
ref = B.reference(jeux)
ESSAIS = []
print("ref " + B.ligne("installee (0,725 / 0,675)", ref))
for sa in (0.40, 0.50, 0.60, 0.725, 0.85):
    for si in (0.50, 0.60, 0.675, 0.75, 0.85):
        r = B.evaluer(jeux, lambda d: B.decider_v10b(d["P10"], seuil_alerte=sa, seuil_inconnu_malade=si))
        ok, detail = B.finaliste(r, ref)
        ESSAIS.append(dict(famille="M3 libelles", nom=f"seuil_alerte={sa} seuil_v11={si}", finaliste=ok, detail=detail, **r))
        print(("F " if ok else "  ") + B.ligne(f"alerte={sa} v11={si}", r))
print("essais :", len(ESSAIS))
(B.SORTIE / "essais_m3_libelles.json").write_text(json.dumps(ESSAIS, ensure_ascii=False, indent=1), encoding="utf-8")
