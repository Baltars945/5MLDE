import pytest

from src import ingestion


def test_premier_lot_puis_curseur_avance(config, lots):
    lot = ingestion.ingerer(config)
    assert lot["nom"] == "lot_000.csv"
    assert lot["lignes"] == 40

    ingestion.promouvoir(lot, config)
    suivant = ingestion.ingerer(config)
    assert suivant["nom"] == "lot_001.csv"


def test_dataset_courant_cumule_sans_doublon(config, lots):
    premier = ingestion.ingerer(config)
    ingestion.promouvoir(premier, config)
    second = ingestion.ingerer(config)
    dataset = ingestion.promouvoir(second, config)

    assert dataset["lignes"] == 60
    assert dataset["donnees"]["dteday"].duplicated().sum() == 0


def test_rejeu_du_meme_lot_ne_duplique_pas(config, lots):
    lot = ingestion.ingerer(config)
    ingestion.promouvoir(lot, config)
    lot["rang"] = 0
    dataset = ingestion.promouvoir(lot, config)

    assert dataset["lignes"] == 40


def test_erreur_quand_plus_de_lot(config, lots):
    for _ in range(2):
        ingestion.promouvoir(ingestion.ingerer(config), config)
    with pytest.raises(IndexError):
        ingestion.ingerer(config)


def test_erreur_quand_aucun_lot(config):
    with pytest.raises(FileNotFoundError):
        ingestion.ingerer(config)
