import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from prefect import flow, task
from prefect.cache_policies import INPUTS, TASK_SOURCE

from src import (
    base,
    entrainement,
    evaluation,
    ingestion,
    preparation,
    qualification,
    registre,
    tracking,
    validation,
)
from src import config as configuration

FICHIER_ALERTES = "rapports/alertes.log"


def alerter(message):
    ligne = f"{datetime.now().isoformat(timespec='seconds')} ALERTE {message}"
    chemin = Path(FICHIER_ALERTES)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("a", encoding="utf-8") as fichier:
        print(ligne, file=fichier)
    print(ligne)
    return ligne


def ouvrir_trace(config):
    try:
        return base.ouvrir_execution(config, None)
    except base.ERREURS as erreur:
        alerter(f"trace d'execution indisponible : {str(erreur).strip()}")
        return None


def fermer_trace(config, execution, details):
    if execution is None:
        return
    try:
        base.fermer_execution(config, execution, details)
    except base.ERREURS as erreur:
        alerter(f"trace d'execution non fermee : {str(erreur).strip()}")


@task(retries=2, retry_delay_seconds=5)
def etape_ingestion(config):
    return ingestion.ingerer(config)


@task(retries=0)
def etape_validation(lot, config):
    return validation.valider(lot, config)


@task
def etape_promotion(lot, config):
    return ingestion.promouvoir(lot, config)


@task(cache_policy=INPUTS + TASK_SOURCE, cache_expiration=timedelta(hours=2))
def etape_preparation(empreinte, chemin, config):
    print(f"preparation du dataset {empreinte}")
    return preparation.preparer(pd.read_csv(chemin), config)


@task
def etape_entrainement(prepare, config):
    debut = time.perf_counter()
    entraine = entrainement.entrainer(prepare, config)
    return entraine, time.perf_counter() - debut


@task
def etape_evaluation(entraine, prepare):
    return evaluation.evaluer(entraine, prepare)


@task(retries=2, retry_delay_seconds=10)
def etape_tracking(etapes, config):
    return tracking.journaliser(etapes, config)


@task
def etape_registre(run, etapes, decision, config):
    return registre.enregistrer(run, etapes, decision, config)


@flow(name="entrainement-velos")
def entrainement_velos(chemin_config=configuration.CHEMIN_DEFAUT):
    config = configuration.charger(chemin_config)
    execution = ouvrir_trace(config)
    etape = "ingestion"
    try:
        lot = etape_ingestion(config)

        etape = "validation"
        controle = etape_validation(lot, config)

        etape = "promotion"
        dataset = etape_promotion(lot, config)

        etape = "preparation"
        prepare = etape_preparation(dataset["empreinte"], dataset["chemin"], config)

        etape = "entrainement"
        entraine, duree = etape_entrainement(prepare, config)

        etape = "evaluation"
        resultats = etape_evaluation(entraine, prepare)

        etape = "tracking"
        etapes = {
            "lot": lot,
            "dataset": dataset,
            "prepare": prepare,
            "entraine": entraine,
            "resultats": resultats,
            "chemin_rapport": controle["chemin_rapport"],
            "duree_entrainement": duree,
        }
        run = etape_tracking(etapes, config)

        etape = "qualification"
        decision = qualification.qualifier(resultats, config)

        etape = "registre"
        version = etape_registre(run, etapes, decision, config)
    except Exception as erreur:
        alerter(f"{etape} en echec sur {chemin_config} : {erreur}")
        fermer_trace(
            config,
            execution,
            {
                "statut": "echec",
                "etape_en_echec": etape,
                "run_id": None,
                "mae": None,
                "decision": None,
                "message": str(erreur)[:500],
                "lot": None,
            },
        )
        raise

    fermer_trace(
        config,
        execution,
        {
            "statut": "succes",
            "etape_en_echec": None,
            "run_id": run["run_id"],
            "mae": decision["mae"],
            "decision": "champion" if decision["qualifie"] else "refuse",
            "message": decision["motif"],
            "lot": lot["nom"],
        },
    )
    return {"lot": lot["nom"], "run": run, "decision": decision, "version": version}


if __name__ == "__main__":
    entrainement_velos()
