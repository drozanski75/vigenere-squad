"""Génère docs/fiche_depot.html conforme au canevas (une page A4) à partir de
docs/publication.yaml, results/metrics.json, ENVIRONMENT.json, EXECUTION.json
et minisign.pub. Ouvrir le fichier dans un navigateur puis « Imprimer > PDF »
(A4, marges par défaut, sans en-têtes ni pieds de page)."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[1]


def lire(p, defaut=None):
    p = R / p
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else (defaut or {})


def main() -> None:
    pub = yaml.safe_load((R / "docs" / "publication.yaml").read_text(encoding="utf-8"))
    m = lire("results/metrics.json")
    env = lire("results/ENVIRONMENT.json")
    exe = lire("results/EXECUTION.json")
    c, d = pub["compte"], pub["depot"]
    base = f"https://github.com/{c}/{d}"
    blob = f"{base}/blob/v1.0.0"
    liens = [
        ("1. Dépôt GitHub public", base),
        ("2. <i>Release</i> <code>v1.0.0</code>", f"{base}/releases/tag/v1.0.0"),
        ("3. DOI Zenodo de la version <code>v1.0.0</code>", f"https://doi.org/10.5281/zenodo.{pub['zenodo_id']}"),
        ("4. Intégration continue sur le tag", f"{base}/actions/runs/{pub['ci_run_id']}"),
        ("5. Page de résultats (GitHub Pages)", f"https://{c}.github.io/{d}/"),
        ("6. Rapport technique (<code>docs/rapport.pdf</code>)", f"{blob}/docs/rapport.pdf"),
        ("7. Vidéo de démonstration (5 à 8 min)", pub["video"]),
        ("8. Procédure d'audit (<code>AUDIT.md</code>)", f"{blob}/AUDIT.md"),
        ("9. Carte du système (<code>SYSTEM_CARD.md</code>)", f"{blob}/SYSTEM_CARD.md"),
        ("10. <code>SHA256SUMS</code>, signature et clé publique",
         f"{blob}/SHA256SUMS · SHA256SUMS.minisig · minisign.pub"),
        ("11. Déclaration d'usage de l'IA (<code>AI_USAGE.md</code>)", f"{blob}/AI_USAGE.md"),
    ]
    res = m.get("resume", {})
    resultats = []
    for k in pub["resultats"][:5]:
        v = res.get(k, "?")
        unite = " %" if ("taux" in k or k.endswith("_pct")) and isinstance(v, (int, float)) else ""
        resultats.append(f"{v}{unite} <code>{html.escape(k)}</code>")
    modeles = "; ".join(f"{n} {(i.get('digest') or '')[:12]}" for n, i in (env.get("modeles") or {}).items()
                        if n.split(":")[0] == "qwen3") or "–"
    materiel = f"{env.get('processeur', '–')}, {env.get('coeurs', '–')} cœurs, {env.get('memoire_totale_go', '–')} Go"
    duree = (f"{exe.get('duree_totale_min', '–')} min ; Python {exe.get('rss_max_python_mo', '–')} Mo + modèles "
             f"{max((exe.get('memoire_modeles_ollama_mo') or {'': 0}).values())} Mo")
    pubkey = (R / "minisign.pub")
    empreinte = hashlib.sha256(pubkey.read_text(encoding="utf-8").strip().splitlines()[-1].encode()).hexdigest() if pubkey.exists() \
        else "–"
    cle_minisign = pubkey.read_text(encoding="utf-8").strip().splitlines()[-1] if pubkey.exists() else "–"
    lignes_liens = "".join(f"<tr><td>{n}</td><td class='u'>{html.escape(u)}</td></tr>" for n, u in liens)
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Fiche de dépôt</title><style>
@page {{ size: A4; margin: 14mm 13mm; }}
body {{ font: 8.6pt/1.32 "Lato","Carlito","Segoe UI",sans-serif; color:#222; margin:0; }}
.tete {{ display:flex; justify-content:space-between; color:#555; border-bottom:1px solid #333; padding-bottom:2px; }}
h1 {{ font-size:11pt; color:#1f3556; margin:10px 0 2px; border-bottom:1px solid #ccc; padding-bottom:3px; }}
.cadre {{ border:1px solid #1f3556; border-radius:4px; margin-top:6px; }}
.bandeau {{ background:#1f3556; color:#fff; font-weight:700; font-size:10.5pt; padding:4px 10px; }}
.in {{ padding:6px 10px 8px; }} table {{ width:100%; border-collapse:collapse; }}
td {{ padding:1.6px 0; vertical-align:top; }} td.u {{ font-family:"DejaVu Sans Mono",monospace; font-size:7.3pt;
  word-break:break-all; }} .l {{ font-weight:700; width:22%; }} .g {{ color:#666; font-weight:400; }}
.sec {{ font-weight:700; margin-top:7px; border-bottom:1px solid #333; padding-bottom:1px; }}
.res {{ text-align:justify; margin:3px 0 0; }} code {{ font-size:7.4pt; }} .pied {{ position:fixed; bottom:0;
  width:100%; display:flex; justify-content:space-between; color:#555; }}
</style></head><body>
<div class="tete"><span>Cryptographie appliquée et IA agentique – Projet individuel</span><span>Fiche de dépôt</span></div>
<div class="cadre"><div class="bandeau">FICHE DE DÉPÔT – PROJET INDIVIDUEL</div><div class="in">
<table><tr><td class="l">Nom, prénom</td><td>{html.escape(pub['nom'])}</td><td class="l">Promotion</td>
<td>{html.escape(pub['promotion'])}</td></tr>
<tr><td class="l">Sujet (n<sup>o</sup>, titre)</td><td>{html.escape(pub['sujet'])}</td>
<td class="l">ORCID <span class="g">(facult.)</span></td><td>{html.escape(pub.get('orcid') or '–')}</td></tr></table>
<div class="sec">Résumé <span class="g">(150 mots au plus : problème, approche, résultat principal)</span></div>
<p class="res">{html.escape(' '.join(pub['resume'].split()))}</p>
<div class="sec">Résultats principaux <span class="g">(trois à cinq valeurs, chacune avec sa clé dans
<code>metrics.json</code>)</span></div>
<table>{''.join(f'<tr><td>{i + 1}. {r}</td></tr>' for i, r in enumerate(resultats))}</table>
<div class="sec">Liens exigés <span class="g">(adresses complètes et accessibles publiquement)</span></div>
<table>{lignes_liens}</table>
<div class="sec">Reproductibilité</div>
<table><tr><td class="l">Modèle(s) et <i>digest</i></td><td class="u">{html.escape(modeles)}</td></tr>
<tr><td class="l">Matériel testé</td><td>{html.escape(materiel)}</td></tr>
<tr><td class="l">Commande</td><td><code>make reproduce</code></td></tr>
<tr><td class="l">Durée, mémoire</td><td>{html.escape(duree)}</td></tr></table>
<div class="sec">Intégrité</div>
<table><tr><td class="l">SHA-256 de l'archive Zenodo</td><td class="u">{html.escape(pub['sha256_archive_zenodo'])}</td></tr>
<tr><td class="l">Empreinte de la clé publique de signature</td><td class="u">SHA-256 {empreinte}<br>
minisign {html.escape(cle_minisign)}</td></tr></table>
</div></div>
<div class="pied"><span>Y. AMEUR – Édition 2026</span><span>1 / 1</span></div>
</body></html>"""
    (R / "docs" / "fiche_depot.html").write_text(page, encoding="utf-8", newline="\n")
    mots = len(pub["resume"].split())
    print(f"docs/fiche_depot.html écrit (résumé : {mots} mots{' — TROP LONG' if mots > 150 else ''})")


if __name__ == "__main__":
    main()
