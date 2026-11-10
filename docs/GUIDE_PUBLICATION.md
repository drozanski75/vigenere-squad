# Guide de mise en ligne et de remise (pour l'auteur)

Échéance : **vendredi 20 novembre 2026**, dépôt de la fiche sur César.
Ordre impératif : tout ce qui est évalué doit être **dans le tag v1.0.0**, et
Zenodo doit être branché **avant** de créer la release.

## Jour 1 — Mise en place (≈ 1 h)

0. **Le plus simple** : double-clic sur `installer.bat` (installe uv et Ollama, construit les données,
   télécharge les 3 modèles et épingle leurs empreintes), puis `lancer.bat`. Les étapes 1-2
   ci-dessous détaillent ce que fait l'installateur.
1. **Machine** : Windows, macOS ou Linux. Sous Windows, tout se fait dans
   l'**Invite de commandes** (cmd) ; pas besoin de WSL ni de PowerShell.
2. **Installer les outils** (Windows, dans cmd) :
   ```
   winget install astral-sh.uv
   winget install Ollama.Ollama
   winget install Git.Git
   ```
   Fermer et rouvrir l'Invite de commandes, puis lancer l'application Ollama
   (icône dans la barre des tâches). Linux/macOS : voir le README.
3. **Créer le dépôt GitHub** public `vigenere-squad` (vide, sans README).
4. **Personnaliser et pousser** :
   ```bash
   cd vigenere-squad
   uv run python scripts/personnaliser.py --compte VOTRE_COMPTE_GITHUB   # --orcid 0000-... si vous en avez un
   git init -b main
   git add -A && git commit -m "Version initiale"
   git remote add origin https://github.com/VOTRE_COMPTE_GITHUB/vigenere-squad.git
   git push -u origin main
   ```
   Faire ensuite des commits réguliers : l'historique atteste du travail individuel.
5. **GitHub Pages** : *Settings → Pages → Source : GitHub Actions*.
6. **Zenodo** : se connecter sur https://zenodo.org avec GitHub, *Account → GitHub*,
   activer l'interrupteur du dépôt `vigenere-squad`. (À faire maintenant ; ne pas
   encore créer de release.)
7. Vérifier que la CI est verte sur `main` (onglet *Actions*). Si gitleaks
   signale un faux positif, l'ajouter à `.gitleaks.toml` avec une justification.

## Jour 1–2 — Premier essai avec le vrai modèle (≈ 30 min)

```
uv run vsquad donnees
uv run vsquad modeles        # télécharge qwen3:4b, qwen3:1.7b, qwen3:0.6b et écrit leurs digests dans config/experiment.yaml
uv run pytest --cov
uv run vsquad rejouer --id standard-cesar-0300-0 --config b_qwen3_4b
uv run vsquad rejouer --id standard-vigenere-0600-0 --config b_qwen3_4b --expliquer
```

Les deux commandes `rejouer` (équivalent de `make smoke`) sont le test décisif : il montre si le modèle respecte le format
JSON, appelle les bons outils et conclut. Si vous voyez beaucoup de `repli`,
`erreur_llm` ou `appel_refuse`, envoyez la sortie : les prompts se règlent
avant la grande évaluation (toute modification de prompt doit incrémenter sa
version et être consignée dans `src/vigenere_squad/prompts/CHANGELOG.md`).

Si la machine a 8 Go : fermer le navigateur pendant l'évaluation ; `qwen3:4b`
occupe environ 3 Go. Le PC ne se met pas en veille pendant l'évaluation (géré par le
programme, sans modifier les réglages Windows).

## Jour 2–4 — Évaluation complète (une nuit, reprenable)

```bash
git add config/experiment.yaml && git commit -m "Épinglage des digests des modèles"
uv run vsquad environnement
uv run vsquad evaluer        # reprenable : relancer la même commande après une interruption
uv run vsquad metriques
uv run vsquad site
```

L'évaluation enchaîne Shannon, Kasiski/autoclave, ablation (a, b, c), robustesse,
défaillances, injection, explications. Durée attendue : plusieurs heures avec
`qwen3:4b` sur CPU (valeur réelle dans `results/EXECUTION.json`). Pour suivre :
`ls results/raw/*/` et `uv run vsquad traces <fichier>`.

Si le temps manque : réduire `par_cellule_agents` (principal) ou les variantes
de robustesse dans `config/experiment.yaml`, **avant** de lancer, et le dire
dans le rapport.

## Jour 4–5 — Analyse, rapport, vidéo

1. **Noter les 10 explications** : lire `results/explications_echantillon.md`,
   remplir `results/notes_explications.csv` avec `docs/grille_explications.md`.
2. `uv run vsquad metriques` puis `uv run python scripts/rapport.py` → `docs/rapport_rendu.md` ;
   conversion en PDF avec pandoc + LaTeX (`make rapport`), ou je la fais pour toi
   si tu m'envoies `results/`.
3. Compléter dans `docs/rapport.md` les deux encadrés « À compléter par
   l'auteur » (interprétation de l'ablation et effet de la taille du modèle),
   relancer `make rapport` ; viser 12 à 20 pages.
4. Relire et ajuster `AI_USAGE.md` (supprimer la dernière ligne en italique).
5. **Vidéo de 5 à 8 min** : `uv run --extra demo python -m vigenere_squad.demo`, casser un Vigenère puis un autoclave
   en montrant les appels d'outils en direct, montrer une trace, `make verify`,
   la page de résultats. Mettre en ligne (YouTube « non répertoriée » ou autre
   lien public) ; ajouter le lien dans le README.
6. `uv run python scripts/audit_traces.py` doit afficher CONFORME.

## Jour 5 — Signature, tag, DOI (dans cet ordre)

```bash
uv run python scripts/signature.py cle    # une seule fois ; clé secrète dans ~/.minisign/ (jamais dans le dépôt)
uv run vsquad signer                       # SHA256SUMS + SHA256SUMS.minisig
uv run vsquad verifier
git add -A && git commit -m "Résultats signés v1.0.0" && git push
```

Attendre que la CI soit verte sur ce commit, puis :

```bash
git tag -a v1.0.0 -m "Version 1.0.0" && git push origin v1.0.0
```

Sur GitHub : *Releases → Draft a new release → tag v1.0.0 → Publish*.
Zenodo archive automatiquement la release et attribue un DOI (quelques minutes).
Le DOI de la **version** (pas le « concept DOI ») va dans la fiche.

Ne plus modifier le tag. Le README peut ensuite recevoir le badge DOI par un
commit sur `main` (après le tag) : `uv run python scripts/personnaliser.py --compte ... --zenodo <ID>`.

## Jour 5 — Fiche de dépôt

1. Télécharger le zip depuis la page Zenodo et calculer `sha256sum fichier.zip`.
2. Récupérer l'identifiant de l'exécution CI sur le tag (URL `.../actions/runs/<RUN_ID>`).
3. Remplir `docs/publication.yaml` (ID Zenodo, RUN_ID, vidéo, SHA-256, résumé
   final ≤ 150 mots avec le résultat principal).
4. `uv run python scripts/fiche.py` → ouvrir `docs/fiche_depot.html` dans le
   navigateur → Imprimer → Enregistrer en PDF (A4, sans en-têtes/pieds de page,
   une seule page).
5. **Tester chaque lien en navigation privée**, puis déposer le PDF sur César.

## Contrôle final (liste de l'annexe B)

- [ ] DOI = archive du tag v1.0.0 ; CI verte sur le tag
- [ ] `vsquad verifier` OK ; empreinte de la clé publique sur la fiche
- [ ] `vsquad reproduire --petit` passe sur un clone vierge
- [ ] durée et mémoire annoncées = `results/EXECUTION.json`
- [ ] chaque valeur de la fiche est une clé de `metrics.json`
- [ ] gitleaks vert ; aucune clé privée publiée
- [ ] `scripts/audit_traces.py` CONFORME
