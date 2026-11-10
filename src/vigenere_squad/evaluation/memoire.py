"""Mesure de la mémoire par chiffré, portable (Windows, macOS, Linux) :
pic de mémoire résidente du processus Python et des processus Ollama locaux,
échantillonné toutes les 0,2 s pendant le cassage d'un chiffré."""

from __future__ import annotations

import threading

import psutil

MO = 2**20


def _rss_ollama() -> int:
    total = 0
    for p in psutil.process_iter(["name"]):
        try:
            if "ollama" in (p.info["name"] or "").lower():
                total += p.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return total


def _taille_modeles_api(hote: str) -> float | None:
    import json
    import urllib.request

    try:
        with urllib.request.urlopen(hote + "/api/ps", timeout=3) as r:  # noqa: S310
            return round(sum(m.get("size", 0) for m in json.loads(r.read()).get("models", [])) / MO, 1)
    except Exception:  # noqa: BLE001
        return None


class PicMemoire:
    """Gestionnaire de contexte : ``with PicMemoire() as pm: ...`` puis ``pm.resultat()``."""

    def __init__(self, periode_s: float = 0.2, ollama: bool = True, hote: str | None = None):
        self.periode = periode_s
        self.hote = hote
        self.ollama = ollama
        self._proc = psutil.Process()
        self._stop = threading.Event()
        self.pic_python = 0
        self.pic_ollama = 0

    def _mesurer(self) -> None:
        self.pic_python = max(self.pic_python, self._proc.memory_info().rss)
        if self.ollama:
            self.pic_ollama = max(self.pic_ollama, _rss_ollama())

    def _boucle(self) -> None:
        while not self._stop.wait(self.periode):
            self._mesurer()

    def __enter__(self) -> "PicMemoire":
        self._mesurer()
        self._fil = threading.Thread(target=self._boucle, daemon=True)
        self._fil.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        self._fil.join(timeout=2)
        self._mesurer()

    def resultat(self) -> dict:
        ollama = round(self.pic_ollama / MO, 1) if self.ollama else None
        if self.ollama and not self.pic_ollama and self.hote:
            ollama = _taille_modeles_api(self.hote)  # Ollama dans un autre conteneur : taille déclarée par l'API
        return {"rss_python_mo": round(self.pic_python / MO, 1), "rss_ollama_mo": ollama}


def memoire_totale_go() -> float:
    return round(psutil.virtual_memory().total / 2**30, 1)


def rss_python_mo() -> float:
    return round(psutil.Process().memory_info().rss / MO, 1)
