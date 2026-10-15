import os
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from api.securite import decoder_access_token, exiger_role, utilisateur_courant


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


def test_role_direction_refuse(db_session, jeton_direction):
    identifiants = HTTPAuthorizationCredentials(scheme="Bearer", credentials=jeton_direction)
    utilisateur = utilisateur_courant(identifiants, db_session)

    with pytest.raises(HTTPException) as erreur:
        exiger_role("exploitant")(utilisateur)
    assert erreur.value.status_code == 403
    assert erreur.value.detail == "Acces reserve au role exploitant"


def test_role_exploitant_accepte(db_session, jeton_exploitant):
    identifiants = HTTPAuthorizationCredentials(scheme="Bearer", credentials=jeton_exploitant)
    utilisateur = utilisateur_courant(identifiants, db_session)
    assert exiger_role("exploitant")(utilisateur).username == "exploitant01"
