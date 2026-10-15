import math

import streamlit as st

from api_client import ErreurApi, appeler_api
from interface import communes, session, tableau

st.set_page_config(page_title="Stations — VéloVille", layout="wide")
session()
st.title("Stations")

try:
    with st.spinner("Chargement..."):
        liste_communes = communes(st.session_state["jeton"])
    commune = st.selectbox("Commune", ["Toutes"] + liste_communes)
    taille_page = st.selectbox("Taille de page", [10, 20, 50], index=1)
    page = st.number_input("Page", min_value=1, value=1, step=1)
    params = {"page": page, "taille_page": taille_page}
    if commune != "Toutes":
        params["commune"] = commune
    with st.spinner("Chargement..."):
        reponse = appeler_api(
            "GET", "/stations", st.session_state["jeton"], params=params,
        )
    st.write(f"{reponse['total']} stations au total")
    tableau(reponse["resultats"], [
        "station_id", "nom", "commune", "capacite", "date_mise_en_service",
    ])
    st.write(f"Page {page} sur {max(1, math.ceil(reponse['total'] / taille_page))}")
except ErreurApi as erreur:
    st.error(str(erreur))
