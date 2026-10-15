from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import ActiviteReponse, IncidentsStatutReponse, StationsActivesReponse
from api.securite import utilisateur_courant
from api.services import indicateurs

router = APIRouter(
    prefix="/indicateurs", tags=["Indicateurs"],
    dependencies=[Depends(utilisateur_courant)],
)


@router.get("/activite-par-jour", response_model=ActiviteReponse)
def activite(
    date_debut: date | None = None,
    date_fin: date | None = None,
    db: Session = Depends(get_db),
):
    return indicateurs.activite_par_jour(db, date_debut, date_fin)


@router.get("/stations-actives", response_model=StationsActivesReponse)
def stations(
    limite: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return indicateurs.stations_actives(db, limite)


@router.get("/incidents-par-statut", response_model=IncidentsStatutReponse)
def incidents(db: Session = Depends(get_db)):
    return indicateurs.incidents_par_statut(db)
