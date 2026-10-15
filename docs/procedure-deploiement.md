# Procédure de déploiement

## Prérequis

Python 3.12 ou supérieur, PostgreSQL 14 ou supérieur, Git Bash pour le script
de sauvegarde sous Windows. PostgreSQL doit être démarré. Ajouter son dossier
bin au PATH, par exemple `C:\Program Files\PostgreSQL\18\bin` sur le poste vérifié.
Ouvrir un terminal à la racine du projet `veloville_bloc2`.

Environnement vérifié : Windows, Python 3.14.7 et PostgreSQL 18.6.

## Dépendances et configuration

Dans PowerShell :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Reporter la valeur générée dans JWT_SECRET du fichier .env. Renseigner la
connexion DATABASE_URL et vérifier les paramètres du front. Ne pas écraser
un fichier .env déjà configuré. Les secrets réels restent dans ce fichier.
Les caractères réservés du mot de passe PostgreSQL doivent être encodés
dans l'URI de connexion.

Sous Linux : `python3 -m venv .venv`, `source .venv/bin/activate`,
`python -m pip install -r requirements.txt`, puis `cp .env.example .env`.
Les commandes Python suivantes utilisent alors `python`.

## Base et comptes

Ouvrir `psql -h localhost -U postgres`. Pour une première installation :

```sql
CREATE ROLE veloville LOGIN;
\password veloville
CREATE DATABASE veloville OWNER veloville;
\q
```

La commande \password demande le mot de passe du rôle sans l'écrire dans
le script. Reporter ce mot de passe dans DATABASE_URL. Ne pas recréer le rôle
ou la base s'ils existent déjà.

Dans PowerShell, charger le schéma et les comptes :

```powershell
psql -h localhost -U veloville -d veloville -v ON_ERROR_STOP=1 -f sql/schema.sql
psql -h localhost -U veloville -d veloville -v ON_ERROR_STOP=1 -f sql/comptes.sql
.\.venv\Scripts\python.exe scripts/importer.py
.\.venv\Scripts\python.exe scripts/importer.py
```

Les comptages attendus aux deux passages sont 120 stations, 2002 trajets et
177 incidents. Le journal contient 192 événements. Les deux comptes fournis
sont exploitant01 et direction01 ; leur mot de passe est indiqué dans sql/comptes.sql.

Si des tables ont été créées avec un autre compte, accorder les droits depuis
psql, avec le compte administrateur connecté à la base veloville :

```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO veloville;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO veloville;
GRANT CREATE ON DATABASE veloville TO veloville;
```

Le dernier droit permet aux tests de créer leur schéma temporaire. Le schéma
SQL conserve les tables existantes ; il n'en modifie pas les anciennes
contraintes. Une installation vierge doit utiliser le schéma fourni.

## Tests et lancement

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=api/services --cov-report=term-missing
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Dans un second terminal à la racine du même projet :

```powershell
.\.venv\Scripts\python.exe -m streamlit run front/app.py
```

Vérifier http://localhost:8000/sante : 200, {"statut":"ok"}.
Ouvrir http://localhost:8501, se connecter et consulter les trois pages.
Dans http://localhost:8000/docs, appeler POST /auth/login, copier access_token,
cliquer sur Authorize et coller le jeton seul. Vérifier qu'un PUT est refusé
avec 403 pour direction, et autorisé pour exploitant sur une transition valide.
Arrêter les serveurs avec Ctrl+C.

Les tests annulent leurs modifications dans un schéma temporaire. Pour utiliser
une autre base de test, définir TEST_DATABASE_URL dans l'environnement ; le
compte doit pouvoir y créer un schéma. Les tests lisent JWT_SECRET depuis .env.

## Sauvegarde

Utiliser Bash (Git Bash sous Windows), avec `pg_dump` et `pg_restore` dans
le PATH. Les outils PostgreSQL doivent avoir une version au moins égale
à celle du serveur. Sous Windows, adapter le numéro de version installé :

```bash
export PATH="/c/Program Files/PostgreSQL/18/bin:$PATH"
```

Depuis la racine du projet, charger les variables locales et lancer le script :

```bash
set -a
source .env
set +a
bash -n scripts/sauvegarde.sh
bash scripts/sauvegarde.sh
```

Les valeurs contenant des caractères spéciaux doivent être entre guillemets
dans `.env`. Conserver `scripts/sauvegarde.sh` avec des fins de ligne LF.

Le script lit `DATABASE_URL` dans l'environnement et convertit le préfixe
`postgresql+psycopg:` en `postgresql:` pour `pg_dump`. Il produit une archive
au format custom, nommée `sauvegardes/veloville_AAAAMMJJ_HHMMSS.dump`.
Le chemin est relatif à la racine du projet, même si le script est appelé
depuis un autre dossier. Le code de retour est non nul en cas d'échec ;
un fichier incomplet est supprimé.

Vérifier le catalogue en remplaçant le nom par celui du fichier créé :

```bash
pg_restore --list sauvegardes/veloville_AAAAMMJJ_HHMMSS.dump
```

Le dossier `sauvegardes/` est ignoré par Git. Les archives contiennent les
données et les hachages des comptes : conserver une copie dans un emplacement
à accès restreint, hors du dépôt distant.

Vérifications locales réalisées : syntaxe Bash, sauvegarde réelle et lecture
du catalogue. Une configuration absente ou une connexion impossible renvoie
un code non nul, sans conserver de fichier incomplet.

## Restauration

Créer une base vide distincte pour vérifier une restauration. Adapter l'hôte,
le port et le compte administrateur à l'installation locale :

```bash
createdb -h localhost -p 5432 -U postgres -O veloville veloville_restauration
pg_restore -h localhost -p 5432 -U veloville -d veloville_restauration --no-owner --no-privileges --exit-on-error sauvegardes/veloville_AAAAMMJJ_HHMMSS.dump
psql -h localhost -p 5432 -U veloville -d veloville_restauration -c "SELECT count(*) FROM station; SELECT count(*) FROM trajet; SELECT count(*) FROM incident; SELECT count(*) FROM utilisateur;"
```

Les mots de passe sont demandés par les outils PostgreSQL. Sur les données
fournies après import, attendre 120 stations, 2002 trajets, 177 incidents
et deux comptes. Vérifier les comptes et les comptages avant d'utiliser cette
base. Arrêter l'API et le front, adapter `DATABASE_URL` dans `.env`, puis
redémarrer les deux services.

La restauration complète dans une base distincte reste à vérifier.
