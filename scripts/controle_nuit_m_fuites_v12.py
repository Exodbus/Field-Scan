#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : le modèle final v12a4 a-t-il appris une photo des juges ?

Le modèle final v12a4 apprend, en plus de ce qu'apprenait la v10b, TDTU et l'Éthiopie (et Mendeley wfzpdmc5vx, Tanzanie
2021, Pérou saines et Sigatoka). Je compare ces photos d'apprentissage aux juges (BanSpot, Cordana du Pérou) **sans
ouvrir une seule image des juges** : seulement les empreintes déjà calculées (vignette 16 x 16 couleur, dHash 64 bits,
SHA-256) par D-maladies (data/raw/nuit_1112/_controle/references_extra.npz) et par l'évaluateur du 9/11
(out/maladies/equipe/evaluateur/test_de_loin/references_fuites.npz). Critère de D-maladies : écart moyen des vignettes
<= 5 (sur 255) sous les 8 symétries, ou dHash <= 10 bits (orientation d'origine), ou SHA-256 égal.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_m_fuites_v12.py
"""
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
OUT = RACINE / "out/controle_nuit_1112"


def sym(v):
    out = []
    for f in (False, True):
        w = v[:, :, ::-1] if f else v
        for k in range(4):
            out.append(np.rot90(w, k, axes=(1, 2)))
    return out


def main():
    X = np.load(RACINE / "data/raw/nuit_1112/_controle/references_extra.npz", allow_pickle=True)
    Y = np.load(RACINE / "out/maladies/equipe/evaluateur/test_de_loin/references_fuites.npz", allow_pickle=True)
    cy = np.array([str(k).replace(chr(92), "/") for k in Y["cle"]])
    sx = X["source"].astype(str)
    okx = X["lisible"].astype(bool)
    groupes_j = {"banspot": (X["v"][(sx == "banspot") & okx], X["h"][(sx == "banspot") & okx], X["sha"][(sx == "banspot") & okx]),
                 "cordana_perou": (Y["v"][np.char.find(cy, "test_perou/inconnue_cordana") >= 0],
                                   Y["h"][np.char.find(cy, "test_perou/inconnue_cordana") >= 0], None)}
    m_ent = np.char.find(cy, "data/feuilles/images/entrainement/") >= 0
    m_tdtu = np.char.find(cy, "data/feuilles_v3_ajouts/images/tdtu/") >= 0
    appr = {"tanzanie2021_perou": (Y["v"][m_ent], Y["h"][m_ent], None),
            "tdtu": (Y["v"][m_tdtu], Y["h"][m_tdtu], None),
            "ethiopie": (X["v"][(sx == "ethiopie_2021") & okx], X["h"][(sx == "ethiopie_2021") & okx], X["sha"][(sx == "ethiopie_2021") & okx]),
            "wfzpdmc5vx": (X["v"][(sx == "mendeley_wfzpdmc5vx") & okx], X["h"][(sx == "mendeley_wfzpdmc5vx") & okx],
                           X["sha"][(sx == "mendeley_wfzpdmc5vx") & okx])}
    lignes, res = [], {}
    lignes.append("effectifs : " + ", ".join(f"{k} {len(v[0])}" for k, v in {**groupes_j, **appr}.items()))
    for nj, (vj, hj, shj) in groupes_j.items():
        vj = vj.astype("float32")
        S = [s.reshape(len(vj), -1) for s in sym(vj)]
        for na, (va, ha, sha) in appr.items():
            A = va.astype("float32").reshape(len(va), -1)
            a2 = (A ** 2).sum(1)
            n_v, exemples = 0, []
            for q in S:
                for i0 in range(0, len(q), 512):
                    Q = q[i0:i0 + 512]
                    d2 = (Q ** 2).sum(1)[:, None] + a2[None, :] - 2 * Q @ A.T
                    ii, jj = np.nonzero(d2 <= (12.0 ** 2) * A.shape[1])      # préfiltre RMS <= 12
                    for i, j in zip(ii, jj):
                        if np.abs(Q[i] - A[j]).mean() <= 5:
                            n_v += 1
                            exemples.append((int(i0 + i), int(j)))
            hj64 = np.array([int(x) & ((1 << 64) - 1) if x is not None else 0 for x in hj], dtype=np.uint64)
            ha64 = np.array([int(x) & ((1 << 64) - 1) if x is not None else 0 for x in ha], dtype=np.uint64)
            n_h = 0
            for i0 in range(0, len(hj64), 256):
                x = np.bitwise_xor(hj64[i0:i0 + 256, None], ha64[None, :])
                bits = np.unpackbits(x.view(np.uint8).reshape(x.shape + (8,)), axis=-1).sum(-1)
                n_h += int((bits <= 10).sum())
            n_sha = len(set(map(str, shj)) & set(map(str, sha))) if shj is not None and sha is not None else None
            res[f"{nj}~{na}"] = dict(vignettes=n_v, dhash=n_h, sha=n_sha, exemples=exemples[:10])
            lignes.append(f"{nj} contre {na} : paires vignette <= 5 (8 symétries) {n_v} ; dHash <= 10 bits {n_h} ; SHA-256 communs {n_sha}")
    (OUT / "m_fuites_v12.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "m_fuites_v12.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))


if __name__ == "__main__":
    main()
