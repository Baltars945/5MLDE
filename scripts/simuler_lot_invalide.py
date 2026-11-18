import argparse
from pathlib import Path

import pandas as pd

from src import config as configuration
from src import ingestion

SUFFIXE = ".origine"


def lot_suivant(config):
    donnees = config["donnees"]
    lots = ingestion.lister_lots(donnees["dossier_lots"])
    rang = ingestion.lire_curseur(donnees["curseur"])["dernier_lot"] + 1
    if rang >= len(lots):
        raise IndexError("plus aucun lot a corrompre")
    return lots[rang]


def injecter(config):
    chemin = lot_suivant(config)
    sauvegarde = Path(str(chemin) + SUFFIXE)
    if not sauvegarde.exists():
        sauvegarde.write_bytes(chemin.read_bytes())

    lot = pd.read_csv(chemin)
    lot.loc[0, "cnt"] = -1
    lot.loc[1, "hum"] = 9.9
    lot.loc[2, "dteday"] = lot.loc[3, "dteday"]
    lot.to_csv(chemin, index=False)
    print(f"lot corrompu : {chemin} (sauvegarde dans {sauvegarde.name})")
    return chemin


def retirer(config):
    dossier = Path(config["donnees"]["dossier_lots"])
    restaures = 0
    for sauvegarde in dossier.glob(f"lot_*.csv{SUFFIXE}"):
        origine = Path(str(sauvegarde)[: -len(SUFFIXE)])
        origine.write_bytes(sauvegarde.read_bytes())
        sauvegarde.unlink()
        restaures += 1
        print(f"lot restaure : {origine.name}")
    if not restaures:
        print("aucun lot a restaurer")
    return restaures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Corrompt le prochain lot pour la demo d'incident")
    parser.add_argument("--retirer", action="store_true", help="restaure les lots sauvegardes")
    parser.add_argument("--config", default=configuration.CHEMIN_DEFAUT)
    arguments = parser.parse_args()
    config = configuration.charger(arguments.config)
    retirer(config) if arguments.retirer else injecter(config)
