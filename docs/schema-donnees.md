# Schéma de données

## Modèle logique

```text
STATION (station_id PK, nom, commune, capacite, latitude, longitude,
         date_mise_en_service)
TRAJET (trajet_id PK, velo_id, depart_horodatage,
        station_depart FK -> STATION.station_id,
        station_arrivee FK -> STATION.station_id NULL,
        duree_secondes, type_usager, usager_ref NULL)
INCIDENT (incident_id PK, date_signalement, cible, velo_id NULL,
          station_id FK -> STATION.station_id NULL, type_incident,
          statut, date_resolution NULL, technicien NULL)
UTILISATEUR (id_utilisateur PK, username UNIQUE, mot_de_passe_hash, role)
```

Une station peut être référencée par plusieurs départs, arrivées et incidents.
Un trajet possède une station de départ et éventuellement une station d'arrivée.
Un incident vise une station ou un vélo. Le périmètre ne prévoit pas de table
de vélos, d'abonnés ou de relation entre utilisateur et trajet.

## Tables et contraintes

Toutes les colonnes sont obligatoires sauf celles indiquées `NULL` dans le MLD.

| Table | Colonnes et types | Contraintes |
|---|---|---|
| station | station_id VARCHAR(10) ; nom et commune TEXT ; capacite INTEGER ; latitude et longitude NUMERIC(8,5) ; date_mise_en_service DATE | Clé primaire station_id ; capacité strictement positive |
| trajet | trajet_id VARCHAR(12) ; velo_id VARCHAR(8) ; depart_horodatage TIMESTAMP ; station_depart et station_arrivee VARCHAR(10) ; duree_secondes INTEGER ; type_usager et usager_ref TEXT | Clé primaire trajet_id ; deux clés étrangères vers station ; durée positive ; type abonne ou occasionnel ; référence obligatoire pour un abonné et absente pour un occasionnel |
| incident | incident_id VARCHAR(12) ; date_signalement et date_resolution TIMESTAMP ; cible, type_incident, statut et technicien TEXT ; velo_id VARCHAR(8) ; station_id VARCHAR(10) | Clé primaire incident_id ; clé étrangère station_id ; statut ouvert, en_cours ou resolu ; une seule cible ; résolution renseignée uniquement pour un incident résolu et postérieure ou égale au signalement |
| utilisateur | id_utilisateur SERIAL ; username, mot_de_passe_hash et role TEXT | Clé primaire id_utilisateur ; username unique ; rôle exploitant ou direction |

Les modèles de `api/models.py` correspondent aux tables de `sql/schema.sql`.
Le script SQL est rejouable avec `CREATE TABLE IF NOT EXISTS` ; il ne migre
pas les contraintes d'une ancienne table déjà présente.

## Règles RG1 à RG8

| Règle | Import et service | Base |
|---|---|---|
| RG1 — Station valide | Identifiant S suivi de trois chiffres, champs obligatoires, coordonnées numériques finies, date valide et capacité positive | Clé primaire, NOT NULL, types et CHECK capacité |
| RG2 — Stations connues | Départ obligatoire et connu ; arrivée renseignée appartenant au référentiel | NOT NULL sur le départ ; deux clés étrangères |
| RG3 — Arrivée facultative | Champ vide converti en None, sans rejet | station_arrivee accepte NULL |
| RG4 — Durée positive | Durée entière strictement positive | CHECK duree_secondes > 0 |
| RG5 — Usager cohérent | Type normalisé ; pseudonyme U suivi de huit caractères hexadécimaux pour un abonné ; aucun pour un occasionnel | CHECK sur le type et la présence du pseudonyme ; format contrôlé à l'import |
| RG6 — Une cible | Vélo ou station, une seule référence ; format du vélo et existence de la station vérifiés | CHECK sur la cible et les références ; clé étrangère station_id |
| RG7 — Statut et transitions | Statut normalisé à l'import ; ouvert vers en_cours ou resolu, en_cours vers resolu dans le service API | CHECK sur les trois statuts ; les transitions sont contrôlées par le service |
| RG8 — Dates et technicien | Cohérence des dates ; technicien absent signalé sans rejet ; résolution datée par l'API | CHECK de présence et d'ordre des dates ; technicien nullable |

Les formats corrigeables sont normalisés, les violations restantes rejetées.
Les doublons exacts sont écartés. L'audit chiffré et le chemin du journal
figurent dans le [README](../README.md#audit-des-csv).

## Résultats de contrôle sur les CSV fiabilisés

- 120 stations, 2002 trajets et 177 incidents.
- Activité du 24 au 30 août 2026 : 329, 311, 306, 300, 315, 219, 222 trajets.
- Incidents avant modification : 46 en cours, 55 ouverts et 76 résolus.
- Le classement des stations additionne départs et arrivées ; une arrivée
  absente n'est attribuée à aucune station. Les égalités sont triées par identifiant.
