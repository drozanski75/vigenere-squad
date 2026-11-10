# Procédure d'audit — Vigenère-Squad v1.0.0

Cette procédure permet à un tiers de vérifier, sans échange avec l'auteur, que
les résultats annoncés sont authentiques et reproductibles. Elle suit la liste
de contrôle de l'annexe B du sujet.

## 0. Prérequis

* Windows, macOS ou Linux, 8 Go de mémoire au moins, sans GPU.
* `git`, [uv](https://docs.astral.sh/uv/) ≥ 0.5, [Ollama](https://ollama.com) ≥ 0.9 démarré —
  **ou seulement Docker** (`docker compose run --rm vsquad <commande>`, voir `compose.yaml`).
* Optionnel : `make` (raccourcis), `minisign` (sinon la vérification Python fournie suffit).

Sous Windows, `installer.bat` prépare tout en une fois ; `uv run vsquad diagnostic` vérifie
l'installation avant l'audit. Toutes les commandes ci-dessous existent sous la forme `uv run vsquad <commande>` (tous
systèmes) ; `make <cible>` en est un raccourci sous Linux et macOS.

## 1. Obtenir la version archivée et vérifier qu'elle correspond au tag

```bash
# Archive Zenodo (DOI de la fiche) :
curl -L -o vsquad.zip "https://zenodo.org/records/<ID>/files/drozanski75/vigenere-squad-v1.0.0.zip?download=1"
sha256sum vsquad.zip          # doit être égal à la valeur « SHA-256 de l'archive Zenodo » de la fiche
unzip vsquad.zip && cd drozanski75-vigenere-squad-*/
# Comparaison avec le tag GitHub :
git clone --depth 1 --branch v1.0.0 https://github.com/drozanski75/vigenere-squad.git /tmp/tag
diff -r --exclude=.git . /tmp/tag && echo "archive identique au tag v1.0.0"
```

Vérifier aussi que l'intégration continue est verte sur le tag (lien n° 4 de la fiche).

## 2. Vérifier l'intégrité et l'authenticité des résultats publiés

```bash
uv run vsquad verifier                      # signature + toutes les empreintes (= make verify)
# ou avec les outils de référence :
minisign -Vm SHA256SUMS -p minisign.pub
sha256sum -c SHA256SUMS
```

Attendu : `Signature and comment signature verified`, puis `OK` pour chaque
fichier. L'empreinte de la clé publique (`python scripts/signature.py
empreinte-cle`) doit être égale à celle de la fiche de dépôt.

## 3. Rejouer l'évaluation complète sur machine vierge

```bash
uv run vsquad reproduire   # (= make reproduce) installe l'environnement figé (uv.lock), télécharge les modèles exacts,
                    # régénère données et corpus (graine 42), exécute toutes les expériences,
                    # reconstruit results/ et la page de résultats
uv run vsquad comparer     # (= make compare) compare aux métriques publiées, avec les tolérances ci-dessous
```

Durée et mémoire annoncées : voir `results/EXECUTION.json` publié
(`duree_totale_min`, `rss_max_python_mo`, `memoire_modeles_ollama_mo`) et
la fiche de dépôt. L'exécution est reprenable : en cas d'interruption,
relancer `uv run vsquad evaluer` reprend là où elle s'était arrêtée.

Contrôle des modèles : avant toute exécution, les empreintes (digest) des
modèles installés sont comparées à celles de `config/experiment.yaml` ; tout
écart arrête l'évaluation.

Évaluation rapide (15 à 30 minutes) : `uv run vsquad reproduire --petit` (modèle
`qwen3:0.6b`, écrit dans `build/small/`, identique au travail de la CI).

## 4. Valeurs attendues et tolérances

| Partie | Exemples de clés dans `metrics.json` | Tolérance |
|---|---|---|
| Référence sans LLM (a) | `experiences.*.a_baseline.*` | **exacte** (déterministe, graines fixes) |
| Shannon, Kasiski/autoclave | `shannon`, `kasiski_autoclave` | **exacte** |
| Configurations à agents (b), (c) | `experiences.principal.b_qwen3_4b.taux_exact` … | **± 2 écarts types** (max des deux écarts types publié/reproduit), plancher 3 points |
| Durées | `duree_moyenne_s` | indicatives (dépendent du processeur) |

`vsquad comparer` applique ces règles et conclut « reproductible », « partiellement
reproductible » ou « non reproductible ».

## 5. Vérifier les traces et la liste fermée d'outils

```bash
uv run vsquad traces traces/principal/b_qwen3_4b/rep0/standard-vigenere-0600-0.jsonl
uv run python scripts/audit_traces.py      # contrôle automatique sur un échantillon aléatoire
```

`audit_traces.py` vérifie, sur un échantillon de traces, que chaque appel
d'outil exécuté appartient à la liste fermée de l'agent appelant, que chaque
valeur de `results/raw` correspond à la décision finale de sa trace, et compte
les appels refusés.

## 6. Autres contrôles

```bash
gitleaks detect --source . --no-git -v     # aucun secret (aussi exécuté en CI)
uv run pytest --cov                        # tests + couverture >= 70 % sur les outils déterministes
```

* Aucune donnée personnelle : seuls des textes du domaine public sont utilisés.
* Aucune clé privée : seule `minisign.pub` est publiée.
* Chaque valeur du rapport et de la fiche de dépôt se retrouve dans
  `metrics.json` (bloc `resume`, clés citées) et renvoie à des traces.

## 7. Conclusion de l'audit

Reporter : reproductible / partiellement reproductible / non reproductible,
avec la sortie de `vsquad comparer` et `vsquad verifier`.
