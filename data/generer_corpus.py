"""Génère les corpus de chiffrés à graine fixe.

Usage : python data/generer_corpus.py --seed 42 [--par-cellule 5]
Produit data/corpus/<variante>.jsonl pour les variantes standard,
sans_espaces, fautes5 et anglais (6 procédés x 6 longueurs x N).
"""
import argparse

from vigenere_squad.evaluation.donnees import CORPUS, VARIANTES, ecrire_jsonl, generer_corpus

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--par-cellule", type=int, default=5)
    a = p.parse_args()
    for v in VARIANTES:
        c = generer_corpus(a.seed, a.par_cellule, v)
        ecrire_jsonl(c, CORPUS / f"{v}.jsonl")
        print(f"{v}: {len(c)} chiffrés -> data/corpus/{v}.jsonl")
