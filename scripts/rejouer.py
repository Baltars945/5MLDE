import argparse

import main
from src import config as configuration
from src import validation


def rejouer(nombre, chemin_config=configuration.CHEMIN_DEFAUT):
    resume = []
    for numero in range(nombre):
        print(f"--- rejeu {numero + 1}/{nombre} ---")
        try:
            resultat = main.executer(chemin_config)
        except IndexError as fin:
            print(f"arret : {fin}")
            break
        except validation.LotNonConforme as rejet:
            print(f"arret : {rejet}")
            break
        resume.append(resultat)

    print("--- resume ---")
    for resultat in resume:
        etat = "champion" if resultat["decision"]["qualifie"] else "refuse"
        print(
            f"{resultat['lot']} version {resultat['version']['version']} "
            f"mae {resultat['decision']['mae']:.0f} {etat}"
        )
    return resume


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rejoue plusieurs lots a la suite")
    parser.add_argument("--lots", type=int, default=3)
    parser.add_argument("--config", default=configuration.CHEMIN_DEFAUT)
    arguments = parser.parse_args()
    rejouer(arguments.lots, arguments.config)
