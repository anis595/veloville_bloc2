import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
API_TIMEOUT_SECONDES = float(os.getenv("API_TIMEOUT_SECONDES", "5"))


class ErreurApi(Exception):
    """Erreur levée lorsque l'API est injoignable ou répond en erreur."""


def appeler_api(methode, chemin, jeton=None, params=None, donnees=None):
    headers = {"Authorization": f"Bearer {jeton}"} if jeton else {}
    try:
        reponse = requests.request(
            methode, API_URL + chemin, params=params, json=donnees,
            headers=headers, timeout=API_TIMEOUT_SECONDES,
        )
    except requests.Timeout:
        raise ErreurApi("L'API met trop de temps à répondre. Réessayez.")
    except requests.RequestException:
        raise ErreurApi("L'API est injoignable. Vérifiez qu'elle est démarrée.")

    if reponse.status_code >= 400:
        messages = {
            401: "Identifiant ou mot de passe incorrect." if chemin == "/auth/login"
            else "Votre session est invalide ou expirée. Veuillez vous reconnecter.",
            403: "Vous n'avez pas le droit de modifier un incident.",
            404: "Incident introuvable." if chemin.startswith("/incidents/")
            else "Station introuvable.",
            422: "Transition de statut non autorisée." if methode == "PUT"
            else "Les critères saisis sont invalides.",
        }
        raise ErreurApi(messages.get(
            reponse.status_code, "L'API a rencontré une erreur. Réessayez.",
        ))
    try:
        return reponse.json()
    except ValueError:
        raise ErreurApi("La réponse de l'API est illisible. Réessayez.")
