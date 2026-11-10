"""Agrégation des résultats bruts en results/metrics.json.

Conventions : pour toute mesure répétée, on rapporte {"moyenne", "ecart_type",
"n_repetitions", "valeurs"} ; les taux sont exprimés en pourcentage.
"""

from __future__ import annotations

import csv
import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path

from ..outils.langue import modele
from .donnees import tranche
from .executer import RESULTS, charger_config

ORDRE_TRANCHES = ["080-119", "120-249", "250-499", "500-899", "900-1499", "1500+"]
PROCEDES = ["cesar", "affine", "vigenere", "autoclave", "substitution", "beaufort"]


def _lire(chemin: Path) -> list[dict]:
    return [json.loads(l) for l in chemin.read_text(encoding="utf-8").splitlines() if l.strip()]


def resume(valeurs: list[float], chiffres: int = 2) -> dict:
    v = [float(x) for x in valeurs]
    return {
        "moyenne": round(st.mean(v), chiffres) if v else None,
        "ecart_type": round(st.stdev(v), chiffres) if len(v) > 1 else 0.0,
        "n_repetitions": len(v),
        "valeurs": [round(x, chiffres) for x in v],
    }


def _par_rep(lignes: list[dict], f) -> list[float]:
    reps = defaultdict(list)
    for l in lignes:
        reps[l["repetition"]].append(l)
    return [f(v) for _, v in sorted(reps.items())]


def taux(cle: str):
    return lambda ls: 100.0 * sum(bool(l[cle]) for l in ls) / len(ls) if ls else 0.0


def moyenne(cle: str):
    return lambda ls: st.mean(float(l[cle] or 0) for l in ls) if ls else 0.0


def longueur_min_90(par_tranche: dict) -> str | None:
    """Plus petite tranche à partir de laquelle le taux moyen reste >= 90 %."""
    retenue = None
    for t in reversed(ORDRE_TRANCHES):
        v = par_tranche.get(t)
        if v is None or v["moyenne"] is None:
            continue
        if v["moyenne"] >= 90:
            retenue = t
        else:
            break
    return retenue


def agreger_lot(lignes: list[dict]) -> dict:
    out = {
        "n_chiffres": len({l["id"] for l in lignes}),
        "taux_exact": resume(_par_rep(lignes, taux("succes_exact"))),
        "taux_procede_correct": resume(_par_rep(lignes, taux("procede_correct"))),
        "precision_lettres": resume(_par_rep(lignes, lambda ls: 100 * st.mean(l["precision_lettres"] for l in ls))),
        "iterations_moyennes": resume(_par_rep(lignes, moyenne("iterations"))),
        "duree_moyenne_s": resume(_par_rep(lignes, moyenne("duree_s")), 3),
        "memoire_python_mo": resume(_par_rep(lignes, lambda ls: st.mean(l.get("rss_python_mo") or 0 for l in ls)), 1),
        "memoire_ollama_mo": resume(_par_rep(lignes, lambda ls: st.mean(l.get("rss_ollama_mo") or 0 for l in ls)), 1),
        "memoire_pic_totale_mo": max((l.get("rss_python_mo") or 0) + (l.get("rss_ollama_mo") or 0) for l in lignes),
        "taux_repli": resume(_par_rep(lignes, lambda ls: 100 * sum(bool(l["replis"]) for l in ls) / len(ls))),
        "appels_refuses_total": sum(l["compteurs"].get("appels_refuses", 0) for l in lignes),
        "appels_outils_moyens": resume(_par_rep(
            lignes, lambda ls: st.mean(l["compteurs"].get("appels_outils", 0) for l in ls))),
        "erreurs_llm_total": sum(l["compteurs"].get("erreurs_llm", 0) for l in lignes),
        "garde_fou_total": sum(l["compteurs"].get("garde_fou_declenche", 0) for l in lignes),
        "contexte_sature_total": sum(l["compteurs"].get("contexte_sature", 0) for l in lignes),
        "statuts": {s: sum(1 for l in lignes if l["statut"] == s) for s in {l["statut"] for l in lignes}},
        "par_procede": {}, "par_tranche": {}, "par_procede_tranche": {}, "longueur_min_90": {},
    }
    for p in PROCEDES:
        lp = [l for l in lignes if l["procede"] == p]
        if not lp:
            continue
        out["par_procede"][p] = resume(_par_rep(lp, taux("succes_exact")))
        out["par_procede_tranche"][p] = {}
        for t in ORDRE_TRANCHES:
            lt = [l for l in lp if l["tranche"] == t]
            if lt:
                out["par_procede_tranche"][p][t] = resume(_par_rep(lt, taux("succes_exact")))
        out["longueur_min_90"][p] = longueur_min_90(out["par_procede_tranche"][p])
    for t in ORDRE_TRANCHES:
        lt = [l for l in lignes if l["tranche"] == t]
        if lt:
            out["par_tranche"][t] = resume(_par_rep(lt, taux("succes_exact")))
    return out


def comparaison_appariee(lignes_a: list[dict], lignes_b: list[dict]) -> dict:
    """Compare deux configurations sur les mêmes chiffrés (sous-ensemble commun)."""
    ids = {l["id"] for l in lignes_b}
    a = [l for l in lignes_a if l["id"] in ids]
    return {"n_chiffres_communs": len(ids), "reference_sur_sous_ensemble": agreger_lot(a)["taux_exact"]}


def agreger_shannon(cfg: dict) -> dict:
    chemin = RESULTS / "raw" / "shannon" / "vigenere.jsonl"
    if not chemin.exists():
        return {}
    lignes = _lire(chemin)
    m = modele("fr").meta
    h = m["entropie_quadgramme_cond_bits"]
    redondance = math.log2(26) - h
    redondance_litt = math.log2(26) - 1.3  # entropie du français ≈ 1,3 bit/lettre (ordre de grandeur classique)
    out = {"redondance_estimee_bits": round(redondance, 3), "entropie_estimee_bits": h,
           "redondance_litterature_bits": round(redondance_litt, 3), "par_longueur_cle": {}}
    for L in sorted({l["longueur_cle"] for l in lignes}):
        lL = [l for l in lignes if l["longueur_cle"] == L]
        courbe, courbe_oracle = {}, {}
        for n in sorted({l["longueur_texte"] for l in lL}):
            ln = [l for l in lL if l["longueur_texte"] == n]
            courbe[n] = round(100 * sum(l["succes"] for l in ln) / len(ln), 1)
            courbe_oracle[n] = round(100 * sum(l["succes_longueur_connue"] for l in ln) / len(ln), 1)
        lmin = next((n for n in sorted(courbe) if all(courbe[k] >= 90 for k in courbe if k >= n)), None)
        lmin_o = next((n for n in sorted(courbe_oracle) if all(courbe_oracle[k] >= 90 for k in courbe_oracle
                                                               if k >= n)), None)
        hk = L * math.log2(26)
        out["par_longueur_cle"][str(L)] = {
            "taux_par_longueur_texte": courbe,
            "taux_longueur_connue": courbe_oracle,
            "longueur_min_90": lmin,
            "longueur_min_90_longueur_connue": lmin_o,
            "distance_unicite_estimee": round(hk / redondance, 1),
            "distance_unicite_litterature": round(hk / redondance_litt, 1),
        }
    return out


def _min_90(courbe: dict) -> int | None:
    return next((n for n in sorted(courbe) if all(courbe[k] >= 90 for k in courbe if k >= n)), None)


def agreger_longueur_min() -> dict:
    chemin = RESULTS / "raw" / "longueur_min" / "procedes.jsonl"
    if not chemin.exists():
        return {}
    lignes = _lire(chemin)
    out = {}
    for p in PROCEDES:
        lp = [l for l in lignes if l["procede"] == p]
        if not lp:
            continue
        connu, ref = {}, {}
        for n in sorted({l["longueur_texte"] for l in lp}):
            ln = [l for l in lp if l["longueur_texte"] == n]
            connu[n] = round(100 * sum(l["succes_procede_connu"] for l in ln) / len(ln), 1)
            lr = [l for l in ln if "succes_reference" in l]
            if lr:
                ref[n] = round(100 * sum(l["succes_reference"] for l in lr) / len(lr), 1)
        out[p] = {"longueur_min_90_procede_connu": _min_90(connu), "longueur_min_90_reference": _min_90(ref),
                  "taux_procede_connu": connu, "taux_reference": ref}
    return out


def agreger_kasiski() -> dict:
    chemin = RESULTS / "raw" / "kasiski_autoclave" / "comparaison.jsonl"
    if not chemin.exists():
        return {}
    lignes = _lire(chemin)
    out = {}
    for p in ("vigenere", "autoclave"):
        lp = [l for l in lignes if l["procede"] == p]
        out[p] = {
            "kasiski_tete_correcte_pct": round(100 * sum(l["kasiski_tete_correcte"] for l in lp) / len(lp), 1),
            "kasiski_top3_pct": round(100 * sum(l["kasiski_dans_top3"] for l in lp) / len(lp), 1),
            "repetitions_moyennes": round(st.mean(l["n_repetitions"] for l in lp), 1),
            "ic_colonnes_vraie_longueur_moyen": round(st.mean(l["ic_colonnes_vraie_longueur"] or 0 for l in lp), 4),
            "ic_moyen": round(st.mean(l["ic"] for l in lp), 4),
        }
    return out


def agreger_explications() -> dict:
    d = RESULTS / "raw" / "explications"
    if not d.exists():
        return {}
    out = {}
    for f in sorted(d.glob("*.jsonl")):
        lignes = _lire(f)
        valides = [l for l in lignes if l.get("exercice_valide") is not None]
        out[f.stem] = {
            "n_explications": len(lignes),
            "exercices_valides_pct": round(100 * sum(bool(l["exercice_valide"]) for l in valides) / len(valides), 1)
            if valides else None,
            "taux_exact_echantillon": round(100 * sum(l["succes_exact"] for l in lignes) / len(lignes), 1),
        }
    notes = RESULTS / "notes_explications.csv"
    if notes.exists():
        with open(notes, encoding="utf-8") as f:
            lignes = [r for r in csv.DictReader(f) if r.get("total", "").strip()]
        if lignes:
            totaux = [float(r["total"]) for r in lignes]
            out["notes_grille"] = {"n": len(totaux), "moyenne_sur_10": round(st.mean(totaux), 2),
                                   "ecart_type": round(st.stdev(totaux), 2) if len(totaux) > 1 else 0.0}
    return out


def agreger_tout(cfg: dict | None = None) -> dict:
    cfg = cfg or charger_config()
    raw = RESULTS / "raw"
    metrics: dict = {"version": "1.0.0", "experiences": {}}
    for d in sorted(p for p in raw.iterdir() if p.is_dir() and p.name not in ("shannon", "kasiski_autoclave",
                                                                                  "longueur_min", "explications")):
        par_conf = defaultdict(list)
        for f in sorted(d.glob("*_rep*.jsonl")):
            par_conf[f.stem.rsplit("_rep", 1)[0]].extend(_lire(f))
        metrics["experiences"][d.name] = {c: agreger_lot(ls) for c, ls in sorted(par_conf.items()) if ls}
        # Comparaison appariée : la référence (a) restreinte au sous-ensemble des agents
        if "a_baseline" in par_conf:
            for c, ls in par_conf.items():
                if c != "a_baseline":
                    metrics["experiences"][d.name][c]["comparaison_reference"] = comparaison_appariee(
                        par_conf["a_baseline"], ls)
    metrics["shannon"] = agreger_shannon(cfg)
    metrics["kasiski_autoclave"] = agreger_kasiski()
    metrics["longueur_min"] = agreger_longueur_min()
    metrics["explications"] = agreger_explications()
    metrics["resume"] = resume_principal(metrics)
    (RESULTS / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False, sort_keys=True),
                                          encoding="utf-8", newline="\n")
    return metrics


def resume_principal(m: dict) -> dict:
    """Valeurs reprises dans la fiche de dépôt (clés stables)."""
    p = m["experiences"].get("principal", {})
    r: dict = {}
    for c, v in p.items():
        r[f"taux_exact_{c}"] = v["taux_exact"]["moyenne"]
        r[f"iterations_{c}"] = v["iterations_moyennes"]["moyenne"]
        r[f"duree_s_{c}"] = v["duree_moyenne_s"]["moyenne"]
        if "comparaison_reference" in v:
            r[f"taux_exact_a_baseline_sur_sous_ensemble_{c}"] = v["comparaison_reference"][
                "reference_sur_sous_ensemble"]["moyenne"]
    for p, d in m.get("longueur_min", {}).items():
        r[f"longueur_min_90_{p}"] = d["longueur_min_90_procede_connu"]
    ka = m.get("kasiski_autoclave", {})
    if ka:
        r["kasiski_tete_correcte_vigenere_pct"] = ka["vigenere"]["kasiski_tete_correcte_pct"]
        r["kasiski_tete_correcte_autoclave_pct"] = ka["autoclave"]["kasiski_tete_correcte_pct"]
    for exp in ("defaillances", "injection"):
        for c, v in m["experiences"].get(exp, {}).items():
            r[f"{exp}_taux_exact_{c}"] = v["taux_exact"]["moyenne"]
            r[f"{exp}_garde_fou_total_{c}"] = v["garde_fou_total"]
    return r


__all__ = ["agreger_tout", "tranche"]
