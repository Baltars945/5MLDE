from pathlib import Path

import psycopg

from flows import pipeline


def test_alerte_ecrite_dans_le_fichier(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "FICHIER_ALERTES", str(tmp_path / "alertes.log"))

    pipeline.alerter("validation en echec sur lot_004.csv")

    lignes = Path(tmp_path / "alertes.log").read_text(encoding="utf-8").splitlines()
    assert len(lignes) == 1
    assert "ALERTE" in lignes[0]
    assert "lot_004.csv" in lignes[0]


def test_trace_indisponible_ne_bloque_pas_le_pipeline(config, monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "FICHIER_ALERTES", str(tmp_path / "alertes.log"))

    def tomber(*arguments):
        raise psycopg.OperationalError("base arretee")

    monkeypatch.setattr(pipeline.base, "ouvrir_execution", tomber)

    assert pipeline.ouvrir_trace(config) is None
    assert "indisponible" in Path(tmp_path / "alertes.log").read_text(encoding="utf-8")


def test_fermeture_sans_trace_ouverte_ne_fait_rien(config, monkeypatch):
    appels = []
    monkeypatch.setattr(pipeline.base, "fermer_execution", lambda *a: appels.append(a))

    pipeline.fermer_trace(config, None, {"statut": "succes"})

    assert appels == []
