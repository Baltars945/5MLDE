import argparse

import requests

from flows.pipeline import entrainement_velos
from src import base
from src import config as configuration

OBSERVATION = {
    "season": 2,
    "yr": 1,
    "mnth": 5,
    "holiday": 0,
    "weekday": 3,
    "workingday": 1,
    "weathersit": 1,
    "temp": 0.62,
    "atemp": 0.6,
    "hum": 0.52,
    "windspeed": 0.18,
}


def titre(texte):
    print()
    print(f"== {texte}")


def demo(api, chemin_config):
    config = configuration.charger(chemin_config)

    titre("etat du service avant entrainement")
    print(requests.get(f"{api}/health/ready", timeout=10).json())
    print(requests.get(f"{api}/modele", timeout=10).json())

    titre("execution du pipeline sur le lot suivant")
    resultat = entrainement_velos(chemin_config)
    print(f"lot {resultat['lot']} version {resultat['version']['version']} {resultat['decision']['motif']}")

    titre("rechargement du modele servi")
    print(requests.post(f"{api}/modele/recharger", timeout=60).json())

    titre("prediction unitaire")
    reponse = requests.post(f"{api}/predict", json=OBSERVATION, timeout=30).json()
    print(reponse)

    titre("prediction en lot")
    lot = {"observations": [OBSERVATION, dict(OBSERVATION, weathersit=3, temp=0.3)]}
    print(requests.post(f"{api}/predict/lot", json=lot, timeout=30).json())

    titre("feedback sur la prediction unitaire")
    feedback = {"prediction_id": reponse["prediction_id"], "valeur_reelle": 5200, "commentaire": "demo"}
    print(requests.post(f"{api}/feedback", json=feedback, timeout=30).json())

    titre("traces en base")
    with base.connexion(config) as lien:
        for libelle, requete in (
            ("requetes", "select count(*) from service.requetes"),
            ("predictions", "select count(*) from service.predictions"),
            ("feedbacks", "select count(*) from service.feedbacks"),
            ("executions", "select count(*) from service.executions_pipeline"),
        ):
            print(libelle, lien.execute(requete).fetchone()[0])
        derniere = lien.execute(
            "select lot, statut, round(mae::numeric, 0), decision from service.executions_pipeline"
            " order by id desc limit 1"
        ).fetchone()
        print("derniere execution", derniere)

    titre("a regarder")
    print("mlflow     http://127.0.0.1:5001")
    print("prefect    http://127.0.0.1:4201")
    print("prometheus http://127.0.0.1:9090")
    print("grafana    http://127.0.0.1:3001")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deroule le parcours nominal de bout en bout")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--config", default=configuration.CHEMIN_DEFAUT)
    arguments = parser.parse_args()
    demo(arguments.api, arguments.config)
