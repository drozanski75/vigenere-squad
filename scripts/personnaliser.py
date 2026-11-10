"""Remplace les marqueurs <COMPTE> (et optionnellement <ID>, ORCID) dans la documentation.

Usage : python scripts/personnaliser.py --compte mon-compte-github [--orcid 0000-0000-0000-0000] [--zenodo 1234567]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
FICHIERS = ["README.md", "CITATION.cff", "AUDIT.md", "docs/publication.yaml", "SYSTEM_CARD.md"]

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--compte", required=True)
    p.add_argument("--orcid")
    p.add_argument("--zenodo", help="identifiant numérique de l'enregistrement Zenodo (après publication)")
    a = p.parse_args()
    for f in FICHIERS:
        chemin = R / f
        t = chemin.read_text(encoding="utf-8").replace("<COMPTE>", a.compte)
        if a.zenodo:
            t = t.replace("<ID>", a.zenodo)
        if a.orcid and f == "CITATION.cff":
            t = t.replace('    # orcid: "https://orcid.org/0000-0000-0000-0000"', f'    orcid: "https://orcid.org/{a.orcid}"')
        if a.orcid and f == "docs/publication.yaml":
            t = t.replace('orcid: ""', f'orcid: "{a.orcid}"')
        chemin.write_text(t, encoding="utf-8", newline="\n")
    if a.orcid:
        z = json.loads((R / ".zenodo.json").read_text(encoding="utf-8"))
        z["creators"][0]["orcid"] = a.orcid
        (R / ".zenodo.json").write_text(json.dumps(z, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("marqueurs remplacés dans :", ", ".join(FICHIERS))
