import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Utilisateur

ALGORITHME = os.getenv("JWT_ALGORITHM", "HS256")
if ALGORITHME != "HS256":
    raise ValueError("JWT_ALGORITHM doit valoir HS256")

bearer = HTTPBearer(auto_error=False)


def verifier_mot_de_passe(clair, hache):
    try:
        return bcrypt.checkpw(clair.encode("utf-8"), hache.encode("utf-8"))
    except ValueError:
        return False


def creer_access_token(username, role):
    duree = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))
    expiration = datetime.now(timezone.utc) + timedelta(minutes=duree)
    contenu = {"sub": username, "role": role, "exp": expiration}
    return jwt.encode(contenu, os.environ["JWT_SECRET"], algorithm=ALGORITHME)


def decoder_access_token(token):
    return jwt.decode(
        token,
        os.environ["JWT_SECRET"],
        algorithms=[ALGORITHME],
        options={"require": ["sub", "role", "exp"]},
    )


def utilisateur_courant(
    identifiants: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    erreur = HTTPException(
        401,
        "Authentification requise ou jeton invalide",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if identifiants is None:
        raise erreur
    try:
        contenu = decoder_access_token(identifiants.credentials)
    except jwt.InvalidTokenError:
        raise erreur

    utilisateur = db.scalar(
        select(Utilisateur).where(Utilisateur.username == contenu["sub"])
    )
    if utilisateur is None or contenu["role"] != utilisateur.role:
        raise erreur
    return utilisateur


def exiger_role(role):
    def verifier(utilisateur=Depends(utilisateur_courant)):
        if utilisateur.role != role:
            raise HTTPException(403, "Acces reserve au role exploitant")
        return utilisateur
    return verifier
