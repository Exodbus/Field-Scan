#!/usr/bin/env python3
"""Prospection hors Roboflow (Zenodo, Hugging Face) : liste compacte des dépôts qui parlent de bananiers vus du ciel.

Aucune donnée n'est téléchargée : seules les fiches (titre, licence, fichiers, taille) sont lues par les API publiques.

Exemple :
    python scripts/v6_prosp_depots.py
"""
import re
import requests

ZENODO = ["banana UAV", "banana drone", "banana plantation orthomosaic", "banana plant detection", "plantain UAV",
          "banano dron", "platano dron", "banana tree counting", "banana aerial annotations", "musa UAV detection",
          "banana canopy UAV", "bananier drone"]
HF = ["banana", "banano", "plantain", "platano", "musa", "bananier"]


def propre(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t or ""))


def main():
    vus = set()
    for q in ZENODO:
        try:
            r = requests.get("https://zenodo.org/api/records", params={"q": q, "size": 25, "type": "dataset"}, timeout=60)
            hits = r.json().get("hits", {}).get("hits", [])
        except Exception as e:
            print("zenodo", q, type(e).__name__); continue
        for h in hits:
            if h["id"] in vus:
                continue
            vus.add(h["id"])
            m = h["metadata"]
            txt = (m.get("title", "") + " " + propre(m.get("description"))).lower()
            if not re.search(r"banan|plantain|pl[aá]tano|musa ", txt):
                continue
            fichiers = h.get("files", [])
            taille = sum(f.get("size", 0) for f in fichiers) / 1e6
            lic = (m.get("license") or {}).get("id")
            print(f"ZENODO {h['id']} | {m.get('publication_date')} | {lic} | {m.get('access_right')} | {taille:.0f} Mo | "
                  f"{m.get('title')[:110]} | {propre(m.get('description'))[:260]}")
    for q in HF:
        try:
            r = requests.get("https://huggingface.co/api/datasets", params={"search": q, "limit": 100}, timeout=60)
            for d in r.json():
                print(f"HF {d['id']} | {d.get('lastModified', '')[:10]} | téléchargements {d.get('downloads')} | "
                      f"{[t for t in d.get('tags', []) if t.startswith(('license', 'task'))]}")
        except Exception as e:
            print("hf", q, type(e).__name__)


if __name__ == "__main__":
    main()
