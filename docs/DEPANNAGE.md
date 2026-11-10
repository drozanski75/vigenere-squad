# Dépannage

Premier réflexe, sur tous les systèmes : `uv run vsquad diagnostic` (ou option 1 de
`lancer.bat`). Il vérifie chaque point ci-dessous et affiche la commande qui corrige.
`uv run vsquad diagnostic --reparer` corrige automatiquement ce qui peut l'être
(données, téléchargement du modèle).

| Symptôme | Cause | Solution |
|---|---|---|
| `'uv' n'est pas reconnu…` juste après l'installation | Windows n'a pas rechargé le PATH | fermer et rouvrir l'Invite de commandes (ou relancer `installer.bat`) |
| `ollama` ouvre un menu (*Chat with a model*, *Launch…*) | `ollama` sans argument lance l'interface interactive | appuyer sur **Échap** ; utiliser `ollama pull qwen3:4b`, ou laisser `installer.bat` le faire |
| Ollama demande de se connecter (`ollama.com/connect…`, modèle `…:cloud`) | modèle *cloud* proposé par défaut par Ollama | **ne pas se connecter** : Ctrl+C. Le projet n'utilise que des modèles locaux, sans compte ni abonnement |
| `Le chemin d'accès spécifié est introuvable` après `cd` | le zip n'a pas été extrait, ou le dossier porte un autre nom | dans l'Explorateur : clic droit sur le zip → *Extraire tout* ; `dir pyproject.toml` doit trouver le fichier |
| `No module named 'resource'` ou `invalid choice: 'donnees'` | ancienne version du projet | utiliser la dernière version (tag v1.0.0 ou branche `main`) |
| La commande semble bloquée sans rien afficher | le modèle réfléchit (CPU) | l'affichage est en direct depuis la v1.1.0 ; dans une 2e fenêtre : `uv run vsquad traces traces\cli\derniere.jsonl` |
| `ollama ps` affiche `17%/83% CPU/GPU` | le modèle déborde de la mémoire graphique, ce qui ralentit fortement | réduire `contexte` dans `config/experiment.yaml` (3 072 → 2 048), ou utiliser `qwen3:1.7b` |
| Plusieurs minutes par chiffré | machine sans carte graphique | normal sur CPU ; réduire `par_cellule_agents` dans `config/experiment.yaml` pour l'évaluation, le dire dans le rapport |
| `Ollama ne répond pas sur http://127.0.0.1:11434` | serveur arrêté | ouvrir l'application Ollama (menu Démarrer) ou `ollama serve` ; Docker : `docker compose up -d ollama` |
| `digest installé ≠ déclaré` | modèle mis à jour depuis l'épinglage | `uv run vsquad modeles` (ré-épingle) ou installer exactement la version déclarée |
| Empreinte SHA-256 inattendue pour un texte de `data/raw` | fichier modifié (conversion de fins de ligne par un éditeur ou par git) | re-télécharger le dépôt ; `.gitattributes` protège `data/raw` |
| Erreur « nom de fichier trop long » sous Windows | chemin du dossier très profond (limite Windows de 260 caractères) | extraire le projet près de la racine, par ex. `C:\vsquad\` |
| Caractères accentués illisibles dans la console | page de code de la console | `chcp 65001` avant de lancer (fait automatiquement par les `.bat`) |

## Ordre de vitesse attendu

| Matériel | Par chiffré avec `qwen3:4b` |
|---|---|
| Carte graphique ≥ 4 Go, modèle 100 % GPU | quelques secondes à ~30 s |
| GPU partiel (modèle qui déborde) | ~1 à 3 min |
| Processeur seul | plusieurs minutes |

La référence sans IA (`--llm aucun`) prend moins d'une seconde partout.
