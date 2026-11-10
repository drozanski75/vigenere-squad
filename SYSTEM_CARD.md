# Carte du système — Vigenère-Squad v1.0.0

## Usage prévu

Outil pédagogique et de recherche qui reçoit un texte chiffré par un procédé
classique (César, affine, Vigenère, autoclave, substitution monoalphabétique,
Beaufort), identifie le procédé, retrouve la clé et le clair, puis rédige une
explication pas à pas pour un étudiant de première année, accompagnée d'un
exercice similaire dont le corrigé est vérifié par le code.

Public : enseignants et étudiants en cryptographie ; chercheurs qui étudient
les systèmes multi-agents à appels d'outils sur matériel grand public.

**Hors périmètre** : chiffrements modernes (AES, RSA…), textes non latins,
cryptanalyse de données réelles de tiers. L'outil ne doit pas être présenté
comme capable d'attaquer des chiffrements utilisés aujourd'hui.

## Architecture

* **Orchestrateur** explicite (`orchestrateur.py`), état partagé typé
  (`etat.py`), boucle de vérification Cryptanalyste ⇄ Linguiste
  (au plus 6 itérations, une par procédé), réessais, replis déterministes, garde-fous.
* **Cinq agents**, un prompt versionné chacun (`src/vigenere_squad/prompts/`),
  une liste fermée d'outils et une sortie JSON validée par Pydantic :

| Agent | Rôle | Outils autorisés |
|---|---|---|
| Classifieur | mono- ou polyalphabétique, ordre des hypothèses | `indice_coincidence`, `frequences` |
| Cryptanalyste | choix et paramétrage de l'attaque, choix du résultat | `kasiski`, `friedman`, `chi2_cesar`, `force_brute_affine`, `attaque_vigenere`, `attaque_beaufort`, `attaque_autoclave`, `recuit_substitution` |
| Linguiste | plausibilité du clair, renvoi en arrière | `score_quadrigrammes` |
| Pédagogue | explication pas à pas, exercice (nouvelle clé) | aucun (lit les traces) |
| Vérificateur | vérifie le corrigé de l'exercice | `chiffrer_exercice`, `casser_exercice` |

* **Principe** : le modèle de langage décide et explique ; le code calcule.
  Aucune opération cryptographique n'est confiée au modèle : le clair et la clé
  annoncés proviennent toujours d'un résultat d'outil désigné par identifiant.

## Modèles et données

| Élément | Valeur |
|---|---|
| Modèle (b), 8 Go | `qwen3:4b` (quantification Q4 par défaut d'Ollama, relevée dans `ENVIRONMENT.json`) — digest dans `config/experiment.yaml` et `results/ENVIRONMENT.json` |
| Modèle (c), taille différente | `qwen3:1.7b` (idem) |
| Modèle d'intégration continue | `qwen3:0.6b` |
| Paramètres | température 0,3, graine `42×1000+répétition`, contexte 4 096 jetons, 512 jetons max en sortie (1 200 pour le Pédagogue), raisonnement (« think ») désactivé, sortie contrainte par schéma JSON |
| Modèle de langue des outils | quadrigrammes appris sur Zola (*Germinal*, *Nana*) et Hugo (*Notre-Dame de Paris*) ; anglais : Austen (*Pride and Prejudice*) |
| Textes des chiffrés (jamais vus à l'apprentissage) | Verne (*Le Tour du monde…*, *Voyage au centre de la Terre*), Flaubert (*Madame Bovary*), Voltaire (*Candide*) ; anglais : Shelley (*Frankenstein*) |
| Origine et licence | Project Gutenberg (domaine public), miroir GITenberg, SHA-256 épinglés (`data/sources.json`) |
| Corpus | 180 chiffrés par variante (6 procédés × 6 longueurs de 80 à 2 000 lettres × 5), clés de 3 à 12 lettres, graine 42 |

## Capacités et limites connues

* Les outils seuls cassent la quasi-totalité des chiffrés de 300 lettres et
  plus ; les échecs se concentrent sur les textes courts (80–150 lettres), en
  particulier la substitution (en dessous de la distance d'unicité, plusieurs
  clairs sont plausibles) et le Vigenère à clé longue.
* « Clair exact » est un critère strict : pour la substitution, une lettre rare
  permutée (K/W, X/Z) suffit à compter un échec ; la précision par lettre est
  donc aussi publiée.
* Les petits modèles locaux peuvent produire un JSON invalide, une conclusion
  hors schéma ou un identifiant de résultat inventé : ces cas sont absorbés par
  les réessais et les replis, et comptés (`taux_repli`, `erreurs_llm_total`).
* Les explications peuvent contenir des erreurs de raisonnement ; leur qualité
  est notée à la main sur 10 explications tirées au hasard (grille dans
  `docs/grille_explications.md`).
* Le système est réglé pour le français ; sur l'anglais il n'utilise le modèle
  de langue anglais que dans l'expérience de référence correspondante.
* Durée : plusieurs dizaines de secondes par chiffré avec `qwen3:4b` sur CPU,
  contre environ une seconde pour la référence sans modèle.

## Risques

Voir `docs/modele_de_menace.md` (STRIDE) : injection de consignes par le texte
ou par une sortie d'outil, appel d'outil halluciné, falsification des
résultats, fuite de secrets. Contre-mesures principales : liste fermée imposée
au contrôle et au décodage, validation Pydantic stricte, garde-fou déterministe
sur le score de plausibilité, signature des résultats, gitleaks.

Risque d'usage : faible (chiffres historiques, textes du domaine public). Le
risque principal est pédagogique : une explication fausse présentée avec
assurance. Les valeurs numériques de l'explication doivent être vérifiées dans
les traces.

## Résultats principaux

Toutes les valeurs proviennent de `results/metrics.json` (clé indiquée).

<!-- RESULTATS:DEBUT -->
*(bloc régénéré par `make rapport` à partir de `results/metrics.json`)*
<!-- RESULTATS:FIN -->

## Contact et citation

Auteur : Dawid Rozanski (M1 Cybersécurité, SUP DE VINCI). Citation : voir
`CITATION.cff` et le DOI Zenodo de la version v1.0.0.
