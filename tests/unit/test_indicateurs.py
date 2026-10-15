from datetime import date, datetime

import pytest

from api.models import Incident, Station, Trajet
from api.services.indicateurs import (
    activite_par_jour, incidents_par_statut, stations_actives,
)


@pytest.fixture
def jeu(db_session):
    for identifiant in ["S001", "S002", "S003"]:
        db_session.add(Station(
            station_id=identifiant, nom=identifiant, commune="Lille",
            capacite=10, latitude=50, longitude=3,
            date_mise_en_service=date(2023, 1, 1),
        ))
    db_session.flush()

    trajets = [
        (1, datetime(2026, 8, 24, 0), "S001", "S002"),
        (2, datetime(2026, 8, 24, 23, 59, 59), "S002", "S001"),
        (3, datetime(2026, 8, 25, 0), "S001", None),
    ]
    for numero, heure, depart, arrivee in trajets:
        db_session.add(Trajet(
            trajet_id=f"T{numero:06}", velo_id="V0001",
            depart_horodatage=heure, station_depart=depart,
            station_arrivee=arrivee, duree_secondes=60,
            type_usager="occasionnel",
        ))

    incidents = [
        (1, "resolu", datetime(2026, 8, 24, 12)),
        (2, "resolu", datetime(2026, 8, 24, 15, 10)),
        (3, "ouvert", None),
    ]
    for numero, statut, resolution in incidents:
        db_session.add(Incident(
            incident_id=f"I2026-{numero:04}",
            date_signalement=datetime(2026, 8, 24, 10),
            cible="velo", velo_id="V0001", type_incident="pneu creve",
            statut=statut, date_resolution=resolution,
        ))
    db_session.flush()


def test_activite_dates_inclusives(db_session, jeu):
    assert activite_par_jour(db_session, date(2026, 8, 24), date(2026, 8, 24)) == {
        "donnees": [{"jour": date(2026, 8, 24), "nb_trajets": 2}],
    }


def test_activite_toute_periode(db_session, jeu):
    assert activite_par_jour(db_session) == {
        "donnees": [
            {"jour": date(2026, 8, 24), "nb_trajets": 2},
            {"jour": date(2026, 8, 25), "nb_trajets": 1},
        ],
    }


@pytest.mark.parametrize("debut,fin,nombre", [
    (date(2026, 8, 25), None, 1),
    (None, date(2026, 8, 24), 2),
    (date(2026, 8, 26), None, 0),
])
def test_activite_periode_partielle_ou_vide(db_session, jeu, debut, fin, nombre):
    resultat = activite_par_jour(db_session, debut, fin)
    assert sum(ligne["nb_trajets"] for ligne in resultat["donnees"]) == nombre


def test_stations_mouvements_et_arrivee_absente(db_session, jeu):
    assert stations_actives(db_session) == {
        "donnees": [
            {"station_id": "S001", "nom": "S001", "nb_departs": 2, "nb_arrivees": 1},
            {"station_id": "S002", "nom": "S002", "nb_departs": 1, "nb_arrivees": 1},
        ],
    }
    assert len(stations_actives(db_session, 1)["donnees"]) == 1


def test_stations_egalite_triee_identifiant(db_session, jeu):
    db_session.add(Trajet(
        trajet_id="T000004", velo_id="V0001",
        depart_horodatage=datetime(2026, 8, 25, 12), station_depart="S002",
        duree_secondes=60, type_usager="occasionnel",
    ))
    db_session.flush()
    assert [s["station_id"] for s in stations_actives(db_session)["donnees"]] == ["S001", "S002"]


def test_station_avec_arrivee_seulement(db_session, jeu):
    db_session.add(Trajet(
        trajet_id="T000004", velo_id="V0001",
        depart_horodatage=datetime(2026, 8, 25, 12),
        station_depart="S001", station_arrivee="S003",
        duree_secondes=60, type_usager="occasionnel",
    ))
    db_session.flush()
    assert stations_actives(db_session)["donnees"][-1] == {
        "station_id": "S003", "nom": "S003", "nb_departs": 0, "nb_arrivees": 1,
    }


def test_incidents_moyenne_heures_arrondie(db_session, jeu):
    assert incidents_par_statut(db_session) == {
        "donnees": [
            {"statut": "ouvert", "nb_incidents": 1},
            {"statut": "resolu", "nb_incidents": 2},
        ],
        "delai_moyen_resolution_heures": 3.6,
    }


def test_incidents_aucun_resolu(db_session, jeu):
    for identifiant in ["I2026-0001", "I2026-0002"]:
        incident = db_session.get(Incident, identifiant)
        incident.statut = "en_cours"
        incident.date_resolution = None
    db_session.flush()
    assert incidents_par_statut(db_session) == {
        "donnees": [
            {"statut": "en_cours", "nb_incidents": 2},
            {"statut": "ouvert", "nb_incidents": 1},
        ],
        "delai_moyen_resolution_heures": None,
    }


def test_indicateurs_base_vide(db_session):
    assert activite_par_jour(db_session) == {"donnees": []}
    assert stations_actives(db_session) == {"donnees": []}
    assert incidents_par_statut(db_session) == {
        "donnees": [], "delai_moyen_resolution_heures": None,
    }
