"""Trailer Field Scan : bande-son synthétisée avec numpy (aucun échantillon, aucun téléchargement).

Éléments : drone grave qui monte (sinus + dents de scie filtrées), risers de bruit blanc filtré, impacts « braam »
(basse puissante, sous-grave, cuivres synthétiques, queue de réverbération), tambour grave qui accélère vers le climax,
silence juste avant le titre, accord final qui s'ouvre sur le titre puis s'éteint. Sortie : WAV stéréo 48 kHz.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/video_trailer_son.py --sortie out/video_trailer/bande_son.wav
    ... --essai       : 2 s d'essai (impact + montée) dans out/video_trailer/travail/essai_son.wav
"""
import argparse
import sys
import wave
from pathlib import Path

import numpy as np
from scipy import signal

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_trailer_decoupage as D  # noqa: E402

SR = 48000
rng = np.random.default_rng(2024)


def env_ad(n, a, d, courbe=3.0):
    t = np.arange(n) / SR
    att = np.clip(t / max(a, 1e-4), 0, 1)
    dec = np.exp(-courbe * np.clip(t - a, 0, None) / max(d, 1e-4))
    return att * dec


def lisse(x, f):
    """Passe-bas simple, f en Hz (scalaire)."""
    b, a = signal.butter(2, f / (SR / 2), "low")
    return signal.lfilter(b, a, x)


def passe_bande_variable(bruit, f0, f1, q=0.9, pas=1024):
    """Bruit filtré par un passe-bande dont la fréquence centrale va de f0 à f1 (échelle log), par blocs."""
    n = len(bruit)
    out = np.zeros(n)
    zi = None
    for i in range(0, n, pas):
        u = i / n
        f = f0 * (f1 / f0) ** u
        b, a = signal.butter(2, [max(f / (1 + 0.5 / q), 30) / (SR / 2), min(f * (1 + 0.5 / q), 20000) / (SR / 2)], "band")
        if zi is None:
            zi = signal.lfilter_zi(b, a) * 0
        seg, zi = signal.lfilter(b, a, bruit[i:i + pas], zi=zi)
        out[i:i + pas] = seg
    return out


def reverb(x, duree=2.8, mix=0.35, graine=1):
    r = np.random.default_rng(graine)
    n = int(duree * SR)
    t = np.arange(n) / SR
    ir_l = r.normal(0, 1, n) * np.exp(-t * 5.2) * (1 - np.exp(-t * 60))
    ir_r = r.normal(0, 1, n) * np.exp(-t * 5.2) * (1 - np.exp(-t * 60))
    ir_l = lisse(ir_l, 3500)
    ir_r = lisse(ir_r, 3500)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    wl = signal.fftconvolve(x[:, 0], ir_l)[:len(x)]
    wr = signal.fftconvolve(x[:, 1], ir_r)[:len(x)]
    w = np.stack([wl, wr], 1)
    w *= np.abs(x).max() / (np.abs(w).max() + 1e-9) * 0.9
    return x * (1 - mix * 0.5) + w * mix


class Piste:
    def __init__(self, duree):
        self.n = int(duree * SR)
        self.m = np.zeros((self.n, 2))

    def ajouter(self, t, x, pan=0.0, gain=1.0):
        i = int(t * SR)
        if i >= self.n:
            return
        x = x[:self.n - i] if i + len(x) > self.n else x
        g = np.array([np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)]) * gain * np.sqrt(2)
        if x.ndim == 1:
            self.m[i:i + len(x)] += x[:, None] * g
        else:
            self.m[i:i + len(x)] += x * gain

    def courbe(self, f):
        t = np.arange(self.n) / SR
        self.m *= f(t)[:, None]


# ------------------------------------------------------------------------------------------------------ sons
def braam(duree=4.5, f0=41.2, force=1.0):
    n = int(duree * SR)
    t = np.arange(n) / SR
    chute = f0 * (1 + 1.2 * np.exp(-t * 7))                    # glissement vers le grave
    ph = 2 * np.pi * np.cumsum(chute) / SR
    sub = np.sin(ph) * env_ad(n, 0.01, duree * 0.55, 3.0)
    cuivre = np.zeros(n)
    for dec in (0.0, 0.7, -0.6):                               # trois dents de scie désaccordées
        ph2 = 2 * np.pi * np.cumsum(f0 * 2 * (1 + dec / 100) * (1 + 0.5 * np.exp(-t * 4))) / SR
        cuivre += signal.sawtooth(ph2) / 3
    for k in range(3):                                         # filtre qui s'ouvre puis se referme
        pass
    ouv = 250 + 1400 * np.exp(-t * 2.2)
    out = np.zeros(n)
    pas = 512
    zi = None
    for i in range(0, n, pas):
        b, a = signal.butter(2, min(ouv[i], 8000) / (SR / 2), "low")
        if zi is None:
            zi = signal.lfilter_zi(b, a) * 0
        seg, zi = signal.lfilter(b, a, cuivre[i:i + pas], zi=zi)
        out[i:i + pas] = seg
    out *= env_ad(n, 0.04, duree * 0.5, 3.0)
    claque = lisse(rng.normal(0, 1, n), 1800) * env_ad(n, 0.002, 0.12, 4.0) * 0.6
    sig = (sub * 1.0 + out * 0.55 + claque) * force
    return sig


def grosse_caisse(force=1.0, tonalite=52.0):
    n = int(0.55 * SR)
    t = np.arange(n) / SR
    f = tonalite * (1 + 1.4 * np.exp(-t * 28))
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * env_ad(n, 0.002, 0.22, 4.5)
    clic = lisse(rng.normal(0, 1, n), 900) * env_ad(n, 0.0005, 0.02, 4.0) * 0.5
    return (s + clic) * force


def riser(duree, f0=200, f1=7000, force=1.0, panoramique=True):
    n = int(duree * SR)
    b = rng.normal(0, 1, (n, 2))
    out = np.stack([passe_bande_variable(b[:, 0], f0, f1), passe_bande_variable(b[:, 1], f0, f1)], 1)
    t = np.linspace(0, 1, n)
    out *= (t ** 2.2)[:, None] * force
    out /= np.abs(out).max() + 1e-9
    return out * force


def drone_grave(duree, f_deb=48.0, f_fin=96.0):
    n = int(duree * SR)
    t = np.arange(n) / SR
    u = t / duree
    f = f_deb * (f_fin / f_deb) ** (u ** 1.3)
    vib = 1 + 0.002 * np.sin(2 * np.pi * 0.23 * t)
    sig_l = np.zeros(n)
    sig_r = np.zeros(n)
    for k, (m, g) in enumerate(((1.0, 1.0), (1.5, 0.45), (2.0, 0.35), (3.0, 0.14))):
        for lado, deriv in ((0, 0.9987), (1, 1.0013)):
            ph = 2 * np.pi * np.cumsum(f * vib * m * deriv) / SR
            s = (np.sin(ph) if k == 0 else signal.sawtooth(ph) * 0.5) * g
            (sig_l if lado == 0 else sig_r)[:] += s
    # filtre qui s'ouvre
    out = []
    for sig in (sig_l, sig_r):
        o = np.zeros(n)
        zi = None
        for i in range(0, n, 2048):
            fc = 140 + 1800 * (i / n) ** 1.6
            b, a = signal.butter(2, fc / (SR / 2), "low")
            if zi is None:
                zi = signal.lfilter_zi(b, a) * 0
            seg, zi = signal.lfilter(b, a, sig[i:i + 2048], zi=zi)
            o[i:i + 2048] = seg
        out.append(o)
    return np.stack(out, 1)


def accord_final(duree):
    n = int(duree * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for f, g, pan in ((55.0, 1.0, 0), (110.0, 0.6, -0.2), (164.8, 0.5, 0.25), (220.0, 0.45, -0.3), (261.6, 0.32, 0.3),
                      (329.6, 0.25, 0.1), (440.0, 0.12, -0.15)):
        for det in (0.998, 1.002):
            s = np.sin(2 * np.pi * f * det * t + rng.uniform(0, 6.28)) * g * 0.4
            s += signal.sawtooth(2 * np.pi * f * det * t) * g * 0.07
            out += s[:, None] * np.array([1 - max(pan, 0), 1 + min(pan, 0)])
    env = np.clip(t / 2.5, 0, 1) ** 2 * np.exp(-np.clip(t - 5.0, 0, None) / 3.0)
    return lisse(out[:, 0], 2500)[:, None] * env[:, None] * np.array([1, 0]) + lisse(out[:, 1], 2500)[:, None] * env[:, None] * np.array([0, 1])


def etincelle(duree=3.5):
    """Scintillement aigu pour le slogan."""
    n = int(duree * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for k, f in enumerate((880.0, 1318.5, 1760.0, 2637.0)):
        d = 0.18 * k
        e = env_ad(n, 0.01, 1.2, 4.0)
        e = np.roll(e, int(d * SR))
        e[:int(d * SR)] = 0
        s = np.sin(2 * np.pi * f * t) * e * 0.05
        out += s[:, None] * np.array([1 - 0.3 * (k % 2), 0.7 + 0.3 * (k % 2)])
    return out


# ------------------------------------------------------------------------------------------------------ mix
def mixer(duree):
    P = Piste(duree)
    T = D.T
    # fond : drone qui monte de 0 à 58 s, silence net de 58,0 à 58,6 s
    dr = drone_grave(D.TITRE_IMPACT, 46.0, 98.0)
    n = len(dr)
    t = np.arange(n) / SR
    niv = np.clip(t / 6.0, 0, 1) ** 1.5 * 0.55 + np.clip((t - 8.7) / 40.0, 0, 1) * 0.45
    niv *= np.where(t > 57.95, np.clip(1 - (t - 57.95) / 0.04, 0, 1), 1.0)
    P.ajouter(0.0, dr * niv[:, None], gain=0.55)
    # petit tapis de sons graves sur noir : cœur sourd
    # risers
    P.ajouter(7.6, riser(3.6, 250, 3500, 0.6), gain=0.35)                 # vers « Jusqu'à aujourd'hui »
    P.ajouter(8.7, riser(2.5, 300, 6000, 0.7), gain=0.30)
    P.ajouter(19.5, riser(4.5, 300, 9000, 0.8), gain=0.40)                # fin de la montée
    P.ajouter(44.5, riser(3.5, 300, 7000, 0.7), gain=0.30)
    P.ajouter(50.0, riser(7.9, 250, 12000, 1.0), gain=0.55)               # grande montée avant le titre
    # braams
    for t0, f, g in ((D.T["montee"][0], 41.2, 0.9), (24.0, 43.65, 0.8), (32.0, 46.25, 0.8), (40.0, 49.0, 0.85),
                     (48.0, 55.0, 0.95), (D.TITRE_IMPACT, 36.7, 1.5)):
        P.ajouter(t0, braam(5.0 if t0 < 58 else 7.5, f, 1.0), gain=g * 0.9)
    # tambour : battements qui accélèrent
    temps = []
    t0 = 11.2
    for c in D.MONTEE:                                   # un coup sur chaque coupe de la montée
        temps.append(c[0])
    temps += [D.MONTEE[-1][0] + 0.5]
    t = 24.0
    for k in range(8):                                   # pouls calme pendant les trois pouvoirs
        pass
    for deb, fin in ((24.0, 48.0),):
        t = deb + 1.0
        while t < fin - 0.5:
            temps.append(t)
            t += 1.0 if t < 40 else 0.8
    t = 48.0
    iv = 0.62
    while t < 57.8:                                      # accélération vers le climax
        temps.append(t)
        t += iv
        iv = max(iv * 0.93, 0.095)
    for i, tt in enumerate(sorted(temps)):
        fort = 1.0 if tt in [c[0] for c in D.MONTEE] or tt > 48 else 0.7
        P.ajouter(tt, grosse_caisse(fort, 50.0 + 6 * (tt > 48)), gain=0.70, pan=0.0)
    # petits coups graves sur les mots de la première partie (apparition du texte)
    for tt in (0.9, 5.2, 8.9):
        P.ajouter(tt, grosse_caisse(0.8, 40.0), gain=0.6)
    # après le silence : accord, étincelle du slogan
    P.ajouter(D.TITRE_IMPACT, accord_final(duree - D.TITRE_IMPACT), gain=0.55)
    P.ajouter(D.SLOGAN, etincelle(), gain=1.0)
    # réverbération globale
    m = reverb(P.m, 3.0, 0.32)
    # silence juste avant le titre
    t = np.arange(len(m)) / SR
    coupe = np.where((t > 57.95) & (t < D.TITRE_IMPACT - 0.02), 0.03, 1.0)
    coupe = np.minimum(coupe, np.clip((t - 57.95) / 0.0001 * 0 + 1, 0, 1))
    m *= coupe[:, None]
    # fondu d'entrée et de sortie
    m *= np.clip(t / 0.4, 0, 1)[:, None] * np.clip((duree - t) / 2.0, 0, 1)[:, None]
    return m


def normaliser(m, crete_db=-1.5):
    # écrêtage doux (pas de saturation dure) puis normalisation à la crête voulue
    m = m - m.mean(0)
    pic = np.abs(m).max()
    m = np.tanh(m / (pic * 0.9)) * 0.9 * pic
    m = m / np.abs(m).max() * 10 ** (crete_db / 20)
    return m


def ecrire_wav(chemin, m):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(m, -1, 1) * 32767).astype("<i2")
    with wave.open(str(chemin), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default=str(RACINE / "out/video_trailer/bande_son.wav"))
    ap.add_argument("--essai", action="store_true")
    a = ap.parse_args()
    if a.essai:
        P = Piste(2.0)
        P.ajouter(0.0, grosse_caisse(1.0), gain=0.8)
        P.ajouter(0.05, braam(1.95, 41.2), gain=0.9)
        P.ajouter(0.0, riser(2.0, 300, 8000, 0.5), gain=0.2)
        m = normaliser(reverb(P.m, 1.2, 0.3))
        ecrire_wav(RACINE / "out/video_trailer/travail/essai_son.wav", m)
        print("essai : crête", np.abs(m).max(), "durée", len(m) / SR)
        return
    m = normaliser(mixer(D.DUREE))
    ecrire_wav(Path(a.sortie), m)
    rms = np.sqrt((m ** 2).mean())
    print(f"bande-son : {len(m) / SR:.1f} s, crête {20 * np.log10(np.abs(m).max()):.1f} dBFS, RMS {20 * np.log10(rms):.1f} dBFS")


if __name__ == "__main__":
    main()
