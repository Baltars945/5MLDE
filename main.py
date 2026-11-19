import argparse

from src import config as configuration
from src import entrainement, evaluation, ingestion, preparation


def executer(chemin_config=configuration.CHEMIN_DEFAUT):
    config = configuration.charger(chemin_config)
    lot = ingestion.ingerer(config)
    dataset = ingestion.promouvoir(lot, config)
    prepare = preparation.preparer(dataset["donnees"], config)
    entraine = entrainement.entrainer(prepare, config)
    return evaluation.evaluer(entraine, prepare)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rejoue le lot suivant et entraine le modele")
    parser.add_argument("--config", default=configuration.CHEMIN_DEFAUT)
    executer(parser.parse_args().config)
