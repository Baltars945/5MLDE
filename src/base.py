import json
from contextlib import contextmanager

import psycopg
from psycopg_pool import ConnectionPool, PoolTimeout

from src import config as configuration

ERREURS = (psycopg.Error, PoolTimeout)
RESERVE = {}


def pool(config):
    if "pool" not in RESERVE:
        RESERVE["pool"] = ConnectionPool(
            configuration.dsn(config),
            min_size=1,
            max_size=config["base"]["connexions_max"],
            timeout=5,
            max_idle=60,
        )
        print(f"reserve de connexions ouverte ({config['base']['connexions_max']} maximum)")
    return RESERVE["pool"]


def fermer_pool():
    reserve = RESERVE.pop("pool", None)
    if reserve is not None:
        reserve.close()


@contextmanager
def connexion(config, delai=5):
    with pool(config).connection(timeout=delai) as lien:
        yield lien


def joignable(config):
    try:
        with connexion(config) as lien:
            lien.execute("select 1")
        return True
    except ERREURS as erreur:
        print(f"base injoignable : {str(erreur).strip()}")
        return False


def tracer_requete(config, trace, predictions=()):
    with connexion(config) as lien, lien.transaction():
        lien.execute(
            """
            insert into service.requetes (id, route, statut, duree_ms, version_modele, erreur)
            values (%(id)s, %(route)s, %(statut)s, %(duree_ms)s, %(version)s, %(erreur)s)
            """,
            trace,
        )
        identifiants = []
        for entrees, valeur in predictions:
            ligne = lien.execute(
                """
                insert into service.predictions (requete_id, version_modele, entrees, prediction)
                values (%s, %s, %s, %s) returning id
                """,
                (trace["id"], trace["version"], json.dumps(entrees), valeur),
            ).fetchone()
            identifiants.append(ligne[0])
    return identifiants


def enregistrer_feedback(config, prediction_id, valeur_reelle, commentaire):
    with connexion(config) as lien:
        existe = lien.execute(
            "select id from service.predictions where id = %s", (prediction_id,)
        ).fetchone()
        if not existe:
            return None
        ligne = lien.execute(
            """
            insert into service.feedbacks (prediction_id, valeur_reelle, commentaire)
            values (%s, %s, %s)
            on conflict (prediction_id) do update
                set valeur_reelle = excluded.valeur_reelle,
                    commentaire = excluded.commentaire,
                    recu_le = now()
            returning id
            """,
            (prediction_id, valeur_reelle, commentaire),
        ).fetchone()
        return ligne[0]


def enregistrer_version(config, version):
    with connexion(config) as lien:
        lien.execute(
            """
            insert into service.versions_modele (nom, version, run_id, mae)
            values (%(nom)s, %(version)s, %(run_id)s, %(mae)s)
            on conflict (nom, version) do update set vue_le = now()
            """,
            version,
        )


def ouvrir_execution(config, lot):
    with connexion(config) as lien:
        ligne = lien.execute(
            "insert into service.executions_pipeline (lot, statut) values (%s, 'en cours') returning id",
            (lot,),
        ).fetchone()
        return ligne[0]


def fermer_execution(config, identifiant, execution):
    with connexion(config) as lien:
        lien.execute(
            """
            update service.executions_pipeline
               set terminee_le = now(),
                   statut = %(statut)s,
                   etape_en_echec = %(etape_en_echec)s,
                   run_id = %(run_id)s,
                   mae = %(mae)s,
                   decision = %(decision)s,
                   message = %(message)s,
                   lot = coalesce(%(lot)s, lot)
             where id = %(id)s
            """,
            dict(execution, id=identifiant),
        )
