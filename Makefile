# Vigenère-Squad — raccourcis (Linux, macOS, WSL).
# Sans `make` (Windows natif) : utiliser directement `uv run vsquad <commande>` (voir README).
# Prérequis : uv (https://docs.astral.sh/uv/) et Ollama >= 0.9 (https://ollama.com) démarré.

UV ?= uv
RUN = $(UV) run --frozen

.PHONY: help install data models test smoke evaluate reproduce reproduce-small metrics site environment \
        compare sign verify rapport fiche demo clean-results

help:
	@echo "make reproduce        évaluation complète depuis un clone vierge  (= uv run vsquad reproduire)"
	@echo "make reproduce-small  évaluation réduite, modèle qwen3:0.6b, CI     (= uv run vsquad reproduire --petit)"
	@echo "make test             tests + couverture >= 70 % sur les outils"
	@echo "make smoke            2 chiffrés avec le vrai modèle, traces affichées"
	@echo "make compare          compare aux métriques publiées (tolérances AUDIT.md)"
	@echo "make verify           vérifie la signature de SHA256SUMS et toutes les empreintes"

install:
	$(UV) sync --frozen

data: install
	$(RUN) vsquad donnees

models: install
	$(RUN) vsquad modeles

test: data
	$(RUN) pytest --cov --cov-report=term --cov-report=xml

smoke: data
	$(RUN) vsquad rejouer --id standard-cesar-0300-0 --config b_qwen3_4b
	$(RUN) vsquad rejouer --id standard-vigenere-0600-0 --config b_qwen3_4b --expliquer

# Évaluation reprenable (ne recalcule pas les lots déjà complets) — pour l'auteur
evaluate: data
	$(RUN) vsquad environnement
	$(RUN) vsquad evaluer
	$(RUN) vsquad metriques
	$(RUN) vsquad site

# Reproduction par un tiers : repart de zéro (les métriques publiées sont copiées dans results/publie/)
reproduce: install
	$(RUN) vsquad reproduire

reproduce-small: install
	$(RUN) vsquad reproduire --petit

metrics:
	$(RUN) vsquad metriques

site:
	$(RUN) vsquad site

environment:
	$(RUN) vsquad environnement

compare:
	$(RUN) vsquad comparer

sign:
	$(RUN) vsquad signer

verify:
	$(RUN) vsquad verifier

rapport:
	$(RUN) python scripts/rapport.py
	cd docs && pandoc rapport_rendu.md -o rapport.pdf --pdf-engine=xelatex -V lang=fr -V geometry:margin=2.2cm \
	  -V mainfont="DejaVu Serif" -V monofont="DejaVu Sans Mono" --toc -N --resource-path=..:../results

fiche:
	$(RUN) python scripts/fiche.py

demo:
	$(UV) sync --frozen --extra demo
	$(RUN) --extra demo python -m vigenere_squad.demo

clean-results:
	rm -rf results/raw results/figures results/metrics.json results/ENVIRONMENT.json results/EXECUTION.json \
	  traces/principal traces/robustesse_* traces/defaillances traces/injection traces/explications site/figures \
	  site/index.html site/metrics.json
