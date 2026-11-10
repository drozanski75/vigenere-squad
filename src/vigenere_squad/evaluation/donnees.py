"""Téléchargement vérifié des textes sources, extraction du corps du texte,
construction des modèles de langue et génération du corpus de chiffrés."""

from __future__ import annotations

import hashlib
import json
import random
import re
import urllib.request
from pathlib import Path

from ..outils import chiffres
from ..outils.langue import DOSSIER_MODELES, ModeleLangue
from ..outils.texte import ALPHABET, lettres, normaliser

RACINE = Path(__file__).resolve().parents[3]
DATA = RACINE / "data"
RAW = DATA / "raw"
CORPUS = DATA / "corpus"

_DEBUT = re.compile(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I | re.S)
_FIN = re.compile(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG", re.I)


def sources() -> list[dict]:
    return json.loads((DATA / "sources.json").read_text(encoding="utf-8"))["textes"]


def sha256_fichier(chemin: Path) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 16), b""):
            h.update(bloc)
    return h.hexdigest()


def telecharger_et_verifier() -> list[str]:
    """Télécharge les textes absents depuis le miroir et vérifie toutes les empreintes."""
    meta = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    RAW.mkdir(parents=True, exist_ok=True)
    journal = []
    for s in meta["textes"]:
        cible = RAW / s["fichier"]
        if not cible.exists():
            url = f"{meta['miroir']}/{s['chemin']}"
            with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 (URL fixe)
                cible.write_bytes(r.read())
            journal.append(f"téléchargé {s['fichier']}")
        empreinte = sha256_fichier(cible)
        if empreinte != s["sha256"]:
            raise RuntimeError(f"Empreinte inattendue pour {s['fichier']} : {empreinte}")
        journal.append(f"vérifié {s['fichier']}")
    return journal


def corps(s: dict) -> str:
    brut = (RAW / s["fichier"]).read_bytes().decode(s["encodage"], errors="replace")
    debut = _DEBUT.search(brut)
    fin = _FIN.search(brut)
    texte = brut[debut.end() if debut else 0 : fin.start() if fin else len(brut)]
    return texte.replace("\r\n", "\n")


def construire_modeles() -> dict:
    resume = {}
    for langue in ("fr", "en"):
        app = [normaliser(corps(s), False) for s in sources() if s["langue"] == langue and s["role"] == "apprentissage"]
        m = ModeleLangue.apprendre(app, langue)
        m.calibrer(app, graine=0)
        m.sauver(DOSSIER_MODELES)
        resume[langue] = m.meta
    return resume


# --- Corpus de chiffrés ---------------------------------------------------------------
LONGUEURS = (80, 150, 300, 600, 1000, 2000)


def tranche(n: int) -> str:
    bornes = [(0, 119, "080-119"), (120, 249, "120-249"), (250, 499, "250-499"),
              (500, 899, "500-899"), (900, 1499, "900-1499"), (1500, 10**9, "1500+")]
    for lo, hi, nom in bornes:
        if lo <= n <= hi:
            return nom
    return "?"


def textes_test(langue: str) -> list[str]:
    return [normaliser(corps(s), True) for s in sources() if s["langue"] == langue and s["role"] == "test"]


def extrait(rng: random.Random, textes: list[str], n_lettres: int) -> str:
    """Extrait commençant en début de phrase, coupé à exactement ``n_lettres`` lettres."""
    texte = rng.choice(textes)
    debuts = [m.end() for m in re.finditer(r"[.!?] ", texte)]
    for _ in range(100):
        d = rng.choice(debuts)
        morceau, n = [], 0
        for c in texte[d:]:
            if "A" <= c <= "Z":
                n += 1
            morceau.append(c)
            if n == n_lettres:
                return "".join(morceau).strip()
    raise RuntimeError("texte trop court pour l'extrait demandé")


def cle_aleatoire(rng: random.Random, procede: str):
    if procede == "cesar":
        return rng.randrange(1, 26)
    if procede == "affine":
        return (rng.choice([a for a in chiffres.A_VALIDES if a != 1]), rng.randrange(26))
    if procede == "substitution":
        p = list(ALPHABET)
        rng.shuffle(p)
        return "".join(p)
    longueur = rng.randint(3, 12)
    return "".join(rng.choice(ALPHABET) for _ in range(longueur))


def appliquer_fautes(rng: random.Random, texte: str, taux: float) -> str:
    sortie = []
    for c in texte:
        if "A" <= c <= "Z" and rng.random() < taux:
            sortie.append(rng.choice(ALPHABET.replace(c, "")))
        else:
            sortie.append(c)
    return "".join(sortie)


VARIANTES = ("standard", "sans_espaces", "fautes5", "anglais")


def generer_corpus(graine: int = 42, par_cellule: int = 5, variante: str = "standard",
                   longueurs=LONGUEURS, procedes=chiffres.PROCEDES) -> list[dict]:
    rng = random.Random(f"{graine}-{variante}")
    textes = textes_test("en" if variante == "anglais" else "fr")
    corpus = []
    for procede in procedes:
        for n in longueurs:
            for r in range(par_cellule):
                clair = extrait(rng, textes, n)
                if variante == "sans_espaces":
                    clair = lettres(clair)
                elif variante == "fautes5":
                    clair = appliquer_fautes(rng, clair, 0.05)
                cle = cle_aleatoire(rng, procede)
                chiffre = chiffres.chiffrer(procede, clair, cle)
                corpus.append({
                    "id": f"{variante}-{procede}-{n:04d}-{r}",
                    "variante": variante,
                    "procede": procede,
                    "longueur": len(lettres(clair)),
                    "tranche": tranche(len(lettres(clair))),
                    "cle": chiffres.cle_en_texte(procede, cle),
                    "longueur_cle": len(cle) if isinstance(cle, str) and procede != "substitution" else None,
                    "clair": clair,
                    "chiffre": chiffre,
                    "langue": "en" if variante == "anglais" else "fr",
                })
    return corpus


def ecrire_jsonl(lignes: list[dict], chemin: Path) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        for l in lignes:
            f.write(json.dumps(l, ensure_ascii=False, sort_keys=True) + "\n")


def lire_jsonl(chemin: Path) -> list[dict]:
    with open(chemin, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]
