from sqlalchemy import Date, cast, func, select

from api.models import Incident, Station, Trajet
from api.services.ressources import filtrer_periode


def activite_par_jour(session, date_debut=None, date_fin=None):
    jour = cast(Trajet.depart_horodatage, Date)
    requete = select(jour.label("jour"), func.count().label("nb_trajets"))
    requete = filtrer_periode(
        requete, Trajet.depart_horodatage, date_debut, date_fin,
    )
    requete = requete.group_by(jour).order_by(jour)
    lignes = session.execute(requete).mappings().all()
    return {"donnees": [dict(ligne) for ligne in lignes]}


def stations_actives(session, limite=10):
    # Compter séparément les départs et les arrivées évite de les multiplier.
    departs = (
        select(Trajet.station_depart.label("station_id"), func.count().label("nombre"))
        .group_by(Trajet.station_depart)
        .subquery()
    )
    arrivees = (
        select(Trajet.station_arrivee.label("station_id"), func.count().label("nombre"))
        .where(Trajet.station_arrivee.is_not(None))
        .group_by(Trajet.station_arrivee)
        .subquery()
    )
    nb_departs = func.coalesce(departs.c.nombre, 0)
    nb_arrivees = func.coalesce(arrivees.c.nombre, 0)
    total = nb_departs + nb_arrivees
    requete = (
        select(
            Station.station_id, Station.nom,
            nb_departs.label("nb_departs"), nb_arrivees.label("nb_arrivees"),
        )
        .outerjoin(departs, Station.station_id == departs.c.station_id)
        .outerjoin(arrivees, Station.station_id == arrivees.c.station_id)
        .where(total > 0)
        .order_by(total.desc(), Station.station_id)
        .limit(limite)
    )
    lignes = session.execute(requete).mappings().all()
    return {"donnees": [dict(ligne) for ligne in lignes]}


def incidents_par_statut(session):
    requete = (
        select(Incident.statut, func.count().label("nb_incidents"))
        .group_by(Incident.statut)
        .order_by(Incident.statut)
    )
    lignes = session.execute(requete).mappings().all()
    duree_heures = func.extract(
        "epoch", Incident.date_resolution - Incident.date_signalement,
    ) / 3600
    delai = session.scalar(
        select(func.avg(duree_heures)).where(
            Incident.statut == "resolu", Incident.date_resolution.is_not(None),
        )
    )
    return {
        "donnees": [dict(ligne) for ligne in lignes],
        "delai_moyen_resolution_heures": round(float(delai), 1) if delai is not None else None,
    }
