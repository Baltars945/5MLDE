def nettoyer(donnees, config):
    preparation = config["preparation"]
    colonnes = preparation["colonnes"] + [preparation["cible"]]
    propre = donnees.drop_duplicates(subset="dteday").sort_values("dteday")
    propre = propre.dropna(subset=colonnes)
    return propre.reset_index(drop=True)


def construire_variables(donnees, config):
    return donnees[config["preparation"]["colonnes"]].astype(float)


def separer(donnees, config):
    coupe = int(len(donnees) * (1 - config["preparation"]["part_test"]))
    return donnees.iloc[:coupe], donnees.iloc[coupe:]


def preparer(donnees, config):
    propre = nettoyer(donnees, config)
    apprentissage, test = separer(propre, config)
    cible = config["preparation"]["cible"]
    print(f"preparation : {len(apprentissage)} lignes d'apprentissage, {len(test)} de test")
    return {
        "x_apprentissage": construire_variables(apprentissage, config),
        "y_apprentissage": apprentissage[cible],
        "x_test": construire_variables(test, config),
        "y_test": test[cible],
        "lignes": len(propre),
        "colonnes": config["preparation"]["colonnes"],
    }
