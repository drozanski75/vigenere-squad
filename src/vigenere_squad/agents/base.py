"""Agent générique : prompt système versionné, liste fermée d'outils, sortie
structurée validée par Pydantic, réessais sur erreur.

Protocole (deux phases par tour, une seule requête au modèle par tour) :
le modèle renvoie un objet JSON ``{"pensee", "appels", "conclusion"}``.
* ``appels`` non vide : l'orchestrateur exécute les outils (après contrôle de
  la liste fermée et validation des arguments), renvoie les résultats, et
  l'agent rejoue un tour ;
* ``appels`` vide : ``conclusion`` est validée par le schéma de l'agent.
"""

from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError

from ..llm import ErreurLLM
from ..outils.registre import OUTILS
from ..traces import Journal

DOSSIER_PROMPTS = Path(__file__).resolve().parents[1] / "prompts"


class EchecAgent(RuntimeError):
    """L'agent n'a pas produit de conclusion valide (après réessais)."""


@dataclass(frozen=True)
class Prompt:
    agent: str
    version: str
    texte: str
    sha256: str


def charger_prompt(agent: str) -> Prompt:
    brut = (DOSSIER_PROMPTS / f"{agent}.md").read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n(.*)", brut, re.S)
    if not m:
        raise ValueError(f"prompt {agent} sans en-tête de version")
    entete = dict(l.split(":", 1) for l in m.group(1).splitlines() if ":" in l)
    return Prompt(agent, entete["version"].strip(), m.group(2).strip(),
                  hashlib.sha256(brut.encode()).hexdigest()[:16])


LONGUEUR_MAX_GRAMMAIRE = 600


def _schema_pour_ollama(schema: dict, defs: dict | None = None):
    """Schéma simplifié pour le décodage guidé d'Ollama : références $ref
    développées (Ollama refuse les $defs imbriqués : erreur HTTP 400), titres
    retirés, et longues bornes maxLength supprimées (grammaire trop lourde ;
    la borne reste vérifiée par Pydantic)."""
    if defs is None and isinstance(schema, dict):
        defs = schema.get("$defs", {})
    if isinstance(schema, dict):
        if "$ref" in schema:
            return _schema_pour_ollama(defs[schema["$ref"].split("/")[-1]], defs)
        out = {}
        for k, v in schema.items():
            if k in ("title", "$defs"):
                continue
            if k == "maxLength" and isinstance(v, int) and v > LONGUEUR_MAX_GRAMMAIRE:
                continue
            out[k] = _schema_pour_ollama(v, defs)
        return out
    if isinstance(schema, list):
        return [_schema_pour_ollama(v, defs) for v in schema]
    return schema


@dataclass
class ParametresExecution:
    reessais: int = 2           # nouvelles tentatives après réponse invalide / erreur
    tours_max: int = 3          # tours d'appels d'outils avant conclusion forcée
    delai_outil_s: float = 120.0
    contraindre_outils: bool = True  # liste fermée imposée aussi au décodage (enum)


class Agent:
    def __init__(self, nom: str, outils: tuple[str, ...], schema_conclusion: type[BaseModel]):
        inconnus = set(outils) - set(OUTILS)
        if inconnus:
            raise ValueError(f"outils inconnus pour {nom} : {inconnus}")
        self.nom = nom
        self.outils = tuple(outils)
        self.schema_conclusion = schema_conclusion
        self.prompt = charger_prompt(nom)

    # --- construction des messages ---------------------------------------------------
    def schema_reponse(self, params: ParametresExecution, phase: str = "conclusion") -> dict:
        """Deux phases : « outils » (premier tour d'un agent outillé : seulement des
        appels, pas de conclusion à générer pour rien) puis « conclusion »
        (conclusion obligatoire ; appels supplémentaires facultatifs)."""
        conclusion = _schema_pour_ollama(self.schema_conclusion.model_json_schema())
        pensee = {"type": "string", "maxLength": 120}
        nom_outil: dict = {"type": "string"}
        if params.contraindre_outils and self.outils:
            nom_outil["enum"] = list(self.outils)
        appels = {
            "type": "array",
            "maxItems": 4,
            "items": {
                "type": "object",
                "properties": {"outil": nom_outil, "arguments": {"type": "object"}},
                "required": ["outil", "arguments"],
            },
        }
        if not self.outils:
            return {"type": "object", "properties": {"pensee": pensee, "conclusion": conclusion},
                    "required": ["pensee", "conclusion"]}
        if phase == "outils":
            return {"type": "object", "properties": {"pensee": pensee, "appels": dict(appels, minItems=1)},
                    "required": ["pensee", "appels"]}
        return {"type": "object", "properties": {"pensee": pensee, "appels": appels, "conclusion": conclusion},
                "required": ["pensee", "appels", "conclusion"]}

    def message_systeme(self) -> str:
        if self.outils:
            lignes = []
            for o in self.outils:
                outil = OUTILS[o]
                champs = list(outil.arguments.model_fields)
                lignes.append(f"- {o}({', '.join(champs)}) : {outil.description}")
            liste = "\n".join(lignes)
        else:
            liste = "(aucun outil : tu lis uniquement les traces fournies)"
        return (
            f"{self.prompt.texte}\n\n"
            f"OUTILS AUTORISÉS (liste fermée, tout autre nom est refusé) :\n{liste}\n\n"
            "FORMAT : réponds uniquement par un objet JSON "
            '{"pensee": "...", "appels": [{"outil": "...", "arguments": {...}}], "conclusion": {...}}. '
            "Pour appeler des outils, remplis 'appels' (la conclusion est alors ignorée). "
            "Pour conclure, laisse 'appels' vide et remplis 'conclusion'. "
            "Tu ne calcules jamais toi-même : tu t'appuies sur les résultats des outils. "
            "Sois bref : 'pensee' en une courte phrase, justification en une phrase. "
            "Demande en UNE SEULE réponse tous les outils dont tu as besoin (plusieurs appels possibles)."
        )

    # --- exécution ----------------------------------------------------------------------
    def executer(self, llm, contexte_texte: str, ctx: dict, journal: Journal,
                 params: ParametresExecution) -> BaseModel:
        messages = [
            {"role": "system", "content": self.message_systeme()},
            {"role": "user", "content": contexte_texte},
        ]
        journal.ecrire("debut_agent", self.nom, prompt_version=self.prompt.version,
                       prompt_sha256=self.prompt.sha256, entree=contexte_texte)
        tours = 0
        erreurs = 0
        deja_appeles: dict[str, dict] = {}
        while True:
            phase = "outils" if (self.outils and tours == 0) else "conclusion"
            schema = self.schema_reponse(params, phase)
            try:
                brut = llm.repondre(self.nom, messages, schema, ctx)
                journal.ecrire("reponse_llm", self.nom, brut=brut)
                if not brut or not brut.strip():
                    raise ValueError("réponse vide")
                donnees = json.loads(brut)
                if not isinstance(donnees, dict):
                    raise ValueError("la réponse n'est pas un objet JSON")
            except (ErreurLLM, ValueError, json.JSONDecodeError) as e:
                erreurs += 1
                journal.ecrire("erreur_llm", self.nom, erreur=str(e), tentative=erreurs)
                ctx.setdefault("compteurs", {}).setdefault("erreurs_llm", 0)
                ctx["compteurs"]["erreurs_llm"] += 1
                if erreurs > params.reessais:
                    raise EchecAgent(f"{self.nom} : {e}") from e
                if not isinstance(e, ErreurLLM):
                    messages.append({"role": "user", "content":
                                     f"Réponse invalide ({e}). Renvoie uniquement l'objet JSON demandé."})
                continue

            appels = donnees.get("appels") or []
            if appels and tours < params.tours_max:
                tours += 1
                messages.append({"role": "assistant", "content": brut})
                resultats = []
                for a in appels[:4]:
                    cle = json.dumps(a, sort_keys=True, ensure_ascii=False) if isinstance(a, dict) else str(a)
                    if cle in deja_appeles:  # appel identique déjà fait : pas de recalcul, rappel explicite
                        resultats.append({**deja_appeles[cle], "note": "appel déjà fait, résultat identique"})
                        ctx.compteurs["appels_repetes"] = ctx.compteurs.get("appels_repetes", 0) + 1
                        continue
                    res = self._appeler(a, ctx, journal, params)
                    deja_appeles[cle] = res
                    resultats.append(res)
                consigne = self.consigne_suite(ctx, tours >= params.tours_max)
                messages.append({"role": "user", "content":
                                 "RÉSULTATS DES OUTILS :\n" + json.dumps(resultats, ensure_ascii=False)
                                 + (f"\n{consigne}" if consigne else "")})
                continue
            try:
                conclusion = self.schema_conclusion.model_validate(donnees.get("conclusion") or {})
            except ValidationError as e:
                erreurs += 1
                journal.ecrire("erreur_llm", self.nom, erreur="conclusion invalide", details=str(e)[:400],
                               tentative=erreurs)
                ctx.setdefault("compteurs", {}).setdefault("erreurs_llm", 0)
                ctx["compteurs"]["erreurs_llm"] += 1
                if erreurs > params.reessais:
                    raise EchecAgent(f"{self.nom} : conclusion invalide") from e
                messages.append({"role": "assistant", "content": brut})
                messages.append({"role": "user", "content":
                                 f"Conclusion invalide : {str(e)[:300]}. Corrige et renvoie le JSON complet."})
                continue
            journal.ecrire("conclusion", self.nom, conclusion=conclusion.model_dump())
            return conclusion

    def consigne_suite(self, ctx, dernier_tour: bool) -> str:
        """Rappel factuel après des résultats d'outils (évite les boucles)."""
        ids = [rid for rid in ctx.get("resultats", {}) if rid not in (ctx.get("ids_rejetes") or [])]
        if self.nom == "cryptanalyste" and not ids:
            return ("Aucune attaque n'a encore été lancée : aucun id_resultat n'existe. Appelle maintenant "
                    "l'attaque adaptée (attaque_vigenere, attaque_beaufort, attaque_autoclave, chi2_cesar, "
                    "force_brute_affine ou recuit_substitution).")
        if self.nom == "cryptanalyste":
            return f"Résultats disponibles : {', '.join(ids)}. Conclus avec l'un d'eux (appels vide)."
        return "Conclus maintenant (appels vide)." if dernier_tour else "Conclus maintenant si tu as assez d'éléments."

    def _appeler(self, appel: dict, ctx: dict, journal: Journal, params: ParametresExecution) -> dict:
        nom = appel.get("outil") if isinstance(appel, dict) else None
        args = (appel.get("arguments") or {}) if isinstance(appel, dict) else {}
        compteurs = ctx.setdefault("compteurs", {})
        if nom not in self.outils:
            compteurs["appels_refuses"] = compteurs.get("appels_refuses", 0) + 1
            journal.ecrire("appel_refuse", self.nom, outil=nom, arguments=args,
                           motif="outil hors de la liste fermée de l'agent")
            return {"outil": nom, "erreur": f"outil non autorisé pour {self.nom}"}
        outil = OUTILS[nom]
        try:
            valides = outil.arguments.model_validate(args)
        except ValidationError as e:
            compteurs["arguments_invalides"] = compteurs.get("arguments_invalides", 0) + 1
            journal.ecrire("arguments_invalides", self.nom, outil=nom, arguments=args, erreur=str(e)[:300])
            return {"outil": nom, "erreur": "arguments invalides", "details": str(e)[:200]}
        compteurs["appels_outils"] = compteurs.get("appels_outils", 0) + 1
        journal.ecrire("appel_outil", self.nom, outil=nom, arguments=valides.model_dump())
        try:
            resultat = executer_outil(outil, ctx, valides, params.delai_outil_s)
        except Exception as e:  # noqa: BLE001 (toute erreur d'outil est rapportée à l'agent)
            compteurs["erreurs_outils"] = compteurs.get("erreurs_outils", 0) + 1
            journal.ecrire("erreur_outil", self.nom, outil=nom, erreur=f"{type(e).__name__}: {e}")
            return {"outil": nom, "erreur": f"{type(e).__name__}: {e}"}
        if outil.est_attaque:
            rid = f"R{len(ctx['resultats']) + 1}"
            ctx["resultats"][rid] = resultat
            journal.ecrire("resultat_outil", self.nom, outil=nom, id_resultat=rid, resultat=resultat)
            return {"outil": nom, "id_resultat": rid, **resume_attaque(resultat)}
        journal.ecrire("resultat_outil", self.nom, outil=nom, resultat=resultat)
        return {"outil": nom, "resultat": resultat}


_POOL = cf.ThreadPoolExecutor(max_workers=2, thread_name_prefix="outil")


def executer_outil(outil, ctx: dict, args, delai: float) -> dict:
    """Exécute un outil avec délai maximal ; les fautes injectées passent ici."""
    faute = ctx.get("injecteur_fautes_outils")
    if faute is not None:
        faute(outil.nom)  # peut lever une exception (faute injectée)
    fut = _POOL.submit(outil.fonction, ctx, args)
    try:
        return fut.result(timeout=delai)
    except cf.TimeoutError as e:
        raise TimeoutError(f"outil {outil.nom} hors délai ({delai} s)") from e


def resume_attaque(r: dict) -> dict:
    """Résumé compact d'un résultat d'attaque pour le modèle (pas le clair complet)."""
    return {
        "procede": r["procede"],
        "cle": r["cle"] if r["procede"] != "substitution" else r["cle"][:26],
        "score_normalise": r["score_normalise"],
        "debut_clair": r["clair"][:80],
    }
