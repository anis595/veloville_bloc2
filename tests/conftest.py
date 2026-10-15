import os
import uuid

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from api.database import Base, DATABASE_URL, get_db
from api.main import app
from api.models import Utilisateur


@pytest.fixture(scope="session")
def moteur_test():
    moteur = create_engine(os.getenv("TEST_DATABASE_URL", DATABASE_URL))
    yield moteur
    moteur.dispose()


@pytest.fixture
def connexion_test(moteur_test):
    connexion = moteur_test.connect()
    transaction = connexion.begin()
    try:
        schema = "test_" + uuid.uuid4().hex
        connexion.execute(text(f'CREATE SCHEMA "{schema}"'))
        connexion.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        Base.metadata.create_all(connexion)
        yield connexion
    finally:
        transaction.rollback()
        connexion.close()


@pytest.fixture
def db_session(connexion_test):
    with Session(bind=connexion_test, join_transaction_mode="create_savepoint") as db:
        yield db


@pytest.fixture
def comptes(db_session):
    mot_de_passe = os.getenv("TEST_PASSWORD") or uuid.uuid4().hex
    hache = bcrypt.hashpw(mot_de_passe.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    for role in ["exploitant", "direction"]:
        db_session.add(Utilisateur(
            username=role + "01", mot_de_passe_hash=hache, role=role,
        ))
    db_session.flush()
    return mot_de_passe


@pytest.fixture
def client(db_session, comptes):
    def remplacer_db():
        yield db_session
    app.dependency_overrides[get_db] = remplacer_db
    try:
        with TestClient(app) as client_test:
            yield client_test
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def jeton_exploitant(client, comptes):
    reponse = client.post("/auth/login", json={
        "username": "exploitant01", "password": comptes,
    })
    return reponse.json()["access_token"]


@pytest.fixture
def jeton_direction(client, comptes):
    reponse = client.post("/auth/login", json={
        "username": "direction01", "password": comptes,
    })
    return reponse.json()["access_token"]
