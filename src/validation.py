import json
from datetime import UTC, datetime
from pathlib import Path

import great_expectations as gx
from great_expectations import expectations as regles
from great_expectations.data_context.types.base import ProgressBarsConfig

NOM_SUITE = "lot_velos"

COLONNES_ATTENDUES = [
    "instant",
    "dteday",
    "season",
    "yr",
    "mnth",
    "holiday",
    "weekday",
    "workingday",
    "weathersit",
    "temp",
    "atemp",
    "hum",
    "windspeed",
    "casual",
    "registered",
    "cnt",
]

BORNES = {
    "season": (1, 4),
    "yr": (0, 1),
    "mnth": (1, 12),
    "holiday": (0, 1),
    "weekday": (0, 6),
    "workingday": (0, 1),
    "weathersit": (1, 4),
    "temp": (0, 1),
    "atemp": (0, 1),
    "hum": (0, 1),
    "windspeed": (0, 1),
    "casual": (0, 100000),
    "registered": (0, 100000),
    "cnt": (1, 100000),
}


class LotNonConforme(Exception):
    pass


def construire_suite(config):
    validation = config["validation"]
    suite = gx.ExpectationSuite(name=NOM_SUITE)
    suite.add_expectation(regles.ExpectTableRowCountToBeBetween(min_value=validation["lignes_minimum"]))
    suite.add_expectation(regles.ExpectTableColumnsToMatchSet(column_set=COLONNES_ATTENDUES))
    suite.add_expectation(regles.ExpectColumnValuesToBeUnique(column="dteday"))
    for colonne, (minimum, maximum) in BORNES.items():
        suite.add_expectation(
            regles.ExpectColumnValuesToNotBeNull(
                column=colonne, mostly=1 - validation["taux_manquants_maximum"]
            )
        )
        suite.add_expectation(
            regles.ExpectColumnValuesToBeBetween(column=colonne, min_value=minimum, max_value=maximum)
        )
    suite.add_expectation(regles.ExpectColumnPairValuesAToBeGreaterThanB(column_A="cnt", column_B="casual"))
    return suite


def valider(lot, config):
    contexte = gx.get_context(mode="ephemeral")
    contexte.variables.progress_bars = ProgressBarsConfig(globally=False, metric_calculations=False)
    source = contexte.data_sources.add_pandas("lots")
    actif = source.add_dataframe_asset(name="lot")
    lot_defini = actif.add_batch_definition_whole_dataframe("complet")
    suite = contexte.suites.add(construire_suite(config))
    definition = contexte.validation_definitions.add(
        gx.ValidationDefinition(data=lot_defini, suite=suite, name=NOM_SUITE)
    )

    resultat = definition.run(batch_parameters={"dataframe": lot["donnees"]})
    echecs = [
        {
            "regle": sortie["expectation_type"],
            "colonne": sortie["kwargs"].get("column"),
            "details": sortie["result"],
        }
        for sortie in resultat.describe_dict()["expectations"]
        if not sortie["success"]
    ]
    rapport = {
        "lot": lot["nom"],
        "empreinte": lot["empreinte"],
        "lignes": lot["lignes"],
        "horodatage": datetime.now(UTC).isoformat(timespec="seconds"),
        "conforme": bool(resultat.success),
        "regles_evaluees": len(resultat.describe_dict()["expectations"]),
        "echecs": echecs,
    }
    chemin = ecrire_rapport(rapport, config)

    if not resultat.success:
        noms = ", ".join(echec["regle"] for echec in echecs)
        raise LotNonConforme(f"lot {lot['nom']} rejete ({len(echecs)} regles en echec : {noms})")

    print(f"lot {lot['nom']} conforme : {rapport['regles_evaluees']} regles verifiees")
    return {"rapport": rapport, "chemin_rapport": str(chemin)}


def ecrire_rapport(rapport, config):
    dossier = Path(config["validation"]["dossier_rapports"])
    dossier.mkdir(parents=True, exist_ok=True)
    horodatage = rapport["horodatage"].replace(":", "-")
    chemin = dossier / f"{Path(rapport['lot']).stem}_{horodatage}.json"
    chemin.write_text(json.dumps(rapport, indent=2, default=str), encoding="utf-8")
    print(f"rapport de validation : {chemin}")
    return chemin
