import os
import subprocess
import time

import mlflow
from mlflow.models import infer_signature

DELAIS = {"MLFLOW_HTTP_REQUEST_TIMEOUT": "10", "MLFLOW_HTTP_REQUEST_MAX_RETRIES": "2"}


def connecter(config):
    for cle, valeur in DELAIS.items():
        os.environ.setdefault(cle, valeur)
    mlflow.set_tracking_uri(config["mlflow"]["uri"])
    mlflow.set_experiment(config["mlflow"]["experience"])


def commit_courant():
    try:
        sortie = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        )
        return sortie.stdout.strip()
    except Exception:
        return "inconnu"


def journaliser(etapes, config):
    lot = etapes["lot"]
    dataset = etapes["dataset"]
    prepare = etapes["prepare"]
    entraine = etapes["entraine"]
    resultats = etapes["resultats"]

    connecter(config)
    debut = time.perf_counter()
    with mlflow.start_run(run_name=lot["nom"]) as run:
        donnees = mlflow.data.from_pandas(
            dataset["donnees"], source=dataset["chemin"], name=f"velos-{lot['nom']}"
        )
        mlflow.log_input(donnees, context="entrainement")
        mlflow.log_params(
            {
                "modele": config["modele"]["type"],
                "n_estimators": config["modele"]["n_estimators"],
                "max_depth": config["modele"]["max_depth"],
                "graine": config["modele"]["graine"],
                "part_test": config["preparation"]["part_test"],
                "colonnes": len(prepare["colonnes"]),
                "lignes_apprentissage": len(prepare["x_apprentissage"]),
                "lignes_test": len(prepare["x_test"]),
            }
        )
        mlflow.log_metrics(
            {
                "mae": resultats["modele"]["mae"],
                "rmse": resultats["modele"]["rmse"],
                "r2": resultats["modele"]["r2"],
                "mae_baseline": resultats["baseline"]["mae"],
                "gain_vs_baseline": resultats["gain_vs_baseline"],
                "lignes_dataset": dataset["lignes"],
                "duree_entrainement_s": etapes.get("duree_entrainement", 0.0),
            }
        )
        mlflow.set_tags(
            {
                "lot": lot["nom"],
                "empreinte_lot": lot["empreinte"],
                "empreinte_dataset": dataset["empreinte"],
                "commit": commit_courant(),
            }
        )
        if etapes.get("chemin_rapport"):
            mlflow.log_artifact(etapes["chemin_rapport"], artifact_path="validation")

        signature = infer_signature(
            prepare["x_apprentissage"], entraine["modele"].predict(prepare["x_apprentissage"])
        )
        modele = mlflow.sklearn.log_model(
            sk_model=entraine["modele"],
            name="modele",
            signature=signature,
            input_example=prepare["x_apprentissage"].head(3),
            serialization_format="cloudpickle",
        )
        mlflow.log_metric("duree_journalisation_s", time.perf_counter() - debut)
        print(f"run mlflow {run.info.run_id}")
        return {"run_id": run.info.run_id, "uri_modele": modele.model_uri}
