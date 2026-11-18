# Demonstration de bout en bout

Ce guide donne trois scenarios. Le premier montre le fonctionnement nominal. Le deuxieme corrompt
un lot de donnees. Le troisieme coupe une dependance. Chaque scenario donne les commandes a lancer
et ce qu'il faut observer.

## 0. Mise en route

```sh
docker compose up -d --wait
uv run python -m scripts.telecharger_donnees
uv run python -m scripts.decouper_lots
uv run python -m scripts.reinitialiser_etat          # repart du premier lot
uv run python -m scripts.rejouer --lots 8          # amene un premier modele champion
uv run python -m scripts.lancer_api --hote 0.0.0.0 # dans un terminal dedie
```

Quatre interfaces servent a l'observation. MLflow http://127.0.0.1:5001, Prefect
http://127.0.0.1:4201, Prometheus http://127.0.0.1:9090 et Grafana http://127.0.0.1:3001.

## 1. Fonctionnement nominal

```sh
PREFECT_API_URL=http://127.0.0.1:4201/api uv run python -m scripts.demo_nominal
```

Le script enchaine sept etapes. Il lit l'etat du service. Il execute le pipeline sur le lot suivant.
Il recharge le modele. Il demande une prediction unitaire, puis une prediction en lot. Il envoie un
feedback. Il compte les traces ecrites en base.

A observer :

| Ou | Quoi |
|---|---|
| Sortie du script | le lot consomme, la version creee, la decision de qualification |
| MLflow | un nouveau run avec params, metriques, dataset en entree et rapport de validation en artefact. Une nouvelle version du modele est taguee |
| MLflow / Models | l'alias `champion` sur la derniere version qualifiee |
| Prefect | le flow `entrainement-velos` en etat Completed, une tache par etape |
| Reponses de l'API | `version_modele` identique a la version champion |
| Grafana, dashboard service | requetes/s, latence, version servie |
| Grafana, dashboard exploitation | derniere execution en `succes`, predictions et feedbacks qui montent |

## 2. Incident controle : lot de donnees invalide

```sh
PREFECT_API_URL=http://127.0.0.1:4201/api uv run python -m scripts.demo_incident_donnees
```

Le script corrompt le prochain lot. Il pose une valeur de `cnt` negative, une humidite a 9.9 et une
date dupliquee. Il lance le pipeline. Il montre les consequences. Il restaure le lot a la fin.

Ce qui doit se produire :

- Le pipeline s'arrete a l'etape `validation`. Le pretraitement n'a pas lieu.
- Le rapport JSON de `rapports/validation/` liste les regles en echec.
- Une ligne est ajoutee dans `rapports/alertes.log`.
- La tache de validation n'est pas retentee. Un lot invalide reste invalide.
- Le curseur ne bouge pas. Le lot n'entre pas dans le dataset courant.
- Aucune nouvelle version de modele n'est creee.
- L'API sert toujours la version d'avant l'incident.
- `service.executions_pipeline` contient une ligne `echec`. L'etape en echec est `validation`. Le
  dashboard exploitation la montre.

La reprise est simple. Le lot est restaure. La commande d'entrainement se relance normalement.

## 3. Incident controle : dependance indisponible

### 3.1 PostgreSQL arrete

```sh
docker compose stop postgres
curl -i http://127.0.0.1:8000/health/live
curl -i http://127.0.0.1:8000/health/ready
curl -i -X POST http://127.0.0.1:8000/predict -H "content-type: application/json" \
  -d '{"season":2,"yr":1,"mnth":5,"holiday":0,"weekday":3,"workingday":1,"weathersit":1,"temp":0.62,"atemp":0.6,"hum":0.52,"windspeed":0.18}'
docker compose start postgres
```

Attendu :

- `/health/live` reste a 200. Le processus repond.
- `/health/ready` passe a 503 avec `"base": false`.
- `/predict` repond 503 `trace indisponible`. L'API ne renvoie aucune prediction sans trace.
- Le compteur `velos_erreurs_base_total` augmente. Le dashboard service le montre.
- `/health/ready` repasse a 200 apres `docker compose start postgres`. L'API n'a pas besoin de
  redemarrer.

### 3.2 MLflow arrete

```sh
docker compose stop mlflow
curl -i -X POST http://127.0.0.1:8000/modele/recharger
curl -s -X POST http://127.0.0.1:8000/predict -H "content-type: application/json" -d '{...}'
PREFECT_API_URL=http://127.0.0.1:4201/api uv run python -m flows.pipeline
docker compose start mlflow
```

Attendu :

- `POST /modele/recharger` repond 503. Le registre est injoignable.
- Les predictions continuent. Le modele deja charge reste en memoire. La version servie ne change
  pas.
- Le pipeline echoue a l'etape `tracking` apres deux tentatives. Une alerte est ecrite.
  `service.executions_pipeline` enregistre `etape_en_echec = tracking`.
- Aucun modele non trace n'est promu.

## 4. Retour arriere sur la version servie

```sh
uv run python -m scripts.retour_arriere --lister
uv run python -m scripts.retour_arriere
curl -s -X POST http://127.0.0.1:8000/modele/recharger
curl -s http://127.0.0.1:8000/modele
```

Attendu :

- L'alias `champion` revient sur la version qualifiee precedente.
- L'API sert cette version apres rechargement.
- Le changement se lit dans `service.versions_modele`. Le panneau "Versions servies par l'API" le
  montre aussi.
