"""Page de résultats publique (GitHub Pages), générée depuis metrics.json."""

from __future__ import annotations

import html
import json
import shutil

from .executer import RESULTS, SITE
from .metriques import ORDRE_TRANCHES, PROCEDES

CSS = """
:root{--s:#fbfaf7;--t:#2b2b2a;--t2:#6b6a63;--l:#e4e2dc;--a:#2a78d6}
@media (prefers-color-scheme:dark){:root{--s:#1a1a19;--t:#f0efec;--t2:#c3c2b7;--l:#3a3a37;--a:#3987e5}
img{background:#fff;border-radius:4px}}
body{font:15px/1.55 system-ui,sans-serif;background:var(--s);color:var(--t);max-width:1080px;margin:auto;padding:24px}
h1{font-size:1.6rem;margin-bottom:.2rem}h2{margin-top:2.2rem;border-bottom:1px solid var(--l);padding-bottom:.3rem}
.sub{color:var(--t2)}table{border-collapse:collapse;margin:.6rem 0;font-variant-numeric:tabular-nums}
td,th{border-bottom:1px solid var(--l);padding:4px 10px;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}
th{color:var(--t2);font-weight:600}img{max-width:100%}a{color:var(--a)}code{font-size:.9em}
.tuiles{display:flex;gap:14px;flex-wrap:wrap}.tuile{border:1px solid var(--l);border-radius:8px;padding:10px 14px;min-width:170px}
.tuile b{display:block;font-size:1.5rem}.tuile span{color:var(--t2);font-size:.85rem}
"""


def _mv(v) -> str:
    if not v or v.get("moyenne") is None:
        return "–"
    if not v.get("ecart_type"):
        return f"{v['moyenne']:.1f}"
    return f"{v['moyenne']:.1f} ± {v['ecart_type']:.1f}"


def _memo(v: dict) -> str:
    py = (v.get("memoire_python_mo") or {}).get("moyenne")
    ol = (v.get("memoire_ollama_mo") or {}).get("moyenne")
    if py is None:
        return "–"
    return f"{py:.0f} + {ol:.0f} (Ollama)" if ol else f"{py:.0f}"


def _table(entetes: list[str], lignes: list[list[str]]) -> str:
    th = "".join(f"<th>{html.escape(h)}</th>" for h in entetes)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in lignes)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>"


def generer_site(liens: dict | None = None) -> str:
    m = json.loads((RESULTS / "metrics.json").read_text(encoding="utf-8"))
    env_p = RESULTS / "ENVIRONMENT.json"
    env = json.loads(env_p.read_text(encoding="utf-8")) if env_p.exists() else {}
    site = SITE
    site.mkdir(parents=True, exist_ok=True)
    if (site / "figures").exists():
        shutil.rmtree(site / "figures")
    shutil.copytree(RESULTS / "figures", site / "figures")
    shutil.copy(RESULTS / "metrics.json", site / "metrics.json")
    p = m["experiences"].get("principal", {})
    parties = [f"<h1>Vigenère-Squad — résultats</h1><p class='sub'>Système multi-agents (LLM local) de "
               f"cryptanalyse des chiffres classiques. Page générée automatiquement depuis "
               f"<a href='metrics.json'>metrics.json</a> (version {m.get('version')}).</p>"]
    tuiles = []
    for c, v in sorted(p.items()):
        tuiles.append(f"<div class='tuile'><span>{html.escape(c)}</span><b>{v['taux_exact']['moyenne']:.1f} %</b>"
                      f"<span>clair exact · {v['n_chiffres']} chiffrés · {v['iterations_moyennes']['moyenne']:.2f}"
                      f" itér.</span></div>")
    parties.append("<div class='tuiles'>" + "".join(tuiles) + "</div>")

    parties.append("<h2>Étude d'ablation (corpus principal)</h2>")
    lignes = []
    for c, v in sorted(p.items()):
        ref = v.get("comparaison_reference", {}).get("reference_sur_sous_ensemble")
        lignes.append([html.escape(c), str(v["n_chiffres"]), _mv(v["taux_exact"]), _mv(ref) if ref else "–",
                       _mv(v["taux_procede_correct"]), _mv(v["iterations_moyennes"]), _mv(v["duree_moyenne_s"]),
                       _mv(v["taux_repli"]), str(v["appels_refuses_total"]), _memo(v)])
    parties.append(_table(["configuration", "chiffrés", "clair exact %", "réf. (a) même sous-ensemble %",
                           "procédé correct %", "itérations", "durée (s)", "replis %", "appels refusés",
                           "mémoire / chiffré (Mo)"], lignes))
    parties.append("<img src='figures/ablation.png' alt='Ablation : taux de succès et durée par configuration'>")

    parties.append("<h2>Taux de clair exact par procédé et par tranche de longueur</h2>")
    for c, v in sorted(p.items()):
        lignes = [[pr] + [_mv(v["par_procede_tranche"].get(pr, {}).get(t)) for t in ORDRE_TRANCHES]
                  + [v["longueur_min_90"].get(pr) or "non atteinte"] for pr in PROCEDES if pr in v["par_procede"]]
        parties.append(f"<h3>{html.escape(c)}</h3>" + _table(["procédé"] + ORDRE_TRANCHES + ["longueur min. 90 %"],
                                                             lignes))
    parties.append("<img src='figures/taux_par_longueur_principal.png' alt='Taux par longueur'>")

    lm = m.get("longueur_min", {})
    if lm:
        parties.append("<h2>Longueur minimale de succès à 90 % (lettres)</h2>")
        parties.append(_table(["procédé", "procédé connu (outil adapté)", "référence (a), procédé inconnu"],
                              [[p_, str(d["longueur_min_90_procede_connu"] or "> max"),
                                str(d["longueur_min_90_reference"] or "> max")] for p_, d in lm.items()]))
    s = m.get("shannon", {})
    if s:
        parties.append("<h2>Lien avec Shannon : distance d'unicité</h2>")
        lignes = [[L, str(d["longueur_min_90"]), str(d["longueur_min_90_longueur_connue"]),
                   str(d["distance_unicite_estimee"]), str(d["distance_unicite_litterature"])]
                  for L, d in sorted(s["par_longueur_cle"].items(), key=lambda kv: int(kv[0]))]
        parties.append(_table(["longueur de clé", "min. 90 % (longueur inconnue)", "min. 90 % (longueur connue)",
                               "U estimée", "U littérature"], lignes))
        parties.append("<img src='figures/shannon.png' alt='Longueur minimale de succès et distance d unicité'>")

    k = m.get("kasiski_autoclave", {})
    if k:
        parties.append("<h2>Autoclave : pourquoi Kasiski échoue</h2>")
        lignes = [[pr, f"{d['kasiski_tete_correcte_pct']}", f"{d['kasiski_top3_pct']}", f"{d['repetitions_moyennes']}",
                   f"{d['ic_colonnes_vraie_longueur_moyen']}"] for pr, d in k.items()]
        parties.append(_table(["procédé", "bonne longueur en tête %", "dans le top 3 %", "répétitions",
                               "IC colonnes (vraie longueur)"], lignes))
        parties.append("<img src='figures/kasiski_autoclave.png' alt='Kasiski vigenere contre autoclave'>")

    rob = {e: v for e, v in m["experiences"].items() if e.startswith("robustesse") or e in ("defaillances", "injection")}
    if rob:
        parties.append("<h2>Robustesse, défaillances et injection de consignes</h2>")
        lignes = [[html.escape(e), html.escape(c), str(v["n_chiffres"]), _mv(v["taux_exact"]),
                   _mv(v["precision_lettres"]), _mv(v["taux_repli"]), str(v["erreurs_llm_total"]),
                   str(v["garde_fou_total"])]
                  for e, d in sorted(rob.items()) for c, v in sorted(d.items())]
        parties.append(_table(["expérience", "configuration", "chiffrés", "clair exact %", "lettres justes %",
                               "replis %", "erreurs LLM", "garde-fous"], lignes))
        parties.append("<img src='figures/robustesse.png' alt='Robustesse'>")

    ex = m.get("explications", {})
    if ex:
        parties.append("<h2>Explications du Pédagogue</h2><pre>" + html.escape(json.dumps(ex, indent=2,
                       ensure_ascii=False)) + "</pre>")

    parties.append("<h2>Environnement et intégrité</h2><pre>" + html.escape(json.dumps(
        {k: env.get(k) for k in ("python", "plateforme", "processeur", "memoire_totale_go", "ollama_version",
                                 "modeles", "commit")}, indent=2, ensure_ascii=False)) + "</pre>")
    if liens:
        parties.append("<ul>" + "".join(f"<li><a href='{html.escape(u)}'>{html.escape(n)}</a></li>"
                                         for n, u in liens.items()) + "</ul>")
    page = (f"<!doctype html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' "
            f"content='width=device-width,initial-scale=1'><title>Vigenère-Squad — résultats</title>"
            f"<style>{CSS}</style></head><body>{''.join(parties)}</body></html>")
    (site / "index.html").write_text(page, encoding="utf-8", newline="\n")
    return str(site / "index.html")
