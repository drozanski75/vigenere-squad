"""Interface en ligne de commande ``vsquad``.

Exemples :
  vsquad casser --texte "WKH TXLFN EURZQ IRA" --llm simule --expliquer
  vsquad casser --fichier chiffre.txt --modele qwen3:4b --trace traces/demo.jsonl
  vsquad rejouer --id standard-vigenere-0300-0 --config b_qwen3_4b
  vsquad traces traces/principal/b_qwen3_4b/rep0/standard-vigenere-0300-0.jsonl
  vsquad evaluer [--sans-llm] [--simule]
  vsquad metriques | vsquad site | vsquad environnement
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _ligne_trace(ev: dict) -> str | None:
    t, agent = ev["type"], ev.get("agent") or ""
    pre = f"[{ev['t_rel_s']:>7}s] {agent:<14}"
    if t == "appel_outil":
        return f"{pre} -> {ev['outil']}({json.dumps(ev['arguments'], ensure_ascii=False)})"
    if t == "resultat_outil":
        r = ev.get("resultat", {})
        court = {k: r[k] for k in ("procede", "cle", "score_normalise", "ic", "ordre", "longueurs_candidates",
                                   "estimation_longueur", "corrige_verifie") if k in r}
        return f"{pre} <- {ev['outil']} {ev.get('id_resultat', '')} {json.dumps(court, ensure_ascii=False)}"
    if t == "conclusion":
        return f"{pre} == {json.dumps(ev['conclusion'], ensure_ascii=False)[:300]}"
    if t in ("repli", "appel_refuse", "erreur_llm", "erreur_outil", "garde_fou", "arguments_invalides"):
        return f"{pre} !! {t} {ev.get('motif') or ev.get('erreur') or ''}"
    if t in ("debut", "fin", "decision", "nouvelle_hypothese"):
        reste = {k: v for k, v in ev.items() if k not in ("ts", "t_rel_s", "run_id", "type", "agent")}
        return f"{pre} ** {t} {json.dumps(reste, ensure_ascii=False)[:300]}"
    if t == "debut_agent":
        return f"{pre} .. réfléchit (prompt v{ev.get('prompt_version')})"
    return None


def _afficher_en_direct(ev: dict) -> None:
    l = _ligne_trace(ev)
    if l:
        print(l, flush=True)


def _afficher_traces(chemin: Path) -> None:
    from .traces import lire

    for ev in lire(chemin):
        l = _ligne_trace(ev)
        if l:
            print(l)


RACINE_PROJET = Path(__file__).resolve().parents[2]


def _script(nom: str, *args: str) -> int:
    """Exécute un script du dossier scripts/ ou data/ dans le même interpréteur."""
    import runpy

    chemin = RACINE_PROJET / nom
    ancien = sys.argv
    sys.argv = [str(chemin), *args]
    try:
        runpy.run_path(str(chemin), run_name="__main__")
    except SystemExit as e:
        return int(e.code or 0) if not isinstance(e.code, str) else 1
    finally:
        sys.argv = ancien
    return 0


def _ollama_pret(hote: str) -> bool:
    import urllib.request

    try:
        with urllib.request.urlopen(hote + "/api/version", timeout=5):  # noqa: S310
            return True
    except Exception:  # noqa: BLE001
        print(f"Ollama ne répond pas sur {hote}. Démarrez l'application Ollama (ou `ollama serve`).",
              file=sys.stderr)
        return False


def _commande_projet(a) -> int:
    import os
    import shutil
    import subprocess

    from .evaluation.executer import charger_config

    cfg = charger_config()
    hote = cfg["environnement_execution"]["hote"]
    if a.commande == "donnees":
        return _script("data/preparer_donnees.py") or _script("data/generer_corpus.py", "--seed", str(cfg["graine"]))
    if a.commande == "comparer":
        return _script("scripts/comparer.py")
    if a.commande == "verifier":
        return _script("scripts/signature.py", "verifier")
    if a.commande == "signer":
        return _script("scripts/signature.py", "empreintes") or _script("scripts/signature.py", "signer")
    if not _ollama_pret(hote):
        return 1
    if a.commande == "modeles":
        return _script("scripts/epingler_modeles.py")
    # reproduire
    if a.petit:
        os.environ["VSQUAD_SORTIE"] = "build/small"
        shutil.rmtree(RACINE_PROJET / "build" / "small", ignore_errors=True)
        modeles = [cfg["ci"]["modele"]]
    else:
        publie = RACINE_PROJET / "results" / "metrics.json"
        if publie.exists():
            (RACINE_PROJET / "results" / "publie").mkdir(parents=True, exist_ok=True)
            shutil.copy(publie, RACINE_PROJET / "results" / "publie" / "metrics.json")
        for sous in ("results/raw", "results/figures", "traces"):
            shutil.rmtree(RACINE_PROJET / sous, ignore_errors=True)
        modeles = [c["modele"] for c in cfg["configurations"].values() if c["type"] == "agents"]
    from .llm import OllamaLLM

    for m in modeles:
        OllamaLLM(m, hote=hote).telecharger()
    if _script("data/preparer_donnees.py") or _script("data/generer_corpus.py", "--seed", str(cfg["graine"])):
        return 1
    # Ré-importe les chemins de sortie (VSQUAD_SORTIE) dans un nouveau processus
    etapes = [["environnement"], ["evaluer"] + (["--petit"] if a.petit else []), ["metriques"], ["site"]]
    for e in etapes:
        r = subprocess.run([sys.executable, "-m", "vigenere_squad.cli", *e], check=False)
        if r.returncode:
            return r.returncode
    print("Terminé." + ("" if a.petit else " Comparer aux résultats publiés : vsquad comparer"))
    return 0


def _llm(args, cfg):
    from .evaluation.executer import creer_llm

    if args.llm == "simule":
        return creer_llm({}, cfg, 0, simule=True)
    conf = {"modele": args.modele, "temperature": 0.3, "contexte": 2048, "jetons_max": 256}
    return creer_llm(conf, cfg, args.graine)


def main(argv=None) -> int:
    for flux in (sys.stdout, sys.stderr):  # consoles Windows : éviter les erreurs d'encodage
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(prog="vsquad", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="commande", required=True)

    c = sp.add_parser("casser", help="casser un chiffré unique")
    c.add_argument("--texte")
    c.add_argument("--fichier", type=Path)
    c.add_argument("--llm", choices=["ollama", "simule", "aucun"], default="ollama")
    c.add_argument("--modele", default="qwen3:4b")
    c.add_argument("--graine", type=int, default=0)
    c.add_argument("--expliquer", action="store_true")
    c.add_argument("--trace", type=Path, default=None, help="journal JSONL (défaut : traces/cli/derniere.jsonl du projet)")

    r = sp.add_parser("rejouer", help="rejouer un chiffré du corpus et afficher ses traces")
    r.add_argument("--id", required=True)
    r.add_argument("--config", default="b_qwen3_4b")
    r.add_argument("--simule", action="store_true")
    r.add_argument("--expliquer", action="store_true")

    t = sp.add_parser("traces", help="afficher un journal JSONL lisiblement")
    t.add_argument("chemin", type=Path)

    e = sp.add_parser("evaluer", help="lancer toutes les expériences")
    e.add_argument("--sans-llm", action="store_true", help="seulement la référence (a) et les expériences déterministes")
    e.add_argument("--simule", action="store_true", help="modèle simulé (tests, sans Ollama)")
    e.add_argument("--config-fichier", type=Path)
    e.add_argument("--petit", action="store_true", help="évaluation réduite (CI, modèle de très petite taille)")
    e.add_argument("--experience", help="n'exécuter qu'une partie : deterministes, principal, robustesse, "
                                         "defaillances, injection, explications (calcul parallèle)")
    e.add_argument("--config", help="configuration (avec --experience)")
    e.add_argument("--rep", type=int, help="répétition (avec --experience)")

    dg = sp.add_parser("diagnostic", help="vérifier l'installation (Ollama, modèle, données, vitesse) et conseiller")
    dg.add_argument("--reparer", action="store_true", help="construire les données et télécharger le modèle si absents")
    dg.add_argument("--rapide", action="store_true", help="sans mesurer la vitesse du modèle")
    dg.add_argument("--modele", help="modèle à vérifier (défaut : celui de la configuration b)")
    sp.add_parser("donnees", help="vérifier les textes sources, construire les modèles de langue et le corpus (graine 42)")
    sp.add_parser("modeles", help="ollama pull des modèles déclarés + épinglage des digests")
    rp = sp.add_parser("reproduire", help="reproduction complète (équivalent de make reproduce), tous systèmes")
    rp.add_argument("--petit", action="store_true", help="évaluation réduite (CI), écrite dans build/small/")
    sp.add_parser("comparer", help="comparer results/metrics.json aux métriques publiées")
    sp.add_parser("verifier", help="vérifier la signature de SHA256SUMS et les empreintes")
    sp.add_parser("signer", help="écrire SHA256SUMS et le signer (clé minisign de l'auteur)")
    sp.add_parser("metriques", help="agréger results/raw -> results/metrics.json et figures")
    sp.add_parser("site", help="générer site/index.html")
    sp.add_parser("environnement", help="écrire results/ENVIRONMENT.json")
    a = p.parse_args(argv)

    from .evaluation.executer import charger_config

    if a.commande == "diagnostic":
        from .diagnostic import diagnostiquer

        return diagnostiquer(a.reparer, a.modele, a.rapide)
    if a.commande in ("donnees", "modeles", "reproduire", "comparer", "verifier", "signer"):
        return _commande_projet(a)
    if a.commande == "traces":
        _afficher_traces(a.chemin)
        return 0
    if a.commande == "metriques":
        from .evaluation.figures import generer_figures
        from .evaluation.metriques import agreger_tout

        m = agreger_tout()
        print(json.dumps(m["resume"], indent=2, ensure_ascii=False))
        print("figures :", generer_figures())
        return 0
    if a.commande == "site":
        from .evaluation.site import generer_site

        print(generer_site())
        return 0
    if a.commande == "environnement":
        from .evaluation.environnement import capturer

        print(json.dumps(capturer(), indent=2, ensure_ascii=False))
        return 0
    if a.commande == "evaluer":
        from .evaluation.executer import executer_tout

        cfg = charger_config(a.config_fichier)
        if a.petit:
            from .evaluation.executer import config_petite

            cfg = config_petite(cfg)
        if a.simule:
            from .evaluation.executer import marquer_simule

            cfg = marquer_simule(cfg)
        if not a.sans_llm and not a.simule and a.experience != "deterministes":
            from .evaluation.environnement import verifier_digests

            cfg_verif = cfg
            if a.experience:  # calcul parallèle : seul le modèle utilisé par ce morceau doit être présent
                import copy

                cible = a.config or cfg["experiences"].get(a.experience, {}).get("configuration")
                cfg_verif = copy.deepcopy(cfg)
                cfg_verif["configurations"] = {k: v for k, v in cfg["configurations"].items() if k == cible}
            for alerte in verifier_digests(cfg_verif, strict=True):
                print("ALERTE", alerte)
        if a.experience:
            from .evaluation.executer import executer_morceau

            executer_morceau(cfg, a.experience, a.config, a.rep, a.simule)
            return 0
        executer_tout(cfg, simule=a.simule, avec_llm=not a.sans_llm)
        return 0

    cfg = charger_config()
    from .heuristique import casser_baseline
    from .traces import Journal

    if a.commande == "rejouer":
        from .evaluation.executer import charger_variante, creer_llm, creer_orchestrateur

        variante = a.id.split("-")[0]
        e = next((x for x in charger_variante(variante) if x["id"] == a.id), None)
        if e is None:
            print(f"identifiant inconnu : {a.id}", file=sys.stderr)
            return 2
        conf = cfg["configurations"][a.config]
        chemin = RACINE_PROJET / "traces" / "rejeu" / a.config / f"{a.id}.jsonl"
        j = Journal(chemin, f"rejeu/{a.id}", ecouteur=_afficher_en_direct)
        if conf["type"] == "baseline":
            res = casser_baseline(e["chiffre"], j, e["langue"])
        else:
            orch = creer_orchestrateur(creer_llm(conf, cfg, cfg["graine"], a.simule), cfg, expliquer=a.expliquer)
            res = orch.casser(e["chiffre"], j, e["langue"], cfg["graine"], clair_exercice=e["clair"]).model_dump()
        from .outils.texte import lettres

        print(f"\nclair exact : {lettres(res['clair'] or '') == lettres(e['clair'])} | procédé réel {e['procede']} "
              f"clé réelle {e['cle']} | trouvé {res['procede']} {res['cle']}")
        print(f"traces : {chemin}")
        return 0

    texte = a.texte if a.texte else (a.fichier.read_text(encoding="utf-8") if a.fichier else sys.stdin.read())
    from .outils.texte import normaliser

    texte = normaliser(texte)
    a.trace = a.trace or RACINE_PROJET / "traces" / "cli" / "derniere.jsonl"
    j = Journal(a.trace, "cli", ecouteur=_afficher_en_direct)
    if a.llm == "aucun":
        res = casser_baseline(texte, j)
    else:
        from .evaluation.executer import creer_orchestrateur

        res = creer_orchestrateur(_llm(a, cfg), cfg, expliquer=a.expliquer).casser(
            texte, j, "fr", a.graine).model_dump()
    print("\n" + json.dumps({k: res[k] for k in ("procede", "cle", "statut", "iterations", "score_normalise")},
                            ensure_ascii=False))
    print("\nCLAIR :\n" + (res["clair"] or ""))
    if res.get("explication"):
        print("\nEXPLICATION :\n" + res["explication"])
    print(f"\ntraces : {a.trace}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
