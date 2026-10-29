#!/usr/bin/env python3
"""Évaluation du « je ne sais pas » sur le jeu éthiopien, à résolution égale (processeur).

Pourquoi ce jeu : ses images (150 x 113 pixels) ont toutes la même résolution et le même style.
Feuilles connues (saines, Sigatoka) et maladie inconnue (flétrissement bactérien, Xanthomonas,
absente de l'entraînement) ne diffèrent donc que par la maladie. Aucun des tests déjà consultés
(BananaLSD, Cordana péruvienne) n'est utilisé.

Méthodes de « familiarité » (plus haut = plus proche des classes connues), sur le modèle retenu
(v2, moyenne sur 4 vues) : proba_max, energie, mahalanobis, plus_proches_voisins ; et le désaccord
entre v1 et v2 sur les 4 vues (8 avis) : information mutuelle, en négatif.

Seuils : global (réglé sur la validation tanzanienne, dans entrainement_maladies.json) quand il
existe ; par site : réglé sur une moitié des feuilles éthiopiennes connues (95 % acceptées),
mesuré sur l'autre moitié et sur l'inconnue ; 20 tirages.

Règle fixée avant le calcul : méthode au meilleur taux de rejet de l'inconnue (seuil par site,
moyenne des tirages) ; l'AUROC départage.

Partie 2 : architecture en deux étapes, comparée à l'architecture actuelle (« à plat »).
  - étape 1 : malade si P(cercosporiose) + P(fusariose) >= 0,5 (seuil fixé à l'avance) ;
  - étape 2 : parmi les maladies, la plus probable, sauf si le score de familiarité restreint aux
    maladies est sous le seuil : « malade, maladie non identifiée ». Seuil réglé sur des feuilles
    malades connues : validation tanzanienne (global) ou moitié des Sigatoka éthiopiennes (par site).
  Règle : meilleur rejet du Xanthomonas (« non identifiée », seuil par site), sans plus de fausses
  alertes sur les feuilles saines que l'architecture à plat ; les maladies détectées départagent.

Exemple :
    python scripts/evaluer_rejet_ethiopie.py --modeles modeles/maladies --out out/maladies/ethiopie
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

CLASSES = ["cercosporiose_noire", "fusariose", "saine"]
I_MALADIES, I_SAINE = [0, 1], 2
SEUIL_ETAPE1 = 0.5
DOSSIERS = {"healthy": "saine", "segatoka": "cercosporiose_noire", "xamthomonas": "inconnue_xanthomonas"}
ACCEPTATION = 0.95


def lister(racine):
    lignes = []
    for f in sorted(Path(racine).rglob("*")):
        if f.suffix.lower() in {".jpg", ".jpeg", ".png"} and f.parent.name.lower() in DOSSIERS:
            lignes.append(dict(chemin=str(f), classe=DOSSIERS[f.parent.name.lower()]))
    if not lignes:
        raise SystemExit(f"Aucune image dans {racine} (dossiers attendus : {', '.join(DOSSIERS)})")
    return pd.DataFrame(lignes)


def sorties_modeles(images, dossier_modeles, noms=("v1", "v2"), lot=32):
    """Pour chaque modèle : logits par vue (4 vues) et caractéristiques de la vue identité. Processeur."""
    import torch
    import torch.nn as nn
    import torchvision.transforms as T
    from PIL import Image
    from torchvision.models import efficientnet_b0

    prep = T.Compose([T.Resize(224), T.CenterCrop(224), T.ToTensor(),
                      T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
    vues = [lambda x: x, lambda x: torch.flip(x, [3]), lambda x: torch.flip(x, [2]), lambda x: torch.flip(x, [2, 3])]
    sorties = {}
    for nom in noms:
        m = efficientnet_b0(weights=None)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, len(CLASSES))
        m.load_state_dict(torch.load(Path(dossier_modeles) / f"meilleur_{nom}.pt", map_location="cpu"))
        m.eval()
        L, F = [], []
        with torch.no_grad():
            for i in range(0, len(images), lot):
                x = torch.stack([prep(Image.open(c).convert("RGB")) for c in images[i:i + lot]])
                lv = []
                for k, v in enumerate(vues):
                    f = torch.flatten(m.avgpool(m.features(v(x))), 1)
                    lv.append(m.classifier(f).numpy())
                    if k == 0:
                        F.append(f.numpy())
                L.append(np.stack(lv))
                print(f"\r  {nom} : {min(i + lot, len(images))}/{len(images)} images", end="", flush=True)
        print()
        sorties[nom] = dict(logits=np.concatenate(L, axis=1), caracteristiques=np.concatenate(F))
    return sorties


def softmax(z):
    z = z - z.max(-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(-1, keepdims=True)


def familiarites(sorties, rejet, k_voisins):
    """Scores de familiarité ; le modèle retenu est v2, moyenne des logits sur 4 vues."""
    L = sorties["v2"]["logits"].mean(0)
    F = sorties["v2"]["caracteristiques"]
    lse = np.log(np.exp(L - L.max(1, keepdims=True)).sum(1)) + L.max(1)
    d = np.stack([np.einsum("ij,jk,ik->i", F - m, rejet["precision"], F - m) for m in rejet["moyennes"]], 1)
    Fn = F / np.linalg.norm(F, axis=1, keepdims=True)
    B = rejet["banque"].astype(np.float32)
    voisins = np.sort(Fn @ B.T, axis=1)[:, -k_voisins]
    P = softmax(np.concatenate([sorties[n]["logits"] for n in ("v1", "v2")]))   # 8 avis : 2 modèles x 4 vues
    pm = P.mean(0)
    entropie = lambda p: -(p * np.log(p + 1e-12)).sum(-1)
    info_mutuelle = entropie(pm) - entropie(P).mean(0)
    return dict(proba_max=softmax(L).max(1), energie=lse, mahalanobis=-d.min(1), plus_proches_voisins=voisins,
                desaccord_v1_v2=-info_mutuelle), L


def entropie(p):
    return -(p * np.log(p + 1e-12)).sum(-1)


def etape2(sorties, rejet):
    """Scores de familiarité restreints aux maladies, probabilité d'être malade, maladie la plus probable."""
    L = sorties["v2"]["logits"].mean(0)
    P = softmax(L)
    p_malade = P[:, I_MALADIES].sum(1)
    q = P[:, I_MALADIES] / p_malade[:, None]
    Lm = L[:, I_MALADIES]
    F = sorties["v2"]["caracteristiques"]
    d = np.stack([np.einsum("ij,jk,ik->i", F - rejet["moyennes"][k], rejet["precision"], F - rejet["moyennes"][k])
                  for k in I_MALADIES], 1)
    Pt = softmax(np.concatenate([sorties[n]["logits"] for n in ("v1", "v2")]))[..., I_MALADIES]
    Q = Pt / Pt.sum(-1, keepdims=True)
    scores = dict(proba_max_maladie=q.max(1),
                  energie_maladie=np.log(np.exp(Lm - Lm.max(1, keepdims=True)).sum(1)) + Lm.max(1),
                  mahalanobis_maladie=-d.min(1), desaccord_maladie=-(entropie(Q.mean(0)) - entropie(Q).mean(0)))
    return scores, p_malade, np.array(CLASSES)[I_MALADIES][q.argmax(1)]


def decider_deux_etapes(p_malade, maladie, score, seuil):
    return np.where(p_malade < SEUIL_ETAPE1, "saine", np.where(score >= seuil, maladie, "malade_non_identifiee"))


def decider_a_plat(classe, score, seuil):
    return np.where(score >= seuil, classe, "je_ne_sais_pas")


def mesurer(rep, vrai):
    inconnue = pd.Series(vrai).str.startswith("inconnue").to_numpy()
    malade = vrai != "saine"
    rejet = np.isin(rep, ["malade_non_identifiee", "je_ne_sais_pas"])
    return dict(fausses_alertes_saines=np.isin(rep[vrai == "saine"], ["cercosporiose_noire", "fusariose", "malade_non_identifiee"]).mean(),
                maladies_detectees=np.isin(rep[malade], ["cercosporiose_noire", "fusariose", "malade_non_identifiee"]).mean(),
                sigatoka_identifiee=(rep[vrai == "cercosporiose_noire"] == "cercosporiose_noire").mean(),
                inconnue_non_identifiee=rejet[inconnue].mean(),
                inconnue_declaree_saine=(rep[inconnue] == "saine").mean(),
                inconnue_nommee_a_tort=np.isin(rep[inconnue], ["cercosporiose_noire", "fusariose"]).mean())


def auroc(connues, inconnues):
    """Probabilité qu'une feuille connue ait un score plus haut qu'une inconnue (égalités comptées pour moitié)."""
    s = np.r_[connues, inconnues]
    rangs = pd.Series(s).rank().to_numpy()
    n1, n0 = len(connues), len(inconnues)
    return float((rangs[:n1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ethiopie", default="data/raw/ethiopie_2021/resized")
    ap.add_argument("--modeles", default="modeles/maladies")
    ap.add_argument("--out", default="out/maladies/ethiopie")
    ap.add_argument("--tirages", type=int, default=20)
    ap.add_argument("--feuilles", default="data/feuilles", help="jeu préparé (validation tanzanienne, pour les seuils globaux de l'étape 2)")
    ap.add_argument("--sans-validation", action="store_true", help="ne pas recalculer la validation (pas de seuil global pour l'étape 2)")
    ap.add_argument("--graine", type=int, default=2026)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    infos = json.loads((Path(args.modeles) / "entrainement_maladies.json").read_text(encoding="utf-8"))
    rejet = dict(np.load(Path(args.modeles) / "rejet.npz"))
    images = lister(args.ethiopie)
    print(images.classe.value_counts().to_string(), "\n")
    sorties = sorties_modeles(images.chemin.tolist(), args.modeles)
    scores, L = familiarites(sorties, rejet, infos["rejet"].get("k_voisins", 10))

    connue = ~images.classe.str.startswith("inconnue").to_numpy()
    pred = np.array(CLASSES)[L.argmax(1)]
    vrai = images.classe.to_numpy()
    print(f"\nFeuilles éthiopiennes connues bien classées (sans rejet) : {(pred[connue] == vrai[connue]).mean():.3f}"
          f" | saines prises pour malades : {np.isin(pred[vrai == 'saine'], CLASSES[:2]).mean():.3f}"
          f" | inconnues déclarées saines : {(pred[~connue] == 'saine').mean():.3f}")

    rng = np.random.default_rng(args.graine)
    idx_connues = np.flatnonzero(connue)
    lignes = []
    for meth, s in scores.items():
        ligne = dict(methode=meth, auroc=round(auroc(s[connue], s[~connue]), 3))
        seuil_global = infos["rejet"]["seuils"].get(meth)
        if seuil_global is not None:
            ligne["acceptees_seuil_global"] = round(float((s[connue] >= seuil_global).mean()), 3)
            ligne["rejet_inconnue_seuil_global"] = round(float((s[~connue] < seuil_global).mean()), 3)
        acc, rej = [], []
        for _ in range(args.tirages):
            melange = rng.permutation(idx_connues)
            etal, mesure = melange[: len(melange) // 2], melange[len(melange) // 2:]
            seuil = np.quantile(s[etal], 1 - ACCEPTATION)
            acc.append((s[mesure] >= seuil).mean()); rej.append((s[~connue] < seuil).mean())
        ligne.update(acceptees_seuil_site=round(float(np.mean(acc)), 3),
                     rejet_inconnue_seuil_site=round(float(np.mean(rej)), 3),
                     rejet_inconnue_seuil_site_ecart_type=round(float(np.std(rej)), 3))
        lignes.append(ligne)
    tab = pd.DataFrame(lignes).sort_values(["rejet_inconnue_seuil_site", "auroc"], ascending=False)
    tab.to_csv(out / "rejet_ethiopie.csv", index=False)
    print("\n" + tab.to_string(index=False))
    meilleure = tab.iloc[0].methode
    actuelle = infos["rejet"]["methode"]
    print(f"\nMéthode retenue par la règle fixée à l'avance : {meilleure} (méthode actuelle : {actuelle})")

    # ---------- Partie 2 : architecture en deux étapes contre architecture à plat ----------
    sc2, p_malade, maladie = etape2(sorties, rejet)
    seuils2_globaux = {}
    index_csv = Path(args.feuilles) / "index.csv"
    if not args.sans_validation and index_csv.exists():
        val = pd.read_csv(index_csv)
        val = val[val.retenue & (val.ensemble == "validation") & (val.classe != "saine")]
        print(f"\nSorties sur les {len(val)} feuilles malades de la validation tanzanienne (seuils globaux de l'étape 2) :")
        s_val = sorties_modeles([str(Path(args.feuilles) / c) for c in val.chemin], args.modeles)
        sc2_val, _, _ = etape2(s_val, rejet)
        seuils2_globaux = {m: float(np.quantile(v, 1 - ACCEPTATION)) for m, v in sc2_val.items()}
    else:
        print("\nValidation non recalculée : pas de seuil global pour l'étape 2.")
    classe_plate = np.array(CLASSES)[L.argmax(1)]
    methode_plate = actuelle
    lignes2 = []
    seuil_plat = infos["rejet"]["seuils"][methode_plate]
    lignes2.append(dict(architecture="à plat (actuelle)", methode=methode_plate, seuil="global",
                        **mesurer(decider_a_plat(classe_plate, scores[methode_plate], seuil_plat), vrai)))
    for m, s in sc2.items():
        if m in seuils2_globaux:
            lignes2.append(dict(architecture="deux étapes", methode=m, seuil="global",
                                **mesurer(decider_deux_etapes(p_malade, maladie, s, seuils2_globaux[m]), vrai)))
    # Seuils par site : à chaque tirage, les connues sont coupées en deux moitiés, classe par classe.
    # À plat : seuil réglé sur toute la moitié d'étalonnage ; deux étapes : sur ses Sigatoka.
    # Les deux architectures sont mesurées sur les mêmes images : l'autre moitié et toute l'inconnue.
    inconnue_idx = np.flatnonzero(~connue)
    rng2 = np.random.default_rng(args.graine)
    cumul = {}
    for _ in range(args.tirages):
        etal, mesure_connues = [], []
        for c in ("saine", "cercosporiose_noire"):
            i = rng2.permutation(np.flatnonzero(vrai == c))
            etal.append(i[: len(i) // 2]); mesure_connues.append(i[len(i) // 2:])
        etal = np.concatenate(etal)
        mes = np.r_[np.concatenate(mesure_connues), inconnue_idx]
        t = np.quantile(scores[methode_plate][etal], 1 - ACCEPTATION)
        cumul.setdefault(("à plat (actuelle)", methode_plate), []).append(
            mesurer(decider_a_plat(classe_plate[mes], scores[methode_plate][mes], t), vrai[mes]))
        etal_s = etal[vrai[etal] == "cercosporiose_noire"]
        for m, s in sc2.items():
            t2 = np.quantile(s[etal_s], 1 - ACCEPTATION)
            cumul.setdefault(("deux étapes", m), []).append(
                mesurer(decider_deux_etapes(p_malade[mes], maladie[mes], s[mes], t2), vrai[mes]))
    for (arch, m), rs in cumul.items():
        lignes2.append(dict(architecture=arch, methode=m, seuil="par site", **pd.DataFrame(rs).mean().to_dict()))
    tab2 = pd.DataFrame(lignes2).round(3)
    tab2.to_csv(out / "architectures_ethiopie.csv", index=False)
    print("\nArchitecture à plat contre deux étapes (Éthiopie ; « non identifiée » = je ne sais pas ou malade non identifiée) :")
    print(tab2.to_string(index=False))
    site = tab2[tab2.seuil == "par site"]
    plate = site[site.architecture == "à plat (actuelle)"].iloc[0]
    eligibles = site[site.fausses_alertes_saines <= plate.fausses_alertes_saines]
    choix = eligibles.sort_values(["inconnue_non_identifiee", "maladies_detectees"], ascending=False).iloc[0]
    print(f"\nRetenue par la règle : {choix.architecture}, {choix.methode} "
          f"(inconnue non identifiée {choix.inconnue_non_identifiee:.3f} contre {plate.inconnue_non_identifiee:.3f} à plat)")
    (out / "parametres.json").write_text(json.dumps(dict(
        modele=infos.get("variante"), methode_actuelle=actuelle, methode_retenue=meilleure, tirages=args.tirages,
        seuil_etape1=SEUIL_ETAPE1, seuils_etape2_globaux=seuils2_globaux,
        architecture_retenue=f"{choix.architecture}, {choix.methode}",
        acceptation_cible=ACCEPTATION, effectifs=images.classe.value_counts().to_dict()), indent=2, ensure_ascii=False),
        encoding="utf-8")


if __name__ == "__main__":
    main()
