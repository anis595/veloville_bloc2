import pandas as pd
import streamlit as st

from api_client import appeler_api

LIBELLES = {
    "station_id": "Identifiant de station", "nom": "Nom", "commune": "Commune",
    "capacite": "Capacité", "date_mise_en_service": "Mise en service",
    "incident_id": "Identifiant", "date_signalement": "Signalé le",
    "cible": "Cible", "velo_id": "Vélo", "type_incident": "Type",
    "statut": "Statut", "date_resolution": "Résolu le", "technicien": "Technicien",
    "jour": "Jour", "nb_trajets": "Nombre de trajets", "nb_departs": "Départs",
    "nb_arrivees": "Arrivées", "total": "Total", "nb_incidents": "Nombre d'incidents",
}


def session(requise=True):
    if "jeton" not in st.session_state:
        if requise:
            st.info("Veuillez vous connecter")
            st.page_link("app.py", label="Aller à la connexion")
            st.stop()
        return
    st.sidebar.write(f"Connecté : {st.session_state['identifiant']}")
    st.sidebar.write(f"Rôle : {st.session_state['role']}")
    if st.sidebar.button("Se déconnecter"):
        st.session_state.clear()
        st.switch_page("app.py")


def tableau(donnees, colonnes=None):
    if not donnees:
        st.info("Aucun résultat pour ces critères.")
        return
    df = pd.DataFrame(donnees)
    if colonnes:
        df = df[colonnes]
    st.dataframe(df.rename(columns=LIBELLES), hide_index=True, width="stretch")


@st.cache_data(ttl=3600, show_spinner=False)
def communes(jeton):
    valeurs = set()
    page = 1
    while True:
        reponse = appeler_api(
            "GET", "/stations", jeton, params={"page": page, "taille_page": 100},
        )
        valeurs.update(ligne["commune"] for ligne in reponse["resultats"])
        if page * 100 >= reponse["total"]:
            break
        page += 1
    return sorted(valeurs)
