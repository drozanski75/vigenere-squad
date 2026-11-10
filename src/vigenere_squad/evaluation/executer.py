"""Exécution des expériences : principal (ablation), robustesse, défaillances,
explications, Shannon, Kasiski/autoclave. Écrit results/raw/ et traces/.

Les exécutions sont reprenables : un fichier brut complet n'est pas recalculé.
"""

from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path

import yaml

from ..agents.base import ParametresExecution
from ..heuristique import casser_baseline, politique_heuristique
from ..llm import LLMDefaillant, LLMSimule, OllamaLLM
from ..orchestrateur import ConfigOrchestrateur, Orchestrateur
from ..outils import attaques, chiffres, stats
from ..outils.texte import ALPHABET, lettres
from ..traces import Journal
from .memoire import PicMemoire, rss_python_mo
from .donnees import CORPUS, LONGUEURS, extrait, generer_corpus, lire_jsonl, textes_test, tranche

RACINE = Path(__file__).resolve().parents[3]
# VSQUAD_SORTIE permet d'écrire ailleurs (ex. reproduce-small -> build/small/) sans toucher aux résultats publiés
BASE = RACINE / os.environ["VSQUAD_SORTIE"] if os.environ.get("VSQUAD_SORTIE") else RACINE
RESULTS = BASE / "results"
TRACES = BASE / "traces"
SITE = BASE / "site"


def charger_config(chemin: Path | None = None) -> dict:
    cfg = yaml.safe_load((chemin or RACINE / "config" / "experiment.yaml").read_text(encoding="utf-8"))
    hote = os.environ.get("OLLAMA_HOST")  # ex. http://ollama:11434 dans Docker Compose
    if hote:
        cfg["environnement_execution"]["hote"] = hote if hote.startswith("http") else f"http://{hote}"
    return cfg


def precision_lettres(a: str, b: str) -> float:
    la, lb = lettres(a or ""), lettres(b or "")
    if not lb:
        return 0.0
    return sum(x == y for x, y in zip(la, lb)) / len(lb)


def sous_ensemble(corpus: list[dict], par_cellule: int | None, longueurs: list[int] | None = None) -> list[dict]:
    """Sous-ensemble stratifié : ``par_cellule`` chiffrés par (procédé, longueur),
    éventuellement restreint à certaines longueurs nominales."""
    if longueurs:
        corpus = [e for e in corpus if int(e["id"].split("-")[-2]) in longueurs]
    if not par_cellule:
        return corpus
    vus: dict = {}
    choisis = []
    for e in corpus:
        k = (e["procede"], e["tranche"])
        if vus.get(k, 0) < par_cellule:
            vus[k] = vus.get(k, 0) + 1
            choisis.append(e)
    return choisis


def creer_llm(cfg_conf: dict, cfg: dict, graine: int, simule: bool = False):
    if simule:
        return LLMSimule(politique_heuristique)
    oc = cfg["orchestrateur"]
    return OllamaLLM(
        modele=cfg_conf["modele"], hote=cfg["environnement_execution"]["hote"],
        temperature=cfg_conf.get("temperature", 0.3), graine=graine,
        contexte_max=cfg_conf.get("contexte", 2048), jetons_max=cfg_conf.get("jetons_max", 256),
        delai=oc.get("delai_llm_s", 180),
    )


def creer_orchestrateur(llm, cfg: dict, expliquer: bool = False) -> Orchestrateur:
    oc = cfg["orchestrateur"]
    params = ParametresExecution(reessais=oc["reessais"], tours_max=oc["tours_max"],
                                 delai_outil_s=oc["delai_outil_s"], contraindre_outils=oc["contraindre_outils"])
    return Orchestrateur(llm, ConfigOrchestrateur(
        iterations_max=oc["iterations_max"], seuil_garde_fou=oc["seuil_garde_fou"],
        seuil_repli=oc["seuil_repli"], expliquer=expliquer, params=params))


def _ligne(e: dict, res: dict, config: str, rep: int, experience: str, memoire: dict | None = None) -> dict:
    return {
        "experience": experience, "configuration": config, "repetition": rep, "id": e["id"],
        "variante": e["variante"], "procede": e["procede"], "longueur": e["longueur"], "tranche": e["tranche"],
        "longueur_cle": e.get("longueur_cle"),
        "procede_trouve": res.get("procede"), "cle_trouvee": res.get("cle"),
        "succes_exact": lettres(res.get("clair") or "") == lettres(e["clair"]),
        "procede_correct": res.get("procede") == e["procede"],
        "precision_lettres": round(precision_lettres(res.get("clair"), e["clair"]), 4),
        "statut": res.get("statut"), "iterations": res.get("iterations"),
        "replis": res.get("replis", []), "compteurs": res.get("compteurs", {}),
        "duree_s": res.get("duree_s"),
        "rss_python_mo": (memoire or {}).get("rss_python_mo"),
        "rss_ollama_mo": (memoire or {}).get("rss_ollama_mo"),
        "exercice_valide": res.get("exercice_valide"),
    }


def executer_lot(experience: str, config: str, cfg_conf: dict, corpus: list[dict], rep: int, cfg: dict,
                 simule: bool = False, fautes: dict | None = None, journal_console=print,
                 injection: bool = False) -> Path:
    sortie = RESULTS / "raw" / experience / f"{config}_rep{rep}.jsonl"
    if sortie.exists() and len(sortie.read_text(encoding="utf-8").splitlines()) == len(corpus):
        journal_console(f"  [déjà fait] {sortie.relative_to(RACINE)}")
        return sortie
    sortie.parent.mkdir(parents=True, exist_ok=True)
    graine = cfg["graine"] * 1000 + rep
    orch = None
    if cfg_conf["type"] == "agents":
        llm = creer_llm(cfg_conf, cfg, graine, simule)
        if fautes:
            llm = LLMDefaillant(llm, taux=fautes["llm"], graine=graine)
        orch = creer_orchestrateur(llm, cfg)
    deja = {}
    if sortie.exists():  # reprise après interruption
        for l in sortie.read_text(encoding="utf-8").splitlines():
            try:  # une ligne coupée par une interruption est ignorée (le chiffré sera refait)
                d = json.loads(l)
                deja[d["id"]] = l
            except (json.JSONDecodeError, KeyError):
                continue
    rng_fautes = random.Random(graine)
    with open(sortie, "w", encoding="utf-8", newline="\n") as f:
        for i, e in enumerate(corpus):
            if e["id"] in deja:
                f.write(deja[e["id"]] + "\n")
                continue
            j = Journal(TRACES / experience / config / f"rep{rep}" / f"{e['id']}.jsonl", f"{config}/rep{rep}/{e['id']}")
            pm = PicMemoire(ollama=orch is not None, hote=cfg["environnement_execution"]["hote"])
            pm.__enter__()
            if orch is None:
                res = casser_baseline(e["chiffre"], j, e["langue_systeme"], graine)
            else:
                orch_inj = None
                if fautes:
                    def orch_inj(nom, _r=rng_fautes):
                        if _r.random() < fautes["outils"]:
                            if _r.random() < 0.5:
                                raise TimeoutError(f"{nom} hors délai (faute injectée)")
                            raise RuntimeError(f"{nom} en échec (faute injectée)")
                res = orch.casser(e["chiffre"], j, e["langue_systeme"], graine, injecteur_fautes=orch_inj,
                                  injection_consignes=injection)
            pm.__exit__(None, None, None)
            ligne = _ligne(e, res if isinstance(res, dict) else res.model_dump(), config, rep, experience,
                           pm.resultat())
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            f.flush()
            journal_console(f"  {experience}/{config}/rep{rep} [{i + 1}/{len(corpus)}] {e['id']} "
                            f"{'OK' if ligne['succes_exact'] else '--'} {ligne['duree_s']}s")
    return sortie


def _preparer(corpus: list[dict], langue_systeme: str = "fr") -> list[dict]:
    for e in corpus:
        e["langue_systeme"] = langue_systeme
    return corpus


FILTRE: dict = {}


def charger_variante(variante: str) -> list[dict]:
    chemin = CORPUS / f"{variante}.jsonl"
    if not chemin.exists():  # génération automatique, déterministe (graine de la configuration)
        from .donnees import VARIANTES, ecrire_jsonl

        cfg = charger_config()
        print("Premier lancement : génération du corpus de chiffrés (graine "
              f"{cfg['graine']})...", flush=True)
        for v in VARIANTES:
            ecrire_jsonl(generer_corpus(cfg["graine"], cfg["corpus"]["par_cellule"], v), CORPUS / f"{v}.jsonl")
    corpus = lire_jsonl(chemin)
    if FILTRE:
        corpus = [e for e in corpus if e["procede"] in FILTRE["procedes"]
                  and int(e["id"].split("-")[-2]) in FILTRE["longueurs"]
                  and int(e["id"].split("-")[-1]) < FILTRE["par_cellule"]]
    return corpus


def marquer_simule(cfg: dict) -> dict:
    """Renomme les configurations à agents (suffixe _simule) quand le modèle
    simulé remplace le LLM, pour qu'aucun résultat simulé ne passe pour réel."""
    ren = {k: (k + "_simule" if v["type"] == "agents" else k) for k, v in cfg["configurations"].items()}
    cfg["configurations"] = {ren[k]: v for k, v in cfg["configurations"].items()}
    ex = cfg["experiences"]
    ex["robustesse"]["configurations"] = [ren.get(c, c) for c in ex["robustesse"]["configurations"]]
    for nom in ("defaillances", "explications", "injection"):
        ex[nom]["configuration"] = ren.get(ex[nom]["configuration"], ex[nom]["configuration"])
    return cfg


def config_petite(cfg: dict) -> dict:
    """Configuration réduite pour l'intégration continue (make reproduce-small) :
    référence (a) + modèle de très petite taille, corpus et répétitions réduits."""
    import copy

    c = copy.deepcopy(cfg)
    ci = c["ci"]
    c["configurations"] = {"a_baseline": {"type": "baseline"},
                           "ci_" + ci["modele"].replace(":", "_"): {"type": "agents", "modele": ci["modele"],
                                                                     "digest": ci["digest"], "temperature": 0.3,
                                                                     "contexte": 2048, "jetons_max": 256}}
    nom_ci = list(c["configurations"])[1]
    c["repetitions"] = ci["repetitions"]
    ex = c["experiences"]
    ex["principal"]["par_cellule_agents"] = ci["par_cellule"]
    ex["robustesse"].update(variantes=["sans_espaces"], configurations=["a_baseline", nom_ci], par_cellule_agents=1,
                            longueurs_agents=None)
    ex["principal"]["longueurs_agents"] = None
    ex["defaillances"]["longueurs"] = None
    ex["injection"]["longueurs"] = None
    ex["defaillances"].update(configuration=nom_ci, repetitions=1)
    ex["explications"].update(configuration=nom_ci, nombre=2)
    ex["injection"].update(configuration=nom_ci, par_cellule=1)
    ex["shannon"].update(longueurs_cle=[3, 6], longueurs_texte=[40, 100, 300], echantillons=5)
    ex["kasiski_autoclave"]["par_cellule"] = 1
    ex["longueur_min"].update(longueurs_texte=[40, 150, 600], echantillons=4, echantillons_reference=2)
    FILTRE.update(procedes=ci["procedes"], longueurs=ci["longueurs"], par_cellule=ci["par_cellule"])
    return c


# --- Expériences ---------------------------------------------------------------------------
def experience_principale(cfg: dict, configs: list[str] | None = None, simule: bool = False) -> None:
    ex = cfg["experiences"]["principal"]
    corpus = _preparer(charger_variante(ex["variante"]))
    for nom, conf in cfg["configurations"].items():
        if configs and nom not in configs:
            continue
        sel = corpus if conf["type"] == "baseline" else sous_ensemble(corpus, ex["par_cellule_agents"],
                                                                     ex.get("longueurs_agents"))
        for rep in range(cfg["repetitions"]):
            executer_lot("principal", nom, conf, sel, rep, cfg, simule)


def experience_robustesse(cfg: dict, simule: bool = False, configs: list[str] | None = None) -> None:
    ex = cfg["experiences"]["robustesse"]
    for variante in ex["variantes"]:
        corpus = charger_variante(variante)
        langues = ["fr", "en"] if variante == "anglais" else ["fr"]
        for langue in langues:
            nom_exp = f"robustesse_{variante}" + (f"_modele_{langue}" if variante == "anglais" else "")
            c = _preparer([dict(e) for e in corpus], langue)
            for nom in ex["configurations"]:
                if configs and nom not in configs:
                    continue
                conf = cfg["configurations"][nom]
                if conf["type"] == "agents" and variante == "anglais" and langue == "en":
                    continue  # le système est conçu pour le français : seule la référence teste le modèle anglais
                sel = c if conf["type"] == "baseline" else sous_ensemble(c, ex["par_cellule_agents"],
                                                                          ex.get("longueurs_agents"))
                for rep in range(cfg["repetitions"]):
                    executer_lot(nom_exp, nom, conf, sel, rep, cfg, simule)


def experience_defaillances(cfg: dict, simule: bool = False) -> None:
    ex = cfg["experiences"]["defaillances"]
    conf = cfg["configurations"][ex["configuration"]]
    corpus = sous_ensemble(_preparer(charger_variante("standard")), ex["par_cellule"], ex.get("longueurs"))
    for rep in range(ex["repetitions"]):
        executer_lot("defaillances", ex["configuration"], conf, corpus, rep, cfg, simule,
                     fautes={"llm": ex["taux_fautes_llm"], "outils": ex["taux_fautes_outils"]})


def experience_injection(cfg: dict, simule: bool = False) -> None:
    """M1/M2 : une consigne malveillante est ajoutée à chaque sortie de
    score_quadrigrammes. Mesure : garde-fous déclenchés et taux de succès."""
    ex = cfg["experiences"]["injection"]
    conf = cfg["configurations"][ex["configuration"]]
    corpus = [e for e in sous_ensemble(_preparer(charger_variante("standard")), ex["par_cellule"],
                                       ex.get("longueurs"))
              if e["procede"] in ex["procedes"]]
    for rep in range(cfg["repetitions"]):
        executer_lot("injection", ex["configuration"], conf, corpus, rep, cfg, simule, injection=True)


def experience_explications(cfg: dict, simule: bool = False) -> Path:
    """Pédagogue + Vérificateur sur N chiffrés tirés au hasard ; produit un
    fichier Markdown à noter avec la grille (docs/grille_explications.md)."""
    ex = cfg["experiences"]["explications"]
    nom = ex["configuration"]
    conf = cfg["configurations"][nom]
    corpus = _preparer(charger_variante("standard"))
    rng = random.Random(cfg["graine"])
    tirage = rng.sample(corpus, ex["nombre"])
    textes = textes_test("fr")
    sortie = RESULTS / "raw" / "explications" / f"{nom}.jsonl"
    if (sortie.exists() and (RESULTS / "explications_echantillon.md").exists()
            and len(sortie.read_text(encoding="utf-8").splitlines()) == ex["nombre"]):
        print("  [déjà fait] explications")
        return sortie
    sortie.parent.mkdir(parents=True, exist_ok=True)
    llm = creer_llm(conf, cfg, cfg["graine"], simule)
    orch = creer_orchestrateur(llm, cfg, expliquer=True)
    md = ["# Explications du Pédagogue (échantillon aléatoire, graine fixe)\n",
          "Notation : voir docs/grille_explications.md ; saisir les notes dans results/notes_explications.csv\n"]
    with open(sortie, "w", encoding="utf-8", newline="\n") as f:
        for i, e in enumerate(tirage):
            clair_ex = extrait(rng, textes, max(400, e["longueur"]))
            j = Journal(TRACES / "explications" / nom / f"{e['id']}.jsonl", f"explications/{e['id']}")
            res = orch.casser(e["chiffre"], j, "fr", cfg["graine"], clair_exercice=clair_ex).model_dump()
            ligne = _ligne(e, res, nom, 0, "explications")
            ligne.update(explication=res.get("explication"), exercice=res.get("exercice"))
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            md.append(f"\n## {i + 1}. {e['id']} (procédé réel : {e['procede']}, clé réelle : {e['cle']})\n")
            md.append(f"Résultat : {res.get('procede')} / clé {res.get('cle')} / "
                      f"{'clair exact' if ligne['succes_exact'] else 'clair inexact'}\n")
            md.append((res.get("explication") or "(aucune)") + "\n")
            md.append(f"\nExercice proposé : `{json.dumps(res.get('exercice'), ensure_ascii=False)}` — "
                      f"corrigé vérifié par les outils : {res.get('exercice_valide')}\n")
            print(f"  explications [{i + 1}/{len(tirage)}] {e['id']}")
    (RESULTS / "explications_echantillon.md").write_text("\n".join(md), encoding="utf-8", newline="\n")
    return sortie


def experience_shannon(cfg: dict) -> Path:
    """Longueur minimale de succès (Vigenère) en fonction de la longueur de clé.
    Outils seuls (déterministes) ; tirages à graine fixe."""
    ex = cfg["experiences"]["shannon"]
    sortie = RESULTS / "raw" / "shannon" / "vigenere.jsonl"
    if sortie.exists():
        return sortie
    sortie.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(f"{cfg['graine']}-shannon")
    textes = textes_test("fr")
    partiel = sortie.with_suffix(".partiel")  # renommé seulement une fois complet (reprise sûre)
    with open(partiel, "w", encoding="utf-8", newline="\n") as f:
        for L in ex["longueurs_cle"]:
            for n in ex["longueurs_texte"]:
                if n < 2 * L:
                    continue
                for s in range(ex["echantillons"]):
                    clair = lettres(extrait(rng, textes, n))
                    cle = "".join(rng.choice(ALPHABET) for _ in range(L))
                    ch = chiffres.vigenere_chiffrer(clair, cle)
                    t0 = time.perf_counter()
                    r = attaques.attaque_vigenere(ch, None)
                    r_oracle = attaques.attaque_vigenere(ch, [L])
                    f.write(json.dumps({
                        "longueur_cle": L, "longueur_texte": n, "echantillon": s,
                        "succes": lettres(r["clair"]) == clair,
                        "succes_longueur_connue": lettres(r_oracle["clair"]) == clair,
                        "duree_s": round(time.perf_counter() - t0, 3),
                    }) + "\n")
            print(f"  shannon : clé de longueur {L} terminée")
    partiel.replace(sortie)
    return sortie


def experience_longueur_min(cfg: dict) -> Path:
    """Longueur minimale de succès à 90 %, en lettres, pour chaque procédé :
    (1) attaque adaptée au procédé connu ; (2) référence (a) qui doit aussi
    identifier le procédé. Grille fine de longueurs, tirages à graine fixe."""
    ex = cfg["experiences"]["longueur_min"]
    sortie = RESULTS / "raw" / "longueur_min" / "procedes.jsonl"
    if sortie.exists():
        return sortie
    sortie.parent.mkdir(parents=True, exist_ok=True)
    textes = textes_test("fr")
    partiel = sortie.with_suffix(".partiel")
    with open(partiel, "w", encoding="utf-8", newline="\n") as f:
        for procede in chiffres.PROCEDES:
            rng = random.Random(f"{cfg['graine']}-longueur-min-{procede}")
            for n in ex["longueurs_texte"]:
                for s in range(ex["echantillons"]):
                    from .donnees import cle_aleatoire

                    clair = extrait(rng, textes, n)
                    cle = cle_aleatoire(rng, procede)
                    ch = chiffres.chiffrer(procede, clair, cle)
                    t0 = time.perf_counter()
                    kw = {"graine": s} if procede == "substitution" else {}
                    r = attaques.ATTAQUES[procede](ch, **kw)
                    ligne = {"procede": procede, "longueur_texte": n, "echantillon": s,
                             "succes_procede_connu": lettres(r["clair"]) == lettres(clair),
                             "duree_s": round(time.perf_counter() - t0, 3)}
                    if s < ex["echantillons_reference"]:
                        b = casser_baseline(ch, Journal(None, "lmin"), "fr", s)
                        ligne["succes_reference"] = lettres(b["clair"]) == lettres(clair)
                    f.write(json.dumps(ligne) + "\n")
            print(f"  longueur minimale : {procede} terminé")
    partiel.replace(sortie)
    return sortie


def experience_kasiski_autoclave(cfg: dict) -> Path:
    """Montre pourquoi Kasiski échoue sur l'autoclave : taux de bonne longueur
    en tête des candidates, Vigenère contre autoclave, mêmes textes et clés."""
    ex = cfg["experiences"]["kasiski_autoclave"]
    sortie = RESULTS / "raw" / "kasiski_autoclave" / "comparaison.jsonl"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    corpus = generer_corpus(cfg["graine"], ex["par_cellule"], "standard", LONGUEURS, ("vigenere",))
    with open(sortie, "w", encoding="utf-8", newline="\n") as f:
        for e in corpus:
            L = e["longueur_cle"]
            for procede in ("vigenere", "autoclave"):
                ch = chiffres.chiffrer(procede, e["clair"], e["cle"])
                k = stats.kasiski(ch)
                fr = stats.friedman(ch)
                f.write(json.dumps({
                    "id": e["id"], "procede": procede, "longueur": e["longueur"], "tranche": tranche(e["longueur"]),
                    "longueur_cle": L,
                    "kasiski_tete_correcte": bool(k["longueurs_candidates"]) and k["longueurs_candidates"][0] == L,
                    "kasiski_dans_top3": L in k["longueurs_candidates"][:3],
                    "n_repetitions": k["n_repetitions"],
                    "ic": fr["ic"],
                    "ic_colonnes_vraie_longueur": fr["ic_par_longueur"].get(L),
                }) + "\n")
    return sortie


def memoire_ollama(hote: str) -> dict:
    """Mémoire occupée par les modèles chargés (Ollama /api/ps), en Mo."""
    import urllib.request

    try:
        with urllib.request.urlopen(hote + "/api/ps", timeout=5) as r:  # noqa: S310
            return {m["name"]: round(m.get("size", 0) / 2**20) for m in json.loads(r.read()).get("models", [])}
    except Exception:  # noqa: BLE001
        return {}


def executer_tout(cfg: dict, simule: bool = False, avec_llm: bool = True) -> None:
    t0 = time.time()
    hote = cfg["environnement_execution"]["hote"]
    pics: dict = {}

    def noter():
        for k, v in memoire_ollama(hote).items():
            pics[k] = max(pics.get(k, 0), v)

    from .veille import pas_de_veille

    try:
        with pas_de_veille():
            _executer_tout(cfg, simule, avec_llm, noter)
    finally:
        bilan = {
            "duree_totale_min": round((time.time() - t0) / 60, 1),
            "rss_max_python_mo": rss_python_mo(),
            "memoire_modeles_ollama_mo": pics,
            "mode": "simule" if simule else ("complet" if avec_llm else "sans_llm"),
            "date_fin": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        RESULTS.mkdir(parents=True, exist_ok=True)
        (RESULTS / "EXECUTION.json").write_text(json.dumps(bilan, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
        print(json.dumps(bilan, ensure_ascii=False))


def _executer_tout(cfg: dict, simule: bool, avec_llm: bool, noter) -> None:
    print("== Shannon (outils seuls)")
    experience_shannon(cfg)
    print("== Longueur minimale de succès par procédé (outils seuls)")
    experience_longueur_min(cfg)
    print("== Kasiski / autoclave")
    experience_kasiski_autoclave(cfg)
    print("== Principal (ablation)")
    experience_principale(cfg, None if avec_llm else ["a_baseline"], simule)
    noter()
    print("== Robustesse")
    experience_robustesse(cfg, simule, None if avec_llm else ["a_baseline"])
    noter()
    if avec_llm:
        print("== Défaillances")
        experience_defaillances(cfg, simule)
        noter()
        print("== Injection de consignes")
        experience_injection(cfg, simule)
        noter()
        print("== Explications")
        experience_explications(cfg, simule)
        noter()
