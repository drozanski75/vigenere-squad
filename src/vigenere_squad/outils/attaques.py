"""Attaques statistiques déterministes (à graine fixe pour le recuit).

Chaque attaque renvoie un dictionnaire homogène :
``{"procede", "cle", "clair", "score", "score_normalise", ...}``
où ``clair`` conserve la structure (espaces, ponctuation) du chiffré.
"""

from __future__ import annotations

import math

import numpy as np

from . import chiffres
from .langue import ModeleLangue, en_tableau, indices_quadgrammes, modele
from .stats import FREQ_REF, friedman, kasiski
from .texte import ALPHABET, N, remettre_structure


def _resultat(m: ModeleLangue, procede: str, cle, chiffre: str, clair_lettres: str, **extra) -> dict:
    clair = remettre_structure(chiffre, clair_lettres)
    return {
        "procede": procede,
        "cle": chiffres.cle_en_texte(procede, cle),
        "clair": clair,
        "score": round(m.score(clair_lettres), 4),
        "score_normalise": round(m.score_normalise(clair_lettres), 3),
        **extra,
    }


def _freq(m: ModeleLangue) -> np.ndarray:
    return np.asarray(m.freq if m.freq else FREQ_REF[m.langue])


def _chi2_decalages(col: np.ndarray, freq: np.ndarray, signe: int = 1) -> np.ndarray:
    """χ² de la colonne déchiffrée pour chacun des 26 décalages.
    signe=+1 : p = c - k (Vigenère) ; signe=-1 : p = k - c (Beaufort)."""
    cpt = np.bincount(col, minlength=N).astype(float)
    n = cpt.sum()
    res = np.empty(N)
    for k in range(N):
        if signe == 1:
            # p = c - k  => compte_p[p] = cpt[(p + k) % N]
            obs = np.roll(cpt, -k)
        else:
            # p = k - c  => compte_p[p] = cpt[(k - p) % N]
            obs = cpt[(k - np.arange(N)) % N]
        res[k] = ((obs - n * freq) ** 2 / (n * freq)).sum()
    return res


# --- César ----------------------------------------------------------------------
def chi2_cesar(chiffre: str, langue: str = "fr") -> dict:
    m = modele(langue)
    t = en_tableau(chiffre)
    scores = _chi2_decalages(t, _freq(m))
    ordre = np.argsort(scores)
    k = int(ordre[0])
    clair = "".join(ALPHABET[x] for x in (t - k) % N)
    return _resultat(
        m, "cesar", k, chiffre, clair,
        chi2_meilleurs={int(i): round(float(scores[i]), 1) for i in ordre[:3]},
    )


# --- Affine -------------------------------------------------------------------------
def force_brute_affine(chiffre: str, langue: str = "fr") -> dict:
    m = modele(langue)
    t = en_tableau(chiffre)
    meilleur = None
    for a in chiffres.A_VALIDES:
        ai = chiffres.inverse_modulaire(a)
        for b in range(N):
            p = (ai * (t - b)) % N
            s = m.score_tableau(p)
            if meilleur is None or s > meilleur[0]:
                meilleur = (s, a, b, p)
    _, a, b, p = meilleur
    return _resultat(m, "affine", (a, b), chiffre, "".join(ALPHABET[x] for x in p), cles_testees=312)


# --- Polyalphabétiques périodiques (Vigenère, Beaufort) -------------------------------
def _dechiffrer_periodique(t: np.ndarray, cle: np.ndarray, signe: int) -> np.ndarray:
    k = cle[np.arange(len(t)) % len(cle)]
    return (t - k) % N if signe == 1 else (k - t) % N


def _raffiner_periodique(m, t, cle, signe, passes=2):
    meilleur = m.score_tableau(_dechiffrer_periodique(t, cle, signe))
    for _ in range(passes):
        ameliore = False
        for j in range(len(cle)):
            origine = cle[j]
            for k in range(N):
                if k == origine:
                    continue
                cle[j] = k
                s = m.score_tableau(_dechiffrer_periodique(t, cle, signe))
                if s > meilleur:
                    meilleur, origine, ameliore = s, k, True
            cle[j] = origine
        if not ameliore:
            break
    return cle, meilleur


def periode_minimale(cle: str) -> str:
    for p in range(1, len(cle) + 1):
        if len(cle) % p == 0 and cle[:p] * (len(cle) // p) == cle:
            return cle[:p]
    return cle


def _longueurs_par_defaut(chiffre: str, langue: str, maxi: int = 15) -> list[int]:
    kas = kasiski(chiffre, longueur_max=maxi)["longueurs_candidates"]
    fri = friedman(chiffre, langue, longueur_max=maxi)["longueurs_candidates"]
    vus: list[int] = []
    for l in fri[:4] + kas[:4]:
        if l not in vus:
            vus.append(l)
    return vus or list(range(1, 8))


def _attaque_periodique(chiffre, longueurs, langue, signe, nom):
    m = modele(langue)
    t = en_tableau(chiffre)
    freq = _freq(m)
    if not longueurs:
        longueurs = _longueurs_par_defaut(chiffre, langue)
    longueurs = [int(l) for l in longueurs if 1 <= int(l) <= max(1, len(t) // 2)] or [1]
    essais = []
    for L in longueurs:
        cle = np.array([int(np.argmin(_chi2_decalages(t[j::L], freq, signe))) for j in range(L)])
        cle, s = _raffiner_periodique(m, t, cle, signe)
        essais.append((s, L, cle.copy()))
    essais.sort(key=lambda e: -e[0])
    s, L, cle = essais[0]
    cle_txt = periode_minimale("".join(ALPHABET[k] for k in cle))
    p = _dechiffrer_periodique(t, cle, signe)
    return _resultat(
        m, nom, cle_txt, chiffre, "".join(ALPHABET[x] for x in p),
        longueurs_testees=[e[1] for e in essais],
        scores_par_longueur={int(e[1]): round(float(e[0]), 3) for e in essais},
    )


def attaque_vigenere(chiffre: str, longueurs: list[int] | None = None, langue: str = "fr") -> dict:
    return _attaque_periodique(chiffre, longueurs, langue, 1, "vigenere")


def attaque_beaufort(chiffre: str, longueurs: list[int] | None = None, langue: str = "fr") -> dict:
    return _attaque_periodique(chiffre, longueurs, langue, -1, "beaufort")


# --- Autoclave ------------------------------------------------------------------------
def _autoclave_dechiffrer_tab(t: np.ndarray, amorce: np.ndarray) -> np.ndarray:
    L = len(amorce)
    p = np.empty_like(t)
    p[:L] = (t[:L] - amorce[: len(t[:L])]) % N
    for i in range(L, len(t)):
        p[i] = (t[i] - p[i - L]) % N
    return p


def _chaine_colonne(col: np.ndarray, k0: int) -> np.ndarray:
    """Colonne j : p0 = c0 - K ; p_{r} = c_{r} - p_{r-1} (récurrence sur la colonne)."""
    p = np.empty_like(col)
    prec = k0
    for r, c in enumerate(col):
        prec = (c - prec) % N
        p[r] = prec
    return p


def attaque_autoclave(chiffre: str, longueur_max: int = 15, langue: str = "fr") -> dict:
    """Attaque de l'autoclave (clé auto sur le clair).

    Pour une longueur d'amorce L, chaque colonne j (positions j, j+L, ...) ne
    dépend que de la lettre d'amorce K_j : p_j = c_j - K_j puis
    p_{j+rL} = c_{j+rL} - p_{j+(r-1)L}. Chaque colonne est donc attaquée
    séparément par χ² sur 26 hypothèses, puis la clé est affinée par escalade
    sur le score de quadrigrammes. La meilleure longueur est retenue.
    """
    m = modele(langue)
    t = en_tableau(chiffre)
    freq = _freq(m)
    essais = []
    for L in range(1, min(longueur_max, max(1, len(t) // 3)) + 1):
        amorce = np.zeros(L, dtype=np.int64)
        for j in range(L):
            col = t[j::L]
            meilleur = None
            for k in range(N):
                p = _chaine_colonne(col, k)
                cpt = np.bincount(p, minlength=N)
                n = cpt.sum()
                x2 = float(((cpt - n * freq) ** 2 / (n * freq)).sum())
                if meilleur is None or x2 < meilleur[0]:
                    meilleur = (x2, k)
            amorce[j] = meilleur[1]
        s = m.score_tableau(_autoclave_dechiffrer_tab(t, amorce))
        for _ in range(2):  # escalade
            ameliore = False
            for j in range(L):
                orig = amorce[j]
                for k in range(N):
                    if k == orig:
                        continue
                    amorce[j] = k
                    s2 = m.score_tableau(_autoclave_dechiffrer_tab(t, amorce))
                    if s2 > s:
                        s, orig, ameliore = s2, k, True
                amorce[j] = orig
            if not ameliore:
                break
        essais.append((s, L, amorce.copy()))
    essais.sort(key=lambda e: -e[0])
    s, L, amorce = essais[0]
    p = _autoclave_dechiffrer_tab(t, amorce)
    return _resultat(
        m, "autoclave", "".join(ALPHABET[k] for k in amorce), chiffre,
        "".join(ALPHABET[x] for x in p),
        longueur_amorce=int(L),
        scores_par_longueur={int(e[1]): round(float(e[0]), 3) for e in sorted(essais, key=lambda e: e[1])},
    )


# --- Substitution monoalphabétique : recuit simulé ----------------------------------------
def recuit_substitution(
    chiffre: str,
    langue: str = "fr",
    iterations: int = 6000,
    redemarrages: int = 6,
    graine: int = 0,
    temperature_initiale: float = 2.0,
) -> dict:
    """Recuit simulé sur la permutation de déchiffrement, objectif = somme des
    log-probabilités de quadrigrammes. Déterministe pour une graine donnée."""
    m = modele(langue)
    t = en_tableau(chiffre)
    rng = np.random.default_rng(graine)
    logp = m.logp
    freq = _freq(m)
    ordre_clair = np.argsort(-freq, kind="stable")
    ordre_chiffre = np.argsort(-np.bincount(t, minlength=N), kind="stable")
    depart = np.empty(N, dtype=np.int64)
    depart[ordre_chiffre] = ordre_clair  # déchiffrement : lettre chiffrée -> claire

    def total(d):
        return float(logp[indices_quadgrammes(d[t])].sum())

    meilleur_global = (-math.inf, depart.copy())
    for r in range(redemarrages):
        d = depart.copy()
        if r > 0:  # redémarrage : perturbation du meilleur point de départ
            base = meilleur_global[1] if r % 2 else depart
            d = base.copy()
            for _ in range(4 + r):
                i, j = rng.integers(0, N, 2)
                d[i], d[j] = d[j], d[i]
        s = total(d)
        best_local = (s, d.copy())
        for it in range(iterations):
            T = temperature_initiale * (1 - it / iterations) + 1e-3
            i, j = rng.integers(0, N, 2)
            if i == j:
                continue
            d[i], d[j] = d[j], d[i]
            s2 = total(d)
            if s2 >= s or rng.random() < math.exp((s2 - s) / T):
                s = s2
                if s > best_local[0]:
                    best_local = (s, d.copy())
            else:
                d[i], d[j] = d[j], d[i]
        if best_local[0] > meilleur_global[0]:
            meilleur_global = best_local
    d = meilleur_global[1].copy()
    # Polissage déterministe : essais exhaustifs des 325 échanges jusqu'à stabilité
    s = total(d)
    ameliore = True
    while ameliore:
        ameliore = False
        for i in range(N):
            for j in range(i + 1, N):
                d[i], d[j] = d[j], d[i]
                s2 = total(d)
                if s2 > s + 1e-9:
                    s, ameliore = s2, True
                else:
                    d[i], d[j] = d[j], d[i]
    # Clé de chiffrement : clair i -> chiffré cle[i]
    cle = ["?"] * N
    for c, p in enumerate(d):
        cle[int(p)] = ALPHABET[c]
    clair = "".join(ALPHABET[x] for x in d[t])
    return _resultat(
        m, "substitution", "".join(cle), chiffre, clair,
        iterations=iterations * redemarrages, graine=graine,
    )


ATTAQUES = {
    "cesar": chi2_cesar,
    "affine": force_brute_affine,
    "vigenere": attaque_vigenere,
    "beaufort": attaque_beaufort,
    "autoclave": attaque_autoclave,
    "substitution": recuit_substitution,
}
