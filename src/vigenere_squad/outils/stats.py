"""Statistiques de cryptanalyse : fréquences, indice de coïncidence, Kasiski,
Friedman, χ². Calculs exacts et déterministes, sans aucun recours au modèle."""

from __future__ import annotations

from collections import Counter, defaultdict

from .texte import ALPHABET, N, lettres

# Indices de coïncidence de référence
IC_ALEATOIRE = 1 / N  # 0,0385
IC_LANGUE = {"fr": 0.0778, "en": 0.0667}

# Fréquences de référence par défaut (remplacées par celles du corpus
# d'apprentissage lorsque le modèle de langue est chargé). Sources usuelles.
FREQ_REF = {
    "fr": [
        0.0763, 0.0090, 0.0326, 0.0367, 0.1472, 0.0107, 0.0087, 0.0074, 0.0753,
        0.0061, 0.0005, 0.0546, 0.0297, 0.0710, 0.0580, 0.0252, 0.0136, 0.0669,
        0.0795, 0.0724, 0.0631, 0.0184, 0.0005, 0.0043, 0.0031, 0.0033,
    ],
    "en": [
        0.0817, 0.0149, 0.0278, 0.0425, 0.1270, 0.0223, 0.0202, 0.0609, 0.0697,
        0.0015, 0.0077, 0.0403, 0.0241, 0.0675, 0.0751, 0.0193, 0.0010, 0.0599,
        0.0633, 0.0906, 0.0276, 0.0098, 0.0236, 0.0015, 0.0197, 0.0007,
    ],
}


def comptes(texte: str) -> list[int]:
    c = Counter(lettres(texte))
    return [c.get(l, 0) for l in ALPHABET]


def frequences(texte: str) -> dict:
    """Effectifs et proportions des 26 lettres, triés par fréquence décroissante."""
    cpt = comptes(texte)
    total = sum(cpt)
    props = [x / total if total else 0.0 for x in cpt]
    ordre = sorted(range(N), key=lambda i: (-cpt[i], i))
    return {
        "total": total,
        "effectifs": dict(zip(ALPHABET, cpt)),
        "proportions": {ALPHABET[i]: round(props[i], 4) for i in range(N)},
        "ordre": "".join(ALPHABET[i] for i in ordre),
    }


def indice_coincidence(texte: str) -> float:
    cpt = comptes(texte)
    n = sum(cpt)
    if n < 2:
        return 0.0
    return sum(x * (x - 1) for x in cpt) / (n * (n - 1))


def colonnes(texte: str, longueur: int) -> list[str]:
    t = lettres(texte)
    return [t[i::longueur] for i in range(longueur)]


def ic_moyen_colonnes(texte: str, longueur: int) -> float:
    cols = colonnes(texte, longueur)
    valeurs = [indice_coincidence(c) for c in cols if len(c) > 1]
    return sum(valeurs) / len(valeurs) if valeurs else 0.0


def _diviseurs(n: int, maxi: int) -> list[int]:
    return [d for d in range(2, maxi + 1) if n % d == 0]


def kasiski(texte: str, taille_min: int = 3, longueur_max: int = 20) -> dict:
    """Test de Kasiski : distances entre répétitions de n-grammes et facteurs."""
    t = lettres(texte)
    positions: dict[str, list[int]] = defaultdict(list)
    for i in range(len(t) - taille_min + 1):
        positions[t[i : i + taille_min]].append(i)
    distances = []
    for pos in positions.values():
        if len(pos) > 1:
            distances.extend(pos[j + 1] - pos[j] for j in range(len(pos) - 1))
    facteurs: Counter[int] = Counter()
    for d in distances:
        facteurs.update(_diviseurs(d, longueur_max))
    # Score : nombre de distances divisibles, pondéré pour ne pas favoriser
    # systématiquement les petits diviseurs (2, 3) : on préfère le plus grand
    # diviseur dont l'effectif reste proche du maximum.
    classement = sorted(facteurs.items(), key=lambda kv: (-kv[1], -kv[0]))
    candidates = []
    if classement:
        maxi = classement[0][1]
        proches = sorted([l for l, v in facteurs.items() if v >= 0.8 * maxi], reverse=True)
        candidates = proches + [l for l, _ in classement if l not in proches]
    return {
        "n_repetitions": len(distances),
        "distances": distances[:50],
        "facteurs": dict(sorted(facteurs.items())),
        "longueurs_candidates": candidates[:6],
    }


def friedman(texte: str, langue: str = "fr", longueur_max: int = 20) -> dict:
    """Estimation de Friedman de la longueur de clé, complétée par l'IC moyen
    par colonnes pour chaque longueur testée (plus fiable sur texte court)."""
    ic = indice_coincidence(texte)
    kp, kr = IC_LANGUE[langue], IC_ALEATOIRE
    n = len(lettres(texte))
    if ic - kr <= 1e-9 or n < 2:
        estimation = float(longueur_max)
    else:
        # Formule complète de Friedman (tient compte de la longueur n)
        estimation = (kp - kr) * n / ((n - 1) * ic - kr * n + kp)
    ic_par_longueur = {
        l: round(ic_moyen_colonnes(texte, l), 4) for l in range(1, min(longueur_max, max(1, n // 2)) + 1)
    }
    # Classement : premières longueurs dont l'IC moyen s'approche de la langue
    # (le seuil relatif écarte les sous-multiples favorisés par une clé à lettres répétées)
    maxi = max(ic_par_longueur.values()) if ic_par_longueur else 0.0
    seuil = max(kr + 0.6 * (kp - kr), 0.9 * maxi)
    au_dessus = [l for l, v in ic_par_longueur.items() if v >= seuil]
    classement = sorted(ic_par_longueur, key=lambda l: -ic_par_longueur[l])
    candidates = sorted(au_dessus)[:3] + [l for l in classement if l not in au_dessus]
    return {
        "ic": round(ic, 5),
        "estimation_longueur": round(estimation, 2),
        "ic_par_longueur": ic_par_longueur,
        "longueurs_candidates": candidates[:6],
    }


def chi2(effectifs: list[int], attendu: list[float]) -> float:
    n = sum(effectifs)
    if n == 0:
        return float("inf")
    return sum((o - n * e) ** 2 / (n * e) for o, e in zip(effectifs, attendu) if e > 0)


def chi2_texte(texte: str, langue: str = "fr", freq=None) -> float:
    return chi2(comptes(texte), freq or FREQ_REF[langue])
