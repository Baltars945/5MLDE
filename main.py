import argparse
import sys
import time

from src import config as configuration
from src import (
    entrainement,
    evaluation,
    ingestion,
    preparation,
    qualification,
    registre,
    tracking,
    validation,
)


def executer(chemin_config=configuration.CHEMIN_DEFAUT):
    config = configuration.charger(chemin_config)
    lot = ingestion.ingerer(config)
    controle = validation.valider(lot, config)
    dataset = ingestion.promouvoir(lot, config)
    prepare = preparation.preparer(dataset["donnees"], config)

    debut = time.perf_counter()
    entraine = entrainement.entrainer(prepare, config)
    duree = time.perf_counter() - debut
    resultats = evaluation.evaluer(entraine, prepare)

    etapes = {
        "lot": lot,
        "dataset": dataset,
        "prepare": prepare,
        "entraine": entraine,
        "resultats": resultats,
        "chemin_rapport": controle["chemin_rapport"],
        "duree_entrainement": duree,
    }
    run = tracking.journaliser(etapes, config)
    decision = qualification.qualifier(resultats, config)
    version = registre.enregistrer(run, etapes, decision, config)
    return {"lot": lot["nom"], "run": run, "decision": decision, "version": version}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rejoue le lot suivant et entraine le modele")
    parser.add_argument("--config", default=configuration.CHEMIN_DEFAUT)
    try:
        executer(parser.parse_args().config)
    except validation.LotNonConforme as rejet:
        print(f"entrainement interrompu : {rejet}")
        sys.exit(1)
