from sklearn.linear_model import Ridge

from src import entrainement, evaluation, preparation
from tests.conftest import jeu


def test_modele_entraine_predit_le_bon_nombre_de_valeurs(config):
    prepare = preparation.preparer(jeu(60), config)
    entraine = entrainement.entrainer(prepare, config)

    assert len(entraine["modele"].predict(prepare["x_test"])) == len(prepare["x_test"])


def test_type_de_modele_pilote_par_la_configuration(config):
    config["modele"]["type"] = "ridge"
    assert isinstance(entrainement.construire(config), Ridge)


def test_evaluation_renvoie_les_metriques_et_le_gain(config):
    prepare = preparation.preparer(jeu(60), config)
    entraine = entrainement.entrainer(prepare, config)

    resultat = evaluation.evaluer(entraine, prepare)

    assert set(resultat["modele"]) == {"mae", "rmse", "r2"}
    assert resultat["modele"]["mae"] >= 0
    attendu = 1 - resultat["modele"]["mae"] / resultat["baseline"]["mae"]
    assert abs(resultat["gain_vs_baseline"] - attendu) < 1e-9
