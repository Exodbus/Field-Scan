"""Vidéo de démonstration : montage et encodage dans le Video Sequence Editor de Blender (H.264, 1920 x 1080, 30 i/s).

Lit une suite d'images 0001.jpg, 0002.jpg... (par défaut out/video_demo/travail/seg_pitch) et écrit le MP4.
Pas d'audio.

    blender.exe -b --factory-startup -P scripts/video_demo_montage.py -- --images <dossier> --sortie <fichier.mp4>
"""
import argparse
import sys
from pathlib import Path

import bpy

RACINE = Path(__file__).resolve().parents[1]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--images", default=str(RACINE / "out/video_demo/travail/seg_pitch"))
ap.add_argument("--sortie", default=str(RACINE / "out/video_demo/field_scan_pitch_60s.mp4"))
a = ap.parse_args(argv)
dossier = Path(a.images).resolve()
fichiers = sorted(dossier.glob("*.jpg"))
sc = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1920, 1080, 100
sc.render.fps, sc.render.fps_base = 30, 1.0
se = sc.sequence_editor_create()
for k, f in enumerate(fichiers):  # un strip d'une image par fichier (les éléments ajoutés à un strip plantent Blender 5.2.4)
    st = se.strips.new_image(f"i{k:04d}", str(f), 1, k + 1)
sc.frame_start, sc.frame_end = 1, len(fichiers)
sc.render.use_sequencer = True
im = sc.render.image_settings
im.media_type = "VIDEO"
im.file_format = "FFMPEG"
ff = sc.render.ffmpeg
ff.format = "MPEG4"
ff.codec = "H264"
ff.constant_rate_factor = "MEDIUM"
ff.ffmpeg_preset = "GOOD"
ff.audio_codec = "NONE"
sc.view_settings.view_transform = "Standard"  # sans cela, AgX grise les blancs du montage
sc.render.filepath = a.sortie
Path(a.sortie).parent.mkdir(parents=True, exist_ok=True)
print("images :", len(fichiers), flush=True)
bpy.ops.render.render(animation=True)
print("MP4 écrit :", a.sortie, flush=True)
