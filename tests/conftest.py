import pytest

from vigenere_squad.outils.langue import DOSSIER_MODELES


@pytest.fixture(scope="session", autouse=True)
def modeles_de_langue():
    """Construit les modèles de langue s'ils sont absents (make data)."""
    if not (DOSSIER_MODELES / "quadgrammes_fr.npy").exists():
        from vigenere_squad.evaluation.donnees import construire_modeles, telecharger_et_verifier

        telecharger_et_verifier()
        construire_modeles()


@pytest.fixture(scope="session")
def texte_fr():
    from vigenere_squad.evaluation.donnees import textes_test

    return textes_test("fr")[0]


@pytest.fixture(scope="session")
def extrait_fr(texte_fr):
    import random

    from vigenere_squad.evaluation.donnees import extrait

    return lambda n, graine=1: extrait(random.Random(graine), [texte_fr], n)
