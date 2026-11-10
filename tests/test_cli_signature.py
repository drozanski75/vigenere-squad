import importlib.util
from pathlib import Path

from vigenere_squad import cli
from vigenere_squad.outils import chiffres


def test_cli_casser_simule(tmp_path, capsys):
    ch = chiffres.vigenere_chiffrer("LE CHIFFRE DE VIGENERE FUT LONGTEMPS REPUTE INDECHIFFRABLE MAIS KASISKI "
                                    "PUIS BABBAGE ONT MONTRE COMMENT LE CASSER EN ESTIMANT LA LONGUEUR DE LA CLE "
                                    "PUIS EN ATTAQUANT CHAQUE COLONNE COMME UN CHIFFRE DE CESAR", "CLEF")
    trace = tmp_path / "t.jsonl"
    assert cli.main(["casser", "--texte", ch, "--llm", "simule", "--expliquer", "--trace", str(trace)]) == 0
    sortie = capsys.readouterr().out
    assert "VIGENERE FUT LONGTEMPS" in sortie and "attaque_vigenere" in sortie
    assert cli.main(["traces", str(trace)]) == 0
    assert cli.main(["casser", "--texte", ch, "--llm", "aucun", "--trace", str(tmp_path / "b.jsonl")]) == 0


def test_signature_aller_retour(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("sig", Path(__file__).parents[1] / "scripts" / "signature.py")
    s = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(s)
    monkeypatch.setenv("MINISIGN_PASSWORD", "test")
    for nom, valeur in {"PUB": "pub", "SUMS": "SUMS", "SIG": "SUMS.minisig", "CLE": "k.key"}.items():
        monkeypatch.setattr(s, nom, tmp_path / valeur)
    monkeypatch.setattr(s, "RACINE", tmp_path)
    monkeypatch.setattr(s, "MOTIFS", ["*.txt"])
    (tmp_path / "a.txt").write_text("résultat", encoding="utf-8")
    s.creer_cle()
    s.ecrire_empreintes()
    s.signer()
    assert s.verifier() is True
    (tmp_path / "a.txt").write_text("falsifié", encoding="utf-8")
    assert s.verifier() is False
    assert len(s.empreinte_cle()) == 64


def test_diagnostic_sans_ollama(monkeypatch, capsys):
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9")
    assert cli.main(["diagnostic", "--rapide"]) == 1
    sortie = capsys.readouterr().out
    assert "Outils de cryptanalyse" in sortie and "Serveur Ollama" in sortie and "[ERREUR]" in sortie
