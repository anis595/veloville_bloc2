# VéloVille — Plateforme de valorisation des données

Projet de consultation des stations, trajets et incidents VéloVille.
La base PostgreSQL, les règles de fiabilisation et l'import CSV sont en place.

## Environnement

Python 3.12 ou supérieur et PostgreSQL 14 ou supérieur.
Les dépendances sont fixées dans `requirements.txt`. Installer avec
`python -m pip install -r requirements.txt` dans l'environnement virtuel.
Copier `.env.example` vers `.env`, puis renseigner la configuration locale.

## Import des données

Créer d'abord les tables avec `sql/schema.sql` et charger les comptes avec
`sql/comptes.sql`. Depuis la racine du projet, environnement virtuel activé :

```powershell
python scripts/importer.py
```

Le script lit les trois CSV de `data/`, les fiabilise, puis insère les stations
avant les trajets et incidents. Les insertions utilisent une transaction et
des paramètres SQL. `ON CONFLICT DO NOTHING` conserve les lignes déjà présentes,
y compris le statut d'un incident modifié après le premier import.

Le journal est [journal_import.csv](journal_import.csv), à la racine. Ses
colonnes sont : fichier source, identifiant, colonne, valeur, motif et décision.
Il est réécrit à chaque exécution. Les doublons portent le motif `Doublon exact`
avec décision `rejet`. Les avertissements non bloquants sont classés avec les
normalisations, et leur motif précise qu'il s'agit d'un avertissement.

Les lignes valides affichées sont les lignes importables du CSV. Elles ne
correspondent pas au nombre de nouvelles insertions lors d'un deuxième import.

## Audit des CSV

Contrôles avant chargement : identifiants, doublons, domaines de valeurs,
dates, durées, références aux stations et cohérence entre les colonnes.

| Défaut constaté | Nombre de lignes | Traitement |
|---|---:|---|
| Stations : défauts détectés | 0 | 120 stations conservées |
| Trajets : doublons exacts | 12 | Une seule occurrence conservée |
| Trajets : durée nulle ou négative | 9 | Rejet |
| Trajets : station d'arrivée inconnue | 7 | Rejet |
| Trajets : dates au format JJ/MM/AAAA HH:MM | 5 | Normalisation |
| Trajets : identifiant de vélo en minuscules | 6 | Normalisation |
| Incidents : statut avec casse ou espace non conforme | 125 | Normalisation |
| Incidents : résolution antérieure au signalement | 3 | Rejet |
| Incidents : technicien absent à la prise en charge | 25 | Avertissement sans rejet |

Une arrivée absente est autorisée : 23 lignes sources sont concernées,
dont 22 trajets conservés après traitement des autres défauts.

| Fichier | Lignes sources | Valides | Rejetées hors doublons | Doublons |
|---|---:|---:|---:|---:|
| stations.csv | 120 | 120 | 0 | 0 |
| trajets.csv | 2030 | 2002 | 16 | 12 |
| incidents.csv | 180 | 177 | 3 | 0 |

Le journal contient 192 événements. Plusieurs événements peuvent concerner
une même ligne : ce nombre ne correspond pas au nombre de lignes rejetées.

## Vérifications

```powershell
python scripts/importer.py
python scripts/importer.py
python -m pytest
```

Après chacun des deux imports, les comptages attendus sur une base initialement
vide sont 120 stations, 2002 trajets et 177 incidents.
Les tests de fiabilisation fonctionnent sans base. Les tests d'import utilisent
un schéma PostgreSQL temporaire, annulé après chaque test. Le compte configuré
par DATABASE_URL doit pouvoir créer un schéma dans la base.
