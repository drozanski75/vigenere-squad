# Vigenère-Squad

[![CI](https://github.com/drozanski75/vigenere-squad/actions/workflows/ci.yml/badge.svg)](https://github.com/drozanski75/vigenere-squad/actions/workflows/ci.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.<ID>.svg)](https://doi.org/10.5281/zenodo.<ID>)
[![Licence : MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![Données : CC BY 4.0](https://img.shields.io/badge/donn%C3%A9es-CC%20BY%204.0-lightgrey.svg)](LICENSE-DOCS-DATA.md)
![Couverture des outils ≥ 70 %](https://img.shields.io/badge/couverture%20outils-%E2%89%A570%25-brightgreen.svg)

**Une équipe d'agents IA qui casse les chiffrements classiques et explique sa démarche.**
Le modèle de langage (local, via Ollama, sans GPU ni abonnement) décide et explique ; le code calcule.

* Résultats publics : https://drozanski75.github.io/vigenere-squad/
* Rapport technique : [`docs/rapport.pdf`](docs/rapport.pdf) · Carte du système : [`SYSTEM_CARD.md`](SYSTEM_CARD.md) ·
  Audit : [`AUDIT.md`](AUDIT.md) · Modèle de menace : [`docs/modele_de_menace.md`](docs/modele_de_menace.md)

## Démarrage le plus simple

* **Windows** : double-cliquer sur **`installer.bat`** (installe uv et Ollama, démarre Ollama, construit les
  données, télécharge les 3 modèles et épingle leurs empreintes, lance le diagnostic), puis sur **`lancer.bat`** (menu : casser un chiffré,
  interface graphique, évaluation…). Invite de commandes uniquement, pas de PowerShell.
* **Linux / macOS** : `sh installer.sh`.
* **Un problème ?** `uv run vsquad diagnostic` explique quoi faire ; voir aussi [`docs/DEPANNAGE.md`](docs/DEPANNAGE.md).

## Installation (5 commandes) — Windows, macOS ou Linux

Prérequis : [uv](https://docs.astral.sh/uv/) et [Ollama](https://ollama.com/download) (application démarrée).
Aucun GPU, aucun abonnement. Testé en intégration continue sous Linux, Windows et macOS.

| Système | Installer uv et Ollama |
|---|---|
| Windows (Invite de commandes) | `winget install astral-sh.uv` puis `winget install Ollama.Ollama` (ou les installateurs des deux sites) |
| macOS | `brew install uv ollama` (ou les installateurs) |
| Linux | `curl -LsSf https://astral.sh/uv/install.sh \| sh` puis `curl -fsSL https://ollama.com/install.sh \| sh` |

Puis, sur tous les systèmes :

```bash
git clone https://github.com/drozanski75/vigenere-squad.git
cd vigenere-squad
uv run vsquad donnees      # environnement figé (uv.lock), textes vérifiés SHA-256, modèles de langue, corpus (graine 42)
uv run vsquad modeles      # télécharge qwen3:4b, qwen3:1.7b, qwen3:0.6b et épingle leurs digests
uv run vsquad casser --fichier exemple_chiffre.txt --expliquer    # lance les agents sur un chiffré
```

### Variante sans rien installer d'autre que Docker

```bash
docker compose run --rm vsquad reproduire --petit    # Ollama et l'outil dans deux conteneurs, CPU seulement
docker compose run --rm vsquad casser --texte "OH SHWLW SULQFH ..." --expliquer
```

## Utilisation

```bash
uv run vsquad casser --texte "OH SHWLW SULQFH ..." --modele qwen3:4b --expliquer
uv run vsquad casser --fichier chiffre.txt --llm aucun          # référence sans LLM
uv run vsquad rejouer --id standard-autoclave-0300-1 --config b_qwen3_4b   # rejouer un chiffré du corpus
uv run vsquad traces traces/principal/b_qwen3_4b/rep0/standard-autoclave-0300-1.jsonl
uv run --extra demo python -m vigenere_squad.demo               # interface Gradio : raisonnement en direct
```

## Reproduction

`make` est un raccourci (Linux, macOS) ; la commande `uv run vsquad ...` fonctionne partout, Windows compris.

| Commande | Raccourci | Contenu | Durée indicative |
|---|---|---|---|
| `uv run pytest --cov` | `make test` | tests + couverture ≥ 70 % sur `vigenere_squad.outils` | < 1 min |
| `uv run vsquad reproduire --petit` | `make reproduce-small` | évaluation réduite avec `qwen3:0.6b` (identique à la CI), écrite dans `build/small/` | ≈ 15-30 min |
| `uv run vsquad reproduire` | `make reproduce` | clone vierge → environnement figé, modèles exacts, données, toutes les expériences, `results/`, page | voir `results/EXECUTION.json` |
| `uv run vsquad comparer` | `make compare` | compare aux métriques publiées avec les tolérances d'`AUDIT.md` | < 1 s |
| `uv run vsquad verifier` | `make verify` | vérifie la signature minisign de `SHA256SUMS` et toutes les empreintes | < 5 s |
| `docker compose run --rm vsquad reproduire` | — | la même chose dans des conteneurs | idem |

Paramètres déclarés : [`config/experiment.yaml`](config/experiment.yaml) (modèles avec digest, température,
graines, contexte, répétitions). Environnement capturé : `results/ENVIRONMENT.json`.

## Architecture

```
                 Orchestrateur — état partagé typé, journal JSONL de chaque message et appel d'outil
   ┌──────────────┬──────────────────┬──────────────────┬────────────────┬────────────────┐
   Classifieur    Cryptanalyste  ⇄   Linguiste          Pédagogue        Vérificateur
   IC, fréquences Kasiski, Friedman  score quadrigr.    (lit les traces)  chiffrer/casser l'exercice
                  χ², affine, recuit, │ non plausible → nouvelle hypothèse (≤ 6 itérations)
                  Vigenère, Beaufort, │ garde-fou : « plausible » refusé si score < 0,65
                  autoclave           │
   Outils déterministes (Python, testés) — toute la cryptographie et tous les calculs, jamais le LLM
```

* Liste fermée d'outils par agent, contrôlée avant exécution **et** imposée au décodage (schéma JSON).
* Le texte chiffré n'est jamais un argument fourni par le modèle ; le clair annoncé provient toujours d'un
  résultat d'outil désigné par identifiant.
* Réessais (JSON invalide, réponse vide, délai dépassé), replis déterministes, arrêt propre.
* Prompts versionnés : [`src/vigenere_squad/prompts/`](src/vigenere_squad/prompts/) et leur
  [journal des modifications](src/vigenere_squad/prompts/CHANGELOG.md).

## Expériences

| Expérience | Ce qui est mesuré |
|---|---|
| `principal` | ablation : (a) sans LLM, (b) `qwen3:4b`, (c) `qwen3:1.7b` ; taux de clair exact par procédé et longueur, itérations, temps, mémoire |
| `robustesse_*` | textes sans espaces ni ponctuation, 5 % de fautes, corpus anglais |
| `defaillances` | fautes injectées (délai, JSON invalide, réponse vide, outil en échec ou hors délai) |
| `injection` | consigne malveillante ajoutée aux sorties d'outil (modèle de menace M1/M2) |
| `shannon` | longueur minimale de succès à 90 % vs longueur de clé, comparée à la distance d'unicité |
| `kasiski_autoclave` | pourquoi Kasiski échoue sur l'autoclave |
| `explications` | 10 explications tirées au hasard, exercices vérifiés par les outils, notation par grille |

## Résultats principaux

<!-- RESULTATS:DEBUT -->
- **b_qwen3_4b** : 97.2 % de clairs exacts contre 100.0 % pour la référence (a) sur les mêmes 12 chiffrés, soit un écart de **-2.8 points** ; 2.64 itérations en moyenne contre 2.03 ; durée multipliée par 1232 ; replis déterministes dans 61.1 % des exécutions.
- **c_qwen3_1.7b** : 88.9 % de clairs exacts contre 100.0 % pour la référence (a) sur les mêmes 12 chiffrés, soit un écart de **-11.1 points** ; 4.39 itérations en moyenne contre 2.03 ; durée multipliée par 993 ; replis déterministes dans 100.0 % des exécutions.

Valeurs clés (`results/metrics.json`, bloc `resume`) :

| clé (metrics.json → resume) | valeur |
|---|---|
| `defaillances_garde_fou_total_b_qwen3_4b` | 0 |
| `defaillances_taux_exact_b_qwen3_4b` | 88.89 |
| `duree_s_a_baseline` | 0.447 |
| `duree_s_b_qwen3_4b` | 550.691 |
| `duree_s_c_qwen3_1.7b` | 444.078 |
| `injection_garde_fou_total_b_qwen3_4b` | 14 |
| `injection_taux_exact_b_qwen3_4b` | 88.89 |
| `iterations_a_baseline` | 2.03 |
| `iterations_b_qwen3_4b` | 2.64 |
| `iterations_c_qwen3_1.7b` | 4.39 |
| `kasiski_tete_correcte_autoclave_pct` | 13.3 |
| `kasiski_tete_correcte_vigenere_pct` | 63.3 |
| `longueur_min_90_affine` | 20 |
| `longueur_min_90_autoclave` | 150 |
| `longueur_min_90_beaufort` | 80 |
| `longueur_min_90_cesar` | 20 |
| `longueur_min_90_substitution` | None |
| `longueur_min_90_vigenere` | 80 |
| `taux_exact_a_baseline` | 93.7 |
| `taux_exact_a_baseline_sur_sous_ensemble_b_qwen3_4b` | 100.0 |
| `taux_exact_a_baseline_sur_sous_ensemble_c_qwen3_1.7b` | 100.0 |
| `taux_exact_b_qwen3_4b` | 97.22 |
| `taux_exact_c_qwen3_1.7b` | 88.89 |

<!-- RESULTATS:FIN -->

## Arborescence

```
config/experiment.yaml   data/ (sources épinglées, scripts à graine fixe, corpus)   src/vigenere_squad/
results/ (raw/, metrics.json, figures/, ENVIRONMENT.json, EXECUTION.json)   traces/ (JSONL)
docs/ (rapport, modèle de menace, grille)   site/ (page de résultats)   SHA256SUMS + .minisig + minisign.pub
```

## Citer

Voir [`CITATION.cff`](CITATION.cff) et le DOI Zenodo de la version v1.0.0.
Code : MIT. Documentation, résultats, données : CC BY 4.0. Textes sources : domaine public (Project Gutenberg).
