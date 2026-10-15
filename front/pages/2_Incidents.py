import math

import streamlit as st

from api_client import ErreurApi, appeler_api
from interface import session, tableau

st.set_page_config(page_title="Incidents — VéloVille", layout="wide")
session()
st.title("Incidents")

if "confirmation_incident" in st.session_state:
    st.success(st.session_state.pop("confirmation_incident"))
statut = st.selectbox("Statut", ["Tous", "ouvert", "en_cours", "resolu"])
taille_page = st.selectbox("Taille de page", [10, 20, 50], index=1)
page = st.number_input("Page", min_value=1, value=1, step=1)
params = {"page": page, "taille_page": taille_page}
if statut != "Tous":
    params["statut"] = statut

try:
    with st.spinner("Chargement..."):
        reponse = appeler_api(
            "GET", "/incidents", st.session_state["jeton"], params=params,
        )
    st.write(f"{reponse['total']} incidents au total")
    tableau(reponse["resultats"])
    st.write(f"Page {page} sur {max(1, math.ceil(reponse['total'] / taille_page))}")
    if st.session_state["role"] == "exploitant" and reponse["resultats"]:
        st.subheader("Changer le statut d'un incident")
        with st.form("modifier_incident"):
            incident_id = st.selectbox(
                "Incident", [ligne["incident_id"] for ligne in reponse["resultats"]],
            )
            nouveau_statut = st.selectbox("Nouveau statut", ["en_cours", "resolu"])
            appliquer = st.form_submit_button("Appliquer")
        if appliquer:
            with st.spinner("Chargement..."):
                appeler_api(
                    "PUT", f"/incidents/{incident_id}/statut",
                    st.session_state["jeton"], donnees={"statut": nouveau_statut},
                )
            st.session_state["confirmation_incident"] = (
                f"Statut de l'incident {incident_id} mis à jour : {nouveau_statut}."
            )
            st.rerun()
    elif st.session_state["role"] == "direction":
        st.info("La modification des incidents est réservée aux exploitants.")
except ErreurApi as erreur:
    st.error(str(erreur))
