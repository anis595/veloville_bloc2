from pathlib import Path

import pandas as pd
import pytest

from api.services.fiabilisation import (
    convertir_date, est_vide, fiabiliser_incidents, fiabiliser_stations,
    fiabiliser_trajets, format_trajet, rg1_station, rg2_stations_trajet,
    rg3_arrivee, rg4_duree, rg5_usager, rg6_cible, rg7_statut, rg8_dates,
)


@pytest.fixture
def station():
    return {
        "station_id": "S001",
        "nom": "Lille - Gare",
        "commune": "Lille",
        "capacite": "15",
        "latitude": "50.63",
        "longitude": "3.06",
        "date_mise_en_service": "2023-01-01",
    }


@pytest.fixture
def trajet():
    return {
        "trajet_id": "T480001",
        "velo_id": "V0001",
        "depart_horodatage": "2026-08-24 12:00:00",
        "station_depart": "S001",
        "station_arrivee": "S002",
        "duree_secondes": "600",
        "type_usager": "abonne",
        "usager_ref": "U1234abcd",
    }


@pytest.fixture
def incident():
    return {
        "incident_id": "I2026-0001",
        "date_signalement": "2026-08-24 10:00",
        "cible": "velo",
        "velo_id": "V0001",
        "station_id": "",
        "type_incident": "pneu creve",
        "statut": "resolu",
        "date_resolution": "2026-08-24 12:00",
        "technicien": "Alice",
    }


def test_rg1_station_valide_ne_modifie_pas_entree(station):
    resultat, journal, rejet = rg1_station(station)
    assert not rejet
    assert resultat["capacite"] == 15
    assert station["capacite"] == "15"
    assert journal == []


@pytest.mark.parametrize("colonne,valeur", [
    ("station_id", "S9999"),
    ("capacite", "0"),
    ("capacite", "-1"),
    ("capacite", "1.5"),
    ("capacite", "inf"),
    ("latitude", "invalide"),
    ("longitude", "invalide"),
    ("latitude", "nan"),
    ("longitude", "inf"),
    ("nom", ""),
    ("commune", ""),
    ("date_mise_en_service", "2026-02-30"),
])
def test_rg1_station_invalide_rejetee(station, colonne, valeur):
    station[colonne] = valeur
    assert rg1_station(station)[2]


def test_rg1_date_alternative_normalisee(station):
    station["date_mise_en_service"] = "01/01/2023"
    resultat, journal, rejet = rg1_station(station)
    assert resultat["date_mise_en_service"] == "2023-01-01"
    assert journal[0]["decision"] == "normalisation"
    assert not rejet


def test_rg2_stations_valides(trajet):
    assert not rg2_stations_trajet(trajet, {"S001", "S002"})[2]


@pytest.mark.parametrize("colonne", ["station_depart", "station_arrivee"])
def test_rg2_station_inconnue_rejetee(trajet, colonne):
    trajet[colonne] = "S999"
    assert rg2_stations_trajet(trajet, {"S001", "S002"})[2]


def test_rg2_reference_normalisee(trajet):
    trajet["station_depart"] = " s001 "
    resultat, journal, rejet = rg2_stations_trajet(trajet, {"S001","S002"})
    assert resultat["station_depart"] == "S001"
    assert journal[0]["decision"] == "normalisation"
    assert not rejet


@pytest.mark.parametrize("valeur", [None, "", " "])
def test_rg3_arrivee_absente_conservee(trajet, valeur):
    trajet["station_arrivee"] = valeur
    resultat, _, rejet = rg3_arrivee(trajet)
    assert resultat["station_arrivee"] is None
    assert not rejet


@pytest.mark.parametrize("valeur,rejet", [
    ("600", False), ("1", False), ("0", True), ("-5", True),
    ("abc", True), ("1.5", True), (None, True),
])
def test_rg4_duree(trajet, valeur, rejet):
    trajet["duree_secondes"] = valeur
    assert rg4_duree(trajet)[2] == rejet


@pytest.mark.parametrize("type_usager,ref,rejet", [
    ("abonne", "U1234abcd", False),
    ("ABONNE", "U1234abcd", False),
    ("abonné", "U1234abcd", False),
    ("abonne", "", True),
    ("abonne", "nom@example.fr", True),
    ("occasionnel", "", False),
    ("occasionnel", "U1234abcd", True),
    ("inconnu", "", True),
])
def test_rg5_usager(trajet, type_usager, ref, rejet):
    trajet.update(type_usager=type_usager, usager_ref=ref)
    assert rg5_usager(trajet)[2] == rejet


@pytest.mark.parametrize("cible,velo,station,rejet", [
    ("velo", "V0001", "", False),
    ("station", "", "S001", False),
    ("station", "", "S999", True),
    ("velo", "V0001", "S001", True),
    ("velo", "", "", True),
    ("velo", "", "S001", True),
    ("station", "V0001", "", True),
    ("autre", "V0001", "", True),
    ("velo", "V99999", "", True),
])
def test_rg6_cible(incident, cible, velo, station, rejet):
    incident.update(cible=cible, velo_id=velo, station_id=station)
    resultat, journal, invalide = rg6_cible(incident, {"S001"})
    assert invalide == rejet
    if rejet:
        assert any(message["decision"] == "rejet" for message in journal)


@pytest.mark.parametrize("statut,attendu,rejet", [
    ("ouvert", "ouvert", False), ("EN COURS", "en_cours", False),
    ("résolu", "resolu", False), ("ferme", "ferme", True),
])
def test_rg7_statut(incident, statut, attendu, rejet):
    incident["statut"] = statut
    resultat, _, invalide = rg7_statut(incident)
    assert resultat["statut"] == attendu
    assert invalide == rejet


@pytest.mark.parametrize("statut,resolution,rejet", [
    ("resolu", "2026-08-24 12:00", False),
    ("resolu", "2026-08-24 10:00", False),
    ("resolu", "2026-08-24 09:59", True),
    ("resolu", "", True),
    ("ouvert", "", False),
    ("en_cours", "", False),
    ("ouvert", "2026-08-24 12:00", True),
    ("resolu", "invalide", True),
])
def test_rg8_coherence_dates(incident, statut, resolution, rejet):
    incident.update(statut=statut, date_resolution=resolution)
    assert rg8_dates(incident)[2] == rejet


def test_rg8_signalement_invalide(incident):
    incident["date_signalement"] = "invalide"
    assert rg8_dates(incident)[2]


def test_rg8_technicien_absent_avertissement(incident):
    incident["technicien"] = ""
    resultat, journal, rejet = rg8_dates(incident)
    assert not rejet
    assert resultat["technicien"] is None
    assert journal[0]["decision"] == "normalisation"
    assert "avertissement" in journal[0]["motif"]


@pytest.mark.parametrize("colonne,valeur", [("trajet_id","T1"),("velo_id","V1"),("depart_horodatage","2026-02-30 10:00")])
def test_format_trajet_invalide(trajet, colonne, valeur):
    trajet[colonne] = valeur
    assert format_trajet(trajet)[2]


def test_format_trajet_normalise(trajet):
    trajet.update(velo_id="v0001", depart_horodatage="24/08/2026 12:00")
    resultat, journal, rejet = format_trajet(trajet)
    assert not rejet
    assert resultat["velo_id"] == "V0001"
    assert resultat["depart_horodatage"] == "2026-08-24 12:00:00"
    assert len(journal) == 2


def test_doublon_exact_ecarte(station):
    valides, journal = fiabiliser_stations(pd.DataFrame([station, station]))
    assert len(valides) == 1
    assert journal.iloc[0]["decision"] == "rejet"
    assert journal.iloc[0]["motif"] == "Doublon exact"


def test_identifiant_identique_lignes_differentes_rejete(station):
    autre = dict(station, nom="Autre nom")
    valides, journal = fiabiliser_stations(pd.DataFrame([station, autre]))
    assert len(valides) == 1
    assert journal.iloc[0]["decision"] == "rejet"


def test_incident_id_invalide(incident):
    incident["incident_id"] = "I1"
    valides, journal = fiabiliser_incidents(pd.DataFrame([incident]), {"S001"})
    assert valides.empty
    assert journal.iloc[0]["colonne"] == "incident_id"


def test_arrivee_facultative_importable(trajet):
    trajet["station_arrivee"] = ""
    valides, journal = fiabiliser_trajets(pd.DataFrame([trajet]), {"S001"})
    assert len(valides) == 1
    assert valides.iloc[0]["station_arrivee"] is None
    assert journal.empty


def test_date_vide_et_invalide():
    assert convertir_date("", ["%Y-%m-%d"], "%Y-%m-%d") is None
    assert convertir_date("invalide", ["%Y-%m-%d"], "%Y-%m-%d") is None
    assert est_vide(float("nan"))


def test_rg8_secondes_conservees(incident):
    incident.update(date_signalement="2026-08-24 10:00:30", date_resolution="2026-08-24 10:00:29")
    assert rg8_dates(incident)[2]
    incident["date_resolution"] = "2026-08-24 10:00:31"
    resultat, _, rejet = rg8_dates(incident)
    assert not rejet
    assert resultat["date_resolution"].endswith("10:00:31")


def test_identifiants_incidents_normalises_uniques(incident):
    autre = dict(incident, incident_id=" i2026-0001 ", technicien="Bob")

    valides, journal = fiabiliser_incidents(
        pd.DataFrame([incident, autre]), {"S001"},
    )

    assert len(valides) == 1
    assert "Identifiant déjà rencontré" in journal["motif"].values


def test_volumes_des_exports_fournis():
    dossier = Path(__file__).resolve().parents[2] / "data"
    stations = pd.read_csv(dossier / "stations.csv", dtype=str, keep_default_na=False)
    trajets = pd.read_csv(dossier / "trajets.csv", dtype=str, keep_default_na=False)
    incidents = pd.read_csv(dossier / "incidents.csv", dtype=str, keep_default_na=False)

    stations_valides, journal_stations = fiabiliser_stations(stations)
    station_ids = set(stations_valides["station_id"])
    trajets_valides, journal_trajets = fiabiliser_trajets(trajets, station_ids)
    incidents_valides, journal_incidents = fiabiliser_incidents(incidents, station_ids)

    assert len(stations_valides) == 120
    assert len(trajets_valides) == 2002
    assert len(incidents_valides) == 177
    assert journal_stations.empty
    assert (journal_trajets["motif"] == "Doublon exact").sum() == 12
    assert journal_trajets[journal_trajets["motif"] == "Durée invalide"].shape[0] == 9
    assert journal_trajets[journal_trajets["motif"] == "Station inexistante ou absente"].shape[0] == 7
    assert (journal_incidents["decision"] == "rejet").sum() == 3
