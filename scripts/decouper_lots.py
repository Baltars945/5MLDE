from pathlib import Path

import pandas as pd

from src import config as configuration


def decouper(config):
    donnees = config["donnees"]
    source = pd.read_csv(donnees["source"])
    dossier = Path(donnees["dossier_lots"])
    dossier.mkdir(parents=True, exist_ok=True)
    for ancien in dossier.glob("lot_*.csv"):
        ancien.unlink()

    taille_historique = donnees["taille_historique"]
    taille_lot = donnees["taille_lot"]
    lots = [source.iloc[:taille_historique]]
    suite = source.iloc[taille_historique:]
    for debut in range(0, len(suite), taille_lot):
        lots.append(suite.iloc[debut : debut + taille_lot])
    if len(lots) > 1 and len(lots[-1]) < taille_lot:
        lots[-2] = pd.concat([lots[-2], lots.pop()])

    chemins = []
    for index, lot in enumerate(lots):
        chemin = dossier / f"lot_{index:03d}.csv"
        lot.to_csv(chemin, index=False)
        chemins.append(chemin)
        print(f"{chemin.name} : {len(lot)} lignes du {lot['dteday'].iloc[0]} au {lot['dteday'].iloc[-1]}")
    print(f"{len(chemins)} lots ecrits dans {dossier}")
    return chemins


if __name__ == "__main__":
    decouper(configuration.charger())
