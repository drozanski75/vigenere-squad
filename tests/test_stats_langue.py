import numpy as np

from vigenere_squad.outils import chiffres, stats
from vigenere_squad.outils.langue import ModeleLangue, modele


def test_indice_coincidence():
    assert stats.indice_coincidence("AAAA") == 1.0
    assert stats.indice_coincidence("A") == 0.0
    assert abs(stats.indice_coincidence("ABCDEFGHIJKLMNOPQRSTUVWXYZ") - 0.0) < 1e-9


def test_frequences_et_chi2(extrait_fr):
    t = extrait_fr(2000)
    f = stats.frequences(t)
    assert f["ordre"][0] == "E"
    assert abs(sum(f["proportions"].values()) - 1) < 0.01
    assert stats.chi2_texte(t) < stats.chi2_texte(chiffres.cesar_chiffrer(t, 3))
    assert stats.chi2([], []) == float("inf")


def test_ic_langue_vs_vigenere(extrait_fr):
    t = extrait_fr(2000)
    assert stats.indice_coincidence(t) > 0.07
    v = chiffres.vigenere_chiffrer(t, "CRYPTOGRAPHIE")
    assert stats.indice_coincidence(v) < 0.05
    assert stats.ic_moyen_colonnes(v, 13) > 0.065


def test_kasiski_et_friedman(extrait_fr):
    t = extrait_fr(1500)
    v = chiffres.vigenere_chiffrer(t, "SECRET")
    k = stats.kasiski(v)
    assert 6 in k["longueurs_candidates"][:2]
    f = stats.friedman(v)
    assert f["longueurs_candidates"][0] == 6
    assert 2 < f["estimation_longueur"] < 12
    assert stats.kasiski("ABC")["longueurs_candidates"] == []
    assert stats.friedman("AB")["estimation_longueur"] == 20.0


def test_modele_score(extrait_fr, tmp_path):
    m = modele("fr")
    t = extrait_fr(400)
    assert m.score_normalise(t) > 0.7
    rng = np.random.default_rng(0)
    alea = "".join(chr(65 + x) for x in rng.integers(0, 26, 400))
    assert m.score_normalise(alea) < 0.2
    assert m.score("AB") == m.meta["plancher_log10"]
    m2 = ModeleLangue.apprendre([t * 3], "xx")
    m2.calibrer([t * 3], taille=100)
    m2.sauver(tmp_path)
    m3 = ModeleLangue.charger("xx", tmp_path)
    assert m3.meta["langue"] == "xx" and m3.logp.shape == m2.logp.shape
    assert 0 < m.meta["entropie_quadgramme_cond_bits"] < m.meta["entropie_unigramme_bits"]
