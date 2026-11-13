#!/usr/bin/env python3
"""M-analyste (nuit du 12/11) : malades ratées, fausses alertes et accord entre modèles, sur le réglage seulement.

Lit out/maladies/analyse/table_reglage.csv (scripts/m12_analyse_table.py). Chaînes comparées : « installee » (v10b,
aiguilleur, v2 en loin) et « F1 » de M-banc (mélange géométrique v10b + soupe + v2, v10b lue entière + 2 x 2, seuil
0,70, loin « v2 ou proche »), avec F3 (même mélange sans morceaux, seuil 0,74).

Rappels de décision (vérifiés sur le code de la chaîne) :
- photo proche, installée : sans alerte <=> P(saine) v10b >= 0,5186 ; F1 : <=> P(saine) du mélange >= 0,70 ;
- photo loin, installée : sans alerte <=> P(saine) v2 >= 0,70 ; F1 : il faut en plus P(saine) du mélange >= 0,70.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_analyse_erreurs.py
Sorties : out/maladies/analyse/erreurs_*.csv et resume_erreurs.txt (tout ce qui est affiché).
"""
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "out/maladies/analyse"
T = pd.read_csv(SORTIE / "table_reglage.csv")
T["lesion"] = T.f_jaune + T.f_brun
T["cadrage"] = pd.cut(T.p_loin, [-0.01, 0.1, 0.3, 0.5, 1.01], labels=["gros plan (<0,1)", "0,1-0,3", "0,3-0,5", "loin (>=0,5)"])
CH = {"installee": "installee", "F1": "F1_trois_morceaux2x2", "F3": "F3_trois"}
SEUIL = {"installee": 0.5186470150947571, "F1": 0.70, "F3": 0.74}
buf = io.StringIO()


def p(*a):
    print(*a)
    print(*a, file=buf)


def rate(s):
    return f"{int(s.sum())}/{len(s)} ({100 * s.mean():.1f} %)" if len(s) else "-"


def profil(sub, ch):
    """Profil de probabilité des ratées : marge de P(saine) du lecteur qui a décidé au-dessus du seuil."""
    k = CH[ch]
    loin = sub.loin.to_numpy()
    if ch == "installee":
        ps = np.where(loin, sub.ps_v2, sub[f"ps_{k}"])
        s = np.where(loin, 0.70, SEUIL[ch])
    else:   # F1/F3 : en loin, la photo est sans alerte si v2 ET mélange disent saine -> la marge est le min des deux marges
        ps_m = sub[f"ps_{k}"].to_numpy()
        ps = np.where(loin, np.minimum(sub.ps_v2.to_numpy() - 0.70, ps_m - SEUIL[ch]) + SEUIL[ch], ps_m)
        s = np.full(len(sub), SEUIL[ch])
    marge = ps - s
    return pd.cut(marge, [-1, 0.05, 0.15, 0.30, 1], labels=["presque (<0,05)", "0,05-0,15", "0,15-0,30", "franche (>=0,30)"]).value_counts().sort_index()


def section_ratees():
    p("=" * 100, "\n1. MALADES RATÉES\n")
    M = T[T.malade]
    for ch in ["installee", "F3", "F1"]:
        al = M[f"al_{CH[ch]}"]
        p(f"--- {ch} : ratées par jeu et classe")
        tab = M.assign(ratee=~al).groupby(["jeu", "vraie"]).ratee.agg(["sum", "count"])
        tab["taux %"] = (100 * tab["sum"] / tab["count"]).round(1)
        p(tab.to_string())
        p(f"--- {ch} : ratées par cadrage (p_loin)")
        tab = M.assign(ratee=~al).groupby(["jeu", "cadrage"], observed=True).ratee.agg(["sum", "count"])
        tab["taux %"] = (100 * tab["sum"] / tab["count"]).round(1)
        p(tab.to_string())
        p(f"--- {ch} : profil de probabilité des ratées (marge de P(saine) au-dessus du seuil qui décide)")
        for j in ["validation", "tdtu", "psfd", "ethiopie"]:
            sub = M[(M.jeu == j) & ~M[f"al_{CH[ch]}"]]
            if len(sub):
                p(f"  {j:11s} n={len(sub):4d}", dict(profil(sub, ch)))
    p("\n--- installée : ratées contre détectées, médianes des mesures d'image (par jeu)")
    cols = ["larg", "haut", "octets_par_px", "qjpeg", "nettete", "lum", "contraste", "sat", "f_vert", "lesion", "f_sombre", "f_gris", "p_loin"]
    for ch in ["installee", "F1"]:
        p(f"[{ch}]")
        for j in ["validation", "tdtu", "psfd", "ethiopie"]:
            s = M[M.jeu == j]
            r = s[~s[f"al_{CH[ch]}"]][cols].median()
            d = s[s[f"al_{CH[ch]}"]][cols].median()
            p(f"  {j:11s} ratées   " + " ".join(f"{c}={r[c]:.3g}" for c in cols))
            p(f"  {j:11s} vues     " + " ".join(f"{c}={d[c]:.3g}" for c in cols))
    p("\n--- taux de ratées par quartile (dans chaque jeu) de la part de pixels jaunes ou bruns (substitut de la gravité visible)")
    for ch in ["installee", "F1"]:
        for j in ["validation", "tdtu", "psfd", "ethiopie"]:
            s = M[M.jeu == j]
            q = pd.qcut(s.lesion.rank(method="first"), 4, labels=["Q1 peu", "Q2", "Q3", "Q4 beaucoup"])
            t = (~s[f"al_{CH[ch]}"]).groupby(q, observed=True).mean().mul(100).round(1)
            p(f"  {ch:9s} {j:11s}", dict(t))
    p("\n--- taux de ratées par quartile de netteté et de taille de fichier par pixel (installée / F1)")
    for var in ["nettete", "octets_par_px", "lum", "f_vert"]:
        for j in ["validation", "tdtu", "psfd", "ethiopie"]:
            s = M[M.jeu == j]
            q = pd.qcut(s[var].rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"])
            a = (~s.al_installee).groupby(q, observed=True).mean().mul(100).round(1)
            b = (~s[f"al_{CH['F1']}"]).groupby(q, observed=True).mean().mul(100).round(1)
            p(f"  {var:13s} {j:11s} installée {dict(a)}  F1 {dict(b)}")


def section_fa():
    p("=" * 100, "\n2. FAUSSES ALERTES SUR SAINES\n")
    S = T[~T.malade]
    for ch in ["installee", "F3", "F1"]:
        k = CH[ch]
        p(f"--- {ch} : réponses données aux saines en alerte")
        p(S[S[f"al_{k}"]].groupby(["jeu", f"r_{k}"]).size().unstack(fill_value=0).to_string())
        p(f"--- {ch} : fausses alertes par cadrage")
        tab = S.groupby(["jeu", "cadrage"], observed=True)[f"al_{k}"].agg(["sum", "count"])
        tab["taux %"] = (100 * tab["sum"] / tab["count"]).round(1)
        p(tab.to_string())
    cols = ["larg", "octets_par_px", "nettete", "lum", "contraste", "sat", "f_vert", "f_jaune", "f_brun", "f_sombre", "f_gris", "p_loin"]
    p("\n--- saines en alerte contre saines sans alerte (installée), médianes")
    for ch in ["installee", "F1"]:
        p(f"[{ch}]")
        for j in ["validation", "tdtu", "ethiopie"]:
            s = S[S.jeu == j]
            a = s[s[f"al_{CH[ch]}"]][cols].median()
            b = s[~s[f"al_{CH[ch]}"]][cols].median()
            p(f"  {j:11s} en alerte " + " ".join(f"{c}={a[c]:.3g}" for c in cols))
            p(f"  {j:11s} sans      " + " ".join(f"{c}={b[c]:.3g}" for c in cols))
    p("\n--- taux de fausses alertes par quartile (dans chaque jeu) de la part jaune + brun (feuille sénescente ou abîmée ?)")
    for ch in ["installee", "F1"]:
        for j in ["validation", "tdtu", "ethiopie"]:
            s = S[S.jeu == j]
            for var in ["lesion", "f_sombre", "f_gris", "nettete"]:
                q = pd.qcut(s[var].rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"])
                t = s[f"al_{CH[ch]}"].groupby(q, observed=True).mean().mul(100).round(1)
                p(f"  {ch:9s} {j:11s} {var:9s}", dict(t))
    p("\n--- profil de probabilité des saines en alerte (P(saine) du lecteur sous le seuil de combien ?)")
    for ch in ["installee", "F1"]:
        k = CH[ch]
        for j in ["validation", "tdtu", "ethiopie"]:
            s = S[(S.jeu == j) & S[f"al_{k}"] & ~S.loin]
            m = s[f"ps_{k}"] - SEUIL[ch]
            t = pd.cut(m, [-1.01, -0.5, -0.2, -0.05, 0], labels=["franche (<-0,5)", "-0,5 à -0,2", "-0,2 à -0,05", "presque (>-0,05)"]).value_counts().sort_index()
            p(f"  {ch:9s} {j:11s} proches en alerte n={len(s)}", dict(t))


def section_accord():
    p("=" * 100, "\n3. ACCORD ET DÉSACCORD : v10b, soupe, v2 seules ; installée ; F3 ; F1\n")
    k1 = CH["F1"]
    for j in ["validation", "tdtu", "psfd", "ethiopie"]:
        s = T[T.jeu == j]
        M, S = s[s.malade], s[~s.malade]
        gain = M[~M.al_installee & M[f"al_{k1}"]]
        perte = M[M.al_installee & ~M[f"al_{k1}"]]
        p(f"--- {j} : malades rattrapées par F1 {len(gain)} (dont loin {int(gain.loin.sum())}) ; perdues {len(perte)} (dont loin {int(perte.loin.sum())})")
        nfa = S[~S.al_installee & S[f"al_{k1}"]]
        mfa = S[S.al_installee & ~S[f"al_{k1}"]]
        p(f"    saines : nouvelles fausses alertes F1 {len(nfa)} (dont loin {int(nfa.loin.sum())}) ; fausses alertes retirées {len(mfa)} (dont loin {int(mfa.loin.sum())})")
        # qui alerte seul ?
        cle = lambda x: ("v10b " if x.al_v10b_seule else "") + ("soupe " if x.al_soupe_seule else "") + ("v2" if x.al_v2_seule else "")
        if len(M):
            c = M.apply(cle, axis=1).replace("", "aucun").value_counts()
            p("    malades, modèles seuls qui alertent :", dict(c))
            aucun = M[~M.al_v10b_seule & ~M.al_soupe_seule & ~M.al_v2_seule]
            p(f"    malades qu'aucun des trois ne voit : {len(aucun)} ; dont ratées par F1 {int((~aucun[f'al_{k1}']).sum())}")
            p("    malades rattrapées par F1, modèles seuls qui alertent :", dict(gain.apply(cle, axis=1).replace("", "aucun").value_counts()))
        if len(S):
            c = S.apply(cle, axis=1).replace("", "aucun").value_counts()
            p("    saines, modèles seuls qui alertent :", dict(c))
    p("\n--- ratées par la chaîne installée, réparties selon la branche et la marge")
    for j in ["tdtu", "psfd", "ethiopie", "validation"]:
        s = T[(T.jeu == j) & T.malade & ~T.al_installee]
        p(f"  {j:11s} ratées {len(s)} : loin {int(s.loin.sum())} (P(saine) v2 médiane {s[s.loin].ps_v2.median():.2f}) ; "
          f"proches {int((~s.loin).sum())} (P(saine) v10b médiane {s[~s.loin].ps_v10b.median():.2f}) ; "
          f"rattrapées par F1 {int(s[f'al_{k1}'].sum())}")


if __name__ == "__main__":
    section_ratees()
    section_fa()
    section_accord()
    (SORTIE / "resume_erreurs.txt").write_text(buf.getvalue(), encoding="utf-8")
