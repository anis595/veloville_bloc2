from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import requests
from streamlit.testing.v1 import AppTest

from api.models import Incident

PAGES = ["1_Stations.py", "2_Incidents.py", "3_Indicateurs.py"]


@pytest.fixture
def ecran(client, monkeypatch):
    dossier = Path(__file__).resolve().parents[2] / "front"
    monkeypatch.syspath_prepend(str(dossier))

    def requete(methode, url, **options):
        return client.request(
            methode, urlsplit(url).path, params=options["params"],
            json=options["json"], headers=options["headers"],
        )

    monkeypatch.setattr(requests, "request", requete)
    return AppTest.from_file(str(dossier / "app.py"), default_timeout=15).run()


def connecter(ecran, mot_de_passe, role="direction"):
    ecran.text_input[0].input(role + "01")
    ecran.text_input[1].input(mot_de_passe)
    ecran.button[0].click().run()
    assert not ecran.exception
    assert ecran.session_state["role"] == role


@pytest.mark.parametrize("page", PAGES)
def test_page_sans_connexion(ecran, monkeypatch, page):
    def requete_interdite(*args, **kwargs):
        raise AssertionError("Une page sans session ne doit pas appeler l'API")

    monkeypatch.setattr(requests, "request", requete_interdite)
    ecran.switch_page("pages/" + page).run()
    assert not ecran.exception
    assert ecran.info[0].value == "Veuillez vous connecter"
    assert not ecran.dataframe


def test_stations_filtre_pagination_et_vide(ecran, comptes, donnees):
    connecter(ecran, comptes)
    ecran.switch_page("pages/1_Stations.py").run()
    assert not ecran.exception
    assert len(ecran.dataframe[0].value) == 20
    assert list(ecran.dataframe[0].value.columns) == [
        "Identifiant de station", "Nom", "Commune", "Capacité", "Mise en service",
    ]
    ecran.selectbox[0].select("Lille").run()
    assert all(ecran.dataframe[0].value["Commune"] == "Lille")
    assert any(m.value == "46 stations au total" for m in ecran.markdown)
    ecran.selectbox[1].select(50).run()
    assert len(ecran.dataframe[0].value) == 46
    ecran.number_input[0].set_value(2).run()
    assert not ecran.exception
    assert not ecran.dataframe
    assert ecran.info[0].value == "Aucun résultat pour ces critères."


def test_incidents_direction_sans_modification(ecran, comptes, donnees):
    connecter(ecran, comptes)
    ecran.switch_page("pages/2_Incidents.py").run()
    ecran.selectbox[0].select("ouvert").run()
    assert not ecran.exception
    assert all(ecran.dataframe[0].value["Statut"] == "ouvert")
    assert any(m.value == "55 incidents au total" for m in ecran.markdown)
    assert not any(b.label == "Appliquer" for b in ecran.button)
    assert ecran.info[0].value == "La modification des incidents est réservée aux exploitants."


def test_incidents_modification_et_transition_refusee(ecran, comptes, donnees, db_session):
    connecter(ecran, comptes, "exploitant")
    ecran.switch_page("pages/2_Incidents.py").run()
    ecran.selectbox[0].select("ouvert").run()
    incident_id = ecran.selectbox[2].value
    next(b for b in ecran.button if b.label == "Appliquer").click().run()
    assert not ecran.exception
    assert "mis à jour : en_cours" in ecran.success[0].value
    assert db_session.get(Incident, incident_id).statut == "en_cours"
    assert incident_id not in set(ecran.dataframe[0].value["Identifiant"])

    ecran.selectbox[0].select("en_cours").run()
    ecran.selectbox[2].select(incident_id)
    next(b for b in ecran.button if b.label == "Appliquer").click().run()
    assert not ecran.exception
    assert ecran.error[0].value == "Transition de statut non autorisée."


def test_indicateurs_metriques_et_filtres(ecran, comptes, donnees):
    connecter(ecran, comptes)
    ecran.switch_page("pages/3_Indicateurs.py").run()
    assert not ecran.exception
    assert ecran.metric[0].value == "2002"
    assert ecran.metric[1].value == "10"
    assert len(ecran.dataframe) == 3
    stations = ecran.dataframe[1].value
    assert all(stations["Total"] == stations["Départs"] + stations["Arrivées"])

    ecran.number_input[0].set_value(3)
    next(b for b in ecran.button if b.label == "Actualiser").click().run()
    assert ecran.metric[1].value == "3"
    ecran.date_input[0].set_value(date(2026, 8, 31))
    next(b for b in ecran.button if b.label == "Actualiser").click().run()
    assert not ecran.exception
    assert ecran.error[0].value == "Les critères saisis sont invalides."


def test_indicateurs_sans_donnees(ecran, comptes):
    connecter(ecran, comptes)
    ecran.switch_page("pages/3_Indicateurs.py").run()
    assert not ecran.exception
    assert [m.value for m in ecran.metric] == ["0", "0", "n. d."]
    assert not ecran.dataframe
    assert len(ecran.info) == 3


@pytest.mark.parametrize("page", PAGES)
def test_page_api_injoignable(ecran, comptes, monkeypatch, page):
    connecter(ecran, comptes)

    def panne(*args, **kwargs):
        raise requests.ConnectionError()

    monkeypatch.setattr(requests, "request", panne)
    ecran.switch_page("pages/" + page).run()
    assert not ecran.exception
    assert ecran.error[0].value == "L'API est injoignable. Vérifiez qu'elle est démarrée."
