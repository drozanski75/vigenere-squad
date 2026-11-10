"""Chiffrements classiques (chiffrement et déchiffrement).

Convention : le texte est normalisé (A-Z majuscules) ; les caractères non
alphabétiques sont recopiés sans modification et ne font pas avancer la clé.
Six procédés : César, affine, Vigenère, autoclave (Vigenère à clé auto),
substitution monoalphabétique, Beaufort (procédé au choix).
"""

from __future__ import annotations

from math import gcd

from .texte import ALPHABET, N, cle_valide

PROCEDES = ("cesar", "affine", "vigenere", "autoclave", "substitution", "beaufort")
MONO = ("cesar", "affine", "substitution")
POLY = ("vigenere", "autoclave", "beaufort")

A_VALIDES = tuple(a for a in range(1, N) if gcd(a, N) == 1)  # 12 valeurs


def _appliquer(texte: str, f) -> str:
    """Applique f(index_lettre, valeur) -> valeur à chaque lettre."""
    sortie = []
    i = 0
    for c in texte:
        if "A" <= c <= "Z":
            sortie.append(chr(65 + f(i, ord(c) - 65) % N))
            i += 1
        else:
            sortie.append(c)
    return "".join(sortie)


# --- César -----------------------------------------------------------------
def cesar_chiffrer(texte: str, k: int) -> str:
    return _appliquer(texte, lambda i, p: p + k)


def cesar_dechiffrer(texte: str, k: int) -> str:
    return _appliquer(texte, lambda i, c: c - k)


# --- Affine ----------------------------------------------------------------
def inverse_modulaire(a: int, n: int = N) -> int:
    if gcd(a, n) != 1:
        raise ValueError(f"{a} n'est pas inversible modulo {n}")
    return pow(a, -1, n)


def affine_chiffrer(texte: str, a: int, b: int) -> str:
    inverse_modulaire(a)
    return _appliquer(texte, lambda i, p: a * p + b)


def affine_dechiffrer(texte: str, a: int, b: int) -> str:
    ai = inverse_modulaire(a)
    return _appliquer(texte, lambda i, c: ai * (c - b))


# --- Vigenère --------------------------------------------------------------
def vigenere_chiffrer(texte: str, cle: str) -> str:
    k = [ord(c) - 65 for c in cle_valide(cle)]
    return _appliquer(texte, lambda i, p: p + k[i % len(k)])


def vigenere_dechiffrer(texte: str, cle: str) -> str:
    k = [ord(c) - 65 for c in cle_valide(cle)]
    return _appliquer(texte, lambda i, c: c - k[i % len(k)])


# --- Beaufort (c = k - p, involutif) ----------------------------------------
def beaufort_chiffrer(texte: str, cle: str) -> str:
    k = [ord(c) - 65 for c in cle_valide(cle)]
    return _appliquer(texte, lambda i, p: k[i % len(k)] - p)


beaufort_dechiffrer = beaufort_chiffrer


# --- Autoclave (clé auto sur le clair) --------------------------------------
def autoclave_chiffrer(texte: str, cle: str) -> str:
    amorce = [ord(c) - 65 for c in cle_valide(cle)]
    flux: list[int] = list(amorce)

    def f(i: int, p: int) -> int:
        k = flux[i]
        flux.append(p)
        return p + k

    return _appliquer(texte, f)


def autoclave_dechiffrer(texte: str, cle: str) -> str:
    amorce = [ord(c) - 65 for c in cle_valide(cle)]
    flux: list[int] = list(amorce)

    def f(i: int, c: int) -> int:
        p = (c - flux[i]) % N
        flux.append(p)
        return p

    return _appliquer(texte, f)


# --- Substitution monoalphabétique ------------------------------------------
def verifier_permutation(cle: str) -> str:
    cle = cle.upper()
    if len(cle) != N or set(cle) != set(ALPHABET):
        raise ValueError("une clé de substitution est une permutation des 26 lettres")
    return cle


def substitution_chiffrer(texte: str, cle: str) -> str:
    """``cle[i]`` est l'image chiffrée de la i-ème lettre du clair."""
    cle = verifier_permutation(cle)
    return _appliquer(texte, lambda i, p: ord(cle[p]) - 65)


def substitution_dechiffrer(texte: str, cle: str) -> str:
    cle = verifier_permutation(cle)
    inv = [0] * N
    for i, c in enumerate(cle):
        inv[ord(c) - 65] = i
    return _appliquer(texte, lambda i, c: inv[c])


# --- Interface uniforme -------------------------------------------------------
def chiffrer(procede: str, texte: str, cle) -> str:
    return _dispatch(procede, texte, cle, True)


def dechiffrer(procede: str, texte: str, cle) -> str:
    return _dispatch(procede, texte, cle, False)


def _dispatch(procede: str, texte: str, cle, chiffre: bool) -> str:
    if procede == "cesar":
        k = int(cle) if not isinstance(cle, str) or cle.lstrip("-").isdigit() else ord(cle.upper()[0]) - 65
        return cesar_chiffrer(texte, k) if chiffre else cesar_dechiffrer(texte, k)
    if procede == "affine":
        a, b = (int(x) for x in (cle if not isinstance(cle, str) else cle.split(",")))
        return affine_chiffrer(texte, a, b) if chiffre else affine_dechiffrer(texte, a, b)
    table = {
        "vigenere": (vigenere_chiffrer, vigenere_dechiffrer),
        "autoclave": (autoclave_chiffrer, autoclave_dechiffrer),
        "beaufort": (beaufort_chiffrer, beaufort_dechiffrer),
        "substitution": (substitution_chiffrer, substitution_dechiffrer),
    }
    if procede not in table:
        raise ValueError(f"procédé inconnu : {procede}")
    return table[procede][0 if chiffre else 1](texte, str(cle))


def cle_en_texte(procede: str, cle) -> str:
    """Représentation textuelle canonique d'une clé (pour comparer et tracer)."""
    if procede == "cesar":
        return str(int(cle) % N)
    if procede == "affine":
        a, b = cle if not isinstance(cle, str) else (int(x) for x in cle.split(","))
        return f"{int(a)},{int(b) % N}"
    return str(cle).upper()
