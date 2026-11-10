"""Journal JSONL horodaté : chaque message, appel d'outil, argument et résultat."""

from __future__ import annotations

import json
import time
from pathlib import Path


def _compact(valeur, limite: int = 600):
    """Tronque les chaînes longues pour garder des traces lisibles."""
    if isinstance(valeur, str):
        return valeur if len(valeur) <= limite else valeur[:limite] + f"…(+{len(valeur) - limite})"
    if isinstance(valeur, dict):
        return {k: _compact(v, limite) for k, v in valeur.items()}
    if isinstance(valeur, list):
        return [_compact(v, limite) for v in valeur[:60]]
    return valeur


class Journal:
    def __init__(self, chemin: Path | None, run_id: str, limite: int = 2000, ecouteur=None):
        self.chemin = chemin
        self.run_id = run_id
        self.limite = limite
        self.evenements: list[dict] = []
        self.ecouteur = ecouteur  # rappel optionnel (démonstrateur en direct)
        self._t0 = time.perf_counter()
        if chemin:
            chemin.parent.mkdir(parents=True, exist_ok=True)
            chemin.write_text("", encoding="utf-8", newline="\n")

    def ecrire(self, type_: str, agent: str | None = None, **donnees) -> dict:
        ev = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "t_rel_s": round(time.perf_counter() - self._t0, 3),
            "run_id": self.run_id,
            "type": type_,
            "agent": agent,
            **_compact(donnees, self.limite),
        }
        self.evenements.append(ev)
        if self.ecouteur:
            self.ecouteur(ev)
        if self.chemin:
            with open(self.chemin, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        return ev

    def compter(self, type_: str) -> int:
        return sum(1 for e in self.evenements if e["type"] == type_)


def lire(chemin: Path) -> list[dict]:
    return [json.loads(l) for l in chemin.read_text(encoding="utf-8").splitlines() if l.strip()]
