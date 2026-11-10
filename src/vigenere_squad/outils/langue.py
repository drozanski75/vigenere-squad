"""Modèle de langue par quadrigrammes (log-probabilités) appris sur un corpus
du domaine public. Sert au score de plausibilité du Linguiste et de fonction
objectif pour les attaques par recuit / escalade."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from .texte import N, lettres

RACINE = Path(__file__).resolve().parents[3]
DOSSIER_MODELES = RACINE / "data" / "models"
TAILLE = N**4


def indices_quadgrammes(t: np.ndarray) -> np.ndarray:
    return ((t[:-3] * N + t[1:-2]) * N + t[2:-1]) * N + t[3:]


def en_tableau(texte: str) -> np.ndarray:
    b = np.frombuffer(lettres(texte).encode("ascii"), dtype=np.uint8)
    return (b - 65).astype(np.int64)


@dataclass
class ModeleLangue:
    langue: str
    logp: np.ndarray  # log10 P(quadgramme), taille 26^4
    freq: list[float]  # fréquences unigrammes
    meta: dict = field(default_factory=dict)

    # --- construction --------------------------------------------------------
    @classmethod
    def apprendre(cls, textes: list[str], langue: str) -> "ModeleLangue":
        comptes = np.zeros(TAILLE, dtype=np.float64)
        uni = np.zeros(N, dtype=np.float64)
        for texte in textes:
            t = en_tableau(texte)
            if len(t) >= 4:
                comptes += np.bincount(indices_quadgrammes(t), minlength=TAILLE)
            uni += np.bincount(t, minlength=N)
        total = comptes.sum()
        plancher = np.log10(0.01 / total)
        logp = np.where(comptes > 0, np.log10(np.maximum(comptes, 1) / total), plancher)
        freq = (uni / uni.sum()).tolist()
        # Entropie conditionnelle H(X4 | X1X2X3) estimée (bits/lettre), utile
        # pour la redondance D = log2(26) - H dans la distance d'unicité.
        c3 = comptes.reshape(N**3, N)
        tot3 = c3.sum(axis=1, keepdims=True)
        with np.errstate(divide="ignore", invalid="ignore"):
            p_cond = np.where(tot3 > 0, c3 / tot3, 0)
            h_cond = -np.nansum(c3 / total * np.where(p_cond > 0, np.log2(p_cond), 0))
        p1 = uni / uni.sum()
        h1 = float(-(p1[p1 > 0] * np.log2(p1[p1 > 0])).sum())
        meta = {
            "langue": langue,
            "n_quadgrammes": int(total),
            "plancher_log10": float(plancher),
            "entropie_unigramme_bits": round(h1, 4),
            "entropie_quadgramme_cond_bits": round(float(h_cond), 4),
        }
        return cls(langue=langue, logp=logp.astype(np.float32), freq=freq, meta=meta)

    def calibrer(self, textes_validation: list[str], graine: int = 0, taille: int = 400) -> None:
        """Mesure le score moyen d'un texte de la langue et d'un texte aléatoire
        pour définir un score normalisé (0 = aléatoire, 1 = langue typique)."""
        rng = np.random.default_rng(graine)
        langue_scores, alea_scores = [], []
        for texte in textes_validation:
            t = en_tableau(texte)
            for debut in range(0, max(1, len(t) - taille), max(taille, len(t) // 20)):
                bloc = t[debut : debut + taille]
                if len(bloc) >= taille:
                    langue_scores.append(self.score_tableau(bloc))
        for _ in range(50):
            alea_scores.append(self.score_tableau(rng.integers(0, N, taille)))
        self.meta["score_moyen_langue"] = float(np.mean(langue_scores))
        self.meta["score_moyen_aleatoire"] = float(np.mean(alea_scores))
        self.meta["ecart_type_langue"] = float(np.std(langue_scores))

    # --- score -----------------------------------------------------------------
    def score_tableau(self, t: np.ndarray) -> float:
        if len(t) < 4:
            return float(self.meta.get("plancher_log10", -10.0))
        return float(self.logp[indices_quadgrammes(t)].mean())

    def score(self, texte: str) -> float:
        return self.score_tableau(en_tableau(texte))

    def score_normalise(self, texte: str) -> float:
        s = self.score(texte)
        lo = self.meta["score_moyen_aleatoire"]
        hi = self.meta["score_moyen_langue"]
        return (s - lo) / (hi - lo)

    # --- persistance -------------------------------------------------------------
    def sauver(self, dossier: Path = DOSSIER_MODELES) -> None:
        dossier.mkdir(parents=True, exist_ok=True)
        np.save(dossier / f"quadgrammes_{self.langue}.npy", self.logp)
        (dossier / f"langue_{self.langue}.json").write_text(
            json.dumps({"freq": self.freq, "meta": self.meta}, indent=2, ensure_ascii=False),
            encoding="utf-8", newline="\n",
        )

    @classmethod
    def charger(cls, langue: str, dossier: Path = DOSSIER_MODELES) -> "ModeleLangue":
        logp = np.load(dossier / f"quadgrammes_{langue}.npy")
        d = json.loads((dossier / f"langue_{langue}.json").read_text(encoding="utf-8"))
        return cls(langue=langue, logp=logp, freq=d["freq"], meta=d["meta"])


@lru_cache(maxsize=4)
def modele(langue: str = "fr") -> ModeleLangue:
    """Modèle chargé une seule fois (le construire avec ``make data``)."""
    chemin = DOSSIER_MODELES / f"quadgrammes_{langue}.npy"
    if not chemin.exists():
        # Construction automatique (déterministe, quelques secondes) à partir des
        # textes sources épinglés : aucune étape manuelle n'est nécessaire.
        import sys

        from ..evaluation.donnees import construire_modeles, telecharger_et_verifier

        print("Premier lancement : construction des modèles de langue (quelques secondes)...",
              file=sys.stderr, flush=True)
        telecharger_et_verifier()
        construire_modeles()
        if not chemin.exists():
            raise FileNotFoundError(f"Modèle de langue absent ({chemin}) : lancer `uv run vsquad donnees`")
    return ModeleLangue.charger(langue)
