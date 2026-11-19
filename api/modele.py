import os

import mlflow
import pandas as pd
from mlflow import MlflowClient

ETAT = {"modele": None, "version": None, "run_id": None, "nom": None, "mae": None}
DELAIS = {"MLFLOW_HTTP_REQUEST_TIMEOUT": "5", "MLFLOW_HTTP_REQUEST_MAX_RETRIES": "1"}


def charger(config):
    for cle, valeur in DELAIS.items():
        os.environ.setdefault(cle, valeur)
    mlflow.set_tracking_uri(config["mlflow"]["uri"])
    nom = config["mlflow"]["modele"]
    alias = config["mlflow"]["alias"]
    version = MlflowClient(config["mlflow"]["uri"]).get_model_version_by_alias(nom, alias)
    ETAT.update(
        {
            "modele": mlflow.pyfunc.load_model(f"models:/{nom}@{alias}"),
            "version": version.version,
            "run_id": version.run_id,
            "nom": nom,
            "mae": version.tags.get("mae"),
        }
    )
    print(f"modele charge : {nom} version {version.version}")
    return etat_public()


def charge():
    return ETAT["modele"] is not None


def etat_public():
    return {cle: valeur for cle, valeur in ETAT.items() if cle != "modele"}


def predire(observations, config):
    cadre = pd.DataFrame(observations)[config["preparation"]["colonnes"]].astype(float)
    return [float(valeur) for valeur in ETAT["modele"].predict(cadre)]
