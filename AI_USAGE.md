# Déclaration d'usage d'outils d'IA générative

Conformément à l'annexe A du sujet, j'indique ici comment des outils d'IA
générative ont été utilisés. J'assume la responsabilité de l'intégralité du
contenu déposé.

| Outil | Usage | Étendue |
|---|---|---|
| Claude (Anthropic), assistant conversationnel et de programmation | Aide à la conception de l'architecture, génération d'une première version du code (outils, agents, orchestrateur, évaluation), des tests et des documents (README, AUDIT, carte du système, modèle de menace, trame du rapport) | Important : la structure initiale du dépôt a été produite avec l'assistant, puis relue, exécutée, testée et ajustée par mes soins |
| Modèles locaux Qwen3 (via Ollama) | Composant du système évalué (agents), pas un outil de rédaction | Voir SYSTEM_CARD.md |

## Ce que j'ai vérifié moi-même

* Exécution de `make test`, `make reproduce-small` et `make reproduce` sur ma machine ;
  lecture des traces d'agents.
* Correction des vecteurs de test (Vigenère « LEMON », autoclave « QUEENLY »,
  affine (5, 8)) contre des sources de référence.
* Relecture et notation manuelle des 10 explications tirées au hasard.
* Rédaction de l'analyse des résultats à partir des valeurs mesurées.

## Ce qui n'a pas été délégué

* Aucun résultat chiffré n'a été produit par un assistant : toutes les valeurs
  proviennent de `results/metrics.json`, généré par le code.
* Les choix de publication (licences, métadonnées Zenodo, clé de signature)
  ont été faits par moi.

*À compléter / ajuster par l'auteur avant la publication de la version v1.0.0.*
