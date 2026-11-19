import random

from locust import HttpUser, between, task


def observation():
    return {
        "season": random.randint(1, 4),
        "yr": 1,
        "mnth": random.randint(1, 12),
        "holiday": random.choice([0, 0, 0, 1]),
        "weekday": random.randint(0, 6),
        "workingday": random.randint(0, 1),
        "weathersit": random.randint(1, 3),
        "temp": round(random.uniform(0.1, 0.9), 3),
        "atemp": round(random.uniform(0.1, 0.9), 3),
        "hum": round(random.uniform(0.2, 0.95), 3),
        "windspeed": round(random.uniform(0.0, 0.5), 3),
    }


class ClientVelos(HttpUser):
    wait_time = between(0.1, 0.4)

    def on_start(self):
        self.predictions = []

    @task(6)
    def prediction_unitaire(self):
        reponse = self.client.post("/predict", json=observation())
        if reponse.status_code == 200:
            self.predictions.append(reponse.json()["prediction_id"])
            self.predictions = self.predictions[-20:]

    @task(2)
    def prediction_en_lot(self):
        lot = {"observations": [observation() for _ in range(10)]}
        self.client.post("/predict/lot", json=lot, name="/predict/lot (10)")

    @task(1)
    def depot_feedback(self):
        if not self.predictions:
            return
        identifiant = self.predictions.pop()
        self.client.post(
            "/feedback",
            json={"prediction_id": identifiant, "valeur_reelle": random.randint(500, 8000)},
        )

    @task(1)
    def sonde_sante(self):
        self.client.get("/health/live")
