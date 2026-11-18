import json
from pathlib import Path

import pandas as pd
import pytest


def jeu(lignes=80, debut="2011-01-01", premier_instant=1):
    dates = pd.date_range(debut, periods=lignes, freq="D")
    return pd.DataFrame(
        {
            "instant": range(premier_instant, premier_instant + lignes),
            "dteday": dates.strftime("%Y-%m-%d"),
            "season": [1 + i % 4 for i in range(lignes)],
            "yr": 0,
            "mnth": dates.month,
            "holiday": 0,
            "weekday": dates.day_of_week,
            "workingday": [i % 7 not in (5, 6) and 1 or 0 for i in range(lignes)],
            "weathersit": [1 + i % 3 for i in range(lignes)],
            "temp": [0.2 + (i % 10) / 20 for i in range(lignes)],
            "atemp": [0.25 + (i % 10) / 20 for i in range(lignes)],
            "hum": [0.4 + (i % 5) / 20 for i in range(lignes)],
            "windspeed": [0.1 + (i % 4) / 20 for i in range(lignes)],
            "casual": [100 + i for i in range(lignes)],
            "registered": [900 + 10 * (i % 20) for i in range(lignes)],
            "cnt": [1000 + 10 * (i % 20) + i for i in range(lignes)],
        }
    )


@pytest.fixture
def config(tmp_path):
    config = json.loads(Path("config.json").read_text(encoding="utf-8"))
    config["donnees"].update(
        {
            "source": str(tmp_path / "day.csv"),
            "dossier_lots": str(tmp_path / "lots"),
            "curseur": str(tmp_path / "etat/curseur.json"),
            "dataset_courant": str(tmp_path / "courant/dataset.csv"),
            "taille_historique": 40,
            "taille_lot": 20,
        }
    )
    config["validation"]["dossier_rapports"] = str(tmp_path / "rapports")
    config["modele"]["n_estimators"] = 10
    return config


@pytest.fixture
def lots(config):
    dossier = Path(config["donnees"]["dossier_lots"])
    dossier.mkdir(parents=True, exist_ok=True)
    jeu(40).to_csv(dossier / "lot_000.csv", index=False)
    jeu(20, debut="2011-02-10", premier_instant=41).to_csv(dossier / "lot_001.csv", index=False)
    return dossier


@pytest.fixture
def config_mlflow(config, tmp_path):
    config["mlflow"]["uri"] = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    config["mlflow"]["experience"] = "tests"
    config["mlflow"]["modele"] = "velos-tests"
    return config


@pytest.fixture
def etapes(config, tmp_path):
    from src import entrainement, evaluation, preparation

    donnees = jeu(60)
    chemin = tmp_path / "dataset.csv"
    donnees.to_csv(chemin, index=False)
    prepare = preparation.preparer(donnees, config)
    entraine = entrainement.entrainer(prepare, config)
    return {
        "lot": {"rang": 0, "nom": "lot_000.csv", "lignes": 60, "empreinte": "aaa"},
        "dataset": {
            "donnees": donnees,
            "chemin": str(chemin),
            "lignes": len(donnees),
            "empreinte": "bbb",
        },
        "prepare": prepare,
        "entraine": entraine,
        "resultats": evaluation.evaluer(entraine, prepare),
        "chemin_rapport": None,
        "duree_entrainement": 0.4,
    }
