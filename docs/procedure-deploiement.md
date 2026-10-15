# Procédure de déploiement

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
