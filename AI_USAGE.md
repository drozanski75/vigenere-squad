# Déclaration d'usage d'outils d'IA générative

Conformément à l'annexe A du sujet, j'indique ici comment des outils d'IA
générative ont été utilisés. J'assume la responsabilité de l'intégralité du
contenu déposé.

| Outil | Usage | Étendue |
|---|---|---|
| Claude (Anthropic), assistant conversationnel et de programmation | Conception de l'architecture, écriture du code (outils, agents, orchestrateur, évaluation, CLI, installateurs), des tests, des workflows d'intégration continue, de la documentation (README, AUDIT, carte du système, modèle de menace, rapport) ; préparation des commits ; génération de la clé de signature et signature de `SHA256SUMS` ; création de la release | Très important : l'essentiel du dépôt a été produit avec l'assistant, sous ma direction, puis exécuté et vérifié sur ma machine |
| Modèles locaux Qwen3 (Ollama) | Composant du système évalué (agents) | Voir SYSTEM_CARD.md |

## Ce que j'ai fait et vérifié moi-même

* Installation et exécution sous Windows 11 (`installer.bat`, `lancer.bat`) : tests
  automatisés (66 réussis), diagnostic, cycles complets des cinq agents avec
  `qwen3:4b`, évaluation réduite ; journaux dans `docs/video/journaux/`.
* Les traces de ces essais ont conduit à plusieurs corrections consignées dans
  `src/vigenere_squad/prompts/CHANGELOG.md` (protocole en deux phases, schéma
  compatible Ollama, garde-fou recalibré à 0,65, hypothèse rejetée non reproposée).
* Création du dépôt public, branchement de Zenodo et de GitHub Pages.

## Exécution de l'évaluation

L'évaluation complète a été exécutée par le workflow « Évaluation complète »
(GitHub Actions, serveurs CPU sans GPU, calcul parallèle) afin de tenir le délai
de remise ; le numéro d'exécution figure dans `results/EXECUTION.json`. Toutes
les valeurs chiffrées proviennent de `results/metrics.json`, produit par le code ;
aucune valeur n'a été saisie à la main ni produite par un assistant.

## Signature

La paire de clés minisign a été générée par l'assistant à ma demande ; seule la
clé publique (`minisign.pub`) est publiée. La signature atteste l'intégrité des
artefacts listés dans `SHA256SUMS` depuis la version v1.0.0.

## Limites assumées

* Pas de vidéo de démonstration.
* Évaluation des agents sur un sous-ensemble stratifié (voir le rapport), faute de temps.
* Les explications du Pédagogue n'ont pas été notées à la main avec la grille
  (`results/notes_explications.csv` vide) ; seuls les indicateurs automatiques
  (exercices vérifiés par les outils) sont publiés.
