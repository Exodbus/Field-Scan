#!/usr/bin/env python3
"""Tableau chiffré des candidats retenus par C-banc (nuit du 13/11), tiré des fichiers de mesure (aucun calcul neuf) :
out/comptage/nuit_1311/banc/essais.json, essais_resolution.json, aiguillage.json, temps.json.
Écrit out/comptage/nuit_1311/banc/finalistes_chiffres.md, repris dans finalistes.md.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c13_banc_finalistes.py --candidats A B ...
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c13_banc_commun as cc  # noqa: E402


def lire(nom):
    p = cc.SORTIE / nom
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidats", nargs="+", required=True)
    a = ap.parse_args()
    E, R, A, T = lire("essais.json"), lire("tableau_resolution.json"), lire("aiguillage.json"), lire("temps.json")
    ref = cc.reference_v5({"v5": {"res": cc.res_float(E["v5"]["res"])}})
    resol = {d["nom"]: d for d in R.get("lignes", [])}
    L = []
    J = cc.REGLAGE
    L.append("| candidat | seuil | " + " | ".join(J) + " | moyenne 5 | moy4 | erreur de compte | val_negatifs | 5.3 |")
    L.append("| --- | --- | " + " | ".join("---" for _ in J) + " | --- | --- | --- | --- | --- |")
    L.append(f"| v5 (référence) | 0.30 | " + " | ".join(f"{ref['f1_' + j]:.3f}" for j in J)
             + f" | {ref['moyenne']:.4f} | {ref['moy4']:.4f} | {ref['err_compte']:.3f} | {ref['fp_neg']} ({100 * ref['taux_fp']:.2f} %) | référence |")
    for nom in a.candidats:
        if nom in E:
            b = cc.choisir(cc.lignes(cc.res_float(E[nom]["res"])))
            st = cc.statut(b, ref)
            L.append(f"| `{nom}` | {b['seuil']:.2f} | " + " | ".join(f"{b['f1_' + j]:.3f} ({b['f1_' + j] - ref['f1_' + j]:+.3f})" for j in J)
                     + f" | {b['moyenne']:.4f} ({st['gain']:+.4f}) | {b['moy4']:.4f} | {b['err_compte']:.3f} | {b['fp_neg']} ({100 * b['taux_fp']:.2f} %) | "
                     + ("passe" if st["finaliste"] else "échoue") + " |")
    L.append("")
    L.append("Rapports détectés / annotés au seuil retenu :")
    L.append("")
    for nom in ["v5"] + a.candidats:
        if nom in E:
            ls = cc.lignes(cc.res_float(E[nom]["res"]))
            b = [l for l in ls if l["seuil"] == 0.30][0] if nom == "v5" else cc.choisir(ls)
            L.append(f"- `{nom}` : " + ", ".join(f"{j} {b['ratio_' + j]:.3f}" for j in J))
    if resol:
        rr = R["reference"]
        cms = sorted(rr, key=float)
        L.append("")
        L.append("Réglage dégradé (moyenne des 5 F1 au seuil du candidat, choisi à 5 cm ; v5 au seuil 0,30). `val_negatifs` : "
                 "mesuré avec la résolution d'origine de chaque tuile (10 à 12 cm/px) :")
        L.append("")
        L.append("| candidat | seuil | " + " | ".join(f"{c} cm" for c in cms) + " | 11 cm par jeu (" + ", ".join(J)
                 + ") | erreur de compte 11 cm | val_negatifs | finaliste résolution | 5.3 |")
        L.append("| --- | --- | " + " | ".join("---" for _ in cms) + " | --- | --- | --- | --- | --- |")
        L.append("| v5 | 0.30 | " + " | ".join(f"{rr[c]['moyenne']:.4f}" for c in cms) + " | "
                 + " / ".join(f"{rr['11']['f1_' + j]:.3f}" for j in J) + f" | {rr['11']['err_compte']:.3f} | 16 | référence | référence |")
        for nom in a.candidats:
            if nom in resol:
                d = resol[nom]
                L.append(f"| `{nom}` | {d['seuil']:.2f} | " + " | ".join(f"{d.get(f'moy@{c}', float('nan')):.4f}" for c in cms) + " | "
                         + " / ".join(f"{d[f'f1_{j}@11']:.3f}" for j in J) + f" | {d['err@11']:.3f} | {d['fp_neg']} | "
                         + f"{'oui' if d['fin_res'] else 'non'} | {'oui' if d['fin_53'] else 'non'} |")
    if A:
        L.append("")
        L.append("Images aiguillées vers la branche « petits » (images / total) :")
        L.append("")
        for nom in a.candidats:
            if nom in A:
                L.append(f"- `{nom}` : " + ", ".join(f"{j} {v[0]} / {v[1]}" for j, v in A[nom].items()))
    if T:
        L.append("")
        L.append("Temps de calcul (processeur, 3 fils, machine partagée ; réseaux calculés, pas lus dans le cache) :")
        L.append("")
        for nom in ["v5"] + a.candidats:
            if nom in T:
                t = T[nom]
                L.append(f"- `{nom}` ({t.get('heure', '')}) : " + ", ".join(
                    f"{j} {v['s_par_tuile']:.2f} s/tuile ({v['s_par_ha']:.1f} s/ha)" for j, v in t.items() if isinstance(v, dict)))
    (cc.SORTIE / "finalistes_chiffres.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
