"""Orchestrateur : enchaîne Classifieur -> Cryptanalyste -> Linguiste (boucle de
correction) -> Pédagogue -> Vérificateur, avec réessais, replis déterministes
et arrêt propre. Toutes les étapes sont journalisées (JSONL)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from pydantic import BaseModel

from .agents.base import EchecAgent, ParametresExecution, executer_outil
from .agents.definitions import creer_agents
from .etat import EtatPartage
from .heuristique import classer_par_ic, explication_gabarit, outil_pour
from .outils import stats
from .outils.registre import OUTILS
from .traces import Journal


@dataclass
class ConfigOrchestrateur:
    iterations_max: int = 6          # une itération par procédé au plus
    seuil_garde_fou: float = 0.65   # en dessous, un « plausible » du Linguiste est refusé
    seuil_repli: float = 0.70       # décision déterministe si le Linguiste est indisponible
    expliquer: bool = False
    verifier_exercice: bool = True
    params: ParametresExecution = field(default_factory=ParametresExecution)


class ResultatCassage(BaseModel):
    mode: str
    procede: str | None
    cle: str | None
    clair: str | None
    score_normalise: float | None
    statut: str                     # accepte | meilleur_effort | echec
    iterations: int
    hypotheses: list[str]
    rejetes: list[str]
    replis: list[str]
    compteurs: dict
    duree_s: float
    explication: str | None = None
    exercice: dict | None = None
    exercice_valide: bool | None = None


class Orchestrateur:
    def __init__(self, llm, config: ConfigOrchestrateur | None = None):
        self.llm = llm
        self.cfg = config or ConfigOrchestrateur()
        self.agents = creer_agents()

    # --- étapes ------------------------------------------------------------------------
    def _classifier(self, etat: EtatPartage, j: Journal) -> None:
        texte = (f"Chiffré à analyser ({len(stats.lettres(etat.chiffre))} lettres). "
                 f"Début : «{etat.chiffre[:200]}»")
        try:
            s = self.agents["classifieur"].executer(self.llm, texte, etat, j, self.cfg.params)
            etat.famille, etat.hypotheses = s.famille, list(dict.fromkeys(s.procedes_probables))
        except EchecAgent as e:
            etat.replis.append("classifieur")
            j.ecrire("repli", "classifieur", motif=str(e))
            etat.famille, etat.hypotheses = classer_par_ic(etat.chiffre)
        # Complète l'ordre avec les procédés non cités (aucune hypothèse n'est exclue d'office)
        for p in classer_par_ic(etat.chiffre)[1]:
            if p not in etat.hypotheses:
                etat.hypotheses.append(p)

    def _cryptanalyser(self, etat: EtatPartage, j: Journal) -> str | None:
        restants = [p for p in etat.hypotheses if p not in etat.rejetes]
        dispo = {rid: f"{r['procede']} clé={r['cle'][:26]} score={r['score_normalise']}"
                 for rid, r in etat.resultats.items() if rid not in etat.ids_rejetes}
        texte = json.dumps({
            "famille_classifieur": etat.famille,
            "hypotheses_restantes": restants,
            "procedes_rejetes": etat.rejetes,
            "avis_linguiste": etat.avis_linguiste,
            "procede_suggere": etat.procede_suggere,
            "resultats_disponibles": dispo,
            "longueur_lettres": len(stats.lettres(etat.chiffre)),
        }, ensure_ascii=False)
        try:
            s = self.agents["cryptanalyste"].executer(self.llm, texte, etat, j, self.cfg.params)
            if s.id_resultat not in etat.resultats or s.id_resultat in etat.ids_rejetes:
                raise EchecAgent(f"identifiant de résultat invalide ou déjà rejeté : {s.id_resultat}")
            p = etat.resultats[s.id_resultat]["procede"]
            if p in etat.rejetes:  # garde-fou : une hypothèse rejetée ne peut pas être reproposée
                etat.compteurs["hypothese_repetee"] = etat.compteurs.get("hypothese_repetee", 0) + 1
                raise EchecAgent(f"procédé déjà rejeté reproposé : {p}")
            return s.id_resultat
        except EchecAgent as e:
            etat.replis.append("cryptanalyste")
            j.ecrire("repli", "cryptanalyste", motif=str(e))
            return self._attaque_deterministe(etat, j, restants)

    def _attaque_deterministe(self, etat: EtatPartage, j: Journal, restants: list[str]) -> str | None:
        """Repli : lance directement l'attaque du prochain procédé non essayé."""
        essayes = {r["procede"] for r in etat.resultats.values()}
        for p in restants:
            if p in essayes and p not in etat.rejetes:
                for rid, r in etat.resultats.items():
                    if r["procede"] == p and rid not in etat.ids_rejetes:
                        return rid
            if p not in essayes:
                outil = OUTILS[outil_pour(p)]
                try:
                    res = executer_outil(outil, etat, outil.arguments(), self.cfg.params.delai_outil_s)
                except Exception as e:  # noqa: BLE001
                    j.ecrire("erreur_outil", "orchestrateur", outil=outil.nom, erreur=str(e))
                    etat.rejetes.append(p)
                    continue
                rid = f"R{len(etat.resultats) + 1}"
                etat.resultats[rid] = res
                j.ecrire("resultat_outil", "orchestrateur", outil=outil.nom, id_resultat=rid, resultat=res)
                return rid
        return None

    def _juger(self, etat: EtatPartage, rid: str, j: Journal) -> bool:
        etat.candidat = rid
        r = etat.resultats[rid]
        texte = json.dumps({"candidat": rid, "procede": r["procede"], "cle": r["cle"][:26],
                            "procedes_rejetes": etat.rejetes}, ensure_ascii=False)
        try:
            s = self.agents["linguiste"].executer(self.llm, texte, etat, j, self.cfg.params)
            plausible, etat.avis_linguiste, etat.procede_suggere = s.plausible, s.justification, s.procede_suivant
        except EchecAgent as e:
            etat.replis.append("linguiste")
            j.ecrire("repli", "linguiste", motif=str(e))
            plausible = r["score_normalise"] >= self.cfg.seuil_repli
            etat.avis_linguiste = "décision de repli sur seuil"
        if plausible and r["score_normalise"] < self.cfg.seuil_garde_fou:
            etat.compteurs["garde_fou_declenche"] = etat.compteurs.get("garde_fou_declenche", 0) + 1
            j.ecrire("garde_fou", "orchestrateur", id_resultat=rid, score_normalise=r["score_normalise"],
                     motif="« plausible » refusé : score trop bas")
            plausible = False
        j.ecrire("decision", "orchestrateur", id_resultat=rid, plausible=plausible)
        return plausible

    def _expliquer(self, etat: EtatPartage, rid: str, j: Journal, res: dict) -> None:
        resume = resume_traces(j, etat, rid)
        try:
            s = self.agents["pedagogue"].executer(self.llm, json.dumps(resume, ensure_ascii=False), etat, j,
                                                  self.cfg.params)
            res["explication"], ex = s.explication, s.exercice.model_dump()
        except EchecAgent as e:
            etat.replis.append("pedagogue")
            j.ecrire("repli", "pedagogue", motif=str(e))
            res["explication"], ex = explication_gabarit(resume), None
        res["exercice"] = ex
        if ex and self.cfg.verifier_exercice and not etat.exercice_clair:
            etat.exercice_clair = etat.resultats[rid]["clair"]  # exercice bâti sur le clair retrouvé
        if ex and self.cfg.verifier_exercice and etat.exercice_clair:
            etat.exercice_procede = etat.resultats[rid]["procede"]  # même procédé imposé
            texte = json.dumps({"procede": etat.exercice_procede, "cle": ex["cle"],
                                "cle_du_chiffre_casse": etat.resultats[rid]["cle"][:26]}, ensure_ascii=False)
            try:
                v = self.agents["verificateur"].executer(self.llm, texte, etat, j, self.cfg.params)
                valide = v.valide
            except EchecAgent as e:
                etat.replis.append("verificateur")
                j.ecrire("repli", "verificateur", motif=str(e))
                valide = False
            # Contre-vérification par le code : le verdict doit refléter l'outil
            verdicts = [ev for ev in j.evenements if ev["type"] == "resultat_outil"
                        and ev.get("outil") == "casser_exercice"]
            verifie = bool(verdicts and verdicts[-1]["resultat"].get("corrige_verifie"))
            nouvelle_cle = ex["cle"].upper() != etat.resultats[rid]["cle"].upper()
            if valide != (verifie and nouvelle_cle):
                j.ecrire("garde_fou", "orchestrateur", motif="verdict du vérificateur corrigé par l'outil")
            res["exercice_valide"] = verifie and nouvelle_cle

    # --- boucle principale --------------------------------------------------------------
    def casser(self, chiffre: str, journal: Journal, langue: str = "fr", graine: int = 0,
               clair_exercice: str | None = None, expliquer: bool | None = None,
               injecteur_fautes=None, injection_consignes: bool = False) -> ResultatCassage:
        t0 = time.perf_counter()
        etat = EtatPartage(chiffre=chiffre, langue=langue, graine=graine, exercice_clair=clair_exercice,
                           injecteur_fautes_outils=injecteur_fautes, injection_consignes=injection_consignes)
        journal.ecrire("debut", "orchestrateur", mode="agents", llm=self.llm.nom, langue=langue)
        self._classifier(etat, journal)
        statut, retenu, iterations = "echec", None, 0
        while iterations < self.cfg.iterations_max:
            rid = self._cryptanalyser(etat, journal)
            if rid is None:
                break
            iterations += 1
            if self._juger(etat, rid, journal):
                statut, retenu = "accepte", rid
                break
            etat.ids_rejetes.append(rid)
            p = etat.resultats[rid]["procede"]
            if p not in etat.rejetes:
                etat.rejetes.append(p)
            journal.ecrire("nouvelle_hypothese", "orchestrateur", rejete=p, iteration=iterations)
        if retenu is None and etat.resultats:
            retenu = max(etat.resultats, key=lambda k: etat.resultats[k]["score_normalise"])
            statut = "meilleur_effort"
        r = etat.resultats.get(retenu) if retenu else None
        res = {
            "mode": "agents", "procede": r and r["procede"], "cle": r and r["cle"], "clair": r and r["clair"],
            "score_normalise": r and r["score_normalise"], "statut": statut, "iterations": iterations,
            "hypotheses": etat.hypotheses, "rejetes": etat.rejetes, "replis": etat.replis,
        }
        if r and (self.cfg.expliquer if expliquer is None else expliquer):
            self._expliquer(etat, retenu, journal, res)
        res["compteurs"] = dict(etat.compteurs)
        res["duree_s"] = round(time.perf_counter() - t0, 3)
        journal.ecrire("fin", "orchestrateur", statut=statut, procede=res["procede"], cle=res["cle"],
                       iterations=iterations, duree_s=res["duree_s"])
        return ResultatCassage(**res)


def resume_traces(j: Journal, etat: EtatPartage, rid: str) -> dict:
    """Résumé factuel des traces (valeurs issues des outils) pour le Pédagogue."""
    mesures = {}
    for ev in j.evenements:
        if ev["type"] == "resultat_outil" and ev.get("outil") in ("indice_coincidence", "frequences", "kasiski",
                                                                     "friedman"):
            r = ev["resultat"]
            if ev["outil"] == "indice_coincidence":
                mesures["ic"] = r["ic"]
            elif ev["outil"] == "frequences":
                mesures["ordre_frequences"] = r["ordre"]
            elif ev["outil"] == "kasiski":
                mesures["kasiski_longueurs"] = r["longueurs_candidates"]
            else:
                mesures["friedman_estimation"] = r["estimation_longueur"]
                mesures["friedman_longueurs"] = r["longueurs_candidates"]
    mesures.setdefault("ic", round(stats.indice_coincidence(etat.chiffre), 5))
    r = etat.resultats[rid]
    p = r["procede"]
    longueur_cle = len(r["cle"]) if p in ("vigenere", "beaufort", "autoclave") else None
    return {
        "mesures": mesures,
        "lecture_des_mesures": {
            "ic": "IC proche de 0,078 = monoalphabétique ; IC nettement plus bas = polyalphabétique "
                  "(l'IC ne donne PAS la longueur de la clé)",
            "friedman_estimation": "estimation grossière ; la longueur réelle est celle de la clé trouvée",
        },
        "longueur_cle_trouvee": longueur_cle,
        "hypotheses_essayees": [etat.resultats[k]["procede"] for k in etat.resultats],
        "procedes_rejetes": etat.rejetes,
        "procede_retenu": r["procede"],
        "cle": r["cle"],
        "score_normalise": r["score_normalise"],
        "longueur_lettres": len(stats.lettres(etat.chiffre)),
        "debut_clair": r["clair"][:120],
    }
