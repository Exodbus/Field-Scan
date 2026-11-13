#!/usr/bin/env python3
"""Écrit out/comptage_v6/banc/finalistes.md (agent C-banc) pour l'agent « Juge » : définition exacte, seuil, chiffres de
réglage (avec le contrôle complet sur les tuiles sans bananier) et moyen de les recalculer. Les juges ne sont pas lus.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/v6_banc_finalistes.py --finalistes A B C
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v6_banc_commun as bc  # noqa: E402
import v6_banc_essais as es  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--finalistes", nargs="+", required=True)
    ap.add_argument("--notes", default="")
    a = ap.parse_args()
    E = es.charger()
    jeux = es.jeux_reglage()
    lignes, base = es.tableau(E, jeux, tri=False)
    L = {l["nom"]: l for l in lignes}
    r5 = {float(s): v for s, v in E["v5"]["res"]["dense"].items()}
    _, l5 = es.ligne(E["v5"]["res"], jeux)
    v530 = [l for l in l5 if l["seuil"] == 0.30][0]
    out = [f"# Finalistes du banc de comptage v6 (agent C-banc), écrits le 13 novembre 2026 à {time.strftime('%H:%M')}",
           "",
           "Écrits **avant toute lecture des juges** (aucun juge n'a été lu par C-banc). Règles : `docs/plan_nuit_2026-11-12.md`, 3.4.",
           f"Réglage : {', '.join(jeux)} (btd_val = moitié validation de banana_tree_detection, découpage v6, archive "
           "`data/drone/comptage_v6_5cm`, ensemble `val_espace`). Fausses détections : 1 424 tuiles sans bananier de validation (6 459 arbres).",
           "",
           f"**Référence v5** (règle 3.4 sur le même réglage) : seuil {base['seuil']}, moyenne {base['moyenne']:.4f}, "
           + ", ".join(f"{j} {base['f1_' + j]:.3f}" for j in jeux) + f", erreur de compte {base['err_compte']:.3f}, "
           f"fausses sans bananier {base['fp_neg']} ({base['taux_fp']:.2%}).",
           f"Pour information, v5 au seuil 0,30 de la chaîne : moyenne {v530['moyenne']:.4f}, "
           + ", ".join(f"{j} {v530['f1_' + j]:.3f}" for j in jeux) + f", erreur de compte {v530['err_compte']:.3f}, fausses {v530['fp_neg']}.",
           "", "| finaliste | seuil | " + " | ".join(jeux) + " | moyenne | gain / v5 | pire perte | erreur de compte | fausses sans bananier |",
           "| --- " * (len(jeux) + 7) + "|"]
    for n in a.finalistes:
        l = L[n]
        out.append(f"| `{n}` | {l['seuil']:.2f} | " + " | ".join(f"{l['f1_' + j]:.3f}" for j in jeux)
                   + f" | {l['moyenne']:.4f} | {l['gain']:+.3f} | {l['pire_perte']:+.3f} | {l['err_compte']:.3f} | "
                   f"{l['fp_neg']} ({l['taux_fp']:.2%}{', quart des tuiles' if 'neg' not in E[n]['res'] else ''}) |")
    out += ["", "## Définitions exactes", ""]
    for n in a.finalistes:
        e = E[n]
        out += [f"### `{n}` ({e['famille']})", "", f"- fabrique : `{e['fabrique']}` dans `scripts/v6_banc_candidats.py` ; réglages :",
                "", "```json", json.dumps(e["reglages"], ensure_ascii=False), "```", "",
                f"- seuil (règle 3.4) : **{L[n]['seuil']:.2f}** sur le score rendu par le candidat ;",
                f"- rapports détectés / annotés : " + ", ".join(f"{j} {L[n]['ratio_' + j]:.3f}" for j in jeux) + ".", ""]
    out += ["## Recalcul", "",
            "Les cartes de chaleur sont en cache dans `out/comptage_v6/banc/cache/` (une carte par modèle, variante et jeu) ; "
            "pour un juge, il faut d'abord calculer ses cartes (`bc.ecrire_cache(modele, groupe, jeu)` avec jeu = `segmento`, `cg`, "
            "`banano`, `neg_test`, groupe `base`, ou `tta` si le finaliste lit une variante m8/x8/g8), puis :", "",
            "```python",
            "import sys; sys.path.insert(0, 'scripts')",
            "import v6_banc_commun as bc, v6_banc_candidats as ca, v6_banc_essais as es",
            "e = es.charger()['<finaliste>']",
            "f = ca.construire(e['fabrique'], e['reglages'])          # Contexte -> (points xy à 5 cm, scores)",
            "for m in ('v3', 'v4', 'v5'): bc.ecrire_cache(m, 'base', '<jeu>')",
            "r = bc.mesurer_jeu(f, '<jeu>')[<seuil>]                  # vp, fp, fn, p, r, f1, detectes, reels, err_compte",
            "```", "",
            "Réglage seul : `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/v6_banc_essais.py` (tableau complet). "
            "Points par image : `scripts/v6_banc_points.py --candidats <finaliste>` (`out/comptage_v6/banc/points/`).",
            "", "Mesure : celle du carnet v5 (pics fenêtre 7, rayon 20 px, appariement un-à-un, disque de 2 000 px, points non-mères ignorés), "
            "vérifiée par l'essai 1 (`out/comptage_v6/banc/controle.txt`). Juges segmento est (`segmento`), CG1-CG9 mères seules (`cg`), "
            "banano (`banano`), sans bananier du test (`neg_test`) : définis dans `bc.jeu`, jamais chargés par C-banc.",
            "", a.notes]
    (bc.SORTIE / "finalistes.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
