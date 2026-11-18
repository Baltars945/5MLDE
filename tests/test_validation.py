from pathlib import Path

import pandas as pd
import pytest

from src import ingestion, validation
from tests.conftest import jeu


def lot_depuis(donnees, nom="lot_test.csv"):
    return {"rang": 0, "nom": nom, "chemin": nom, "lignes": len(donnees), "empreinte": "test", "donnees": donnees}


def test_lot_conforme_accepte(config):
    sortie = validation.valider(lot_depuis(jeu(30)), config)

    assert sortie["rapport"]["conforme"] is True
    assert sortie["rapport"]["echecs"] == []


def test_lot_trop_petit_rejete(config):
    with pytest.raises(validation.LotNonConforme):
        validation.valider(lot_depuis(jeu(5)), config)


def test_valeur_hors_bornes_rejetee(config):
    donnees = jeu(30)
    donnees.loc[3, "hum"] = 4.2

    with pytest.raises(validation.LotNonConforme):
        validation.valider(lot_depuis(donnees), config)


def test_date_dupliquee_rejetee(config):
    donnees = jeu(30)
    donnees.loc[4, "dteday"] = donnees.loc[5, "dteday"]

    with pytest.raises(validation.LotNonConforme):
        validation.valider(lot_depuis(donnees), config)


def test_colonne_manquante_rejetee(config):
    donnees = jeu(30).drop(columns=["windspeed"])

    with pytest.raises(validation.LotNonConforme):
        validation.valider(lot_depuis(donnees), config)


def test_rapport_ecrit_meme_en_cas_d_echec(config):
    donnees = jeu(30)
    donnees.loc[0, "cnt"] = -10

    with pytest.raises(validation.LotNonConforme):
        validation.valider(lot_depuis(donnees), config)

    rapports = list(Path(config["validation"]["dossier_rapports"]).glob("*.json"))
    assert len(rapports) == 1


def test_lot_invalide_ne_touche_pas_le_dataset_courant(config, lots):
    dossier = Path(config["donnees"]["dossier_lots"])
    casse = pd.read_csv(dossier / "lot_001.csv")
    casse.loc[0, "cnt"] = -1
    casse.to_csv(dossier / "lot_001.csv", index=False)

    ingestion.promouvoir(ingestion.ingerer(config), config)
    lignes_avant = len(pd.read_csv(config["donnees"]["dataset_courant"]))
    curseur_avant = ingestion.lire_curseur(config["donnees"]["curseur"])["dernier_lot"]

    with pytest.raises(validation.LotNonConforme):
        validation.valider(ingestion.ingerer(config), config)

    assert len(pd.read_csv(config["donnees"]["dataset_courant"])) == lignes_avant
    assert ingestion.lire_curseur(config["donnees"]["curseur"])["dernier_lot"] == curseur_avant
