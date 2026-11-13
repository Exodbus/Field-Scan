"""Module maladies : photos de feuilles, classifieur (processeur), décision en deux étapes.

Deux sortes de modèles, selon « maladies.modele » dans la config :

1. Un **dossier** de réseaux PyTorch avec leur seuils.json : ConvNeXt-Tiny (v2 du binôme, soupe v2 + v8, C5) ou ViT
   DINOv2 / DINOv3 (DINOv2-FT, D5, E5), selon « reseau » ; 3 classes (saine, cercosporiose noire, fusariose) ou 5
   (plus Cordana et Pestalotiopsis), selon « classes ». Moyenne des réseaux, chacun sur 1 ou 4 vues (identité, deux
   miroirs, quart de tour), préparation de la v2 (rotation EXIF, recadrage carré au centre à 224 pixels, JPEG qualité 95).
   Décision de la v2 (seuils.json) :
     malade si 1 - P(saine) >= seuil_alerte ;
     maladie nommée si elle fait au moins seuil_nom de P(malade), sinon « malade, non identifiée » ;
     « je ne sais pas » si la plus forte probabilité est sous seuil_confiance.
   Ce sont les mêmes calculs que modeles/maladies_binome/maladies_v2/classifieur.py.

   **Deux branches** (si « maladies.aiguilleur » est donné ; docs/protocole_maladies_deux_branches.md et
   docs/protocole_maladies_cinq_classes.md) : un aiguilleur (DINOv2 figé + régression logistique) repère les photos
   prises de loin (plante entière). Elles passent par « maladies.modele_loin » (la v2), et leur alerte porte le message
   « à confirmer par un gros plan de la zone malade ». Les autres passent par « maladies.modele ».
   Branche « proche » : une photo « je ne sais pas » dont P(malade) atteint le seuil d'alerte devient « malade, non
   identifiée » (alerte) si « maladies.jnsp_alerte » est vrai (amendement 2 du protocole « cinq classes ») ; de même
   pour la branche « loin » avec « maladies.jnsp_alerte_loin » (amendement 3). Une alerte de la branche « loin » a une
   confiance « faible » dans le bulletin (pénalité réduite).
   Probabilités affichées : mise à l'échelle de température (« maladies.temperature », réglée sur la validation) ; les
   décisions restent prises sur les probabilités brutes.

2. Un **fichier ONNX** (ancien classifieur EfficientNet-B0) et, à côté, entrainement_maladies.json
(classes, vues, normalisation, méthode et seuil de rejet réglés sur la validation). Préparation identique
à la validation : rotation EXIF, petit côté ramené à 256 pixels, redimensionnement à 224, centre 224 x 224,
moyenne des sorties sur les vues (identité, miroirs, rotation de 180°).

Décision (seuil de rejet = celui de la validation, 95 % des feuilles connues acceptées) :
  P(malade) = P(cercosporiose) + P(fusariose)
  P(malade) <  seuil_malade : « saine » si confiance >= seuil, sinon « je ne sais pas » ;
  P(malade) >= seuil_malade : la maladie la plus probable si confiance >= seuil, sinon « malade, non identifiée ».
Une photo avec coordonnées GPS est rattachée à sa parcelle ; une feuille malade y déclenche une alerte,
dont la preuve est la photo elle-même. Les photos sans GPS figurent dans le bulletin, à part.
"""
import json
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from PIL import Image, ImageOps
from shapely.geometry import Point

from fieldscan.modules import Resultat

LIBELLES = {"saine": "feuille saine", "cercosporiose_noire": "cercosporiose noire (Sigatoka)",
            "fusariose": "fusariose ou autre flétrissement vasculaire (à confirmer par un examen du pseudo-tronc)",
            "malade_non_identifiee": "feuille malade, maladie non identifiée", "je_ne_sais_pas": "je ne sais pas",
            "cordana": "cordana (taches foliaires à Cordana musae)",
            "pestalotiopsis": "pestalotiopsis (taches foliaires à Pestalotiopsis)",
            "autre_maladie": "feuille malade, autre maladie (ni cercosporiose noire ni fusariose)",
            "a_verifier": "à vérifier : le modèle ne sait pas dire si la feuille est saine"}
VUES = {"identite": lambda x: x, "miroir_horizontal": lambda x: x[..., ::-1], "miroir_vertical": lambda x: x[..., ::-1, :],
        "rotation_180": lambda x: x[..., ::-1, ::-1]}


CLASSES_CONVNEXT = ["saine", "cercosporiose_noire", "fusariose"]   # ordre des sorties : saine, black_sigatoka, fusarium
NOMS_CHAINE = {"saine": "saine", "black_sigatoka": "cercosporiose_noire", "fusarium": "fusariose", "cordana": "cordana",
               "pestalotiopsis": "pestalotiopsis", "autre": "autre_maladie", "other": "autre_maladie"}
MESSAGE_LOIN = "photo prise de loin : à confirmer par un gros plan de la zone malade"
IMAGENET = ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])


def _vit(reseau, n_classes):
    """DINOv2 ViT-B/14 (torch.hub) ou DINOv3 ViT-B/16 (timm) + tête linéaire sur [jeton de classe, moyenne des jetons
    d'image], comme dans les carnets d'entraînement (notebooks/entrainer_maladies_*_kaggle.py)."""
    import torch
    if reseau in ("dinov2", "dinov2l"):
        dos = torch.hub.load("facebookresearch/dinov2", "dinov2_vitb14" if reseau == "dinov2" else "dinov2_vitl14", trust_repo=True)
    else:
        import timm
        dos = timm.create_model("vit_base_patch16_dinov3.lvd1689m", pretrained=False, num_classes=0, dynamic_img_size=True)

    class Vit(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.dino, self.tete = dos, torch.nn.Linear(2 * getattr(dos, "embed_dim", 768), n_classes)

        def forward(self, x):
            f = self.dino.forward_features(x)
            c, t = (f["x_norm_clstoken"], f["x_norm_patchtokens"]) if isinstance(f, dict) else (f[:, 0], f[:, self.dino.num_prefix_tokens:])
            return self.tete(torch.cat([c, t.mean(1)], 1))
    return Vit()


def charger_convnext(dossier):
    """Dossier de réseaux (*.pt, poids 16 ou 32 bits) et leur seuils.json : ConvNeXt-Tiny (v2, soupe, C5) ou ViT DINOv2 /
    DINOv3 (DINOv2-FT, D5, E5), selon « reseau » dans seuils.json ; 3 ou 5 classes selon « classes »."""
    import torch
    from torchvision import models
    seuils = json.loads((dossier / "seuils.json").read_text(encoding="utf-8"))
    # Format du binôme (v10b) : une liste « membres » (un seul pris en charge ici), réseau « timm:<nom> », taille de
    # lecture, taille d'apprentissage, normalisation ; docs/protocole_maladies_v10b.md
    membres = seuils.get("membres") or [{}]
    if len(membres) != 1:
        raise RuntimeError(f"{dossier} : {len(membres)} familles de réseaux, une seule prise en charge")
    mb = membres[0]
    reseau = mb.get("reseau", seuils.get("reseau", "convnext"))
    classes = [NOMS_CHAINE[c] for c in seuils.get("classes", ["saine", "black_sigatoka", "fusarium"])]
    fichiers = sorted(dossier.glob(mb.get("motif", "*.pt")))[:seuils.get("nb_reseaux", 99)]
    reseaux = []
    for chemin in fichiers:
        if reseau == "convnext":
            r = models.convnext_tiny(weights=None)
            r.classifier[2] = torch.nn.Linear(r.classifier[2].in_features, len(classes))
        elif reseau.startswith("timm:"):   # v10b du binôme : ConvNeXt-Tiny aux poids DINOv3 (timm >= 1.0.20)
            import timm
            try:   # comme le classifieur du binôme : img_size pour les ViT, ignoré par les ConvNeXt
                r = timm.create_model(reseau.split(":", 1)[1], pretrained=False, num_classes=len(classes),
                                      img_size=mb.get("taille_apprentissage", mb.get("taille", 224)), dynamic_img_size=True)
            except TypeError:
                r = timm.create_model(reseau.split(":", 1)[1], pretrained=False, num_classes=len(classes))
        else:
            r = _vit(reseau, len(classes))
        poids = torch.load(chemin, map_location="cpu", weights_only=True)
        r.load_state_dict({k: v.float() if v.is_floating_point() else v for k, v in poids.items()})
        reseaux.append(r.eval())
    if not reseaux:
        raise RuntimeError(f"aucun réseau *.pt dans {dossier}")
    norm = seuils.get("normalisation", {"moyenne": mb.get("moyenne", IMAGENET[0]), "ecart_type": mb.get("ecart", IMAGENET[1])})
    return dict(type="convnext", reseau=reseau, reseaux=reseaux, classes=classes,
                vues=["identite", "miroir_horizontal", "miroir_vertical", "quart_de_tour"] if seuils.get("quatre_vues", True) else ["identite"],
                moyenne=np.array(norm.get("moyenne", IMAGENET[0]), "float32"), ecart=np.array(norm.get("ecart_type", IMAGENET[1]), "float32"),
                methode="proba_max", seuil=float(seuils["seuil_confiance"]), seuil_alerte=float(seuils["seuil_alerte"]),
                seuil_nom=float(seuils["seuil_nom"]), nom=seuils.get("modele", dossier.name), source_reglages=str(dossier / "seuils.json"),
                taille=int(mb.get("taille", 224)), lecture=mb.get("lecture"),
                # v10b : « autre » n'est jamais nommée (classe fourre-tout) -> « malade, non identifiée »
                nommer_autre=False,
                # règle B : « saine » seulement si P(saine) >= seuil_confiance ; tout doute restant -> « à vérifier » (alerte)
                regle_b=bool(seuils.get("regle_b", False)),
                # règle de la v11 : un doute avec 1 - P(saine) >= ce seuil -> « malade, non identifiée »
                seuil_inconnu_malade=seuils.get("seuil_inconnu_malade"))


def preparer_convnext(chemin, moyenne=IMAGENET[0], ecart=IMAGENET[1], taille=224, lecture=None):
    """Préparation de la v2 (classifieur.preparer) : photo remise droite, côté le plus court à `taille` pixels (224 ; 384
    pour la v10b), recadrage carré au centre, réenregistrée en JPEG qualité 95 ; puis normalisation (ImageNet par défaut)."""
    import io
    with Image.open(chemin) as im:
        im.draft("RGB", (lecture or 2 * taille, lecture or 2 * taille))   # v10b : JPEG lu en au moins 896 px
        im = ImageOps.exif_transpose(im).convert("RGB")
        petite = ImageOps.fit(im, (taille, taille), method=Image.BILINEAR)
    tampon = io.BytesIO()
    petite.save(tampon, format="JPEG", quality=95)
    a = np.asarray(Image.open(tampon).convert("RGB"), dtype="float32") / 255.0
    a = (a - np.asarray(moyenne, "float32")) / np.asarray(ecart, "float32")
    return a.transpose(2, 0, 1)


def predire_convnext(chemins, m, lot=16):
    """Probabilités (n, nombre de classes) : moyenne des vues, puis des réseaux (comme classifieur.probabilites)."""
    import torch
    vues = {"identite": lambda x: x, "miroir_horizontal": lambda x: x.flip(3), "miroir_vertical": lambda x: x.flip(2),
            "quart_de_tour": lambda x: x.rot90(1, (2, 3))}
    sorties = []
    with torch.no_grad():
        for i in range(0, len(chemins), lot):
            x = torch.from_numpy(np.stack([preparer_convnext(c, m["moyenne"], m["ecart"], m.get("taille", 224), m.get("lecture")) for c in chemins[i:i + lot]]))
            p = torch.stack([sum(torch.softmax(r(vues[v](x)), 1) for v in m["vues"]) / len(m["vues"]) for r in m["reseaux"]]).mean(0)
            sorties.append(p.numpy())
    return np.concatenate(sorties) if sorties else np.zeros((0, len(m["classes"])), "float32")


def decider_convnext(P, m):
    """Décision de la v2, pour 3 ou 5 classes (la première est « saine ») ; renvoie les mêmes sorties que decider()."""
    p_malade = 1 - P[:, 0]
    part = P[:, 1:].max(1) / np.maximum(p_malade, 1e-9)
    maladie = np.array(m["classes"])[1 + P[:, 1:].argmax(1)]
    nommable = (part >= m["seuil_nom"]) & ((maladie != "autre_maladie") | m.get("nommer_autre", True))
    reponse = np.where(p_malade < m["seuil_alerte"], "saine", np.where(nommable, maladie, "malade_non_identifiee")).astype(object)
    confiance = P.max(1)
    reponse[confiance < m["seuil"]] = "je_ne_sais_pas"
    if m.get("jnsp_alerte"):   # amendement 2 du protocole « cinq classes » : sûr que c'est malade, pas de quelle maladie
        reponse[(confiance < m["seuil"]) & (p_malade >= m["seuil_alerte"])] = "malade_non_identifiee"
    if m.get("regle_b"):   # v10b, règle B : une feuille n'est dite saine que si P(saine) atteint le seuil de confiance
        reponse[(reponse == "saine") & (P[:, 0] < m["seuil"])] = "je_ne_sais_pas"
    if m.get("seuil_inconnu_malade") is not None:   # v10b, règle de la v11 : doute probablement malade -> non identifiée
        reponse[(reponse == "je_ne_sais_pas") & (p_malade >= float(m["seuil_inconnu_malade"]))] = "malade_non_identifiee"
    if m.get("regle_b"):   # le doute qui reste donne une alerte, comme dans la chaîne du binôme (« inconnu » -> alerte)
        reponse[reponse == "je_ne_sais_pas"] = "a_verifier"
    return reponse.astype(str), p_malade, confiance, P


def charger_aiguilleur(chemin):
    """Aiguilleur « loin / près » (docs/protocole_maladies_deux_branches.md, partie A ; scripts/ajuster_aiguilleur.py)."""
    import torch
    a = {k: v for k, v in np.load(chemin).items()}
    a["dino"] = torch.hub.load("facebookresearch/dinov2", "dinov2_vitb14", trust_repo=True).eval()
    return a


def p_loin(chemins, a, lot=16):
    """P(photo prise de loin) : caractéristiques DINOv2 figées (vue d'origine, préparation de la v2), puis logistique."""
    import torch
    car = []
    with torch.no_grad():
        for i in range(0, len(chemins), lot):
            x = torch.from_numpy(np.stack([preparer_convnext(c) for c in chemins[i:i + lot]]))
            f = a["dino"].forward_features(x)
            car.append(torch.cat([f["x_norm_clstoken"], f["x_norm_patchtokens"].mean(1)], 1).double().numpy())
    if not car:
        return np.zeros(0)
    z = ((np.concatenate(car) - a["moyenne"]) / a["ecart"]) @ a["poids"].T + a["biais"]
    z -= z.max(1, keepdims=True)
    return np.exp(z[:, 1]) / np.exp(z).sum(1)


# ---------------------------------------------------------------------------------------------------------------------
# F1 « trois morceaux 2 x 2 » (adopté par Corentin le 13/11/2026 ; docs/nuit_2026-11-12/recap.md, section 2 ;
# définition : scripts/m12_banc_finalistes.py, CANDIDATS["F1_trois_morceaux2x2"]). Lecteur proche = moyenne géométrique
# à poids égaux de la v10b (lue entière et en 4 morceaux), de la soupe v2 + v8 et de la v2, décidée avec les seuils de
# la v10b sauf la confiance (0,70) ; photo « loin » : réponse de la v2 si elle alerte, sinon celle du lecteur proche.
# Les fonctions ci-dessous sont des copies exactes de celles du script de référence.
# ---------------------------------------------------------------------------------------------------------------------
MALADES = {"cercosporiose_noire", "fusariose", "malade_non_identifiee", "cordana", "pestalotiopsis", "autre_maladie",
           "a_verifier"}


def morceaux_2x2(chemin):
    """Quatre morceaux de 60 % de côté, aux quatre coins de la photo remise droite (JPEG lu en au moins 896 px)."""
    import io
    with Image.open(chemin) as im:
        im.draft("RGB", (896, 896))
        im = ImageOps.exif_transpose(im).convert("RGB")
    w, h = im.size
    mw, mh = max(1, round(0.6 * w)), max(1, round(0.6 * h))
    sortie = []
    for iy in range(2):
        for ix in range(2):
            x0, y0 = round(ix * (w - mw)), round(iy * (h - mh))
            t = io.BytesIO()
            im.crop((x0, y0, x0 + mw, y0 + mh)).save(t, format="PNG")
            t.seek(0)
            sortie.append(t)
    return sortie


def lecture_morceaux(P10, G2):
    """P(malade) = moyenne de celle de la photo entière et de la moyenne des 2 plus fortes P(malade) des 4 morceaux ;
    P(saine) remplacée, les maladies gardant leurs proportions."""
    pm = ((1 - P10[:, 0]) + np.sort(1 - G2[:, :, 0], 1)[:, -2:].mean(1)) / 2
    reste = np.clip(1 - P10[:, 0], 1e-9, None)
    Q = P10 * (pm / reste)[:, None]
    Q[:, 0] = 1 - pm
    return Q


def melange_geometrique(P10, Pso, Pv2):
    """Moyenne géométrique à poids égaux sur saine / cercosporiose / fusariose ; « autre » de la v10b gardée (poids 1/3)."""
    w = 1 / 3
    lg = w * (np.log(np.clip(P10[:, :3], 1e-9, 1)) + np.log(np.clip(Pso, 1e-9, 1)) + np.log(np.clip(Pv2, 1e-9, 1)))
    q = np.hstack([np.exp(lg), w * P10[:, 3:]])
    return q / q.sum(1, keepdims=True)


def decider_melange(P10, Pso, Pv2, pl, G2, m_proche, m_loin, loin_ou_proche=True):
    """Décision F1 sur des probabilités déjà calculées. G2 : (n, 4, classes) ou None (sans lecture 2 x 2).
    Renvoie (reponse, p_malade, confiance, P du lecteur proche, masque des photos décidées par la v2)."""
    P10l = P10 if G2 is None else lecture_morceaux(P10, G2)
    rp, pmp, cp, Pp = decider_convnext(melange_geometrique(P10l, Pso, Pv2), m_proche)
    rl, pml, cl, _ = decider_convnext(Pv2, m_loin)
    loin = pl >= 0.5
    par_v2 = loin & (np.isin(rl, list(MALADES)) if loin_ou_proche else True)
    return np.where(par_v2, rl, rp), np.where(par_v2, pml, pmp), np.where(par_v2, cl, cp), Pp, par_v2


def _executer_melange(ctx, reg, m, chemins, temp):
    """Chaîne F1 complète : aiguilleur, trois lecteurs, morceaux 2 x 2 de la v10b, décision. Lit les morceaux sur toutes
    les photos dont la réponse vient du lecteur proche (environ 10 s de plus par photo sur le processeur)."""
    import time
    n = len(chemins)
    ms, mv2 = (charger_convnext(Path(d)) for d in reg["melange_proche"])
    m_proche = {**m, "seuil": float(reg["seuil_confiance_melange"]), "jnsp_alerte": bool(reg.get("jnsp_alerte", False))}
    m_loin = {**mv2, "jnsp_alerte": bool(reg.get("jnsp_alerte_loin", False))}
    ctx.journal.info(f"  Maladies : F1, mélange géométrique {m['nom']} + {ms['nom']} + {mv2['nom']}, confiance sous "
                     f"{m_proche['seuil']:.2f}, morceaux 2 x 2 : {'oui' if reg.get('morceaux_2x2') else 'non'}")
    pl = p_loin(chemins, charger_aiguilleur(Path(reg["aiguilleur"]))) if reg.get("aiguilleur") else np.zeros(n)
    P10, Pso, Pv2 = predire_convnext(chemins, m), predire_convnext(chemins, ms), predire_convnext(chemins, mv2)
    G2 = None
    if reg.get("morceaux_2x2"):
        rl = decider_convnext(Pv2, m_loin)[0]
        besoin = ~((pl >= 0.5) & np.isin(rl, list(MALADES))) if reg.get("loin_ou_proche", True) else (pl < 0.5)
        G2 = np.tile(np.eye(P10.shape[1])[0], (n, 4, 1))   # « saine » pour les photos dont la v2 décide seule (non lu)
        idx, t0 = np.flatnonzero(besoin), time.time()
        for k in range(0, len(idx), 8):
            lot = idx[k:k + 8]
            G2[lot] = predire_convnext([t for i in lot for t in morceaux_2x2(chemins[i])], m).reshape(len(lot), 4, -1)
        ctx.journal.info(f"  Maladies : morceaux 2 x 2 lus sur {len(idx)} photo(s) en {time.time() - t0:.0f} s")
    reponse, p_malade, confiance, Pp, par_v2 = decider_melange(P10, Pso, Pv2, pl, G2, m_proche, m_loin,
                                                               reg.get("loin_ou_proche", True))
    # Probabilités affichées : celles du mélange (température « melange » si elle est réglée un jour), ou celles de la v2
    # pour les photos qu'elle décide (température « loin »)
    Pp_aff, Pv2_aff = calibrer(Pp, temp.get("melange")), calibrer(Pv2, temp.get("loin"))
    probas = {c: np.where(par_v2, np.nan, Pp_aff[:, k]) for k, c in enumerate(m["classes"])}
    for k, c in enumerate(mv2["classes"]):
        probas[c] = np.where(par_v2, Pv2_aff[:, k], probas[c])
    branche = np.where(pl >= 0.5, "loin", "proche").astype(object) if reg.get("aiguilleur") else np.full(n, "unique", dtype=object)
    ctx.journal.info(f"  Maladies : {int((pl >= 0.5).sum())} photo(s) prise(s) de loin, dont {int(par_v2.sum())} décidée(s) par la v2")
    return reponse.astype(str), p_malade.astype(float), confiance.astype(float), probas, branche, pl


def calibrer(P, t):
    """Probabilités affichées : mise à l'échelle de température (t réglé sur la validation) ; décisions inchangées."""
    if not t or t == 1:
        return P
    q = np.power(np.clip(P, 1e-12, 1), 1 / t)
    return q / q.sum(1, keepdims=True)


def charger_modele(reglages):
    chemin = Path(reglages["maladies"]["modele"])
    if not chemin.exists():
        raise RuntimeError(f"modèle introuvable : {chemin}")
    if chemin.is_dir():
        return charger_convnext(chemin)
    import onnxruntime as ort
    infos_path = chemin.parent / "entrainement_maladies.json"
    infos = json.loads(infos_path.read_text(encoding="utf-8")) if infos_path.exists() else {}
    rejet = infos.get("rejet", {})
    methode = rejet.get("methode", reglages["maladies"]["methode_rejet"])
    if methode not in ("proba_max", "energie"):
        raise RuntimeError(f"méthode de rejet « {methode} » non prise en charge à l'inférence")
    return dict(type="onnx", session=ort.InferenceSession(str(chemin), providers=["CPUExecutionProvider"]),
                classes=infos.get("classes", ["cercosporiose_noire", "fusariose", "saine"]),
                vues=infos.get("vues", list(VUES)),
                moyenne=np.array(infos.get("normalisation", {}).get("moyenne", [0.485, 0.456, 0.406]), "float32"),
                ecart=np.array(infos.get("normalisation", {}).get("ecart_type", [0.229, 0.224, 0.225]), "float32"),
                methode=methode, seuil=float(rejet.get("seuils", {}).get(methode, reglages["maladies"]["seuil_rejet"])),
                source_reglages=str(infos_path) if infos else "config.yaml")


def preparer_image(chemin, m):
    im = ImageOps.exif_transpose(Image.open(chemin)).convert("RGB")
    r = 256 / min(im.size)
    if r < 1:
        im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    r = 224 / min(im.size)
    im = im.resize((max(224, round(im.width * r)), max(224, round(im.height * r))), Image.BILINEAR)
    g, h = (im.width - 224) // 2, (im.height - 224) // 2
    a = np.asarray(im.crop((g, h, g + 224, h + 224)), dtype="float32") / 255.0
    return ((a - m["moyenne"]) / m["ecart"]).transpose(2, 0, 1)


def predire(chemins, m, lot=16):
    """Logits moyennés sur les vues, une ligne par photo."""
    sorties = []
    nom_entree = m["session"].get_inputs()[0].name
    for i in range(0, len(chemins), lot):
        x = np.stack([preparer_image(c, m) for c in chemins[i:i + lot]]).astype("float32")
        L = np.mean([m["session"].run(None, {nom_entree: np.ascontiguousarray(VUES[v](x))})[0] for v in m["vues"]], axis=0)
        sorties.append(L)
    return np.concatenate(sorties)


def decider(L, m, seuil_malade):
    P = np.exp(L - L.max(1, keepdims=True))
    P /= P.sum(1, keepdims=True)
    cls = m["classes"]
    i_malades = [cls.index("cercosporiose_noire"), cls.index("fusariose")]
    p_malade = P[:, i_malades].sum(1)
    confiance = P.max(1) if m["methode"] == "proba_max" else (np.log(np.exp(L - L.max(1, keepdims=True)).sum(1)) + L.max(1))
    maladie = np.array(cls)[np.array(i_malades)[P[:, i_malades].argmax(1)]]
    sur = confiance >= m["seuil"]
    reponse = np.where(p_malade < seuil_malade, np.where(sur, "saine", "je_ne_sais_pas"),
                       np.where(sur, maladie, "malade_non_identifiee"))
    return reponse, p_malade, confiance, P


def _date_photo(chemin):
    try:
        brut = Image.open(chemin).getexif().get_ifd(0x8769).get(36867) or Image.open(chemin).getexif().get(306)
        return datetime.strptime(brut, "%Y:%m:%d %H:%M:%S").date().isoformat() if brut else ""
    except Exception:
        return ""


def _preuve(chemin, sortie, nom):
    im = ImageOps.exif_transpose(Image.open(chemin)).convert("RGB")
    im.thumbnail((640, 640))
    dest = sortie / "preuves" / nom
    dest.parent.mkdir(exist_ok=True)
    im.save(dest, quality=85)
    return f"preuves/{nom}"


def executer(ctx):
    reg = ctx.reglages["maladies"]
    m = charger_modele(ctx.reglages)
    photos = ctx.inventaire.photos
    chemins = [p.chemin for p in photos]
    temp = reg.get("temperature", {}) or {}
    f1 = bool(reg.get("melange_proche")) and m["type"] == "convnext" and len(chemins) > 0
    if f1:   # F1 (adopté le 13/11/2026)
        ctx.journal.info(f"  Maladies : v10b {m['nom']} ({len(m['reseaux'])} réseau(x) {m['reseau']}), alerte à "
                         f"{m['seuil_alerte']:.2f}, nom à {m['seuil_nom']:.2f} (réglages : {m['source_reglages']})")
        reponse, p_malade, confiance, probas, branche, pl = _executer_melange(ctx, reg, m, chemins, temp)
    elif m["type"] == "convnext":
        ctx.journal.info(f"  Maladies : modèle {m['nom']} ({len(m['reseaux'])} réseau(x) {m['reseau']}, {len(m['classes'])} classes), "
                         f"{len(m['vues'])} vue(s), alerte à {m['seuil_alerte']:.2f}, nom à {m['seuil_nom']:.2f}, "
                         f"« je ne sais pas » sous {m['seuil']:.4f} (réglages : {m['source_reglages']})")
        m["jnsp_alerte"] = bool(reg.get("jnsp_alerte", False))
        reponse, p_malade, confiance, P = decider_convnext(predire_convnext(chemins, m), m)
        P_aff = calibrer(P, temp.get("proche"))
    else:
        ctx.journal.info(f"  Maladies : modèle {Path(reg['modele']).name}, {len(m['vues'])} vue(s), rejet {m['methode']} "
                         f"au seuil {m['seuil']:.4f} (réglages : {m['source_reglages']})")
        L = predire(chemins, m)
        reponse, p_malade, confiance, P = decider(L, m, reg["seuil_malade"])
        P_aff = P
    classes = list(m["classes"])
    if not f1:
        probas = {c: P_aff[:, k].copy() for k, c in enumerate(classes)}
        branche, pl = np.full(len(chemins), "unique", dtype=object), np.full(len(chemins), np.nan)
    if not f1 and reg.get("aiguilleur") and m["type"] == "convnext" and len(chemins):
        # Architecture à deux branches (docs/protocole_maladies_cinq_classes.md, section 4) : les photos prises de loin
        # (plante entière) passent par le modèle « loin » (la v2), avec un message « à confirmer par un gros plan ».
        pl = p_loin(chemins, charger_aiguilleur(Path(reg["aiguilleur"])))
        loin = pl >= 0.5
        branche = np.where(loin, "loin", "proche").astype(object)
        ctx.journal.info(f"  Maladies : aiguilleur loin / près ({reg['aiguilleur']}) : {int(loin.sum())} photo(s) prise(s) de loin")
        if loin.any():
            mf = charger_convnext(Path(reg["modele_loin"]))
            mf["jnsp_alerte"] = bool(reg.get("jnsp_alerte_loin", False))   # amendement 3 du protocole « cinq classes »
            idx = np.flatnonzero(loin)
            rf, pmf, cf, Pf = decider_convnext(predire_convnext([chemins[i] for i in idx], mf), mf)
            reponse, p_malade, confiance = reponse.astype(object), p_malade.astype(float), confiance.astype(float)
            reponse[idx], p_malade[idx], confiance[idx] = rf, pmf, cf
            Pf_aff = calibrer(Pf, temp.get("loin"))
            for c in set(classes) | set(mf["classes"]):
                probas.setdefault(c, np.full(len(chemins), np.nan))
                probas[c][idx] = Pf_aff[:, mf["classes"].index(c)] if c in mf["classes"] else np.nan
            reponse = reponse.astype(str)
    p_malade_aff = 1 - probas["saine"]
    tab = pd.DataFrame(dict(fichier=chemins, lat=[p.lat for p in photos], lon=[p.lon for p in photos],
                            reponse=reponse, libelle=[LIBELLES[r] for r in reponse], p_malade=np.round(p_malade, 3),
                            p_malade_affichee=np.round(p_malade_aff, 3), confiance=np.round(confiance, 3),
                            branche=branche, p_loin=np.round(pl, 3), **{f"p_{c}": np.round(v, 3) for c, v in probas.items()}))
    tab["date"] = [_date_photo(c) for c in chemins]
    loc = tab.dropna(subset=["lat", "lon"])
    tab["parcelle_id"] = None
    if len(loc):
        pts = gpd.GeoDataFrame(loc[[]], geometry=gpd.points_from_xy(loc.lon, loc.lat), crs="EPSG:4326")
        jointure = gpd.sjoin(pts, ctx.parcelles.to_crs("EPSG:4326")[["parcelle_id", "geometry"]], how="left", predicate="within")
        jointure = jointure[~jointure.index.duplicated()]
        tab.loc[jointure.index, "parcelle_id"] = jointure.parcelle_id.values
    tab["preuve"] = [_preuve(c, ctx.sortie, f"photo_{k:04d}.jpg") for k, c in enumerate(chemins, start=1)]
    tab.to_csv(ctx.sortie / "maladies_photos.csv", index=False)

    malades = {"cercosporiose_noire", "fusariose", "malade_non_identifiee", "cordana", "pestalotiopsis", "autre_maladie",
               "a_verifier"}
    alertes = []
    for r in tab[tab.parcelle_id.notna() & tab.reponse.isin(malades)].itertuples():
        # Gravité forte même si la maladie n'est pas identifiée : ne pas savoir laquelle ne rend pas la situation moins urgente
        alertes.append(dict(parcelle_id=r.parcelle_id, module="maladies", type="feuille_malade", indice=r.reponse,
                            date=r.date, gravite="forte", valeur=r.p_malade, z=None,
                            # loin, ou doute de la règle B (« à vérifier ») : pénalité réduite, à confirmer
                            confiance="faible" if r.branche == "loin" or r.reponse == "a_verifier" else "normale",
                            message=f"Photo {Path(r.fichier).name} : {r.libelle} (P(malade) = {r.p_malade_affichee:.2f}, "
                            f"confiance {r.confiance:.2f})" + (f" ; {MESSAGE_LOIN}" if r.branche == "loin" else ""),
                            source=Path(r.fichier).name, carte=None, preuve=r.preuve, geometry=Point(r.lon, r.lat)))
    par = []
    for pid, g in tab[tab.parcelle_id.notna()].groupby("parcelle_id"):
        n_mal = int(g.reponse.isin(malades).sum())
        par.append(dict(parcelle_id=pid, n_photos=len(g), n_malades=n_mal, part_malades=round(n_mal / len(g), 2),
                        maladies=", ".join(sorted(set(g.reponse[g.reponse.isin(malades)])))))
    pp = pd.DataFrame(par).set_index("parcelle_id") if par else pd.DataFrame()
    resume = dict(reponses=tab.reponse.value_counts().to_dict(), photos_localisees=int(tab.lat.notna().sum()),
                  photos_dans_parcelles=int(tab.parcelle_id.notna().sum()), methode_rejet=m["methode"], seuil_rejet=m["seuil"],
                  modele=m.get("nom", Path(reg["modele"]).name), seuil_alerte=m.get("seuil_alerte", reg["seuil_malade"]),
                  photos_loin=int((tab.branche == "loin").sum()),
                  photos=tab[["fichier", "reponse", "libelle", "p_malade", "p_malade_affichee", "confiance", "branche",
                              "parcelle_id", "preuve"]].to_dict("records"))
    ctx.journal.info(f"  Maladies : {len(tab)} photo(s) ; réponses {resume['reponses']} ; {resume['photos_dans_parcelles']} rattachée(s) à une parcelle")
    return Resultat(par_parcelle=pp, alertes=alertes, couches=[str(ctx.sortie / "maladies_photos.csv")], resume=resume)
