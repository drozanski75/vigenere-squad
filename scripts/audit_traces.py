"""Contrôle d'audit automatique sur un échantillon de traces :
1. tout appel d'outil exécuté appartient à la liste fermée de l'agent ;
2. la décision finale de chaque trace correspond à la ligne de results/raw ;
3. chaque ligne de results/raw a sa trace.

Usage : python scripts/audit_traces.py [--echantillon 50] [--graine 0]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "src"))

from vigenere_squad.agents.definitions import OUTILS_PAR_AGENT  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--echantillon", type=int, default=50)
    p.add_argument("--graine", type=int, default=0)
    p.add_argument("--racine", type=Path, default=RACINE)
    a = p.parse_args()
    raw = sorted((a.racine / "results" / "raw").glob("*/*_rep*.jsonl"))
    lignes = [(f, json.loads(l)) for f in raw for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lignes:
        print("aucun résultat brut")
        return 1
    rng = random.Random(a.graine)
    tirage = rng.sample(lignes, min(a.echantillon, len(lignes)))
    problemes, appels, refuses, sans_trace = [], 0, 0, 0
    for f, l in tirage:
        exp = f.parent.name
        trace = a.racine / "traces" / exp / l["configuration"] / f"rep{l['repetition']}" / f"{l['id']}.jsonl"
        if not trace.exists():
            sans_trace += 1
            problemes.append(f"trace absente : {trace.relative_to(a.racine)}")
            continue
        evs = [json.loads(x) for x in trace.read_text(encoding="utf-8").splitlines() if x.strip()]
        for ev in evs:
            if ev["type"] == "appel_outil":
                appels += 1
                if ev["outil"] not in OUTILS_PAR_AGENT.get(ev["agent"], ()):
                    problemes.append(f"{trace.name} : {ev['agent']} a exécuté {ev['outil']} hors liste")
            elif ev["type"] == "appel_refuse":
                refuses += 1
        fin = next((ev for ev in reversed(evs) if ev["type"] == "fin"), None)
        if fin is None or fin.get("procede") != l["procede_trouve"] or fin.get("cle") != l["cle_trouvee"]:
            problemes.append(f"{trace.name} : décision finale ≠ résultat brut")
    print(f"{len(tirage)} exécutions contrôlées, {appels} appels d'outils exécutés, {refuses} appels refusés "
          f"(hors liste, bloqués avant exécution), {sans_trace} trace(s) absente(s)")
    for pb in problemes:
        print("  PROBLÈME", pb)
    print("CONFORME" if not problemes else f"{len(problemes)} problème(s)")
    return 0 if not problemes else 1


if __name__ == "__main__":
    raise SystemExit(main())
