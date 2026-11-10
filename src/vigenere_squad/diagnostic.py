"""Diagnostic de l'installation (``vsquad diagnostic [--reparer]``).

Vérifie, dans l'ordre où les problèmes apparaissent en pratique : Python et
dépendances, dossier du projet, données et modèles de langue, outils de
cryptanalyse, serveur Ollama, modèle installé, vitesse réelle du modèle et
répartition CPU/GPU. Pour chaque problème, affiche la commande qui le corrige ;
avec ``--reparer``, corrige ce qui peut l'être automatiquement.
Sortie en ASCII pour toutes les consoles (Windows compris).
"""

from __future__ import annotations

import json
import platform
import shutil
import sys
import time
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
OK, ATT, ERR = "[ OK ]", "[ATTENTION]", "[ERREUR]"


class Rapport:
    def __init__(self):
        self.lignes: list[tuple[str, str, str]] = []

    def ajouter(self, etat: str, sujet: str, detail: str = "", conseil: str = "") -> None:
        self.lignes.append((etat, sujet, conseil))
        print(f"{etat:<12} {sujet}" + (f" : {detail}" if detail else ""), flush=True)
        if conseil and etat != OK:
            print(f"{'':<12}  -> {conseil}", flush=True)

    def erreurs(self) -> int:
        return sum(1 for e, _, _ in self.lignes if e == ERR)


def _get(hote: str, chemin: str, delai: float = 5) -> dict:
    with urllib.request.urlopen(hote + chemin, timeout=delai) as r:  # noqa: S310 (hôte local)
        return json.loads(r.read())


def _post(hote: str, chemin: str, corps: dict, delai: float) -> dict:
    req = urllib.request.Request(hote + chemin, data=json.dumps(corps).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=delai) as r:  # noqa: S310
        return json.loads(r.read())


def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("-")[0].split(".")[:3] if x.isdigit())


def diagnostiquer(reparer: bool = False, modele: str | None = None, rapide: bool = False) -> int:
    from .evaluation.executer import charger_config

    r = Rapport()
    print(f"Diagnostic Vigenere-Squad — {platform.system()} {platform.release()}, Python {sys.version.split()[0]}")
    print("-" * 72)

    # 1. Python et dossier
    if sys.version_info < (3, 11):
        r.ajouter(ERR, "Python", sys.version.split()[0], "Python >= 3.11 requis : lancer via `uv run ...` (uv l'installe)")
    else:
        r.ajouter(OK, "Python", sys.version.split()[0])
    attendus = ["pyproject.toml", "uv.lock", "config/experiment.yaml", "data/sources.json"]
    manquants = [f for f in attendus if not (RACINE / f).exists()]
    if manquants:
        r.ajouter(ERR, "Dossier du projet", f"fichiers absents : {manquants}",
                  "se placer dans le dossier extrait qui contient pyproject.toml (commande `cd`)")
        return 1
    r.ajouter(OK, "Dossier du projet", str(RACINE))
    cfg = charger_config()
    modele = modele or cfg["configurations"]["b_qwen3_4b"]["modele"]
    hote = cfg["environnement_execution"]["hote"]

    # 2. Données
    from .outils.langue import DOSSIER_MODELES

    corpus_ok = (RACINE / "data" / "corpus" / "standard.jsonl").exists()
    modeles_ok = (DOSSIER_MODELES / "quadgrammes_fr.npy").exists()
    if not (corpus_ok and modeles_ok) and reparer:
        print(f"{'':<12} construction des données (vsquad donnees)...", flush=True)
        from .evaluation.donnees import (CORPUS, VARIANTES, construire_modeles, ecrire_jsonl, generer_corpus,
                                         telecharger_et_verifier)

        telecharger_et_verifier()
        construire_modeles()
        for v in VARIANTES:
            ecrire_jsonl(generer_corpus(cfg["graine"], cfg["corpus"]["par_cellule"], v), CORPUS / f"{v}.jsonl")
        corpus_ok = modeles_ok = True
    if corpus_ok and modeles_ok:
        try:
            from .evaluation.donnees import telecharger_et_verifier

            telecharger_et_verifier()
            r.ajouter(OK, "Données", "textes sources vérifiés (SHA-256), modèles de langue et corpus présents")
        except Exception as e:  # noqa: BLE001
            r.ajouter(ERR, "Données", str(e), "re-télécharger le dépôt (un fichier de data/raw est altéré)")
    else:
        r.ajouter(ERR, "Données", "modèles de langue ou corpus absents", "uv run vsquad donnees")
        return 1

    # 3. Outils de cryptanalyse (sans LLM)
    from .heuristique import casser_baseline
    from .outils.chiffres import vigenere_chiffrer
    from .traces import Journal

    clair = ("IL ETAIT HUIT HEURES ET LE TRAIN SE PREPARAIT A PARTIR VERS LA MER AVEC SES VOYAGEURS "
             "QUI ATTENDAIENT SUR LE QUAI EN REGARDANT LES NUAGES PASSER AU DESSUS DE LA GARE")
    t0 = time.perf_counter()
    res = casser_baseline(vigenere_chiffrer(clair, "ROUTE"), Journal(None, "diag"))
    ok = res["clair"] == clair
    r.ajouter(OK if ok else ERR, "Outils de cryptanalyse",
              f"Vigenere casse en {time.perf_counter() - t0:.2f} s (cle {res['cle']})" if ok else "échec du test",
              "uv run pytest  (pour voir quel outil échoue)")

    # 4. Ollama
    try:
        version = _get(hote, "/api/version").get("version", "?")
    except Exception:  # noqa: BLE001
        conseil = ("démarrer l'application Ollama (menu Démarrer > Ollama) ; si elle n'est pas installée : "
                   "winget install Ollama.Ollama" if platform.system() == "Windows"
                   else "lancer `ollama serve` (installation : https://ollama.com/download)")
        r.ajouter(ERR, "Serveur Ollama", f"aucune réponse sur {hote}", conseil)
        return _conclure(r)
    if _version_tuple(version) < (0, 9):
        r.ajouter(ERR, "Serveur Ollama", f"version {version}", "mettre Ollama à jour (>= 0.9 requis)")
    else:
        r.ajouter(OK, "Serveur Ollama", f"version {version} sur {hote}")

    # 5. Modèle local
    noms = {m.get("name") for m in _get(hote, "/api/tags").get("models", [])}
    if modele not in noms:
        if reparer:
            print(f"{'':<12} téléchargement de {modele} (plusieurs Go)...", flush=True)
            from .llm import OllamaLLM

            OllamaLLM(modele, hote=hote).telecharger()
            noms.add(modele)
        else:
            r.ajouter(ERR, f"Modèle {modele}", "non installé",
                      f"ollama pull {modele}   (ou : uv run vsquad diagnostic --reparer)")
            return _conclure(r)
    r.ajouter(OK, f"Modèle {modele}", "installé (modèle local, aucun compte Ollama nécessaire)")
    if any(n and n.endswith(":cloud") for n in noms):
        r.ajouter(ATT, "Modèles cloud", "des modèles « :cloud » sont présents",
                  "ils ne sont pas utilisés ; ne pas se connecter à ollama.com, le projet est 100 % local")

    if rapide:
        return _conclure(r)

    # 6. Vitesse réelle et répartition CPU/GPU
    oc = cfg["configurations"]["b_qwen3_4b"]
    corps = {"model": modele, "stream": False, "think": False, "format": {"type": "object", "properties": {
        "reponse": {"type": "string", "maxLength": 60}}, "required": ["reponse"]},
        "messages": [{"role": "user", "content": "Réponds en JSON {\"reponse\": ...} : quel est le chiffre de "
                                                 "Vigenère en une phrase courte ?"}],
        "options": {"num_ctx": oc.get("contexte", 3072), "num_predict": 64, "temperature": 0}}
    print(f"{'':<12} mesure de la vitesse du modèle (premier chargement possible : 10-60 s)...", flush=True)
    try:
        t0 = time.perf_counter()
        d = _post(hote, "/api/chat", corps, 300)
        duree = time.perf_counter() - t0
        json.loads(d["message"]["content"])
        n_out = d.get("eval_count", 0)
        vitesse = n_out / (d.get("eval_duration", 1) / 1e9) if d.get("eval_duration") else 0
        etat = OK if vitesse >= 8 else ATT
        r.ajouter(etat, "Vitesse du modèle", f"{vitesse:.1f} jetons/s en génération, JSON valide ({duree:.0f} s "
                  f"avec chargement)",
                  "machine lente : l'évaluation complète sera longue ; envisager qwen3:1.7b (voir DEPANNAGE.md)")
    except Exception as e:  # noqa: BLE001
        r.ajouter(ERR, "Appel au modèle", str(e), "redémarrer Ollama puis relancer le diagnostic")
        return _conclure(r)
    try:
        ps = [m for m in _get(hote, "/api/ps").get("models", []) if m.get("name") == modele]
        if ps:
            taille, vram = ps[0].get("size", 0), ps[0].get("size_vram", 0)
            part = 100 * vram / taille if taille else 0
            if part >= 99:
                r.ajouter(OK, "Processeur", f"100 % sur la carte graphique ({taille / 2**30:.1f} Go)")
            elif part > 0:
                ctx_cfg = oc.get("contexte", 2048)
                conseil = ("réduire `contexte` dans config/experiment.yaml (ex. 2048)" if ctx_cfg > 2048 else
                           "les poids du modèle dépassent la mémoire graphique : fonctionnement normal mais plus "
                           "lent ; qwen3:1.7b tiendrait entièrement sur le GPU (voir DEPANNAGE.md)")
                r.ajouter(ATT, "Processeur", f"{part:.0f} % GPU / {100 - part:.0f} % CPU (le modèle déborde de la "
                          f"mémoire graphique)", conseil)
            else:
                r.ajouter(ATT, "Processeur", "100 % CPU (pas de carte graphique utilisée)",
                          "fonctionne, mais lentement : compter plusieurs minutes par chiffré")
    except Exception:  # noqa: BLE001
        pass

    # 7. Mémoire et disque
    from .evaluation.memoire import memoire_totale_go

    ram = memoire_totale_go()
    r.ajouter(OK if ram >= 8 else ATT, "Mémoire vive", f"{ram} Go", "8 Go minimum recommandés")
    libre = shutil.disk_usage(RACINE).free / 2**30
    r.ajouter(OK if libre >= 5 else ATT, "Espace disque", f"{libre:.0f} Go libres", "prévoir 5 Go (modèles, traces)")
    return _conclure(r)


def _conclure(r: Rapport) -> int:
    print("-" * 72)
    n = r.erreurs()
    if n == 0:
        print("Tout est prêt. Essai : uv run vsquad casser --fichier exemple_chiffre.txt --expliquer")
    else:
        print(f"{n} problème(s) bloquant(s) : appliquer les conseils ci-dessus, ou relancer avec --reparer.")
    return 0 if n == 0 else 1
