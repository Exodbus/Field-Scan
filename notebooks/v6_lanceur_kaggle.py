# Field Scan, nuit du 12/11 : lanceur Kaggle des recettes v6 du détecteur de centres (agent C-entraîneur).
# Chaque recette tourne dans un sous-processus sur son propre GPU (T4 x 2 : deux recettes à la fois).
# Le code d'entraînement (notebooks/v6_travail_centres.py) est embarqué ci-dessous (base64) par scripts/v6_entr_pousser.py.
# Réglage seulement : le travail retire les juges au chargement (ensembles test_*, dossier cg/) et ne les lit jamais.
import base64, glob, json, os, shutil, subprocess, sys, time, zipfile

RECETTES = []   # remplacé
PLACES_DEFAUT = 3
SOURCE_B64 = ""   # remplacé

t_debut = time.time()
print("Installation de onnx et onnxruntime…", flush=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--timeout", "20", "--retries", "1", "onnx", "onnxruntime"])
z = [p for p in glob.glob("/kaggle/input/**/comptage_v6_5cm*.zip", recursive=True) if os.path.isfile(p)]
d = [os.path.dirname(p) for p in glob.glob("/kaggle/input/**/tuiles.csv", recursive=True)
     if "comptage-v6-5cm" in p or "comptage_v6_5cm" in p]          # jamais le jeu des neufs (comptage-v6-neufs)
assert z or d, "Introuvable : comptage_v6_5cm.zip ou dossier comptage_v6_5cm"
if d:
    D = d[0]
else:
    D = "/tmp/v6"; shutil.rmtree(D, ignore_errors=True)
    with zipfile.ZipFile(z[0]) as zz:
        zz.extractall(D)
    if not os.path.exists(f"{D}/tuiles.csv"):
        D = os.path.dirname(glob.glob(f"{D}/**/tuiles.csv", recursive=True)[0])
print("Données :", D, "| préparées en", round(time.time() - t_debut), "s", flush=True)
TRAVAIL = "/kaggle/working/v6_travail_centres.py"
open(TRAVAIL, "w", encoding="utf-8").write(base64.b64decode(SOURCE_B64).decode("utf-8"))

import torch
n_gpu = max(1, torch.cuda.device_count())
print(n_gpu, "GPU :", [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())], flush=True)


def resoudre(r):
    r = dict(r)
    if r.get("melange_poids"):
        r["melange_poids"] = [[c if os.path.exists(c) else (glob.glob(f"/kaggle/input/**/{c}", recursive=True) or [c])[0], w]
                              for c, w in r["melange_poids"]]
    if r.get("distillation"):
        r["distillation"] = [glob.glob(f"/kaggle/input/**/{c}", recursive=True)[0] for c in r["distillation"]]
    for cle in ("jeux_neufs", "jeu_finca"):           # nom de jeu -> dossier contenant tuiles.csv (jeu Kaggle comptage-v6-neufs)
        if r.get(cle):
            noms = r[cle] if isinstance(r[cle], list) else [r[cle]]
            dossiers = [os.path.dirname(glob.glob(f"/kaggle/input/**/{n}/**/tuiles.csv", recursive=True)[0]) for n in noms]
            r[cle] = dossiers if isinstance(r[cle], list) else dossiers[0]
    if r.get("init") and not os.path.exists(r["init"]):
        c = glob.glob(f"/kaggle/input/**/{r['init']}", recursive=True)
        assert c, f"poids de départ introuvables : {r['init']}"
        r["init"] = c[0]
    return r


PLACES = int(os.environ.get("V6_PLACES", "0")) or PLACES_DEFAUT   # sous-processus simultanés (répartis sur les GPU)
file_attente = list(RECETTES)
finis = set()
en_cours = {}   # gpu -> (processus, nom, fichier journal, position lue)
while file_attente or en_cours:
    for g in range(PLACES):
        prets = [r for r in file_attente if r.get("apres") in (None, *finis)]   # « apres » : attend la fin d'une autre recette
        if g not in en_cours and prets:
            file_attente.remove(prets[0]); r = resoudre(prets[0])
            sortie = f"/kaggle/working/{r['nom']}"
            os.makedirs(sortie, exist_ok=True)
            env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(g % n_gpu), V6_DONNEES=D, V6_SORTIE=sortie, V6_RECETTE=json.dumps(r),
                       PYTHONIOENCODING="utf-8", OMP_NUM_THREADS="1", **({"V6_ESSAI": "1"} if r.get("essai") else {}))
            log = open(f"{sortie}/console.txt", "w")
            p = subprocess.Popen([sys.executable, "-u", TRAVAIL], env=env, stdout=log, stderr=subprocess.STDOUT)
            en_cours[g] = [p, r["nom"], f"{sortie}/console.txt", 0]
            print(f"[{time.strftime('%H:%M')}] lancé {r['nom']} sur GPU {g % n_gpu}", flush=True)
    time.sleep(60)
    for g in list(en_cours):
        p, nom, chemin, pos = en_cours[g]
        with open(chemin, encoding="utf-8", errors="replace") as f:
            f.seek(pos); neuf = f.read(); en_cours[g][3] = f.tell()
        for ligne in neuf.splitlines():
            if ligne.strip() and not ligne.startswith("    seuil"):
                print(f"[{nom}] {ligne}", flush=True)
        if p.poll() is not None:
            print(f"[{time.strftime('%H:%M')}] {nom} terminé, code {p.returncode}", flush=True)
            del en_cours[g]; finis.add(nom)
os.remove(TRAVAIL)
print("TOUT EST FINI en", round((time.time() - t_debut) / 60), "min", flush=True)
for r in RECETTES:
    print(r["nom"], sorted(os.listdir(f"/kaggle/working/{r['nom']}")))
