"""Vérifie les textes sources (SHA-256) et construit les modèles de langue.

Usage : python data/preparer_donnees.py
"""
import json

from vigenere_squad.evaluation.donnees import construire_modeles, telecharger_et_verifier

if __name__ == "__main__":
    for ligne in telecharger_et_verifier():
        print(ligne)
    print(json.dumps(construire_modeles(), indent=2, ensure_ascii=False))
