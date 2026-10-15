from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import ChangementStatut, IncidentLecture, IncidentsPage
from api.securite import exiger_role, utilisateur_courant
from api.services.ressources import changer_statut, lister_incidents

router = APIRouter(
    prefix="/incidents", tags=["Incidents"],
    dependencies=[Depends(utilisateur_courant)],
)


@router.get("", response_model=IncidentsPage)
def incidents(
    statut: Literal["ouvert", "en_cours", "resolu"] | None = None,
    page: int = Query(1, ge=1),
    taille_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return lister_incidents(db, statut, page, taille_page)


@router.put(
    "/{incident_id}/statut", response_model=IncidentLecture,
    dependencies=[Depends(exiger_role("exploitant"))],
)
def modifier_statut(
    incident_id: str, donnees: ChangementStatut, db: Session = Depends(get_db),
):
    return changer_statut(db, incident_id, donnees.statut)
