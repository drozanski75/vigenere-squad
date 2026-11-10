import pytest

from vigenere_squad.etat import EtatPartage
from vigenere_squad.outils import chiffres
from vigenere_squad.outils.registre import OUTILS


@pytest.fixture
def etat(extrait_fr):
    clair = extrait_fr(500, graine=8)
    return EtatPartage(chiffre=chiffres.vigenere_chiffrer(clair, "VERNE")), clair


def test_outils_statistiques(etat):
    e, _ = etat
    sans = OUTILS["indice_coincidence"].arguments()
    assert OUTILS["indice_coincidence"].fonction(e, sans)["ic"] < 0.06
    assert "effectifs" not in OUTILS["frequences"].fonction(e, sans)
    assert "distances" not in OUTILS["kasiski"].fonction(e, sans)
    assert OUTILS["friedman"].fonction(e, sans)["longueurs_candidates"][0] == 5


def test_attaques_et_score(etat):
    e, clair = etat
    o = OUTILS["attaque_vigenere"]
    r = o.fonction(e, o.arguments(longueurs=[5]))
    assert r["cle"] == "VERNE"
    e.resultats["R1"] = r
    s = OUTILS["score_quadrigrammes"]
    out = s.fonction(e, s.arguments(id_resultat="R1"))
    assert out["score_normalise"] > 0.75
    with pytest.raises(KeyError):
        s.fonction(e, s.arguments(id_resultat="R9"))
    for nom in ("chi2_cesar", "force_brute_affine", "attaque_beaufort", "attaque_autoclave"):
        assert OUTILS[nom].fonction(e, OUTILS[nom].arguments())["procede"]
    rs = OUTILS["recuit_substitution"]
    assert rs.fonction(e, rs.arguments(iterations=500, redemarrages=1))["procede"] == "substitution"


def test_validation_stricte_des_arguments():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        OUTILS["attaque_autoclave"].arguments(longueur_max=99)
    with pytest.raises(ValidationError):
        OUTILS["kasiski"].arguments.model_validate({"texte": "injection"})


@pytest.mark.parametrize("procede,cle", [("cesar", "4"), ("affine", "5,8"), ("vigenere", "ZOLA"),
                                         ("beaufort", "HUGO"), ("autoclave", "FLAUBERT"),
                                         ("substitution", "QWERTYUIOPASDFGHJKLZXCVBNM")])
def test_exercice_chiffrer_et_casser(extrait_fr, procede, cle):
    e = EtatPartage(chiffre="X", exercice_clair=extrait_fr(700, graine=9), exercice_procede=procede)
    c = OUTILS["chiffrer_exercice"]
    assert c.fonction(e, c.arguments(procede=procede, cle=cle))["longueur"] > 0
    v = OUTILS["casser_exercice"].fonction(e, OUTILS["casser_exercice"].arguments())
    assert v["procede"] == procede
    if procede != "substitution":
        assert v["corrige_verifie"] is True
    with pytest.raises(ValueError):
        c.fonction(e, c.arguments(procede="enigma", cle="A"))


def test_etat_acces_dictionnaire():
    e = EtatPartage(chiffre="ABC")
    assert e["chiffre"] == "ABC" and e.get("inexistant", 1) == 1
    with pytest.raises(KeyError):
        e["inexistant"] = 1
    assert e.setdefault("candidat", "R1") == "R1" and e.setdefault("candidat", "R2") == "R1"
    assert "chiffre" in list(e) and dict(e)["chiffre"] == "ABC"
