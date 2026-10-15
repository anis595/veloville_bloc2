# VéloVille — Plateforme de valorisation des données

Projet de consultation des stations, trajets et incidents VéloVille.
La base PostgreSQL, les règles de fiabilisation, l'import CSV, la connexion
JWT, les routes Stations, Trajets et Incidents et les trois indicateurs sont en place.
Le front Streamlit permet la connexion et la consultation des trois écrans.
Version 1.0.0. Installation complète dans
[la procédure de déploiement](docs/procedure-deploiement.md).

L'application suit le chemin CSV → fiabilisation → PostgreSQL → API FastAPI
→ Streamlit. Les routeurs délèguent les traitements aux services ; le front
centralise ses appels dans api_client.py.

## Environnement

Python 3.12 ou supérieur et PostgreSQL 14 ou supérieur.
Les dépendances sont fixées dans `requirements.txt`. Installer avec
`python -m pip install -r requirements.txt` dans l'environnement virtuel.
Copier `.env.example` vers `.env`, puis renseigner la configuration locale.

Dans PowerShell, depuis la racine du projet :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Ne pas écraser une configuration .env existante. Pour les commandes ci-dessous,
activer l'environnement ou remplacer `python` par `.\.venv\Scripts\python.exe`.

| Variable | Usage / valeur par défaut |
|---|---|
| DATABASE_URL | Connexion SQLAlchemy à PostgreSQL ; adapter celle de .env.example |
| JWT_SECRET | Secret à générer localement ; obligatoire |
| JWT_ALGORITHM | HS256 |
| JWT_EXPIRATION_MINUTES | 60 |
| API_URL | http://localhost:8000 |
| API_TIMEOUT_SECONDES | 5 |
| TEST_DATABASE_URL | Facultatif ; sinon les tests utilisent DATABASE_URL |
| TEST_PASSWORD | Facultatif ; sinon mot de passe de test généré aléatoirement |

Générer le secret avec `python -c "import secrets; print(secrets.token_hex(32))"`.
Les étapes de création de la base et des comptes sont dans la procédure.

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

## Connexion à l'API

Renseigner `JWT_SECRET` dans `.env` avec une valeur générée localement et garder
`JWT_ALGORITHM=HS256`. La durée des jetons est définie par
`JWT_EXPIRATION_MINUTES`, avec une valeur par défaut de 60 minutes.

```powershell
python -m uvicorn api.main:app --port 8000
```

Ouvrir http://localhost:8000/docs. `GET /sante` répond `{"statut":"ok"}`.
Dans `POST /auth/login`, envoyer l'identifiant et le mot de passe d'un des
comptes fournis. La réponse contient un jeton, son type `bearer` et le rôle.
Les mots de passe sont vérifiés avec bcrypt contre les hachages en base.

Les dépendances de sécurité vérifient la signature, l'expiration, le compte
et le rôle. Toutes les routes de données demandent un jeton. Un jeton absent
ou refusé produit un 401 ; un rôle insuffisant produit un 403.

Dans Swagger, copier la valeur de `access_token` obtenue à la connexion,
puis cliquer sur Authorize et coller le jeton seul, sans préfixe Bearer.

| Route | Paramètres / comportement |
|---|---|
| GET /stations | Filtre commune, page, taille_page ; tri par identifiant |
| GET /stations/{station_id} | Station détaillée ; 404 si absente |
| GET /trajets | Dates de début et fin incluses, station de départ ou d'arrivée, pagination ; tri par départ croissant |
| GET /incidents | Filtre statut, pagination ; tri par signalement décroissant |
| PUT /incidents/{incident_id}/statut | Rôle exploitant ; transitions ouvert vers en_cours ou resolu, en_cours vers resolu |

La pagination renvoie total, page, taille_page et resultats. La taille par
défaut est 20, le maximum 100 et la page minimale 1. Les paramètres hors
bornes donnent 422. Une période inversée est également refusée avec 422.

Le passage d'un incident à résolu renseigne sa date de résolution si elle
est vide. Les PUT modifient réellement la base ; un nouvel import conserve
ces modifications. Les tests annulent leurs propres modifications.

## Indicateurs

Les deux rôles peuvent consulter les trois routes protégées :

| Route | Calcul |
|---|---|
| GET /indicateurs/activite-par-jour | Nombre de départs par jour, dates de début et fin incluses ; toute la période sans filtre |
| GET /indicateurs/stations-actives | Départs et arrivées des stations classées par nombre total de mouvements ; limite par défaut 10, entre 1 et 50 |
| GET /indicateurs/incidents-par-statut | Nombre par statut présent et délai moyen de résolution en heures, arrondi à une décimale |

L'activité est triée par jour croissant. Les stations sont triées par mouvements
décroissants, puis par identifiant en cas d'égalité. Une arrivée absente ne compte
pour aucune station. Le délai moyen ne concerne que les incidents résolus avec
une date de résolution ; il vaut `null` s'il n'y en a aucun.

Les agrégats sont calculés en SQL avec SQLAlchemy : seules les lignes de résultat
sont renvoyées à l'application. Les tests vérifient les calculs sur un petit jeu
connu et les comparent aux requêtes SQL de contrôle sur les CSV fiabilisés.

## Connexion au front

Garder l'API démarrée et ouvrir un second terminal, depuis la racine du projet :

```powershell
python -m streamlit run front/app.py
```

Ouvrir http://localhost:8501. Le formulaire envoie l'identifiant et le mot de
passe masqué à `POST /auth/login`. Après connexion, le jeton et le rôle sont
conservés dans `st.session_state`. L'identifiant et le rôle sont affichés dans
la barre latérale ; « Se déconnecter » vide la session.

Le client `front/api_client.py` lit `API_URL` (défaut `http://localhost:8000`)
et `API_TIMEOUT_SECONDES` (défaut 5) dans l'environnement. Il ajoute le jeton
Bearer aux appels protégés et transforme les erreurs HTTP, les délais dépassés
et les pannes réseau en messages en français. Le jeton n'est pas affiché.

Les pages du menu latéral proposent :

- Stations : filtre par commune, pages de 10, 20 ou 50 lignes et total.
- Incidents : filtre par statut et pagination ; seul l'exploitant peut
  modifier le statut. Le tableau est rechargé après une modification.
- Indicateurs : période, nombre de stations et bouton « Actualiser »,
  trois métriques et trois tableaux, sans graphique.

Sans connexion, chaque page demande de se connecter et propose un lien vers
le formulaire. Les chargements, résultats vides et erreurs ont des messages
en français. La liste des communes est mise en cache pendant une heure ;
les listes paginées et les incidents restent lus dans l'API.

## Choix écoresponsables

La pagination est réalisée côté serveur, avec un maximum de 100 lignes par
requête. Le front propose des tailles de 10, 20 et 50 pour limiter les
transferts et l'affichage. Les indicateurs sont agrégés en SQL : l'application
reçoit les résultats des calculs, sans charger tous les trajets en mémoire.

La liste des communes est conservée avec `st.cache_data(ttl=3600)` pour éviter
de relire les stations à chaque interaction. Aucun rafraîchissement automatique
ni fonctionnement en temps réel n'est ajouté. Les filtres des indicateurs sont
regroupés dans un formulaire pour ne lancer les requêtes qu'à leur validation
ou à l'ouverture de la page. Les bibliothèques du squelette suffisent.

## Sauvegarde et restauration

Le script `scripts/sauvegarde.sh` crée une archive PostgreSQL horodatée au
format custom. Il demande `DATABASE_URL` dans l'environnement et renvoie
un code non nul si la sauvegarde échoue. Un fichier incomplet est supprimé.

Dans Git Bash, depuis la racine du projet :

```bash
set -a
source .env
set +a
bash scripts/sauvegarde.sh
```

Ajouter les outils PostgreSQL au PATH si nécessaire. Les commandes de contrôle
du catalogue et de restauration dans une base distincte figurent dans
[la procédure de déploiement](docs/procedure-deploiement.md).
Les archives de `sauvegardes/` sont ignorées par Git.

## Vérifications

```powershell
python scripts/importer.py
python scripts/importer.py
python -m pytest
python -m pytest --cov=api/services --cov-report=term-missing
```

Après chacun des deux imports, les comptages attendus sur une base initialement
vide sont 120 stations, 2002 trajets et 177 incidents.
Les tests de fiabilisation fonctionnent sans base. Les tests d'import, d'API
et d'indicateurs utilisent un schéma PostgreSQL temporaire, annulé après
chaque test. La configuration vient de `TEST_DATABASE_URL` si elle existe,
sinon de `DATABASE_URL`. Le compte doit pouvoir créer un schéma dans la base.
Les mots de passe de test sont générés aléatoirement, ou lus dans
`TEST_PASSWORD` si cette variable est définie.

Mesure du 15/10/2026 : **161 tests réussis ; couverture de api/services :
100 % des 326 instructions**, au-dessus du minimum de 60 % demandé.
Cette mesure porte sur les lignes exécutées, pas sur tous les comportements
possibles. Les parcours Streamlit sont également testés avec AppTest.
Un avertissement de dépréciation de Starlette concernant httpx est émis ;
les tests fonctionnent avec les versions fixées.

## Recette et documentation

Les dix cas du [plan fourni](docs/recette/plan-de-recette.md) ont été exécutés
dans l'ordre sur un schéma vide isolé : dix OK, aucun KO et aucun NT.
Les [résultats et le procès-verbal](docs/recette/resultats-recette.md) précisent
les preuves, les réserves et les contrôles restant à effectuer.

- [Schéma et règles de gestion](docs/schema-donnees.md)
- [Matrice des rôles et données sensibles](docs/matrice-roles-droits.md)
- [Déploiement, sauvegarde et restauration](docs/procedure-deploiement.md)
- [Journal des versions](CHANGELOG.md)
- [Support de soutenance, dix diapositives](docs/soutenance.pdf)

## Limites et points à valider

Le front a été vérifié par AppTest et le serveur Streamlit a démarré. La
lisibilité sur tablette, le clavier et le lecteur d'écran restent à valider
dans un navigateur. La restauration complète dans une autre base n'a pas été
exécutée ; seule la création d'une archive et la lecture de son catalogue
ont été vérifiées. Les essais n'ont porté que sur l'extrait de données fourni.

La gestion des comptes se fait par SQL. La déconnexion ne révoque pas un jeton
déjà émis ; il expire à l'échéance prévue. La purge et la planification des
sauvegardes ne sont pas incluses. Les fonctions météo et d'anticipation sont
hors du périmètre V1. Le schéma fourni ne migre pas une base ancienne.

Avant le dépôt, valider et signer le procès-verbal. L'énoncé demande aussi
une branche de fonctionnalité ou de correction fusionnée et un tag par version
du CHANGELOG ; ces éléments doivent correspondre à l'historique réellement livré.
