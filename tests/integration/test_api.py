import os
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select, text

from api.models import Incident
from api.securite import decoder_access_token, utilisateur_courant


def test_sante(client):
    reponse = client.get("/sante")
    assert reponse.status_code == 200
    assert reponse.json() == {"statut": "ok"}


@pytest.mark.parametrize("username,role", [
    ("exploitant01", "exploitant"), ("direction01", "direction"),
])
def test_login_accepte(client, comptes, username, role):
    reponse = client.post("/auth/login", json={
        "username": username, "password": comptes,
    })

    assert reponse.status_code == 200
    resultat = reponse.json()
    assert resultat["token_type"] == "bearer"
    assert resultat["role"] == role
    contenu = decoder_access_token(resultat["access_token"])
    assert contenu["sub"] == username
    assert contenu["role"] == role
    assert contenu["exp"] > datetime.now(timezone.utc).timestamp()


@pytest.mark.parametrize("username", ["exploitant01", "inconnu"])
def test_login_refuse(client, username):
    reponse = client.post("/auth/login", json={
        "username": username, "password": "incorrect",
    })
    assert reponse.status_code == 401
    assert reponse.json() == {"detail": "Identifiants invalides"}


def test_login_mot_de_passe_trop_long(client):
    reponse = client.post("/auth/login", json={
        "username": "exploitant01", "password": "x" * 100,
    })
    assert reponse.status_code == 401


def test_login_corps_incomplet(client):
    assert client.post("/auth/login", json={"username": "exploitant01"}).status_code == 422


def test_utilisateur_sans_jeton(db_session):
    with pytest.raises(HTTPException) as erreur:
        utilisateur_courant(None, db_session)
    assert erreur.value.status_code == 401


def test_utilisateur_jeton_valide(db_session, jeton_direction):
    identifiants = HTTPAuthorizationCredentials(scheme="Bearer", credentials=jeton_direction)
    utilisateur = utilisateur_courant(identifiants, db_session)
    assert utilisateur.username == "direction01"
    assert utilisateur.role == "direction"


@pytest.mark.parametrize("contenu", [
    {"sub": "direction01", "role": "direction", "exp": 1},
    {"sub": "direction01", "role": "direction"},
    {"sub": "direction01", "role": "exploitant"},
    {"sub": "inconnu", "role": "direction"},
])
def test_utilisateur_jeton_refuse(db_session, comptes, contenu):
    contenu = dict(contenu)
    if contenu["sub"] == "inconnu" or contenu["role"] == "exploitant":
        contenu["exp"] = datetime.now(timezone.utc) + timedelta(minutes=5)
    jeton = jwt.encode(contenu, os.environ["JWT_SECRET"], algorithm="HS256")
    identifiants = HTTPAuthorizationCredentials(scheme="Bearer", credentials=jeton)

    with pytest.raises(HTTPException) as erreur:
        utilisateur_courant(identifiants, db_session)
    assert erreur.value.status_code == 401


def test_utilisateur_signature_modifiee(db_session, jeton_direction):
    debut, signature = jeton_direction.rsplit(".", 1)
    premier = "a" if signature[0] != "a" else "b"
    jeton = debut + "." + premier + signature[1:]
    identifiants = HTTPAuthorizationCredentials(scheme="Bearer", credentials=jeton)

    with pytest.raises(HTTPException) as erreur:
        utilisateur_courant(identifiants, db_session)
    assert erreur.value.status_code == 401


def test_role_direction_refuse(client, donnees, db_session, jeton_direction):
    incident = db_session.scalar(select(Incident).where(Incident.statut == "ouvert"))
    reponse = client.put(
        f"/incidents/{incident.incident_id}/statut",
        headers={"Authorization": "Bearer " + jeton_direction},
        json={"statut": "en_cours"},
    )

    assert reponse.status_code == 403
    assert reponse.json() == {"detail": "Acces reserve au role exploitant"}
    db_session.refresh(incident)
    assert incident.statut == "ouvert"


def test_role_exploitant_et_transitions(client, donnees, db_session, jeton_exploitant):
    incident = db_session.scalar(select(Incident).where(Incident.statut == "ouvert"))
    route = f"/incidents/{incident.incident_id}/statut"
    headers = {"Authorization": "Bearer " + jeton_exploitant}

    reponse = client.put(route, headers=headers, json={"statut": "en_cours"})
    assert reponse.status_code == 200
    assert reponse.json()["statut"] == "en_cours"
    assert reponse.json()["date_resolution"] is None
    db_session.refresh(incident)
    assert incident.statut == "en_cours"

    reponse = client.put(route, headers=headers, json={"statut": "en_cours"})
    assert reponse.status_code == 422
    assert reponse.json() == {"detail": "Transition de statut non autorisee"}

    avant = datetime.now()
    reponse = client.put(route, headers=headers, json={"statut": "resolu"})
    assert reponse.status_code == 200
    assert reponse.json()["statut"] == "resolu"
    resolution = datetime.fromisoformat(reponse.json()["date_resolution"])
    assert avant <= resolution <= datetime.now()
    db_session.refresh(incident)
    assert incident.statut == "resolu"
    assert incident.date_resolution == resolution

    reponse = client.put(route, headers=headers, json={"statut": "en_cours"})
    assert reponse.status_code == 422


@pytest.mark.parametrize("methode,route", [
    ("GET", "/stations"),
    ("GET", "/stations/S001"),
    ("GET", "/trajets"),
    ("GET", "/incidents"),
    ("GET", "/indicateurs/activite-par-jour"),
    ("GET", "/indicateurs/stations-actives"),
    ("GET", "/indicateurs/incidents-par-statut"),
    ("PUT", "/incidents/I2026-0001/statut"),
])
def test_routes_sans_jeton(client, methode, route):
    reponse = client.request(methode, route, json={"statut": "en_cours"})
    assert reponse.status_code == 401


def test_route_jeton_invalide(client):
    reponse = client.get(
        "/stations", headers={"Authorization": "Bearer jeton.invalide.xyz"},
    )
    assert reponse.status_code == 401


def test_liste_vide(client, jeton_direction):
    reponse = client.get("/stations", headers={"Authorization": "Bearer " + jeton_direction})
    assert reponse.status_code == 200
    assert reponse.json() == {"total": 0, "page": 1, "taille_page": 20, "resultats": []}


def test_stations_pagination(client, donnees, jeton_direction):
    headers = {"Authorization": "Bearer " + jeton_direction}
    reponse = client.get("/stations?page=1&taille_page=50", headers=headers)
    assert reponse.status_code == 200
    resultat = reponse.json()
    assert resultat["total"] == 120
    assert resultat["page"] == 1
    assert resultat["taille_page"] == 50
    assert len(resultat["resultats"]) == 50
    assert resultat["resultats"][0]["station_id"] == "S001"
    assert [s["station_id"] for s in resultat["resultats"]] == sorted(
        s["station_id"] for s in resultat["resultats"]
    )
    assert len(client.get("/stations?page=3&taille_page=50", headers=headers).json()["resultats"]) == 20
    assert client.get("/stations?page=999", headers=headers).json()["resultats"] == []


def test_stations_filtre_commune(client, donnees, jeton_direction):
    reponse = client.get(
        "/stations?commune=Lille&taille_page=100",
        headers={"Authorization": "Bearer " + jeton_direction},
    )
    assert reponse.status_code == 200
    assert reponse.json()["total"] == 46
    assert all(s["commune"] == "Lille" for s in reponse.json()["resultats"])


def test_station_detail(client, donnees, jeton_direction):
    reponse = client.get(
        "/stations/S001", headers={"Authorization": "Bearer " + jeton_direction},
    )
    assert reponse.status_code == 200
    assert reponse.json()["station_id"] == "S001"
    assert reponse.json()["nom"] == "Lille - Gare"
    assert set(reponse.json()) == {
        "station_id", "nom", "commune", "capacite", "latitude", "longitude",
        "date_mise_en_service",
    }


def test_station_introuvable(client, jeton_direction):
    reponse = client.get(
        "/stations/S999", headers={"Authorization": "Bearer " + jeton_direction},
    )
    assert reponse.status_code == 404
    assert reponse.json() == {"detail": "Station introuvable"}


@pytest.mark.parametrize("route", [
    "/stations?page=0",
    "/stations?taille_page=0",
    "/stations?taille_page=101",
    "/trajets?page=-1",
    "/trajets?date_debut=invalide",
    "/trajets?date_debut=2026-08-30&date_fin=2026-08-24",
    "/incidents?statut=ferme",
    "/incidents?taille_page=101",
    "/indicateurs/activite-par-jour?date_debut=invalide",
    "/indicateurs/activite-par-jour?date_debut=2026-08-30&date_fin=2026-08-24",
    "/indicateurs/stations-actives?limite=0",
    "/indicateurs/stations-actives?limite=51",
])
def test_parametres_invalides(client, jeton_direction, route):
    reponse = client.get(route, headers={"Authorization": "Bearer " + jeton_direction})
    assert reponse.status_code == 422


def test_trajets_periode_et_station(client, donnees, jeton_direction):
    headers = {"Authorization": "Bearer " + jeton_direction}
    params = {"date_debut": "2026-08-24", "date_fin": "2026-08-24", "taille_page": 100}
    reponse = client.get("/trajets", headers=headers, params=params)
    assert reponse.status_code == 200
    assert reponse.json()["total"] == 329
    assert all(t["depart_horodatage"].startswith("2026-08-24") for t in reponse.json()["resultats"])

    params["station"] = "S002"
    reponse = client.get("/trajets", headers=headers, params=params)
    assert reponse.status_code == 200
    trajets = reponse.json()["resultats"]
    assert trajets
    assert all(t["station_depart"] == "S002" or t["station_arrivee"] == "S002" for t in trajets)
    assert any(t["station_depart"] != "S002" for t in trajets)
    assert any(t["station_arrivee"] != "S002" for t in trajets)
    heures = [t["depart_horodatage"] for t in trajets]
    assert heures == sorted(heures)


def test_incidents_filtre_et_tri(client, donnees, jeton_direction):
    headers = {"Authorization": "Bearer " + jeton_direction}
    reponse = client.get("/incidents", headers=headers)
    assert reponse.status_code == 200
    assert reponse.json()["total"] == 177
    dates = [i["date_signalement"] for i in reponse.json()["resultats"]]
    assert dates == sorted(dates, reverse=True)

    reponse = client.get("/incidents?statut=ouvert&taille_page=100", headers=headers)
    assert reponse.status_code == 200
    assert reponse.json()["total"] == 55
    assert all(i["statut"] == "ouvert" for i in reponse.json()["resultats"])


def test_resolution_directe(client, donnees, db_session, jeton_exploitant):
    incident = db_session.scalar(select(Incident).where(Incident.statut == "ouvert"))
    reponse = client.put(
        f"/incidents/{incident.incident_id}/statut",
        headers={"Authorization": "Bearer " + jeton_exploitant},
        json={"statut": "resolu"},
    )
    assert reponse.status_code == 200
    assert reponse.json()["statut"] == "resolu"
    assert reponse.json()["date_resolution"] is not None


def test_incident_introuvable(client, jeton_exploitant):
    reponse = client.put(
        "/incidents/I2026-9999/statut",
        headers={"Authorization": "Bearer " + jeton_exploitant},
        json={"statut": "resolu"},
    )
    assert reponse.status_code == 404
    assert reponse.json() == {"detail": "Incident introuvable"}


def test_nouveau_statut_invalide(client, jeton_exploitant):
    reponse = client.put(
        "/incidents/I2026-0001/statut",
        headers={"Authorization": "Bearer " + jeton_exploitant},
        json={"statut": "ouvert"},
    )
    assert reponse.status_code == 422


@pytest.mark.parametrize("role", ["exploitant", "direction"])
def test_indicateurs_accessibles_aux_deux_roles(client, comptes, role):
    connexion = client.post("/auth/login", json={
        "username": role + "01", "password": comptes,
    })
    headers = {"Authorization": "Bearer " + connexion.json()["access_token"]}
    for route in ["activite-par-jour", "stations-actives", "incidents-par-statut"]:
        reponse = client.get("/indicateurs/" + route, headers=headers)
        assert reponse.status_code == 200
        assert reponse.json()["donnees"] == []


def test_activite_comparee_au_sql(client, donnees, db_session, jeton_direction):
    headers = {"Authorization": "Bearer " + jeton_direction}
    params = {"date_debut": "2026-08-24", "date_fin": "2026-08-30"}
    reponse = client.get("/indicateurs/activite-par-jour", headers=headers, params=params)
    assert reponse.status_code == 200
    lignes = db_session.execute(text("""
        SELECT depart_horodatage::date AS jour, count(*) AS nb_trajets
        FROM trajet
        WHERE depart_horodatage::date BETWEEN '2026-08-24' AND '2026-08-30'
        GROUP BY jour ORDER BY jour
    """)).mappings().all()
    attendu = [
        {"jour": ligne["jour"].isoformat(), "nb_trajets": ligne["nb_trajets"]}
        for ligne in lignes
    ]
    assert reponse.json() == {"donnees": attendu}
    trajets = client.get("/trajets", headers=headers, params=params).json()
    assert sum(ligne["nb_trajets"] for ligne in attendu) == trajets["total"] == 2002


def test_stations_actives_sur_csv(client, donnees, db_session, jeton_direction):
    headers = {"Authorization": "Bearer " + jeton_direction}
    reponse = client.get("/indicateurs/stations-actives", headers=headers)
    assert reponse.status_code == 200
    lignes = db_session.execute(text("""
        SELECT s.station_id, s.nom,
               count(*) FILTER (WHERE m.sens = 'depart') AS nb_departs,
               count(*) FILTER (WHERE m.sens = 'arrivee') AS nb_arrivees
        FROM station s
        JOIN (
            SELECT station_depart AS station_id, 'depart' AS sens FROM trajet
            UNION ALL
            SELECT station_arrivee, 'arrivee' FROM trajet WHERE station_arrivee IS NOT NULL
        ) m ON m.station_id = s.station_id
        GROUP BY s.station_id, s.nom
        ORDER BY count(*) DESC, s.station_id
        LIMIT 10
    """)).mappings().all()
    assert reponse.json() == {"donnees": [dict(ligne) for ligne in lignes]}
    assert len(reponse.json()["donnees"]) == 10


def test_incidents_indicateur_sur_csv(client, donnees, db_session, jeton_direction):
    reponse = client.get(
        "/indicateurs/incidents-par-statut",
        headers={"Authorization": "Bearer " + jeton_direction},
    )
    assert reponse.status_code == 200
    resultat = reponse.json()
    assert resultat["donnees"] == [
        {"statut": "en_cours", "nb_incidents": 46},
        {"statut": "ouvert", "nb_incidents": 55},
        {"statut": "resolu", "nb_incidents": 76},
    ]
    delai = db_session.scalar(text("""
        SELECT avg(extract(epoch FROM date_resolution - date_signalement)) / 3600
        FROM incident WHERE statut = 'resolu' AND date_resolution IS NOT NULL
    """))
    assert resultat["delai_moyen_resolution_heures"] == round(float(delai), 1)
