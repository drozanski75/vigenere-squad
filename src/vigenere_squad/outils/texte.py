"""Normalisation des textes et conversions lettres <-> entiers.

Toutes les opérations travaillent sur l'alphabet latin majuscule A-Z (26 lettres).
Les caractères qui ne sont pas des lettres sont conservés tels quels par les
fonctions de chiffrement, mais ignorés par les statistiques.
"""

from __future__ import annotations

import re
import unicodedata

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
N = 26

_LIGATURES = {"Œ": "OE", "œ": "OE", "Æ": "AE", "æ": "AE", "ß": "SS"}
_ESPACES = re.compile(r"\s+")
_NON_LETTRES = re.compile(r"[^A-Z]")


def sans_accents(texte: str) -> str:
    """Retire les diacritiques et développe les ligatures (é -> E, œ -> OE)."""
    for lig, rep in _LIGATURES.items():
        texte = texte.replace(lig, rep)
    decompose = unicodedata.normalize("NFD", texte)
    return "".join(c for c in decompose if unicodedata.category(c) != "Mn")


def normaliser(texte: str, garder_ponctuation: bool = True) -> str:
    """Majuscules sans accents.

    Si ``garder_ponctuation`` est vrai, espaces et ponctuation ASCII sont conservés
    (les blancs multiples sont réduits à un espace). Sinon seules les lettres A-Z
    sont conservées.
    """
    t = sans_accents(texte).upper()
    if not garder_ponctuation:
        return _NON_LETTRES.sub("", t)
    t = "".join(c if (c in ALPHABET or c in " .,;:!?'-") else " " for c in t)
    return _ESPACES.sub(" ", t).strip()


def lettres(texte: str) -> str:
    """Ne garde que les lettres A-Z (le texte doit déjà être normalisé)."""
    return _NON_LETTRES.sub("", texte.upper())


def vers_entiers(texte: str) -> list[int]:
    return [ord(c) - 65 for c in texte if "A" <= c <= "Z"]


def vers_texte(nombres: list[int]) -> str:
    return "".join(chr(65 + (n % N)) for n in nombres)


def cle_valide(cle: str) -> str:
    """Normalise une clé alphabétique ; lève ValueError si elle est vide."""
    c = lettres(sans_accents(cle))
    if not c:
        raise ValueError("clé alphabétique vide")
    return c


def remettre_structure(modele: str, lettres_seules: str) -> str:
    """Réinjecte des lettres dans la structure (espaces, ponctuation) de ``modele``."""
    it = iter(lettres_seules)
    sortie = []
    for c in modele:
        if "A" <= c <= "Z":
            sortie.append(next(it, "?"))
        else:
            sortie.append(c)
    return "".join(sortie)
