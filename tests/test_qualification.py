from src import qualification

RESULTATS = {"modele": {"mae": 800.0}, "baseline": {"mae": 2000.0}, "gain_vs_baseline": 0.6}


def test_modele_sous_les_seuils_est_retenu(config):
    decision = qualification.qualifier(RESULTATS, config)

    assert decision["qualifie"] is True
    assert decision["motif"] == "seuils respectes"


def test_mae_trop_haute_refusee(config):
    resultats = dict(RESULTATS, modele={"mae": 5000.0})

    decision = qualification.qualifier(resultats, config)

    assert decision["qualifie"] is False
    assert "mae" in decision["motif"]


def test_gain_insuffisant_refuse(config):
    resultats = dict(RESULTATS, gain_vs_baseline=0.05)

    decision = qualification.qualifier(resultats, config)

    assert decision["qualifie"] is False
    assert "gain" in decision["motif"]


def test_les_deux_motifs_sont_cumules(config):
    resultats = dict(RESULTATS, modele={"mae": 5000.0}, gain_vs_baseline=-0.2)

    decision = qualification.qualifier(resultats, config)

    assert decision["qualifie"] is False
    assert " et " in decision["motif"]
