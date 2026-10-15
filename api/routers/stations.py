from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import StationLecture, StationsPage
from api.securite import utilisateur_courant
from api.services import ressources

router = APIRouter(
    prefix="/stations", tags=["Stations"],
    dependencies=[Depends(utilisateur_courant)],
)


@router.get("", response_model=StationsPage)
def lister_stations(
    commune: str | None = None,
    page: int = Query(1, ge=1),
    taille_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return ressources.lister_stations(db, commune, page, taille_page)


@router.get("/{station_id}", response_model=StationLecture)
def lire_station(station_id: str, db: Session = Depends(get_db)):
    return ressources.lire_station(db, station_id)
