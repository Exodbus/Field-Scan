"""Applique la règle « finaliste » du plan (section 3) aux résumés du banc de réglage (15/11/2026).

Règle (écrite avant calcul, journal 14 h 01) :
  rappel moyen >= référence + 0,05 ; aucun niveau de gravité ne perd plus de 0,02 ;
  fausses alertes sur scènes sans injection <= référence (ha). 2 finalistes au plus par module,
  classés par rappel moyen décroissant puis fausses alertes sans injection croissantes.
Les contrôles (suffixe « r ») ne sont pas des essais.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd

import t15_commun as tc

FICHIERS = {"vigueur": "resume_vigueur.csv", "stress": "resume_stress.csv", "temporel": "resume_temporel.csv",
            "drone": "resume_drone.csv"}


# Contrôle de la session principale (14 h 16) : TS1 à TS4 refusés (surface comptée sans les parcelles que leur correctif
# garde) ; seules les variantes du tour 3 (TT*, journal 14 h 18) concourent pour le temporel.
NON_ADMISSIBLES = {"TS1", "TS2", "TS3", "TS4"}


def decider(res):
    ref = res[res.variante == "REF"].iloc[0]
    lignes = []
    for _, r in res.iterrows():
        if r.variante == "REF" or r.variante[-1] in "riu":
            continue
        pertes = {g: ref[f"rappel_{g}"] - r[f"rappel_{g}"] for g in tc.NOMS_GRAVITE}
        c1 = r.rappel_moyen >= ref.rappel_moyen + 0.05 - 1e-9
        c2 = max(pertes.values()) <= 0.02 + 1e-9
        c3 = r.fa_ha_sans_injection <= ref.fa_ha_sans_injection + 1e-9
        lignes.append(dict(variante=r.variante, gain_rappel=round(r.rappel_moyen - ref.rappel_moyen, 4),
                           perte_max_gravite=round(max(pertes.values()), 4), c_rappel=c1, c_gravite=c2, c_fa=c3,
                           passe=bool(c1 and c2 and c3 and r.variante not in NON_ADMISSIBLES),
                           admissible=r.variante not in NON_ADMISSIBLES, rappel_moyen=r.rappel_moyen, fa=r.fa_ha_sans_injection))
    d = pd.DataFrame(lignes)
    if len(d):
        # tri stable : à égalité de rappel et de FA, l'ordre d'écriture des essais départage
        ok = d[d.passe].sort_values(["rappel_moyen", "fa"], ascending=[False, True], kind="stable")
        d["finaliste"] = d.variante.isin(list(ok.variante[:2]))
    return d


if __name__ == "__main__":
    dossier = tc.SORTIE / "reglage"
    for m, f in FICHIERS.items():
        p = dossier / f
        if not p.exists():
            print(f"{m} : pas encore de résumé")
            continue
        res = pd.read_csv(p)
        for tour in (2, 3):
            p2 = dossier / f.replace(".csv", f"_tour{tour}.csv")
            if p2.exists():                       # tours 2 et 3 : mêmes graines, même référence (vérifiée)
                r2 = pd.read_csv(p2)
                a, b = res[res.variante == "REF"].iloc[0], r2[r2.variante == "REF"].iloc[0]
                assert abs(a.rappel_moyen - b.rappel_moyen) < 1e-9 and abs(a.fa_ha_sans_injection - b.fa_ha_sans_injection) < 1e-9
                res = pd.concat([res, r2[r2.variante != "REF"]], ignore_index=True)
        d = decider(res)
        d.to_csv(dossier / f"decision_{m}.csv", index=False)
        print(f"== {m} ==")
        print(res.to_string(index=False))
        print(d.to_string(index=False))
