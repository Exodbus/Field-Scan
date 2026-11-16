#!/usr/bin/env python3
"""Prépare les médias et les chiffres de la page d'accueil de la démo finale (out/demo_finale/index.html).

Lit uniquement des sorties déjà produites (aucun calcul de modèle) :
  - Martinique : out/demo_martinique/ (parcelles automatiques, bulletin de la chaîne) et les captures de la visite 3D ;
  - El Oro : out/demo_eloro/ (comptage v5 par la chaîne, extraits de contrôle) ;
  - maladies : out/demo_finale/maladies_chaine/ (chaîne run.py --modules maladies sur les 8 photos BanSpot tirées par
    scripts/demo_finale_tirer_photos.py ; BanSpot est un jeu de juges, jamais appris).

Écrit out/demo_finale/medias/*.jpg, out/demo_finale/chiffres.json, puis out/demo_finale/index.html : la page
out/demo_finale/modele.html avec les images et les chiffres intégrés (page autonome). On modifie modele.html, jamais
index.html.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/demo_finale_preparer.py
"""
import base64
import csv
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from PIL import Image  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
OUT = RACINE / "out" / "demo_finale"
MEDIAS = OUT / "medias"


def jpeg(src, nom, cote=1600, recadrage=None, qualite=85):
    """Copie réduite (plus grand côté = cote px) en JPEG ; recadrage = (g, h, d, b) en fractions de l'image."""
    im = Image.open(src).convert("RGB")
    if recadrage:
        w, h = im.size
        g, ha, d, b = recadrage
        im = im.crop((int(g * w), int(ha * h), int(d * w), int(b * h)))
    im.thumbnail((cote, cote), Image.LANCZOS)
    MEDIAS.mkdir(parents=True, exist_ok=True)
    im.save(MEDIAS / nom, quality=qualite, optimize=True)
    return f"medias/{nom}"


def lire_csv(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    ch = {}

    # 1. Martinique : parcelles et vigueur (chaîne run.py, bulletin)
    dm = RACINE / "out" / "demo_martinique"
    bul = lire_csv(dm / "chaine" / "bulletin.csv")
    res = json.loads((dm / "synthese_resume.json").read_text(encoding="utf-8"))
    ch["martinique"] = dict(
        parcelles=len(bul),
        surface_ha=round(sum(float(r["surface_ha"]) for r in bul), 1),
        vertes=sum(r["niveau"] == "vert" for r in bul),
        orange=sum(r["niveau"] == "orange" for r in bul),
        rouges=sum(r["niveau"] == "rouge" for r in bul),
        zones_faibles=res["alertes"]["zone_faible"],
        surface_zones_faibles_ha=res["surface_zones_faibles_ha"],
        pieds_v5=res["pieds"],
    )
    jpeg(dm / "parcelles_auto.png", "martinique_parcelles.jpg", cote=2000)
    jpeg(dm / "parcelles_auto.png", "martinique_parcelles_zoom.jpg", cote=1600, recadrage=(0.33, 0.18, 0.66, 0.55))
    vm = RACINE / "out" / "visite_basse_pointe_zone" / "captures"
    for src, nom in [("02_drone_ensemble.jpg", "visite_drone.jpg"),
                     ("03_sol_devant_panneau.jpg", "visite_sol.jpg"),
                     ("06_mode_sante.jpg", "visite_sante.jpg")]:
        jpeg(vm / src, nom, cote=1280, qualite=88)

    # 2. El Oro : comptage par drone (chaîne run.py, détecteur v5)
    de = RACINE / "out" / "demo_eloro"
    cp = lire_csv(de / "chaine" / "comptage_parcelles.csv")
    par = {r["parcelle_id"]: r for r in cp}
    banane = ["P14", "P15", "P16"]
    ch["eloro"] = dict(
        pieds_total=sum(int(r["n_pieds"]) for r in cp),
        pieds_bananeraie=sum(int(par[p]["n_pieds"]) for p in banane),
        bananeraie={p: dict(pieds=int(par[p]["n_pieds"]), densite_ha=float(par[p]["densite_ha"]),
                            espacement_m=_f(par[p]["espacement_median_m"]),
                            bas=int(par[p]["n_pieds_estimes_bas"]), haut=int(par[p]["n_pieds_estimes_haut"]))
                    for p in banane},
        resolution_cm=6.4,
    )
    # extrait_P15.png = deux panneaux (image seule | pieds détectés) : on garde le panneau de droite, sans son titre
    jpeg(de / "controle_pieds" / "extrait_P15.png", "eloro_comptage_P15.jpg", cote=1200, qualite=88,
         recadrage=(0.508, 0.035, 0.99, 0.995))
    jpeg(de / "parcelles_auto_zoom_bananes.png", "eloro_parcelles_bananes.jpg", cote=1400)

    # 3. Maladies : photos de smartphone (chaîne run.py --modules maladies)
    mc = OUT / "maladies_chaine"
    fichier = mc / "maladies_photos.csv"
    photos = []
    vraies = {r["photo"]: r["classe_vraie"] for r in lire_csv(OUT / "tirage_banspot.csv")}
    if fichier.exists():
        for r in lire_csv(fichier):
            r["classe_vraie"] = vraies.get(Path(r.get("photo") or r.get("fichier") or "").name)
            photos.append(r)
    ch["maladies_photos"] = photos
    src_dir = OUT / "photos_banspot"
    for r in photos:
        nom = Path(r.get("photo") or r.get("fichier") or "").name
        if nom and (src_dir / nom).exists():
            r["vignette"] = jpeg(src_dir / nom, "feuille_" + Path(nom).stem + ".jpg", cote=640, qualite=85)

    (OUT / "chiffres.json").write_text(json.dumps(ch, ensure_ascii=False, indent=1), encoding="utf-8")
    assembler(ch)
    print(json.dumps({k: v for k, v in ch.items() if k != "maladies_photos"}, ensure_ascii=False, indent=1))
    print(f"{len(photos)} photos de feuilles ; colonnes : {list(photos[0].keys()) if photos else '-'}")


def data_uri(rel):
    return "data:image/jpeg;base64," + base64.b64encode((OUT / rel).read_bytes()).decode("ascii")


def assembler(ch):
    """index.html = modele.html avec les images affichées et les chiffres intégrés (page autonome).

    Le serveur local coupe parfois une réponse (antivirus) : intégrées, les images ne dépendent plus de lui, et la page
    s'ouvre aussi d'un double-clic. Les liens vers les grandes images et les visites restent des fichiers à part.
    """
    html = (OUT / "modele.html").read_text(encoding="utf-8")
    html = re.sub(r'<img src="(medias/[^"]+)"', lambda m: f'<img src="{data_uri(m.group(1))}"', html)
    integre = json.loads(json.dumps(ch))
    for p in integre.get("maladies_photos", []):
        if p.get("vignette"):
            p["vignette"] = data_uri(p["vignette"])
    marque = "const CHIFFRES_INTEGRES = null;"
    assert marque in html, "marque absente de modele.html"
    html = html.replace(marque, "const CHIFFRES_INTEGRES = " + json.dumps(integre, ensure_ascii=False) + ";")
    (OUT / "index.html").write_text(html, encoding="utf-8")
    print(f"index.html : {len(html.encode('utf-8')) / 1e6:.1f} Mo")


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    main()
