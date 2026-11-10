"""État partagé typé entre l'orchestrateur, les agents et les outils."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class EtatPartage:
    chiffre: str
    langue: str = "fr"
    graine: int = 0
    # Décisions successives
    famille: str | None = None
    hypotheses: list[str] = field(default_factory=list)
    rejetes: list[str] = field(default_factory=list)          # procédés rejetés
    ids_rejetes: list[str] = field(default_factory=list)      # résultats rejetés
    candidat: str | None = None                                # id du résultat en cours d'examen
    avis_linguiste: str | None = None
    procede_suggere: str | None = None
    # Résultats d'attaques : id -> dict (clair, clé, score...)
    resultats: dict[str, dict] = field(default_factory=dict)
    # Exercice
    exercice_clair: str | None = None
    exercice_procede: str | None = None
    exercice_chiffre: str | None = None
    # Instrumentation
    compteurs: dict[str, int] = field(default_factory=dict)
    replis: list[str] = field(default_factory=list)
    injection_consignes: bool = False   # expérience M1/M2 : consigne malveillante dans la sortie d'outil
    injecteur_fautes_outils: Callable[[str], None] | None = None

    # Accès de type dictionnaire (utilisé par les outils)
    def __getitem__(self, cle: str) -> Any:
        return getattr(self, cle)

    def __setitem__(self, cle: str, valeur: Any) -> None:
        if not hasattr(self, cle):
            raise KeyError(f"champ d'état inconnu : {cle}")
        setattr(self, cle, valeur)

    def get(self, cle: str, defaut: Any = None) -> Any:
        return getattr(self, cle, defaut)

    def setdefault(self, cle: str, defaut: Any) -> Any:
        v = getattr(self, cle, None)
        if v is None:
            setattr(self, cle, defaut)
            return defaut
        return v

    def __iter__(self):
        return iter(self.__dataclass_fields__)

    def keys(self):
        return list(self.__dataclass_fields__)
