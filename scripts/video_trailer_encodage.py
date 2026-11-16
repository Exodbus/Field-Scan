"""Trailer Field Scan : montage final dans le Video Sequence Editor de Blender (images + bande-son), sortie H.264 + AAC.

    blender.exe -b --factory-startup -P scripts/video_trailer_encodage.py -- --images <dossier jpg> --son <wav> --sortie <mp4>
"""
import argparse
import sys
from pathlib import Path

import bpy

RACINE = Path(__file__).resolve().parents[1]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--images", default=str(RACINE / "out/video_trailer/travail/seg_trailer"))
ap.add_argument("--son", default=str(RACINE / "out/video_trailer/bande_son.wav"))
ap.add_argument("--sortie", default=str(RACINE / "out/video_trailer/field_scan_trailer.mp4"))
ap.add_argument("--larg", type=int, default=1920)
ap.add_argument("--haut", type=int, default=1080)
ap.add_argument("--crf", default="HIGH")
a = ap.parse_args(argv)
fichiers = sorted(Path(a.images).glob("*.jpg"))
sc = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = a.larg, a.haut, 100
sc.render.fps, sc.render.fps_base = 24, 1.0
se = sc.sequence_editor_create()
for k, f in enumerate(fichiers):
    se.strips.new_image(f"i{k:04d}", str(f), 1, k + 1)
son = se.strips.new_sound("bande_son", a.son, 2, 1)
sc.frame_start, sc.frame_end = 1, len(fichiers)
sc.render.use_sequencer = True
im = sc.render.image_settings
im.media_type = "VIDEO"
im.file_format = "FFMPEG"
ff = sc.render.ffmpeg
ff.format = "MPEG4"
ff.codec = "H264"
ff.constant_rate_factor = a.crf
ff.ffmpeg_preset = "GOOD"
ff.audio_codec = "AAC"
ff.audio_bitrate = 256
ff.audio_channels = "STEREO"
ff.audio_mixrate = 48000
sc.view_settings.view_transform = "Standard"
sc.render.filepath = a.sortie
Path(a.sortie).parent.mkdir(parents=True, exist_ok=True)
print("images :", len(fichiers), "son :", son.name, flush=True)
bpy.ops.render.render(animation=True)
print("MP4 écrit :", a.sortie, flush=True)
