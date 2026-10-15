from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Connexion(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class Jeton(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Literal["exploitant", "direction"]


class StationLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    station_id: str
    nom: str
    commune: str
    capacite: int
    latitude: float
    longitude: float
    date_mise_en_service: date


class TrajetLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    trajet_id: str
    velo_id: str
    depart_horodatage: datetime
    station_depart: str
    station_arrivee: str | None
    duree_secondes: int
    type_usager: str
    usager_ref: str | None


class IncidentLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    incident_id: str
    date_signalement: datetime
    cible: str
    velo_id: str | None
    station_id: str | None
    type_incident: str
    statut: str
    date_resolution: datetime | None
    technicien: str | None


class Pagination(BaseModel):
    total: int
    page: int
    taille_page: int


class StationsPage(Pagination):
    resultats: list[StationLecture]


class TrajetsPage(Pagination):
    resultats: list[TrajetLecture]


class IncidentsPage(Pagination):
    resultats: list[IncidentLecture]


class ChangementStatut(BaseModel):
    statut: Literal["en_cours", "resolu"]


class ActiviteJour(BaseModel):
    jour: date
    nb_trajets: int


class ActiviteReponse(BaseModel):
    donnees: list[ActiviteJour]


class StationActive(BaseModel):
    station_id: str
    nom: str
    nb_departs: int
    nb_arrivees: int


class StationsActivesReponse(BaseModel):
    donnees: list[StationActive]


class IncidentsStatut(BaseModel):
    statut: str
    nb_incidents: int


class IncidentsStatutReponse(BaseModel):
    donnees: list[IncidentsStatut]
    delai_moyen_resolution_heures: float | None
