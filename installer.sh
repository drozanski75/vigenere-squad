#!/usr/bin/env sh
# Vigenère-Squad : installation automatique (Linux, macOS). Usage : sh installer.sh
set -e
cd "$(dirname "$0")"
[ -f pyproject.toml ] || { echo "Lancer ce script depuis le dossier du projet."; exit 1; }
export PATH="$HOME/.local/bin:$PATH"
echo "[1/5] uv"
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
echo "[2/5] Ollama"
if ! command -v ollama >/dev/null 2>&1; then
  if [ "$(uname)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then brew install ollama
  else curl -fsSL https://ollama.com/install.sh | sh; fi
fi
echo "[3/5] Serveur Ollama"
if ! curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
  (ollama serve >/tmp/ollama.log 2>&1 &)
  i=0; until curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; do
    i=$((i+1)); [ $i -gt 30 ] && { echo "Ollama ne démarre pas (voir /tmp/ollama.log)"; exit 1; }; sleep 2; done
fi
echo "[4/5] Données, modèle principal et diagnostic"
uv run vsquad diagnostic --reparer
echo "[5/5] Tous les modèles de l'évaluation et épinglage des empreintes"
uv run vsquad modeles
echo "Terminé. Essai : uv run vsquad casser --fichier exemple_chiffre.txt --expliquer"
