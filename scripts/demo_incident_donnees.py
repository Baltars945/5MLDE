import argparse
import json
from pathlib import Path

import requests

from flows.pipeline import FICHIER_ALERTES, entrainement_velos
from scripts import simuler_lot_invalide
from src import base, ingestion
from src import config as configuration


def titre(texte):
    print()
    print(f"== {texte}")


def dernier_rapport(config):
    rapports = sorted(
        Path(config["validation"]["dossier_rapports"]).glob("*.json"),
        key=lambda chemin: chemin.stat().st_mtime,
    )
    return json.loads(rapports[-1].read_text(encoding="utf-8")) if rapports else None


def demo(api, chemin_config):
    config = configuration.charger(chemin_config)
    curseur_avant = ingestion.lire_curseur(config["donnees"]["curseur"])["dernier_lot"]
    version_avant = requests.get(f"{api}/modele", timeout=10).json()["version"]

    titre("injection d'un lot invalide")
    simuler_lot_invalide.injecter(config)

    titre("execution du pipeline sur ce lot")
    echec = None
    try:
        entrainement_velos(chemin_config)
    except Exception as erreur:
        echec = erreur
        print(f"pipeline interrompu : {erreur}")

    titre("rapport de validation")
    rapport = dernier_rapport(config)
    print(f"lot {rapport['lot']} conforme {rapport['conforme']} regles {rapport['regles_evaluees']}")
    for faute in rapport["echecs"]:
        print(f"  regle en echec : {faute['regle']} colonne {faute['colonne']}")

    titre("alerte")
    alertes = Path(FICHIER_ALERTES)
    if alertes.exists():
        print(alertes.read_text(encoding="utf-8").strip().splitlines()[-1])

    titre("etat apres incident")
    curseur_apres = ingestion.lire_curseur(config["donnees"]["curseur"])["dernier_lot"]
    print(f"curseur avant {curseur_avant} apres {curseur_apres}")
    with base.connexion(config) as lien:
        print(
            "derniere execution",
            lien.execute(
                "select lot, statut, etape_en_echec from service.executions_pipeline"
                " order by id desc limit 1"
            ).fetchone(),
        )
    version_apres = requests.get(f"{api}/modele", timeout=10).json()["version"]
    print(f"version servie avant {version_avant} apres {version_apres}")

    titre("restauration du lot")
    simuler_lot_invalide.retirer(config)

    if echec is None:
        raise SystemExit("le lot invalide n'a pas interrompu le pipeline")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Demonstration d'un incident de donnees")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--config", default=configuration.CHEMIN_DEFAUT)
    arguments = parser.parse_args()
    demo(arguments.api, arguments.config)
