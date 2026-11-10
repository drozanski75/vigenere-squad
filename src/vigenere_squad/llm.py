"""Clients de modèle de langage.

* ``OllamaLLM`` : modèle local servi par Ollama (API HTTP /api/chat), sortie
  contrainte par schéma JSON (décodage guidé).
* ``LLMSimule`` : politique scriptée déterministe, utilisée par les tests
  automatisés pour exercer tout le chemin multi-agents sans modèle.
* ``LLMDefaillant`` : enveloppe d'injection de fautes (délai dépassé, JSON
  invalide, réponse vide) pour l'étude de robustesse.
"""

from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


class ErreurLLM(RuntimeError):
    """Erreur de transport ou d'exécution du modèle (réessayable)."""


class ClientLLM(Protocol):
    nom: str

    def repondre(self, agent: str, messages: list[dict], schema: dict, contexte: dict) -> str: ...


@dataclass
class OllamaLLM:
    modele: str
    hote: str = "http://127.0.0.1:11434"
    temperature: float = 0.3
    graine: int = 0
    contexte_max: int = 2048
    jetons_max: int = 256
    delai: float = 180.0
    # Le Pédagogue rédige un texte long : budget de jetons propre
    jetons_max_par_agent: dict = field(default_factory=lambda: {"pedagogue": 900})
    nom: str = field(init=False)
    stats: dict = field(default_factory=lambda: {"appels": 0, "jetons_entree": 0, "jetons_sortie": 0, "duree_s": 0.0})

    def __post_init__(self):
        self.nom = f"ollama:{self.modele}"

    def _post(self, chemin: str, corps: dict, delai: float) -> dict:
        req = urllib.request.Request(
            self.hote + chemin,
            data=json.dumps(corps).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=delai) as r:  # noqa: S310 (hôte local configuré)
                return json.loads(r.read())
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            raise ErreurLLM(f"Ollama injoignable ou délai dépassé : {e}") from e

    def repondre(self, agent: str, messages: list[dict], schema: dict, contexte: dict) -> str:
        corps = {
            "model": self.modele,
            "messages": messages,
            "stream": False,
            "format": schema,
            "think": False,
            "keep_alive": "30m",
            "options": {
                "temperature": self.temperature,
                "seed": self.graine,
                "num_ctx": self.contexte_max,
                "num_predict": self.jetons_max_par_agent.get(agent, self.jetons_max),
            },
        }
        t = time.perf_counter()
        d = self._post("/api/chat", corps, self.delai)
        self.stats["appels"] += 1
        self.stats["jetons_entree"] += int(d.get("prompt_eval_count", 0))
        self.stats["jetons_sortie"] += int(d.get("eval_count", 0))
        # Ollama tronque silencieusement le début d'un prompt trop long : on le signale
        if int(d.get("prompt_eval_count", 0)) + int(d.get("eval_count", 0)) >= self.contexte_max - 8:
            self.stats["contexte_sature"] = self.stats.get("contexte_sature", 0) + 1
            if isinstance(contexte, dict) or hasattr(contexte, "compteurs"):
                c = contexte.compteurs if hasattr(contexte, "compteurs") else contexte.setdefault("compteurs", {})
                c["contexte_sature"] = c.get("contexte_sature", 0) + 1
        self.stats["duree_s"] += time.perf_counter() - t
        return d.get("message", {}).get("content", "")

    def telecharger(self) -> None:
        """Équivalent de `ollama pull` par l'API HTTP (fonctionne aussi vers un conteneur)."""
        req = urllib.request.Request(self.hote + "/api/pull", data=json.dumps(
            {"model": self.modele, "stream": True}).encode(), headers={"Content-Type": "application/json"})
        dernier = ""
        with urllib.request.urlopen(req, timeout=3600) as r:  # noqa: S310
            for ligne in r:
                d = json.loads(ligne or b"{}")
                if "error" in d:
                    raise ErreurLLM(d["error"])
                etat = d.get("status", "")
                if etat != dernier:
                    print(f"  {self.modele} : {etat}", flush=True)
                    dernier = etat

    def digest(self) -> str | None:
        """Empreinte du modèle installé (``ollama list``)."""
        try:
            req = urllib.request.Request(self.hote + "/api/tags")
            with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
                for m in json.loads(r.read()).get("models", []):
                    if m.get("name") == self.modele or m.get("model") == self.modele:
                        return m.get("digest")
        except Exception:  # noqa: BLE001
            return None
        return None


Politique = Callable[[str, list[dict], dict, dict], dict]


@dataclass
class LLMSimule:
    """Modèle simulé : une politique Python produit la réponse JSON attendue."""

    politique: Politique
    nom: str = "simule"
    stats: dict = field(default_factory=lambda: {"appels": 0})

    def repondre(self, agent: str, messages: list[dict], schema: dict, contexte: dict) -> str:
        self.stats["appels"] += 1
        return json.dumps(self.politique(agent, messages, schema, contexte), ensure_ascii=False)


@dataclass
class LLMDefaillant:
    """Enveloppe qui injecte des fautes avec une probabilité donnée."""

    interne: Any
    taux: float = 0.2
    graine: int = 0
    types: tuple[str, ...] = ("delai", "json_invalide", "vide")
    journal: list = field(default_factory=list)

    def __post_init__(self):
        self._rng = random.Random(self.graine)
        self.nom = f"defaillant({self.interne.nom},{self.taux})"
        self.stats = getattr(self.interne, "stats", {})

    def repondre(self, agent: str, messages: list[dict], schema: dict, contexte: dict) -> str:
        if self._rng.random() < self.taux:
            faute = self._rng.choice(self.types)
            self.journal.append({"agent": agent, "faute": faute})
            if faute == "delai":
                raise ErreurLLM("délai dépassé (faute injectée)")
            if faute == "json_invalide":
                return '{"pensee": "tronqué", "appels": ['
            return ""
        return self.interne.repondre(agent, messages, schema, contexte)
