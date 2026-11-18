import argparse
import os
import shutil
from pathlib import Path

import uvicorn

DOSSIER_METRIQUES = "data/metriques"


def preparer_metriques(dossier=DOSSIER_METRIQUES):
    chemin = Path(dossier)
    if chemin.exists():
        shutil.rmtree(chemin)
    chemin.mkdir(parents=True)
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = str(chemin.resolve())
    print(f"metriques multiprocessus dans {chemin}")
    return chemin


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lance l'api de prediction")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--hote", default="127.0.0.1", help="0.0.0.0 pour laisser prometheus scraper")
    arguments = parser.parse_args()

    if arguments.workers > 1:
        preparer_metriques()
    print(f"api sur {arguments.hote}:{arguments.port} avec {arguments.workers} worker(s)")
    uvicorn.run(
        "api.main:application",
        host=arguments.hote,
        port=arguments.port,
        workers=arguments.workers,
        log_level="warning",
    )
