"""Module maladies : photos de feuilles, classifieur ONNX (processeur), décision en deux étapes.

Modèle et réglages : le fichier ONNX (config « maladies.modele ») et, à côté, entrainement_maladies.json
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
            "malade_non_identifiee": "feuille malade, maladie non identifiée", "je_ne_sais_pas": "je ne sais pas"}
VUES = {"identite": lambda x: x, "miroir_horizontal": lambda x: x[..., ::-1], "miroir_vertical": lambda x: x[..., ::-1, :],
        "rotation_180": lambda x: x[..., ::-1, ::-1]}


def charger_modele(reglages):
    import onnxruntime as ort
    chemin = Path(reglages["maladies"]["modele"])
    if not chemin.exists():
        raise RuntimeError(f"modèle introuvable : {chemin}")
    infos_path = chemin.parent / "entrainement_maladies.json"
    infos = json.loads(infos_path.read_text(encoding="utf-8")) if infos_path.exists() else {}
    rejet = infos.get("rejet", {})
    methode = rejet.get("methode", reglages["maladies"]["methode_rejet"])
    if methode not in ("proba_max", "energie"):
        raise RuntimeError(f"méthode de rejet « {methode} » non prise en charge à l'inférence")
    return dict(session=ort.InferenceSession(str(chemin), providers=["CPUExecutionProvider"]),
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
    ctx.journal.info(f"  Maladies : modèle {Path(reg['modele']).name}, {len(m['vues'])} vue(s), rejet {m['methode']} "
                     f"au seuil {m['seuil']:.4f} (réglages : {m['source_reglages']})")
    L = predire(chemins, m)
    reponse, p_malade, confiance, P = decider(L, m, reg["seuil_malade"])

    tab = pd.DataFrame(dict(fichier=chemins, lat=[p.lat for p in photos], lon=[p.lon for p in photos],
                            reponse=reponse, libelle=[LIBELLES[r] for r in reponse], p_malade=p_malade.round(3),
                            confiance=confiance.round(3),
                            **{f"p_{c}": P[:, k].round(3) for k, c in enumerate(m["classes"])}))
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

    malades = {"cercosporiose_noire", "fusariose", "malade_non_identifiee"}
    alertes = []
    for r in tab[tab.parcelle_id.notna() & tab.reponse.isin(malades)].itertuples():
        # Gravité forte même si la maladie n'est pas identifiée : ne pas savoir laquelle ne rend pas la situation moins urgente
        alertes.append(dict(parcelle_id=r.parcelle_id, module="maladies", type="feuille_malade", indice=r.reponse,
                            date=r.date, gravite="forte", valeur=r.p_malade, z=None,
                            confiance="normale", message=f"Photo {Path(r.fichier).name} : {r.libelle} "
                            f"(P(malade) = {r.p_malade:.2f}, confiance {r.confiance:.2f})",
                            source=Path(r.fichier).name, carte=None, preuve=r.preuve, geometry=Point(r.lon, r.lat)))
    par = []
    for pid, g in tab[tab.parcelle_id.notna()].groupby("parcelle_id"):
        n_mal = int(g.reponse.isin(malades).sum())
        par.append(dict(parcelle_id=pid, n_photos=len(g), n_malades=n_mal, part_malades=round(n_mal / len(g), 2),
                        maladies=", ".join(sorted(set(g.reponse[g.reponse.isin(malades)])))))
    pp = pd.DataFrame(par).set_index("parcelle_id") if par else pd.DataFrame()
    resume = dict(reponses=tab.reponse.value_counts().to_dict(), photos_localisees=int(tab.lat.notna().sum()),
                  photos_dans_parcelles=int(tab.parcelle_id.notna().sum()), methode_rejet=m["methode"], seuil_rejet=m["seuil"],
                  photos=tab[["fichier", "reponse", "libelle", "p_malade", "confiance", "parcelle_id", "preuve"]].to_dict("records"))
    ctx.journal.info(f"  Maladies : {len(tab)} photo(s) ; réponses {resume['reponses']} ; {resume['photos_dans_parcelles']} rattachée(s) à une parcelle")
    return Resultat(par_parcelle=pp, alertes=alertes, couches=[str(ctx.sortie / "maladies_photos.csv")], resume=resume)
