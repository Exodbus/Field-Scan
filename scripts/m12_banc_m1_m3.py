#!/usr/bin/env python3
"""M1 (mélange v10b + soupe), M3 (seuils de la v10b) et idées libres, sur le réglage seulement (plan du 12/11, 4.3-4.4).

Aucun passage de réseau : probabilités en cache. Chaque configuration évaluée compte pour un essai.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/m12_banc_m1_m3.py
"""
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402
from fieldscan.modules import maladies  # noqa: E402

jeux = B.charger_reglage()
ref = B.reference(jeux)
ESSAIS = []          # (famille, nom, résultat, finaliste, détail)
GRILLE_T = [round(x, 2) for x in np.arange(0.30, 0.901, 0.02)]   # seuil sur P(saine) (règle B) : 31 valeurs


def essai(famille, nom, f_proche, jeux_=None, montrer=True):
    r = B.evaluer(jeux_ or jeux, f_proche)
    ok, detail = B.finaliste(r, ref)
    ESSAIS.append(dict(famille=famille, nom=nom, finaliste=ok, detail=detail, **r))
    if montrer:
        print(("F " if ok else "  ") + B.ligne(nom, r), flush=True)
    return r, ok


def so4(d):
    """Soupe ramenée aux 4 classes de la v10b : P(autre) = 0 (la soupe n'a pas cette classe)."""
    return np.hstack([d["Pso"], np.zeros((len(d["Pso"]), 1))])


def melange(d, w, geo=False, t10=None, tso=None):
    """w = poids de la soupe. Moyenne arithmétique, ou géométrique renormalisée ; températures facultatives avant mélange."""
    a, b = maladies.calibrer(d["P10"], t10), maladies.calibrer(so4(d), tso)
    if not geo:
        return (1 - w) * a + w * b
    # géométrique : sur 3 classes communes + « autre » de la v10b gardée telle quelle (pondérée par 1 - w)
    q = np.power(np.clip(a[:, :3], 1e-9, 1), 1 - w) * np.power(np.clip(b[:, :3], 1e-9, 1), w)
    q = np.hstack([q, (1 - w) * a[:, 3:]])
    return q / q.sum(1, keepdims=True)


def balayage(famille, nom, f_P, montrer_tout=False):
    """Grille du seuil sur P(saine) pour des probabilités f_P(d) ; affiche le meilleur finaliste et le minimax."""
    res = []
    for t in GRILLE_T:
        r, ok = essai(famille, f"{nom} t={t:.2f}", lambda d, t=t: B.decider_v10b(f_P(d), seuil=t), montrer=montrer_tout)
        res.append((t, r, ok))
    return res


def resume(res, nom):
    fin = [(t, r) for t, r, ok in res if ok]
    print(f"  {nom} : finalistes pour t dans {[t for t, _ in fin]}")
    if fin:
        t, r = min(fin, key=lambda x: x[1]["cout_moyen"])
        print("  meilleur finaliste : " + B.ligne(f"{nom} t={t:.2f}", r))
    t, r, ok = min(res, key=lambda x: max(x[1][j]["cout"] for j in B.REGLAGE))
    print(f"  minimax (pire coût des 4 jeux le plus bas, {max(r[j]['cout'] for j in B.REGLAGE):.1f}) : "
          + ("F " if ok else "non finaliste ") + B.ligne(f"{nom} t={t:.2f}", r))
    t, r, ok = min(res, key=lambda x: x[1]["cout_moyen"])
    print("  coût moyen le plus bas sans contrainte : " + ("F " if ok else "non finaliste ") + B.ligne(f"{nom} t={t:.2f}", r))


print("réf " + B.ligne("chaîne installée", ref))

print("\n=== M3 : seuil de confiance / règle B de la v10b (seuil sur P(saine)) ===")
m3 = balayage("M3", "v10b", lambda d: d["P10"], montrer_tout=True)
resume(m3, "M3 v10b")

print("\n=== M1 : mélange v10b + soupe, seuils de la v10b ===")
for w in (0.25, 0.5, 0.75):
    essai("M1", f"moyenne, poids soupe {w}", lambda d, w=w: B.decider_v10b(melange(d, w)))
essai("M1", "moyenne géométrique 0,5", lambda d: B.decider_v10b(melange(d, 0.5, geo=True)))
essai("M1", "moyenne 0,5, températures 0,79 / 0,61", lambda d: B.decider_v10b(melange(d, 0.5, t10=0.79, tso=0.61)))


def ou(d, et=False):
    r10, rso = B.decider_v10b(d["P10"]), maladies.decider_convnext(d["Pso"], B.M_SOUPE)[0]
    a10, aso = np.isin(r10, list(B.ALERTE)), np.isin(rso, list(B.ALERTE))
    if et:   # alerte seulement si les deux alertent : sinon « saine »
        return np.where(a10 & aso, r10, "saine")
    return np.where(a10, r10, np.where(aso, rso, r10))


essai("M1", "alerte si l'un des deux alerte", ou)
essai("M1", "alerte si les deux alertent", lambda d: ou(d, et=True))

print("\n=== M1 + M3 : mélange puis seuil sur P(saine) réglé ===")
for w in (0.25, 0.5, 0.75):
    resume(balayage("M1+M3", f"moyenne w={w}", lambda d, w=w: melange(d, w)), f"moyenne w={w}")
resume(balayage("M1+M3", "géométrique 0,5", lambda d: melange(d, 0.5, geo=True)), "géométrique 0,5")
resume(balayage("M1+M3", "moy 0,5 temp", lambda d: melange(d, 0.5, t10=0.79, tso=0.61)), "moyenne 0,5 températures")

print("\n=== M1 : « l'un des deux », seuils des deux modèles réglés (v10b : P(saine) < a ; soupe : P(saine) < b) ===")
GA, GB = [0.40, 0.46, 0.52, 0.58, 0.64, 0.70, 0.76], [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
ou2 = []
for a in GA:
    for b in GB:
        def f(d, a=a, b=b):
            r10 = B.decider_v10b(d["P10"], seuil=a)
            rso = maladies.decider_convnext(d["Pso"], B.M_SOUPE)[0]
            aso = d["Pso"][:, 0] < b
            rso = np.where(np.isin(rso, list(B.ALERTE)), rso, "malade_non_identifiee")
            return np.where(np.isin(r10, list(B.ALERTE)), r10, np.where(aso, rso, r10))
        r, ok = essai("M1 ou réglé", f"ou a={a} b={b}", f, montrer=False)
        ou2.append((a, b, r, ok))
print("  coût moyen (lignes a = seuil v10b, colonnes b = seuil soupe ; * = finaliste)")
for a in GA:
    print("  a=%.2f " % a + " ".join(f"{r['cout_moyen']:6.2f}{'*' if ok else ' '}" for aa, b, r, ok in ou2 if aa == a))
fin = [(a, b, r) for a, b, r, ok in ou2 if ok]
if fin:
    a, b, r = min(fin, key=lambda x: x[2]["cout_moyen"])
    print("  meilleur finaliste : " + B.ligne(f"ou a={a} b={b}", r))

print("\n=== Idée libre : seuil de l'aiguilleur (p_loin >= s -> v2) ===")
for s in (0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 0.97, 1.01):
    j2 = {j: {**d, "loin": d["p_loin"] >= s} for j, d in jeux.items()}
    essai("aiguilleur", f"aiguilleur s={s}" + (" (tout v2)" if s == 0 else " (tout v10b)" if s > 1 else ""),
          lambda d: B.decider_v10b(d["P10"]), jeux_=j2)

print("\n=== Idée libre : branche loin = alerte si la v2 ou la v10b alerte ===")
def loin_ou(d):
    r10 = B.decider_v10b(d["P10"])
    return r10
j3 = {}
for j, d in jeux.items():
    r10 = B.decider_v10b(d["P10"])
    rl = np.where(np.isin(d["r_loin"], list(B.ALERTE)), d["r_loin"], r10)
    j3[j] = {**d, "r_loin": rl}
essai("loin", "loin : v2 ou v10b", lambda d: B.decider_v10b(d["P10"]), jeux_=j3)
j4 = {}
for j, d in jeux.items():
    r10 = B.decider_v10b(d["P10"])
    rl = np.where(np.isin(d["r_loin"], list(B.ALERTE)) & np.isin(r10, list(B.ALERTE)), d["r_loin"], "saine")
    j4[j] = {**d, "r_loin": rl}
essai("loin", "loin : v2 et v10b", lambda d: B.decider_v10b(d["P10"]), jeux_=j4)

print("\n=== Détail par branche de la chaîne installée (où sont les erreurs) ===")
for j, d in jeux.items():
    rep = B.chaine(d, B.decider_v10b(d["P10"]))
    al = np.isin(rep, list(B.ALERTE))
    for nom, masque in (("proche", ~d["loin"]), ("loin", d["loin"])):
        m, s = d["malade"] & masque, ~d["malade"] & masque
        print(f"  {j:10s} {nom:6s} malades sans alerte {int((m & ~al).sum())}/{int(m.sum())} ; saines en alerte {int((s & al).sum())}/{int(s.sum())}")

print(f"\nNombre d'essais de ce script : {len(ESSAIS)}")
(B.SORTIE / "essais_m1_m3.json").write_text(json.dumps(ESSAIS, ensure_ascii=False, indent=1), encoding="utf-8")
