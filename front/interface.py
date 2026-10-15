import streamlit as st


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
