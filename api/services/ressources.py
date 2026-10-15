from fastapi import HTTPException
from sqlalchemy import select

from api.models import Utilisateur
from api.securite import creer_access_token, verifier_mot_de_passe


def connexion(db, username, password):
    utilisateur = db.scalar(
        select(Utilisateur).where(Utilisateur.username == username)
    )
    if utilisateur is None or not verifier_mot_de_passe(
        password, utilisateur.mot_de_passe_hash,
    ):
        raise HTTPException(401, "Identifiants invalides")
    return {
        "access_token": creer_access_token(username, utilisateur.role),
        "token_type": "bearer",
        "role": utilisateur.role,
    }
