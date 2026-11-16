"""Trailer Field Scan : enchaîne le rendu 3D (Blender, Eevee, 4 fils) puis l'étalonnage de chaque plan. Reprise possible
(les images déjà rendues sont sautées).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/video_trailer_lancer.py [plan ...]
"""
import subprocess
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
BLENDER = r"C:\Users\coren\outils\blender_5.2.4\blender-5.2.4-windows-x64\blender.exe"
PY = str(RACINE / ".venv/Scripts/python.exe")
# plan -> cadence de rendu (le reste vient du flux optique ; le plan FPV est trop rapide pour être interpolé)
PLANS = [("grue", 12), ("final", 12), ("aube", 12), ("rangs", 12), ("orbite", 12), ("fpv", 24)]
choix = sys.argv[1:]
for plan, fps in PLANS:
    if choix and plan not in choix:
        continue
    t = time.time()
    cmd = [BLENDER, "-b", "--factory-startup", "-P", str(RACINE / "scripts/video_trailer_rendu3d.py"), "--", "--plan", plan,
           "--fps", str(fps), "--ech", "16", "--larg", "1920", "--haut", "804", "--fils", "4"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    lignes = [l for l in r.stdout.splitlines() if "IMAGE" in l]
    print(plan, "rendu : code", r.returncode, len(lignes), "images,", f"{time.time() - t:.0f} s", flush=True)
    if lignes:
        print("  dernière :", lignes[-1], flush=True)
    if r.returncode != 0:
        print(r.stdout[-1500:], r.stderr[-1500:], flush=True)
    t = time.time()
    env = {"PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([PY, "-I", "-u", str(RACINE / "scripts/video_trailer_etalonnage.py"), "--plan", plan, "--fps", str(fps)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env={**__import__("os").environ, **env})
    print(plan, "étalonnage : code", r.returncode, r.stdout.strip().splitlines()[-1:] , f"{time.time() - t:.0f} s", flush=True)
