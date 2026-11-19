\set ON_ERROR_STOP on
\getenv mot_de_passe_api VELOS_DB_PASSWORD
\getenv mot_de_passe_grafana GRAFANA_DB_PASSWORD

BEGIN;

DO $roles$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'velos_api') THEN
        CREATE ROLE velos_api LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'velos_lecture') THEN
        CREATE ROLE velos_lecture LOGIN;
    END IF;
END
$roles$;

ALTER ROLE velos_api PASSWORD :'mot_de_passe_api';
ALTER ROLE velos_lecture PASSWORD :'mot_de_passe_grafana';
ALTER ROLE velos_lecture SET default_transaction_read_only = on;
ALTER ROLE velos_lecture SET statement_timeout = '10s';

REVOKE ALL ON DATABASE velos FROM PUBLIC;
GRANT CONNECT ON DATABASE velos TO velos_api, velos_lecture;

CREATE SCHEMA IF NOT EXISTS service;
GRANT USAGE ON SCHEMA service TO velos_api, velos_lecture;

CREATE TABLE IF NOT EXISTS service.versions_modele (
    id bigserial PRIMARY KEY,
    nom text NOT NULL,
    version text NOT NULL,
    run_id text NOT NULL,
    mae double precision,
    vue_le timestamptz NOT NULL DEFAULT now(),
    UNIQUE (nom, version)
);

CREATE TABLE IF NOT EXISTS service.requetes (
    id uuid PRIMARY KEY,
    recue_le timestamptz NOT NULL DEFAULT now(),
    route text NOT NULL,
    statut integer NOT NULL,
    duree_ms double precision NOT NULL,
    version_modele text,
    erreur text
);

CREATE TABLE IF NOT EXISTS service.predictions (
    id bigserial PRIMARY KEY,
    requete_id uuid NOT NULL REFERENCES service.requetes (id) ON DELETE CASCADE,
    faite_le timestamptz NOT NULL DEFAULT now(),
    version_modele text NOT NULL,
    entrees jsonb NOT NULL,
    prediction double precision NOT NULL
);

CREATE TABLE IF NOT EXISTS service.feedbacks (
    id bigserial PRIMARY KEY,
    prediction_id bigint NOT NULL REFERENCES service.predictions (id) ON DELETE CASCADE,
    recu_le timestamptz NOT NULL DEFAULT now(),
    valeur_reelle double precision NOT NULL CHECK (valeur_reelle >= 0),
    commentaire text,
    UNIQUE (prediction_id)
);

CREATE TABLE IF NOT EXISTS service.executions_pipeline (
    id bigserial PRIMARY KEY,
    demarree_le timestamptz NOT NULL DEFAULT now(),
    terminee_le timestamptz,
    lot text,
    statut text NOT NULL,
    etape_en_echec text,
    run_id text,
    mae double precision,
    decision text,
    message text
);

CREATE INDEX IF NOT EXISTS requetes_recue_le ON service.requetes (recue_le DESC);
CREATE INDEX IF NOT EXISTS predictions_faite_le ON service.predictions (faite_le DESC);
CREATE INDEX IF NOT EXISTS executions_demarree_le ON service.executions_pipeline (demarree_le DESC);

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA service TO velos_api;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA service TO velos_api;
GRANT SELECT ON ALL TABLES IN SCHEMA service TO velos_lecture;

COMMIT;
