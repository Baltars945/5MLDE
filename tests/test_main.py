import pandas as pd
import pytest

import main
from src import validation


@pytest.fixture
def sans_mlflow(config, monkeypatch):
    monkeypatch.setattr(main.configuration, "charger", lambda chemin: config)
    monkeypatch.setattr(
        main.tracking,
        "journaliser",
        lambda etapes, config: {"run_id": "run-test", "uri_modele": "models:/velos/1"},
    )
    monkeypatch.setattr(
        main.registre,
        "enregistrer",
        lambda run, etapes, decision, config: {
            "nom": "velos-tests",
            "version": "1",
            "alias": decision["qualifie"],
        },
    )
    return config


def test_execution_enchaine_toutes_les_etapes(sans_mlflow, lots):
    resultat = main.executer("config.json")

    assert resultat["lot"] == "lot_000.csv"
    assert resultat["run"]["run_id"] == "run-test"
    assert resultat["version"]["version"] == "1"
    assert pd.read_csv(sans_mlflow["donnees"]["dataset_courant"]).shape[0] == 40


def test_execution_interrompue_par_un_lot_invalide(sans_mlflow, lots):
    dossier = sans_mlflow["donnees"]["dossier_lots"]
    casse = pd.read_csv(f"{dossier}/lot_000.csv")
    casse.loc[0, "cnt"] = -3
    casse.to_csv(f"{dossier}/lot_000.csv", index=False)

    with pytest.raises(validation.LotNonConforme):
        main.executer("config.json")

    assert main.ingestion.lire_curseur(sans_mlflow["donnees"]["curseur"])["dernier_lot"] == -1
