BEGIN;
CREATE TABLE IF NOT EXISTS station (
    station_id VARCHAR(10) PRIMARY KEY,
    nom TEXT NOT NULL,
    commune TEXT NOT NULL,
    capacite INTEGER NOT NULL CHECK (capacite > 0),
    latitude NUMERIC(8,5) NOT NULL,
    longitude NUMERIC(8,5) NOT NULL,
    date_mise_en_service DATE NOT NULL
);
CREATE TABLE IF NOT EXISTS trajet (
    trajet_id VARCHAR(12) PRIMARY KEY,
    velo_id VARCHAR(8) NOT NULL,
    depart_horodatage TIMESTAMP NOT NULL,
    station_depart VARCHAR(10) NOT NULL REFERENCES station(station_id),
    station_arrivee VARCHAR(10) REFERENCES station(station_id),
    duree_secondes INTEGER NOT NULL CHECK (duree_secondes > 0),
    type_usager TEXT NOT NULL CHECK (type_usager IN ('abonne','occasionnel')),
    usager_ref TEXT,
    CHECK ((type_usager = 'abonne' AND usager_ref IS NOT NULL)
        OR (type_usager = 'occasionnel' AND usager_ref IS NULL))
);
CREATE TABLE IF NOT EXISTS incident (
    incident_id VARCHAR(12) PRIMARY KEY,
    date_signalement TIMESTAMP NOT NULL,
    cible TEXT NOT NULL,
    velo_id VARCHAR(8),
    station_id VARCHAR(10) REFERENCES station(station_id),
    type_incident TEXT NOT NULL,
    statut TEXT NOT NULL CHECK (statut IN ('ouvert','en_cours','resolu')),
    date_resolution TIMESTAMP,
    technicien TEXT,
    CHECK ((cible = 'velo' AND velo_id IS NOT NULL AND station_id IS NULL)
        OR (cible = 'station' AND station_id IS NOT NULL AND velo_id IS NULL)),
    CHECK ((statut = 'resolu' AND date_resolution IS NOT NULL AND date_resolution >= date_signalement)
        OR (statut <> 'resolu' AND date_resolution IS NULL))
);
CREATE TABLE IF NOT EXISTS utilisateur (
    id_utilisateur SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    mot_de_passe_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('exploitant','direction'))
);
COMMIT;
