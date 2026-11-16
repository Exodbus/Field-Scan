"""Trailer Field Scan : contrôle du MP4 final.

- extrait une image toutes les 2 s dans out/video_trailer/controle/ (OpenCV) ;
- lit les boîtes MP4 pour confirmer la présence et la durée de la piste vidéo et de la piste son (codec, fréquence) ;
- mesure la crête et le niveau de la bande-son source (WAV) et signale les images noires ou figées.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/video_trailer_controle.py
"""
import struct
import wave
from pathlib import Path

import cv2
import numpy as np

RACINE = Path(__file__).resolve().parents[1]
MP4 = RACINE / "out/video_trailer/field_scan_trailer.mp4"
CTRL = RACINE / "out/video_trailer/controle"


def boites(data, debut, fin, chemin=""):
    i = debut
    while i + 8 <= fin:
        taille, typ = struct.unpack(">I4s", data[i:i + 8])
        typ = typ.decode("latin1")
        h = 8
        if taille == 1:
            taille = struct.unpack(">Q", data[i + 8:i + 16])[0]
            h = 16
        elif taille == 0:
            taille = fin - i
        yield chemin + "/" + typ, i + h, i + taille
        if typ in ("moov", "trak", "mdia", "minf", "stbl"):
            yield from boites(data, i + h, i + taille, chemin + "/" + typ)
        i += taille


def pistes():
    data = MP4.read_bytes()
    res = []
    cur = {}
    for ch, a, b in boites(data, 0, len(data)):
        if ch.endswith("/trak") and ch.count("/") == 2:
            if cur:
                res.append(cur)
            cur = {}
        if ch.endswith("/mdhd"):
            ver = data[a]
            if ver == 1:
                ts, dur = struct.unpack(">II", data[a + 20:a + 28])[0], struct.unpack(">Q", data[a + 24:a + 32])[0]
                ts = struct.unpack(">I", data[a + 20:a + 24])[0]
            else:
                ts, dur = struct.unpack(">II", data[a + 12:a + 20])
            cur["duree_s"] = dur / ts
            cur["echelle"] = ts
        if ch.endswith("/hdlr"):
            cur["type"] = data[a + 8:a + 12].decode("latin1")
        if ch.endswith("/stsd"):
            cur["codec"] = data[a + 12:a + 16].decode("latin1")
    if cur:
        res.append(cur)
    return res


def main():
    print("fichier :", MP4, f"{MP4.stat().st_size / 1e6:.1f} Mo")
    for p in pistes():
        print("  piste :", p)
    cap = cv2.VideoCapture(str(MP4))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"  vidéo : {cap.get(cv2.CAP_PROP_FRAME_WIDTH):.0f} x {cap.get(cv2.CAP_PROP_FRAME_HEIGHT):.0f}, {fps:.2f} i/s, {n} images, {n / fps:.2f} s")
    CTRL.mkdir(parents=True, exist_ok=True)
    for f in CTRL.glob("*.jpg"):
        f.unlink()
    precedent = None
    figees = []
    noires = []
    k = 0
    while True:
        ok, im = cap.read()
        if not ok:
            break
        t = k / fps
        if k % int(round(2 * fps)) == 0:
            cv2.imwrite(str(CTRL / f"t{int(round(t)):03d}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 90])
        utile = im[138:942]
        g = cv2.cvtColor(utile, cv2.COLOR_BGR2GRAY)
        if g.mean() < 2 and not (8.7 <= t <= 11.2 or t < 3.2 or 58.0 <= t <= 58.7 or t > 70):
            noires.append(round(t, 2))
        if precedent is not None and np.abs(g.astype(np.int16) - precedent).mean() < 0.02 and 3.2 < t < 8.6:
            figees.append(round(t, 2))
        precedent = g.astype(np.int16)
        k += 1
    print("  images noires hors passages prévus :", noires[:20])
    print("  images figées :", figees[:20])
    # bandes noires : lignes hors de la zone utile
    ok, im = cv2.VideoCapture(str(MP4)).read()
    print("  bande haute (moyenne) :", im[:130].mean().round(2), " bande basse :", im[950:].mean().round(2))
    w = wave.open(str(RACINE / "out/video_trailer/bande_son.wav"))
    x = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, 2) / 32768.0
    print(f"  WAV source : {w.getnframes() / w.getframerate():.1f} s, {w.getframerate()} Hz, "
          f"crête {20 * np.log10(np.abs(x).max()):.1f} dBFS, RMS {20 * np.log10(np.sqrt((x ** 2).mean())):.1f} dBFS, "
          f"échantillons écrêtés : {(np.abs(x) >= 0.999).sum()}")


if __name__ == "__main__":
    main()
