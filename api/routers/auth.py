from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import Connexion, Jeton
from api.services.ressources import connexion

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=Jeton)
def login(donnees: Connexion, db: Session = Depends(get_db)):
    return connexion(db, donnees.username, donnees.password)
