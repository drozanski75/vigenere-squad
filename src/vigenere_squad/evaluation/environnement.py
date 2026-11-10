"""Capture automatique de l'environnement d'exécution (results/ENVIRONMENT.json)."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import urllib.request
from importlib import metadata

from .executer import RACINE, RESULTS, charger_config


def _cmd(*args) -> str | None:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=10, check=False).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _memoire_go() -> float | None:
    from .memoire import memoire_totale_go

    return memoire_totale_go()


def _ollama(hote: str) -> dict:
    out: dict = {}
    try:
        with urllib.request.urlopen(hote + "/api/version", timeout=5) as r:  # noqa: S310
            out["version"] = json.loads(r.read()).get("version")
        with urllib.request.urlopen(hote + "/api/tags", timeout=5) as r:  # noqa: S310
            out["modeles"] = {m["name"]: {"digest": m.get("digest"), "taille_octets": m.get("size"),
                                          "quantification": m.get("details", {}).get("quantization_level")}
                              for m in json.loads(r.read()).get("models", [])}
    except Exception:  # noqa: BLE001
        out["version"] = None
    return out


def capturer(mode: str = "complet") -> dict:
    cfg = charger_config()
    ol = _ollama(cfg["environnement_execution"]["hote"])
    deps = {}
    for p in ("numpy", "pydantic", "pyyaml", "matplotlib", "py-minisign", "psutil", "pytest"):
        try:
            deps[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            deps[p] = None
    env = {
        "mode": mode,
        "python": sys.version.split()[0],
        "plateforme": platform.platform(),
        "processeur": platform.processor() or platform.machine(),
        "coeurs": os.cpu_count(),
        "memoire_totale_go": _memoire_go(),
        "ollama_version": ol.get("version"),
        "modeles": ol.get("modeles", {}),
        "modeles_declares": {k: {"modele": v.get("modele"), "digest": v.get("digest")}
                             for k, v in cfg["configurations"].items() if v["type"] == "agents"},
        "dependances": deps,
        "commit": _cmd("git", "-C", str(RACINE), "rev-parse", "HEAD"),
        "graine": cfg["graine"],
        "repetitions": cfg["repetitions"],
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "ENVIRONMENT.json").write_text(json.dumps(env, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    return env


def verifier_digests(cfg: dict | None = None, strict: bool = False) -> list[str]:
    """Compare les empreintes déclarées dans experiment.yaml et installées."""
    cfg = cfg or charger_config()
    installes = _ollama(cfg["environnement_execution"]["hote"]).get("modeles", {})
    alertes = []
    for nom, c in cfg["configurations"].items():
        if c["type"] != "agents":
            continue
        reel = installes.get(c["modele"], {}).get("digest")
        if reel is None:
            alertes.append(f"{nom} : modèle {c['modele']} non installé (ollama pull {c['modele']})")
        elif c.get("digest") not in (reel, "A_RENSEIGNER"):
            alertes.append(f"{nom} : digest installé {reel[:12]} ≠ déclaré {str(c['digest'])[:12]}")
    if strict and alertes:
        raise SystemExit("\n".join(alertes))
    return alertes
