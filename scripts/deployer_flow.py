import argparse

from flows.pipeline import entrainement_velos

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sert le flow avec une planification")
    parser.add_argument("--nom", default="horaire")
    parser.add_argument("--cron", default="0 * * * *")
    arguments = parser.parse_args()
    print(f"deploiement {arguments.nom} planifie sur {arguments.cron}")
    entrainement_velos.serve(name=arguments.nom, cron=arguments.cron)
