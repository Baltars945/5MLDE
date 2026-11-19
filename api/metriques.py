import os

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)

REQUETES = Counter("velos_requetes_total", "requetes traitees", ["route", "statut"])
DUREE = Histogram(
    "velos_duree_requete_secondes",
    "duree de traitement des requetes",
    ["route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
PREDICTIONS = Counter("velos_predictions_total", "predictions produites")
FEEDBACKS = Counter("velos_feedbacks_total", "feedbacks recus")
ERREURS_BASE = Counter("velos_erreurs_base_total", "echecs d'ecriture des traces")
MODELE_CHARGE = Gauge("velos_modele_charge", "1 si un modele est charge", multiprocess_mode="livemax")
MODELE_VERSION = Gauge("velos_modele_version", "version du modele servi", multiprocess_mode="livemax")
LOCATIONS_PREVUES = Histogram(
    "velos_locations_prevues",
    "distribution des predictions",
    buckets=(500, 1500, 2500, 3500, 4500, 5500, 6500, 7500, 8500),
)


def exposer():
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        registre = CollectorRegistry()
        multiprocess.MultiProcessCollector(registre)
    else:
        registre = REGISTRY
    return generate_latest(registre), CONTENT_TYPE_LATEST
