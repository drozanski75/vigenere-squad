"""Télécharge les modèles déclarés (ollama pull) et inscrit leur digest dans
config/experiment.yaml (étiquette + empreinte exactes du modèle utilisé)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "src"))

from vigenere_squad.evaluation.executer import charger_config  # noqa: E402
from vigenere_squad.llm import OllamaLLM  # noqa: E402

if __name__ == "__main__":
    seulement_ci = "--ci" in sys.argv
    cfg = charger_config()
    modeles = [cfg["ci"]["modele"]] if seulement_ci else (
        [c["modele"] for c in cfg["configurations"].values() if c["type"] == "agents"] + [cfg["ci"]["modele"]])
    chemin = RACINE / "config" / "experiment.yaml"
    texte = chemin.read_text(encoding="utf-8")
    for m in modeles:
        client = OllamaLLM(m, hote=cfg["environnement_execution"]["hote"])
        client.telecharger()
        digest = client.digest()
        print(f"{m} -> {digest}")
        if seulement_ci:
            continue
        # Remplace la ligne digest qui suit la ligne `modele: "<m>"`
        motif = re.compile(rf'(modele: "{re.escape(m)}"\n(?:\s+\w+:.*\n)*?\s+digest: )"[^"]*"')
        texte, n = motif.subn(rf'\1"{digest}"', texte)
        if n == 0:
            print(f"  (ligne digest introuvable pour {m})")
    if not seulement_ci:
        chemin.write_text(texte, encoding="utf-8", newline="\n")
