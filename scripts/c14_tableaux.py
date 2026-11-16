#!/usr/bin/env python3
"""Tableaux de out/comptage/nuit_1311/piste2/essais.json (agent C-piste2, 14/11), en Markdown, chiffres à la virgule.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c14_tableaux.py nom1 nom2 ...
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
E = json.loads((RACINE / "out/comptage/nuit_1311/piste2/essais.json").read_text(encoding="utf-8"))
J = ["dense", "plantain", "jeunes", "mm", "btd_val"]


def v(x, n=4):
    return f"{x:.{n}f}".replace(".", ",")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("| candidat | seuil | dense | plantain | jeunes | MM | btd_val | moyenne 5 | 4 anciennes (sans btd_val) | erreur | val_neg | 8 cm | 11 cm | 4 anciennes à 11 cm | 5.3 |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for n in sys.argv[1:]:
        e = E[n]
        r = e["retenu"] if n != "v5" else [l for l in e["lignes"] if l["seuil"] == 0.30][0]
        s = e.get("statut", {})
        c11, c8 = e.get("cm11"), e.get("cm8")
        st = "référence" if n == "v5" else ("finaliste" if s.get("finaliste") else "non")
        if n != "v5" and c11 and not s.get("finaliste"):
            res = (c11["moyenne"] >= 0.6306 and r["moyenne"] >= 0.7727 and s["c2"] and s["c3"] and s["c4"])
            st += " ; « résolution » oui" if res else ""
        elif n != "v5" and c11 and s.get("finaliste") and c11["moyenne"] >= 0.6306:
            st += " ; « résolution » oui"
        print(f"| `{n}` | {v(r['seuil'], 2)} | " + " | ".join(v(r['f1_' + j]) for j in J)
              + f" | {v(r['moyenne'])} | {v(r['moy4'])} | {v(r['err_compte'], 3)} | {r['fp_neg']} ({v(100 * r['taux_fp'], 2)} %) | "
              + (v(c8["moyenne"]) if c8 else "—") + " | " + (v(c11["moyenne"]) if c11 else "—") + " | "
              + (v(c11["moy4"]) if c11 else "—") + f" | {st} |")


if __name__ == "__main__":
    main()
