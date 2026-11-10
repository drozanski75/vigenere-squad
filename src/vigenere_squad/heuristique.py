"""Heuristique codée en dur (configuration d'ablation (a), sans modèle de
langage), replis déterministes de l'orchestrateur et politique du modèle
simulé utilisée par les tests."""

from __future__ import annotations

import json
import time

from .outils import stats
from .outils.attaques import ATTAQUES
from .outils.chiffres import MONO, POLY
from .traces import Journal

SEUIL_IC_MONO = 0.060
SEUIL_ACCEPTATION = 0.70

OUTIL_PAR_PROCEDE = {
    "cesar": "chi2_cesar",
    "affine": "force_brute_affine",
    "substitution": "recuit_substitution",
    "vigenere": "attaque_vigenere",
    "beaufort": "attaque_beaufort",
    "autoclave": "attaque_autoclave",
}


def outil_pour(procede: str) -> str:
    return OUTIL_PAR_PROCEDE[procede]


def classer_par_ic(chiffre: str) -> tuple[str, list[str]]:
    ic = stats.indice_coincidence(chiffre)
    if ic >= SEUIL_IC_MONO:
        return "mono", list(MONO) + list(POLY)
    return "poly", list(POLY) + list(MONO)


def casser_baseline(chiffre: str, journal: Journal, langue: str = "fr", graine: int = 0) -> dict:
    """Référence (a) : ordre fixe des attaques selon l'IC, arrêt au premier
    clair dont le score normalisé dépasse le seuil, sinon meilleur score."""
    t0 = time.perf_counter()
    journal.ecrire("debut", "baseline", mode="baseline", langue=langue)
    famille, ordre = classer_par_ic(chiffre)
    journal.ecrire("decision", "baseline", famille=famille, ordre=ordre,
                   ic=round(stats.indice_coincidence(chiffre), 5))
    essais = []
    statut = "meilleur_effort"
    for p in ordre:
        if p == "substitution":
            r = ATTAQUES[p](chiffre, langue=langue, graine=graine)
        else:
            r = ATTAQUES[p](chiffre, langue=langue)
        essais.append(r)
        journal.ecrire("resultat_outil", "baseline", outil=OUTIL_PAR_PROCEDE[p], resultat=r)
        if r["score_normalise"] >= SEUIL_ACCEPTATION:
            statut = "accepte"
            break
    meilleur = essais[-1] if statut == "accepte" else max(essais, key=lambda r: r["score_normalise"])
    res = {
        "mode": "baseline", "procede": meilleur["procede"], "cle": meilleur["cle"], "clair": meilleur["clair"],
        "score_normalise": meilleur["score_normalise"], "statut": statut, "iterations": len(essais),
        "hypotheses": ordre, "rejetes": [e["procede"] for e in essais if e is not meilleur], "replis": [],
        "compteurs": {"appels_outils": len(essais)}, "duree_s": round(time.perf_counter() - t0, 3),
    }
    journal.ecrire("fin", "baseline", statut=statut, procede=res["procede"], cle=res["cle"],
                   iterations=res["iterations"], duree_s=res["duree_s"])
    return res


def explication_gabarit(resume: dict) -> str:
    m = resume.get("mesures", {})
    return (
        f"### Démarche (explication automatique de repli)\n"
        f"1. L'indice de coïncidence vaut {m.get('ic')} (français ≈ 0,078, aléatoire ≈ 0,038).\n"
        f"2. Hypothèses essayées : {', '.join(resume.get('hypotheses_essayees', []))}.\n"
        f"3. Procédé retenu : {resume.get('procede_retenu')}, clé {resume.get('cle')}, "
        f"score de plausibilité {resume.get('score_normalise')}.\n"
        f"4. Texte de {resume.get('longueur_lettres')} lettres."
    )


# --- Politique du modèle simulé (tests et démonstration hors ligne) ---------------------------
def _nb_resultats(messages: list[dict]) -> int:
    return sum(1 for m in messages if m["role"] == "user" and m["content"].startswith("RÉSULTATS DES OUTILS"))


def _derniers_resultats(messages: list[dict]) -> list[dict]:
    for m in reversed(messages):
        if m["role"] == "user" and m["content"].startswith("RÉSULTATS DES OUTILS"):
            return json.loads(m["content"].split("\n", 1)[1].split("\nConclus")[0])
    return []


def politique_heuristique(agent: str, messages: list[dict], schema: dict, ctx) -> dict:
    """Reproduit la démarche attendue d'un agent, en JSON conforme au protocole."""
    n = _nb_resultats(messages)
    vide = {"pensee": "", "appels": [], "conclusion": {}}
    if agent == "classifieur":
        if n == 0:
            return {**vide, "appels": [{"outil": "indice_coincidence", "arguments": {}},
                                        {"outil": "frequences", "arguments": {}}]}
        famille, ordre = classer_par_ic(ctx["chiffre"])
        return {**vide, "conclusion": {"famille": famille, "procedes_probables": ordre,
                                       "justification": "Décision fondée sur l'IC mesuré."}}
    if agent == "cryptanalyste":
        restants = [p for p in ctx["hypotheses"] if p not in ctx["rejetes"]]
        if ctx.get("procede_suggere") in restants:
            restants.remove(ctx["procede_suggere"])
            restants.insert(0, ctx["procede_suggere"])
        if not restants:
            return {**vide, "conclusion": {"id_resultat": "R0", "procede": "cesar", "justification": "rien"}}
        p = restants[0]
        for rid, r in ctx["resultats"].items():
            if r["procede"] == p and rid not in ctx["ids_rejetes"]:
                return {**vide, "conclusion": {"id_resultat": rid, "procede": p,
                                               "justification": "Résultat de l'attaque adaptée."}}
        return {**vide, "appels": [{"outil": OUTIL_PAR_PROCEDE[p], "arguments": {}}]}
    if agent == "linguiste":
        if n == 0:
            return {**vide, "appels": [{"outil": "score_quadrigrammes",
                                        "arguments": {"id_resultat": ctx["candidat"]}}]}
        dernier = _derniers_resultats(messages)
        s = dernier[0].get("resultat", {}).get("score_normalise", 0) if dernier else 0
        return {**vide, "conclusion": {"plausible": s >= SEUIL_ACCEPTATION,
                                       "justification": f"score normalisé {s}", "procede_suivant": None}}
    if agent == "pedagogue":
        resume = json.loads(messages[1]["content"])
        p = resume["procede_retenu"]
        cles = {"cesar": "7", "affine": "5,8", "substitution": "QWERTYUIOPASDFGHJKLZXCVBNM"}
        return {**vide, "conclusion": {"explication": explication_gabarit(resume),
                                       "exercice": {"procede": p, "cle": cles.get(p, "EXERCICE"),
                                                    "enonce": "Déchiffrer ce texte."}}}
    if agent == "verificateur":
        entree = json.loads(messages[1]["content"])
        if n == 0:
            return {**vide, "appels": [{"outil": "chiffrer_exercice",
                                        "arguments": {"procede": entree["procede"], "cle": entree["cle"]}},
                                       {"outil": "casser_exercice", "arguments": {}}]}
        res = _derniers_resultats(messages)
        ok = bool(res and res[-1].get("resultat", {}).get("corrige_verifie"))
        return {**vide, "conclusion": {"valide": ok, "commentaire": "vérifié par casser_exercice"}}
    raise ValueError(agent)
