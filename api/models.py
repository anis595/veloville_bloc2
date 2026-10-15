from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class Station(Base):
    __tablename__ = "station"
    __table_args__ = (CheckConstraint("capacite > 0"),)

    station_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    nom: Mapped[str] = mapped_column(Text)
    commune: Mapped[str] = mapped_column(Text)
    capacite: Mapped[int]
    latitude: Mapped[Decimal] = mapped_column(Numeric(8, 5))
    longitude: Mapped[Decimal] = mapped_column(Numeric(8, 5))
    date_mise_en_service: Mapped[date] = mapped_column(Date)


class Trajet(Base):
    __tablename__ = "trajet"
    __table_args__ = (
        CheckConstraint("duree_secondes > 0"),
        CheckConstraint("type_usager IN ('abonne', 'occasionnel')"),
        CheckConstraint("(type_usager = 'abonne' AND usager_ref IS NOT NULL) OR (type_usager = 'occasionnel' AND usager_ref IS NULL)"),
    )

    trajet_id: Mapped[str] = mapped_column(String(12), primary_key=True)
    velo_id: Mapped[str] = mapped_column(String(8))
    depart_horodatage: Mapped[datetime] = mapped_column(DateTime)
    station_depart: Mapped[str] = mapped_column(ForeignKey("station.station_id"))
    station_arrivee: Mapped[str | None] = mapped_column(ForeignKey("station.station_id"))
    duree_secondes: Mapped[int]
    type_usager: Mapped[str] = mapped_column(Text)
    usager_ref: Mapped[str | None] = mapped_column(Text)


class Incident(Base):
    __tablename__ = "incident"
    __table_args__ = (
        CheckConstraint("statut IN ('ouvert', 'en_cours', 'resolu')"),
        CheckConstraint("(cible = 'velo' AND velo_id IS NOT NULL AND station_id IS NULL) OR (cible = 'station' AND station_id IS NOT NULL AND velo_id IS NULL)"),
        CheckConstraint("(statut = 'resolu' AND date_resolution IS NOT NULL AND date_resolution >= date_signalement) OR (statut <> 'resolu' AND date_resolution IS NULL)"),
    )

    incident_id: Mapped[str] = mapped_column(String(12), primary_key=True)
    date_signalement: Mapped[datetime] = mapped_column(DateTime)
    cible: Mapped[str] = mapped_column(Text)
    velo_id: Mapped[str | None] = mapped_column(String(8))
    station_id: Mapped[str | None] = mapped_column(ForeignKey("station.station_id"))
    type_incident: Mapped[str] = mapped_column(Text)
    statut: Mapped[str] = mapped_column(Text)
    date_resolution: Mapped[datetime | None] = mapped_column(DateTime)
    technicien: Mapped[str | None] = mapped_column(Text)


class Utilisateur(Base):
    __tablename__ = "utilisateur"
    __table_args__ = (CheckConstraint("role IN ('exploitant', 'direction')"),)

    id_utilisateur: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(Text, unique=True)
    mot_de_passe_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
