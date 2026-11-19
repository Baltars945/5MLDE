import mlflow
from mlflow import MlflowClient


def client(config):
    return MlflowClient(tracking_uri=config["mlflow"]["uri"])


def enregistrer(run, etapes, decision, config):
    nom = config["mlflow"]["modele"]
    mlflow.set_tracking_uri(config["mlflow"]["uri"])
    version = mlflow.register_model(run["uri_modele"], nom)
    connexion = client(config)
    etiquettes = {
        "lot": etapes["lot"]["nom"],
        "mae": f"{decision['mae']:.1f}",
        "gain_vs_baseline": f"{decision['gain']:.3f}",
        "qualifie": "oui" if decision["qualifie"] else "non",
        "motif": decision["motif"],
    }
    for cle, valeur in etiquettes.items():
        connexion.set_model_version_tag(nom, version.version, cle, valeur)

    if decision["qualifie"]:
        connexion.set_registered_model_alias(nom, config["mlflow"]["alias"], version.version)
        print(f"version {version.version} promue {config['mlflow']['alias']}")
    else:
        print(f"version {version.version} enregistree sans alias : {decision['motif']}")
    return {"nom": nom, "version": version.version, "alias": decision["qualifie"]}


def version_servie(config):
    connexion = client(config)
    version = connexion.get_model_version_by_alias(config["mlflow"]["modele"], config["mlflow"]["alias"])
    return {"version": version.version, "run_id": version.run_id, "tags": version.tags}


def versions(config, limite=10):
    connexion = client(config)
    trouvees = connexion.search_model_versions(f"name='{config['mlflow']['modele']}'")
    triees = sorted(trouvees, key=lambda version: int(version.version), reverse=True)
    return triees[:limite]


def deplacer_alias(config, numero):
    connexion = client(config)
    connexion.set_registered_model_alias(config["mlflow"]["modele"], config["mlflow"]["alias"], numero)
    print(f"alias {config['mlflow']['alias']} place sur la version {numero}")
    return numero
