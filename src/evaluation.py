from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def mesurer(modele, x, y):
    prediction = modele.predict(x)
    return {
        "mae": float(mean_absolute_error(y, prediction)),
        "rmse": float(mean_squared_error(y, prediction) ** 0.5),
        "r2": float(r2_score(y, prediction)),
    }


def evaluer(entraine, prepare):
    modele = mesurer(entraine["modele"], prepare["x_test"], prepare["y_test"])
    baseline = mesurer(entraine["baseline"], prepare["x_test"], prepare["y_test"])
    gain = 1 - modele["mae"] / baseline["mae"]
    print(f"mae modele {modele['mae']:.0f} / baseline {baseline['mae']:.0f} / gain {gain:.1%}")
    return {"modele": modele, "baseline": baseline, "gain_vs_baseline": float(gain)}
