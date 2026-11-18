import argparse

from src import config as configuration
from src import registre


def lister(config):
    try:
        servie = registre.version_servie(config)["version"]
    except Exception:
        servie = None
    print(f"versions de {config['mlflow']['modele']} (alias {config['mlflow']['alias']} : {servie or 'aucun'})")
    for version in registre.versions(config, limite=20):
        marque = f" <= {config['mlflow']['alias']}" if version.version == servie else ""
        print(
            f"version {version.version} mae {version.tags.get('mae', '?')} "
            f"lot {version.tags.get('lot', '?')} qualifie {version.tags.get('qualifie', '?')}{marque}"
        )


def version_precedente(config):
    servie = registre.version_servie(config)
    anciennes = [
        version
        for version in registre.versions(config, limite=50)
        if int(version.version) < int(servie["version"]) and version.tags.get("qualifie") == "oui"
    ]
    if not anciennes:
        raise LookupError("aucune version qualifiee plus ancienne que celle servie")
    return anciennes[0].version


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deplace l'alias champion sans toucher au code")
    parser.add_argument("--lister", action="store_true")
    parser.add_argument("--version", help="numero de version a servir")
    parser.add_argument("--config", default=configuration.CHEMIN_DEFAUT)
    arguments = parser.parse_args()
    config = configuration.charger(arguments.config)

    if arguments.lister:
        lister(config)
    else:
        cible = arguments.version or version_precedente(config)
        servie = registre.version_servie(config)
        print(f"version servie avant : {servie['version']}")
        registre.deplacer_alias(config, cible)
