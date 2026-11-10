import importlib.util
from pathlib import Path

from vigenere_squad.evaluation.donnees import generer_corpus, tranche
from vigenere_squad.evaluation.executer import precision_lettres, sous_ensemble
from vigenere_squad.evaluation.metriques import agreger_lot, longueur_min_90, resume
from vigenere_squad.outils import chiffres


def test_corpus_deterministe_et_coherent():
    a = generer_corpus(42, 1, "standard", (80, 300))
    b = generer_corpus(42, 1, "standard", (80, 300))
    assert a == b and len(a) == 12
    for e in a:
        assert chiffres.dechiffrer(e["procede"], e["chiffre"], e["cle"]) == e["clair"]
        assert e["longueur"] in (80, 300)
    s = generer_corpus(42, 1, "sans_espaces", (80,))
    assert all(" " not in e["clair"] for e in s)
    assert generer_corpus(42, 1, "anglais", (80,))[0]["langue"] == "en"


def test_utilitaires():
    assert tranche(80) == "080-119" and tranche(2000) == "1500+"
    assert precision_lettres("ABCD", "ABCE") == 0.75 and precision_lettres("A", "") == 0.0
    corpus = [{"procede": "cesar", "tranche": "080-119", "id": i} for i in range(5)]
    assert len(sous_ensemble(corpus, 2)) == 2 and len(sous_ensemble(corpus, None)) == 5


def _ligne(rep, ok, procede="cesar", t="080-119"):
    return {"id": f"{procede}{t}", "repetition": rep, "succes_exact": ok, "procede_correct": True,
            "precision_lettres": 1.0 if ok else 0.5, "iterations": 1, "duree_s": 0.1, "rss_max_mo": 10,
            "replis": [], "compteurs": {"appels_outils": 2}, "statut": "accepte", "procede": procede, "tranche": t}


def test_agregation():
    lignes = [_ligne(0, True), _ligne(1, False), _ligne(2, True)]
    m = agreger_lot(lignes)
    assert m["taux_exact"]["moyenne"] == 66.67 and m["taux_exact"]["n_repetitions"] == 3
    assert m["par_procede"]["cesar"]["valeurs"] == [100.0, 0.0, 100.0]
    assert resume([1.0])["ecart_type"] == 0.0
    pt = {"080-119": {"moyenne": 50}, "120-249": {"moyenne": 95}, "250-499": {"moyenne": 100}}
    assert longueur_min_90(pt) == "120-249"
    assert longueur_min_90({"080-119": {"moyenne": 10}}) is None


def test_comparateur():
    spec = importlib.util.spec_from_file_location("comparer", Path(__file__).parents[1] / "scripts" / "comparer.py")
    c = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c)
    v = agreger_lot([_ligne(0, True), _ligne(1, True), _ligne(2, True)])
    pub = {"experiences": {"principal": {"a_baseline": v, "b": v}}, "shannon": {}, "kasiski_autoclave": {}}
    w = agreger_lot([_ligne(0, False), _ligne(1, False), _ligne(2, False)])
    rep = {"experiences": {"principal": {"a_baseline": v, "b": w}}, "shannon": {}, "kasiski_autoclave": {}}
    verdicts = {l[0]: l[1] for l in c.comparer(pub, rep)}
    assert verdicts["principal/a_baseline/taux_exact"] == "OK"
    assert verdicts["principal/b/taux_exact"] == "ÉCART"


def test_reprise_apres_ligne_coupee(tmp_path, monkeypatch):
    """Une évaluation interrompue au milieu d'une ligne reprend sans erreur."""
    import json

    from vigenere_squad.evaluation import executer as ex

    monkeypatch.setattr(ex, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(ex, "TRACES", tmp_path / "traces")
    cfg = ex.charger_config()
    corpus = ex._preparer(ex.sous_ensemble(ex.charger_variante("standard"), 1, [80]))[:3]
    sortie = ex.executer_lot("t", "a_baseline", {"type": "baseline"}, corpus, 0, cfg, journal_console=lambda m: None)
    lignes = sortie.read_text(encoding="utf-8").splitlines()
    sortie.write_text(lignes[0] + "\n" + lignes[1][:25], encoding="utf-8")  # interruption simulée
    ex.executer_lot("t", "a_baseline", {"type": "baseline"}, corpus, 0, cfg, journal_console=lambda m: None)
    reprise = [json.loads(l) for l in sortie.read_text(encoding="utf-8").splitlines()]
    assert [r["id"] for r in reprise] == [e["id"] for e in corpus]
