"""Trailer Field Scan : captures de la VRAIE visite 3D web (out/visite_basse_pointe_zone, servie sur localhost:8770) avec
Edge en mode headless, pilotées par le protocole DevTools (scripts/video_trailer_cdp.py). Le rendu logiciel (SwiftShader)
met environ 15 s par capture : on prend donc des états successifs de l'interface (ensemble, parcelle R054 sélectionnée,
« Marcher au bord », mode Santé), et le montage les relie par des mouvements de caméra simulés.
Le dossier de la visite n'est pas modifié (lecture seule via le serveur).

    (serveur) .venv/Scripts/python.exe -m http.server 8770 -d out        puis :
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/video_trailer_visite.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_trailer_cdp as C

SORTIE = Path(__file__).resolve().parents[1] / "out/video_trailer/travail/visite"
SORTIE.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8770/visite_basse_pointe_zone/index.html"


def attendre(e, s, msg):
    print(f"  attente {s} s : {msg}", flush=True)
    time.sleep(s)


e = C.Edge()
try:
    e.cmd("Page.navigate", url=URL)
    attendre(e, 40, "chargement de la page et de three.js")
    e.js("document.querySelector('#b-commencer').click()")
    attendre(e, 110, "vue d ensemble, tuiles")
    e.capture(SORTIE / "s1_ensemble_a.jpg", 95)
    e.capture(SORTIE / "s1_ensemble_b.jpg", 95)
    lignes = e.js("[...document.querySelectorAll('#liste .ligne')].map(l => l.innerText.replace(/\s+/g,' ')).join(' | ')")
    print("lignes :", lignes, flush=True)
    # clic sur R054 dans la liste -> survol et fiche
    e.js("[...document.querySelectorAll('#liste .ligne')].find(l => l.innerText.includes('R054')).click()")
    attendre(e, 6, "survol vers R054")
    e.capture(SORTIE / "s2_r054_a.jpg", 95)
    attendre(e, 12, "arrivée sur R054")
    e.capture(SORTIE / "s2_r054_b.jpg", 95)
    print("fiche :", e.js("(document.querySelector('#fiche')||document.body).innerText.slice(0,300)"), flush=True)
    # Marcher au bord
    e.js("document.querySelector('#f-marcher').click()")
    attendre(e, 6, "marche au bord")
    e.capture(SORTIE / "s3_marche_a.jpg", 95)
    attendre(e, 10, "marche, suite")
    e.capture(SORTIE / "s3_marche_b.jpg", 95)
    # mode Santé et zones
    e.js("document.querySelector('#f-sante').click()")
    attendre(e, 10, "mode Santé, zones")
    e.capture(SORTIE / "s4_sante_a.jpg", 95)
    attendre(e, 10, "mode Santé, suite")
    e.capture(SORTIE / "s4_sante_b.jpg", 95)
    e.js("document.querySelector('#b-ensemble').click()")
    attendre(e, 12, "retour vue d'ensemble en mode Santé")
    e.capture(SORTIE / "s5_ensemble_sante.jpg", 95)
    print("captures terminées", flush=True)
finally:
    e.fermer()
