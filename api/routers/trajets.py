from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import TrajetsPage
from api.securite import utilisateur_courant
from api.services.ressources import lister_trajets

router = APIRouter(
    prefix="/trajets", tags=["Trajets"],
    dependencies=[Depends(utilisateur_courant)],
)


@router.get("", response_model=TrajetsPage)
def trajets(
    date_debut: date | None = None,
    date_fin: date | None = None,
    station: str | None = None,
    page: int = Query(1, ge=1),
    taille_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return lister_trajets(db, date_debut, date_fin, station, page, taille_page)
