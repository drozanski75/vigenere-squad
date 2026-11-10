import pytest

from vigenere_squad.outils import attaques, chiffres
from vigenere_squad.outils.texte import lettres

CLES = {"cesar": 11, "affine": (7, 3), "vigenere": "LOGARITHME", "beaufort": "MERLIN",
        "autoclave": "DIDEROT", "substitution": "QWERTYUIOPASDFGHJKLZXCVBNM"}


@pytest.mark.parametrize("procede", chiffres.PROCEDES)
def test_attaque_reussit_sur_texte_long(procede, extrait_fr):
    clair = extrait_fr(800, graine=3)
    ch = chiffres.chiffrer(procede, clair, CLES[procede])
    r = attaques.ATTAQUES[procede](ch)
    trouve, attendu = lettres(r["clair"]), lettres(clair)
    if procede == "substitution":  # lettres rares parfois permutées : on exige 98 % de lettres justes
        assert sum(a == b for a, b in zip(trouve, attendu)) / len(attendu) > 0.98
    else:
        assert trouve == attendu
    assert r["score_normalise"] > 0.7
    assert r["procede"] == procede
    assert r["clair"].count(" ") == clair.count(" ")


def test_cles_retrouvees(extrait_fr):
    clair = extrait_fr(600, graine=5)
    assert attaques.chi2_cesar(chiffres.cesar_chiffrer(clair, 11))["cle"] == "11"
    assert attaques.force_brute_affine(chiffres.affine_chiffrer(clair, 7, 3))["cle"] == "7,3"
    r = attaques.attaque_vigenere(chiffres.vigenere_chiffrer(clair, "LOGARITHME"), [10, 20])
    assert r["cle"] == "LOGARITHME"
    assert attaques.attaque_autoclave(chiffres.autoclave_chiffrer(clair, "DIDEROT"))["cle"] == "DIDEROT"


def test_periode_minimale():
    assert attaques.periode_minimale("ABCABC") == "ABC"
    assert attaques.periode_minimale("ABCD") == "ABCD"


def test_longueurs_invalides_et_texte_court(extrait_fr):
    clair = extrait_fr(300, graine=2)
    ch = chiffres.vigenere_chiffrer(clair, "CLE")
    r = attaques.attaque_vigenere(ch, [0, 999])  # longueurs absurdes -> repli sur 1
    assert r["longueurs_testees"] == [1]
    r = attaques.attaque_beaufort(chiffres.beaufort_chiffrer(clair, "CLE"))
    assert lettres(r["clair"]) == lettres(clair)


def test_recuit_deterministe(extrait_fr):
    clair = extrait_fr(400, graine=4)
    ch = chiffres.substitution_chiffrer(clair, CLES["substitution"])
    a = attaques.recuit_substitution(ch, iterations=1500, redemarrages=2, graine=1)
    b = attaques.recuit_substitution(ch, iterations=1500, redemarrages=2, graine=1)
    assert a["cle"] == b["cle"] and sorted(a["cle"]) == sorted("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
