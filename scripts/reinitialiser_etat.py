import argparse
import shutil
from pathlib import Path

from src import config as configuration


def reinitialiser(config, rapports=False):
    cibles = [Path(config["donnees"]["curseur"]).parent, Path(config["donnees"]["dataset_courant"]).parent]
    if rapports:
        cibles.append(Path(config["validation"]["dossier_rapports"]))

    for cible in cibles:
        if cible.exists():
            shutil.rmtree(cible)
            print(f"supprime : {cible}")
        else:
            print(f"deja absent : {cible}")
    print("le prochain entrainement repartira du premier lot")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remet le rejeu des lots a zero")
    parser.add_argument("--rapports", action="store_true", help="supprime aussi les rapports de validation")
    parser.add_argument("--config", default=configuration.CHEMIN_DEFAUT)
    arguments = parser.parse_args()
    reinitialiser(configuration.charger(arguments.config), arguments.rapports)
