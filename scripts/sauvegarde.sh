#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DATABASE_URL:?Renseignez DATABASE_URL dans les variables du terminal}"
url="${DATABASE_URL/postgresql+psycopg:/postgresql:}"
mkdir -p sauvegardes
fichier="sauvegardes/veloville_$(date +%Y%m%d_%H%M%S).dump"

if pg_dump --dbname="$url" --format=custom --file="$fichier"; then
    printf 'Sauvegarde créée : %s\n' "$fichier"
else
    rm -f -- "$fichier"
    exit 1
fi
