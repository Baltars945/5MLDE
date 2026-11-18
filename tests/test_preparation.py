import numpy as np
import pandas as pd

from src import preparation
from tests.conftest import jeu


def test_nettoyage_retire_doublons_et_valeurs_manquantes(config):
    donnees = jeu(30)
    donnees = pd.concat([donnees, donnees.iloc[[0]]], ignore_index=True)
    donnees.loc[5, "temp"] = np.nan

    propre = preparation.nettoyer(donnees, config)

    assert propre["dteday"].duplicated().sum() == 0
    assert propre["temp"].isna().sum() == 0
    assert len(propre) == 29


def test_separation_respecte_la_chronologie(config):
    prepare = preparation.preparer(jeu(50), config)

    assert len(prepare["x_apprentissage"]) == 40
    assert len(prepare["x_test"]) == 10
    assert prepare["y_apprentissage"].index.max() < prepare["y_test"].index.min()


def test_variables_limitees_aux_colonnes_configurees(config):
    prepare = preparation.preparer(jeu(50), config)

    assert list(prepare["x_apprentissage"].columns) == config["preparation"]["colonnes"]
    assert "cnt" not in prepare["x_apprentissage"].columns
