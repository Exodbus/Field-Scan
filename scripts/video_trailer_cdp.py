"""Petit client Chrome DevTools Protocol en bibliothèque standard (WebSocket maison) pour piloter Edge en mode headless.
Utilisé par video_trailer_visite.py pour capturer la vraie visite 3D web (out/visite_basse_pointe_zone) en mouvement.
Rien n'est installé ni téléchargé ; Edge est déjà présent sur le poste.
"""
import base64
import json
import os
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


class Ws:
    def __init__(self, url):
        assert url.startswith("ws://")
        hote, chemin = url[5:].split("/", 1)
        h, p = hote.split(":")
        self.s = socket.create_connection((h, int(p)), timeout=120)
        cle = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /{chemin} HTTP/1.1\r\nHost: {hote}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {cle}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        rep = b""
        while b"\r\n\r\n" not in rep:
            rep += self.s.recv(1)
        assert b" 101 " in rep.split(b"\r\n")[0], rep
        self.tampon = b""

    def envoyer(self, texte):
        d = texte.encode()
        n = len(d)
        entete = bytearray([0x81])
        if n < 126:
            entete.append(0x80 | n)
        elif n < 65536:
            entete += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            entete += bytes([0x80 | 127]) + struct.pack(">Q", n)
        masque = os.urandom(4)
        entete += masque
        self.s.sendall(bytes(entete) + bytes(b ^ masque[i % 4] for i, b in enumerate(d)))

    def _lire(self, n):
        while len(self.tampon) < n:
            morceau = self.s.recv(1 << 20)
            if not morceau:
                raise EOFError
            self.tampon += morceau
        r, self.tampon = self.tampon[:n], self.tampon[n:]
        return r

    def recevoir(self):
        msg = b""
        while True:
            b0, b1 = self._lire(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._lire(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._lire(8))[0]
            msg += self._lire(n)
            if b0 & 0x80:
                return msg.decode("utf-8", "replace")


class Edge:
    def __init__(self, port=9333, largeur=1920, hauteur=1080):
        self.dossier = tempfile.mkdtemp(prefix="edge_trailer_")
        self.proc = subprocess.Popen([
            EDGE, "--headless=new", f"--remote-debugging-port={port}", f"--window-size={largeur},{hauteur}",
            "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--hide-scrollbars",
            "--mute-audio", "--no-first-run", f"--user-data-dir={self.dossier}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
                cible = [p for p in pages if p.get("type") == "page"][0]
                break
            except Exception:
                time.sleep(0.5)
        self.ws = Ws(cible["webSocketDebuggerUrl"])
        self.n = 0
        self.evenements = []
        self.cmd("Page.enable")
        self.cmd("Runtime.enable")
        self.cmd("Emulation.setDeviceMetricsOverride", width=largeur, height=hauteur, deviceScaleFactor=1, mobile=False)

    def cmd(self, methode, **params):
        self.n += 1
        i = self.n
        self.ws.envoyer(json.dumps({"id": i, "method": methode, "params": params}))
        while True:
            m = json.loads(self.ws.recevoir())
            if m.get("id") == i:
                if "error" in m:
                    raise RuntimeError(f"{methode} : {m['error']}")
                return m.get("result", {})
            self.evenements.append(m)
            if len(self.evenements) > 500:
                self.evenements = self.evenements[-200:]

    def js(self, code):
        r = self.cmd("Runtime.evaluate", expression=code, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError(str(r["exceptionDetails"])[:400])
        return r.get("result", {}).get("value")

    def capture(self, chemin, qualite=92):
        r = self.cmd("Page.captureScreenshot", format="jpeg", quality=qualite)
        Path(chemin).write_bytes(base64.b64decode(r["data"]))

    def souris(self, x, y, bouton="left"):
        for t in ("mousePressed", "mouseReleased"):
            self.cmd("Input.dispatchMouseEvent", type=t, x=x, y=y, button=bouton, clickCount=1)

    def fermer(self):
        try:
            self.cmd("Browser.close")
        except Exception:
            pass
        try:
            self.proc.kill()
        except Exception:
            pass
