"""Encode une suite d'images PNG en vidéo MP4 (H.264) avec le séquenceur de Blender (FFmpeg intégré à Blender,
rien à installer ni à télécharger).

    blender.exe -b --factory-startup -P scripts/blender_video.py -- <dossier_images> <sortie.mp4> [largeur hauteur ips]
"""
import sys
from pathlib import Path

import bpy


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    dossier, sortie = Path(argv[0]), Path(argv[1])
    largeur = int(argv[2]) if len(argv) > 2 else 1280
    hauteur = int(argv[3]) if len(argv) > 3 else 720
    ips = int(argv[4]) if len(argv) > 4 else 24
    images = sorted(dossier.glob("image_*.png"))
    assert images, f"aucune image dans {dossier}"
    sc = bpy.context.scene
    se = sc.sequence_editor_create()
    pistes = se.strips if hasattr(se, "strips") else se.sequences       # Blender 5 : « strips »
    # une piste d'une image par image : ajouter des éléments à une seule piste fait planter Blender 5.2 en
    # arrière-plan (allocation aberrante vers la 35e image)
    for k, im in enumerate(images):
        pistes.new_image(name=f"i{k:04d}", filepath=str(im.resolve()), channel=1 + k % 2, frame_start=1 + k)
    sc.frame_start, sc.frame_end = 1, len(images)
    sc.render.fps = ips
    sc.render.resolution_x, sc.render.resolution_y = largeur, hauteur
    sc.render.resolution_percentage = 100
    # les images sont déjà finies (sRGB) : pas de transformation de vue (AgX par défaut les assombrirait)
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    iset = sc.render.image_settings
    if hasattr(iset, "media_type"):
        iset.media_type = "VIDEO"
    iset.file_format = "FFMPEG"
    ff = sc.render.ffmpeg
    ff.format = "MPEG4"
    ff.codec = "H264"
    ff.constant_rate_factor = "HIGH"
    ff.ffmpeg_preset = "GOOD"
    ff.gopsize = ips
    ff.audio_codec = "NONE"
    sc.render.use_sequencer = True
    sc.render.filepath = str(sortie)
    bpy.ops.render.render(animation=True)
    print(f"VIDEO {sortie} : {len(images)} images à {ips} i/s ({len(images) / ips:.1f} s)")


if __name__ == "__main__":
    main()
