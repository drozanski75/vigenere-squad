import random

import pytest

from vigenere_squad.outils import chiffres as c
from vigenere_squad.outils.texte import (cle_valide, lettres, normaliser, remettre_structure, sans_accents,
                                         vers_entiers, vers_texte)


def test_normalisation_accents_et_ligatures():
    assert sans_accents("Élève œuvre") == "Eleve OEuvre"
    assert normaliser("Où est-il ?  Là !") == "OU EST-IL ? LA !"
    assert normaliser("Où est-il ?", garder_ponctuation=False) == "OUESTIL"
    assert normaliser("a b«c»") == "A B C"


def test_conversions_et_structure():
    assert vers_texte(vers_entiers("AZ")) == "AZ"
    assert remettre_structure("AB, C", "XYZ") == "XY, Z"
    assert remettre_structure("AB C", "X") == "X? ?"
    with pytest.raises(ValueError):
        cle_valide("123")


def test_vecteurs_connus():
    assert c.vigenere_chiffrer("ATTACKATDAWN", "LEMON") == "LXFOPVEFRNHR"
    assert c.autoclave_chiffrer("ATTACKATDAWN", "QUEENLY") == "QNXEPVYTWTWP"
    assert c.cesar_chiffrer("ABC XYZ", 3) == "DEF ABC"
    assert c.affine_chiffrer("AFFINE", 5, 8) == "IHHWVC"


@pytest.mark.parametrize("procede", c.PROCEDES)
def test_aller_retour(procede):
    rng = random.Random(7)
    clair = "BONJOUR, CECI EST UN TEST DE CHIFFREMENT CLASSIQUE !"
    for _ in range(5):
        from vigenere_squad.evaluation.donnees import cle_aleatoire

        cle = cle_aleatoire(rng, procede)
        ch = c.chiffrer(procede, clair, cle)
        assert lettres(ch) != lettres(clair) or procede == "beaufort"
        assert c.dechiffrer(procede, ch, cle) == clair
        assert ch.count(" ") == clair.count(" ")


def test_beaufort_involutif():
    assert c.beaufort_chiffrer(c.beaufort_chiffrer("ATTAQUE", "CLE"), "CLE") == "ATTAQUE"


def test_erreurs_de_cle():
    with pytest.raises(ValueError):
        c.affine_chiffrer("A", 13, 1)
    with pytest.raises(ValueError):
        c.substitution_chiffrer("A", "ABC")
    with pytest.raises(ValueError):
        c.chiffrer("enigma", "A", "B")
    with pytest.raises(ValueError):
        c.inverse_modulaire(2)


def test_cles_textuelles():
    assert c.chiffrer("cesar", "A", "D") == "D"
    assert c.chiffrer("cesar", "A", "3") == "D"
    assert c.chiffrer("affine", "B", "5,8") == c.affine_chiffrer("B", 5, 8)
    assert c.cle_en_texte("cesar", 29) == "3"
    assert c.cle_en_texte("affine", (5, 30)) == "5,4"
    assert c.cle_en_texte("affine", "5,8") == "5,8"
    assert c.cle_en_texte("vigenere", "cle") == "CLE"
