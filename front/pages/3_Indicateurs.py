from datetime import date

import streamlit as st

from api_client import ErreurApi, appeler_api
from interface import session, tableau

st.set_page_config(page_title="Indicateurs — VéloVille", layout="wide")
session()
st.title("Indicateurs")

with st.form("filtres_indicateurs"):
    date_debut = st.date_input("Date de début", date(2026, 8, 24))
    date_fin = st.date_input("Date de fin", date(2026, 8, 30))
    limite = st.number_input("Nombre de stations", min_value=1, max_value=50, value=10)
    st.form_submit_button("Actualiser")

try:
    with st.spinner("Chargement..."):
        jeton = st.session_state["jeton"]
        activite = appeler_api("GET", "/indicateurs/activite-par-jour", jeton, params={
            "date_debut": str(date_debut), "date_fin": str(date_fin),
        })
        stations = appeler_api(
            "GET", "/indicateurs/stations-actives", jeton, params={"limite": limite},
        )
        incidents = appeler_api("GET", "/indicateurs/incidents-par-statut", jeton)
    st.metric("Trajets sur la période", sum(ligne["nb_trajets"] for ligne in activite["donnees"]))
    st.metric("Stations actives", len(stations["donnees"]))
    delai = incidents["delai_moyen_resolution_heures"]
    st.metric(
        "Délai moyen de résolution (h)",
        "n. d." if delai is None else str(delai).replace(".", ","),
    )
    st.subheader("Activité par jour")
    tableau(activite["donnees"])
    st.subheader("Stations les plus actives")
    for ligne in stations["donnees"]:
        ligne["total"] = ligne["nb_departs"] + ligne["nb_arrivees"]
    tableau(stations["donnees"])
    st.subheader("Incidents par statut")
    tableau(incidents["donnees"])
except ErreurApi as erreur:
    st.error(str(erreur))
