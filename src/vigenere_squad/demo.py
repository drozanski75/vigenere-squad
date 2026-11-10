"""Démonstrateur local (Gradio) : raisonnement des agents et appels d'outils
affichés en direct.  Lancer : make demo  (puis ouvrir http://127.0.0.1:7860)."""

from __future__ import annotations

import json
import queue
import threading
from pathlib import Path

import gradio as gr

from .evaluation.executer import charger_config, creer_llm, creer_orchestrateur
from .heuristique import casser_baseline
from .outils import chiffres
from .outils.texte import normaliser
from .traces import Journal

ICONES = {"appel_outil": "🔧", "resultat_outil": "📊", "conclusion": "🧠", "repli": "↩️", "appel_refuse": "⛔",
          "erreur_llm": "⚠️", "erreur_outil": "⚠️", "garde_fou": "🛡️", "decision": "⚖️", "nouvelle_hypothese": "🔁",
          "debut": "▶️", "fin": "🏁"}


def _ligne(ev: dict) -> str | None:
    t = ev["type"]
    if t not in ICONES:
        return None
    a = ev.get("agent") or ""
    if t == "appel_outil":
        d = f"{ev['outil']}({json.dumps(ev['arguments'], ensure_ascii=False)})"
    elif t == "resultat_outil":
        r = ev.get("resultat", {})
        d = f"{ev['outil']} {ev.get('id_resultat', '')} " + json.dumps(
            {k: r[k] for k in ("procede", "cle", "score_normalise", "ic", "longueurs_candidates", "ordre",
                               "estimation_longueur", "corrige_verifie") if k in r}, ensure_ascii=False)
    elif t == "conclusion":
        d = json.dumps(ev["conclusion"], ensure_ascii=False)[:400]
    else:
        d = json.dumps({k: v for k, v in ev.items() if k not in ("ts", "t_rel_s", "run_id", "type", "agent")},
                       ensure_ascii=False)[:300]
    return f"`{ev['t_rel_s']:6.1f}s` {ICONES[t]} **{a}** {d}"


def casser_en_direct(texte: str, mode: str, expliquer: bool):
    cfg = charger_config()
    texte = normaliser(texte)
    file: queue.Queue = queue.Queue()
    j = Journal(Path(__file__).resolve().parents[2] / "traces" / "demo" / "derniere.jsonl", "demo", ecouteur=file.put)
    resultat: dict = {}

    def travail():
        try:
            if mode == "sans LLM (référence)":
                resultat.update(casser_baseline(texte, j))
            else:
                simule = mode == "modèle simulé"
                conf = {"modele": mode.split(" ")[-1], "temperature": 0.3}
                orch = creer_orchestrateur(creer_llm(conf, cfg, 0, simule), cfg, expliquer=expliquer)
                resultat.update(orch.casser(texte, j).model_dump())
        except Exception as e:  # noqa: BLE001
            resultat["erreur"] = str(e)
        file.put(None)

    threading.Thread(target=travail, daemon=True).start()
    journal = []
    while True:
        ev = file.get()
        if ev is None:
            break
        l = _ligne(ev)
        if l:
            journal.append(l)
            yield "\n\n".join(journal), "", ""
    if "erreur" in resultat:
        yield "\n\n".join(journal), f"Erreur : {resultat['erreur']}", ""
        return
    entete = f"**{resultat['procede']}** · clé `{resultat['cle']}` · {resultat['statut']}\n\n"
    yield "\n\n".join(journal), entete + (resultat["clair"] or ""), resultat.get("explication") or ""


def exemple(procede: str) -> str:
    clair = ("IL ETAIT HUIT HEURES QUARANTE-CINQ, ET PASSEPARTOUT ATTENDAIT SON MAITRE DANS LA GARE, "
             "TANDIS QUE LE TRAIN SE PREPARAIT A PARTIR VERS LIVERPOOL AVEC SES VOYAGEURS.")
    cles = {"cesar": 7, "affine": "5,8", "vigenere": "VERNE", "autoclave": "FOGG", "beaufort": "AOUDA",
            "substitution": "QWERTYUIOPASDFGHJKLZXCVBNM"}
    return chiffres.chiffrer(procede, clair, cles[procede])


def interface():
    with gr.Blocks(title="Vigenère-Squad") as app:
        gr.Markdown("# Vigenère-Squad\nLe modèle de langage décide et explique ; le code calcule.")
        with gr.Row():
            texte = gr.Textbox(label="Texte chiffré", lines=5)
            with gr.Column():
                mode = gr.Radio(["ollama qwen3:4b", "ollama qwen3:1.7b", "modèle simulé", "sans LLM (référence)"],
                                value="ollama qwen3:4b", label="Mode")
                expl = gr.Checkbox(value=True, label="Explication du Pédagogue + exercice")
                proc = gr.Dropdown(list(chiffres.PROCEDES), value="vigenere", label="Exemple")
                gr.Button("Charger l'exemple").click(exemple, proc, texte)
                go = gr.Button("Casser", variant="primary")
        journal = gr.Markdown(label="Raisonnement des agents (en direct)")
        clair = gr.Markdown()
        explication = gr.Markdown()
        go.click(casser_en_direct, [texte, mode, expl], [journal, clair, explication])
    return app


if __name__ == "__main__":
    interface().queue().launch(server_name="127.0.0.1")
