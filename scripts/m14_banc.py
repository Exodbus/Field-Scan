#!/usr/bin/env python3
"""Banc de M-piste2 (14/11) : mélanges F1 + élève (MC1), règle de désaccord (MC2), et mesure des élèves Kaggle (MC3).
Règles écrites avant tout calcul : docs/nuit_2026-11-13/journal_m_piste2.md (18 h 50). Règle « finaliste » : plan 4.3.

Données (aucun juge) :
- 4 anciens jeux et AgroVisionBD : scripts/m13_banc_commun.charger (morceaux connus ; ailleurs méthode des bornes) ;
  morceaux d'AgroVisionBD lus par M-piste2 en plus : out/maladies/nuit_1311/piste2/g2_agrovision_p2.npz ;
- roamer_dev_loin_feuilles : maître de F1 (out/maladies/nuit_1311/kaggle/maitre/maitre_roamer_dev_loin.npz) + aiguilleur ;
- élèves : fichiers predictions_<nom>_<jeu>.csv (format des caches).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m14_banc.py mc12
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
from fieldscan.modules import maladies  # noqa: E402
import m12_banc_commun as B  # noqa: E402
import m13_banc_commun as C  # noqa: E402

SORTIE = RACINE / "out/maladies/nuit_1311/piste2"
SORTIE.mkdir(parents=True, exist_ok=True)
KAG = RACINE / "out/maladies/nuit_1311/kaggle"
JEUX5 = C.JEUX5
TOUS = JEUX5 + ["roamer"]
COLS = ["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]
ALERTE = list(B.ALERTE)
M_P = lambda s: {**B.M_V10B, "seuil": s}   # noqa: E731


# --------------------------------------------------------------------------------------------------------------------
def charger():
    jeux = C.charger(roamer=False)
    g2 = SORTIE / "g2_agrovision_p2.npz"   # morceaux lus par M-piste2 (bornes), en plus de ceux de M-banc
    if g2.exists():
        z = np.load(g2)
        jeux["agrovision"]["G2"][z["indices"]] = z["g2"]
    pr = pd.read_csv(KAG / "p_loin_roamer_dev_loin.csv")
    z = np.load(KAG / "maitre" / "maitre_roamer_dev_loin.npz", allow_pickle=True)
    assert list(z["chemin"]) == list(pr.chemin)
    jeux["roamer"] = C._d(np.array(pr.chemin, dtype=object), pr.etat, pr.etat.eq("malade").values, z["P10"], z["Pso"],
                          z["Pv2"], pr.p_loin.values, z["G2"])
    return jeux


def cle(j, chemins):
    """Chemins des caches des élèves -> ordre du banc."""
    if j == "agrovision":
        return [str(c) for c in chemins]
    return [str(c) for c in chemins]


def lire_eleve(jeux, dossier, nom, en_plus=()):
    """Probabilités d'un élève (moyenne de plusieurs dossiers/noms si en_plus) dans l'ordre du banc."""
    srcs = [(Path(dossier), nom)] + [(Path(d), n) for d, n in en_plus]
    for j, d in jeux.items():
        jj = "roamer_dev_loin" if j == "roamer" else j
        Ps = []
        for dos, n in srcs:
            df = pd.read_csv(dos / f"predictions_{n}_{jj}.csv").set_index("chemin")
            Ps.append(df.loc[cle(j, d["chemin"]), COLS].to_numpy("float64"))
        d["D"] = np.mean(Ps, 0)
        assert np.isfinite(d["D"]).all() and d["D"].shape == (len(d["chemin"]), 4)


def lire_kaggle(jeux, sources):
    """Forme « ensemble livrable » (M-entraîneur) : TDTU et Éthiopie lus par le(s) réseau(x) qui ne les ont pas appris
    (predictions_<nom>_<jeu>.csv) ; autres jeux : moyenne des réseaux des 2 plis (predictions_<nom>_<jeu>_pli_*.csv).
    Plusieurs recettes : moyenne de tous les réseaux."""
    for j, d in jeux.items():
        jj = "roamer_dev_loin" if j == "roamer" else j
        fs = []
        for dos, n in sources:
            if j in ("tdtu", "ethiopie"):
                fs.append(Path(dos) / f"predictions_{n}_{jj}.csv")
            else:
                t = sorted(Path(dos).glob(f"predictions_{n}_{jj}_pli_*.csv"))
                assert len(t) == 2, (dos, n, jj, t)
                fs += t
        Ps = [pd.read_csv(f).set_index("chemin").loc[cle(j, d["chemin"]), COLS].to_numpy("float64") for f in fs]
        d["D"] = np.mean(Ps, 0)
        assert np.isfinite(d["D"]).all()


# --------------------------------------------------------------------------------------------------------------------
# Règles. Chaque règle : (d, G2) -> réponses ; toutes croissantes en P(malade) des morceaux (bornes valables).
def f1(d, G2):
    return C.f1(d, G2)


def chaine_eleve(d, G2=None, sp=0.50, sl=0.70):
    rp = maladies.decider_convnext(d["D"], M_P(sp))[0]
    rl = maladies.decider_convnext(d["D"], M_P(sl))[0]
    loin = np.where(np.isin(d["r_loin"], ALERTE), d["r_loin"], rl)
    return np.where(d["loin"], loin, rp).astype(object)


def mc1_ou(d, G2):
    a, b = f1(d, G2), chaine_eleve(d)
    return np.where(np.isin(a, ALERTE), a, b)


def mc1_v(d, G2):
    a, b = f1(d, G2), chaine_eleve(d)
    sur = np.isin(b, ALERTE) & (b != "a_verifier")
    return np.where(~np.isin(a, ALERTE) & sur, "a_verifier", a).astype(object)


def mc1_g(w):
    sp = 0.70 * (1 - w) + 0.50 * w

    def regle(d, G2):
        F = maladies.melange_geometrique(maladies.lecture_morceaux(d["P10"], G2), d["Pso"], d["Pv2"])
        lg = (1 - w) * np.log(np.clip(F, 1e-9, 1)) + w * np.log(np.clip(d["D"], 1e-9, 1))
        P = np.exp(lg - lg.max(1, keepdims=True))
        P /= P.sum(1, keepdims=True)
        rp = maladies.decider_convnext(P, M_P(sp))[0]
        rl = maladies.decider_convnext(P, M_P(0.70))[0]
        loin = np.where(np.isin(d["r_loin"], ALERTE), d["r_loin"], rl)
        return np.where(d["loin"], loin, rp).astype(object)
    return regle


def mc1_vote(d, G2):
    """Essai 7 (journal, 18 h 45) : alerte forte de F1 ou de l'élève, ou alerte des deux."""
    a, b = f1(d, G2), chaine_eleve(d)
    aa, ab = np.isin(a, ALERTE), np.isin(b, ALERTE)
    fa, fb = aa & (a != "a_verifier"), ab & (b != "a_verifier")
    garde = fa | fb | (aa & ab)
    return np.where(garde, np.where(aa, a, b), "saine").astype(object)


def mc1_ou_proche(d, G2):
    """Essai 8 : MC1-OU sur les photos « proches », F1 sur les photos « loin »."""
    return np.where(d["loin"], f1(d, G2), mc1_ou(d, G2)).astype(object)


def m2_morceaux(s):
    """Essais 15-16 (veille M2) : F1, et « à vérifier » si au moins 2 morceaux sur 4 ont P(malade) >= s."""
    def regle(d, G2):
        a = f1(d, G2)
        n = ((1 - G2[:, :, 0]) >= s).sum(1)
        return np.where(~np.isin(a, ALERTE) & (n >= 2), "a_verifier", a).astype(object)
    return regle


def m5_conforme(jeux, ref):
    """Essai 17 (veille M5, diagnostic) : seuil t du lecteur proche de F1 choisi sur 4 jeux par contrôle conformel du
    risque (taux de ratées <= alpha), mesuré sur le 5e."""
    grille = np.round(np.arange(0.70, 0.995, 0.01), 2)
    tab = {}
    for t in grille:
        regle = lambda d, G2, t=t: maladies.decider_melange(d["P10"], d["Pso"], d["Pv2"], d["p_loin"], G2, M_P(t), B.M_V2, True)[0]  # noqa: E731
        tab[float(t)] = C.evaluer(jeux, regle, JEUX5)
    out = {}
    for alpha in (0.01, 0.02):
        par = {}
        for h in JEUX5:
            autres = [j for j in JEUX5 if j != h]
            n = sum(ref[j]["nm"] for j in autres)
            t_ok = [t for t in tab if (sum(tab[t][j]["msa"] for j in autres) + 1) / (n + 1) <= alpha]
            t = min(t_ok) if t_ok else None
            if t is None:
                par[h] = dict(seuil=None)
                continue
            m = tab[t][h]
            par[h] = dict(seuil=t, taux_ratees=m["msa"] / m["nm"], alpha=alpha, sea=m["sea"], ns=m["ns"], msa=m["msa"],
                          nm=m["nm"], cout=m["cout"], inconnues=m.get("inconnues", 0))
        out[f"alpha_{alpha}"] = par
    return out


def mc2(k):
    def regle(d, G2):
        a = f1(d, G2)
        n = sum((P[:, 0] < 0.5).astype(int) for P in (d["P10"], d["Pso"], d["Pv2"], d["D"]))
        return np.where(~np.isin(a, ALERTE) & (n >= k), "a_verifier", a).astype(object)
    return regle


# --------------------------------------------------------------------------------------------------------------------
def evaluer(jeux, regle):
    r = C.evaluer(jeux, regle, TOUS)
    r["msa_total5"] = int(sum(r[j]["msa"] for j in JEUX5))
    return r


def conditions(r, ref, jeux_=JEUX5):
    """Règle 4.3 (sans le temps) restreinte aux jeux donnés (coût moyen sur ces jeux)."""
    cr = float(np.mean([r[j]["cout"] for j in jeux_]))
    cf = float(np.mean([ref[j]["cout"] for j in jeux_]))
    c = dict(cout=cr <= cf - 1.0,
             tanzanie=("validation" not in jeux_) or (r["validation"]["msa"] <= 14 and r["validation"]["sea"] <= 77),
             pays=all(100 * (r[j]["msa"] / r[j]["nm"] - ref[j]["msa"] / ref[j]["nm"]) <= 2.0 for j in jeux_),
             roamer=r["roamer"]["msa"] <= ref["roamer"]["msa"] + 2)
    return all(c.values()), c, cr


def choisir(cands, ref, jeux_=JEUX5):
    """Règle de choix (journal, 18 h 50) : parmi ceux qui passent, coût le plus bas ; à 0,1 près, moins de malades ratées."""
    ok = []
    for nom, r in cands.items():
        p, _, cr = conditions(r, ref, jeux_)
        if p:
            ok.append((cr, sum(r[j]["msa"] for j in jeux_), nom))
    if not ok:
        return None
    m = min(c for c, _, _ in ok)
    proches = [x for x in ok if x[0] <= m + 0.1]
    return min(proches, key=lambda x: (x[1], x[0]))[2]


def croise(cands, ref):
    """Coût croisé : choix sur 4 jeux, mesure sur le 5e ; si rien ne passe sur les 4, on garde F1 pour le 5e."""
    out, choix = [], {}
    for h in JEUX5:
        autres = [j for j in JEUX5 if j != h]
        n = choisir(cands, ref, autres)
        choix[h] = n or "F1"
        out.append((cands[n] if n else ref)[h]["cout"])
    return float(np.mean(out)), choix


def ecart(r, ref):
    diff = sum(int((r[j]["_alerte"] != ref[j]["_alerte"]).sum()) for j in JEUX5)
    n = sum(len(r[j]["_alerte"]) for j in JEUX5)
    plus = sum(int((ref[j]["_alerte"] & ~r[j]["_alerte"] & jeux_global[j]["malade"]).sum()) for j in JEUX5)
    moins = sum(int((~ref[j]["_alerte"] & r[j]["_alerte"] & jeux_global[j]["malade"]).sum()) for j in JEUX5)
    return dict(alertes_differentes=diff, photos=n, malades_perdues_vs_F1=plus, malades_rattrapees_vs_F1=moins)


def resume(nom, r, ref):
    p, c, _ = conditions(r, ref)
    e = ecart(r, ref)
    inc = sum(r[j].get("inconnues", 0) for j in TOUS)
    return dict(nom=nom, cout_reglage=r["cout_reglage"], msa_total5=r["msa_total5"], roamer_msa=r["roamer"]["msa"],
                finaliste_sans_temps=p, conditions=c, inconnues=inc, **e,
                par_jeu={j: {k: v for k, v in r[j].items() if not k.startswith("_")} for j in TOUS})


def ligne(nom, r):
    return C.ligne(nom, r) + f" | ratées5={r['msa_total5']}"


jeux_global = None


def main():
    global jeux_global
    quoi = sys.argv[1]
    jeux = charger()
    jeux_global = jeux
    lire_eleve(jeux, KAG / "pour_banc/d3b", "d3b")
    ref = evaluer(jeux, f1)
    rd = evaluer(jeux, chaine_eleve)
    print(ligne("F1 (référence)", ref))
    print(ligne("d3b (référence)", rd))
    res = {"F1": resume("F1", ref, ref), "d3b": resume("d3b", rd, ref)}
    if quoi == "mc12":
        regles = {"MC1-OU": mc1_ou, "MC1-V": mc1_v, "MC1-G25": mc1_g(0.25), "MC1-G50": mc1_g(0.50),
                  "MC2-k1": mc2(1), "MC2-k2": mc2(2)}
        R = {}
        for nom, f in regles.items():
            R[nom] = evaluer(jeux, f)
            res[nom] = resume(nom, R[nom], ref)
            print(ligne(nom, R[nom]))
            print("   ", res[nom]["finaliste_sans_temps"], res[nom]["conditions"], {k: res[nom][k] for k in
                  ("alertes_differentes", "malades_perdues_vs_F1", "malades_rattrapees_vs_F1", "inconnues")})
        for piste, noms in (("MC1", ["MC1-OU", "MC1-V", "MC1-G25", "MC1-G50"]), ("MC2", ["MC2-k1", "MC2-k2"]),
                            ("MC1+MC2", list(regles))):
            cands = {n: R[n] for n in noms}
            ch = choisir(cands, ref)
            cc, choix = croise(cands, ref)
            res[f"choix_{piste}"] = dict(choisi=ch, cout_croise=cc, choix_par_jeu_tenu=choix)
            print(f"choix {piste} : {ch} | coût croisé {cc:.2f} | {choix}")
        # photos d'AgroVisionBD inconnues (bornes) pour une des règles : à lire
        inc = np.zeros(len(jeux["agrovision"]["chemin"]), bool)
        for f in regles.values():
            inc |= C.bornes(jeux["agrovision"], f)[2]
        (SORTIE / "a_lire_agrovision.json").write_text(json.dumps([int(i) for i in np.flatnonzero(inc)]), encoding="utf-8")
        print("AgroVisionBD : photos à lire (morceaux) :", int(inc.sum()))
    if quoi == "mc1b":   # essais 7 et 8 (journal, 18 h 45), choisis après lecture des essais 1 à 6
        prec = json.loads((SORTIE / "bilan_mc12.json").read_text(encoding="utf-8"))
        R = {}
        for nom, f in (("MC1-VOTE", mc1_vote), ("MC1-OU-proche", mc1_ou_proche)):
            R[nom] = evaluer(jeux, f)
            res[nom] = resume(nom, R[nom], ref)
            print(ligne(nom, R[nom]))
            print("   ", res[nom]["finaliste_sans_temps"], res[nom]["conditions"], {k: res[nom][k] for k in
                  ("alertes_differentes", "malades_perdues_vs_F1", "malades_rattrapees_vs_F1", "inconnues")})
        # coût croisé de la piste MC1 complète (essais 1 à 4, 7, 8)
        regles = {"MC1-OU": mc1_ou, "MC1-V": mc1_v, "MC1-G25": mc1_g(0.25), "MC1-G50": mc1_g(0.50)}
        for nom, f in regles.items():
            R[nom] = evaluer(jeux, f)
        ch = choisir(R, ref)
        cc, choix = croise(R, ref)
        res["choix_MC1_complet"] = dict(choisi=ch, cout_croise=cc, choix_par_jeu_tenu=choix,
                                        plus_bas=min(R, key=lambda n: R[n]["cout_reglage"]))
        print(f"choix MC1 (1-4, 7, 8) : {ch} | coût croisé {cc:.2f} | {choix} | plus bas : {res['choix_MC1_complet']['plus_bas']}")
        _ = prec
    if quoi == "mc3":   # essais K1 à K8 (journal, 18 h 50, 18 h 43 et 18 h 46)
        L2P = KAG / "lot2p"
        K = SORTIE / "kaggle" / (sys.argv[2] if len(sys.argv) > 2 else "lot1")
        sources = {"d3b_ctrl": [(L2P, "d3b")], "K1 d3g1": [(K, "d3g1")], "K2 d3b+d3g1": [(L2P, "d3b"), (K, "d3g1")],
                   "K3 d3c": [(K, "d3c")], "K4 d3cg1": [(K, "d3cg1")], "K5 d3c+d3cg1": [(K, "d3c"), (K, "d3cg1")]}
        Rb, Rc = {"d3b": rd}, {"P8 MC1-OU-proche (d3b)": evaluer(jeux, mc1_ou_proche)}
        for nom, src in sources.items():
            if not all((dos / f"predictions_{n}_tdtu.csv").exists() for dos, n in src):
                print("absent :", nom)
                continue
            lire_kaggle(jeux, src)
            R = evaluer(jeux, chaine_eleve)
            res[nom] = resume(nom, R, ref)
            print(ligne(nom, R))
            print("   ", res[nom]["finaliste_sans_temps"], res[nom]["conditions"], {k: res[nom][k] for k in
                  ("alertes_differentes", "malades_perdues_vs_F1", "malades_rattrapees_vs_F1")})
            if nom == "d3b_ctrl":
                assert abs(R["cout_reglage"] - rd["cout_reglage"]) < 1e-9, "d3b relu depuis les plis ≠ pour_banc"
                continue
            Rb[nom] = R
            cnom = {"K1 d3g1": "K7 MC1-OU-proche (d3g1)", "K2 d3b+d3g1": "K8 MC1-OU-proche (d3b+d3g1)",
                    "K5 d3c+d3cg1": "K6 MC1-OU-proche (d3c+d3cg1)"}.get(nom)
            if cnom:
                Rc[cnom] = evaluer(jeux, mc1_ou_proche)
                res[cnom] = resume(cnom, Rc[cnom], ref)
                print(ligne(cnom, Rc[cnom]))
                print("   ", res[cnom]["finaliste_sans_temps"], res[cnom]["conditions"], {k: res[cnom][k] for k in
                      ("alertes_differentes", "malades_perdues_vs_F1", "malades_rattrapees_vs_F1")})
        for fam, cands in (("B", {k: v for k, v in Rb.items() if k != "K1 d3g1"}), ("C", Rc)):
            cc, choix = croise(cands, ref)
            res[f"choix_{fam}"] = dict(choisi=choisir(cands, ref), cout_croise=cc, choix_par_jeu_tenu=choix)
            print(f"choix famille {fam} :", res[f"choix_{fam}"])
    if quoi == "graines":   # K9 à K12 (journal, 19 h 27) : dispersion sur les graines 0 à 3, aucune sélection
        K1_, K2_ = SORTIE / "kaggle/lot1", SORTIE / "kaggle/lot2"
        srcs = {0: (KAG / "lot2p", "d3b"), 1: (K1_, "d3g1"), 2: (K2_, "d3g2"), 3: (K2_, "d3g3")}
        tab = {}
        for g, src in srcs.items():
            lire_kaggle(jeux, [src])
            for nom, f in (("eleve", chaine_eleve), ("MC1-OU-proche", mc1_ou_proche)):
                R = evaluer(jeux, f)
                s = resume(f"{nom} graine {g}", R, ref)
                tab[f"{nom} g{g}"] = s
                print(ligne(f"{nom} graine {g}", R), "| passe :", s["finaliste_sans_temps"])
        res["graines"] = tab
        for nom in ("eleve", "MC1-OU-proche"):
            c = [tab[f"{nom} g{g}"]["cout_reglage"] for g in srcs]
            m = [tab[f"{nom} g{g}"]["msa_total5"] for g in srcs]
            r_ = [tab[f"{nom} g{g}"]["roamer_msa"] for g in srcs]
            p = [tab[f"{nom} g{g}"]["finaliste_sans_temps"] for g in srcs]
            res[f"resume_{nom}"] = dict(cout_moyen=float(np.mean(c)), cout_min=min(c), cout_max=max(c), ratees5=m,
                                        roamer=r_, passent=int(sum(p)))
            print(nom, res[f"resume_{nom}"])
    if quoi == "veille":   # essais 15 à 17 (journal, 18 h 50)
        R = {}
        inc = np.zeros(len(jeux["agrovision"]["chemin"]), bool)
        for nom, f in (("M2-s70", m2_morceaux(0.70)), ("M2-s90", m2_morceaux(0.90))):
            R[nom] = evaluer(jeux, f)
            res[nom] = resume(nom, R[nom], ref)
            inc |= C.bornes(jeux["agrovision"], f)[2]
            print(ligne(nom, R[nom]))
            print("   ", res[nom]["finaliste_sans_temps"], res[nom]["conditions"], {k: res[nom][k] for k in
                  ("alertes_differentes", "malades_perdues_vs_F1", "malades_rattrapees_vs_F1", "inconnues")})
        (SORTIE / "a_lire_agrovision_m2.json").write_text(json.dumps([int(i) for i in np.flatnonzero(inc)]), encoding="utf-8")
        cc, choix = croise(R, ref)
        res["choix_M2"] = dict(choisi=choisir(R, ref), cout_croise=cc, choix_par_jeu_tenu=choix)
        print("choix M2 :", res["choix_M2"])
        res["M5_conforme"] = m5_conforme(jeux, ref)
        for a, par in res["M5_conforme"].items():
            for h, m in par.items():
                print(a, h, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()})
    (SORTIE / f"bilan_{quoi}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
