import streamlit as st

from api_client import ErreurApi, appeler_api
from interface import session

st.set_page_config(page_title="VéloVille", layout="wide")
st.title("VéloVille — Plateforme de restitution")
session(requise=False)

if "jeton" in st.session_state:
    st.success(
        f"Connecté en tant que {st.session_state['identifiant']} "
        f"(rôle : {st.session_state['role']})."
    )
    st.info("Utilisez le menu latéral pour accéder aux écrans.")
else:
    st.subheader("Connexion")
    with st.form("connexion"):
        identifiant = st.text_input("Identifiant")
        mot_de_passe = st.text_input("Mot de passe", type="password")
        valider = st.form_submit_button("Se connecter")
    if valider:
        try:
            with st.spinner("Chargement..."):
                reponse = appeler_api("POST", "/auth/login", donnees={
                    "username": identifiant, "password": mot_de_passe,
                })
            st.session_state.update(
                jeton=reponse["access_token"], role=reponse["role"],
                identifiant=identifiant,
            )
            st.rerun()
        except ErreurApi as erreur:
            st.error(str(erreur))
