import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api import metriques, modele
from api.schemas import (
    Feedback,
    LotObservations,
    Observation,
    Prediction,
    ReponseFeedback,
    ReponseLot,
    ReponseModele,
    ReponsePrediction,
)
from src import base
from src import config as configuration

config = configuration.charger()


def publier_etat_modele():
    etat = modele.etat_public()
    metriques.MODELE_CHARGE.set(1 if modele.charge() else 0)
    if etat["version"]:
        metriques.MODELE_VERSION.set(float(etat["version"]))
    return etat


def enregistrer_version_servie(etat):
    base.enregistrer_version(
        config,
        {
            "nom": etat["nom"],
            "version": etat["version"],
            "run_id": etat["run_id"],
            "mae": float(etat["mae"]) if etat["mae"] else None,
        },
    )


@asynccontextmanager
async def cycle_de_vie(application):
    try:
        enregistrer_version_servie(modele.charger(config))
    except Exception as erreur:
        print(f"modele indisponible au demarrage : {erreur}")
    publier_etat_modele()
    yield
    base.fermer_pool()


application = FastAPI(title="Prevision des locations de velos", version="1.0", lifespan=cycle_de_vie)


@application.middleware("http")
async def chronometrer(requete: Request, suivant):
    requete.state.debut = time.perf_counter()
    reponse = await suivant(requete)
    if requete.url.path != "/metrics":
        metriques.REQUETES.labels(requete.url.path, str(reponse.status_code)).inc()
        metriques.DUREE.labels(requete.url.path).observe(duree_ms(requete) / 1000)
    return reponse


def duree_ms(requete):
    return (time.perf_counter() - getattr(requete.state, "debut", time.perf_counter())) * 1000


def trace_de(requete, statut, erreur=None):
    return {
        "id": str(uuid.uuid4()),
        "route": requete.url.path,
        "statut": statut,
        "duree_ms": duree_ms(requete),
        "version": modele.etat_public()["version"],
        "erreur": erreur,
    }


def tracer_echec(requete, statut, erreur):
    try:
        base.tracer_requete(config, trace_de(requete, statut, erreur))
    except base.ERREURS as panne:
        metriques.ERREURS_BASE.inc()
        print(f"trace non ecrite : {str(panne).strip()}")


def exiger_modele(requete):
    if modele.charge():
        return
    tracer_echec(requete, 503, "modele indisponible")
    raise HTTPException(status_code=503, detail="modele indisponible")


def enregistrer_predictions(requete, entrees, valeurs):
    trace = trace_de(requete, 200)
    couples = list(zip(entrees, valeurs, strict=True))
    try:
        identifiants = base.tracer_requete(config, trace, couples)
    except base.ERREURS as panne:
        metriques.ERREURS_BASE.inc()
        print(f"prediction non tracee : {str(panne).strip()}")
        tracer_echec(requete, 503, "trace indisponible")
        raise HTTPException(status_code=503, detail="trace indisponible") from panne

    metriques.PREDICTIONS.inc(len(valeurs))
    for valeur in valeurs:
        metriques.LOCATIONS_PREVUES.observe(valeur)
    return trace["id"], identifiants


@application.post("/predict", response_model=ReponsePrediction)
def predire(observation: Observation, requete: Request):
    exiger_modele(requete)
    entrees = [observation.model_dump()]
    valeurs = modele.predire(entrees, config)
    requete_id, identifiants = enregistrer_predictions(requete, entrees, valeurs)
    return ReponsePrediction(
        requete_id=requete_id,
        version_modele=modele.etat_public()["version"],
        prediction_id=identifiants[0],
        locations_prevues=round(valeurs[0], 1),
    )


@application.post("/predict/lot", response_model=ReponseLot)
def predire_lot(lot: LotObservations, requete: Request):
    exiger_modele(requete)
    maximum = config["api"]["taille_lot_maximum"]
    if len(lot.observations) > maximum:
        tracer_echec(requete, 422, f"lot de {len(lot.observations)} au-dela de {maximum}")
        raise HTTPException(status_code=422, detail=f"lot limite a {maximum} observations")

    entrees = [observation.model_dump() for observation in lot.observations]
    valeurs = modele.predire(entrees, config)
    requete_id, identifiants = enregistrer_predictions(requete, entrees, valeurs)
    return ReponseLot(
        requete_id=requete_id,
        version_modele=modele.etat_public()["version"],
        predictions=[
            Prediction(prediction_id=identifiant, locations_prevues=round(valeur, 1))
            for identifiant, valeur in zip(identifiants, valeurs, strict=True)
        ],
    )


@application.post("/feedback", response_model=ReponseFeedback)
def deposer_feedback(feedback: Feedback, requete: Request):
    try:
        identifiant = base.enregistrer_feedback(
            config, feedback.prediction_id, feedback.valeur_reelle, feedback.commentaire
        )
    except base.ERREURS as panne:
        metriques.ERREURS_BASE.inc()
        tracer_echec(requete, 503, f"feedback non ecrit : {str(panne).strip()[:200]}")
        raise HTTPException(status_code=503, detail="base indisponible") from panne

    if identifiant is None:
        tracer_echec(requete, 404, f"prediction {feedback.prediction_id} inconnue")
        raise HTTPException(status_code=404, detail="prediction inconnue")

    metriques.FEEDBACKS.inc()
    base.tracer_requete(config, trace_de(requete, 200))
    return ReponseFeedback(feedback_id=identifiant, prediction_id=feedback.prediction_id)


@application.get("/health/live")
def vivant():
    return {"statut": "vivant"}


@application.get("/health/ready")
def pret(requete: Request):
    details = {"modele": modele.charge(), "base": base.joignable(config)}
    if all(details.values()):
        return {"statut": "pret", **details}
    tracer_echec(requete, 503, f"non pret : {details}")
    return JSONResponse(status_code=503, content={"statut": "non pret", **details})


@application.get("/modele", response_model=ReponseModele)
def decrire_modele(requete: Request):
    exiger_modele(requete)
    etat = modele.etat_public()
    return ReponseModele(
        nom=etat["nom"],
        version=etat["version"],
        run_id=etat["run_id"],
        alias=config["mlflow"]["alias"],
        mae=etat["mae"],
    )


@application.post("/modele/recharger")
def recharger_modele(requete: Request):
    try:
        etat = modele.charger(config)
    except Exception as erreur:
        tracer_echec(requete, 503, f"rechargement impossible : {erreur}")
        raise HTTPException(status_code=503, detail="rechargement impossible") from erreur

    publier_etat_modele()
    try:
        enregistrer_version_servie(etat)
    except base.ERREURS as panne:
        metriques.ERREURS_BASE.inc()
        print(f"version servie non tracee : {str(panne).strip()}")
    return {"version": etat["version"], "run_id": etat["run_id"]}


@application.get("/metrics")
def exposer_metriques():
    corps, type_contenu = metriques.exposer()
    return Response(content=corps, media_type=type_contenu)


@application.exception_handler(RequestValidationError)
async def entrees_invalides(requete: Request, erreur: RequestValidationError):
    details = [
        {"champ": ".".join(str(partie) for partie in faute["loc"]), "message": faute["msg"]}
        for faute in erreur.errors()[:5]
    ]
    tracer_echec(requete, 422, "entrees invalides")
    return JSONResponse(status_code=422, content={"erreur": "entrees invalides", "details": details})


@application.exception_handler(Exception)
async def erreur_interne(requete: Request, erreur: Exception):
    tracer_echec(requete, 500, type(erreur).__name__)
    return JSONResponse(status_code=500, content={"erreur": "erreur interne"})
