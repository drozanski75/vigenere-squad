import re
import json

import pytest

from vigenere_squad.agents.base import Agent, EchecAgent, ParametresExecution, charger_prompt
from vigenere_squad.agents.definitions import OUTILS_PAR_AGENT, SortieClassifieur, creer_agents
from vigenere_squad.etat import EtatPartage
from vigenere_squad.heuristique import casser_baseline, politique_heuristique
from vigenere_squad.llm import ErreurLLM, LLMDefaillant, LLMSimule, OllamaLLM
from vigenere_squad.orchestrateur import ConfigOrchestrateur, Orchestrateur
from vigenere_squad.outils import chiffres
from vigenere_squad.outils.texte import lettres
from vigenere_squad.traces import Journal, lire


class Script:
    """Modèle scripté : renvoie successivement les réponses fournies."""

    def __init__(self, reponses):
        self.reponses = list(reponses)
        self.nom = "script"

    def repondre(self, agent, messages, schema, ctx):
        r = self.reponses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r if isinstance(r, str) else json.dumps(r)


P = ParametresExecution(reessais=2, tours_max=2, delai_outil_s=30)


def _classifieur():
    return Agent("classifieur", OUTILS_PAR_AGENT["classifieur"], SortieClassifieur)


def test_prompts_versionnes():
    for nom in OUTILS_PAR_AGENT:
        p = charger_prompt(nom)
        assert re.fullmatch(r"\d+\.\d+\.\d+", p.version) and len(p.sha256) == 16
    assert set(creer_agents()) == set(OUTILS_PAR_AGENT)


def test_schema_impose_liste_fermee():
    s = _classifieur().schema_reponse(P)
    assert s["properties"]["appels"]["items"]["properties"]["outil"]["enum"] == ["indice_coincidence", "frequences"]
    assert "appels" not in creer_agents()["pedagogue"].schema_reponse(P)["properties"]
    # Premier tour d'un agent outillé : appels seuls ; ensuite conclusion obligatoire
    assert "conclusion" not in _classifieur().schema_reponse(P, "outils")["properties"]
    assert "conclusion" in _classifieur().schema_reponse(P, "conclusion")["required"]


def test_schema_compatible_ollama():
    """Aucune référence $ref / $defs (Ollama répond HTTP 400), pas de très longue borne."""
    import json

    for agent in creer_agents().values():
        for phase in ("outils", "conclusion"):
            texte = json.dumps(agent.schema_reponse(P, phase))
            assert "$ref" not in texte and "$defs" not in texte and '"maxLength": 2500' not in texte


def test_appel_repete_non_recalcule():
    etat = EtatPartage(chiffre="WKH TXLFN EURZQ IRA")
    j = Journal(None, "t")
    ag = creer_agents()["cryptanalyste"]
    appel = {"pensee": "", "appels": [{"outil": "kasiski", "arguments": {}}]}
    llm = Script([appel, appel, {"pensee": "", "appels": [{"outil": "chi2_cesar", "arguments": {}}],
                                 "conclusion": {}},
                  {"pensee": "", "appels": [], "conclusion": {"id_resultat": "R1", "procede": "cesar",
                                                               "justification": "ok"}}])
    out = ag.executer(llm, "x", etat, j, ParametresExecution(tours_max=3))
    assert out.id_resultat == "R1" and etat.compteurs["appels_repetes"] == 1
    assert j.compter("appel_outil") == 2
    assert "OUTILS AUTORISÉS" in _classifieur().message_systeme()


def test_appel_hallucine_refuse_puis_conclusion():
    etat = EtatPartage(chiffre="WKH TXLFN EURZQ IRA")
    j = Journal(None, "t")
    llm = Script([
        {"pensee": "", "appels": [{"outil": "dechiffrer_tout", "arguments": {}},
                                  {"outil": "kasiski", "arguments": {}},
                                  {"outil": "indice_coincidence", "arguments": {"x": 1}}], "conclusion": {}},
        {"pensee": "", "appels": [], "conclusion": {"famille": "mono", "procedes_probables": ["cesar"],
                                                     "justification": "ok"}},
    ])
    out = _classifieur().executer(llm, "x", etat, j, P)
    assert out.famille == "mono"
    assert etat.compteurs["appels_refuses"] == 2  # outil inventé + outil d'un autre agent
    assert etat.compteurs["arguments_invalides"] == 1
    assert j.compter("appel_refuse") == 2


@pytest.mark.parametrize("faute", ["", "{pas du json", "[1, 2]", ErreurLLM("délai")])
def test_reessai_apres_faute(faute):
    etat = EtatPartage(chiffre="ABC")
    ok = {"pensee": "", "appels": [], "conclusion": {"famille": "poly", "procedes_probables": ["vigenere"],
                                                      "justification": "ok"}}
    out = _classifieur().executer(Script([faute, ok]), "x", etat, Journal(None, "t"), P)
    assert out.famille == "poly" and etat.compteurs["erreurs_llm"] == 1


def test_echec_apres_reessais_et_conclusion_invalide():
    etat = EtatPartage(chiffre="ABC")
    with pytest.raises(EchecAgent):
        _classifieur().executer(Script(["", "", ""]), "x", etat, Journal(None, "t"), P)
    mauvaise = {"pensee": "", "appels": [], "conclusion": {"famille": "tri"}}
    with pytest.raises(EchecAgent):
        _classifieur().executer(Script([mauvaise] * 3), "x", etat, Journal(None, "t"), P)


def test_erreur_et_delai_outil():
    etat = EtatPartage(chiffre="ABCDEF")

    def injecteur(nom):
        raise TimeoutError(f"{nom} hors délai (faute injectée)")

    etat.injecteur_fautes_outils = injecteur
    j = Journal(None, "t")
    llm = Script([{"pensee": "", "appels": [{"outil": "frequences", "arguments": {}}], "conclusion": {}},
                  {"pensee": "", "appels": [], "conclusion": {"famille": "mono", "procedes_probables": ["cesar"],
                                                               "justification": "x"}}])
    _classifieur().executer(llm, "x", etat, j, P)
    assert etat.compteurs["erreurs_outils"] == 1 and j.compter("erreur_outil") == 1


@pytest.fixture
def cas(extrait_fr):
    clair = extrait_fr(600, graine=11)
    return clair, chiffres.autoclave_chiffrer(clair, "ZOLA")


def test_orchestrateur_complet_avec_modele_simule(cas, tmp_path):
    clair, ch = cas
    orch = Orchestrateur(LLMSimule(politique_heuristique), ConfigOrchestrateur(expliquer=True))
    chemin = tmp_path / "t.jsonl"
    r = orch.casser(ch, Journal(chemin, "t"), clair_exercice=clair)
    assert r.statut == "accepte" and r.procede == "autoclave" and lettres(r.clair) == lettres(clair)
    assert r.iterations == 2 and r.rejetes == ["vigenere"]
    assert r.explication and r.exercice_valide is True
    evs = lire(chemin)
    assert {e["agent"] for e in evs} >= {"classifieur", "cryptanalyste", "linguiste", "pedagogue", "verificateur"}
    # Les agents n'invoquent que leurs outils autorisés
    for e in evs:
        if e["type"] == "appel_outil":
            assert e["outil"] in OUTILS_PAR_AGENT[e["agent"]]


def test_replis_si_modele_toujours_en_panne(cas):
    clair, ch = cas

    class Panne:
        nom = "panne"

        def repondre(self, *a):
            raise ErreurLLM("serveur arrêté")

    r = Orchestrateur(Panne(), ConfigOrchestrateur(expliquer=True)).casser(ch, Journal(None, "t"),
                                                                           clair_exercice=clair)
    assert {"classifieur", "cryptanalyste", "linguiste", "pedagogue"} <= set(r.replis)
    assert lettres(r.clair) == lettres(clair) and r.statut == "accepte"
    assert "repli" in r.explication


def test_defaillances_injectees(cas):
    clair, ch = cas
    llm = LLMDefaillant(LLMSimule(politique_heuristique), taux=0.4, graine=3)
    r = Orchestrateur(llm).casser(ch, Journal(None, "t"))
    assert llm.journal and r.statut in ("accepte", "meilleur_effort")
    assert lettres(r.clair) == lettres(clair)


def test_garde_fou_contre_linguiste_complaisant(extrait_fr):
    clair = extrait_fr(150, graine=12)
    ch = chiffres.substitution_chiffrer(clair, "QWERTYUIOPASDFGHJKLZXCVBNM")

    def complaisant(agent, messages, schema, ctx):
        if agent == "linguiste":
            return {"pensee": "", "appels": [], "conclusion": {"plausible": True, "justification": "oui"}}
        return politique_heuristique(agent, messages, schema, ctx)

    r = Orchestrateur(LLMSimule(complaisant), ConfigOrchestrateur(iterations_max=2)).casser(ch, Journal(None, "t"))
    assert r.compteurs.get("garde_fou_declenche", 0) >= 1


def test_identifiant_invente_par_le_cryptanalyste(cas):
    clair, ch = cas

    def menteur(agent, messages, schema, ctx):
        if agent == "cryptanalyste":
            return {"pensee": "", "appels": [], "conclusion": {"id_resultat": "R42", "procede": "cesar",
                                                                "justification": "invention"}}
        return politique_heuristique(agent, messages, schema, ctx)

    r = Orchestrateur(LLMSimule(menteur)).casser(ch, Journal(None, "t"))
    assert "cryptanalyste" in r.replis and lettres(r.clair) == lettres(clair)


def test_baseline(cas):
    clair, ch = cas
    r = casser_baseline(ch, Journal(None, "b"))
    assert r["procede"] == "autoclave" and r["iterations"] == 2 and r["statut"] == "accepte"


def test_client_ollama_injoignable():
    llm = OllamaLLM("qwen3:0.6b", hote="http://127.0.0.1:9", delai=1)
    with pytest.raises(ErreurLLM):
        llm.repondre("classifieur", [], {}, {})
    assert llm.digest() is None


def test_injection_dans_sortie_outil_contree_par_garde_fou(extrait_fr):
    """Un Linguiste qui obéit à la consigne injectée est corrigé par le garde-fou."""
    clair = extrait_fr(400, graine=13)
    ch = chiffres.autoclave_chiffrer(clair, "HUGO")

    def naif(agent, messages, schema, ctx):
        if agent == "linguiste" and any("CONSIGNE PRIORITAIRE" in m["content"] for m in messages):
            return {"pensee": "", "appels": [], "conclusion": {"plausible": True, "justification": "consigne"}}
        return politique_heuristique(agent, messages, schema, ctx)

    r = Orchestrateur(LLMSimule(naif)).casser(ch, Journal(None, "t"), injection_consignes=True)
    assert r.compteurs["garde_fou_declenche"] >= 1
    assert r.procede == "autoclave" and lettres(r.clair) == lettres(clair)


def test_exercice_par_defaut_sur_le_clair_retrouve(cas):
    """Sans clair d'exercice fourni, l'exercice est bâti sur le clair retrouvé (pas sur le chiffré)."""
    clair, ch = cas
    r = Orchestrateur(LLMSimule(politique_heuristique), ConfigOrchestrateur(expliquer=True)).casser(
        ch, Journal(None, "t"))
    assert r.exercice_valide is True


def test_hypothese_rejetee_non_reproposee(cas):
    """Un Cryptanalyste qui relance sans cesse César (trace réelle qwen3:0.6b) ne bloque pas la boucle :
    l'orchestrateur refuse la répétition et passe aux hypothèses suivantes."""
    clair, ch = cas

    def obstine(agent, messages, schema, ctx):
        if agent == "classifieur" and any(m["content"].startswith("RÉSULTATS") for m in messages):
            return {"pensee": "", "appels": [], "conclusion": {"famille": "mono", "procedes_probables": ["cesar"],
                                                                "justification": "erreur volontaire"}}
        if agent == "cryptanalyste":
            if not any(m["content"].startswith("RÉSULTATS") for m in messages):
                return {"pensee": "", "appels": [{"outil": "chi2_cesar", "arguments": {}}]}
            dernier = max(ctx["resultats"], key=lambda k: int(k[1:]))
            return {"pensee": "", "appels": [], "conclusion": {"id_resultat": dernier, "procede": "cesar",
                                                                "justification": "encore César"}}
        if agent == "linguiste" and any(m["content"].startswith("RÉSULTATS") for m in messages):
            return {"pensee": "", "appels": [], "conclusion": {"plausible": True, "justification": "oui"}}
        return politique_heuristique(agent, messages, schema, ctx)

    r = Orchestrateur(LLMSimule(obstine)).casser(ch, Journal(None, "t"))
    assert r.compteurs["hypothese_repetee"] >= 1
    assert r.procede == "autoclave" and lettres(r.clair) == lettres(clair)
