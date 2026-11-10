"""Rend docs/rapport.md -> docs/rapport_rendu.md en remplaçant les balises
{{nom}} par des valeurs et tableaux calculés depuis results/metrics.json, et
met à jour les blocs « Résultats principaux » du README et de SYSTEM_CARD.

Aucune valeur n'est saisie à la main : tout provient de metrics.json.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
ORDRE = ["080-119", "120-249", "250-499", "500-899", "900-1499", "1500+"]
PROCEDES = ["cesar", "affine", "vigenere", "autoclave", "substitution", "beaufort"]


def mv(v, unite="") -> str:
    if not v or v.get("moyenne") is None:
        return "–"
    if not v.get("ecart_type"):
        return f"{v['moyenne']:.1f}{unite}"
    return f"{v['moyenne']:.1f} ± {v['ecart_type']:.1f}{unite}"


def memo(d: dict) -> str:
    py = (d.get("memoire_python_mo") or {}).get("moyenne")
    ol = (d.get("memoire_ollama_mo") or {}).get("moyenne")
    return "–" if py is None else (f"{py:.0f} + {ol:.0f}" if ol else f"{py:.0f}")


def table(entetes, lignes) -> str:
    out = ["| " + " | ".join(entetes) + " |", "|" + "|".join("---" for _ in entetes) + "|"]
    out += ["| " + " | ".join(str(c) for c in l) + " |" for l in lignes]
    return "\n".join(out)


def valeurs(m: dict) -> dict:
    v: dict = {}
    exp = m["experiences"]
    p = exp.get("principal", {})
    agents = sorted(c for c in p if c != "a_baseline")
    base = p.get("a_baseline")
    v["n_corpus"] = base["n_chiffres"] if base else "–"
    v["n_agents"] = p[agents[0]]["n_chiffres"] if agents else "–"
    v["TABLE_ablation"] = table(
        ["configuration", "chiffrés", "clair exact (%)", "réf. (a) même sous-ensemble (%)", "procédé correct (%)",
         "lettres justes (%)", "itérations", "durée (s)", "mémoire (Mo)", "replis (%)", "appels refusés"],
        [[c, d["n_chiffres"], mv(d["taux_exact"]),
          mv(d.get("comparaison_reference", {}).get("reference_sur_sous_ensemble")) if c != "a_baseline" else "–",
          mv(d["taux_procede_correct"]), mv(d["precision_lettres"]), mv(d["iterations_moyennes"]),
          mv(d["duree_moyenne_s"]), memo(d), mv(d["taux_repli"]), d["appels_refuses_total"]]
         for c, d in sorted(p.items())])
    for c, d in p.items():
        v[f"TABLE_tranches_{c}"] = table(
            ["procédé"] + ORDRE + ["longueur min. 90 %"],
            [[pr] + [mv(d["par_procede_tranche"].get(pr, {}).get(t)) for t in ORDRE]
             + [d["longueur_min_90"].get(pr) or "non atteinte"] for pr in PROCEDES if pr in d["par_procede"]])
    blocs = [f"### Configuration {c}\n\n{v[f'TABLE_tranches_{c}']}" for c in sorted(p)]
    v["TABLES_tranches"] = "\n\n".join(blocs)
    # Apport mesuré des agents (sur le même sous-ensemble)
    phrases = []
    for c in agents:
        d = p[c]
        ref = d.get("comparaison_reference", {}).get("reference_sur_sous_ensemble", {})
        if ref.get("moyenne") is None:
            continue
        delta = d["taux_exact"]["moyenne"] - ref["moyenne"]
        cout = d["duree_moyenne_s"]["moyenne"] / max(base["duree_moyenne_s"]["moyenne"], 1e-6) if base else None
        phrases.append(
            f"- **{c}** : {d['taux_exact']['moyenne']:.1f} % de clairs exacts contre {ref['moyenne']:.1f} % pour la "
            f"référence (a) sur les mêmes {d['n_chiffres']} chiffrés, soit un écart de **{delta:+.1f} points** ; "
            f"{d['iterations_moyennes']['moyenne']:.2f} itérations en moyenne contre "
            f"{base['iterations_moyennes']['moyenne']:.2f} ; durée multipliée par {cout:.0f} ; "
            f"replis déterministes dans {d['taux_repli']['moyenne']:.1f} % des exécutions.")
    v["apport_agents"] = "\n".join(phrases) or "*(configurations à agents non encore exécutées)*"
    # Shannon
    s = m.get("shannon", {})
    if s:
        v["redondance_estimee"] = s["redondance_estimee_bits"]
        v["entropie_estimee"] = s["entropie_estimee_bits"]
        v["redondance_litt"] = s["redondance_litterature_bits"]
        v["TABLE_shannon"] = table(
            ["longueur de clé", "min. 90 % (longueur inconnue)", "min. 90 % (longueur connue)",
             "U (D estimée)", "U (D = 3,4 bits)"],
            [[L, d["longueur_min_90"], d["longueur_min_90_longueur_connue"], d["distance_unicite_estimee"],
              d["distance_unicite_litterature"]] for L, d in sorted(s["par_longueur_cle"].items(),
                                                                     key=lambda kv: int(kv[0]))])
        rapports = [d["longueur_min_90_longueur_connue"] / d["distance_unicite_estimee"]
                    for d in s["par_longueur_cle"].values() if d["longueur_min_90_longueur_connue"]]
        v["rapport_shannon"] = f"{min(rapports):.1f} à {max(rapports):.1f}" if rapports else "–"
    lm = m.get("longueur_min", {})
    v["TABLE_longueur_min"] = table(
        ["procédé", "min. 90 % — procédé connu (lettres)", "min. 90 % — référence (a), procédé inconnu (lettres)"],
        [[p_, d["longueur_min_90_procede_connu"] or "> max", d["longueur_min_90_reference"] or "> max"]
         for p_, d in lm.items()]) if lm else "*(non exécuté)*"
    k = m.get("kasiski_autoclave", {})
    if k:
        v["TABLE_kasiski"] = table(
            ["procédé", "bonne longueur en tête (%)", "dans le top 3 (%)", "répétitions de trigrammes",
             "IC global", "IC moyen des colonnes à la vraie longueur"],
            [[p_, d["kasiski_tete_correcte_pct"], d["kasiski_top3_pct"], d["repetitions_moyennes"], d["ic_moyen"],
              d["ic_colonnes_vraie_longueur_moyen"]] for p_, d in k.items()])
    rob = {e: d for e, d in exp.items() if e.startswith("robustesse") or e in ("defaillances", "injection")}
    v["TABLE_robustesse"] = table(
        ["expérience", "configuration", "chiffrés", "clair exact (%)", "lettres justes (%)", "replis (%)",
         "erreurs LLM", "garde-fous"],
        [[e, c, d["n_chiffres"], mv(d["taux_exact"]), mv(d["precision_lettres"]), mv(d["taux_repli"]),
          d["erreurs_llm_total"], d["garde_fou_total"]] for e, ds in sorted(rob.items()) for c, d in sorted(ds.items())]
    ) if rob else "*(non exécuté)*"
    ex = m.get("explications", {})
    v["explications"] = "```json\n" + json.dumps(ex, indent=2, ensure_ascii=False) + "\n```" if ex else "*(non exécuté)*"
    env = json.loads((RACINE / "results" / "ENVIRONMENT.json").read_text(encoding="utf-8")) if (
        RACINE / "results" / "ENVIRONMENT.json").exists() else {}
    exe = json.loads((RACINE / "results" / "EXECUTION.json").read_text(encoding="utf-8")) if (
        RACINE / "results" / "EXECUTION.json").exists() else {}
    v["materiel"] = (f"{env.get('processeur')} ({env.get('coeurs')} cœurs), {env.get('memoire_totale_go')} Go, "
                     f"{env.get('plateforme')}") if env else "–"
    v["ollama"] = env.get("ollama_version") or "–"
    v["modeles_digests"] = ", ".join(f"`{n}` `{(d.get('digest') or '')[:12]}`"
                                     for n, d in (env.get("modeles") or {}).items()) or "–"
    v["duree_totale"] = exe.get("duree_totale_min", "–")
    v["memoire"] = (f"{exe.get('rss_max_python_mo')} Mo (Python) + modèles "
                    f"{exe.get('memoire_modeles_ollama_mo')}") if exe else "–"
    v["resume_cles"] = table(["clé (metrics.json → resume)", "valeur"],
                             [[f"`{k}`", val] for k, val in m.get("resume", {}).items()])
    return v


def rendre(gabarit: str, v: dict) -> str:
    return re.sub(r"\{\{(\w+)\}\}", lambda mo: str(v.get(mo.group(1), f"[{mo.group(1)} : non disponible]")), gabarit)


def bloc_resultats(v: dict) -> str:
    return (f"{v['apport_agents']}\n\nValeurs clés (`results/metrics.json`, bloc `resume`) :\n\n{v['resume_cles']}\n")


def maj_bloc(chemin: Path, contenu: str) -> None:
    t = chemin.read_text(encoding="utf-8")
    t = re.sub(r"(<!-- RESULTATS:DEBUT -->\n).*?(\n<!-- RESULTATS:FIN -->)",
               lambda mo: mo.group(1) + contenu + mo.group(2), t, flags=re.S)
    chemin.write_text(t, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    m = json.loads((RACINE / "results" / "metrics.json").read_text(encoding="utf-8"))
    v = valeurs(m)
    gabarit = (RACINE / "docs" / "rapport.md").read_text(encoding="utf-8")
    (RACINE / "docs" / "rapport_rendu.md").write_text(rendre(gabarit, v), encoding="utf-8", newline="\n")
    for f in ("README.md", "SYSTEM_CARD.md"):
        maj_bloc(RACINE / f, bloc_resultats(v))
    print("docs/rapport_rendu.md écrit ; blocs de résultats du README et de SYSTEM_CARD mis à jour")
