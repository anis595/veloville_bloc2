import re
import unicodedata
from datetime import datetime
from math import isfinite

import pandas as pd

COLONNES_JOURNAL = [
    "fichier_source", "identifiant", "colonne", "valeur", "motif", "decision",
]


def est_vide(valeur):
    return valeur is None or pd.isna(valeur) or str(valeur).strip() == ""


def ajouter_journal(journal, fichier, identifiant, colonne, valeur, motif, decision):
    journal.append({
        "fichier_source": fichier,
        "identifiant": identifiant,
        "colonne": colonne,
        "valeur": valeur,
        "motif": motif,
        "decision": decision,
    })


def journal_dataframe(journal):
    return pd.DataFrame(journal, columns=COLONNES_JOURNAL)


def supprimer_accents(texte):
    resultat = ""
    for caractere in unicodedata.normalize("NFD", texte):
        if unicodedata.category(caractere) != "Mn":
            resultat += caractere
    return resultat


def convertir_date(valeur, formats, format_sortie):
    if est_vide(valeur):
        return None
    for format_date in formats:
        try:
            return datetime.strptime(str(valeur).strip(), format_date).strftime(format_sortie)
        except ValueError:
            pass
    return None


def signaler(journal, fichier, ligne, colonne, motif, decision="rejet"):
    colonnes_id = {
        "stations.csv": "station_id",
        "trajets.csv": "trajet_id",
        "incidents.csv": "incident_id",
    }
    colonne_id = colonnes_id[fichier]
    ajouter_journal(journal, fichier, ligne[colonne_id], colonne, ligne.get(colonne), motif, decision)


def normaliser(ligne, colonne, valeur, journal, fichier):
    ancienne = ligne[colonne]
    if not est_vide(ancienne) and str(ancienne) != str(valeur):
        signaler(journal, fichier, ligne, colonne, f"Valeur normalisée en {valeur}", "normalisation")
    ligne[colonne] = valeur


def entier_positif(valeur):
    # Un entier écrit avec .0 est convertible sans perte.
    nombre = float(valeur)
    if not nombre.is_integer() or not 0 < nombre <= 2147483647:
        raise ValueError("Entier strictement positif attendu")
    return int(nombre)


def retirer_doublons(dataframe, fichier, colonne_id):
    journal = []
    for _, ligne in dataframe[dataframe.duplicated()].iterrows():
        signaler(journal, fichier, ligne, colonne_id, "Doublon exact", "rejet")
    return dataframe.drop_duplicates().copy(), journal


def rg1_station(ligne):
    ligne = dict(ligne)
    journal = []
    fichier = "stations.csv"
    normaliser(ligne, "station_id", str(ligne["station_id"]).strip().upper(), journal, fichier)
    rejet = False
    if not re.fullmatch(r"S[0-9]{3}", ligne["station_id"]):
        signaler(journal, fichier, ligne, "station_id", "Identifiant invalide")
        rejet = True
    try:
        normaliser(ligne, "capacite", entier_positif(ligne["capacite"]), journal, fichier)
    except (ValueError, TypeError, OverflowError):
        signaler(journal, fichier, ligne, "capacite", "Capacité invalide")
        rejet = True
    for colonne in ["latitude", "longitude"]:
        try:
            valeur = float(ligne[colonne])
            if not isfinite(valeur):
                raise ValueError
            ligne[colonne] = valeur
        except (ValueError, TypeError):
            signaler(journal, fichier, ligne, colonne, "Coordonnée invalide")
            rejet = True
    for colonne in ["nom", "commune"]:
        if est_vide(ligne[colonne]):
            signaler(journal, fichier, ligne, colonne, "Valeur obligatoire")
            rejet = True
    valeur = convertir_date(ligne["date_mise_en_service"], ["%Y-%m-%d", "%d/%m/%Y"], "%Y-%m-%d")
    if valeur is None:
        signaler(journal, fichier, ligne, "date_mise_en_service", "Date invalide")
        rejet = True
    else:
        normaliser(ligne, "date_mise_en_service", valeur, journal, fichier)
    return ligne, journal, rejet


def rg2_stations_trajet(ligne, station_ids):
    ligne = dict(ligne)
    journal = []
    rejet = False
    for colonne in ["station_depart", "station_arrivee"]:
        if colonne == "station_arrivee" and est_vide(ligne[colonne]):
            continue
        normaliser(ligne, colonne, str(ligne[colonne]).strip().upper(), journal, "trajets.csv")
        if ligne[colonne] not in station_ids:
            signaler(journal, "trajets.csv", ligne, colonne, "Station inexistante ou absente")
            rejet = True
    return ligne, journal, rejet


def rg3_arrivee(ligne):
    ligne = dict(ligne)
    if est_vide(ligne["station_arrivee"]):
        ligne["station_arrivee"] = None
    return ligne, [], False


def rg4_duree(ligne):
    ligne = dict(ligne)
    journal = []
    try:
        normaliser(ligne, "duree_secondes", entier_positif(ligne["duree_secondes"]), journal, "trajets.csv")
    except (ValueError, TypeError, OverflowError):
        signaler(journal, "trajets.csv", ligne, "duree_secondes", "Durée invalide")
        return ligne, journal, True
    return ligne, journal, False


def rg5_usager(ligne):
    ligne = dict(ligne)
    journal = []
    normaliser(ligne, "type_usager", supprimer_accents(str(ligne["type_usager"]).strip().lower()), journal, "trajets.csv")
    type_usager = ligne["type_usager"]
    ref = ligne["usager_ref"]
    if type_usager not in ["abonne", "occasionnel"]:
        signaler(journal, "trajets.csv", ligne, "type_usager", "Type d'usager invalide")
        return ligne, journal, True
    if type_usager == "abonne" and (est_vide(ref) or not re.fullmatch(r"U[0-9a-fA-F]{8}", str(ref).strip())):
        signaler(journal, "trajets.csv", ligne, "usager_ref", "Abonné sans pseudonyme valide")
        return ligne, journal, True
    if type_usager == "occasionnel" and not est_vide(ref):
        signaler(journal, "trajets.csv", ligne, "usager_ref", "Un occasionnel ne doit pas avoir de pseudonyme")
        return ligne, journal, True
    normaliser(ligne, "usager_ref", None if est_vide(ref) else str(ref).strip(), journal, "trajets.csv")
    return ligne, journal, False


def rg6_cible(ligne, station_ids):
    ligne = dict(ligne)
    journal = []
    normaliser(ligne, "cible", str(ligne["cible"]).strip().lower(), journal, "incidents.csv")
    for colonne in ["velo_id", "station_id"]:
        valeur = None if est_vide(ligne[colonne]) else str(ligne[colonne]).strip().upper()
        normaliser(ligne, colonne, valeur, journal, "incidents.csv")
    cible = ligne["cible"]
    velo = ligne["velo_id"]
    station = ligne["station_id"]
    if cible not in ["velo", "station"]:
        signaler(journal, "incidents.csv", ligne, "cible", "Cible invalide")
        return ligne, journal, True
    if cible == "velo":
        cible_valide = velo is not None and station is None
    else:
        cible_valide = station is not None and velo is None
    if not cible_valide:
        signaler(journal, "incidents.csv", ligne, "cible", "La cible doit correspondre à une seule référence")
        return ligne, journal, True
    if cible == "station" and station not in station_ids:
        signaler(journal, "incidents.csv", ligne, "station_id", "Station inexistante")
        return ligne, journal, True
    if cible == "velo" and not re.fullmatch(r"V[0-9]{4}", velo):
        signaler(journal, "incidents.csv", ligne, "velo_id", "Identifiant de vélo invalide")
        return ligne, journal, True
    return ligne, journal, False


def rg7_statut(ligne):
    ligne = dict(ligne)
    journal = []
    statut = supprimer_accents(str(ligne["statut"]).strip().lower()).replace(" ", "_")
    normaliser(ligne, "statut", statut, journal, "incidents.csv")
    if statut not in ["ouvert", "en_cours", "resolu"]:
        signaler(journal, "incidents.csv", ligne, "statut", "Statut invalide")
        return ligne, journal, True
    return ligne, journal, False


def rg8_dates(ligne):
    ligne = dict(ligne)
    journal = []
    rejet = False
    formats = [
        "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S",
    ]
    for colonne in ["date_signalement", "date_resolution"]:
        if colonne == "date_resolution" and est_vide(ligne[colonne]):
            ligne[colonne] = None
            continue
        format_sortie = "%Y-%m-%d %H:%M"
        if str(ligne[colonne]).strip().count(":") == 2:
            format_sortie = "%Y-%m-%d %H:%M:%S"
        valeur = convertir_date(ligne[colonne], formats, format_sortie)
        if valeur is None:
            signaler(journal, "incidents.csv", ligne, colonne, "Date invalide")
            rejet = True
        else:
            normaliser(ligne, colonne, valeur, journal, "incidents.csv")
    resolution = ligne["date_resolution"]
    if not rejet:
        if ligne["statut"] == "resolu" and resolution is None:
            signaler(journal, "incidents.csv", ligne, "date_resolution", "Incident résolu sans date de résolution")
            rejet = True
        elif ligne["statut"] != "resolu" and resolution is not None:
            signaler(journal, "incidents.csv", ligne, "date_resolution", "Date de résolution présente sur un incident non résolu")
            rejet = True
        elif resolution is not None:
            date_resolution = datetime.fromisoformat(resolution)
            date_signalement = datetime.fromisoformat(ligne["date_signalement"])
            if date_resolution < date_signalement:
                signaler(journal, "incidents.csv", ligne, "date_resolution", "Résolution antérieure au signalement")
                rejet = True
    if ligne["statut"] in ["en_cours", "resolu"] and est_vide(ligne["technicien"]):
        signaler(journal, "incidents.csv", ligne, "technicien", "Technicien absent : avertissement, ligne conservée", "normalisation")
    if est_vide(ligne["technicien"]):
        ligne["technicien"] = None
    return ligne, journal, rejet


def format_trajet(ligne):
    ligne = dict(ligne)
    journal = []
    rejet = False
    for colonne, motif in [("trajet_id", r"T[0-9]{6}"), ("velo_id", r"V[0-9]{4}")]:
        normaliser(ligne, colonne, str(ligne[colonne]).strip().upper(), journal, "trajets.csv")
        if not re.fullmatch(motif, ligne[colonne]):
            signaler(journal, "trajets.csv", ligne, colonne, "Identifiant invalide")
            rejet = True
    formats = [
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S",
    ]
    valeur = convertir_date(ligne["depart_horodatage"], formats, "%Y-%m-%d %H:%M:%S")
    if valeur is None:
        signaler(journal, "trajets.csv", ligne, "depart_horodatage", "Date de départ invalide")
        rejet = True
    else:
        normaliser(ligne, "depart_horodatage", valeur, journal, "trajets.csv")
    return ligne, journal, rejet


def fiabiliser(dataframe, fichier, colonne_id, regles, station_ids=None):
    donnees, journal = retirer_doublons(dataframe, fichier, colonne_id)
    valides = []
    ids_vus = set()
    for ligne in donnees.to_dict(orient="records"):
        rejet = False
        if fichier == "incidents.csv":
            identifiant = str(ligne[colonne_id]).strip().upper()
            normaliser(ligne, colonne_id, identifiant, journal, fichier)
        for regle in regles:
            if regle in [rg2_stations_trajet, rg6_cible]:
                ligne, messages, invalide = regle(ligne, station_ids)
            else:
                ligne, messages, invalide = regle(ligne)
            journal.extend(messages)
            rejet = rejet or invalide
        identifiant = ligne[colonne_id]
        if identifiant in ids_vus:
            signaler(journal, fichier, ligne, colonne_id, "Identifiant déjà rencontré")
            rejet = True
        ids_vus.add(identifiant)
        if fichier == "incidents.csv":
            if not re.fullmatch(r"I[0-9]{4}-[0-9]{4}", ligne[colonne_id]):
                signaler(journal, fichier, ligne, colonne_id, "Identifiant d'incident invalide")
                rejet = True
        if not rejet:
            valides.append(ligne)
    return pd.DataFrame(valides, columns=dataframe.columns, dtype=object), journal_dataframe(journal)


def fiabiliser_stations(dataframe):
    return fiabiliser(dataframe, "stations.csv", "station_id", [rg1_station])


def fiabiliser_trajets(dataframe, station_ids):
    regles = [format_trajet, rg2_stations_trajet, rg3_arrivee, rg4_duree, rg5_usager]
    return fiabiliser(dataframe, "trajets.csv", "trajet_id", regles, station_ids)


def fiabiliser_incidents(dataframe, station_ids):
    regles = [rg6_cible, rg7_statut, rg8_dates]
    return fiabiliser(dataframe, "incidents.csv", "incident_id", regles, station_ids)
