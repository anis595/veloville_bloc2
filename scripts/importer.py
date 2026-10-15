"""Import des CSV fiabilisés et écriture du journal des rejets."""

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import pandas as pd
from sqlalchemy import text

from api.database import engine
from api.services.fiabilisation import (
    fiabiliser_incidents,
    fiabiliser_stations,
    fiabiliser_trajets,
)


def importer_stations(connexion, stations):
    requete = text("""
        INSERT INTO station (
            station_id, nom, commune, capacite,
            latitude, longitude, date_mise_en_service
        ) VALUES (
            :station_id, :nom, :commune, :capacite,
            :latitude, :longitude, :date_mise_en_service
        )
        ON CONFLICT (station_id) DO NOTHING
    """)
    for station in stations.to_dict(orient="records"):
        connexion.execute(requete, station)


def importer_trajets(connexion, trajets):
    requete = text("""
        INSERT INTO trajet (
            trajet_id, velo_id, depart_horodatage, station_depart,
            station_arrivee, duree_secondes, type_usager, usager_ref
        ) VALUES (
            :trajet_id, :velo_id, :depart_horodatage, :station_depart,
            :station_arrivee, :duree_secondes, :type_usager, :usager_ref
        )
        ON CONFLICT (trajet_id) DO NOTHING
    """)
    for trajet in trajets.to_dict(orient="records"):
        connexion.execute(requete, trajet)


def importer_incidents(connexion, incidents):
    requete = text("""
        INSERT INTO incident (
            incident_id, date_signalement, cible, velo_id, station_id,
            type_incident, statut, date_resolution, technicien
        ) VALUES (
            :incident_id, :date_signalement, :cible, :velo_id, :station_id,
            :type_incident, :statut, :date_resolution, :technicien
        )
        ON CONFLICT (incident_id) DO NOTHING
    """)
    for incident in incidents.to_dict(orient="records"):
        connexion.execute(requete, incident)


def afficher_bilan(nom, source, valides, journal):
    doublons = (journal["motif"] == "Doublon exact").sum()
    rejets = len(source) - len(valides) - doublons
    print(
        f"{nom} : {len(source)} lignes sources = {len(valides)} valides"
        f" + {rejets} rejets + {doublons} doublons"
    )


def main():
    stations = pd.read_csv(RACINE / "data/stations.csv", dtype=str, keep_default_na=False)
    trajets = pd.read_csv(RACINE / "data/trajets.csv", dtype=str, keep_default_na=False)
    incidents = pd.read_csv(RACINE / "data/incidents.csv", dtype=str, keep_default_na=False)

    stations_valides, journal_stations = fiabiliser_stations(stations)
    station_ids = set(stations_valides["station_id"])
    trajets_valides, journal_trajets = fiabiliser_trajets(trajets, station_ids)
    incidents_valides, journal_incidents = fiabiliser_incidents(incidents, station_ids)

    journal = pd.concat(
        [journal_stations, journal_trajets, journal_incidents], ignore_index=True,
    )
    journal.to_csv(RACINE / "journal_import.csv", index=False)

    afficher_bilan("stations.csv", stations, stations_valides, journal_stations)
    afficher_bilan("trajets.csv", trajets, trajets_valides, journal_trajets)
    afficher_bilan("incidents.csv", incidents, incidents_valides, journal_incidents)

    # Les stations doivent exister avant les trajets et incidents qui les référencent.
    with engine.begin() as connexion:
        importer_stations(connexion, stations_valides)
        importer_trajets(connexion, trajets_valides)
        importer_incidents(connexion, incidents_valides)

    print("Import terminé.")
    print(f"Journal : journal_import.csv ({len(journal)} événements)")


if __name__ == "__main__":
    main()
