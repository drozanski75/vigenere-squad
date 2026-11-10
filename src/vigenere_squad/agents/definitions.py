"""Les cinq agents spécialisés : rôle, outils autorisés (liste fermée) et
schéma de sortie."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .base import Agent

Procede = Literal["cesar", "affine", "vigenere", "autoclave", "substitution", "beaufort"]


class SortieClassifieur(BaseModel):
    model_config = ConfigDict(extra="ignore")
    famille: Literal["mono", "poly"]
    procedes_probables: list[Procede] = Field(min_length=1, max_length=6)
    justification: str = Field(max_length=240)


class SortieCryptanalyste(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id_resultat: str = Field(pattern=r"^R\d+$", description="résultat d'attaque retenu, ex. R2")
    procede: Procede
    justification: str = Field(max_length=240)


class SortieLinguiste(BaseModel):
    model_config = ConfigDict(extra="ignore")
    plausible: bool
    justification: str = Field(max_length=240)
    procede_suivant: Procede | None = None


class Exercice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    procede: Procede
    cle: str = Field(min_length=1, max_length=40)
    enonce: str = Field(max_length=300)


class SortiePedagogue(BaseModel):
    model_config = ConfigDict(extra="ignore")
    explication: str = Field(min_length=80, max_length=2500)
    exercice: Exercice


class SortieVerificateur(BaseModel):
    model_config = ConfigDict(extra="ignore")
    valide: bool
    commentaire: str = Field(max_length=200)


OUTILS_PAR_AGENT: dict[str, tuple[str, ...]] = {
    "classifieur": ("indice_coincidence", "frequences"),
    "cryptanalyste": ("kasiski", "friedman", "chi2_cesar", "force_brute_affine", "attaque_vigenere",
                      "attaque_beaufort", "attaque_autoclave", "recuit_substitution"),
    "linguiste": ("score_quadrigrammes",),
    "pedagogue": (),
    "verificateur": ("chiffrer_exercice", "casser_exercice"),
}

SORTIES = {
    "classifieur": SortieClassifieur,
    "cryptanalyste": SortieCryptanalyste,
    "linguiste": SortieLinguiste,
    "pedagogue": SortiePedagogue,
    "verificateur": SortieVerificateur,
}


def creer_agents() -> dict[str, Agent]:
    return {nom: Agent(nom, OUTILS_PAR_AGENT[nom], SORTIES[nom]) for nom in OUTILS_PAR_AGENT}
