import json

import pytest
import requests

from front.api_client import API_TIMEOUT_SECONDES, API_URL, ErreurApi, appeler_api


def test_appel_transmet_parametres_et_jeton(monkeypatch):
    appel = {}

    def requete(methode, url, **options):
        appel.update(methode=methode, url=url, **options)
        reponse = requests.Response()
        reponse.status_code = 200
        reponse._content = b'{"donnees": []}'
        return reponse

    monkeypatch.setattr(requests, "request", requete)
    assert appeler_api(
        "GET", "/stations", jeton="jeton-test", params={"commune": "Lille"},
    ) == {"donnees": []}
    assert appel == {
        "methode": "GET", "url": API_URL + "/stations",
        "params": {"commune": "Lille"}, "json": None,
        "headers": {"Authorization": "Bearer jeton-test"},
        "timeout": API_TIMEOUT_SECONDES,
    }


def test_login_sans_entete_bearer(monkeypatch):
    def requete(methode, url, **options):
        assert methode == "POST"
        assert options["headers"] == {}
        assert options["json"] == {"username": "compte-test", "password": "test"}
        reponse = requests.Response()
        reponse.status_code = 200
        reponse._content = b'{"role": "direction"}'
        return reponse

    monkeypatch.setattr(requests, "request", requete)
    assert appeler_api("POST", "/auth/login", donnees={
        "username": "compte-test", "password": "test",
    }) == {"role": "direction"}


@pytest.mark.parametrize("code,methode,chemin,message", [
    (401, "POST", "/auth/login", "Identifiant ou mot de passe incorrect."),
    (401, "GET", "/stations", "Votre session est invalide ou expirée. Veuillez vous reconnecter."),
    (403, "PUT", "/incidents/I2026-0001/statut", "Vous n'avez pas le droit de modifier un incident."),
    (404, "GET", "/stations/S999", "Station introuvable."),
    (404, "PUT", "/incidents/I2026-9999/statut", "Incident introuvable."),
    (422, "PUT", "/incidents/I2026-0001/statut", "Transition de statut non autorisée."),
    (422, "GET", "/trajets", "Les critères saisis sont invalides."),
    (500, "GET", "/stations", "L'API a rencontré une erreur. Réessayez."),
])
def test_erreurs_http_en_francais(monkeypatch, code, methode, chemin, message):
    def requete(*args, **kwargs):
        reponse = requests.Response()
        reponse.status_code = code
        reponse._content = json.dumps({"detail": "Erreur technique"}).encode()
        return reponse

    monkeypatch.setattr(requests, "request", requete)
    with pytest.raises(ErreurApi) as erreur:
        appeler_api(methode, chemin)
    assert str(erreur.value) == message


@pytest.mark.parametrize("exception,message", [
    (requests.Timeout, "L'API met trop de temps à répondre. Réessayez."),
    (requests.ConnectionError, "L'API est injoignable. Vérifiez qu'elle est démarrée."),
])
def test_erreurs_reseau_en_francais(monkeypatch, exception, message):
    def requete(*args, **kwargs):
        raise exception()

    monkeypatch.setattr(requests, "request", requete)
    with pytest.raises(ErreurApi) as erreur:
        appeler_api("GET", "/stations")
    assert str(erreur.value) == message


def test_reponse_json_illisible(monkeypatch):
    def requete(*args, **kwargs):
        reponse = requests.Response()
        reponse.status_code = 200
        reponse._content = b"reponse incorrecte"
        return reponse

    monkeypatch.setattr(requests, "request", requete)
    with pytest.raises(ErreurApi) as erreur:
        appeler_api("GET", "/stations")
    assert str(erreur.value) == "La réponse de l'API est illisible. Réessayez."
