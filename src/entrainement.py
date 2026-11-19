from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge


def construire(config):
    modele = config["modele"]
    if modele["type"] == "ridge":
        return Ridge(alpha=modele.get("alpha", 1.0))
    return RandomForestRegressor(
        n_estimators=modele["n_estimators"],
        max_depth=modele["max_depth"],
        random_state=modele["graine"],
        n_jobs=-1,
    )


def entrainer(prepare, config):
    modele = construire(config)
    modele.fit(prepare["x_apprentissage"], prepare["y_apprentissage"])
    baseline = DummyRegressor(strategy="mean")
    baseline.fit(prepare["x_apprentissage"], prepare["y_apprentissage"])
    print(f"modele entraine : {config['modele']['type']}")
    return {"modele": modele, "baseline": baseline, "type": config["modele"]["type"]}
