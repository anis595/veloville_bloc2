# Squelette du projet VéloVille — mode d'emploi

Ce dossier est le point de départ imposé de votre dépôt. Il contient
l'arborescence attendue, des fichiers vides ou des stubs (docstring
« À compléter : ... »), et quelques fichiers prêts à l'emploi.

## Contenu

| Chemin | État | Rôle |
|---|---|---|
| `README.md` | stub | Documentation principale du projet, à rédiger |
| `CHANGELOG.md` | amorce | Journal des versions, première entrée posée |
| `requirements.txt` | à compléter | Dépendances listées sans version : fixez-les |
| `.gitignore` | prêt | Exclusions Python, secrets, sauvegardes |
| `.env.example` | prêt | Variables attendues, sans valeur sensible |
| `data/` | prêt | Copie des trois exports CSV |
| `sql/schema.sql` | vide | Seules les sections sont posées |
| `sql/comptes.sql` | **prêt** | Les deux comptes fournis, mots de passe hachés bcrypt |
| `scripts/importer.py` | stub | Import et fiabilisation |
| `scripts/sauvegarde.sh` | stub | Sauvegarde pg_dump horodatée |
| `api/` | stubs | Application FastAPI, routeurs, services métier |
| `tests/` | stubs | `conftest.py`, tests unitaires et d'intégration |
| `front/` | stubs | Application Streamlit, client HTTP, trois pages |
| `docs/` | stubs | Schéma, matrice des droits, procédure, recette |
| `docs/recette/plan-de-recette.md` | prêt | Copie du plan de recette fourni |
| `docs/recette/anomalies/` | vide | Une fiche par anomalie |

`sql/comptes.sql` est le seul fichier contenant du code finalisé : il
insère les comptes `exploitant01` (rôle exploitant) et `direction01` (rôle
direction), mot de passe `Formation2026!` pour les deux. Il suppose que la
table `utilisateur` existe avec les colonnes `username`, `mot_de_passe_hash`
et `role`, et une contrainte d'unicité sur `username` (nécessaire au
`ON CONFLICT`).

## Initialisation

1. Copiez le dossier `squelette-git/` à l'emplacement de votre choix et
   renommez-le `veloville/`. Supprimez ce fichier `README-SQUELETTE.md` ou
   conservez-le : il n'est pas évalué.
2. Initialisez le dépôt et faites le premier commit :

   ```bash
   cd veloville
   git init -b main
   git add .
   git commit -m "Initialiser le projet VéloVille depuis le squelette fourni"
   ```

3. Associez le dépôt distant individuel indiqué par le formateur et poussez :

   ```bash
   git remote add origin <url-du-depot-individuel>
   git push -u origin main
   ```

4. Créez l'environnement virtuel et installez les dépendances :

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip freeze > requirements.txt   # puis relisez et nettoyez le fichier
   ```

5. Copiez `.env.example` en `.env` et renseignez les valeurs. Vérifiez avec
   `git status` que `.env` n'apparaît pas.

6. Créez la base et le rôle PostgreSQL (adaptez l'utilisateur
   administrateur à votre installation) :

   ```bash
   psql -U postgres -c "CREATE ROLE veloville LOGIN PASSWORD 'veloville';"
   psql -U postgres -c "CREATE DATABASE veloville OWNER veloville;"
   ```

   Puis, une fois `sql/schema.sql` écrit :

   ```bash
   psql -U veloville -d veloville -f sql/schema.sql
   psql -U veloville -d veloville -f sql/comptes.sql
   ```

## Conventions

- Lancement de l'API depuis la racine : `uvicorn api.main:app --reload`.
- Lancement du front depuis la racine : `streamlit run front/app.py`.
- Tests et couverture : `pytest --cov=api/services --cov-report=term-missing`.
- Les modules `api/services/fiabilisation.py` et `api/services/indicateurs.py`
  sont les modules métier dont la couverture est mesurée.
- Chaque stub indique dans sa docstring ce qu'il doit contenir. Les noms de
  fichiers et de dossiers ne doivent pas être modifiés ; vous pouvez ajouter
  des modules.
- Mot de passe du compte PostgreSQL, secret JWT : uniquement dans `.env`.
