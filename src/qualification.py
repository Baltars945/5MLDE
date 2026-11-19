def qualifier(resultats, config):
    seuils = config["qualification"]
    mae = resultats["modele"]["mae"]
    gain = resultats["gain_vs_baseline"]

    motifs = []
    if mae > seuils["mae_maximum"]:
        motifs.append(f"mae {mae:.0f} au-dessus du maximum {seuils['mae_maximum']:.0f}")
    if gain < seuils["gain_minimum_baseline"]:
        motifs.append(f"gain {gain:.1%} sous le minimum {seuils['gain_minimum_baseline']:.0%}")

    decision = {
        "qualifie": not motifs,
        "motif": "seuils respectes" if not motifs else " et ".join(motifs),
        "mae": mae,
        "gain": gain,
    }
    print(f"qualification : {'retenu' if decision['qualifie'] else 'refuse'} ({decision['motif']})")
    return decision
