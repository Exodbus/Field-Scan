#!/usr/bin/env python3
"""Mesure unique du test khadavy (docs/protocole_maladies_test_khadavy.md, sections 5 à 7).

Les deux modèles passent une fois, chacun par sa propre chaîne de décision, sur les images figées de
data/test_khadavy/liste.csv (SHA-256 vérifiés) :
  - v2 ConvNeXt (binôme, modèle de la chaîne) : modeles/maladies_binome/maladies_v2 (classifieur.py) ;
  - B0 (Corentin, colonne de comparaison) : modeles/maladies/maladies_v2.onnx (fieldscan/modules/maladies.py).
Les empreintes des fichiers des modèles sont vérifiées contre celles du protocole avant toute prédiction.

--essai : vérifie le code sur 30 images de validation tanzanienne, sans lire khadavy ni écrire de verrou.
Sans --essai : mesure unique ; un fichier VERROU empêche toute seconde mesure.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/mesurer_test_khadavy.py [--essai]
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
DOSSIER_V2 = RACINE / "modeles/maladies_binome/maladies_v2"
sys.path.insert(0, str(DOSSIER_V2))

EMPREINTES = {  # protocole, section 4
    "modeles/maladies/maladies_v2.onnx": "241841de12ce86fb0d4f411575f7300c7ec4785a23672824283ac3a5a00cf6a7",
    "modeles/maladies/entrainement_maladies.json": "3e766e578b207c8dd85259aea34487f57d2169a9a607cc32534dc092bba0ca98",
    "fieldscan/modules/maladies.py": "fec6a9fe3a09105a91983bc1521f0d7c0f634017e9f22e965cadae08c29d01da",
    "modeles/maladies_binome/maladies_v2/poids/maladies_v2_convnext_tiny_1.pt": "276630d275c32c83a6f05942d6eb00036980c1a0a5fdb3c7130ab848265229b7",
    "modeles/maladies_binome/maladies_v2/poids/maladies_v2_convnext_tiny_2.pt": "1ad6e8981463a36eeefe5b130c709c8a3fb00de42779c0f6afd062da561db683",
    "modeles/maladies_binome/maladies_v2/poids/maladies_v2_convnext_tiny_3.pt": "711a202fc6f2d151c2ee75bf82d89f085ea02df35d0b6ad6d4bfdf2afff4e395",
    "modeles/maladies_binome/maladies_v2/poids/seuils.json": "a5a52d957b172a86e7737f8903a6f0bb3bf798af84321d0a56d374e80e4fd418",
    "modeles/maladies_binome/maladies_v2/classifieur.py": "7179ad81f55437a506eaa83a6e8a643363135fa39334096c7dff68865d8a7041",
}
EMPREINTE_LISTE = "c8e6d50a2c5750605cb7de01c4ce2bc8351121f8b4904d497d78c0bc8681af73"
MALADE = {"cercosporiose_noire", "fusariose", "malade_non_identifiee"}
VERS_COMMUN_V2 = {"saine": "saine", "black_sigatoka": "cercosporiose_noire", "fusarium": "fusariose",
                  "malade_non_identifiee": "malade_non_identifiee", "inconnu": "je_ne_sais_pas"}
REPONSES = ["saine", "cercosporiose_noire", "fusariose", "malade_non_identifiee", "je_ne_sais_pas"]
VRAIE = {"Sehat": "saine", "Bercak-Hitam": "cercosporiose_noire", "Bercak-Kuning": "inconnue"}


def sha(chemin):
    return hashlib.sha256(Path(chemin).read_bytes()).hexdigest()


def verifier_empreintes():
    for f, h in EMPREINTES.items():
        if sha(RACINE / f) != h:
            sys.exit(f"empreinte différente du protocole : {f}")


def predire_v2(chemins):
    import classifieur
    reseaux, seuils = classifieur.charger(DOSSIER_V2 / "poids")
    t = time.perf_counter()
    P = classifieur.probabilites(reseaux, [str(c) for c in chemins])
    duree = (time.perf_counter() - t) / max(len(chemins), 1)
    rep = [VERS_COMMUN_V2[r] for r in classifieur.decider(P, seuils)]
    return pd.DataFrame(dict(reponse=rep, p_saine=P[:, 0], p_cercosporiose_noire=P[:, 1], p_fusariose=P[:, 2])), duree


def predire_b0():
    from fieldscan.modules import maladies as mb0

    def lancer(chemins):
        reglages = {"maladies": {"modele": str(RACINE / "modeles/maladies/maladies_v2.onnx"),
                                 "methode_rejet": "proba_max", "seuil_rejet": 0.7076}}
        m = mb0.charger_modele(reglages)
        t = time.perf_counter()
        L = mb0.predire([str(c) for c in chemins], m)
        duree = (time.perf_counter() - t) / max(len(chemins), 1)
        rep, _, _, P = mb0.decider(L, m, 0.5)
        cls = m["classes"]
        return pd.DataFrame(dict(reponse=list(rep), **{f"p_{c}": P[:, k] for k, c in enumerate(cls)})), duree
    return lancer


def f1(vrai, pred, c):
    tp = int(((vrai == c) & (pred == c)).sum()); fp = int(((vrai != c) & (pred == c)).sum())
    fn = int(((vrai == c) & (pred != c)).sum())
    return 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else float("nan")


def f1_macro(vrai, pred):
    return float(np.mean([f1(vrai, pred, "saine"), f1(vrai, pred, "cercosporiose_noire")]))


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; e = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - e, 3), round(c + e, 3)]


def part(masque, total):
    k, n = int(masque.sum()), int(total.sum())
    return dict(k=k, n=n, part=round(k / n, 3) if n else None, ic95=wilson(k, n))


def mesures_khadavy(df):
    v, r = df.vraie.to_numpy(), df.reponse.to_numpy()
    connues = np.isin(v, ["saine", "cercosporiose_noire"])
    vc, rc = v[connues], r[connues]
    rng = np.random.default_rng(2026)
    boot = [f1_macro(vc[i], rc[i]) for i in (rng.integers(0, len(vc), len(vc)) for _ in range(10000))]
    sa, cn, inc = v == "saine", v == "cercosporiose_noire", v == "inconnue"
    malade = cn | inc
    est_malade = np.isin(r, list(MALADE))
    return {
        "f1_macro_connues": round(f1_macro(vc, rc), 4),
        "f1_macro_ic95": [round(float(np.percentile(boot, 2.5)), 4), round(float(np.percentile(boot, 97.5)), 4)],
        "f1_saine": round(f1(vc, rc, "saine"), 4), "f1_cercosporiose_noire": round(f1(vc, rc, "cercosporiose_noire"), 4),
        "sigatoka_nommee": part(cn & (r == "cercosporiose_noire"), cn),
        "saines_bien_classees": part(sa & (r == "saine"), sa),
        "fausses_alertes": part(sa & est_malade, sa),
        "malades_dites_saines": part(malade & (r == "saine"), malade),
        "malades_dites_malades": part(malade & est_malade, malade),
        "je_ne_sais_pas": {c: part((v == c) & (r == "je_ne_sais_pas"), v == c) for c in ["saine", "cercosporiose_noire", "inconnue"]},
        "kuning_signalee_malade": part(inc & est_malade, inc),
        "kuning_reconnue_inconnue": part(inc & np.isin(r, ["malade_non_identifiee", "je_ne_sais_pas"]), inc),
        "kuning_dite_cercosporiose_noire": part(inc & (r == "cercosporiose_noire"), inc),
        "matrice": pd.crosstab(df.vraie, df.reponse).reindex(columns=REPONSES, fill_value=0).to_dict("index"),
    }


def mesures_indicatives(df):
    r = df.reponse.to_numpy()
    est_malade = np.isin(r, list(MALADE))
    roamer = df.jeu.eq("roamer_black_sigatoka").to_numpy()
    pan = df.jeu.eq("research_panama").to_numpy()
    sain_p, mal_p = pan & df.classe.eq("healthy").to_numpy(), pan & df.classe.eq("diseased").to_numpy()
    return {
        "roamer_dite_malade": part(roamer & est_malade, roamer),
        "roamer_dite_cercosporiose_noire": part(roamer & (r == "cercosporiose_noire"), roamer),
        "roamer_reponses": df[roamer].reponse.value_counts().to_dict(),
        "panama_malades_dites_malades": part(mal_p & est_malade, mal_p),
        "panama_malades_dites_fusariose": part(mal_p & (r == "fusariose"), mal_p),
        "panama_saines_fausses_alertes": part(sain_p & est_malade, sain_p),
        "panama_matrice": pd.crosstab(df[pan].classe, df[pan].reponse).to_dict("index"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--essai", action="store_true")
    ap.add_argument("--out", default="out/maladies/test_khadavy")
    args = ap.parse_args(argv)
    out = RACINE / (args.out + ("_essai" if args.essai else ""))
    verifier_empreintes()

    if args.essai:
        idx = pd.read_csv(RACINE / "data/feuilles/index.csv")
        val = idx[idx.source.eq("tanzanie_2022") & idx.retenue].groupby("classe").head(10)
        liste = pd.DataFrame(dict(jeu="essai", classe=val.classe.values, fichier=val.chemin.values))
        base = RACINE / "data/feuilles"
    else:
        if (out / "VERROU").exists():
            sys.exit(f"{out / 'VERROU'} existe : la mesure unique a déjà été faite.")
        if sha(RACINE / "data/test_khadavy/liste.csv") != EMPREINTE_LISTE:
            sys.exit("liste.csv différente de la liste figée")
        liste = pd.read_csv(RACINE / "data/test_khadavy/liste.csv")
        base = RACINE / "data/test_khadavy"
        for f, h in zip(liste.fichier, liste.sha256):
            if sha(base / f) != h:
                sys.exit(f"image modifiée : {f}")
        out.mkdir(parents=True, exist_ok=True)
        (out / "VERROU").write_text(f"mesure lancée le {time.strftime('%Y-%m-%d %H:%M:%S')}\n", encoding="utf-8")
    out.mkdir(parents=True, exist_ok=True)
    chemins = [base / f for f in liste.fichier]

    bilan = {}
    for nom, lancer in (("v2_convnext", predire_v2), ("b0", predire_b0())):
        rep, duree = lancer(chemins)
        df = pd.concat([liste.reset_index(drop=True), rep], axis=1)
        df.to_csv(out / f"reponses_{nom}.csv", index=False)
        b = dict(secondes_par_photo=round(duree, 3))
        if args.essai:
            b["reponses_par_classe"] = pd.crosstab(df.classe, df.reponse).to_dict("index")
        else:
            k = df[df.jeu.eq("khadavy")].assign(vraie=lambda d: d.classe.map(VRAIE))
            b["khadavy"] = mesures_khadavy(k)
            b["indicatifs"] = mesures_indicatives(df[~df.jeu.eq("khadavy")])
        bilan[nom] = b
        print(nom, "terminé", flush=True)
    (out / "bilan.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(bilan, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
