import psycopg
import pytest
from fastapi.testclient import TestClient

from api import main, modele

OBSERVATION = {
    "season": 1,
    "yr": 1,
    "mnth": 3,
    "holiday": 0,
    "weekday": 2,
    "workingday": 1,
    "weathersit": 1,
    "temp": 0.5,
    "atemp": 0.5,
    "hum": 0.5,
    "windspeed": 0.2,
}


class ModeleFactice:
    def predict(self, cadre):
        return [4200.0 + index for index in range(len(cadre))]


@pytest.fixture
def base_en_memoire(monkeypatch):
    memoire = {"requetes": [], "predictions": [], "feedbacks": {}}

    def tracer_requete(config, trace, predictions=()):
        memoire["requetes"].append(trace)
        identifiants = []
        for entrees, valeur in predictions:
            memoire["predictions"].append((entrees, valeur))
            identifiants.append(len(memoire["predictions"]))
        return identifiants

    def enregistrer_feedback(config, prediction_id, valeur, commentaire):
        if prediction_id > len(memoire["predictions"]):
            return None
        memoire["feedbacks"][prediction_id] = valeur
        return prediction_id

    monkeypatch.setattr(main.base, "tracer_requete", tracer_requete)
    monkeypatch.setattr(main.base, "enregistrer_feedback", enregistrer_feedback)
    monkeypatch.setattr(main.base, "enregistrer_version", lambda config, version: None)
    monkeypatch.setattr(main.base, "joignable", lambda config: True)
    return memoire


@pytest.fixture
def client(monkeypatch, base_en_memoire):
    monkeypatch.setitem(modele.ETAT, "modele", ModeleFactice())
    monkeypatch.setitem(modele.ETAT, "version", "7")
    monkeypatch.setitem(modele.ETAT, "run_id", "run-test")
    monkeypatch.setitem(modele.ETAT, "nom", "velos-tests")
    monkeypatch.setitem(modele.ETAT, "mae", "700.0")
    monkeypatch.setattr(modele, "charger", lambda config: modele.etat_public())
    with TestClient(main.application) as client:
        yield client


def test_prediction_unitaire_renvoie_la_version_servie(client):
    reponse = client.post("/predict", json=OBSERVATION)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["version_modele"] == "7"
    assert corps["locations_prevues"] == 4200.0
    assert corps["prediction_id"] == 1


def test_lot_et_unitaire_donnent_le_meme_resultat(client):
    unitaire = client.post("/predict", json=OBSERVATION).json()
    lot = client.post("/predict/lot", json={"observations": [OBSERVATION]}).json()

    assert lot["predictions"][0]["locations_prevues"] == unitaire["locations_prevues"]
    assert lot["version_modele"] == unitaire["version_modele"]


def test_lot_trop_grand_refuse(client):
    lot = {"observations": [OBSERVATION] * (main.config["api"]["taille_lot_maximum"] + 1)}

    reponse = client.post("/predict/lot", json=lot)

    assert reponse.status_code == 422


def test_entree_hors_bornes_refusee_sans_trace_brute(client):
    reponse = client.post("/predict", json=dict(OBSERVATION, hum=3.4))

    assert reponse.status_code == 422
    assert reponse.json()["erreur"] == "entrees invalides"
    assert "Traceback" not in reponse.text


def test_champ_inconnu_refuse(client):
    reponse = client.post("/predict", json=dict(OBSERVATION, inconnu=1))

    assert reponse.status_code == 422


def test_feedback_sur_prediction_connue(client):
    prediction = client.post("/predict", json=OBSERVATION).json()

    reponse = client.post(
        "/feedback", json={"prediction_id": prediction["prediction_id"], "valeur_reelle": 4000}
    )

    assert reponse.status_code == 200
    assert reponse.json()["prediction_id"] == prediction["prediction_id"]


def test_feedback_sur_prediction_inconnue(client):
    reponse = client.post("/feedback", json={"prediction_id": 4242, "valeur_reelle": 10})

    assert reponse.status_code == 404


def test_panne_de_trace_ne_renvoie_pas_un_faux_succes(client, monkeypatch):
    def tomber(config, trace, predictions=()):
        raise psycopg.OperationalError("base arretee")

    monkeypatch.setattr(main.base, "tracer_requete", tomber)

    reponse = client.post("/predict", json=OBSERVATION)

    assert reponse.status_code == 503
    assert reponse.json()["detail"] == "trace indisponible"


def test_ready_passe_en_503_quand_la_base_tombe(client, monkeypatch):
    monkeypatch.setattr(main.base, "joignable", lambda config: False)

    reponse = client.get("/health/ready")

    assert reponse.status_code == 503
    assert reponse.json()["base"] is False


def test_live_reste_disponible_sans_modele(client, monkeypatch):
    monkeypatch.setitem(modele.ETAT, "modele", None)

    assert client.get("/health/live").status_code == 200
    assert client.post("/predict", json=OBSERVATION).status_code == 503


def test_metriques_exposees_pour_prometheus(client):
    client.post("/predict", json=OBSERVATION)

    corps = client.get("/metrics").text

    assert "velos_requetes_total" in corps
    assert "velos_predictions_total" in corps
    assert "velos_duree_requete_secondes_bucket" in corps
