from sqlalchemy import func, select, text

from api.models import Incident, Station, Trajet
from scripts.importer import importer_incidents, importer_stations, importer_trajets


def charger(connexion, donnees):
    stations, trajets, incidents = donnees
    importer_stations(connexion, stations)
    importer_trajets(connexion, trajets)
    importer_incidents(connexion, incidents)


def test_import_idempotent(connexion_test, donnees_valides):
    for _ in range(2):
        charger(connexion_test, donnees_valides)

        for modele, nombre in [(Station, 120), (Trajet, 2002), (Incident, 177)]:
            total = connexion_test.scalar(select(func.count()).select_from(modele))
            assert total == nombre


def test_import_references_et_valeurs(connexion_test, donnees_valides):
    charger(connexion_test, donnees_valides)

    orphelins = connexion_test.scalar(text("""
        SELECT count(*) FROM trajet t
        LEFT JOIN station s ON s.station_id = t.station_arrivee
        WHERE t.station_arrivee IS NOT NULL AND s.station_id IS NULL
    """))
    assert orphelins == 0
    assert connexion_test.scalar(text("SELECT count(*) FROM trajet WHERE duree_secondes <= 0")) == 0
    assert connexion_test.scalar(text("SELECT count(*) FROM trajet WHERE station_arrivee IS NULL")) == 22
    assert connexion_test.scalar(text("""
        SELECT count(*) FROM incident
        WHERE statut NOT IN ('ouvert', 'en_cours', 'resolu')
    """)) == 0


def test_reimport_conserve_statut_incident(connexion_test, donnees_valides):
    charger(connexion_test, donnees_valides)
    incident_id = connexion_test.scalar(text("""
        SELECT incident_id FROM incident
        WHERE statut = 'ouvert' ORDER BY incident_id LIMIT 1
    """))
    connexion_test.execute(text("""
        UPDATE incident SET statut = 'en_cours' WHERE incident_id = :identifiant
    """), {"identifiant": incident_id})

    charger(connexion_test, donnees_valides)

    statut = connexion_test.scalar(text("""
        SELECT statut FROM incident WHERE incident_id = :identifiant
    """), {"identifiant": incident_id})
    assert statut == "en_cours"
