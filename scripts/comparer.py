"""Compare les métriques reproduites (results/metrics.json) aux métriques
publiées (results/publie/metrics.json, ou la version du tag v1.0.0 dans git).

Tolérances (voir AUDIT.md) :
* parties déterministes (référence a_baseline, Shannon, Kasiski) : égalité exacte ;
* parties dépendant du modèle : |reproduit - publié| <= 2 x max(σ publié, σ reproduit),
  avec un plancher de 3 points de pourcentage (σ peut être nul sur 3 répétitions).
Code de sortie 0 si tout est conforme.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
PLANCHER = 3.0


def charger_publie() -> dict:
    p = RACINE / "results" / "publie" / "metrics.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    sortie = subprocess.run(["git", "-C", str(RACINE), "show", "v1.0.0:results/metrics.json"],
                            capture_output=True, text=True, check=True)
    return json.loads(sortie.stdout)


def deterministe(config: str) -> bool:
    return config == "a_baseline"


def comparer(pub: dict, rep: dict) -> list[tuple[str, str, str, str]]:
    lignes = []
    for exp, confs in pub["experiences"].items():
        for conf, v in confs.items():
            r = rep["experiences"].get(exp, {}).get(conf)
            cle = f"{exp}/{conf}/taux_exact"
            if r is None:
                lignes.append((cle, "ABSENT", str(v["taux_exact"]["moyenne"]), "-"))
                continue
            a, b = v["taux_exact"], r["taux_exact"]
            if deterministe(conf):
                ok = a["moyenne"] == b["moyenne"]
                tol = "exacte"
            else:
                t = max(PLANCHER, 2 * max(a["ecart_type"], b["ecart_type"]))
                ok = abs(a["moyenne"] - b["moyenne"]) <= t
                tol = f"±{t:.1f}"
            lignes.append((cle, "OK" if ok else "ÉCART", f"{a['moyenne']} → {b['moyenne']}", tol))
            if deterministe(conf):
                for p, tr in v["par_procede_tranche"].items():
                    for t, x in tr.items():
                        y = r["par_procede_tranche"].get(p, {}).get(t, {}).get("moyenne")
                        if x["moyenne"] != y:
                            lignes.append((f"{cle}/{p}/{t}", "ÉCART", f"{x['moyenne']} → {y}", "exacte"))
    for bloc in ("shannon", "kasiski_autoclave", "longueur_min"):
        ok = pub.get(bloc) == rep.get(bloc)
        lignes.append((bloc, "OK" if ok else "ÉCART", "identique" if ok else "différent", "exacte"))
    return lignes


if __name__ == "__main__":
    pub = charger_publie()
    rep = json.loads((RACINE / "results" / "metrics.json").read_text(encoding="utf-8"))
    lignes = comparer(pub, rep)
    largeur = max(len(l[0]) for l in lignes)
    for cle, verdict, valeurs, tol in lignes:
        print(f"{cle:<{largeur}}  {verdict:<6} {valeurs:<22} tolérance {tol}")
    ecarts = sum(1 for l in lignes if l[1] != "OK")
    conclusion = "reproductible" if ecarts == 0 else (
        "partiellement reproductible" if ecarts < len(lignes) / 2 else "non reproductible")
    print(f"\n{ecarts} écart(s) sur {len(lignes)} contrôles -> {conclusion}")
    sys.exit(0 if ecarts == 0 else 1)
