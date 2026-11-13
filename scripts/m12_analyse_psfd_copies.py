#!/usr/bin/env python3
"""M-analyste (nuit du 12/11) : PSFD est-il un jeu augmenté (copies tournées, miroirs) ? Effet sur le compte des ratées.

1. Photo « tournée » : les 4 coins (8 x 8 px) sont noirs (valeur max < 20) -> copie tournée avec fond noir.
2. Groupes de quasi-copies : similarité cosinus des caractéristiques DINOv3 figées (photo entière) >= seuil,
   regroupement par composantes connexes (seuils 0,90 et 0,95), et dHash 64 bits sous 8 symétries <= 10 bits.
3. Ratées (installée, F1) par photo et par groupe : un groupe est « raté » si la majorité de ses photos l'est.
Même calcul sur TDTU, Éthiopie et la validation pour comparaison (taille des groupes).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_analyse_psfd_copies.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402

SORTIE = RACINE / "out/maladies/analyse"
T = pd.read_csv(SORTIE / "table_reglage.csv")
CARAC = RACINE / "out/maladies/nuit_1112/kaggle/caract_dinov3"
K1 = "F1_trois_morceaux2x2"


def coins_noirs(chemin):
    a = np.asarray(Image.open(B.fichier(chemin)).convert("L"))
    c = [a[:8, :8], a[:8, -8:], a[-8:, :8], a[-8:, -8:]]
    return all(x.max() < 20 for x in c)


def dhash(a):
    im = Image.fromarray(a).convert("L").resize((9, 8), Image.BILINEAR)
    x = np.asarray(im, int)
    return np.packbits((x[:, 1:] > x[:, :-1]).ravel())


def dhash8(chemin):
    a = np.asarray(Image.open(B.fichier(chemin)).convert("RGB"))
    vues = [a, a[:, ::-1], a[::-1], a[::-1, ::-1], a.transpose(1, 0, 2), a.transpose(1, 0, 2)[:, ::-1],
            a.transpose(1, 0, 2)[::-1], a.transpose(1, 0, 2)[::-1, ::-1]]
    return np.stack([dhash(np.ascontiguousarray(v)) for v in vues])


def composantes(adj):
    n = len(adj)
    lab = -np.ones(n, int)
    k = 0
    for i in range(n):
        if lab[i] >= 0:
            continue
        pile = [i]
        lab[i] = k
        while pile:
            u = pile.pop()
            for v in np.nonzero(adj[u])[0]:
                if lab[v] < 0:
                    lab[v] = k
                    pile.append(v)
        k += 1
    return lab


def main():
    idx = pd.read_csv(CARAC / "index_reglage.csv")
    F = np.load(CARAC / "caracteristiques_reglage.npy", mmap_mode="r")
    res = {}
    for j in ["psfd", "tdtu", "ethiopie", "validation"]:
        s = T[T.jeu == j].reset_index(drop=True)
        pos = pd.Series(np.arange(len(idx)), index=idx.chemin)
        X = np.asarray(F[pos[s.chemin].to_numpy(), 0], dtype="float32")
        X /= np.linalg.norm(X, axis=1, keepdims=True)
        sim = X @ X.T
        np.fill_diagonal(sim, 0)
        H = np.stack([dhash8(c) for c in s.chemin])           # (n, 8, 8 octets)
        bits = np.unpackbits(H, axis=2).reshape(len(s), 8, 64)
        ref = bits[:, 0]                                        # vue d'origine
        dist = np.full((len(s), len(s)), 99, np.int16)
        if len(s) <= 2000:
            for v in range(8):
                for a in range(0, len(s), 250):
                    d = (ref[a:a + 250, None, :] != bits[None, :, v, :]).sum(2)
                    dist[a:a + 250] = np.minimum(dist[a:a + 250], d)
        np.fill_diagonal(dist, 99)
        r = dict(n=len(s))
        for nom, adj in [("dino_0.90", sim >= 0.90), ("dino_0.95", sim >= 0.95), ("dhash_10", dist <= 10)]:
            lab = composantes(adj)
            s[nom] = lab
            tailles = pd.Series(lab).value_counts()
            r[nom] = dict(groupes=int(len(tailles)), photos_en_groupe=int(tailles[tailles > 1].sum()),
                          plus_gros=int(tailles.max()))
            if s.malade.any():
                m = s[s.malade]
                for ch, col in [("installee", "al_installee"), ("F1", f"al_{K1}")]:
                    g = m.groupby(nom)[col].apply(lambda x: (~x).mean())
                    r[nom][f"groupes_malades_{ch}_ratés"] = f"{int((g > 0.5).sum())}/{len(g)}"
        if j == "psfd":
            s["coins_noirs"] = [coins_noirs(c) for c in s.chemin]
            m = s[s.malade]
            r["coins_noirs"] = dict(total=int(s.coins_noirs.sum()),
                                    ratees_installee=f"{int((m.coins_noirs & ~m.al_installee).sum())}/{int((~m.al_installee).sum())}",
                                    ratees_F1=f"{int((m.coins_noirs & ~m[f'al_{K1}']).sum())}/{int((~m[f'al_{K1}']).sum())}",
                                    taux_ratees_F1_tournees=float((~m[m.coins_noirs][f"al_{K1}"]).mean()),
                                    taux_ratees_F1_droites=float((~m[~m.coins_noirs][f"al_{K1}"]).mean()),
                                    taux_ratees_inst_tournees=float((~m[m.coins_noirs].al_installee).mean()),
                                    taux_ratees_inst_droites=float((~m[~m.coins_noirs].al_installee).mean()))
            s[["chemin", "vraie", "coins_noirs", "dino_0.90", "dino_0.95", "dhash_10", "al_installee", f"al_{K1}"]].to_csv(
                SORTIE / "psfd_copies.csv", index=False)
        res[j] = r
        print(j, json.dumps(r, ensure_ascii=False))
    (SORTIE / "copies_bilan.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
