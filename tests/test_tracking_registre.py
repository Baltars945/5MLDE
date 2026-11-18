import pytest
from mlflow import MlflowClient

from src import registre, tracking

RETENU = {"qualifie": True, "motif": "seuils respectes", "mae": 700.0, "gain": 0.6}
REFUSE = {"qualifie": False, "motif": "gain insuffisant", "mae": 2500.0, "gain": 0.01}


@pytest.fixture
def run(config_mlflow, etapes, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    return tracking.journaliser(etapes, config_mlflow)


def test_run_contient_params_metriques_et_dataset(config_mlflow, run):
    client = MlflowClient(tracking_uri=config_mlflow["mlflow"]["uri"])
    journalise = client.get_run(run["run_id"])

    assert journalise.data.params["modele"] == "random_forest"
    assert journalise.data.metrics["mae"] >= 0
    assert journalise.data.tags["lot"] == "lot_000.csv"
    assert journalise.data.tags["empreinte_dataset"] == "bbb"
    assert journalise.inputs.dataset_inputs


def test_modele_retenu_recoit_l_alias(config_mlflow, etapes, run):
    version = registre.enregistrer(run, etapes, RETENU, config_mlflow)

    servie = registre.version_servie(config_mlflow)
    assert servie["version"] == version["version"]
    assert servie["tags"]["qualifie"] == "oui"


def test_modele_refuse_reste_sans_alias(config_mlflow, etapes, run):
    registre.enregistrer(run, etapes, REFUSE, config_mlflow)

    with pytest.raises(Exception):
        registre.version_servie(config_mlflow)


def test_alias_revient_sur_la_version_precedente(config_mlflow, etapes, run):
    premiere = registre.enregistrer(run, etapes, RETENU, config_mlflow)
    seconde = registre.enregistrer(run, etapes, RETENU, config_mlflow)
    assert registre.version_servie(config_mlflow)["version"] == seconde["version"]

    registre.deplacer_alias(config_mlflow, premiere["version"])

    assert registre.version_servie(config_mlflow)["version"] == premiere["version"]
