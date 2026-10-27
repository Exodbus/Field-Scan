"""Liste les images a exclure d'un jeu : copies exactes et images ambigues.

Usage :
    python scripts/make_exclusions.py data/raw/bananalsd/.../OriginalSet

Regles :
  - fichiers strictement identiques (SHA-256) dans la meme classe : on garde
    le premier (ordre alphabetique), on exclut les autres ;
  - fichiers strictement identiques dans des classes differentes : etiquette
    contradictoire, on exclut TOUS les exemplaires.

Rien n'est supprime ni deplace. Le script ecrit out/exclusions.csv et affiche
les effectifs par classe avant / apres.
"""
import argparse
import csv
import hashlib
from collections import defaultdict
from pathlib import Path

EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


def sha(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier", type=Path)
    ap.add_argument("--sortie", type=Path, default=Path("out/exclusions.csv"))
    a = ap.parse_args()

    fichiers = sorted(p for p in a.dossier.rglob("*")
                      if p.is_file() and p.suffix.lower() in EXT)
    if not fichiers:
        raise SystemExit("Aucune image trouvee.")

    groupes = defaultdict(list)
    for f in fichiers:
        groupes[sha(f)].append(f)

    exclusions = []  # (fichier, classe, raison, reference)
    for h, liste in groupes.items():
        if len(liste) < 2:
            continue
        classes = {f.parent.name for f in liste}
        if len(classes) > 1:
            for f in liste:
                exclusions.append((f, f.parent.name, "etiquette contradictoire",
                                   "; ".join(f"{g.parent.name}/{g.name}" for g in liste if g != f)))
        else:
            garde = liste[0]
            for f in liste[1:]:
                exclusions.append((f, f.parent.name, "copie exacte",
                                   f"{garde.parent.name}/{garde.name}"))

    avant, apres = defaultdict(int), defaultdict(int)
    exclus = {e[0] for e in exclusions}
    for f in fichiers:
        avant[f.parent.name] += 1
        if f not in exclus:
            apres[f.parent.name] += 1

    a.sortie.parent.mkdir(parents=True, exist_ok=True)
    with open(a.sortie, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["fichier", "classe", "raison", "reference"])
        for f, c, r, ref in sorted(exclusions, key=lambda t: (t[1], t[0].name)):
            w.writerow([f"{c}/{f.name}", c, r, ref])

    print(f"{len(fichiers)} images, {len(exclusions)} a exclure -> {a.sortie}")
    print(f"  copies exactes : {sum(1 for e in exclusions if e[2] == 'copie exacte')}")
    print(f"  etiquette contradictoire : {sum(1 for e in exclusions if e[2] != 'copie exacte')}")
    print("\nEffectifs par classe (avant -> apres) :")
    for c in sorted(avant):
        print(f"  {c:16s} {avant[c]:4d} -> {apres[c]:4d}")
    print(f"  {'TOTAL':16s} {sum(avant.values()):4d} -> {sum(apres.values()):4d}")
