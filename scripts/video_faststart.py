#!/usr/bin/env python3
"""Place le bloc « moov » d'un MP4 avant les données (« faststart »), pour que le navigateur lance la lecture sans
attendre la fin du fichier. Les décalages des morceaux (stco / co64) sont corrigés de la taille du moov.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/video_faststart.py entree.mp4 sortie.mp4
"""
import struct
import sys

CONTENEURS = {b"moov", b"trak", b"mdia", b"minf", b"stbl", b"edts", b"dinf", b"udta"}


def blocs(d, debut, fin):
    o = debut
    while o < fin:
        taille, typ = struct.unpack(">I4s", d[o:o + 8])
        entete = 8
        if taille == 1:
            taille = struct.unpack(">Q", d[o + 8:o + 16])[0]
            entete = 16
        elif taille == 0:
            taille = fin - o
        yield o, taille, typ, entete
        o += taille


def corriger(moov, decalage):
    moov = bytearray(moov)

    def parcourir(debut, fin):
        for o, taille, typ, ent in blocs(moov, debut, fin):
            if typ in CONTENEURS:
                parcourir(o + ent, o + taille)
            elif typ == b"stco":
                n = struct.unpack(">I", moov[o + 12:o + 16])[0]
                for i in range(n):
                    p = o + 16 + 4 * i
                    v = struct.unpack(">I", moov[p:p + 4])[0] + decalage
                    if v > 0xFFFFFFFF:
                        raise SystemExit("décalage trop grand pour stco")
                    moov[p:p + 4] = struct.pack(">I", v)
            elif typ == b"co64":
                n = struct.unpack(">I", moov[o + 12:o + 16])[0]
                for i in range(n):
                    p = o + 16 + 8 * i
                    moov[p:p + 8] = struct.pack(">Q", struct.unpack(">Q", moov[p:p + 8])[0] + decalage)
    _, taille, _, ent = next(blocs(moov, 0, len(moov)))
    parcourir(ent, taille)
    return bytes(moov)


def main(entree, sortie):
    d = open(entree, "rb").read()
    tous = list(blocs(d, 0, len(d)))
    moov = [b for b in tous if b[2] == b"moov"]
    mdat = [b for b in tous if b[2] == b"mdat"]
    if not moov or not mdat:
        raise SystemExit("moov ou mdat absent")
    if moov[0][0] < mdat[0][0]:
        open(sortie, "wb").write(d)
        print("déjà en faststart")
        return
    o, t, _, _ = moov[0]
    bloc_moov = corriger(d[o:o + t], t)
    avant = b"".join(d[b[0]:b[0] + b[1]] for b in tous if b[0] < mdat[0][0])
    reste = b"".join(d[b[0]:b[0] + b[1]] for b in tous if b[0] >= mdat[0][0] and b[2] != b"moov")
    open(sortie, "wb").write(avant + bloc_moov + reste)
    print(f"faststart : moov ({t} octets) placé avant mdat -> {sortie}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
