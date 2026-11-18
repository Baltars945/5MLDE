import json
import os
from pathlib import Path

CHEMIN_DEFAUT = "config.json"


def charger(chemin=CHEMIN_DEFAUT):
    config = json.loads(Path(chemin).read_text(encoding="utf-8"))
    config["base"]["mot_de_passe"] = os.environ.get("VELOS_DB_PASSWORD", "")
    config["mlflow"]["uri"] = os.environ.get("MLFLOW_TRACKING_URI", config["mlflow"]["uri"])
    return config


def dsn(config):
    base = config["base"]
    return (
        f"host={base['hote']} port={base['port']} dbname={base['nom']} "
        f"user={base['utilisateur']} password={base['mot_de_passe']}"
    )
