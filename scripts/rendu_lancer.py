#!/usr/bin/env python3
"""Lance les rendus Blender de la parcelle (scripts/blender_scene.py, version 2) puis compose les planches.

Rendus (Cycles, processeur, débruiteur OpenImageDenoise) écrits dans --donnees (défaut out/rendu_blender/v3) :
  vue_drone_naturel.png, vue_drone_sante.png, vue_proche_naturel.png, vue_heros_naturel.png (1920 x 1080),
  vue_dessus_naturel.png, vue_dessus_sante.png
  (et, sur demande, vue_photo_naturel.png : la mosaïque réelle au sol, vue oblique)
Planches :
  planche_dessus_comparaison.png  mosaïque réelle + centres détectés | rendu 3D vu de dessus
  planche_dessus_sante.png        mosaïque réelle | rendu 3D teinté par l'ExG réel de la chaîne, avec légende
  planche_drone_sante.png         vue de drone teintée, avec légende
La scène est aussi enregistrée : parcelle_bananiers.blend (vue drone, rendu naturel).
Survol animé (facultatif, ~1 h 15) : --survol appelle scripts/rendu_survol.py (survol_parcelle.mp4).

Prérequis : scripts/rendu_preparer.py (plants.csv, tuile.png, donnees_rendu.json).
Exemple (6 fils, rien d'autre ne tourne) :
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/rendu_lancer.py --fils 6
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/rendu_lancer.py --composer-seulement
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

BLENDER = r"C:\Users\coren\outils\blender_5.2.4\blender-5.2.4-windows-x64\blender.exe"
RENDUS = [  # vue, mode, échantillons, largeur, hauteur
    ("drone", "naturel", 40, 1600, 900),
    ("drone", "sante", 40, 1600, 900),
    ("proche", "naturel", 40, 1600, 900),
    ("heros", "naturel", 72, 1920, 1080),
    ("dessus", "naturel", 32, 1000, 1000),
    ("dessus", "sante", 32, 1000, 1000),
    ("photo", "naturel", 32, 1600, 900),
]
PAR_DEFAUT = ["drone_naturel", "drone_sante", "proche_naturel", "heros_naturel", "dessus_naturel", "dessus_sante"]
ORANGE, JAUNE, VERT = (0xEF, 0x6C, 0x00), (0xE8, 0xC5, 0x47), (0x2E, 0x7D, 0x32)
ECART_BAS, ECART_HAUT = -0.05, 0.06


def police(taille, gras=False):
    for nom in (("segoeuib.ttf", "arialbd.ttf") if gras else ("segoeui.ttf", "arial.ttf")):
        try:
            return ImageFont.truetype(f"C:/Windows/Fonts/{nom}", taille)
        except OSError:
            continue
    return ImageFont.load_default()


def couleur(e):
    if e <= 0:
        t = min(max((e - ECART_BAS) / -ECART_BAS, 0), 1)
        a, b = ORANGE, JAUNE
    else:
        t = min(max(e / ECART_HAUT, 0), 1)
        a, b = JAUNE, VERT
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def legende(largeur, info):
    """Bandeau de légende de la teinte « santé » (mesure réelle, pas une alerte)."""
    h = 120
    im = Image.new("RGB", (largeur, h), (250, 250, 247))
    d = ImageDraw.Draw(im)
    x0, x1, y0 = 40, 520, 52
    for x in range(x0, x1):
        e = ECART_BAS + (ECART_HAUT - ECART_BAS) * (x - x0) / (x1 - x0)
        d.line([(x, y0), (x, y0 + 22)], fill=couleur(e))
    f, fg = police(17), police(19, True)
    for e in (-0.05, 0.0, 0.03, 0.06):
        x = x0 + (e - ECART_BAS) / (ECART_HAUT - ECART_BAS) * (x1 - x0)
        d.line([(x, y0 + 22), (x, y0 + 28)], fill=(40, 40, 40))
        d.text((x, y0 + 30), f"{e:+.2f}".replace(".", ","), font=f, fill=(40, 40, 40), anchor="ma")
    v = info["vigueur"]
    d.text((x0, 12), "Teinte des feuilles : vigueur relative mesurée par la chaîne (ExG drone, écart à la médiane de la parcelle)",
           font=fg, fill=(20, 20, 20))
    lignes = [
        "Donnée réelle : carte ExG du module vigueur (run.py), lissée sur 3 m, lue au centre de chaque pied détecté.",
        f"Parcelle {v['parcelle']} : bulletin {v['niveau_parcelle']} (score {v['score_parcelle']:.0f}), médiane ExG "
        f"{v['exg_mediane_parcelle']:.3f}. Aucune zone d'alerte du bulletin dans cette mosaïque.".replace(".", ",", 1),
        "L'ExG mêle verdeur et couverture du sol : c'est un indice relatif, pas un diagnostic plant par plant.",
    ]
    for k, t in enumerate(lignes):
        d.text((x1 + 40, 44 + 22 * k), t, font=police(16), fill=(50, 50, 50))
    return im


def titre(im, texte, sous_titre=""):
    h = 70 if sous_titre else 46
    out = Image.new("RGB", (im.width, im.height + h), (250, 250, 247))
    out.paste(im, (0, h))
    d = ImageDraw.Draw(out)
    d.text((16, 10), texte, font=police(22, True), fill=(20, 20, 20))
    if sous_titre:
        d.text((16, 40), sous_titre, font=police(16), fill=(60, 60, 60))
    return out


def composer(dossier):
    info = json.loads((dossier / "donnees_rendu.json").read_text(encoding="utf-8"))
    n = info["detecteur"]["n_detectes"]
    c = 900
    tuile = Image.open(dossier / "tuile.png").convert("RGB").resize((c, c), Image.LANCZOS)
    det = Image.open(dossier / "tuile_detections.png").convert("RGB").resize((c, c), Image.LANCZOS)
    cote = info["cote_sol_m"][0]
    nt = len(info.get("tuiles", [info.get("tuile")]))
    st_tuile = (f"{nt} tuiles d'entraînement Flora Pluas recollées, {cote:.1f} x {cote:.1f} m à 5 cm/px".replace(".", ",")
                if nt > 1 else f"{info.get('tuile')} (entraînement), {cote:.1f} x {cote:.1f} m à 5 cm/px".replace(".", ","))
    for mode, nom, texte_d in (("naturel", "planche_dessus_comparaison.png", "Rendu 3D vu de dessus : un bananier procédural par centre"),
                               ("sante", "planche_dessus_sante.png", "Rendu 3D teinté par la vigueur réelle (ExG de la chaîne)")):
        r = dossier / f"vue_dessus_{mode}.png"
        if not r.exists():
            continue
        rendu = Image.open(r).convert("RGB").resize((c, c), Image.LANCZOS)
        gauche = titre(det if mode == "naturel" else tuile,
                       f"Image réelle et {n} centres détectés (comptage v5, seuil 0,30)" if mode == "naturel" else "Image réelle",
                       st_tuile)
        droite = titre(rendu, texte_d, "même cadrage, même échelle ; formes, sol et arbres d'agroforesterie illustratifs")
        pl = Image.new("RGB", (2 * c + 20, gauche.height), (250, 250, 247))
        pl.paste(gauche, (0, 0))
        pl.paste(droite, (c + 20, 0))
        if mode == "sante":
            lg = legende(pl.width, info)
            tout = Image.new("RGB", (pl.width, pl.height + lg.height), (250, 250, 247))
            tout.paste(pl, (0, 0))
            tout.paste(lg, (0, pl.height))
            pl = tout
        pl.save(dossier / nom)
        print("planche :", nom)
    r = dossier / "vue_drone_sante.png"
    if r.exists():
        im = Image.open(r).convert("RGB")
        lg = legende(im.width, info)
        tout = Image.new("RGB", (im.width, im.height + lg.height), (250, 250, 247))
        tout.paste(im, (0, 0))
        tout.paste(lg, (0, im.height))
        tout.save(dossier / "planche_drone_sante.png")
        print("planche : planche_drone_sante.png")


def blender(args, fils):
    cmd = [BLENDER, "-b", "--factory-startup", "-t", str(fils), "-P", str(RACINE / "scripts/blender_scene.py"), "--"] + args
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def survol(dossier, fils):
    """Survol animé : délégué à scripts/rendu_survol.py (photo réelle -> 3D, EEVEE, encodage MP4)."""
    cmd = [sys.executable, "-I", "-u", str(RACINE / "scripts/rendu_survol.py"), "--donnees", str(dossier), "--fils", str(fils)]
    print(subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout[-2000:])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--donnees", default="out/rendu_blender/v4")
    ap.add_argument("--fils", type=int, default=6, help="fils de calcul de Cycles (8 cœurs : 6 si rien d'autre ne tourne)")
    ap.add_argument("--echelle-echantillons", type=float, default=1.0, help="multiplie les échantillons de chaque rendu")
    ap.add_argument("--vues", nargs="*", help="sous-ensemble, par ex. drone_naturel proche_naturel photo_naturel")
    ap.add_argument("--composer-seulement", action="store_true")
    ap.add_argument("--survol", action="store_true", help="rend aussi le survol animé (long)")
    a = ap.parse_args()
    dossier = (RACINE / a.donnees).resolve()
    if not a.composer_seulement:
        for vue, mode, ech, lx, ly in RENDUS:
            if f"{vue}_{mode}" not in (a.vues or PAR_DEFAUT):
                continue
            args = ["--donnees", str(dossier), "--vue", vue, "--mode", mode,
                    "--echantillons", str(max(4, round(ech * a.echelle_echantillons))),
                    "--fils", str(a.fils), "--largeur", str(lx), "--hauteur", str(ly)]
            if vue == "drone" and mode == "naturel":
                args += ["--blend", str(dossier / "parcelle_bananiers.blend")]
            t = time.time()
            res = blender(args, a.fils)
            lignes = [l for l in res.stdout.splitlines() if l.startswith(("RENDU", "Error")) or "bananiers (" in l]
            print(f"[{time.strftime('%H:%M')}] {vue}/{mode} : code {res.returncode}, {time.time() - t:.0f} s ; " + " | ".join(lignes),
                  flush=True)
            if res.returncode != 0:
                print(res.stdout[-3000:], res.stderr[-3000:])
        if a.survol:
            survol(dossier, a.fils)
    composer(dossier)


if __name__ == "__main__":
    main()
