"""Bulletin par parcelle : score de santé, niveau, priorité, alertes et leurs preuves.

Score (formule transparente, réglages dans config.yaml, section « score ») :
  100, moins une pénalité par module en alerte sur la parcelle (un module compte une fois) :
  (une alerte de gravité forte et de confiance normale place la parcelle au moins en orange)
  pénalité = pénalité du module x (1 si gravité forte, sinon facteur_moyenne) x (facteur_confiance_faible si confiance faible).
Niveaux : vert (>= seuil_vert), orange (>= seuil_orange), rouge (en dessous). Une parcelle qu'aucun module
n'a pu évaluer est « non évaluée » (pas de score inventé).
Priorité : parcelles en alerte, par score croissant, puis surface décroissante.
"""
import html
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

MODULE_PENALITE = {"vigueur": "vigueur", "stress": "stress", "temporel": "evolution", "maladies": "maladie", "comptage": "densite"}
COULEURS = {"vert": "#2e7d32", "orange": "#ef6c00", "rouge": "#c62828", "non évalué": "#9e9e9e"}


def _vignette(ctx, alerte, chemin_png):
    """Découpe la carte source autour de l'alerte, avec le contour de la parcelle (noir) et de la zone (magenta)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import rasterio
    from rasterio.windows import from_bounds
    carte = ctx.sortie / alerte["carte"]
    if not carte.exists():
        return None
    parc = ctx.parcelles.set_index("parcelle_id").loc[[alerte["parcelle_id"]]]
    with rasterio.open(carte) as src:
        geo_alerte = gpd.GeoSeries([alerte["geometry"]], crs="EPSG:4326").to_crs(src.crs)
        geo_parc = parc.to_crs(src.crs).geometry
        x0, y0, x1, y1 = geo_parc.union_all().union(geo_alerte.iloc[0]).bounds
        marge = max(x1 - x0, y1 - y0) * 0.3 + 3 * abs(src.transform.a)
        x0, y0, x1, y1 = x0 - marge, y0 - marge, x1 + marge, y1 + marge
        fen = from_bounds(x0, y0, x1, y1, src.transform)
        a = src.read(1, window=fen, boundless=True, fill_value=np.nan).astype("float32")
    centre = "residu" in alerte["carte"] or "delta" in alerte["carte"]
    v = a[~np.isnan(a)]
    if v.size == 0:
        return None
    if centre:
        m = float(np.nanpercentile(np.abs(v), 98)) or 0.05
        vmin, vmax, cmap = -m, m, "RdBu"
    else:
        vmin, vmax, cmap = float(np.percentile(v, 2)), float(np.percentile(v, 98)), "RdYlGn"
    fig, ax = plt.subplots(figsize=(4.2, 4.2), dpi=100)
    im = ax.imshow(a, extent=(x0, x1, y0, y1), cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")
    geo_parc.boundary.plot(ax=ax, color="black", linewidth=1.2)
    if alerte["type"].startswith("zone"):
        geo_alerte.boundary.plot(ax=ax, color="magenta", linewidth=1.6)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(""); ax.set_ylabel("")
    ax.set_title(f"{alerte['parcelle_id']} | {alerte['indice']} | {alerte['date']}", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
    fig.tight_layout(); fig.savefig(chemin_png); plt.close(fig)
    return str(chemin_png.relative_to(ctx.sortie)).replace("\\", "/")


def calculer(ctx, statuts):
    """Tableau par parcelle (score, niveau, priorité) et liste des alertes numérotées, avec leur preuve."""
    reg = ctx.reglages["score"]
    pen, f_moy = reg["penalites"], reg.get("facteur_moyenne", 0.6)
    f_conf, s_vert, s_orange = reg.get("facteur_confiance_faible", 0.5), reg.get("seuil_vert", 80), reg.get("seuil_orange", 60)
    alertes = [a for nom in ctx.resultats for a in ctx.resultats[nom].alertes]
    (ctx.sortie / "preuves").mkdir(exist_ok=True)
    for k, a in enumerate(alertes, start=1):
        a["id"] = f"A{k:03d}"
        if a.get("preuve") is None and a.get("carte"):
            try:
                a["preuve"] = _vignette(ctx, a, ctx.sortie / "preuves" / f"{a['id']}.png")
            except Exception as e:       # une vignette manquante n'empêche pas le bulletin
                ctx.journal.avertir(f"Vignette {a['id']} non produite : {e}")
                a["preuve"] = None

    evaluees = set()
    for nom, r in ctx.resultats.items():
        if not r.par_parcelle.empty and "statut" in r.par_parcelle:
            evaluees |= set(r.par_parcelle.index[r.par_parcelle.statut == "ok"])
        elif not r.par_parcelle.empty:
            evaluees |= set(r.par_parcelle.dropna(how="all").index)
    lignes = []
    for _, p in ctx.parcelles.iterrows():
        pid = p.parcelle_id
        siennes = [a for a in alertes if a["parcelle_id"] == pid]
        retrait, detail = 0.0, []
        for module in sorted({a["module"] for a in siennes}):
            du_module = [a for a in siennes if a["module"] == module]
            f = max(1.0 if a["gravite"] == "forte" else f_moy for a in du_module)
            if all(a.get("confiance") == "faible" for a in du_module):
                f *= f_conf
            r = pen.get(MODULE_PENALITE.get(module, module), 0) * f
            retrait += r
            detail.append(f"{module} −{r:.0f}")
        if pid in evaluees:
            score = max(0.0, 100.0 - retrait)
            niveau = "vert" if score >= s_vert else "orange" if score >= s_orange else "rouge"
            if niveau == "vert" and any(a["gravite"] == "forte" and a.get("confiance") != "faible" for a in siennes):
                niveau = "orange"         # une alerte forte et fiable ne laisse jamais une parcelle en vert
        else:
            score, niveau = np.nan, "non évalué"
        lignes.append(dict(parcelle_id=pid, surface_ha=p.surface_ha, score=round(score, 0) if score == score else np.nan,
                           niveau=niveau, n_alertes=len(siennes), detail_score=", ".join(detail),
                           alertes=" ; ".join(f"[{a['id']}] {a['message']}" for a in siennes)))
    tab = pd.DataFrame(lignes)
    en_alerte = tab[tab.n_alertes > 0].sort_values(["score", "surface_ha"], ascending=[True, False])
    tab["priorite"] = tab.parcelle_id.map({pid: k for k, pid in enumerate(en_alerte.parcelle_id, start=1)})
    for nom, r in ctx.resultats.items():
        if not r.par_parcelle.empty:
            tab = tab.merge(r.par_parcelle.add_prefix(f"{nom}_"), left_on="parcelle_id", right_index=True, how="left")
    return tab, alertes


def _carte_fixe(ctx, tab, alertes, chemin):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    g = ctx.parcelles.merge(tab[["parcelle_id", "niveau", "score"]], on="parcelle_id")
    fig, ax = plt.subplots(figsize=(8, 7), dpi=110)
    g.plot(ax=ax, color=[COULEURS[n] for n in g.niveau], edgecolor="black", linewidth=0.6, alpha=0.85)
    zones = [a["geometry"] for a in alertes if a["type"].startswith("zone")]
    if zones:
        gpd.GeoSeries(zones, crs="EPSG:4326").to_crs(g.crs).boundary.plot(ax=ax, color="magenta", linewidth=1)
    points = [a["geometry"] for a in alertes if a["geometry"] is not None and a["geometry"].geom_type == "Point"]
    if points:
        gpd.GeoSeries(points, crs="EPSG:4326").to_crs(g.crs).plot(ax=ax, color="#d81b60", markersize=18, edgecolor="white")
    for _, r in g.iterrows():
        c = r.geometry.representative_point()
        ax.annotate(f"{r.parcelle_id}\n{'' if r.score != r.score else int(r.score)}", (c.x, c.y), ha="center", va="center", fontsize=6)
    ax.set_title("Bulletin Field Scan : score de santé par parcelle (zones en alerte en magenta)", fontsize=10)
    ax.set_axis_off()
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in COULEURS.values()]
    ax.legend(handles, list(COULEURS), loc="lower left", fontsize=7)
    fig.tight_layout(); fig.savefig(chemin); plt.close(fig)


def _html(ctx, tab, alertes, statuts, chemin):
    parc = ctx.parcelles.to_crs("EPSG:4326").merge(tab[["parcelle_id", "score", "niveau", "priorite", "n_alertes"]], on="parcelle_id")
    parc_json = json.loads(parc[["parcelle_id", "score", "niveau", "priorite", "n_alertes", "geometry"]].to_json(na="null"))
    al = gpd.GeoDataFrame([{k: v for k, v in a.items()} for a in alertes], geometry="geometry", crs="EPSG:4326") if alertes else None
    al_json = json.loads(al[["id", "parcelle_id", "module", "type", "gravite", "date", "message", "source", "preuve", "geometry"]]
                         .to_json(na="null")) if al is not None else {"type": "FeatureCollection", "features": []}
    e = html.escape
    s2 = ctx.cache.get("s2")
    derniere = s2.dates[-1] if s2 is not None and s2.dates else None
    lignes = []
    for _, r in tab.sort_values(["priorite", "parcelle_id"], na_position="last").iterrows():
        siennes = [a for a in alertes if a["parcelle_id"] == r.parcelle_id]
        liens = "<br>".join(f"<a href='#' onclick=\"montrer('{a['id']}');return false;\">[{a['id']}]</a> {e(a['message'])}" for a in siennes) or "—"
        score = "—" if r.score != r.score else int(r.score)
        prio = "" if r.priorite != r.priorite else int(r.priorite)
        dd = r.get("vigueur_date")
        if isinstance(dd, str) and derniere and dd != derniere:
            date_txt = f"{dd}<br><small style='color:#c62828'>image du {derniere} inexploitable (nuages)</small>"
        else:
            date_txt = dd if isinstance(dd, str) else "—"
        n_det = r.get("comptage_n_pieds")
        if n_det == n_det and n_det is not None:
            pieds_txt = (f"{int(n_det)} détectés<br><small>≈ {int(r.comptage_n_pieds_estimes_bas)} à "
                         f"{int(r.comptage_n_pieds_estimes_haut)} estimés</small>")
        else:
            pieds_txt = "—"
        lignes.append(f"<tr><td>{prio}</td><td><b>{e(r.parcelle_id)}</b></td><td>{r.surface_ha:.1f}</td><td>{date_txt}</td><td>{pieds_txt}</td>"
                      f"<td><span class='pastille' style='background:{COULEURS[r.niveau]}'>{score}</span> {r.niveau}</td>"
                      f"<td>{e(r.detail_score or '')}</td><td>{liens}</td></tr>")
    mod = "".join(f"<li><b>{m}</b> : {s['statut']}" + (f" ({e(s.get('raison', ''))})" if s.get("raison") else "")
                  + (f", {s['alertes']} alerte(s)" if "alertes" in s else "") + "</li>" for m, s in statuts.items())
    reg = ctx.reglages["score"]
    note_comptage = ""
    if "comptage" in ctx.resultats:
        rc = ctx.resultats["comptage"].resume
        note_comptage = (f"<p><b>Pieds</b> : {rc.get('pieds', 0)} pieds détectés sur l'orthomosaïque, soit environ "
                         f"{rc.get('pieds_estimes_bas', 0)} à {rc.get('pieds_estimes_haut', 0)} pieds estimés (détectés x "
                         f"{rc.get('coefficient_bas')} à x{rc.get('coefficient_haut')}, rapports réel / détecté mesurés en "
                         "validation en plantation dense et en agroforesterie). Les jeunes plantations aux feuilles fines "
                         "sont sous-comptées au-delà de cette fourchette. Les points détectés sont dans pieds.geojson.</p>")
    photos_html = ""
    if "maladies" in ctx.resultats:
        ph = ctx.resultats["maladies"].resume.get("photos", [])
        cases = "".join(f"<figure style='display:inline-block;width:170px;margin:4px;vertical-align:top;font-size:12px'>"
                        f"<a href='{e(x['preuve'])}' target='_blank'><img src='{e(x['preuve'])}' style='width:165px;height:125px;object-fit:cover'></a>"
                        f"<figcaption><b>{e(x['libelle'])}</b><br>P(malade) {x['p_malade']:.2f}, confiance {x['confiance']:.2f}<br>"
                        f"{'parcelle ' + e(str(x['parcelle_id'])) if x['parcelle_id'] else '<i>non localisée</i>'}</figcaption></figure>"
                        for x in ph[:300])
        res = ctx.resultats["maladies"].resume
        photos_html = (f"<section><h3>Photos de feuilles ({len(ph)})</h3><p>Réponses : "
                       + ", ".join(f"{k} {v}" for k, v in res.get("reponses", {}).items())
                       + f". Rejet par {res.get('methode_rejet')} au seuil {res.get('seuil_rejet', 0):.4f} (95 % des feuilles connues "
                       "de la validation acceptées). Une feuille malade est signalée même quand la maladie n'est pas identifiée.</p>"
                       + cases + (f"<p>… et {len(ph) - 300} autres (voir maladies_photos.csv)</p>" if len(ph) > 300 else "") + "</section>")
    page = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>Bulletin Field Scan</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>body{{font-family:system-ui,sans-serif;margin:0;color:#222}} header{{padding:12px 18px;background:#1b5e20;color:white}}
main{{display:flex;flex-wrap:wrap}} #carte{{flex:1 1 560px;height:600px}} #cote{{flex:1 1 380px;padding:12px;max-height:600px;overflow:auto}}
table{{border-collapse:collapse;width:100%;font-size:13px}} td,th{{border-bottom:1px solid #ddd;padding:4px 6px;text-align:left;vertical-align:top}}
.pastille{{display:inline-block;min-width:28px;text-align:center;color:white;border-radius:10px;padding:1px 6px}}
section{{padding:12px 18px}} #preuve img{{max-width:100%;border:1px solid #ccc}}</style></head><body>
<header><h2 style="margin:0">Bulletin de santé par parcelle</h2>
<div>{len(tab)} parcelles, {tab.surface_ha.sum():.1f} ha | {len(alertes)} alerte(s) | {int((tab.niveau == 'rouge').sum())} rouge(s), {int((tab.niveau == 'orange').sum())} orange(s)</div></header>
<main><div id="carte"></div><div id="cote"><h3>Preuve de l'alerte sélectionnée</h3><div id="preuve">Cliquez sur une alerte (carte ou tableau) pour voir l'image source.</div></div></main>
<section><h3>Parcelles par priorité</h3><table><tr><th>Priorité</th><th>Parcelle</th><th>ha</th><th>Données du</th><th>Pieds</th><th>Score</th><th>Calcul</th><th>Alertes</th></tr>{''.join(lignes)}</table></section>
{photos_html}
<section><h3>Modules</h3><ul>{mod}</ul>
<p><b>Score</b> : 100 moins une pénalité par module en alerte ({', '.join(f'{k} {v}' for k, v in reg['penalites'].items())}),
réduite à {int(reg.get('facteur_moyenne', 0.6) * 100)} % pour une gravité moyenne et divisée par deux si la confiance est faible.
Vert ≥ {reg.get('seuil_vert', 80)}, orange ≥ {reg.get('seuil_orange', 60)}, rouge en dessous ; une alerte forte et fiable place la parcelle au moins en orange.</p>
{note_comptage}</section>
<script>
const parcelles={json.dumps(parc_json)}, alertes={json.dumps(al_json)}, couleurs={json.dumps(COULEURS)};
const carte=L.map('carte'); L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',{{maxZoom:19,attribution:'Esri'}}).addTo(carte);
const cp=L.geoJSON(parcelles,{{style:f=>({{color:'#000',weight:1,fillColor:couleurs[f.properties.niveau],fillOpacity:0.45}}),
 onEachFeature:(f,l)=>l.bindTooltip(f.properties.parcelle_id+' : '+(f.properties.score===null?'non évaluée':f.properties.score))}}).addTo(carte);
const parId={{}}; const ca=L.geoJSON(alertes,{{filter:f=>f.properties.type.startsWith('zone'),style:{{color:'magenta',weight:2,fillOpacity:0.2}},
 onEachFeature:(f,l)=>{{parId[f.properties.id]=l; l.on('click',()=>montrer(f.properties.id));}}}}).addTo(carte);
L.geoJSON(alertes,{{filter:f=>f.geometry.type==='Point',pointToLayer:(f,ll)=>L.circleMarker(ll,{{radius:7,color:'#fff',weight:2,fillColor:'#d81b60',fillOpacity:0.95}}),
 onEachFeature:(f,l)=>l.on('click',()=>montrer(f.properties.id))}}).addTo(carte);
carte.fitBounds(cp.getBounds());
function montrer(id){{const f=alertes.features.find(x=>x.properties.id===id); if(!f) return; const p=f.properties;
 const contenu='<p><b>['+p.id+'] '+p.parcelle_id+'</b> | '+p.module+' | '+p.type+' | gravité '+p.gravite+' | '+p.date+'</p><p>'+p.message+'</p>'+
 (p.preuve?'<img src="'+p.preuve+'" style="max-width:100%">':'<i>pas de vignette</i>')+'<p style="font-size:12px">Source : '+p.source+'</p>';
 document.getElementById('preuve').innerHTML=contenu;
 const g=L.geoJSON(f); carte.fitBounds(g.getBounds(),{{maxZoom:16}});
 L.popup({{maxWidth:440,minWidth:300}}).setLatLng(g.getBounds().getCenter()).setContent(contenu).openOn(carte);}}
</script></body></html>"""
    Path(chemin).write_text(page, encoding="utf-8")


def produire(ctx, statuts):
    tab, alertes = calculer(ctx, statuts)
    tab.to_csv(ctx.sortie / "bulletin.csv", index=False)
    if alertes:
        gdf = gpd.GeoDataFrame(alertes, geometry="geometry", crs="EPSG:4326")
        gdf.to_file(ctx.sortie / "alertes.geojson", driver="GeoJSON")
    else:
        (ctx.sortie / "alertes.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    _carte_fixe(ctx, tab, alertes, ctx.sortie / "carte_bulletin.png")
    _html(ctx, tab, alertes, statuts, ctx.sortie / "bulletin.html")
    return tab, alertes
