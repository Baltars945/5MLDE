# Prevision des locations de velos

Projet final 5MLDE. L'objectif est une chaine MLOps complete et reproductible. Elle couvre
l'ingestion, le controle qualite, l'entrainement suivi dans MLflow, l'orchestration Prefect,
l'API de prediction, la persistance PostgreSQL et la supervision Prometheus / Grafana.

Le modele reste simple. C'est un choix assume. La chaine doit fonctionner de bout en bout.
C'est le seul objectif.

## Donnees

Jeu de donnees UCI Bike Sharing (fichier `day.csv`, 731 jours, 2011-2012).
Source : https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset

Les donnees ne sont pas versionnees. Un script les telecharge.

## Installation

```sh
uv python install 3.12
uv sync
```
