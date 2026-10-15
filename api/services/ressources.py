from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import Date, cast, func, or_, select

from api.models import Incident, Station, Trajet, Utilisateur
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


def paginer(db, requete, page, taille_page):
    total = db.scalar(
        select(func.count()).select_from(requete.order_by(None).subquery())
    )
    decalage = (page - 1) * taille_page
    resultats = db.scalars(requete.offset(decalage).limit(taille_page)).all()
    return {
        "total": total,
        "page": page,
        "taille_page": taille_page,
        "resultats": resultats,
    }


def lister_stations(db, commune, page, taille_page):
    requete = select(Station).order_by(Station.station_id)
    if commune is not None:
        requete = requete.where(Station.commune == commune)
    return paginer(db, requete, page, taille_page)


def lire_station(db, station_id):
    station = db.get(Station, station_id)
    if station is None:
        raise HTTPException(404, "Station introuvable")
    return station


def filtrer_periode(requete, colonne, date_debut, date_fin):
    if date_debut and date_fin and date_debut > date_fin:
        raise HTTPException(422, "La date de debut doit preceder la date de fin")
    if date_debut:
        requete = requete.where(cast(colonne, Date) >= date_debut)
    if date_fin:
        requete = requete.where(cast(colonne, Date) <= date_fin)
    return requete


def lister_trajets(db, date_debut, date_fin, station, page, taille_page):
    requete = filtrer_periode(
        select(Trajet), Trajet.depart_horodatage, date_debut, date_fin,
    )
    if station is not None:
        requete = requete.where(or_(
            Trajet.station_depart == station, Trajet.station_arrivee == station,
        ))
    requete = requete.order_by(Trajet.depart_horodatage, Trajet.trajet_id)
    return paginer(db, requete, page, taille_page)


def lister_incidents(db, statut, page, taille_page):
    requete = select(Incident).order_by(
        Incident.date_signalement.desc(), Incident.incident_id,
    )
    if statut is not None:
        requete = requete.where(Incident.statut == statut)
    return paginer(db, requete, page, taille_page)


def changer_statut(db, incident_id, statut):
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(404, "Incident introuvable")
    transitions = {
        "ouvert": ["en_cours", "resolu"],
        "en_cours": ["resolu"],
        "resolu": [],
    }
    if statut not in transitions[incident.statut]:
        raise HTTPException(422, "Transition de statut non autorisee")
    incident.statut = statut
    if statut == "resolu" and incident.date_resolution is None:
        incident.date_resolution = datetime.now()
    db.commit()
    db.refresh(incident)
    return incident
