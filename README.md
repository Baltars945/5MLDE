# Prevision des locations de velos

Projet final 5MLDE. L'objectif est une chaine MLOps complete et reproductible. Elle couvre
l'ingestion par lots, le controle qualite bloquant, l'entrainement suivi dans MLflow,
l'orchestration Prefect, l'API de prediction, la persistance PostgreSQL et la supervision
Prometheus / Grafana.

Le modele reste simple. C'est un choix assume. La demonstration porte sur la chaine. Elle fonctionne
de bout en bout. Elle se rejoue. Elle s'arrete quand les donnees ne sont pas conformes.

## 1. Sujet et donnees

On prevoit `cnt`, le nombre de locations de velos d'une journee, a partir du calendrier et de la
meteo du jour.

| | |
|---|---|
| Source | UCI Bike Sharing Dataset, fichier `day.csv` |
| Lien | https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset |
| Volume | 731 lignes, du 2011-01-01 au 2012-12-31 |
| Cible | `cnt` |
| Variables | `season`, `yr`, `mnth`, `holiday`, `weekday`, `workingday`, `weathersit`, `temp`, `atemp`, `hum`, `windspeed` |
| Licence | Creative Commons Attribution 4.0 (CC BY 4.0) |
| Citation demandee | Fanaee-T, H. et Gama, J., *Event labeling combining ensemble detectors and background knowledge*, Progress in Artificial Intelligence, 2013 |

Les donnees ne sont pas versionnees dans Git. Un script les telecharge et un autre les decoupe.

Le jeu est historique. Il est **rejoue par lots** pour simuler l'arrivee de nouvelles donnees.
Le premier lot est l'historique de 2011 (365 jours). Les suivants couvrent 30 jours chacun.
Chaque execution du pipeline consomme le lot suivant et l'ajoute au dataset courant.

Les colonnes `casual` et `registered` ne servent pas de variables explicatives. Leur somme est
exactement la cible. Elles sont conservees pour les controles de coherence.

## 2. Architecture

```
day.csv (UCI)
   |
   v
decoupage en lots        data/lots/lot_000.csv ... lot_012.csv
   |
   v
ingestion (curseur)  --> lot suivant + empreinte sha256
   |
   v
validation Great Expectations  --(non conforme)--> arret + alerte + rapport JSON
   |
   v
promotion du lot --> data/courant/dataset.csv
   |
   v
preparation -> entrainement -> evaluation
   |
   v
MLflow : run, params, metriques, dataset, artefacts, modele versionne
   |
   v
qualification (seuils) --> alias "champion" ou refus motive
   |
   v
API FastAPI (charge l'alias champion, le garde en memoire)
   |                                   |
   v                                   v
PostgreSQL (requetes,            Prometheus (/metrics)
predictions, feedbacks,                 |
executions)                             v
   |                                 Grafana
   +---------------------------------->
```

Prefect orchestre le pipeline, avec une tache par etape. Locust mesure la capacite de l'API.

| Composant | Role | Port local |
|---|---|---|
| MLflow | suivi des runs et registre de modeles | 5001 |
| Prefect | orchestration et planification | 4201 |
| PostgreSQL | traces du service et des executions | 5433 |
| Prometheus | collecte des metriques de l'API | 9090 |
| Grafana | dashboards | 3001 |
| API | predictions, feedbacks, metriques | 8000 |

Ces ports sont decales de ceux des TPs. Les deux stacks peuvent ainsi tourner en parallele.

## 3. Installation

Les pre-requis sont Docker Desktop, `uv` et Python 3.12.

```sh
uv python install 3.12
uv sync
docker compose up -d --wait
```

Les mots de passe de la stack locale ont des valeurs par defaut. Elles servent seulement en local,
car les services sont lies a `127.0.0.1`. Pour les remplacer, copier `.env.example` en `.env` et
renseigner `POSTGRES_PASSWORD`, `VELOS_DB_PASSWORD`, `GRAFANA_DB_PASSWORD` et
`GRAFANA_ADMIN_PASSWORD`. Aucun mot de passe de production ne doit etre commite.

## 4. Preparer les donnees

```sh
uv run python -m scripts.telecharger_donnees
uv run python -m scripts.decouper_lots
```

Le resultat attendu est `data/brut/day.csv` (731 lignes), puis 13 lots dans `data/lots/`.

Pour repartir du premier lot, sans toucher a l'historique MLflow :

```sh
uv run python -m scripts.reinitialiser_etat
```

## 5. Entrainer

Execution directe, un lot par appel :

```sh
uv run python main.py --config config.json
```

Execution orchestree par Prefect :

```sh
PREFECT_API_URL=http://127.0.0.1:4201/api uv run python -m flows.pipeline
```

Rejouer plusieurs lots a la suite :

```sh
uv run python -m scripts.rejouer --lots 8
```

Planifier le pipeline (toutes les heures par defaut) :

```sh
PREFECT_API_URL=http://127.0.0.1:4201/api uv run python -m scripts.deployer_flow --cron "0 * * * *"
```

Le flow ajoute ce que l'execution directe n'a pas. Il fait deux tentatives sur l'ingestion et sur le
tracking. Il n'en fait aucune sur la validation. Il met le pretraitement en cache si les donnees et
le code n'ont pas change. Il ecrit une trace de l'execution en base. Il leve une alerte en cas
d'echec.

## 6. Modeles et mise en service

Chaque execution cree un run MLflow et une version du modele. La qualification compare la MAE au
seuil `qualification.mae_maximum`. Elle compare aussi le gain face a une baseline moyenne au seuil
`qualification.gain_minimum_baseline`. La version recoit l'alias `champion` si les deux seuils sont
tenus. Sinon elle est enregistree, taguee et laissee de cote avec son motif de refus.

```sh
uv run python -m scripts.retour_arriere --lister
uv run python -m scripts.retour_arriere                  # revient a la version qualifiee precedente
uv run python -m scripts.retour_arriere --version 9      # force une version
```

Le retour arriere ne touche pas au code. Il deplace un alias. L'API recharge le modele servi avec
`POST /modele/recharger`.

## 7. API de prediction

```sh
uv run python -m scripts.lancer_api --workers 1
uv run python -m scripts.lancer_api --hote 0.0.0.0       # pour que Prometheus puisse scraper
```

| Route | Role |
|---|---|
| `POST /predict` | prediction unitaire |
| `POST /predict/lot` | prediction par lot, borne par `api.taille_lot_maximum` |
| `POST /feedback` | valeur reelle observee pour une prediction |
| `GET /health/live` | le processus repond |
| `GET /health/ready` | modele charge et base joignable, sinon 503 |
| `GET /modele` | version, run et MAE du modele servi |
| `POST /modele/recharger` | recharge l'alias champion |
| `GET /metrics` | metriques Prometheus |

Exemple :

```sh
curl -s -X POST http://127.0.0.1:8000/predict \
  -H "content-type: application/json" \
  -d '{"season":2,"yr":1,"mnth":5,"holiday":0,"weekday":3,"workingday":1,"weathersit":1,"temp":0.62,"atemp":0.6,"hum":0.52,"windspeed":0.18}'
```

Chaque reponse porte la version du modele qui a predit. Pydantic valide les entrees. Un champ
inconnu, une valeur hors bornes ou un lot trop grand renvoient un 422 lisible. L'API ne renvoie
jamais de trace brute. Une prediction n'est renvoyee que si sa trace est ecrite en base. Sinon l'API
repond 503.

Le modele est charge une seule fois au demarrage du worker et garde en memoire.

## 8. Persistance

Le schema `service` est cree dans PostgreSQL par `base/init.sql`.

| Table | Contenu |
|---|---|
| `requetes` | horodatage, route, statut, duree, version servie, erreur |
| `predictions` | entrees, valeur predite, version, requete associee |
| `feedbacks` | valeur reelle par prediction, un seul feedback par prediction |
| `versions_modele` | versions chargees par l'API |
| `executions_pipeline` | lot, statut, etape en echec, run MLflow, MAE, decision |

Deux roles existent. `velos_api` ecrit. `velos_lecture` lit seulement, et Grafana l'utilise.

L'API passe par une reserve de connexions (`base.connexions_max`, 8 par defaut). Elle a ete ajoutee
apres la premiere campagne de charge. L'ouverture d'une connexion par requete provoquait des erreurs
a 25 utilisateurs et 4 workers.

## 9. Supervision

Prometheus scrape `/metrics` toutes les 10 s. Grafana provisionne deux dashboards, versionnes dans
`observabilite/grafana/tableaux/` :

- **Velos - service de prediction** lit Prometheus. Il montre les requetes/s par route, la latence
  p50 et p95, le taux d'erreur, la version servie, le modele charge et la distribution des
  predictions.
- **Velos - exploitation et pipeline** lit PostgreSQL. Il montre les dernieres executions du
  pipeline, les erreurs de l'API, les feedbacks, l'ecart moyen prediction / reel et les versions
  servies.

Grafana ecoute sur http://127.0.0.1:3001. Le compte est `admin`, avec le mot de passe
`GRAFANA_ADMIN_PASSWORD`.

## 10. Charge et dimensionnement

```sh
uv run python -m scripts.campagne_charge --workers 1 4 --paliers 10 25 50 100 --duree 60
```

La campagne demarre l'API elle-meme. Elle joue les paliers avec Locust, en mode sans interface. Elle
mesure le CPU et la memoire du processus et de ses workers. Elle ecrit `rapports/charge/resultats.md`
et `rapports/charge/mesures.json`.

Le detail des paliers mesures est dans `rapports/charge/resultats.md`.

## 11. Demonstrations

Le parcours nominal et deux incidents controles sont decrits pas a pas dans
[docs/DEMO.md](docs/DEMO.md), avec les commandes et ce qu'il faut observer.

```sh
uv run python -m scripts.demo_nominal
uv run python -m scripts.demo_incident_donnees
```

## 12. Tests et lint

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest --cov=src --cov=api --cov=flows --cov-fail-under=75
```

Les tests n'ont besoin d'aucun service. Un fichier SQLite temporaire remplace MLflow. Une fausse
base en memoire remplace PostgreSQL. Un modele factice remplace le vrai modele.

### Integration continue

Le workflow `.github/workflows/ci.yml` se lance a chaque push sur `main` et `develop` et a chaque pull
request. Il enchaine des workflows reutilisables :

| Job | Fichier | Verification |
|---|---|---|
| lint | `lint.yml` | `ruff check` et `ruff format --check` |
| tests | `tests.yml` | `pytest` avec une couverture minimale de 75 %, rapport `coverage.xml` en artefact |
| security | `security.yml` | `pip-audit` sur les dependances verrouillees de `uv.lock` |
| compose | `compose.yml` | validation de `compose.yml`, demarrage de la stack, sante de MLflow, Prefect, Prometheus et Grafana |

Les trois premiers jobs tournent en parallele. Le job `compose` ne demarre que s'ils reussissent. Un
nouveau push sur la meme branche annule l'execution en cours.

## 13. Limites connues

- Le decoupage temporel du test rend la MAE sensible a la saison couverte par le dernier lot. Les
  premiers lots ne qualifient aucun modele. C'est le comportement attendu de la barriere de
  qualification.
- `PROMETHEUS_MULTIPROC_DIR` agrege les metriques entre workers. Il n'est actif que si l'API tourne
  avec plusieurs workers.
- Les mesures de charge viennent d'un poste de developpement, pas d'un serveur dedie.
- L'API tourne en local, hors Docker, pour simplifier les tests de charge.
